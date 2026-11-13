"""Offline evidence for the v4 refusal-feedback keys on recorded items (zero network).

Rebuilds every item's live prompt through the production builder (and checks
it against the recorded SHA-256), then rebuilds it with Change 1 only and with
both changes (`benchmarks.vlm_bench.refusal_feedback_replay`). Writes to OUT_DIR:

- `summary.json`: offered-set counts, prompt-length deltas (characters, and
  text tokens estimated from each item's recorded text-token/character ratio),
  how often a withheld plan was shown live, how many withheld analyses were
  followed by an overlapping analysis inside the feedback window, and the
  replay cost estimate from each bundle's `cost.log`;
- `excerpts.txt`: before/after context blocks for the named episodes;
- `hiding_excerpts.txt`: the same episodes' context blocks with both keys on,
  before and after the finished-plan rule (`plan_tracker.hidden_plan_reason`);
- `items_withheld.jsonl`: the withheld analyses, for a paid replay, with
  `frame_path` set to the bundle's kept annotated frame where one exists.

No model is called; the model's answers stay the recorded ones.

Usage (from the repo root, PYTHONPATH as for the unit tests):
    python scripts/refusal_feedback_offline.py ITEMS.jsonl OUT_DIR [EPISODE_SUBSTR ...]
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

from benchmarks.vlm_bench.items import write_items
from benchmarks.vlm_bench.refusal_feedback_replay import (
    cached_episode_states,
    feedback_request,
    items_by_episode,
    read_m5_log,
)
from benchmarks.vlm_bench.run import load, rebuild_request
from reasoning.vlm.prompt_builder import build_prompt_payload

WINDOW_SEC = 300.0
MAX_ENTRIES = 3
_COST_RE = re.compile(
    r"billed_calls=(\d+)(?:\s+shadow_calls=(\d+)\s+shadow_usd=([0-9.]+))?\s+est_usd=([0-9.]+)"
)


def _usd_per_ordinary_call(bundle: Path) -> float | None:
    # `items.est_usd_per_call` does not parse the shadow-cell cost line, whose
    # billed calls include one per-cluster shadow call per analysis.
    path = bundle / "cost.log"
    matches = _COST_RE.findall(path.read_text()) if path.is_file() else []
    if not matches:
        return None
    billed, shadow_calls, shadow_usd, usd = matches[-1]
    calls = int(billed) - int(shadow_calls or 0)
    return (float(usd) - float(shadow_usd or 0.0)) / calls if calls > 0 else None


def _finished(plan_state: Any) -> bool:
    # Every leg that is part of the resolution (not "continue") is terminal.
    legs = [leg for leg in plan_state.legs if leg.action != "continue"]
    return bool(legs) and all(leg.status in ("done", "failed", "exhausted") for leg in legs)


def _leg_pending_or_active(plan_state: Any) -> bool:
    # The leg-status-only reading of "in progress", for comparison.
    return any(
        leg.action != "continue" and leg.status in ("pending", "active")
        for leg in plan_state.legs
    )


def _context_block(user: str) -> str:
    return user[user.index("Known robot IDs") : user.index("Guidance:")].strip()


def _stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    return {"median": statistics.median(values), "max": max(values), "min": min(values)}


def _refusal_block(user: str) -> str | None:
    marker = "Proposals the system withheld"
    if marker not in user:
        return None
    return user[user.index(marker) :].split("\n\n", 1)[0]


def _hiding_summary(
    rows: list[dict[str, Any]],
    d_hide: list[int],
    d_hide_tok: list[float],
    d_after: list[int],
) -> dict[str, Any]:
    # Both keys on, before vs after the finished-plan rule. "in progress" is
    # the rule's own reading (no hidden reason); the leg-only reading counts a
    # resolution leg still pending/active by its (recorded or reconstructed)
    # status alone.
    def count(subset: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "prompts": len(subset),
            "plan_block_before": sum(r["plan_block_both_before_hiding"] for r in subset),
            "plan_block_after": sum(r["plan_block_both"] for r in subset),
            "hold_this_plan_before": sum(r["hold_this_plan_both_before_hiding"] for r in subset),
            "hold_this_plan_after": sum(r["hold_this_plan_both"] for r in subset),
        }

    with_block = [r for r in rows if r["plan_block_both_before_hiding"]]
    hidden = [r for r in with_block if r["plan_hidden_reason"] is not None]
    return {
        "all": count(rows),
        "shown_plan_in_progress": count(
            [r for r in with_block if r["plan_hidden_reason"] is None]
        ),
        "shown_plan_not_in_progress": count(hidden),
        "by_plan_state_source": {
            source: {
                "in_progress": sum(
                    r["plan_state_source"] == source and r["plan_hidden_reason"] is None
                    for r in with_block
                ),
                "hidden": sum(r["plan_state_source"] == source for r in hidden),
            }
            for source in ("recorded", "reconstructed", "acceptance")
        },
        "by_in_flight_source": {
            source: sum(r["in_flight_source"] == source for r in with_block)
            for source in ("log", "artifact_proxy")
        },
        "hidden_reasons": {
            reason: sum(r["plan_hidden_reason"] == reason for r in hidden)
            for reason in ("completed", "failed", "not_dispatched", "no_resolution_legs")
        },
        "leg_only_in_progress": sum(r["candidate_leg_pending_or_active"] for r in with_block),
        "dispatch_aware_in_progress": len(with_block) - len(hidden),
        "hidden_with_previous_attempt_block": sum(r["previous_attempt_block"] for r in hidden),
        "hidden_with_earlier_failed_block": sum(r["earlier_failed_block"] for r in hidden),
        "hidden_failed_with_any_attempt_block": sum(
            r["previous_attempt_block"] or r["earlier_failed_block"]
            for r in hidden if r["plan_hidden_reason"] == "failed"
        ),
        "hidden_failed": sum(r["plan_hidden_reason"] == "failed" for r in hidden),
        "refusal_block_unchanged_all": all(r["refusal_block_unchanged"] for r in rows),
        "prompts_with_refusal_block": sum(r["n_refused"] > 0 for r in rows),
        "chars_delta_hiding": _stats([d for d, r in zip(d_hide, rows, strict=True) if d]),
        "est_text_tokens_delta_hiding": _stats([t for t in d_hide_tok if t]),
        "chars_delta_after_vs_live": _stats(d_after),
    }


def main(argv: list[str]) -> int:
    items_path, out_dir = Path(argv[1]), Path(argv[2])
    excerpt_episodes = argv[3:] or ["pos25", "pos23"]
    out_dir.mkdir(parents=True, exist_ok=True)
    items = load(items_path)
    rows: list[dict[str, Any]] = []
    excerpts: list[str] = []
    hiding_excerpts: list[str] = []
    withheld_items = []
    usd_per_call: dict[str, float | None] = {}
    for bundle, episode in items_by_episode(items).items():
        states = cached_episode_states(bundle, WINDOW_SEC, MAX_ENTRIES)
        states_before = cached_episode_states(
            bundle, WINDOW_SEC, MAX_ENTRIES, hide_finished=False
        )
        times = read_m5_log(Path(bundle))
        usd_per_call[bundle] = _usd_per_ordinary_call(Path(bundle))
        artifacts = {
            item.request_id: json.loads(
                (Path(bundle) / "decisions" / f"{item.request_id}.json").read_text()
            )
            for item in episode
        }
        for index, item in enumerate(episode):
            base_request = rebuild_request(item, "frame.png")
            base = build_prompt_payload(base_request).user_prompt
            assert hashlib.sha256(base.encode()).hexdigest() == item.prompt.user_sha256
            state = states.get(item.request_id)
            offer = build_prompt_payload(feedback_request(base_request, item, None)).user_prompt
            both = build_prompt_payload(feedback_request(base_request, item, state)).user_prompt
            # Both keys on, before the finished-plan rule (66c323f).
            before_state = states_before.get(item.request_id)
            both_before = build_prompt_payload(
                feedback_request(base_request, item, before_state)
            ).user_prompt
            candidate = None if before_state is None else before_state.plan_state
            usage = item.recorded.token_usage or {}
            ratio = (usage.get("input_tokens_text") or 0) / len(base) if base else 0.0
            art = artifacts[item.request_id]
            withheld = bool(art.get("dispatch_withheld"))
            later = [
                other for other in episode[index + 1 :]
                if set((art.get("decision") or {}).get("involved_robots") or [])
                & set(times.start.get(other.request_id, (0.0, []))[1])
            ]
            next_gap = None
            if withheld and later and item.request_id in times.written:
                next_gap = times.start[later[0].request_id][0] - times.written[item.request_id]
            rows.append({
                "episode": Path(bundle).name, "request_id": item.request_id,
                "t_s": round(item.t_s, 1), "withheld": withheld,
                "strategy": (art.get("decision") or {}).get("strategy"),
                "base_offers_jc": '"junction_clear"' in base,
                "offer_offers_jc": '"junction_clear"' in offer,
                "both_offers_jc": '"junction_clear"' in both,
                "hold_this_plan_base": "Hold this plan" in base,
                "hold_this_plan_both_before_hiding": "Hold this plan" in both_before,
                "hold_this_plan_both": "Hold this plan" in both,
                "plan_block_both_before_hiding": "Active plan (plan_id=" in both_before,
                "plan_block_both": "Active plan (plan_id=" in both,
                "plan_hidden_reason": None if state is None else state.plan_hidden_reason,
                "in_flight_source": None if state is None else state.in_flight_source,
                "candidate_leg_pending_or_active": bool(
                    candidate is not None and _leg_pending_or_active(candidate)
                ),
                "previous_attempt_block": "Previous attempt in this episode:" in both,
                "earlier_failed_block": "Earlier failed attempt in this episode:" in both,
                "refusal_block_unchanged": _refusal_block(both) == _refusal_block(both_before),
                "chars_both_before_hiding": len(both_before),
                "live_plan_was_withheld": bool(state and state.live_plan_was_withheld),
                "plan_state_source": None if state is None else state.plan_state_source,
                "both_plan_finished": bool(candidate is not None and _finished(candidate)),
                "n_refused": 0 if state is None else len(state.refused_proposals),
                "chars_base": len(base), "chars_offer": len(offer), "chars_both": len(both),
                "tok_ratio": ratio,
                "next_overlapping_gap_wall_s": next_gap,
            })
            if withheld:
                # The live annotated frame, when the bundle kept it: without
                # one the replay sends a neutral grey image instead.
                frame = Path(bundle) / "frames" / f"{item.request_id}.png"
                if item.frame_path is None and frame.is_file():
                    item = item.model_copy(update={"frame_path": str(frame)})
                withheld_items.append(item)
            if any(tag in Path(bundle).name for tag in excerpt_episodes):
                excerpts.append(
                    f"=== {Path(bundle).name} t_s={item.t_s:.1f} {item.request_id[:8]} "
                    f"decision={(art.get('decision') or {}).get('strategy')} "
                    f"withheld={withheld}\n--- BEFORE (live)\n{_context_block(base)}\n"
                    f"--- AFTER (both keys on)\n{_context_block(both_before)}\n"
                )
                hiding_excerpts.append(
                    f"=== {Path(bundle).name} t_s={item.t_s:.1f} {item.request_id[:8]} "
                    f"decision={(art.get('decision') or {}).get('strategy')} "
                    f"withheld={withheld} plan_source="
                    f"{None if state is None else state.plan_state_source} in_flight_source="
                    f"{None if state is None else state.in_flight_source} hidden_reason="
                    f"{None if state is None else state.plan_hidden_reason}\n"
                    f"--- BEFORE HIDING (both keys on, 66c323f)\n{_context_block(both_before)}\n"
                    f"--- AFTER HIDING\n{_context_block(both)}\n"
                )
    write_items(withheld_items, out_dir / "items_withheld.jsonl")
    (out_dir / "excerpts.txt").write_text("\n".join(excerpts))
    (out_dir / "hiding_excerpts.txt").write_text("\n".join(hiding_excerpts))
    d_offer = [r["chars_offer"] - r["chars_base"] for r in rows]
    d_both = [r["chars_both_before_hiding"] - r["chars_base"] for r in rows]
    d_hide = [r["chars_both"] - r["chars_both_before_hiding"] for r in rows]
    d_hide_tok = [d * r["tok_ratio"] for d, r in zip(d_hide, rows, strict=True)]
    d_after = [r["chars_both"] - r["chars_base"] for r in rows]
    d_tok = [(r["chars_both_before_hiding"] - r["chars_base"]) * r["tok_ratio"] for r in rows]
    w = [r for r in rows if r["withheld"]]
    gaps = [r["next_overlapping_gap_wall_s"] for r in w if r["next_overlapping_gap_wall_s"]]
    replay_usd = sum(usd_per_call.get(i.bundle) or 0.0 for i in withheld_items)
    summary = {
        "items": len(rows),
        "withheld": len(w),
        "base_prompts_offering_junction_clear": sum(r["base_offers_jc"] for r in rows),
        "change1_prompts_offering_junction_clear": sum(r["offer_offers_jc"] for r in rows),
        "both_prompts_offering_junction_clear": sum(r["both_offers_jc"] for r in rows),
        "live_prompts_showing_a_withheld_plan": sum(r["live_plan_was_withheld"] for r in rows),
        "live_prompts_with_hold_this_plan": sum(r["hold_this_plan_base"] for r in rows),
        "both_prompts_with_hold_this_plan": sum(
            r["hold_this_plan_both_before_hiding"] for r in rows
        ),
        "both_prompts_showing_a_finished_plan": sum(r["both_plan_finished"] for r in rows),
        "hiding": _hiding_summary(rows, d_hide, d_hide_tok, d_after),
        "both_prompts_with_refusal_feedback": sum(r["n_refused"] > 0 for r in rows),
        "withheld_prompts_with_refusal_feedback": sum(r["n_refused"] > 0 for r in w),
        "plan_state_source": {
            s: sum(r["plan_state_source"] == s for r in rows)
            for s in ("none", "recorded", "reconstructed", "acceptance")
        },
        "chars_delta_change1": _stats(d_offer),
        "chars_delta_both": _stats(d_both),
        "est_text_tokens_delta_both": _stats(d_tok),
        "withheld_followed_by_overlapping_analysis": len(gaps),
        "within_window": sum(g <= WINDOW_SEC for g in gaps),
        "next_overlapping_gap_wall_s": _stats(gaps),
        "replay_withheld_calls": len(withheld_items),
        "replay_items_with_live_frame": sum(i.frame_path is not None for i in withheld_items),
        "replay_usd_estimate_from_cost_logs": round(replay_usd, 4),
        "window_sec": WINDOW_SEC, "max_entries": MAX_ENTRIES,
    }
    (out_dir / "summary.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
