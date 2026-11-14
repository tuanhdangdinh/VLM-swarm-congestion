// Evidence rows for chapter 3: one evidence call per number, id = chapter.NN.
// Code facts are read at 68e67b5 (the runtime that ran the experiments). Files that differ
// between 68e67b5 and cbe3dcf are cited at 68e67b5 on purpose.
#import "../lib.typ": *

#evidence("3.01", [Design targets: Layer 1 at 20–50 Hz, Layer 2 at 0.5–2 Hz; proposal safety values d\_min 0.3 m, v\_max 0.2 m/s.], [`68e67b5:docs/modules.md` (header and M4.4)])

#evidence("3.02", [Architecture figure: module boundaries, layer rates and topic names.], [`68e67b5:docs/modules.md`; `68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` (DEFAULT\_TOPICS); `68e67b5:ros2_ws/src/swarm_perception/swarm_perception/perception_node.py`; `68e67b5:ros2_ws/src/swarm_execution/swarm_execution/command_bus_node.py`; `68e67b5:isaac/vgu_sim/ros_graphs.py`])

#evidence("3.03", [Nav2 controller\_frequency 20 Hz; DWB FollowPath max\_vel\_x 0.18 m/s, below the 0.2 m/s safety cap.], [`68e67b5:ros2_ws/src/swarm_simulation/config/nav2_params.yaml` (lines 73, 96)])

#evidence("3.04", [Safety monitor republishes zero Twist for held robots every 0.025 s (40 Hz) and cancels the Nav2 goal; publishes /safety/holds.], [`68e67b5:ros2_ws/src/swarm_execution/swarm_execution/safety_monitor_node.py` (module docstring; HOLD\_PERIOD\_SEC line 126)])

#evidence("3.05", [M5 timer period 0.5 s; detector runs on each scene message; M2 and M3 run on a ThreadPoolExecutor with max\_workers=1.], [`68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` (lines 517, 606, 750)])

#evidence("3.06", [Module input/output names: topics, service, messages and data contracts.], [`68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` (DEFAULT\_TOPICS); `68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` (lines 580–606); `68e67b5:ros2_ws/src/swarm_perception/swarm_perception/perception_node.py`; `68e67b5:ros2_ws/src/swarm_perception/swarm_perception/models.py`; `68e67b5:reasoning/vlm/models.py` (ReasonerRequest, ReasonerResult, CongestionDecision, SnapshotFrame); `68e67b5:reasoning/rag/command_grounder.py` (VerifiedPlan, JunctionClearPhasePlan); `68e67b5:reasoning/schemas/coordination_command.schema.json`; `68e67b5:ros2_ws/src/swarm_interfaces/msg/CoordinationCommand.msg`, `CoordinationStatus.msg`, `srv/TriggerCongestionAnalysis.srv`; `68e67b5:ros2_ws/src/swarm_execution/swarm_execution/safety_monitor_node.py` (lines 147–158); `68e67b5:ros2_ws/src/swarm_execution/swarm_execution/command_bus_node.py`; `68e67b5:ros2_ws/src/swarm_execution/swarm_execution/nav2_adapter.py` (line 20); `68e67b5:isaac/vgu_sim/ros_graphs.py` (line 120); `68e67b5:isaac/vgu_sim/cmd_vel_watchdog_node.py`])

#evidence("3.07", [ArUco dictionary DICT\_4X4\_50 (marker 0.12 m); camera 1280 × 960 at 30 fps on /camera/image\_raw.], [`68e67b5:ros2_ws/src/swarm_perception/config/aruco.yaml`; `68e67b5:ros2_ws/src/swarm_perception/config/camera.yaml`])

#evidence("3.08", [State machine: states monitoring/analyzing/dispatching; single in-flight cycle; cooldown and busy gating; queued-follower fold for a solo stall beside a busy set of at least 2 robots.], [`68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/state_machine.py` (is\_queued\_follower, on\_event)])

#evidence("3.09", [reasoning\_enabled (default true); false disables detection, M2, M3, dispatch; scene log, registry and task stream continue.], [`68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` (line 544, REASONING\_OFF\_STATUS\_LINE); `ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A35 Arm B switch)])

