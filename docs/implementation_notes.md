# Implementation Notes

**Prepared:** 2026-07-11

**Revision history:**

- Initial draft: living log created; seeded with verified notes from M1/M4/M6 work through 2026-07-08 and the congestion-reasoner program state.

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

- **2026-10-04** — **Capability-probe battery run live, once per backend;
  model pin wired (step-10 follow-up (a))**
  (`docs/reports/2026-10-04-capability-probe-results.md`).
  These are the pre-collection baseline runs the v2 freeze cites (manifest
  `9659782d…`, prompt v1 template `b1af71e8…`).
  - **Pin wiring (`7ba1170`):** `scripts/capability_probes.py` now resolves
    `openai`/`gemini` from `config/models.yaml`, using the
    `probe_presentation_order` precedent.
    - Temperature is forced to 0.0.
    - Each item gets one `analyze` call. The reasoner's re-ask and
      grey-image fallback are deliberately not applied.
    - Every record carries the configured model and the served model.
  - **Served models:** `gpt-4o-2024-08-06` ×60 and
    `gemini-robotics-er-2-preview` ×60.
  - **Frames:** all 60 re-materialized hash-clean from the main checkout's
    `data/logs/vm_runs` (audit `OK`).
  - **Gemini ER-2:** 60/60, i.e. 15/15 on every type.
  - **gpt-4o:** 58/60. It scored 15/15 on every type except `left_right`,
    where it got 13/15 [0.62, 0.96].
    - Both misses are near the centre line (margins 0.46 m and 0.64 m).
    - Both answers were letter A, listed first.
  - **gpt-4o refused 0/60 times on real annotated frames**, against the
    19–38% recorded on the congestion prompt. The task text and the frame
    distribution changed together, so the cause is not identified.
  - **`nearest_first` priors:** 0/8 robot_1 picks where robot_1 was wrong,
    and 5/5 correct where the first-listed option was wrong. Follow-up (c)
    is answered for this battery.
  - **Ceiling:** at n=15 a perfect score's Wilson lower bound is 0.796, so
    the battery cannot rank the backends.
  - **LRR-Bench:** checked against the paper's Tables II and III. Its
    near-chance and near-zero results are on the composite-position and 3D
    movement tasks. On basic Position, GPT-4o scores 78–80 against 95 for
    humans. The spec's "left/right near chance" wording should be fixed at
    freeze, and the research note's "55.33%" figure is absent from the v1
    HTML.
  - **Spend:** about $0.25 total.
  - **Results JSONL** (gitignored):
    `data/logs/capability_probes/{gemini_20261003T201320Z,openai_20261003T201935Z}/`.
  - **Still open:** follow-up (b), the owner confirming the left/right
    operationalization.

- **2026-10-03** — **The χ-epsilon and grammar rulings are implemented
  (report Rev 2, `docs/reports/2026-10-03-plan-grammar-fixes.md`).**
  - **χ-epsilon rule (`b176e56`):** option (b), with
    `GroundingParams.junction_recede_order_epsilon = 0.15`.
    - Verification only: a within-ε recede order is no reorder problem,
      while the recede-SET audit stays strict and dispatch stays in χ
      order.
    - `junction_clear_plan_matches_dispatch` is replaced by the
      order-aware `junction_clear_dispatch_match` → `JunctionDispatchMatch
      {matches, order_equivalent}`. `PlanDispatchInfo.order_equivalent`
      is now in every artifact's `plan` block.
  - **Repair bound RE-FROZEN AT 4** (supersedes the step-7b freeze at 3,
    same procedure). `recede_order_swapped` left the sweep corpus, and the
    two depth-5 cases are now depth 4. m3_default at bounds 1/2/3/4 is
    9/5/3/0 over 13 repairable cases.
  - **Prompt re-pinned to v3.2 (`9bb6780`).** The decision-field agreement
    rule rides the `"yield"` rule line, since
    `_plan_disagrees_with_decision_fields` is yield-only. The convoy gloss
    adds "while an opposing robot gives way". Baseline pin `c3fb9fcf…`;
    the live calibration ran on v3.1 (`42463ce2…`).
  - **Mirrored-axis composite caveat** recorded as in the spec; no code
    change.
  - **Apparatus gotchas from the calibration run:**
    - The v2 driver's `GATE OK` also fires on a Nav2-abort cleanup
      (`logs saved to` is printed on the failure path), so it is not proof
      of a run.
    - A failed early run leaves Isaac alive for more than 12 min (it
      simulates out its 300 sim-s at 0.27 RTF), longer than the 231–356 s
      cleanup-survival figure. The next launch's 420 s guard refuses;
      kill by PID and confirm the GPU is idle.
  - Suite: 63 / 4581 / 152 against a baseline of 63 / 4551 / 152; the
    failing set is identical.

- **2026-10-03** — **VLM-planning review fixes: prompt v3.1 plan grammar
  + emission/consistency metric split landed; χ-epsilon rule STOPPED for
  a ruling; live ER-2 calibration on IB10 PASSES 4/4 and the plan shape
  changed.** Branch `feat/v2-plan-grammar` (from
  `feat/prereg-v2-composite` at `af7cec5`). Full report:
  `docs/reports/2026-10-03-plan-grammar-fixes.md`.
  - **v3.1 (`13d7392`):** a static `_PLAN_GRAMMAR` block (action meanings
    + the `_is_consistent` rules) and a gloss for all eight strategy
    tokens. Re-pinned in place under `prompt_version=3`; artifacts are
    told apart by `user_sha256` (v3.0 baseline `22baf2df…`, v3.1
    `42463ce2…`). v1/v2 pins are unchanged.
  - **Metric split (`7bf4e89`):** `emitted` = parseable; new
    `consistent`. Oracle-order agreement stays gated on consistency. Old
    artifacts score by recomputation.
  - **Gotcha — the χ order "flips" are jam-formation asymmetry, not
    snapshot timing** (supersedes the "snapshot-timing dependent" reading
    in the next entry). Settled-margin noise within a run is ≤ 5 mm;
    margins between runs range from −0.142 to +0.049 m in a scene that is
    symmetric by design.
  - **Gotcha — ε on the recede-order audit reopens freeze-blocker 1.**
    Dispatch is grounded from the raw decision, before verification,
    always in χ order, and `junction_clear_plan_matches_dispatch` ignores
    order.
  - **Gotcha — ε ≥ 0.02 m changes the bound freeze.** It drops two
    depth-5 sweep cases to depth 4, so bound 4 reaches full coverage.
  - **Calibration (`fc_run_20261003_154833`):** ER-2 proposed its first
    recede legs: `reverse` for robot_1/robot_2 (the E-W axis), `cross`
    for robot_3/robot_4. The plan was consistent and `repaired` at
    exactly bound 3. The outcome was 4/4, `outcome_rank` (1, 4, 4),
    yielder last. With χ tied (0.939/0.939), a 0.01 m flip would have
    made the same plan `m3_default`. Bundle:
    `data/logs/vm_runs/plan_grammar_cal/` (gitignored).
  - **Apparatus gotchas:**
    - The driver's `GATE OK` also fires on a Nav2-bringup abort, because
      `logs saved to` is printed on the failure path.
    - An aborted early run leaves Isaac simulating its full 300 sim-s
      (more than 12 min), so the next launch's 420 s guard refuses.
      Kill it by PID and confirm the GPU is idle.
  - Suite: 63 / 4565 / 152 against a baseline of 63 / 4551 / 152; the
    failing set is identical.

- **2026-10-03** — **v2 demo episodes recorded on IB10 (scripted 4/4 +
  LIVE ER-2 4/4), with four apparatus gotchas.** Runs
  `fc_run_20261003_062051` (scripted) and `fc_run_20261003_064912`
  (live, `gemini-robotics-er-2-preview`, prompt v3, plan channel on):
  both resolved 4/4 with yielder-last attribution; the live model chose
  `junction_clear` unprompted, its own plan (one `cross` + three
  `wait`s, no receders) was rejected as inconsistent → `m3_default`
  (first live datum for the plan-emission metrics); videos + scorer
  outputs under `data/logs/vm_runs/v2_demo/` (gitignored). Gotchas for
  future runs: (1) `intersection_bottleneck.yaml` `duration_sec: 300`
  governs — `run_simulation` never applies `--duration-sec`, so
  `SIM_SEC` beyond 300 sim-s only records idle frames; (2) with four
  Nav2 stacks `/perception/annotated_frame` drops to ~1.0–1.9 fps (vs
  6–7 Hz pre-Nav2), and the recorder's literal frames÷seconds
  re-timing recipe overstates duration when the recorder outlives
  Isaac — re-time from the last recorder progress line inside the
  Isaac-active window; (3) IB10's χ order flips between runs
  ([robot_4, robot_3] in the 7b rerun vs [robot_3, robot_4] in both
  demo runs — snapshot-timing dependent; superseded by 2026-10-03
  plan-grammar entry: between-run jam-formation asymmetry), so the
  `intersection_junction_clear_vlm_verbatim_once.json` mock can score
  `repaired` instead of `vlm_verbatim`; any fixture pinning verbatim
  provenance must derive the recede order from the live snapshot, not
  hardcode it; (4) the bracketed `pgrep '[r]un_simulation'` guard is
  defeated by any concurrent command line containing the bare string —
  keep the literal out of every SSH command.

- **2026-10-03** — **v2 build-order step 8 phase 2 (loop-detour family)
  STOPS on a design-control failure; step-9 visual pass PASSES.** Branch
  `feat/v2-final-wave` (from `feat/prereg-v2-composite` at `1ee23d2`); full
  report `docs/reports/2026-10-03-loop-family-and-visual-pass.md`.
  - **Built:** M3 reroute grounding to declared far-aisle waypoints
    (`SceneGeometry.reroute_waypoints`, None = byte-identical `waypoints:
    []`). Also built: `loop_detour_{permanent,transient}` (one factor, two
    cells; the minimal loop has one detour length), the
    `LoopDetourOracleConfig`/`LoopDetourCostRecord` oracle,
    `coverage_scene_scores.py loop`/`loop-cost`, the regret arms, and the VM
    drivers (`scripts/vm/v2_final_run.sh`, `v2_overlay.py`,
    `loop_family_sampler.py`, `frame_snapshots.py`).
  - **STOP (gotcha):** a 0.22 m blocker gap stops robot_1 by the
    collision monitor's 0.24 m stop box, but NavFn prefers the loop. In
    3 of 3 runs every global plan from the second sample (11.7–13.6 s) went
    round the loop, and robot_1 left the primary aisle at about 25 s,
    before any dispatch. The mechanism is only PARTLY characterized:
    - Contributing factor: lidar box marks plus the global inflation band
      make the gap high-cost. A standalone NavFn sweep flips at a 0.22 m
      gap and not at 0.30 m.
    - Unexplained: at sim 54.8 the live grid had no sensor marks and a
      zero-cost pinch centre, yet the live planner still planned the loop.
    Evidence: `data/logs/vm_runs/loop_family/navfn_sweep/`. Phase 1's PASS
    (0.55 m gap, no stall) does not carry over to a stalling blocker.
  - **Loop drivability:** Nav2's own detour completed once and wedged once
    at the second-aisle mouth (0.3 m remnant corner). The declared reroute
    (the first live `follow_waypoints`) stalled 0.3 m from waypoint 1 and
    failed by watchdog. It is not root-caused, so its live M4 path is
    unvalidated.
  - **Tracked faulted robot:** infeasible as a transient blocker. The M4
    pair latch (0.45 m) fires before the collision monitor can stop
    robot_1 (≤ 0.38 m reach), and it is permanent. The authored transient
    cell uses T3a's untracked visual instead (deviation, for a ruling).
  - **Not collected:** no cost table; transient dwell provisional and
    unregistered; both yamls carry a STATUS "do not collect" block.
    Coordinator options are listed in the report.
  - **Visual pass:** B2-visual and B3-slip USDs built and validated. The
    load prop is visible and never covers the marker (spawn, standoff,
    goal). The loaded robot is 100% fresh in both members (the empty
    robot_1 in r2 was 99.55%, a 2-row blip). A/B diff:
    0 pixels changed in the marker window. Maps are byte-identical. `b3`
    on a real GT log gives first_slipper robot_1, latency 28.6 s,
    consistent with GT.
  - **Flagged:** live Arm B shadow yielder differs from the registered
    `classical_yielder` in r1. The B3 goal-stack latch recurred at
    0.4448 m (censoring valve). Suite: 63 / 4551 / 152 vs baseline
    63 / 4490 / 152 at `1ee23d2`, identical failing set.

- **2026-10-03** — **Step 7b closed: STEP-7b RULINGS (vi)/(vii) landed and
  the IB10 mock rerun PASSES 4/4** (supersedes the "STOP for a ruling" in
  the next entry). Report: `docs/reports/2026-10-03-step7b-oracle-freeze.md`
  (Rev 2). (vi) The release `yield` of the yielder now carries
  `crossing_order` [lead, *receders] with `crossing_clear_m` [lead pocket +
  second pocket + `min_distance_m`, receder pocket + `corridor.half_length_m`
  + `min_distance_m`] (IB10: [2.65, 2.05]) and twice the receders' backstop,
  so M4's ordered multi-passer path frees it only after the last receder
  clears (`589aeb3`, M3 only). **Gotcha / deviation from the ruling text:**
  the second receder keeps its lead-gated passive `yield` instead of a
  linked `temporary_wait`. `safety.admitted_partners` gives a
  `temporary_wait` no partners, and the unaddressed lead never COMPLETEs,
  so the literal structure loses the lead/receder exemption the lead needs
  to squeeze past (0.248-0.34 m measured). (vii) `outcome_rank` = (all
  arrived, phase ordinal, arrivals) plus `release_attribution`'s
  `yielder_last` (`4d7ee48`). Rerun `fc_run_20261003_030944` (code
  `4d7ee48`): 4/4, every release `reason=clearance`, yielder `gate_release`
  at sim 185.800 after robot_3's at 153.667, in band, STALE max 1 row,
  `outcome_rank` (1, 4, 4). Suite 63 failed / 4490 passed vs baseline 63 /
  4416, failing-name set identical.
- **2026-10-03** — **v2 build-order step 7b: rulings (i)-(v) landed, IB10
  scoring frozen, IB10 mock rerun FAILS 2/4 on a new design-level
  release-sequencing finding (STOP for a ruling).** Branch
  `feat/v2-step7b` (from `feat/prereg-v2-composite` at `cf368ec`); full
  report `docs/reports/2026-10-03-step7b-oracle-freeze.md`. (ii) Repair
  bound re-swept 1-4 on the 18-case corpus, frozen at **3** (no bound
  reaches full coverage; documented m3_default tail: two depth-5 cases plus
  `missing_both_recede_candidates`), `8071f8a`. (iv) Attempt-3's 82 s
  streak was a race artifact (robot_3/robot_4 0.076-0.144 m apart on the
  same arm). The race-free endgame (predecessor rerun, `cdf18b5`) exposed
  the real pocket problem: the lead parks at its goal 0.45 m behind the
  second receder's 1.2 m pocket and latches (3/4). Fix: new
  `SceneGeometry.junction_recede_stagger_m` (k-th chi candidate recedes to
  `offset - k * stagger`, assigned after ranking; release clearance = lead +
  second pocket + `min_distance_m`); IB10 declares 0.2, so the second pocket
  sits at 1.0 m (window [1.0, 1.05] from the 0.6 m STALE band and the S1
  yielder-return bound), `7070813`. Part 3: `JunctionOracleConfig` +
  IB10 `oracle:` block + `coverage_scene_scores.py ib10` (`aefbecb`), regret
  arms `junction_clear` vs censored `best_single_yield` (`062cd21`). Rerun
  `fc_run_20261003_022532` (code `7070813`, manifest-verified): valid jam,
  chi pair and order correct, inside-first, phase `resolved`, release
  attributable (`gate_release ... reason=clearance sim_t=139.967` for both
  held robots), no band excursion, no STALE streak (max 5 rows), but
  **2/4**. The release frees the second receder (robot_3, northbound) and
  the yielder (robot_1, eastbound) on the same gate at the same instant;
  their paths cross and they latch for good 3 s later at 0.416 m. The
  spec's "the yielder re-enters last" is not implemented relative to the
  second receder. The candidate fix (chain the yielder behind the second
  receder, M3-only) is NOT applied and awaits a ruling. Suite: baseline 63
  failed / 4416 passed, branch 63 / 4472, failing-name set identical.

- **2026-10-02** — **v2 build-order step 7a: five IB10 freeze-blocker fixes
  landed (branch `feat/v2-blockers`, from `feat/prereg-v2-composite` at
  `d3aa0f3`), full report `docs/reports/2026-10-02-step7a-blocker-fixes.md`.**
  (1) **Recede-set membership/order audit** (`command_grounder.
  _plan_problems`): a `junction_clear` plan naming the wrong recede pair, or
  the right pair in the wrong relative order, no longer verifies
  `vlm_verbatim` — closes the step-6 sweep's metric hole and run B's live
  order bug. Re-run sweep (18 cases, +1 new order-only case): `max_repair_
  edits=2` no longer covers every repairable case (now 7/14 = 50%, down
  from 100% pre-fix) — membership defects cost 2-5 edits under the shipped
  `yield_feasibility_mode="off"` (no cheap yield-touching swap available),
  while the pure order defect costs exactly 1 (a `reorder`). Flagged as a
  NEW freeze-relevant finding for the coordinator (raise the bound for
  `junction_clear`? accept `m3_default` for severe cases? — not decided
  here). (2) **Staggered post-composite release**
  (`ground_junction_clear_phases` gains a trailing `"release"` phase, 2+
  recede candidates only): the chi-lead recede candidate is released
  immediately; every other recede candidate plus the yielder are held via
  a plain `yield` naming the lead as `passer_robot_id`, reusing M4's
  existing odometry-gated `CrossingChain` UNCHANGED (never a fixed timer).
  Clearance is geometry-derived (`2 * junction_recede_offset_m + min_
  distance_m`), not a constant. (3) **Cross-command continue-vs-reverse
  exemption** (M4-adjacent; see the protocol note immediately below).
  (4) **Reverse tracked-band clamp**: new `SceneGeometry.tracked_extent_m`
  (None default, byte-identical without it); a plain `reverse` leg's backup
  distance is clamped so a robot's post-backup progress along its own
  declared arm never exceeds it — pinned against both live episodes'
  overshoot numbers (2.38/2.42 m, both would now stop at 1.75 m). (5)
  **Fallback-exhaustion semantics**: new terminal `PlanLegStatus`
  `"exhausted"`, written by a new `orchestrator_node._mark_fallback_
  exhausted` when a `junction_clear` fallback's own resolution is itself a
  failure (not just an earlier phase's) — logs loudly
  (`outcome=fallback_exhausted`), and permanently folds the affected robots
  into the trigger-suppression gate (`_exhausted_robots`, unioned into
  `cooldown_robots`) so M5 stops re-dispatching an already-exhausted
  conflict. `plan_metrics.any_leg_exhausted` is the scoring-side building
  block. Confirmed the phase QUEUE itself already terminates correctly on a
  failed fallback (`done=True` unconditionally, never retried) — the
  re-trigger source this fix actually had to stop was M5's OWN congestion
  detector re-firing on the still-stalled robots, not the phase queue.
  Local suite zero-delta (`d3aa0f3` baseline, byte-identical failing-test-
  name set): 63 failed / 4384 passed / 152 skipped / 3 collection errors
  before, 63 failed / 4412 passed / 152 skipped / 3 errors after (+28 new/
  renamed pins). `ruff check` clean on every touched file.
  **VM mock verification (first two attempts) and their "0/4, design-level
  finding" framing: SUPERSEDED, see the correction entry immediately
  below** — the real cause was this task's own bug (the release action's
  `yield` parameters), not an M4/design limitation. First VM attempt was
  truncated by an under-sized `REC_SEC` relative to the measured real-time
  factor (~0.27-0.31, not close to 1x even for a zero-latency mock run) —
  the SAME RTF-miscalibration trap the composite-smoke report's own live
  episodes hit; treated under the standing one-re-run allowance (still
  accurate, unaffected by the correction below). The Isaac-survival
  `pgrep` gate caught a REAL leftover on both of the first two attempts —
  the host Isaac process outlived `fc-launch`'s own "killing Isaac" cleanup
  line by 10+ minutes each time, consuming GPU the whole time; killed by
  hand both times, confirmed gone before proceeding (still accurate).

- **2026-10-02** — **CORRECTION (same task, step 7a): the VM's "0/4,
  design-level finding" was this task's own implementation bug in fix 2,
  not an M4/design limitation — found by advisor review, fixed, and
  re-verified: 4/4.** The release phase's `yield` action (fix 2) carried
  only `passer_robot_id`/`passer_clear_m`, on the wrong assumption that a
  `yield` with no backup/pull-off parameters is a passive hold.
  `command_bus_node`'s `yield`/`reverse` branch unconditionally runs
  `Nav2Adapter.backup(robot_id, params.get("backup_distance_m", 0.3), ...)`
  FIRST (an unrequested 0.3 m backup on an already-parked robot), and
  `hold_sec = params.get("hold_sec", 0.0)` — left unset, `_on_backup_
  result` never calls `_start_hold` at all, so the `CrossingChain`/
  odometry-gated wait this fix exists to reuse never engaged; the command
  just completed ~35 s after the unrequested backup, with no relation to
  the lead's real clearance. That is what the second VM attempt's 0/4 and
  the persistent `min_pairwise_distance_m=0.118` cluster actually were —
  not a 120 s backstop (the release resolved in 35 s, not 120), not M4's
  `reverse` execution going the wrong way. Fixed: `"backup_distance_m":
  0.0` (completes on the first odometry tick, no real motion) and
  `"hold_sec": params.junction_recede_hold_sec` (now a genuine backstop
  behind the real `CrossingChain` wait, not instead of it). Pinned:
  `test_release_phase_actions_are_a_passive_hold_not_a_maneuver`. Re-ran
  locally (zero-delta maintained) and on the VM (third attempt, same
  `REC_SEC=1050`/`SIM_SEC=1100`): full phase sequence, no fallback, **4/4
  arrivals** (`ArrivalGate`: robot_2 0.06 m, robot_4 0.07 m, robot_3
  0.06 m, robot_1 0.08 m, all `within_tolerance`), jam-forms-first
  confirmed from GT (all four stopped within 1 m of centre by sim 28.0 s,
  before the 34.3 s trigger), no tracked-band excursion (every robot's max
  `|x|`/`|y|` is its own goal coordinate). Isaac exited cleanly on its own
  this time (no leftover process). **New STALE finding, flagged per the
  registered instrumentation rule, run NOT invalidated**: `robot_3`/
  `robot_4` each showed a 275-row (~82 s) STALE streak, sim 101.2-183.2 s —
  materially longer than any prior recorded streak (previous max 26 rows) —
  coincident with the two recede candidates parked 0.08-0.15 m apart (see
  the characteristic noted above). No overlap with the trigger snapshot or
  either robot's own arrival, so it does not invalidate this run per the
  resolved gate's ruling, but it is a new, larger data point for whether
  the registered 1.65 m spawn-re-radius fallback should now be considered
  — an owner call, not applied here. VM restored pristine
  (`1f656533`/`e18c723`, all four copies, re-verified after each of the
  three attempts), GPU idle, no stray processes, this task's own `/tmp`
  artifacts removed. Full report (superseding its own first-draft VM
  section in place, per its own revision history):
  `docs/reports/2026-10-02-step7a-blocker-fixes.md`.

- **2026-10-02** — **SECOND CORRECTION (same task, step 7a, same attempt-3
  run, no further VM run needed): the entry above's "4/4" is real, but its
  "ordered release" claim is not — the correct, final design-level
  finding.** A second advisor-review pass on the SAME attempt-3 logs
  (`/tmp/fc_20261002_160626_m4.log`, the run's own GT) found that the
  release resolved via its sim-clock HOLD-TIMER backstop
  (`hold_sec=junction_recede_hold_sec=120`, consumed by `create_timer`,
  which runs on the node clock — i.e. sim time under this project's
  standing `use_sim_time`, NOT wall time: 452 observed wall-s at this
  run's own measured RTF ~0.27 is ~122 sim-s, matching `hold_sec` almost
  exactly), not via the `CrossingChain`'s real clearance tracking — which
  could never have fired, because GT shows the release's own lead
  (`robot_3`, ranked[0]) staying at speed 0.00-0.04 m/s for the entire
  sim 100-180 s window, never approaching the required 2.85 m of
  displacement. Worse: `robot_4`, one of the TWO robots the release is
  supposed to hold until that clearance, independently reached its own
  goal (arrived at wall 1790958022, BEFORE the release's own COMPLETED at
  1790958039) — `m4.log` shows `resume base mission robot=robot_4
  goal=(0.0, -1.75)` firing at wall 1790957587.891, the SAME instant the
  cross phase resolves and the release command is dispatched. A robot
  genuinely held by a `yield` cannot independently drive ~3 m to its own
  goal; `robot_4` escaped through `BaseMissionDriver`'s own resume path,
  not through anything fix 2 dispatched. **Root cause, and why it also
  explains the same-side recede placement this task's first two VM
  attempts both observed without correctly attributing it**:
  `CoordinationTracker`'s own module docstring states "Commands and
  statuses arrive on separate topics with no cross-topic ordering
  guarantee" — `BaseMissionDriver` (a SEPARATE node, `coordination_
  client_node.py`) resumes a robot's base mission on the terminal status
  of whichever command currently owns it, and a LATER phase's new
  command is not guaranteed to land before that resume fires;
  `m4.log` shows this same race firing for `robot_3` itself six times
  across the run, at every phase boundary it is held through, which is
  the actual mechanism that put the two recede candidates on the same
  side in the first place (not an M4 `reverse`-execution anomaly, as an
  earlier, now-corrected reading of this same evidence guessed). This one
  pre-existing M4 mechanism produced the same-side placement, let a held
  robot leave early, and made the clearance target unreachable — it is a
  property of the message contract between `command_bus_node` and
  `coordination_client_node`, not of fix 2's own phase-level machinery
  (the new `release` phase, its triggering, and the geometry-derived
  clearance distance are implemented exactly as specified and are
  confirmed NOT to be what failed). Fixing it is a change to
  `BaseMissionDriver`/`command_bus_node` or the status-ordering contract
  between them, out of this task's scope — **the design-level finding for
  the coordinator**, per the task's own framing. No VM state changed by
  this correction (same attempt-3 artifacts, re-read, not re-run); the
  restore/cleanup already recorded above stands. Full report corrected in
  place, per its own revision history:
  `docs/reports/2026-10-02-step7a-blocker-fixes.md`.

- **2026-10-02** — **THIRD CORRECTION (same task, step 7a): two more
  factual errors in the entry above, from a third advisor-review pass on
  the SAME attempt-3 logs (no further VM run); plus a real bug found and
  fixed in fix 3 (separate from the VM finding).** (1) The race direction
  above is backwards. `BaseMissionDriver.on_command` (`base_mission.py`)
  deliberately does nothing when a robot is ALREADY suppressed, so a
  SUCCESSOR command (the release's own `yield` for `robot_4`) reaching
  `coordination_client_node` BEFORE it has processed the PREDECESSOR
  phase's terminal status for that robot is IGNORED, not a transient win
  -- the predecessor's terminal, processed moments later, then frees the
  robot PERMANENTLY (no retry). The "six times" count is also wrong:
  `resume base mission` fires once per `_desired()` call per status
  event, including re-issues of a goal not yet Nav2-accepted, not one
  race per line. (2) `robot_3`/`robot_4`'s long stall during the
  close-parked dwell is NOT a safety-latch effect: `m4.log` shows ZERO
  `safety stop robot=robot_3`/`robot=robot_4` lines anywhere in the
  release's own 452 s window -- `safety_monitor_node: exempt pairs
  changed pairs=robot_1+robot_3,robot_3+robot_4` (wall 1790957587.948)
  confirms the release's own `yield` actions (naming `robot_3` as
  `passer_robot_id`) make `robot_1`/`robot_4` EACH exempt against
  `robot_3` -- the EXISTING exemption machinery working exactly as
  designed. `robot_3`'s own stall shows up instead as repeated `cancel-all
  robot=robot_3 action=navigate_to_pose ... goals_canceling=1` lines, a
  separate Nav2-level goal-churn effect not traced to its own root cause
  (out of this task's scope). The 452 s / ~120 sim-s timer-match claim is
  weakened accordingly: this run's own RTF was never separately computed
  (the ~0.27 figure cited was historical, not measured for THIS run), so
  the "timer, not clearance" conclusion rests on the lead's own speed
  (0.00-0.04 m/s for the whole window -- 2.85 m of displacement could not
  have happened regardless of timing), not on the RTF arithmetic. (3)
  **Separately, fix 3's OWN first draft was found to be a blanket
  exemption in real dispatch** (`orchestrator_node._with_plan_continue_
  partners`): plans are scene-wide, so EVERY tracked robot a decision
  omits becomes a `continue` leg, and `PlanTracker.accept_plan` tracks
  `m3_default` plans too ("every executed resolution has a plan") -- so
  naming every `continue` leg of the tracked plan, as shipped, named
  every OTHER robot in the WHOLE SCENE as exempt against any `reverse`,
  violating the task's own "do NOT blanket-exempt" instruction. Fixed:
  narrowed to `_last_trigger_robot_ids`, the ORIGINAL congestion event's
  own robot set, captured once per fresh analysis (`_handle_outcome`,
  just before `_dispatch`) from data the pipeline already computes
  (`CongestionEvent.involved_robots`) -- no new computation, a new
  `frozenset` instance attribute only. Episode 1 decision 2's own shape is
  now pinned directly: `robot_1` (part of the triggering event) stays
  exempt, `robot_2` (never part of it) does not. Local suite zero-delta
  maintained (byte-identical failing-test-name set to the `d3aa0f3`
  baseline) through all three corrections; `ruff check` clean. Fix 3's own
  section, its pins, and the M4 protocol note are all updated in the
  report to the narrowed version; this note documents the mistake and the
  fix, per the maintenance rule, rather than rewriting the first SAFETY
  fix-3 note above it. `docs/reports/2026-10-02-step7a-blocker-fixes.md`
  carries the corrected sections.

- **2026-10-02** — **FOURTH CORRECTION (same task, step 7a): the THIRD
  CORRECTION entry above made a factual error of its own, and separately
  dropped a sentence from the SECOND CORRECTION entry it was appended
  after — both found on a further advisor-review pass, SAME attempt-3
  logs/GT, no further VM run; plus a real, cheap fix landed for a
  disclosure this entry found, below.** (1) **Factual error, same
  mechanism as the earlier ones: a speed range read too coarsely.** The
  THIRD CORRECTION's point (2) says the lead's speed is "0.00-0.04 m/s
  for the whole window -- 2.85 m of displacement could not have happened
  regardless of timing." A precise GT read (every row, not a coarse
  sample) over the release's own window — computed from this run's OWN
  measured RTF (`(253.57-30.73) sim-s / 836.49 wall-s = 0.2664`, not the
  historical ~0.27 figure), giving sim 94.9-215.4 for wall
  `ACTIVE`/`COMPLETED` `1790957587.49`/`1790958039.44` — shows `robot_3`
  near-stationary (0.00-0.04 m/s) only through sim ~100-195 s, THEN
  moving at 0.15-0.17 m/s for the final ~20 s, reaching a straight-line
  displacement of **2.90 m from window start to window end — just OVER,
  not under, the 2.85 m `passer_clear_m` threshold**. Whether
  `CrossingChain`'s own tracked "moved" value (measured from the passer's
  first post-admission odometry sample, not necessarily this window's
  exact start) crossed 2.85 m before or after the ~120.5 s window closed
  cannot be distinguished from the logs alone — genuinely AMBIGUOUS, not
  "could not have happened regardless of timing" as THIRD CORRECTION
  claimed. The report's finding 1 and its "Ordered secondary release" /
  "Safety during the close-parked window" table rows are corrected to
  this ambiguous framing (not VM-re-verified; a re-read of the same
  artifacts). This also affects attribution: in THIS run (attempt 3) it
  is `robot_4` — not `robot_3`, as attempt 2 showed (attempt 1 never
  reached the release phase, so it contributes no data point here) —
  that ends up parked on the other robot's declared side, which is
  CONSISTENT WITH a race-order-dependent mechanism, not proof of one with
  only two data points. (2) **Append-only violation, self-caught:
  restoring a dropped sentence.** When THIRD CORRECTION was appended
  after it (commit `819bf65`), the SECOND CORRECTION entry immediately
  above it was edited to drop its own closing sentence instead of being
  left untouched, losing this fact: GT's own `robot_robot_contacts` field
  recorded no physical contact at any point in the run, including the
  0.0761 m minimum-separation row at sim 106.1 s, despite 14,910
  safety-monitor `min_distance_violation` log lines over the whole run
  (not traced further to which specific pairs produced each line).
  Restated here per the append-only rule rather than re-editing SECOND
  CORRECTION again. (3) **Disclosures: one fixed, two left open (out of
  this task's five-fix scope).** (a) **Fixed**: fix 3's trigger-set
  narrowing (`_last_trigger_robot_ids`) was correct for the
  detector-driven path, but `orchestrator_node._on_trigger_analysis` (the
  operator/test manual-trigger RPC) built its own `CongestionEvent.
  involved_robots` from EVERY robot in the latest snapshot, not the
  actual conflict set — so a `reverse` dispatched after a
  manually-triggered analysis still got a scene-wide `plan_continue_
  partners` set, i.e. an instance of the exact blanket-exemption pattern
  fix 3 exists to remove, on this one path. Fixed by giving
  `_submit_pipeline` a `trigger_robots: frozenset[str] | None = None`
  parameter that `_on_trigger_analysis` passes as `frozenset()` (fails
  closed to v1/no-narrowing behavior on the manual path, rather than
  scene-wide); the detector-driven call site is unchanged (passes
  `None`, preserving the real trigger set). Pinned:
  `test_manual_trigger_reverse_gets_no_plan_continue_partners`. Local
  suite zero-delta maintained (byte-identical failing-test-name set to
  the `d3aa0f3` baseline, main-repo `.venv`); `ruff check` clean. (b)
  **Still open**: `_last_trigger_robot_ids` is set in `_handle_outcome`
  but never cleared afterward, so it holds the previous cycle's robot set
  between analyses (harmless for the IB10 composite scenario, whose
  `junction_clear` plans carry no `continue` legs to exempt, but a latent
  staleness window on scenes that do) — not fixed here, flagged for the
  coordinator. (c) the first CORRECTION entry's "before the 34.3 s
  trigger" figure is off by the last digit — the report's own trigger
  decision artifact (`fff3e18...`) reads `scene.stamp=34.2` s; corrected
  here, not edited in place there, per the append-only rule. No VM state
  changed by the forensic re-reads in this entry (same attempt-3
  artifacts, re-read, not re-run); item (a)'s code fix is new and is
  included in the VM-deployed branch tip for whoever runs it next.
  `docs/reports/2026-10-02-step7a-blocker-fixes.md` carries the corrected
  finding 1, attribution paragraph, and both affected table rows.

- **2026-10-02** — **FIFTH CORRECTION (same task, step 7a): the entry
  above's closing claim is false. The VM does NOT carry item (a)'s fix
  (or the fix-3 narrowing fix before it) — verified by md5, no further
  VM run performed beyond that read.** `orchestrator_node.py` on the VM
  (all three copies: `ros2_ws/src/.../orchestrator_node.py`, the colcon
  `build/` copy, and the `install/` copy -- identical in both the host
  filesystem and the `vgu_ros` container, which bind-mounts
  `/home/ubuntu/vgu-vlm-swarm` at `/ws` rather than holding a separate
  copy) md5s to `9f0e758d89db65e41156bba6381b0cde`, which matches
  `git show 29f7e3f:ros2_ws/.../orchestrator_node.py` exactly -- the
  commit right after the SECOND CORRECTION, BEFORE `4e1a7a9` (fix 3's
  trigger-set narrowing) and `643d9ae` (this entry's own manual-trigger
  closure) were written. **The VM run this report scores (attempt 3) was
  executed against fix 3's first-draft blanket exemption, not the
  narrowed or manual-trigger-safe versions** -- those two fixes are
  unit-pinned only, never exercised live. Nothing in the attempt-3
  VM evidence this report and log rely on (the five fixes' phase
  sequence, the 4/4 arrivals, the release-window ambiguity, the
  same-side race) depends on fix 3's own exemption scope, so none of it
  is invalidated by this -- but the branch must be redeployed (plain
  copy + rebuild, the documented colcon-mtime-skip convention) before
  its NEXT VM run, which this task does not perform (out of scope; no
  VM run beyond read-only verification was authorized past attempt 3).
  **Also corrected, same read:** the "all four copies" pristine-config
  claim in the CORRECTION/SECOND CORRECTION entries and the report's own
  VM-close-out section overcounts by conflating host-path and
  container-path views of the SAME bind-mounted files (`vgu_ros`
  mounts the host tree at `/ws`, not a separate copy) -- there are three
  distinct files on disk (`orchestrator.yaml` source + installed,
  `rag.yaml` source only), all independently re-verified pristine just
  now (`1f656533.../e18c723...`, host and container paths agree because
  they are the same inode), GPU idle (0%/171 MiB), no Isaac/Nav2 process,
  one leftover `/tmp/gt_run3_displacement.py` scratch script from this
  task's own earlier forensic read removed. `docs/reports/2026-10-02-
  step7a-blocker-fixes.md`'s VM-close-out section and fix 3's own section
  are corrected to state the VM-validated version plainly and drop "all
  four."

- **2026-10-02** — **SIXTH CORRECTION (same task, step 7a): the entry
  above left an unverified claim ("nothing attempt-3's evidence is used
  for depends on fix 3's exemption scope") -- now checked against the
  run's own decision artifact, not assumed.** `data/logs/m5_decisions/
  fff3e18376454ab4b7f63c5f978b61d0.json` (the run's only DISPATCHED
  trigger -- checked against all 11 `m5_decisions` artifacts carrying
  this run's `run_id`; the other 10 have `strategy=none`,
  `grounded_command_present=False`, no plan, so nothing was dispatched;
  their stamps are 30.7 s (before the 34.2 s trigger) and 218.3-253.6 s
  (after the release window, sim 94.9-215.4, had already resolved),
  `m3_default` junction_clear) shows `involved_robots=["robot_1",
  "robot_2", "robot_3", "robot_4"]` -- ALL FOUR scene robots, so the
  blanket and narrowed trigger-set scopes are IDENTICAL for this run
  regardless (first reason). Its `plan.legs` are `robot_3: reverse,
  robot_4: reverse, robot_1: yield, robot_2: cross` -- ZERO `continue`
  legs, directly confirming FOURTH CORRECTION's point (3)(b) ("IB10's
  junction_clear plans carry no continue legs to exempt") from the
  artifact itself, not inference (second, independent reason:
  `_with_plan_continue_partners` filters for `continue` legs and finds
  none either way). A third, independent reason neither prior entry
  named: `_with_plan_continue_partners` is only ever called for
  `action == "reverse"` (`_publish_fanned_out`'s own dispatch, fix 3's
  own section above) -- the release phase's own actions (fix 2) are all
  `yield`, never `reverse`, so fix 3's code path is not even reached by
  the release command fix 2 and finding 2/3 analyze. All three reasons
  independently guarantee fix 3's exemption-scope bug (blanket vs.
  narrowed vs. manual-trigger-safe) could not have changed this run's
  outcome. No VM state changed (local artifact read only).
  safety.py`'s `admitted_partners` gained an ADDITIVE, v2-branch-only
  exemption parameter.** `plan_partners: frozenset[str] = frozenset()`
  (sourced from a NEW `plan_continue_partners_from_parameters` reader on a
  `reverse` leg's own `parameters_json`, populated only by `orchestrator_
  node._with_plan_continue_partners` when a tracked `plan_id` is present
  and the SAME plan names another robot `continue`). This is additive to
  the existing own-command `members` scope, never a substitute: a v1 (no
  plan channel) `reverse` command never carries `plan_continue_partners`,
  so `admitted_partners`'s behavior for every v1 scenario is byte-
  identical (regression-pinned, `test_no_plan_reverse_plus_an_uninvolved_
  robot_still_latches`). Rationale: a `continue` leg of the same accepted
  plan as a `reverse` receives no command of its own, so it is invisible to
  the existing `members`-based scope; the wire `CoordinationCommand` has no
  `plan_id` field, so the information travels on the reverse leg's own
  parameters instead of a cross-command lookup. Scoped narrowly (pair-
  scope discipline pinned: a `continue` robot NOT named on this specific
  reverse's own parameters stays fully latched, `test_reverse_does_not_
  exempt_an_other_plan_continue_robot`) — never a blanket same-plan-or-wider
  exemption.
  **Superseded in part by the THIRD and FOURTH CORRECTION entries above
  (FIFTH notes the fix is not yet deployed)**: this entry's "the SAME
  plan names another robot `continue`" undersells the actual scope by
  the time of this log's last entry — the shipped code also requires
  that robot to be in `_last_trigger_robot_ids` (added by THIRD
  CORRECTION) and that narrowing is itself bypassed to empty on the
  manual-trigger path (closed by FOURTH CORRECTION's item (3)(a); FIFTH
  CORRECTION found this closure was never exercised on the VM). Not
  rewritten here per the append-only rule.

- **2026-10-02** — **v2 build-order step 9: B2-visual urgency pair and B3
  first-to-slip authored (local only; branch `feat/v2-b-scenarios`)** (prereg-v2
  design docs/superpowers/specs/2026-09-30-prereg-v2-design.md, "(c)"/"(e)").
  - **B2-visual (`priority_visual_r1`/`_r2`, `isaac/config/scenarios/`).**
    Byte-identical T1 `wopen_eopen` geometry to v1's `priority_urgent_r1`/
    `_r2` pair, but urgency carries ONLY visually: one robot's
    `robots[].loaded: true` authors a pallet/load prop
    (`isaac/vgu_sim/load_prop_asset.py`) rigidly mounted flush to its
    chassis rear (local x = -0.102, no floating gap); both robots share one
    neutral task label (`cross_narrow_aisle`) and NO robot carries a
    registry `priority` (v1's pair sets `priority: 1` on the urgent robot,
    unrendered; this pair has none, so `priority_override` cannot ground --
    it needs a unique registry max, and a 0-0 tie has none -- degrading to
    `strategy=unsupported`: a deliberate asymmetry against v1 B2, recorded
    in the scenario header; the executable route is `yield` naming the
    empty robot, per the new mocks
    `config/mock_decisions/priority_visual_r{1,2}_yield_once.json`).
    `RobotScenarioConfig.loaded` is additive (default `False`, omitted from
    every dump via a new `model_serializer`, mirroring `OracleConfig`'s
    ordering-field pattern), so every v1 scenario's dump stays byte-identical
    (verified: `tests/unit/test_generate_head_on_family.py`'s 34 cases still
    pass). Reuses `PriorityOracleConfig` unchanged (no contract change).
    Mounting geometry and the marker/lidar-plane clearance are pure Python
    (`marker_clearance_m`, `lidar_plane_clearance_m`; both verified positive,
    0.042 m each, pinned in `tests/unit/test_load_prop_asset.py` with no
    simulator); the USD authoring (`author_load_prop`) and its validator
    (`isaac/vgu_sim/validation.py::validate_robot_load_prop`, wired into
    `scenario_builder.build_scenario_stage`) are pxr-only and pinned with
    `pytest.importorskip("pxr")` the same way `test_m6_validation.py`
    already does (`tests/unit/test_load_prop_asset_pxr.py`, skipped
    locally, 4 cases). The no-text-urgency pin
    (`tests/unit/test_priority_visual_scenarios.py::TestNoTextUrgency`)
    renders this pair's actual prompt and diffs it against the raw v2
    template to confirm the only two superficially-matching terms
    ("priority", from `priority_override`'s strategy-enum listing; "empty",
    from an unrelated field-rendering rule) are template-fixed, not a leak --
    every other candidate term (urgent/load/pallet/cargo/payload) is absent
    in both presentation orders and both members, which render byte-identical
    prompts to each other (unlike v1's pair, whose task labels swap).
    Both members' maps are pinned byte-identical to the T1 map (no physics
    change: the prop carries no `CollisionAPI`/`RigidBodyAPI`/`MassAPI`, and
    its top, local z = 0.13, stays under the lidar's single scan plane,
    local z = 0.172).
  - **B3 first-to-slip (`convoy_counterflow_slip`,
    `isaac/config/scenarios/convoy_counterflow_slip.yaml`).** A variant
    scene, byte-identical geometry to the v1-frozen `convoy_counterflow`
    cell (diff confined to `name` and `oracle`, pinned in
    `tests/unit/test_convoy_counterflow_slip_scenario.py`; map pinned equal
    too) that changes only what is SCORED: which platoon member
    (`oracle.platoon`) is first to actually resume motion once the yielder
    clears the gate, and how long that takes. New `OracleConfig.first_slipper`
    field (additive, optional, validated as a `platoon` member, omitted from
    the dump when unset -- same discipline as the existing ordering fields).
    **Slip-onset criterion** (`scripts/coverage_scene_scores.py`,
    `slip_onset_sec`/`first_slipper`/`score_b3`): a platoon member slips at
    the first GT sample after the conflict onset whose departure from its
    own onset-time position (> 0.05 m) is sustained for >= 1.0 s
    continuously (mirrors `stop_time_sec`'s spell rule, inverted); the
    first-to-slip identity ties to the lower robot id
    (`first_passer`'s existing convention), and
    `first_slip_latency_sec` is that onset minus the conflict onset. Reads
    only each robot's own GT track, so a scripted command (e.g. the
    robot_3/robot_4 hold-back release at ~43-51 sim-s) cannot trigger it by
    itself. **Bug caught by the test suite, fixed before landing:** an
    earlier version scanned each robot's FULL GT track, which read a lead
    robot's own pre-standoff APPROACH (necessarily far from its not-yet-
    reached onset position) as an immediate false slip at t=0; fixed by
    restricting the scan to samples at/after the conflict onset. Pinned with
    a synthetic GT fixture covering jitter-below-threshold, a poke-and-
    return shorter than the hold, a robot that never moves, and -- the
    regression case for the bug above -- identity flipping to a non-lead
    platoon member (`tests/unit/test_coverage_scene_scores.py`, 8 new
    cases). **Degeneracy, flagged per the build task's instruction, not
    treated as a defect:** under the scene's own designed/correct execution,
    `first_slipper` (`robot_1`, the platoon lead) is already implied by
    `oracle.correct_order[0]`, so the identity call is not independently
    informative for a correctly-executed episode; it is scored anyway
    because (a) a live, imperfectly-grounded run can diverge from the design
    (a wrong identity is itself diagnostic), and (b) latency is a new
    continuous metric with no v1 counterpart. No M2/M3 VLM-facing contract
    changed (confirmed: `OracleConfig` is scenario/oracle-side only).
  - **Suite:** full local run at the branch point (`955b962`, clean venv,
    `requirements-dev.txt`) vs. the same tree with both items landed: 63
    failed / 4310 passed / 144 skipped / 3 collection errors (baseline) vs.
    63 failed / 4372 passed / 152 skipped / 3 errors (final) -- the FAILED
    test-name set is byte-identical (diffed), so zero regressions; the +62
    passed / +8 skipped are this task's own new tests (the 8 skips are the
    pxr-only authoring/validation cases, matching the project's existing
    convention of skipping rather than erroring without Isaac Sim's `pxr`).
    The 3 pre-existing collection errors (`test_marker_asset.py`,
    `test_robot_asset.py`, `test_scenario_builder.py`, all missing a
    `pytest.importorskip("pxr")` guard) and the 63 pre-existing failures
    (49 `test_aruco_parity` cases plus 14 others, all pxr- or
    environment-dependent) are untouched, out of this task's scope.
  - **Turnkey for the VM pass (USD rebuild + visual verification, not done
    here):** build both `priority_visual_r{1,2}` scenes and confirm (1) the
    load prop renders visibly in the overhead annotated frame without
    covering the ArUco marker at the standoff AND at the ROI edges near each
    robot's spawn/goal; (2) M1 marker detection is unaffected (100% fresh,
    0% STALE, matching the step-6 STALE-streak instrumentation rule) on both
    the loaded and the empty robot; (3) a same-pose loaded-vs-empty crop
    comparison between the two members is a free visual A/B; (4) both
    scenes' Nav2 maps regenerate byte-identical to the committed ones (no-op,
    already verified without Isaac from the authored YAML); (5) run the new
    `scripts/coverage_scene_scores.py b3 --gt <dir>` subcommand once against
    a real `convoy_counterflow_slip` GT log and sanity-check `first_slipper`/
    `first_slip_latency_sec` against the live trajectory.

- **2026-10-02** — **T3b's map-bake open item is resolved: by design, not a
  bug** (v2 build-order step 9 pre-check; resolves the open item flagged in
  the loop-map entry below, "`obstacle_in_candidate.yaml` (T3b)'s own
  Y-asymmetric static obstacle does not appear baked into its committed map
  ... flagged for the coordinator"). `obstacle_in_candidate.yaml`'s
  `candidate_box` is declared under `timed_obstacles` (`asset: static_box`,
  `spawn_at_sec: 1.0`, `remove_at_sec: null`), not under `static_obstacles`.
  `generate_warehouse_map.build_occupancy_grid`'s own docstring states the
  rule generally: "Timed obstacles are never baked -- they are runtime-
  spawned bodies, not part of the static map" — only `rasterize_static_obstacles`
  (the `static_obstacles` list) and `rasterize_aisle_barrier` touch the grid
  beyond the default rack/wall pass. The scenario's own header already
  documents this as intentional, predating the open item by several days
  (`58bb428`, 2026-09-28): "Nav2 layer. The box is not baked into the map.
  It spawns at 1 s, before M5's first scene (~12 s), so Nav2's lidar marks
  it from the start... The yield is not a Nav2 leg... Nav2 never refuses
  anything, because nothing asks it" — i.e. the box must stay off the
  Nav2-map text/geometry channel (T3b's whole point is that avoiding it
  needs the image, not a map or lidar-refusal signal), and `static_obstacles`
  would also leak into `prompt_static_obstacles`/M5's text channel, which
  T3b's header separately requires to stay absent. Two cheap confirmations
  (local, no VM): (1) the committed `warehouse_map_obstacle_in_candidate.pgm`
  reads 255 (FREE) at the box's world cell and its 0.05 m neighborhood
  (world (−0.32, 0.81), the box's declared `pose`); (2) regenerating the map
  from `obstacle_in_candidate.yaml` via `generate_warehouse_map.py` is
  byte-identical to the committed `.pgm`/`.yaml` (resolution 0.05,
  origin [−6.0, −4.0, 0.0] unchanged). RULING: the loop-map entry's "own
  Y-asymmetric static obstacle" phrasing was a mislabel (T3b's obstacle is a
  timed obstacle, not a static one); no code change, no T3b yaml edit (a
  v1-frozen cell). The T3b yaml header needed no correction since it already
  states the by-design rationale.
- **2026-10-02** — **v2 build-order step 6, episode 2 (extended live
  re-run, one-re-run allowance): the `junction_clear` composite's own
  fallback path can itself fail.** `docs/reports/2026-10-02-ib10-
  composite-smoke.md`'s Episode 2 section, same branch. Re-ran the live
  episode with `REC_SEC=1350`/`SIM_SEC=1400` (sized to the measured 0.27
  real-time factor) after discovering episode 1's apparent "no progress"
  was the ROS2 stack dying early. Episode 2's own measured RTF places its
  control-stack teardown PAST the scenario's 300 s GT cap, so its full
  trajectory is genuinely, continuously supervised -- confirming, not
  truncating, the result. Outcome: 10 real VLM calls (vs. 2 in episode 1),
  the model oscillating between `reverse` and a narrower `junction_clear`
  for the same `robot_3`/`robot_4` conflict, before a fourth composite
  attempt's CROSS phase fails to resolve for 495 real seconds and M5's own
  documented fallback (derived-mode `reroute`, all four robots) ALSO
  fails for every robot. Scene frozen (0.388 m separation, zero velocity)
  from sim~180 s to the 300 s cap under a confirmed-alive stack. Same 1/4
  arrival result as episode 1 (`robot_2` only), but via a different,
  worse failure mode -- answers the "does more time help" question the
  first episode left open: no. Also reproduces episode 1's `robot_3`
  out-of-tracked-band `reverse` excursion (`|y|=2.42` this time vs `2.38`)
  at the same sim-time window both times (108.6-114.9 s), now a confirmed,
  not one-off, pattern. Added as freeze-blocking finding 5. VM restored
  pristine a second time (same `1f656533`/`e18c723` pair, all four
  copies), GPU idle, no stray processes.

- **2026-10-02** — **v2 build-order step 6: IB10 `junction_clear` composite
  smoke, mock (2 runs) + one live ER-2 episode, full report
  `docs/reports/2026-10-02-ib10-composite-smoke.md`, branch
  `feat/v2-ib10-smoke` (from `feat/prereg-v2-composite` at `955b962`).**
  (1) **Goal-table fix landed**: `ros2_ws/src/swarm_orchestrator/config/
  orchestrator.yaml`'s IB10 comment now documents `junction_recede_
  offset_m: 1.2` + `junction_backup_clearance_m: 1.1` together (the step-5
  post-landing bug-4 fix); verified end to end through the real `load_
  config` path, not a hand-built dict. (2) **Loudness guard widened**
  (`reasoning/rag/command_grounder.py`): `junction_geometry=shipped_
  unsolved:missing=<field,field>` now fires whenever `junction_clear`
  grounds without BOTH fields, independent of which code path produced the
  fallback (the first draft only caught one of three cases; a coordinator-
  review correction). (3) **Repair-bound sweep** (`scripts/junction_clear_
  repair_bound_sweep.py`, local, no VM): confirms `max_repair_edits=2`
  (the shipped default, unchanged) clears every case that reaches repair at
  all in a 17-case deterministic corpus -- but surfaces a FREEZE-BLOCKING
  metric hole, not fixed here: a `junction_clear` plan naming the WRONG
  recede pair verifies `vlm_verbatim` (no membership check exists for
  recede-set correctness under `yield_feasibility_mode="off"`), while
  `junction_clear_plan_matches_dispatch` correctly flags it `False` --
  metrics (ii)/(iv) alone would silently over-credit this defect class.
  (4) **Mock smoke, 2/2 runs**: full recede(staggered)-then-yield-then-cross
  phase sequence executes correctly both times (run A `m3_default`, run B
  `vlm_verbatim`, chi order flipped between runs on live near-tied
  positions -- confirms step-5's own "cosmetic, not exercised twice" chi-tie
  finding in a real run), solved-row numbers (backup 0.799 m / park
  |x|=1.018 m / escort 1.998 m) grounded both times, deploy check clean
  (no `shipped_unsolved` tag). Both runs land at 1/4 arrivals within their
  300 s window -- ROOT CAUSE (corrected mid-task after the live episode,
  do not read the mock-run sections of the report without this): NOT a
  suppression/cooldown bug -- M5's detector re-triggers the post-resolution
  N-S conflict (robot_3/robot_4 released toward each other's original
  goals after the composite's `done=True`) 4-8 times per run, but
  `MockBackend` holds its scripted array's LAST entry (`none`) forever once
  exhausted, so a finite 3-entry mock can never answer a conflict it wasn't
  scripted for. (5) **Live ER-2 episode confirms this**: two live decisions
  (`junction_clear` -> model's own plan is inconsistent, `m3_default`
  correctly substituted, composite resolves identically to the mocks; then
  `reverse` for the same secondary N-S pair, `vlm_verbatim`, dispatched) --
  1/4 arrived but `robot_3` was still moving when the 300 s window closed
  (decision 2 landed at wall-elapsed ~306 s, almost no time left to
  execute), a materially different (in-progress, not frozen) result from
  the mocks. API spend: 3 live calls (1 preflight + 2 episode), ~9.3k
  tokens total, ~$0.017 at the published ER-2 rate (input $1/1M, output
  $5/1M, sourced live -- thinking-token billing assumed, not confirmed for
  this model specifically). STALE instrumentation: every run showed at
  most one single-frame blip (never a streak), none in a scoring-relevant
  window -- does not invalidate any run per the resolved gate's ruling.
  Zero-delta local suite maintained throughout (58 failed/4311 passed/139
  skipped vs. the `955b962` baseline, identical failing-test-name set).
  VM (`vgu-vgu-thule-base-isaac-workstation-vm`) restored pristine on all
  four `orchestrator.yaml`/`rag.yaml` copies (independently confirmed by a
  full 724-file `git ls-files` md5 manifest diff against the VM: only the
  two restored config files and two since-updated doc files differ, no
  code), GPU idle, no stray processes.
  **CORRECTION (same task, same report, post-advisor-review):** three
  claims in the first pass were wrong, all fixed in the report, not here:
  (1) the STALE table above used a collapse-to-first-row method that
  erased every real dropout -- recomputed with the project's own raw-row
  method (`m1_y_extent_probe_analysis.py`'s `score_scene_log`), the true
  numbers run 2-26 rows per streak, not 0-1; one streak (live run,
  `robot_3`, 25 rows) overlaps an ACTIVE unresolved-conflict window, not an
  idle dwell. (2) Arrivals were re-verified against the actual scoring
  instrument (`ArrivalGate`'s `arrived at base goal`/`arrival accepted`/
  `arrival rejected` log lines), which agrees with the GT-distance estimate
  in all three runs (1/4, `robot_2` only) -- the instrument was right, just
  previously unconfirmed directly. (3) The live episode's "1/4, ran out of
  time" framing was wrong: decision 2's trigger stamp (read from the
  decision artifact, not estimated from wall-clock) is 96 s, not ~306 s;
  the real mechanism, traced through `m4.log` + GT, is that the decision's
  own `continue` leg for the uninvolved `robot_1` let it close to within
  the 0.45 m safety latch of the reversing `robot_4` (`admitted_partners`
  only exempts same-command members), permanently stalling `robot_4`'s
  `reverse` and, with it, the command's resolution and M5's retrigger.
  Also newly folded in: run B's `junction_clear` dispatch order (chi
  re-ranked `robot_3` before `robot_4` live, opposite the proposed plan)
  verifies `vlm_verbatim`/`dispatch_matches_plan=true` despite executing a
  different sequence -- the SAME metric hole as the step-4 sweep's
  wrong-recede-pair finding (no recede-vs-recede order check exists),
  now confirmed live, not just swept.
  **SUPERSEDES the "permanently stalling"/"~200 s" framing two sentences
  up** (same task, further review pass found `REC_SEC=450` bounds the ROS2
  control stack in WALL seconds while this scenario runs at a measured real-
  time factor of 0.27 -- the container teardown this episode hit lands at
  sim~134.6 s, not after a long stall; `robot_4`'s `reverse` simply never
  resolved inside the ~37 s it had before the harness tore the stack down.
  A second, longer episode (`REC_SEC=1350`) reproduced the same `continue`-
  vs-`reverse` safety-latch trigger on the SAME scene twice more, but both
  times the commands resolved within ~53 s given more time -- "stalls"
  under the original harness, not an unconditional deadlock. See the full
  report for the corrected trace and the second episode's own results.

- **2026-10-02** — **v2 build-order step 5, post-landing advisor-review
  fixes** (same branch, same task; six real bugs found by independent
  review of the entry below, none caught by the tests that existed at that
  point because the node-harness tests ran under the 2-robot default
  `initial_tasks`, silently filtering robot_3/robot_4 out of every phase
  and masking the held-robot wiring entirely):
  1. **Held robots corrupted their own future plan leg.** A phase's
     `temporary_wait` hold resolving COMPLETED was routed by
     `_apply_plan_leg_status` onto the HELD robot's real (different,
     still-`pending`) plan leg, marking it `done` before it ever ran (e.g.
     robot_1's `yield` after phase one's robot_4-only recede). Fixed by a
     new `JunctionClearPhase.held_robot_ids` (and `JunctionClearPhasePlan.
     fallback_held_robot_ids`), threaded through `JunctionPhaseAdvance`
     into a new `orchestrator_node._junction_held_robots` side table;
     `_apply_plan_leg_status` now skips a robot entirely when it is held
     for that command_id. Pinned:
     `TestHeldRobotsNeverCorruptTheirRealPlanLeg` (`test_m5_node_
     junction_clear.py`).
  2. **The fallback left an already-receded (or mid-failure) cross-axis
     robot unaddressed.** J1 correctly drops both cross-axis robots from
     the fallback yield's own order, but the fallback command named
     neither at all -- a receded robot's base mission could resume through
     the junction while the fallback yield ran. Fixed: `ground_junction_
     clear_phases` now adds the SAME `extra_holds` pattern the cross phase
     already used to the fallback command too, for every `ranked`
     candidate it does not already address. Pinned:
     `TestFallbackHoldsAlreadyRecededRobots`, `test_the_fallback_is_a_
     plain_yield_dropping_the_cross_pair_via_j1` (updated).
  3. **`dispatch_matches_plan` read False on every clean `junction_clear`
     run.** It compared phase one alone (`grounded`) against the tracked
     plan's FULL sequence -- a category mismatch, since one phase is never
     the whole resolution. Fixed: new `command_grounder.junction_clear_
     plan_matches_dispatch` reconstructs the whole sequence's per-robot
     action (each robot's action from whichever phase actually acts on it,
     every phase's held robots excluded from its own contribution) and
     `InProcessPipeline.run` uses it instead of `plan_matches_dispatch`
     when `junction_phases is not None`. Pinned against the REAL
     `InProcessPipeline` (the node-harness fake pipeline hard-codes this
     field, which is what let the bug through originally):
     `test_junction_clear_seeds_phases_and_matches_dispatch`,
     `test_junction_clear_absent_without_a_declared_pocket_still_matches`
     (`test_m5_reasoning_pipeline.py`).
  4. **The cross phase silently used the shipped 1.7 m clearance, not
     C''s.** None of this task's test geometries declared
     `junction_backup_clearance_m` (J2) alongside `junction_recede_
     offset_m`; without both, the cross phase grounds the study's "1, E-W,
     shipped" row (backup 1.151 m, retreat_x -1.37 m) -- the SAME
     park->passer-goal race the design exists to avoid -- instead of "1,
     E-W, J2" (backup 0.799 m, confirmed in [0.69, 0.91]; park |x| 1.018 m,
     matching the table's 1.02; escort 1.998 m, matching [1.77, 2.00]).
     Not a code defect -- `SceneGeometry.junction_backup_clearance_m` was
     already read correctly wherever declared -- but a test-fixture and
     DEPLOYMENT-REQUIREMENT gap: **step 6's IB10 goal-table row MUST
     declare BOTH `junction_recede_offset_m: 1.2` AND `junction_backup_
     clearance_m: 1.1`**, or `junction_clear` quietly runs the cross phase
     at the unsolved shipped numbers with no error, only the absence of
     any `junction_clear=fallback:*` tag to notice by. Pinned:
     `test_cross_phase_matches_the_studys_c_prime_numbers_only_with_j2_
     declared` (`test_junction_clear_grounding.py`).
  5. **The "compute once from one snapshot" assumption, verified, not just
     argued.** Grounded the cross phase from the pre-recede snapshot and
     again from a POST-recede one (robot_3/robot_4 at their final |y| =
     1.2 pockets): every SAFETY-CRITICAL yield parameter (backup, pull-off,
     retreat x/y, escort distance) is identical either way, confirming
     `JunctionClearPhasePlan`'s own docstring claim -- none of them reads a
     cross-axis robot's position. FINDING, reported rather than papered
     over: the cosmetic `extra_holds` LIST ORDER (robot_3 vs robot_4 first)
     CAN differ between the two groundings, because chi re-ranks on
     whichever positions it is given and the two candidates are an exact
     tie at |y| = 1.2; harmless (M4 has no ordering dependency between two
     `temporary_wait` entries) and not actually exercised twice by this
     system (`ground_junction_clear_phases` runs once per decision, from
     one snapshot, never re-grounded from a later one), but a real
     divergence, not nothing. Pinned: `test_cross_phase_safety_numbers_do_
     not_react_to_the_recede_pairs_position`.
  6. **Attempt bookkeeping resolved after phase one, not the whole
     sequence.** `_resolve_command` called `self._attempts.resolve`
     unconditionally; since `.record()` is only ever called once (for
     phase 0, in `_dispatch`), phase one's OWN resolution matched that
     recorded command_id and closed the attempt "completed" after just the
     first recede -- before the cross phase had even been dispatched, so a
     LATER phase's failure would never reach `failure_context`. Fixed:
     `_resolve_command` now defers `self._attempts.resolve` until
     `JunctionPhaseAdvance.done` (carrying the ORIGINAL phase-0 command_id
     forward through a new `_junction_original_command_id` side table,
     re-keyed on every advance) and resolves it once, with the terminal
     outcome. Also reordered `_advance_junction_phase` to run BEFORE
     `_publish_registry()` (a smaller finding from the same review: the
     old order published one moment with every override cleared before the
     next phase's overrides were set). Pinned: `TestAttemptResolutionDeferred`.
  - **Test-fixture fix, not a separate bug**: `test_m5_node_junction_
    clear.py`'s `_node()` now declares `initial_tasks` for all four IB10
    robots (the harness default is two) -- without it,
    `filter_command_robot_ids` silently dropped robot_3/robot_4 from every
    dispatched phase, which is exactly how all six bugs above went
    unnoticed by the FIRST round of tests. New `TestAllFourRobotsAddressed`
    pins the real 4-robot dispatch shape directly.
  - **Tests**: 159 passing in the targeted files after these fixes (up
    from 148 before this round); full-suite zero-delta re-confirmed
    against the SAME baseline file as the entry below (`/tmp/
    jc_baseline_failed_names.txt`, this environment, 63 failed / 4227
    passed / 144 skipped at `a3e458e`): 63 failed / 4286 passed / 144
    skipped after, identical failing-test-name set. `make lint` (ruff)
    clean.

- **2026-10-02** — **v2 build-order step 5: `junction_clear` contract landed
  on `feat/v2-junction-clear`** (branched from `feat/prereg-v2-composite` at
  `a3e458e`), per `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`
  "(a) Composite recede-then-yield command" and the (a0)/M5 sections,
  **LOCAL BUILD + UNIT TESTS ONLY** -- no VM, no live API calls; step 6
  (IB10 mock/live smoke) is a separate task. Spec sync first: the branch had
  diverged from `fix/deadlock-collision-resolution`'s five 2026-10-02 doc
  commits (repair-semantics rulings, step-6 STALE-gate resolution, plan
  lifecycle pending-only-cancel/hold rulings, capability-battery note, the
  hold-vs-replan REFINEMENT); cherry-picked in order onto a reset branch tip
  (`28d9bd2`..`4e285a0`), one trivial append conflict resolved by hand;
  `git diff fix/deadlock-collision-resolution -- docs/superpowers/specs/
  2026-09-30-prereg-v2-design.md` confirmed empty after.
  - **Strategy token** (`reasoning/vlm/models.py` `CongestionDecision.
    strategy`, `reasoning/schemas/vlm_decision.schema.json`,
    `isaac/vgu_sim/config.py` `OracleStrategy` -- a pinned parity mirror,
    caught by the existing `test_oracle_literals_match_the_decision_
    contract`): `junction_clear` added to the shared Literal. Only prompt
    v3's strategy list mentions it (`reasoning/vlm/prompt_builder.py`
    `_USER_TEMPLATE`); v1/v2 (`prompt_v1.py`/`prompt_v2.py`) are separate,
    untouched frozen modules, confirmed by re-running their hash-pin tests
    unchanged. No scene-specific guidance bullet added for it (an owner
    call per the advisor review below; the risk is handing IB10 its own
    answer). DECISION (recorded, not changed): the Literal is shared across
    every prompt version, same as `blocker_kind`/`crossing_order`/
    `proposed_plan` already are -- a v1/v2-prompted response that happened
    to emit the string now parses instead of raising, consistent with how
    every other v2+-only field already behaves under every prompt version;
    not a new inconsistency this token introduces, so no
    `prompt_version`-gated validation was added.
  - **(a0) consistency rule**: `_is_consistent` gained `junction_clear ->
    >= 1 reverse or yield leg` (`command_grounder.py`).
  - **(a) Grounding -- chi cost-ranked recede selection**
    (`reasoning/rag/maneuver_geometry.py`): chi = s*D_SPACE + t*N_f
    (A-DRIVE, arXiv:2204.04910). New `GroundingParams` fields, all
    placeholders in the same convention as `PlanRepairParams.
    max_repair_edits`: `junction_recede_cost_space_weight=1.0`,
    `junction_recede_cost_follower_weight=0.5`,
    `junction_recede_tolerance_m=0.1`, `junction_recede_hold_sec=120.0`.
    New `SceneGeometry.junction_recede_offset_m: float | None` (the
    declared pocket target, the study's C' h ~= 1.2 m -- a SCENE CONSTANT,
    not derived from J2's clearance arithmetic; confirmed by hand:
    `recede_distance_m` gives D_SPACE(robot_3)=0.942, D_SPACE(robot_4)=0.923
    against the IB10 GT standoff, both landing at the declared |y|=1.2,
    matching the study's "0.93-0.95 m from +-0.25-0.27" within rounding).
    New pure functions `recede_axis_offset_m`/`recede_distance_m`/
    `recede_follower_count`/`recede_cost`/`rank_recede_candidates`/
    `is_at_recede_pocket`.
  - **INTERPRETATION, flagged (not settled by name in either spec)**: the
    recede candidate SET is structural -- involved robots whose declared
    arm axis differs from `geometry.corridor.axis` -- not chi-discovered;
    chi only orders WITHIN that set. Verified this matters: ranking all
    four IB10 robots unrestricted puts robot_2 (yield axis) first by chi, so
    without the structural restriction the oracle's "correct recede pair by
    chi" would be wrong. Pinned in
    `test_candidates_restricted_to_the_yield_axis_are_never_chosen`
    (`tests/unit/test_junction_clear_grounding.py`).
  - **M3 grounding, real dispatch** (`command_grounder.py`): discovered via
    advisor review that the (a0) verify/repair engine (`_derive_default_
    plan`/`verify_and_repair_plan`) is measurement-only -- it does NOT
    drive what M4 receives (`ground_reasoner_result`/`_ground_derived` do,
    independently; `plan_matches_dispatch` only AUDITS agreement). New
    `ground_junction_clear_phases` builds the REAL ordered command
    sequence: one `reverse` command per recede candidate (chi order), each
    holding EVERY involved robot via `temporary_wait` (not just the active
    one) so `safety.admitted_partners` exempts the active robot against the
    whole scrum -- a single-robot recede command would latch immediately,
    confirmed by reading `admitted_partners`/`CLEARING_ACTIONS` before
    writing this, per the advisor review's flag. The final `cross` phase
    reuses `_ground_derived`'s existing yield branch verbatim (via a new
    `_as_yield_decision` rebuild helper) and ALSO holds every recede
    candidate via `temporary_wait` -- `reverse` never holds on its own
    (`command_bus_node.py` always resolves it with `hold_sec=0.0`), so
    without this a receded robot's base mission could resume toward its
    original goal, back through the junction, mid-crossing. `_ground_
    derived`'s own `junction_clear` branch returns ONLY `plan.phases[0].
    command` (`ground_reasoner_result`'s single-command contract preserved
    for every strategy: "the NEXT unresolved step"); falls back to plain
    `yield` over every involved robot (unchanged geometry, J1 drops the
    cross-axis pair to no-op) when no pocket is declared or no candidate
    survives chi -- exactly "v1 behavior ... single yield or no-op" (M5
    spec section), reusing the SAME code path the real fallback dispatch
    uses. **Scope cut**: implemented for DERIVED mode only (the shipped,
    live `config/rag.yaml` mode, the only one IB10 is tested under);
    LEGACY mode (`_ground_legacy`) degrades `junction_clear` to the
    existing non-spatial wait fan-out (added to the `{"convoy",
    "priority_override"}` degradation set) rather than raising
    `CommandGroundingError`.
  - **(a0) default-plan derivation** (`_derive_default_plan`): extended
    with a `junction_clear` branch producing the FULL sequence in one
    `proposed_plan`-shaped list (recede legs in chi order, then the
    yield-axis `yield`/`cross` legs via a new shared `_yield_default_
    actions` helper, factored out of the existing `yield` branch so both
    paths can never drift). `_plan_problems` gained the matching ordering
    AUDIT of a VLM-proposed plan: any yield-axis `yield`/`cross` leg
    positioned before a recede candidate's `reverse` leg is infeasible
    (the escort would run while that candidate is still 0.24-0.34 m away,
    unexempted outside its own command); the repair engine resolves it with
    a pure REORDER, pinned in `test_a_plan_that_crosses_before_receding_is_
    repaired`.
  - **M5 phase queue** (new `ros2_ws/src/swarm_orchestrator/swarm_
    orchestrator/junction_phase_queue.py`, ROS2-free, exported from the
    package `__init__.py`): `JunctionPhaseQueue` tracks one `junction_
    clear` decision's PRECOMPUTED phase sequence (`ground_junction_clear_
    phases`'s output, computed once from the triggering snapshot -- the
    scene does not change mid-sequence since every phase's command holds
    every uninvolved robot). `on_resolved(command_id, completed)` advances
    to the next phase on COMPLETED, or to the precomputed plain-`yield`
    fallback on FAILED (never retried, never simultaneous with another
    recede). **DESIGN CORRECTION from the advisor review**: the first draft
    re-derived one phase per M2 cycle (stateless); dropped because it would
    log phantom unforced replans (one per phase, with no failed leg),
    pin plan agreement at 0 for junction_clear, and make the IB10
    inside-first oracle unscoreable (no single plan ever names the whole
    sequence). The landed design computes the whole sequence once,
    accepted as ONE plan (one `plan_id`, zero replans for a clean run); M5
    advances through it by updating leg status via direct command
    dispatch, bypassing M2/`PlanTracker.accept_plan` entirely for phases
    2+. Wired into `orchestrator_node.py`: `_dispatch` seeds a queue from
    `outcome.junction_phases` (new `PipelineOutcome` field, same
    `plan_channel_enabled` gate as `plan`); `_resolve_command` (the single
    place both `_on_status` and the `_on_timer` timeout path funnel
    through) calls the new `_advance_junction_phase`, which publishes the
    next phase via a new `_dispatch_junction_phase` -- sharing
    `_publish_fanned_out` (extracted from `_dispatch`) for the identical
    per-robot publish/override/log sequence, but deliberately skipping
    `self._attempts.record` (a phase advance is not a new M2 decision; only
    the original `_dispatch` call records the one attempt the whole
    resolution counts as). Each later phase's command_id is mapped to the
    SAME `plan_id` so `_apply_plan_leg_status` keeps routing status onto
    the one tracked plan's legs.
  - **FLAGGED, not resolved by static reading (step-6's to watch for)**:
    the race between a receded robot's base mission resuming (once its
    `reverse` command's override clears) and M5 dispatching the next
    phase's `temporary_wait` hold for it -- argued safe by precedent
    (base-mission resumption elsewhere in this codebase also gates on a
    periodic timer tick, never synchronously inside the same status
    callback, per `_on_timer`'s own `release_due` pattern) but not provable
    without a live run.
  - **Hold-vs-replan REFINEMENT** (`plan_tracker.py` `_is_hold`): if any leg
    of the active plan has reached `failed`, an identical re-issue is now
    NEVER a hold, regardless of the remaining-legs comparison -- closes the
    FLAGGED gap the step-4 CORE build pinned (`test_failed_leg_reproposed_
    identically_is_still_a_hold_flagged_gap`, now renamed and flipped to
    `test_failed_leg_reproposed_identically_is_an_evidence_driven_replan`:
    `held=False`, new `plan_id`, `classify_revision_cause(["robot_1"]) ==
    "evidence_driven"`).
  - **Dispatch logging** (`orchestrator_node.py` `_publish_fanned_out`):
    the per-robot dispatch log line gains ` plan_id=<n>`, appended only
    when a plan_id is tracked for that command_id, so a flag-off line
    stays byte-identical (re-pinned by
    `test_dispatch_log_line_has_no_plan_id_when_the_flag_is_off`).
  - **Tests** (zero-delta, +48 new passing): `tests/unit/
    test_junction_clear_grounding.py` (23: chi hand-computed cells incl. a
    synthetic follower cell, IB10 D_SPACE pins, consistency rule,
    default-plan derivation incl. both fallback paths, phase-ordering audit
    + repair, staggered-never-simultaneous, legacy-mode degradation, the
    single-command contract), `tests/unit/test_junction_phase_queue.py`
    (13, pure), `tests/unit/test_m5_node_junction_clear.py` (11, ROS2
    stubbed per `test_m5_node_probe.py`'s harness: seeding, ordinary
    advance, failure fallback, timeout fallback, flag-off byte identity),
    `tests/unit/test_m5_plan_tracker.py` (flipped test),
    `tests/unit/test_prompt_builder_v3.py` (6 pins re-computed, +19 chars
    each from the strategy-list addition; v1/v2 untouched). Full-suite
    zero-delta confirmed against a clean detached worktree at the branch
    point (`a3e458e`, this environment, 3 pxr-only files ignored per the
    documented local/container split): 63 failed / 4227 passed / 144
    skipped before, 63 failed / 4275 passed / 144 skipped after, identical
    failing-test-name set. `make lint` (ruff) clean on every touched file.
  - **Not built, explicitly out of scope for this task**: stage-2 (retreat
    letter choice) for the `cross` phase (`retreat_choice` is accepted and
    forwarded but a dedicated stage-2 call is not wired for it, same
    `retreat=default:no_choice` degradation as an ordinary yield with no
    choice supplied); the `wait`-leg feasibility placeholder noted in the
    CORE build stays a documented placeholder (the study does not define a
    junction-scoped check); `max_repair_edits`/the chi weights/
    `junction_recede_hold_sec` remain placeholders, to be sized from the
    step-6 mock sweep per the spec's own build-order text.

- **2026-10-02** — **v2 build-order step 10, fourth correction: inter-robot
  label occlusion, distance-based dedup, fail-loud runner, geometry-fidelity
  tests** (supersedes the manifest numbers and the audit-coverage claims of
  the third-correction entry below; same branch, same `--seed 20261002`).
  Closes four gaps a review of the third correction found: (1) its
  `scanning.scene_is_legible` only checked centre-to-centre distance between
  robots, not whether one robot's drawn box could still cover part of
  *another* robot's label despite centres being >=70 px apart -- the same
  clipped-label defect as the first two corrections, one level removed; (2)
  its bucket-rounded dedup key (`round(x / 0.05)`) could put two positions a
  millimetre apart in different buckets and miss them as duplicates -- a
  direct distance check on the real, frozen manifest found 6 affected items
  (7 duplicate pairs: one item, `nearest_first_011`, duplicated two others)
  (mostly `nearest_first`, which the third-correction entry's own *answer*
  distribution had already hinted at: `robot_2` correct in 6 of 15 items
  from only 5 scenes); (3) `occlusion.py`'s replica of M1's drawing geometry
  was asserted correct by inspection, never tested against the real drawing
  function it replicates; (4) the runner scored a missing/drifted frame as a
  `"backend_error"` record and kept going, which would silently deflate an
  accuracy number after real (paid) backend calls, rather than failing the
  run before any call was made. Fixes:
  - `reasoning/vlm/capability_probes/occlusion.py`: new `SLACK_PX = 3` (line
    thickness + anti-aliasing) applied to the existing badge-overlap check
    and a new public `rects_overlap`; new `tests/unit/test_annotation_geometry_fidelity.py`
    renders the real `swarm_perception.annotation.draw_robot_overlay` and
    `grid._draw_cell_badge` on a blank canvas and asserts every painted
    pixel stays inside the replica geometry plus `SLACK_PX` (with a negative
    control proving the test isn't vacuous) -- the accurate claim is "shares
    one definition with the builder, tested against the real renderer",
    not "immune to a shared bug" (corrected wording from the entry below).
  - `scanning.scene_is_legible` now also rejects a frame when any two
    robots' M1 box/label rects overlap each other (not just when their
    centres are close), via `occlusion.rects_overlap`.
  - `scanning.dedup_key` (bucket rounding) replaced by
    `scanning.deduplicate_by_distance` + `max_displacement_m`: two
    candidates naming the same reference robot (or both none, `robot_count`)
    over the same tracked robot set are the same configuration when their
    largest per-robot GT displacement is under
    `NEAR_DUPLICATE_MAX_DISPLACEMENT_M` (0.10 m) -- one definition, used by
    both the builder's selection step and the audit script's own duplicate
    check (previously the audit re-derived the old bucketed key, which could
    not catch what that key itself missed).
  - `scripts/capability_probes.py`: split into `prepare_item` (materialize +
    build the prompt; raises on any failure) and `run_item` (the backend
    call only; still never raises). `run_battery` now prepares every item
    before constructing the backend or making any call, so a missing/drifted
    frame aborts the whole run with no JSONL/summary written, instead of
    being scored. New `ProbeAnswerRecord.error_type`/`error_message` capture
    a genuine backend exception's diagnostics (CLAUDE.md: no silent
    swallowing).
  - New tests: `test_capability_probe_scanning.py` (17, direct coverage of
    `scene_is_legible`/`deduplicate_by_distance`/`max_displacement_m`/GT
    matching -- previously only exercised indirectly), 3 in
    `test_annotation_geometry_fidelity.py`, plus the runner's
    `prepare_item`/`run_item` split test updates in
    `test_capability_probes_runner.py` (missing-frame now asserted to
    `raise`, not to produce a record).
  - Rebuilt manifest (same seed): still 15/15 per type, across 11 run
    families and 14 scenarios. Per type: `robot_count` 10 scenes, 5/5/5
    across {2,3,4}; `left_right` 10 scenes, 8 right / 7 left; `locate_robot`
    5 scenes, cells {1,3,4,5} (3,4,4,4) -- **4 of 9 cells**, down from 8
    scenes at the top of this correction: the new inter-robot occlusion
    check took it to 6, and switching to distance-based dedup took it to 5;
    `nearest_first` 5 scenes, answers {robot_1: 4, robot_2: 7, robot_3: 2,
    robot_4: 2}. The audit's distance check passes clean on this set (no
    remaining dedup gap), but `nearest_first` is balanced on *scene robot
    count* (`_balance_by_scene_robot_count`), not on the correct answer, so
    whether the `robot_2` concentration reflects the source logs or the
    balance key is not established -- flagged as a gap below, not asserted
    either way. Correct-letter distributions are not degenerate to one
    letter for any type (e.g. `left_right` 6 A / 9 B, `nearest_first` 8 A /
    7 B; `robot_count` D at 6/15, the rest 1-3 each -- within noise at
    n=15, not itself a flag).
  - `scripts/audit_capability_probe_manifest.py` (updated for the shared
    `scanning` functions above) reports `OK: all 60 items passed every
    check` on the rebuilt manifest -- this is now the verification method of
    record; see the gap report for what it does not cover.
  - Full-suite zero-delta re-confirmed (same 63 pre-existing failures, 4075
    -> 4211 passing across all four correction rounds plus the original
    build, 136 new tests total).
  - **Known residual gaps, carried forward, not fixed**: the model-pin gap
    (runner defaults to backend-factory config, i.e. the `gpt-4o` alias for
    openai and no config at all -- a hard error -- for anthropic/llama_server);
    the round, unlabeled objects visible in several scenes remain
    unidentified ("unmarked round objects", not "obstacles" -- never
    confirmed); the grid's 9 cells are not evenly reachable (`locate_robot`
    draws from only 4 of 9 after every filter: {1,3,4,5}); `y_extent_probe`
    kept no frames and contributed nothing; the left/right operationalization
    (image-frame halves, not a world-frame aisle side) is unchanged and still
    flagged for the v2-freeze owner's confirmation; `nearest_first`'s correct
    answers skew toward `robot_2` (7/15) and away from `robot_3`/`robot_4`
    (2/15 each) -- unexplained (see above) and worth checking against the
    project's own recorded gpt-4o `robot_1`-naming prior
    (`project_presentation_order_finding`) before attributing a live run's
    `nearest_first` errors to a located-reasoning gap rather than an ID
    prior; `--backend mock` end-to-end testing only exercises the
    parse-failure path (its default canned text is not a probe letter), not
    a scripted-correct run through the CLI itself (covered instead via
    direct `prepare_item`/`run_item` calls in the unit tests).

- **2026-10-02** — **v2 build-order step 10, third correction: M1-vs-GT
  answer agreement, frame-wide occlusion, cell uniqueness, duplicate-scene
  dedup, independent audit script** (SUPERSEDED by the entry above for
  manifest numbers and audit coverage -- the entry's own "all 60 items
  passed every check" is accurate for the checks that existed at the time,
  which did not yet include inter-robot label occlusion or a true
  distance-based duplicate check; the M1-vs-GT agreement and cell-uniqueness
  logic it introduced stand unchanged). The second correction's occlusion check
  tested only the *named* robot against the grid badges; a further look at
  its own rendered evidence (two images it had called "correct") showed a
  *different* tracked robot's label clipped by a badge in the same frame,
  and -- independently -- that several `locate_robot` items had two or three
  tracked robots sharing one cell, so the item did not actually require
  identifying the named robot (any guess near the cluster scored correct).
  Separately, many near-duplicate items had entered the pool: consecutive
  decision calls during a stalled episode log nearly identical robot
  positions a few seconds apart, and the per-run item cap did not catch
  this, so `n=15` per type overstated how much independent evidence the set
  held. Fixes:
  - New `reasoning/vlm/capability_probes/scanning.py` centralizes GT-row
    matching, the per-frame legibility check, and the scene-configuration
    dedup key, shared by both the build script and the new audit script
    below (one definition, not two that could drift).
  - `scripts/build_capability_probe_manifest.py`: `scanning.scene_is_legible`
    (edge-clear, >=70 px separated, no STALE, computed from **M1** pixel
    positions -- M1 is what the image actually shows) now gates *every*
    probe type per frame, not `robot_count` alone. Badge occlusion
    (`occlusion.robot_overlaps_any_grid_badge`) is checked for *every*
    tracked robot in the frame, not only the named one: any collision
    disqualifies every `locate_robot` item from that frame. A `locate_robot`
    candidate is further dropped when any other tracked robot shares its GT
    cell (`cell_not_unique`). Every candidate's GT-derived answer
    (cell/side/nearest) must now also equal the same answer computed from
    **M1** positions (`m1_gt_answer_disagreement`) -- a principled
    replacement for guessing a safety margin in pixels/metres: if the
    displayed (M1) and scored (GT) positions would give different answers,
    the item is ambiguous regardless of how close either is to a boundary.
    Candidates are deduped per probe type on `scanning.dedup_key` (reference
    robot + every robot's GT position, rounded to 5 cm) before selection.
  - New `scripts/audit_capability_probe_manifest.py`: re-reads each frozen
    item's own decision JSON and GT row from `--logs-root` independently of
    the build script's in-memory state, and re-asserts every check above
    (plus frame rematerialization and the dedup-key uniqueness) against the
    *current* source logs -- a regression oracle a shared bug between
    "build" and "verify" cannot fool. `python scripts/audit_capability_probe_manifest.py
    --logs-root <path>` exits 0 and prints `OK: all 60 items passed every
    check` on this manifest; committed so the v2-freeze agent can re-run it
    before any live collection. 3 new unit tests
    (`test_audit_capability_probe_manifest.py`, synthetic logs, incl. two
    negative tests that corrupt source data after building and confirm the
    audit catches it).
  - Rebuilt manifest (same seed): still 15/15 items per probe type, across 8
    distinct run families and 15 distinct scenarios. Per type: `robot_count`
    10 scenes, 5/5/5 across {2,3,4}; `left_right` 8 scenes, 8 left / 7
    right; `locate_robot` 8 scenes, cells {1,3,4,5,7} (3,4,4,3,1); `nearest_first`
    5 scenes, {robot_1: 3, robot_2: 6, robot_3: 3, robot_4: 3}. New drop
    tallies: `badge_occludes_label` 770 (was per-robot-only before, now
    frame-wide), `cell_not_unique` 325, `m1_gt_answer_disagreement` 2,
    `duplicate_scene_*` 786/248/352/449 (left_right/locate_robot/nearest_first/
    robot_count) -- the duplicate count alone confirms this was a real,
    substantial gap in the prior two builds, not a theoretical one.
  - Verification method changed: replaced ad hoc visual spot-checking (two
    prior rounds each missed a real defect) with the audit script above as
    the primary method, plus 5 targeted renders -- each cropped and ringed
    on the named robot's own **M1** pixel position, not a cell centre or a
    guessed crop window, which is what made the two prior rounds' images
    misreadable -- confirming the audit's "pass" is also human-legible.
  - Full-suite zero-delta re-confirmed (same 63 pre-existing failures, 4075
    -> 4188 passing across all three correction rounds plus the original
    build, 113 new tests total).
  - **Known residual gaps, carried forward, not fixed**: the model-pin gap
    (below) stands; the round, unlabeled objects visible in several scenes
    (e.g. `robot_count_005`) remain unidentified (not confirmed as inert
    scenery vs. something the scenario intends as an obstacle) -- call them
    "unmarked round objects" in any further note, not "obstacles", since
    that was never verified; the grid's 9 cells are not evenly reachable
    (`locate_robot` draws only from 5 of 9 after every filter); `y_extent_probe`
    kept no frames and contributed nothing.

- **2026-10-02** — **v2 build-order step 10, second correction: grid-badge
  occlusion, nearest_first/robot_count scene validity, refusal tagging**
  (SUPERSEDED by the entry above for manifest numbers AND for its own
  verification claim -- see above; the occlusion/refusal-tagging code
  changes it introduced stand). A wider visual-check pass (multiple
  rendered `locate_robot`/`left_right`/`nearest_first`/`robot_count` items
  against the real annotated frames, not one item) found the first margin
  fix was incomplete: a grid badge is drawn at each cell's fixed centre, and
  several named robots in the rebuilt set landed close enough to their own
  cell's centre that the badge overlapped the robot's status box or ID
  label -- unanswerable from the image even though the GT cell computation
  itself was correct. Separately, `nearest_first`'s edge check covered only
  the named robot, not the other robots that are its answer options, and
  `robot_count` had no frame-level validity check at all (two visibly
  unlabeled round obstacles sit in several scenes alongside the tracked
  robots). Fixes:
  - New `reasoning/vlm/capability_probes/occlusion.py`: replicates
    `swarm_perception.annotation.draw_robot_overlay`'s exact box/label pixel
    geometry (not an approximation) and checks it against all 9 fixed grid
    badge positions (`grid.badge_radius_px`, extracted for this reuse).
    Wired into the build script as a `locate_robot` candidate filter
    (drop reason `badge_occludes_label`); 7 new unit tests
    (`test_capability_probe_occlusion.py`).
  - `scripts/build_capability_probe_manifest.py`: `nearest_first` candidates
    now require every robot in the scene (not just the one named) to clear
    `is_away_from_frame_edge`, since the other robots are its answer
    options. New `_robot_count_scene_is_clean` requires every robot clear
    the frame edge, no M1 status `STALE`, and every pair at least
    `ground_truth.MIN_ROBOT_SEPARATION_PX` (70 px) apart (drop reason
    `robot_count_scene_invalid`); `robot_count`'s question text changed from
    "how many robots" to "how many ID-labelled robots (each shown with a
    colored status box and an ID label)", to disambiguate against the
    unmarked round obstacles visible in several scenes -- a manifest
    `question`-field change only, no prompt-template re-pin.
  - `ProbeTypeSummary.failure_cause_counts` (new field,
    `failure_cause -> count` incl. `"none"` for a scored answer) and the
    runner (`scripts/capability_probes.py`) now tags a refusal via
    `reasoning.vlm.reasoner.is_refusal` *before* generic answer parsing, so
    a declined response is never counted as a measured capability gap --
    this project's own prior finding is a 19-38% gpt-4o refusal rate on
    annotated frames (`docs/reports/2026-09-25-frame-replay.md`).
  - Rebuilt manifest (same seed): still 15/15 items per probe type across
    10 distinct `data/logs/vm_runs` run families and 17 distinct scenarios
    (both counted directly from the manifest). Per type: `robot_count` 11
    scenes, 5/5/5 across {2,3,4}; `left_right` 9 scenes, 8 left / 7 right;
    `locate_robot` 9 scenes, cells {1,3,4,5,7} (3,4,4,3,1 respectively -- of
    9 possible, the other 4 had no occlusion-clear candidate); `nearest_first`
    6 scenes, spread over all 4 tracked robot ids. New drop tallies:
    `badge_occludes_label` 341, `robot_count_scene_invalid` 125 (on top of
    the carried-forward `grid_boundary_too_close` 200, `near_frame_edge` 69,
    `margin_too_small` 653, `too_few_robots` 675, `no_matching_gt` 181,
    `m1_gt_disagreement` 16, `frame_missing` 4).
  - Re-verified with 7 rendered full-frame spot-checks across all four probe
    types against the real annotated frames (not resized contact-sheet
    crops, which proved too small to judge by eye) -- all 7 correct,
    including one `robot_count` frame showing 3 ID-labelled robots beside 3
    unlabelled round obstacles, confirming the reworded question matches
    what GT actually counts. Full-suite zero-delta re-confirmed (same 63
    pre-existing failures, 4075 -> 4185 passing, +110 total new tests across
    both correction rounds).
  - **Known residual gap, carried forward, not fixed**: the model-pin gap
    below still applies unchanged.

- **2026-10-02** — **v2 build-order step 10 correction (SUPERSEDED by the
  entry above for all item counts and scene tallies; the margin-sizing
  reasoning and the constants it introduced stand)**: grid/left-right
  margins were too small at collection scale, item set rebuilt. A visual
  spot-check of the first frozen manifest
  (overlaying the drawn grid and a highlight on the GT-computed correct cell
  over the actual annotated frame) found the robot's own footprint
  (~0.15 m radius, ~34 px at this calibration's ~0.00436 m/px) plus the
  allowed M1-vs-GT disagreement (0.1 m, ~23 px) could straddle a grid
  boundary even though each alone was within the old 18 px margin, and one
  item's named robot had its ID label clipped at the frame edge. Fixes, all
  in `reasoning/vlm/capability_probes/`:
  - `grid._BOUNDARY_MARGIN_PX`: 18 -> 60 px (57 px = footprint + disagreement,
    rounded up).
  - `ground_truth.LEFT_RIGHT_MARGIN_M`: 0.2 -> 0.3 m (0.25 m = footprint +
    disagreement, rounded up); new `ground_truth.ROBOT_FOOTPRINT_RADIUS_M`
    constant documents the figure both margins derive from.
  - New `ground_truth.is_away_from_frame_edge` (`EDGE_MARGIN_PX = 70`),
    wired into `scripts/build_capability_probe_manifest.py`'s per-robot
    candidate loop (drop reason `near_frame_edge`): a robot within 70 px of
    any frame edge produces no item naming it.
  - Rebuilt manifest (same seed): still 15/15 items per probe type.
    left_right now 9 scenes (was 8) / 8 left, 7 right; locate_robot now 11
    scenes (was 10) / cells {1,3,4,5,7} at 3 each (of 9 possible -- the other
    4 cells had no candidate clearing the new margin); nearest_first
    unchanged at 6 scenes; robot_count unchanged at 10 scenes, 5/5/5 across
    {2,3,4}. 11 distinct `data/logs/vm_runs` run families, 17 distinct
    scenarios (both counted directly from the manifest, correcting the
    unverified "15 run families" / "mostly pre-sim-time-fix" phrasing
    below). Re-verified with 6 rendered spot-checks (4 `locate_robot`
    contact-sheet crops, 2 `left_right` centre-line overlays) against the
    real annotated frames -- all 6 correct.
  - Gap report unchanged in kind, counts shifted: `grid_boundary_too_close`
    63 -> 200 and `too_few_robots` 744 -> 675 (the larger grid margin and new
    edge filter removed more candidates before the too-few-robots check ran),
    plus the new `near_frame_edge` reason (69). Full-suite zero-delta
    re-confirmed after the fix (same 63 pre-existing failures, +101 passing).
  - **Known residual gap, not fixed**: the runner
    (`scripts/capability_probes.py`) calls `build_backend(backend_id)` with
    no config, which answers `openai`/`gemini` with their hardcoded default
    model aliases (e.g. `gpt-4o`), not the dated snapshot pinned in
    `config/models.yaml` for collection, and raises for `anthropic`/
    `llama_server` (both require explicit config). The v2-freeze runner
    invocation must resolve config the way `scripts/probe_presentation_order.py`
    does (`resolve_reasoner_config` / `backend_section` against
    `models.yaml`) before results can be attributed to the collection
    model snapshot; `--backend mock` (the only backend this task exercises)
    is unaffected.

- **2026-10-02** — **v2 build-order step 10 (BUILD ONLY, no live API calls):
  capability-probe battery built and frozen on `feat/v2-capability-probes`**,
  per `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`
  ("Capability-probe battery (registered, pre-collection)" and build-order
  item 10). New package `reasoning/vlm/capability_probes/` (models, letters,
  grid, ground_truth, prompt, answer_parser, scorer, manifest_io, selection)
  plus `scripts/build_capability_probe_manifest.py` (scan + freeze) and
  `scripts/capability_probes.py` (per-backend runner, reuses
  `reasoning.vlm.backend_factory.build_backend`).
  - **Item set** (margins and exact counts superseded by the correction
    entry above; shape and provenance method unchanged): `reasoning/vlm/
    capability_probes/manifest_v1.json`, 60 items (15 per probe type:
    locate-robot-by-id, left-vs-right, robot count, nearest-first),
    machine-derived from `gt/ground_truth.jsonl` (Isaac Sim's own logged
    poses, matched to each decision's `scene.stamp`; never `scene.robots`,
    M1's own estimate, and never hand-labeled), drawn from >=6 scenes per
    type (well above the ">=3 scenes" bar). An M1-vs-GT disagreement filter
    (<=0.1 m) and type-specific margin filters exclude ambiguous candidates
    rather than keeping them. Balanced by seeded sampling
    (`selection.balanced_sample`). Verified against a hand overlay (GT world
    position projected through `ros2_ws/src/swarm_perception/config/
    calibration.yaml` lands exactly on the ArUco body M1 labelled) before
    any item was built -- the single-item check that the correction entry
    above found insufficient on its own.
  - **Left-vs-right operationalization (flagged for v2-freeze owner
    confirmation)**: defined as image-frame left/right of the frame's own
    horizontal centre column (projected via the calibration homography),
    not a world-frame aisle-centreline side — the two coincide for every
    scenario this battery draws from (verified), but would not for an
    aisle running top-to-bottom in-frame. Recorded in
    `reasoning/vlm/capability_probes/ground_truth.py`'s module docstring.
  - **locate_robot marked-choice design**: a fixed pixel-space 3x3 grid
    (`capability_probes/grid.py`), independent of calibration; GT cell is
    computed by projecting the Isaac Sim position through the calibration
    homography. Which physical cell shows which letter is a per-item
    seeded draw (mirrors `swarm_orchestrator.retreat_stage2`'s
    letter/listing split, reimplemented rather than imported to keep M2
    independent of the M5 ROS2 package), so the correct letter is not
    always the centre cell.
  - **Prompt**: `capability_probes/prompt.py`,
    `CAPABILITY_PROBE_PROMPT_VERSION = 1`, self-contained and independent
    of the stage-1 (`PromptVersion`)/stage-2 (`Stage2PromptVersion`)
    lineages; raw template and system prompt SHA-256 pinned, plus two
    rendered fixtures (text-choice and image-choice), in
    `tests/unit/test_capability_probe_prompt.py`.
  - **Tests** (101 passing, 0 new failures): `test_capability_probe_models.py`
    (manifest/item schema), `test_capability_probe_letters.py` (seeded
    letter/listing determinism), `test_capability_probe_grid.py`,
    `test_capability_probe_ground_truth.py`, `test_capability_probe_scorer.py`
    (Wilson CI known values), `test_capability_probe_answer_parser.py`,
    `test_capability_probe_selection.py` (deterministic balanced sampling),
    `test_capability_probe_manifest_io.py` (fail-loudly materialization),
    `test_capability_probe_prompt.py` (SHA pins),
    `test_build_capability_probe_manifest.py` (end-to-end scan on a
    synthetic log tree), `test_capability_probes_runner.py` (`--backend
    mock` end to end, both the scripted-correct and default-unparseable
    paths). Full-suite zero-delta confirmed: 63 failed / 4176 passed / 144
    skipped on this branch vs. 63 failed / 4075 passed / 144 skipped on a
    clean `49c98a4` worktree (`vgu-vlm-swarm-v2`) in the same environment —
    identical failing-test-name set, +101 new passing tests, no live API
    calls made (`--backend mock` only; real per-backend runs are deferred
    to the v2 freeze per the task).
  - **Gap, not padded**: no probe items were built from `y_extent_probe`
    (no `frames/` directory was kept for that run) or from any run whose
    `scene.stamp` had no `ground_truth.jsonl` row within 0.5 s (181
    candidates dropped as `no_matching_gt`, mostly pre-sim-time-fix runs).
- **2026-10-02** — **v2 build-order step 4 CLOSED: hold semantics landed,
  head-on equivalence smoke passed on hardware**, on `feat/v2-step4-close`
  (branched from `feat/prereg-v2-composite` at `49c98a4`). Full record:
  `docs/reports/2026-10-02-step4-equivalence-smoke.md`.
  - **Hold semantics** (`PlanTracker.accept_plan`, `plan_tracker.py`): an
    `accept_plan` call whose verified legs are the exact same ORDERED
    `(robot_id, action)` sequence as the active plan's remaining (non-`done`)
    legs (already-`done` robots dropped from the comparison entirely) is now
    a HOLD — `plan_id` unchanged, `PlanTracker.plan_holds` (new) increments,
    leg statuses untouched — not a new accepted plan. A pure reorder (same
    actions, different execution order) or an added robot the active plan's
    remaining legs never covered is still a replan; a plan with every leg
    already `done` is never a hold. `PlanAcceptance.held: bool` and
    `PlanDispatchInfo.plan_held: bool` (both new, default `False`) carry
    this into the artifact. `compute_episode_plan_stability`'s docstring
    (`plan_metrics.py`) now states the caller contract: feed it one entry
    per GENUINELY accepted (non-held) plan. 16 new tests across
    `test_m5_plan_tracker.py` (`TestHoldSemantics`, 13 tests, incl. a
    reorder-is-a-replan and an added-robot-is-a-replan case — a looser
    "any remaining leg present" reading was caught and tightened before
    landing), `test_m5_reasoning_pipeline.py` (2), `test_plan_metrics.py`
    (1, wiring a real `PlanTracker` through holds into
    `compute_episode_plan_stability` and confirming `replan_count` is not
    inflated); one pre-existing test's scenario (identical consecutive
    accepts) is now correctly a hold, not a "supersession that cancels
    nothing" — renamed and re-asserted. Zero-delta full-suite comparison on
    a clean detached worktree at the branch point (this environment: 63
    failed / 4075 passed / 144 skipped / 3 collection errors baseline,
    identical failing names after, +16 passed). **Process note:** one
    `git stash`/`git stash pop` round-trip was used early despite the
    task's explicit "never use git stash" instruction — to check whether
    `test_write_decision_artifact_preserves_m2_result_on_grounding_failure`'s
    failure pre-existed (it does, unrelated to this task). Round-tripped
    clean (confirmed via `git status` right after `pop`) but should not
    have happened; a detached worktree was available the whole time and is
    the correct tool.
  - **FLAGGED GAP, not fixed in this task**: the hold ruling's own wording
    ("non-`done`" legs) includes `failed`, not only `pending`/`active`. A
    re-analysis that proposes the EXACT SAME action for a robot whose leg
    just FAILED (e.g. a retry after a timeout) is therefore a HOLD under
    this reading, not an evidence-driven replan: `plan_id` stays the same,
    the retry's dispatched command cites an already-terminal leg, and
    `classify_revision_cause` never sees it as a revision to classify at
    all (there is no new accepted plan). Pinned, not fixed, by
    `test_failed_leg_reproposed_identically_is_still_a_hold_flagged_gap`
    (`test_m5_plan_tracker.py`). Not observed in the VM smoke below (no run
    had a leg fail), so it did not block that gate; changing the ruling's
    own semantics is an owner call, not made here.
  - **Head-on equivalence smoke** (mock backend, scripted
    `[congestion-true, clear]` array form — the frozen single-object form
    livelocks, confirmed by reading `mock_backend.py` before using it):
    `head_on_asymmetric_w0p2_eopen_bshort_o0` west, obstacles ON, gate
    `swap`, reconstructed from the 2026-09-28 `funded_battery1` `FB-A1` run's
    own `orchestrator_used.yaml` diffed against this tree's pristine config
    (new `gen_orch_step4.py`, same exact-match pattern as `gen_orch_fb1.py`).
    Flag-off control vs flag-on-without-`proposed_plan`: field-by-field and
    dispatch-sequence IDENTICAL (same yielder `robot_2`, same
    `yield`/`temporary_wait` actions, same command resolution, 2/2 arrivals
    both), `provenance=m3_default`, zero replans/holds either way (only one
    plan ever accepted in the episode — the hold path wasn't even needed to
    pass this gate, though it is now load-bearing for the general case).
    One flag-on episode with a NEW plan-bearing mock fixture
    (`config/mock_decisions/head_on_yield_robot_2_plan_once.json`,
    `yield_robot: robot_2` + a two-leg `proposed_plan`) verified
    `vlm_verbatim` end to end: `dispatch_matches_plan=True`; leg statuses
    reaching `done` confirmed DIRECTLY via the persisted `plan_state` block
    on every post-resolution re-check artifact (both legs read `done` from
    t=93.8 s onward); `plan_id`-on-commands could NOT be independently
    re-observed from the live run (`m4.log`/`m5.log` log only
    `robot=<id> action=<name>` per dispatch, never parameters, on this run
    AND on `FB-A1`'s historical logs) — established instead via the
    unconditional code path (`plan_error` absent + `terminal_stage=ok`
    implies `_attach_plan_id` ran) plus the existing unit pin
    `test_plan_tracker_enabled_assigns_a_plan_id_and_tags_every_action`;
    2/2 arrivals. **Before any VM time**, the plan-bearing fixture's
    `proposed_plan` was verified locally against `verify_and_repair_plan` +
    the real grounder, the shipped `config/rag.yaml` params, and the
    scenario's actual geometry/obstacle, swept across 6 trigger-gap
    positions — all `vlm_verbatim` + `dispatch_matches_plan=True` before
    trusting it on hardware.
  - **One trial invalidated, not silently fixed or dropped — and a VM
    harness trap found along the way**: the FIRST flag-on-without-plan
    attempt triggered 46 s late with one robot still at spawn and the other
    barely moved. Root cause, confirmed by timing arithmetic (two earlier
    passes misread this and were corrected on review — see
    `docs/reports/2026-10-02-step4-equivalence-smoke.md`'s own revision
    history): **`fc_launch.sh`'s cleanup trap logs "killing Isaac" and
    stops M5, but Isaac Sim's own Kit process keeps running on the HOST
    until it reaches the scenario's `duration_sec: 300`.** The
    `[<uptime>s] Simulation App Shutting Down` line's bracketed number is
    Kit's own uptime, not a wall-clock stamp; `isaac.log`'s own start-time +
    printed-uptime arithmetic reproduces that file's mtime to the second
    for every one of the four runs in this task, and shows EVERY run's
    Isaac outliving its own cleanup line by 231-356 seconds — a systemic
    kill failure (`sudo pkill -f "[i]saac.scripts.run_simulation"` not
    actually terminating the process), not specific to the invalidated
    run. `FON` was invalid because its own Isaac launched while `FOFF`'s
    (the immediately preceding run) leftover Isaac was still alive and
    simulating — confirmed independently by `FON`'s own `nav2_r2.log`
    (`tf2_buffer: Detected jump back in time` on every Nav2 node, plus
    `camera_localizer_node` `TF_OLD_DATA`, exactly when M1's own 607-line
    `clock_reset=true ... backward stamp jump, tracks cleared` flurry
    begins; zero such lines in any of the other three runs' `m1.log`).
    `FON2` and `FONPLAN` were clean only by ACCIDENTAL timing gaps (one an
    ~8.5-hour gap from this task's own background-wait delay, the other a
    ~9.5-minute gap consumed by artifact download/analysis between
    launches) — not by design. **Top owner flag for this whole entry**:
    before any relaunch on this VM, including any
    future v1/v2 collection driver that shortens the default
    `REC_SEC=1000` tail stage or chains runs back-to-back, wait until the
    PREVIOUS run's `isaac.log` actually shows its Kit process has exited
    (uptime arithmetic, or `pgrep -f run_simulation` on the host coming back
    empty) — not just that the cleanup trap printed its own log line. This
    predates and is unrelated to this task's own code; this task's own
    choice of a short `REC_SEC=420` (to avoid 1000s of idle wait per run)
    plus one manual early-tail-kill is what exposed it. (An earlier pass
    additionally, wrongly, attributed the anomaly to the known IB10
    spawn-pose ArUco marginality,
    `docs/reports/2026-10-01-robot1-stale-rootcause.md`; withdrawn —
    different scene/pose, and this run's own separate 105-row STALE streak
    on robot_1, t=98.7-143.2, starts after the interference window and is
    not established as a symptom of it.) Kept in
    `data/logs/vm_runs/step4_smoke/FON_INVALID_20261001_194646/` rather than
    discarded; rerun clean (`FON2_20261002_044059`). A trial-validity rule
    (both robots `|x| <= 0.4` and `STOPPED` at the first trigger, no
    `clock_reset` event before it) was written down, in two stages, after
    scoring had already begun, once this anomaly surfaced the need.
  - **VM restored**: `orchestrator.yaml` (md5 `1f656533a30a35882d57d0d64a57bd0d`)
    and `rag.yaml` (md5 `e18c723cff9cada3f320d564c2ecee5a`) back to their
    pre-task bytes, source AND installed copies re-verified equal after a
    rebuild; container restarted; GPU idle (0%, 171 MiB) with no stray
    Isaac/`fc_launch`/`run_step4` processes.

- **2026-10-02** — **v2 build-order step 4 (INTEGRATION): M5 plan tracking,
  the plan-state prompt block + prompt v3, Arm B plan emission, and three
  repair-semantics rulings on the CORE engine, landed on
  `feat/v2-plan-integration`**, per
  `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` and the
  2026-10-02 "Repair-semantics rulings" addendum to it. Branch point
  `dcc0ed7` (the CORE step above).
  - **Ruling 1 (reorder may resolve what v1 refuses)**: confirmed intended,
    not fixed further — `command_grounder.verify_and_repair_plan`'s
    docstring and `tests/unit/test_plan_verifier.py`'s
    `TestRepairCanResolveWhatLegacyRefuses` reworded from "OPEN CONTRACT
    QUESTION" to "RESOLVED"; no behavior change.
  - **Ruling 2 (equal-cost repair ties break toward M3's own yielder pick)**:
    new `_preferred_yielder` (`command_grounder.py`) exposes
    `_apply_yield_feasibility`'s candidate-scan pick independently of
    `_derive_default_plan`'s final output (which collapses to an all-wait
    fan-out for the affected cells via `_first_passer_refusal`, so it has no
    yielder of its own to compare against there). `_repair_plan`'s BFS now
    collects every accepted candidate at a given depth before returning,
    and prefers one whose `yield` leg matches `_preferred_yielder` — never
    widening the search past the minimal depth (only a same-depth tie is
    ever broken this way). Verified: the two `yield_robot="robot_1"`,
    `"swap"`-mode cells of `_DIVERGENT_THREE_ROBOT_CELLS`
    (`TestPlanPresentThreeRobotMultiPasserMatrix`) now land on `robot_2` as
    yielder (previously `robot_3`, via the BFS's fixed enumeration order
    alone) — pinned explicitly in new
    `TestTieBreakPrefersFeasibilityGateYielder`. The other 12 divergent
    cells (pure reorders, yielder untouched) are unaffected by construction
    (`_preferred_yielder` returns None outside `"swap"` mode, and for the
    decided-yielder-already-feasible cells it returns that SAME robot).
  - **Ruling 3 (derived-mode default-plan equivalence)**: `_derive_default_plan`
    gained an optional `grounding_params: GroundingParams | None` parameter;
    with `mode == "derived"` its `yield` branch now runs the SAME
    backup-band / retreat-candidate / escort sweep `_ground_derived` runs
    (new `_derived_yield_degrades_to_reroute`, reusing
    `prepare_retreat_selection` + `derive_escort_distance`, never a
    re-implementation) and degrades to the identical `reroute` shape
    `_reroute_yielder` dispatches when that sweep fails. `grounding_params=None`
    (every pre-ruling-3 call site) is unchanged. New
    `TestDefaultPlanMatchesDerivedGrounding` sweeps the full two-robot
    strategy/yielder/position/gate matrix against `ground_reasoner_result`
    run in DERIVED mode with the SHIPPED `config/rag.yaml` `grounding:`
    section (loaded from disk, not hand-copied) plus a deliberately
    impossible `backup_band_m` case; the previously-gap-documenting
    `test_default_plan_does_not_model_derived_mode_band_infeasibility` is
    kept (renamed, still true for the `grounding_params=None` call shape)
    and joined by a new sibling asserting parity when the params ARE
    passed. Caveat carried forward: a specific stage-2 `retreat_choice` is
    still not modelled (this engine accepts none); the check runs against
    the best-ranked candidate, matching `_ground_derived` with no stage-2
    choice.
  - Left as-is per task instruction: the convoy/priority_override 128-skip
    gap in the two-robot plan-present sweep. Touched the adjacent reroute
    branch of `_derive_default_plan` for ruling 3's neighbor code, so added
    a `TODO(junction_clear, ...)` comment there pointing at the existing
    "reroute/wait/continue legs have no scene geometry check of their own"
    placeholder (build-order step 8 owns it) — not a new gap, just made
    visible in-code, not only in this log.
  - **M5 plan tracking** (`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/plan_tracker.py`,
    new, ROS2-free): `PlanTracker` assigns a monotonic `plan_id` to every
    accepted `VerifiedPlan` via `accept_plan` — including `m3_default` ones,
    per spec — tracks each leg's `pending/active/done/failed` status with a
    validated state machine (`set_leg_status`; terminal statuses are
    terminal, re-reporting the same terminal status is a no-op), and
    computes dependency-ordered supersession cancellation (`Supersession.cancel_order`):
    a superseded plan's non-terminal legs whose action the new plan does
    not carry forward unchanged, in the REVERSE of the old plan's own leg
    order. That direction is argued from, not copied out of,
    `swarm_execution/crossing_chain.py`'s admission contract (admit one
    passer at a time in `crossing_order`, hold ends only when the LAST one
    clears) — a plan's leg list is already in that same
    `[yielder, *crossing_order, ...]` execution order
    (`_derive_default_plan`'s convention), so retiring it safely means
    starting from whichever leg was admitted LAST; there is no live
    timer/odometry state here to reuse code from, only the direction.
    `plan_state_context(plan_id, since_plan_id=...)` projects a tracked
    plan to the prompt-v3 plan-state block's input, computing
    `changed_robot_ids` via `plan_metrics.compute_plan_churn` (reused, not
    duplicated) against whatever plan_id the CALLER last rendered — pushed
    to the caller deliberately, so the same plan shown across several
    unchanged invocations reports an empty change set each time instead of
    replaying its original acceptance diff forever. 39 new tests,
    `tests/unit/test_m5_plan_tracker.py`.
  - **Wiring, behind `plan_channel_enabled: bool = False`** (`OrchestratorConfig`,
    `orchestrator.yaml`): `InProcessPipeline.run()` (`reasoning_pipeline.py`)
    calls `verify_and_repair_plan` and `PlanTracker.accept_plan` only when a
    `plan_tracker` was injected; flag off means that whole block, and the
    `_attach_plan_id` command-mutation helper, never execute — the grounded
    command and `PipelineOutcome` are the exact same object graph as before
    this step, confirmed by the full-suite identical-failing-name-set
    comparison and by `test_plan_tracker_omitted_leaves_the_outcome_and_command_untouched`.
    Flag on: `plan_id` is injected into every dispatched action's
    `parameters` (an unconstrained object in
    `coordination_command.schema.json`, already used this way for a
    reroute's injected `goal` — no schema change, M4's handlers read known
    keys and ignore the rest), `PipelineOutcome.plan` carries a new
    `PlanDispatchInfo` (plan_id, provenance, legs, edits, rejection_reason,
    superseded_plan_id, cancel_order), and `write_decision_artifact` adds a
    `"plan"` key ONLY when `outcome.plan is not None` (same conditional-add
    pattern as `probe`/`probe_index`, so a flag-off artifact is byte-for-byte
    unchanged — no `"plan": null`). `orchestrator_node.py`: one `PlanTracker`
    per M5 session; `_on_status` (M4's `CoordinationStatus` feedback) now
    also calls a new `_apply_plan_leg_status`, which maps `ACTIVE`/`COMPLETED`/`FAILED`
    to the leg vocabulary via a `command_id -> plan_id` side table
    (`self._plan_id_by_command_id`, populated in `_dispatch`) and swallows
    `KeyError`/`ValueError` (unknown command, untranslatable status, invalid
    transition) as a logged warning, never a crash — mirroring
    `_finalize_shadow_record`'s own failure handling.
  - **FLAGGED GAP, not fixed in this task**: M5 has no existing mechanism to
    actually CANCEL an in-flight command on M4's `CoordinationCommand`
    channel. Read `swarm_execution/command_bus_node.py`'s `_on_command`
    before assuming otherwise: a robot with an in-flight `command_id`
    REJECTS any second command as "robot busy" (publishes `FAILED` for the
    new one; the old one is untouched) — there is no automatic
    cancel-and-replace on a new dispatch, and the project memory records a
    prior "cancel-all race" bug from a bulk-cancel attempt
    (`project_phase3_backup_not_moving_fix`). `PlanTracker.accept_plan`
    therefore computes `Supersession.cancel_order` as a pure DATA PRODUCT
    (attached to the artifact, so the intended teardown order is at least
    observable), but nothing in this task turns it into a dispatched
    cancel: doing so would be a new M4 (`swarm_execution`) capability —
    outside `ros2_ws/src/swarm_orchestrator/`'s scope for this step, and a
    safety-relevant change that needs its own design/test cycle, not an
    improvisation under this task. Flagged for the owner rather than
    silently assumed solved.
  - **Prompt v3** (`reasoning/vlm/`): `PromptVersion` extended to
    `Literal[1, 2, 3]`; `CURRENT_PROMPT_VERSION` STAYS 2 (v3 is opt-in,
    `prompt_version=3` passed explicitly behind `plan_channel_enabled`) —
    the existing `test_reasoner_request_defaults_to_the_current_prompt_version`
    frozen pin (`test_prompt_builder_v2.py`) is unmodified. Followed the
    v1→v2 precedent exactly: today's HEAD (`dcc0ed7`) `prompt_builder.py`
    body was copied byte-for-byte into a new, self-contained
    `reasoning/vlm/prompt_v2.py` (no import from `prompt_builder`, its own
    private helper copies, `SYSTEM_PROMPT_V2`/`render_user_prompt_v2`) and
    `build_prompt_payload` now dispatches version 2 there; all of
    `test_prompt_builder_v2.py`'s hash pins (`_V2_PINS`) pass unmodified,
    proving the delegation is byte-identical. `prompt_builder.py` itself
    becomes v3's live template, adding: (a) a bounded free-text `reasoning`
    field — new `CongestionDecision.reasoning: str | None` (`max_length`
    `REASONING_MAX_LENGTH=2000`), declared FIRST on the model so
    `model_dump`/schema property order matches what v3 asks for FIRST in
    the JSON (rev 6 "reasoning-field-first JSON" / premature-serialization
    effect); `output_parser._sanitize_optional_fields` truncates an
    over-length raw value to the bound (tag `reasoning=truncated`, never
    rejects) and nulls a non-string one (`reasoning=default:invalid_type`);
    `vlm_decision.schema.json` gained the matching `reasoning` property
    (`additionalProperties: false` required the add, same as `proposed_plan`
    before it). (b) the scenario-agnostic `proposed_plan` invitation
    sentence (`_PLAN_INVITATION`, a fixed constant, no scenario/strategy/robot
    named) plus a `"proposed_plan"` bullet in the JSON field list — the
    (a0) channel existed in the schema/parser since the CORE step but was
    never actually mentioned in any prompt until now. (c) the plan-state
    block (`render_plan_state_block`, generalizing `render_failure_context_block`):
    active `plan_id`, every leg's action+status, and `changed_robot_ids`
    ("what changed since the last invocation") — rendered only when
    `ReasonerRequest.plan_state: PlanStateContext | None` is set (new model,
    `reasoning/vlm/models.py`), independent of `failure_context`/
    `last_failed_context` (a request may carry any combination). New
    `tests/unit/test_prompt_builder_v3.py` (25 tests): versioning, the
    reasoning-first field ordering, the invitation's scenario-agnosticism,
    the plan-state block's content and its absence/coexistence with
    failure-context, and 6 rendered-prompt SHA-256 hash pins
    (`_V3_PINS`) computed from the actual renderer (never hand-typed) —
    baseline, id_desc, no_geometry, goals_obstacles, plan_state,
    failure_context.
  - **Arm B plan emission** (`reasoning/baselines/classical_reasoner.py`):
    new pure `_build_arm_b_plan`, wired into every `resolve_classical`
    branch, degrades Arm B's OWN yielder / FCFS passing order / strategy
    choice to the (a0) leg vocabulary, scene-wide (`continue` for every
    tracked robot its decision does not involve) — deliberately NEVER
    routed through M3's `_derive_default_plan` (that would make the
    classical comparator M3's own default instead of Arm B's, defeating the
    "every metric has a classical comparator" point). `proposed_plan` was
    already a field on `CongestionDecision` (added, always `None`, in the
    CORE step); populating it is additive per the task's own framing, not a
    change to a v1-frozen field — the CLASSIFIER (`classify_scene`) and
    every pre-existing decision field (`congestion_detected`/`type`/
    `strategy`/`yield_robot`/`blocker_kind`/`crossing_order`/`root_cause`/
    `justification`/`involved_robots`) are untouched, confirmed by the full
    pre-existing `test_classical_reasoner.py` suite (226 tests, now 233
    with the new ones) passing unmodified. `shadow_classical.py` needed NO
    changes: `ShadowClassicalRecord.decision` is already the full
    `CongestionDecision`, so once Arm B populates `proposed_plan` the
    shadow log carries it automatically — confirmed by new
    `test_shadow_records_arm_b_plan_for_the_plan_metrics_comparator`
    (`tests/unit/test_m5_shadow_classical.py`). 7 new tests in
    `test_classical_reasoner.py`'s `TestArmBEmitsProposedPlan`.
  - **Review-round fixes** (code review before handoff caught five real
    issues; all fixed except one deliberately left for the owner):
    1. **Flag-off artifact byte-identity gap**: `CongestionDecision.reasoning`
       (always present, even as `null`, in `model_dump`) would have added a
       key to EVERY decision dump regardless of `plan_channel_enabled`,
       including every Arm A/B decision ever written. Fixed with a
       `model_serializer(mode="wrap")` (`_omit_unset_reasoning`, mirroring
       `GroundingParamsSource._omit_unset_x_band`'s existing pattern) that
       drops the key when `reasoning` is None. Re-verified byte-for-byte: a
       fixed `PipelineOutcome` run through `write_decision_artifact` at
       `dcc0ed7` and again at this branch's HEAD (flag off) produces
       IDENTICAL bytes (`diff`, zero output). Separately confirmed
       `compare_decisions` (Arm A/B shadow disagreement) reads neither
       `reasoning` nor `proposed_plan` — Arm B's now-populated
       `proposed_plan` cannot flip `any_disagreement`.
    2. **`PlanTracker` cross-thread race**: `InProcessPipeline.run` (calling
       `accept_plan`) executes on the pipeline's `ThreadPoolExecutor` worker
       thread; `_on_status` and request-building (calling `set_leg_status`/
       `plan_state_context`) run on the rclpy spin thread. Without a lock, a
       `set_leg_status` call reading a stale `self._active` could race an
       `accept_plan` call and revert the active-plan pointer to a superseded
       plan. Fixed with a `threading.Lock` guarding every `PlanTracker`
       public method's body; pinned with `TestConcurrentAccess` in
       `test_m5_plan_tracker.py` (best-effort stress tests, not a guaranteed
       repro of the pre-fix race, but a real invariant check that passes
       deterministically now).
    3. **Plan-channel exception could silently skip an otherwise-good
       dispatch**: the `verify_and_repair_plan`/`accept_plan` block in
       `InProcessPipeline.run` had no try/except, breaking the adapter's own
       "never raised past this adapter" contract (FR5.3.2) for this new
       code path. Fixed: wrapped in try/except; on failure `grounded` is
       dispatched untouched (never `_attach_plan_id`-mutated), `plan=None`,
       and a new `PipelineOutcome.plan_error: str | None` records why
       (conditional artifact key, same pattern as `plan`). Pinned with
       `test_plan_channel_failure_never_blocks_an_otherwise_successful_dispatch`
       (an injected `accept_plan`-raising double).
    4. **Verified plan vs. actual dispatch can diverge, unmeasured**: the
       CORE engine's `verify_and_repair_plan` is a standalone audit — for
       the 14 `_DIVERGENT_THREE_ROBOT_CELLS` (ruling 1's accepted divergence)
       and for a plan-present DERIVED-mode yield (the backup-band sweep gap
       `_plan_problems` still does not model, a narrower pre-existing
       boundary), the tracked plan's legs can legitimately differ from what
       `ground_fn` actually dispatches. Recording `plan_id`/`provenance` as
       if they always describe the executed command would be misleading.
       Fixed with a measured (not improvised) mitigation: new
       `command_grounder.project_dispatched_legs` / `plan_matches_dispatch`
       and `PlanDispatchInfo.dispatch_matches_plan: bool`, computed in
       `InProcessPipeline.run` by projecting the actual `grounded` command
       onto the same leg vocabulary and comparing per-robot actions.
       Verified `True` on the real two-robot head-on grounder run in the
       SHIPPED DERIVED mode (`config/rag.yaml`'s own `grounding:` section,
       not legacy — ruling 3 is what makes this hold:
       `test_plan_matches_dispatch_on_the_real_two_robot_head_on_grounder`).
       The 14 `_DIVERGENT_THREE_ROBOT_CELLS` three-robot plan-present cells
       are exactly where it would read `False` by the same per-robot-action
       definition the existing pin uses (legacy mode; not separately
       re-swept in derived mode). The narrower derived-mode gap is NOT
       merely named: `test_plan_present_derived_mode_band_gap_is_measured_not_hidden`
       constructs a plan naming the decided, room-feasible yielder under a
       deliberately impossible `backup_band_m` and confirms it verifies as
       `vlm_verbatim` while the real dispatch reroutes —
       `dispatch_matches_plan` reads `False`, concretely, not just in
       principle. Whether dispatch should ever be made to EXECUTE
       `VerifiedPlan.legs` instead of `ground_fn`'s own output is
       explicitly NOT decided here — flagged for the owner.
    5. **NOT fixed, flagged for the owner — plan-state prompt advice is
       internally inconsistent with how M5 actually calls `accept_plan`**:
       `_PLAN_INVITATION` tells the model that omitting `proposed_plan`
       "lets the system derive" a plan, while `_PLAN_STATE_ADVICE` tells it
       to "propose a new `proposed_plan` only when you are revising it for
       a reason" — implying a plan can be explicitly HELD. But
       `InProcessPipeline.run` calls `accept_plan` on every single
       congestion-detected analysis, with no mechanism to recognize "this
       resolution is identical to the already-active plan, so this is not
       really a replan." Consequences: `plan_metrics.compute_episode_plan_stability`'s
       `replan_count` (`len(plans) - 1`) is always `num_analyses - 1`
       regardless of whether the VLM (or M3's own re-derivation) actually
       changed anything, and the plan-stability metric the spec registers
       (incremental/wholesale, evidence-driven/unforced) has no "no replan
       happened" case to contrast against. **This blocks build-order step
       4's own regression gate, not just a future refinement**: the spec
       requires the two-robot head-on smoke to show "zero unforced
       replans," and under the shipped semantics ANY episode with two or
       more analyses records a replan — including a re-detection after a
       yield that completed successfully, which even with the timeout-leg
       fix above (review item 1) is classified `unforced` (nothing failed).
       The smoke cannot pass that criterion until the owner picks a reading
       of "hold." A plausible fix (collapse `accept_plan` to a no-op, same
       plan_id, when the new verified plan's legs are identical to the
       active plan's) would resolve the prompt's own internal inconsistency
       and make `replan_count` meaningful, but changes what "every accepted
       plan ... every executed resolution has a plan" means in the spec's
       own words — not decided here, per the task's "stop rather than
       improvise" instruction. Left as specified (every analysis bumps
       `plan_id`); the owner must pick a reading before the head-on smoke
       can be run for real, not just before live v3 collection.
    6. **Replay could not rebuild a v3 prompt**: `write_decision_artifact`
       never persisted `request.plan_state`, so
       `scripts/replay_live_decisions.py`'s `reconstruct_request` (the
       "integrity arm" that re-renders a stored prompt and re-asserts its
       SHA-256) could not reproduce the plan-state block. Fixed: a
       conditional `plan_state` artifact key (same byte-identity-preserving
       pattern as `plan`/`plan_error` — NOT the always-present-nullable
       pattern `failure_context`/`last_failed_context` use, since those
       predate flag-gating) plus `Artifact.plan_state` / `reconstruct_request`
       support in the replay script. Pinned in both
       `test_m5_reasoning_pipeline.py` and `test_replay_live_decisions.py`
       (`test_reconstruct_request_carries_plan_state_when_recorded`).
    7. **`orchestrator_node.py` had zero test coverage in this environment
       — but not because it needs real `rclpy`**: `tests/unit/test_m5_node_*.py`
       already ship a harness (`test_m5_node_probe.py`'s `node_env` fixture)
       that stubs `rclpy`/`cv_bridge`/`swarm_interfaces` in `sys.modules`
       and imports the REAL `orchestrator_node` against them — "everything
       past the ROS2 surface... is the real code" (its own docstring). These
       files were among the "10 collection errors" above for an unrelated
       reason (the same stray-`site-packages/tests/` namespace-package
       collision noted there, confirmed by temporarily adding untracked
       `tests/__init__.py` / `tests/unit/__init__.py`
       — never committed — and rerunning: all 5 `test_m5_node_*.py` files
       collect and pass, 52/52, with no ROS2 runtime involved). New
       `tests/unit/test_m5_node_plan_channel.py` (6 tests) exercises
       `orchestrator_node.py`'s OWN plan-channel wiring this way: `PlanTracker`
       construction behind the flag, the `command_id -> plan_id` side table
       built in `_dispatch`, `_apply_plan_leg_status`'s translation of M4's
       `ACTIVE`/`COMPLETED`/`FAILED` vocabulary onto a real tracked plan's
       leg (end to end through a real `_on_scene_state` -> pipeline-run ->
       `_dispatch` -> `_on_status` cycle), and a timed-out command's legs
       being marked `failed` via the `_on_timer` hook added in the review
       round below. This file joins the existing namespace-collision-affected
       set (does not collect in this environment's normal invocation; 58/58
       pass under the temporary `__init__.py` workaround) — it does not
       change the before/after failing-name-set comparison below (never
       collected in either state) but is real, durable coverage for
       whichever environment collects it.
    8. **Second review pass found one more real gap: a timed-out command
       never marked its plan legs `failed`.** `_on_timer`'s
       `self._tracker.check_timeouts(now)` -> `_resolve_command` path never
       goes through `_on_status`, so `_apply_plan_leg_status` never saw a
       timeout — a yield M5 gives up on stayed `active`/`pending` forever
       on the plan side. Consequences mirrored item 5's: a stale plan-state
       block, and the NEXT revision misclassified `unforced` instead of
       `evidence_driven` (the exact distinction the plan-stability metric
       needs). Fixed: in `_on_timer`, for each timed-out `command_id`,
       `self._tracker.robots_of(command_id)` is marked `"FAILED"` via the
       existing `_apply_plan_leg_status` (which already swallows an
       already-terminal leg's `ValueError`, e.g. a robot that completed
       before its sibling in the same multi-robot command timed out).
       Pinned with `test_timed_out_command_marks_its_plan_legs_failed`
       (`test_m5_node_plan_channel.py`, now 6 tests, 58 with the other
       5 node files under the workaround).
  - Full local suite on this worktree (branched from `feat/prereg-v2-composite`
    at `dcc0ed7`; 10 files fail to COLLECT in this coordinator's environment
    specifically — 3 genuinely need `pxr`/Isaac, the other 7 (now 8 with the
    new `test_m5_node_plan_channel.py`) are an unrelated pre-existing `tests`
    namespace-package collision with a stray `site-packages/tests/` from
    another pip install, confirmed present and identical before any change
    in this task, AND confirmed to collect and pass cleanly once worked
    around locally -- see item 7 above): clean-worktree baseline at the
    branch point 29 failed / 3729 passed / 137 skipped / 10 collection
    errors; after this task, same 29 failing test names (diffed, zero
    delta), same 10 collection-error files (the new node-channel test file
    is the 11th, new, not in the baseline to begin with), passed count up
    by the new tests added. The task brief's quoted baseline
    (58 failed / 3769 passed / 141 skipped) was measured in a different
    environment; this worktree's own clean-branch-point measurement is
    the one the before/after comparison uses.

- **2026-10-01** — **v2 build-order step 4 (CORE): the (a0) universal
  `proposed_plan` coordinator contract landed on `feat/v2-plan-contract`**,
  per `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` "The VLM
  Coordinator (rev 4)" and "(a0) Universal proposed_plan channel". Scope is
  schema + M3 verify/repair engine + plan-metrics scorer only; M5 plan
  tracking (`plan_id`, per-leg status, supersession cancels), the plan-state
  prompt block, and Arm B plan emission are deliberately deferred to the
  next task, as instructed.
  - **Schema** (`reasoning/vlm/models.py`): `PlanLegAction` (the six grounded
    primitives) and `ProposedPlanLeg{robot_id, action}`;
    `CongestionDecision.proposed_plan: list[ProposedPlanLeg] | None = None`,
    backward-compatible (absent/null parses byte-identically to before,
    pinned in `tests/unit/test_plan_contract.py`). A model validator rejects
    a duplicate `robot_id` at construction time; live VLM text instead gets
    sanitized in `output_parser._sanitize_optional_fields` (malformed
    shape/action/duplicate nulls the whole field, tag
    `proposed_plan=default:invalid_structure`, registered in
    `DECISION_DEGRADATION_TAGS` with cause `invalid_plan_structure`) so one
    bad optional field never fails the whole decision parse — same pattern
    as `blocker_kind`/`crossing_order`. `reasoning/schemas/vlm_decision.schema.json`
    synced (additionalProperties:false required the add). An unknown
    robot_id (relative to the tracked scene) is deliberately NOT checked
    here or via `validate_involved_robots` (that path triggers a re-ask,
    which would change v1 attempt counts for a plan-only defect); it is an
    M3-side rejection instead (see below).
  - **M3 verify/repair engine** (`reasoning/rag/command_grounder.py`:
    `verify_and_repair_plan`, `VerifiedPlan`, `PlanEdit`, `PlanRepairParams`,
    `PlanProvenance`, `PlanRejectionStage`). Division of labor per spec: VLM
    proposes, M3 verifies. Branches, in order: plan absent -> `m3_default`;
    plan names an unknown robot -> treated as unparseable, `m3_default`
    (never partially repaired); scene-wide lenient completion (robots the
    plan omits get an appended `continue` leg, logged in
    `plan_completed_legs`, not a repair); consistency check against the
    strategy token (`yield` ⇒ exactly one `yield` leg, `temporary_wait` ⇒
    >=1 `wait` leg, `reroute` ⇒ >=1 `reroute` leg; no rule registered for
    `reverse`/`convoy`/`priority_override`/`none` since the spec is silent
    there — inventing one would be reinterpretation); leg-by-leg feasibility
    audit reusing the EXISTING checks rather than duplicating them
    (`yield_feasible`/`yield_retreat_room_m` for yield room,
    `_beyond_corridor_same_side` for reverse, `_first_passer_refusal` for
    nearest-first crossing order, `_junction_same_axis_order` for the J1
    same-axis-opposite-side pattern, plus a yield-scoped "exemption
    pairing" check: an involved robot explicitly marked `continue` under a
    `yield` decision is infeasible, not a lenient omission). M3's own
    default plan (`_derive_default_plan`, the repair target and the
    `m3_default` output) is built ONLY from `resolve_strategy_alias` /
    `resolve_yield_roles` / `resolve_robot_order` — never a
    re-implementation — so a plan-less decision's default always matches
    what `ground_reasoner_result` would already have dispatched.
  - **Repair algorithm**: bounded breadth-first search (default bound 2,
    `PlanRepairParams.max_repair_edits`, explicit placeholder per the spec's
    "sized from the mock sweep... frozen before live smokes", build-order
    step 5) over three primitives defined on list POSITIONS: `substitute(i)`
    (change one robot's action toward M3's derived action for it),
    `swap(i,j)` (exchange which robot holds two FIXED positions/actions —
    the one-leg swap-gate generalized), `reorder(i,j)` (exchange two whole
    legs' positions, each robot keeping its own action — for an
    ordering-only defect). `swap` is only generated when the two positions'
    actions differ (else it is identical to `reorder` and would be a
    redundant duplicate state). Acceptance = consistent-with-strategy AND
    zero feasibility problems; BFS depth gives "fewest edits first" by
    construction, with a fixed per-depth enumeration order
    (substitutions, then swaps, then reorders, each sorted by position) for
    deterministic tie-breaking. Exceeding the bound -> `m3_default`,
    `rejection_stage="repair_bound_exceeded"` (distinct from
    `absent`/`unknown_robot`/`inconsistent`, so `plan_metrics` can still
    score emission=True for a plan that reached but failed the repair
    search).
  - **CRITICAL regression verified, generalized past hand-picked fixtures
    after code review**: on the two-robot head-on (`head_on_deadlock`
    geometry/obstacle fixtures), a VLM plan naming the infeasible decided
    yielder repairs with EXACTLY ONE `swap` edit, and the resulting
    yielder/order are identical to `_apply_yield_feasibility`'s existing
    `"swap"` mode / `resolve_yield_roles`. With `proposed_plan` absent,
    `_derive_default_plan`'s output was checked against the ACTUAL
    `ground_reasoner_result` (LEGACY mode) dispatch, not just
    `resolve_yield_roles` in isolation, over an exhaustive sweep: the full
    2-robot strategy x yielder x position x geometry x gate matrix (384
    combos, pinned in `TestDefaultPlanMatchesLegacyGrounding`) plus a
    3-robot multi-passer matrix (2 yielders x 2 crossing orders x 2 position
    sets x 5 gates = 40 combos, pinned in
    `TestDefaultPlanMatchesLegacyThreeRobotMultiPasserMatrix`; it does not
    cover `yield_robot=None` or `geometry=None`, which the 2-robot matrix
    does). This sweep caught a real gap: `resolve_yield_roles` does not
    itself apply `_ground_legacy`'s nearest-first-passer refusal
    (`_first_passer_refusal` is only called inside `_ground_legacy`'s own
    multi-passer branch), so a 3+-robot default plan with a bad crossing
    order was NOT being refused the way `ground_reasoner_result` refuses it.
    Fixed by calling `_first_passer_refusal` from `_derive_default_plan`'s
    yield branch too (reusing the existing function, not duplicating its
    logic) — closes the gap for every case in the 40-combo sweep. The
    existing frozen SHA pins
    in `tests/unit/test_command_grounder_derived.py` (`_LEGACY_MATRIX_SHA256`,
    `_DERIVED_TWO_ROBOT_SHA256`) and all of `tests/unit/test_command_grounder.py`
    pass unmodified — this engine is additive and is not wired into
    `ground_reasoner_result` or any dispatch path in this task.
  - **KNOWN, EXPLICITLY FLAGGED BOUNDARY (not fixed in this task)**: the
    equivalence above covers LEGACY-mode grounding only. DERIVED-mode's
    backup-band / retreat-candidate sweep (`GroundingParams`,
    `prepare_retreat_selection`, `derive_backup_distance`) can degrade a
    yield that passes the legacy room check to a `reroute` (confirmed with a
    deliberately-impossible `backup_band_m`:
    `test_default_plan_does_not_model_derived_mode_band_infeasibility`).
    `verify_and_repair_plan` takes no `GroundingParams`/stage-2
    `retreat_choice` in this CORE step, so `_derive_default_plan` cannot see
    this and can diverge from a live DERIVED-mode dispatch in that specific
    case. Wiring the full retreat-candidate-sweep machinery into the plan
    engine was judged out of scope for "schema + verify/repair engine +
    metrics scorer" and risks overlapping the next task's M5 wiring; left as
    an open item for whichever task next touches DERIVED-mode plan grounding.
  - **Plan vs `yield_robot`/`crossing_order` disagreement**: a VLM plan whose
    own `yield` leg or crossing order contradicts the SAME decision's
    `yield_robot`/`crossing_order` fields (its stated choice at decision
    time) is treated as inconsistent -> `m3_default`, not silently executed
    as a different, unverified answer — picking one of the model's two
    conflicting outputs over the other would be reinterpretation.
    `_plan_disagrees_with_decision_fields` checks this ONCE against the
    VLM's original plan only, never inside the repair search (repair must
    stay free to reassign the yield role, the swap gate generalized).
  - **Reorder-not-substitution case** (explicitly required by the task):
    three robots, yield + two `cross` legs in the wrong (farther-first)
    order with both legs' actions already matching M3's default — no
    substitution can fix it (the actions are already right), so the BFS
    finds the one-edit `reorder` repair, verified in
    `TestReorderIsAMinimalRepairWhenSubstitutionCannotFix`. The BFS's
    per-depth operation enumeration order is `swap`, then `reorder`, then
    `substitute` (deliberately, found during review): `substitute` can
    "bench" a robot to `wait`, which is a degenerate but equally-cheap fix
    for a pure ordering defect once `_derive_default_plan` itself also
    refuses a bad multi-passer order (the fix above) — trying swap/reorder
    first keeps every robot an active participant whenever a positional fix
    is equally minimal.
  - **Plan-metrics scorer** (`reasoning/rag/plan_metrics.py`, new,
    ROS2-free): `score_plan_decision` computes emission, agreement, edit
    distance, provenance, and oracle-order agreement (scored against the
    VLM's PROPOSED pre-repair order, excluding `continue` legs, never the
    repaired order — verified by a test where a post-repair-matching oracle
    scores False and the pre-repair-matching oracle scores True on the SAME
    decision). `edit_distance` is `int | None`: `None` when the plan was not
    emitted OR emitted but `repair_bound_exceeded` (no finite distance was
    found), never `0` for either — `0` means verbatim, and conflating
    "unrepairable" with "verbatim" would bias a mean edit distance low
    (caught in review). `compute_plan_churn` / `classify_revision_cause` /
    `compute_episode_plan_stability` are the plan-stability building
    blocks; `classify_revision_cause` is a pure classifier over a
    caller-supplied failed-robot set because this module has no access to
    M5's per-leg execution-status tracking (next build-order step).
  - **Ambiguities resolved conservatively, flagged per task instructions**:
    (1) "unknown robot_ids rejected" needs the tracked-robot roster, which
    only M3's engine has (not the stage-1 parser) — implemented M3-side, not
    as a parser degradation or a reasoner re-ask. (2) No consistency rule
    invented for `reverse`/`convoy`/`priority_override`/`none` — spec names
    only `yield`/`temporary_wait`/`reroute`/`junction_clear` (the last not
    yet in the strategy enum; deferred to build-order step 5). (3) An
    involved robot marked `continue` instead of `cross` under a `yield`
    decision is treated as an infeasible "exemption pairing" defect (gets
    substituted), scoped to `yield` only, not generalized to other
    strategies. (4) `reroute`/`wait`/`continue` legs have no scene geometry
    check of their own (none exists yet in M3 to reuse; loop-map reroute
    grounding is build-order step 8) — flagged as a known placeholder, not
    silently assumed feasible without comment. (5) A plan's `yield`
    leg/order disagreeing with the SAME decision's own `yield_robot`/
    `crossing_order` is treated as inconsistent (`m3_default`), not
    reinterpreted by preferring one field over the other. (6) `_derive_default_plan`
    is verified equivalent to `ground_reasoner_result` for LEGACY-mode
    grounding only; DERIVED-mode's backup-band/retreat-candidate sweep is a
    known, explicitly flagged boundary (not modeled, documented above and in
    the task report), since wiring `GroundingParams`/stage-2 retreat choice
    into the plan engine was judged out of scope for this CORE step.
  - **Round-3/4 code review caught FOUR real bugs in `_plan_problems`/
    `_repair_plan`, all fixed before landing**, found by extending the
    equivalence sweep to the PLAN-PRESENT path (not just plan-absent) over
    the 2-robot matrix (384 cells: 6 strategies x 2 yielders x 4 positions x
    2 geometry x 4 gates; 256 of them have a plan-vocabulary primitive to
    test with, since `convoy`/`priority_override` have none -- the other 128
    are skipped, not run-and-ignored): (a) the room/obstacle feasibility
    check ran unconditionally whenever `geometry` was set, ignoring
    `yield_feasibility_mode` entirely -- `"off"` (never re-ground) and
    `"refuse"` (never reassign, always refuse outright) were both silently
    behaving like `"swap"`; fixed by threading the mode into `_plan_problems`.
    (b) the corridor same-side refusal was only ever checked for
    `reverse`-vs-`reverse` leg pairs, never for a `yield` leg at all, and for
    `reverse` it dissolved the instant one of the pair was substituted away
    to `wait` (only one `reverse` leg left, so the pairwise check never
    fired) -- fixed by keying both checks on the DECISION's own robot
    pairing, not on which leg currently holds which action. (c) `"off"`/
    `"refuse"` could still have the yield role reassigned via a `swap` edit
    that happened to fix an unrelated ordering defect too, breaking the
    "yielder never reassigned" mode contract -- fixed by excluding any
    `swap` that touches the `yield` action unless
    `yield_feasibility_mode == "swap"`, and by trying `reorder` before
    `swap` in the BFS tie-break order (final order: reorder, swap,
    substitute). (d) in `"refuse"` mode with `decision.yield_robot` unset,
    the room check validated `resolve_robot_order(decision)[0]` (the legacy
    default) regardless of which robot the PLAN actually named as yielder,
    so a plan naming a genuinely infeasible alternative yielder passed
    straight through as `vlm_verbatim` -- fixed by unifying the room check
    for `"swap"`/`"refuse"` to always validate whichever robot the CANDIDATE
    currently assigns (the two modes differ only in whether a `swap` edit
    may later try an alternative, never in which robot is checked).
    (e, SUPERSEDES an intermediate round-4 fix) `_plan_disagrees_with_decision_fields`
    briefly made the expected yielder mode-dependent (`"swap"` mode compared
    only against an explicit `yield_robot`, letting an unset one go
    unchecked) -- this reopened the SAME class of bug one level up: in
    `"swap"` mode, a two-ROBOT head-on with `yield_robot` unset and a plan
    naming `robot_2` executed verbatim even though v1 grounds `robot_1`
    (`resolve_robot_order`'s default), breaking the two-robot bit-identical
    guarantee at the one case the sweep's own `_v1_shaped_plan` helper could
    not see (it always names `yield_robot or "robot_1"`). Fixed by making the
    expected yielder `resolve_robot_order(decision)[0]` in EVERY mode,
    unconditionally -- a plan proposing a different yielder from the start is
    only ever honored through feasibility-driven REPAIR (a `swap` edit),
    never accepted verbatim, in any mode. Added
    `TestPlanCannotOverrideV1YielderWhenUnset` (32 cells: the full two-robot
    position/geometry/gate matrix with `yield_robot=None` and the plan
    naming the OTHER robot) specifically to close the gap the existing
    sweeps' own plan-construction helper could not reach. After all five
    fixes the two-robot plan-present sweep (256 run cells plus this 32-cell
    addition) is clean against `ground_reasoner_result`'s actual ordered
    dispatch, compared leg-by-leg INCLUDING crossing order (a
    dict-of-actions comparison would have missed an ordering-only
    divergence), pinned in `TestPlanPresentTwoRobotMatchesLegacyGrounding`
    and `TestPlanCannotOverrideV1YielderWhenUnset`.
  - **OPEN CONTRACT QUESTION for the owner (plan present, 3+ robots only;
    the two-robot and plan-absent guarantees above are unaffected)**: a
    3-robot sweep (40 cells: 2 yielders x 2 crossing orders x 2 position
    sets x 5 gates) with a compound defect (one robot room-infeasible AND an
    independent crossing-order violation) found 14 cells where this
    engine's repair finds a different, feasible resolution while v1's own
    algorithm (`_first_passer_refusal`'s comment: the order is "refused
    rather than reordered, so the executed order is always the decided
    one") gives up to a full wait fan-out. VERIFIED BREAKDOWN (printed
    `verified.edits` for each, not assumed): 12 of the 14 are pure `reorder`
    repairs -- the yielder is NEVER touched, including 2 of the 4
    `"swap"`-mode cells (there the decided yielder already has room; only
    the crossing order was wrong). Only 2 cells are genuine yielder
    reassignments, both `"swap"`-mode with `robot_1` as the decided (and
    room-infeasible) yielder: one resolves in a single `swap` edit (to
    `robot_3`), the other needs `reorder` then `swap` (2 edits, also to
    `robot_3`) -- in NEITHER case does the repair search even attempt
    `robot_2` (`_apply_yield_feasibility`'s own first-feasible pick here),
    because the fixed enumeration order (reorder, then swap, then
    substitute, each sorted by position) finds `robot_3` first; a same-depth
    path to `robot_2` was not confirmed absent, only not reached. This is
    NOT resolved as "intended" here -- it is flagged for the owner to pick
    between: (i) keep `reorder`'s ability to overturn v1's "never reorder,
    only refuse" design (the current, pinned behaviour); (ii) make an
    ordering-only defect refuse exactly like v1 instead of reordering, for
    `3+`-robot scenes; (iii) in `"swap"` mode specifically, break the
    enumeration tie toward whichever robot `_apply_yield_feasibility`'s own
    scan would have picked, for the 2 yielder-reassignment cells only (the
    12 reorder-only cells are a separate question, (i)/(ii)). Whichever is
    chosen,
    "repair toward M3's own derived plan" should be narrowed in the spec
    text to mean "substitutions move toward D" specifically -- in all 14
    cells D itself (computed via `resolve_yield_roles`, which equals v1's
    refusal here) is the all-wait fan-out, and the accepted repair moves
    AWAY from it, so the phrase does not describe what happens. The current
    (unchanged) behaviour is pinned exactly, cell-by-cell, in
    `TestPlanPresentThreeRobotMultiPasserMatrix`'s
    `_DIVERGENT_THREE_ROBOT_CELLS`, so a future change to either direction
    is a deliberate, visible diff to that set, not a silent behavior change.
    `convoy`/`priority_override` plan-present behavior is UNVERIFIED by any
    sweep (`ground_reasoner_result` aliases them to a yield via
    `resolve_strategy_alias` before dispatch; `verify_and_repair_plan`'s own
    consistency/feasibility checks, including the refuse-mode fix above,
    run on the un-aliased strategy token) -- flagged, not silently assumed
    correct.
  - Tests: `tests/unit/test_plan_contract.py` (18),
    `tests/unit/test_plan_verifier.py` (913 collected; 128 skipped in
    isolation -- the convoy/priority_override cells of the two-robot
    plan-present sweep, intentionally unverified per above),
    `tests/unit/test_plan_metrics.py` (20) — all new, 951 collected / 823
    passing + 128 skipped in isolation. Targeted reruns of
    `test_command_grounder.py` / `test_command_grounder_derived.py` /
    `test_vlm_output_parser.py` / `test_reasoner.py` / `test_gemini_backend.py`
    (272 tests) pass unmodified in behavior (one exact-dict test in
    `test_vlm_output_parser.py` updated to include the new degradation tag).
    Full local suite before/after on this worktree (branched from
    `feat/prereg-v2-composite`, 3 pxr-only files ignored): 63 failed / 2957
    passed / 16 skipped before, 63 failed / 3780 passed / 144 skipped after
    — identical failing-test NAME set (diffed, zero delta). (The task
    brief's stated baseline, 58/2946/13, was measured on a different base
    tree; the pre-change baseline actually captured on this worktree's
    branch point is the one compared here.)

- **2026-10-01** — **v2 build-order step 2: J1 same-axis filter landed on
  `feat/v2-armb-filter` (v2 branch only, per
  `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` Prerequisites item
  2; a v1-frozen file, `reasoning/rag/command_grounder.py`).** Implements
  `docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md`
  Decision's standing finding ("Arm B's intersection order puts censored
  held robots first... inexecutable: the escort runs through the partner at
  0.000 m") and Owner-Override Build List item 2. The study's literal "drop
  every robot whose declared arm axis differs from the yielder's" is
  **narrower in practice**: a new `_junction_same_axis_order` helper only
  drops a cross-axis robot when its own-axis, opposite-side partner is also
  in the order (the actual `passer_travel_m` far-mouth collision
  mechanism) — the literal reading refuses the already-shipped
  `bottleneck_merge` (B1) T-junction yield outright, where the yielder's
  declared arm is legitimately perpendicular to its only passer with no
  opposite-side partner. Found by running the full local suite before
  committing (22 of 39 new failures were `test_bottleneck_merge_scenario.py`);
  fixed, then reran clean. Tag `order=junction_same_axis`, no-op when
  `geometry.arms` is unset (every scene outside the two that declare arms).
  Updated two pre-existing `test_intersection_bottleneck_scenario.py` pins
  to the new (intended) executable order:
  `test_every_yielder_grounds_a_yield_along_its_own_arm` and the former
  `test_robot_3_escort_still_runs_into_the_waiting_robot_4` (replaced by
  `test_cross_axis_held_pair_gets_no_action_instead_of_an_inexecutable_one`,
  `TestFourWayResidualsUnderJunctionGeometry`). New unit tests in
  `tests/unit/test_command_grounder_derived.py`
  (`TestJunctionSameAxisFilter`, `TestCrossAxisPasserWithNoPartner`) and
  `tests/unit/test_m5_shadow_classical.py` (Arm B's shadow stage-2 consumer,
  `classical_retreat_answer`). Full local suite before/after on the same
  tree: 58 failed / 2933 passed / 13 skipped after vs. 58 failed / 2922
  passed / 13 skipped on a clean throwaway worktree at the same base commit
  — identical failing-test sets, 11 net new passing tests, 3 pxr-only files
  ignored (`test_marker_asset.py`, `test_robot_asset.py`,
  `test_scenario_builder.py`) per the documented local/container split.
  `reasoning/baselines/classical_reasoner.py` (the v1-frozen Arm B
  classifier itself) is untouched, as the study specifies.

- **2026-10-01** — **J2 (junction-scoped backup clearance) landed on
  `feat/v2-j2`** — v2 build-order prerequisite 1
  (`docs/superpowers/specs/2026-09-30-prereg-v2-design.md` Prerequisites item
  1; derivation in `docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md`
  section 3, owner-override build list item 1). Added
  `SceneGeometry.junction_backup_clearance_m: float | None = Field(default=None,
  gt=0.0)` (`reasoning/rag/scene_geometry.py`); `derive_backup_distance`
  (`reasoning/rag/maneuver_geometry.py`) substitutes it for
  `GroundingParams.backup_clearance_m` only when the yielder has a declared
  `arms` entry and the override is set. Confirmed the single consumption
  site with `grep -rn "backup_clearance" reasoning/ ros2_ws/src/`:
  `retreat_candidates.py` and `shadow_classical.py` consume the
  already-derived `backup_m`/retreat pose, not the raw clearance, so no
  other call site needed a change; legacy-mode grounding never calls
  `derive_backup_distance`, so J2 cannot affect it either (matches the
  study's framing as a derived-mode, scene-scoped override only). Default
  stays `None`: shipped `orchestrator.yaml` `scenario_geometry` and
  `config/rag.yaml` are untouched and pinned by test. 13 new tests
  (`tests/unit/test_maneuver_geometry.py::TestJunctionBackupClearance`, 7
  tests; `tests/unit/test_intersection_bottleneck_scenario.py` — a
  shipped-default pin plus `TestJunctionBackupClearanceOverride`, 6 tests)
  reproduce the study's section-3 sweep at `junction_backup_clearance_m=1.1`:
  the park floor (`park_offset_m` = 1.018 m) binds for standoff ≥ 0.082 m
  and the N-S passer end holds at 1.668 m for s ∈ {0.10, 0.13, 0.20, 0.27},
  vs. 2.08–2.25 m (outside the 1.80 m tracked band) under the shipped 1.7 m
  — pinned both through `derive_backup_distance`/`derive_escort_distance`
  directly and through `ground_reasoner_result` end to end (the latter as a
  plain two-robot yield decision; `_yield_decision`'s four-way
  `involved_robots` list is incompatible with a two-robot crossing order and
  silently falls back to the implicit order, a trap hit and fixed while
  writing this pin). Full local unit suite (3 `pxr`-only files
  uncollectable in this environment, ignored): 58 failed / 2935 passed / 13
  skipped with J2, vs. 58 failed / 2922 passed / 13 skipped on the same
  tree with J2 stashed out — identical failing test names, zero new
  failures, 13 new passes. This count differs from the 63 failed / 2935
  passed / 14 skipped recorded at the `prereg-v1` tag entry below; the gap
  predates this change (2 more files fail `pxr` collection entirely in
  this session's environment) and is an environment/session difference,
  not a regression.
- **2026-09-30** — **`prereg-v1` tag: live-VLM demo verification + freeze.** Two live-VLM
  demo episodes recorded (footage in `data/logs/vm_runs/live_demo/`, gitignored): ER-2 run
  `20260930_152222` (clean yield of `robot_2`, 2/2 arrivals) and gpt-4o run `20260930_154216`
  (named `robot_1`, swap gate re-grounded to `robot_2`, then `temporary_wait` on re-analysis,
  2/2 arrivals, 0 refusals) — full detail in
  `docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md` Rev 25. Tag freezes the primary
  model pin (`config/models.yaml` `gpt-4o` alias → dated snapshot `gpt-4o-2024-08-06`,
  secondary already pinned to `gemini-robotics-er-2-preview`), the prompt-hash table and
  pristine config MD5s recorded in the design spec's "Model and decoding pre-registration"
  section (rev 9.5, "Prereg-v1 freeze record"), and six shipped-config-reading test
  assertions updated to match the pin (`tests/unit/test_vlm_config.py`,
  `tests/unit/test_m5_reasoning_pipeline.py`, `tests/unit/test_reasoner.py`) — no
  reasoning/prompt/oracle code touched. Local suite unaffected by this change (confirmed via
  A/B stash comparison): 63 failed / 2935 passed / 14 skipped both before and after, 3 known
  pxr-only files ignored per the documented local/container environment split.
- **2026-09-30** — **B3 goal-table revision landed and VM-verified; both smokes clear the
  0.45 m safety floor and the full chain, but fall well short of the 0.60 m margin
  discipline, which geometry alone cannot reach — gate closure left to the coordinator**
  (Rev 22 order, commits `b5c573a`, `e91a2a2`, `7d6abd9` superseded in part by this entry's
  corrected numbers; VM `vgu-vgu-thule-base-isaac-workstation-vm`, tree verified 644/647
  clean against HEAD before and after — the 3 mismatches are the same pre-existing `docs/`
  files out of scope for this task, untouched; new pristine `orchestrator.yaml` md5
  `fdbbccc61169b465181abdb931a38c85` (changes again with this entry's follow-up comment
  fixes — see VM end state below for the final value), `config/rag.yaml` unchanged at
  `e18c723cff9cada3f320d564c2ecee5a`; artifacts `data/logs/vm_runs/b3_fix/`).

  **Root cause (confirmed by `414037b`, this entry closes it):** `robot_1`/`robot_3`'s goals
  were `(2.45, ∓0.30)`, 0.6 m apart — exactly M4's `min_distance_m` (0.45) + the 0.15 m margin
  discipline, with zero headroom. That static number was never the real hazard (two robots
  resting 0.6 m apart are safe): the hazard is dynamic — once the crossing chain resumes
  `robot_3`'s base-mission Nav2 goal while `robot_4` is still escorted, `robot_3`'s released
  approach runs roughly toward its own goal, cutting inside the static separation on the way,
  and passed 0.426–0.444 m from the parked `robot_1` in 3 of 4 prior VM replicates (< 0.45 m),
  latching permanently under the correct passer-passer non-exemption (`safety.py`
  `admitted_partners`).

  **Fix (`isaac/config/scenarios/convoy_counterflow.yaml`, `scripts/strategy_regret.py`,
  `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`):** widened to `(2.45, ∓0.36)` —
  **not** the task's own `±0.45` candidate, which was checked and rejected: at `±0.45` a
  robot's footprint edge sits only 0.06 m from the rack face (`|y| = 0.6`,
  `nominal_aisle_width_m / 2`, `warehouse_builder._build_rack_blocks`), 0.09 m inside the
  0.15 m `wall_margin_m` floor that this exact scene's own `pull_off_lateral_m` already
  enforces for `robot_2`'s parked lateral offset (`reasoning/rag/scene_geometry.py`). `±0.36`
  is exactly that `pull_off_lateral_m` value (`aisle_half_width_m` 0.6 − `half_width_m` 0.09
  − `wall_margin_m` 0.15) — the widest offset consistent with the margin `robot_2` already
  safely uses in this identical aisle, derived, not guessed.

  **Nominal model vs. measured poses — the nominal model overstates the gain.** Modeling
  `robot_3`'s post-escort approach as the idealized straight segment `(1.774, 0.0) ->
  robot_3's goal` and taking its closest point to `robot_1`'s goal (pinned as a regression
  guard, `tests/unit/test_convoy_counterflow_scenario.py::TestC7GoalStack::
  test_robot_3_release_approach_clears_the_parked_robot_1`, confirmed to fail standalone on
  the pre-fix geometry) gives 0.549 m at the old `±0.30` stack and 0.636 m at `±0.36` — a
  nominal +0.087 m gain. The **measured GT table** (below) shows only ~+0.03 m: at the instant
  of closest approach `robot_1` is still settling toward its goal (not yet at its full offset)
  and `robot_3`'s real Δx is smaller than the idealized line assumes. Static goal-to-goal
  separation is 0.72 m by config (was 0.6 m), but robots settle inside Nav2 tolerance toward
  the centreline to a **measured parked separation of only ~0.57–0.58 m**. `robot_4`'s goal
  `(1.85, 0.0)` clearance to both new goals: 0.6997 m nominal (was 0.671 m). M1 tracked band
  (`|y|` up to ~1.7–1.75 elsewhere) is non-binding. Map: confirmed unaffected (`TestC13Map`,
  goal coordinates are not map-side). USD: the task's premise that "goals aren't in the USD"
  is not quite right — `scenario_builder._author_robot` authors a purely-cosmetic, non-physics
  goal marker sphere per robot (visible in raw camera frames, confirmed by inspecting
  `bscene_smoke/B3S_20260929_161207/frames/*_raw.png`), which read-through code review
  confirms no GT/M5/Nav2 logic ever reads back — genuinely non-functional, but rebuilt anyway
  for correctness (`isaac/scripts/build_scenario.py`, VM `python.sh`) after both smoke seeds
  so the tag-candidate tree is fully current; `validate_simulation.py` reports
  `PASS: isaac/scenarios/convoy_counterflow.usd`.

  **VM verification — B3 oracle smoke ×2 (`data/logs/vm_runs/b3_fix/`), full chain + 4/4
  position-verified M5 arrivals on both, independently cross-checked by
  `scripts/rescore_arrivals.py` (era-aware; both runs: 4/4 scored, 0 flipped, 0
  latched-without-acceptance, 0 censored) — measured `robot_1`↔`robot_3` GT minima below:**

  | stack | run | measured min (GT) | status |
  |---|---|---|---|
  | ±0.30 | B3PROBE / b3_oracle / B3DISP | 0.426 / 0.444 / ~0.432 m | latched (< 0.45) |
  | ±0.30 | B3S (one clean replicate) | 0.462 m | clean |
  | ±0.36 | seed 42 (this fix) | 0.475 m | clean |
  | ±0.36 | seed 43 (this fix) | 0.463 m | clean |

  - **Seed 42** (`20260930_090446`): chain complete — single `cancel-all` pair at the initial
    standoff (`robot_1`/`robot_2`, the yield trigger itself), `resume base mission
    robot=robot_3` fires at the same instant `escort robot_4: ACTIVE` starts (the exact
    defect-trigger condition), zero `cancel-all` for `robot_3` at any point, `escort robot_4:
    COMPLETED` printed (absent in every prior failing run). All 4 M5 acceptance lines
    `check=within_tolerance`: `robot_1` 0.06 m, `robot_3` 0.10 m, `robot_4` 0.07 m, `robot_2`
    0.09 m. GT minimum 0.4746 m at sim_t 117.8 s.
  - **Seed 43** (`20260930_093313`): same clean chain and all 4 M5 acceptances (`robot_1`
    0.07, `robot_3` 0.11, `robot_4` 0.07, `robot_2` 0.05 m). GT minimum 0.4628 m at sim_t
    118.5 s. One transient anomaly, checked thoroughly rather than hand-waved: a
    `min_distance_violation` `cancel-all` pair for `robot_1`/`robot_3` fired at epoch
    ~1790761249, ~4 s after `robot_3`'s M5 arrival — its FIRST logged reason was
    `stale_pose_unsafe` (an M1 tracking dropout, not a distance reading), the hold lasted
    ~3 s (last `safety stop robot=robot_3` line at epoch 1252.04) and self-cleared ~292 s
    before the run's own end (1544) — i.e. genuinely transient, not a latch that happened to
    look survivable. A full GT scan (every row, not just the global minimum) confirms `robot_1`
    stayed motionless at its already-parked pose for the entire window and `robot_1`↔`robot_3`
    distance has exactly one dip below 0.55 m in the whole run (the approach pass at sim_t
    116.9–120.0, minimum 0.4628 at 118.5) — there is no second dip near epoch 1249, confirming
    the safety-monitor event there was driven by M1 perception noise on an already-safe pair,
    not a second real approach.

  **Sensitivity and the margin discipline is not reachable by widening y alone.** Two clean
  runs at `±0.36` following a documented 3-of-4 failure rate at `±00.30` is suggestive but not
  proof at n = 2 (≈ 6% under a no-improvement null) — especially since `B3S`, a clean replicate
  already recorded at the *old* `±0.30` geometry, measured 0.462 m, statistically
  indistinguishable from both new seeds. Extrapolating the same measured-approach method:
  `±0.41` (the Nav2 global-costmap-inflation boundary, `aisle_half_width_m − half_width_m −
  inflation_radius_m` = 0.6 − 0.09 − 0.10, `nav2_params.yaml`) projects to ≈0.49 m and the
  task's own `±0.45` candidate to ≈0.51 m measured — reaching the full 0.60 m margin
  discipline would need roughly `±0.65`, past the rack face entirely. **The 0.15 m margin is
  therefore not achievable by widening this goal stack's y offset under any legal value; only
  the 0.45 m hard floor is.** Both seeds pass the floor, the full chain, and 4/4 verified
  arrivals — the task's literal PASS bar. Whether that is enough to fully close the B3
  outcome-collection gate, given the margin discipline cannot be met by this lever, is left
  to the coordinator rather than declared unilaterally here. The optional strategy-regret
  oracle arm (time-permitting per the task) was not run this session.

  **Container pytest baseline** (tree `e91a2a2`, full `ROS_SETUP`, inside `vgu_ros`, same 5
  documented `pxr`-file ignores as `dispatch_fix`'s entry above): **2998 collected, 2970
  passed, 18 failed, 10 skipped** (82.3 s) — fewer collected than the prior container
  baseline (2980/23/12, 3015 collected, tree `1e8080d`); the ~17-item collection drift across
  the intervening commits is not investigated here (out of scope for this task). None of the
  18 failing test names (`test_aruco_generation`, `test_fc_launch_dry_run`,
  `test_gemini_backend`, `test_m5_congestion_detector`, `test_m5_reasoning_pipeline`,
  `test_m6_config`, `test_m6_validation`, `test_openai_backend`, `test_t2b_forced_order`)
  touch this fix's files; `test_convoy_counterflow_scenario.py` +
  `test_strategy_regret.py` run standalone inside the container: 100/100 passed. Local
  baseline unaffected: `tests/unit` (same ignores) still 58 failed / 2924 passed / 9 skipped
  (was ~58/2921+); this fix adds **three** new passing tests across `b5c573a`/`e91a2a2`
  (`test_robot_1_and_robot_3_goal_separation_clears_the_safety_margin`,
  `test_goal_lateral_matches_this_scenes_own_pull_off_margin`,
  `test_robot_3_release_approach_clears_the_parked_robot_1`), all green, all confirmed to
  fail on the pre-fix geometry standalone. **VM end state:** tree re-verified against HEAD
  (644/647 match, same 3 pre-existing `docs/` mismatches); `.pristine` scratch backups
  deleted; `orchestrator.yaml`/`rag.yaml` restored to this fix's own committed content (not
  the pre-fix `dispatch_fix` baseline) and rebuilt (`colcon build --merge-install
  --packages-select swarm_orchestrator`, cwd `/ws/ros2_ws`, inside a login shell `bash -lc`
  as `fc_launch.sh` itself uses — a plain non-login `docker exec ... bash -c` without
  `ROS_SETUP` sourced first fails outside a rebuilt `swarm_interfaces`/`swarm_perception`
  context, a pitfall for a manual rebuild outside `fc_launch.sh`); installed copy, source
  copy and `git show HEAD:` all hash-match. Container restarted; `pgrep -f
  'run_simulation|fc_launch'` confirms no stray Isaac/`fc_launch` processes,
  GPU idle (0 %, 171 MiB).

- **2026-09-30** — **Rev 20's two apparatus defects characterized; both SCOPED, no code fix** (VM
  `vgu-vgu-thule-base-isaac-workstation-vm`, tree verified 645/647 clean against HEAD `1e8080d`
  before and after — the 2 mismatches are `docs/superpowers/` files, out of scope here and
  untouched; pristine `orchestrator.yaml`/`config/rag.yaml` md5 `dd1c5b7ff4fd628a0812c40157023c71`
  / `e18c723cff9cada3f320d564c2ecee5a`, matching the installed copies; artifacts
  `data/logs/vm_runs/dispatch_fix/`). **301e77f's "structural, all 3 runs" and "fails on
  min_distance_violation" claims are superseded by this entry's evidence below.**

  **(b) B3 4-robot dispatch gap — NOT a registry/BaseMissionDriver/retry bug; a probabilistic
  robot_1/robot_3 goal-separation latch.** Traced every layer named in the task and found each
  correct: `robot_4` is in the B1/B3 goal table (`scripts/strategy_regret.py:195-202`,
  `initial_tasks`), `TaskRegistry.release_due`/`to_json` (`task_registry.py:38-119`) releases and
  publishes it like any robot, and `BaseMissionDriver._desired()` (`base_mission.py:55-63`)
  correctly excludes only `_held`/`_suppressed_by` robots — confirmed by a clean, fully successful
  4/4-arrival replicate of this exact scenario/mock/seed
  (`data/logs/vm_runs/bscene_smoke/B3S_20260929_161207`: `m4.log:1356` `resume base mission
  robot=robot_4`, `nav2_r4.log:271` `Begin navigating from current location (1.78, 0.00) to (1.85,
  0.00)`, `m5.log:4020` `robot robot_4 arrived at base goal (1.85, 0.0) distance_m=0.09`) that
  exercises the identical code path end to end. The actual, reproduced failure (3 of 4 known runs —
  `B3PROBE_20260930_044351`, `bscene_smoke/b3_oracle_20260930_013059`, and this session's
  `dispatch_fix/B3DISP_20260930_073750`): once the crossing chain's intermediate release
  (`command_bus_node.py:237-240`) resumes `robot_3`'s base-mission Nav2 goal toward `(2.45, 0.3)`
  while `robot_4` is still being escorted through the same single-lane corridor, `robot_3`'s live
  approach passes close enough to `robot_1` (already parked at `(2.45, -0.3)`, only 0.6 m away) to
  breach the 0.45 m floor (`config/safety.yaml:2`) for real: GT center-to-center distance at the
  frozen end state is `0.4256 m` (B3PROBE), `0.4442 m` (b3_oracle) and `0.4324 m` (B3DISP, this
  session — `min_pairwise_distance_m` in that run's final GT row is actually the robot_3/robot_4
  pair, even tighter), all `< 0.45`, and `robot_3`/`robot_4` separately end up at `0.3977 m` /
  `0.4163 m` / sub-0.45 m across the three failing runs. The 0.45 m breach is genuine
  proximity (not a perception artifact): the newly-flagged safety-stop lines
  (`nav2 cancel-all requested robot=robot_3` / `robot=robot_1`, same tick) are the real reason, not
  the hardcoded `reason=min_distance_violation` text repeated on every 40 Hz hold line. Per
  `safety.py:110-153` (`admitted_partners`) and its own pinned tests
  (`tests/unit/test_safety_monitor.py::test_waiting_passers_are_not_paired_with_each_other`,
  `::test_backup_phase_never_pairs_two_passers`, the latter citing the live-verified T2b
  "bystander latch" as the reason), two passers of the same multi-passer yield are DELIBERATELY
  never exempt from each other — loosening that would undo a load-bearing, GPU-verified T2b safety
  invariant, so it is not touched. Once latched, `BaseMissionDriver.retry()` correctly skips held
  robots (`base_mission.py:55-63`) — "robot_3's leg is never retried" is *correct*, not a bug: two
  robots held at zero-twist never produce a fresh >=0.45 m separation on their own, so the latch is
  permanent by construction, not a missed retry. `robot_4` separately never gets a `resume base
  mission`/Nav2 dispatch in the 2 failing runs because by the time its `temporary_wait` reaches
  COMPLETED (chain finished — most likely `hold_sec` backstop, not "passer cleared": `escort
  robot_4: COMPLETED` never prints in either failing run) it is *already* `_held` from the same
  robot_1/robot_3 cluster, so `_desired()` correctly omits it — this is the already-registered
  finding F6 (arrival definition; `docs/implementation_notes.md` M2/M5 section, 2026-09-2x entry)
  applied to a robot latched at its goal, not a new dispatch defect. **Root cause is therefore B3's
  goal table**: `robot_1`'s and `robot_3`'s goals (`(2.45, -0.3)` / `(2.45, 0.3)`,
  `isaac/config/scenarios/convoy_counterflow.yaml` via `scripts/strategy_regret.py:197-199`) are
  only 0.6 m apart — the scenario's own test suite checks `robot_4`'s goal against the other two
  (`GOAL_STACK_M = 0.60`, `tests/unit/test_convoy_counterflow_scenario.py::TestC7GoalStack`) but
  never checks `robot_1` against `robot_3` directly — and the live, non-straight-line Nav2 approach
  into the shared corridor occasionally (not always: `B3S` is clean, `B3PROBE`/`b3_oracle`/`B3DISP`
  are not) closes that 0.6 m margin below 0.45 m before either robot settles. **Separately
  confirmed, worth its own line item**: `robot_4`'s raw-cmd_vel escort (`drive_heading`,
  `nav2_adapter.py`) advanced ~5.2 cm (GT x: `1.7086` at sim 163.3 -> `1.7603` at the run's final
  row, sim 260.0) *after* the M6 `cmd_vel_watchdog` relay logged `cmd_vel relay hold engaged
  robot=robot_4` (`isaac.log`, B3PROBE) — a small, real violation of the invariant
  `docs/specs/module4/safety-monitor.md` §8 states plainly ("A held robot's wheels receive zero
  irrespective of `cmd_vel`"), in the same "M4 raw-cmd_vel obstacle blindness" family already
  tracked (prereg-v1-amendments item 25) but not previously observed to leak through the *gated*
  relay itself, only to bypass the Nav2 collision_monitor. Flagged for the M4/M6 owner; not fixed
  here (reported per instruction, not diagnosed to a line-level cause — candidates are a narrow
  20 Hz relay-vs-physics race or residual momentum, not distinguished). **Verdict: SCOPE, not fix.**
  A safe fix is a scenario goal-table change (widen the `robot_1`/`robot_3` goal separation,
  analogous to B1's `half_length_m` fix) requiring its own local sweep + VM re-verification + pin
  rewrite across `test_convoy_counterflow_scenario.py`'s ~30 pinned exact values — out of this
  task's budget and, per `B3S`'s clean replicate, not even validatable from one more smoke (the
  failure is probabilistic, roughly 3-of-4 to date). **B3 outcome/flow-metric collection stays
  blocked** until the coordinator orders that goal-table revision; this session's VM replicate
  (`dispatch_fix/B3DISP_20260930_073750`, seed 42, `convoy_counterflow_oracle_order_once.json`) is
  reported as a 4th data point (failed the same way, only `robot_1`+`robot_2` got M5 arrival
  lines), not a PASS/FAIL verdict, and "robot_3 retries after cancellation" is not an attainable
  PASS criterion without weakening `base_mission.py`'s correct held-robot exclusion.

  **(a) B1 default-candidate backup/sidestep failure — confirmed candidate- and heading-specific,
  refuting "sweep uses nominal poses."** `generate_retreat_candidates`/`_sweep_clears`
  (`reasoning/rag/retreat_candidates.py:38-124, 201-212`) validate against `frame.robots`, i.e. the
  live snapshot at grounding time — current poses, not nominal ones; that hypothesis is refuted by
  the code itself. The actual, 3/3-reproduced failure (`B1FIX_S43`, `SWFIX_oracle_s42`,
  `SWFIX_oracle_s43`, all `retreat=default:no_choice`): the yield's FAILED status arrives
  202.3-202.5 s after the pull-off/sidestep ACTIVE in every run — an exact match (within logging
  jitter) to `Nav2Adapter.sidestep`'s own wall-clock safety deadline
  (`nav2_adapter.py:198-228,375`: `max(15 * (pi/0.5 + |lateral_m|/0.1), 30)` = `202.25 s` for
  `lateral_m = -0.72`) — i.e. the sidestep genuinely times out (`"side step timed out in phase
  {phase}"`), not a safety-monitor rejection (zero `safety stop` log lines for any robot in the
  entire `[pull-off ACTIVE, FAILED]` window of `B1FIX_S43`, and zero `robot_static_contacts` /
  `robot_robot_contacts` anywhere in that run's GT). `rank_candidates` (`retreat_candidates.py:
  127-162`) ties both surviving candidates' `lateral_clearance_m` at this geometry and its
  tie-break ("farther from the corridor is better") picks candidate `B` (`lateral_m = -0.72`, the
  2x/farther option) as `ranked[0]` — confirmed from the decision JSON's own `stage2.default_label
  = "B"` — while the one stage-2-forced comparison run (`B1FIX_S43R`, mock answers letter "B" which
  `letter_assignment` maps to `grounded_label = "A"`, `lateral_m = -0.36`) completes its sidestep
  cleanly in ~39 s (`m4.log:1381-1386`, backup ACTIVE -> pull-off ACTIVE -> hold ACTIVE with no
  FAILED). GT trajectory for the default candidate (`B1FIX_S43`) pins the mechanism exactly: the
  backup and turn-out phases complete normally, but the drive segment overshoots the candidate's
  own validated target (`x ~= -0.38` to `-0.42`, inside the `aisle_x_band_m = [-0.46, 0.46]`
  feasibility band) to GT `x = -0.56` — 0.10 m past the band edge — after which `theta` oscillates
  at the +-pi wrap boundary with zero net progress and zero speed for the remainder of the
  deadline. This is the same mechanism as the already-documented residual ("M4 backup overshoots
  the NS_BAND west edge at 2 of 8 measured poses", `301e77f`'s notes entry above): the swept
  validation models the backup/sidestep as idealized straight-line segments
  (`axes.retreat`/`axes.left`, world frame), while M4 executes them as a heading-relative,
  odometry-closed loop (`nav2_adapter.py` `backup`/`sidestep`) whose cumulative drift scales with
  maneuver distance — large enough for the 2x/`-0.72 m` candidate to carry the yielder past the
  validated band into the wall, small enough for the 1x/`-0.36 m` candidate to stay clear. This is
  a genuine, reproducible candidate-validation gap, but principled fix requires modeling M4's
  actual execution geometry (or its empirically-measured drift) inside the sweep/ranking used by
  every derived-mode scene (`T3b`'s pre-registered occupied-choice test, `T2b`, Arm B's stage-2
  answer, every other B1 pose) — out of budget to validate safely here. **Verdict: SCOPE, not
  fix**, per the task's own option (ii): B1 trials where the DEFAULT (no stage-2) candidate is used
  are outcome-contaminated (100% reproduced sidestep timeout, 3/3) and must be excluded from
  flow-metric collection / scored decision-only; only stage-2-selected-candidate trials are valid
  for B1 flow metrics. Sharper than the task's own framing: the exclusion rule is *"default
  candidate is the tied-clearance, farther-from-corridor 2x lateral variant"*, not merely "steep
  yielder heading" — all 3 default-candidate runs times differ in heading (`-69.8 deg`, `-67.2
  deg`, `-58.3 deg`) but fail identically; the mechanism is the candidate's excursion distance
  relative to the aisle band, heading sets how much drift accumulates over that excursion.

  **VM verification (this session, `data/logs/vm_runs/dispatch_fix/`):** `B3DISP_20260930_073750`
  (convoy_counterflow, seed 42, oracle-order mock) — 4th replicate of the same failure shape, not a
  PASS (see above). `B1DISP_20260930_075853` (bottleneck_merge, seed 43, yield mock, no stage-2) —
  4th consecutive reproduction of the exact `retreat=default:no_choice` / 202.4 s sidestep-timeout
  failure shape (202.43 s this run); reported as "failure shape confirmed unchanged", not a PASS,
  per the (a) scoping verdict above. **Container pytest baseline** (tree `1e8080d`, full
  `ROS_SETUP`, inside `vgu_ros`): diagnosed the "collects only 1 test" symptom precisely —
  `tests/unit/test_lidar.py` and `tests/unit/test_robot_drive.py` each do a *module-level*
  `pytest.importorskip("pxr")`; `pxr` (USD) is genuinely absent from this ROS2 container (it lives
  only in the separate Isaac Sim `python.sh` environment), and the ROS2 `launch_testing`/
  `launch_testing_ros` pytest plugins' `pytest_pycollect_makemodule` hook imports every `.py` file
  to probe for a launch-test entrypoint; the resulting `Skipped` (a `BaseException`, not
  `Exception`) escapes that hook's own error handling and silently truncates the *whole* session to
  "no tests collected" whenever either file is combined with others (confirmed by bisection: each
  collects fine alone). Workaround for this run only (no code change): `--ignore` both files plus
  three more `isaac.vgu_sim` tests with unconditional, unguarded `pxr` imports
  (`test_marker_asset.py`, `test_robot_asset.py`, `test_scenario_builder.py`) — all five are
  Isaac-Sim/USD-only tests, out of scope for a ROS2-container run by design, the same class of
  environment split as the local/container difference already on record. Result: **3015 collected,
  2980 passed, 23 failed, 12 skipped** (80.18 s) — not directly comparable to the prior "local
  58/2921 / container 63/2926" figures since the excluded-file set differs; this is the first
  container run to separate the `pxr`-environment-split files out explicitly instead of either
  failing on them or silently collecting zero. Full lists in
  `data/logs/vm_runs/dispatch_fix/SUMMARY.txt`. **VM end state:** tree re-verified against HEAD
  `1e8080d` (645/647 match; the 2 mismatches are the same out-of-scope `docs/superpowers/` files),
  `orchestrator.yaml`/`rag.yaml` restored pristine (md5s above, installed copies match), container
  restarted, no stray Isaac/`fc_launch` processes, GPU idle (0%, 171 MiB). No code change lands
  with this entry (0 commits touch `ros2_ws/`, `reasoning/`, or `isaac/`); this is a `docs:` notes
  entry only.

- **2026-09-30** — **B1 `bottleneck_merge` geometry fix landed and
  GPU-validated** (`5dbb3a5`; VM `vgu-vgu-thule-base-isaac-workstation-vm`,
  tree verified 647/647 clean before and after; artifacts
  `data/logs/vm_runs/b1_fix/`). Root cause pinned exactly:
  `derive_escort_distance`'s crossing-arm branch reduces to
  `required_escort = corridor.half_length_m - robot_1.x + 0.65` at this
  geometry; at `half_length_m` 0.6 this is 0.77-0.87 m against the 1.0 m
  `escort_band_m` floor across all 8 measured GT trigger poses (the prior
  entry's 5, plus 3 more pulled from `SW1_alternative_s42/s43` and
  `SW1_wait_s42`), 7 of which are the LEVEL_OR_PAST sub-case
  (`robot_2.x < robot_1.x`) the pre-fix constraint grid excluded from every
  feasibility check. **Two physical levers were GPU-probed and rejected on
  measured data, not hand-derived:** shifting the A55-E gate east (rejected
  without a run: the standoff forms at `robot_1.x < 0.5`, well before either
  robot nears the gate at `x >= 0.7`) and moving `robot_2`'s spawn (probed
  both directions: -0.2 m raised `robot_1.x` to 0.591, worse; +0.35 m gave
  0.435, inside the original geometry's own 0.148-0.483 spread — one GPU
  sample per config cannot resolve a slope inside that noise, so the lever is
  closed, not under-explored). **The fix instead raises
  `scenario_geometry.corridor.half_length_m` 0.6 -> 1.1** in
  `orchestrator.yaml`'s B1 goal-table row (and `strategy_regret.py`'s
  `SceneSpec`) — a lever outside the task's candidate list, adopted after a
  local sweep (`half_length_m` in `{0.6, 0.8, 0.9, 1.0, 1.1}` against all 8
  measured poses, not a synthetic grid) showed `robot_2`'s own park y is set
  by `backup_clearance_m` (1.7 m), not `half_length_m`, until it exceeds
  ~1.3 — so the suspected C1 coupling (shared corridor object sizes both
  robot_1/3's escort and robot_2's own backup/park) does not bind here. At
  1.1 every measured pose clears the escort floor by >= 0.167 m (0.267 m at
  the tightest pose, `SW1_wait_s42`). No scenario spawn, goal, barrier or map
  value changed. **Residual, not fixed:** M4's actual reverse-along-heading
  backup overshoots the NS_BAND west edge at 2 of the 8 measured poses
  (B1S1 -52.5°, SW1_alternative_s42 -55.9°), independent of `half_length_m`
  (governed by the 1.7 m clearance, not the escort formula). **GPU
  validation:** smoke seed 42 drew a no-event episode (Δt >= 3 s, the
  scenario's own documented trimodal outcome, not a fix failure); smoke seed
  43 grounded the oracle yield FEASIBLE (confirms the fix) but exposed a
  **new, previously-unobservable M4 finding**: `robot_2`'s backup command
  itself resolved FAILED on the DEFAULT (`retreat=default:no_choice`) park
  candidate, on `safety_monitor_node` `min_distance_violation` — reproduced
  3/3 times on every run that skipped stage 2 (`B1FIX_S43`, `SWFIX_oracle_s42`,
  `SWFIX_oracle_s43`) — while the one run that set
  `VGU_MOCK_RETREAT_CHOICE_FILE` (forcing stage-2 candidate `B`) resolved
  COMPLETED cleanly. This was never observable before this fix: grounding
  always refused the yield first. Flagged for M4/retreat-candidate owner
  attention, not fixed here (out of scope). The stage-2 aperture-absence gap
  flagged in the prior entry is now closed: live-grepped the executed stage-2
  prompt (`B1FIX_S43R`) for aperture/barrier/gate/corridor/static-obstacle
  tokens — 0 hits, `status=answered`. B1 strategy-regret sweep (n=2
  seeds/arm, uncensored insofar as grounding is concerned) gives
  `oracle` 424.1 s (best, still GT-censored by the M4 finding above) vs
  `alternative` 556.35 s (+132.25 s regret) and `wait` 558.0 s (+133.9 s
  regret) — oracle is the clear cost-minimizing arm even under the M4
  apparatus issue. B3 arrival probe (3rd B3 run,
  `B3PROBE_20260930_044351`): `robot_3` GT final distance 0.3757 m, a second
  near-miss just outside the 0.35 m tolerance (predecessor 0.0941 m clean;
  prior session's replication 0.3586 m); `robot_4` GT distance 0.090 m
  (comfortably inside tolerance) but M5 never logs its acceptance in any of
  the 3 B3 runs to date, and Nav2 never logs a "Begin navigating" for
  `robot_4` in any of them either — a structural M5/Nav2-dispatch gap for
  that robot, not merely a tight tolerance. `robot_3`'s single Nav2 attempt
  in each of the 2 near-miss runs gets canceled ~8 s after starting and is
  never retried.

- **2026-09-30** — **Coverage-scene B1/B2/B3 smoke batch + sweeps completed**
  (VM `vgu-vgu-thule-base-isaac-workstation-vm`, tree `4393155`,
  `data/logs/vm_runs/bscene_smoke/BSCENE_SMOKE_SUMMARY.txt`). Inherited-commit
  verification (`5d2ce53`, `34d6b53`, `4393155`): all pass, suite 63 failed /
  2926 passed / 14 skipped / 3 errors (same 63 failing tests as the a830d4e
  baseline; the delta is new passing tests only), no fix-forward needed. Part
  A (`fc_launch` four-stack lifecycle gate) was already landed in `ed75288`
  before the three inherited commits — verified live under 3 stacks (B1) and
  4 stacks (B3, first attempt, `NAV2_BRINGUP_FAILED` never triggered); no new
  commit made. **B1 finding:** `bottleneck_merge`'s oracle mock did not
  reliably resolve at seed 42 across 5 independent executions (1 predecessor
  smoke + 2 replications this session + 2 sweep runs): the trigger typically
  fires when `robot_1` is within 0.82–0.87 m of the gate exit, below the
  derived escort-band floor of 1.0 m, so the yield grounds infeasible and
  degrades to a reroute of all three robots, producing a permanent ~0.33 m
  three-way latch (0/3 arrivals); the one sweep execution that avoided this
  path still censored by a different mechanism. Not tuned or fixed (task
  scope was smoke verification); B1's strategy-regret sweep was not extended
  further since `strategy_regret.py` keys an arm by executed roles
  (`roles_from_command`), and at this trigger geometry both the oracle and
  alternative arms collapse toward the same reroute/censored regime. **B2**
  (`priority_urgent_r1`/`_r2`) fully replicated both members' predictions
  (alias tag, %CP 1.0, byte-level label-only prompt diff, sweep
  `best_arm=yield_urgent` uncensored in both, regret 13.1s / 5.1s). **B3**
  (`convoy_counterflow`) replicated the four-stack gate, the `aliased:convoy`
  tag + oracle crossing order, park position, and vacated-spawn clearance,
  but this session's independent replication confirmed only 2 of 4
  arrivals via M5's own arrival-gate log (robot_3 stalled 0.36 m from goal,
  just outside `arrival_position_tolerance_m: 0.35`; robot_4 sat 0.10 m from
  goal per GT but never got an M5 "arrived" log line and Nav2's own log shows
  no terminal status for either robot) — a partial-pass deviation from the
  predecessor's clean 4/4 run, reported not resolved. B3's sweep was not run
  (time budget; matches the predecessor's own "if time" deprioritization).
  **Process note:** this session discovered, only after independently
  re-verifying Part A and re-running all four smokes from scratch, that a
  near-complete 2026-09-29 batch already existed under
  `data/logs/vm_runs/bscene_smoke/` (all four smokes + B1/B2 sweeps executed
  and scored, only the summary's placeholder sections and this notes entry
  left unfinished) — consistent with the predecessor being cut off by a rate
  limit near the finish line. The duplication cost real GPU wall-time; it is
  kept as independent replication evidence (materially strengthening the B1
  finding) rather than discarded. A same-named ad-hoc driver script,
  `_vm_driver/run_bscene.sh`, was overwritten by this session's own version
  before the collision was noticed (its behavioral difference — ending
  `fc_launch`'s stage-9 tail at Isaac's actual exit rather than an idle
  `REC_SEC` — is preserved in prose in the summary; the original file
  content is not recoverable). No other predecessor driver file was touched
  (verified by mtime). This session's `apply_scene.py` duplicates the
  pre-existing `gen_orch_bscene.py`; it fixed one bug the original did not
  have (merging `scenario_geometry.corridor` onto a pristine copy instead of
  replacing it wholesale, which would have silently dropped
  `occluder_height_m` for B2/B3) before any B2/B3 run. VM end state: tree and
  installed packages re-verified byte-identical to HEAD's 647-file manifest,
  `orchestrator.yaml`/`config/rag.yaml` restored to pristine
  (`d0f390694f12bf1d8fcd90e0cb02d6df` / `e18c723cff9cada3f320d564c2ecee5a`,
  matching the predecessor's own recorded values), container restarted, GPU
  idle.

- **2026-09-29** — **Coverage scenes B1/B2/B3 built offline** per the unified
  scene design (`3b3a529`) and amendments items 28–30 (`ce04bad`); **no VM
  work — the smoke batch is pending**, and the new scenes' USDs regenerate
  VM-side (C13). Landed: held-robot exclusion in Arm B (`2f5a2d1`,
  `SnapshotFrame.held_robot_ids` fed from `TaskRegistry.is_pending`; the
  `RobotStateInput` contract is untouched); world x band for y-arm yielders,
  `grounding_aisle_x_band_m` (`86bee0d`); M3-only `TaskAssignment.priority`
  + `PriorityOracleConfig` (`6dfef27`, prompts pinned byte-identical with
  and without it); `convoy`/`priority_override` grounded as the ordered
  yield, tag `strategy=aliased:*` (`cb44d7a`; pooling addendum: those
  strategies do not pool across this commit); `fcfs_yielder` fact
  correction (`6d511be`); the scenes, maps, goal-table rows, mocks and
  C1–C13 pin tests (`16df6d5`, `f159644`); `scripts/strategy_regret.py`
  for item 29 (`78fca50`). Findings where the design doc does not
  reproduce, each pinned: (a) the approved exclusion is candidacy-only
  (parked-robot shape), so the 10/45 crowded B3 cases read `unknown
  [robot_1, robot_2]` (a wait), not the design's 45/45 `head_on` — that
  needs the held robot out of the crowding check too, an owner decision;
  (b) B1's refused `robot_1` yield degrades to a reroute of `robot_1`,
  it is NOT re-grounded to `robot_2` (the swap gate needs static
  obstacles, B1 has none); (c) B3's `robot_3`/`robot_4` escorts are
  3.674/4.244 m, not 3.574/4.174 (those came from the rejected east-shifted
  queue; ends still x 1.774); (d) B1 has a level-or-past sub-case (robot_2
  not east of robot_1) that Arm B reads `blocked_path [robot_1]`; (e) B1's
  reverse-along-heading gate needs x0 ≥ 1.35·cos|θ| − 0.46 (x0 ≥ 0.174 at
  −62°), narrower than the design's wording. The `fcfs_yielder` correction
  changed all 7 manifest rows to `robot_2`; `contrasts_fcfs` flips
  true→false for the three `w0p2_*` rows and T2b, false→true for the three
  `wopen_e0p2_*` rows and `wopen_eopen` (whose `correct_yielder` stays
  `robot_1`, now a named constant, rationale reworded); the design-doc and
  rev-8.6 annotations under `docs/superpowers/` are left for the owner.
  Not built (design build items outside this slice): B1 GT
  `bottleneck_conflict_active` + gate-flow scorer, B2 %CP scorer, B3
  `censored_omitted_queue` rescorer, the fc_launch four-stack lifecycle
  gate, and a VM driver for the strategy sweeps; `acceptance_logging`
  computes `conflict_active` only for `head_on`, so B1/B3 log false until
  the GT functions land. M5 decision artifacts do not record the grounded
  command, so the regret harness maps an artifact to its arm from the
  decision, the analysed scene and M3's yield provenance.

- **2026-09-29** — **Unified scene design committed** (`3b3a529`,
  `docs/superpowers/specs/2026-09-29-unified-scene-design.md`): C55
  single-lane module (0.55 m, workable band [0.50, 0.63)), A55-J/A55-E
  aperture placements, derived goal/length rules replacing per-scene
  magic numbers, a 13-check constraint table, MiR250-anchored fidelity
  frame (s ≈ 3.3 by width; latency forgiveness 10.9–20× recorded as a
  scoped fidelity limit), and full specs for B1 `bottleneck_merge` (3
  robots), B2 `priority_urgent_*` (2-robot label-swapped pair; urgency
  via task label — NO new prompt version) and B3 `convoy_counterflow`
  (4 robots; Arm B's outcome censored by construction). Migration
  recommendation: CONSERVATIVE (grandfather existing scenes, record
  deviations D1–D3, 0 re-validation runs) vs full consistency (~25–45
  runs, invalidates A1/margins/pins for no measurable gain). Findings
  requiring pre-tag action: `fcfs_yielder: robot_1` in the family
  manifest/T2b YAML/rev 8.6 is FACTUALLY WRONG (full ties yield
  robot_2 — pinned test), so `contrasts_fcfs` annotations need
  correction; a held-robot exclusion in Arm B is a new rule decision
  (fixes B1 and 10/45 B3 grid cases); T2b Arm-B-executed episodes risk
  a B3-style latch (inferred — check before collection).

- **2026-09-29** — **Intersection resolvability design study: recommendation
  D — the T1-X log-only fallback stands** (`0c27a4d`,
  `docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md`).
  Decisive: robots stop 0.24–0.42 m apart (latch latency), so a formed
  four-way jam is never clearable — every scheme's first-passer transit is
  ≤ 0.351 m vs the 0.45 m floor; the schemes that complete episodes (A, C′
  with junction-scoped J1/J2 changes) degenerate to two sequential
  head-ons — Arm B classifies `head_on`, the GT intersection oracle never
  fires — so the tier identity is lost either way. N-S escorts sit only
  0.032–0.132 m inside M1's tracked band even under J2. Standalone
  finding: robots held inside the zone are always FCFS-censored and
  always ordered first — a same-axis filter is prerequisite to ANY
  junction ordering. The genuine four-way needs a composite command
  (cross pair reverses, then the axis pair yields) — named as the
  prereg-v2 candidate. C′'s build list is recorded in the study should
  the owner override.

- **2026-09-29** — **`intersection_bottleneck` v2 (user decision: the
  four-way must be resolvable): S2 and the yielder-latch mechanism are
  DISCHARGED live; S1 stays OPEN, so the scene is still not resolvable.**
  Code `8397509` (M3), `2613575` (M4), `0514333` (goal-table row),
  `60a00bf`/`e758136` (tests, robot_3 mock). Evidence:
  `data/logs/vm_runs/intersection_v2/INTERSECTION_V2_SUMMARY.txt`
  (git-ignored), failure pre-registered in `PREDICTION_pre_run.txt` there.
  This partly supersedes the 2026-09-29 audit entry below (its S2 and
  latch findings).
  - **S2 discharged (M3).** `SceneGeometry.arms` gives each robot the arm
    it approached on; its yield grounds, gates and sweeps along that arm.
    Without `arms` the code path is identical: the 576-output SHA and the
    family-oracle pins pass untouched. Live, run IBB4 grounded a
    north-south yield for `robot_3` (retreat (0.334, −1.789)).
  - **Yielder latch discharged (M4).** During a yield's backup and pull-off
    (read from the bus's ACTIVE status details, `yield_phase.py`), the
    yielder is exempt against every robot its command addresses; from the
    hold on, progressive admission is unchanged. Live: IBA1 `robot_2`
    backed out 1.512 m (GT) and IBB4 `robot_3` 1.626 m south along its own
    arm, each with 0 safety stops during the backup (IB10: 0 m).
  - **S1 OPEN.** Each first passer sits 0.28–0.42 m from the cross pair,
    pairs no command exempts, so its escort is held (IBA1 `robot_1`
    0.004 m, IBB4 `robot_4` 0.0 m). A same-lane passer's straight escort
    would also run into its waiting opposing partner. Both runs: 0/4
    arrivals, 0 contacts, the hold backstop ends the yield.
  - **Binding text.** This conflicts with rev 9.3 (decision C, `3177615`):
    its T1-X log-only fallback REMAINS the binding text until a resolvable
    command decomposition exists (an S1 design study is next).

- **2026-09-29** — **`intersection_bottleneck` (mandatory T1 #2): pre-tag
  audit done. NOT tag-ready: re-authoring is needed.** Light fixes are in
  `49ac434`; the smoke mock and status are in `fa20d21`. The smoke is
  `data/logs/vm_runs/intersection_smoke/IB10_20260929_085349`
  (git-ignored; `INTERSECTION_SMOKE_SUMMARY.txt` has the audit table and
  the checklist).
  - **Fixed (light).**
    - Spawns and goals moved to 1.75 m on all four arms. The June spawns
      at (±3.0, 0) were out of frame. (0, ±2.0) sat 0.09 m inside the
      2.092 homography y-edge. The derived y band is 1.80.
    - The approach radii are now equal. Unequal radii give a two-robot
      head_on first.
    - Added the per-scenario map.
    - `duration_sec` is now 300.
    - `family: intersection` is now explicit.
    - Added an `orchestrator.yaml` goal-table row, with the Arm B zone
      `crossing_1` (origin, r 1.5 = `r_conflict_m`). The shipped
      `shadow_classical_zones` stays `[]`.
    - Pinned by `tests/unit/test_intersection_bottleneck_scenario.py`.
  - **Live, working.**
    - M1 tracked all four robots in every full-rate row.
    - The standoff formed. The GT intersection oracle was active from
      31 sim-s to the end.
    - The trigger fired.
    - **Arm B's first live `intersection` classification is positive:**
      35/35 analyses, zone `crossing_1`, no censoring at the first
      standoff analysis. Its pick matched the forced mock.
  - **Structural defects.**
    - Two opposing pairs meet at the centre. No single-yield command can
      clear them. The robots stop 0.33–0.45 m from the cross pair, and M4
      exempts only yielder↔admitted-passer pairs. So the latch held the
      yielder's own backup, and the yield FAILED after 219 s with zero
      arrivals. This was predicted offline before the run.
    - M3's single-axis corridor cannot ground a north-south yielder. Arm
      B's own retreat was ungroundable in 33/35 analyses.
  - **Apparatus.**
    - Four Nav2 stacks overload g2-standard-8: load1 ~15 (max 30), RTF
      ~0.22.
    - Nav2 lifecycle bring-up failed in 3 of 8 launches: two "Aborting
      bringup" and one stack not active after 90 s. `fc_launch.sh`'s
      action-list wait does not catch it.
    - The stage-9 `tail -f` races M5's log creation.
    - Both were worked around VM-side only: a lifecycle gate plus a
      pre-created log in `_vm_driver/run_ib.sh`. `fc_launch.sh` is
      unchanged.
  - **Re-author options (coordinator decision).**
    - (A) A two-robot perpendicular crossing. This needs a shared M3
      per-yielder retreat axis and a formation pilot.
    - (B) Drop the scenario from T1 and amend the matrix. T1 would be
      `head_on_deadlock` plus `head_on_asymmetric_wopen_eopen_o0`.
  - **VM.** The pristine `orchestrator.yaml` md5 goes from `ca35f94e…` to
    `8c2c64ce…`. `rag.yaml` is unchanged (`e18c723c…`).

- **2026-09-29** — **T1 tuning basket (amendments item 14): discharged,
  pending coordinator review.** One value changed, four kept, all frozen at
  `prereg-v1`. Evidence: `docs/reports/2026-09-29-t1-tuning-basket.md`;
  code `caaf95f`; T1 run `data/logs/vm_runs/t1_basket/T1B1_20260929_000054`
  (git-ignored).
  - **Changed: the head_on FCFS zone.** A new `ClassicalParams.fcfs_zone_radius_m`
    is set to 1.0 in `config/rag.yaml`.
    - Default `None` falls back to `r_conflict_m`. A validator requires at
      least `r_conflict_m` / 2.
    - `r_conflict_m` 1.5 still decides the head_on pairing.
    - Spawn-phase censoring fell from 9/17 to 0/17 corpus records.
    - On T1B1, 1.5 censors both robots and 1.0 censors neither. The rebuilt
      full-rate buffer reproduces the live record.
    - The 56 window-truncated records stay censored at any radius. The
      `censored_arrivals` flag still reports them.
  - **Kept.**
    - M1 `stopped_threshold_mps` 0.01: no clean separator. Real 1–5 cm/s
      creep overlaps the parked-jitter tail. 0.03 is recorded as the named
      rejected option for the tag: parked SLOW falls 11.75% → 0.27% on the
      corpus and 27.2% → 1.0% on T1, but all T1 creep would read STOPPED.
    - M1 `slow_threshold_mps` 0.05: parked max 0.055, maneuver min 0.079.
    - Arm B `stopped_speed_mps` 0.05: stall max 0.038 at snapshots, motion
      min 0.079.
    - M4 `max_linear_velocity_mps` 0.2: full-rate T1 transit max 0.1803,
      p99 0.169, 0 rows above 0.19. The rule sits 0.02 above that and 0.02
      below the 0.22 mechanical max.
  - **Gotchas.**
    - `speed_limit_violation` counts in `m4.log` are not evidence. The first
      latch reason wins, and clearing robots are exempt.
    - An M1 marker-identity swap on T1B1 (`robot_2` reported at `robot_1`'s
      pose for one frame, 46.5 sim-s) drove the EMA to 5.47 m/s on a parked
      robot. It was masked only by the yield exemption. A glitch detector is
      out of scope and recorded as a limitation.
    - The full-rate recorder (`/perception/scene_state`, passive, inside
      `vgu_ros`) is the only way to see M4's actual input. The M5 scene log
      samples about 1 row per wall-second.
  - **Spec.** The research design gets a Rev 9.2 line, and
    `fcfs_zone_radius_m` joins the tuning-parity parameter list.
  - **VM.** The tree is now `caaf95f` (manifest
    `/home/ubuntu/caaf95f_md5.txt`). This includes the
    `obstacle_in_candidate.yaml` resync from the Status residual. The
    pristine copies are `~/rag_pristine_caaf95f.yaml` and
    `~/orchestrator_pristine_caaf95f.yaml`.

- **2026-09-29** — **Rev 9.1: the nine `[REV9-OPEN]` markers are settled
  as coordinator resolutions (reviewable at the tag), and two pre-tag code
  items land.** Evidence: `25983a1` (spec), `a7730ee` (T3b rationale),
  `37a0dd5` (code).
  - **Spec.** The resolutions cover the following:
    - A10 is a rule-gap fix, not tuning.
    - The T0 denominator is 20 distinct moving-phase scenes.
    - A per-tier channel table sets obstacles on for T1/T2 and off for T3,
      with geometry true everywhere.
    - T3c is exempt from the oracle block.
    - T3b stops at 15 scored trials, with a cap of 30 episodes.
    - The first yield-deciding analysis is the scored unit: T3a
      absences count as misses, T3b is scored on answered trials only,
      and more than 30% degraded makes a cell inconclusive.
    - The gpt-4o snapshot is pinned at tag time, and the served model is
      recorded per call.
    - The backtrack is measured as peak minus minimum after the peak.
  - **Residuals.** These are still open at the tag:
    - The absent-decision rule for T0 probes and T2 RQ3.
    - T0's `prompt_static_obstacles` value, which is inert because no
      boxes are declared.
    - `served_model` on stage-2 (`RetreatChooser`) records.
  - **T3b rationale.** `obstacle_in_candidate.yaml` now states only the
    construction. No test pinned the text. Its header comments still cite
    the rev-8.6 ≥ 9/15 criterion and call yielder handling "an open
    decision"; both are stale.
  - **`served_model`.** Each backend parses the provider's `model` string
    into `BackendResponse.served_model`:
    - The `Reasoner` keeps the value from the last response, refusals and
      failed cycles included.
    - It writes the value to both `diagnostics` and
      `reasoner_config_effective`.
    - The value is None for mock, and for Gemini when the response has
      no `model`.
  - **`latched_at_goal`.** `rescore_arrivals.py` adds a row for any robot
    with no M5 acceptance line whose final M1 sample is within 0.35 m of
    its GT goal and fresh.
    - The row is dated from the start of the final dwell.
    - It counts as arrived and adds two CSV columns.
    - On the two T2b alternative-arm runs it credits `robot_2` (0.089 m
      and 0.085 m) and not `robot_3`.
    - Pre-existing gap: `accepted_late` robots still get no row and do
      not count as arrived. In the logged runs this has occurred once, in
      the discarded funded-battery-1 run `20260928_155012`.
    - Over all 12 run roots under `data/logs/vm_runs`, the only latched
      rows are those two T2b runs. `t0_t3c_verify` still aborts on its
      pre-existing clock-anchor error.
  - **Success criteria.** `9b1c7b9` carries the T0 denominator and the
    T3a/T3b absent-decision rules into the success criteria.

- **2026-09-29** — **Research design rev 9: the prereg amendment set is
  absorbed in place, and the spec is now the authoritative pre-`prereg-v1`
  text.** Documentation only; no code, config or VM change. Evidence:
  `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`
  (rev 9 entry, `Status:` line, inline `Rev 9:` notes) and the Rev 15
  header line in `docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`,
  which stays as the decision record.
  - **Absorbed.** A1–A10 and checklist items 1–26: the built battery with
    real scenario names, T3a decision-scored (B-executed cell dropped),
    the T3b test corrected to occupied-choice < 1/3 on
    executed-`robot_1`-yield trials, T2b on legacy grounding with the
    censored 0.6485 lower bound, the model table (gpt-4o + ER-2), and
    prompt v2 / stage-2 v3.
  - **Model table.** Filled: 1280 × 960 PNG as sent, `max_tokens` 2048
    (stage 2 inherits it), and the retry budgets. The config pins the
    alias `gpt-4o`, while the API served `gpt-4o-2024-08-06`; decision
    artifacts do not record the served snapshot (superseded by the
    2026-09-29 rev 9.1 entry: `served_model` is recorded). Still REQUIRED: the ER-2
    version, which the API does not expose, and the prompt-template
    hashes at tag time.
  - **Arrival definition pinned (F6).** Only position-check arrivals
    count. A robot latched at its goal counts as arrived, flagged
    `latched_at_goal`. This is the harness scorer's reading, the one the
    frozen margin used. `rescore_arrivals.py` still needs a latched-at-goal
    path: today it emits rows only for M5-reported arrivals (superseded
    by the 2026-09-29 rev 9.1 entry).
  - **Open for the coordinator** (superseded by the 2026-09-29 rev 9.1
    entry). There are 9 `[REV9-OPEN]` markers,
    listed by `grep -n REV9-OPEN` on the spec. Among them:
    absent/degraded-decision scoring, the passer-backtrack definition,
    per-tier `prompt_static_obstacles`, the T3c oracle block, and the T3b
    stopping rule.
    - The T3b oracle `rationale` neutralisation (amendments item 24) is a
      YAML edit and was deliberately not made.

- **2026-09-29** — **The first three-robot runs: the T2b smoke passes, and the
  forced-order margin is a LOWER-BOUND of 0.6485 (the alternative order ends
  in a permanent bystander latch).** Tree `6d66a0d`, all mock, runs
  2026-09-28 16:50–18:46 UTC: smoke S1, the harness (`oracle`/`alternative`
  × seeds 42, 43) and an oracle repeat R1 (seed 44). 0 apparatus failures.
  Evidence: `data/logs/vm_runs/t2b_smoke/T2B_SMOKE_SUMMARY.txt`, with the
  per-run dirs, `harness_20260928_171248/margin.json`,
  `ARRIVALS_RESCORED_T2B.csv`, `_analysis/` and `_vm_driver/`.
  - **Deploy.** Shipped `3ebb7ea..6d66a0d` (49 files). The tree checks
    609/609, and the install 82/82 after rebuilding `swarm_orchestrator`,
    `swarm_execution` and `swarm_simulation`.
    - Pristine `orchestrator.yaml` `c06bdb4e…` → `ca35f94e…`. `rag.yaml` is
      unchanged (`9fcc39ff…`). `fc_launch.sh` `cd7e49b6…` → `ffffb107…`; no
      launcher copies exist outside the tree.
    - The T2b USD builds and validates with 3 robots and markers 1–3.
    - The runs used `gen_orch_t2b.py`: legacy grounding, `robot_3`
      `start_delay_sec` 55, corridor half-length 0.5, `random` order.
      Preflight FAILs on the pristine config and PASSes after apply (the
      symbols-only NOTE: the VM has no `.git`).
    - Restored afterwards: orchestrator `ca35f94e…` in source and install,
      `rag.yaml` `9fcc39ff…`.
  - **Smoke (S1): PASS.**
    - `robot_3` stays stationary through the trigger in 6/6 runs (GT
      displacement 0.000 m). The trigger comes at M5 start +42.7–43.9 s.
    - The forced `robot_2` yield with `[robot_1, robot_3]` dispatches as
      three commands.
    - Ordered release: `robot_1` clears at +134.71 s after dispatch, and
      `robot_3`'s escort starts 0.04 s later. The pair set grows
      `robot_1+robot_2` → `+robot_2+robot_3` (it is cumulative). The
      yielder completes in the same instant as the last passer.
    - All three robots arrive (rescore 14/14 `within_tolerance` over 6
      runs). No bystander latch.
    - The literal `released: …` lines are not in any log: they are the status
      message's `detail`, which is not logged. The release is shown by the
      event order instead.
    - The episode fold was never exercised (0 `trigger folded`).
  - **RTF 0.34 with three robots** (two robots: ~0.39). The host is
    CPU-bound: load ~14 on 8 vCPU, GPU ~20%. The 55 s hold-back is validated
    with 11–12 s of headroom; no re-derivation is needed.
  - **Margin.** Oracle totals are 319.1 and 311.1 s. Alternative totals are
    514.3 and 524.6 s, with `robot_3` censored at the 300 sim-s horizon. The
    harness prints `margin=0.6485 … LOWER-BOUND`. The `oracle.margin` record
    in `margin.json` is NOT written into the YAML: that needs the owner's
    option-(e) call and `--accept-censored`.
    - With S1 and R1 added the margin is 0.6579 (supplementary).
    - The permanent latch is conditional on the once-mock: M5 re-analysed the
      stuck scene 34 times per run.
  - **Findings.**
    - `run_simulation --duration-sec` is ignored, so Isaac always stops at
      the scenario's `duration_sec`. The T2b header's "overrides this
      anyway" is wrong.
    - The oracle's `robot_2` return leg stalls 8–19 sim-s at the east aisle
      mouth in 4/4 oracle runs. This opens 5 solo-stall analyses per run.
    - `robot_1`/`robot_3` end 0.604–0.613 m apart: above the latch, but only
      0.004–0.013 m above the 0.6 m STALE band.
    - Arm B's FCFS yielder at the symmetric standoff is `robot_1` in only
      3/6 runs, so the header's "FCFS yields robot_1" is a coin flip live.
    - The latch drops RTF to ~0.285.
    - The harness GT scorer credits the latched alternative `robot_2`
      (0.09 m from its goal) as arrived at 57.5 s. M5 and the rescorer never
      do.
    - Use `REC_SEC` ≥ 1000 for a latched arm: at 950 Isaac finished GT but was
      killed before writing `run_manifest.json`.
  - **Rescore at N = 3** works unchanged. `run_both_arrived_*` means "all
    arrived", so only the column name is two-robot. The staging needs
    `decisions/` and a mock-labelled `orchestrator.yaml.used`.

- **2026-09-28** — **First funded battery batch (tree `3ebb7ea`): the T2b
  safety slice passes live, stage-2 v3 is verified on a real build, and T3c,
  T3a and T3b have their first model answers.** All B–D cells are probes at
  n = 1 per model, not collection. Evidence:
  `data/logs/vm_runs/funded_battery1/FUNDED_BATTERY1_SUMMARY.txt`, with per-run
  dirs, `ARRIVALS_RESCORED_FB1.csv` (17/17 within tolerance), `_analysis/` and
  `_vm_driver/`.
  - **Deploy.** `58bb428..3ebb7ea` was shipped: 20 files. The tree checks
    591/591, and the install 80/80 after rebuilding `swarm_orchestrator` and
    `swarm_execution`.
    - The pristine `orchestrator.yaml` is unchanged at `c06bdb4e…`, and
      `rag.yaml` at `9fcc39ff…`.
    - The old deploy scripts' in-container import check had always died on
      `ModuleNotFoundError: rclpy`, because `PYTHONPATH` was overwritten. It
      is now appended.
    - The VM stays at `3ebb7ea`. The T2b slices committed later (`4295de2`…)
      are not deployed.
  - **Group A (mock `_bshort` west yield): PASS.** The two-robot
    byte-identical claim holds live; details are in the M4 entry below.
  - **v3 deploy-skew check.** Run A carried a stage-2 mock, so the live build
    was proven before any funded call. Every answered stage-2 record (A1, D1,
    D2, D2b) has `stage2_prompt_version: 3`, and its `listing_order` equals
    the prompt's `- X:` lines. This supersedes the stage-2 v3 entry's
    "Pending: funded run".
  - **B/C, first `blocker_kind` data.** Every detected-blocker answer had a
    kind matching the member: `object` ×5 over 4 runs (T3c pallet, T3a box) and
    `transient` ×1 (C4). Every `none` answer carried an explicit null, so the
    key was never missing (71/71, including ER-2 with `force_schema` false).
  - **Detection is the weak link, not kind.**
    - gpt-4o detected the blocker on 2 of its 38 T3a/T3c analyses, and on 0/8
      for the transient member. Its `none` answers reason only from pairwise
      distance and facing.
    - ER-2 detected it on the first or second analysis in 3/3 episodes, then
      also reverted to `none` on re-analysis with the blocker still visible.
    - So T3a/T3c oracle wording must fix which analysis per episode counts.
  - **T3a hits.**
    - C2 (ER-2, object) a1 answered anomaly/reroute/object: a full hit,
      non-divergent from Arm B.
    - C4 (ER-2, transient) a2 answered bottleneck/temporary_wait/transient:
      the first divergent-and-correct T3a event.
    - After the reroute failed, ER-2 answered `priority_override`, which
      degraded to temporary_wait.
    - The transient member resolved at the despawn even with no command (C3),
      as item 18 predicted.
  - **T3b under v3.** Both kept trials (D1 gpt-4o, D2b ER-2) avoided the
    occupied candidate, and neither chose the first-listed, the default or
    letter A. On each draw two of those readings coincided, and the choice was
    neither.
    - ER-2's D2b justification names the blocked letter.
    - D2 (ER-2) named robot_2 and was discarded by item 23, then re-run as
      D2b. Its robot_2 sidestep drove into the NE rack, and the yield FAILED on
      the 242.8 s wall bound. The episode never resolved (item 25 again).
  - **Refusals and errors.**
    - gpt-4o refused on attempt 1 in 0/41 calls, with 0 fallbacks. The census
      band of 14–25% came from head-on frames; these scenes differ.
    - ER-2: one 120 s timeout (a ~128 s call) and two ConnectionErrors, all
      recovered on attempt 2.
    - No HTTP 429. Estimated spend is well under $1.
  - **VM end state.** `orchestrator.yaml` restored (`c06bdb4e…`, source ==
    installed); `vgu_ros` restarted; GPU idle; instance RUNNING.

- **2026-09-28** — **The remaining T2b slices landed: oracle
  `correct_order`, the launcher robot loop, robot_3's hold-back, three-robot
  episode scoping, permutation presentation order, the M3 multi-passer
  leftovers, and the `t2b_flow_ordering` scenario with its forced-order
  harness** (`4295de2`, `9315b86`+`ea02da7`, `daa2558`, `f76ae31`, `9d20b39`,
  `4e555ca`, `4f92163`). Unit-tested only. The VM work (T2b USD build, the
  three-robot smoke with `mpstat`/`uptime`, the forced-order runs and the
  margin) rides the next batch; another agent held the VM.
  - **Numbering.** Items cite
    `docs/reports/2026-09-27-three-robot-feasibility.md`. The brief numbered
    the hold-back #6, episode scoping #7 and the order scheme #8, following
    the Rev 2 Layer 7 text ("build item 6"). The report's build table numbers
    them #12 (geometry option a), #6 and #7.
  - **#3 Oracle** (`4295de2`). `OracleConfig` has an optional
    `correct_order`: every robot but the correct yielder, no duplicates. It
    also has an `OracleMarginRecord` (`margin`), which the harness writes.
    An ordering oracle on the `head_on` family must keep
    `expected_conflict.involved_robots` at the standoff pair. Unset fields
    stay out of every dump, so the generated family YAMLs are unchanged.
  - **#4 Launcher** (`ea02da7`). `fc_launch.sh` loops over the scenario's
    robots in robot-number order for the spawn parse, the odom/scan waits,
    one Nav2 stack each (the first starts the map server), the action waits
    and the Nav2 log collection. It also takes `SEED` (default 42).
    - Two-robot pin: DRY_RUN output of five two-robot cases equals goldens
      recorded from the pre-loop script (`9315b86`,
      `tests/unit/test_fc_launch_dry_run.py`).
    - One difference: an abort before stage 2 no longer lists two empty
      nav2 log sections in `tail_logs.txt`.
    - The VM `gen_orch` scripts are VM-side and not in the repo; the next
      batch writes a T2b one.
  - **Hold-back** (`daa2558`; brief #6). `TaskAssignment.start_delay_sec`
    (default 0).
    - Until the delay (M5 wall clock) has passed, the registry entry carries
      `"start_pending": true`. M4's `BaseMissionDriver` then records no
      goal, and M5 gives the robot no stall or arrival evidence.
    - The robot stays in the registry, so M1 keeps tracking it, and the
      prompt still shows its goal.
    - Absent or 0 publishes the exact old JSON (pinned).
    - T2b uses 55 s. The justification from the corpus timing is in the
      scenario header.
  - **#6 Episode scoping** (`f76ae31`; brief #7).
    - A solo stall outside a busy command of two or more robots is FOLDED:
      no analysis starts, and the robot joins the episode's members and
      `AttemptMemory`'s scope.
    - Members also include dispatched command robots. With three or more
      members, overlap is tested against the members (the merge) and the
      episode closes on the last member's arrival.
    - Two-robot pin: a two-robot scene cannot fold or reach three members.
      300 random two-robot operation sequences match the pre-change tracker,
      and every two-robot gate case is unchanged.
    - The report's union-find is realised as this single-slot merge.
      Multiple concurrently open episodes would change two-robot semantics.
  - **#7 Order scheme** (`9d20b39`; brief #8). Verdict: `random` did NOT
    draw permutations. It drew only `id_asc`/`id_desc`, which at N = 3 never
    put `robot_2` first.
    - `random` with three or more scene robots now draws a uniform
      permutation (a tuple; recorded as a list). It uses its own per-episode
      stream, so two-robot draws are identical (pinned against the old
      policy over 50 seeds × 12 episodes). Uniformity is test-checked over
      1200 draws.
    - `ReasonerRequest.robot_presentation_order` accepts an explicit tuple.
    - The T0 probe draws over its scene's robots.
    - `probe_presentation_order.py` records the first-listed robot of the
      standoff pair, not `known_robot_ids[0]`.
  - **#9 M3 leftovers** (`4e555ca`).
    - Derived multi-passer yields emit per-passer `crossing_clear_m` and
      `crossing_escort_m` (a later passer's is unbanded, as in legacy), and
      scale hold, wait and resolution backstops by the passer budget.
    - `filter_command_robot_ids` prunes dropped robots from
      `crossing_order` and its aligned lists, and renumbers
      `linked_position`.
    - Two-robot derived output is pinned by a digest taken at `9d20b39`.
  - **#11 Scenario + harness, #2 map** (`4f92163`). The geometry deviates
    from `wopen_eopen`: the corridor is 1.0 m, not 2.0 m.
    - M4 drives every passer to park + 0.65 m. With the 2.0 m corridor,
      robot_3's escort ends 0.06 m from robot_1's +2.5 goal, so the oracle
      order itself would latch.
    - robot_3 holds at x = −2.45, and the band for this corridor is
      [−2.5, −2.324]. The constraint checks run as unit tests with M3's and
      Arm B's own code: tracking, spawn latch, Arm B `head_on` across the
      standoff grid, park reachability, and escort ends against the 0.45 m
      latch and the 0.6 m STALE band.
    - Harness: `scripts/t2b_forced_order.py` (preflight / plan / score) and
      `scripts/vm/t2b_forced_order.sh`. Preflight refuses unless the safety
      commits (`9c38042`, `99f4699`, `38868d2`, `fc441d4`) and the
      hold-back are in the deployed tree, by symbol and, in a git checkout,
      by ancestry. It also checks the T2b M5 settings and
      `grounding.mode: legacy`.
  - **Flags.**
    - The alternative order will likely end in a permanent robot_2/robot_3
      bystander latch at the west end (infeasible, not slower). The margin
      is then a censored lower bound, and the cost model becomes report
      option (e): an owner decision. (Confirmed live on both seeds: see the
      2026-09-29 T2b smoke entry; LOWER-BOUND 0.6485.)
    - Under the shipped derived mode, the alternative grounds a reroute, and
      the oracle's robot_3 escort ends 0.27 m from robot_1's goal (a latch).
      Live T2b collection in derived mode needs a decision; the harness runs
      legacy.
    - The 55 s delay assumes a three-robot RTF ≥ ~0.25. The smoke must
      record the RTF and robot_3's position at the trigger. The brief also
      said "released when the standoff forms"; releasing then (~24–29
      wall-s) would move robot_3 ~0.7 m before the trigger, so "stationary
      at trigger" took precedence. (Superseded by the 2026-09-29 T2b smoke
      entry: RTF 0.34, trigger at +42.7–43.9 s, robot_3 stationary in 6/6;
      55 s validated.)
    - The fold has no proximity test. In any scene with three or more robots
      (e.g. the four-robot `dynamic_anomaly`), a solo stall anywhere during
      another pair's command is deferred until that command resolves, not
      analysed at once.
    - `score` prints a censored margin as LOWER-BOUND (feasibility contrast),
      never PASS, and writes it to the scenario only with
      `--accept-censored`. Preflight checks commit ancestry only when the
      safety files equal the checkout's HEAD. An rsync deploy over an older
      checkout relies on the symbol checks, with a NOTE.
    - `tests/unit/test_m5_node_t2b_dispatch.py` runs both arms through M5's
      production pipeline (mock backend → parser → legacy grounding →
      filter → fan-out) from a solo `robot_2` stall. Each dispatches the
      forced three-robot yield with per-passer clearances.
    - `orchestrator.yaml` changed (the goal-table row and a `random`
      comment), so the VM's pristine-md5 `gen_orch` copies need refreshing.

- **2026-09-28** — **Stage-2 prompt v3 lists the candidates in a seeded
  order independent of the letters (amendments item 26)** (`526d957`). This
  answers calibration divergence 2: v2 listed in letter order, so letter A
  was always the first-listed slot and a first-slot prior read as pick-A.
  Letter, listing slot and geometry rank are now decoupled three ways. The
  letter→candidate assignment (`derive_letter_seed`, `assign_letters`) is
  byte-unchanged. Needs a colcon rebuild of `swarm_orchestrator`.
  - **Seed scheme** (`retreat_stage2.py`).
    - `derive_listing_seed(base, i)` is SHA-256 of `"{base}:stage2list:{i}"`.
      It reuses the letter draw's `letter_seed_base` and
      `letter_draw_index`; the salt keeps it independent of the letter
      stream (`"{base}:stage2:{i}"`).
    - `draw_listing_order(letters, seed)` shuffles the sorted letters with
      `random.Random(seed)`.
    - Test-checked over 400 draws at k = 4: letter A lands 60–140 in every
      slot, and so does the default letter. Over 1600 draws the joint
      (default letter × slot of A) fills all 16 cells, 55–145.
  - **Prompt.** v3 renders both the candidate lines and the answer
    enumeration (`"<one of C, A, D, B>"`) in listing order. Otherwise the
    enumeration would keep A first-mentioned. The text is v2's otherwise.
    - `RetreatChoiceRequest.listing_order` is required under v3, so a
      caller cannot silently fall back to letter order. Under v2 it must be
      unset, and it must be a permutation of the letters.
    - `candidates` stays in letter order, and the chooser's valid-label set
      is unchanged.
  - **Artifact.** `stage2` gains:
    - `listing_order`: the shown letters in listed order;
    - `listing_seed`.

    `draw_listing_order(letters, listing_seed)` reproduces the order. A test
    parses the `- X:` lines of the recorded `user_prompt` and checks they
    equal `listing_order`. Both fields are null on skipped calls and on every
    v2 record. The log line gains `listing=`.
  - **Three positional readings, never merged** (on the `stage2` block, all
    in *shown* letters):
    - chose the first-listed: `choice == listing_order[0]`;
    - chose the default: `choice == default_letter`, equivalently
      `grounded_label == default_label`;
    - chose letter A: `choice == "A"`.

    Under v2 the first and third are the same event (first-listed is always
    A). `TestListingOrder::test_three_positional_readings_stay_distinct`
    pins a k = 3 draw (base 0, draw 0: default B, listed C first). Answering
    A, B or C there makes exactly one reading true. The two-letter-space
    trap of the item-22 entry still applies.
  - **v2 is frozen history, not retired.** Its corpus is the six funded
    stage-2 calls of the calibration mini-pilot
    (`data/logs/vm_runs/calibration/20260928_104408` … `_122832`).
    - `Stage2PromptVersion = Literal[2, 3]`, and `prompt_version=2` still
      renders letter order.
    - Pins are kept as `_V2_*`: marked `61502f20…`/`3ff66fe9…`, unmarked
      `4275d2ec…`/`d91e23c9…`.
    - v3 given the letter-order listing reproduces all four v2 SHAs byte for
      byte (test). v2 and v3 share one template, so any later template edit
      must fork it as a new version rather than edit it.
    - All six calibration `user_sha256` values re-render through v2. That is
      one inlined test (run `112237`: default B, answered A) and one
      `skipif`-absent test over the git-ignored runs, which asserts 6.
  - **v3 pins** (`tests/unit/test_stage2_prompt.py`). Listings are
    head-on `[B, A]` and three-robot `[C, A, D, B]`:
    - marked: `4655915e…` head-on, `27c1ed70…` three-robot;
    - unmarked: `9c922b60…` / `d1899a4e…`.
  - **Mock.** Unaffected. `retreat_choice_b.json` forces the *shown* letter
    B, which does not depend on the listing: a test checks that two requests
    differing only in `listing_order` get the same answer. The item-22 advice
    stands; read `letter_assignment["B"]` or `grounded_label` for the
    candidate.
  - **Suite.** 2171 passed, 60 failed, 14 skipped, 3 collection errors. The
    failing set is identical to the pre-change baseline (2137 passed). It is
    M6/Isaac, ArUco parity and six unit tests, all pre-existing and none in
    stage 2. `ruff check` is clean on the touched files; the repo-wide count
    is unchanged at 152.
  - **Deploy trap: tree skew fails quietly in both directions.**
    - A stale `swarm_orchestrator` build with a synced `reasoning/` builds a
      v3 request with no `listing_order`. The validator raises, and the
      stage-2 catch-all records `degraded` with `requires listing_order`.
      Every call grounds the default, so the instrument is off.
    - A rebuilt `swarm_orchestrator` with a stale `reasoning/` has the field
      silently dropped (`extra` is ignored). The prompt renders in letter
      order and is stamped `stage2_prompt_version: 2`, yet the record still
      carries a `listing_order` that was never shown.
    - Trust `listing_order` only when `stage2_prompt_version == 3`. A
      v2-stamped record with a non-null `listing_order` means a stale
      `reasoning/`.
  - **Pending:** a funded run showing a `stage2_prompt_version: 3` record
    whose `listing_order` matches its prompt's `- X:` lines (superseded by
    the later 2026-09-28 funded-battery entry: verified on D1, D2 and D2b
    and on the mock run A1); `docs/specs/module5_orchestrator.md`
    is still not updated with the stage-2 fields.

- **2026-09-28** — **Calibration mini-pilot (amendments item 16) ran on both
  funded models. No outcome, timing or safety cliff. Of the two behavioural
  divergences, divergence 1 does not block the freeze; divergence 2 is a
  freeze-timing decision for the user.** This was
  the first funded run of prompt v2, derived grounding and stage 2. Evidence:
  `data/logs/vm_runs/calibration/CALIBRATION_SUMMARY.txt`, with per-run
  dirs, `ARRIVALS_RESCORED_CALIBRATION.csv` and `_vm_driver/`.
  - **Funding probe.** One text-only call per backend from `vgu_ros`:
    - gpt-4o: HTTP 200 (`gpt-4o-2024-08-06`; 500 RPM, 30k TPM).
    - ER-2 Interactions API: HTTP 200. The 2026-09-27 monthly-cap 429 is
      gone.
    - No 429 appeared in any run.
  - **Apparatus.**
    - Cell: `_bshort` west, goals 2.6 / −1.5, n = 3 per model.
    - Settings: gate `swap`, random order with seed null, obstacles ON (the
      block is in 50/50 prompts), debug and raw frames, shadow on,
      `t0_probe_mode` off.
    - Tree: the VM tree is `58bb428`, verified 589/589 against local
      `git archive`. Nothing was deployed.
    - Verified in every run: startup lines `grounding mode=derived` and
      `stage2 marks enabled`, and 50/50 artifacts with `prompt_version: 2`
      and `grounding_mode: derived`.
    - CE2 was an apparatus failure: robot_1's Nav2 lifecycle never went
      active, so there were 0 API calls. That cell was re-run once as CE2b.
  - **In band against N1–N3 and K4–K6/S1–S2:**
    - episode outcome 6/6, position-verified. Of the 12 first arrivals, 11
      pass the M1 check. CE3 robot_1 was accepted as `stale_estimate` and is
      verified by GT only (0.126 m). The rescore CSV also has 10 repeat
      lines; 0 flipped, 0 box overlap;
    - first yield 150.8–152.7 s;
    - minimum pairwise distance 0.223–0.262 m;
    - backtrack 0–0.066 m;
    - the derived park pose equals legacy, (1.79–1.81, ±0.36–0.38), or
      1.44 after a reverse opening (legacy 1.46/1.52).
  - **Divergence 1: gpt-4o now names robot_2 on west.** It did so on the
    first yield decision in 3/3 runs, so the gate fired 0/3; in N it named
    robot_1 3/3.
    - Two of the three were `id_asc`, so it is not the first-slot prior.
    - Its reasons cite robot_2 being "already stopped" (robot_1 was SLOW at
      the trigger) or the goals new in v2.
    - The robot_1 anchor, and so "the gate is necessary for gpt-4o", rests on
      v1 data only.
    - This does not block the freeze: outcomes are unchanged, and nothing is
      pooled across the bundle.
  - **Divergence 2: every stage-2 answer was letter "A", 6/6 across both
    models.**
    - Two of those were non-default picks. Under no letter preference,
      P = 1/64.
    - Letter and first-listed slot are confounded.
    - The candidates are mirror-symmetric with nothing visible between them,
      so this shows the prior exists, not that it overrides evidence.
    - If the prior persists when a candidate is visibly occupied, a pick-A
      policy lands exactly on chance (1/3) in T3b, and the approved
      occupied-choice < 1/3 test would come out null by prior.
    - Separating letter from slot changes the stage-2 rendering and its pinned
      SHAs, so the user decides before the freeze (superseded by the later
      2026-09-28 listing-order entry: stage-2 prompt v3, item 26).
  - **Stage-2 health.**
    - All 6 answered on attempt 1: k = 2, marks drawn, 0 refusals, 0
      timeouts, 0 degraded. One valid `yield_refused` skip.
    - Latency: gpt-4o 1.5–2.2 s, ER-2 3.8–5.2 s.
    - The extra call adds about 3–6 s between the first analysis and
      dispatch.
  - **Refusals (gpt-4o).**
    - Attempt 1 refused on 2/20 calls (10%). That is below the census band of
      14–25%, but within noise at n = 20. Terminal 0.
    - `image_fallback_used` fired once, reported separately: CO3's
      yield-deciding call was answered on the grey image. It is the fallback's
      first closed-loop use.
  - **Other findings.**
    - **Resolution-time tails.** CO3 took 422 s and CE3 645 s, driven by the
      existing return-leg corridor-mouth Nav2 stall (80.5 and 139.7 sim-s,
      baseline 3.6–44.7). CE3 had no commands during the stall.
    - **CE3 stale arrival.** robot_1's online arrival was accepted as
      `stale_estimate`; ground truth puts it 0.126 m from goal.
    - **Repeat arrival lines.** M5 re-sends `temporary_wait` to a robot that
      has already arrived, so arrival lines repeat. Scorers must dedupe.
  - **VM end state.** `orchestrator.yaml` pristine, source and installed
    `c06bdb4e…`; `vgu_ros` restarted; GPU idle; instance RUNNING.

- **2026-09-28** — **The T3b obstacle-in-candidate scenario is built and
  mock-smoked on the VM, both runs PASS. This was also the first live run of
  the derived and stage-2 stack.** Commits: `e205f5f` (per-scenario band),
  `9d4141a` (stage-2 mock passthrough in `fc_launch`), `58bb428` (scenario,
  oracle, map, tests). Design header:
  `isaac/config/scenarios/obstacle_in_candidate.yaml`. Evidence:
  `data/logs/vm_runs/t3b_smoke/T3B_SMOKE_SUMMARY.txt`. The funded VLM run is
  still pending.
  - **Deviation: this is not the wopen_eopen shape.**
    - The racks fill |x|, |y| > 0.6, so the family's far candidate is inside
      a rack. At the family park point x = ±1.789, the far candidate sits at
      +0.72, and with the 0.36 m sidestep it ranks first.
    - Shrinking the sidestep until 2× fits in the aisle leaves the passer
      about 3 cm from the parked yielder.
    - The design moves the yield into the plus junction instead:
      - the corridor is 0.55 × 1.6 m at x ∈ [0.4, 2.0];
      - robot_1 spawns at (0, 0), robot_2 at (2.5, 0);
      - robot_1's park point is x = −0.323. At the nominal standoff the
        park-point floor sets the backup.
  - **Candidates and the `ranked[0]` pin.** robot_1 yields; labels are M3's.
    - Ranked order is C, A, B. C = (−0.323, +0.72) is occupied, A =
      (−0.323, +0.36), B = (−0.323, −0.36). The band drops D.
    - All three tie on sidestep clearance, so C ranks first on distance from
      the corridor.
    - The box is a grey `static_box` timed obstacle, 0.40 × 0.30 × 0.35 m at
      (−0.32, 0.81). It spawns at 1 s, never despawns and is not baked into
      the map.
    - `tests/unit/test_obstacle_in_candidate_scenario.py` pins, using the
      scenario's own numbers:
      - k = 3;
      - `ranked[0]` = C = the oracle's occupied and classical candidate;
      - C's sweep enters the box;
      - A's and B's sweeps keep ≥ 0.24 m from the box (robot half-width
        0.09 + wall margin 0.15);
      - all of the above across separations of 0.25–0.98 m, a ±0.2 m shift
        of the meeting point, ±0.06 m yielder y, and a passer up to 0.04 m
        north of the yielder;
      - the known flip: a passer 0.05 m north makes B rank first.
  - **Band delivery** (`e205f5f`).
    - New key `grounding_aisle_y_band_m` in `orchestrator.yaml`, default
      `null`, set per scenario like `scenario_geometry`. The goal table
      there lists T3b's values: corridor centre 1.2, half-length 0.8, band
      [−0.55, 1.0].
    - It is merged into the grounding params once at startup, so the
      pipeline and Arm B's `ClassicalRetreatContext` rank from the same
      params.
    - It is recorded as `grounding_params_source.aisle_y_band_override_m`
      and appears in the startup log line.
  - **Oracle.** New `RetreatOracleConfig` (`isaac/vgu_sim/config.py`),
    added alongside the existing oracles: yielder, passer,
    `candidate_count`, `occupied_candidate`, `correct_candidates`,
    `classical_candidate`, objective `avoid_occupied_candidate`. Labels are
    M3 labels (`grounded_label`), never shown letters.
  - **First VM outing of derived + stage 2: no surprises in the plumbing.**
    - The startup log showed `grounding mode=derived … band_override=True`
      and `stage2 marks enabled`.
    - 36/36 artifacts carry `grounding_mode: derived` and the band.
    - The `fc_launch` mock passthrough (`MOCK_RETREAT_CHOICE_FILE`) worked.
  - **Smoke S1** (`20260927_182225`, stage-2 mock forcing shown B, seed 1).
    - Stage 2 answered B → M3 A (the default letter was A = C).
      `marks_drawn: true`.
    - The yielder parked 3.5 cm from A and 0.28 m from the box. robot_2 was
      escorted past.
    - Both robots arrived, verified at 0.09 m. The era-aware rescore gives
      2/2 within tolerance.
    - Arm B's `classical_retreat` was C, the occupied candidate
      (`same_yielder` true, `equals_executed` false).
    - The only safety latch was the standoff itself, before dispatch. The
      family runs show the same burst (e.g. 1752 stops in `bshort2`
      `20260926_065219`).
  - **Parallax verdict: PASS**
    (`data/logs/vm_runs/t3b_smoke/_analysis/s1_stage2_parallax.png`).
    - The occupied candidate's ring is centred on the box's south part, and
      the box fills most of it.
    - The adjacent ring clears the box image by ~25 px.
    - The floor edge images ~23 px inward, as the 0.21 m-plane homography
      predicts.
  - **Smoke S2** (`20260927_183837`, no stage-2 script, so
    `skip_reason=no_backend`). This is the outcome contrast, and it is not
    what the design note expected. Nav2 never refuses anything, because the
    sidestep is raw `cmd_vel` on chassis odometry with Nav2 and
    `collision_monitor` bypassed. Instead:
    - The default C drove robot_1 into the box. It was pinned 0.038 m from
      the face for 71 sim-s (`_analysis/s2_pinned_f870.png`).
    - The yield ended FAILED only on M4's wall-clock bound, 242 wall-s after
      dispatch. The hold never began, so robot_2 was never escorted.
    - Both base missions resumed and re-deadlocked in the corridor mouth
      (separation 0.40 m).
    - The mock's scripted `none` answers meant nobody arrived. With a live
      VLM the episode would be re-analysed.
  - **Flags for the caller:**
    - **Only robot_1 is a designed yielder.** If robot_2 yields, it parks at
      x = 2.723, and the same band admits its +0.72 candidate, which is in
      the NE rack. S2's Arm B did exactly that: robot_2's "C" at (2.83,
      0.71). Collection must either restrict scoring to robot_1 yields or
      force the yielder.
    - **Criterion mismatch.** rev 8.6 tests ≥ 9/15 against chance 1/3
      (p = 0.031). But avoiding one of three candidates has chance 2/3, and
      against that 9/15 gives p = 0.80; α = 0.05 needs 14/15. This needs a
      prereg decision; the test pins `chance_rate` = 2/3.
    - Arm B's yielder is a first-come-first-served tie in this geometry.
    - S1 showed an 18 s Nav2 pause when the robot re-entered the corridor
      from the off-axis park.
  - **VM state.** Tree 58bb428, 589/589 files. Pristine `orchestrator.yaml`
    `c06bdb4e…`, `rag.yaml` `9fcc39ff…`. The USD is VM-only. End state
    restored.
  - **Not updated:** `docs/specs/module5_orchestrator.md` (new key).

- **2026-09-28** — **Stage 2 is complete for T3b: set-of-mark letters are
  drawn, letters are counterbalanced, stage 2 has its own retry budget, and
  the shadow records Arm B's stage-2 answer** (`49416c7` drawing, `ad10aeb`
  letters + budget, `e73c189` shadow). This closes amendments items 21–22 and
  both riders. T3b is now blocked only on its scenario and a VM run. It needs
  a colcon rebuild of `swarm_orchestrator`: there is a new module and a new
  `swarm_perception` exec_depend.
  - **Item 21: set-of-mark drawing** (`swarm_orchestrator/stage2_marks.py`).
    - **Where it happens.** M5 reads its own dumped stage-1 PNG. It places
      each candidate with `swarm_perception.geometry.world_to_pixel`, which
      applies the inverse of M1's pixel→world homography (the same mapping
      M1's robot boxes use). The math is not duplicated. The pixel position
      is scaled by PNG size ÷ calibration `image_size`, so
      `frame_downscale_width` is handled. The drawing is written to
      `<request_id>_stage2.png`, beside the frame.
    - **What the model gets.** That image and a v2 prompt that says the
      letters are drawn.
    - **Calibration.** New key `stage2_calibration_path`. `null` means the
      `swarm_perception` share `config/calibration.yaml`, the file M1
      launches with. It is loaded once at startup, and a failure is never
      fatal.
    - **Drawing spec.** Each candidate gets:
      - a ring the size of the robot footprint (0.15 m radius, 34 px at
        1280×960), drawn black 3 px under white 1 px;
      - a small white badge at the exact point (radius 0.0095 × width,
        12 px, minimum 9), with a 2 px black outline;
      - a black Hershey letter centred in the badge.

      There are no status colours. It is a ring, not a disc, so an
      obstacle on a candidate stays visible; a 0.3 m box is about 69 px.
    - **Degradation.** Any of these sends the unmarked frame and a prompt
      that says "not drawn", with `stage2.marks_drawn: false` and
      `stage2.marks.reason` recorded:
      - no marker or no calibration;
      - an unreadable frame;
      - aspect mismatch above 1 %;
      - any candidate outside the frame;
      - any render exception.

      It never costs the call. `stage2.marks` records every letter's
      `(u, v)` in the drawn image, the scale and the calibration path.
      `_cleanup_frame` also removes `_stage2.png`.
    - **Deviation from rev-8 A.1/A.3.** The marks go on the stage-1
      *annotated* frame (arrows and goal markers kept), not on a fresh M1
      frame with them dropped. The homography is at the marker plane
      (`plane_height_m` 0.21), the same plane M1's robot positions live on.
  - **Stage-2 prompt v2.** `Stage2PromptVersion = Literal[2]` (superseded
    by the later 2026-09-28 listing-order entry: `Literal[2, 3]`, current 3,
    v2 frozen). v1 is
    retired, not frozen, because no v1 data exists:
    - `e358229` was never pushed; `git branch -a --contains` lists only this
      branch;
    - it was never deployed (VM deploy was still pending);
    - nothing under `data/` has a `stage2` key;
    - both API backends are funding-blocked.

    v2 has two variants:
    - marked: `61502f20…` head-on, `3ff66fe9…` three-robot. It uses A.3's
      "Choose the marked retreat position…" wording and the sentence "Each
      position is marked on the image by its letter in a white disc, inside
      a ring the size of the robot.";
    - unmarked: byte-identical to v1, pins `4275d2ec…`/`d91e23c9…` kept
      (`tests/unit/test_stage2_prompt.py`).
  - **Item 22: letter counterbalancing** (`retreat_stage2.py`). M3's labels
    and the grounder are unchanged. The letters the VLM sees are a seeded
    uniform permutation of M3's label set. The answer is mapped back to M3's
    label before grounding.
    - **Seed.** `derive_letter_seed(base, draw_index)` is SHA-256 of
      `"{base}:stage2:{i}"`. `base` is M5's presentation-order seed
      (`prompt_robot_order_seed`, else derived from `VGU_RUN_ID`/session).
      `i` counts derived-yield stage-2 invocations per M5 process, so paired
      runs with the same run id get the same letter sequence.
    - **Artifact fields.** `stage2` gains:
      - `default_letter`: the shown letter of rank 0;
      - `letter_seed_base`, `letter_draw_index`, `letter_seed`;
      - `letter_assignment`: letter → `candidate_label`, `rank`, `x`, `y`;
      - `letter` on each ranked candidate;
      - `grounded_label`: the M3 label handed to the grounder.

      `assign_letters(len(candidates), letter_seed)` reproduces the
      assignment, and a test checks that.
    - **Two letter spaces, a trap for analysis.**
      - `stage2.choice` and `default_letter` are in *shown* letters.
      - `default_label` and the command's `yield.retreat_choice` are *M3*
        labels.
      - "Chose the default" is `choice == default_letter`, or
        `grounded_label == default_label`.
      - Never compare `choice` with `retreat_choice`.
      - (Extended by the later 2026-09-28 listing-order entry: "chose the
        first-listed" is a third reading, `choice == listing_order[0]`.)
    - **Balance.** Default-letter balance is test-checked: 200 draws over k
      = 2 land 70–130 on A, and k = 4 is near-uniform.
  - **Rider: stage-2 budget.** New keys `stage2_max_attempts: 2` and
    `stage2_timeout_sec: 8.0`. They replace stage 1's attempts and timeout
    in a copy of the reasoner config; sampling stays stage 1's.
    - The worst case is 16 s, inside one `command_timeout_sec` (20 s),
      instead of 4 × 120 s on openai.
    - 8 s is above every measured stage-1 call: gpt-4o 2.1–6.0 s, ER-2
      3.2–3.8 s. The stage-2 prompt is shorter and the answer is one
      letter.
    - Each `RetreatChoiceResult` records `max_attempts` and `timeout_sec`.
  - **Rider: Arm B's stage-2 answer** (`shadow_classical.py`). The shadow
    gets the pipeline's params, geometry, obstacles and gate mode
    (`ClassicalRetreatContext`). It records `classical_retreat` on every
    shadow record.
    - **What it computes.** It runs `resolve_yield_roles` and then
      `prepare_retreat_selection` for the *classical* yielder, and records
      `ranked[0]`: M3 label, x, y, backup, lateral, and the candidate count.
    - **Status.** `computed`, or one of:
      - `not_applicable`: no classical yield, or not in derived mode;
      - `unavailable`: gate refusal, infeasible backup, or no candidate;
      - `error`: isolated like the censoring flag. The decision is kept and
        the error goes to `shadow_error`.
    - **Comparison.** `finalize` compares it with the executed yield by
      yielder and position, at the command's 3-dp rounding, never by
      letter. It sets `comparable`, `same_yielder`, `equals_executed` and
      `executed`. The comparison is not comparable with no command or a
      non-derived yield.
  - **Not updated:** `docs/specs/module5_orchestrator.md` (still also
    missing the earlier stage-2 fields).
  - **Mock smoke.** `retreat_choice_b.json` now forces the *shown* letter
    B. Read `stage2.letter_assignment["B"]` or `grounded_label` for the
    candidate it grounded. To force a particular candidate, pin
    `prompt_robot_order_seed` to a value whose draw 0 puts B there.
  - **Packaging.** `swarm_perception` is imported lazily. An M5 environment
    without it still starts, and logs `calibration_unavailable` with stage 2
    unmarked.
  - **Parallax check for the T3b author.** The homography is at the marker
    plane, so the rings sit where a robot marker would be seen.
    - With the camera at 3 m over the origin, floor-level features at
      |r| ≈ 1.83 m appear about 7 % closer to the image centre. That is
      about 0.13 m, or ~29 px, against the 34 px ring radius.
    - The top of a 0.9 m box lands about 0.6 m farther out.
    - Check the obstacle's image footprint against the ring on an Isaac
      frame, not in world coordinates.
  - **Pending:** the T3b scenario, and a VM run that shows `marks_drawn:
    true` with the letters over the right spots on a real frame. Check the
    M5 startup log for `stage2 marks enabled`. An unavailable-calibration
    warning there means stage 2 runs unmarked. (Superseded by the later
    2026-09-28 T3b entry: scenario built, and VM run `20260927_182225`
    showed `stage2 marks enabled` and `marks_drawn: true`, with the letters
    on the right spots.)

- **2026-09-28** — **Derived grounding and stage-2 retreat selection are wired
  into M5, and `config/rag.yaml` now says `grounding.mode: derived`**
  (`e358229` wiring, `1648dd2` flip; revert `1648dd2` alone to go back to
  legacy). This finishes the M5 half of the Pillar 2 slice (2026-09-27 entry
  below). VM deployment is pending and rides the next batch. `swarm_orchestrator`
  gains a new module, so it needs a colcon rebuild; see the VM harness traps.
  - **What existed and what was built.** The candidates, the grounder,
    `RetreatChoiceDecision`, `parse_retreat_choice_text` and the schema all
    existed. New in this change:
    - the stage-2 prompt, `reasoning/vlm/stage2_prompt.py`;
    - the call, `RetreatChooser` in `reasoning/vlm/retreat_chooser.py`;
    - the M5 step, `swarm_orchestrator/retreat_stage2.py`.
    `InProcessPipeline` builds one `SnapshotFrame` from the stage-1 request
    (the analysed scene with registry goals). The same frame, geometry,
    obstacles, gate mode and params go to both `run_retreat_stage2` and
    `ground_fn`, so the letters resolve against the same poses.
    `crossing_order` is not passed, so the grounder reads it off the decision.
  - **Stage 2 ships with text-only letters (flagged gap; superseded by the
    later 2026-09-28 stage-2 completion entry).** Rev-8 A.1/A.3
    have M1 draw lettered marks on a fresh decision frame, with arrows and
    goals dropped. That is not built. The prompt lists the letters with
    world coordinates, says they are not drawn, and reuses the stage-1
    annotated frame as-is. This does not block the wiring, but it **blocks
    T3b collection**: without marks, the VLM cannot tie a letter to the
    obstacle it sees.
  - **Stage-2 prompt, version 1** (`CURRENT_STAGE2_PROMPT_VERSION`,
    independent of the stage-1 `PromptVersion`). Two renderings are
    SHA-pinned in `tests/unit/test_stage2_prompt.py`: head-on 2-candidate
    `4275d2ec…` and three-robot 4-candidate `d91e23c9…`. Candidates are listed
    in letter order, never rank order, and without sweep clearances, so the
    geometry-max answer does not leak. **Confound for T3b:** labels follow
    generation order, and mirror-image candidates tie in the ranker and
    break on label. In a symmetric scene, A is therefore both the
    geometry-max default and the first-listed slot. The stage-1 first-slot
    prior finding makes that worth controlling before T3b is scored.
  - **Degradation chain.** Stage 2 never blocks, and every failure grounds
    `ranked[0]`.
    - It runs only for a `yield` in derived mode. Other cases record
      `stage2: null`.
    - It skips the call, with `status=skipped`, for any of these
      `skip_reason`s: `yield_refused`, `no_candidates`, `single_candidate`
      (k = 1, nothing to choose), `disabled` (the new
      `stage2_retreat_selection: false` key in `orchestrator.yaml`), and
      `no_backend`. The grounder then tags `retreat=default:no_choice`.
    - Inside the call, timeouts, backend exceptions (such as an HTTP 429)
      and refusal-shaped or unparsable text each spend an attempt, with a
      re-ask for the last two. The attempts are bounded by the stage-1
      `ReasonerConfig` (`max_attempts` × `timeout_sec`). Exhausting them
      gives `status=degraded` with `failure_cause`
      `timeout`/`backend_error`/`refusal`/`parse_failure`, and
      `retreat=default:no_choice`.
    - A well-formed answer naming an unrendered letter ends the call at once
      (`failure_cause=invalid_label`). It is handed to the grounder, which
      tags `retreat=default:invalid_label`: the measured cause is kept, not
      retried away.
    - Any exception in stage 2 itself is recorded as `error`, with the same
      default.
    - **Funding:** both API backends are blocked, so stage 1 fails first
      and stage 2 never even fires live. When it does, the worst case with
      the shipped config is 4 × 120 s on openai and 2 × 120 s on gemini,
      the same bound as stage 1. A separate stage-2 attempt/timeout key
      does not exist yet (superseded by the later 2026-09-28 stage-2
      completion entry: 2 × 8 s).
  - **Mock.** The stage-1 mock is scripted, so sharing it would make stage 2
    consume the next `VGU_MOCK_DECISION_FILE` entry. Stage 2 therefore gets
    its own mock only when `VGU_MOCK_RETREAT_CHOICE_FILE` names a script, a
    single object or an array (`config/mock_decisions/retreat_choice_b.json`
    forces B, for T3b's smoke). Otherwise the result is
    `skip_reason=no_backend`. Real backends reuse the stage-1 instance
    (`build_retreat_choice_backend`).
  - **Artifacts** (every triggered and probe artifact). `grounding_mode`;
    `grounding_params_source` (path, `section_present`, params);
    `grounding_degradations`, lifted from the command because per-action
    messages drop it; and `stage2`. The `stage2` block holds the ranked
    candidates with clearances, `default_label`, the prompt with SHA-256
    hashes and the image path (never bytes), the `RetreatChoiceResult`, the
    choice and the cause. There is also one `stage2 request=…` log line per
    derived yield. Grounding params are loaded once at startup from
    `grounding_params_path` (new key, default `config/rag.yaml`). A missing
    file or invalid section stops M5; a missing section runs legacy and
    warns.
  - **The flip is not byte-equivalent, and no SHA pin says it is.** Both pins
    in `tests/unit/test_command_grounder_derived.py` (`d1958150…`) cover
    legacy mode only: `mode="legacy"`, and they assert no `degradations`.
    What carries equivalence for the shipped config is:
    - `test_reproduces_the_legacy_scene_geometry_maneuver`: 1.489 / 0.36 /
      2.739 at the deadlock pose;
    - the new `test_repo_config_is_derived_with_default_thresholds` (the
      shipped config equals the params those tests use);
    - `test_repo_config_keeps_the_verified_maneuver_m4_executes`: every key
      M4 reads, plus the wait and resolution time, equals legacy at that
      pose.

    Derived commands also differ from legacy:
    - they carry `degradations`;
    - they carry `retreat_x_m`/`retreat_y_m`/`retreat_choice`/`crossing_order`
      instead of `park_*`. Nothing in M4, M5 or `scripts/` reads `park_*`
      (re-grepped). `park_coord_m` equals `retreat_x_m` there;
    - passer waits carry `linked_position`;
    - an out-of-band yield reroutes the yielder instead of being clamped;
    - without a declared geometry, derived uses its own fallbacks (escort
      clearance 0.5 vs legacy 0.65; backup from `backup_clearance_m`
      instead of `PARK_ABS_X_M`), so the distances differ from legacy. M5
      ships a geometry, so this does not apply live.

    So post-flip decisions must not be pooled with legacy-grounded ones on
    grounding-dependent outcomes.
  - **Not updated:** `docs/specs/module5_orchestrator.md` (artifact fields,
    config keys) and `docs/specs/module3_rag_grounding.md`.
  - **Pending:** VM deploy and a mock smoke of a derived yield with
    `VGU_MOCK_RETREAT_CHOICE_FILE` (the B sidestep is −0.36 m, to the
    robot's right; superseded by the later 2026-09-28 stage-2 completion
    entry: the script now forces the *shown* letter B, whose candidate
    depends on the letter draw). (Superseded by the later 2026-09-28 T3b
    entry: deployed at `58bb428` and mock-smoked, `grounding mode=derived`
    at startup and `grounding_mode` in every artifact.)
  - **Deploy trap: a stale build silently stays legacy.** If
    `swarm_orchestrator` is colcon-stale while `config/` and `reasoning/`
    are synced, the old node never passes `params`, and grounding stays
    legacy whatever `rag.yaml` says. Check that the M5 startup log shows
    `grounding mode=derived`, and that every artifact has a
    `grounding_mode` key. An artifact without that key came from a stale
    build.

- **2026-09-27** — **T3a blocker-kind pair authored with its oracle, and
  mock-smoked on the VM: both members PASS** (`ad379f1`, `8ee6393`; scenario
  headers `isaac/config/scenarios/blocked_path_{object,transient}.yaml`;
  evidence `data/logs/vm_runs/t3a_smoke/T3A_SMOKE_SUMMARY.txt`). Design:
  "T3a" in `docs/superpowers/specs/2026-09-27-scenario-battery-design.md`.
  - **Oracle.** The new `BlockerOracleConfig` (`isaac/vgu_sim/config.py`)
    sits beside the yield `OracleConfig`. It records `correct_blocker_kind` /
    `correct_strategy` plus the Arm B answer (`classical_*`), mirroring
    `fcfs_yielder`. The strategy must be the kind's default from research
    design A.5 (object -> reroute, transient -> temporary_wait).
    - Object member: object/reroute, same as classical (the non-divergent
      control).
    - Transient member: transient/temporary_wait against classical
      object/reroute (the divergent member). The untracked robot-shaped
      blocker is `transient` because "robot" means a listed robot:
      amendments item 15b, confirmed 2026-09-27.
  - **Smoke, mock backend forcing the oracle answer once.**
    - W1 (object): the stall triggered on scene 21.8. The dispatched reroute
      re-sent the goal and FAILED, and robot_1 never resolved (expected,
      next bullet).
    - W2 (transient): the stall triggered on scene 24.1. temporary_wait held
      8 s, and robot_1 arrived 0.08 m from its goal 32 s after the 70 s
      despawn.
    - On each run's first analysis Arm B answered
      blocked_path/object/reroute (`blocker_kind_match` true on W1, false on
      W2). Later re-analyses were not all like that: 5 of 22 in W1 and 2 of
      7 in W2 got `none`, because robot_1 was moving in a Nav2 recovery at
      that moment. The T3a scorer must fix which analysis per episode
      counts.
    - Both runs: no blocker text in any prompt, no M1 detection of the
      unmarked robot, 0 safety stops.
    - These were the first live runs of the prompt-v2 bundle (mock backend):
      no errors.
  - **Outcome caveat: T3a can only be scored on the decision.** `reroute`
    re-sends the task goal, which M4's base mission already does every 2 s,
    and Nav2 replans at 1 Hz on the lidar-marked costmap. A robot that
    stalls at an object therefore has no route left. The object member
    cannot resolve under any strategy, and the transient member resolves at
    the despawn under any strategy. So the research design's "B executed on
    5 pairs for outcome contrast" cell has no outcome contrast in this map.
    Decide before the freeze whether that cell stays.
  - **Prompt noise:** at trigger time robot_1's heading is whatever Nav2's
    spin recovery left. In W1 the prompt said "robot_1 faces robot_2: yes"
    at 2.6 m.
  - **Pending:** (first funded probe, n = 1 per model per member: see the
    2026-09-28 funded-battery entry) a funded VLM run of the pair (N = 15 pairs + 10 Arm B
    executed).

- **2026-09-27** — **Amendments item 15a discharged in code: the v2 guidance
  line now admits rendered goals and tasks as evidence** (`b4a8d91`;
  `docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md` item 15). The
  v1 line "Decide from the robot coordinates and the image, not from
  assumptions about intent." contradicted v2's rendered `goal_x/goal_y/task`.
  v2 now reads "Decide from the robot states (including their stated goals
  and tasks) and the image; do not assume intentions beyond what is stated."
  v1 (`prompt_v1.py`) and its pins are untouched; replay integrity still
  reconstructs 74/74. The four v2 pins in `tests/unit/test_prompt_builder_v2.py`
  were re-pinned (+49 chars each). This is free only because v2 is unfrozen
  and no live data exists under it (calibration pilot, item 16, is
  funding-blocked); after the freeze it would be a new prompt version.

- **2026-09-27** — **The prompt-v2 bundle landed: the one planned
  prompt/contract break before the `prereg-v1` freeze** (`991ffae`,
  `3013e88`, `5af09e0`). Design: "The Prompt-v2 Bundle" in
  `docs/superpowers/specs/2026-09-27-scenario-battery-design.md`. It subsumes
  amendments blockers 10 and 13
  (`docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`).
  - **Contract.** `CongestionDecision` gains two optional fields.
    `blocker_kind` is `robot | object | transient`. `crossing_order` is a
    permutation of `involved_robots`: the first entry passes first, and a
    yielder passes after the robots it yields to. The model rejects a
    non-permutation.
    - The parser does not fail the decision on a bad value. An out-of-set
      `blocker_kind`, or an order that is not a permutation, parses to None.
      The tag goes to `ReasonerDiagnostics.decision_degradations`
      (`blocker_kind=default:invalid_label` → `invalid_label`,
      `crossing_order=default:non_permutation` → `non_permutation_order`).
      No re-ask is spent.
    - An absent field carries no tag. Whether None counts as `invalid_label`
      is the T3a/T2b scorer's call.
    - The tags are merged into the grounder's `DEGRADATION_TAGS`, so one
      `degradation_cause` covers the whole breakdown.
    - `vlm_decision.schema.json` now lists `yield_robot`, which was missing:
      with `additionalProperties: false`, `force_schema=True` could never
      have emitted it. It also lists the two new fields.
  - **Prompt v2.** The diff against v1 is three regions:
    - The header reads `Robot states:`. The "(sorted by ID)" claim was false
      under `id_desc`. Stating the drawn order instead would add a region
      that differs between the counterbalanced conditions.
    - There are two new output-format bullets.
    - Each robot's registry goal and mission task label render through the
      existing `goal_x=…, goal_y=…, task=…` path, which had never run live.
      M5 attaches them to the snapshot with `attach_registry_assignments`,
      so the stored `scene` alone reconstructs a v2 prompt. The goal is the
      effective goal, the same lookup the Arm B shadow uses. The task is
      `TaskRegistry.mission_task`, the base label: an override's task is the
      dispatched action (e.g. `yield`), which would prime the answer.
  - **Versioning guarantee.** `ReasonerRequest.prompt_version`
    (`Literal[1, 2]`, default 2) selects the template.
    - v1 is `reasoning/vlm/prompt_v1.py`, a self-contained copy of the
      4a71ffb builder. It imports and shares nothing from `prompt_builder`,
      so editing v2 cannot move a v1 byte.
    - `tests/unit/test_prompt_v1_frozen.py` pins nine v1 renderings. They
      were computed at HEAD before any edit, and include the goal/task,
      `id_desc`, crosscheck and double-failure paths.
    - Artifacts now record `prompt_version`. The replay reconstructor reads
      a missing key as v1.
    - `--arm integrity` gives batch1 74/74, batch2 56/56, all 130/130. A
      sweep of every local run directory that `load_artifacts` reads (54
      dirs) reconstructs all 654 artifacts: 0 mismatches, 309 of them
      without a local frame PNG.
    - v2 SHAs are pinned in `tests/unit/test_prompt_builder_v2.py`. A change
      there is a new version, not a re-pin.
  - **Arm B and the handoffs.** `resolve_classical` puts the
    classification's `blocker_kind` on its decision (`object` on
    `blocked_path`, `robot` on `head_on`/`intersection`, None on
    `unknown`/`none`). It also puts the FCFS order there as
    `crossing_order`, at 3+ robots only.
    - `DisagreementRecord` gains `blocker_kind_match` and `order_match`.
      Each is None, meaning not comparable, when either side lacks the
      value. False counts toward `any_disagreement`; None does not.
    - The shadow feeds the comparator the classification verdict and the
      full passing order, so a two-robot VLM order is comparable.
    - With no explicit `crossing_order`, the derived grounder reads
      `decision.crossing_order` minus the grounded (post-gate) yielder.
  - **Consequence.** Every post-bundle prompt differs from every pilot, so
    nothing that straddles the bundle may be pooled.
  - **Pending.** The calibration mini-pilot (n = 3 per model on `_bshort`
    west) is blocked on funding: gpt-4o credits are exhausted and Gemini hit
    its spending cap. It must run before the template hashes freeze at
    `prereg-v1`.

- **2026-09-27** — **M5's stall and cooldown clocks run on wall time, but
  scenario timing is in sim time.** `stall_threshold_sec` (12) and
  `cooldown_sec` (15) are measured on `time.monotonic()`
  (`orchestrator_node._on_scene_state`). At the VM's real-time factor of about
  0.38, that makes a stall trigger about 4.6 sim-s after the robot stops, and
  re-analyses about 6.4 sim-s apart. In the T3c v2 smoke `20260927_125419`,
  robot_1 stopped at about sim 31 and the first analysis fired on scene 35.2.
  A scenario author who reads the thresholds as sim-seconds overestimates
  every trigger delay by about 2.6x. The v2 YAML header was corrected
  (comments only).

- **2026-09-27** — **Probe freshness gate (Fix 1) verified live. The T3c v2
  smoke ran clean on apparatus, but got no M2 answer because Gemini hit its
  spending cap** (89884a3; `data/logs/vm_runs/t3c_v2/T3C_V2_SUMMARY.txt`).
  - **Fix 1 (089d56e), PASS.** normal_flow run `20260927_124234`:
    - Isaac exited at 12:50:36Z. The last probe, at 12:50:32Z, ran on the
      live scene 179.0.
    - One `t0 probe deferred reason=snapshot_stale` line followed at
      12:50:47Z.
    - No probe fired in the 167 s M5 stayed up after that. The previous run
      fired 37 probes on the frozen final scene.
  - **T3c v2 smoke** (`20260927_125419`, dynamic_anomaly_v2, see the M6
    entry):
    - The box appeared on schedule. robot_1 stalled and 15 stall analyses
      fired as one episode.
    - The box stayed image-only: no prompt text mentions it.
    - Both arrivals were verified by position: 0.07 m and 0.05 m.
    - Minimum pairwise distance was 0.70 m. There were 0 safety stops.
    - Arm B produced 15/15 clean blocks: `anomaly`/[robot_1],
      `temporary_wait` first and then `reroute`.
    - The era-aware rescore scored 2/2 within tolerance (sim era, 15
      anchors).
  - **Blocker:** every ER-2 call from 12:43Z onward returned HTTP 429 "exceeded
    its monthly spending cap" (42/42 in the two runs), so M2's T3c answer
    (type, strategy, justification) is still unobserved. OpenAI credits have
    also been exhausted since 2026-09-25. The oracle stays pending on two
    things: prompt-v2's `blocker_kind` field, and a funded re-run of the
    unchanged v2 smoke. (Superseded by the 2026-09-28 funded-battery
    entry: both models answered anomaly/reroute/`object` exactly once per
    episode, then `none` on re-analysis.)
  - **Procedure gap:** the pre-flight check only confirms the key is present.
    A one-call canary before each run would catch an exhausted cap.

- **2026-09-27** — **Arm B rule change (pre-freeze): robots parked at their
  goal are no longer `blocked_path` / `unknown` candidates** (5e13805). The
  T0 verification run `20260927_111348` found classical shadow verdicts of
  `blocked_path`/`anomaly`/`reroute` on 60/60 post-arrival probes
  (`data/logs/vm_runs/t0_t3c_verify/VERIFY_SUMMARY.txt`, F-T0-2): the
  classifier had no notion of "stopped because arrived". `classify_scene`
  (`reasoning/baselines/classical_reasoner.py`) now drops a stopped robot
  within the new `ClassicalParams.arrived_exclusion_radius_m` (0.35, equal
  to M5's `arrival_position_tolerance_m`; also in `config/rag.yaml`) of its
  own goal before the `blocked_path` and `unknown` rules; `none` when no
  candidate is left (root_cause "stopped robots are all parked at their
  goals"). `head_on` and `intersection` still see parked robots, and a
  parked robot still counts as another robot's blocker; goalless robots are
  unchanged. This is a RULE change, not T1 tuning; the normative Arm B
  section in the design spec does not mention it yet and needs an
  amendment. Replaying T1's 65 artifact scenes: old rule 60 `blocked_path` /
  5 `none` (the recorded tally, exactly), new rule 65 `none`.
- **2026-09-27** — **T0 probes are now gated on snapshot receipt age**
  (089d56e). In run `20260927_111348` Isaac exited at sim 180.37 and M5
  kept probing the frozen final scene (probes 28-64 were replicates, F-T0-1):
  the frame-vs-scene skew check compares two sim stamps that freeze
  together. `probe_block_reason` (`swarm_orchestrator/probe.py`) now takes
  the wall-clock age of the latest SceneState receipt and returns
  `snapshot_stale` past `t0_probe_max_snapshot_age_sec` (new, default 3.0 s,
  in `OrchestratorConfig` and `orchestrator.yaml`), checked after `no_scene`
  and before `frame_not_fresh`, logged once per deferral like the other
  reasons. A live feed (M1 publishes per camera frame) never gets near it.
  VM check pending: the next T0 run's probe count should stop at Isaac exit.
- **2026-09-27** — **T0 negative-control tier built (scenario + M5 log-only
  probe mode); VM/USD verification pending.** Implements the design spec's T0
  tier (`docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`,
  "Scenario battery" / run matrix: FP rate ≤ 10% on 20 probes).
  `isaac/config/scenarios/normal_flow.yaml` (33232b8): two robots pass in
  opposite directions on lanes y = ∓0.35 (spawns/goals at x = ±2.5) inside
  the 1.2 m cross aisle — the racks fill every quadrant, so the "open
  warehouse" lanes at y = ±0.8 the brief suggested are inside rack blocks.
  Nominal minimum pairwise distance 0.70 m at the pass (0.25 m over M4's
  0.45 m latch), not enforced by geometry: check `min_pairwise_distance_m` in
  the acceptance log on the VM. Schema: new `normal_flow` family;
  `expected_conflict` is now required-but-nullable and `null` is legal only
  for that family. Its Nav2 map equals the default map byte for byte. Before
  a T0 run, set `initial_tasks` to the lane goals (table in
  `orchestrator.yaml`) or the robots get the ±2.5 centreline goals and meet
  head-on. Probe mode (50bab61, M5 spec FR5.3.12): off by default; probes run
  M2 only on their own executor, are recorded with `probe: true`, and are
  refused at `_dispatch` by a request-id ledger if one ever got there.
  Pending: scenario USD build + a T0 probe episode on the VM; and
  `scripts/rescore_arrivals.py` does not skip `reason=t0_probe` lines, so do
  not rescore T0 runs with it.
- **2026-09-27** — **Pillar 2 stage-2 retreat machinery landed offline (Phase 1
  plan Tasks 3, 8, 9, 11, adapted to the current tree).** It is on branch
  `feat/pillar2-retreat`, unmerged. This is the prerequisite slice for T3b
  (`docs/superpowers/specs/2026-09-27-scenario-battery-design.md` §T3b).
  - Commits: `9d027e6` (Task 3), `09b74db` (Task 8), `6094794` (Task 9),
    `cf81fa9` (Task 11). Tests are in `tests/unit/test_retreat_choice_parser.py`,
    `test_maneuver_geometry.py`, `test_retreat_candidates.py` and
    `test_command_grounder_derived.py`.
  - **Deliberately not included.** There is no M5 wiring: no stage-2 call, no
    marker rendering and no artifact fields. There is also no config flip:
    `config/rag.yaml` `grounding: mode: legacy`. Both follow the prompt-v2
    bundle.
  - **Legacy guarantee.** `ground_reasoner_result` gains keyword-only
    `snapshot`, `params`, `retreat_choice` and `crossing_order`. The legacy
    body moved verbatim into `_ground_legacy`.
    - A SHA-256 over 576 legacy outputs is pinned at `d255a09`. The inputs
      cover every strategy × yielder × position set × geometry × gate mode.
    - The same digest is asserted with `params=GroundingParams()` plus a
      snapshot, a retreat choice and a crossing order, which is what the M5
      flip will pass.
    - `tests/unit/test_command_grounder.py` is unmodified.
  - **Composition with the M3 yield gate.** `resolve_yield_roles` runs these
    steps in order:
    1. `yield_robot`;
    2. the gate (`swap`/`refuse`) on the snapshot positions;
    3. the corridor same-side refusal;
    4. the crossing order.

    Only after that does `prepare_retreat_selection` build the candidates, for
    the grounded yielder. A gate refusal keeps the legacy wait fan-out
    byte-for-byte, with a tag added.
  - **scene_geometry reuse.** When a `SceneGeometry` is declared, the derived
    mode takes the following from `scene_geometry`:
    - the park point, which floors the backup;
    - `pull_off_lateral_m`, `passer_clearance_m` and the safety radius;
    - the corridor-axis retreat side the gate uses.

    At the deadlock pose it reproduces the legacy 1.489 / 0.36 / 2.739. The
    `GroundingParams` constants apply only without a geometry. The family
    oracle and `scene_geometry.py` are untouched.
  - **Deviations from the plan sketch.**
    - The backup minimum is exact, not a 0.01 m scan: float drift in the scan
      gave 1.31 for 1.3.
    - The Task 9 sidestep test's robot sat on the shared backup path, which
      vetoed all four candidates. The robot was moved, and the veto is now
      its own test.
    - Task 10 (blocker-kind compatibility) is skipped because
      `CongestionDecision` has no `blocker_kind`. The order comes from the
      `crossing_order` keyword until that field exists.
    - `RetreatLabelError` separates `invalid_label` from `parse_failure`.
    - `retreat=default` splits into `:no_choice` and `:invalid_label`.
    - A missing snapshot tags only spatial strategies.
    - A partial snapshot counts as `distances=unavailable`.
    - An infeasible yield reroutes the *yielder*.
    - Every tag maps to a measurement-plan cause via `degradation_cause`.
  - **Flagged for T3b and Phase 2.**
    - The head-on corridor geometry offers k = 2 candidates, not k = 3. The
      far variants at 0.72 m fail the 0.36 m band, so T3b needs a wider
      explicit `aisle_y_band_m`.
    - Stage 2 and grounding must use the same snapshot: letters are
      positional, and `RetreatChoiceDecision` is not bound to a yielder.
    - The sweep ignores declared static obstacles.
    - A derived `reverse` still uses the blind 1.3 m constant.
    - `linked_position` for three or more robots needs M4's Pillar 3 release
      chain.
    - `ranked[0]` equals Arm B's stage-2 answer only when both arms ground the
      same yielder. `reasoning/baselines/` is unchanged.

- **2026-09-27** — **Rescore sim-time regression fixed; censored FCFS
  arrivals flagged** (follow-ups to the S1/S2 validation entry below,
  `data/logs/vm_runs/simtime_shadow_val/VALIDATION_SUMMARY.txt` F3/F4).
  - `scripts/rescore_arrivals.py` (`64bb0bd`) detects the clock era per run.
    Wall era: the scene-log stamp span overlaps the M5 log's wall span ±60 s,
    and stamps are used unchanged. Sim era otherwise: stamp → `t + offset`,
    where `offset` (wall − monotonic) is derived per run as the median of
    one anchor per analysis: the `starting analysis request=` wall time
    minus the scene log's interpolated `t` at that artifact's scene stamp.
    It is recorded in the new `clock_*` CSV columns. Derived 1790272483.650 /
    .652 on S1/S2, vs 1790272483.644 measured on the VM. Sim era without
    anchors, anchors disagreeing (MAD > 1 s), or an event >60 s outside the
    mapped scene span raises `ClockReconciliationError`: the re-score aborts
    with exit 2 and no CSV.
  - Re-runs: `simtime_shadow_val` 4/4 `within_tolerance`, matching
    `ARRIVALS_RESCORED_SIMTIME_WALLMAPPED.csv` on every column except
    `m1_estimate_age_sec`. That column differs because a lagging robot stamp
    is now interpolated on the sim→wall map instead of the shim's sim-second
    age subtracted from wall time. `bshort_gpt4o` and `bshort2` are
    identical on all 34 prior columns; all 55 rows of the top-level
    `ARRIVALS_RESCORED.csv` are identical.
  - Gotcha: era detection uses span *overlap*, not the median.
    `bshort_gpt4o/20260926_204952`'s captured M5 log ends ~430 s before its
    scene log does.
  - Ground truth is still joined by nearest position, so the −0.45 s
    M1→GT stamp lag (F1) is not applied. It is documented in the script
    docstring for any future time join.
  - Shadow record (`1a38379`): new `censored_arrivals` field lists involved
    robots whose FCFS arrival stamp equals the oldest buffered frame's
    stamp, i.e. already in-zone at the window start (S2 robot_1). It uses
    the same zone and `derive_motion_table` rule as FCFS. `None` means no
    FCFS order was computed. The flag only marks the answer; the decision
    and tiebreak are unchanged, and the boundary-spawn radius question stays
    a pre-registration decision.

- **2026-09-27** — **Shadow logging + sim-time stamps live-verified (S1/S2,
  merge `97634be` deployed to the VM as the new apparatus).** Two ER-2 west
  `_bshort` episodes, 12/13 checklist items clean: M1 transit speed 0.14
  vs ground-truth 0.15 sim-m/s (was ≈0.06), STALE onset 0.9–1.3 s
  confirming the 1.15 retune, trigger timing unchanged, M4 speed rule 0
  fires, shadow blocks clean on 13/13 analyses, classical-vs-ER-2
  disagreement 12/13, both runs 2/2 position-verified. FAIL: S2 FCFS
  arrival censored (spawn sits exactly on the 1.5 m zone boundary) —
  `censored_arrivals` flag + radius question tracked. Regression found:
  `rescore_arrivals.py` silently mis-scores sim-time runs (fix in a
  follow-up entry). Constant −0.45 s M1→ground-truth stamp offset; parked
  STOPPED/SLOW flicker ≈4×. Findings Rev 14 §AQ; amendments blockers 11
  and 12 discharged; artifacts `data/logs/vm_runs/simtime_shadow_val/`.

- **2026-09-27** — **Arm B shadow logging wired into M5** (`6d70238`). This
  meets the spec's shadow-logging requirement: in Arm A, the classical
  answer is also computed and logged for every decision. See "Experimental
  arms, pairing, and shadow logging" in
  `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`.
  This is the code-level wiring for amendments blocker 12
  (`docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`). The blocker
  is not discharged until the combined VM run validates it. The pure logic
  is in `swarm_orchestrator/shadow_classical.py`, and the node only feeds it
  and reads from it.
  - **Evidence asymmetry.** The shadow frames carry goals from the registry.
    The VLM request carries none: `build_reasoner_request` reads `goal` off
    `RobotView`, which has no such field. This affects the claim that both
    arms see "the same inputs". Recorded, not changed. *(Superseded by the
    2026-09-27 prompt-v2 bundle entry: v2 requests carry registry goals.)*
  - **Isolation.** The shadow is observational. It never dispatches, and it
    never touches the `ReasonerRequest` or the VLM decision.
    - The node calls `evaluate` after the worker submit, so the shadow cannot
      delay the VLM call. It calls `finalize` before the artifact write.
    - Failures are recorded as `shadow_error` and never raised. A test pins
      that every other artifact key is identical with and without a failing
      shadow.
  - **Buffer.** The buffer keeps 60 s of history on M1 stamps, at most one
    frame per 0.25 s.
    - The trigger snapshot is always the newest frame classified, even when
      decimation skipped it.
    - Dropped frames and robot-less frames are skipped.
    - A stamp that goes backwards clears the buffer.
    - Robot goals come from the M5 task registry.
    - M1 velocities pass through unscaled, per blocker 11; see the comment in
      `snapshot_to_frame`.
  - **Config.** The new keys in `orchestrator.yaml` are:
    - `shadow_classical: true`, the default.
    - `shadow_classical_params_path: "config/rag.yaml"`.
    - `shadow_classical_window_sec`. The loader rejects it unless it exceeds
      `stall_threshold_sec`.
    - `shadow_classical_sample_period_sec`. Startup rejects it unless it is
      below `arrival_tie_sec`.
    - `shadow_classical_zones: []`.

    If the `classical:` params are invalid, M5 stops at startup. If the file
    or the section is missing, every analysis records a `shadow_error`
    instead of silently running on defaults.
  - **Artifact.** Each decision artifact gets a top-level `shadow_classical`
    block, which is null when the shadow is disabled. It holds:
    - the classical decision, classification and `passing_order`;
    - a `comparison` with `comparable` and the `DisagreementRecord`. When the
      VLM gives `decision=None`, `comparable` is false and a reason is given.
    - the full params dump;
    - `prior_attempts`, counted per episode by the episode tracker, not by
      `AttemptMemory`, which is off in the RQ5 control;
    - the buffer extent (`frame_count`, `oldest_stamp`), so censored arrivals
      can be detected offline.

    The node logs one `shadow request=… scenario=… strategy=… yield=…
    disagree=…` line per analysis. It has not been VM-validated yet; that is
    planned as a combined run with the M1 sim-time work.

- **2026-09-27** — **Failure-context depth policy adopted: the prompt carries
  the most recent attempt plus the most recent failed attempt** (`7f9884d`).
  Two blocks when they differ, one when the latest attempt is itself the
  failure or nothing has failed.
  - **Defect.** The context was one attempt deep. A completed maneuver
    displaced a failed yield, and M2 then re-selected the same infeasible
    yielder. Seen at `7482f0ad` in `20260924_201328` (findings Rev 1
    §Secondary Findings (a)). L4 repeated it (`20260925_011246`, request
    `ca63fbd5`, Rev 2 §B run-level detail, §D item 3). D2 does not show the
    displacement: it failed `yield` then `reverse`, and every later prompt
    carried that failed `reverse`. It is cited only as the Rev 4 §K/§N pairing
    with L4.
  - **Contract.** `ReasonerRequest.failure_context` is unchanged. The new
    field is `last_failed_context: FailureContext | None = None`. Setting it
    without `failure_context` is rejected.
  - **Prompt.** The second block is labelled `Earlier failed attempt in this
    episode:`. It comes after the `Previous attempt` block and has its own
    generic advice line.
  - **Byte stability.** With the field left as None, the prompt renders
    byte-identically. This is pinned by `_SINGLE_FAILURE_CONTEXT_PROMPT_SHA256`
    in `tests/unit/test_prompt_builder.py` and by the replay `FC_USER_SHA256`
    test.
  - **M5.** The logic is `AttemptMemory.contexts_for` plus
    `build_failure_contexts`.
    - "Failed" means any resolved non-completed outcome, `timed_out`
      included, because `summarize_outcome` ranks `timed_out` above `failed`.
    - The failed slot lives exactly as long as the latest record and has no
      window of its own. In L4 the failed yield was 56.1 s old at the
      re-analysis, against a 60 s window.
    - The episode boundary is unchanged.
  - **Artifacts.** Decision artifacts gain a top-level `last_failed_context`,
    and `scripts/replay_live_decisions.py` reconstructs it.
  - **Node log.** When the second block is attached, the node logs a separate
    `last_failed_context attached` line.

- **2026-09-27** — **`reasoner_config_effective` now records
  `image_fallback_after_attempts`** (`5386bd3`). It records the resolved
  `ReasonerConfig` value verbatim, the same convention as `max_attempts`:
  shipped openai 2, gemini/llama_server/mock None. The field defaults to None,
  so blocks written earlier still parse. For those earlier runs, None cannot be
  told apart from "mitigation off" by this field alone; use the run date
  against 2026-09-26. This closes the gap noted in the gpt-4o `_bshort` entry
  below (findings Rev 13 §AO).

- **2026-09-27** — **gpt-4o `_bshort` pilot 6/6 on the adopted apparatus;
  baseline complete on both models.** Six runs (N1–N6) on tree `7103f9d`
  with the M4 exemption fix deployed (now permanent on the VM): all
  position-verified, opening `yield` 6/6, gate `swap` fired 4/6 (every
  infeasible naming re-grounded), refusals 4/28 attempt-1 / 0 terminal,
  fallback never reached (0/28), backtrack ≤ 0.004 m, `box_overlap` 0/12.
  `_bshort` now stands at 15/15 across gpt-4o and ER-2. New items: a
  phantom `robot_17` from an M1 marker-ID misread latched N5's robot_1 for
  6.4 s pre-episode (M1 robustness item), and
  `reasoner_config_effective` lacks `image_fallback_after_attempts`.
  Findings Rev 13 §AO; artifacts `data/logs/vm_runs/bshort_gpt4o/`
  (git-ignored).

- **2026-09-27** — **Frame replay Rev 5: the three credit-blocked arms ran in
  full** (`docs/reports/2026-09-25-frame-replay.md` Rev 5; rows in
  `data/experiments/2026-09-26-batch2-replay/`; $5.45, cumulative $13.32).
  - **Arm X (image fallback).** Terminal refusal fell from 10/84 to 0/84
    (p = 1.5e-3), and 93 of 94 fallback decisions (X and F together) match
    the scene's modal frame-attached (strategy, yielder) decision. Only 1 of
    those 94 is a yield, so the yielder choice is untested.
    - Recommendation: **keep** `image_fallback_after_attempts: 2`.
    - The separate-reporting rule for `image_fallback_used` rows **stands**
      (A6). The Arm-S grey cells are the same stimulus as the fallback
      attempt, and they move the yielder on standoffs.
    - The grey fallback is not refusal-proof: 2 of 96 fallback attempts
      refused, both on `bb7a2fec` raw.
  - **Arm F (annotated vs raw).** The overlay is **not** the trigger. Gated to
    |skew| <= 0.2 s, raw refuses 30/72 against 20/72 annotated (p = 0.11).
    Refusals lock to the exact frame M5 sent: live-valid scenes refuse 2/45
    annotated against 15/45 raw. Dropping the overlay is not a mitigation.
  - **S2 remainder.** The 101 rows ran under the rewritten reasoner and are
    kept as a separate east-only stratum, never pooled with Rev 4's 187. It
    adds 1 positive and 1 reversing scene (the reversal rests on 1 yield) to
    Rev 4's 7 of 9.
  - **Resume gotcha.** §AB's resume command omits `--out-dir`, but batch-2
    arms must pass `--out-dir data/experiments/2026-09-26-batch2-replay`.
  - **Pooling gotcha.** The script's `analyze` pools every `S2` row. Split the
    rows on the presence of `image_fallback_after_attempts` first.
  - This discharges the replay parts of prereg items 4–5
    (`docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`). The
    forced-order live cells and the gpt-4o `_bshort` pilot are still open.

- **2026-09-26** — **Arm B classical reasoner landed offline (Phase 1 plan
  Tasks 4, 12–14, adapted to the current tree).** It is on branch
  `feat/arm-b-classical` and is not yet wired into M5.
  - The code is in `reasoning/baselines/` and `reasoning/vlm/motion_table.py`,
    and the `classical:` section of `config/rag.yaml` holds the rev-8
    defaults.
  - Contract gap: `CongestionDecision` has no `blocker_kind` or
    `crossing_order`.
    - `decide_classical` emits only the shared contract.
    - `resolve_classical` also returns the classifier's `blocker_kind` and
      the full FCFS `passing_order`.
    - `compare_decisions` compares only `strategy`, `type` and `yield_robot`.
    - Blocker and order shadow comparison (T3a, RQ3 for 3+ robots) needs
      those fields added to the contract first.
  - Deviations from the plan sketch:
    - `head_on` means exactly two stopped robots within `r_conflict` *of
      each other*, so a distant stopped bystander no longer vetoes it.
    - FCFS is measured at the zone that produced the verdict: the pair
      midpoint for `head_on`, the matched mapped zone for `intersection`.
    - `MotionTableEntry` is trimmed to the arrival fields.
    - `prior_yields` is dropped from `derive_motion_table` and
      `decide_classical`.
    - Task 1's `SnapshotFrame` and `BlockerKind` were added additively.
  - Per-task commits: `f345c7a` (Task 4), `6c27f04` (Task 12), `de994c6`
    (Task 13) and `20669c3` (Task 14). Tests are in
    `tests/unit/test_classical_reasoner.py`, `test_shadow_comparison.py`,
    `test_motion_table.py` and `test_vlm_models.py`.
- **2026-09-26** — **K1/G4 "interpenetration" is driven nose-to-nose
  contact caused by a `reroute` landing on the post-`reverse` re-approach.**
  - M5's stall memory survives a command (`congestion_detector.py:99-108`),
    so the analysis after a `reverse` fires mid-approach.
  - ER-2 answered `reroute` in 2 of the 27 archived reverse-opened runs
    (G4, K1), and those are the only 2 contact runs. The other 25 yielded
    with 0 contacts, and the 6 `reroute`s dispatched after a yield had
    0 contacts.
  - No reverse opening in the 12 gpt-4o runs.
  - Corrections: M1 *did* go STALE in both runs, contrary to Rev 7 §AC.
    `robot_robot_contacts` is hard-coded `[]`, not a silent detector. Use the
    collider signed gap, not centre distance alone, for contact.

  M4 root cause and mitigations: M4 entry of the same date and
  `docs/reports/2026-09-26-close-approach-analysis.md`. Overnight findings
  need a Rev 11 correction of §AC/§AI.
- **2026-09-26** — **`_bshort` validated on both sides at the ±2.6 passer
  goal; adopted as the pre-registration T2a scenario.** Six ER-2 runs on
  tree `cf4899f` (east K1–K3 first-ever, west K4–K6 re-run after the
  `dcfa144` widening): 6/6 position-verified, correct yielder executed 6/6
  (gate `swap` fired 2/6), 0 refusals on 39 calls, 0 Nav2 recoveries, passer
  backtrack 0.000–0.003 m. Discharges prereg amendment A1's condition and
  the Rev 6 §W item 6 scenario question. Two caveats recorded: realised
  escort margin is 0.063–0.096 m (Nav2 stops the passer short of the
  nominal 2.6), and K1 is a second G4-class 0.076 m interpenetration during
  ER-2's opening non-yield phase with all safety layers silent
  (pre-Arm-B blocker, amendment A5). Findings Rev 10 §AI; artifacts
  `data/logs/vm_runs/bshort2/` (git-ignored). *K1 "interpenetration … all
  safety layers silent" clause superseded by the 2026-09-26 close-approach
  entry above.*
- **2026-09-26** — **Pre-registration amendment set drafted from the pilot
  campaign**: `docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`
  binds the 2026-09-24/26 adjudications (`_bshort` T2a instrument, random
  presentation order with order-conditioned analysis, gate `swap` scored
  pre-gate, position-verified episode outcome primary, distance-channel
  safety columns, `max_attempts: 4` + ER-2 as secondary backend replacing
  `llama_server`) for absorption into the research design spec as rev 9 at
  the `prereg-v1` tag. Its freeze-blocker list records that
  `reasoning/baselines/classical_reasoner.py` (Arm B) is specified but not
  implemented — the largest open work item — plus the `_bshort` east
  validation, the failure-context depth decision, and the credit-blocked
  gpt-4o arms. Draft only; nothing frozen until the tag.
- **2026-09-26** — **`scripts/rescore_arrivals.py` flags accepted arrivals
  whose pose reaches into a static obstacle box** (`8e77bc4`). For each
  `within_tolerance` accept it reads `static_obstacles` from the run's
  scenario YAML (`--scenarios-dir`, default `isaac/config/scenarios`) and
  sets `box_overlap` / `box_overlap_obstacle` when the M1 position lies in a
  box grown by `ROBOT_HALF_WIDTH_M` = 0.175 m, with a stderr warning.
  Reporting only; verdicts unchanged. Motivation: the `_bshort` blocked-side
  goal sits 0.20 m from the box near face, so the 0.35 m tolerance band
  reaches inside the box. 0.175 m is conservative against the 0.14 × 0.18 m
  Nav2 footprint: on `_bshort` any accept ≥ 0.025 m past the goal toward the
  box flags. Local re-run over 41 runs: 0 flags (no `_bshort` runs synced).
- **2026-09-25** — **Every pre-`4f39899` run re-scored against M1's position
  check; exactly one arrival flips.** `scripts/rescore_arrivals.py` re-runs
  `arrival.py::classify_arrival` offline over all 31 `data/logs/vm_runs/`
  runs (55 reported arrivals) plus a ground-truth cross-check. Only
  `20260925_124609` (ER-2 pilot `E1` `robot_2`, the known Nav2 false success)
  rejects; M1-vs-GT bias is ~6 mm everywhere including that case. ER-2 pilot
  both-arrived count corrects 3/6 → 2/6; the other seven batches are
  unchanged. Detail: `docs/reports/2026-09-25-arrival-rescoring.md`.
- **2026-09-25** — **M3 can now refuse or re-ground a yield the scene makes
  impossible** (`8362178`, feature branch `feat/m3-yield-feasibility`, not
  merged). The feasibility rule the family oracle already encoded moved into
  `reasoning/rag/scene_geometry.py` (`required_room_m`, `yield_retreat_room_m`,
  `yield_feasible`), so `isaac/vgu_sim/family_oracle.py` and the executed
  maneuver now score off one function; a test regenerates the three committed
  family `oracle:` blocks unchanged (`06feaf8`). `ground_reasoner_result` gains
  `static_obstacles` + `yield_feasibility_mode` (`off`/`swap`/`refuse`; M5 key
  `grounding_yield_feasibility`), `swap` recording `yield_robot_grounded_from`
  on the yield action. **Ships off, and is a no-op while `static_obstacles`
  stays commented out in `orchestrator.yaml`** — turning it on is an
  experimental condition, since it changes which robot executes.
- **2026-09-25** — **The yielder the VLM names follows presentation order, not
  geometry; the 2026-09-19 confound is resolved.** A counterbalanced offline
  probe (`scripts/probe_presentation_order.py`, 360 calls, 0 parse failures, 0
  API errors) ran the three head-on asymmetric family scenarios x
  `id_asc`/`id_desc` x static-obstacle channel on/off, at temperature 0.0 (n=5)
  and 0.6 (n=10), through the production `Reasoner`/`openai` path. Reversing the
  presentation order collapses `P(yield_robot == robot_1)` from 20/20 to 5/20 for
  gpt-4o (Fisher p = 7.7e-07) and from 20/20 to 0/20 for gpt-4o-mini
  (p = 1.5e-11). `P(yield_robot == correct_yielder)` stays at chance
  (0.40–0.59) in every condition, with or without the obstacle channel, and no
  justification string ever cited the obstacle. **gpt-4o-mini matches `H_slot`
  outright; gpt-4o is slot-dominant with a residual `robot_1` pull** (under
  `id_desc` it does not commit, 0.75 at T=0.0 and 0.53 at T=0.6, so its signature
  verdict is "mixed" rather than clean `H_slot`). The bias is not
  instruction-compliance: the "first listed robot backs up" clause was removed
  before this probe and a guard test asserts its absence. **Consequence: every
  decision artifact collected before `922dd36` was rendered at `id_asc` and
  carries this bias, so the obstacle-channel A/B cannot be reported as a modality
  result until the order confound is removed from the historical artifacts too.**
  Probe is offline with a synthetic plan-view image — a deviation from the live
  pipeline that a counterbalanced live run must confirm. Modality added in
  `922dd36` (`ReasonerRequest.robot_presentation_order`, M5
  `prompt_robot_order`, shipped `id_asc`); probe and raw data in `dadb3f5`
  (`data/experiments/2026-09-25-presentation-order/`). Full detail:
  `docs/reports/2026-09-25-presentation-order-probe.md`.
- **2026-09-19** — **Paired A/B run on the head-on-asymmetric blocked
  variant is a null result, confounded by presentation order.** Two recorded
  gpt-4o runs on `head_on_asymmetric_w0p2_eopen_o0` (Run A modality off
  `20260919_042935`, Run B modality on `20260919_044729`) both chose
  `yield`/`yield_robot=robot_1` — the side the parked blocker makes
  infeasible — both `FAILED` at a ~0.093 m standoff (the robot's own
  half-width against the box), both followed with `reverse` (dispatched
  symmetrically, so it cannot resolve a two-robot head-on), and neither
  produced an arrival. **Supplying the obstacle's id/centre/extent produced
  no measurable change in the decision under test — but this is a single
  paired run, not a distribution, and `robot_1` is also the first robot the
  prompt presents (states rendered "sorted by ID"), so the model's choice
  and presentation order are perfectly confounded in both runs; the result
  bounds nothing about the modality in general and does not by itself
  distinguish a positional default from a spatial judgement.** Breaking the
  confound needs a counterbalanced `involved_robots`-order condition —
  applies to every artifact collected to date, not just these two runs.
  Full detail: `docs/reports/2026-09-18-head-on-family-validity.md`, "RQ5
  recovery runs (gpt-4o), modality A/B" (`6d9f540`).
- **2026-09-19** — **VM harness traps found running the head-on-asymmetric
  family (Tasks 7–8), all three would recur.** (1) `rsync --delete` without
  a curated exclude list will delete VM-only build outputs and secrets
  (`.env`, generated Isaac assets); even a previously-curated exclude list
  can miss stray VM-only files, so prefer an explicit synced-file list over
  `--delete` for small changesets, or dry-run and read the deletion list
  line by line. (2) `rsync -a` preserves source mtimes, so a source file
  older than the VM's last build output is silently *not* recopied by
  `colcon build`/setuptools `build_py` even though the build reports
  success — after any `rsync -a`, touch every source file and wipe
  `ros2_ws/{build,install,log}` before rebuilding, or the run executes
  another branch's installed code (this produced a `GeminiBackendConfig`
  `ImportError` from a stale install). (3) `grep -c <symbol>` on an
  installed file is not a sync check — a different branch's independent
  implementation of the same field name gives a false positive; use
  `md5sum`/`sha256sum` against the worktree source instead. Detail:
  `docs/reports/2026-09-18-head-on-family-validity.md`, "Harness Findings".
- **2026-09-19** — `build_backend`'s mock branch (`reasoning/vlm/backend_factory.py`)
  now accepts a JSON array in `VGU_MOCK_DECISION_FILE`, scripted into
  `MockBackend(response_sequence=...)`, which holds its last entry once
  exhausted; a single-object file keeps the unchanged `response_text=...`
  behaviour. Added `config/mock_decisions/head_on_yield_once.json` and
  `head_on_yield_robot_2_once.json` (existing yield decision, then a
  `congestion_detected: false` decision) so key-less runs can represent a
  scene that clears instead of replaying the same decision forever. This
  was root-caused from the T1 control run in
  `docs/reports/2026-09-18-head-on-family-validity.md` Rev 2: the frozen
  single-decision mock, not an M4 defect, caused `robot_1` to be
  re-commanded (and re-cancelled) on all 16 stall-triggered M2 analyses.
  `head_on_yield.json` / `head_on_yield_robot_2.json` are left frozen —
  a later task needs that form for an arm where the forced maneuver is
  expected to fail. Supersedes the 2026-09-16 entry below only insofar as
  the hook now supports a scripted sequence, not just a single decision.
- **2026-09-17** — Phase 2 slice landed ahead of Phase 1: failure-context
  feedback (rev-8 A.1) is wired end-to-end — `AttemptMemory` in M5, `FailureContext`
  + prompt block in M2, context recorded in decision artifacts. Episode rule =
  time window after resolution, any outcome (rev 8.2). Design:
  `docs/superpowers/specs/2026-09-17-failure-context-closed-loop-design.md`;
  plan: `docs/superpowers/plans/2026-09-17-failure-context-closed-loop.md`.
  Host verification pending (see M2/M5 section).
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

- **2026-10-01** — **robot_1/`x=-1.75` STALE dropout, scope narrowed
  further but NOT fully closed: the goal arrival and the single-yield
  park dwell are clean at the specific poses tested; the not-yet-built v2
  composite command's own geometry is unverified, and the recommendation
  is to instrument rather than assume safe** (`docs/reports/2026-10-01-
  robot1-stale-rootcause.md` rev 3, branch `feat/v2-stale-rootcause`,
  commits `5c7b833`, `4edd4c8`, `173d036`, `dedb71b`, plus the commit
  landing this note). **Supersedes the entry below's scope
  claim** ("confined to robot_1's pre-departure spawn dwell" was correct
  but incomplete — it had not checked the dwell robot_1 gets if chosen as
  the single-yield junction yielder, which lasts the whole maneuver, not a
  transient window) **and its footprint-vs-position framing** (the
  marker's rendered pixel footprint is uniform across the frame — nadir
  camera, pure scale-plus-offset homography, no perspective term — so the
  marginality is inferred to be a sub-pixel-*phase* effect, not a
  `|x|`-radial band; inferred from the asset's own pixel geometry and
  OpenCV's documented defaults, not confirmed against captured frames, no
  debug frames having been kept on these runs). Computed the real
  yield-park pose directly from the project's own pinned grounding code
  (`reasoning/rag/maneuver_geometry.py:derive_backup_distance`, run against
  `tests/unit/test_intersection_bottleneck_scenario.py`'s existing IB10
  ground-truth standoff frame) rather than assumed from the scenario
  header's north-south-only "1.7 m clearance binds" note: robot_1 as the
  east-west yielder parks at `(-1.37, 0.359)`, not near `-1.75`. A fourth
  VM run held robot_1 there directly: 100% fresh, 97.87% exact-stamp-match,
  0 `STALE` — clean at that pose. That single-yield path is the only
  grounding code that exists today, though: the v2 composite
  `junction_clear` command the prereg-v2 spec actually wants step 6 to
  smoke-test is not implemented anywhere in this codebase yet, so its own
  recede-phase geometry for the E-W pair remains unknown. Also corrected a
  second over-claim: yaw was never actually varied for marker 1 at the
  failing position (only `yaw=0` has been tested there) — doesn't change
  the IB10 conclusion, since `yaw=0` is the only arrival/park orientation
  robot_1 is ever structurally given (`TaskAssignment.goal` is a bare
  `tuple[float, float]`, no yaw field — `swarm_orchestrator/models.py:47`),
  but the original claim of having "ruled out" yaw was not warranted.
  Traced `position-verified` to its actual implementation — first cited
  `congestion_detector.py` (wrong: that is M5's live stall trigger, not the
  arrival scorer), corrected to `swarm_orchestrator/arrival.py::
  classify_arrival`/`ArrivalGate`, the gate every current/future run
  (including IB10 step 6) is actually scored by (shipped active,
  `orchestrator.yaml`: `arrival_position_check: true`) — and found it is
  explicitly **stale-tolerant by design**: a stale or missing M1 estimate
  is accepted, not rejected (`reason="stale_estimate"`, `accepted=True`,
  `on_nav2_success` calls `mark_arrived` on it regardless, "an M1 outage
  must not block every arrival in a run, it only means the arrival is
  unverified"); only a *fresh* out-of-tolerance reading rejects an arrival.
  A separate, stricter offline rescorer (`scripts/rescore_arrivals.py`,
  ground truth used only as its independent cross-check column) credits
  only `within_tolerance`, passing over `stale_estimate` as "not evidence
  either way" — but it only re-scores runs that predate the online gate
  (its own docstring: before commit `4f39899`), so it is not the mechanism
  any future IB10 run is scored by. The one place a `STALE` read can still
  cost a credit in *that* legacy tool specifically is its "latched at goal"
  fallback (a robot never explicitly accepted, scored off its final
  sample). No fix applied, same reasoning as below
  plus one more ruled-out option: swapping which robot starts on which
  side of the E-W arm does not dodge this for free, since robot_1 (the
  marker that actually fails) would then arrive at the original failing
  pose anyway (yaw always 0). Recommendation revised to make "instrument
  every stationary dwell for a long STALE streak, on any robot" the
  default, over "accept as-is", given the composite command's geometry is
  simply not yet known.
- **2026-10-01** — **robot_1/`x=-1.75` STALE dropout root-caused: marker_1 x
  position interaction at a marginal pixel footprint, not occlusion/
  lighting/homography; no fix applied (scenario-geometry and M1-code fix
  candidates both out of this task's scope)** — **scope claim and the
  footprint-vs-position framing both superseded by the entry above;
  mechanism's existence and the non-fix reasoning otherwise stand.**
  (`docs/reports/2026-10-01-robot1-stale-rootcause.md`, branch
  `feat/v2-stale-rootcause`, commits `3f24ac9`, `f155d7a`). Three mock-
  backend VM runs (swap, nudge, goalpose) resolve the entry below: static
  occlusion/lighting/homography asymmetry and the overlapping-marker
  mechanism are all ruled out by scene inspection + GT (racks and camera
  are programmatically symmetric, markers are fully emissive so lighting
  can't shade them unevenly, GT `min_pairwise_distance_m` stayed
  `2.04`-`2.47` m). A swap of which position robot_1/robot_2 spawn at shows
  the catastrophic failure follows neither the marker alone nor the
  position alone: marker_1 is clean at `(+1.75, 0)` (93-100%
  exact-stamp-match) and marker_2 at `(-1.75, 0)` is only mildly degraded
  (70-74% exact-stamp-match, 5-7 row streaks) — the combination is
  required. Measured mechanism: the marker's rendered footprint is `~3.67`
  px/ArUco-cell at this homography scale, below OpenCV's default
  `perspectiveRemovePixelPerCell=4` — a generic marginal-decode condition
  at `|x| ~= 1.75-1.85` that costs any marker a few percent of exact-frame
  detections, with marker_1's specific bit pattern tipping that into 74-82%
  chronic `STALE` specifically near `x = -1.75`. A 0.10 m spawn nudge
  (`-1.75` -> `-1.65`) fully clears it (100%/100%, 0 `STALE`) but is **not**
  applied: it breaks the pinned `test_approach_radii_are_equal` (radii
  `{1.75}`, `tests/unit/test_intersection_bottleneck_scenario.py:183-185`)
  and the equal-approach-radii design invariant that IB10's derived park-
  offset/backup-clearance geometry is built on — a scenario-redesign
  decision for whoever re-authors the already-flagged "NOT tag-ready" IB10,
  not a unilateral edit here. A fourth run (goalpose: all four robots at
  their actual IB10 goal poses, real Nav2 arrival yaw 0) found the
  practical IB10 risk narrower than first feared: robot_1's own goal
  arrival is clean (100%/100%), and only robot_2's goal arrival at the
  ex-problem position carries the same mild background noise any marker
  shows there — the catastrophic failure is confined to robot_1's
  pre-departure *spawn* dwell, whose scoring impact depends on Arm B's
  sampling timing (not established here). No config-exposed ArUco detector
  parameter exists to tune this (`detector_params` is never wired from
  `perception_node.py`; `aruco.yaml`'s `min_detection_confidence` is dead
  config) — any such fix is an M1-code change, out of scope (v1-frozen).
- **2026-10-01** — **Y-extent PASS replicated (n=2); the `robot_1`/`x=-1.75`
  dropout below also replicated and is now a registered risk, not noise**
  (same report, rev 2: `docs/reports/2026-10-01-m1-y-extent-verification.md`)
  — **root-caused by the entry above.**
  A second run of the `|y| = 1.2` scenario (same seed, ~20 min later, full
  container restart between) reproduced the PASS near-exactly: `robot_3`/
  `robot_4` 100% fresh, 0 `STALE`, bias `0.0029`/`0.0072` m both times. It
  also reproduced `robot_1`'s `STALE` flapping at `(x, y) = (-1.75, 0)`:
  82.1% `STALE` this time vs. 74.0% the first time, 51 vs. 53-row streaks,
  19.8 vs. 20.6 s max carried-forward age — ruling out a one-off artifact.
  That point is `robot_1`'s exact spawn (and `marker_id`) in
  `isaac/config/scenarios/intersection_bottleneck.yaml`, the IB10 cell v2
  is building toward; `robot_2` (`marker_id=2`) at the mirror `x = +1.75`
  and `robot_1` itself at a different `x` (`-2.4`, the other run) were both
  100% fresh in every run, so neither "that x" nor "that marker" alone
  explains it — the combination does. Not root-caused (out of this probe's
  scope); **recommended as a build-order item before step 6 (IB10 composite
  mock smoke)**, since it bears on that cell's position-verified arrival
  scoring and Arm B's shadow classification, both of which read M1 state.
  **Supersedes the entry below's "looks like a transient... not a position
  or marker-id defect" characterization of the same observation** — it is
  reproducible, and it is specific to a (position, marker) pair, just not
  the single-variable defect first guessed.
- **2026-10-01** — **Y-extent verified at the composite command's recede
  endpoints, `|y| ~= 1.2`: PASS, wide margin** (v2 build-order step 3,
  `docs/reports/2026-10-01-m1-y-extent-verification.md`, branch
  `feat/v2-y-extent` commits `a742768`..`f4cb623`). Two mock-backend VM runs
  with all four robots held stationary: `robot_3`/`robot_4` at
  `y = -1.2`/`+1.2` tracked 100% fresh (285/285 rows), 0 `STALE`, bias
  `0.0029`-`0.0072` m — an order of magnitude under the study's own M1
  error budget. A second run additionally found `y = 1.8` (stationary, not
  just in motion) and `y = 2.0` (inside the previously-"unverified"
  `1.80-2.03` band) both 100% fresh, 0 `STALE`, bias up to `0.0113` m —
  narrowing but not closing that open question (only two discrete points
  checked). Unrelated surprise, same run: the x-axis reference point
  `robot_1` (`x = -1.75`, nominally "verified") flickered `STALE` for 74%
  of one run (longest streak 53 consecutive ~1 s rows) while its mirror
  `robot_2` (`x = +1.75`) and `robot_1` itself at a different `x` (run 2)
  stayed 100% fresh — looks like a transient per-run artifact, not a
  position or marker-id defect, but unexplained; flagged for a follow-up
  probe before any long-dwell stationary-robot scenario assumes 100% M1
  uptime. Two tooling bugs found and fixed while running this probe (both
  general, not scenario-specific): `fc_launch.sh`'s decision-summary stage
  (`ls -t m5_decisions/*.json | head -3` under `set -e -o pipefail`) aborts
  silently before its final `done: STAMP=...` line once more than 3 old
  decision files have accumulated (2180 were present) — the run itself is
  unaffected, only a caller parsing that line; and `patch_initial_tasks.py`
  originally restored `orchestrator.yaml` with `shutil.copy2` (preserves
  the backup's old mtime), which made colcon's incremental build silently
  skip re-copying the restored file into `install/` on the very next build
  — the project's "never trust colcon exit codes" trap, triggered by a
  config *restore* rather than a deploy. Caught only by an end-of-task
  manual md5 check of the installed path (the driver's own post-restore
  log line was checking the wrong path, a second bug also fixed); both
  fixed in `scripts/vm/patch_initial_tasks.py` / `scripts/vm/m1_y_extent_probe.sh`
  before the VM was left pristine.
- **2026-09-27** — **Backward-stamp-jump reset and `stale_after_sec`
  retune for sim-time stamps** (`ce31a14`, `7d4a52b`; spec
  `docs/specs/module1_perception.md` Rev 2).
  - **Reset.** With sim-stamped frames (M6 entry, same date), an Isaac
    timeline stop/restart makes stamps jump backwards. Before this change,
    `StateEstimator`'s late-frame check would then have dropped every frame
    until the new clock passed the old `_last_stamp`. Now a frame older than
    the latest stamp by more than `clock_reset_threshold_sec` clears all
    tracks and the baseline and is processed as a first frame. The flag
    `diagnostics.clock_reset: true` and `clock_reset_prev_stamp` appear only
    on that frame, so forward-only output is byte-identical (pinned by
    `test_forward_path_output_unchanged_by_clock_reset_threshold`).
    `PerceptionNode` logs a warning on it. Smaller jumps are still dropped as
    late frames. Default and launch value 1.0 s: that is 15–30 frame periods,
    far above DDS reordering, and it caps the blind window of a reset small
    enough to slip under it. Live path: `runner.py:164` stops the timeline
    after every repetition.
  - **Stale retune.** `perception.launch.py` `stale_after_sec` 3.0 → 1.15.
    The 3.0 was tuned on wall stamps, ≈ 1.14 sim-s at RTF 0.38, and the
    overlapping-marker anti-flap window is physical. `safety.yaml` and
    `safety.py` comments were updated to match (comments only). The M4
    STALE-margin comment now reads 1.15 s × 0.2 m/s = 0.23 m, not 0.6 m.
    `docs/specs/module4/safety-monitor.md` §7 still says "3 s" (historical
    run-D text, left as is).
  - **Not retuned (T1 tuning territory).** `stopped_threshold_mps` and
    `slow_threshold_mps` keep their nominal values, which shifts their
    effective values:

  Effective thresholds (M1 speeds were ≈ RTF × true, RTF ≈ 0.38, per the
  close-approach side finding):

  | Quantity | Nominal | Effective before (wall stamps) | Effective after (sim stamps) |
  |---|---|---|---|
  | M1 `stopped_threshold_mps` | 0.01 | ≈ 0.026 sim-m/s | 0.01 sim-m/s |
  | M1 `slow_threshold_mps` | 0.05 | ≈ 0.13 sim-m/s | 0.05 sim-m/s |
  | M1 `stale_after_sec` | 3.0 → 1.15 | ≈ 1.14 sim-s | 1.15 sim-s |
  | M4 `max_linear_velocity_mps` rule | 0.2 | ≈ 0.52 sim-m/s (never fired) | 0.2 sim-m/s (now live) |
  | Arm B `stopped_speed_mps` | 0.05 | ≈ 0.13 sim-m/s | 0.05 sim-m/s (now meaningful) |
  | M5 `proximity_slow_speed_mps` (close/slow stall pairs) | 0.05 | ≈ 0.13 sim-m/s | 0.05 sim-m/s |

  Live-check risks: a stationary robot's ArUco jitter may now read SLOW
  (floor 0.026 → 0.01), and M5's close/slow stall pairing now needs
  ≤ 0.05 sim-m/s rather than ≤ 0.13, so the stall trigger may fire later.
  Nav2 `max_vel_x` / `max_speed_xy` are 0.18, under M4's now-live 0.2 m/s
  rule, but filtered-velocity overshoot near the cap is unverified.

  Evidence: `docs/reports/2026-09-26-close-approach-analysis.md` side
  finding (M1 0.060 m/s vs GT 0.155 m/s at RTF 0.38); prereg amendment
  item 11 (`docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`).
  **Live verification pending** (combined VM run after merge).

- **2026-09-16** — **Marker-plane calibration: 7.5 % radial bias removed.**
  `pixel_to_world_homography` computed the homography for the ground
  plane z = 0, but the ArUco marker sits at z = 0.21 m; for the nadir
  camera at 3.0 m every world coordinate M1 reported was inflated by
  3.0/(3.0−0.21) = 1.0753 (measured: spawn −1.5 read as −1.62; errors of
  0.178 m at GT −2.268 and 0.156 m at −2.074, ratios 1.075–1.081). Fix:
  `pixel_to_world_homography(config, plane_height_m=0.0)` translates the
  camera centre down by the plane height (exact for the general tilted
  case); `build_calibration_dict` defaults `plane_height_m` to
  `MARKER_HEIGHT_M` (0.21, defined locally with a parity test against
  `marker_asset`, which cannot be imported without Isaac) and records it in
  the artifact. Regenerated `swarm_perception/config/calibration.yaml`:
  scale 0.004686 → 0.004358 m/px, offsets −2.999/2.249 → −2.789/2.092;
  intrinsics unchanged. Residuals on the three measured instances after
  the fix: 7 mm, 7 mm, 0 mm. The old test oracle used the camera height
  as the plane height — it had encoded the bias. **Consequences:** M5's
  proximity/stall geometry now sees true distances (≈7 % smaller than
  before); `annotation.py` draws registry goals (floor points) through
  the inverted marker-plane homography, so goal markers in the VLM's
  annotated frame now render ~7 % too far from the image centre —
  cosmetic, open. Host verification of M1-vs-GT with the new artifact is
  part of run D.

- **2026-07-03** — Colliding/overlapping ArUco markers make robots go STALE
  (marker lost), not STOPPED, which delays stall detection. Mitigation:
  `stale_after_sec` ≥ 3.0 and `velocity_alpha` ≈ 0.15 in the perception
  config for congestion scenarios. (`stale_after_sec` value superseded by
  2026-09-27 entry: 1.15 sim-s on sim-time stamps.)
- **2026-06-17** — Marker placement contract: the ArUco marker prim must live
  under `aruco_marker_link` (a `base_link` child inside the physics
  hierarchy), not under the robot root, or physics parses fail;
  `isaac/vgu_sim/validation.py` checks this and must be updated in sync with
  any marker-asset change (silent crash otherwise). See
  `docs/superpowers/specs/2026-06-17-aruco-markers-on-sim-robots-design.md`.

---

## M2 VLM / M5 Orchestrator Pipeline

- **2026-09-26** — **Rev 7 consolidates the night: two live batches and two
  safety-metric corrections** (`docs/reports/2026-09-25-overnight-findings.md`
  §X–§AC). Detail is in the per-topic entries — the two 2026-09-26 entries below
  (image fallback; batch-2 replay replication), the 2026-09-25 re-scoring entry
  under **Congestion-Resolution Experiment**, the 2026-09-26 `_gshort` entry
  under **M6**. New: batch 2 (gpt-4o random order, 5/6, but draws aligned with
  side so the gate rate is confounded; refusals 37.5% a-1 / 14.3% terminal) and
  batch 3 (ER-2 forced order, 5/6, 0 refusals) — **ER-2 has no `robot_1` anchor**
  (1/3 where gpt-4o is 124/125), so the slot/ID artifact is model-specific.
  **Binds every prior run: `safety.yaml min_distance_m: 0.45` is breached in
  every Arm A run (0.23–0.28 m by design; G4 wedged at 0.076 m ~18 s), and a
  zero `robot_robot_contacts` count is detector silence — use min pairwise distance.**
- **2026-09-26** — **Neutral-image fallback lands in M2; its validation arm is
  coded but unrun (no OpenAI credits).** `ReasonerConfig.image_fallback_after_attempts`
  (shipped `2`, `openai` only) makes a refused attempt `k >= threshold` re-send the
  *unchanged* prompt with a mid-grey PNG of the frame's size — once per request, no
  re-ask suffix, backends untouched; cost recorded in
  `diagnostics.{refusal_attempts,image_fallback_used,image_fallback_attempt}`. Spec
  §M2.5 FR2.5.4-5; `9d7328f`, `a255cc8`. Arm X (168 cells) aborted on
  `insufficient_quota` with **zero** rows — resume with
  `python scripts/replay_live_decisions.py --arm X --runs batch2 --n 4 --pace-sec 8.0`.
- **2026-09-26** — **Batch-2 replication weakens the obstacle-text finding;
  raw-frame arm unrun (credits).** `docs/reports/2026-09-25-frame-replay.md`
  Rev 4; Arm S2 187/288 runs, $1.24, aborted on `insufficient_quota`. The
  text-on → text-off contrast replicates in direction (pooled 0.714 → 0.375,
  p = 1.1e-3; 7/9 scenes) but **Rev 3's level does not**: P(feasible) 0.962
  (batch 1) vs 0.435 (batch 2) on prompts differing only in pose decimals, so
  the side signal is fragile and scene-dependent. Frame-amplification contrast
  (b) is now unconfirmed (batch 2 has no headroom to test it). Frame refusal
  trigger replicates: 17/96 real, 0/91 grey.
- **2026-09-25** — **Sampling config and the raw camera frame are now on record**
  (M2 §7.1 `EffectiveSamplingConfig`, M5 FR5.3.11). Every decision artifact and
  reasoner JSONL line carries `reasoner_config_effective` (model_id,
  temperature, top_p/top_k/presence_penalty, max_attempts, max_tokens, gemini
  seed/thinking_level, `unsupported_sampling`), as configured from
  `config/models.yaml` — no prior artifact proved gpt-4o ran at 0.0, the gap the
  ER-2 pilot logged as "sampling uncontrolled"; failure cycles record it too.
  `keep_raw_frames: true` (needs `keep_debug_frames`) also dumps M1's input frame
  as `<request_id>_raw.png` with `raw frame skew_sec=`; the M2 request is unchanged.
- **2026-09-25** — **Rev 6 consolidates the day: side-signal carrier, ER-2
  pilot, position-verified arrival** (`docs/reports/2026-09-25-overnight-findings.md`
  §S–§W). The three entries below carry the detail (obstacle-text side signal,
  FR5.1.9 arrival check, `max_attempts` 2 → 4). New in Rev 6: the six-run ER-2
  pilot (`data/logs/vm_runs/ER2_PILOT_SUMMARY.txt`, runs
  `20260925_{124609,130115,132335,133841,135334,140824}`) — 0/115 refusals,
  gate 2/6, episode outcome 3/6 by log but 2/6 physically, sampling
  uncontrolled; the earlier "geometry unused / channel inert" claims marked
  superseded for gpt-4o; the ER-2 opening `reverse` marked trigger-confounded
  (3/4 solo-stall vs gpt-4o 0/6). **Do not quote any pre-`4f39899` arrival
  count until it is re-scored from the scene log at 0.35 m.**
  (`docs/reports/2026-09-25-frame-replay.md` Rev 3; Arms S and D, 348 runs,
  $2.66). Within-artifact ablation on the six genuine standoffs (3/side) x order
  x obstacle-text x image: withholding the text with the real frame kept
  collapses P(feasible) 0.962 → 0.556 (p = 8.8e-4); the frame amplifies; states
  alone carry nothing. Still **0/288** traces cite the blocker — **never read
  trace silence as a channel being unused; ablate.** `id_asc` picks `robot_1`
  124/125 whatever the channels, so the slot bias *suppresses* this one.
- **2026-09-25** — **Base-goal arrival is now position-verified (FR5.1.9).** M5
  marked a robot arrived on Nav2's own "Goal succeeded": in run
  `20260925_124609` `bt_navigator` succeeded for robot_2 while M1 put it 0.59 m
  away (logged `distance_to_goal_m={'robot_2': 0.59}` 21 times after).
  `swarm_orchestrator/arrival.py` cross-checks it at 0.35 m (> M1's ≈0.1 m bias,
  ≤ `arrived_radius_m`); a rejected arrival stays stall-eligible and is accepted
  late once M1 reaches tolerance. Episode closure now follows the verdict, so
  `prompt_robot_order: random` draw sequences shift too. **Prereg:** episode
  outcome must be position-verified in both arms — re-score pre-fix runs from
  `scene_log_dir`, and treat their order draws as not comparable either.
- **2026-09-25** — **`openai` reasoner `max_attempts` raised 2 → 4.**
  `config/models.yaml` nests `max_attempts: 4` under `vlm.openai.reasoner`.
  Per Arm M (`docs/reports/2026-09-25-frame-replay.md` Rev 2), conditional
  on a refused first attempt, terminal refusal is 57.1% shipped vs 26.9% at
  `max_attempts=4` (p = 0.031); trigger is the annotated frame, not text.
- **2026-09-25** — **Rev 5: Arm A pilot green on the adopted defaults; the
  refusal class is bigger and image-driven**
  (`docs/reports/2026-09-25-overnight-findings.md` §O–§R, consolidating the
  three entries below). Six runs (`20260925_063520`/`065143`/`070637`/`072130`/
  `073621`/`075116`, gpt-4o T=0.0, obstacles ON, order `random`, gate `"swap"`,
  `keep_debug_frames: true`): M2 named an infeasible yielder in 4/6, the gate
  re-grounded all four, first yield COMPLETED 6/6 (142.2–147.9 s), episode
  outcome 4/6 — both misses the blocker-on-goal-path property, not coordination
  failures. First `yield_robot` = `robot_1` in 5/6 (ID-anchored); zero `reverse`
  openings. **Supersedes the "3 of 22" refusal figure in the §K–§N entry
  below**: 23/101 attempt-1, 12/101 terminal, 9 of 12 obstacle-ON, Rev 1 §6(b)
  included. Replay Arms O/M/grey stay blocked on OpenAI credit.
- **2026-09-25** — **Frame replay complete (rev 2); supersedes the "Arm O n=1 /
  Arms M, grey not run" entry below.** 546 runs, 708 calls, $3.97
  (`docs/reports/2026-09-25-frame-replay.md`). Grey sub-arm settles the refusal
  trigger within one design: **0/120** refusals on grey images against 22/60 on
  the same prompts with their real frames (p = 1.5e-12). Arm R over all 74
  artifacts: 42/222 attempt-1 (18.9%), terminal 9.9%. Arm O (n=8): P(robot_1)
  0.979 `id_asc` vs 0.468 `id_desc` (p = 5.0e-9); under `id_desc` **only**, the
  choice covaries with obstacle side (west 2/23 vs east 20/24) — mechanism OPEN:
  0/95 decisions and 0/95 `<think>` traces cite the obstacle, and n = 3
  artifacts per side. Do NOT flip the default to `id_desc`; keep
  `prompt_robot_order: random`. Arm M: `max_attempts=4` cuts terminal refusals
  from 57.1% to 26.9% of refused analyses (p = 0.031); retrying the ORIGINAL
  prompt is worse than the re-ask (85.7%). **Action: set `max_attempts: 4` for
  the gpt-4o reasoner.**
- **2026-09-25** — **The real annotated frame is the gpt-4o refusal trigger**
  (`scripts/replay_live_decisions.py`, report
  `docs/reports/2026-09-25-frame-replay.md`). All 74 pilot prompts re-render
  byte-identically from `scene` + `orchestrator.yaml.used` + stored order (74/74
  SHA-256, failure-context artifacts included). Replaying 36 of them x n=3 with
  the real PNG gives 27/108 attempt-1 refusals (25.0%) against 0/240 on the same
  prompts with synthetic images (p = 1.2e-13) and 8/36 live (p = 0.83); terminal
  11.1%, re-ask recovers 55.6%. Arm O reached only n=1/cell and Arms M/grey did
  not run — the OpenAI credit balance was exhausted mid-run (HTTP 429
  `insufficient_quota`, now a `QuotaAbort`; resume with the same commands, cells
  are keyed and skipped).
- **2026-09-25** — **gpt-4o refuses ~23% of M2 calls; the re-ask recovers half,
  and the prompt is not the trigger.** Census of all 163 local decision
  artifacts: 12 terminal refusals (not 3) spread over obstacle-ON *and* -OFF
  runs, plus 11 `parse_status="invalid"` artifacts with the same
  "no JSON object" signature that the re-ask rescued — so 23/101 gpt-4o calls,
  0/62 ER-2. Every prompt-side split (obstacles p=1.0; failure context
  0.0030→0.094; time window 0.013→0.080) collapses once attempt 1 is scored,
  two refusals differ from a success by two characters, and a 240-call offline
  replay of the stored prompts (± re-ask suffix, T=0/0.6, wording ablations,
  gpt-4o-mini) produced **0 refusals** in 30/30 cells, $1.21. Act:
  `max_attempts` 2→4, and
  persist per-attempt `raw_text`. `docs/reports/2026-09-25-gpt4o-refusals.md`.
- **2026-09-25** — **The offline presentation-order probe does not predict live
  behaviour; gpt-4o has a refusal failure class.** Five gate-`off` runs on
  `w0p2_eopen` (`20260925_035042`/`040539`/`042022` ER-2, `043512`/`045004`
  gpt-4o, tree `e6be85c`). ER-2 without the gate reproduces the gpt-4o failure
  (D2 named the blocked `robot_1`, yield FAILED, arrested at the same 0.1020 m)
  but not deterministically — 3/6 `robot_1` across all six ER-2 asymmetric runs.
  gpt-4o with the obstacle channel OFF still names `robot_1` (9/11 live, 5/6
  under `id_desc`) against 0.25 offline: **the live pipeline is ID-anchored, the
  synthetic probe slot-anchored** — treat the probe as a stimulus study. New:
  3 of 22 gpt-4o analyses returned `"I'm sorry, I can't assist with that."`
  (`VLMOutputParseError`, `attempts=2`), 0 of 37 on ER-2; and ER-2's opening
  `reverse` is 5/6, not 3/3. `docs/reports/2026-09-25-overnight-findings.md` §K–§N.
- **2026-09-25** — **ER-2 verified live as an M2 backend; its signature is an
  opening `reverse`.** Four closed-loop runs (`20260925_021549`/`023122`/
  `024628`/`030129`, tree `e6be85c`) all reached 2/2 arrivals with 25/25
  artifacts `attempts=1`, `parse_status=valid`, no `decision=None`, no 429s. ER-2
  matches gpt-4o on the symmetric baseline and on the gate cell (G1 named the
  blocked `robot_1`; M3 `swap` re-grounded to `robot_2`), but on **every**
  asymmetric scene it opens with `reverse`, which completes in ~35 s without
  resolving the standoff — failure context then steers it to `yield`, one extra
  analysis per episode. So **ER-2's first decision is not comparable to
  gpt-4o's**; use episode outcome as the primary metric. Permanent confounds:
  the Interactions API drops sampling and emits no `<think>` block though
  thinking is billed. `docs/reports/2026-09-25-overnight-findings.md` §F–§J.
- **2026-09-25** — **ER-2 arm of the offline presentation-order probe**
  (`docs/reports/2026-09-25-presentation-order-probe.md` Rev 2).
  `probe_presentation_order.py --backend gemini --seeds N` sweeps seeds `0..N-1`
  (one backend per seed) because the Interactions API has no temperature; records
  carry `seed` + `unsupported_sampling` and rows key on `temperature="seeded"`,
  leaving the gpt-4o rows byte-identical. 180 calls, 0 parse failures: ER-2 chose
  `reverse` in 155/180, `P(correct)=6/13`, and the textual obstacle channel drives
  `yield` to zero (60/60 vs 47/60, p=1.2e-04) with no justification naming it.
- **2026-09-25** — **`feat/gemini-er2-backend` merged onto the FR2.1.9 line**
  (`c7a08e7`, a `--no-ff` merge of `7d6e1c4`). Select ER-2 with
  `reasoning_backend_id: gemini` in
  `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml` plus a
  `GEMINI_API_KEY` in the environment; `config/models.yaml`'s `vlm.gemini`
  block carries no `reasoner:` override on purpose, so the backend inherits the
  shared sampling defaults (temperature 0.6) and reports what the Interactions
  API drops in `ReasonerDiagnostics.unsupported_sampling`. `vlm.openai` still
  resolves to temperature 0.0, unchanged. Prompt-block order after the merge:
  robot states → pairwise geometry → static obstacles → known IDs → failure
  context → guidance → visual cross-check → output format, so the cross-check
  block's "the pairwise geometry above" still refers to a block above it.
  **Re-pin:** the crosscheck baselines `_BASELINE_PROMPT_SHA256` (`5a57c937…`
  → `3b77d224…`) and `_BASELINE_PROMPT_SHA256_NO_GEOMETRY` (`4664ff95…` →
  `a9c8abfc…`) in `tests/unit/test_prompt_builder.py` were generated at
  7f5e075, which predates the permanent `yield_robot` stimulus change; a
  rendered diff of `_request()` at 7d6e1c4 vs the merge shows only the three
  documented FR2.1.9 edits, so the pins were re-pointed, not the prompt fixed
  (`590ac23`). The geometry-on value is now identical to
  `_PRE_OBSTACLE_OFF_PROMPT_SHA256` by construction; both constants are kept
  because they pin the same string for different reasons. Artifacts under
  `data/logs/er2_grounding` were collected under the 7f5e075 prompt and are
  comparable with each other, not byte-identical to post-FR2.1.9 renders.
- **2026-09-25** — **Five live gpt-4o runs validate the feasibility gate; `swap`
  is the recommended default.** L1 `20260925_002713` (`id_asc`, `swap`)
  re-grounded `robot_1`→`robot_2` → COMPLETED yield, 2/2 arrivals, on the cell
  that fails deterministically ungated (L4 `011246`, `off`: FAILED at 0.102 m,
  0/2). The gate is a no-op when the yielder is already feasible (L2 `004252`,
  L3 `005754`); `refuse` is inferior (L5 `012747`, 1/2). Random order is
  mechanically correct (provenance verified, `episode_index` stable at 0 across
  an episode) but changes no outcome alone. **Corrects the order entry below:
  live, the slot effect is weaker than offline — `robot_1` named in 7/9 pooled
  obstacle-ON live runs regardless of order, and L1 vs L3 (identical config)
  disagreed, so T=0.0 is not run-to-run deterministic.** Caveat: all five runs
  ran obstacles ON, so order and channel co-vary. `docs/reports/2026-09-25-overnight-findings.md` §B–§D.
- **2026-09-25** — **M3's yield feasibility gate is now visible in the M5
  decision artifact.** Merging `feat/order-random` and
  `feat/m3-yield-feasibility` left a provenance gap: with
  `grounding_yield_feasibility` on, the robot that executes a yield need not be
  the one `decision.yield_robot` names, and nothing outside the grounded
  command said so. `summarize_yield_grounding` (`reasoning_pipeline.py`) reads
  the gate's outcome back off that command — a swap tags the yield action's
  parameters with `yield_robot_grounded_from`, a refusal drops the yield action
  and fans out `temporary_wait` with a `"yield refused:"` reason — and
  `write_decision_artifact` records `yield_robot_grounded_from`,
  `yield_regrounded_reason`, `yield_refusal_reason` plus the configured
  `grounding_yield_feasibility` mode. Gotcha: the refusal test must be the
  `"yield refused:"` **prefix**, not the presence of `reason` — a yield that
  grounded normally also carries one, the M2 root cause. The node logs
  `yield re-grounded request=… from=… to=… reason=…` /
  `yield refused request=… reason=…` on the same helper, so the log and the
  artifact cannot drift. Spec FR5.3.10 in `docs/specs/module5_orchestrator.md`.
- **2026-09-25** — **`prompt_robot_order: random` counterbalances the
  presentation order per congestion episode, with the drawn order auditable.**
  `swarm_orchestrator/presentation_order.py` adds a pure
  `PresentationOrderPolicy(mode, seed).order_for_episode(k)` plus an
  `EpisodeOrderTracker` that holds one episode's order across its re-analyses;
  each decision artifact now carries `robot_presentation_order` (read off the
  request, so it cannot disagree with the persisted prompt hashes),
  `prompt_robot_order_mode`, `prompt_robot_order_seed` and `episode_index`.
  Gotcha: the episode scope is **not** `AttemptMemory`'s — that memory returns
  nothing at `failure_context_window_sec: 0` (the RQ5 memoryless control), which
  would re-draw the order inside a single deadlock. `prompt_robot_order_seed:
  null` derives the seed from `VGU_RUN_ID` via SHA-256, not `hash()`
  (`PYTHONHASHSEED` randomizes string hashes per process). Default stays
  `id_asc`. Commit `43bf941`; spec FR5.3.9 in `docs/specs/module5_orchestrator.md`.
- **2026-09-25** — **Live counterbalanced runs confirm the offline verdict: the
  yielder M2 names follows presentation order, not feasibility.** Four gpt-4o
  runs, obstacle modality ON: R1 `20260924_195708` `w0p2_eopen`/`id_desc` →
  `robot_2`, COMPLETED 146.4 s; R2 `20260924_201328` `w0p2_eopen`/`id_asc` →
  `robot_1`, FAILED 243.7 s arrested 0.102 m from the blocker; R3
  `20260924_203437` / R4 `20260924_205009` `wopen_e0p2`/`id_desc` → `robot_1`
  twice, COMPLETED. **Caveat: the three `id_desc` runs yielding a feasible robot
  is a design coincidence — each bias aligns with feasibility in one variant —
  not feasibility reasoning; no justification cited the obstacle.** Gotcha:
  `static_obstacles` ships commented out in `swarm_orchestrator/config/orchestrator.yaml`,
  so `prompt_static_obstacles: true` alone renders no obstacle block while the
  MODALITY guard reports ON. Detail: `docs/reports/2026-09-25-overnight-findings.md`.
- **2026-09-25** — **Closed loop replicated on the new host** (run_id
  `20260924_193112`, `head_on_deadlock`, openai gpt-4o at temperature
  0.0, obstacle modality OFF). First analysis 34.6 s after components
  started, both robots stalled at 0.26 m nose-to-nose (a third onset
  mode between the 0.08 m contact and the ≈0.45 m planner-stall standoff
  recorded 2026-09-16); one `yield` (`yield_robot=robot_1`), `COMPLETED`
  after 148 s; robot_2 arrived at +3.3 min, robot_1 at +5.5 min; 12 m
  52 s wall; 0 analyses after both arrivals (2 348 `trigger suppressed`
  lines). Deviation worth keeping: after robot_2 had arrived, a *solo*
  stall of robot_1 (`robots=['robot_1']`, distance 1.18 m, not facing)
  triggered a second analysis that the model answered `anomaly`/`reroute`
  — the congestion gate fires on single-robot stalls, which the
  pre-registration's episode rule should account for. Component logs
  live inside the container (`/tmp` of `vgu_ros`); `docker cp` them
  before the launcher's exit-trap restart. Artifacts (git-ignored):
  `data/logs/vm_runs/20260924_193112/` on the workstation.
- **2026-09-19** — **Correction: the OFF-condition comparability claim below
  overstates what the byte-identity test proves, and the 44/44 census
  over-reads compliance as absence-of-signal** (final whole-branch review,
  Finding 1). (a) `yield_robot` (FR2.1.9) has **no OFF condition** — it is a
  permanent prompt change (adds the output-format bullet, extends the
  `<think>` step, and removes the `strategy="yield" (first listed robot
  backs up)` clause) applied to every request from `c4072d0`/`0efd01e`
  onward. Rendering the shared `_request()` fixture at branch base
  `e21326f` (3171 chars, sha `5a57c937…`) versus HEAD with the obstacle
  modality off (3338 chars, sha `3b77d224…`) shows the 167-char delta these
  edits introduced. The obstacle modality's byte-identity test (`056fa22`,
  below) pins the OFF obstacle condition against the tree *after* this
  change — a true and useful guarantee for isolating that one modality, but
  it does not establish that the OFF condition at HEAD matches the
  pre-2026-09-19 stimulus, which the entry below implies. (b) The 44/44
  `robot_1`-first census below (design review Finding 2) was collected
  under a prompt that *instructed* "first listed robot backs up", so it is
  substantially evidence of compliance with that instruction, not only
  evidence that the position channel went unused when free to vary. Full
  reasoning: `docs/specs/module2_vlm_reasoning.md` FR2.1.8/FR2.1.9,
  `docs/reports/2026-09-18-head-on-family-validity.md` Rev 6.
- **2026-09-19** — **Two observability channels landed as declared,
  default-off Arm A modalities** (owner instruction: "do your
  recommendations", responding to the 2026-09-19 design review). (1)
  `CongestionDecision.yield_robot: str | None`, meaningful only when
  `strategy == "yield"`, never required — module-2 FR2.1.9
  (`c4072d0`, `0efd01e`: `feat: add explicit yield_robot field to the
  congestion decision`, `fix: scope yield_robot reordering to yield and drop
  the list-order hint`). `reasoning.rag.command_grounder.resolve_robot_order`
  moves it to the front of `involved_robots` only for `strategy == "yield"`,
  leaving `reroute` (which reads `robot_ids[0]` as the rerouter) and every
  other strategy untouched. Before this field, list position in
  `involved_robots` was the only yielder channel; a census of 524 decision
  artifacts found `robot_1` listed first in 44/44 `yield` decisions — never
  once `robot_2` — i.e. position had never been observed to carry a choice
  (`docs/superpowers/specs/2026-09-19-head-on-asymmetric-family-design-review.md`,
  Finding 2; caveated by the 2026-09-19 correction above — the prompt
  instructed this exact convention, so 44/44 is compliance evidence too).
  (2) `ReasonerRequest.include_static_obstacles` /
  `static_obstacles: list[StaticObstacleInput]`, rendered as a
  "Static obstacles (world-frame axis-aligned boxes):" block (id, centre,
  extent only — no wording naming a robot, maneuver, or blocked side) —
  module-2 FR2.1.8, M5 `prompt_static_obstacles` (`bf2d89d`, `501bb49`:
  `feat: add static-obstacle prompt modality behind a default-off flag`,
  `fix: keep prompt-facing obstacle ids neutral and gate the ON clause`).
  Both default **off**; an off prompt (or an on prompt with no obstacles
  configured) is byte-identical to the pre-modality prompt, pinned by a
  length + SHA-256 test (provenance commit `056fa22`), because every
  decision artifact collected before 2026-09-19 was produced without either
  channel and comparability depends on the off condition never changing a
  byte. **Superseded by the 2026-09-19 correction above**: "both default
  off" is true of the obstacle channel but not of `yield_robot`, which has
  no off switch, and the byte-identity test only isolates the obstacle
  modality — it does not establish comparability with the pre-2026-09-19
  corpus. `orchestrator.yaml`'s shipped `static_obstacles` ids are
  deliberately neutral (`obstacle_1`, not the scenario yaml's `blocker_west`)
  and must not be synced to the scenario yaml's descriptive names — the id
  renders verbatim into the prompt and would otherwise hand the model the
  inference the modality exists to measure (fix round 1, `501bb49`, after a
  review caught the initial `blocker_west` id as exactly that leak). Specs:
  `docs/specs/module2_vlm_reasoning.md` FR2.1.8/FR2.1.9,
  `docs/specs/module5_orchestrator.md` (config table), rev-8 spec rev 8.6.
- **2026-09-18** — **`include_visual_crosscheck` does NOT transfer to
  `gpt-4o`: a prompt-level change with a model-level effect. Do not turn the
  flag on for the `openai` arm.** Full five-cell x two-variant matrix against
  `openai`/`gpt-4o` at its pinned temperature 0.0 (resolved via
  `resolve_reasoner_config`, recorded per artifact), same two stimuli
  (SHA-256 re-verified `1dea9aed…3589` / `ad5db360…ea31`, re-measured at 0.251 m
  and 4.884 m), n = 5 per cell per variant, 50 calls: Experiment 6 in
  `docs/reports/2026-09-18-gemini-er2-image-grounding.md`; artifacts
  `data/logs/er2_grounding/grounding_run4_gpt4o_xcheck_{off,on}.jsonl` (VM,
  git-ignored). No harness change was needed — the probe already drove
  `--backend openai --experiment 4`. Results: both gates 5/5 in both variants;
  the cross-check-off half **replicates the earlier n = 3 baseline exactly**;
  the added Fix-B regression cell E stayed no-congestion **5/5 in both
  variants**, so the wording does not reopen run 3 on the arm that produced it.
  But the incongruent cells answer per the image **1/10** against ER-2's 10/10
  (cell B 1/5, cell C 0/5), missing the pre-stated ≥ 3/5 criterion in both — so
  the flag is ineffective, not unsafe, here. Three consequences: (a) **new
  hazard** — justifications mentioning the image go 0/25 → 18/25 with the flag
  on, and 9/10 contradiction-cell calls assert the image *confirms* the states
  while the frame grossly contradicts them, so `justification` text cannot be
  read as evidence of image use (register A8); (b) **A3's scope changes** —
  `gpt-4o` never returned ER-2's `anomaly`/`priority_override`, but its one
  detecting call misclassified too (`crowding`/`reroute`), and in a *different
  way*: ER-2 mislabelled the input-integrity condition (a missing enum slot),
  `gpt-4o` mislabelled the physical configuration (a wrong pick among existing
  slots — `deadlock` was available). So A3's conflation claim still rests on
  ER-2 alone, the recommended `state_disagreement` type would not have fixed
  `gpt-4o`'s error, and A3 is the binding blocker for `gemini` only since
  `gpt-4o` mostly fails to detect at all (register A3 now carries a
  minimal-ontology-fix recommendation — not implemented); (c) **two
  prior observations narrowed** — `gpt-4o` at temperature 0.0 is *near*-, not
  fully, deterministic (2–5 unique raw responses per 5 repeats, so every n = 5
  "5/5" here is ~n = 1 plus a stability check), and the `<think>` block is a
  verbatim template echo in 23/25 and 19/25 rather than 12/12, with the added
  content landing only in the congruent cells (contradiction cells: pure echo
  10/10). VM protocol as before: `reasoning/vlm/{models,prompt_builder}.py` and
  the probe script installed for the run and restored byte-verified afterwards
  (`7cf02340…b071d7` / `e1441903…41ea6e4`), probe script not left resident.
  Register open item 2 closed (`docs/reports/2026-09-18-research-findings-register.md`).

- **2026-09-18** — **The 2026-09-18 null result was our prompt, and it is
  apparatus-wide: an opt-in image/state cross-check inverts it without
  breaking Fix B.** *(Partly superseded by the entry above: the null result is
  apparatus-wide, but the cross-check fix is ER-2-specific.)* New modality flag
  `ReasonerRequest.include_visual_crosscheck` (default `False`;
  `reasoning/vlm/models.py`, `reasoning/vlm/prompt_builder.py`) appends a block
  that gives the image precedence over the state block **only on a clear
  contradiction**, leaving Fix B's "do not re-derive distances or facing from
  the coordinates" clause verbatim; the off-variant prompt is byte-identical to
  the pre-flag one, pinned by SHA-256 in `tests/unit/test_prompt_builder.py`.
  Measured on the same two stimuli, n = 5 per cell, both variants (report
  Experiments 4–5 in `docs/reports/2026-09-18-gemini-er2-image-grounding.md`;
  artifacts `data/logs/er2_grounding/grounding_run3_{xcheck_off,xcheck_on,gpt4o_off}.jsonl`,
  VM, git-ignored): ER-2's incongruent cells go from **0/10 to 10/10
  image-consistent** answers with both gates still 5/5, and the added Fix-B
  regression cell (1.2 m apart, `|Δθ| = π`, diverging, both MOVING) still
  answers no-congestion 5/5 under the new prompt — run 3 is **not**
  reintroduced. Two facts that block adoption and one that changes the
  preregistration: (a) cell B's detection is right but 4/5 of its answers are
  `type=anomaly` with `priority_override`/`reroute` rather than
  `deadlock`+`yield`/`reverse`, so the flag would dispatch the wrong command —
  do not turn it on in production yet; (b) the same 2x2 against
  `openai`/`gpt-4o` at its pinned temperature 0.0 followed the text 6/6, so
  "Arm A's decision is text-driven under the production prompt" applies to the
  primary cell too, and the parent spec's modality table now carries the axis
  as `—`/unregistered (rev 8.6); (c) `gpt-4o` does emit a `<think>` block
  (12/12) but its content is a verbatim echo of the prompt's template sentence,
  settling ER-2 design doc §4(d)'s unverified claim in the direction of "no
  usable trace from either hosted arm".

- **2026-09-18** — **Gemini ER-2 reads our overhead frame but does not decide
  from it: decision-level image grounding is NOT demonstrated.** Report:
  `docs/reports/2026-09-18-gemini-er2-image-grounding.md`; harness
  `scripts/probe_gemini_er2_grounding.py`; artifacts
  `data/logs/er2_grounding/grounding_run{1,2_exp3_n9}.jsonl` (VM, git-ignored).
  Two frames from `run_id=gemini_20260918_084649`, measured at 0.251 m
  (nose-to-nose) and 4.884 m apart, were crossed with synthetic 0.35 m-facing
  and 2.50 m-diverging text states through the unmodified prompt and
  `Reasoner` at `thinking_level: low` with no `seed`. Both congruent gate
  cells passed 3/3; in the incongruent cells the decision followed the
  **text** — 6/6 calls with `include_pairwise_geometry=True` (n = 3/cell) and
  22/24 with it `False` (n = 12/cell), the 2 exceptions being the only
  responses in 36 decision calls whose justification reads visual rather than
  numeric. ER-2's native pointing, by contrast, hit both robots in both
  frames (12/12 points inside half a robot width, 0.005–0.125 m, including
  the pair 0.25 m apart), so the image is readable to it and still does not
  move the answer. Prereg consequence: for this scenario and prompt the
  `gemini` Arm A cell is equivalent to a text-only reasoner (spec Rev 5 open
  item). **Gotcha:** the ArUco detector cannot be re-run reliably on M1
  *annotated* frames — the 40x40 px status box and the velocity arrow are
  drawn over the 28 px marker and destroy its quiet zone (both markers
  recovered in 3 of 121 sampled frames) — so ground truth for an annotated
  frame comes from `data/logs/m5_scene/<session>.jsonl` at the header stamp
  `scripts/record_topic_video.py` burns into the frame, which agrees with
  re-detection to ~1 mm where both are available.
- **2026-09-18** — **Gemini ER-2 live-run recipe committed as
  `scripts/run_gemini_er2_demo.sh`, generalized over `BACKEND_ID`.** The
  launch sequence behind the `gemini_20260918_084649` run (entry directly
  below) existed only as `/tmp/gem_record_launch.sh` on the VM and would not
  have survived a reboot; retrieved and landed in the repo. Backend is now a
  parameter (`BACKEND_ID`, default `gemini`) instead of hardcoded: the script
  sets `reasoning_backend_id` in `ros2_ws/src/swarm_orchestrator/config/
  orchestrator.yaml` and runs `colcon build --merge-install --packages-select
  swarm_orchestrator` before launching, because `orchestrator.launch.py`
  loads the **installed** copy via `get_package_share_directory` — a source
  edit alone is inert (same trap noted in the entry below). The cleanup trap
  now restores the previous `reasoning_backend_id` and rebuilds again on
  exit, so a run can no longer silently leave the VM pointed at a different
  model — that exact revert had to be done by hand after the live run this
  script is derived from. Matches `scripts/run_phase3_demo.sh` house
  conventions (`set -euo pipefail`, `log`/`wait_topic`/`wait_action`
  helpers, `sudo timeout` not `timeout sudo`, cleanup trap) and preserves the
  bracketed-`pkill` convention (`"[i]saac.scripts.run_simulation"`) from
  `docs/superpowers/plans/2026-09-18-head-on-asymmetric-family.md` so a kill
  pattern can't match its own invocation. ffmpeg re-timing (`setpts=<stamped
  fps / achieved fps>*PTS`, per the entry below's 2.1033 factor) is
  documented as a manual post-step in the script header, not automated —
  achieved fps is only known from the recorder's own exit line after the
  run. Verified with `bash -n` and a read-through only; not re-run on the VM
  (that would repeat the ~20 min live demo).
- **2026-09-18** — **Full closed-loop `head_on_deadlock` demo run live on the
  `gemini` backend (Gemini Robotics-ER 2); both robots reached their goals and
  the entry directly below's artifact fix is confirmed live.** Run
  `run_id=gemini_20260918_084649` on the GCP VM (run-H recipe:
  `localization:=camera`, M1 before Nav2, seed 42). Five analyses, all
  `backend_id=gemini-robotics-er-2-preview`, all `parse_status=valid` at
  `attempts=1` — so **`force_schema=false` held up live with zero re-asks and
  zero parser rejections**, and no fallback to `openai` occurred. Sequence:
  `deadlock`/`reverse` dispatched and `completed` but did not clear the
  standoff; the next analysis carried `failure_context` and ER-2 explicitly
  cited it ("the previous attempt to reverse both robots did not successfully
  resolve the deadlock, the yield strategy is now selected"), returning
  `deadlock`/`yield`, which M3 grounded, M4 dispatched, and which resolved the
  conflict — robot_2 arrived at `(-2.5, 0.0)`, robot_1 at `(2.5, 0.0)`. This
  is the first end-to-end evidence that the failure-context loop changes a
  *live* second decision, not just a unit-test fixture.
  **Artifact confirmation of the fix below:** every one of the five
  `data/logs/m5_decisions/<request_id>.json` files carries
  `diagnostics.unsupported_sampling = {"presence_penalty": 0.0,
  "temperature": 0.6, "top_k": 20.0, "top_p": 0.95}` (`top_k` renders as
  `20.0` because `_extract_unsupported_sampling` casts through `float`).
  Correction to that entry's wording: the M5 path writes no *reasoner* JSONL —
  `write_reasoner_log` is called only by tests, and M5's JSONL is the M1 scene
  log (`append_scene_log` → `data/logs/m5_scene`), which carries no
  diagnostics. The confound is checkable only from the per-request JSON that
  `swarm_orchestrator.reasoning_pipeline.write_decision_artifact` writes,
  which dumps `ReasonerDiagnostics.model_dump(mode="json")` wholesale.
  **Measured, single run, not a claim about the models:** ER-2 latency mean
  3384 ms (min 3162, max 3765) against the tagged gpt-4o run
  `run_id=20260917_163714` at 3863 ms; total tokens mean 2297 vs 1826, the
  gap explained by ER-2's `thought_tokens` (137–224/call), which has no
  gpt-4o counterpart. ER-2 returned `congestion_detected=false` on three of
  five analyses with explicit numeric grounds (robots "1.20 meters apart",
  above the 0.5 m threshold) while robots were still flagged stalled — i.e.
  it declined to declare deadlocks on separated/parked robots, the inverse of
  gpt-4o's spurious-deadlock failure mode recorded for run 3. One run and
  five calls: directional only, not a measured difference.
  **Two setup traps confirmed, one brief correction.** The backend switch is
  `reasoning_backend_id` in `ros2_ws/src/swarm_orchestrator/config/
  orchestrator.yaml`, not `config/models.yaml`, and `orchestrator.launch.py`
  loads the **installed** copy via `get_package_share_directory`, so the
  source edit only takes effect after `colcon build --merge-install
  --packages-select swarm_orchestrator` (plain `colcon build` errors in this
  workspace). Contrary to the dispatch brief, the VM's **source**
  `orchestrator_node.py` also lacked the `gemini` branch of
  `_load_vlm_config`, as did `reasoning/vlm/{reasoner,models}.py` (VM is not a
  git checkout; files are hand-copied) — all three needed copying from
  `85b4b18`. Also contrary to the brief, the `Path("config/models.yaml")`
  CWD trap was never live here: container `vgu_ros` already has
  `WorkingDir=/ws`, so prior `openai` runs were not silently falling back;
  `-w /ws` was passed anyway to make that definitive. Isaac must be launched
  as the `ubuntu` user (`/home/ubuntu` is mode 0750). Evidence:
  `data/logs/recordings/2026-09-18/` (git-ignored; 566 s real-time capture,
  recorder achieved 3.941 fps against a stamped 8.289, so playback needs
  `setpts=2.1033*PTS`).

- **2026-09-18** — **`unsupported_sampling` now reaches the persisted run
  artifact, not just `BackendResponse.raw`/stderr.** Closes the gap the
  entry directly below flagged: `GeminiBackend` recorded dropped
  `temperature`/`top_p`/`top_k`/`presence_penalty` in
  `BackendResponse.raw["unsupported_sampling"]`, but `Reasoner.run()`
  (`reasoning/vlm/reasoner.py`) only threaded `latency_ms`/`token_usage`/
  `parse_status` into `ReasonerDiagnostics`, so a preregistered run's JSONL
  trace never carried the confound. Added
  `ReasonerDiagnostics.unsupported_sampling: dict[str, float] | None = None`
  (`reasoning/vlm/models.py`; `None` means "backend honoured everything or
  didn't report," distinct from an empty dict). `Reasoner.run()` now
  validates and threads `BackendResponse.raw.get("unsupported_sampling")`
  through every diagnostics-construction site — first-attempt success,
  re-ask-then-success, and exhausted-retries via `build_failed_result`
  (malformed values, e.g. non-dict or non-numeric entries, are dropped to
  `None` rather than raised). `write_reasoner_log` emits the key only when
  set. This is backend-agnostic: `AnthropicBackend`/`OpenAIBackend`/
  `LlamaServerBackend` are untouched and get `None`, so `AnthropicBackend`'s
  equivalent silent drop (`anthropic_backend.py:42`) remains invisible in its
  own artifacts until it adopts the same `raw["unsupported_sampling"]`
  convention — see the open-items list in
  `docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`
  (Rev 4). Tests: `tests/unit/test_reasoner.py` (new cases covering presence,
  absence, malformed input, the re-ask path, and the JSONL artifact).

- **2026-09-18** — **`gemini` VLM backend landed and live-verified through the
  real reasoner path.** Supersedes the "backend code remains untouched" line
  in the probe entry directly below: `GeminiBackend`
  (`reasoning/vlm/gemini_backend.py`), `GeminiBackendConfig`
  (`reasoning/vlm/models.py`), the `"gemini"` branch in
  `reasoning/vlm/backend_factory.py`, and a `vlm.gemini` block in
  `config/models.yaml` are implemented (`force_schema` defaults `False`, per
  the probe's gate result) and unit-tested
  (`tests/unit/test_gemini_backend.py`, 20 tests, mocked `requests`).
  `AnthropicBackend`'s silent drop of `temperature`/`top_p`/`top_k` is not
  repeated: `GeminiBackend` records the four `ReasonerConfig` sampling fields
  it cannot send in `BackendResponse.raw["unsupported_sampling"]` on every
  call and logs one WARNING per backend instance. Verified live on
  `vgu-canary-base-isaac-workstation-vm` (container `vgu_ros`) through
  `reasoning.vlm.reasoner.Reasoner` — not the probe script — via a throwaway
  scratchpad driver wrapping `build_backend("gemini", GeminiBackendConfig())`
  in a response-recording shim, against the same real frame the probe used
  (`data/logs/m5_frames/0cad824071954e21832da19a6fcb588b.png`) with two
  robots 0.35 m apart and mutually facing (a genuine head-on configuration,
  unlike the probe's non-conflicting 1.00 m synthetic states). Result: HTTP
  200 (implied — the backend raises `ConnectionError` on ≥400), latency 2492
  ms, 1 attempt, `token_usage={"prompt_tokens": 1907, "completion_tokens":
  138, "thought_tokens": 121, "total_tokens": 2166}`,
  `raw["unsupported_sampling"] = {"temperature": 0.6, "top_p": 0.95, "top_k":
  20, "presence_penalty": 0.0}` populated as designed, and a correctly parsed
  decision: `congestion_detected=true type=deadlock strategy=yield
  involved_robots=[robot_1, robot_2]` — the textually correct answer for a
  0.35 m head-on pair under the prompt's 0.5 m threshold rule, extracted from
  a markdown-fenced JSON block despite `force_schema=False`. This also
  confirmed the real usage-block shape empirically: the provider nests usage
  under a top-level `"usage"` key with `total_input_tokens`,
  `total_output_tokens`, `total_thought_tokens`, `total_tokens` present
  exactly as named in the Rev 2 probe's §6 cost table, plus additional
  per-modality breakdown fields (`input_tokens_by_modality`,
  `model_invocation_token_counts`) not used by the mapping but preserved
  verbatim in `raw`. `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py`'s
  `_load_vlm_config` also gained a `"gemini"` branch (`GeminiBackendConfig(**backend_raw)`)
  so the `vlm.gemini` config block resolves through the production path, not
  only through direct `build_backend` calls. Full design rationale, the
  request/response schema, and the reproducibility/confound discussion:
  `docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`
  (Rev 3).
- **2026-09-18** — **Gemini Robotics-ER 2 probe run live on the VM: §7 gate
  PASSED.** Supersedes the "not yet run against a live key" line in the
  entry directly below. `scripts/probe_gemini_er2.py` ran inside container
  `vgu_ros` on `vgu-canary-base-isaac-workstation-vm`
  (`sudo docker exec -w /ws vgu_ros bash -lc "set -a && source /ws/.env &&
  set +a && python3 scripts/probe_gemini_er2.py --schema --thinking-level
  low"`; key sourced from `/home/ubuntu/vgu-vlm-swarm/.env` so it never
  reached argv; `x-goog-api-key` worked on the first attempt, no bearer
  fallback needed). The probe's repo search found a real committed-on-VM
  frame, `data/logs/m5_frames/0cad824071954e21832da19a6fcb588b.png`
  (`data/logs/` is git-ignored, hence "no image found" on a fresh checkout);
  no placeholder was synthesized. **Both** conditions passed: `--schema
  --thinking-level low` (HTTP 200, 3562 ms, 2166 total tokens: input 1907 /
  output 88 / thought 171) and `--no-schema --thinking-level low` (HTTP 200,
  2605 ms, 2194 total tokens: input 1907 / output 85 / thought 202) each
  returned a payload satisfying `reasoning/schemas/vlm_decision.schema.json`
  and passed both `parse_decision_text` (tolerant) and `parse_vlm_decision`
  (strict): `congestion_detected=false, type=none, strategy=none` on the
  probe's hardcoded robots (1.00 m apart, prompt threshold 0.5 m) — the
  textually correct answer, though the states are synthetic against a
  real-but-arbitrary scene frame, so this is schema conformance and
  threshold arithmetic, not demonstrated image grounding (one sample per
  condition). **New confound:** both responses billed `total_thought_tokens`
  (171 / 202) but returned **no visible `<think>…</think>` block** at all —
  ER-2 withholds its reasoning trace regardless of `response_format`,
  breaking trace-level comparability with the `llama_server`/Cosmos arm's
  visible-trace design (`llama_server_backend.py` deliberately omits
  `response_format` to preserve that trace); untested candidate mitigation
  `generation_config.thinking_summaries`
  (<https://ai.google.dev/api/interactions-api>). **Measured cost:**
  ≈$0.0032/analysis at standard pricing from Result 1's counts (both probe
  calls actually ran free tier, $0.00), roughly half the project's measured
  ≈$0.006/analysis for `gpt-4o`; latency 2.6–3.6 s. Full evidence,
  reproduction recipe, limitation discussion, and updated cost arithmetic:
  `docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`
  (rev 2, "Gate result and open questions" + "Cost"). Backend code
  (`reasoning/vlm/gemini_backend.py`, `backend_factory.py`,
  `config/models.yaml`) remains untouched: passing the gate does not by
  itself authorize landing the backend, which stays pending the user's
  decision on research design.
- **2026-09-18** — **Gemini Robotics-ER 2 evaluated as a candidate third Arm A
  backend; gated on a probe, not landed.** The page originally proposed for
  this evaluation (`ai.google.dev/gemini-api/docs/generate-content/robotics-spatial`)
  is marked "(Legacy)"; the live transport is the **Interactions API**
  (`POST https://generativelanguage.googleapis.com/v1beta/interactions`), not
  `:generateContent` — request field `input` (Content items, not a
  `messages`/`role` list), response text at `steps[].content[].text`, no
  `messages`. Target model `gemini-robotics-er-2-preview` (the
  `-streaming-preview` Live API variant does not support structured output;
  `-er-1.6-preview` is being shut down end of August 2026). **Key finding:**
  `generation_config` has no `temperature`/`top_p`/`top_k` field at all — not
  merely unsupported values, absent from the schema — so this backend cannot
  be pinned to greedy decoding the way `openai` is (`config/models.yaml`
  `temperature: 0.0`, pinned after run 3's `|Δθ| ≈ π` diverging-robots
  misread, rev-8 spec 8.4). Nearest controls are `seed` and `thinking_level`
  (low/high), a new ablation axis with no counterpart in `openai`/`llama_server`.
  Noted in passing: `anthropic` (`reasoning/vlm/anthropic_backend.py`) already
  drops `temperature`/`top_p`/`top_k` for the same reason (HTTP 400) and is
  **not** in the parent spec's "Model and decoding pre-registration" table —
  an existing, unrecorded between-arm confound that a `gemini` cell must not
  repeat. Design doc (full transport delta table, Option A backend sketch,
  Option B spatial-primitives-as-grounding deferral, cost estimate):
  `docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md`.
  Gate: `scripts/probe_gemini_er2.py` (real M2 prompt + schema
  `response_format` against the live API) must pass before
  `reasoning/vlm/gemini_backend.py`/`backend_factory.py`/`config/models.yaml`
  are touched; not yet run against a live key as of this entry — superseded
  by 2026-09-18 entry above (probe run live on the VM, gate PASSED).
- **2026-09-17** — **Research-readiness items 2–4 landed.** (2) The derived
  pairwise-geometry lines are a switchable modality
  (`ReasonerRequest.include_pairwise_geometry`, M5 `prompt_pairwise_geometry`,
  default on) and an ablation axis — rev-8 spec 8.5, module-2 FR2.1.7
  (`feat: derived pairwise geometry becomes a switchable prompt modality`).
  (3) Measurement plumbing (`feat: artifacts carry run/session ids, rendered
  prompt, scene; 1 Hz scene log`): every decision artifact now records
  `run_id` (from `VGU_RUN_ID`, exported by the launch scripts as the STAMP),
  `session_id` (per M5 process), the rendered prompt with SHA-256 hashes
  (rebuilt by the pure prompt builder; a re-ask suffix on retry is not
  captured), the M1 `scene` snapshot the request came from, and the detector's
  `distance_to_goal_m`; the request is now built on the callback thread so the
  artifact records exactly what was sent. M5 also writes one scene snapshot
  per second to `data/logs/m5_scene/<session_id>.jsonl` (`scene_log_dir`,
  `scene_log_period_sec`). (4) Investigation report:
  `docs/reports/2026-09-17-failure-attribution-ladder.md`. Host check for (3)
  done (run 6, 16:38–16:48 UTC, unrecorded): artifact `6bbcadbb…` carries
  `run_id=20260917_163714`, `session_id`, the rendered prompt (3 597 chars,
  both hashes), the scene with both robots and `distance_to_goal_m`; scene log
  `data/logs/m5_scene/c76c9c10….jsonl` had 493 lines after ~8 min (≈ 1 Hz).
  Aside: this run's onset differed (first analysis 9 min in, `bottleneck/
  reroute` on robot_1 at 3.7 m from goal) — the run-to-run variance the paired
  design exists for; stopped right after the check.
- **2026-09-17** — **Run 5 (recorded) confirms fix A: silence once parked.**
  Same stack, 11:02–11:15 UTC. M4 reported `base goal reached` for robot_2 at
  11:06:08 and robot_1 at 11:08:11; M5 logged `arrived at base goal` for both.
  5 analyses in total: the initial `deadlock/yield` (distances 2.61/2.63 m),
  then four `none` answers on robot_1 alone while it was genuinely slow in
  the gap (`distance_to_goal_m` 3.82 → 3.46), and **none at all after
  11:08:11** — seven minutes where run 4 made ~25 needless gpt-4o calls.
  robot_2 was never analysed after its arrival. Ground truth at the end:
  0.09 / 0.04 m from goals, 4.9 m apart. Runs 3 → 4 → 5: 12 → 32 → 5
  analyses, 11 → 1 → 1 dispatches. Fix C was not exercised (no false
  deadlock to refuse after fix B). Video + timeline:
  `data/logs/recordings/2026-09-17/run5_failure_context_annotated.mp4`,
  `README_run5_after_fixes_a_c.md` (git-ignored; logs and segments on the VM
  host under `data/logs/fc_check_20260917/run5_*`). Side note: 2 682
  `trigger suppressed … frame_ready=True` lines during the yield (the detector
  fires at frame rate while robots are busy/cooling down — pre-existing log
  noise, harmless).
- **2026-09-17** — **Fixes A and C landed** (`feat: arrived signal from M4
  excuses parked robots from stall evidence`, `fix: refuse reverse when both
  robots are past the corridor on one side`). C: M3 now refuses `reverse` under
  the same rule as the yield refusal — both robots past the corridor mouth on
  one side → `temporary_wait` for both with `requested_strategy: reverse`
  (shared helper `_beyond_corridor_same_side`; run-3 positions −1.22/−2.46 are
  the test case). A: M4's coordination client publishes
  `CoordinationStatus(command_id="base_mission", status="COMPLETED")` when
  Nav2 reports a base goal reached (module-4 README); M5 routes it to
  `CongestionDetector.mark_arrived`, which excuses the robot from stall
  evidence while M1 keeps it within `arrived_radius_m` (0.5 m,
  `orchestrator.yaml`) of that goal (module-5 FR5.1.8); `CongestionEvent.
  distance_to_goal_m` + the `starting analysis` log now show M1's distance
  per stalled robot. Host check: run 5 (recorded) pending — expect no
  analyses once both robots are parked, and the logged distances to reveal
  M1's offset at the goals.
- **2026-09-17** — **Run 4 (recorded) confirms fix B: no mid-scenario
  re-approach.** Same stack, 10:33–10:47 UTC, gpt-4o at temperature 0.0 with
  the pairwise-geometry prompt. 32 analyses, **1 dispatch** (the initial
  `deadlock/yield` at 10:34:39), **31 `congestion_detected=false`** — including
  the three attached re-analyses right after the yield completed (10:37:36,
  10:37:54, 10:38:13), the exact point where run 3 flipped to `deadlock/
  reverse`. Ground truth at the end: robot_1 0.08 m and robot_2 0.04 m from
  their goals, 4.9 m apart. Video + timeline:
  `data/logs/recordings/2026-09-17/run4_failure_context_annotated.mp4`,
  `README_run4_after_fix_b.md` (git-ignored; logs and segments on the VM host
  under `data/logs/fc_check_20260917/run4_*`). Still open: the detector
  re-fired `2 robot(s) stalled` every cooldown on two parked robots for 9 min
  (31 gpt-4o calls answering `none`) — fix A; and fix C as a safety net.
- **2026-09-17** — **Root cause of the mid-scenario re-approach (runs 1–3):
  M5-induced.** Evidence (run 3 ground truth + frames + M4 log): the first
  yield resolves correctly and robot_2 reaches its goal (`Goal succeeded`
  09:50:11, GT 0.04 m). Then (1) the detector re-fires `2 robot(s) stalled`
  every cooldown — robot_1 legitimately (Nav2 progress failures in the 0.7 m
  gap, 4 recoveries 09:48–09:51), robot_2 spuriously although parked at its
  goal (M1's camera estimate must exceed `goal_reached_tolerance_m` 0.15;
  unverifiable — scene_state is not logged); (2) on the same scene the VLM
  answered `none` twice (09:50:17, 09:50:37) then `deadlock/reverse`
  (09:50:56, `parse=invalid` re-ask) with "stopped and facing opposite
  directions" — the robots were 1.1 m apart and heading AWAY from each other,
  which the prompt's `|Δθ| ≈ π` heuristic could not distinguish from head-on;
  temperature 0.6 made the flip stochastic; (3) M3 grounded `reverse` for
  both with no guard for a robot at its goal, M4 executed it (09:51:00), and
  robot_2 backed east into the aisle mouth: GT 0.39 m at sim 120–155 s, a
  self-inflicted deadlock that seeded the yield/reverse alternation (robot_1
  ended at x = −5.3). **Fix B landed** (`feat: pairwise geometry and
  facing-based head-on definition in the prompt`, `feat: per-backend reasoner
  sampling override; gpt-4o samples greedily`): the prompt now states each
  pair's distance and mutual facing (60° cone) and defines head-on as facing
  + ≤ 0.5 m (module-2 FR2.1.7); `openai` samples at 0.0 via
  `vlm.openai.reasoner` in `config/models.yaml` while Cosmos keeps its preset
  (FR2.2.3; rev-8 spec 8.4). Not yet done: fix C (grounding guard: never back
  up a robot at its goal / past the corridor) and fix A (arrived = M4 goal
  status, log detector distances). Host check: run 4 (recorded) in progress.
- **2026-09-17** — **Run 3, recorded: degraded-yield wording verified live.**
  Same stack, 09:46–09:59 UTC, `scripts/record_topic_video.py` on
  `/perception/annotated_frame` (8.7 Hz stamped, 3.5 fps achieved under load →
  re-timed with ffmpeg); video and event timeline at
  `data/logs/recordings/2026-09-17/run3_failure_context_annotated.mp4` +
  `README_run3_failure_context.md` (git-ignored; raw segments and logs on the
  VM host under `data/logs/fc_check_20260917/run3_*`). 12 decisions, 2 `none`
  right after the first yield completed (09:50:17, 09:50:37 — the rev-8.3
  advice), then yield/reverse alternation on genuine re-stalls (`close/slow`
  triggers 09:53:01, 09:56:59). M3 refused two yields (both robots past the
  corridor), and the next blocks read `"yield completed 18 s ago (executed as
  temporary_wait); …"` (09:53:01, 09:58:44 attaches; artifact justification:
  "Previous yield strategy was ineffective") — supersedes the "unit-tested
  only" caveat in the run-2 entry below.
- **2026-09-17** — **Run 2 with the rev-8.3 block: the memoryful VLM now
  answers `none`** (08:20–09:32 UTC, same run-H stack, gpt-4o; logs on the VM
  host under `data/logs/fc_check_20260917/run2_*`). 91 analyses, 43 with
  `failure_context`, **58 `congestion_detected=false` (64 %) vs 2 of 16 in
  run 1**; 23 dispatches; both robots ended at their goals (GT 0.06 / 0.07 m
  from goal). First yield completed 08:24, then three consecutive attached
  re-analyses (08:25:11/30/51, `strategy=yield executed=yield`) answered
  `none`, and the memory expired; later `none` answers with a reroute context
  attached read e.g. "Robots are significantly apart with no opposing headings
  or physical conflict" (08:36–08:37 artifacts). Strategy rotation
  still occurred mid-run (yield/reverse alternation 08:4x–09:0x while the
  robots re-stalled), so the closing-advice change reduces but does not
  remove post-resolution intervention. Defect found and fixed (`fix: name the
  executed maneuver by the decided strategy's own action`): a `reroute` fans
  out as `reroute` + `temporary_wait`, which the first summarizer labelled
  `mixed`, so three blocks read "reroute completed … (executed as mixed)";
  `summarize_executed_strategy(actions, strategy)` now names the decided
  strategy whenever its own action ran (unit-tested; label change not re-run
  on the host). No M3-degraded yield occurred this run, so the "(executed as
  temporary_wait)" wording is unit-tested only. Gotchas: `run_simulation
  --duration-sec 900` did not stop Isaac (GT sim time reached 1 608 s;
  stopped by hand); with both robots parked at their goals M5 still fired
  `1 robot(s) stalled` for robot_1 every cooldown — M1's camera estimate of
  distance-to-goal sits outside `goal_reached_tolerance_m` (0.15) where GT
  says 0.06 — worth a look before Arm A/B collection.
- **2026-09-17** — **Previous-attempt block: executed maneuver + explicit
  `none` option** (`feat: report the executed strategy in the previous-attempt
  block`, `feat: previous-attempt advice names congestion_detected=false`;
  rev-8 spec 8.3, design rev 3). `AttemptRecord.executed_strategy` is derived
  from the fanned-out action names (`summarize_executed_strategy`) and, when it
  differs from the decided strategy, `failure_detail` reads e.g. `"yield
  completed 15 s ago (executed as temporary_wait); …"`; the block's closing
  advice now says to report `congestion_detected=false` when the congestion is
  gone. **Why:** the entry below — M3-degraded yields were told to the VLM as
  "yield completed", and the memoryful model rotated strategies on stalls that
  were no longer congestion. Host check pending (next entry).
- **2026-09-17** — **Failure-context attach verified on the VM** (run
  07:03–07:24 UTC, `localization:=camera` stack, gpt-4o; logs on the VM host
  under `data/logs/fc_check_20260917/`). First decision 07:03:57
  `deadlock/yield` (artifact `d012f061…`, `failure_context: null`) →
  `COMPLETED` 07:06:36 → **natural** re-detection 07:06:52 (`2 robot(s)
  stalled`) → M5 logged `failure_context attached command=…-yield
  strategy=yield outcome=completed` → artifact `52b76ea6…` carries
  `failure_context = {strategy: yield, yield_robot: robot_1, outcome_status:
  completed, failure_detail: "yield completed 15 s ago; congestion re-detected
  for the same robots"}` and the decision changed to `deadlock/reverse`. Over
  the run: 16 decisions, 15 with context attached, all `parse_status=valid`
  (one `invalid` recovered by re-ask), 2.1–6.0 s latency; the model cites the
  block in its justifications ("The previous 'yield' strategy did not resolve
  the issue, so 'reverse' is recommended" — `7501e9ff…`, also `6583a8ba…`,
  `ff81d9d3…`, `9b37ef9c…`, `3118df9d…`). Manual
  `/orchestrator/trigger_analysis` calls were all rejected `suppressed`
  because a command was always active; the natural path covered the check.
  This closes the "host check pending" item in the entry below. Two
  observations for the experiment, not defects of the mechanism: (1) the
  memoryful VLM alternated yield/reverse across 14 cycles on post-resolution
  stalls of robots ~6.5 m apart (ground truth 07:22: robot_2 overshot its goal
  by 2.1 m after a `reroute`), answering `none` only twice — RQ5's measurable
  behaviour; the `failure_context_window_sec: 0` ablation is the control.
  (2) `AttemptMemory` records the decision's strategy, so a yield that M3
  degraded to `temporary_wait` (`yield_robot: null`) is still reported to the
  VLM as "yield completed" — recording the grounded strategy would be more
  faithful; open item. Also visible now: `resolved status=` logs 3–5× per
  command because `_on_status` re-enters `_resolve_command` on every status
  message once the command is terminal (pre-existing; harmless).
- **2026-09-17** — **Previous-attempt context on re-analysis** (commits
  `feat: add FailureContext and ReasonerRequest.failure_context` through
  `feat: M5 attaches previous-attempt context on re-analysis`). M5 records
  each dispatched attempt (`strategy`, `yield_robot` = the robot whose
  fanned-out action is `yield`), finalizes it on resolution with
  `timed_out > failed > completed` precedence, and attaches it to the next
  `ReasonerRequest` for overlapping robots inside `failure_context_window_sec`
  (default 60 s; must exceed cooldown + stall threshold = 27 s, enforced at
  config load; 0 = off). The prompt gains a "Previous attempt in this episode"
  block; the artifact gains `failure_context`. **Why:** runs G/H re-derived
  every cooldown with no memory (rev-8 A.1, run 12). Host check pending: force
  a re-analysis via `/orchestrator/trigger_analysis` inside the window and
  confirm `failure_context != null` in the artifact.
- **2026-09-17** — **Robots within goal tolerance are excluded from stall
  detection.** `CongestionDetector.update` now skips a robot whose
  distance-to-goal ≤ `goal_reached_tolerance_m` (new `OrchestratorConfig`
  field, default 0.15; `orchestrator.yaml`), clearing its stall
  bookkeeping the same way STALE robots are handled; the close/slow-pair
  rule is untouched (two robots jammed at a goal still trigger).
  **Why:** an arrived robot is stationary by definition and read as
  `stalled ≥ 12 s` forever; in runs C, D, G and H that re-triggered
  analyses every cooldown on parked robots, and in G and H gpt-4o
  eventually answered deadlock/yield for two robots sitting at their
  goals, pulling one off its goal. Spec: module5 FR5.1.7. Host check
  pending (M5 should stay idle with both robots parked at ±2.5).
- **2026-09-16** — **Yield refused when both robots are past the corridor
  on the same side.** In the geometry-aware path, if
  `|yielder − center| > half_length` and `|passer − center| > half_length`
  with the same sign, the grounder emits `temporary_wait` (8 s,
  `requested_strategy: yield`, reason string) for every involved robot
  instead of a yield — the "park on the yielder's own side" rule would
  otherwise pick the far side and reverse the yielder through the whole
  corridor with backup/escort at their clamps (observed in run C after
  localization failed and M5 re-triggered). No-geometry and inside/
  straddling cases unchanged; `command_id` keeps the `-yield` suffix like
  the other degraded strategies. `expected_resolution_time_sec` is 8.0 for
  the refused case. Not yet exercised live (the trigger needs a
  post-resolution re-detection).
- **2026-09-16** — **Yield sizing derived from declared scene geometry**
  (`8cfb186`). Supersedes the constant-based sizing in the two entries
  below: `PARK_ABS_X_M` (1.8), `pull_off_lateral_m` (0.35) and
  `PASSER_CLEARANCE_M` (0.65) remain only as the no-geometry fallback.
  M5 now loads a `scenario_geometry` block from `orchestrator.yaml`
  (corridor axis/centre/half-length 1.0, aisle half-width 0.6, occluder
  height 0.9, camera 3.0, marker 0.21, robot half-width 0.09, marker
  half-size 0.06, safety radius 0.45, margins 0.3/0.15/0.2) and the
  pipeline passes it to `ground_reasoner_result(…, geometry=…)`.
  `reasoning/rag/scene_geometry.py` derives: visibility boundary
  = half_length·(cam−marker)/(cam−occluder) = 1.329; park offset =
  boundary + marker half + park margin = **1.689**; side-step =
  aisle half − robot half − wall margin = **0.36**; passer clearance =
  safety radius + margin = 0.65. The grounder works along the declared
  corridor axis (x or y) relative to `center_m`, emits `park_axis` and
  `park_coord_m` (and `park_x_m` when the axis is x), and its
  already-parked test is centre-relative (the old `park_x < 0` test
  silently assumed a corridor at 0). **Why:** the constants were
  scenario knowledge hidden in M3; the derivation makes the dependence
  explicit and lets another scenario declare different geometry instead
  of retuning code. The head_on park offset moves 1.80 → 1.69 m (still
  0.36 m outside the projected silhouette).
  **Verified live (run A, 09:47–09:52 UTC, gpt-4o):** dispatched yield
  carried `park_axis x, park_coord_m = park_x_m = −1.689,
  pull_off_lateral_m 0.36, backup 1.678, escort = clear 2.477` — every
  value reproducible from the standoff (backup = |−0.011 + 1.689|; escort
  ⇒ passer at 0.138 vs GT 0.119). Yielder parked at GT x −1.668 (2 cm from
  target); both robots resumed to their ±2.5 goals; 1 777 tokens, no
  errors. **But** with the 0.3 m margin the yielder had one **7.6 s
  detection blackout** starting 0.3 s before hold start (right after the
  side-step) plus ~5 % scattered misses while parked — versus 1.6 % /
  0.86 s max at the 1.8 m park (run 8) and minutes-long loss at 1.47 m
  (run 7). Monotonic in margin across three distances: the rendered block
  edge is softer than the geometric projection, and 7.6 s exceeds
  `stale_after_sec 3.0`. `park_margin_m` raised 0.3 → 0.4 (park ≈ 1.789,
  the distance verified clean), keeping the derivation; the margin is now
  documented as empirical.
  The geometry block must be kept in sync with
  `isaac/config/scenarios/head_on_deadlock.yaml`, `isaac/config/warehouse.yaml`
  and `CameraConfig` by hand until M5 reads the scenario file.
- **2026-09-16** — **Yield grounding is now scene-aware** (`039d92e`).
  `ground_reasoner_result(result, robot_positions=...)` takes the robots'
  world (x, y) — the pipeline passes them from `request.robot_states`, one
  hop from `SceneSnapshot.robots` — and, for `yield`, parks the yielder at
  `park_x = ∓PARK_ABS_X_M` (1.5 m; its own side, away from the passer) with
  `backup = clamp(|yielder_x − park_x|, 0.3, 2.5)` and
  `escort = passer_clear = clamp(|passer_x − park_x| + 0.65, 0.5, 4.0)`
  (0.45 m safety radius + 0.2 m). `park_x_m` is emitted in the params for
  traceability. Without positions the old 1.3 m / 2.4 m constants remain as
  the fallback, so `reverse` and all prior tests are unchanged. **Why:**
  the fixed distances were sized for one standoff position; onset is
  bimodal (run 4 stall at ~1 m vs run 6 standoff at ~0.1 m), and the
  fixed park spot sat in the 0.9 m barrier's camera shadow (see run 6
  finding below). 1.5 m clears the block top by ≥ 0.24 m for any y.
  Base goals also moved ±3.0 → ±2.5 (`orchestrator.yaml`,
  `head_on_deadlock.yaml`): ±3.0 is the ROI edge (`roi_width_m 6.0`), so a
  robot at its goal was half off-frame. Goal spheres are baked into the
  scenario USD, so this needs `build_scenario` on the sim host. `GroundFn`
  became a `Protocol` to express the keyword. 11 new unit tests; suite
  failures unchanged from the pre-existing 21.
  **Live verification (run 7, 07:32–07:38 UTC, gpt-4o):** grounded from
  the real standoff — `park_x_m −1.5`, `backup 1.528` (yielder at x≈+0.03),
  `escort = passer_clear 2.287` (passer at ≈+0.14; M1 read 0.143). Yielder
  parked at world ≈ −1.47 (odom), passer escorted 2.291 m then Nav2 to
  −2.5; **both robots reached their ±2.5 goals and were detected there
  (`STOPPED`, not `STALE`)** — the ROI change works, and it is the first
  run in which the yielder completed its mission afterwards rather than
  looping in DWB recovery (runs 4, 6). gpt-4o: deadlock/yield, 1 743
  tokens, 5.5 s; 9 post-resolution analyses all `congestion_detected=false`.
  **Open defect:** at the poll nearest `COMPLETED`, M1 reported
  `markers_detected: 1, ids_missing: ["robot_1"]` — the yielder was
  undetected while parked at ≈(−1.47, +0.35). The barrier-occlusion model
  does **not** explain this pose (the camera ray crosses x = −1 at y ≈ 0.24,
  over the corridor gap, at z ≈ 1.1 m), so occlusion by the 0.9 m blocks is
  at most a partial explanation of run 6 and not the mechanism here. Common
  factor across runs 6/7 is the +0.35 m lateral offset near the corridor
  mouth; spawn (−1.5, 0) and the goals are detected.
  **Resolved by static render probe (same day):** rendering the stage with
  robot_1 placed at five poses and running `cv2.aruco` on each frame:
  spawn (−1.5, 0) ✓, parked (−1.47, +0.35) ✓, mirror (−1.47, −0.35) ✓,
  parked facing +y ✓, but (−1.20, +0.35) ✗ — the block covers all but a
  sliver. In the (−1.47, +0.35) crop the marker sits flush against the
  block's projected silhouette. The correct occlusion model is the block's
  *projected footprint on the marker plane*, not the ray to the marker
  centre: the block top (z = 0.9) projects to |x| ≈ 1.0·(3−0.21)/(3−0.9)
  ≈ 1.33 and |y| ≥ 0.275·1.329 ≈ 0.37, so a 0.12 m marker centred at
  |x| = 1.47 has ~0.08 m of clearance — inside the odometry error of a
  1.5 m reverse plus a turn-drive-turn sidestep, and inside anti-aliasing
  flicker at the silhouette. Fix: `PARK_ABS_X_M` 1.5 → 1.8
  (= 1.33 + 0.06 half-width + 0.3 margin). Downstream still fits: worst-case
  backup ≈ 2.4 (< 2.5 cap), escort ≈ 3.04 (< 4.0 cap, < 45 s hold), passer
  parks at ≈ −2.45 (goal −2.5).
  **Verified live (run 8, 08:11–08:17 UTC, gpt-4o):** yield params
  `park_x_m −1.8, backup 1.697, escort = clear 2.466` (yielder at −0.103);
  yielder parked at world (−1.785, +0.361), passer escorted 2.468 m; both
  `COMPLETED` at T+2 m 28 s; both robots reached their goals. A continuous
  `/perception/status` recording (4 022 msgs over the 5.5 min window,
  `dropped_frame` never true) shows **robot_1 missing in 13 of 835 frames
  (1.6 %) while parked, longest gap 0.86 s** — versus minutes-long loss in
  run 6 and a miss at the only sample in run 7. The occlusion defect is
  closed. What remains is detection flicker on *moving* robots: 483/4 022
  frames (12 %) miss one marker, max gap 1.5 s; robot_1's three longest
  gaps (1.30 / 1.02 / 0.90 s) all fall inside the turn-drive-turn sidestep,
  robot_2's 65 gaps (max 0.59 s) all inside its escort. All gaps are under
  `stale_after_sec: 3.0`, so none reached M5 as STALE. One frame reported
  `ids_unexpected: ['robot_41']` (a spurious id-41 detection), handled by
  M1's unexpected-id path. Safety monitor latched both robots at the
  standoff before dispatch and released for the backup, as designed.
- **2026-09-16** — **First live-VLM closed loop on the new VM** (run 6,
  06:27–06:33 UTC, `reasoning_backend_id: openai`, `gpt-4o-2024-08-06`):
  one analysis (`2 robot(s) close/slow >= 12.0s`) → decision
  `type=deadlock, strategy=yield, involved=[robot_1, robot_2]`,
  `parse_status=valid`, 1 attempt, 4.5 s latency, 1 814 tokens (≈ $0.006) →
  dispatch → M4 yield/temporary_wait → `COMPLETED` both at T+2 m 16 s →
  robot_2 reached its goal (odom 4.415 m ≈ run 4's 4.43). Zero backend
  errors. Artifact: `data/logs/m5_decisions/9fa91fded10c41a5ab3d0764077ec8d2.json`
  (on the VM). The model's `<think>` trace is sound: pairwise distance from
  M1 positions (0.12 m), opposing headings (Δθ ≈ π), both STALE → deadlock →
  first-listed robot yields. Findings:
  - **Scenario dynamics are not deterministic across runs.** Run 4 stalled
    at ~1 m (planner failure, single-robot stall trigger); run 6 formed a
    tight nose-to-nose standoff (M1 centres 0.12 m apart, close/slow
    trigger). Both are consistent with the new lidar visibility (see M6
    note); the experiment needs several runs to characterise the onset
    distribution before Arm A/B collection, and the congestion spec should
    admit both signatures or pin one.
  - **The yielder parks in the barrier's camera shadow.** M1 lost robot_1
    (`markers_detected: 0`, `ids_missing: [robot_1, robot_2]`) 1–3 min after
    dispatch in both runs 4 and 6. Geometry: barrier blocks are 0.90 m tall
    (`z_center 0.45, z_half 0.45`, `scenario_builder._author_aisle_barrier`)
    over x ∈ [−1, 1]; the overhead camera is at (0, 0, 3). After backing
    1.3 m and side-stepping +0.35 m the yielder sits near (−1.3, +0.35); the
    camera→marker ray crosses the block's west face at z ≈ 0.92 m (marker
    centre) and lower for the near half — partially occluded at run 6's
    pose, fully occluded (z ≈ 0.64 m) at run 4's (−1.18, 0.27). robot_2 is
    separately lost at its goal (x ≈ −2.93 is 15 px from the ROI edge). Net
    effect: M5 is blind to both robots exactly when it should confirm
    resolution or catch a re-deadlock. Options (undecided): lower the
    barrier (≈ 0.3 m keeps it a lidar wall at z = 0.172 while clearing the
    camera ray); widen the ROI; or park the yielder short of the block end.
  - Pre-flight gotcha: `/ws/.env` had `OPENAI_API_KEY= sk-…` (space after
    `=`), so `source` set the key empty and returned non-zero, which would
    have short-circuited the `set -a && source … && ros2 launch` chain.
    Fixed in place on the VM (untracked file). Worth a startup check in the
    demo script.
  - At analysis time both M1 tracks were already STALE (near-contact
    markers, the known 2026-06 behaviour), so the VLM decided on the last
    good positions. Fine here, but it means the decision input is frozen
    for the duration of any standoff.
- **2026-09-16** — **Full closed loop verified key-less on the new VM** (run 4,
  05:19–05:28 UTC): Isaac → M1 → M5 stall detection → scripted mock decision
  (`VGU_MOCK_DECISION_FILE=config/mock_decisions/head_on_yield.json`) → M3
  grounding → `dispatch` → M4 `command received ... action=yield` (robot_1)
  + `temporary_wait` (robot_2) → backup → pull-off → hold + escort → both
  `COMPLETED` → `resume base mission`. Stage durations (36 s backup, 33 s
  pull-off, 74 s escort) match the grounded 1.3 m / 0.35 m / 2.4 m at
  0.1 m/s and a ~0.35× realtime factor; robot_2 finished at map x≈−2.93
  (goal −3.0). This is the first time M3/M4 dispatch has been driven
  without a live VLM. Caveats, all observed in the same run:
  - **The trigger was not the July standoff.** No `safety stop` fired and
    `/safety/holds` stayed empty; M5 fired on `robots=['robot_2'] reason=1
    robot(s) stalled` after robot_2's planner failed (`Failed to create a
    plan from potential`) at ~1 m separation (odom: robot_1 +1.03 m,
    robot_2 +0.91 m from ±1.5 spawns). Leading hypothesis, unconfirmed: the
    newly added visual meshes make each robot visible to the other's RTX
    lidar, so Nav2 blocks earlier than the 0.45 m safety envelope. If true,
    the experiment's "deadlock" now manifests as a planner stall, not a
    nose-to-nose standoff — revalidate the congestion spec's onset
    assumptions before collecting Arm A/B runs.
  - robot_1 stuck after resume (`Failed to make progress` ×3 from
    1789536382), parked at odom (0.46, 0.34) near the wall — the open
    pull-off Nav2 recovery-loop item from 2026-07-03, reproduced.
  - M1 reported both robots `STALE` from 05:25:45 with byte-identical
    `scene_state` payloads thereafter; robot_2 at x≈−2.93 is at the ±3 m ROI
    edge, but robot_1 at x≈−1.18 was in view, so this looks like frames
    stopping rather than detection failing. Not yet diagnosed.
  - Nav2 ERROR on both robots: `inflation radius (0.070) is smaller than
    the computed inscribed radius (0.080) of your footprint`. Pre-existing
    and deliberate, not a regression: `local_costmap.inflation_radius: 0.07`
    has been set since `05ab38f` (2026-06-28) because Nav2's 0.55 m default
    is wider than the aisle; the 0.14×0.18 m footprint's inscribed radius is
    0.08, so Nav2 logs this on every launch. Safe to ignore.
  - Perception stamps ran ~9 s ahead of M5's clock (wall vs sim time);
    `frame_scene_max_skew_sec` did not block this run but worth knowing.
- **2026-09-16** — Key-less closed loop on the new VM stalls at M2 by design,
  not by fault: with `reasoning_backend_id: mock` M5 detected the standoff
  (`2 robot(s) close/slow >= 12.0s`, later `stalled >= 12.0s`), started an
  analysis every ~15 s and wrote a decision artifact each time, but every one
  ended `no dispatch stage=vlm reason=congestion_detected=false` — the mock's
  hard-coded `_DEFAULT_RESPONSE`. M4 therefore never received a command. The
  ~41k `trigger suppressed ... frame_ready=True` lines are just cooldown/busy
  gaps between those analyses, not a blocker. `build_backend("mock")` had no
  way to script a decision; a `VGU_MOCK_DECISION_FILE` hook was added so the
  loop can be exercised end-to-end without an API key (fixture:
  `config/mock_decisions/head_on_yield.json`). This supersedes the reading of
  the 2026-07-05 entry that only the openai swap remained: M3/M4 dispatch had
  never actually been driven from a mock decision.
- **2026-07-05** — M6→M1→M5→M2 closed loop runs end-to-end on the GCP/Isaac
  host with the mock backend; the only remaining swap for live reasoning is
  `backend_id: openai`, blocked on an API key.
- **2026-06-15** — Offline input-encoding ablation harness spec:
  `docs/superpowers/specs/2026-06-15-m2-input-ablation-design.md`. Rev-8 of
  the congestion spec governs live-loop modality conditions; the 06-15 doc
  remains the spec for the offline benchmark runner and encoder seam.

---

## M4 Execution & Nav2

- **2026-10-03** — **Step-7b rulings (i)/(iii)/(v): M4 race guard + CrossingChain
  gate-event logging, both additive-only.** Branch `feat/v2-step7b`, cut from
  `feat/prereg-v2-composite`. Executes
  `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` build-order step 7,
  STEP-7a OUTCOME rulings for 7b
  (`docs/reports/2026-10-02-step7a-blocker-fixes.md`); full report:
  `docs/reports/2026-10-03-step7b-oracle-freeze.md`.
  - **M4 PROTOCOL NOTE (ruling i, race guard).** 7a traced the "ordered
    release not demonstrated" finding to `BaseMissionDriver`
    (`ros2_ws/src/swarm_execution/swarm_execution/base_mission.py`) and
    `CoordinationClientNode`
    (`.../coordination_client_node.py`) — **not** `command_bus_node.py`,
    which the spec text names; recorded here as the file deviation the spec
    assumed wrongly, since the race is in the client's own cross-topic
    ordering (`/coordination/commands` vs `/coordination/status`), not the
    bus's dispatch logic. Fix: `BaseMissionDriver` now tracks, per robot,
    the latest command_id seen while already suppressed
    (`_pending_next`), so a terminal for the recorded SUPPRESSION OWNER that
    arrives after a successor command was already seen (but not yet taken,
    because ownership transfer waits for the owner's own terminal) is
    recognized as stale and promotes the successor to owner instead of
    resuming base navigation. Symmetric handling for the successor's own
    terminal arriving first. Additive-only: one new dict, the existing
    `on_command`/`on_status` return contracts unchanged, the v1
    single-command path produces byte-identical call sequences (no second
    command is ever seen while suppressed, so `_pending_next` stays empty
    throughout). `BaseMissionDriver` stays ROS2-free; log-worthy decisions
    are queued (`drain_events()`) and drained by the node after each
    `on_command`/`on_status` call, not logged from the pure driver.
  - **M4 PROTOCOL NOTE (ruling iii, gate-event logging).**
    `command_bus_node.py`'s yield-hold closures (`_admit`, `_on_passer_odom`,
    `_finish_hold`) and `crossing_chain.py`'s `ChainStep` (new `moved_m`
    field) gained sim-stamped, structured log lines
    (`crossing_chain gate_admit` / `gate_cleared` / `gate_release`) at every
    admission/release decision — state transitions only, never per
    odometry tick. `gate_release` carries an explicit
    `reason=clearance|hold_timer`: 7a's own report could not distinguish,
    from logs alone, whether the SAME attempt-3 run's hold ended via
    genuine `CrossingChain` tracking or the `hold_sec` timer backstop; this
    closes that gap for every future run, live or mock. Additive-only:
    no control-flow change, only new log lines plus one new dataclass
    field with no default (both existing construction sites updated, no
    third-party caller exists).
  - **Ruling (v).** `_last_trigger_robot_ids`
    (`ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py`)
    is now cleared at the end of every `_handle_outcome` call (closing a
    latent staleness window where a later, unrelated dispatch could read a
    leftover trigger set). A `junction_clear` resolution's LATER phases
    (`_dispatch_junction_phase`, which runs after that clear) still need
    the triggering event's robot set for `_with_plan_continue_partners`'s
    pair-scope narrowing, so it is persisted into a new
    `_trigger_robots_by_plan[plan_id]` dict at the point `_dispatch` learns
    the plan_id (before the clear), and `_with_plan_continue_partners` now
    reads that plan-bound copy instead of the transient attribute.
  - **Verification.** Full local suite, clean detached baseline at
    `cf368ec`: 63 failed / 4416 passed / 152 skipped / 3 collection errors
    (environment-specific `pxr`/API-key/USD failures, pre-existing).
    After rulings (i)/(iii)/(v): 63 failed / 4426 passed / 152 skipped / 3
    errors — failing-test-name set byte-identical to baseline (`diff`
    confirmed empty); +10 is this task's own new pins.

- **2026-09-29** — **The pair-scoped exemption and its bystander guard pass
  their first live three-robot test, and so does ordered multi-passer
  release.** Tree `6d66a0d`, T2b, mock. Evidence:
  `data/logs/vm_runs/t2b_smoke/T2B_SMOKE_SUMMARY.txt`, section "Bystander-latch
  evidence". This supersedes the entry below's "Not exercised".
  - **Bystander.** In the alternative order (`robot_1` yields; `robot_2`
    then `robot_3` pass), both seeds behave the same way.
    - The exempt set at `robot_3`'s admission is
      `robot_1+robot_2,robot_1+robot_3`.
    - The released `robot_2`, heading west, and `robot_3`'s eastbound escort
      close to 0.430 / 0.433 m (GT). `safety stop … min_distance_violation`
      then fires on the non-exempt pair about 4 s after both start moving.
    - The latch holds to the end of the run (~775 wall-s, ~38k stop lines per
      robot). No contacts.
    - The hold backstop completes the yield at +371.5 s. `robot_3`'s escort
      then FAILS on its drive timeout.
    - The exempt yielder never approached `robot_3` (≥ 0.95 m).
  - **Ordered release** (oracle, 4 runs). Each next passer's escort starts
    0.01–0.05 s after the previous passer's wait COMPLETED. The yielder
    COMPLETES with the last passer.
  - **Caveats.**
    - The exempt set is cumulative: a released passer's pair stays exempt
      until the yield ends.
    - The `released: …` provenance is only in the status message `detail`,
      never in a log line.
    - The permanent latch cuts RTF from 0.34 to ~0.285.

- **2026-09-28** — **The T2b safety slice passes its live two-robot
  regression** (run A1 `20260928_132235`, mock `head_on_yield_robot_2_once`
  on `_bshort` west, tree `3ebb7ea`; evidence
  `data/logs/vm_runs/funded_battery1/FUNDED_BATTERY1_SUMMARY.txt`, Group
  A). This supersedes the entry below's "live regression is pending".
  - **Exemption events.**
    - `exempt pairs changed pairs=robot_1+robot_2` fires when the yield goes
      ACTIVE, and `pairs=-` fires at COMPLETED. There are no other
      transitions.
    - The yielder logs `exempt=True`. The passer's `temporary_wait` logs
      `exempt=False`, so only the pair is exempt.
    - 0 `safety stop` lines fall inside the exempt window.
  - **Latch timing.**
    - The standoff latch lasted 13.2 s and began 12.8 s before the analysis
      (calibration −12.0 to −12.9). It ended 0.01 s before the exemption
      opened. No latch fired during backup, hold or escort.
    - The yield phases are +46.8 / +80.7 / +151.9 s, against
      calibration's 46.9–47.6 / 80.7–82.1 / 150.8–152.6 s.
  - **Outcome.** Both robots arrived within tolerance. The GT minimum pairwise
    distance was 0.262 m.
  - **Other live exemptions, all with 0 stops inside the window:**
    - robot_1 yields in D1 and D2b;
    - a robot_2 yield in D2;
    - a two-robot `reverse` in D2.
  - **Not exercised:** the bystander case, ordered multi-passer release and
    the first-passer guard. They wait for a T2b scenario run. (Superseded by
    the 2026-09-29 T2b entry above: the bystander case and ordered release
    are verified live; both forced arms were accepted by the first-passer
    guard, whose refusal path is still not exercised live.)
  - **M5 lag (minor, not investigated).** M5 logged `resolved` 3.0 s after
    M4's COMPLETED; it was 0.1 s in CO1.

- **2026-09-28** — **T2b safety prerequisites landed: pair-scoped clearing
  exemption (`9c38042`, `fc441d4`) and ordered hold-until-last release
  (`99f4699`, `38868d2`). Unit-tested only; the live regression is pending the
  next VM batch.** The
  user decided on 2026-09-28 to build T2b, with these two items landing and
  verifying before any wrong-order run
  (`docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`, commit
  `ae2b22c`). Both items come from
  `docs/reports/2026-09-27-three-robot-feasibility.md`.
  - **Numbering.** The decision calls these items 9 and 11. The report's
    build table numbers them #8 (pair-scoped exemption) and #10
    (hold-until-last), and its #9 is the M3 N-robot yield grounding.
  - **Pair scope.** A `yield`/`reverse` robot is now exempt only against the
    partners its own command names. A bystander keeps the distance rule and
    the STALE remembered-distance rule, and the clearing robot latches with
    it. A yield's later passers join only after every earlier passer's wait
    under the command has `COMPLETED`. Details:
    `docs/specs/module4/safety-monitor.md` §10, "Pair scope".
  - **Two-robot pins.** `test_two_robot_pair_scope_matches_robot_scope` shows
    the new evaluation equals the old one on every distance/STALE/latch/memory
    combination whenever the clearing command names both robots.
  - **One intentional flip.** A lone yield with no partner command now fails
    closed. `test_coordinating_robot_suppressed_from_safety_stop` was updated
    to dispatch the partner's wait, as production does.
  - **Ordered release.** `swarm_execution/crossing_chain.py` (pure) drives
    `command_bus_node`'s hold. Passers are admitted one at a time in
    `crossing_order`: an escorted passer is driven, an unescorted one has its
    wait released. Each passer clears on its own odometry displacement since
    admission. The yield completes only when the last passer clears.
    - A cleared non-last passer's wait completes with `released: passer
      cleared`.
    - The next unescorted passer's wait completes with `released: previous
      passer cleared`.
    - A backstop, `FAILED` or busy-reject still releases every remaining wait
      at once.
    - The full status streams of the five two-robot flows are pinned
      (`test_two_robot_*_status_stream_pinned`).
  - **M3 legacy yield with ≥ 2 passers** (the live mode). The command now
    carries every passer:
    - a linked wait per passer, with `linked_position`;
    - on the yield: `crossing_order`, from the explicit order or else the
      decision's, minus the yielder, falling back to involved order;
    - `crossing_clear_m`/`crossing_escort_m`, computed per passer as
      `|x − park| + clearance` and not clamped at `MAX_ESCORT_M`;
    - `hold_sec`, wait and resolution backstops scaled by
      Σ max(1, escort / 4.0).
    - Two-robot payloads are pinned unchanged, including under a
      `crossing_order`.
  - **First-passer guard (`38868d2`).** The pair scope trusts
    `crossing_order[0]` as the standoff partner, exempt from the start. M3
    therefore refuses a multi-passer yield whose first passer is not the
    passer nearest the yielder, or whose order cannot be checked. It returns
    the gate-style wait fan-out and never reorders. Without the guard, a
    yielder with its queued follower named first backs onto that follower,
    unguarded. Both intended T2b arms stay executable.
  - **One parser (`fc441d4`).** The monitor reads a yield's passers through
    the bus's `plan_crossing`, so the two readers cannot disagree.
  - **Open items.**
    - Derived mode still emits one `passer_clear_m`, so M4 reuses it for
      later passers.
    - `filter_command_robot_ids` does not prune `crossing_order`.
    - Two waits of one yield are never paired, so the queued-follower latch
      (report Layer 4) stands. It is the Layer 7 geometry decision.
- **2026-09-26** — **The safety monitor's coordination exemption now covers
  only `yield` and `reverse` (fix `45e55f4`; host-verified).** Mitigation 1
  of `docs/reports/2026-09-26-close-approach-analysis.md` is implemented.
  - A pair is exempt while one member's `ACTIVE` command is a clearing
    maneuver. Nav2 legs (`reroute`, `convoy`, `navigate`, `goal`,
    `priority_override`), waits (`wait`, `temporary_wait`, `stop`) and unseen
    actions keep the 0.45 m rule and the STALE fail-safe armed.
  - The action comes from `/coordination/commands`, not the command id. The
    id is `<request>-<strategy>` and is shared by all robots of a decision,
    and a refused `reverse` becomes `temporary_wait`s under `…-reverse`.
  - Terminal statuses clear a robot only for the command it is `ACTIVE` on.
    Before this change, `base_mission` statuses and busy-rejects also
    cleared it.
  - Details: `docs/specs/module4/safety-monitor.md` §10. That spec's §7 bound
    is corrected from 20 s to the 120 s wall watchdog.

  Host runs on `_bshort` west (`data/logs/vm_runs/m4fix/`):
  - **M1 (mock `reverse` → `reroute` → `yield`).** The latch fired during the
    `reroute`, 8.7 s wall after it went `ACTIVE`. The latch's cancel-all
    failed the leg. The pair was held at 0.381 m (ground truth) for 49.2 s,
    with no contact, then yielded; both robots arrived.
  - **M2 (ER-2, K-config).** The yield completed in 152.8 s wall. Both
    robots arrived `within_tolerance`, the minimum was 0.276 m, and no latch
    fired during the escort.

  Open: a leg that goes `ACTIVE` after a latch (the K1 order) is still held
  until the 120 s watchdog, because mitigation 2 is not implemented.
- **2026-09-26** — **K1/G4 close approaches root-caused: the safety
  monitor's coordination exemption, not a latch failure.** The robots were
  in nose-to-nose *contact*, not interpenetrating: the collider signed gap
  was 0.0000 ± 0.0003 m for 51.0 s (G4) and 51.6 s (K1) of sim time.
  0.076 m is 2 × the +0.038 m chassis nose offset, as in Run D. Mechanism:
  - ER-2's `reroute` grounds to `reroute {"waypoints": []}` plus a 15 s
    `temporary_wait` for the partner, and M5 injects the base goal
    (`orchestrator_node.py:545-552`).
  - Both commands go `ACTIVE`. Any `ACTIVE` member exempts the pair from the
    distance rule and from the STALE fail-safe (`safety.py:95,192,202`;
    `safety_monitor_node.py:161`).
  - The Nav2 leg drove robot_1 into its waiting partner. In K1 the exemption
    lifted a latch that had fired 0.8 s wall earlier.
  - The exemption lasted until the 120 s *wall* Nav2-leg watchdog
    (`command_bus_node.py:42-44,355-359`; max(3 × M5's 20 s, 120 s floor),
    about 46 sim-s at RTF 0.38), not the 20 s that `safety-monitor.md` §7
    claims. The `safety.yaml` `command_timeout_sec` key is loaded but ignored.

  The same pair was latched to rest at 0.27 m on approach 1 when unexempted;
  the 84 other full-speed crossings in the archive rested at ≥ 0.164 m.
  Instrumentation: `_emergency_stop` logs `safety stop …
  reason=min_distance_violation` at the 40 Hz hold rate with a hard-coded
  reason (`safety_monitor_node.py:214-218`), so K1's "5880 safety stops" is
  about 58 s of latched time, not events. Only the line at `:176` carries the
  real reason. M1 `linear_velocity` is metres per wall-second (about
  RTF × true), so the 0.2 m/s speed rule cannot fire at RTF 0.38
  (superseded by 2026-09-27 M6 entry: camera now sim-stamped).
  Recommended fix, not implemented: exempt only `yield`/`reverse`; Nav2-goal
  legs and waits must not exempt a pair. Pair it with failing Nav2 legs of
  held robots. Ranking and costs in
  `docs/reports/2026-09-26-close-approach-analysis.md`. ("Not implemented"
  is superseded by the 2026-09-26 clearing-exemption entry for the
  exemption half; failing held legs is still open.)
- **2026-09-17** — **Run H: creep-while-latched fixed and verified;
  resolution and goals on video.** Latch at GT 0.4406 m with a 0.263 m/s
  closing rate; rest 1.0 sim-s later at 0.1693 m. Over the next 100 sim-s
  (1 027 GT records) separation stayed **0.1693–0.1698 m (0.5 mm
  drift)**, both markers detected in 1 909/1 918 frames (99.5 %). One
  `cancel-all … return_code=0 goals_canceling=1` per robot, `cmd_vel
  relay hold engaged` for both, and **zero** `Received a goal, begin
  computing control effort` / `Failed to make progress` for the whole
  run (run G: dozens). Resolution: gpt-4o deadlock/yield (1 765 tokens);
  relay holds released 0.11 s after dispatch (the yielder freed for its
  backup); park achieved (−1.799, 0.371) vs commanded (−1.789, 0.36);
  escort 2.528 vs 2.527 m; both `COMPLETED`; `Goal succeeded` once each
  (robot_2 final −2.450). Recording: `data/logs/recordings/2026-09-17/
  runH_annotated.mp4` (frame numbers in its README). Two observations:
  (1) the robots stop at 0.17 m, not 0.45 — stopping distance at
  0.26 m/s closure, not creep; contact is 0.076 m, so ~9 cm of clearance
  and separated markers; raise `min_distance_m` if more margin is wanted.
  (2) Post-resolution re-trigger again: with both robots parked at their
  goals the stall detector kept firing (`stalled ≥ 12 s`), and after
  seven correct `congestion_detected=false` answers gpt-4o produced one
  spurious yield (analysis #9) that pulled robot_1 from 2.43 back to
  2.15. A robot within goal tolerance is not stalled — detector rule
  fix in progress. Sim ran at 0.349× wall.
- **2026-09-17** — **Fixes for the creep-while-latched defect (below),
  host-unverified.** (1) `99edaca` — the Isaac-side `cmd_vel` relay
  (`isaac/vgu_sim/cmd_vel_watchdog{,_node}.py`) now subscribes
  `/safety/holds` once and returns zero on `cmd_vel_safe` for any listed
  robot before the silence-timeout logic runs; malformed payloads keep the
  previous set (fail-closed); transitions logged once. Cannot stall a
  commanded backup because the safety monitor already removes
  coordinating robots from `held` at the source. Spec: safety-monitor.md
  §8, FR6.4.8 amended. (2) `5f9394a` — `Nav2Adapter.cancel()` sends a
  real cancel-all (`action_msgs/srv/CancelGoal`, zero uuid + zero stamp)
  to `/<robot>/{navigate_to_pose,follow_waypoints}/_action/cancel_goal`,
  cached per (robot, action), logging the server's `return_code` /
  `goals_canceling` or a WARNING — replacing `cancel_goals_async`, which
  does not exist on rclpy's `ActionClient` (verified against the jazzy
  source) and was silenced by a bare `except`. (3) The safety monitor
  turned out not to use `Nav2Adapter` at all: `safety_monitor_node.
  _cancel_nav2_goal` had its own copy of the same dead call and logged
  `nav2 goal cancelled` regardless — being replaced by the shared adapter
  cancel. Host check for all three: after a latch, no `Received a goal,
  begin computing control effort` for either robot, `cancel-all …
  goals_canceling=1`, `cmd_vel relay hold engaged`, and GT
  `min_pairwise_distance_m` ≥ 0.4 m for ≥ 3 min with both markers
  detected.
- **2026-09-17** — **Defect: the safety latch does not hold the robots
  still — they creep into contact while latched.** Seen by the user on
  the run-G video and confirmed frame by frame: at the latch (frame 6878)
  the robots are ~0.45 m apart with both markers detected; 47 s later
  (frame 7400), still latched and before any M5 decision, the two ArUco
  quads fully overlap and M1 shows both as `STALE`. Ground truth in run E
  showed the same: 0.354 → 0.085 m over ~36 sim-s via intermittent
  velocity blips ≤ 0.062 m/s. Every earlier "standoff" (runs 6–8, A, C,
  D) also ended at ~0.08–0.12 m — contact — so this has been the norm,
  masked because contact happened to occur before or during M5's
  decision. Consequence chain: contact ⇒ overlapping markers ⇒ M1 blind
  ⇒ VLM reasons on stale poses and the annotated frame shows a merged
  blob. **Root cause (run G Nav2 logs, both robots):** after the monitor
  logged `nav2 goal cancelled` (t = 494) no new `NavigateToPose` was ever
  received, yet `controller_server` kept executing `follow_path` —
  `Failed to make progress` → `Aborting handle` → `Received a goal, begin
  computing control effort` at t = 553 and again at t = 617 — i.e. the
  original navigation goal's behavior tree was still running and DWB kept
  nudging the robot into the obstacle at creep speed until contact. The
  cancel never happened: `Nav2Adapter.cancel()` cancels goals it did not
  send via `client.cancel_goals_async(goals_to_cancel=None)` inside a bare
  `try/except: pass`, and rclpy's `ActionClient` has no such method — the
  `AttributeError` is swallowed and "cancelled" is logged regardless. So
  the safety monitor has never been able to stop a goal issued by
  `coordination_client`. (The command bus's `cancel()` before a backup
  has the same dead branch, but its handle-based cancel of its own goals
  works, which is why yields still executed.) Publishers on
  `/robot_1/cmd_vel`: `safety_monitor_node` (zero twists),
  `collision_monitor` (relaying the still-running controller — the creep
  source), `command_bus_node` (idle). Two fixes in progress: a **real
  cancel-all** through the action's `CancelGoal` service (zero uuid + zero
  stamp), logged with the response instead of silenced; and an
  **authoritative hold in the Isaac-side `cmd_vel` relay** — any robot in
  `/safety/holds` gets zero on `cmd_vel_safe` regardless of publishers
  (coordination lift is already expressed by removal from `held`). Side
  observation from the same
  logs: in the 60 s before the latch `bt_navigator` received a "goal
  preemption request" every ~1 s — `coordination_client` is re-issuing
  the base goal continuously, restarting DWB each time; worth a look at
  `BaseMissionDriver` acceptance tracking.
- **2026-09-16** — **Run G (recorded): resolution on film under camera
  localization; two runbook fragilities.** `scripts/record_topic_video.py`
  (new; cv2 `mp4v`, one frame per message stamped at a fixed fps,
  segment files so a crash keeps earlier footage) recorded
  `/perception/annotated_frame` (8.6 Hz → 11 fps) and `/camera/image_raw`
  (5.2 Hz, only 1.7 Hz captured under load). Run F was lost to a GCE host
  `REPAIRING` event mid-yield (both MP4s truncated, `moov atom not
  found`); run G delivered: latch 16:34:54 UTC, gpt-4o deadlock/yield
  dispatched 16:36:05, robot_2 `COMPLETED` 16:40:22 and **`Goal
  succeeded` 16:46:04 on film**, robot_1 `Goal succeeded` 59 s after the
  film ends. Videos and logs under `data/logs/recordings/2026-09-16/`
  (gitignored). Two fragilities: (1) `ros2 topic pub --once` for the
  latched `/coordination/tasks` registry can exit before DDS matches M4's
  subscriber — nothing latched and the robots sat at spawn ~7 min; use
  `timeout 15 ros2 topic pub -r 1 …` (run F's `--once` worked by timing
  luck). (2) **Post-resolution re-triggering:** after the yield, M5 fired
  two more analyses while robot_1 crossed the aisle toward its goal and
  gpt-4o answered `deadlock/yield` both times although the robots were
  metres apart; the second yield `FAILED` for robot_1 (it still reached
  its goal). Same pattern as runs C/D. Not a grounding-guard case (one
  robot inside the corridor); it is a detector/VLM false-positive question
  for the Arm A/B evaluation — the VLM reasserting "deadlock" from stale
  context after a resolution is exactly the kind of error the experiment
  should measure, not suppress silently. Both publishers on the recorded
  topics are RELIABLE, not BEST_EFFORT.
- **2026-09-16** — **Run E: deadlock resolved end to end under camera
  localization; both robots reached their goals.** Stack: marker-plane
  calibration, `localization:=camera` + scenario map, geometry-derived
  yield (margin 0.4), STALE fail-safe, yield-refusal guard, fixed GT
  oracle; one live gpt-4o decision. Sequence: safety latch
  `min_distance_violation` at GT 0.443 m with both markers detected
  (before contact) → M5 `2 robot(s) close/slow` → gpt-4o deadlock/yield
  (1 835 tokens, 6.2 s) → grounded `park −1.789, backup 0.971,
  pull_off 0.36, escort = clear 1.724` → achieved park −1.804/−1.811,
  pull-off 0.368, escort 1.729 m → both `COMPLETED` → base missions
  resumed → **robot_1 at +2.419, robot_2 at −2.490, Nav2 `Goal
  succeeded` twice each, separation 4.9 m, `conflict_active false`**.
  Eleven follow-up analyses all `congestion_detected=false`. Camera
  localization vs GT during the maneuver **10.1 / 7.9 mm mean** (max 33 /
  59 mm); whole span 14.6 / 21.9 mm mean. Zero errors in M1/M4/M5.
  Observations: (1) the STALE fail-safe never fired — the min-distance
  rule alone held the latch through a 430 s marker blackout because it
  evaluates carried STALE poses (~0.14 m); why run D lost its latch is
  therefore still unexplained, and the fail-safe remains as a second
  line. (2) While latched, small `cmd_vel` blips (≤ 0.062 m/s) let the
  pair creep from 0.354 m to 0.085 m (contact) over ~36 sim-s; source
  undiagnosed — `/robot_1/cmd_vel` has four publishers (safety monitor,
  collision monitor, docking server, watchdog). (3) **Bring-up race:**
  robot_1's `global_costmap` timed out (~1.5 s) waiting for `map → odom`
  because the camera localizer publishes only after its first fix; the
  lifecycle manager aborted and Nav2 was activated by hand. Fix: seed
  the localizer with the spawn pose at startup (AMCL's `initial_pose`
  semantics) — **landed** the same day: `CameraLocalizer(initial_map_to_odom=…)`
  + node params `set_initial_pose` / `initial_pose.{x,y,yaw}` wired from
  the launch `x/y/yaw` args; valid because odometry is spawn-relative
  (identity at t = 0), so the spawn pose in map *is* `map → odom` at
  startup. The first real fix replaces the seed (logged once with
  `replaced_seed=true`); a STALE hold before any fix keeps it. Host-
  unverified. (4) M1 both-marker rate 85.7 % over the M5
  window, 83.8 % during the parked hold (per-robot split lost to a
  recorder truncation). (5) The yield-refusal guard was not exercised.
- **2026-09-16** — **Safety monitor STALE fail-safe.** `safety.py`
  `evaluate_latches` now unions a second rule onto the min-distance rule:
  a `STALE` robot keeps any latch it had, and a pair in which either
  robot is `STALE` is latched if its last *both-fresh* distance was below
  `stale_unsafe_distance_m` (default `min_distance_m + 0.15` = 0.60;
  `safety.yaml` keys `stale_pose_is_unsafe: true`,
  `stale_unsafe_distance_m: 0.6`, loaded with `.get` so an old installed
  yaml cannot throw). The distance memory is refreshed only from
  both-fresh pairs, so a carried stale pose never launders into the
  trusted datum; the existing coordination lift (a commanded backup may
  proceed) is honoured. Reason logged once per latch
  (`reason=stale_pose_unsafe`); `/safety/holds` payload unchanged.
  **Why:** run D — overlapping markers made both robots `STALE`, and the
  monitor treated them as absent while they were interpenetrating. Spec:
  `docs/specs/module4/safety-monitor.md` §7 (rev 5), which also records
  two residual blind windows: a wedged `ACTIVE` command (bounded by the
  command bus's 20 s nav2-leg watchdog) and the empty-`robots[]`
  dropped-frame path (re-latches on the next good frame). 35 safety
  tests pass. Host-unverified.
- **2026-09-16** — **Run D: camera localization verified; robots found
  interpenetrating; safety monitor blind under marker loss.** With
  `localization:=camera` (+ marker-plane calibration): M1 vs GT at spawn
  **0.96 cm / 0.41 cm** (was 12 cm); both `camera_localizer` nodes
  acquired within 1 cm of the spawn poses; Nav2 active and navigating from
  the camera TF; localization error vs GT **0.4 / 1.8 cm mean** while
  driving (N=62), **2.9 / 0.6 cm mean** during the yield (N=223), worst
  16 cm in a 509 s span that included a period of physical contact. No
  degeneracy — the held correction stays valid because odometry is
  drift-free. **Loop outcome was poor for reasons upstream of
  localization:** gpt-4o's first decision was `reverse` (both back up
  1.3 m, both resume); the robots re-approached and came to rest
  **nose-to-nose in contact (0.078 m centre distance), pressed against
  the south wall (y ≈ −0.18)**, anti-aligned (relative heading 3.145
  rad) — a live camera crop shows the two ArUco quads overlapping
  (`scratchpad/runD_live_zoom.png` of this session). With overlapping
  quads neither marker is detectable: `markers_detected == 0` in 13 449
  of 19 607 status frames, robot_1 gap 401 s, both `STALE`, so M5
  reasoned on stale poses (`temporary_wait`/anomaly, then two `yield`s;
  one FAILED), Nav2 planning failed from inside inflated wall cost
  (44 + 13 `failed to create plan`), no goal reached.
  **Collision is enforced — an earlier reading of this as
  interpenetration was wrong.** Host probe (same day): driving robot_1
  into an uncommanded robot_2 at 0.1 and 0.2 m/s pushed robot_2 by 0.57 m
  and 1.55 m, and the centre distance plateaued at 0.0760 / 0.0765 m —
  exactly nose-to-nose for this URDF (`base_link` at the wheel axle,
  chassis collision box origin x −0.032 with half-length 0.07 ⇒ front at
  +0.038 ⇒ 2 × 0.038 = 0.076 m). All five collider prims per robot have
  `collisionEnabled`, no `CollisionGroup`/`FilteredPairs` exist, no
  tunnelling at the speed limit. `min_pairwise_distance_m` is a
  centre-to-centre metric; `robot_robot_contacts` in the acceptance log is
  hard-coded `[]` (never measured — do not read it as "no contact").
  **The actual systemic findings:** (1) the 0.12 m markers are centred on
  `base_link`, 0.038 m behind the nose, so **at physical contact the two
  quads necessarily overlap and M1 loses both robots at exactly the
  physical deadlock**; the designed 0.45 m safety envelope normally stops
  robots before that, and run D reached contact only because `reverse`
  resumed both base missions into each other. Options, undecided: a
  smaller or rear-offset marker (M1 would need the offset), or accept
  the blind window and rely on the fail-safe. (2) **The safety monitor
  had no fail-safe for perception loss** — a `STALE` robot last seen 8 cm
  from another was treated as absent; fixed the same day (see the STALE
  fail-safe entry). The yield-refusal guard correctly did not fire
  (robots were inside the corridor). 4 gpt-4o calls, 7 097 tokens.
- **2026-09-16** — **`localization:=camera` added, host-unverified**
  (`4c1b697`). Third localization mode: a per-robot
  `swarm_perception/camera_localizer_node` (launched inside the namespaced
  Nav2 group; no static TF, no AMCL) turns M1's world pose into
  `map → <robot>/odom` = T_map_base ∘ T_odom_base⁻¹, where T_odom_base is
  the LATEST `odom → base_footprint` TF from Isaac (never looked up at the
  scene stamp: Isaac fills the image header with system time while TF and
  nodes run sim time; latency error ≤ 0.2 m/s × 0.1 s = 2 cm). Publishes
  at 20 Hz stamped +0.3 s (AMCL's convention) and holds the last value
  while the marker is `STALE` — valid because odometry is drift-free.
  Pure SE(2) core in `camera_localizer.py` (yaw normalised via atan2 so a
  π-heading robot does not flip sign each cycle); node importable without
  rclpy; 15 unit tests. **Why:** AMCL degenerates in this symmetric
  warehouse after the yield maneuver (run C), while the apparatus already
  has a global sensor whose pose error is 3–7 cm (now ≤ 3 cm with the
  marker-plane calibration). Prerequisite: M1 must be up before Nav2
  activates. Verification = run D.
- **2026-09-16** — **AMCL localizes to 2 cm with the scenario map (run B2);
  degenerates after the yield maneuver (run C).** With
  `localization:=amcl map_yaml:=…warehouse_map_head_on_deadlock.yaml`,
  stamp-matched error vs ground truth over the approach and standoff was
  **mean 0.022 m, max 0.052 / 0.085 m** (robot_1 N=29, robot_2 N=33;
  time alignment solved via odom↔GT with 0.3 mm residual) — on par with
  M1 (0.03–0.07 m). Nav2 planned and drove from the AMCL pose. First run
  in the project with self-localized robots. **Run C** (full loop under
  AMCL, gpt-4o): deadlock/yield, `park_coord_m −1.789`, yielder held at
  GT (−1.75, 0.37), M1 missed it in 10/790 frames (longest 0.35 s) — the
  0.4 m park margin is confirmed. But as each robot moved west of the
  barrier, its AMCL estimate jumped ~2 m in y within ~5 s (robot_1 to
  y≈−1.76 at t 426→431, robot_2 to y≈+2.15 at t 458→465) while x stayed
  right; C-window error mean 1.6 / 1.3 m. Both reported poses lie in
  **solid rack** in the map (49/49 occupied cells around them), so this is
  a degenerate filter output (split/bimodal cloud), not a relocalization
  to a look-alike place — no parallel aisle exists (at x = −2 the only free
  band is y ∈ [−0.6, 0.6]). Timing coincides with the side-step turns and
  the unmapped other robot at < 1 m. Consequences: `GridBased … failed to
  plan`, `Goal failed`, neither robot reached its goal, and M5 re-triggered
  a second analysis (2 live calls total) whose yield was nonsensical —
  both robots were now on the same side, so "park on the yielder's own
  side" flipped to `+1.789` with backup/escort at their clamps (2.5 / 4.0).
  Open items: (1) AMCL post-maneuver degeneracy — diagnose with
  `/robot_N/particle_cloud` at the jump; candidate levers `z_rand`,
  `laser_likelihood_max_dist`, `resample_interval`, `recovery_alpha_*`;
  (2) grounder guard for a re-triggered yield when no robot is inside the
  corridor extent. **Default remains `localization:=static`.**
- **2026-09-16** — **Per-scenario Nav2 map with the barrier** (`1d53053`).
  `isaac/scripts/generate_warehouse_map.py --scenario <yaml>` now
  rasterizes `aisle_barrier` with the same geometry as
  `scenario_builder._author_aisle_barrier` (blocks over x ∈ center ±
  length/2, |y| ∈ [effective/2, nominal_aisle/2]) into
  `maps/warehouse_map_<scenario>.pgm/.yaml`; the default map is untouched
  (byte-identical re-generation checked). `warehouse_map_head_on_deadlock`
  adds exactly 480 occupied cells (240 per block, purely additive; aisle
  core still free). Cell rounding puts the map corridor walls at |y| = 0.30
  vs the physical 0.275, i.e. a 0.60 m map corridor — the global planner
  gets ±0.11 m instead of ±0.085 m and now sees the barrier at plan time
  rather than only via lidar. `nav2_robot.launch.py` gains `map_yaml`
  (default: the base map) feeding the shared `map_server`;
  `run_phase3_demo.sh` passes the head_on map. **Why:** AMCL cannot
  localize against a map missing the dominant lidar feature (run B).
  Verification against AMCL pending (run B2).
- **2026-09-16** — **AMCL option executed on host (run B): mechanism
  verified, localization fails because the map lacks the barrier.**
  With `localization:=amcl` both `/robot_N/amcl` reached `active`, the
  static `map_to_odom_ground_truth` was correctly absent, AMCL published
  `map → robot_N/odom` equal to the spawn poses, params bound under the
  namespace (`base_frame_id robot_1/base_footprint`, `scan_topic
  /robot_1/scan`), Nav2 navigated from the AMCL pose, and there were
  **zero** TF/map/scan warnings — the launch/params design holds. But
  once the robots moved, stamp-matched error vs the (now correct)
  ground truth settled at 0.77–1.10 m for robot_2 (five samples, mean
  0.93) and 1.40 m for robot_1 (one sample), against M1's 0.03–0.07 m;
  robot_2's lateral error alone (~0.6 m) would place it inside the aisle
  wall. Cause found offline: `warehouse_map.pgm` was generated from
  `WarehouseConfig` on 2026-06-25 (`494cbba`), before the `aisle_barrier`
  existed; it has **0 occupied cells** in x∈[−1,1], y∈[0.275,0.6] where the
  0.90 m block is, so AMCL fits scans of 0.55 m corridor walls to a map
  that says the aisle is 1.2 m wide. Fix in progress: per-scenario map
  (`generate_warehouse_map.py --scenario`) rasterizing the barrier, and a
  `map_yaml` launch argument. Measurement gotcha for future checks:
  `/robot_N/amcl_pose` is RELIABLE + TRANSIENT_LOCAL and only updates on
  ≥ `update_min_d` motion, so `topic echo --once` returns a possibly
  minutes-old pose; compare by `header.stamp`, not sample time.
- **2026-09-16** — **`localization:=amcl` option added, host-unverified.**
  `nav2_robot.launch.py` now takes `localization:=static|amcl` (default
  `static`, behaviour unchanged). Under `amcl`, the static
  `map_to_odom_ground_truth` node is not launched; instead a namespaced
  `nav2_amcl` node (params via the same `RewrittenYaml(root_key=robot_id)`
  wrapper the vendored navigation launch uses; initial pose from the
  `x/y/yaw` args; no node-level `/tf` remaps, per the launch docstring's
  findings) plus a `lifecycle_manager_localization` managing only `amcl`.
  `nav2_params.yaml` gains an `amcl:` block: Jazzy nav2_bringup defaults
  except namespace-token frames, absolute `scan_topic`/`map_topic`
  literals (same failure class as `global_costmap.map_topic`),
  `laser_{min,max}_range` = LDS 0.12/3.5, `update_min_d/a` tightened to
  0.05 m / 0.1 rad so a short backup still triggers filter updates.
  nav2_bringup's `localization_launch.py` is deliberately not used (it
  hardcodes its own `map_server`, colliding with the shared one).
  **Why:** the static transform is a ground-truth shortcut (disclosed in
  the experiment spec, App. A.7); AMCL leaves `/odom` untouched, so M4's
  odometry-closed primitives are unaffected by this step alone. Plan,
  risks (symmetric-corridor particle flip; `xy_goal_tolerance 0.1` margin;
  M1/map alignment unverified) and the odometry-noise follow-up:
  `docs/superpowers/plans/2026-09-16-amcl-localization-plan.md`. Host
  checks still to run are listed in `docs/specs/module4/phase2-nav2-stack.md`
  (2026-09-16 section).
- **2026-09-16** — Goal coordinates verified end-to-end on the rebuilt stack:
  with `nav2_robot.launch.py` given the scenario spawns (`x:=-1.5` /
  `x:=1.5 yaw:=3.14159265`), Nav2 logged `Begin navigating from current
  location (-1.50, -0.00) to (3.00, 0.00)` for robot_1 and `(1.50, 0.00) →
  (-3.00, 0.00)` for robot_2 — map-frame pose equals the YAML spawn, goal
  equals `orchestrator.yaml`'s `initial_tasks`. Both robots then drove into
  the aisle (M1 placed robot_1 at x≈0.00; `/robot_1/odom` on a fresh run
  showed 0.8 m forward travel), met head-on, and the safety monitor latched
  `min_distance_violation` on both — the intended standoff. Two caveats:
  (1) `scripts/run_phase3_demo.sh` still hardcodes `x:=-0.6 / 0.6` (stale
  since commit `0a0604c` moved spawns to ±1.5), which would misplace
  `map→odom` by 0.9 m — do not use it unpatched. (2) `safety_monitor_node`
  emitted 58 `safety stop ... min_distance_violation` WARN lines in 0.48 s
  at latch time (alternating robots) — noisy but not yet shown to be harmful.
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

- **2026-10-02** — **Loop-map Nav2 pre-emption control smoke: PASS on both
  runs, after finding and fixing a previously-invisible `generate_warehouse_
  map.write_map()` bug** (`docs/reports/2026-10-02-loop-preemption-smoke.md`
  Rev 3, Sections 6-7; v2 build-order step 8, Phase 1). Full write-up in the
  report; summary here:
  - **Bug**: `write_map()` applied an erroneous `np.flipud` before saving
    the PGM. `nav2_map_server` loads a PGM's row 0 directly as the map's
    +y (north) edge with no additional flip of its own — the extra flip
    silently mirrored any Y-asymmetric map feature to the wrong side of
    `y=0`. Invisible on every scenario built before this one because the
    base warehouse and every existing scenario's own geometry are
    Y-symmetric about `y=0` (flipping a symmetric array is a no-op).
    First exposed by the loop map's second aisle, the first ever
    one-sided feature.
  - **Fix**: removed the flip (one line); regenerated every existing
    committed map and confirmed byte-identical (the fix is provably a
    no-op for every v1-frozen scenario); new regression tests in
    `tests/unit/test_loop_map.py` pin both the carve-lands-on-the-right-
    side property and the symmetric-map self-mirror invariant.
  - **Builder extension**: `LoopMapConfig` on `ScenarioConfig`
    (`isaac/vgu_sim/config.py`); `scenario_builder._author_loop_connectors`
    deactivates the shared NE rack block via a scenario-local USD override
    and authors 4 replacement cubes (2 at the shared 0.9 m rack height, 2
    lowered to 0.3 m specifically to keep the camera's line of sight to
    the second aisle clear — see the report's camera-occlusion model,
    Section 3); `generate_warehouse_map.rasterize_loop_map` mirrors the
    same carve into the 2D map. NW/SE/SW racks untouched; the shared
    `warehouse.usd` and default map are untouched (verified byte-identical).
  - **Live results**: positive control (`compute_path_to_pose` into the
    second aisle) SUCCEEDED on every post-fix run, proving the loop is
    genuinely navigable; the blocker run still never entered the second
    aisle (GT `max|y| = 0.224`, 0/~200 sampled plans with
    `entered_second_aisle: true`) — Nav2 pushed through the narrowed
    primary-aisle gap instead, exactly as designed. Mock decision layer
    silent on every run (0 dispatches). M1-coverage bonus probe: 100%
    fresh, 0 STALE, both robots, bias 0.006-0.008 m.
  - **Protocol note**: the `write_map()` fix and the `loop_map: null`
    addition to the 7 committed head-on-family fixtures (mechanical,
    null-field-only, from adding an optional field to `ScenarioConfig`)
    are both touches to nominally-frozen v1 artifacts, landed on
    `feat/v2-loop-map` (off `feat/prereg-v2-composite`) only, per
    relationship-to-v1 rule 2 — both verified byte-identical/safe for
    every existing v1 artifact before landing.
  - **Separate open item, not investigated**: `obstacle_in_candidate.yaml`
    (T3b)'s own Y-asymmetric static obstacle does not appear baked into
    its committed map at either its position or its mirror — unrelated to
    the flip bug (confirmed: both sides read free), flagged for the
    coordinator, out of this task's scope.

- **2026-09-28** — **`fc_launch.sh` launches one Nav2 stack per scenario
  robot, and the three-robot `t2b_flow_ordering` scenario and map exist; its
  USD build and first smoke are pending the next VM batch** (`ea02da7`,
  `4f92163`). This closes the Rev 15 §AS "four robots, two Nav2 stacks"
  launcher defect for any scenario. Two-robot launches are byte-identical
  (DRY_RUN goldens, `tests/unit/test_fc_launch_dry_run.py`).
  - Scenario edits are inert until `build_scenario` regenerates the USD on
    the VM.
  - The map, `warehouse_map_t2b_flow_ordering`, is generated from the
    scenario (1.0 m barrier) and pinned against regeneration.
  - Details and flags: the Congestion-Resolution Experiment entry of the
    same date.

- **2026-09-27** — **Timed obstacles can now be a marker-less robot, and
  the T3a pair's map decision is recorded; the real asset worked on the VM**
  (`ad379f1`, `8ee6393`; `data/logs/vm_runs/t3a_smoke/T3A_SMOKE_SUMMARY.txt`).
  - **Asset.** `TimedObstacleConfig.asset` selects the authoring:
    - `robot_visual_no_marker` references the imported robot USD with its
      `Physics` variant set to `none`. That gives no articulation, rigid
      bodies or joints; the 5 collision shapes stay as static colliders.
      No marker is authored (markers are per robot), and the prop lives
      under `/World/DynamicObstacles`, outside `validate_robot_marker`'s
      `/World/Robots`.
    - `static_box` is a grey box.
    - Any other label keeps the legacy red box, so `dynamic_anomaly*` build
      unchanged (a pxr test pins it).
    - Checked on the VM's real asset: 38 prims, 0 physics bodies,
      0 `aruco_marker`, bbox 0.25 x 0.32 x 0.35 m centred on the pose;
      `validate_simulation` PASS.
  - **Scale 1.82.** The lidar scans one plane at 0.182 m, and at scale 1 the
    only burger structure there is the 7 cm LDS head. NavFn (0.07 m
    inscribed radius) plans past that in any corridor a robot can drive, so
    the robot would never stall. At 1.82 the plane cuts the middle plate,
    about 0.25 m wide. The test re-derives this from the STL.
    - Live in W2: the first plan failure came 0.7 s after the spawn. But 4
      plans still went through in the next 3 s, so robot_1 rolled 0.5 m
      further than W1's box let it.
  - **Map decision: neither member bakes the blocker.**
    - A baked, passage-closing box leaves NavFn no path at t = 0, so robot_1
      would never leave its spawn. (The family blockers can be baked only
      because they sit behind a spawn.)
    - An unbaked `static_obstacles` box is found by the lidar at 3.5 m, so
      robot_1 would stop ~1.5 m earlier than the transient member.
    - So both blockers spawn at 16 s as timed obstacles, and the object's
      box never despawns. Only the 0.50 m corridor is baked, and the two
      maps are byte-identical. Live stop points: W1 x = -2.00, W2 x = -1.89.
  - **robot_2 placement.** The plus-shaped warehouse has one east-west
    passage, so robot_2 runs in the north pocket that the barrier seals,
    not normal_flow's westbound lane.

- **2026-09-27** — **Timed obstacles verified live (Fix 3 PASS), and T3c v2
  `dynamic_anomaly_v2` authored** (89884a3; evidence
  `data/logs/vm_runs/t3c_v2/T3C_V2_SUMMARY.txt`). Run `20260927_123505`
  (old dynamic_anomaly, RECORD=1) logged `timed obstacle event
  sim_time=8.00 ... True` / `20.00 ... False`; recorded frames show the box
  absent up to stamp 8.23, present 8.60-20.30, absent from 20.67 (render lag
  <= 0.6 s). The activated collider reaches Nav2 through the lidar: robot_2
  bent its path to y=+0.33 around it (and in the v2 smoke robot_1's planner
  failed 0.9 s after the spawn and first planned again 1.9 s after the
  despawn). Ground truth cannot show obstacles: `acceptance_logging` records
  robots only and hard-codes `robot_static_contacts: []`. **v2 design:**
  normal_flow's lanes, and one 0.3 x 1.05 x 0.5 m box at (1.5, -0.075), active
  30-110 of 200 sim-s. It covers robot_1's whole lane and leaves a 0.15 m
  strip, narrower than the robot. The plain on-lane 0.3 m box was rejected:
  Nav2 routes around it (as robot_2 did in run 123505), so M5 would never
  trigger. The spec's "window >= 60 sim-s" also cannot catch a robot on a
  5 m lane, which parks by ~45 s. Map equals the default map (the generator
  never bakes `timed_obstacles`). No oracle block yet.
  **Gotchas:**
  - Robots stop where the plan first fails (1.4 m short of the box), not at
    the box.
  - Departure time jitters: ~10.6 s in T0, ~14.5 s in the v2 smoke.
  - After the despawn, robot_1 paused ~18 s at x=1.15 until the controller's
    "Failed to make progress" abort. The probable cause is stale local-costmap
    marks; this is unconfirmed.
- **2026-09-27** — **Timed obstacles are now activated by the runner; live
  check pending** (c5cecaf). `runner.py` built `EventScheduler` with no
  callbacks, so both defaulted to no-ops and the deactivated
  `/World/DynamicObstacles/<id>` prim was never activated: T3c smoke run
  `20260927_113513` showed an empty aisle inside the 8-20 s window
  (`data/logs/vm_runs/t0_t3c_verify/VERIFY_SUMMARY.txt`, F-T3c-1). Every
  earlier dynamic_anomaly run had no obstacle. No new USD authoring was
  needed: `scenario_builder._author_obstacle` already authors the collidable
  box and `SetActive(False)` for the runner to reactivate. The new
  `event_scheduler.prim_activation_callbacks` toggle `SetActive(True/False)`
  on a stage fetched at event time, because `SimulationContext.reset()`
  reloads the stage after the scheduler is built. A missing prim raises, so
  it becomes the run's `failure` rather than a silent no-op. The runner
  prints `timed obstacle event sim_time=... active={...}` per spawn/remove,
  and `scheduler.reset()` in `finally` is guarded so it cannot skip the
  manifest. Unit-tested against a fake stage (`tests/unit/test_m6_event_scheduler.py`).
  **Pending live:** whether a collider activated mid-run is picked up by the
  physics backend, the RTX lidars (Nav2 costmaps) and the camera render.
  Check the Isaac log line, and the camera/recording frames at x=1.5 inside
  the window. F-T3c-2/5/6 (ROI-edge spawns, window timing, head-on geometry)
  still block usable T3c data.
- **2026-09-27** — **Camera frames now stamped with sim time**
  (`a1aa81d`). `useSystemTime` is `False` on both the `/camera/image_raw`
  and `/camera/camera_info` helpers (`isaac/vgu_sim/ros_graphs.py`). This
  brings the code in line with M6 FR6.6.8, which always said sim time.
  - **Why the old comment was obsolete.** It chose wall time because sim
    time stayed at 0 in the 2026-06-18 static run. The runner has since
    fixed that (`_set_timeline_window` plus `play()` + `app.update()`,
    `runner.py:64-89,230-242`). `/clock`, odom and TF were already
    sim-stamped, and Nav2 runs on `use_sim_time`.
  - **Effect.** Wall stamps made M1's frame-stamp kinematics read ≈ RTF ×
    true (0.38×) (`docs/reports/2026-09-26-close-approach-analysis.md` side
    finding). The effective-threshold table is in the same-date M1 entry.
  - **Zero-timestamp check: no gating needed.** The helper's
    `IsaacSimulationGate` is keyed on sim time whatever `useSystemTime` is
    (`docs/reports/2026-06-18-m6-m2-integration-gcp-run.md`). A frame
    therefore only publishes once sim time is advancing, and
    `_wait_for_ros_topics` fails the run loudly (`_TopicTimeoutError`)
    unless a live `/camera/image_raw` sample arrives. At worst a single t=0
    frame is harmless to M1 (forward-only).
  - **USD rebuild is not needed.** The camera graphs are wired at run time
    by `runner._wire_ros_graphs` → `create_global_ros_graphs`, after
    `reset()`. `scenario_builder.py` authors only the empty
    `/World/ROSGraphs` scopes. The flip takes effect on the next run once
    the VM checkout has this code.
  - **Related comments.** Comment-only edits in `camera_localizer_node.py`
    and `nav2_robot.launch.py`, which said Isaac fills scene stamps from
    system time. The latest-TF lookup is kept.
  - **Timers unchanged.** M5's stall and command timers stay on
    `time.monotonic()` (wall). Only M1's quantities changed basis.
  - Offline guard: `tests/unit/test_m6_ros_graphs.py` (stubbed `omni`/`pxr`).
  - **Live verification pending.** Next combined VM run: M1 speeds ≈ GT sim
    speeds, status sanity, stall-trigger timing.

- **2026-09-26** — **`_bshort` open-side passer goal widened from ±2.5 to
  ±2.6** (`dcfa144`). At ±2.5 the goal cleared the M3 escort endpoint
  (`park_offset_m` 1.789 + `passer_clearance_m` 0.65 = 2.439 m) by only
  0.061 m, under the ≈0.1 m drift `FEASIBILITY_MARGIN_M` budgets for; ±2.6
  clears it by 0.161 m (0.811 m past the park point). Blocked-side goal,
  spawns, blockers, oracle and maps unchanged; `beyond` and `_gshort`
  untouched. Constant `BLOCKED_SHORT_PASSER_GOAL_M` in
  `isaac/scripts/generate_head_on_family.py`; both `_bshort` YAML headers now
  print the margins, and a test asserts ≥ 0.15 m on both sides.
  **Operator step:** for `_bshort`, hand-set `orchestrator.yaml`
  `initial_tasks` to `[2.6, 0.0]` (west) / `[-2.6, 0.0]` (east); only the
  comment table there was updated, the live block is unchanged. **USD not rebuilt** — rebuild both `_bshort` scenario USDs on the
  VM before the next run (a stale USD keeps the old goal).

- **2026-09-26** — **`_bshort` (blocked-side goal short) fixes the west
  park-beyond-goal failure with no reintroduced blocker-path loss.** Commit
  `e708ffa`. Three-run ER-2 pilot, west variant: 3/3 position-verified
  arrivals (J1–J3), gate fired once per run, 0 refusals. Ground truth shows
  the passer's backtrack after its max x was 0.000 m in all three (versus
  0.580 m in `_gshort` H2) — the passer's goal now clears the M3 escort
  endpoint by only 0.050–0.061 m, a thin margin against ≈0.1 m drift. East
  variant built and validated, not yet run. Report
  `docs/reports/2026-09-25-overnight-findings.md` §AG–§AH; extends the
  `_gshort` pilot entry below. Margin superseded by 2026-09-26
  entry (goal widened to ±2.6).

- **2026-09-26** — **`_gshort` fixes the blocker-on-goal-path losses but
  symmetric ±1.5 goals park the yielder beyond the passer's goal.** Six-run
  ER-2 pilot at `c2d8491`: 4/6 position-verified against 2/6 on ±2.5, 0/6
  blocker-path losses. New failure: the yielder parks at `park_offset_m` =
  1.789 m, beyond the passer's goal at 1.5 m, so the arrived passer rests on
  the axis 0.437 m away — inside M4's 0.45 m — and holds it (H2, H3). East is
  3/3 and west 1/3, but that split is a race, not side-safety — the variants
  mirror. `_bshort` is the candidate fix. Container recipe now needs `pillow`;
  verify installs by `md5`, not `colcon` exit code. Report
  `docs/reports/2026-09-25-overnight-findings.md` §AD–§AF; extends the
  `_gshort` creation entry below.

- **2026-09-26** — **`_gshort` head-on variants put the blocker off every goal
  path**: `head_on_asymmetric_{w0p2_eopen,wopen_e0p2}_gshort_o0` goal on the
  opposing spawn (±1.5), not the inherited ±2.5 that lay beyond the box.
  Goal mode is a `--goal-mode` generator option, **not** a
  `HeadOnAsymmetricParams` field — a params field would rewrite the frozen v1
  `parameters:` blocks. **Operator step: set `orchestrator.yaml`
  `initial_tasks` to ±1.5 and rebuild `swarm_orchestrator`** — M5 reads goals
  from there, not the scenario YAML. Design rev 4, spec
  `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md`.

- **2026-09-25** — **New Isaac host stood up after the `summer-flux`
  project lost GPU quota.** Instance `vgu-vgu-thule-base-isaac-workstation-vm`,
  GCP project `project-355a9186-f6f8-4b89-a44`, zone `us-central1-c`
  (us-central1-a stocked out), g2-standard-8 + L4 (driver 595.84), deployed
  with Isaac Automator `--not-from-image --isaacsim v6.0.1`
  (`--from-image` needs a project-scoped image family and `--isaacsim
  latest` resolves to git `main` = 7.0.0a1 — pinned to v6.0.1, closest to
  the validated 6.0.0-rc.59). Isaac Sim source build at
  `/home/ubuntu/IsaacSim-source`, symlink `/home/ubuntu/IsaacSim`.
  `vgu_ros` container rebuilt from the 2026-09-16 recipe plus `pip3
  install --break-system-packages requests` (stock `ros:jazzy` lacks it;
  `reasoning/vlm/openai_backend.py` needs it). Full asset chain rebuilt:
  URDF import with the four ROBOTIS STLs staged next to the URDF (4
  visual meshes, `burger_base` 48 040 pts — the 2026-09-16 mesh-less
  import does not recur), `warehouse_base.usd`, all six scenario USDs,
  `validate_simulation` PASS on `head_on_deadlock` and the three
  `head_on_asymmetric` variants; headless `run_simulation` `completed:
  true`, 3 001 ground-truth records over 300 sim-s, render product `rgb
  (960,1280,4) mean=127.94` (old host 127.95). Two host facts: `pxr`
  imports only inside a `SimulationApp` (a bare `python.sh -c "from pxr
  import Usd"` fails), and each new extension set's first launch spends
  ≈5–7 min compiling shaders.
- **2026-09-25** — **`run_simulation.py --duration-sec` is a dead flag.**
  It is parsed and validated but never passed into `ResolvedRunConfig`
  (`isaac/vgu_sim/config.py` has no `duration_sec` field; the
  `ResolvedRunConfig(...)` call in `isaac/scripts/run_simulation.py`
  omits it), so the scenario YAML's `runtime.duration_sec`/`duration_sec`
  (300 s for `head_on_deadlock`) always governs. This is the root cause
  of the long-standing "`--duration-sec` does not stop Isaac" note
  (2026-09-17, M5/M2 entries above) — the flag was never wired, not
  ignored at shutdown. Not fixed (experiment night); fix = add the field
  and pass `args.duration_sec` through, with a unit test.
- **2026-09-19** — **`head_on_asymmetric` scenario family landed and
  hardware-verified.** `ScenarioConfig` gains `family` (inferred from legacy
  names, explicit for generated ones), `static_obstacles`/`ObstacleSize`, and
  `parameters`/`oracle` (`df047ae`). A pure `isaac/vgu_sim/family_oracle.py`
  computes yield feasibility from the same `reasoning.rag.scene_geometry`
  functions M3 grounds with, loaded from M5's `scenario_geometry` block
  (`2382aae`). `isaac/scripts/generate_head_on_family.py` writes the three
  committed v1 variant yamls plus `family_manifest.csv`
  (`isaac/config/scenarios/family/`) (`b6b6843`). Static and timed obstacles
  are now authored as real `UsdGeom.Cube` collision geometry
  (`_author_box`/`_author_static_obstacles`,
  `/World/Scenario/StaticObstacles/<id>`) instead of empty Xforms, dispatch
  keys on `family` not `name`, and `validate_scenario_obstacles` fails the
  build (not a later run) on a missing prim (`34686a5`). Per-scenario Nav2
  maps bake the `static_obstacles` footprint in addition to the aisle
  barrier (`539de1b`, `0583195`). Spec:
  `docs/specs/module6_simulation.md` Rev 4; design:
  `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md`
  (rev 2/3). Hardware evidence
  (`docs/reports/2026-09-18-head-on-family-validity.md`, "Validity Pairs
  (T2a)"): all four forced-yielder mock runs matched the frozen oracle —
  forced-infeasible yield `FAILED` with the robot stalled ~0.09 m (its own
  half-width) from the blocker's near face on both variants; forced-feasible
  yield `COMPLETED` with both robots arriving, mirrored east/west. The frozen
  `oracle:` block is consumed only by config validation
  (uniqueness/membership checks) — nothing in the M1–M5 runtime pipeline
  reads `correct_yielder`, so it cannot silently become part of a live Arm A
  score.
- **2026-09-16** — Simulation rebuilt and re-verified on a new host after the
  old VM was deleted: `vgu-canary-base-isaac-workstation-vm` (project
  `summer-flux-501516-n6`, us-central1-a, g2-standard-8 + L4, Isaac Sim
  6.0.0-rc.59 source build at `/home/ubuntu/IsaacSim`). Full asset chain
  rebuilt from a clean checkout — URDF import → `warehouse_base.usd` →
  `head_on_deadlock.usd` → `validate_simulation` **PASS** → headless run
  `completed: true, failure: null`, 451 ground-truth records over 45 sim-s,
  camera render product live (`rgb (960,1280,4) mean=127.95`). Isaac's bundled
  Jazzy `rclpy` loads inside Kit, so no host ROS 2 is needed for a sim-only
  run. Three facts worth keeping:
  - **Robot visual meshes were never in the repo.** The committed URDF
    references `meshes/{burger_base,left_tire,right_tire,lds}.stl`, which do
    not exist, so a plain import of it yields collision primitives only.
    Supplying the four ROBOTIS STLs next to the URDF imports 4 visual meshes
    (burger_base 48 040 pts). **Confirmed** as the cause of the bodyless robots
    in `data/logs/recordings/h3_final_demo_v13.mp4`: a fresh overhead render on
    this host (mean 127.93, matching the run's render product) shows chassis,
    both wheels, and a cast shadow where the July frame had only a floating
    marker quad. The meshes currently exist **only on the VM**, not in git, so
    a rebuild from `git archive HEAD` on a fresh host reproduces the mesh-less
    import. Note the marker renders offset from the body centroid — expected,
    not a perception bias: `aruco_marker_joint` is at `base_link` with no x/y
    offset, while the `base_link` visual mesh carries a `-0.032 m` origin and
    `base_link` itself sits at the wheel axis. M1's marker-derived pose is
    therefore in the same frame as odom and ground truth.
  - **Nothing validates visual geometry.** `validate_robot_asset` checks the
    articulation root, wheel `DriveAPI`, and disabled `base_joint`;
    `validation.py` checks metadata, namespace, camera frustum, marker mesh,
    and unresolved references. A mesh-less import passes every gate.
  - **Imported meshes are instanced**, so `Usd.Stage.Traverse()` reports zero
    `UsdGeom.Mesh` prims. Use `Traverse(Usd.TraverseInstanceProxies())` when
    checking an imported robot asset, or the geometry looks absent when it is
    not.
  - The `turtlebot3_burger_1/` import collision (2026-06-18 report, item 3) is
    avoidable without a post-hoc merge: move the committed URDF+meshes to a
    staging dir, free `isaac/assets/robots/turtlebot3_burger/`, then import —
    the importer writes the un-suffixed path `paths.robot_asset_path()` expects.
- **2026-09-16** — **Ground-truth oracle fixed for position; time axis
  still wrong.** `acceptance_logging.sample_robot_positions` now reads the
  chassis prim (`/World/Robots/<id>/Geometry/base_footprint/base_link`,
  the single `ArticulationRootAPI` prim; `base_link` name as fallback) via
  `ComputeLocalToWorldTransform(Usd.TimeCode.Default())`, resolved once
  per robot and cached by *path* so a stage reload cannot return a dead
  prim. Host probe compared four sources on the same step: root Xform
  frozen at spawn; chassis USD world pose = `RigidPrim.get_world_poses()`
  exactly; a raw Fabric attribute read returned only the local translate
  (rejected). Verified on the VM with both robots driven at 0.1 m/s:
  `x` now changes (robot_1 −1.5 → −0.049, robot_2 +1.5 → +0.021 at the
  deadlock), `speed_mps` non-zero while moving, `conflict_active` true for
  the first time, and the logged positions match spawn+odom to four
  decimals for both robots (opposite signs). That verification run then
  completed on its own (`run_manifest.json` `completed: true, failure:
  null`, 2 261 records); its final record has both robots parked
  nose-to-nose at the corridor centre — robot_1 (−0.057, −0.028),
  robot_2 (0.022, −0.019), `min_pairwise_distance_m 0.079`,
  `conflict_active: true` — the first acceptance log in the project to
  register a head-on conflict. Pre-fix file preserved on the VM as
  `ground_truth.jsonl.prefix_buggy_*`. Supersedes the "not a motion
  oracle" entry below for *positions*.
  **Still open — time axis:** `runner.py` advances `sim_time` by one
  `physics_dt` per `app.update()`, but at `rendering_hz 30` /
  `physics_hz 60` each update steps physics twice, so the counter runs at
  ~½ true sim time (GT 25.4 s vs `/clock` 48 s). Consequences: every
  velocity in `ground_truth.jsonl` is inflated ~1.9× (0.181 logged vs
  ~0.116 true), and a declared `duration_sec` runs ~1.9× longer in real
  sim time. **Fixed in code, host-unverified:** the loop now sets
  `sim_time = sim_ctx.current_time − loop_start_time`, anchored at
  recording start because `event_scheduler` `spawn_at_sec` and
  `duration_sec` are authored relative to it (a raw clock would include
  the topic-wait startup time). The step-count sampling gate was removed
  (it would have halved the log rate to 5 Hz); `AcceptanceLogger`'s own
  10 Hz throttle governs. **Verified on host (run A):** GT `sim_time_sec`
  vs `/clock` slope 1.008 over 127 s (0.992 over a shorter pair); robot_2's
  logged `speed_mps` during the 0.1 m/s escort max 0.092 / mean 0.089,
  independently matching 2.480 m over 27.2 sim-s = 0.091 m/s (the
  escort's lateral servo costs ~10 %); GT vs odom position agreement
  0.4 mm. `ground_truth.jsonl` is now usable as the experiment's metric
  source for position, distance, speed and `conflict_active`.
- **2026-09-16** — **Robots are now mutually visible to RTX lidar; they were
  not before the mesh fix.** Probe (fresh sim, no Nav2, robots parked at
  ±1.5 facing each other, 3.0 m apart): each robot's forward ±10° sector
  returns 1.6–2.3 m (the 0.55 m corridor wall, at exactly the ranges
  `0.275/sin(bearing)` predicts) and then a cluster at **2.99–3.12 m** —
  matching the other robot's front plate edge (~2.99), LDS body (~3.06)
  and rear structure (~3.1) from the observer's lidar origin. Nothing else
  in the scene lies 3 m straight ahead (far wall > 3.5 m `range_max`).
  Caveat: the probe kept bearings only for sector minima, so "at 0°" is
  inferred from geometry, not measured. Why this is new: the scan plane is
  z = 0.172 m; before the STLs the only render geometry on a robot was the
  marker quad at z = 0.21 m (see `lidar.exclude_from_rtx_lidar` docstring,
  2026-06-25), and collision prims are not rendered — so July's robots had
  no lidar cross-section at all, which is why motion-BVH work was needed to
  get *anything* into the costmap. **Consequence:** Nav2 now sees the
  oncoming robot from 3 m. In run 4 the planner blocked at ~1 m separation
  and no standoff formed; in run 6 (same config) a tight nose-to-nose
  standoff did form. So the 0.45 m standoff the July H3 runs and the
  congestion spec assume is now one of at least two onset modes, not the
  only one. The spec's onset window and the safety-monitor's role need
  revalidating over several runs before Arm A/B data collection.
  Options, not yet decided: accept planner-stall as the deadlock signature;
  or exclude robot meshes from the lidar (Isaac RTX-visibility / semantic
  filtering) to restore the July geometry while keeping the camera view.
- **2026-09-16** — OpenAI key verified on the VM for `gpt-4o`
  (`/v1/models/gpt-4o` 200; 2-token chat completion answered from
  `gpt-4o-2024-08-06`). Stored only in `/home/ubuntu/vgu-vlm-swarm/.env`
  (`chmod 600`), sourced inside the container via `set -a && source
  /ws/.env && set +a` immediately before launching M5 — never on a command
  line.
- **2026-09-16** — **`ground_truth.jsonl` does not track robot motion.**
  `acceptance_logging.sample_robot_positions` reads
  `UsdGeom.Xformable(/World/Robots/<id>).ComputeLocalToWorldTransform(0.0)` —
  the USD transform of the robot *root* prim, which physics never updates
  (Newton moves the articulation in Fabric; see the 2026-06-21 Fabric entry).
  Evidence from one run: the file reported `x=-1.5, speed=0.0` for both
  robots for 300 sim-s while Nav2 logged navigation from that spawn, M1 saw
  robot_1 at x≈0.00, and `/robot_1/odom` showed ~0.8 m of travel. So
  `conflict_active`, `min_pairwise_distance_m`, and `speed_mps` in the
  acceptance log are all constant-at-spawn and must not be used as a motion
  oracle until this is fixed (read the chassis/`base_link` prim through
  Fabric/usdrt, or reuse the odom bridge). `/robot_N/odom` is the honest
  arbiter in the meantime. Unclear whether the July H3 runs relied on this
  file; their conclusions were drawn from M1 and odom, per the M4 notes.
- **2026-09-16** — `vgu_ros` container rebuilt from scratch and verified
  against host Isaac. The container was never defined in the repo (only
  `.devcontainer/Dockerfile`, which is a *different* base —
  `osrf/ros:jazzy-desktop`), so it died with the old VM. Recipe that works,
  from plain `ros:jazzy` (the image every Nav2 param finding in
  `docs/specs/module4/phase2-nav2-stack.md` was validated against — do not
  swap the base without revalidating those):
  ```
  docker run -d --name vgu_ros --network host --ipc=host \
    -v /home/ubuntu/vgu-vlm-swarm:/ws -w /ws ros:jazzy sleep infinity
  apt-get install -y --no-install-recommends ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup python3-colcon-common-extensions python3-opencv \
    python3-jsonschema python3-pip
  pip3 install --break-system-packages "pydantic>=2.7"
  colcon build --symlink-install --merge-install   # in /ws/ros2_ws
  ```
  Verified: 5 swarm packages registered, `swarm_interfaces` msgs import,
  `/clock` delivering at ~12 Hz **inside** the container (data, not just
  discovery — the 2026-06-19 root cause), `/robot_1/odom` and `/tf` echoing,
  and `controller_server`/`planner_server`/`bt_navigator` all lifecycle
  `active` with `/robot_1/navigate_to_pose` live. Notes:
  - `--network host --ipc=host` plus `FASTRTPS_DEFAULT_PROFILES_FILE=
    /ws/config/dds/fastdds.xml` on **both** sides remains mandatory.
  - Stock `ros:jazzy` has numpy and yaml but **no** cv2, pydantic, or
    jsonschema, and zero nav2 packages.
  - apt `python3-opencv` is 4.6.0, which exposes `DetectorParameters` but
    **not** `ArucoDetector`. That is fine and deliberate: `detection.py`
    version-gates on `ArucoDetector` and takes the legacy
    `DetectorParameters_create()` path. Do **not** pip-install
    `opencv-contrib-python` on top — mixing the two is what the 4.6.0 segfault
    comment in `detection.py` warns about.
  - apt `jsonschema` is 4.10.3, below `requirements.txt`'s `>=4.22`. The only
    API used (`Draft202012Validator`) exists in 4.10, so it was left alone —
    revisit if schema validation misbehaves.
  - Without Isaac running, `local_costmap` blocks on
    `robot_1/base_link -> robot_1/odom` and Nav2 never activates. That is
    expected, not a container fault: the frame comes from Isaac. Nav2 activates
    on its own once the sim publishes TF.
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
