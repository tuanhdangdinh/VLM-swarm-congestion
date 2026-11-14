# Bachelor Thesis Draft Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A compiling Typst thesis in `thesis/` with chapters 1–5 fully drafted from verified sources, and results, discussion, conclusion and abstract left as skeletons with placeholders. These held parts wait for the other sessions to finish.

**Architecture:**
- **Shared scaffold:** one task builds the scaffold first. It covers the template look, shared macros, a check script and the full chapter skeleton.
- **Parallel work:** independent drafting tasks (bibliography, diagrams, chapters 3, 4 and 5) then run in parallel. Each writes only its own files.
- **Sequenced work:** chapter 2 waits on the bibliography and chapter 1 waits on everything. A final pass runs the checks.
- **Commits:** the controller commits after each task. Subagents never commit, which avoids git index-lock collisions in the shared worktree.

**Tech Stack:**
- Typst 0.15.1 with `fletcher` and `cetz` from Typst Universe (versions resolved in Task 0, not recalled).
- Built-in APA citation style.
- Python 3 stdlib for checks, plus the installed skills `typst-documents`, `citation-management`, `paper-lookup`, `scientific-writing`, `scientific-critical-thinking` and `peer-review`.

**Spec:** `docs/superpowers/specs/2026-11-13-thesis-design.md` (Rev 6). Read it before any task. Sections 4 (guardrails), 6 (source map and newest-source rule) and 9a (settled calls) are binding.

## Global Constraints

- **Work location:** worktree `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm-thesis`, branch `docs/thesis`. Write only under `thesis/`, plus `docs/implementation_notes.md` in Task 8. Every other branch, worktree, VM and data folder is read-only.
- **No experiments:** no VM, no paid API calls and no pushes.
- **Look:** A4, New Computer Modern 11 pt, VGU logo header and page footer as in `/Users/tuanhdangdinh/Downloads/Project week 5/main.typ`. Code font is `DejaVu Sans Mono`, because Cascadia Code is not installed.
- **Language:** English.
- **Runtime described:** the v3 pinned runtime `68e67b5`. Verify code facts with `git show 68e67b5:<path>`. v4 features are marked exploratory and default-off.
- **Held content:** Results, Discussion, Conclusion and Abstract stay skeletons, with every held sentence in `#todo[...]` (owner decision 2026-11-14).
- **Numbers:** every number in prose is followed by `#ev("<id>")`, pointing to an Evidence Index entry that names the file or commit. No repo paths appear in chapter prose or captions; paths live only in `thesis/evidence/*.typ`.
- **References:** every reference is resolved from DOI or arXiv metadata through `citation-management`/`paper-lookup` before it enters `refs.bib`. Nothing is cited from memory.
- **Claim language:** "the pipeline (VLM + grounding) clears the jam", never "the VLM solves congestion". prereg-v3 tranche 1 is called a pilot. v4, IB10 and Arm C are exploratory and never pooled with prereg-v3.
- **Disk:** about 7 GB free (99% full). Do not clone, download PDFs or create worktrees. Run `df -h .` before Task 1 and stop if under 3 GB free.

## Review Focus

1. **Stale or superseded numbers:** a number copied from an older report revision or batch, such as E1–E26 pilots, instead of the latest. Each evidence entry must name the newest report and its commit. A reviewer checks 5 random `#ev` entries against their sources.
2. **v4 code described as the evaluated system:** a fact read from the code baseline `cbe3dcf` that differs at `68e67b5`. Tasks 3–5 diff every cited code file between the two commits.
3. **Fabricated or mis-resolved citations:** an entry whose DOI resolves to a different paper. Task 1 runs `validate_citations.py`, and every key carries a `doi` or `eprint`.
4. **Overclaiming in Introduction or Contributions:** findings stated without their evidence type. Task 7 includes a phrase checklist.
5. **Diagrams in a mismatched font or broken at A4 width:** every figure compiles inside `main.typ` at text width, and Task 2 renders each to PNG to look at it.

---

### Task 0: Scaffold, conventions, check script

