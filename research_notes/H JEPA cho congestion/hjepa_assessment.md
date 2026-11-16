# H-JEPA / JEPA Family — Assessment for VGU VLM Swarm

**Prepared:** 2026-10-11
**Question:** Does LeCun's (H-)JEPA line help a thesis on VLM-as-centralized-semantic-coordinator for warehouse swarm congestion resolution (overhead camera + ArUco M1, VLM strategy selection M2, classical verify/repair M3, Nav2 M4)?
**Bottom line (preview):** Related-Work/Discussion contrast + Future Work framing now; optionally a frozen V-JEPA 2 encoder as a conflict-prediction *probe baseline* if time allows. Not a component of v1–v3.

---

## 1. The source: LeCun 2022, "A Path Towards Autonomous Machine Intelligence"

- Position paper (v0.9.2, 2022-06-27), published on OpenReview, not arXiv (a tutorial companion exists as arXiv 2306.02572). Proposes a modular cognitive architecture: configurator, perception, **world model**, cost (intrinsic + trainable critic), actor, short-term memory.
- **JEPA** (Joint-Embedding Predictive Architecture): predict the *representation* of a future/masked signal from the representation of the observed signal, instead of predicting pixels (generative) or using contrastive pairs. Energy-based view: low energy for compatible (x, y) pairs; collapse prevented by regularization (VICReg-style variance/covariance terms, or EMA target encoder). Key claim: abstraction in representation space lets the model **ignore unpredictable detail** — exactly what pixel-space video prediction wastes capacity on.
- **Mode-1 vs Mode-2:** Mode-1 = fast reactive policy; Mode-2 = deliberate planning — optimize an action sequence by rolling the world model forward in latent space and minimizing a cost function (CEM / gradient-based trajectory optimization).
- **H-JEPA specifically adds:** a *stack* of JEPAs at multiple abstraction levels and timescales. Higher levels predict coarser representations further ahead; hierarchical Mode-2 planning decomposes a task top-down — high level produces subgoal representations, lower levels plan short horizons to reach them. In the 2022 paper this was a *proposal with no implementation or numbers*.

## 2. The realized family, with numbers

