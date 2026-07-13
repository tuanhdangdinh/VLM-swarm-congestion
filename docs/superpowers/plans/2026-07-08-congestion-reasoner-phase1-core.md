# Congestion Reasoner Phase 1 — Reasoning Core & Arm B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the offline (non-ROS2) reasoning core of the rev-8 congestion-resolution research design: stage-1/stage-2 VLM contracts, temporal/failure/modality prompt machinery, derived-geometry grounding (Pillars 1, 2, 4), and the Arm B classical reasoner with shadow comparison.

**Architecture:** Everything in this phase is pure Python under `reasoning/`, unit-testable without ROS2, Isaac, or network. New VLM fields and prompt blocks extend the existing M2 contract models; the grounder gains a `derived` mode behind a `GroundingParams.mode` switch (default `legacy`) so the live pipeline is behavior-identical until Phase 2 flips the call site. The classical reasoner (Arm B) emits the same `CongestionDecision` type the VLM emits, so grounding/validation/execution are shared by construction.

**Tech Stack:** Python 3.10+, Pydantic v2 (frozen models), jsonschema Draft 2020-12, pytest, PyYAML. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md` (rev 8). Normative mechanism detail: its Appendix A. Arm B rules: its "Arm B — classical reasoner specification" section.

## Global Constraints

- Type hints on every public signature; `X | Y` unions, built-in generics (`list[str]`, `tuple[float, float]`), never `typing.Optional`/`List`.
- All cross-module data contracts are Pydantic v2 models with `ConfigDict(frozen=True)`.
- Google-style docstrings on every public function/class; one-line summary ending with a period.
- Imports ordered stdlib / third-party / local with one blank line between groups; no wildcard imports.
- Strategy tokens are exactly the existing enum: `yield`, `reroute`, `convoy`, `priority_override`, `temporary_wait`, `reverse` (rev-8 "Naming rule"). This plan introduces **no new enum entries**.
- Schema changes are additive-optional only; `required` arrays in existing JSON schemas do not change.
- Existing unit tests must stay green **unmodified**, with one allowed exception: `tests/unit/test_prompt_builder.py` assertions that pin the exact old template text may be updated minimally (Task 5 notes this).
- Legacy grounding output must remain byte-identical: `ground_reasoner_result(result)` with no new arguments returns exactly today's command dicts (no `degradations` key).
- Commits: Conventional Commits, subject < 72 chars, no body, no `Co-Authored-By` trailer.
- Run tests with the venv active: `source .venv/bin/activate` once per session; gate every commit on the touched test file plus `pytest tests/unit -q`.
- Do not log secrets or base64 image data anywhere.

## Design decisions locked in this plan

These interpret the spec where it under-determines the code; reviewers should check them once here rather than per-task:

1. **Reasoning-side snapshot contract.** M5's `SceneSnapshot` (ROS2 package) never crosses into `reasoning/`. This plan defines `SnapshotFrame` (stamp + `list[RobotStateInput]`) in `reasoning/vlm/models.py`; Phase 2 converts at the call site.
2. **Legacy/derived mode switch.** `GroundingParams.mode: Literal["legacy", "derived"] = "legacy"`. Legacy is the verbatim current grounder body; derived is the Appendix-A behavior (no-snapshot ⇒ non-spatial wait, feasibility bands, candidates, compatibility matrix).
3. **Clearance constants are exposed directly**, not as the spec's `2*min_distance_m + margin` formula: `backup_clearance_m = 1.7` and `escort_clearance_m = 0.5` reproduce the verified head-on tuning (1.3 m backup from a 0.4 m standoff; 2.4 m escort from a 1.9 m park distance). The formula lives in the field docstrings.
4. **Backup feasibility is a numeric scan** (0.01 m steps over the band), not interval algebra — simpler to verify, fast at this scale.
5. **Sweep validation thresholds are per-robot:** `min(min_distance_m, starting separation to that robot)`. A deadlock's pre-existing sub-threshold separation must not veto the retreat that resolves it; the maneuver must simply never make any separation worse than that floor.
6. **Classical type mapping** onto the existing enum: `head_on → deadlock`, `intersection → bottleneck`, `blocked_path → anomaly`, `unknown → anomaly` (scenario kind is also carried verbatim in a `scenario` field for artifacts).
7. **`MotionTableEntry` carries `arrival_stamp`** in addition to `arrival_order` so the classical FCFS tiebreak reuses the same derivation instead of duplicating zone-entry detection.

## File structure

Created:

- `reasoning/schemas/retreat_choice.schema.json` — stage-2 response schema.
- `reasoning/vlm/motion_table.py` — snapshot history → `MotionTable` derivation.
- `reasoning/rag/maneuver_geometry.py` — `GroundingParams`, projections, backup/escort derivations (Pillar 1), config loader.
- `reasoning/rag/retreat_candidates.py` — candidate generation, swept-path validation, deterministic ranking (Pillar 2).
- `reasoning/rag/strategy_compatibility.py` — blocker-kind compatibility matrix (Pillar 4).
- `reasoning/baselines/__init__.py`, `reasoning/baselines/classical_reasoner.py`, `reasoning/baselines/shadow.py` — Arm B + shadow comparison.
- Tests: `tests/unit/test_vlm_models.py`, `test_retreat_choice_parser.py`, `test_motion_table.py`, `test_maneuver_geometry.py`, `test_retreat_candidates.py`, `test_strategy_compatibility.py`, `test_classical_reasoner.py`, `test_shadow_comparison.py`.

Modified:

- `reasoning/vlm/models.py` — `BlockerKind`, `ModalityCondition`, `SnapshotFrame`, `MotionTable(+Entry)`, `FailureContext`, `RetreatChoiceDecision`; new optional fields on `CongestionDecision` and `ReasonerRequest`; `PromptPayload.image_path: str | None`.
- `reasoning/schemas/vlm_decision.schema.json` — optional `blocker_kind`/`yield_robot`/`crossing_order`.
- `reasoning/schemas/coordination_command.schema.json` — optional `degradations`.
- `reasoning/vlm/output_parser.py` — `_extract_json_object` factoring, role-field validation, `parse_retreat_choice_text`.
- `reasoning/vlm/prompt_builder.py` — sectioned template, motion/failure blocks, annotation-scheme sentence, modality assembly.
- `reasoning/vlm/openai_backend.py`, `anthropic_backend.py`, `llama_server_backend.py` — skip image part when `image_path is None`.
- `reasoning/rag/command_grounder.py` — mode switch, derived flow, `prepare_retreat_selection`, retreat-choice application.
- `reasoning/vlm/__init__.py` — new exports.
- `config/rag.yaml` — `grounding:` and `classical:` sections.
- `docs/specs/module2_vlm_reasoning.md`, `docs/specs/module3_rag_grounding.md` — contract addenda (Task 15).
- Test extensions: `tests/unit/test_schemas.py`, `test_vlm_output_parser.py`, `test_prompt_builder.py`, `test_openai_backend.py`, `test_anthropic_backend.py`, `test_llama_server_backend.py` (create if missing), `test_command_grounder.py`.

Interface freeze for Phase 2 (M5 will call): `derive_motion_table(...)`, `build_prompt_payload(request)` with the new `ReasonerRequest` fields, `ground_reasoner_result(result, snapshot=..., params=..., retreat_choice=...)`, `prepare_retreat_selection(...)`, `decide_classical(...)`, `compare_decisions(...)`, `load_grounding_params(...)`, `load_classical_params(...)`.

---

### Task 1: Stage-1 contract — `SnapshotFrame` + role fields on `CongestionDecision`

**Files:**
- Modify: `reasoning/vlm/models.py`
- Modify: `reasoning/schemas/vlm_decision.schema.json`
- Create: `tests/unit/test_vlm_models.py`
- Modify: `tests/unit/test_schemas.py`

**Interfaces:**
- Consumes: existing `RobotStateInput`, `CongestionDecision` in `reasoning/vlm/models.py`.
- Produces: `BlockerKind = Literal["robot", "object", "transient"]`; `SnapshotFrame(stamp: float, robots: list[RobotStateInput])` with method `find_robot(robot_id: str) -> RobotStateInput | None`; `CongestionDecision` gains `blocker_kind: BlockerKind | None = None`, `yield_robot: str | None = None`, `crossing_order: list[str] | None = None`. All later tasks import these from `reasoning.vlm.models`.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_vlm_models.py`:

```python
import pytest
from pydantic import ValidationError

from reasoning.vlm.models import CongestionDecision, RobotStateInput, SnapshotFrame


def _decision(**overrides):
    base = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": ["robot_1", "robot_2"],
        "root_cause": "head-on standoff",
        "strategy": "yield",
        "justification": "two robots face to face",
    }
    base.update(overrides)
    return CongestionDecision(**base)


class TestCongestionDecisionRoleFields:
    def test_role_fields_default_none(self):
        decision = _decision()
        assert decision.blocker_kind is None
        assert decision.yield_robot is None
        assert decision.crossing_order is None

    def test_role_fields_accepted(self):
        decision = _decision(
            blocker_kind="robot",
            yield_robot="robot_1",
            crossing_order=["robot_2"],
        )
        assert decision.blocker_kind == "robot"
        assert decision.yield_robot == "robot_1"
        assert decision.crossing_order == ["robot_2"]

    def test_blocker_kind_lowercased(self):
        decision = _decision(blocker_kind="Object")
        assert decision.blocker_kind == "object"

    def test_blocker_kind_rejects_unknown_value(self):
        with pytest.raises(ValidationError):
            _decision(blocker_kind="wall")


class TestSnapshotFrame:
    def test_find_robot_returns_matching_state(self):
        frame = SnapshotFrame(
            stamp=12.5,
            robots=[RobotStateInput(robot_id="robot_1", x=1.0, y=2.0, theta=0.0)],
        )
        state = frame.find_robot("robot_1")
        assert state is not None
        assert state.x == 1.0

    def test_find_robot_returns_none_for_unknown_id(self):
        frame = SnapshotFrame(stamp=0.0, robots=[])
        assert frame.find_robot("robot_9") is None

    def test_snapshot_frame_is_frozen(self):
        frame = SnapshotFrame(stamp=0.0, robots=[])
        with pytest.raises(ValidationError):
            frame.stamp = 1.0
```

Append to `tests/unit/test_schemas.py`:

```python
def test_vlm_decision_schema_accepts_optional_role_fields():
    from jsonschema import Draft202012Validator

    from reasoning.schemas import load_schema

    payload = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": ["robot_1", "robot_2"],
        "root_cause": "standoff",
        "strategy": "yield",
        "justification": "j",
        "blocker_kind": "robot",
        "yield_robot": "robot_1",
        "crossing_order": ["robot_2"],
    }
    Draft202012Validator(load_schema("vlm_decision")).validate(payload)


def test_vlm_decision_schema_still_accepts_legacy_payload():
    from jsonschema import Draft202012Validator

    from reasoning.schemas import load_schema

    payload = {
        "congestion_detected": False,
        "type": "none",
        "involved_robots": [],
        "root_cause": "clear",
        "strategy": "none",
        "justification": "j",
    }
    Draft202012Validator(load_schema("vlm_decision")).validate(payload)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_vlm_models.py tests/unit/test_schemas.py -v`
Expected: `test_vlm_models.py` fails with `ImportError: cannot import name 'SnapshotFrame'`; the new schema test fails with `ValidationError` (additionalProperties).

- [ ] **Step 3: Implement**

In `reasoning/vlm/models.py`, add after the imports:

```python
BlockerKind = Literal["robot", "object", "transient"]
ModalityCondition = Literal["dual", "text_only", "image_only"]
```

Add after `RobotStateInput`:

```python
class SnapshotFrame(BaseModel):
    """One reasoning-side scene snapshot (M5 converts its SceneSnapshot to this)."""

    model_config = ConfigDict(frozen=True)

    stamp: float = Field(ge=0)
    robots: list[RobotStateInput]

    def find_robot(self, robot_id: str) -> RobotStateInput | None:
        """Return the state for `robot_id`, or None if absent from this frame."""
        for state in self.robots:
            if state.robot_id == robot_id:
                return state
        return None
```

In `CongestionDecision`, add fields after `justification`:

```python
    blocker_kind: BlockerKind | None = None
    yield_robot: str | None = None
    crossing_order: list[str] | None = None
```

Extend the existing lowercase validator decorator to cover the new enum field:

```python
    @field_validator("type", "strategy", "blocker_kind", mode="before")
    @classmethod
    def _lowercase_enum(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value
```

In `reasoning/schemas/vlm_decision.schema.json`, add to `"properties"` (leave `"required"` and `"additionalProperties": false` unchanged):

```json
    "blocker_kind": {
      "type": ["string", "null"],
      "enum": ["robot", "object", "transient", null]
    },
    "yield_robot": { "type": ["string", "null"] },
    "crossing_order": {
      "type": ["array", "null"],
      "items": { "type": "string" }
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_vlm_models.py tests/unit/test_schemas.py -v`
Expected: PASS (all).

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/vlm/models.py reasoning/schemas/vlm_decision.schema.json tests/unit/test_vlm_models.py tests/unit/test_schemas.py
git commit -m "feat: add stage-1 role fields and SnapshotFrame contract"
```

---

### Task 2: Parser role-field validation

**Files:**
- Modify: `reasoning/vlm/output_parser.py` (inside `parse_decision_text`)
- Modify: `tests/unit/test_vlm_output_parser.py`

**Interfaces:**
- Consumes: `CongestionDecision` role fields (Task 1).
- Produces: `parse_decision_text` now rejects (raises `VLMOutputParseError`) any decision where `yield_robot ∉ involved_robots`, where `crossing_order` is present without `yield_robot` or is not a duplicate-free permutation of `involved_robots − {yield_robot}`, or where role/semantic fields appear on a `congestion_detected=false` decision. Downstream (reasoner reask loop) is unchanged — a raise triggers the existing containment path.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_vlm_output_parser.py`:

```python
import json

import pytest

from reasoning.vlm.errors import VLMOutputParseError
from reasoning.vlm.output_parser import parse_decision_text


def _payload(**overrides) -> str:
    base = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": ["robot_1", "robot_2", "robot_3"],
        "root_cause": "standoff",
        "strategy": "yield",
        "justification": "j",
    }
    base.update(overrides)
    return json.dumps(base)


class TestRoleFieldValidation:
    def test_valid_roles_parse(self):
        decision = parse_decision_text(
            _payload(yield_robot="robot_1", crossing_order=["robot_2", "robot_3"])
        )
        assert decision.yield_robot == "robot_1"
        assert decision.crossing_order == ["robot_2", "robot_3"]

    def test_yield_robot_not_involved_rejected(self):
        with pytest.raises(VLMOutputParseError, match="yield_robot"):
            parse_decision_text(_payload(yield_robot="robot_9"))

    def test_crossing_order_without_yield_robot_rejected(self):
        with pytest.raises(VLMOutputParseError, match="crossing_order"):
            parse_decision_text(_payload(crossing_order=["robot_2", "robot_3"]))

    def test_crossing_order_missing_member_rejected(self):
        with pytest.raises(VLMOutputParseError, match="permutation"):
            parse_decision_text(
                _payload(yield_robot="robot_1", crossing_order=["robot_2"])
            )

    def test_crossing_order_duplicate_rejected(self):
        with pytest.raises(VLMOutputParseError, match="permutation"):
            parse_decision_text(
                _payload(yield_robot="robot_1", crossing_order=["robot_2", "robot_2"])
            )

    def test_crossing_order_containing_yielder_rejected(self):
        with pytest.raises(VLMOutputParseError, match="permutation"):
            parse_decision_text(
                _payload(yield_robot="robot_1", crossing_order=["robot_1", "robot_2"])
            )

    def test_no_congestion_with_role_fields_rejected(self):
        with pytest.raises(VLMOutputParseError, match="congestion_detected"):
            parse_decision_text(
                _payload(
                    congestion_detected=False,
                    type="none",
                    strategy="none",
                    involved_robots=[],
                    blocker_kind="object",
                )
            )

    def test_legacy_payload_without_role_fields_still_parses(self):
        decision = parse_decision_text(_payload())
        assert decision.yield_robot is None
        assert decision.crossing_order is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_vlm_output_parser.py -v -k RoleField`
Expected: FAIL — the rejection tests parse successfully instead of raising.

- [ ] **Step 3: Implement**

In `parse_decision_text` in `reasoning/vlm/output_parser.py`, extend the existing invariant block. Replace:

```python
    if not decision.congestion_detected:
        if decision.type != "none" or decision.strategy != "none" or decision.involved_robots:
            raise VLMOutputParseError(
                "congestion_detected=false requires type='none', strategy='none', "
                "involved_robots=[]."
            )
```

with:

```python
    if not decision.congestion_detected:
        if decision.type != "none" or decision.strategy != "none" or decision.involved_robots:
            raise VLMOutputParseError(
                "congestion_detected=false requires type='none', strategy='none', "
                "involved_robots=[]."
            )
        if (
            decision.blocker_kind is not None
            or decision.yield_robot is not None
            or decision.crossing_order is not None
        ):
            raise VLMOutputParseError(
                "congestion_detected=false forbids blocker_kind, yield_robot, "
                "and crossing_order."
            )
```

Then, after the whole `if not decision.congestion_detected: ... elif ...` block (immediately before `return decision`), add:

```python
    if decision.yield_robot is not None and decision.yield_robot not in decision.involved_robots:
        raise VLMOutputParseError(
            f"yield_robot {decision.yield_robot!r} is not in involved_robots."
        )
    if decision.crossing_order is not None:
        if decision.yield_robot is None:
            raise VLMOutputParseError("crossing_order requires yield_robot.")
        expected = [r for r in decision.involved_robots if r != decision.yield_robot]
        if (
            len(decision.crossing_order) != len(set(decision.crossing_order))
            or sorted(decision.crossing_order) != sorted(expected)
        ):
            raise VLMOutputParseError(
                "crossing_order must be a permutation of involved_robots minus "
                "yield_robot."
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_vlm_output_parser.py -v`
Expected: PASS (new and pre-existing tests).

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/vlm/output_parser.py tests/unit/test_vlm_output_parser.py
git commit -m "feat: validate yield_robot and crossing_order at parse time"
```

---

### Task 3: Stage-2 contract — retreat-choice schema, model, parser

**Files:**
- Create: `reasoning/schemas/retreat_choice.schema.json`
- Modify: `reasoning/vlm/models.py` (add `RetreatChoiceDecision`)
- Modify: `reasoning/vlm/output_parser.py` (factor `_extract_json_object`, add `parse_retreat_choice_text`)
- Create: `tests/unit/test_retreat_choice_parser.py`

**Interfaces:**
- Consumes: `VLMOutputParseError` from `reasoning.vlm.errors`.
- Produces: `RetreatChoiceDecision(retreat_choice: str, justification: str)` (single letter, uppercased by validator) and `parse_retreat_choice_text(text: str, valid_labels: set[str]) -> RetreatChoiceDecision`. Task 11's grounder accepts `RetreatChoiceDecision | None`; Phase 2's pipeline calls this parser on the stage-2 response.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_retreat_choice_parser.py`:

```python
import pytest

from reasoning.vlm.errors import VLMOutputParseError
from reasoning.vlm.output_parser import parse_retreat_choice_text


class TestParseRetreatChoiceText:
    def test_plain_json_parses(self):
        choice = parse_retreat_choice_text(
            '{"retreat_choice": "B", "justification": "clears the aisle"}',
            valid_labels={"A", "B"},
        )
        assert choice.retreat_choice == "B"
        assert choice.justification == "clears the aisle"

    def test_lowercase_label_normalized(self):
        choice = parse_retreat_choice_text(
            '{"retreat_choice": "a", "justification": "left is clear"}',
            valid_labels={"A", "B"},
        )
        assert choice.retreat_choice == "A"

    def test_think_block_and_fences_tolerated(self):
        text = (
            "<think>{not json} weighing A vs B</think>\n"
            '```json\n{"retreat_choice": "A", "justification": "j"}\n```'
        )
        choice = parse_retreat_choice_text(text, valid_labels={"A", "B"})
        assert choice.retreat_choice == "A"

    def test_label_outside_candidate_set_rejected(self):
        with pytest.raises(VLMOutputParseError, match="not among candidates"):
            parse_retreat_choice_text(
                '{"retreat_choice": "C", "justification": "j"}',
                valid_labels={"A", "B"},
            )

    def test_multicharacter_label_rejected(self):
        with pytest.raises(VLMOutputParseError):
            parse_retreat_choice_text(
                '{"retreat_choice": "AB", "justification": "j"}',
                valid_labels={"A", "B"},
            )

    def test_non_json_rejected(self):
        with pytest.raises(VLMOutputParseError):
            parse_retreat_choice_text("I choose candidate A", valid_labels={"A"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_retreat_choice_parser.py -v`
Expected: FAIL with `ImportError: cannot import name 'parse_retreat_choice_text'`.

- [ ] **Step 3: Implement**

Create `reasoning/schemas/retreat_choice.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RetreatChoice",
  "type": "object",
  "required": ["retreat_choice", "justification"],
  "properties": {
    "retreat_choice": { "type": "string", "pattern": "^[A-Da-d]$" },
    "justification": { "type": "string" }
  },
  "additionalProperties": false
}
```

In `reasoning/vlm/models.py`, add after `CongestionDecision`:

```python
class RetreatChoiceDecision(BaseModel):
    """Stage-2 VLM output: one set-of-mark candidate letter plus one clause."""

    model_config = ConfigDict(frozen=True)

    retreat_choice: str = Field(min_length=1, max_length=1)
    justification: str

    @field_validator("retreat_choice", mode="before")
    @classmethod
    def _uppercase_label(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value
```

In `reasoning/vlm/output_parser.py`, factor the JSON-extraction body of `parse_decision_text` into a module-level helper and reuse it. Add above `parse_decision_text`:

```python
def _extract_json_object(text: str) -> dict[str, Any]:
    """Extract one JSON object from raw VLM text (think blocks/fences tolerated)."""
    without_think = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    candidate = re.sub(
        r"^```(?:json)?\s*|\s*```$", "", without_think.strip(), flags=re.DOTALL
    )
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise VLMOutputParseError("VLM output contains no JSON object.") from None
        try:
            return json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise VLMOutputParseError(f"VLM output is not valid JSON: {exc}") from exc
```

Replace the corresponding lines at the top of `parse_decision_text` (from `without_think = ...` through the inner `parsed = json.loads(...)` fallback) with:

```python
    parsed = _extract_json_object(text)
```

Add at the end of the module (import `RetreatChoiceDecision` alongside `CongestionDecision`):

```python
def parse_retreat_choice_text(
    text: str, valid_labels: set[str]
) -> RetreatChoiceDecision:
    """Parse a stage-2 retreat-choice response and validate its label.

    Args:
        text: Raw assistant text from the stage-2 VLM call.
        valid_labels: Letters of the candidates actually rendered (e.g. {"A", "B"}).

    Returns:
        Validated choice with the label uppercased.

    Raises:
        VLMOutputParseError: On JSON failure, schema violation, or a label not
            among the rendered candidates. Callers fall back to the
            geometry-best candidate (containment: `retreat=default`).
    """
    parsed = _extract_json_object(text)
    try:
        choice = RetreatChoiceDecision(**parsed)
    except (TypeError, ValidationError) as exc:
        raise VLMOutputParseError(
            f"retreat choice failed schema validation: {exc}"
        ) from exc
    if choice.retreat_choice not in valid_labels:
        raise VLMOutputParseError(
            f"retreat_choice {choice.retreat_choice!r} not among candidates "
            f"{sorted(valid_labels)}."
        )
    return choice
```

Add `"parse_retreat_choice_text"` to the module's `__all__`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_retreat_choice_parser.py tests/unit/test_vlm_output_parser.py -v`
Expected: PASS — including all pre-existing parser tests (the factoring must not change behavior).

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/schemas/retreat_choice.schema.json reasoning/vlm/models.py reasoning/vlm/output_parser.py tests/unit/test_retreat_choice_parser.py
git commit -m "feat: add stage-2 retreat-choice schema, model, and parser"
```

---

### Task 4: Motion table — model and derivation

**Files:**
- Modify: `reasoning/vlm/models.py` (add `MotionTableEntry`, `MotionTable`)
- Create: `reasoning/vlm/motion_table.py`
- Create: `tests/unit/test_motion_table.py`

**Interfaces:**
- Consumes: `SnapshotFrame`, `RobotStateInput` (Task 1).
- Produces: `MotionTableEntry(robot_id: str, arrival_order: int | None, arrival_stamp: float | None, seconds_stopped: float, displacement_m: float, prior_yields: int)`; `MotionTable(window_sec: float, entries: list[MotionTableEntry])`; `derive_motion_table(frames: Sequence[SnapshotFrame], conflict_center: tuple[float, float], conflict_radius_m: float, prior_yields: Mapping[str, int] | None = None, stopped_speed_mps: float = 0.05) -> MotionTable`. Task 5 renders it; Task 13 reuses `arrival_stamp` for FCFS.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_motion_table.py`:

```python
import pytest

from reasoning.vlm.models import RobotStateInput, SnapshotFrame
from reasoning.vlm.motion_table import derive_motion_table


def _frame(stamp: float, *robots: tuple[str, float, float, float | None]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=stamp,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=0.0, linear_velocity=v)
            for rid, x, y, v in robots
        ],
    )


class TestDeriveMotionTable:
    def test_arrival_order_follows_zone_entry_sequence(self):
        frames = [
            _frame(0.0, ("robot_1", 0.2, 0.0, 0.3), ("robot_2", 5.0, 0.0, 0.3)),
            _frame(1.0, ("robot_1", 0.2, 0.0, 0.0), ("robot_2", 0.8, 0.0, 0.3)),
            _frame(2.0, ("robot_1", 0.2, 0.0, 0.0), ("robot_2", 0.5, 0.0, 0.0)),
        ]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=1.5)
        by_id = {e.robot_id: e for e in table.entries}
        assert by_id["robot_1"].arrival_order == 1
        assert by_id["robot_1"].arrival_stamp == 0.0
        assert by_id["robot_2"].arrival_order == 2
        assert by_id["robot_2"].arrival_stamp == 1.0

    def test_robot_never_in_zone_has_no_arrival(self):
        frames = [_frame(0.0, ("robot_1", 9.0, 9.0, 0.3))]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=1.5)
        assert table.entries[0].arrival_order is None
        assert table.entries[0].arrival_stamp is None

    def test_seconds_stopped_counts_trailing_stopped_interval_only(self):
        frames = [
            _frame(0.0, ("robot_1", 0.0, 0.0, 0.3)),
            _frame(2.0, ("robot_1", 0.6, 0.0, 0.3)),
            _frame(4.0, ("robot_1", 0.6, 0.0, 0.0)),
            _frame(6.0, ("robot_1", 0.6, 0.0, 0.0)),
        ]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=5.0)
        assert table.entries[0].seconds_stopped == pytest.approx(4.0)

    def test_stopped_falls_back_to_displacement_when_velocity_missing(self):
        frames = [
            _frame(0.0, ("robot_1", 0.0, 0.0, None)),
            _frame(2.0, ("robot_1", 0.01, 0.0, None)),
        ]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=5.0)
        assert table.entries[0].seconds_stopped == pytest.approx(2.0)

    def test_displacement_is_first_to_last_distance(self):
        frames = [
            _frame(0.0, ("robot_1", 0.0, 0.0, 0.3)),
            _frame(1.0, ("robot_1", 3.0, 4.0, 0.3)),
        ]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=1.0)
        assert table.entries[0].displacement_m == pytest.approx(5.0)

    def test_prior_yields_injected(self):
        frames = [_frame(0.0, ("robot_1", 0.0, 0.0, 0.0))]
        table = derive_motion_table(
            frames,
            conflict_center=(0.0, 0.0),
            conflict_radius_m=1.0,
            prior_yields={"robot_1": 2},
        )
        assert table.entries[0].prior_yields == 2

    def test_entries_sorted_by_robot_id_and_window_measured(self):
        frames = [
            _frame(3.0, ("robot_2", 0.0, 0.0, 0.0), ("robot_1", 1.0, 0.0, 0.0)),
            _frame(7.5, ("robot_2", 0.0, 0.0, 0.0), ("robot_1", 1.0, 0.0, 0.0)),
        ]
        table = derive_motion_table(frames, conflict_center=(0.0, 0.0), conflict_radius_m=1.0)
        assert [e.robot_id for e in table.entries] == ["robot_1", "robot_2"]
        assert table.window_sec == pytest.approx(4.5)

    def test_empty_frames_raise(self):
        with pytest.raises(ValueError):
            derive_motion_table([], conflict_center=(0.0, 0.0), conflict_radius_m=1.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_motion_table.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'reasoning.vlm.motion_table'`.

- [ ] **Step 3: Implement**

In `reasoning/vlm/models.py`, add after `SnapshotFrame`:

```python
class MotionTableEntry(BaseModel):
    """Per-robot motion summary derived from the snapshot ring buffer."""

    model_config = ConfigDict(frozen=True)

    robot_id: str = Field(min_length=1)
    arrival_order: int | None = None
    arrival_stamp: float | None = None
    seconds_stopped: float = Field(ge=0.0)
    displacement_m: float = Field(ge=0.0)
    prior_yields: int = Field(default=0, ge=0)


class MotionTable(BaseModel):
    """Derived temporal context for stage-1 prompts and the classical reasoner."""

    model_config = ConfigDict(frozen=True)

    window_sec: float = Field(ge=0.0)
    entries: list[MotionTableEntry]
```

Create `reasoning/vlm/motion_table.py`:

```python
import math
from collections.abc import Mapping, Sequence

from reasoning.vlm.models import (
    MotionTable,
    MotionTableEntry,
    RobotStateInput,
    SnapshotFrame,
)


def derive_motion_table(
    frames: Sequence[SnapshotFrame],
    conflict_center: tuple[float, float],
    conflict_radius_m: float,
    prior_yields: Mapping[str, int] | None = None,
    stopped_speed_mps: float = 0.05,
) -> MotionTable:
    """Summarize buffered snapshots into per-robot motion evidence.

    Args:
        frames: Snapshot history, any order; sorted by stamp internally.
        conflict_center: World-frame center of the conflict zone `(x, y)`.
        conflict_radius_m: Zone radius; entry inside it defines "arrival".
        prior_yields: Yield counts this episode, keyed by robot_id.
        stopped_speed_mps: Speed below which a robot counts as stopped.

    Returns:
        Table with one entry per robot present in the latest frame, sorted
        by robot_id.

    Raises:
        ValueError: If `frames` is empty.
    """
    if not frames:
        raise ValueError("derive_motion_table requires at least one frame")
    ordered = sorted(frames, key=lambda f: f.stamp)
    window_sec = ordered[-1].stamp - ordered[0].stamp
    yields = dict(prior_yields or {})

    entries: list[MotionTableEntry] = []
    for robot_id in sorted(s.robot_id for s in ordered[-1].robots):
        history = [
            (frame.stamp, state)
            for frame in ordered
            if (state := frame.find_robot(robot_id)) is not None
        ]
        arrival_stamp = _arrival_stamp(history, conflict_center, conflict_radius_m)
        entries.append(
            MotionTableEntry(
                robot_id=robot_id,
                arrival_stamp=arrival_stamp,
                seconds_stopped=_trailing_stopped_sec(history, stopped_speed_mps),
                displacement_m=math.hypot(
                    history[-1][1].x - history[0][1].x,
                    history[-1][1].y - history[0][1].y,
                ),
                prior_yields=yields.get(robot_id, 0),
            )
        )

    arrivals = sorted(
        (e.arrival_stamp, e.robot_id) for e in entries if e.arrival_stamp is not None
    )
    order_by_id = {robot_id: i + 1 for i, (_, robot_id) in enumerate(arrivals)}
    entries = [
        entry.model_copy(update={"arrival_order": order_by_id.get(entry.robot_id)})
        for entry in entries
    ]
    return MotionTable(window_sec=window_sec, entries=entries)


def _arrival_stamp(
    history: list[tuple[float, RobotStateInput]],
    center: tuple[float, float],
    radius_m: float,
) -> float | None:
    for stamp, state in history:
        if math.hypot(state.x - center[0], state.y - center[1]) <= radius_m:
            return stamp
    return None


def _trailing_stopped_sec(
    history: list[tuple[float, RobotStateInput]], stopped_speed_mps: float
) -> float:
    total = 0.0
    for (t0, s0), (t1, s1) in zip(reversed(history[:-1]), reversed(history[1:])):
        dt = t1 - t0
        if dt <= 0:
            continue
        if s1.linear_velocity is not None:
            stopped = abs(s1.linear_velocity) < stopped_speed_mps
        else:
            step = math.hypot(s1.x - s0.x, s1.y - s0.y)
            stopped = step / dt < stopped_speed_mps
        if not stopped:
            break
        total += dt
    return total
```

Note: `model_copy(update=...)` is the Pydantic v2 way to "modify" a frozen model — it returns a new instance.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_motion_table.py -v`
Expected: PASS (all 8).

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/vlm/models.py reasoning/vlm/motion_table.py tests/unit/test_motion_table.py
git commit -m "feat: derive per-robot motion table from snapshot history"
```

---

### Task 5: Prompt blocks — failure context, motion table, annotation scheme, role-field instructions

**Files:**
- Modify: `reasoning/vlm/models.py` (add `FailureContext`; extend `ReasonerRequest`)
- Modify: `reasoning/vlm/prompt_builder.py`
- Modify: `tests/unit/test_prompt_builder.py`