**Files:**
- Create: `thesis/main.typ`, `thesis/lib.typ`, `thesis/check.sh`, `thesis/assets/images/vgu_logo.png` (copied from the template), `thesis/bibliography/refs.bib` (empty), `thesis/evidence/index.typ`
- Create chapter skeletons: `thesis/chapters/00-front.typ`, `01-introduction.typ`, `02-background.typ`, `03-system-design.typ`, `04-implementation.typ`, `05-methodology.typ`, `06-results.typ`, `07-discussion.typ`, `08-conclusion.typ`, `09-appendix-evidence.typ`
- Create one evidence file per chapter: `thesis/evidence/ch1.typ` … `ch5.typ`, `ch6.typ`

**Interfaces (produced, used by every later task):**
- `#todo(body)`: visible orange-bordered box labelled "TODO". Used for every held item.
- `#ev(id: str)`: renders `[id]` as a link to label `<ev:id>` in the appendix. IDs look like `"3.04"`, with the chapter number, a dot and two digits.
- `#evidence(id: str, claim: content, source: content)`: one appendix row with label `<ev:id>`, where `source` is a raw path or commit string. Called only inside `thesis/evidence/chN.typ`.
- `#fig-source(id)`: the caption suffix ` Source: [id].` for tables and figures.
- Each chapter file starts with `#import "../lib.typ": *`.
- `main.typ` includes the chapters in order. The evidence appendix includes `evidence/ch1.typ`…`ch6.typ` inside a 3-column table (ID, claim, source).

- [ ] **Step 1:** Load the `typst-documents` skill. Copy `vgu_logo.png` from `/Users/tuanhdangdinh/Downloads/Project week 5/assets/images/`.
- [ ] **Step 2:** Look up the current `fletcher` and `cetz` versions on Typst Universe (`https://typst.app/universe/package/fletcher`, `.../cetz`). Record them as `#let fletcher-version` comments in `lib.typ`. Import them where diagrams live (Task 2), not in `lib.typ`.
- [ ] **Step 3:** Write `main.typ`. Carry over the template's page, header, footer, text, par, heading and raw rules, replacing the raw font with `DejaVu Sans Mono`. Drop the unused `versatile-apa`/`codly` imports unless compile needs them.
  - **Title page:** "Bachelor Thesis", the title from spec §5, Instructor Dr. Vo Bich Hien, Student Dang Dinh Tu Anh – 10422086, "HO CHI MINH CITY, 11/2026".
  - **Front matter (`00-front.typ`):** Declaration of Authorship (`#todo` owner text), Acknowledgements (`#todo`), Abstract (`#todo`), outline, list of figures, list of tables, abbreviations table.
  - **Numbering:** heading numbering `"1.1"`, with chapters as level-1 headings, each starting on a new page.
  - **Bibliography:** `#bibliography("bibliography/refs.bib", style: "apa", title: "References")`.
- [ ] **Step 4:** Write every chapter skeleton with its section headings from spec §5. Every section body is `#todo[...]`, naming what goes there.
- [ ] **Step 5:** Write `check.sh`, which prints a summary and exits non-zero on failure:
  - **(a)** `typst compile thesis/main.typ thesis/main.pdf` with zero errors.
  - **(b)** counts of `#todo` and `[VERIFY]` per chapter.
  - **(c)** fails if any `thesis/chapters/*.typ` line matches `docs/|data/|\.md\b|\.json\b|worktree|vgu-vlm-swarm-`.
  - **(d)** fails if any `#ev("X")` has no matching `#evidence("X"` in `thesis/evidence/`, or the reverse.
  - **(e)** fails if any `@key` in chapters is missing from `refs.bib`. Typst also errors on this; the separate check gives a clearer message.
- [ ] **Step 6:** Run `bash thesis/check.sh`. Expected: compile OK, many TODOs, zero path, ev and cite failures.
- [ ] **Step 7:** Controller commits with `git add thesis && git commit -m "docs: thesis scaffold and checks"`.

### Task 1: Bibliography (single owner of `refs.bib`)

**Files:** Modify `thesis/bibliography/refs.bib`. Create `thesis/bibliography/KEYS.md`, one line per key: `key — short description — DOI/arXiv`.

