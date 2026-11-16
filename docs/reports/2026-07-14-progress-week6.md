# Weekly Progress Report — Week 6

**Project:** Leveraging Vision-Language Models (VLM) and Retrieval-Augmented Generation (RAG) for Congestion Management in Warehouse Swarm Robotics
**Student:** Dang Dinh Tu Anh (10422086) · **Supervisor:** Dr. Vo Bich Hien
**Vietnamese-German University, Department of Computer Science**
**Period:** 08–14 July 2026 · **Report date:** 14 July 2026

> This is an individual capstone project. Contributions are attributed by role and module rather than by person.

---

## I. Abstract / Project Overview

Week 6 was a deliberately documentation-focused week: no new system code was written, and the controlled runs projected in last week's plan were **not** collected. Instead, the effort went into converting Week 5's experimental design into an executable form. The design specification advanced from revision 7 to revision 8, gaining a statistical plan, a full specification of the second experimental arm (Arm B, a classical reasoner used as a like-for-like baseline against the VLM), a preregistration draft, and an apparatus appendix. A detailed, task-by-task implementation plan for the offline reasoning core was then written, so that the reasoning-side code Arm B requires can be built without ROS2, Isaac Sim, or network access. Finally, the project's implementation-notes log was established and the engineering-standards document was updated. The week's honest characterisation is that it produced plans and specifications rather than results — a consolidation step that reduces execution risk before the reasoning-core build begins. The preregistration cannot yet be frozen because the exact VLM model identifiers remain to be locked. Next week will lock those identifiers and begin implementing the reasoning core against the new plan.

## II. Completed Tasks

