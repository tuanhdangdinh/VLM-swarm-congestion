# Research Findings Register

**Prepared:** 2026-09-18

**Revision history:**

- Initial draft (2026-09-18): consolidates findings from the 2026-09-16 → 2026-09-18 verification, camera-localization, failure-context, and Gemini Robotics-ER 2 work into research-usable claims.
- Rev 2 (2026-09-18): folds in the `gpt-4o` cross-check matrix (report Experiment 6, open item 2). **A6 is now known to be model-specific, not apparatus-wide** — the same prompt change gives 10/10 on ER-2 and 1/10 on `gpt-4o`. A3 amended with the prompt-level-vs-model-specific reading and a minimal-ontology-fix recommendation; A1 strengthened at matched n; A4 extended to n = 50 and narrowed; new A8 records the confabulated-justification hazard the cross-check introduces. Open item 2 closed.

---

## Purpose

This register separates **what we have evidence for** from **what we could claim**. Each entry states the claim, the evidence with its sample size, and the research angle it supports. It is not an implementation log — that is `docs/implementation_notes.md`, which this file links rather than duplicates.

Sample sizes are small almost everywhere. Every entry marked **directional** needs the paired-seed matrix (`docs/superpowers/plans/2026-07-08-congestion-reasoner-phase1-core.md`) before it appears in a written claim.

---

## A. Apparatus validity — what the experiment actually measures

These are the highest-value findings because they determine whether any downstream result means what it appears to mean.

### A1. Arm A is text-driven by construction, for every model

**Claim.** The VLM layer does not use the camera image to reach its congestion decision. It performs arithmetic on M1's derived numeric state; the image is attached and ignored.

**Evidence.** A 2×2 congruent/incongruent design (`docs/reports/2026-09-18-gemini-er2-image-grounding.md`, Experiments 2, 3, 5, 6) on matched real frames — one with robots 0.251 m apart, one with 4.884 m, both measured, not eyeballed. Both models now at n = 5, one apparatus, both congruent gates passing 5/5:

| Condition | Gemini ER-2 | gpt-4o (temp 0.0) |
|---|---|---|
| image conflict + text clear | 0/5 image-consistent | 0/5 |
| image clear + text conflict | 0/5 image-consistent | 0/5 |

No justification in 42 ER-2 calls or 37 gpt-4o calls under the production prompt cited visual evidence; none acknowledged the contradiction. The gpt-4o half was re-run at n = 5 rather than reusing the n = 3 numbers, and **replicates them exactly** (cell A `deadlock`/`yield` 5/5, D `none` 5/5, B `none` 5/5, C `deadlock`/`yield` 5/5), with 0/25 justifications mentioning the image.

**Narrowed (Rev 2).** The earlier observation that gpt-4o's outputs were "byte-identical across repeats at temperature 0.0" held at n = 3 but **fails at n = 5**: raw responses were unique in 2–5 of 5 repeats per cell. Temperature 0.0 on this hosted endpoint is near-deterministic, not deterministic — so every gpt-4o "5/5" in this register carries roughly the information of n = 1 plus a stability check, and any single-call exception must not be over-read.

**Cause.** Our own prompt (`reasoning/vlm/prompt_builder.py:82`): *"Use the pairwise geometry above; do not re-derive distances or facing from the coordinates."* That clause is load-bearing — it is Fix B, and removing it regresses the run-3 failure in D5.

**Research angle.** A negative/ablation result with a reusable method: *how much does the visual channel contribute to VLM-mediated multi-robot coordination?* The honest answer for this apparatus is currently "nothing", and that is publishable. It also forces a framing decision on the whole thesis (see Recommendation 1).

### A2. Perception and decision-grounding are dissociable

**Claim.** A model can localize the robots precisely and still not use that perception in its decision.

**Evidence.** On the same frames where its decisions ignored the image, ER-2's native pointing output hit both robots 12/12 within the pre-stated ring: error 0.005–0.016 m (1–4 px) on the conflict frame, and the separation between its two returned points was 0.245–0.257 m against a true 0.251 m — so it resolved two distinct robots a quarter-metre apart, not one blob twice.

**Research angle.** A measurable dissociation between capability and use. Embodied-reasoning models appear to need explicit licence to let perception override structured state input — which is a claim about prompt/interface design, not about model capability.