**Interfaces:** Produces the keys used by Tasks 3–7. Other tasks **request** new references by adding `#todo[cite: <description>]`, and the controller routes those requests back to this task's agent. Other tasks never edit `refs.bib`.

- [ ] **Step 1:** Harvest candidate references:
  - every paper named in the main checkout's `reports/*.md` and `research_notes/*/*.md` (read-only, untracked files);
  - the template's `bibliography/ref.bib` and `sections/ref.typ`;
  - the reference lists of `docs/project_proposal.md` and `docs/reports/2026-11-13-thesis-evidence-register.md`.
- [ ] **Step 2:** Select about 35–50 references covering spec §5 chapter 2:
  - MAPF/CBS and congestion-aware planning;
  - ORCA/RVO and Nav2;
  - deadlock taxonomies and resolution;
  - VLM/LLM robot planners and coordinators, including Gemini Robotics-ER;
  - grounding and plan feasibility.
  
  Also include tools: ROS 2, Isaac Sim, ArUco, Nav2.
- [ ] **Step 3:** For each reference, resolve metadata by DOI or arXiv ID with `citation-management` (`doi_to_bibtex.py`) or `paper-lookup`. Use software or documentation entries (`@misc` with url and `urldate = 2026-11-14`) only for tools. Drop anything unresolvable.
- [ ] **Step 4:** Run `python ~/.claude/skills/citation-management/scripts/validate_citations.py thesis/bibliography/refs.bib`. Expected: no errors. Fix or drop failures.
- [ ] **Step 5:** Run `bash thesis/check.sh`. Expected: compile OK.
- [ ] **Step 6:** Controller commits with `docs: thesis bibliography`.

### Task 2: Diagrams

**Files:** Create `thesis/figures/architecture.typ`, `pipeline.typ`, `scene-ib10.typ`, `scene-s1b.typ`. Each exports one function, `#let <name>-figure() = ...`, which returns content sized to text width (`architecture-figure`, `pipeline-figure`, `ib10-figure`, `s1b-figure`).

**Interfaces:** Consumed by Tasks 3 (architecture, pipeline) and 5 (scenes). Each chapter wraps the call in `#figure(..., caption: [...])`.

- [ ] **Step 1:** `architecture-figure`: built with fletcher. It shows Layer 1 (M4 execution and safety, Nav2, robots, 20–50 Hz) and Layer 2 (M1 perception → M5 orchestrator → M2 VLM → M3 grounding → M4, 0.5–2 Hz), with the topic names from `git show 68e67b5:` config and launch files and M6 simulation around them.
- [ ] **Step 2:** `pipeline-figure`: built with fletcher. It shows the sequence detect → decide → ground → act → resolve, including the M3 refusal/repair branch and the safety gate.
- [ ] **Step 3:** `ib10-figure` and `s1b-figure`: built with cetz. They show the scene layout to scale, with robot start positions and goals taken from the scenario YAML at `68e67b5`. Find the path with `git show 68e67b5 --stat`/`git grep intersection_bottleneck 68e67b5`. Add a meter scale bar.
- [ ] **Step 4:** Render each figure through a throwaway test file with `typst compile figtest.typ figtest-{p}.png`, then Read the PNG to check that it looks right, fits the width and uses the New Computer Modern font. Delete the test files.
- [ ] **Step 5:** Controller commits with `docs: thesis diagrams`.

### Tasks 3–5: Chapter drafting (run in parallel)

Common steps for each chapter task:
1. Read the spec's §4, §6 and §9a, and the sources in the chapter's row of the source map. Start from `docs/reports/2026-11-13-thesis-evidence-register.md`.
2. Draft the prose:
   - Use `scientific-writing` guidance and the claim language from Global Constraints.
   - Follow every number with `#ev("N.xx")` and add the matching `#evidence(...)` to `thesis/evidence/chN.typ`. Its source must be the newest report plus commit, or a `68e67b5:<path>` code path.
   - For code facts, run `git diff 68e67b5 cbe3dcf -- <path>`. If the file differs, use the `68e67b5` version.