#evidence("3.10", [ReasonerConfig defaults max\_attempts 2, timeout\_sec 30.0; presentation order id\_asc (default), id\_desc, or a random permutation per episode with 3+ robots; backends mock, llama\_server, openai, anthropic, gemini.], [`68e67b5:reasoning/vlm/models.py` (ReasonerConfig lines 977–1003; RobotPresentationOrder comments); `68e67b5:reasoning/vlm/backend_factory.py` (lines 35–39); `68e67b5:ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml` (prompt\_robot\_order: id\_asc)])

#evidence("3.11", [Pipeline figure: detect, decide, ground, act, resolve; yield gate swap/refuse; refusal dispatches nothing; safety hold.], [`68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` (InProcessPipeline.run); `68e67b5:reasoning/rag/command_grounder.py` (\_apply\_yield\_feasibility); `68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` (refusal\_no\_action, lines 1259–1290); `68e67b5:ros2_ws/src/swarm_execution/swarm_execution/safety_monitor_node.py`])

#evidence("3.12", [Shipped M5 config: stall\_threshold\_sec 12.0, progress\_epsilon\_m 0.10, cooldown\_sec 15.0, command\_timeout\_sec 20.0; timeouts expire only commands with no ACTIVE robot.], [`68e67b5:ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`; `68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/congestion_detector.py`; `68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/command_lifecycle.py` (check\_timeouts)])

#evidence("3.13", [Stage-2 retreat selection on (stage2\_retreat\_selection: true, stage2\_max\_attempts 2, stage2\_timeout\_sec 8.0); an invalid or missing letter grounds the top-ranked candidate (tag retreat=default:\*).], [`68e67b5:ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`; `68e67b5:reasoning/rag/command_grounder.py` (ground\_reasoner\_result docstring; DEGRADATION\_TAGS)])

#evidence("3.14", [CongestionDecision strategy Literal has 8 values (none, yield, reroute, convoy, priority\_override, temporary\_wait, reverse, junction\_clear); type has 5 values; grounder emits only yield, reverse, reroute, temporary\_wait actions.], [`68e67b5:reasoning/vlm/models.py` (CongestionDecision); `68e67b5:reasoning/rag/command_grounder.py` (all "action" literals, lines 1016–3226)])

#evidence("3.15", [Strategy table: M3 grounding per strategy and M4 execution primitive.], [`68e67b5:reasoning/rag/command_grounder.py` (ground\_reasoner\_result, resolve\_strategy\_alias, ground\_junction\_clear\_phases, \_wait\_fan\_out); `68e67b5:ros2_ws/src/swarm_execution/swarm_execution/command_bus_node.py` (\_dispatch, lines 151–530)])

#evidence("3.16", [Convoy alias: opposed bearing > 90°; priority\_override alias only with exactly 2 involved robots; non-spatial bounded wait 8.0 s.], [`68e67b5:reasoning/rag/command_grounder.py` (\_OPPOSED\_BEARING\_DEG line 311, resolve\_strategy\_alias, \_NONSPATIAL\_WAIT\_SEC line 1421)])

#evidence("3.17", [Grounding settings: shipped defaults vs S1b overlay; max\_repair\_edits default 4, not overridden in config.], [`68e67b5:ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`; `68e67b5:isaac/config/scenarios/mapd_5_s1b.yaml` (M5 overlay, lines 168–220); `68e67b5:config/grounding/s1b_dynamic.yaml` (mode: derived); `68e67b5:config/rag.yaml` (mode: derived); `68e67b5:reasoning/rag/command_grounder.py` (PlanRepairParams); IB10 overlay: `2557d75:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (lines 28–30)])

#evidence("3.18", [Yield feasibility gate (swap / refuse, ties by robot order); junction\_clear chi ranking, release lead = rank 0, yielder re-enters last; no candidate → plain yield, tag junction\_clear=fallback:no\_candidates plus shipped\_unsolved tag if geometry fields missing.], [`68e67b5:reasoning/rag/command_grounder.py` (\_apply\_yield\_feasibility lines 465–569; JunctionClearPhasePlan; lines 2375–2396)])

#evidence("3.19", [refusal\_no\_action withholds a refused yield's wait fan-out and an empty-waypoint reroute fallback; effective only with task\_stream enabled.], [`68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/orchestrator_node.py` (lines 476–481, 1259–1290); `68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` (yield\_refusal\_fan\_out, empty\_reroute\_fallback)])

