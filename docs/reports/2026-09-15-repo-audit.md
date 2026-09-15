# Repository Audit — CI, Test Suite, and Dependency Health

**Prepared:** 2026-09-15

**Revision history:**

- Initial draft: full-repository audit of CI state, test-suite health, dependency pinning, standards conformance, and secrets hygiene at commit `0ad2a68`.

---

## Overview

### Audit Scope

- Repository-wide, not module-scoped: CI gates, the `pytest` suite, lint state, dependency declarations, secrets hygiene, and conformance to `CLAUDE.md` / `docs/standards/`.
- Audited commit `0ad2a68` on branch `claude/laughing-volta-fwnqvs` (identical tree to `main` at the time of audit).
- Read-only: no source, config, or test file was modified while producing this report.

### What Was Audited

- Both GitHub Actions workflows and their full run history (56 runs across `python_ci.yml` and `ros_ci.yml`).
- The complete `pytest` suite: bare invocation, invocation with uncollectable modules excluded, and the `-m "not ros2"` escape hatch documented in `pyproject.toml`.
- `ruff check .` against the project's own configured rule set (`E`, `F`, `I`, `UP`, `B`).
- Runtime dependency declarations across `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `package.xml`, and `setup.py`, against actually-installed versions.
- Tracked files scanned for credential-shaped strings; `.gitignore` and `.env.example` reviewed.
- Spot conformance checks against `CLAUDE.md`: ROS2 callback discipline, Pydantic contracts, module boundaries, marker registration, and test-isolation rules.

### This Report

This report records the audit findings, the evidence for each, and a recommended
remediation order; it does not apply any fix.

---

## Objective

- [x] Determine whether the project's automated quality gates actually gate anything.
- [x] Establish the true pass/fail state of the test suite.
- [x] Separate genuine production defects from test and configuration drift.
- [x] Verify secrets hygiene and dependency-pinning policy.
- [x] Record findings with stable IDs so remediation can be tracked.

---

## Summary of Findings

| ID | Severity | Area | Finding |
|---|---|---|---|
| A1 | Critical | CI | Python CI has never passed; lint gate masks the test gate |
| A2 | Critical | Tests | `pytest` aborts during collection; zero tests run |
| A3 | Critical | M1 | ArUco id unpacking breaks on OpenCV 5.x; detection non-functional |
| A4 | High | M4 | `Nav2Adapter` fixture rot; systemic `__new__` bypass fragility |
| A5 | High | M5 | Close-pair reset test is confounded; behavior has no real coverage |
| A6 | High | M2 | `build_backend` openai path contradicts its own docstring and test |
| A7 | High | Tests | Two stale assertions contradict deliberate config and schema changes |
| A8 | Medium | Deps | Unbounded major-version ranges; no lockfile |
| A9 | Medium | Deps | `pyproject.toml` omits four runtime dependencies |
| A10 | Medium | Tests | `isaac_sim` marker unregistered; documented deselect is ineffective |
| A11 | Medium | Lint | 167 ruff errors across the tree |
| A12 | Low | Docs | `.env.example` omits `ANTHROPIC_API_KEY` |
| A13 | Low | Docs | `CLAUDE.md` file layout omits `swarm_execution/` |

---

## Critical Findings

### A1 — Python CI has never passed, and the lint gate masks the test gate

`.github/workflows/python_ci.yml` runs five steps in order: dependency install,
`ruff check .`, `python scripts/smoke_perception.py`, then `pytest`. Ruff exits
non-zero, so **the smoke and `pytest` steps have never executed in CI**.

All 28 `python_ci.yml` runs are `failure`, from run 1 (2026-06-05, commit
`35d7a52`, the initial M1 implementation) through run 28 (2026-07-13, commit
`0ad2a68`). There is no green run in the repository's history. Runs complete in
roughly 20 seconds, consistent with failing before any test executes.

The failing job log terminates with:

```text
Found 167 errors.
[*] 98 fixable with the `--fix` option (8 hidden fixes can be enabled with the `--unsafe-fixes` option).
##[error]Process completed with exit code 1.
```

`ros_ci.yml` (colcon build) is `success` at `0ad2a68`, though it failed on runs
24–26. This finding is the root enabler of A2 through A7: the test suite has had
no enforcement since the project began.

### A2 — `pytest` aborts during collection, so zero tests run

Three test modules import `pxr` (USD) at module top level with no guard:

- `tests/unit/test_marker_asset.py`
- `tests/unit/test_robot_asset.py`
- `tests/unit/test_scenario_builder.py`

`pxr` ships with Isaac Sim's embedded Python and is not in
`requirements-dev.txt`. Collection therefore raises three `ModuleNotFoundError`
errors and pytest reports `Interrupted: 3 errors during collection` — **no test
executes at all**, locally via `make test` or in CI.

The repository already establishes the correct idiom in its sibling modules,
which skip cleanly:

```python
pxr = pytest.importorskip("pxr")
from pxr import Usd, UsdGeom  # noqa: E402 — after importorskip
```

That guard is present in `tests/unit/test_lidar.py`,
`tests/unit/test_robot_drive.py`, and `tests/unit/test_m6_validation.py`, and
absent from the three modules above. This is an omission, not a design gap.

### A3 — M1 ArUco id unpacking breaks on OpenCV 5.x

`ros2_ws/src/swarm_perception/swarm_perception/detection.py:95` unpacks detector
ids assuming a two-dimensional array:

```python
ids_flat = [int(i[0]) for i in ids]
```

OpenCV 4.x returned `ids` shaped `(N, 1)`; **OpenCV 5.0 returns `(N,)`**.
Probed directly against the installed build (`opencv-contrib-python 5.0.0.93`,
`cv2.__version__ == "5.0.0"`):

```text
ids type <class 'numpy.ndarray'> ids array([1], dtype=int32)
ids shape (1,) ndim 1
n corners 1 corner0 shape (1, 4, 2)
```

Every call to `detect_aruco_markers` therefore raises
`IndexError: invalid index to scalar variable.`, making M1 perception
non-functional on a fresh install — in the module `CLAUDE.md` designates as
fully implemented and as the reference pattern for the project. Corner handling
at line 97 is unaffected, since corners remain `(1, 4, 2)`.

The 49 failures in `tests/unit/test_aruco_parity.py` are this bug, correctly
detected. The unbounded pin `opencv-contrib-python>=4.8` (A8) is what admitted
the major-version bump.

A shape-robust replacement was validated against all four conventions:

```python
ids_flat = [int(i) for i in np.asarray(ids).reshape(-1)]
```

| `ids` shape | Current expression | Validated replacement |
|---|---|---|
| `(N, 1)` — OpenCV 4.x | `[1, 7]` | `[1, 7]` |
| `(N,)` — OpenCV 5.x | `IndexError` | `[1, 7]` |
| `(1, 1)` | `[1]` | `[1]` |
| `(1,)` | `IndexError` | `[1]` |

`isaac/scripts/probe_cam_change.py:118` and
`isaac/scripts/probe_physxfabric.py:162` already use the equivalent
`ids.flatten()` idiom, so the robust form has in-tree precedent.

---

## High Findings

### A4 — `Nav2Adapter` fixture rot, and a systemic `__new__` bypass fragility

The `adapter` fixture at `tests/unit/test_nav2_adapter.py:90-95` constructs the
object via `Nav2Adapter.__new__(Nav2Adapter)` and hand-assigns three attributes.
`Nav2Adapter.__init__`
(`ros2_ws/src/swarm_execution/swarm_execution/nav2_adapter.py:103-117`) assigns
eight, having since grown `_backup_clients`, `_cancel_clients`, `_backup_pubs`,
`_backup_timers`, and `_backup_odom_subs`. `cancel()` reads `_backup_timers`,
so all 13 tests fail with:

```text
AttributeError: 'Nav2Adapter' object has no attribute '_backup_timers'
```

**Production code is correct here** — `__init__` sets the attribute at line 115.
The fixture is stale.

The wider issue is that the fixture duplicates `__init__`'s attribute list, so it
will rot again on the next attribute added. The `__new__` bypass is a
project-wide convention for ROS2-free node tests, used at 16 sites across four
files — `test_nav2_adapter.py` (3), `test_command_bus_node.py` (9),
`test_base_mission.py` (1), `test_safety_monitor.py` (1) — each carrying the same
latent failure mode. Note that one nav2 test already patches around it by
setting `a._backup_timers = {}` by hand at line 367. Stubbing only the ROS2
boundary, rather than bypassing `__init__`, would remove the whole class of
failure.

### A5 — Close-pair reset test is confounded, leaving the behavior uncovered

`tests/unit/test_m5_congestion_detector.py::test_close_pair_timer_resets_when_robots_separate`
asserts `event is None` after two robots separate and re-approach.

The close-pair timer is in fact **working correctly**. The emitted event reason
is `"2 robot(s) stalled >= 10.0s"`, not `"close/slow >= ..."`, which proves
`close_stalled` was empty and the reset at
`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/congestion_detector.py:134-135`
fired as designed.

The event originates from the independent progress-stall path: `robot_0` sits at
`(0.0, 0.0)` with a goal at `(10.0, 0.0)` for the full 11 simulated seconds,
exceeding `stall_threshold_sec=10.0`. With that setup the assertion can never
hold, regardless of close-pair behavior.

Consequences:

- The test violates the `CLAUDE.md` rule "Test one behavior per function."
- The close-pair reset logic has **no passing coverage**, because the only test
  naming it is failing for an unrelated reason.

Isolating it requires robots that are making progress toward their goals, so the
progress-stall path cannot fire.

### A6 — `build_backend` openai path contradicts its own docstring and test

`reasoning/vlm/backend_factory.py` raises `ValueError` when `backend_config` is
`None` for `llama_server` (line 36-37) and `anthropic` (line 53-54), but for
`openai` silently substitutes a default at lines 44-45:

```python
if backend_id == "openai":
    if backend_config is None:
        backend_config = OpenAIBackendConfig()
