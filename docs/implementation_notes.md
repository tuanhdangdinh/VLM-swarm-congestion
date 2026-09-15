# Implementation Notes

**Prepared:** 2026-07-11

**Revision history:**

- Initial draft: living log created; seeded with verified notes from M1/M4/M6 work through 2026-07-08 and the congestion-reasoner program state.
- Rev 2 (2026-09-15): added a Repo Tooling & CI section for repository-wide findings that do not belong to a single module.

---

## Purpose and Maintenance Rules

This is the project's **living implementation log**: dated, append-only notes
recording decisions, verified fixes, gotchas, and open items that do not fit a
one-shot report. It complements — never replaces — the other document types:

- **Specs** (`docs/specs/`, `docs/superpowers/specs/`) define what to build.
- **Plans** (`docs/superpowers/plans/`) define how to build it, task by task.
- **Reports** (`docs/reports/`) are one-shot deep dives on a completed module
  or investigation (structure in `docs/standards/doc_style.md`).
- **This file** captures the connective tissue: "we learned X on date Y,
  evidence at Z" — the facts you need before touching a subsystem.

Rules for maintaining it:

- One bullet per note: `- **YYYY-MM-DD** — fact (pointer to commit, doc, or file).`
- Append under the matching module section, newest entry first. Do not rewrite
  or delete old entries; if a note is superseded, append the new fact and mark
  the old one `superseded by <date> entry`.
- Convert relative dates to absolute before writing.
- Link evidence (commit hash, spec, report, config file) instead of restating
  detail that lives elsewhere.
- Update the header revision history only for structural changes to this
  document, not for routine entries.

---

## Congestion-Resolution Experiment (research program: M2/M3/M5)

- **2026-07-11** — Phase 1 execution deliberately deferred. Prerequisites
  before data collection: commit the rev-8 spec + Phase 1 plan; fill the two
  REQUIRED pre-registration fields (primary `openai` `model_id` — blocked on
  API key — and secondary `llama_server` `model_id`); then tag `prereg-v1`.
- **2026-07-08** — Phase 1 implementation plan written:
  `docs/superpowers/plans/2026-07-08-congestion-reasoner-phase1-core.md`
  (15 TDD tasks, offline reasoning core + Arm B). Not yet executed. Key
  decision: `GroundingParams.mode` = `legacy` (default) / `derived`;
  `config/rag.yaml` stays `legacy` until Phase 2 flips the M5 call site, so
  the live loop is untouched by Phase 1. Planned phase split: 1 reasoning
  core, 2 M5/M1 integration, 3 M4 execution semantics, 4 scenario battery +
  oracle blocks, 5 harness + pre-registration freeze.
- **2026-07-08** — Spec rev 8 applied (external design review):
  `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`.
  Adds run matrix + statistical plan (paired-seed, N=30 pairs per T1 scenario
  with a one-time extension rule), full Arm B classical-reasoner
  specification with tuning-parity rule, T0 log-only negative probes,
  RQ1–RQ5 renaming (was H1–H5, collided with the "H3" run series),
  model/decoding pre-registration table, and rev-6 mechanism detail restored
  as Appendix A.
- **2026-07-08** — Open reconciliation item for the pre-registration freeze:
  the rev-8 model table pins temperature 0.0 (classification rule), but
  `ReasonerConfig` deliberately defaults to 0.6/0.95/20 because Cosmos
  Reason 2 is a chain-of-thought model that degrades at temperature 0.0
  (comment in `reasoning/vlm/models.py`). Resolution: 0.0 for non-CoT
  backends, model-card preset for CoT models, exact values recorded at
  freeze.

---

## M1 Perception

- **2026-09-15** — OpenCV 5.x returns `cv2.aruco.detectMarkers` ids as 1-D
  `(N,)`, not the 4.x `(N, 1)`, so `detection.py:95` raises `IndexError` on
  every detection and M1 is non-functional on a fresh install. Validated fix:
  `[int(i) for i in np.asarray(ids).reshape(-1)]`. Finding A3 in
  `docs/reports/2026-09-15-repo-audit.md`.