3. Run `bash thesis/check.sh`. Expected: compile OK, zero path, ev and cite failures, and this chapter's `#todo` count at 0 except `cite:` requests.
4. Report to the controller the `[VERIFY]` count and any `cite:` requests, which the controller routes to Task 1.
5. The controller commits.

#### Task 3: Chapter 3, System Design (`thesis/chapters/03-system-design.typ`, `thesis/evidence/ch3.typ`)

- **Sections:**
  - 3.1 Requirements and design goals.
  - 3.2 Two-layer architecture (use `architecture-figure`).
  - 3.3 Modules M1–M6 and contracts. Include a table of each module's inputs and outputs, with names taken from code at `68e67b5`.
  - 3.4 Decision pipeline (`pipeline-figure`).
  - 3.5 Strategy vocabulary, with the enum from `68e67b5` code and which strategies are executable at M4.
  - 3.6 Grounding (M3): feasibility checks, repair, refusal and the default plan.
  - 3.7 Safety invariants: 0.45 m margin, 0.20 m floor, pre- and post-arm gates, clearing exemption. The exemption-scope gap and its fix are described as found after the experiments, with the fix default-off in the runtime used.
- **Sources:** `docs/specs/module*`, `docs/modules.md`, `docs/isaac_vlm_pipeline.md`, `docs/reports/module5_orchestrator_implementation.md`, `docs/reports/2026-11-13-safety-exemption-trace.md`, and the code at `68e67b5`.
- **Length:** about 8–12 pages.

#### Task 4: Chapter 4, Implementation (`thesis/chapters/04-implementation.typ`, `thesis/evidence/ch4.typ`)

- **Sections:**
  - 4.1 Software stack, as a table: ROS 2 Jazzy, Nav2, Isaac Sim version, Python, VLM backends with exact model IDs as configured at `68e67b5`.
  - 4.2 Perception: ArUco, homography, state estimation.
  - 4.3 Orchestrator state machine and task registry.
  - 4.4 Execution: yield as pull-off and escort, backup, wait, junction_clear phase queue.
  - 4.5 VLM backends and prompt construction.
  - 4.6 Engineering lessons (guardrail 4: decision and consequence, at most one paragraph each): sim-time vs wall-clock, Fabric/USD sync, DDS UDP profile, motion BVH, scenario USD rebuild.
  - 4.7 Testing and reproducibility: test-suite size at `68e67b5` measured with `git grep -c "def test_" 68e67b5 -- tests | awk`, pins and md5 checks.
  - 4.8 Physical TurtleBot3 demonstration. Use spec §7 only. Copy 1–2 images from `~/Downloads/verified_scenarios_12-11-2026/verified_scenarios_images_2026-11-12/` to `thesis/assets/images/`, and state the lineage caveat.
- **Sources:** weekly progress reports, `docs/implementation_notes.md`, `docs/guides/*`, the demo README, and the code at `68e67b5`.
- **Length:** about 10–14 pages.

#### Task 5: Chapter 5, Experimental Methodology (`thesis/chapters/05-methodology.typ`, `thesis/evidence/ch5.typ`)

- **Sections:**
  - 5.1 Research questions and hypotheses, as preregistered.
  - 5.2 Preregistration history v1 → v2 → v3 and why each changed. Keep it brief and cite the addenda by number.
  - 5.3 Scenes: S1b, a 5-robot unified scene (`s1b-figure`), and IB10, a 4-robot intersection (`ib10-figure`).
  - 5.4 Arms: A (Layer 2 on), B (Layer 2 off via `reasoning_enabled=False`), C (grounder default, no VLM call; from the addendum). Describe the procedure only, with no outcomes.
  - 5.5 Measures, using the A33 definitions verbatim in substance, including resolution and arrivals for IB10.
  - 5.6 Procedure: interleaving, horizons, episode caps, exclusions and attempt rules, and safety gates.
  - 5.7 Analysis plan: paired seed bootstrap (10000 resamples, seed 20261021) for tranche 1, and small-sample exact methods for IB10. Use the `statistical-analysis` skill to state the method only.
  - 5.8 Offline v4 bench methodology: replay of 187 recorded analyses and the grounding-first and per-cluster variants.
  - 5.9 Threats to validity known in advance, written with the `scientific-critical-thinking` skill. Cover M3 repair as a confound, the deterministic Arm B freeze, a single scene per experiment, simulation only, and small n.
