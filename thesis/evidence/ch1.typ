// Evidence rows for chapter 1: one evidence call per number, id = chapter.NN.
#import "../lib.typ": *

#evidence("1.01", [Design targets: Layer 1 at 20–50 Hz, Layer 2 at 0.5–2 Hz.], [`68e67b5:docs/modules.md` (header)])

#evidence("1.02", [CongestionDecision strategy is a closed set of 8 values (none, yield, reroute, convoy, priority\_override, temporary\_wait, reverse, junction\_clear).], [`68e67b5:reasoning/vlm/models.py` (CongestionDecision)])

#evidence("1.03", [Five research questions RQ1 to RQ5 (renamed from H1 to H5), frozen with the prereg-v1 research design; RQ1 scope note (post-trigger classification only).], [`569d95c:docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md` ("Research questions (RQ1-RQ5, thesis skeleton)")])

#evidence("1.04", [Safety monitor: min\_distance\_m 0.45 (pair hold), stale fail-safe; hard\_contact\_floor\_m 0.0 shipped, 0.20 in the floor file installed for live cells; floor latches exempt pairs. v3 A9: 0.20 m floor ruled a push-limiter backstop, not a contact preventer.], [`68e67b5:ros2_ws/src/swarm_execution/config/safety.yaml`; `68e67b5:config/safety/safety_floor020.yaml`; `68e67b5:ros2_ws/src/swarm_execution/swarm_execution/safety.py` (SafetyLimits, evaluate\_latches); `ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A9)])

#evidence("1.05", [prereg-v1 tag on 2026-09-30 (= 569d95c); prereg-v3 design prepared 2026-10-06; append-only addenda; every scored criterion registered before collection, pilots excluded.], [tag `prereg-v1` = `569d95c`; `569d95c:docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`; `ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (header; Discipline items 2-3)])

#evidence("1.06", [Bench corpus: 187 recorded analyses from 31 live S1b episodes (E6-E26 pilots, E27-E31 tranche 1).], [`05a44eb:docs/reports/2026-10-22-v4-bench-baseline.md` (Inventory)])

#evidence("1.07", [Physical demonstration on 12 November 2026: TurtleBot3s, overhead RealSense, ArUco, `gemini-3.1-flash-lite`, deterministic grounding, safety monitor; four scenarios A, C, D, E of up to four robots; robots had no goals.], [`~/Downloads/verified_scenarios_12-11-2026/README.md` lines 1-18, 22-189 (md5 26718adbffa7a3135ebd509630afc3c2); `decision_artifacts/` (robot state keys, empty distance\_to\_goal\_m)])

#evidence("1.08", [Tranche 1: 5 seeds (positions 1 to 5) x 2 arms = 10 episodes; registered confirmatory n is 20 per arm; owner decided 2026-11-13 to skip tranche 2; tranche 1 reported as pilot.], [`75a499c:docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` (sections 1.1, 1.3, 1.5); `ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A32); `50704c2:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (section 1)])

#evidence("1.09", [IB10: 4 robots, one per arm of a cross aisle; registered 5 episodes per arm (Arm A Layer 2 on, Arm B Layer 2 off); exploratory, separate from prereg-v3.], [`68e67b5:isaac/config/scenarios/intersection_bottleneck.yaml`; `50704c2:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (sections 1, 3)])

#evidence("1.10", [Grounder-default run: Arm C (scripted mock, M3 default plan, no VLM call) vs Arm A; e02 C ... e10 C, 5 Arm C slots; never pooled with the 2026-11-13 arms or prereg-v3.], [`e6a904e:docs/superpowers/specs/2026-11-14-ib10-safety-default-arm-addendum.md` (sections 1, 3, 9)])

#evidence("1.11", [Stage 1 live shadow of the per-cluster variant: 7 episodes, seed positions 21-27; shadow never dispatched; exploratory.], [`0eb8ce5:docs/reports/2026-11-13-v4-stage1-shadow-results.md` (Scope, Runtime)])

#evidence("1.12", [v1 amendment A2: presentation order random, seeded, recorded, analyses conditioned on it; rationale: the yielder gpt-4o names under id\_asc is a positional artifact (first-slot prior).], [`569d95c:docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md` (A2)])

#evidence("1.13", [IB10 registration: in the earlier live pilot every IB10 plan was repaired or replaced by M3; a resolved Arm A episode shows the pipeline resolving the jam, not the model's choice.], [`50704c2:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (section 6, "Model vs grounder")])

#evidence("1.14", [S1b: 5 robots, 5 task nodes, 5 tasks per robot (task stream).], [`68e67b5:isaac/config/scenarios/mapd_5_s1b.yaml`])
