# Feasibility Grounding for VLM Multi-Robot Plan Emission (2025–2026)

Research notes, 2026-10-04. Scope: techniques for getting VLMs to emit geometrically feasible multi-step / multi-agent plans from a single scene image, with per-technique adoptability verdicts for our setting (single annotated overhead frame + numeric state + small action vocabulary + grammar + classical leg-by-leg verifier/repair).

Verification legend: **VERIFIED** = primary source (paper PDF/abstract) read directly. **UNVERIFIED** = from search-result summaries only; claim plausible but numbers not checked against the primary text.

## KQ1 — Visual prompting FOR PLANNING (multi-step / multi-agent plan elicitation; candidate-maneuver marking)

### Takeaway
The candidate-overlay-then-select pattern (PIVOT lineage) is now routinely extended from single actions to whole trajectories: several 2025–2026 navigation systems render numbered/colored candidate *paths* on the camera image and have the VLM pick one. But in every published instance the VLM selects ONE pre-rendered trajectory per agent per query — **no published work was found where candidate maneuvers are marked on the image and the VLM COMPOSES an ordered multi-agent plan from them** (our "stage-2 generalized to plans"). That composition step appears to be open territory; the closest analogues compose plans per-arm from a predefined atomic prompt set (MA-VLA) or assign a leader + waypoint sequence from one overhead image (MIT VLM-GCBF+).