| Model | Date | What it is | Headline numbers |
|---|---|---|---|
| **I-JEPA** (arXiv 2301.08243, CVPR 2023) | 2023 | Image JEPA: predict masked-region representations with ViT; non-generative SSL | ViT-H/14: ~77% ImageNet linear probe; 2–10x less pretrain compute than MAE/iBOT |
| **V-JEPA** (2024, Meta) | 2024 | Video JEPA, masked spatio-temporal prediction in latent space | Frozen-eval wins on **motion-centric** benchmarks: SSv2 ~72 (ViT-H), where image encoders (DINOv2 etc.) lag badly — evidence that latent video prediction learns *motion*, not just appearance |
| **V-JEPA 2** (arXiv 2506.09985, June 2025) | 2025 | Scaled to >1M hours internet video, ViT-g (~1B) encoder; also LLM-aligned video QA at 8B scale | SSv2 **77.3** top-1; Epic-Kitchens-100 action *anticipation* **39.7 R@5** (beats task-specific models); video QA: PerceptionTest 84.0, **TempCompass 76.9** |
| **V-JEPA 2-AC** (same paper) | 2025 | Action-conditioned post-training on **<62 h unlabeled** DROID robot video -> latent world model; zero-shot planning (CEM over latent rollouts, image goals, no rewards/task training) | Meta's eval, 2 labs, Franka: reach 100%, cup pick-place **80%**, box **65%** (Octo baseline 10–15%); planning on the order of ~16 s per action step |
| **H-JEPA** (arXiv 2610.06805, Oct 2026 — Zhang, Terver, Rabbat, **LeCun**, Balestriero; AMI Labs after LeCun's late-2025 Meta departure) | 2026 | First end-to-end *hierarchical* instantiation: stack of action-conditioned JEPAs, each level predicts further ahead in its own latent space; top-down planning, higher-level predictions = subgoals for level below | Visual AntMaze: 3-level hierarchy **18% -> 73%** success vs flat JEPA, with *less* planner compute; extends to DROID offline planning with inverse-dynamics supervision; code release unconfirmed (too new) |
| **HWM** — "Hierarchical Planning with Latent World Models" (arXiv 2604.03208, 2026) | 2026 | Independent hierarchical latent-MPC; latent macro-actions | Real Franka pick-place from one goal image: HWM 70% vs **single-level (V-JEPA-2-AC-style) 0%** on their 27 start-goal configs; up to 3x less planning compute |
| Adjacent 2025–26 | — | Navigation World Models (LeCun group, CVPR 2025); value-structured JEPA latents for navigation (Dec 2025, ~0.96 acc on specific nav tasks); TD-JEPA latent MPC; **JEPA driving world models** with 21-agent multi-agent inputs (38.7M params); Auto-JEPA (NAVSIM 91.3 PDMS); FactorJEPA (crowded mixed traffic, layout/agent/interaction factorization) | Multi-agent JEPA exists only in *autonomous-driving* form; **no warehouse/fleet/swarm JEPA work found** |

**Replication caveat (important for the thesis):** the HWM paper's independent Franka evaluation got ~0% from a V-JEPA-2-AC-style single-level planner on their configurations vs Meta's in-house 65–80% — latent-planning results are currently highly setup-sensitive and hard to reproduce. Use this when arguing for explicit verification.

**DeepFleet anchor (arXiv 2508.08574, Amazon, 2025):** four model families over *fleet state data* (robot-centric decision transformer, robot-floor cross-attention, conv image-floor, graph-floor GNN+temporal attention), trained on movement data from hundreds of thousands of warehouse robots; Amazon claims ~10% fleet travel-efficiency gain. Note: DeepFleet's best-scaling variants are the **state-vector** ones (robot-centric, graph-floor), *not* the image/conv one.

## 3. Touchpoint assessment

### (a) Congestion forecasting — could a JEPA world model predict jam formation from overhead video? -> **No-help for this thesis; probe baseline at most**

- The modality argument is against us: JEPA's selling point is learning dynamics from raw video *without labels or perception*. But M1 already gives near-perfect state (ArUco world-frame pose + velocity). Once you have state vectors, the natural learned forecaster is a DeepFleet-style state-sequence model (decision transformer / GNN), and DeepFleet itself found the conv-image variant scaled *worst* — evidence that for fleet forecasting, video/image input is the wrong abstraction when state is available.
- Data scale kills training: V-JEPA 2 needed >1M h video; DeepFleet needed Amazon-scale fleet logs. We have a handful of Isaac Sim scenarios and replay logs. Training *any* world model (JEPA or ConvLSTM) to beat hand-designed congestion detection on our data volume is not credible.
- What *is* credible: **frozen V-JEPA 2 encoder + attentive probe** on our overhead replay clips as a *conflict-prediction baseline* — "will these robots conflict in the next T seconds?" binary probe, trained on a few hundred labeled clips. This is exactly the frozen-eval protocol the V-JEPA papers use, runs on one L4, and would sit next to the gpt-4o 9/20 / ER-2 16/20 conflict-prediction probes as a "motion-pretrained SSL encoder" condition. Modest effort (days, not weeks), optional, and the honest expectation is it may win on motion cues while being completely non-semantic (no strategy output).
- Latent prediction also gives no calibrated occupancy/jam map without training a decoder — another piece we'd have to build.

### (b) The VLM temporal weakness — does V-JEPA address it? -> **Diagnosis-help, strongly citable; not an actionable fix in-thesis**

- Yes, conceptually it is *exactly* the gap: our measured gpt-4o temporal inversion (13/15) is consistent with frame-sampled image encoders that carry appearance but no motion features. V-JEPA's defining result is dominance on **motion-discriminative** benchmarks (SSv2) where appearance-centric image encoders fail; and V-JEPA-2-backed video QA scores **76.9 TempCompass** (a temporal-understanding benchmark) — direct published evidence that a latent-video-predictive front-end improves the temporal reasoning class our probes show failing. Cite this in the Discussion as the architectural explanation of the weakness.
- Why it's not a fix we can ship: wiring a V-JEPA encoder into M2 means visual-encoder->LLM alignment training (Meta did it at 8B scale with large multimodal SFT) — impossible against closed APIs (gpt-4o, Gemini/ER-2) and out of budget on one L4 for open models. Our frozen architecture already has the cheap workaround: M1-derived velocity vectors/trails injected into the annotation and prompt (state text substitutes for missing motion features).
- Optional small experiment for the Discussion: run the *temporal-order* probe (which robot moved first / direction of motion) against a frozen V-JEPA 2 attentive probe to show a motion-pretrained encoder passes exactly where gpt-4o inverts. Nice-to-have, not required.

### (c) Latent-space planning vs discrete strategy + classical verification -> **Yes-help: this is the strongest, zero-cost payoff — a Related Work / Discussion contrast**

- Clean dichotomy for the thesis: **LeCun Mode-2** = continuous trajectory optimization (CEM/gradients) over learned latent dynamics against a cost function; **ours (propose–verify)** = a VLM proposes one of a small discrete strategy enum (yield/reroute/convoy/...), a classical verifier grounds and repairs it, Nav2 executes. Contrast axes:
  1. *Interpretability/auditability:* our strategies are human-readable and safety-checkable per command; latent plans are opaque and verification must happen post-hoc in action space.
  2. *Guarantees:* M3/M4 enforce explicit invariants (min distance, speed limits); energy minimization offers no constraint satisfaction guarantees.
  3. *Data:* V-JEPA 2-AC needed 62 h robot interaction video + 1M h pretraining; our pipeline needs zero interaction data (prompting + retrieval).
  4. *Robustness today:* independent replication (HWM, 2604.03208) got ~0% from single-level latent planning where the authors reported 65–80% — supports the thesis position that propose–verify with explicit verification is the certifiable option in 2026.
- **Convergence worth one paragraph:** H-JEPA's 2026 result (hierarchy: slow abstract level emits subgoals for a fast low level; AntMaze 18->73%) is structurally the *same bet* as our two-layer architecture — slow semantic Layer 2 (0.5–2 Hz) emitting discrete subgoals/strategies for fast reactive Layer 1 (20–50 Hz, Nav2). We instantiate the hierarchy with a pretrained VLM + symbolic verifier instead of learned latent levels; both lines agree that *temporal abstraction is where the leverage is*. This legitimizes our architecture from the world-model camp's own newest results.

### (d) Feasibility for a small academic lab -> **Probe-level yes, training/planning-level no**

- Open weights: I-JEPA and V-JEPA/V-JEPA 2 checkpoints are publicly released (GitHub facebookresearch, HuggingFace; V-JEPA 2 in ViT-L/H/g sizes — verify license per checkpoint before any redistribution; V-JEPA 1 was non-commercial). H-JEPA (2610.06805) code release unconfirmed as of 2026-10-11.
- One L4 (24 GB): frozen ViT-L/ViT-H inference + attentive-probe training -> comfortably yes. Fine-tuning ViT-g or any action-conditioned post-training -> no (multi-A100/H100 territory). CEM latent planning at V-JEPA-2-AC scale (~16 s/action) would ironically fit our 0.5–2 Hz Layer-2 cadence, but the model is manipulation-trained — nothing transfers to multi-robot floor dynamics without retraining we cannot afford.
- No existing warehouse/swarm JEPA checkpoint exists to borrow; the multi-agent JEPA work is all autonomous driving.

### (e) Future Work paragraph (ready to adapt)

> The propose–verify architecture deliberately trades predictive foresight for auditability: congestion is detected after onset and resolved by discrete, verifiable strategies. A complementary line, LeCun's hierarchical joint-embedding predictive architectures, has recently moved from proposal (LeCun, 2022) to instantiation: V-JEPA 2 learns action-conditioned latent dynamics from unlabeled video and plans zero-shot on real manipulators (Assran et al., 2025), and H-JEPA shows that stacking predictive levels at multiple timescales — the same slow-deliberative/fast-reactive split this thesis implements symbolically — improves long-horizon planning substantially (Zhang et al., 2026). For warehouse congestion, a JEPA-style world model trained on overhead fleet video or state logs could in principle *anticipate* jam formation seconds before the onset our detector requires, replacing reaction with prevention; Amazon's DeepFleet demonstrates the data appetite and payoff of learned fleet dynamics at industrial scale. The obstacles are equally concrete: such models require data volumes and compute far beyond a single-site deployment, their latent plans resist the safety verification that M3/M4 provide, and independent replications of latent planning remain brittle. A realistic first step is not replacing the coordinator but augmenting its perception: a frozen motion-pretrained video encoder (V-JEPA 2) probed for short-horizon conflict prediction, feeding the same verified strategy pipeline — directly targeting the temporal reasoning deficit measured in current VLMs while preserving the architecture's auditability.

## 4. Verdict

| Touchpoint | Verdict |
|---|---|
| (a) Congestion forecasting component | **No** for v1–v3 (data scale, redundant modality vs M1 state); optional frozen-encoder probe baseline |
| (b) Temporal weakness | **Cite as diagnosis** (SSv2/TempCompass evidence); no in-thesis fix path against closed APIs |
| (c) Architectural contrast | **Yes — use now** in Related Work/Discussion (Mode-2 vs propose–verify; H-JEPA hierarchy <-> our two-layer split; HWM replication gap) |
| (d) Lab feasibility | Probe on L4 yes; training/planning no |
| (e) Future work | Paragraph above |

**Recommendation: related-work contrast now + future-work paragraph; V-JEPA 2 attentive-probe conflict baseline only if schedule allows; do not build JEPA into v1–v3.**

## Sources

- LeCun, "A Path Towards Autonomous Machine Intelligence" v0.9.2 (OpenReview, 2022); tutorial companion arXiv 2306.02572
- I-JEPA: arXiv 2301.08243 (CVPR 2023)
- V-JEPA 2 / V-JEPA 2-AC: arXiv 2506.09985; Meta blog ai.meta.com/research/vjepa/
- H-JEPA: arXiv 2610.06805 (Zhang, Terver, Rabbat, LeCun, Balestriero — AMI Labs, Oct 2026); VentureBeat coverage
- HWM (independent hierarchical latent planning + V-JEPA-2-AC replication gap): arXiv 2604.03208
- DeepFleet: arXiv 2508.08574; amazon.science blog (~10% travel-efficiency claim)
- Adjacent: Auto-JEPA arXiv 2607.29031; FactorJEPA arXiv 2608.01049; JEPA driving world model geographic diversity arXiv 2607.04500; TD-JEPA arXiv 2607.25337; VLA-JEPA arXiv 2602.10098
