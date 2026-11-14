# Bachelor Thesis Draft — Design

**Prepared:** 2026-11-13

**Revision history:**

- Initial draft (2026-11-13): scope, chapter plan, sources, guardrails.
- Rev 5 (2026-11-14): scientific skills workflow (Section 8).
- Rev 4 (2026-11-14): IB10 run finished; report pending on feat/ib10-live-resolution.
- Rev 3 (2026-11-13): Stage 1 run finished (report pending); IB10 run in progress; owner decisions skip tranche 2 / run IB10 confirmed.
- Rev 2 (2026-11-13): newest-source rule (6.0); branch rebased onto fdf333d; source map points at latest reports.

---

## 1. Intent

Produce the full bachelor thesis for the VGU Department of Computer Science committee, due **Sunday 2026-11-15**. The thesis presents the VGU VLM Swarm project: a hybrid two-layer warehouse swarm coordinator where a VLM detects and classifies congestion and a grounding layer turns its decision into safe robot commands.

The owner reviews and edits; the builder drafts every chapter. The **results are held**: the main experiment (4-robot `intersection_bottleneck`, IB10, VLM on vs off) has not run yet. Everything except results, discussion, conclusion, and abstract is written now; those four get skeletons with explicit placeholders.

## 2. Goals

- A compilable Typst thesis that reuses the look of the owner's template `/Users/tuanhdangdinh/Downloads/Project week 5/main.typ` (VGU title page, logo header, page footer, New Computer Modern 11 pt, A4, APA references).
- Standard thesis chapters (Section 5), English.
- Every factual claim traceable to a repo document, commit, or data file listed in Section 6.
- Typst-native diagrams (`fletcher` for block/flow diagrams, `cetz` for scene layouts), editable in the repo and visible in the Tinymist live preview.
- A results skeleton with labelled placeholder tables/figures so the data can be dropped in later without restructuring.

## 3. Non-goals

- No new experiments, VM runs, or paid API calls.
- No code changes in the project packages.
- No final numbers for the IB10 experiment or the v4 Stage 1 shadow run.
- No Abstract/Discussion/Conclusion prose that asserts an outcome.

## 4. Guardrails (owner-confirmed anti-goals)

1. **No overclaiming.** The defensible claim is "the VLM plus grounding pipeline clears a congestion case", not "the VLM solves congestion". M3 repaired or replaced every earlier live plan; say so. prereg-v3 tranche 1 is reported as a **pilot** (0/10 full resolution).
2. **Only defensible numbers.** Each number cites its source file. If a number cannot be traced, leave it out or mark `[VERIFY]`.
3. **Related work sets up the question**, it is not a paper list. Each subsection ends with the gap this project addresses.
4. **Design decisions, not a bug diary.** Implementation lessons (sim-time vs wall-clock, Fabric sync, DDS profile, motion BVH) appear as engineering lessons with their consequence, briefly.
5. **Do not undersell.** Real contributions get stated plainly: the working closed loop, the safety gates and floors, the preregistration discipline (v1→v3, addenda), the finding that grounding (not detection) is the bottleneck, the presentation-order bias finding, the physical TurtleBot3 demonstration.
6. **v4 is exploratory** and is never pooled with prereg-v3. IB10 is exploratory and separate from v3.

## 5. Chapter plan

Front matter: title page (adapted from template: "Bachelor Thesis", title "Leveraging Vision-Language Models (VLM) for Congestion Management in Warehouse Swarm Robotics", instructor Dr. Vo Bich Hien, student Dang Dinh Tu Anh — 10422086, "HO CHI MINH CITY, 11/2026"), Abstract (placeholder), table of contents, list of figures, list of tables, list of abbreviations.