**Interfaces:**
- Consumes: `MotionTable` (Task 4), role fields (Task 1).
- Produces: `FailureContext(strategy: str, yield_robot: str | None, crossing_order: list[str] | None, outcome_status: str, failure_detail: str)`; `ReasonerRequest` gains `motion_table: MotionTable | None = None` and `failure_context: FailureContext | None = None`; prompt builder exposes `ANNOTATION_SCHEME_SENTENCE: str`, `render_motion_table_block(table: MotionTable) -> str`, `render_failure_context_block(context: FailureContext) -> str`. Task 6 adds the modality switch on top of this sectioned assembly.

**Note on existing tests:** this task rebuilds the user prompt from ordered sections. All original content (task framing, state block, known IDs, guidance, JSON format, think format) is preserved verbatim for a default request, but if any existing `test_prompt_builder.py` assertion pins the exact full template string, update that assertion minimally to the new assembled text. Substring assertions must pass untouched.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_prompt_builder.py`:

```python
from reasoning.vlm.models import (
    FailureContext,
    MotionTable,
    MotionTableEntry,
    ReasonerRequest,
    RobotStateInput,
)
from reasoning.vlm.prompt_builder import (
    ANNOTATION_SCHEME_SENTENCE,
    build_prompt_payload,
    render_failure_context_block,
    render_motion_table_block,
)


def _request(**overrides) -> ReasonerRequest:
    base = {
        "request_id": "req-1",
        "image_path": "/tmp/frame.png",
        "frame_id": "cam",
        "stamp": 1.0,
        "robot_states": [
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
            RobotStateInput(robot_id="robot_2", x=0.4, y=0.0, theta=3.14),
        ],
    }
    base.update(overrides)
    return ReasonerRequest(**base)


def _motion_table() -> MotionTable:
    return MotionTable(
        window_sec=8.0,
        entries=[
            MotionTableEntry(
                robot_id="robot_1",
                arrival_order=1,
                arrival_stamp=0.0,
                seconds_stopped=12.4,
                displacement_m=0.05,
                prior_yields=0,
            ),
            MotionTableEntry(
                robot_id="robot_2",
                arrival_order=None,
                arrival_stamp=None,
                seconds_stopped=0.0,
                displacement_m=1.5,
                prior_yields=1,
            ),
        ],
    )


class TestPromptBlocks:
    def test_motion_table_block_renders_all_columns(self):
        block = render_motion_table_block(_motion_table())
        assert "Motion summary over the last 8 s" in block
        assert "robot_id=robot_1, arrival_order=1, seconds_stopped=12.4" in block
        assert "displacement_m=0.05, prior_yields=0" in block
        assert "arrival_order=-" in block  # robot_2 never entered the zone

    def test_failure_context_block_renders_outcome(self):
        block = render_failure_context_block(
            FailureContext(
                strategy="yield",
                yield_robot="robot_1",
                crossing_order=["robot_2"],
                outcome_status="FAILED",
                failure_detail="wait expired unresolved",
            )
        )
        assert "Previous attempt this episode" in block
        assert "strategy=yield" in block
        assert 'crossing_order=["robot_2"]' in block
        assert "detail=wait expired unresolved" in block

    def test_default_request_has_no_optional_blocks(self):
        payload = build_prompt_payload(_request())
        assert "Motion summary" not in payload.user_prompt
        assert "Previous attempt" not in payload.user_prompt
        assert ANNOTATION_SCHEME_SENTENCE in payload.user_prompt

    def test_blocks_included_when_fields_present(self):
        payload = build_prompt_payload(
            _request(
                motion_table=_motion_table(),
                failure_context=FailureContext(
                    strategy="temporary_wait",
                    yield_robot=None,
                    crossing_order=None,
                    outcome_status="FAILED",
                    failure_detail="wait expired unresolved",
                ),
            )
        )
        assert "Motion summary" in payload.user_prompt
        assert "Previous attempt" in payload.user_prompt

    def test_role_field_instructions_present(self):
        payload = build_prompt_payload(_request())
        assert '"blocker_kind"' in payload.user_prompt
        assert '"yield_robot"' in payload.user_prompt
        assert '"crossing_order"' in payload.user_prompt
        assert "blocker_kind=\"object\" allows only" in payload.user_prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_prompt_builder.py -v -k "Blocks or role_field"`
Expected: FAIL with `ImportError: cannot import name 'FailureContext'`.

- [ ] **Step 3: Implement models**

In `reasoning/vlm/models.py`, add after `MotionTable`:

```python
class FailureContext(BaseModel):
    """Prior-attempt summary injected into re-analysis prompts (Reflexion-lite)."""

    model_config = ConfigDict(frozen=True)

    strategy: str = Field(min_length=1)
    yield_robot: str | None = None
    crossing_order: list[str] | None = None
    outcome_status: str = Field(min_length=1)
    failure_detail: str = Field(min_length=1)
```

In `ReasonerRequest`, add after `robot_states`:

```python
    motion_table: MotionTable | None = None
    failure_context: FailureContext | None = None
```

- [ ] **Step 4: Implement the sectioned prompt builder**

Replace `reasoning/vlm/prompt_builder.py`'s template and `build_prompt_payload` with the sectioned version below. Keep `SYSTEM_PROMPT`, its Cosmos comment, and `format_robot_state_lines` exactly as they are.

```python
ANNOTATION_SCHEME_SENTENCE = (
    "Annotation scheme: box color = robot identity, box style = motion status, "
    "fading polyline trails = the last ~8 s of motion, G<n> labels = robot "
    "goals, circled letters (A/B/C/D) = retreat candidates when present."
)

_TASK_FRAMING = """You are a warehouse swarm robotics traffic controller. Analyze the \
overhead camera view together with the robot states below and detect congestion \
patterns such as deadlocks, bottlenecks, crowding, or anomalies."""

_STATE_GUIDANCE = """Guidance:
- Robots are roughly 0.3 m wide; treat any two robots within ~0.5 m of each \
other as physically conflicting.
- theta is heading in radians: 0=east(+x), π/2=north(+y), π or -π=west(-x), \
-π/2=south(-y). Two robots with |theta_1 - theta_2| close to π are facing \
each other head-on.
- deadlock: two or more robots each blocked by the other. The most common case \
is a head-on standoff — two robots facing opposite directions (theta values \
differing by ~π) in the same narrow aisle, both STOPPED or STALE, unable to \
pass. This IS a deadlock even with only two robots. \
bottleneck: several robots queued waiting behind one slow robot or blocked passage \
(one-way congestion, not opposing). crowding: many robots packed into a small \
area. anomaly: unexpected or unsafe configuration.
- For head-on deadlock (two stopped/stale robots with opposing headings and/or \
opposing goal directions): classify as type="deadlock" and strategy="yield" \
(first listed robot backs up) or strategy="reverse" (both back up to clear).
- For a simple bottleneck (robots queued in the same direction): classify as \
type="bottleneck" and strategy="temporary_wait" or "yield".
- Decide from the robot coordinates and the image, not from assumptions about intent."""

_OUTPUT_FORMAT = """Produce a JSON object with exactly these fields:
- "congestion_detected": true or false
- "type": "none" | "deadlock" | "bottleneck" | "crowding" | "anomaly"
- "involved_robots": list of robot_id strings, from the known IDs only
- "root_cause": one sentence
- "strategy": "none" | "yield" | "reroute" | "convoy" | "priority_override" | \
"temporary_wait" | "reverse"
- "justification": one or two sentences
- "blocker_kind": "robot" | "object" | "transient" — what is physically \
blocking, judged from visible evidence (omit or null when nothing is blocked)
- "yield_robot": when strategy="yield", the robot_id that retreats; must be \
one of involved_robots (otherwise omit or null)
- "crossing_order": when strategy="yield", the remaining involved robots in \
the order they should pass, first passer first (otherwise omit or null)

Rules:
- Only use robot IDs from the known list above.
- When congestion_detected is false: set type="none", strategy="none", involved_robots=[].
- When congestion_detected is true: type and strategy must not be "none", and \
involved_robots must be non-empty.
- blocker_kind="object" allows only strategy "reroute" or "temporary_wait" \
(bounded probe); blocker_kind="transient" allows only "temporary_wait" or \
"reroute"; blocker_kind="robot" allows any strategy.
- crossing_order must list every involved robot except yield_robot, exactly once.

Answer using the following format:
<think>
Compute the pairwise distance between robots, check theta values for opposing \
headings (head-on deadlock), inspect goal positions for opposing directions, \
identify any conflicts, and decide the congestion type and strategy.
</think>
Immediately after the </think> tag, write ONLY the final JSON object, with no \
surrounding text or markdown."""


def render_motion_table_block(table: MotionTable) -> str:
    """Render the derived motion table as deterministic prompt lines.

    Args:
        table: Motion summary derived from the snapshot ring buffer.

    Returns:
        Multi-line block; arrival_order "-" marks robots that never entered
        the conflict zone.
    """
    lines = [
        f"Motion summary over the last {table.window_sec:.0f} s "
        "(arrival_order '-' = never entered the conflict zone):"
    ]
    for entry in table.entries:
        arrival = entry.arrival_order if entry.arrival_order is not None else "-"
        lines.append(
            f"- robot_id={entry.robot_id}, arrival_order={arrival}, "
            f"seconds_stopped={entry.seconds_stopped:.1f}, "
            f"displacement_m={entry.displacement_m:.2f}, "
            f"prior_yields={entry.prior_yields}"
        )
    return "\n".join(lines)


def render_failure_context_block(context: FailureContext) -> str:
    """Render the prior-attempt block for re-analysis prompts.

    Args:
        context: Outcome of the previous resolution attempt this episode.

    Returns:
        Two-line block stating what was tried and how it ended.
    """
    order = json.dumps(context.crossing_order) if context.crossing_order is not None else "[]"
    return (
        "Previous attempt this episode (outcome known — do not repeat it blindly):\n"
        f"- strategy={context.strategy}, yield_robot={context.yield_robot or '-'}, "
        f"crossing_order={order}, outcome={context.outcome_status}, "
        f"detail={context.failure_detail}"
    )


def build_prompt_payload(request: ReasonerRequest) -> PromptPayload:
    """Build a deterministic, fully-rendered prompt payload from a request.

    Args:
        request: Validated reasoning request from M5/M1.

    Returns:
        Frozen `PromptPayload` with fixed system prompt and dynamic user prompt.
    """
    sorted_states = sorted(request.robot_states, key=lambda s: s.robot_id)
    known_ids = [s.robot_id for s in sorted_states]
    lines = format_robot_state_lines(sorted_states)
    block = "\n".join(f"- {line}" for line in lines) or "- no robots observed"

    sections = [
        _TASK_FRAMING,
        f"Robot states (sorted by ID):\n{block}",
        f"Known robot IDs: {json.dumps(known_ids)}",
        ANNOTATION_SCHEME_SENTENCE,
    ]
    if request.motion_table is not None:
        sections.append(render_motion_table_block(request.motion_table))
    if request.failure_context is not None:
        sections.append(render_failure_context_block(request.failure_context))
    sections.append(_STATE_GUIDANCE)
    sections.append(_OUTPUT_FORMAT)

    return PromptPayload(
        system_prompt=SYSTEM_PROMPT,
        user_prompt="\n\n".join(sections),
        image_path=request.image_path,
        known_robot_ids=known_ids,
    )
```

Update the module's imports to include the new models:

```python
from reasoning.vlm.models import (
    FailureContext,
    MotionTable,
    PromptPayload,
    ReasonerRequest,
    RobotStateInput,
)
```

Delete the old `_USER_TEMPLATE` constant (its content now lives in `_TASK_FRAMING`, `_STATE_GUIDANCE`, and `_OUTPUT_FORMAT`).

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_prompt_builder.py -v`
Expected: PASS. If a pre-existing assertion pinned the exact full template, update only that expected string (allowed exception in Global Constraints).

- [ ] **Step 6: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/vlm/models.py reasoning/vlm/prompt_builder.py tests/unit/test_prompt_builder.py
git commit -m "feat: add motion, failure, and role-field prompt blocks"
```

---

### Task 6: Modality conditions — dual / text_only / image_only assembly

**Files:**
- Modify: `reasoning/vlm/models.py` (`ReasonerRequest.modality`, `PromptPayload.image_path: str | None`)
- Modify: `reasoning/vlm/prompt_builder.py`
- Modify: `tests/unit/test_prompt_builder.py`

**Interfaces:**
- Consumes: `ModalityCondition` (Task 1), sectioned builder (Task 5).
- Produces: `ReasonerRequest.modality: ModalityCondition = "dual"`; `build_prompt_payload` emits `image_path=None` for `text_only` and omits state/motion/failure text for `image_only`, per the rev-8 modality-condition input table. Task 7 makes backends tolerate `image_path=None`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_prompt_builder.py` (reuses `_request`, `_motion_table` from Task 5):

```python
class TestModalityConditions:
    def test_dual_is_default_with_image_and_state(self):
        payload = build_prompt_payload(_request())
        assert payload.image_path == "/tmp/frame.png"
        assert "Robot states (sorted by ID):" in payload.user_prompt
        assert ANNOTATION_SCHEME_SENTENCE in payload.user_prompt

    def test_text_only_drops_image_and_annotation_sentence(self):
        payload = build_prompt_payload(
            _request(modality="text_only", motion_table=_motion_table())
        )
        assert payload.image_path is None
        assert ANNOTATION_SCHEME_SENTENCE not in payload.user_prompt
        assert "overhead camera view" not in payload.user_prompt
        assert "Robot states (sorted by ID):" in payload.user_prompt
        assert "Motion summary" in payload.user_prompt

    def test_image_only_drops_state_motion_and_failure_blocks(self):
        payload = build_prompt_payload(
            _request(
                modality="image_only",
                motion_table=_motion_table(),
                failure_context=FailureContext(
                    strategy="yield",
                    yield_robot="robot_1",
                    crossing_order=["robot_2"],
                    outcome_status="FAILED",
                    failure_detail="wait expired unresolved",
                ),
            )
        )
        assert payload.image_path == "/tmp/frame.png"
        assert "Robot states (sorted by ID):" not in payload.user_prompt
        assert "Motion summary" not in payload.user_prompt
        assert "Previous attempt" not in payload.user_prompt
        assert ANNOTATION_SCHEME_SENTENCE in payload.user_prompt
        # Known robot IDs stay in every modality (needed for involved_robots).
        assert '"robot_1"' in payload.user_prompt
        assert '"robot_2"' in payload.user_prompt

    def test_image_only_keeps_known_ids_and_output_format(self):
        payload = build_prompt_payload(_request(modality="image_only"))
        assert "Known robot IDs:" in payload.user_prompt
        assert '"congestion_detected"' in payload.user_prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_prompt_builder.py -v -k Modality`
Expected: FAIL — `ReasonerRequest` has no `modality` field (ValidationError) and `PromptPayload.image_path` rejects None.

- [ ] **Step 3: Implement**

In `reasoning/vlm/models.py`:

- `ReasonerRequest`: add after `failure_context`:

```python
    modality: ModalityCondition = "dual"
```

- `PromptPayload`: change `image_path: str` to:

```python
    image_path: str | None
```

In `reasoning/vlm/prompt_builder.py`, add framings and image-only guidance next to `_TASK_FRAMING` (rename usage as shown below; `_TASK_FRAMING` keeps its dual text):

```python
_TASK_FRAMING_TEXT_ONLY = """You are a warehouse swarm robotics traffic controller. Analyze the \
robot states below and detect congestion patterns such as deadlocks, \
bottlenecks, crowding, or anomalies."""

_TASK_FRAMING_IMAGE_ONLY = """You are a warehouse swarm robotics traffic controller. Analyze the \
overhead camera view and detect congestion patterns such as deadlocks, \
bottlenecks, crowding, or anomalies."""

_FRAMING_BY_MODALITY = {
    "dual": _TASK_FRAMING,
    "text_only": _TASK_FRAMING_TEXT_ONLY,
    "image_only": _TASK_FRAMING_IMAGE_ONLY,
}

_IMAGE_GUIDANCE = """Guidance:
- Robots are roughly 0.3 m wide; treat any two robots that appear within \
about 1.5 robot-widths of each other as physically conflicting.
- deadlock: two or more robots each blocked by the other, e.g. a head-on \
standoff in a narrow aisle — this IS a deadlock even with only two robots. \
bottleneck: several robots queued behind one slow robot or blocked passage \
(one-way congestion, not opposing). crowding: many robots packed into a small \
area. anomaly: unexpected or unsafe configuration.
- For a head-on deadlock choose strategy="yield" or strategy="reverse"; for a \
simple same-direction queue choose "temporary_wait" or "yield".
- Decide from the image evidence (positions, trails, goal labels), not from \
assumptions about intent."""
```