- **2026-07-03** — Colliding/overlapping ArUco markers make robots go STALE
  (marker lost), not STOPPED, which delays stall detection. Mitigation:
  `stale_after_sec` ≥ 3.0 and `velocity_alpha` ≈ 0.15 in the perception
  config for congestion scenarios.
- **2026-06-17** — Marker placement contract: the ArUco marker prim must live
  under `aruco_marker_link` (a `base_link` child inside the physics
  hierarchy), not under the robot root, or physics parses fail;
  `isaac/vgu_sim/validation.py` checks this and must be updated in sync with
  any marker-asset change (silent crash otherwise). See
  `docs/superpowers/specs/2026-06-17-aruco-markers-on-sim-robots-design.md`.

---

## M2 VLM / M5 Orchestrator Pipeline

- **2026-09-15** — `build_backend` substitutes a default `OpenAIBackendConfig()`
  when config is absent, while `llama_server` and `anthropic` raise; its own
  docstring and `test_openai_backend.py:131` both expect the raise. Open
  decision, not a mechanical fix. Finding A6 in
  `docs/reports/2026-09-15-repo-audit.md`.
- **2026-09-15** — The close/slow-pair reset in `congestion_detector.py:134-135`
  works, but its only test is confounded by the independent progress-stall path,
  so the reset itself has no passing coverage. Finding A5 in
  `docs/reports/2026-09-15-repo-audit.md`.
- **2026-07-05** — M6→M1→M5→M2 closed loop runs end-to-end on the GCP/Isaac
  host with the mock backend; the only remaining swap for live reasoning is
  `backend_id: openai`, blocked on an API key.
- **2026-06-15** — Offline input-encoding ablation harness spec:
  `docs/superpowers/specs/2026-06-15-m2-input-ablation-design.md`. Rev-8 of
  the congestion spec governs live-loop modality conditions; the 06-15 doc
  remains the spec for the offline benchmark runner and encoder seam.

---

## M4 Execution & Nav2

- **2026-09-15** — `scripts/run_phase3_demo.sh` still passes the superseded
  `x:=±0.6` spawn offsets to `nav2_robot.launch.py`, while the scenario it
  launches spawns at `±1.5` (changed in `0a0604c`, ~2h after the demo script
  landed in `35aad18`; the script has never been updated). Because
  `IsaacComputeOdometry` is spawn-relative, that static `map → odom` transform
  must equal the true spawn pose, so Nav2's `map` frame is displaced 0.9 m in x
  from the world frame M1 and M5 use: goals land 0.9 m short, the costmap
  misregisters by more than the 0.55 m corridor width, and M5 never sees goal
  completion. Fix by deriving spawns from the scenario YAML rather than
  restating them. Finding A15 in `docs/reports/2026-09-15-repo-audit.md`.
- **2026-09-15** — The `Nav2Adapter` test fixture bypasses `__init__` via
  `__new__` and hand-sets 3 of the 8 attributes it assigns, so all 13 tests fail
  on `_backup_timers`; production code is correct. The same bypass is used at 16
  sites across four test files and carries the same latent failure. Finding A4
  in `docs/reports/2026-09-15-repo-audit.md`.
- **2026-07-03** — Deadlock fix "H3" branch merged and verified (runs 8–13):
  separation and single-cycle resolution fixed; motion BVH requires the
  triple kit-arg. Open item at merge time: Nav2 pull-off recovery loop
  (superseded in design by the rev-8 derived-candidate retreat).
- **2026-07-02/03** — Backup-not-moving fix (commit `05ab38f`): robots stayed
  stationary despite backup COMPLETED because of a cancel-all race plus
  `collision_monitor` `stop_pub_timeout: 2.0` both zeroing `cmd_vel`.
  Odometry-based `backup()` then verified end-to-end on a fresh natural
  deadlock: 0.8 m backup + hold + yield complete.