1. **Introduction** — warehouse congestion and deadlock; limits of purely local reactive control; why a semantic layer; research question(s) as in `docs/project_proposal.md`; contributions (guardrail 5); thesis outline.
2. **Background and Related Work** — MAPF/CBS and congestion-aware planning; reactive avoidance (ORCA) and Nav2; deadlock/congestion taxonomies and resolution strategies; VLMs/LLMs as robot planners and coordinators; grounding/RAG and plan feasibility; gap statement.
3. **System Design** — two-layer architecture (fast 20–50 Hz / slow 0.5–2 Hz); modules M1–M6 and their contracts; data flow detect→decide→ground→act→resolve; strategy vocabulary; safety invariants (0.45 m margin, floors, pre/post-arm gates). Figures: architecture, pipeline sequence.
4. **Implementation** — stack (ROS 2 Jazzy, Nav2, Isaac Sim, ArUco perception, VLM backends ER-2 / gpt-4o / Claude, deterministic M3 grounding); yield as pull-off-and-escort; engineering lessons; physical TurtleBot3 deployment (Section 7).
5. **Experimental Methodology** — evolution of the preregistration (v1→v2→v3, why); scenes (S1b 5-robot unified scene, IB10 4-robot intersection) with layout figures; arms (Layer 2 on vs off via `reasoning_enabled=False`); measures as defined in A33 (completeness, makespan, throughput, delay vs free flow, GT conflict <0.45 m, detection/type F1); interleaving and bootstrap; safety gates; offline v4 bench methodology (replay, grounding-first, per-cluster); threats to validity known in advance.
6. **Results** — skeleton only: 6.1 IB10 Arm A vs B (placeholder table + figure); 6.2 prereg-v3 tranche 1 pilot (placeholder table; numbers may be filled from the tranche-1 report since they exist, see Section 8); 6.3 exploratory findings (presentation order, gpt-4o refusals, v4 bench); 6.4 physical demonstration.
7. **Discussion** — placeholder headings: what the evidence supports, grounding as bottleneck, limitations, threats to validity.
8. **Conclusion and Future Work** — placeholder headings.

References: BibTeX/YAML in `thesis/bibliography/`, APA via the template's CSL; real `#cite` calls (the template's hand-written `ref.typ` is not reused). Appendices: optional (strategy enum, metric definitions).