Replace `build_prompt_payload` (from Task 5) with the modality-aware version:

```python
def build_prompt_payload(request: ReasonerRequest) -> PromptPayload:
    """Build a deterministic, fully-rendered prompt payload from a request.

    Args:
        request: Validated reasoning request from M5/M1. `request.modality`
            selects which input channels the prompt carries (rev-8 modality
            table): text_only drops the image and annotation sentence;
            image_only drops the state, motion, and failure blocks.

    Returns:
        Frozen `PromptPayload`; `image_path` is None under text_only.
    """
    sorted_states = sorted(request.robot_states, key=lambda s: s.robot_id)
    known_ids = [s.robot_id for s in sorted_states]
    include_text_state = request.modality != "image_only"
    include_image = request.modality != "text_only"

    sections = [_FRAMING_BY_MODALITY[request.modality]]
    if include_text_state:
        lines = format_robot_state_lines(sorted_states)
        block = "\n".join(f"- {line}" for line in lines) or "- no robots observed"
        sections.append(f"Robot states (sorted by ID):\n{block}")
    sections.append(f"Known robot IDs: {json.dumps(known_ids)}")
    if include_image:
        sections.append(ANNOTATION_SCHEME_SENTENCE)
    if include_text_state and request.motion_table is not None:
        sections.append(render_motion_table_block(request.motion_table))
    if include_text_state and request.failure_context is not None:
        sections.append(render_failure_context_block(request.failure_context))
    sections.append(_STATE_GUIDANCE if include_text_state else _IMAGE_GUIDANCE)
    sections.append(_OUTPUT_FORMAT)

    return PromptPayload(
        system_prompt=SYSTEM_PROMPT,
        user_prompt="\n\n".join(sections),
        image_path=request.image_path if include_image else None,
        known_robot_ids=known_ids,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_prompt_builder.py -v`
Expected: PASS (Task 5 tests included — dual behavior unchanged).

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/vlm/models.py reasoning/vlm/prompt_builder.py tests/unit/test_prompt_builder.py
git commit -m "feat: add dual/text-only/image-only modality conditions"
```

---

### Task 7: Backends tolerate `image_path=None`

**Files:**
- Modify: `reasoning/vlm/openai_backend.py:86-95` (`_build_messages`)
- Modify: `reasoning/vlm/anthropic_backend.py:84-97` (`_build_messages`)
- Modify: `reasoning/vlm/llama_server_backend.py:93-108` (`_build_messages`)
- Modify: `tests/unit/test_openai_backend.py`, `tests/unit/test_anthropic_backend.py`
- Create if missing: `tests/unit/test_llama_server_backend.py`

**Interfaces:**
- Consumes: `PromptPayload.image_path: str | None` (Task 6).
- Produces: each backend's `_build_messages(payload)` emits a text-only user message when `image_path is None`; behavior with a path is unchanged. `MockBackend` ignores images already — no change.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_openai_backend.py`:

```python
from reasoning.vlm.models import PromptPayload
from reasoning.vlm.openai_backend import OpenAIBackend


def _text_payload() -> PromptPayload:
    return PromptPayload(
        system_prompt="sys",
        user_prompt="usr",
        image_path=None,
        known_robot_ids=["robot_1"],
    )


def test_openai_build_messages_omits_image_when_path_none():
    messages = OpenAIBackend()._build_messages(_text_payload())
    assert messages[0] == {"role": "system", "content": "sys"}
    assert messages[1] == {"role": "user", "content": "usr"}
```

Append to `tests/unit/test_anthropic_backend.py`:

```python
from reasoning.vlm.models import PromptPayload
from reasoning.vlm.anthropic_backend import AnthropicBackend


def test_anthropic_build_messages_omits_image_when_path_none():
    payload = PromptPayload(
        system_prompt="sys",
        user_prompt="usr",
        image_path=None,
        known_robot_ids=["robot_1"],
    )
    messages = AnthropicBackend()._build_messages(payload)
    assert messages == [
        {"role": "user", "content": [{"type": "text", "text": "usr"}]}
    ]
```

Create (or append to) `tests/unit/test_llama_server_backend.py`:

```python
from reasoning.vlm.llama_server_backend import LlamaServerBackend
from reasoning.vlm.models import PromptPayload


def test_llama_build_messages_text_only_when_image_path_none():
    backend = LlamaServerBackend(mmproj_path="mmproj.gguf")
    payload = PromptPayload(
        system_prompt="sys",
        user_prompt="usr",
        image_path=None,
        known_robot_ids=["robot_1"],
    )
    messages = backend._build_messages(payload)
    assert messages[1] == {"role": "user", "content": "usr"}


def test_llama_build_messages_includes_image_when_path_set(tmp_path):
    image = tmp_path / "frame.png"
    image.write_bytes(b"fake-png-bytes")
    backend = LlamaServerBackend(mmproj_path="mmproj.gguf")
    payload = PromptPayload(
        system_prompt="sys",
        user_prompt="usr",
        image_path=str(image),
        known_robot_ids=["robot_1"],
    )
    messages = backend._build_messages(payload)
    content = messages[1]["content"]
    assert content[0]["type"] == "image_url"
    assert content[1] == {"type": "text", "text": "usr"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_openai_backend.py tests/unit/test_anthropic_backend.py tests/unit/test_llama_server_backend.py -v -k "image_path_none or text_only"`
Expected: FAIL with `TypeError` from `Path(None)` inside `_encode_image`.

- [ ] **Step 3: Implement**

`reasoning/vlm/openai_backend.py` — replace `_build_messages`:

```python
    def _build_messages(self, payload: PromptPayload) -> list[dict]:
        user_content: str | list[dict]
        if payload.image_path is None:
            user_content = payload.user_prompt
        else:
            data_url = self._encode_image(payload.image_path)
            user_content = [
                {"type": "text", "text": payload.user_prompt},
                {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
            ]
        return [
            {"role": "system", "content": payload.system_prompt},
            {"role": "user", "content": user_content},
        ]
```

`reasoning/vlm/anthropic_backend.py` — replace `_build_messages`:

```python
    def _build_messages(self, payload: PromptPayload) -> list[dict]:
        user_content: list[dict] = []
        if payload.image_path is not None:
            media_type, image_data = self._encode_image(payload.image_path)
            user_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                }
            )
        user_content.append({"type": "text", "text": payload.user_prompt})
        return [{"role": "user", "content": user_content}]
```

`reasoning/vlm/llama_server_backend.py` — in `_build_messages`, change the condition line:

```python
        if self.mmproj_path is not None and payload.image_path is not None:
```

(the media-first comment and both branches stay as they are).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_openai_backend.py tests/unit/test_anthropic_backend.py tests/unit/test_llama_server_backend.py -v`
Expected: PASS, including all pre-existing backend tests (with-image behavior unchanged).

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/vlm/openai_backend.py reasoning/vlm/anthropic_backend.py reasoning/vlm/llama_server_backend.py tests/unit/test_openai_backend.py tests/unit/test_anthropic_backend.py tests/unit/test_llama_server_backend.py
git commit -m "feat: skip image content when payload has no image path"
```

---

### Task 8: Pillar 1 — `GroundingParams` and derived maneuver distances

**Files:**
- Create: `reasoning/rag/maneuver_geometry.py`
- Create: `tests/unit/test_maneuver_geometry.py`

**Interfaces:**
- Consumes: `SnapshotFrame` (Task 1).
- Produces (Tasks 9, 11, 14 import all of these from `reasoning.rag.maneuver_geometry`):
  - `GroundingParams` (fields listed in the implementation below; `mode: Literal["legacy", "derived"] = "legacy"`).
  - `Derivation(feasible: bool, value_m: float | None, reason: str | None)`.
  - `project_progress(start: tuple[float, float], current: tuple[float, float], axis_theta: float) -> float`.
  - `derive_backup_distance(frame: SnapshotFrame, yielder_id: str, other_ids: Sequence[str], params: GroundingParams) -> Derivation`.
  - `derive_escort_distance(frame: SnapshotFrame, passer_id: str, yielder_parked_xy: tuple[float, float], params: GroundingParams) -> Derivation`.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_maneuver_geometry.py`:

```python
import math

import pytest

from reasoning.rag.maneuver_geometry import (
    Derivation,
    GroundingParams,
    derive_backup_distance,
    derive_escort_distance,
    project_progress,
)
from reasoning.vlm.models import RobotStateInput, SnapshotFrame


def _frame(*robots: tuple[str, float, float, float]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=theta)
            for rid, x, y, theta in robots
        ],
    )


class TestProjectProgress:
    def test_progress_along_x_axis(self):
        assert project_progress((0.0, 0.0), (2.5, 1.0), 0.0) == pytest.approx(2.5)

    def test_progress_along_y_axis(self):
        assert project_progress((0.0, 0.0), (1.0, 3.0), math.pi / 2) == pytest.approx(3.0)

    def test_backward_motion_is_negative(self):
        assert project_progress((0.0, 0.0), (-1.0, 0.0), 0.0) == pytest.approx(-1.0)


class TestDeriveBackupDistance:
    def test_reproduces_verified_head_on_tuning(self):
        # robot_1 faces east at origin, robot_2 stands 0.4 m ahead:
        # required d = backup_clearance 1.7 - 0.4 = 1.3 (the verified constant).
        frame = _frame(("robot_1", 0.0, 0.0, 0.0), ("robot_2", 0.4, 0.0, math.pi))
        result = derive_backup_distance(frame, "robot_1", ["robot_2"], GroundingParams())
        assert result.feasible
        assert result.value_m == pytest.approx(1.3, abs=0.02)

    def test_robot_behind_yielder_makes_backup_infeasible(self):
        # The yielder faces east, so the retreat axis points west; robot_3 at
        # x=-0.5 sits 0.5 m into the retreat path. Its clearance constraint
        # |0.5 - d| >= 1.7 allows only d >= 2.2, above the 2.0 band max.
        frame = _frame(
            ("robot_1", 0.0, 0.0, 0.0),
            ("robot_2", 0.4, 0.0, math.pi),
            ("robot_3", -0.5, 0.0, 0.0),
        )
        result = derive_backup_distance(
            frame, "robot_1", ["robot_2", "robot_3"], GroundingParams()
        )
        assert not result.feasible
        assert "band" in result.reason

    def test_missing_yielder_is_infeasible_with_reason(self):
        frame = _frame(("robot_2", 0.4, 0.0, math.pi))
        result = derive_backup_distance(frame, "robot_1", ["robot_2"], GroundingParams())
        assert not result.feasible
        assert "robot_1" in result.reason

    def test_missing_other_robot_is_infeasible_with_reason(self):
        frame = _frame(("robot_1", 0.0, 0.0, 0.0))
        result = derive_backup_distance(frame, "robot_1", ["robot_9"], GroundingParams())
        assert not result.feasible
        assert "robot_9" in result.reason


class TestDeriveEscortDistance:
    def test_reproduces_verified_head_on_tuning(self):
        # Passer at x=0.25 facing west; yielder parked at x=-1.65:
        # along-axis distance 1.9 + escort_clearance 0.5 = 2.4 (verified).
        frame = _frame(("robot_2", 0.25, 0.0, math.pi))
        result = derive_escort_distance(
            frame, "robot_2", (-1.65, 0.0), GroundingParams()
        )
        assert result.feasible
        assert result.value_m == pytest.approx(2.4, abs=0.01)

    def test_out_of_band_escort_is_infeasible(self):
        frame = _frame(("robot_2", 0.25, 0.0, math.pi))
        result = derive_escort_distance(
            frame, "robot_2", (-3.5, 0.0), GroundingParams()
        )
        assert not result.feasible
        assert "band" in result.reason

    def test_missing_passer_is_infeasible(self):
        frame = _frame(("robot_1", 0.0, 0.0, 0.0))
        result = derive_escort_distance(frame, "robot_9", (0.0, 0.0), GroundingParams())
        assert not result.feasible
        assert "robot_9" in result.reason
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_maneuver_geometry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'reasoning.rag.maneuver_geometry'`.

- [ ] **Step 3: Implement**

Create `reasoning/rag/maneuver_geometry.py`:

```python
import math
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from reasoning.vlm.models import SnapshotFrame

_SCAN_STEP_M = 0.01


class GroundingParams(BaseModel):
    """Tunable geometry parameters for derived-mode grounding (rev-8 A.2/A.3).

    `backup_clearance_m` and `escort_clearance_m` are the composed
    pass-clearance values (the spec's `2*min_distance_m + margin` form);
    defaults reproduce the verified head-on tuning: 1.3 m backup from a
    0.4 m standoff, 2.4 m escort from a 1.9 m park distance.
    """

    model_config = ConfigDict(frozen=True)

    mode: Literal["legacy", "derived"] = "legacy"
    min_distance_m: float = Field(default=0.45, gt=0)
    backup_clearance_m: float = Field(default=1.7, gt=0)
    escort_clearance_m: float = Field(default=0.5, gt=0)
    backup_band_m: tuple[float, float] = (0.5, 2.0)
    escort_band_m: tuple[float, float] = (1.0, 3.5)
    lateral_m: float = Field(default=0.35, gt=0)
    sweep_step_m: float = Field(default=0.1, gt=0)
    aisle_y_band_m: tuple[float, float] | None = None
    hold_backstop_sec: float = Field(default=45.0, gt=0)
    wait_backstop_sec: float = Field(default=120.0, gt=0)
    resolution_backstop_sec: float = Field(default=150.0, gt=0)


class Derivation(BaseModel):
    """Outcome of one geometric derivation: a value or an infeasibility reason."""

    model_config = ConfigDict(frozen=True)

    feasible: bool
    value_m: float | None = None
    reason: str | None = None


def project_progress(
    start: tuple[float, float], current: tuple[float, float], axis_theta: float
) -> float:
    """Signed displacement projected onto a transit axis (rev-8 A.2).

    Args:
        start: World position when the maneuver began, `(x, y)`.
        current: Current world position, `(x, y)`.
        axis_theta: Transit-axis heading in radians (world frame).

    Returns:
        Progress in meters; lateral drift contributes nothing and backward
        motion is negative.
    """
    return (current[0] - start[0]) * math.cos(axis_theta) + (
        current[1] - start[1]
    ) * math.sin(axis_theta)


def derive_backup_distance(
    frame: SnapshotFrame,
    yielder_id: str,
    other_ids: Sequence[str],
    params: GroundingParams,
) -> Derivation:
    """Minimum in-band retreat distance clearing every crossing robot.

    Scans the feasibility band in 0.01 m steps for the smallest retreat `d`
    such that the axis-projected separation to every robot in `other_ids`
    is at least `params.backup_clearance_m`. Out-of-band requirements are
    infeasible, never clamped (rev-8 A.2).

    Args:
        frame: Current scene snapshot.
        yielder_id: Robot that retreats.
        other_ids: Robots in the crossing order (all must be present).
        params: Geometry parameters.

    Returns:
        Feasible derivation with `value_m`, or infeasible with `reason`.
    """
    yielder = frame.find_robot(yielder_id)
    if yielder is None:
        return Derivation(feasible=False, reason=f"yielder {yielder_id} not in snapshot")
    axis = (-math.cos(yielder.theta), -math.sin(yielder.theta))
    offsets: list[float] = []
    for robot_id in other_ids:
        state = frame.find_robot(robot_id)
        if state is None:
            return Derivation(feasible=False, reason=f"robot {robot_id} not in snapshot")
        offsets.append(
            (state.x - yielder.x) * axis[0] + (state.y - yielder.y) * axis[1]
        )

    low, high = params.backup_band_m
    d = low
    while d <= high + 1e-9:
        if all(abs(s - d) >= params.backup_clearance_m for s in offsets):
            return Derivation(feasible=True, value_m=round(d, 3))
        d += _SCAN_STEP_M
    return Derivation(
        feasible=False,
        reason=(
            f"no backup distance in band [{low}, {high}] m satisfies "
            f"clearance {params.backup_clearance_m} m"
        ),
    )


def derive_escort_distance(
    frame: SnapshotFrame,
    passer_id: str,
    yielder_parked_xy: tuple[float, float],
    params: GroundingParams,
) -> Derivation:
    """Escort distance placing the passer past the parked yielder (rev-8 A.2).

    Signed distance along the passer's own heading from its current position
    to the yielder's parked position, plus `params.escort_clearance_m`.
    Out-of-band requirements are infeasible, never truncated.

    Args:
        frame: Current scene snapshot.
        passer_id: Robot escorted through the conflict.
        yielder_parked_xy: World position the yielder retreats to.
        params: Geometry parameters.

    Returns:
        Feasible derivation with `value_m`, or infeasible with `reason`.
    """
    passer = frame.find_robot(passer_id)
    if passer is None:
        return Derivation(feasible=False, reason=f"passer {passer_id} not in snapshot")
    along = project_progress(
        (passer.x, passer.y), yielder_parked_xy, passer.theta
    )
    required = along + params.escort_clearance_m
    low, high = params.escort_band_m
    if required < low or required > high:
        return Derivation(
            feasible=False,
            reason=(
                f"required escort {required:.2f} m outside band [{low}, {high}] m"
            ),
        )
    return Derivation(feasible=True, value_m=round(required, 3))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_maneuver_geometry.py -v`
Expected: PASS (all).

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/rag/maneuver_geometry.py tests/unit/test_maneuver_geometry.py
git commit -m "feat: derive backup and escort distances with feasibility bands"
```