### A3. The decision ontology conflates "sensors disagree" with "robots conflict"

**Claim.** Given a genuine image/state contradiction, a model that detects it classifies it into the wrong category, which would dispatch the wrong command. **Directional** on the prompt-level reading (see below).

**Evidence — ER-2 (n = 5).** With the cross-check modality enabled (A6), the "image says conflict, text says clear" cell returned `type=anomaly` with `priority_override`/`reroute` in 4 of 5 calls, rather than `deadlock` with `yield`/`reverse`. The model treats the tracker disagreement itself as the anomaly. Detection 5/5 correct, classification 1/5 correct.

**Prompt-level or model-specific? (Rev 2 — the question open item 2 was run to answer.)** `gpt-4o` was put through the same cell with the same prompt at n = 5 (report Experiment 6). The answer is *neither cleanly*, because gpt-4o's failure sits one step upstream:

| Cell B, cross-check on | ER-2 (n = 5) | gpt-4o (n = 5) |
|---|---|---|
| Did not detect (`type=none`) | 0 | **4** |
| Detected, classified correctly (`deadlock` + `yield`/`reverse`) | 1 | **0** |
| Detected, misclassified | 4 (`anomaly` + `priority_override`/`reroute`) | **1** (`crowding` + `reroute`) |

What this supports, in descending order of confidence:

1. **The specific `anomaly` signature is ER-2-specific as measured.** gpt-4o never returned `anomaly` or `priority_override`.
2. **Misclassification-on-detection is not ER-2-specific — but it is a *different kind* of error on each model, and the two must not be pooled.** Across both models, 6 detecting calls produced 1 correct classification and 5 misclassifications. But:
   - **ER-2 mislabelled the input-integrity condition.** `anomaly` + `priority_override` treats the tracker disagreement *itself* as the thing being classified. That is evidence of a **missing slot** in the enum, which is what A3's claim asserts.
   - **gpt-4o mislabelled the physical configuration.** Its detecting call perceived the image correctly and named the disagreement in prose (*root_cause: "Both robots are in close proximity in a narrow aisle"*; *justification: "indicating crowding despite the pairwise distance"*), then chose `crowding` for two robots nose-to-nose in a corridor — where `deadlock` was available, defined in the prompt, and correct. That is a **wrong choice among existing slots**, not a missing one.

   So A3's claim as stated — that the ontology conflates "sensors disagree" with "robots conflict" — **still rests on ER-2 alone**. A new `state_disagreement` type would have prevented ER-2's error and would **not** have prevented gpt-4o's. What the second model adds is that *something* goes wrong at the classification step on more than one model, not that the *same* thing does. **Directional, and thinner than a pooled 5-of-6 would suggest:** n = 1 codable call for gpt-4o, one scenario, one contradiction direction, near-deterministic decoding (A1).
3. **A3 is no longer the binding blocker for the `openai` arm.** A3 framed the problem as "detects correctly, classifies wrongly" — true of ER-2. For gpt-4o the flag mostly does not detect at all (A6), so fixing the ontology would unblock the flag for `gemini` and leave `openai` exactly where it is. **Cell C carries no A3 information** and is excluded from these counts: its correct answer is `type=none`, so there is no classification to get right or wrong. A3 rests on cell B for both models.

**Minimal ontology fix (recommendation only — not implemented, and deliberately out of scope of the Experiment 6 run).** Scope first: this addresses **ER-2's** error, the missing slot. It does nothing for gpt-4o's error, which was a wrong pick among slots that already exist and needs a different remedy (and, on the `openai` arm, is downstream of the A6 non-detection problem anyway). The smallest change that gives a model a right answer to reach for is one of:

- **A distinct decision type** for input-integrity conditions, e.g. `type="state_disagreement"` paired with a non-actuating strategy (`temporary_wait` or a new `resense`/`hold`), so "the tracker and the camera disagree" cannot be expressed as a world condition at all. Cost: a schema change in `reasoning/vlm/models.py`, the enum in the prompt, and M3/M5 consumers.
- **Or an explicit precedence rule in the prompt**, leaving the enum alone: state that when the image contradicts the states, the decision must describe *the physical configuration seen in the image* and the disagreement belongs in `root_cause`/`justification`, never in `type`. Cheaper, no downstream change, but it relies on instruction-following — which Experiment 6 shows is exactly what does not transfer across models.

