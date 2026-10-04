# Review of the user's paper folder (2026-10-04)

Source: `/Users/tuanhdangdinh/Downloads/VLM-Robo/paper-mcp/` (10 papers,
user-collected Apr–Jul 2026). Reviewed by the coordinator against the
registered v2 claims and the three survey rounds.

## Claim-relevant (one required citation found)

**SwarmVLM (arXiv:2508.07814, Zafar et al., Skolkovo, Aug 2025) —
MISSED BY ALL THREE SURVEY ROUNDS; REQUIRED cite for claim 1.**
Read: pp. 1–5 (method + experiments). A ceiling-mounted top-down
camera feeds Molmo-7B-D (4-bit) which extracts obstacle count/spatial
arrangement as TEXT; a naive RAG (FAISS over SIX pre-stored cases)
retrieves impedance parameters (virtual mass/stiffness/damping/force)
for a leader-drone + follower-ground-robot pair; APF does all path
planning. 12 real trials, 11/12 success; VLM-RAG 80% detection in
good lighting (60% poor). Differentiation from claim 1 (all four
axes): (1) the VLM never classifies congestion nor selects among
resolution strategies — it feature-extracts for a 6-row parameter
lookup; (2) no robot–robot conflict exists — two heterogeneous agents
in fixed leader–follower roles avoiding static/dynamic OBSTACLES;
(3) no plans, no commands — output is impedance coefficients;
(4) scale n=2, no fleet. BUT it occupies the surface phrase
"VLM(+RAG) over a top-down warehouse view," and our M3 is literally
RAG — so claim 1's text must name and carve it out, and related work
should also note its cited lineage (ImpedanceGPT, HetSwarm — same
group, same pattern) as the "VLM-tunes-control-parameters" family,
orthogonal to semantic congestion resolution.

## Related-work adds (no claim pressure)

- **Opinion-driven narrow-corridor navigation (arXiv:2504.20947,
  Alghamdi & Park)** — Nonlinear Opinion Dynamics decides who passes
  first through a narrow corridor; decentralized, no VLM. Cite in the
  head-on family's related work as the decentralized
  decision-theoretic alternative to FCFS/AIM-style yielder selection
  (Arm B family context).
- **Voronoi + congestion-metric replanning (arXiv:2202.11334, Arul &
  Manocha)** — decentralized dense-navigation with an explicit
  congestion METRIC triggering replanning; cite as the classical
  congestion-metric lineage behind our detector's congestion framing.
- **Congestion-aware MAPF for pick-up & delivery (GECCO '25,
  10.1145/3712256.3726339, Asadi, Nowé, Ghofrani)** — evolutionary
  congestion-aware lifelong MAPF; classical baseline-family cite
  alongside RHCR.
- **SocialNav-SUB (arXiv:2509.08757)** — VLM scene-understanding QA
  benchmark for social navigation; the nearest published kin to our
  capability-probe battery. Cite when introducing the battery;
  differentiate: ours uses the system's OWN frames with GT-derived
  answers as a per-backend PRE-TEST, not a general benchmark.
- **NaVid (2402.15852), CronusVLA (2506.19816), ContextVLA
  (2510.04246)** — single-robot VLN/VLA showing temporal/multi-frame
  context materially helps embodied decisions (training-side).
  Cite in the multi-frame A/B cell's rationale as convergent
  evidence; none touches multi-robot coordination.
- **Co-NavGPT (2310.07937)** and **Garg/MIT-REALM PMLR** — already in
  rounds 1–3; folder copies match the cited versions.

## Verdict

No claim is scooped. One wording action: claim 1 gains an explicit
SwarmVLM carve-out. Six new related-work citations adopted. The
survey-miss root cause: SwarmVLM's terms ("impedance control",
"heterogeneous") sit outside the congestion/deadlock/coordination
query space all three rounds used — worth one defensive line in the
thesis's search-method appendix.
