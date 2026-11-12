"""Grounding-first per-cluster choice: one decision per observed group (v4 lever 3).

v1 and v2 ask for one option per item, so a scene with two separate
conflicts needs one option that spans both, and the models rarely pick one
(docs/reports/2026-10-24-v4-gf-cluster-candidates.md, Rev 2). This variant
keeps v2's option list and asks for one choice per observed group instead:
the answer's `choices` object must have exactly the group labels as keys,
each mapped to one of that group's option ids or to `none_feasible`.

The slot split, the per-group answer contract (`choices_model` and the
parser) and the prompt section are shared with the live path in
`reasoning.vlm.per_cluster_choice`; the joint check is
`reasoning.rag.joint_check`. Their docstrings state the rules. This module
adapts a `BenchItem` to those plain inputs (`gf_cluster` for the v2 options,
`grounder_offline.ground_command` as the probe, the overlay's geometry for
the safety radius) and keeps the bench variant (the ask/re-ask loop) and the
zero-network sanity chooser. Nothing here reads `item.gt`.

`joint_check` reports what can be checked offline when the chosen commands
would be issued together; the live M5 dispatches one grounded command per
analysis, so nothing here is executable live as one decision.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any, Literal

from benchmarks.vlm_bench.grounder_offline import ground_command, item_config, item_frame
from benchmarks.vlm_bench.models import BenchItem
from benchmarks.vlm_bench.variants.base import ReplayContext, VariantAnswer
from benchmarks.vlm_bench.variants.gf_cluster import (
    GROUPING_RULE,
    ClusterOption,
    generate_cluster_candidates,
)
from reasoning.rag import joint_check as shared_joint_check
from reasoning.rag.joint_check import JointCheck
from reasoning.vlm.models import (
    BackendResponse,
    PromptPayload,
    ReasonerConfig,
    ReasonerRequest,
)
from reasoning.vlm.per_cluster_choice import (
    ANSWER_KEYS_PREFIX,
    GENERATOR_VERSION_PER_CLUSTER,
    NONE_FEASIBLE,
    SLOT_RULE,
    GroupSlot,
    OptionIds,
    PerClusterAnswer,
    PerClusterCandidateSet,
    build_slots,
    choices_model,
    chosen_options,
    compose_per_cluster_payload,
    group_decisions,
    opaque_id,
    parse_per_cluster_answer,
    read_answer_keys,
    render_per_cluster_section,
)
from reasoning.vlm.prompt_builder import build_prompt_payload
from reasoning.vlm.reasoner import build_reask_prompt, invoke_backend
from reasoning.vlm.retry_policy import DEFAULT_RETRY_POLICY, classify_failure

PER_CLUSTER_VARIANT = "grounding_first_per_cluster"


def per_cluster_candidates(
    item: BenchItem,
    include_wait: bool = True,
    option_ids: OptionIds = "numbered",
    shuffle_seed: int | None = None,
) -> tuple[PerClusterCandidateSet, tuple[int, ...] | None, int | None]:
    """Split the item's v2 options into one slot per observed group.

    Reads only what `generate_cluster_candidates` reads (scene state, recorded
    params and overlay, recorded classical `r_conflict_m`); never `item.gt`.
    The split is `reasoning.vlm.per_cluster_choice.build_slots`.

    Args:
        item: The bench item.
        include_wait: List `temporary_wait` options too.
        option_ids: "numbered" (v2's global 1-based numbers) or "opaque".
        shuffle_seed: When set, permute options within each group
            (`shuffle_cluster_candidates`); numbered ids follow the presented
            order, opaque ids follow the option.

    Returns:
        The slots, the presented order as unshuffled 1-based v2 numbers (None
        when not shuffled) and the per-item shuffle seed (or None).
    """
    base = generate_cluster_candidates(item, include_wait, "drop", "drop")
    return build_slots(base, option_ids, shuffle_seed)


def joint_check(item: BenchItem, chosen: Mapping[str, ClusterOption | None]) -> JointCheck:
    """Check the chosen options against each other as if issued together (scene only).

    Each chosen option is grounded again with the offline M3 (each one alone,
    as M3 always grounds). Reads the scene and the episode geometry, never
    `item.gt` (`reasoning.rag.joint_check.joint_check`).

    Args:
        item: The bench item.
        chosen: Label -> chosen option (None for `none_feasible`).

    Returns:
        The exact checks (shared robots, retreat clashes) and the heuristic
        path-proximity pairs.
    """
    geometry = item_config(item).scenario_geometry
    return shared_joint_check.joint_check(
        item_frame(item), chosen, lambda decision: ground_command(item, decision), geometry
    )


class GroundingFirstPerClusterVariant:
    """v2 options split per observed group; the reply's `choices` give one decision per group."""

    name = PER_CLUSTER_VARIANT
    generator_version: str | None = GENERATOR_VERSION_PER_CLUSTER

    def __init__(
        self,
        include_wait: bool = True,
        shuffle_seed: int | None = None,
        option_ids: OptionIds = "numbered",
    ) -> None:
        """Configure the variant.

        Args:
            include_wait: List `temporary_wait` options too.
            shuffle_seed: When set, shuffle options within each group.
            option_ids: "numbered" (v2 numbers) or "opaque" per-item tokens.
        """
        self.include_wait = include_wait
        self.shuffle_seed = shuffle_seed
        self.option_ids = option_ids

    def candidate_set(
        self, item: BenchItem
    ) -> tuple[PerClusterCandidateSet, tuple[int, ...] | None, int | None]:
        """The item's slots as presented, with the shuffle order and per-item seed.

        Args:
            item: The bench item.

        Returns:
            See `per_cluster_candidates`.
        """
        return per_cluster_candidates(item, self.include_wait, self.option_ids, self.shuffle_seed)

    def answer_extra(
        self,
        item: BenchItem,
        candidates: PerClusterCandidateSet,
        choices: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        """Per-item run-config record: groups, option ids, the choices and the joint check.

        Args:
            item: The bench item.
            candidates: The presented slots.
            choices: The validated choices, or None on a parse failure.

        Returns:
            A JSON-safe dict.
        """
        record: dict[str, Any] = {
            "grouping_threshold_m": candidates.base.threshold_m,
            "groups": {g.label: list(g.robots) for g in candidates.base.groups},
            "slots": {s.label: list(s.option_ids) for s in candidates.slots},
            "choices": None if choices is None else dict(choices),
        }
        if choices is not None:
            chosen = chosen_options(candidates, choices)
            record["chosen_v2_numbers"] = {
                label: None if o is None else candidates.base.options.index(o) + 1
                for label, o in chosen.items()
            }
            record["joint_check"] = joint_check(item, chosen).model_dump(mode="json")
        return record

    def run_info(self) -> dict[str, Any]:
        """Run-level settings for the run config.

        Returns:
            The grouping and slot rules and the flags.
        """
        return {
            "grouping_rule": GROUPING_RULE,
            "grouping_threshold_source": "item.classical.params.r_conflict_m",
            "slot_rule": SLOT_RULE,
            "offgroup": "drop",
            "cross_group": "drop",
            "include_wait": self.include_wait,
            "option_ids": self.option_ids,
            "schema_delivery": "prompt-stated keys + per-item Pydantic validation + re-ask",
        }

    def answer(
        self, item: BenchItem, request: ReasonerRequest, context: ReplayContext
    ) -> VariantAnswer:
        """Ask once per attempt with the composed prompt; re-ask on invalid choices.

        Backend errors back off as the production `Reasoner` does
        (`DEFAULT_RETRY_POLICY`); a deterministic 4xx ends the call.

        Args:
            item: The bench item.
            request: The rebuilt live request.
            context: Backend (cached) and reasoner config.

        Returns:
            `group_decisions` (label -> decision or None) on a valid reply;
            `decision=None` with `parse_status="failed"` after `max_attempts`.
        """
        candidates, order, item_seed = self.candidate_set(item)
        first = compose_per_cluster_payload(build_prompt_payload(request), candidates)
        sha = hashlib.sha256(first.user_prompt.encode()).hexdigest()
        config = context.reasoner_config
        payload = first
        attempts = 0
        waited = 0.0
        failed_once = False
        last: BackendResponse | None = None
        error: str | None = None
        while attempts < config.max_attempts:
            attempts += 1
            try:
                last = invoke_backend(context.backend, payload, config)
            except Exception as exc:  # one recorded attempt, as in `Reasoner.run`
                error = f"{type(exc).__name__}: {exc}"
                if classify_failure(exc) == "stop":
                    break
                if attempts < config.max_attempts:
                    waited += DEFAULT_RETRY_POLICY.wait_before_retry(exc, attempts, waited)
                continue
            parsed = parse_per_cluster_answer(last.text, candidates)
            if parsed.status == "choices":
                decisions = group_decisions(candidates, parsed.choices, parsed.model_answer)
                n_none = sum(1 for d in decisions.values() if d is None)
                return VariantAnswer(
                    decision=None,
                    group_decisions=decisions,
                    prompt_sha256=sha,
                    attempts=attempts,
                    parse_status="invalid" if failed_once else "valid",
                    raw_text=last.text,
                    n_candidates=candidates.n_options,
                    token_usage=last.token_usage,
                    latency_ms=last.latency_ms,
                    note=(
                        "choices="
                        + ",".join(f"{k}:{v}" for k, v in parsed.choices.items())
                        + f"; none_feasible={n_none}/{len(decisions)}"
                    ),
                    option_order=order,
                    shuffle_item_seed=item_seed,
                    extra=self.answer_extra(item, candidates, parsed.choices),
                )
            failed_once = True
            error = parsed.error
            if config.allow_reask:
                payload = build_reask_prompt(first, error or "invalid choices")
        return VariantAnswer(
            decision=None,
            prompt_sha256=sha,
            attempts=attempts,
            parse_status="failed",
            raw_text=None if last is None else last.text,
            n_candidates=candidates.n_options,
            token_usage=None if last is None else last.token_usage,
            latency_ms=None if last is None else last.latency_ms,
            note=f"parse_failure: {error}",
            option_order=order,
            shuffle_item_seed=item_seed,
            extra=self.answer_extra(item, candidates, None),
        )


class FixedGroupChoiceBackend:
    """A zero-network backend that answers the same rule in every group (sanity chooser).

    It reads the slot labels and allowed ids from the composed prompt's
    stated answer keys, so it needs no item.
    """

    def __init__(self, policy: Literal["first", "none_feasible"] = "first") -> None:
        """Fix the rule.

        Args:
            policy: "first" (the first listed option of every group) or
                "none_feasible" (every group).
        """
        self.policy = policy
        self.calls = 0

    def analyze(self, payload: PromptPayload, config: ReasonerConfig) -> BackendResponse:
        """Answer the rule's choice for every stated group.

        Args:
            payload: The composed payload.
            config: Ignored.

        Returns:
            The reply in the decision JSON shape plus `choices`.
        """
        self.calls += 1
        keys = read_answer_keys(payload.user_prompt)
        choices = {
            label: ids[0] if self.policy == "first" else NONE_FEASIBLE
            for label, ids in keys.items()
        }
        text = json.dumps(
            {
                "congestion_detected": True,
                "type": "deadlock",
                "involved_robots": [],
                "root_cause": "fixed-group-choice sanity backend",
                "strategy": "yield",
                "justification": "fixed-group-choice sanity backend",
                "choices": choices,
            }
        )
        return BackendResponse(text=text, backend_id="fixed-group-choice")


__all__ = [
    "ANSWER_KEYS_PREFIX",
    "FixedGroupChoiceBackend",
    "GENERATOR_VERSION_PER_CLUSTER",
    "GroundingFirstPerClusterVariant",
    "GroupSlot",
    "JointCheck",
    "NONE_FEASIBLE",
    "PER_CLUSTER_VARIANT",
    "PerClusterAnswer",
    "PerClusterCandidateSet",
    "choices_model",
    "chosen_options",
    "compose_per_cluster_payload",
    "group_decisions",
    "joint_check",
    "opaque_id",
    "parse_per_cluster_answer",
    "per_cluster_candidates",
    "read_answer_keys",
    "render_per_cluster_section",
]