The first is the more defensible research contribution; the second is the cheaper experiment. Either needs re-measuring on both arms, because the flag's effect proved model-specific.

**Research angle.** The strategy/type enum (`none | deadlock | bottleneck | crowding | anomaly`) has no category for *state-estimation disagreement*, which is an input-integrity condition rather than a world condition. This is a small, concrete contribution to decision taxonomies for sensor-mediated coordination — and it is a prerequisite for shipping A6 on the `gemini` arm.

### A4. A visible reasoning trace can be an empty shell

**Claim.** The presence of a `<think>` block is not evidence that reasoning was externalised.

**Evidence.** gpt-4o emitted a `<think>` block in 12/12 calls whose content was a verbatim echo of the prompt's own template sentence. ER-2 emitted none in 50 calls while billing 121–470 thought tokens per call.

**Extended and narrowed (Rev 2, n = 50 more gpt-4o calls — report Experiment 6).** Presence replicates: **25/25 in each variant**. The "always an empty shell" reading does not: the content is a pure template echo in **23/25** (cross-check off) and **19/25** (cross-check on), so 2/25 and 6/25 carried real reasoning appended after the echo. The shell is therefore usual, not universal.

**The interesting part is where the content is not.** All six non-echo blocks in the cross-check-on variant fall in the *congruent* cells (D, E). In the two contradiction cells the block is a pure echo **10/10** — i.e. the trace acquires content exactly where the task is easy and stays empty where the model has a genuine contradiction to resolve. Recorded as an observation over 50 calls, not a mechanism, and not a hypothesis test.

**Research angle.** Trace-based interpretability and trace-comparability claims need validation, not assumption — and a per-call presence rate is not enough; the content has to be checked against the prompt's own template and stratified by task difficulty, or an echo passes for reasoning. Incidentally this defuses a confound we had recorded against ER-2: there was little reasoning content in the other arm's trace to lose.

### A5. Hosted models differ in which decoding controls exist at all

**Claim.** Cross-arm decoding comparability cannot be assumed for API-hosted models.

**Evidence.** The Gemini Interactions API `generation_config` exposes no `temperature`, `top_p`, `top_k` or `presence_penalty` — only `max_output_tokens`, `seed`, `stop_sequences`, `thinking_level`, `thinking_summaries`, `tool_choice` and media configs (verified against the live API, 2026-09-18). Our `openai` arm is pinned to temperature 0.0 for the documented reason in D5; ER-2 cannot be pinned equivalently. `seed` yields a reproducible sample, not the distribution mode. Separately, the `anthropic` backend silently discarded these same parameters and was absent from the parent spec's decoding-preregistration table.

**Research angle.** A reproducibility hazard specific to API-hosted model comparisons. Our mitigation is itself a method worth stating: record the unhonoured parameters *in the run artifact* (`unsupported_sampling`, commit `85b4b18`) so the confound appears in the data rather than in a footnote.

### A6. Instruction was the binding constraint **for ER-2 only** — a prompt-level change with a model-level effect

**Claim (amended, Rev 2).** Adding an explicit image/state cross-check instruction makes the image decisive on Gemini ER-2, without reopening the failure it was originally suppressing. **The same instruction does not work on gpt-4o.** So "instruction, not capability, was the binding constraint" is a claim about the `gemini` arm, not about the apparatus.

**Evidence — ER-2.** `include_visual_crosscheck` (opt-in, default off, commit `467d3db`). Incongruent cells move from 0/10 to **10/10 image-consistent** at n=5 per cell. Congruent gates hold 5/5 both ways. A dedicated regression cell reproducing the run-3 geometry — 1.20 m apart, |Δθ| = π, diverging, both MOVING — stayed no-congestion 5/5 under both variants, so Fix B survives. Cost: +174 prompt tokens, latency 2819 → 3701 ms.

**Evidence — gpt-4o (Rev 2, report Experiment 6, open item 2).** Same two stimuli, same five cells, same prompt, same pre-stated ≥ 3/5 criterion, n = 5 per cell per variant, temperature 0.0 resolved from `config/models.yaml`:

| Incongruent cells, cross-check on | ER-2 | gpt-4o |
|---|---|---|
| answered per the image | **10/10** | **1/10** |
| flagged the disagreement (pre-stated rule) | 8/10 | 0/10 |
| flagged the disagreement (manual read of rule misses) | 10/10 | 1/10 |

Both congruent gates passed 5/5 in both variants, so the cells are interpretable; the criterion is missed in **both** discriminating cells (B 1/5, C 0/5). The regression cell E held no-congestion 5/5 in both variants, so the pre-stated hard-fail (E flips to deadlock, making the modality unsafe on the production arm) **did not occur** — gpt-4o fails on effectiveness, not on safety. Cost on this arm: +169 prompt tokens, latency essentially unchanged (2185 → 2209 ms), consistent with the model doing no extra work on the contradiction.

**Research angle.** The interesting result is the *dissociation between the level of the intervention and the level of the effect*: an identical prompt edit inverts one model's decisions completely and moves another's by one call in ten. That is a direct caution against the common practice of reporting a prompt-engineering fix on one model as a property of the pipeline — and it is cheap to test for, with the same 2×2 (E1).

**Caveats.** Still blocked on A3 for the `gemini` arm; still untested whether either model consults the image when the channels *agree* (the gates cannot distinguish "always looks, rarely disagrees" from a no-op); contradictions extreme by construction; and the block's wording was frozen against ER-2's behaviour before any gpt-4o call, so "does not transfer" is a statement about **this** block, not about the non-existence of a block that would work on gpt-4o.

### A7. Ground-truth vs sensor-derived disclosure

**Claim.** The apparatus's sensing is now genuinely sensor-derived where it matters, and the remaining scripted components are enumerated.

**Evidence.** Appendix A.7 of `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`. Localization moved from ground truth to camera-derived (M1 pose ∘ inverse odom) at 0.4–2.9 cm vs ground truth, no degeneracy. M3's yield sizing remains geometric templating from a declared `scenario_geometry` block, not retrieval — the largest remaining scripted component.

**Research angle.** A disclosure standard for simulation-based robotics claims: which layers are oracle-fed, which are sensed, which are scripted. Reviewers rarely get this and it is cheap to provide.

### A8. A cross-check instruction can manufacture false visual corroboration

**Claim.** Asking a model to check the image against the state block can change what its justification *claims* without changing its decision — producing text that asserts a visual check was performed and passed, on calls where it demonstrably was not.

**Evidence.** gpt-4o, report Experiment 6, n = 25 per variant. Justifications mentioning the visual channel rise from **0/25** (cross-check off) to **18/25** (on), and to 10/10 in the contradiction cells. **9 of those 10 assert the image agrees with the states**, while the attached frame grossly contradicts them — e.g. cell C, 3/5 calls verbatim: *"The pairwise geometry indicates a head-on deadlock, and the image confirms the robots are facing each other in a narrow aisle"*, against a frame showing the robots 4.9 m apart at opposite ends of the aisle. The decision was unchanged from the off variant in 9/10 of those calls.

**Research angle.** A concrete interpretability hazard, and one that cuts against a natural mitigation: "ask the model to justify against the image" makes the log *look* grounded exactly where grounding failed, so justification text cannot be used as evidence of image use. It also matters for any pipeline that logs justifications for human review or feeds them to a downstream reasoner (our failure-context mechanism, B2, does the latter). The paired off-variant is what makes the claim measurable: the same model, same stimulus, same decision, different claim about how it was reached. **Directional** — one model, one prompt, n = 10 contradiction-cell calls.

---

## B. Multi-robot coordination — strategy-level findings

### B1. Symmetric strategies cannot resolve a head-on deadlock

**Claim.** `reverse`, dispatched to both robots simultaneously, cannot resolve a two-robot head-on standoff in a corridor. Symmetry-breaking is necessary.

**Evidence.** Observed live in the ER-2 run (`gemini_20260918_084649`): analysis 1 chose `deadlock`/`reverse`, both robots backed up and the command resolved `completed`, yet the next analysis found them 1.29 m apart "both currently moving" and they re-converged. Analysis 3 chose `yield` (asymmetric) and it cleared. n=1 run, but the mechanism is deterministic rather than statistical.