---

### Task 9: Pillar 2 — retreat candidates: generation, swept validation, ranking

**Files:**
- Create: `reasoning/rag/retreat_candidates.py`
- Create: `tests/unit/test_retreat_candidates.py`

**Interfaces:**
- Consumes: `SnapshotFrame` (Task 1), `GroundingParams` (Task 8).
- Produces (Task 11 imports these from `reasoning.rag.retreat_candidates`):
  - `RetreatCandidate(label: str, x: float, y: float, backup_m: float, lateral_m: float, min_sweep_clearance_m: float, lateral_clearance_m: float)`.
  - `generate_retreat_candidates(frame: SnapshotFrame, yielder_id: str, backup_m: float, params: GroundingParams) -> list[RetreatCandidate]` — survivors of swept-path validation, labeled `A..D` in generation order (left, right, far-left, far-right).
  - `rank_candidates(candidates: list[RetreatCandidate], transit_axis_theta: float, yielder_xy: tuple[float, float]) -> list[RetreatCandidate]` — deterministic; `ranked[0]` is the geometry-max default (= Arm B's stage-2 answer).

**Ranking metric note:** the backup segment is shared by all candidates, so its clearance cannot discriminate between them (in a head-on standoff it is always the standoff distance). Validation covers the full sweep; ranking uses `lateral_clearance_m` (min clearance over the sidestep segment only), tie-broken by distance from the transit corridor (farther = better), then label.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_retreat_candidates.py`:

```python
import math

import pytest

from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.rag.retreat_candidates import (
    generate_retreat_candidates,
    rank_candidates,
)
from reasoning.vlm.models import RobotStateInput, SnapshotFrame


def _frame(*robots: tuple[str, float, float, float]) -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id=rid, x=x, y=y, theta=theta)
            for rid, x, y, theta in robots
        ],
    )


_HEAD_ON = _frame(("robot_1", 0.0, 0.0, 0.0), ("robot_2", 0.4, 0.0, math.pi))


class TestGenerateRetreatCandidates:
    def test_open_floor_yields_four_labeled_candidates(self):
        candidates = generate_retreat_candidates(
            _HEAD_ON, "robot_1", 1.3, GroundingParams()
        )
        assert [c.label for c in candidates] == ["A", "B", "C", "D"]
        assert [round(c.lateral_m, 2) for c in candidates] == [0.35, -0.35, 0.7, -0.7]
        # yielder faces east, so retreat is west and "left" is +y
        assert candidates[0].x == pytest.approx(-1.3)
        assert candidates[0].y == pytest.approx(0.35)

    def test_aisle_band_discards_far_candidates(self):
        params = GroundingParams(aisle_y_band_m=(-0.6, 0.6))
        candidates = generate_retreat_candidates(_HEAD_ON, "robot_1", 1.3, params)
        assert [round(c.lateral_m, 2) for c in candidates] == [0.35, -0.35]
        assert [c.label for c in candidates] == ["A", "B"]

    def test_robot_on_sidestep_segment_discards_candidate(self):
        # robot_3 sits exactly where the left sidestep ends; the left and
        # far-left sweeps both pass within min_distance of it.
        frame = _frame(
            ("robot_1", 0.0, 0.0, 0.0),
            ("robot_2", 0.4, 0.0, math.pi),
            ("robot_3", -1.3, 0.35, 0.0),
        )
        candidates = generate_retreat_candidates(frame, "robot_1", 1.3, GroundingParams())
        assert [round(c.lateral_m, 2) for c in candidates] == [-0.35, -0.7]
        assert [c.label for c in candidates] == ["A", "B"]

    def test_preexisting_standoff_separation_does_not_veto_retreat(self):
        # robot_2 is 0.4 m away (< min_distance 0.45) before the maneuver even
        # starts; retreating away from it must still validate.
        candidates = generate_retreat_candidates(
            _HEAD_ON, "robot_1", 1.3, GroundingParams()
        )
        assert candidates, "deadlock standoff must not veto its own resolution"

    def test_unknown_yielder_returns_empty(self):
        assert generate_retreat_candidates(_HEAD_ON, "robot_9", 1.3, GroundingParams()) == []


class TestRankCandidates:
    def test_side_away_from_third_robot_ranks_first(self):
        # robot_3 north of the parked zone: right-side (negative lateral)
        # candidates have larger sidestep clearance and must rank first.
        frame = _frame(
            ("robot_1", 0.0, 0.0, 0.0),
            ("robot_2", 0.4, 0.0, math.pi),
            ("robot_3", -1.3, 1.0, 0.0),
        )
        params = GroundingParams(aisle_y_band_m=(-0.6, 0.6))
        candidates = generate_retreat_candidates(frame, "robot_1", 1.3, params)
        ranked = rank_candidates(candidates, 0.0, (0.0, 0.0))
        assert ranked[0].lateral_m == pytest.approx(-0.35)

    def test_symmetric_scene_breaks_tie_by_label(self):
        params = GroundingParams(aisle_y_band_m=(-0.6, 0.6))
        candidates = generate_retreat_candidates(_HEAD_ON, "robot_1", 1.3, params)
        ranked = rank_candidates(candidates, 0.0, (0.0, 0.0))
        assert [c.label for c in ranked] == ["A", "B"]

    def test_ranking_is_deterministic(self):
        params = GroundingParams()
        candidates = generate_retreat_candidates(_HEAD_ON, "robot_1", 1.3, params)
        first = rank_candidates(candidates, 0.0, (0.0, 0.0))
        second = rank_candidates(list(reversed(candidates)), 0.0, (0.0, 0.0))
        assert [c.label for c in first] == [c.label for c in second]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_retreat_candidates.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'reasoning.rag.retreat_candidates'`.

- [ ] **Step 3: Implement**

Create `reasoning/rag/retreat_candidates.py`:

```python
import math

from pydantic import BaseModel, ConfigDict, Field

from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.vlm.models import RobotStateInput, SnapshotFrame

_LABELS = ("A", "B", "C", "D")


class RetreatCandidate(BaseModel):
    """One validated retreat pose offered to the stage-2 set-of-mark call."""

    model_config = ConfigDict(frozen=True)

    label: str = Field(min_length=1, max_length=1)
    x: float
    y: float
    backup_m: float
    lateral_m: float
    min_sweep_clearance_m: float
    lateral_clearance_m: float


def generate_retreat_candidates(
    frame: SnapshotFrame,
    yielder_id: str,
    backup_m: float,
    params: GroundingParams,
) -> list[RetreatCandidate]:
    """Generate swept-path-validated retreat candidates for the yielder.

    Candidates are left/right/far-left/far-right sidesteps at the derived
    backup distance. The backup and sidestep segments are sampled at
    `params.sweep_step_m`; every sample must clear every other robot and
    stay inside the aisle band when one is configured (rev-8 A.3).

    The per-robot clearance floor is `min(params.min_distance_m, starting
    separation)`: a deadlock's pre-existing sub-threshold separation must
    not veto the retreat that resolves it — the sweep must simply never
    make any separation worse than that floor.

    Args:
        frame: Current scene snapshot.
        yielder_id: Robot that retreats.
        backup_m: Derived backup distance (Pillar 1).
        params: Geometry parameters.

    Returns:
        Surviving candidates labeled A.. in generation order; empty when
        the yielder is unknown or nothing validates.
    """
    yielder = frame.find_robot(yielder_id)
    if yielder is None:
        return []
    others = [s for s in frame.robots if s.robot_id != yielder_id]
    retreat = (-math.cos(yielder.theta), -math.sin(yielder.theta))
    left = (
        math.cos(yielder.theta + math.pi / 2),
        math.sin(yielder.theta + math.pi / 2),
    )
    start = (yielder.x, yielder.y)
    parked = (start[0] + backup_m * retreat[0], start[1] + backup_m * retreat[1])

    survivors: list[RetreatCandidate] = []
    for lateral in (
        params.lateral_m,
        -params.lateral_m,
        2 * params.lateral_m,
        -2 * params.lateral_m,
    ):
        end = (parked[0] + lateral * left[0], parked[1] + lateral * left[1])
        backup_samples = _sample_segment(start, parked, params.sweep_step_m)
        lateral_samples = _sample_segment(parked, end, params.sweep_step_m)
        samples = backup_samples + lateral_samples
        if params.aisle_y_band_m is not None:
            low, high = params.aisle_y_band_m
            if any(not (low <= sy <= high) for _, sy in samples):
                continue
        if not _sweep_clears(samples, others, params.min_distance_m):
            continue
        survivors.append(
            RetreatCandidate(
                label=_LABELS[len(survivors)],
                x=end[0],
                y=end[1],
                backup_m=backup_m,
                lateral_m=lateral,
                min_sweep_clearance_m=round(_min_clearance(samples, others), 3),
                lateral_clearance_m=round(_min_clearance(lateral_samples, others), 3),
            )
        )
    return survivors


def rank_candidates(
    candidates: list[RetreatCandidate],
    transit_axis_theta: float,
    yielder_xy: tuple[float, float],
) -> list[RetreatCandidate]:
    """Deterministic geometry ranking; `ranked[0]` is the default candidate.

    Sort by sidestep clearance (descending), then distance from the transit
    corridor (descending — farther off the corridor is better), then label.

    Args:
        candidates: Validated candidates from `generate_retreat_candidates`.
        transit_axis_theta: Heading of the conflict's transit axis.
        yielder_xy: Yielder position defining the corridor line.

    Returns:
        New list, best candidate first.
    """

    def corridor_distance(candidate: RetreatCandidate) -> float:
        dx = candidate.x - yielder_xy[0]
        dy = candidate.y - yielder_xy[1]
        return abs(-math.sin(transit_axis_theta) * dx + math.cos(transit_axis_theta) * dy)

    return sorted(
        candidates,
        key=lambda c: (-c.lateral_clearance_m, -corridor_distance(c), c.label),
    )


def _sample_segment(
    p0: tuple[float, float], p1: tuple[float, float], step_m: float
) -> list[tuple[float, float]]:
    length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    count = max(1, math.ceil(length / step_m))
    return [
        (p0[0] + (p1[0] - p0[0]) * i / count, p0[1] + (p1[1] - p0[1]) * i / count)
        for i in range(count + 1)
    ]


def _sweep_clears(
    samples: list[tuple[float, float]],
    others: list[RobotStateInput],
    min_distance_m: float,
) -> bool:
    if not others:
        return True
    start = samples[0]
    for other in others:
        floor = min(
            min_distance_m, math.hypot(other.x - start[0], other.y - start[1])
        )
        for sx, sy in samples:
            if math.hypot(other.x - sx, other.y - sy) < floor - 1e-9:
                return False
    return True


def _min_clearance(
    samples: list[tuple[float, float]], others: list[RobotStateInput]
) -> float:
    if not others:
        return math.inf
    return min(
        math.hypot(other.x - sx, other.y - sy)
        for sx, sy in samples
        for other in others
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_retreat_candidates.py -v`
Expected: PASS (all).

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/rag/retreat_candidates.py tests/unit/test_retreat_candidates.py
git commit -m "feat: generate, sweep-validate, and rank retreat candidates"
```

---

### Task 10: Pillar 4 — blocker-kind strategy compatibility

**Files:**
- Create: `reasoning/rag/strategy_compatibility.py`
- Create: `tests/unit/test_strategy_compatibility.py`

**Interfaces:**
- Consumes: nothing beyond stdlib.
- Produces (Task 11 imports from `reasoning.rag.strategy_compatibility`):
  - `COMPATIBLE_STRATEGIES: dict[str, frozenset[str]]`.
  - `enforce_strategy_compatibility(strategy: str, blocker_kind: str | None) -> tuple[str, str | None]` returning `(effective_strategy, degradation_tag_or_None)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_strategy_compatibility.py`:

```python
from reasoning.rag.strategy_compatibility import (
    COMPATIBLE_STRATEGIES,
    enforce_strategy_compatibility,
)


class TestEnforceStrategyCompatibility:
    def test_in_set_strategy_passes_through_untagged(self):
        assert enforce_strategy_compatibility("reroute", "object") == ("reroute", None)

    def test_object_incompatible_defaults_to_reroute(self):
        assert enforce_strategy_compatibility("yield", "object") == (
            "reroute",
            "strategy=incompatible-defaulted",
        )

    def test_transient_incompatible_defaults_to_temporary_wait(self):
        assert enforce_strategy_compatibility("yield", "transient") == (
            "temporary_wait",
            "strategy=incompatible-defaulted",
        )

    def test_robot_kind_allows_full_strategy_set(self):
        for strategy in ("yield", "reverse", "temporary_wait", "reroute", "convoy", "priority_override"):
            assert enforce_strategy_compatibility(strategy, "robot") == (strategy, None)

    def test_unclassified_blocker_is_unconstrained_but_tagged(self):
        assert enforce_strategy_compatibility("yield", None) == (
            "yield",
            "blocker=unclassified",
        )

    def test_matrix_matches_rev8_appendix_a5(self):
        assert COMPATIBLE_STRATEGIES["object"] == frozenset({"reroute", "temporary_wait"})
        assert COMPATIBLE_STRATEGIES["transient"] == frozenset({"temporary_wait", "reroute"})
        assert "yield" in COMPATIBLE_STRATEGIES["robot"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_strategy_compatibility.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `reasoning/rag/strategy_compatibility.py`:

```python
COMPATIBLE_STRATEGIES: dict[str, frozenset[str]] = {
    "robot": frozenset(
        {"yield", "reverse", "temporary_wait", "reroute", "convoy", "priority_override"}
    ),
    "object": frozenset({"reroute", "temporary_wait"}),
    "transient": frozenset({"temporary_wait", "reroute"}),
}

_KIND_DEFAULTS: dict[str, str] = {
    "object": "reroute",
    "transient": "temporary_wait",
}


def enforce_strategy_compatibility(
    strategy: str, blocker_kind: str | None
) -> tuple[str, str | None]:
    """Constrain the strategy to the blocker-kind compatible set (rev-8 A.5).

    Args:
        strategy: Strategy chosen by the reasoner (never "none" at grounding).
        blocker_kind: Declared blocker kind, or None when unclassified.

    Returns:
        `(effective_strategy, degradation_tag)`. In-set choices pass through
        untagged; out-of-set choices are replaced by the per-kind default and
        tagged `strategy=incompatible-defaulted`; an absent blocker_kind
        leaves the strategy unconstrained, tagged `blocker=unclassified`.
    """
    if blocker_kind is None:
        return strategy, "blocker=unclassified"
    if strategy in COMPATIBLE_STRATEGIES[blocker_kind]:
        return strategy, None
    return _KIND_DEFAULTS.get(blocker_kind, strategy), "strategy=incompatible-defaulted"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_strategy_compatibility.py -v`
Expected: PASS.

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/rag/strategy_compatibility.py tests/unit/test_strategy_compatibility.py
git commit -m "feat: enforce blocker-kind strategy compatibility matrix"
```

---

### Task 11: Grounder derived mode — snapshot, candidates, ordering, degradations

**Files:**
- Modify: `reasoning/rag/command_grounder.py`
- Modify: `reasoning/schemas/coordination_command.schema.json`
- Modify: `tests/unit/test_command_grounder.py`

**Interfaces:**
- Consumes: `SnapshotFrame`, `RetreatChoiceDecision` (Tasks 1, 3); `GroundingParams`, `derive_backup_distance`, `derive_escort_distance` (Task 8); `generate_retreat_candidates`, `rank_candidates`, `RetreatCandidate` (Task 9); `enforce_strategy_compatibility` (Task 10).
- Produces:
  - `ground_reasoner_result(result: ReasonerResult, *, snapshot: SnapshotFrame | None = None, params: GroundingParams | None = None, retreat_choice: RetreatChoiceDecision | None = None) -> dict[str, Any]` — `params=None` or `mode="legacy"` is byte-identical to today; `mode="derived"` implements rev-8 Appendix A.
  - `RetreatSelection(backup: Derivation, candidates: list[RetreatCandidate])` and `prepare_retreat_selection(frame: SnapshotFrame, yielder_id: str, crossing_ids: Sequence[str], params: GroundingParams) -> RetreatSelection` — Phase 2's pipeline calls this to render stage-2 markers, then passes the parsed choice back via `retreat_choice`.
  - Derived commands carry a `degradations: list[str]` key (schema-extended, optional).

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_command_grounder.py`:

```python
import math

from reasoning.rag.command_grounder import (
    ground_reasoner_result,
    prepare_retreat_selection,
)
from reasoning.rag.maneuver_geometry import GroundingParams
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerDiagnostics,
    ReasonerResult,
    RetreatChoiceDecision,
    RobotStateInput,
    SnapshotFrame,
)