```

Its own docstring states the opposite — "backends that require it raise on
absence", plus a documented `Raises: ValueError: ... required config is
missing`. `tests/unit/test_openai_backend.py:131-133` encodes the raising
behavior. Code, docstring, and test all disagree.

This requires a design decision rather than a mechanical fix: the default
construction may be deliberate convenience, in which case the docstring and test
are what should change.

Independently, that test is environment-dependent and fails two different ways:

| Ambient environment | Observed failure |
|---|---|
| `OPENAI_API_KEY` unset | Wrong message: `OPENAI_API_KEY is not set in the environment` |
| `OPENAI_API_KEY` set | `Failed: DID NOT RAISE ValueError` |

It needs `monkeypatch.delenv` regardless of how the factory question is settled.

### A7 — Two stale assertions contradict deliberate config and schema changes

Both are cases where the production change was intentional and the test was never
updated.

- `tests/unit/test_m6_config.py:159` asserts
  `effective_width_m == pytest.approx(0.4)`, but
  `isaac/config/scenarios/head_on_deadlock.yaml:43` is `0.55`. The 0.55 m
  corridor was a deliberate change (commit `aa80d96`, superseding an earlier
  0.70 m version) and carries an extended in-file rationale. It is also already
  recorded in `docs/implementation_notes.md` under M6 (2026-07-04). **The config
  is correct; the assertion is stale.**
- `tests/unit/test_m5_reasoning_pipeline.py:285` passes
  `strategy="robot_1 yields while robot_2 passes"`, but
  `CongestionDecision.strategy` is now a `Literal` enum
  (`reasoning/vlm/models.py:56`) admitting only `none`, `yield`, `reroute`,
  `convoy`, `priority_override`, `temporary_wait`, `reverse`. The test predates
  the schema tightening; other tests in the same file already use `strategy="yield"`.

---

## Medium Findings

### A8 — Unbounded major-version ranges and no lockfile

`requirements.txt` specifies lower bounds only. `opencv-contrib-python>=4.8`
admitted the 4 to 5 major bump that caused A3; `numpy>=1.24` resolved to 2.4.6.

| Declared | Installed |
|---|---|
| `opencv-contrib-python>=4.8` | 5.0.0.93 |
| `numpy>=1.24` | 2.4.6 |
| `pydantic>=2.7` | 2.13.5 |
| `pytest>=8.2` | 9.1.1 |

This is a policy gap against the project's own standard: `CLAUDE.md` names
OpenCV ArUco APIs specifically under "External Library Verification" as
version-sensitive, and `docs/standards/doc_style.md` requires recording library
versions when an API is version-sensitive.

### A9 — `pyproject.toml` omits four runtime dependencies

`CLAUDE.md` requires runtime dependencies in both `pyproject.toml` and
`requirements.txt`. `pyproject.toml` declares only `jsonschema`, `pydantic`, and
`pyyaml`, omitting `numpy`, `opencv-contrib-python`, `Pillow`, and `requests` —
all imported by runtime code. A `pip install .` produces a broken install.

### A10 — `isaac_sim` marker unregistered, and the documented deselect is ineffective

`pyproject.toml` registers only the `ros2` marker. `@pytest.mark.isaac_sim` is
used at 7 sites (`test_m6_scenarios.py` 5, `test_m4_phase1_drive.py` 1,
`test_m4_phase2_nav2.py` 1) and is unregistered.

More importantly, the escape hatch the marker description advertises —
`deselect with -m 'not ros2'` — does not restore a clean run. With the three
uncollectable modules excluded, `-m "not ros2"` deselects only 4 tests and still
leaves 69 failures. Marking alone does not prevent a default run from failing;
per `CLAUDE.md`, environment-dependent tests must be separable from fast unit
tests, which in practice means `importorskip` guards as used elsewhere.

### A11 — 167 ruff errors across the tree

Counts under the project's configured rule set:

| Rule | Count | Description |
|---|---|---|
| I001 | 71 | unsorted-imports |
| E501 | 41 | line-too-long |
| F401 | 20 | unused-import |
| E402 | 10 | module-import-not-at-top-of-file |
| B017 | 7 | assert-raises-exception |
| UP031 | 5 | printf-string-formatting |
| B905 | 4 | zip-without-explicit-strict |
| F541 | 4 | f-string-missing-placeholders |
| UP037 | 2 | quoted-annotation |
| B007 | 1 | unused-loop-control-variable |
| B904 | 1 | raise-without-from-inside-except |
| F841 | 1 | unused-variable |

98 are auto-fixable. The 10 E402 violations warrant judgment rather than blanket
fixing: several are legitimate post-`importorskip` imports, and comparable sites
already carry `# noqa: E402` in some files but not others, so the right action is
to normalize that annotation.