**Research angle.** The cleanest standalone result available. It is formalisable: partition the strategy enum into symmetry-breaking and symmetry-preserving, and show that in a corridor narrower than twice the robot width plus clearance, a symmetry-preserving strategy cannot change the conflict's topology. Then validate in sim across seeds. Low risk, tight claim, and it connects to the deadlock literature already collected.

### B2. Failure context changes a real subsequent decision

**Claim.** Supplying the outcome of a failed prior attempt changes the next strategy choice, live, on a real scenario rather than a fixture.

**Evidence.** Same run, analysis 3, verbatim: *"Since the previous attempt to reverse both robots did not successfully resolve the deadlock, the yield strategy is now selected to have robot_1 back up while robot_2 waits."* This is the first live evidence for the closed-loop mechanism on branch `feat/failure-context-closed-loop`; earlier evidence was fixture-level. Prior runs 1–5 provide the aggregate context-attachment rates.

**Research angle.** RQ5 (closed-loop adaptation), with attempts-to-resolution as the dependent measure. Pairs naturally with B1: the mechanism's first correct act was to escape a symmetry trap.

### B3. Congestion onset is bimodal

**Claim.** Once robots are mutually lidar-visible, deadlock onset arrives either as a planner stall at ~1 m or as a tight standoff, not as a single characteristic mode.

**Evidence.** Observed across runs 4 and 6 (2026-09-16 notes). Not yet characterised across seeds.

**Research angle.** Trigger design and onset taxonomy; needs multi-run characterisation before Arm A/B collection. **Directional.**

### B4. Arrival and stall detection interact badly

**Claim.** Robots parked at their goals are read as stalled and re-trigger analyses, producing spurious congestion events and occasionally spurious yields.

**Evidence.** Runs G/H (2026-09-16/17): M1's camera-derived distance-to-goal sat outside `goal_reached_tolerance_m` 0.15 while ground truth said 0.06. Fixed by the detector's goal-tolerance skip (`d40f009`) and `mark_arrived` (FR5.1.8); run 5 showed zero analyses after both arrivals.

**Research angle.** Termination detection in centralized coordination — a mundane but real source of phantom events in any stall-triggered architecture.

---

## C. Systems and sensing — lessons with publishable methods content

### C1. A safety invariant that never fired, for weeks

**Claim.** The safety latch was a silent no-op: `cancel_goals_async` does not exist on rclpy's `ActionClient`, and the call sat inside a bare `except` in two separate files. Latched robots kept being driven into contact by the local planner.

**Evidence.** Verified against the rclpy Jazzy source; fixed in `5f9394a` and `bbcfe85` with a real cancel-all via the `CancelGoal` service plus a cmd_vel relay that zeroes any robot in `/safety/holds`. Run H then showed robots stopping at ~0.17 m with 0.5 mm drift over 100 s.

**Research angle / methods.** Found by a human watching a recording, not by the test suite — which passed throughout. The lesson generalises: for safety invariants, *absence of an error is not evidence of action*. Negative-path assertions (did the goal actually get cancelled?) are the missing test class. This is strong material for a systems-lessons section and it is the kind of thing reviewers remember.

### C2. Fiducial tracking goes blind exactly in the configuration of interest

**Claim.** ArUco-based tracking fails at the moment of closest approach, which is precisely the state the coordinator needs to observe.

**Evidence.** At 0.076 m nose-to-nose the marker quads overlap and M1 reports STALE rather than STOPPED (mitigated by `stale_after_sec` 3.0 and `velocity_alpha` 0.15, not solved).

**Research angle.** Argues for close-range sensor fusion, and is a concrete instance of a general point: the sensing modality's failure region coincides with the decision's critical region.

### C3. Annotating frames for the VLM destroys them for reuse

**Claim.** The same annotation that makes a frame legible to the VLM makes it unusable for fiducial re-detection.

**Evidence.** M1's 40×40 px status box and velocity arrow are drawn over the 28 px marker and destroy its quiet zone: both markers recovered in only **3 of 121** sampled frames, and relaxed detector parameters produced false IDs (17/37/45). Ground truth for the grounding study had to come from M1's scene log matched on the recorder's burned-in timestamp, validated to ~1 mm against re-detection where both existed.