| # | Task | Role / module | Outcome |
|---|------|---------------|---------|
| 1 | **Experiment design advanced to revision 8** | Research design | The spatial-congestion-resolution design gained a statistical plan, a preregistration draft, and an apparatus appendix, and was expanded substantially (~630 lines added) into a preregistration-ready form |
| 2 | **Arm B (classical reasoner) specification** | Research design / baselines | A full specification of the second experimental arm: a deterministic classical reasoner that emits the *same* `CongestionDecision` type as the VLM, so grounding, validation, and execution are shared by construction and the two arms differ only in the decision source |
| 3 | **Phase-1 reasoning-core implementation plan** | Planning | A task-by-task plan (`docs/superpowers/plans/2026-07-08-congestion-reasoner-phase1-core.md`) for the offline reasoning core: stage-1/stage-2 VLM contracts, temporal/failure/modality prompt machinery, derived-geometry grounding (the design's Pillars 1, 2, and 4), and the Arm B reasoner with shadow comparison — all pure Python under `reasoning/`, unit-testable without ROS2 |
| 4 | Implementation-notes log established | Documentation | `docs/implementation_notes.md` created as the project's living, append-only implementation log, with a maintenance rule added to `CLAUDE.md` (rev 4) |

The week's purpose was to make the next block of work safe to execute rather than to execute it. Two design decisions drove this. First, Arm B was specified to reuse the VLM's exact decision contract, which means the experiment compares two *decision sources* through an identical downstream pipeline rather than comparing two whole systems — a cleaner, more defensible comparison. Second, the reasoning core was scoped as pure, offline Python so that the bulk of the remaining implementation can be built and unit-tested on the development machine, without the ROS2 and Isaac Sim environment that has been the recurring source of friction. The implementation plan also locks a number of decisions the specification left under-determined (clearance constants, feasibility scanning, and the classical type mapping), so those do not have to be relitigated during the build.

## III. In-Progress / Ongoing Tasks

- **Preregistration freeze — blocked on model identifiers.** The preregistration is drafted as part of revision 8, but it cannot be frozen until the exact VLM model identifiers (and their versions) are locked, since the design's validity depends on naming what is being tested. *Next action:* select and pin the model identifiers. *Target:* Week 7.
- **Reasoning-core implementation — planned, not started.** The Phase-1 plan is complete and reviewed, but no code has been written against it. This is the immediate next block of work. *Target:* Weeks 7–8.
- **Controlled experimental runs — not started.** No data has been collected; execution depends on both the frozen preregistration and the reasoning-core build. *Target:* Weeks 8 onward.
- **M3 RAG action grounding — subsumed into the reasoning-core plan.** The previously outstanding RAG grounding work is now folded into the Phase-1 plan as the derived-geometry grounding step, rather than remaining a separate placeholder.
- **Open Nav2 recovery-loop item (yield pull-off) — still open.** Carried over from Week 5; not addressed this week.

## IV. Outcomes & Achievements

The week's principal output is a preregistration-ready experimental design and a complete implementation plan for the reasoning core — the two artifacts needed to turn the working demonstration from Week 5 into measured evidence. The advance to revision 8, incorporating a statistical plan and a specified baseline arm, means the experiment now has a defined comparison, defined metrics, and a defined analysis, rather than an intention to compare. The Arm B design is a genuine methodological result: by having the classical baseline emit the same decision type as the VLM, the study isolates the contribution of semantic reasoning while holding perception, grounding, and execution constant. In engineering terms the week was light — three documentation commits and no new tests — which is stated plainly here; the value delivered is reduced risk and a clear, ordered path for the implementation weeks that follow. The new implementation-notes log also improves the project's traceability going forward.

## V. Challenges, Risks & Mitigation

- **Model-identifier lock is a hard prerequisite.** The preregistration cannot be frozen, and therefore no confirmatory runs can begin, until the specific VLM models are chosen and pinned. *Impact:* blocks the entire experimental phase. *Mitigation:* model selection is the first task of Week 7; the design is otherwise complete, so this is the only remaining gate.
- **Schedule pressure from a planning-heavy week.** A week spent on documents rather than code compresses the time available for implementation and data collection. *Impact:* the evaluation timeline tightens. *Mitigation:* the reasoning core was deliberately scoped as offline, unit-testable Python so it can be built quickly and in parallel with environment work; the detailed task plan removes design decisions from the critical path.
- **Scope of the reasoning core.** The Phase-1 plan is large and touches many `reasoning/` modules. *Impact:* risk of regressions in the working M2 pipeline. *Mitigation:* the plan mandates additive-optional schema changes, a default `legacy` grounding mode that keeps live behaviour byte-identical, and the existing unit tests staying green unmodified.

## VI. Plan for Next Week

Week 7 converts the plans into code and unblocks the experiment. The first action is to lock the VLM model identifiers so the preregistration can be frozen. Implementation of the reasoning core then begins against the Phase-1 plan, starting with the data contracts and prompt machinery and proceeding to the Arm B classical reasoner, each task gated on its unit tests. Because this work is offline Python, it can progress independently of the simulation environment. The carried-over Nav2 recovery-loop item will be addressed if it threatens the eventual runs. All tasks are individual work.

| # | Task | Dependency | Expected deliverable | Target |
|---|------|------------|----------------------|--------|
| 1 | Select and pin VLM model identifiers | — | Frozen preregistration | 15 Jul |
| 2 | Implement reasoning-core data contracts and parsers | — | New Pydantic models and schemas, unit-tested | 15–17 Jul |
| 3 | Implement derived-geometry grounding (Pillars 1, 2, 4) | 2 | Grounder `derived` mode behind a switch, unit-tested | 17–19 Jul |
| 4 | Implement the Arm B classical reasoner + shadow comparison | 2 | Baseline emitting `CongestionDecision`, unit-tested | 18–20 Jul |
| 5 | Address the open Nav2 pull-off recovery-loop item | — | Robust repeated resolution | as needed |

**Remarks.** The main reflection is that a planning week is worth reporting as such rather than dressing it up: the deliverable is a de-risked path, and the honest measure of the week is that the experiment is now fully specified but not yet run. One request for supervisory input: guidance on which VLM model(s) to commit to for the confirmatory runs, since this choice is currently the single blocker on freezing the preregistration and beginning data collection.

## VII. References

Asadi, M., Nowé, A., & Ghofrani, J. (2025). Congestion-aware multi-agent path planning for pick-up and delivery tasks. *Proceedings of the Genetic and Evolutionary Computation Conference*, 1523–1531. https://doi.org/10.1145/3712256.3726339

Garg, K., Nair, D. S. K., Zhang, S., Arkin, J., & Fan, C. (2026). Online motion planning for connected multi-robot systems using vision language models as high-level planners. *Proceedings of Machine Learning Research*, 1–21. https://mit-realm.github.io/VLM-gcbfplus-website/

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2021). *Retrieval-augmented generation for knowledge-intensive NLP tasks*. https://arxiv.org/abs/2005.11401

Sharon, G., Stern, R., Felner, A., & Sturtevant, N. R. (2015). Conflict-based search for optimal multi-agent pathfinding. *Artificial Intelligence, 219*, 40–66. https://doi.org/10.1016/j.artint.2014.11.006

Stern, R., Sturtevant, N., Felner, A., Koenig, S., Ma, H., Walker, T., Li, J., Atzmon, D., Cohen, L., Kumar, T. K. S., Boyarski, E., & Bartak, R. (2019). *Multi-agent pathfinding: Definitions, variants, and benchmarks*. https://arxiv.org/abs/1906.08291