---

## Low Findings

### A12 — `.env.example` omits `ANTHROPIC_API_KEY`

`.env.example` documents only `OPENAI_API_KEY`, but the anthropic backend is
supported and reads `ANTHROPIC_API_KEY` by default
(`reasoning/vlm/models.py:127`, `reasoning/vlm/anthropic_backend.py:33`). Anyone
selecting that backend has no documented setup path.

### A13 — `CLAUDE.md` file layout omits `swarm_execution/`

The File Layout tree lists `swarm_perception`, `swarm_interfaces`,
`swarm_orchestrator`, and `swarm_simulation`, but not `swarm_execution`, which
exists on disk and is named in Module Boundaries (`CLAUDE.md:247`). The onboarding
document understates the workspace.

---

## Verified Healthy

Recorded so remediation does not disturb what is already correct.

- **Secrets hygiene.** `.env` and `.env.local` are gitignored; only
  `.env.example` is tracked and holds a placeholder. A scan of all tracked files
  for OpenAI, Anthropic, AWS, GitHub-token, and PEM private-key patterns found
  nothing. Keys are read via `os.environ` under a configurable `api_key_env`
  name, with explicit "never the key itself" comments in
  `reasoning/vlm/models.py`.
- **ROS2 async discipline.** Every `future.result()` call sits inside a `done()`
  guard or a done-callback — `orchestrator_node.py:237`,
  `nav2_adapter.py:590`, `nav2_adapter.py:614`. No blocking VLM or action call
  appears in a timer or high-rate callback, matching the `CLAUDE.md` prohibition.