- **2026-06-28** — Nav2 stall (M4 Phase 2 Task 8) resolved in `09778fa`:
  scan-namespace remap + DWB goal-tolerance fixes; clean rebuild reproduced
  goal reach at 0.0964 m.
- **2026-06-25** — Nav2 Jazzy parameter typing: integer parameters supplied
  as floats crash `bt_navigator` silently (`default_server_timeout: 60`
  works, `60.0` dies). Applies to all Nav2 YAML in
  `ros2_ws/src/swarm_simulation`.
- **2026-06-24** — M4 Phase 2 runs Nav2 in a `ros:jazzy` container with the
  Isaac side overridden to `ROS_DISTRO=jazzy`; transport/TF/map remap bugs
  from the pivot are confirmed fixed. See `docs/specs/module4/`.
- **2026-06-21** — Drive-chain fixed-base bug: the URDF importer's `fix_base`
  welded `base_link` to the world; freeing the chassis requires disabling
  the generated `base_joint`. Verified and landed (M4 Phase 1; report:
  `docs/reports/2026-06-21-m4-phase1-completion.md`).

---

## M6 Simulation / Isaac Sim

- **2026-09-15** — `tests/unit/test_m6_config.py:159` still asserts
  `effective_width_m == 0.4` although the corridor has been 0.55 m since
  2026-07-04 (commit `aa80d96`); the config is correct and the assertion is
  stale. Finding A7 in `docs/reports/2026-09-15-repo-audit.md`.
- **2026-07-04** — Aisle-width congestion gap closed: 0.55 m × 2.0 m
  `aisle_barrier` corridor built and verified in
  `isaac/config/scenarios/head_on_deadlock.yaml`.
- **2026-07-01** — Scenario YAML edits are inert until `build_scenario`
  regenerates the USD; a stale USD cost ~10 debugging runs. Always rebuild
  after editing anything under `isaac/config/scenarios/`.
- **2026-06-30** — Host-launched Isaac needs
  `FASTRTPS_DEFAULT_PROFILES_FILE` forcing UDP transport; otherwise
  shared-memory transport silently drops all data to the Nav2 container and
  the system looks hung.
- **2026-06-21** — Fabric/USD sync for Newton articulations: enable
  `enable_fabric_usd_notice_handler` and write world positions to Fabric
  after each step; `omni.physx.fabric` does **not** work for Newton
  articulations (report:
  `docs/reports/2026-06-21-m6-fabric-sync-investigation.md`).
- **2026-06-18** — The Isaac Sim machine is Windows: guides and commands for
  that host use PowerShell and `python.bat` (see `docs/guides/`).

---

## Repo Tooling & CI

- **2026-09-15** — Python CI has never passed: all 28 `python_ci.yml` runs from
  2026-06-05 to 2026-07-13 failed at `ruff check .` (167 errors), which runs
  before the `pytest` step, so the suite has never executed in CI. Full audit:
  `docs/reports/2026-09-15-repo-audit.md`.
- **2026-09-15** — Bare `pytest` aborts during collection: three test modules
  import `pxr` without `pytest.importorskip`, giving `Interrupted: 3 errors` and
  zero tests run. Sibling USD tests already use the guard. Finding A2.
- **2026-09-15** — The `-m "not ros2"` escape hatch advertised in
  `pyproject.toml` does not restore a clean run (deselects 4, leaves 69
  failures), and `isaac_sim` is used as a marker at 7 sites without being
  registered; environment-dependent tests need `importorskip`, not just a
  marker. Finding A10.
- **2026-09-15** — Dependency declarations are unpinned and incomplete:
  `opencv-contrib-python>=4.8` admitted the OpenCV 5 break behind finding A3,
  and `pyproject.toml` omits `numpy`, `opencv-contrib-python`, `Pillow`, and
  `requests` although runtime code imports all four. Findings A8, A9.