- **Sources:** prereg v1/v2 specs, `git show feat/v3-design:docs/superpowers/specs/2026-10-06-prereg-v3-design.md` (A33–A36), the IB10 spec on `feat/ib10-live-resolution`, the addendum on `feat/ib10-safety-default-arm`, and the v4 bench reports.
- **Do not include** any result numbers. Those belong to the held Chapter 6.
- **Length:** about 10–14 pages.

### Task 6: Chapter 2, Background and Related Work (after Task 1)

**Files:** `thesis/chapters/02-background.typ`. Citations only; no `#ev` is needed unless the chapter cites a project number.

- [ ] **Step 1:** Write sections 2.1–2.5 per spec §5. Each subsection ends with a 1–2 sentence gap statement tied to this project (guardrail 3). Cite only keys in `KEYS.md`, and route any new need as a `cite:` request.
- [ ] **Step 2:** Write 2.6, a comparison table of 6–10 closest works against this project: centralized or decentralized, VLM input, grounding, live robots or simulation, and safety layer.
- [ ] **Step 3:** Run `check.sh`; the controller then commits. Length: about 10–14 pages.

### Task 7: Chapter 1, Introduction (after Tasks 3–6)

**Files:** `thesis/chapters/01-introduction.typ`, `thesis/evidence/ch1.typ`.

- [ ] **Step 1:** Write the sections:
  - 1.1 Motivation.
  - 1.2 Problem statement.
  - 1.3 Research questions, from the proposal and prereg.
  - 1.4 Contributions, using the spec §9a tone.
  - 1.5 Scope and non-goals.
  - 1.6 Thesis outline.
  
  The IB10 outcome is a `#todo`.
- [ ] **Step 2:** Run the phrase check: `grep -n -i -E "solves|proves|significantly|state-of-the-art|guarantee" thesis/chapters/0[1-5]*.typ`. Every hit must be justified or reworded.
- [ ] **Step 3:** Run `check.sh`; the controller then commits.

### Task 8: Integration pass

- [ ] **Step 1:** Run `bash thesis/check.sh` and confirm it is clean apart from the expected held TODOs in Chapters 6–8, the Abstract and front-matter owner text.
- [ ] **Step 1b:** Run the `scientific-writing` local audits (`audit_claims.py` and `check_consistency.py` from `~/.claude/skills/scientific-writing/scripts/`; read the skill for their input format). Run them on chapters 1–5, exporting the text with `typst query` or a plain-text conversion if the tools need Markdown. Fix any inconsistent numbers or terms they report.
- [ ] **Step 2:** Dispatch one `peer-review` pass, committee-style, on chapters 1–5 using the compiled PDF and sources. Fix the findings, or list them for the owner.
- [ ] **Step 3:** Run the pre-submission refresh with `git for-each-ref --sort=-committerdate refs/heads | head`. If any branch is newer than the spec §6.0 table, update the table and the affected text.
- [ ] **Step 4:** Append a dated entry to `docs/implementation_notes.md` per CLAUDE.md, covering the thesis draft, its location and the held parts.
- [ ] **Step 5:** The controller commits. Then report to the owner: page count, TODO and VERIFY counts, review findings, and the list of placeholders waiting on other sessions.

**Deferred to the results fill (not in this plan):** `scientific-visualization` plots (IB10 arms A/B/C, tranche 1 pilot, v4 bench) and the `statistical-analysis` computations, scripted in `thesis/figures/src/`. They are held with Chapter 6 by owner decision, and get their own plan when the other sessions finish.

**Cut line if time runs short (Saturday evening):** Tasks 0, 1, 3, 4 and 5 are must-have. Task 6 can shrink to about 6 pages. The Task 8 peer-review step is optional. Chapter 1 is written last but is required.