- **ROS2 CI** is green at `0ad2a68`.
- **`scripts/smoke_perception.py`** passes.
- **444 tests pass** once collection is unblocked; the bulk of the suite is sound.
- The Pydantic v2 contract style, module boundaries, and the `importorskip`
  convention are well established. The findings above are drift against an
  existing design, not absence of one.

---

## Verification

Commands run during the audit, from the repository root with
`requirements-dev.txt` installed:

```bash
python -m pytest -q
python -m pytest -q --ignore=tests/unit/test_marker_asset.py \
                    --ignore=tests/unit/test_robot_asset.py \
                    --ignore=tests/unit/test_scenario_builder.py
python -m pytest -q -m "not ros2" --ignore=tests/unit/test_marker_asset.py \
                    --ignore=tests/unit/test_robot_asset.py \
                    --ignore=tests/unit/test_scenario_builder.py
ruff check . --statistics
python scripts/smoke_perception.py
```

Observed results:

```text
bare pytest:            4 skipped, 3 errors in 1.14s  (Interrupted — 0 tests ran)
3 modules excluded:    71 failed, 444 passed, 17 skipped in 3.38s
plus -m "not ros2":    69 failed, 444 passed, 15 skipped, 4 deselected in 3.56s
ruff check .:          Found 167 errors.
smoke_perception.py:   swarm_perception smoke test passed
```

Failure distribution with the three uncollectable modules excluded:

| Test module | Failures | Root cause | Defect location |
|---|---|---|---|
| `test_aruco_parity.py` | 49 | A3 | Production code |
| `test_nav2_adapter.py` | 13 | A4 | Test fixture |
| `test_m6_scenarios.py` | 5 | Missing `rclpy` and unbuilt USD | Environment |
| `test_m6_config.py` | 1 | A7 | Test assertion |
| `test_m5_reasoning_pipeline.py` | 1 | A7 | Test assertion |
| `test_m5_congestion_detector.py` | 1 | A5 | Test construction |
| `test_openai_backend.py` | 1 | A6 | Undecided |

| Check | Expected | Actual |
|---|---|---|
| Python CI green at HEAD | `success` | `failure` at `ruff check .` — FAIL |
| Python CI ever green | at least one `success` in 28 runs | zero successes — FAIL |
| ROS2 CI green at HEAD | `success` | `success` — PASS |
| `pytest` collects cleanly | 0 collection errors | 3 collection errors, suite interrupted — FAIL |
| `ruff check .` clean | 0 errors | 167 errors — FAIL |
| `smoke_perception.py` exits 0 | exit 0 | exit 0 — PASS |
| M1 ArUco detection on installed OpenCV | ids decoded | `IndexError` on every call — FAIL |
| `-m "not ros2"` yields a clean run | 0 failures | 69 failures, 4 deselected — FAIL |
| No credentials in tracked files | none | none — PASS |
| No blocking calls in ROS2 callbacks | none | none — PASS |
| Runtime deps declared in `pyproject.toml` | all | 4 missing — FAIL |

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| A3 makes M1 unusable on any fresh install, and M1 feeds M2 and M5 | Apply the validated `reshape(-1)` fix and add a unit test covering both id shapes, independent of installed OpenCV |
| A1 and A2 together mean no regression is detectable | Fix collection first, then lint, so `pytest` begins running in CI; consider splitting lint and test into separate jobs so one cannot mask the other |
| A4's bypass pattern recurs at 16 sites and will rot again | Replace `__new__` bypass with a fixture stubbing only the ROS2 boundary |
| A8 admits further silent breaking upgrades | Add upper bounds for version-sensitive packages, starting with `opencv-contrib-python` |
| A5 leaves close-pair reset logic unverified while it is load-bearing for congestion detection | Rebuild the test so only the close-pair path can fire |
| Fixing 167 lint errors in bulk risks touching unrelated files | Use `ruff check --fix` for the 98 auto-fixable, then hand-review E501, E402, and B017 |

---

## Recommended Remediation Order

Ordered so each step makes the next one verifiable.

1. Guard the three `pxr` imports with `pytest.importorskip` (A2) — the suite becomes runnable.
2. Fix `detection.py:95` and add shape-independent coverage (A3) — M1 works; 49 tests recover.
3. Clear lint: `ruff check --fix`, then hand-fix E501, E402, B017 (A11) — CI reaches `pytest` for the first time.
4. Add dependency upper bounds and complete `pyproject.toml` (A8, A9).
5. Repair the `Nav2Adapter` fixture (A4), update the two stale assertions (A7), and re-isolate the close-pair test (A5).
6. Register the `isaac_sim` marker and guard the Isaac and `rclpy` tests (A10).
7. Settle the openai factory semantics, then align docstring and test (A6).
8. Documentation touch-ups (A12, A13).

Steps 1 through 4 and 6 are mechanical and verifiable against the suite. Step 5
is mechanical but requires care not to mask real behavior. Step 7 needs an owner
decision before any code changes.

---

## Dependency Changes

No new dependencies. A8 and A9 recommend constraining and completing existing
declarations, not adding packages.

---

## Sources Checked

- [OpenCV - ArUco marker detection docs](https://docs.opencv.org/4.x/d9/d6a/group__aruco.html) — `detectMarkers` return contract; version-sensitive between 4.x and 5.x. Installed version probed directly: `opencv-contrib-python 5.0.0.93`.
- [pytest - marker registration docs](https://docs.pytest.org/en/stable/how-to/mark.html) — custom markers must be registered in `[tool.pytest.ini_options] markers`.
- [pytest - importorskip API](https://docs.pytest.org/en/stable/reference/reference.html#pytest-importorskip) — module-level skip for optional imports.
- [Ruff - rules reference](https://docs.astral.sh/ruff/rules/) — rule codes cited in A11.
- GitHub Actions run history for `tuanhdangdinh/VLM-swarm-congestion`, workflows `python_ci.yml` (28 runs) and `ros_ci.yml`, including the failed job log for run 28.
- Repository sources at commit `0ad2a68`: `CLAUDE.md`, `docs/standards/coding_style.md`, `docs/standards/doc_style.md`, `docs/implementation_notes.md`.