Target length guess (builder's call): roughly 45–70 pages once results are in.

## 6. Source map

### 6.0 Newest-source rule (owner requirement)

The thesis describes the **newest** code and the **newest** scenario results. Branch lineage as of 2026-11-13:

| Role | Branch @ commit | Notes |
|---|---|---|
| **Code baseline (thesis branch base)** | `feat/v4-per-cluster-parity` @ fdf333d | Contains `feat/v3-integration` (68e67b5, the pinned v3 runtime incl. tranche-1 report 75a499c), `feat/v4-vlm-bench` (7850f5a), `feat/v4-per-cluster` (48234f2), Stage 0 parity + Stage 1 shadow. `docs/thesis` is cut from here. |
| Prereg v3 design + addenda A9–A36 | `feat/v3-design` @ ad67a18 | Not merged into the code baseline; read via `git show feat/v3-design:docs/superpowers/specs/2026-10-06-prereg-v3-design.md`. |
| IB10 experiment registration | `feat/ib10-live-resolution` @ 50704c2 | Branched from 68e67b5; IB10 runs on the **v3 pin runtime**, not on v4 code. |
| Older lineage — do not use as source | `fix/deadlock-collision-resolution` @ fc73151 | Main checkout; superseded by the branches above. |

Rules:

- **Describe the system as it ran.** Chapters 3–4 describe the v3 pinned runtime (68e67b5), because every live experiment (tranche 1, IB10) runs on it. v4 additions (grounding-first and per-cluster variants, Stage 1 shadow, default off) are described as exploratory extensions, clearly marked, never as the evaluated system.
- **Verify against code, not only docs.** Module descriptions (topics, strategy enum, safety thresholds, config keys) are checked against source files at fdf333d; where a spec disagrees with code, code wins and the spec is not cited for that point.
- **Newest results only.** Superseded numbers (earlier pilots, E1–E26 batches, earlier report revisions) appear only as history in Methodology, never as results. Use the latest revision of each report (e.g. per-cluster choice Rev 3, gf-cluster Rev 2, replay-er2 Rev 2).
- **Pending results** stay `#todo` until their report is committed:
  - v4 Stage 1 per-cluster shadow: run FINISHED 2026-11-13 15:47 UTC (7 episodes, seed positions 21–27; pooled script output exists in gitignored `v4_s1b_pc_shadow_analysis/stage1_summary_all.json`, no report yet). Shadow only, nothing dispatched; exploratory.
  - IB10 live run: FINISHED 2026-11-13 (Arm A 4/5 resolved, Arm B 0/5; 0 floor stops, 0 GT contacts; 0/5 VLM plans executed verbatim — 4 repaired, 1 replaced by M3). Report being written to `docs/reports/2026-11-13-ib10-live-resolution-results.md` on `feat/ib10-live-resolution`; numbers enter the thesis only from that committed report, with the claim "VLM + grounding pipeline clears the jam" (M3-default-without-VLM ablation not run — state as limitation).
- **Pre-submission refresh.** Before handing over the final draft, re-list branches by commit date (`git for-each-ref --sort=-committerdate refs/heads`) and check for commits newer than this table; update this table and any affected text.

### 6.1 Topic → source

Paths are relative to the thesis worktree (code baseline) unless a branch is named. **Read-only**: never edit anything outside `thesis/` and this spec.

| Topic | Sources |
|---|---|
| Motivation, RQ | `docs/project_proposal.md`, `docs/project_plan.md`, `docs/modules.md` |
| Module design | `docs/specs/module1_perception.md` … `module6_simulation.md`, `docs/specs/module4/`, `docs/isaac_vlm_pipeline.md`, `docs/reports/module5_orchestrator_implementation.md` |
| Weekly history / lessons | `docs/reports/2026-06-*`, `2026-07-*` progress reports, `docs/implementation_notes.md` |
| Related work | `reports/*.md` and `research_notes/*/` (untracked, main checkout), `research_notes/.../user_paper_folder_review.md`, owner's bibliography in template `bibliography/ref.bib` |
| Prereg v1–v3 | `docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`, `2026-09-30-prereg-v2-design.md`, `feat/v3-design:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A9–A36, A33 measures) |
| Scenes | `docs/superpowers/specs/2026-09-27-scenario-battery-design.md`, `2026-09-29-intersection-resolvable-design.md`, `2026-09-29-unified-scene-design.md`, `2026-10-06-v3-scene-design.md` |
| IB10 experiment | `../vgu-vlm-swarm-v7a/docs/superpowers/specs/2026-11-13-ib10-live-resolution-experiment.md` (branch `feat/ib10-live-resolution`) |
| Tranche 1 pilot | `docs/reports/2026-10-21-s1b-confirmatory-tranche1.md` (commit 75a499c) |
| Exploratory findings | `docs/reports/2026-09-25-presentation-order-probe.md`, `2026-09-25-gpt4o-refusals.md`, `2026-09-18-gemini-er2-image-grounding.md`, `2026-09-18-research-findings-register.md` |
| v4 bench | `docs/reports/2026-10-22-v4-bench-baseline.md`, `2026-10-23-v4-grounding-first-candidates.md`, `2026-10-23-v4-replay-er2.md`, `2026-10-24-v4-gf-cluster-candidates.md`, `2026-11-12-v4-per-cluster-choice.md` (all in the code baseline; latest revisions) |
| v4 per-cluster live path | `docs/superpowers/specs/2026-11-12-per-cluster-live-path-design.md`, `docs/guides/v4_s1b_pc_shadow_runbook.md` |
| Physical demo | `~/Downloads/verified_scenarios_12-11-2026/README.md` + images + `decision_artifacts/` |
| Template | `/Users/tuanhdangdinh/Downloads/Project week 5/` (copy, do not modify) |

**Do-not-touch:** `vgu-vlm-swarm-v6d/data/logs/vm_runs/v4_s1b_pc_shadow/`, `vgu-vlm-swarm-v7a/data/logs/vm_runs/ib10_live/`, `data/bench/` in v6a/v6c, the Isaac VM (in use for IB10).

## 7. Physical demonstration (owner decision: include)

Implementation chapter section + Results placeholder. State what it shows (TurtleBot3s, overhead RealSense + ArUco, `gemini-3.1-flash-lite`, deterministic grounding, Zenoh, live execution with safety monitor; backup commands completing in e.g. two simultaneous head-on deadlocks) and what it does not: robots had no navigation goals, and that code lineage is not in this repository. Copy images from the demo folder into `thesis/assets/images/`.

## 8. Decided "how"

- **Location:** `thesis/` in the worktree `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-thesis`, branch `docs/thesis` (rebased onto fdf333d, the newest code tip; see 6.0). Not pushed without owner OK. *(builder's call, stated to owner)*
- **Tooling:** Typst 0.15.1 locally (`typst compile thesis/main.typ`); owner previews with Tinymist in VS Code/Cursor or `typst watch`. Use the `typst-documents` skill.
- **Diagrams:** Typst-native `fletcher` + `cetz`, pinned package versions. *(owner accepted)*
- **Structure:** `thesis/main.typ` + `thesis/chapters/NN-name.typ` + `thesis/assets/` + `thesis/bibliography/`.
- **Scientific skills (owner request, installed 2026-11-14 from K-Dense-AI/scientific-agent-skills @ 2d2065f into `~/.claude/skills/`):**
  - `paper-lookup` + `citation-management`: every bibliography entry is resolved by DOI/arXiv ID (Crossref, OpenAlex, arXiv) and generated as BibTeX from the API record; `validate_citations.py` run over `thesis/bibliography/*.bib` before handover. This implements the "never cite from memory" rule.
  - `scientific-writing`: drafting guidance; `audit_claims.py` / `check_consistency.py` used as a pre-handover pass over the chapter text (export to Markdown if a tool needs it).
  - `peer-review`: one committee-style review of the full draft before handover; findings fixed or listed for the owner.
  - `scientific-visualization`: results plots (IB10 arm comparison, tranche-1 pilot, v4 bench) made with Matplotlib, exported as SVG/PDF with New Computer Modern-compatible fonts, scripts kept in `thesis/figures/src/` so plots regenerate from data.
  - `statistical-analysis`: small-sample inference for the held results (e.g. exact test and exact/Wilson intervals for IB10 4/5 vs 0/5; bootstrap CIs as preregistered for tranche 1), reported with effect sizes, never as more than an exploratory pilot.
  - `scientific-critical-thinking`: threats-to-validity section in Methodology and Discussion (confounds such as M3 repairing every plan, deterministic Arm B freeze, single scene, simulation-only).
  - Not installed: `literature-review` (needs OpenRouter key, PRISMA/biomedical focus), `scientific-schematics` (AI image generation; diagrams stay Typst-native).
- **Placeholders:** a single `#todo[...]` macro (visible coloured box) for every held number or sentence, so a grep finds them all before submission.

## 9. Left to the builder

Section wording and order within chapters; which existing images to reuse; abbreviation list; appendix content; whether tranche-1 pilot numbers already published in the tranche-1 report go in now (allowed: they exist and are final — but phrased as pilot) or wait with the rest.

## 9a. Settled after builder check (planner's calls, owner to confirm while reading)

- **Evidential tone of Introduction/Contributions.** System and method contributions (closed loop, safety gates, preregistration discipline, physical demo) are stated plainly. Empirical findings (grounding as the bottleneck, presentation-order bias) are stated as findings *from the pilot and offline bench*, with the evidence type named ("in a 10-episode pilot", "in offline replay of 187 recorded analyses"). The headline experimental contribution (IB10) is described as the evaluation performed, with outcome deferred to Chapter 6 via `#todo`.
- **Unreachable sources.** All sibling worktrees in Section 6 exist as of 2026-11-13 (v6a, v6c, v7a, and `feat/v3-design` / `feat/v3-integration` branches). If a source cannot be read, mark the claim `[VERIFY]` and continue; do not stop.
- **Bibliography.** Prefer references already named in `reports/`, `research_notes/`, and the template `ref.bib`. New references are allowed only if verified online (DOI, arXiv, or publisher page fetched) before entry; never cite from memory. Unverifiable items are dropped, not guessed.
- **Front matter.** Add a Declaration of Authorship and an Acknowledgements page (placeholder text for the owner) before the abstract. No VGU page limit was given (owner: "up to you").
- **Physical demo.** Every statement sourced only from `~/Downloads/verified_scenarios_12-11-2026/README.md` and its artifacts, with the lineage caveat in the text.
- **Traceability form.** Literature via `#cite`. Repo evidence via a short "Source:" line in table/figure captions plus an appendix **Evidence Index** mapping each reported number to its file/commit. No raw paths in running prose.

## 10. Acceptance

- `typst compile thesis/main.typ` succeeds with no errors.
- Chapters 1–5 complete prose; 6–8 and Abstract skeletons with `#todo` markers.
- Every number has a traceable source; `[VERIFY]` count reported to owner.
- Implementation-notes entry appended per CLAUDE.md.