def _decision(**overrides) -> CongestionDecision:
    base = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": ["robot_1", "robot_2"],
        "root_cause": "head-on standoff",
        "strategy": "yield",
        "justification": "j",
        "blocker_kind": "robot",
        "yield_robot": "robot_1",
        "crossing_order": ["robot_2"],
    }
    base.update(overrides)
    return CongestionDecision(**base)


def _result(decision: CongestionDecision) -> ReasonerResult:
    return ReasonerResult(
        request_id="req-1",
        decision=decision,
        raw_text=None,
        diagnostics=ReasonerDiagnostics(
            request_id="req-1", backend_id="mock", attempts=1, parse_status="valid"
        ),
    )


def _head_on_frame() -> SnapshotFrame:
    return SnapshotFrame(
        stamp=1.0,
        robots=[
            RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
            RobotStateInput(robot_id="robot_2", x=0.4, y=0.0, theta=math.pi),
        ],
    )


_DERIVED = GroundingParams(mode="derived", aisle_y_band_m=(-0.6, 0.6))


class TestLegacyModeUnchanged:
    def test_no_arguments_means_legacy_without_degradations(self):
        command = ground_reasoner_result(_result(_decision()))
        assert "degradations" not in command
        yield_params = command["actions"][0]["parameters"]
        assert yield_params["backup_distance_m"] == 1.3


class TestDerivedYield:
    def test_derived_distances_and_ordering_fields(self):
        command = ground_reasoner_result(
            _result(_decision()), snapshot=_head_on_frame(), params=_DERIVED
        )
        yield_action = command["actions"][0]
        assert yield_action["robot_id"] == "robot_1"
        p = yield_action["parameters"]
        assert p["backup_distance_m"] == 1.3
        # Escort here is 2.2, not the verified scenario's 2.4: this synthetic
        # yielder starts at x=0 (not -0.35), so the chosen candidate parks at
        # x=-1.3 and the passer's along-axis distance is 1.7 + clearance 0.5.
        assert p["passer_escort_distance_m"] == 2.2
        assert p["passer_clear_m"] == 2.2
        assert p["crossing_order"] == ["robot_2"]
        assert p["retreat_choice"] == "A"
        assert "retreat=default" in command["degradations"]
        waits = [a for a in command["actions"] if a["action"] == "temporary_wait"]
        assert waits[0]["robot_id"] == "robot_2"
        assert waits[0]["parameters"]["linked_position"] == 0

    def test_retreat_choice_applied_without_default_tag(self):
        command = ground_reasoner_result(
            _result(_decision()),
            snapshot=_head_on_frame(),
            params=_DERIVED,
            retreat_choice=RetreatChoiceDecision(retreat_choice="B", justification="j"),
        )
        p = command["actions"][0]["parameters"]
        assert p["retreat_choice"] == "B"
        assert p["pull_off_lateral_m"] == -0.35
        assert "retreat=default" not in command["degradations"]

    def test_unrendered_retreat_label_falls_back_to_default(self):
        command = ground_reasoner_result(
            _result(_decision()),
            snapshot=_head_on_frame(),
            params=_DERIVED,
            retreat_choice=RetreatChoiceDecision(retreat_choice="D", justification="j"),
        )
        assert command["actions"][0]["parameters"]["retreat_choice"] == "A"
        assert "retreat=default" in command["degradations"]

    def test_missing_role_fields_use_legacy_convention_tagged(self):
        command = ground_reasoner_result(
            _result(_decision(yield_robot=None, crossing_order=None)),
            snapshot=_head_on_frame(),
            params=_DERIVED,
        )
        assert command["actions"][0]["robot_id"] == "robot_1"
        assert "roles=legacy-convention" in command["degradations"]


class TestDerivedDegradations:
    def test_no_snapshot_degrades_to_nonspatial_wait(self):
        command = ground_reasoner_result(
            _result(_decision()), snapshot=None, params=_DERIVED
        )
        assert all(a["action"] == "temporary_wait" for a in command["actions"])
        assert "distances=unavailable" in command["degradations"]

    def test_incompatible_strategy_defaulted_by_blocker_kind(self):
        command = ground_reasoner_result(
            _result(_decision(blocker_kind="object")),
            snapshot=_head_on_frame(),
            params=_DERIVED,
        )
        assert command["command_id"] == "req-1-reroute"
        assert command["actions"][0]["action"] == "reroute"
        assert "strategy=incompatible-defaulted" in command["degradations"]

    def test_infeasible_backup_returns_reroute_outcome(self):
        # A third robot 0.5 m behind the yielder blocks the retreat band.
        frame = SnapshotFrame(
            stamp=1.0,
            robots=[
                RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0),
                RobotStateInput(robot_id="robot_2", x=0.4, y=0.0, theta=math.pi),
                RobotStateInput(robot_id="robot_3", x=-0.5, y=0.0, theta=0.0),
            ],
        )
        command = ground_reasoner_result(
            _result(
                _decision(
                    involved_robots=["robot_1", "robot_2", "robot_3"],
                    crossing_order=["robot_2", "robot_3"],
                )
            ),
            snapshot=frame,
            params=_DERIVED,
        )
        assert command["actions"][0]["action"] == "reroute"
        assert any(d.startswith("yield=infeasible") for d in command["degradations"])


class TestPrepareRetreatSelection:
    def test_selection_exposes_ranked_candidates(self):
        selection = prepare_retreat_selection(
            _head_on_frame(), "robot_1", ["robot_2"], _DERIVED
        )
        assert selection.backup.feasible
        assert [c.label for c in selection.candidates] == ["A", "B"]

    def test_infeasible_backup_yields_empty_candidates(self):
        frame = SnapshotFrame(
            stamp=1.0,
            robots=[RobotStateInput(robot_id="robot_1", x=0.0, y=0.0, theta=0.0)],
        )
        selection = prepare_retreat_selection(frame, "robot_1", ["robot_9"], _DERIVED)
        assert not selection.backup.feasible
        assert selection.candidates == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_command_grounder.py -v -k "Derived or Legacy or Selection"`
Expected: FAIL with `ImportError: cannot import name 'prepare_retreat_selection'`.

- [ ] **Step 3: Implement**

In `reasoning/schemas/coordination_command.schema.json`, add to the top-level `"properties"` (leave `"required"` and both `"additionalProperties": false` unchanged):

```json
    "degradations": {
      "type": "array",
      "items": { "type": "string" }
    }
```

In `reasoning/rag/command_grounder.py`:

1. Extend the imports:

```python
from collections.abc import Sequence
from typing import Any

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict

from reasoning.rag.maneuver_geometry import (
    Derivation,
    GroundingParams,
    derive_backup_distance,
    derive_escort_distance,
)
from reasoning.rag.retreat_candidates import (
    RetreatCandidate,
    generate_retreat_candidates,
    rank_candidates,
)
from reasoning.rag.strategy_compatibility import enforce_strategy_compatibility
from reasoning.schemas import load_schema
from reasoning.vlm.models import (
    CongestionDecision,
    ReasonerResult,
    RetreatChoiceDecision,
    SnapshotFrame,
)
```

2. Rename the current `ground_reasoner_result` body: everything from `robot_ids = decision.involved_robots` down to the final `return validate_coordination_command(...)` moves verbatim (including every tuning comment) into:

```python
def _ground_legacy(decision: CongestionDecision, request_id: str) -> dict[str, Any]:
    """Scenario-tuned legacy bridge (pre-rev-8 behavior), byte-identical."""
    robot_ids = decision.involved_robots
    command_id = f"{request_id}-{decision.strategy}"
    # ... existing body unchanged ...
```

3. Add the new public API:

```python
class RetreatSelection(BaseModel):
    """Stage-2 inputs: the derived backup and the ranked candidate set."""

    model_config = ConfigDict(frozen=True)

    backup: Derivation
    candidates: list[RetreatCandidate]


def prepare_retreat_selection(
    frame: SnapshotFrame,
    yielder_id: str,
    crossing_ids: Sequence[str],
    params: GroundingParams,
) -> RetreatSelection:
    """Derive the backup distance and the ranked retreat candidates.

    Args:
        frame: Current scene snapshot.
        yielder_id: Robot that retreats.
        crossing_ids: Robots that will cross, in passing order.
        params: Geometry parameters.

    Returns:
        Selection with `candidates` ranked best-first; empty candidates when
        the backup is infeasible or nothing survives the sweep.
    """
    backup = derive_backup_distance(frame, yielder_id, list(crossing_ids), params)
    if not backup.feasible:
        return RetreatSelection(backup=backup, candidates=[])
    yielder = frame.find_robot(yielder_id)
    candidates = generate_retreat_candidates(frame, yielder_id, backup.value_m, params)
    ranked = rank_candidates(candidates, yielder.theta, (yielder.x, yielder.y))
    return RetreatSelection(backup=backup, candidates=ranked)


def ground_reasoner_result(
    result: ReasonerResult,
    *,
    snapshot: SnapshotFrame | None = None,
    params: GroundingParams | None = None,
    retreat_choice: RetreatChoiceDecision | None = None,
) -> dict[str, Any]:
    """Convert a validated decision into an executable coordination command.

    With `params=None` or `params.mode == "legacy"` this is the pre-rev-8
    scenario-tuned bridge, byte-identical to the previous behavior. With
    `params.mode == "derived"` it implements rev-8 Appendix A: compatibility
    enforcement, derived distances with feasibility bands, ranked retreat
    candidates, explicit crossing order, and `degradations` markers instead
    of blind constants.

    Args:
        result: Reasoner output (Arm A or Arm B — both emit CongestionDecision).
        snapshot: Current scene frame; None in derived mode degrades to a
            non-spatial wait (`distances=unavailable`).
        params: Geometry parameters and mode switch.
        retreat_choice: Parsed stage-2 choice; None or an unrendered label
            falls back to the geometry-best candidate (`retreat=default`).

    Returns:
        Schema-valid coordination command dict.

    Raises:
        CommandGroundingError: On empty/non-congestion decisions or an
            unsupported strategy.
    """
    decision = result.decision
    if decision is None or not decision.congestion_detected:
        raise CommandGroundingError("cannot ground an empty or non-congestion decision")
    if params is None or params.mode == "legacy":
        return _ground_legacy(decision, result.request_id)
    return _ground_derived(decision, result.request_id, snapshot, params, retreat_choice)


def _with_degradations(command: dict[str, Any], degradations: list[str]) -> dict[str, Any]:
    return validate_coordination_command({**command, "degradations": degradations})