**Research angle.** A pipeline design finding — annotation-for-consumption versus annotation-for-provenance are different artifacts and should be stored separately. Also a practical warning for anyone reusing annotated frames as evaluation stimuli.

### C4. Calibration must target the measurement plane, and golden tests can enshrine the bug

**Claim.** Computing the homography to the ground plane while the markers sit at z = 0.21 m produced a 7.5 % radial bias; the existing test oracle had encoded that bias, so the test passed.

**Evidence.** One-line fix in `isaac/vgu_sim/calibration.py` (`cam_center = position_m - [0, 0, plane_height_m]`); scale 0.004686 → 0.004358 m/px, offsets −2.999/2.249 → −2.789/2.092. Error at spawn dropped to ≤ 1 cm.

**Research angle / methods.** Regression tests written against a biased implementation certify the bias. Oracles need independent derivation.

### C5. External camera localization beat onboard scan matching during maneuvers

**Claim.** For an overhead-camera warehouse, camera-derived localization is more robust than AMCL through close-quarters maneuvers.

**Evidence.** Camera (`map→odom = T_map_base ∘ T_odom_base⁻¹`): 0.4–2.9 cm mean vs ground truth, no degeneracy. AMCL with a per-scenario map: 2.2 cm mean while in or near the corridor, but the estimate jumped ~2 m into occupied map space during and after the yield, after which goals failed. Root cause of the initial 1 m AMCL error was a base map generated before the aisle barrier existed.

**Research angle.** A localization-modality comparison under maneuver stress, with a concrete failure mode rather than an average-error table. **Directional** — one scenario.

### C6. Verify the oracle before trusting it

**Claim.** Two independent ground-truth defects would each have corrupted results silently.

**Evidence.** The GT logger read the static root Xform instead of the chassis prim (fixed, then verified to four decimals against odometry); and sim time counted one `physics_dt` per `app.update()` while physics stepped twice, making the time axis ~1.9× off (fixed via `sim_ctx.current_time` anchored at loop start). Also, Fabric and USD poses diverge under the Newton backend unless explicitly synced.

### C7. Transport-level silent data loss

**Claim.** DDS shared-memory transport silently drops all host↔container traffic, presenting as a hang rather than an error.

**Evidence.** Requires `FASTRTPS_DEFAULT_PROFILES_FILE` forcing UDPv4 for host Isaac launches. Related: `ros2 topic pub --once` fails silently because the publisher exits before DDS matching completes.

---

## D. Model and provider characteristics

### D1. Cost and latency

| | ER-2 | gpt-4o |
|---|---|---|
| per analysis | ≈ $0.0032 | ≈ $0.006 (measured earlier); ≈ $0.0053/0.0059 off/on (n=25 each, Rev 2) |
| latency | 2.5–3.8 s | 2.7–4.9 s; mean 2.19/2.21 s off/on (n=25 each, Rev 2) |
| mean total tokens | 2297 (n=5) | 1826 (n=3); 1747/1931 off/on (n=25 each, Rev 2) |

ER-2 was ~12 % faster and ~26 % more tokens, the gap being thought tokens with no gpt-4o counterpart. Pricing $1.00/1M input and $5.00/1M output through 2026-12-31, doubling 2027-01-01; a free tier exists. **Directional** at these sample sizes.

**Rev 2 addition.** The cross-check block's cost differs sharply by arm, which is itself a signal: on ER-2 it raised mean latency 2819 → 3701 ms and mean thought tokens 287 → 470, concentrated in the contradiction cell; on gpt-4o it raised latency by 24 ms (2185 → 2209) for +169 prompt tokens. The arm that used the instruction paid for it; the arm that did not, did not (A6).

### D2. Schema conformance without forcing

ER-2 returned first-attempt valid decisions in 5/5 live-run calls and across all 50 grounding calls with `response_format` **disabled**. The untagged historical gpt-4o artifact pool runs 492 valid / 14 invalid / 10 failed (n=516, 4.7 % non-valid). **Directional**, but it justifies keeping `force_schema: false` and preserving the prompt contract.