### Cited Findings
- PIVOT (VERIFIED concept, 2024 baseline for the lineage): annotates the image with visual proposals (candidate robot actions, trajectories), VLM selects best, distribution refit, iterate — zero-shot robot control and navigation without robot training data — [arXiv:2402.07872](https://arxiv.org/abs/2402.07872), [project](https://pivot-prompt.github.io/assets/pivot.pdf)
- MOKA (VERIFIED concept, RSS 2024): marks candidate keypoints, grids and labels on 2D images, converting affordance/motion reasoning into sequential VQA; keypoints+waypoints then lifted to SE(3) trajectories. Multi-STAGE but single-arm; plan structure comes from an LLM task decomposition, not composed from marked maneuvers — [arXiv:2403.03174](https://arxiv.org/abs/2403.03174), [RSS page](https://roboticsproceedings.org/rss20/p062.html)
- VL-TGS (RA-L vol 10 no 6, June 2025, UNVERIFIED numbers): CVAE samples multiple traversability-constrained candidate trajectories; VLM evaluates/selects among them for mapless outdoor global navigation — [arXiv:2408.02454](https://arxiv.org/pdf/2408.02454), [RA-L PDF](https://people.cs.gmu.edu/~xiao/papers/tgs.pdf)
- "From Obstacles to Etiquette: Robot Social Navigation with VLM-Informed Path Selection" (2026, UNVERIFIED): samples collision-free path candidates, projects them into the image as **numbered, colored polylines with index labels at endpoints**, fine-tuned VLM picks by traversability/social compliance/distance — the cleanest published template for marking candidate maneuvers on the frame — [arXiv:2602.09002](https://arxiv.org/html/2602.09002v1)
- "Slow Brain, Fast Planner" (2026, UNVERIFIED): same render-candidates-as-labeled-polylines pattern, used asynchronously so the VLM's slow choice conditions a fast local planner — latency architecture directly analogous to our Layer-2/Layer-1 split — [arXiv:2606.20458](https://arxiv.org/pdf/2606.20458)
- MA-VLA (2026, UNVERIFIED): VLM planner converts a goal into a structured sequence of **per-arm sub-instructions** by conditioning on instruction + visual observations + a **predefined atomic prompt set** — the closest published analogue to "compose a plan from a fixed maneuver vocabulary," though for multi-arm manipulation, not mobile robots — [arXiv:2608.25864](https://arxiv.org/pdf/2608.25864)
- Wonderful Team (2024/2025, UNVERIFIED): zero-shot physical task planning with visual LLMs using image annotation across a multi-agent (multi-role) VLM pipeline — [arXiv:2407.19094](https://arxiv.org/pdf/2407.19094)
- "Beyond Waypoints: A Trajectory-Centric Waypointing Paradigm for VLN" (2026, UNVERIFIED): argues trajectory-level (not waypoint-level) visual prompting for navigation — [arXiv:2606.07244](https://arxiv.org/pdf/2606.07244)
- RT-Trajectory (ICLR 2024, lineage anchor, VERIFIED concept): coarse 2D trajectory sketches overlaid on the image condition a policy; sketches can come from drawings, videos, or automated waypoint generators — [arXiv:2311.01977](https://arxiv.org/abs/2311.01977); 2025 descendant Sketch-to-Skill bootstraps RL from 2D sketches (~96% of teleop baseline, UNVERIFIED) — [arXiv:2503.11918](https://arxiv.org/abs/2503.11918v1)

### Inferences
- Adoptability verdicts:
  - **Numbered candidate-path overlay (2602.09002 / 2606.20458 pattern): ADOPT.** Render the verifier's candidate recede/yield maneuvers as labeled polylines/slots on the annotated frame; ask the model to pick one label per robot plus an ordering. Converts our hardest failure (axis-mirror of the modeled recede set) into a discrete choice over only modeled options. Cost: rendering code + slightly busier frame; no training.
  - **Plan COMPOSITION from marked maneuvers: no prior art found** — doing it would be novel; the safe published-pattern decomposition is per-leg selection (one labeled choice per robot) + model-stated ordering, with grammar enforcing enabling actions, i.e., selection N times + textual ordering rather than free composition.
  - **PIVOT-style iteration: SKIP** for 0.5–2 Hz loop (multiple VLM round-trips per decision); single-shot selection over verifier-generated candidates captures most of the benefit.
  - **MA-VLA-style atomic-prompt-set conditioning: partial adopt** — our action vocabulary already is the atomic set; their evidence supports keeping the vocabulary explicitly enumerated in-prompt with per-robot slots.

### Gaps
- No paper found that marks candidate maneuvers for MULTIPLE robots on one image and asks the VLM to emit an ordered joint plan over them; could not verify any measured feasible-plan-rate gains for trajectory-overlay vs text-only prompting in the navigation papers (numbers live in paper tables not retrieved).

## KQ2 — Feasibility feedback in-prompt (stating the verifier's constraints; does it raise feasible-plan rates?)

### Takeaway
Yes, with the strongest published evidence coming from MAPF: listing each agent's currently-feasible actions in the prompt ("single-step observation") plus a checker-feedback re-prompt loop is the established recipe, and 2025 work reports feedback loops roughly doubling performance. A separate 2025–2026 thread (RLVR) shows constraints are internalized better by training with a verifier reward than by prompting — small constraint-trained models beat large prompted ones — but that requires fine-tuning. Giving the VLM the verifier's constraint set as text is cheap and published-supported; giving it visually (overlays) is supported by the KQ1 and KQ4 evidence.

### Cited Findings
- "Why Solving Multi-agent Path Finding with LLM has not Succeeded Yet" (UNVERIFIED details): prompt includes map, agent starts/goals, and **single-step observation (SSO) listing the feasible actions for each agent next step**; a high-level checker detects agent/obstacle collisions and feeds error messages back, LLM regenerates until collision-free per step; context length is the binding failure mode at scale — [arXiv:2401.03630](https://arxiv.org/abs/2401.03630)
- ACL 2025 survey of LLM planning: closed-loop re-prompting with executor/validator feedback until plan is executable is the standard pattern; "feedback loops nearly double performance" via structured error summaries and targeted patches (survey-level claim, UNVERIFIED which benchmark) — [A Modern Survey of LLM Planning Capabilities](https://aclanthology.org/2025.acl-long.958.pdf)
- "Collision- and Reachability-Aware Multi-Robot Control with Grounded LLM Planners" (VERIFIED abstract): RL with verifiable rewards (positive reward only for valid, task-completing plans) on Qwen2.5-3B-Instruct and Qwen3-4B; **constraint-aware small LLMs largely outperform large-scale models without constraint grounding** on BoxNet and BoxNet3D (MuJoCo) multi-robot tasks — [arXiv:2505.20573](https://arxiv.org/abs/2505.20573)
- VIZ-COAST, "Using VLM Reasoning to Constrain Task and Motion Planning" (VERIFIED abstract; Kavraki/Kingston groups, submitted AAAI 2027): inverts the flow — VLM looks at image + domain description and emits constraints that prune the classical TAMP search *before* failures, "drastically reducing planning times" and in some domains eliminating downward-refinement failures entirely (no numbers in abstract) — [arXiv:2510.25548](https://arxiv.org/abs/2510.25548)
- MIT VLM-GCBF+ PMLR 2026 paper (VERIFIED, full text read): prompt states constraints textually (waypoints "at least 2r from all obstacles," "NOT intersect any obstacles") and requests strict JSON `{"Leader": Id, "Waypoints": [[x,y],...]}`; feasible-waypoint-generation accuracy was then measured per model over 100 environments (Fig. 3; newer models better: GPT-5 > GPT-4o > GPT-4o-mini > GPT-4; VLM mode beats LLM mode of the same model) — [PDF](https://mit-realm.github.io/VLM-gcbfplus-website/files/Online_planning_using_VLMs.pdf)
- Self-corrective task planning by inverse prompting (2025, UNVERIFIED): LLM re-derives/checks its own plan via inverse prompting to catch infeasible steps — [arXiv:2503.07317](https://arxiv.org/html/2503.07317v1)
- PhysVLM (CVPR 2025, UNVERIFIED details): encodes robot-specific reachability as an extra "S-P Map" input channel so the VLM reasons with explicit physical-feasibility information; Phys100K dataset, EQA-phys benchmark across six robots — [CVPR 2025 paper](https://openaccess.thecvf.com/content/CVPR2025/papers/Zhou_PhysVLM_Enabling_Visual_Language_Models_to_Understand_Robotic_Physical_Reachability_CVPR_2025_paper.pdf)

### Inferences
- Adoptability verdicts:
  - **SSO-style per-robot feasible-action lists in prompt: ADOPT now.** Our verifier already computes candidate sets; serializing "robot_k may: {reverse-south, yield-slot-B, wait}" is exactly the MAPF SSO recipe and directly attacks mirror-set and mis-assigned-yielder failures by construction (infeasible options never offered). Cost: ~tens of tokens per robot.
  - **One-shot verifier-feedback re-prompt (checker error → regenerate): ADOPT with a bound of 1–2 retries** at 0.5–2 Hz; the published loops iterate per-step, we'd iterate per-plan. The ACL-survey "feedback nearly doubles performance" claim supports even a single structured-error retry before falling back to classical repair.
  - **RLVR constraint internalization (2505.20573): DEFER** — requires fine-tuning infrastructure, but is the published path if prompted feasibility plateaus; notable that a 3–4B constraint-trained model sufficed.
  - **PhysVLM-style feasibility map as an input channel: inference-time analogue = shade the verifier's clearance/tracked-band regions onto the overhead frame.** No published measurement of that exact inference-time variant found.

### Gaps
- No paper isolates "stating the constraint set in-prompt vs not" as a controlled ablation with a feasible-PLAN-rate delta for VLMs on images (MAPF work is text-grid; VLM-GCBF+ measures absolute feasibility rates, not the with/without-constraint-statement delta). The exact numeric bars of VLM-GCBF+ Fig. 3/5 are in figures, not text.

## KQ3 — Symmetry / multimodality handling (mirror-equivalent resolutions)

### Takeaway
Published systems break symmetric deadlocks by DESIGNATION, not by scoring both modes: a leader/first-mover is chosen (by the VLM/LLM, by auction-like dialogue, or heuristically by distance-to-goal) and the rest of the resolution is derived from that choice. I found **no published canonicalization or accept-either-mirror scoring protocol for VLM plan evaluation** — evaluation practice in these papers is outcome-based (deadlock resolved / reach rate), which implicitly accepts either mirror. Our presentation-order finding (first-slot/robot_1 priors) has no direct published counterpart as a tie-break mechanism, which makes the in-house `random order + condition on draw` protocol ahead of the literature.

### Cited Findings
- "Foundation Models to the Rescue: Deadlock Resolution in Connected Multi-Robot Systems" (VERIFIED via successor paper + abstract): symmetric deadlock is resolved by the foundation model assigning a **leader** plus waypoints; leader should be "the agent that can move freely in the environment" — [arXiv:2404.06413](https://arxiv.org/abs/2404.06413)
- VLM-GCBF+ PMLR 2026 (VERIFIED full text): for large MRS (N≥10) the leader choice is removed from the VLM entirely — **leader assigned heuristically as the agent with minimum distance to its goal** (k-means sub-teams, sub-leaders by vicinity), VLM only does waypoints; i.e., the symmetric/assignment-prone decision is canonicalized by a deterministic rule — [PDF](https://mit-realm.github.io/VLM-gcbfplus-website/files/Online_planning_using_VLMs.pdf)
- GameChat (2025, UNVERIFIED details): symmetric agents (equal distance to collision point, equal velocity) break the tie via **natural-language negotiation grounded in task urgency**, yielding a "socially optimal" priority order with game-theoretic (subgame-perfect-equilibrium) backing — [arXiv:2503.12333](https://arxiv.org/pdf/2503.12333)
- "The Before, During, and After of Multi-Robot Deadlock" (background, UNVERIFIED): formal geometric characterization of deadlock sets for CBF-controlled robots — the classical statement that symmetric configurations admit multiple equivalent exits — [arXiv:2206.01781](https://arxiv.org/pdf/2206.01781)
- Evaluation practice: VLM-GCBF+ scores reach rate / interventions / time / tokens, never which mirror was taken (VERIFIED); the MAPF-LLM work scores collision-free validity and makespan — [arXiv:2401.03630](https://arxiv.org/abs/2401.03630)

### Inferences
- Adoptability verdicts:
  - **Deterministic designation before the VLM call: ADOPT.** The strongest published pattern (VLM-GCBF+ large-N mode) is to remove the symmetric choice from the model: have the classical layer pick the yielder/receding side by a stated rule (e.g., min distance-to-goal, or robot clear of the tracked band) and ask the VLM only to fill in the plan around that designation. This directly addresses mis-assigned-yielder and mirror-set failures.
  - **If the VLM must choose: require a stated tie-break.** GameChat's urgency-grounded priority suggests prompting "if resolutions are symmetric, prefer the one where the robot with lower task urgency / larger free space yields, and say which rule you applied" — but note this exact prompting move is our extrapolation; no paper measures it.
  - **Scoring: accept-either-mirror at the outcome level** is implicitly what all published evaluations do; for our experiments, scoring plan-vs-modeled-set should either canonicalize (reflect model output into the modeled half-space before comparison) or score both mirrors and take the max — no published precedent to cite either way, so document the choice in the prereg.

### Gaps
- No published work found on canonicalization or mirror-equivalence-aware scoring of VLM-emitted plans; no ablation found on tie-break statements in prompts reducing mirror errors. Both would be novel measurable contributions.

## KQ4 — Spatial-grounding advances usable at inference time (grids, rulers, coordinate-free prompting, ego→allo)

### Takeaway
2025–2026 GUI-grounding work gives the clearest measured evidence for our planned labeled metric grid: converting continuous coordinate prediction into **discrete labeled-grid-cell prediction** (Mark-Grid scaffold) yields order-of-magnitude accuracy gains for some models, but grid overlays are model-dependent and can HURT (Qwen2.5-VL-7B regressions reported). Overhead/BEV is confirmed as the favorable viewpoint — benchmarks show performance rises as the view approaches bird's-eye — so our frame choice is already on the right side of the ego→allo gap; the remaining risk is coordinate READOUT, which grid-ID prediction fixes.

### Cited Findings
- "How Auxiliary Reasoning Unleashes GUI Grounding in VLMs" (2025, UNVERIFIED exact numbers): failing to output coordinates is a **communication gap, not a perception gap**; Coordinate / Axis-Grid / Mark-Grid scaffolds overlay axes, labeled intersections, numbered cells; strongest variant (Mark-Grid: predict grid ID, then zoomed second pass) improves click accuracy from ~5% to ~72% on ScreenSpot-v2 — [arXiv:2509.11548](https://arxiv.org/pdf/2509.11548)
- "Improving GUI Grounding with Explicit Position-to-Coordinate Mapping" (2025, UNVERIFIED): same thesis, explicit position→coordinate mapping in-prompt — [arXiv:2510.03230](https://awesomepapers.io/multimodal/papers/2510.03230)
- VLM2-Bench VP-grid caveat (UNVERIFIED): dot-matrix grid with per-dot coordinate tuples + textual coordinate-system description helps some models but causes **significant performance drops for Qwen2.5-VL-7B** — grid overlays are not uniformly beneficial — [arXiv:2502.12084](https://arxiv.org/pdf/2502.12084)
- Visual Position Prompt (VPP, 2025, UNVERIFIED): axis-like position embeddings/overlays improve MLLM visual grounding — [arXiv:2503.15426](https://arxiv.org/html/2503.15426v2)
- InfiniBench (2025, UNVERIFIED): model performance on perspective-taking and spatiotemporal tasks **improves substantially as the viewpoint approaches bird's-eye** — supports our overhead-frame design — [arXiv:2511.18200](https://arxiv.org/pdf/2511.18200)
- ViewSpatial-Bench (ECCV 2026): 5,700+ QA pairs over 1,000+ scenes isolating egocentric-vs-allocentric localization; documents a persistent ego→allo gap in current VLMs — [GitHub](https://github.com/ZJU-REAL/ViewSpatial-Bench), [page](http://zjureal.com/ViewSpatial-Page/); related: CityCube (ACL 2026) [PDF](https://aclanthology.org/2026.acl-long.416.pdf), 3ViewSense [arXiv:2603.07751](https://arxiv.org/pdf/2603.07751)
- VLM-GCBF+ (VERIFIED): VLMs given the overhead image **plus a textual listing of agent/goal coordinates** ("to assist the VLM with the precise locations... we provide their text description as well"); image+text beat text-only (LLM) on feasible waypoint generation, and VLM token usage stayed flat (~1000 tokens) as scene complexity grew while LLM text descriptions ballooned — [PDF](https://mit-realm.github.io/VLM-gcbfplus-website/files/Online_planning_using_VLMs.pdf)
- "Evaluating VLMs' Spatial Reasoning Over Robot Motion" (2026, UNVERIFIED): benchmark of VLM spatial judgments specifically about robot motion/plans with motion preferences — relevant test material for plan-level spatial outputs — [arXiv:2603.13100](https://arxiv.org/pdf/2603.13100)

### Inferences
- Adoptability verdicts:
  - **Labeled metric grid: ADOPT, but as DISCRETE cell IDs, not as a ruler for coordinate regression.** The measured GUI gains come from letting the model name a labeled cell; for us, have the model reference maneuver endpoints/clearance regions by cell label (e.g., "robot_2 reverse into C4") and let the verifier map labels→metric. Also matches our redundant numeric-state channel (the VLM-GCBF+ image+text-coordinates recipe is VERIFIED to be their choice).
  - **Pilot the grid per-model.** The Qwen regression result means the planned grid should be A/B'd against the current SoM-only frame for each backend (gpt-4o, Gemini ER-2) before freezing — cheap ablation, high downside if skipped.
  - **Coordinate-free relational prompting:** no dedicated 2025–2026 method paper found beyond benchmark diagnoses; the practical published recipe is grid-ID discretization rather than pure relational language.
  - **Ego→allo conversion aids: NOT NEEDED** — we are already allocentric/overhead, the favorable regime per InfiniBench; the known residual hazard is left/right-axis confusion in textual directions, which candidate-label selection (KQ1) sidesteps entirely.

### Gaps
- No published measurement of grid overlays on PLAN-level outputs (all measured gains are point-grounding/click tasks); transfer to multi-step plan feasibility is an inference. No 2025–2026 paper found on metric rulers/scale bars specifically for overhead robot-coordination frames.

## KQ5 — Multi-robot VLA / planner models (2026): feasible multi-robot plans from one scene image?

### Takeaway
The strongest 2026 claim with evidence is the MIT REALM PMLR 2026 system: a single overhead image → leader + waypoint plan for 5–50 robots, zero-shot, with measured feasibility and reach rates, and feasibility ultimately guaranteed by the GCBF+ safety layer rather than the VLM. True multi-robot VLAs remain embryonic: MA-VLA covers multi-ARM coordination, decentralized VLM collaboration (D-VLC, COMRES-VLM) covers exploration/search, and no 2026 model was found claiming verifier-free geometrically-feasible multi-robot plan emission. Every credible system keeps a classical safety/verification layer — exactly our architecture.

### Cited Findings
- "Online Motion Planning for Connected Multi-Robot Systems using VLMs as High-level Planners," Garg, Nair, Zhang, Arkin, Fan — PMLR vol (L4DC-style) 2026 (VERIFIED, full text read):
  - Input: base64 JPEG overhead plot (agents blue, goals green, observed obstacles) + textual coordinates + task description; output: strict JSON leader + waypoint list; triggered only on deadlock detection (avg speed < δv while far from goals).
  - Scale: 20 Room envs (N=5), 20 Maze envs (N=25, M=100 obstacles), 11 Maze envs (N=50, M=375).
  - Results (figures; qualitative text VERIFIED): foundation models beat A* high-level planner on reach rate in large-scale Maze and beat it on compute time everywhere (A* cost grows with obstacle count, VLM flat); random leader+waypoints <0.5 reach rate; in small Room envs A* mean reach rate beats VLMs but trails LLMs. VLM tokens ~constant (~1k/intervention) vs LLM tokens growing with scene complexity. GPT-5 at LOW reasoning effort ≈ same reach rate as medium at up to 4x less time, 2x fewer tokens. Low-level GCBF+ layer guarantees safety regardless of VLM output.
  - [PDF](https://mit-realm.github.io/VLM-gcbfplus-website/files/Online_planning_using_VLMs.pdf), [website](https://mit-realm.github.io/VLM-gcbfplus-website/), predecessor [arXiv:2404.06413](https://arxiv.org/abs/2404.06413)
- MA-VLA (2026, UNVERIFIED): multi-arm VLA composing per-arm sub-instruction sequences from a VLM planner + atomic prompt set; claims compositional generalization for collaboration, manipulation-only — [arXiv:2608.25864](https://arxiv.org/pdf/2608.25864)
- D-VLC (2026, UNVERIFIED): decentralized VLM collaboration for heterogeneous embodied multi-robot systems in unknown environments — [arXiv:2607.29009](https://arxiv.org/pdf/2607.29009)
- COMRES-VLM (2025, UNVERIFIED): coordinated multi-robot exploration and search with VLMs — [arXiv:2509.26324](https://arxiv.org/pdf/2509.26324)
- MARS Challenge report (2026, UNVERIFIED): community state of multi-agent robotic systems; relevant for the claim landscape — [arXiv:2601.18733](https://arxiv.org/pdf/2601.18733)
- Compositional Coordination for Multi-Robot Teams with LLMs (2025, UNVERIFIED): LLM decomposes coordination into composable behaviors — [arXiv:2507.16068](https://arxiv.org/pdf/2507.16068)
- "10 Open Challenges Steering the Future of VLA Models" (2025 survey, UNVERIFIED): multi-agent scenarios framed as "high-level planner as orchestrator assigning tasks to low-level action experts" — i.e., the field's consensus architecture matches ours — [arXiv:2511.05936](https://arxiv.org/pdf/2511.05936)
- GameChat (2025): multi-LLM dialogue for multi-agent navigation with safety from CBFs, not from the LLM — [arXiv:2503.12333](https://arxiv.org/pdf/2503.12333)

### Inferences
- Adoptability verdicts and direct steals from VLM-GCBF+ (our nearest neighbor, VERIFIED):
  1. **Trigger-on-deadlock, not continuous querying** — matches our congestion-timeout design; validated at N up to 50.
  2. **Strict JSON output schema stated in prompt** — they credit it for consistent parsing; we already do the grammar analogue.
  3. **GPT-5 low reasoning effort** is their cost/latency sweet spot — worth testing when OpenAI credits return.
  4. **Their feasibility stance = ours**: VLM output is advisory; a provably-safe layer (GCBF+ for them, our leg-by-leg verifier + Nav2/safety invariants) owns feasibility. No 2026 system was found that trusts raw VLM plan geometry.
  5. Their "image tokens stay flat as scene complexity grows" result is a quantified argument for our image+numeric-state hybrid over ever-longer text state.
- No multi-robot VLA claims end-to-end feasible plan emission from one image without a safety layer; treating our verifier as removable is unsupported by any 2026 evidence found.

### Gaps
- Exact per-model feasible-waypoint percentages in VLM-GCBF+ (Fig. 3) and reach-rate bars (Fig. 5) are rendered in figures, not stated in text — if needed for a related-work table, pull from the figures in the saved PDF or the appendix. CoRL/ICRA/RSS 2026 proceedings were not exhaustively swept; a dedicated pass over CoRL 2026 multi-robot VLA papers could still surface a plan-composition-from-marked-candidates paper, though none appeared in any of eight searches.