def _ground_derived(
    decision: CongestionDecision,
    request_id: str,
    snapshot: SnapshotFrame | None,
    params: GroundingParams,
    retreat_choice: RetreatChoiceDecision | None,
) -> dict[str, Any]:
    degradations: list[str] = []
    strategy, tag = enforce_strategy_compatibility(decision.strategy, decision.blocker_kind)
    if tag is not None:
        degradations.append(tag)

    # Non-spatial degrade: nothing about a maneuver can be verified without
    # a snapshot, so no executable spatial constants are ever emitted.
    if snapshot is None:
        degradations.append("distances=unavailable")
        fallback = decision.model_copy(update={"strategy": "temporary_wait"})
        return _with_degradations(_ground_legacy(fallback, request_id), degradations)

    if strategy != "yield":
        effective = decision.model_copy(update={"strategy": strategy})
        return _with_degradations(_ground_legacy(effective, request_id), degradations)

    yielder = decision.yield_robot
    if yielder is None:
        yielder = decision.involved_robots[0]
        degradations.append("roles=legacy-convention")
    order = list(
        decision.crossing_order
        or [r for r in decision.involved_robots if r != yielder]
    )
    if not order:
        degradations.append("yield=no-passer")
        fallback = decision.model_copy(update={"strategy": "temporary_wait"})
        return _with_degradations(_ground_legacy(fallback, request_id), degradations)

    selection = prepare_retreat_selection(snapshot, yielder, order, params)
    if not selection.backup.feasible or not selection.candidates:
        reason = (
            f"yield=infeasible:{selection.backup.reason}"
            if not selection.backup.feasible
            else "retreat=no-valid-candidate"
        )
        degradations.append(reason)
        reroute = decision.model_copy(update={"strategy": "reroute"})
        return _with_degradations(_ground_legacy(reroute, request_id), degradations)

    chosen = selection.candidates[0]
    if retreat_choice is None:
        degradations.append("retreat=default")
    else:
        match = next(
            (c for c in selection.candidates if c.label == retreat_choice.retreat_choice),
            None,
        )
        if match is None:
            degradations.append("retreat=default")
        else:
            chosen = match

    escort = derive_escort_distance(snapshot, order[0], (chosen.x, chosen.y), params)
    if not escort.feasible:
        degradations.append(f"yield=infeasible:{escort.reason}")
        reroute = decision.model_copy(update={"strategy": "reroute"})
        return _with_degradations(_ground_legacy(reroute, request_id), degradations)

    actions: list[dict[str, Any]] = [
        {
            "robot_id": yielder,
            "action": "yield",
            "parameters": {
                "backup_distance_m": chosen.backup_m,
                "hold_sec": params.hold_backstop_sec,
                "pull_off_lateral_m": chosen.lateral_m,
                "retreat_choice": chosen.label,
                "reason": decision.root_cause,
                "passer_robot_id": order[0],
                "passer_clear_m": escort.value_m,
                "passer_escort_distance_m": escort.value_m,
                "crossing_order": order,
            },
        }
    ]
    for position, robot_id in enumerate(order):
        actions.append(
            {
                "robot_id": robot_id,
                "action": "temporary_wait",
                "parameters": {
                    "duration_sec": params.wait_backstop_sec,
                    "linked_position": position,
                },
            }
        )
    return validate_coordination_command(
        {
            "command_id": f"{request_id}-yield",
            "actions": actions,
            "expected_resolution_time_sec": params.resolution_backstop_sec,
            "fallback": "stop",
            "degradations": degradations,
        }
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_command_grounder.py tests/unit/test_schemas.py -v`
Expected: PASS — every pre-existing grounder test untouched and green (legacy byte-identical), all new derived tests green.

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/rag/command_grounder.py reasoning/schemas/coordination_command.schema.json tests/unit/test_command_grounder.py
git commit -m "feat: derived-mode grounding with candidates and degradations"
```

---

### Task 12: Arm B — geometry classifier

**Files:**
- Create: `reasoning/baselines/__init__.py` (empty for now; populated in Task 14)
- Create: `reasoning/baselines/classical_reasoner.py`
- Create: `tests/unit/test_classical_reasoner.py`

**Interfaces:**
- Consumes: `SnapshotFrame`, `RobotStateInput`, `BlockerKind` (Task 1).
- Produces (Task 13 extends this module; Task 14 exports it):
  - `ConflictZone(zone_id: str, x: float, y: float, radius_m: float)`.
  - `ClassicalParams` (defaults from the rev-8 Arm B section: `r_conflict_m=1.5`, `r_block_m=1.0`, `heading_opposition_min_deg=150.0`, `axis_cross_min_deg=45.0`, `axis_cross_max_deg=135.0`, `arrival_tie_sec=1.0`, `stopped_speed_mps=0.05`, `goal_beyond_max_deg=60.0`).
  - `ClassicalClassification(scenario, congestion_type, blocker_kind, involved_robots)`.
  - `classify_scene(frames: Sequence[SnapshotFrame], zones: Sequence[ConflictZone], params: ClassicalParams) -> ClassicalClassification`.

**Rule order (rev-8 Arm B, evaluated on the latest frame):** `head_on` → `intersection` → `blocked_path` → `unknown`; `none` when no robot is stopped. The classifier sees **no image**: `blocked_path` always classifies `blocker_kind="object"` — the forced non-divergence T3a measures. Type mapping: `head_on→deadlock`, `intersection→bottleneck`, `blocked_path→anomaly`, `unknown→anomaly`.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_classical_reasoner.py`:

```python
import math

from reasoning.baselines.classical_reasoner import (
    ClassicalParams,
    ConflictZone,
    classify_scene,
)
from reasoning.vlm.models import RobotStateInput, SnapshotFrame


def _robot(
    rid: str,
    x: float,
    y: float,
    theta: float,
    v: float = 0.0,
    goal: tuple[float, float] | None = None,
) -> RobotStateInput:
    return RobotStateInput(
        robot_id=rid, x=x, y=y, theta=theta, linear_velocity=v, goal=goal
    )


def _frame(stamp: float, *robots: RobotStateInput) -> SnapshotFrame:
    return SnapshotFrame(stamp=stamp, robots=list(robots))


_PARAMS = ClassicalParams()
_ZONE = ConflictZone(zone_id="crossing", x=0.0, y=0.0, radius_m=1.5)


class TestClassifyScene:
    def test_head_on_standoff_classified_deadlock_robot(self):
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
            _robot("robot_2", 0.4, 0.0, math.pi, goal=(-5.0, 0.0)),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert c.scenario == "head_on"
        assert c.congestion_type == "deadlock"
        assert c.blocker_kind == "robot"
        assert sorted(c.involved_robots) == ["robot_1", "robot_2"]

    def test_crossing_axes_at_zone_classified_intersection(self):
        frame = _frame(
            1.0,
            _robot("robot_1", -0.8, 0.0, 0.0, goal=(5.0, 0.0)),
            _robot("robot_2", 0.0, -0.8, math.pi / 2, goal=(0.0, 5.0)),
        )
        c = classify_scene([frame], [_ZONE], _PARAMS)
        assert c.scenario == "intersection"
        assert c.congestion_type == "bottleneck"
        assert c.blocker_kind == "robot"

    def test_lone_stopped_robot_with_clear_front_is_blocked_path_object(self):
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
            _robot("robot_2", 3.0, 0.0, 0.0, v=0.3),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert c.scenario == "blocked_path"
        assert c.blocker_kind == "object"
        assert c.involved_robots == ["robot_1"]

    def test_mutual_block_with_crosswise_goals_is_unknown(self):
        # Opposing headings but goals pointing away from each other: the
        # goal-beyond check fails head_on; each robot has the other within
        # r_block ahead, so blocked_path also fails -> unknown.
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.0, 5.0)),
            _robot("robot_2", 0.5, 0.0, math.pi, goal=(0.0, -5.0)),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert c.scenario == "unknown"
        assert c.congestion_type == "anomaly"
        assert c.blocker_kind is None

    def test_all_moving_is_none(self):
        frame = _frame(
            1.0,
            _robot("robot_1", 0.0, 0.0, 0.0, v=0.4),
            _robot("robot_2", 0.4, 0.0, math.pi, v=0.4),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert c.scenario == "none"
        assert c.congestion_type == "none"
        assert c.involved_robots == []

    def test_stopped_by_status_when_velocity_missing(self):
        frame = _frame(
            1.0,
            RobotStateInput(
                robot_id="robot_1", x=0.0, y=0.0, theta=0.0, status="STALE",
                goal=(5.0, 0.0),
            ),
        )
        c = classify_scene([frame], [], _PARAMS)
        assert c.scenario == "blocked_path"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_classical_reasoner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'reasoning.baselines'`.

- [ ] **Step 3: Implement**

Create `reasoning/baselines/__init__.py` (empty file) and `reasoning/baselines/classical_reasoner.py`:

```python
import math
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from reasoning.vlm.models import BlockerKind, RobotStateInput, SnapshotFrame

_STOPPED_STATUSES = {"STOPPED", "STALE"}


class ConflictZone(BaseModel):
    """Mapped conflict zone from scenario config (circle in world frame)."""

    model_config = ConfigDict(frozen=True)

    zone_id: str = Field(min_length=1)
    x: float
    y: float
    radius_m: float = Field(gt=0)


class ClassicalParams(BaseModel):
    """Arm B thresholds (rev-8); tunable on T1 only, frozen at prereg-v1."""

    model_config = ConfigDict(frozen=True)

    r_conflict_m: float = Field(default=1.5, gt=0)
    r_block_m: float = Field(default=1.0, gt=0)
    heading_opposition_min_deg: float = Field(default=150.0, gt=0)
    axis_cross_min_deg: float = Field(default=45.0, ge=0)
    axis_cross_max_deg: float = Field(default=135.0, gt=0)
    arrival_tie_sec: float = Field(default=1.0, gt=0)
    stopped_speed_mps: float = Field(default=0.05, gt=0)
    goal_beyond_max_deg: float = Field(default=60.0, gt=0)


class ClassicalClassification(BaseModel):
    """Geometry-classifier verdict (RQ1 control)."""

    model_config = ConfigDict(frozen=True)

    scenario: Literal["none", "head_on", "intersection", "blocked_path", "unknown"]
    congestion_type: Literal["none", "deadlock", "bottleneck", "anomaly"]
    blocker_kind: BlockerKind | None
    involved_robots: list[str]


def classify_scene(
    frames: Sequence[SnapshotFrame],
    zones: Sequence[ConflictZone],
    params: ClassicalParams,
) -> ClassicalClassification:
    """Classify the latest frame with the rev-8 Arm B geometry rules.

    Rules evaluate in order head_on -> intersection -> blocked_path ->
    unknown on the latest frame. The classifier has no image channel, so
    blocked_path always reports blocker_kind="object" (T3a's forced
    non-divergence).

    Args:
        frames: Snapshot history (only the latest frame is classified).
        zones: Mapped conflict zones from scenario config.
        params: Classifier thresholds.

    Returns:
        Classification with the involved robot ids, sorted.

    Raises:
        ValueError: If `frames` is empty.
    """
    if not frames:
        raise ValueError("classify_scene requires at least one frame")
    latest = max(frames, key=lambda f: f.stamp)
    stopped = [s for s in latest.robots if _is_stopped(s, params)]
    if not stopped:
        return ClassicalClassification(
            scenario="none", congestion_type="none", blocker_kind=None, involved_robots=[]
        )

    if len(stopped) == 2 and _is_head_on(stopped[0], stopped[1], params):
        return ClassicalClassification(
            scenario="head_on",
            congestion_type="deadlock",
            blocker_kind="robot",
            involved_robots=sorted(s.robot_id for s in stopped),
        )

    intersection = _intersection_robots(stopped, zones, params)
    if intersection:
        return ClassicalClassification(
            scenario="intersection",
            congestion_type="bottleneck",
            blocker_kind="robot",
            involved_robots=sorted(intersection),
        )

    blocked = [
        s.robot_id
        for s in stopped
        if not _has_robot_ahead(s, latest.robots, params)
    ]
    if blocked:
        return ClassicalClassification(
            scenario="blocked_path",
            congestion_type="anomaly",
            blocker_kind="object",
            involved_robots=sorted(blocked),
        )

    return ClassicalClassification(
        scenario="unknown",
        congestion_type="anomaly",
        blocker_kind=None,
        involved_robots=sorted(s.robot_id for s in stopped),
    )


def _is_stopped(state: RobotStateInput, params: ClassicalParams) -> bool:
    if state.linear_velocity is not None:
        return abs(state.linear_velocity) < params.stopped_speed_mps
    return (state.status or "").upper() in _STOPPED_STATUSES


def _angle_between_deg(a: float, b: float) -> float:
    diff = abs(a - b) % (2 * math.pi)
    if diff > math.pi:
        diff = 2 * math.pi - diff
    return math.degrees(diff)


def _is_head_on(
    a: RobotStateInput, b: RobotStateInput, params: ClassicalParams
) -> bool:
    if math.hypot(a.x - b.x, a.y - b.y) > params.r_conflict_m:
        return False
    if _angle_between_deg(a.theta, b.theta) < params.heading_opposition_min_deg:
        return False
    if a.goal is not None and b.goal is not None:
        if not _goal_beyond(a, b, params) or not _goal_beyond(b, a, params):
            return False
    return True


def _goal_beyond(
    robot: RobotStateInput, other: RobotStateInput, params: ClassicalParams
) -> bool:
    goal_bearing = math.atan2(robot.goal[1] - robot.y, robot.goal[0] - robot.x)
    other_bearing = math.atan2(other.y - robot.y, other.x - robot.x)
    return _angle_between_deg(goal_bearing, other_bearing) <= params.goal_beyond_max_deg


def _intersection_robots(
    stopped: list[RobotStateInput],
    zones: Sequence[ConflictZone],
    params: ClassicalParams,
) -> list[str]:
    for zone in zones:
        in_zone = [
            s
            for s in stopped
            if math.hypot(s.x - zone.x, s.y - zone.y) <= params.r_conflict_m
        ]
        with_goals = [s for s in in_zone if s.goal is not None]
        for i, a in enumerate(with_goals):
            for b in with_goals[i + 1 :]:
                axis_a = math.atan2(a.goal[1] - a.y, a.goal[0] - a.x)
                axis_b = math.atan2(b.goal[1] - b.y, b.goal[0] - b.x)
                angle = _angle_between_deg(axis_a, axis_b)
                if params.axis_cross_min_deg <= angle <= params.axis_cross_max_deg:
                    return [s.robot_id for s in in_zone]
    return []


def _has_robot_ahead(
    robot: RobotStateInput,
    all_robots: list[RobotStateInput],
    params: ClassicalParams,
) -> bool:
    heading = (math.cos(robot.theta), math.sin(robot.theta))
    for other in all_robots:
        if other.robot_id == robot.robot_id:
            continue
        dx, dy = other.x - robot.x, other.y - robot.y
        if math.hypot(dx, dy) <= params.r_block_m and (
            dx * heading[0] + dy * heading[1] > 0
        ):
            return True
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_classical_reasoner.py -v`
Expected: PASS.

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/baselines/__init__.py reasoning/baselines/classical_reasoner.py tests/unit/test_classical_reasoner.py
git commit -m "feat: add Arm B geometry classifier"
```

---

### Task 13: Arm B — policy table, FCFS + commitment tiebreak, full decision

**Files:**
- Modify: `reasoning/baselines/classical_reasoner.py`
- Modify: `tests/unit/test_classical_reasoner.py`

**Interfaces:**
- Consumes: `classify_scene` (Task 12), `derive_motion_table` + `MotionTableEntry.arrival_stamp` (Task 4), `CongestionDecision` (Task 1).
- Produces: `decide_classical(frames: Sequence[SnapshotFrame], zones: Sequence[ConflictZone], params: ClassicalParams, prior_yields: Mapping[str, int] | None = None, prior_attempts: int = 0) -> CongestionDecision`. Arm B emits the same type the VLM emits — same grounding, same validation, same execution (rev-8 arms section). Task 14's shadow comparator consumes two `CongestionDecision`s.

**Policy table (rev-8 Arm B):** `head_on → yield` (yielder = FCFS loser); `intersection → yield + ordered crossing` (order = FCFS, yielder = last arrival); `blocked_path → reroute` (blocker object); `unknown → temporary_wait` once, then `reroute` on re-analysis (`prior_attempts >= 1`).

**Tiebreak:** order by arrival stamp; within a tie cluster (< `arrival_tie_sec`), higher commitment passes first, where commitment = in-zone path length / zone diameter; residual ties order by `robot_id` ascending. The yielder is the last robot in the resulting order.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_classical_reasoner.py`:

```python
from reasoning.baselines.classical_reasoner import decide_classical


def _standoff_frames(
    r2_start_x: float = 0.4, r2_arrival_stamp: float = 0.0
) -> list[SnapshotFrame]:
    """Two frames ending in the verified head-on standoff geometry."""
    return [
        _frame(
            0.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
            _robot("robot_2", r2_start_x, 0.0, math.pi, goal=(-5.0, 0.0)),
        ),
        _frame(
            r2_arrival_stamp if r2_arrival_stamp > 0.0 else 2.0,
            _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
            _robot("robot_2", 0.4, 0.0, math.pi, goal=(-5.0, 0.0)),
        ),
    ]


class TestDecideClassicalHeadOn:
    def test_later_arrival_yields(self):
        # robot_2 starts outside the conflict zone and arrives second.
        frames = _standoff_frames(r2_start_x=5.0, r2_arrival_stamp=2.0)
        decision = decide_classical(frames, [], _PARAMS)
        assert decision.congestion_detected is True
        assert decision.type == "deadlock"
        assert decision.strategy == "yield"
        assert decision.blocker_kind == "robot"
        assert decision.yield_robot == "robot_2"
        assert decision.crossing_order == ["robot_1"]

    def test_arrival_tie_lower_commitment_yields(self):
        # Both in zone from t=0; robot_1 travels deeper inside the zone.
        frames = [
            _frame(
                0.0,
                _robot("robot_1", -0.5, 0.0, 0.0, v=0.3, goal=(5.0, 0.0)),
                _robot("robot_2", 0.9, 0.0, math.pi, goal=(-5.0, 0.0)),
            ),
            _frame(
                0.5,
                _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
                _robot("robot_2", 0.85, 0.0, math.pi, goal=(-5.0, 0.0)),
            ),
            _frame(
                1.0,
                _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
                _robot("robot_2", 0.4, 0.0, math.pi, goal=(-5.0, 0.0)),
            ),
        ]
        decision = decide_classical(frames, [], _PARAMS)
        assert decision.yield_robot == "robot_2"

    def test_full_tie_breaks_by_robot_id(self):
        frames = _standoff_frames()
        decision = decide_classical(frames, [], _PARAMS)
        assert decision.yield_robot == "robot_2"
        assert decision.crossing_order == ["robot_1"]


class TestDecideClassicalOtherScenarios:
    def test_blocked_path_reroutes_object(self):
        frames = [
            _frame(
                1.0,
                _robot("robot_1", 0.0, 0.0, 0.0, goal=(5.0, 0.0)),
                _robot("robot_2", 3.0, 0.0, 0.0, v=0.3),
            )
        ]
        decision = decide_classical(frames, [], _PARAMS)
        assert decision.strategy == "reroute"
        assert decision.blocker_kind == "object"
        assert decision.yield_robot is None
        assert decision.crossing_order is None

    def test_unknown_waits_first_then_reroutes(self):
        frames = [
            _frame(
                1.0,
                _robot("robot_1", 0.0, 0.0, 0.0, goal=(0.0, 5.0)),
                _robot("robot_2", 0.5, 0.0, math.pi, goal=(0.0, -5.0)),
            )
        ]
        first = decide_classical(frames, [], _PARAMS, prior_attempts=0)
        second = decide_classical(frames, [], _PARAMS, prior_attempts=1)
        assert first.strategy == "temporary_wait"
        assert second.strategy == "reroute"

    def test_no_congestion_returns_none_decision(self):
        frames = [
            _frame(1.0, _robot("robot_1", 0.0, 0.0, 0.0, v=0.4))
        ]
        decision = decide_classical(frames, [], _PARAMS)
        assert decision.congestion_detected is False
        assert decision.type == "none"
        assert decision.strategy == "none"
        assert decision.involved_robots == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_classical_reasoner.py -v -k Decide`
Expected: FAIL with `ImportError: cannot import name 'decide_classical'`.

- [ ] **Step 3: Implement**

Append to `reasoning/baselines/classical_reasoner.py` (extend the imports with `from collections.abc import Mapping, Sequence` and `from reasoning.vlm.models import CongestionDecision` and `from reasoning.vlm.motion_table import derive_motion_table`):

```python
def decide_classical(
    frames: Sequence[SnapshotFrame],
    zones: Sequence[ConflictZone],
    params: ClassicalParams,
    prior_yields: Mapping[str, int] | None = None,
    prior_attempts: int = 0,
) -> CongestionDecision:
    """Arm B: deterministic classical decision on the same inputs as Arm A.

    Applies the rev-8 policy table on top of `classify_scene`. Emits the
    same `CongestionDecision` contract the VLM emits, so grounding,
    validation, and M4 execution are shared across arms.

    Args:
        frames: Snapshot history (ring-buffer contents).
        zones: Mapped conflict zones from scenario config.
        params: Classifier thresholds.
        prior_yields: Yield counts this episode, keyed by robot_id.
        prior_attempts: Prior resolution attempts this episode (unknown
            scenario waits once, then reroutes).

    Returns:
        Frozen decision; `congestion_detected=False` when nothing is stopped.
    """
    classification = classify_scene(frames, zones, params)
    involved = classification.involved_robots
    if classification.scenario == "none":
        return CongestionDecision(
            congestion_detected=False,
            type="none",
            involved_robots=[],
            root_cause="classical: no stopped robots",
            strategy="none",
            justification="classical geometry classifier found no congestion",
        )

    if classification.scenario in ("head_on", "intersection"):
        order = _passing_order(frames, involved, zones, params, prior_yields)
        yielder = order[-1]
        return CongestionDecision(
            congestion_detected=True,
            type=classification.congestion_type,
            involved_robots=involved,
            root_cause=(
                f"classical: {classification.scenario} between {', '.join(involved)}"
            ),
            strategy="yield",
            justification=(
                "FCFS with commitment tiebreak: "
                f"{yielder} arrived last or is least committed"
            ),
            blocker_kind="robot",
            yield_robot=yielder,
            crossing_order=order[:-1],
        )

    if classification.scenario == "blocked_path":
        return CongestionDecision(
            congestion_detected=True,
            type=classification.congestion_type,
            involved_robots=involved,
            root_cause=f"classical: {', '.join(involved)} blocked with clear front",
            strategy="reroute",
            justification="classical policy: blocked_path is always object -> reroute",
            blocker_kind="object",
        )

    strategy = "temporary_wait" if prior_attempts == 0 else "reroute"
    return CongestionDecision(
        congestion_detected=True,
        type=classification.congestion_type,
        involved_robots=involved,
        root_cause=f"classical: unclassified stall of {', '.join(involved)}",
        strategy=strategy,
        justification=(
            "classical policy: unknown scenario waits once then reroutes "
            f"(prior_attempts={prior_attempts})"
        ),
    )


def _passing_order(
    frames: Sequence[SnapshotFrame],
    involved: list[str],
    zones: Sequence[ConflictZone],
    params: ClassicalParams,
    prior_yields: Mapping[str, int] | None,
) -> list[str]:
    latest = max(frames, key=lambda f: f.stamp)
    states = [s for s in latest.robots if s.robot_id in involved]
    if zones:
        center = (zones[0].x, zones[0].y)
        radius = zones[0].radius_m
    else:
        center = (
            sum(s.x for s in states) / len(states),
            sum(s.y for s in states) / len(states),
        )
        radius = params.r_conflict_m
    table = derive_motion_table(
        frames, center, radius, prior_yields, params.stopped_speed_mps
    )
    arrival = {
        e.robot_id: e.arrival_stamp for e in table.entries if e.robot_id in involved
    }
    commitment = {
        rid: _commitment(frames, rid, center, radius) for rid in involved
    }
    ordered = sorted(
        involved,
        key=lambda r: (arrival.get(r) is None, arrival.get(r) or 0.0),
    )
    result: list[str] = []
    i = 0
    while i < len(ordered):
        j = i + 1
        while (
            j < len(ordered)
            and arrival.get(ordered[i]) is not None
            and arrival.get(ordered[j]) is not None
            and arrival[ordered[j]] - arrival[ordered[i]] < params.arrival_tie_sec
        ):
            j += 1
        result.extend(sorted(ordered[i:j], key=lambda r: (-commitment[r], r)))
        i = j
    return result


def _commitment(
    frames: Sequence[SnapshotFrame],
    robot_id: str,
    center: tuple[float, float],
    radius: float,
) -> float:
    ordered = sorted(frames, key=lambda f: f.stamp)
    path = 0.0
    previous: tuple[RobotStateInput, bool] | None = None
    for frame in ordered:
        state = frame.find_robot(robot_id)
        if state is None:
            continue
        inside = math.hypot(state.x - center[0], state.y - center[1]) <= radius
        if previous is not None and inside and previous[1]:
            path += math.hypot(state.x - previous[0].x, state.y - previous[0].y)
        previous = (state, inside)
    return path / (2 * radius)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_classical_reasoner.py -v`
Expected: PASS (Tasks 12 + 13 tests).

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/baselines/classical_reasoner.py tests/unit/test_classical_reasoner.py
git commit -m "feat: Arm B policy table with FCFS commitment tiebreak"
```

---

### Task 14: Shadow comparator, config loaders, public exports

**Files:**
- Create: `reasoning/baselines/shadow.py`
- Create: `tests/unit/test_shadow_comparison.py`
- Modify: `reasoning/rag/maneuver_geometry.py` (add `load_grounding_params`)
- Modify: `reasoning/baselines/classical_reasoner.py` (add `load_classical_params`)
- Modify: `reasoning/baselines/__init__.py`, `reasoning/vlm/__init__.py`
- Modify: `config/rag.yaml`
- Modify: `tests/unit/test_maneuver_geometry.py`, `tests/unit/test_classical_reasoner.py` (loader tests)

**Interfaces:**
- Consumes: `CongestionDecision` (Task 1), `GroundingParams` (Task 8), `ClassicalParams` (Task 12).
- Produces:
  - `DisagreementRecord(strategy_match, yielder_match, order_match, blocker_match, type_match, any_disagreement)` and `compare_decisions(vlm: CongestionDecision, classical: CongestionDecision) -> DisagreementRecord` in `reasoning/baselines/shadow.py` — Phase 2 logs this per decision (disagreements are first-class events).
  - `load_grounding_params(path: Path = Path("config/rag.yaml")) -> GroundingParams` and `load_classical_params(path: Path = Path("config/rag.yaml")) -> ClassicalParams` — missing sections yield defaults.
  - `reasoning.baselines` and `reasoning.vlm` re-export the Phase-1 public API.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_shadow_comparison.py`:

```python
from reasoning.baselines.shadow import compare_decisions
from reasoning.vlm.models import CongestionDecision


def _decision(**overrides) -> CongestionDecision:
    base = {
        "congestion_detected": True,
        "type": "deadlock",
        "involved_robots": ["robot_1", "robot_2"],
        "root_cause": "standoff",
        "strategy": "yield",
        "justification": "j",
        "blocker_kind": "robot",
        "yield_robot": "robot_1",
        "crossing_order": ["robot_2"],
    }
    base.update(overrides)
    return CongestionDecision(**base)


class TestCompareDecisions:
    def test_identical_decisions_have_no_disagreement(self):
        record = compare_decisions(_decision(), _decision())
        assert record.any_disagreement is False
        assert record.strategy_match and record.yielder_match
        assert record.order_match and record.blocker_match and record.type_match

    def test_strategy_disagreement_flagged(self):
        record = compare_decisions(_decision(strategy="reroute"), _decision())
        assert record.strategy_match is False
        assert record.any_disagreement is True

    def test_yielder_disagreement_flagged(self):
        record = compare_decisions(
            _decision(yield_robot="robot_2", crossing_order=["robot_1"]), _decision()
        )
        assert record.yielder_match is False
        assert record.order_match is False
        assert record.any_disagreement is True

    def test_absent_order_on_both_sides_matches(self):
        vlm = _decision(yield_robot=None, crossing_order=None)
        classical = _decision(yield_robot=None, crossing_order=None)
        record = compare_decisions(vlm, classical)
        assert record.order_match is True

    def test_blocker_kind_disagreement_flagged(self):
        record = compare_decisions(_decision(blocker_kind="object", strategy="reroute"), _decision())
        assert record.blocker_match is False
        assert record.any_disagreement is True
```

Append to `tests/unit/test_maneuver_geometry.py`:

```python
class TestLoadGroundingParams:
    def test_missing_section_yields_defaults(self, tmp_path):
        from pathlib import Path

        from reasoning.rag.maneuver_geometry import load_grounding_params

        config = tmp_path / "rag.yaml"
        config.write_text("rag:\n  top_k: 3\n", encoding="utf-8")
        params = load_grounding_params(Path(config))
        assert params.mode == "legacy"
        assert params.backup_clearance_m == 1.7

    def test_section_overrides_defaults(self, tmp_path):
        from pathlib import Path

        from reasoning.rag.maneuver_geometry import load_grounding_params

        config = tmp_path / "rag.yaml"
        config.write_text(
            "grounding:\n  mode: derived\n  lateral_m: 0.4\n", encoding="utf-8"
        )
        params = load_grounding_params(Path(config))
        assert params.mode == "derived"
        assert params.lateral_m == 0.4

    def test_repo_config_parses(self):
        from pathlib import Path

        from reasoning.rag.maneuver_geometry import load_grounding_params

        params = load_grounding_params(Path("config/rag.yaml"))
        assert params.mode == "legacy"  # live loop stays legacy until Phase 2
```

Append to `tests/unit/test_classical_reasoner.py`:

```python
class TestLoadClassicalParams:
    def test_repo_config_parses_with_rev8_defaults(self):
        from pathlib import Path

        from reasoning.baselines.classical_reasoner import load_classical_params

        params = load_classical_params(Path("config/rag.yaml"))
        assert params.r_conflict_m == 1.5
        assert params.arrival_tie_sec == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_shadow_comparison.py tests/unit/test_maneuver_geometry.py tests/unit/test_classical_reasoner.py -v -k "Compare or Load"`
Expected: FAIL with import errors for `shadow`, `load_grounding_params`, `load_classical_params`.

- [ ] **Step 3: Implement**

Create `reasoning/baselines/shadow.py`:

```python
from pydantic import BaseModel, ConfigDict

from reasoning.vlm.models import CongestionDecision


class DisagreementRecord(BaseModel):
    """Field-level agreement between the VLM (Arm A) and classical (Arm B)."""

    model_config = ConfigDict(frozen=True)

    strategy_match: bool
    yielder_match: bool
    order_match: bool
    blocker_match: bool
    type_match: bool
    any_disagreement: bool


def compare_decisions(
    vlm: CongestionDecision, classical: CongestionDecision
) -> DisagreementRecord:
    """Compare the two arms' decisions; disagreements are first-class events.

    Args:
        vlm: Arm A decision (executed in Arm A episodes).
        classical: Arm B shadow decision computed on the same inputs.

    Returns:
        Frozen record; `any_disagreement` is True when any compared field
        differs. Absent optional fields compare as equal when absent on
        both sides.
    """
    strategy_match = vlm.strategy == classical.strategy
    yielder_match = vlm.yield_robot == classical.yield_robot
    order_match = (vlm.crossing_order or []) == (classical.crossing_order or [])
    blocker_match = vlm.blocker_kind == classical.blocker_kind
    type_match = vlm.type == classical.type
    return DisagreementRecord(
        strategy_match=strategy_match,
        yielder_match=yielder_match,
        order_match=order_match,
        blocker_match=blocker_match,
        type_match=type_match,
        any_disagreement=not (
            strategy_match and yielder_match and order_match and blocker_match and type_match
        ),
    )
```

Append to `reasoning/rag/maneuver_geometry.py` (add `from pathlib import Path` to the stdlib imports and `import yaml` to third-party):

```python
def load_grounding_params(path: Path = Path("config/rag.yaml")) -> GroundingParams:
    """Load the `grounding:` section of the RAG config; defaults when absent.

    Args:
        path: YAML config path.

    Returns:
        Validated params; an absent or empty section yields all defaults.
    """
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return GroundingParams(**(raw.get("grounding") or {}))
```

Append to `reasoning/baselines/classical_reasoner.py` (add `from pathlib import Path` and `import yaml`):

```python
def load_classical_params(path: Path = Path("config/rag.yaml")) -> ClassicalParams:
    """Load the `classical:` section of the RAG config; defaults when absent.

    Args:
        path: YAML config path.

    Returns:
        Validated params; an absent or empty section yields all defaults.
    """
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return ClassicalParams(**(raw.get("classical") or {}))
```

Append to `config/rag.yaml` (mode stays `legacy` — the live loop is unaffected until Phase 2 flips it):

```yaml

grounding:
  mode: legacy
  min_distance_m: 0.45
  backup_clearance_m: 1.7
  escort_clearance_m: 0.5
  backup_band_m: [0.5, 2.0]
  escort_band_m: [1.0, 3.5]
  lateral_m: 0.35
  sweep_step_m: 0.1

classical:
  r_conflict_m: 1.5
  r_block_m: 1.0
  heading_opposition_min_deg: 150.0
  axis_cross_min_deg: 45.0
  axis_cross_max_deg: 135.0
  arrival_tie_sec: 1.0
  stopped_speed_mps: 0.05
  goal_beyond_max_deg: 60.0
```

Replace `reasoning/baselines/__init__.py` with:

```python
"""Arm B classical reasoner and shadow comparison (rev-8 experiment control)."""

from reasoning.baselines.classical_reasoner import (
    ClassicalClassification,
    ClassicalParams,
    ConflictZone,
    classify_scene,
    decide_classical,
    load_classical_params,
)
from reasoning.baselines.shadow import DisagreementRecord, compare_decisions

__all__ = [
    "ClassicalClassification",
    "ClassicalParams",
    "ConflictZone",
    "DisagreementRecord",
    "classify_scene",
    "compare_decisions",
    "decide_classical",
    "load_classical_params",
]
```

In `reasoning/vlm/__init__.py`, extend the `from reasoning.vlm.models import (...)` block with `BlockerKind`, `FailureContext`, `ModalityCondition`, `MotionTable`, `MotionTableEntry`, `RetreatChoiceDecision`, `SnapshotFrame`; add `from reasoning.vlm.motion_table import derive_motion_table`; extend the `output_parser` import with `parse_retreat_choice_text`; extend the `prompt_builder` import with `ANNOTATION_SCHEME_SENTENCE`, `render_failure_context_block`, `render_motion_table_block`; and add each new name to `__all__` (keep it sorted).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_shadow_comparison.py tests/unit/test_maneuver_geometry.py tests/unit/test_classical_reasoner.py -v`
Expected: PASS.

- [ ] **Step 5: Full suite + commit**

```bash
pytest tests/unit -q
git add reasoning/baselines/ reasoning/rag/maneuver_geometry.py reasoning/vlm/__init__.py config/rag.yaml tests/unit/test_shadow_comparison.py tests/unit/test_maneuver_geometry.py tests/unit/test_classical_reasoner.py
git commit -m "feat: shadow comparison, config loaders, public exports"
```

---

### Task 15: Docs sync and final verification

**Files:**
- Modify: `docs/specs/module2_vlm_reasoning.md`
- Modify: `docs/specs/module3_rag_grounding.md`

**Interfaces:**
- Consumes: everything above (documentation of the shipped contracts).
- Produces: module specs consistent with the code, per CLAUDE.md's rule that schema changes update specs and downstream consumers.

- [ ] **Step 1: Append the M2 addendum**

At the end of `docs/specs/module2_vlm_reasoning.md`, add:

```markdown

---

## Addendum — Phase 1 congestion-reasoner contracts (2026-07-08)

Implemented per rev-8 of
`docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`
(Phase 1 plan: `docs/superpowers/plans/2026-07-08-congestion-reasoner-phase1-core.md`).

- `CongestionDecision` gains optional `blocker_kind` ("robot" | "object" |
  "transient"), `yield_robot`, and `crossing_order`. The parser rejects a
  `yield_robot` outside `involved_robots` and any `crossing_order` that is
  not a duplicate-free permutation of the remaining involved robots.
- Stage-2 contract: `retreat_choice.schema.json`, `RetreatChoiceDecision`,
  and `parse_retreat_choice_text(text, valid_labels)`; an unrendered label
  raises and callers fall back to the geometry-best candidate.
- `ReasonerRequest` gains `motion_table` (from
  `reasoning.vlm.motion_table.derive_motion_table`), `failure_context`
  (prior-attempt block, rev-5 Reflexion-lite), and `modality`
  ("dual" | "text_only" | "image_only", rev-8 modality table).
- `PromptPayload.image_path` is now `str | None`; every backend emits a
  text-only user message when it is None.
```

- [ ] **Step 2: Append the M3 addendum**

At the end of `docs/specs/module3_rag_grounding.md`, add:

```markdown

---

## Addendum — Phase 1 derived grounding (2026-07-08)

Implemented per rev-8 Appendix A (Phase 1 plan:
`docs/superpowers/plans/2026-07-08-congestion-reasoner-phase1-core.md`).

- `ground_reasoner_result(result, *, snapshot, params, retreat_choice)`:
  `params.mode="legacy"` (default) is byte-identical to the pre-rev-8
  bridge; `mode="derived"` adds compatibility enforcement
  (`strategy_compatibility.py`), derived backup/escort distances with
  feasibility bands (`maneuver_geometry.py`), swept-path-validated ranked
  retreat candidates (`retreat_candidates.py`), explicit
  `crossing_order`/`linked_position` fields, and a `degradations` list
  (schema-extended, optional) instead of blind constants.
- No-snapshot in derived mode grounds a non-spatial `temporary_wait`
  tagged `distances=unavailable`; infeasible geometry grounds a reroute
  outcome tagged `yield=infeasible:*` — never clamped motion.
- Arm B (`reasoning/baselines/`) emits the same `CongestionDecision`
  contract; `compare_decisions` records per-field shadow disagreement.
- Config: `grounding:` and `classical:` sections in `config/rag.yaml`
  (live mode stays `legacy` until the Phase 2 call-site flip).
```

- [ ] **Step 3: Full verification**

```bash
pytest tests/unit -q
make lint
```

Expected: full unit suite green; lint clean. If lint flags anything in the new modules, fix it before committing.

- [ ] **Step 4: Commit**

```bash
git add docs/specs/module2_vlm_reasoning.md docs/specs/module3_rag_grounding.md
git commit -m "docs: sync module 2/3 specs with phase-1 contracts"
```

---

## Phase 1 exit criteria

- All 15 tasks committed; `pytest tests/unit -q` and `make lint` green.
- `git log --oneline` shows one commit per task, conventional subjects.
- Live behavior unchanged: `config/rag.yaml` grounding mode is `legacy`, and the no-argument `ground_reasoner_result(result)` output is byte-identical (guarded by `TestLegacyModeUnchanged`).
- Phase 2 (M5/M1 integration) can start against the frozen interfaces listed in the header.