### D3. Decoding temperature behaves as a safety parameter

**Claim.** Sampling temperature changed a coordination decision from correct to hazardous.

**Evidence.** At temperature 0.6, gpt-4o matched |Δθ| ≈ π on two robots driving *apart*, answered `deadlock`/`reverse`, and M3/M4 backed a robot that was already at its goal into the aisle — manufacturing a real deadlock and a yield/reverse oscillation. Pinning to 0.0 (`vlm.openai.reasoner.temperature`) eliminated it; run 4 then gave 32 analyses, 1 dispatch, 31 `none`.

**Research angle.** A tight, quantifiable claim: decoding temperature is a safety-relevant parameter in embodied decision loops, with a concrete mechanism (spurious geometric pattern matching) and a concrete consequence (a physical deadlock created by the resolver). This is one of the most publishable single findings in the register.

---

## E. Methodological contributions

- **E1. The contradiction 2×2** as a cheap, general validity probe for any VLM-in-the-loop system: present matched congruent and deliberately incongruent (image, state) pairs and see which channel the decision follows. 12 calls and a few cents answered a question that a year of average-accuracy metrics would not have.
- **E2. Pre-stated criteria plus anti-degeneracy guards.** In the pointing experiment, the natural "within half a robot width" criterion is degenerate for a 0.25 m pair — half the separation falls inside the hit ring, so reporting one blob twice would pass. Fixed by forcing one-to-one assignment and reporting the *returned inter-point separation* against the true one.
- **E3. Instrument confounds into the artifact.** Recording unhonoured sampling parameters per call (`unsupported_sampling`) turns a documentation problem into data.
- **E4. Provenance under sensor degradation.** When re-detection on stored stimuli is unreliable (C3), recover ground truth from the logged scene state matched on a burned-in timestamp, and cross-validate where both are available.

---

## Open items gating any data collection

1. **A3** — the state-disagreement category, before `include_visual_crosscheck` is used for anything live on the `gemini` arm. Now scoped by item 2's outcome: A3 is the binding blocker for `gemini`, not for `openai`.
2. ~~**gpt-4o with the cross-check enabled** — the symmetric half of A6, never run.~~ **Done (2026-09-18, report Experiment 6, 50 calls).** Outcome: **the fix does not transfer** — 1/10 image-consistent against ER-2's 10/10, gates 5/5 both variants, regression cell E clean 5/5 both variants. Consequences folded into A6 (now scoped to ER-2), A3 (misclassification not ER-2-specific but not confirmable as prompt-level either, since gpt-4o mostly fails to detect at all; minimal ontology fix recommended there), A1 (matched n = 5 baseline replicates; temperature-0.0 determinism narrowed), A4 (extended to n = 50, echo rate narrowed), and new **A8** (the cross-check manufactures false visual corroboration on gpt-4o). **New open item:** whether a wording tuned for gpt-4o could work is untested — but note that if the flag needs per-model wording, it is a per-arm confound in any Arm A/B comparison, which is a reason to prefer the A3 schema fix over prompt tuning.
3. **Scenario battery (T2/T3)** — forced-failure yield, three-robot bottleneck, object blocker. Isaac/USD and Nav2 work; still the gating item.
4. **Paired-seed Arm A/B matrix** — every entry marked *directional* depends on it.
5. **Prompt-variant declaration** — parent spec Rev 8.6 requires every reported Arm A decision to name its prompt variant.
6. **Branch hygiene** — `feat/gemini-er2-backend` stacks on the unmerged `feat/failure-context-closed-loop`.

---

## References

- `docs/reports/2026-09-18-gemini-er2-image-grounding.md` — Experiments 1–5, stimuli, pre-stated criteria.
- `docs/superpowers/specs/2026-09-18-gemini-robotics-er2-integration-design.md` — ER-2 transport, confounds, backend design.
- `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md` — rev-8 experiment design; Appendix A.7 disclosure; modality table (Rev 8.6).
- `docs/superpowers/specs/2026-09-17-failure-context-closed-loop-design.md` — closed-loop memory mechanism.
- `docs/implementation_notes.md` — dated implementation log for every fix cited here.
- `docs/reports/2026-09-17-failure-attribution-ladder.md` — attribution framework.