#evidence("3.20", [verify\_and\_repair\_plan: lenient completion, rejection stages, BFS repair with swap/reorder/substitute, max\_repair\_edits 4, provenance vlm\_verbatim/repaired/m3\_default; dispatch comes from the grounder, plan audit records dispatch\_matches\_plan; "does not change ground\_reasoner\_result or any dispatch path".], [`68e67b5:reasoning/rag/command_grounder.py` (lines 3270–3470, 4362–4400, 4574–4640, 4761–4850); `68e67b5:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py` (InProcessPipeline.\_run\_from\_result)])

#evidence("3.21", [Later extensions default off: per\_cluster\_shadow.enabled false; refusal\_feedback.enabled and prompt\_offer\_groundable\_strategies false; grounding-first is an offline bench variant.], [`cbe3dcf:ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`; `384e948:ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py` (RefusalFeedbackConfig); `cbe3dcf:benchmarks/vlm_bench/variants/grounding_first.py`])

#evidence("3.22", [Safety values: min\_distance\_m 0.45, max\_linear\_velocity\_mps 0.2, stale\_unsafe\_distance\_m 0.6 (= 0.45 + STALE\_UNSAFE\_MARGIN\_M 0.15), hard\_contact\_floor\_m 0.0 shipped; floor file sets 0.20 with all other values equal; floor latches exempt and waived pairs.], [`68e67b5:ros2_ws/src/swarm_execution/config/safety.yaml`; `68e67b5:config/safety/safety_floor020.yaml`; `68e67b5:ros2_ws/src/swarm_execution/swarm_execution/safety.py` (SafetyLimits, evaluate\_latches)])

#evidence("3.23", [min\_distance\_m raised from 0.3 to 0.45: 0.3 m left ~0.5 s reaction at 0.28 m/s worst-case closing vs 0.2–0.4 s latency; 0.45 m restores ~1 s; grounder sizes passer clearance from the 0.45 m radius.], [`68e67b5:docs/specs/module4/safety-monitor.md` (lines 13, 58–62); `68e67b5:docs/modules.md` (M4.4 d\_min 0.3 m); `68e67b5:reasoning/rag/command_grounder.py` (PASSER\_CLEARANCE\_M comment)])

#evidence("3.24", [Clearing exemption: CLEARING\_ACTIONS = {yield, reverse}; own-command partners; backup phase vs admitted passers; shield holds not partners; A19 one-sided waivers; speed rule exempts clearing robots.], [`68e67b5:ros2_ws/src/swarm_execution/swarm_execution/safety.py` (lines 33–58, admitted\_partners, ClearingExemption); `68e67b5:ros2_ws/src/swarm_execution/swarm_execution/safety_monitor_node.py` (docstring; line 280)])

#evidence("3.25", [Floor value 0.20 m = footprint contact 0.18 m + ~2 × M1 median static error 0.011 m.], [`68e67b5:ros2_ws/src/swarm_execution/config/safety.yaml` (hard\_contact\_floor\_m comment)])

#evidence("3.26", [Arming procedure: per-run swap of the floor file; episode gated on M4 startup line hard\_contact\_floor\_m=0.2, chain stops otherwise; shipped file restored and md5-verified after each invocation; floor stops counted.], [`68e67b5:docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` (§1.6, report commit 75a499c); `2557d75:docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (lines 24, 30, 85, 104–105); `ad67a18:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A28(i), A32: "pre/post arm gates")])

#evidence("3.27", [Exemption-scope code trace (2026-11-13): five paths, paths 1–4 bugs/risks, path 5 by design; no incident attributed; floor armed as backstop in recent live cells.], [`cbe3dcf:docs/reports/2026-11-13-safety-exemption-trace.md`])

#evidence("3.28", [Fix for paths 1–3 behind safety.scoped\_clearing\_exemption, on only for literal true; absent or false behaves exactly as at 68e67b5; not part of the evaluated runtime.], [`8933863:docs/reports/2026-11-14-safety-exemption-fix.md` (Behaviour section; branch fix/safety-exemption-scope, based on 68e67b5)])
