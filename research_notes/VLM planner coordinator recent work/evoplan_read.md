# EvoPlan deep read — novelty check for provenance claim (freeze gate)

**Read:** 2026-10-04. Full PDF (24 pp) read, all appendices A–D.
**Paper:** EvoPlan: Evolutionary Neuro-Symbolic Robot Planning with Spatio-Temporal Guarantees. arXiv:2607.06724v1 (cs.RO), submitted 2026-07-07. Bhavya Sai Nukapotula, Samin Moosavi, Haoze Wang, Luke Duncan, Diya Shakkottai, Varun Murali, Srinivas Shakkottai (Texas A&M).
**Status:** preprint only. No comments/venue field on the abs page; no venue claim in the PDF. No code release for EvoPlan itself found (paper or web); it *uses* the third-party OpenEvolve library (cited as "codelion (2024). OpenEvolve: LLM-driven evolutionary program search. github.com/codelion/openevolve").

## 1. Who proposes, who repairs, what validators do

**The LLM does both proposal and repair. Validators only gate/reject and emit feedback; they never modify a plan.**

- Abstract: "an *evolutionary PDDL planner*: an LLM proposes and repairs plans, programmatic validators decide which ones survive, and the validated portion of the plan grows over iterations."
- Sec. 4.2: "an LLM proposes plan edits, a programmatic cascade decides which survive, and the cascade's *descriptive feedback* (the failing action and its unsatisfied precondition) conditions the next LLM mutation, so the loop evolves plans in response to verifier signals rather than free-form sampling."
- Sec. 4.2, "Evolutionary search loop": "Each generation, the LLM proposes an edit to the current best candidate conditioned on the parent's validator feedback; typical edits include inserting a missing precondition action, repairing an object binding, swapping independent actions, or resampling a suffix, but the edit type is not constrained ex ante. A four-stage cascade scores the child: PDDL syntax, VAL … simulation, goal reachability, and (when continuous execution is involved) predicted robustness against the global constraint Φ_mob … Stages short-circuit. Invalid plans are demoted by the cascade, not by an LLM critic."
- Introduction (Sec. 1): "a neural model generates and repairs candidate plans, while symbolic validation and data-derived temporal-logic constraints decide which candidates may be executed."

**Deterministic/non-LLM mechanisms present (none is minimal plan repair):**
- `REWRITE_HEADS(P, μ)`: "regex substitution of predicate heads in P by μ" (App. B.1 Routines; Alg. 1 lines 17–19). Deterministic code, but it rewrites the *PDDL problem's goal predicates*, not plan legs, and the map μ itself comes from "a single LLM call [that] produces a predicate-symbol map μ" (Sec. 4.2, "Open-world and misaligned deployments").
- Verified-prefix commit at runtime (Sec. 4.3 / Problem Def. "Output"): "When w_k violates N at runtime, the verified prefix a_1…a_{k−1} is committed, the resulting world state becomes the new initial state, and the planner is re-invoked to produce a fresh suffix-replacing plan." Deterministic *truncation + full LLM replan*, not an edit toward the nearest valid plan.
- `best_safe_prefix(population)` fallback in the C.1 pseudocode when no valid plan is found within budget — deterministic *selection/truncation*, again not repair.

## 2. Evaluation metrics (complete list)

Planner metrics (Sec. 4.2, 5.2, App. B):
- **Success rate (SR%)** and **tokens-to-solve (# Tok.)** — Table 2 (open-world ALFWorld Text, N=134), Table 7 (closed-world Blocksworld, 4 variants), Table 8 (closed-world ALFWorld).
- **Validated fraction |π_valid|/|π| vs. iteration** — Fig. 2 (a) open-world, (b) closed-world, (c) closed-world population ("% of tasks" fully solved / partial progress / no progress by iteration). Sec. 4.2, "Verified-prefix preservation": "Although no prefix is explicitly frozen, the validated fraction |π_valid|/|π| grows monotonically over iterations on hard tasks … Token usage stays proportional to the unverified work because VAL feedback marks only the failing action." **This is the closest thing in the paper to a per-leg quantity. It is a per-plan validity fraction (mean ± 1σ over tasks), binary valid/invalid per step at each iteration. It carries NO origin label: it does not distinguish a step that survived verbatim from the first proposal from one the LLM rewrote five times.**
- **Iteration counts**, qualitative: "most tasks converge within 1–3 iterations" (App. B.2, "Mystery as the difficulty floor"; repeated after Table 9). Worked example box (App. B.1): one Mystery Blocksworld instance "converges in four iterations," each row showing candidate plan + validator verdict (INVALID/VALID, "steps 3/10, score 0.31" style step-score annotations) + feedback string.
- **Ablation** Table 9: single-shot LLM+VAL (k=1) 86.7% vs full evolutionary loop 99.7% SR at ~1.5× token cost (Blocksworld Plain, N=300, Qwen3-32B).

**Absent entirely: repair counts, repair magnitude, edit distance between proposal and final plan, per-action origin/provenance labels, verbatim-vs-repaired tabulations.** The candidate database in App. C.1 ("maintains a database of candidate plans and their evaluator feedback") stores per-candidate (plan, score, feedback) tuples — iteration-level artifacts, not per-leg origin labels, and nothing of it is reported as an experimental quantity.

Shield/execution metrics (not planner provenance; Sec. 5.1, 5.3, App. A, C):
- Table 1a/4: Driving Score, Route Completion, collisions, red-light infractions, total infractions, **vetoes (total shield substitutions)**, routes completed (Bench2Drive).
- Table 1b/5: SR%, collision-termination CT%, McNemar 95% CIs (HA-VLN-CE, N=1839 paired).
- Table 6: per-cause collision decomposition (avoidable / trajectory-crossing / human-into-static).
- Table 3: per-mission Gazebo metrics (success, route %, collisions, path length, time, intimate/personal/social zone tick %, P_int, min clearance). Fig. 5: crowd-density sweep.

## 3. Domain

- **Single-robot / single-agent throughout.** App. D, "Multi-robot and grounded collaboration": "The present paper focuses on a single Jackal-style deployment, but the same global Φ_mob shield and evolutionary planner can be extended to multi-robot missions by adding role assignment, communication, and shared-resource constraints." Sec. 6 lists "richer multi-robot tasks" as future work. No congestion, deadlock, or inter-robot coordination anywhere.
- **The evolutionary planner is evaluated on text/symbolic benchmarks only:** ALFWorld Text / AlfredTWEnv TextWorld (N=134 valid_unseen, 50-step budget; Sec. 5.2, Table 2) and NL-PDDL Blocksworld Plain/Mystery/Randomized/Misalignment (App. B.2, Table 7). The embodied parts (Bench2Drive driving, HA-VLN-CE navigation) evaluate the **STL shield**, not the planner; the Gazebo Jackal factory demo (Sec. 5.3, 5 pick-and-drop missions, 1 run each) is an illustration of the execution loop.
- Backbones: locally hosted Qwen3-32B, gpt-oss-120b; shield policy Qwen2.5-VL.

## 4. Venue / artifacts

- arXiv v1 only (2026-07-07), cs.RO, no listed venue or workshop. Searches surface no EvoPlan repository; the only linked code is the upstream OpenEvolve library. GenePlan (arXiv:2603.09481, ICAPS 2026) is a *different* group's evolutionary-PDDL paper — not this one; worth a separate skim but it evolves generalized plans, also LLM-mutation-based.
- Risk note for artifacts: their internal OpenEvolve run database (candidate + feedback per iteration) *could* in principle be post-processed into something provenance-like, but nothing is released and nothing of that form is reported.

## 5. Verdict against the three thesis claims

| Thesis claim | Verdict | Why |
|---|---|---|
| Three-way per-leg provenance (verbatim / repaired / defaulted), logged per leg as an experimental quantity, produced by deterministic minimal repair, for multi-robot congestion plans | **(c) untouched** | EvoPlan has no origin labels of any kind, no deterministic repair (all repair is LLM mutation), single-robot, no congestion domain. Fig. 2's validated fraction is validity status, not provenance, and is per-plan aggregate. |
| "deterministic minimal repair by a non-LLM module is essentially absent from the LLM-robotics era" | **(b) mild tightening advised** | The sentence survives — EvoPlan is direct supporting evidence (repair is explicitly LLM; validators only demote: "Invalid plans are demoted by the cascade, not by an LLM critic"). But EvoPlan contains two deterministic non-LLM *mechanisms* a hostile examiner could wave at: REWRITE_HEADS regex substitution (applies an LLM-derived predicate map to the problem, not the plan) and verified-prefix truncation / best_safe_prefix fallback (truncation, not repair). Tighten so neither counts. |
| "no published system reports per-leg provenance of a model-proposed plan as an experimental quantity" | **(b) mild tightening advised** | Strictly true: Fig. 2 reports a per-iteration *validated-prefix fraction*, which is per-step *validity*, not per-leg *origin*. But it is a published, plotted, per-step-derived experimental quantity about plan composition, so the sentence should name it and draw the distinction rather than leave the opening. |

**Proposed tightened wordings:**

- Deterministic-repair sentence → "Deterministic minimal repair — a non-LLM module that edits the model's proposed plan into the nearest admissible plan — is essentially absent from the LLM-robotics era: validator-gated systems such as EvoPlan [cite] route every repair back through the LLM ('invalid plans are demoted by the cascade, not by an LLM critic') and fall back only to truncation (verified-prefix commit) or to deterministic application of LLM-derived rewrite maps, never to deterministic edits of the plan itself."
- No-per-leg-provenance sentence → "No published system reports the origin of each plan leg — verbatim, repaired, or defaulted — as an experimental quantity. The nearest published quantity, EvoPlan's validated-prefix fraction |π_valid|/|π| (Fig. 2 of arXiv:2607.06724), tracks validator acceptance per iteration, not per-leg origin: a leg that survives unchanged from the first proposal and a leg rewritten across five mutations are indistinguishable in it."
- The registered three-way provenance claim itself needs no change; cite EvoPlan in related work as the closest propose-verify analogue (LLM-repair + symbolic gating, verified-prefix growth) and contrast on all three axes: origin labels (none vs three-way), repair agent (LLM vs deterministic minimal), domain (single-robot text/symbolic planning vs multi-robot congestion).

## Spare quotes (with locations)

- Sec. 1: "Rather than calling a classical search procedure, an LLM proposes and repairs plans against a fixed PDDL problem P and domain D, and a programmatic validator cascade scores each candidate. Elitism on validator feedback grows the validated prefix of the plan monotonically over iterations, without any explicit suffix-only mutation. The result is a system that uses LLM generation only inside a formally evaluated loop."
- Problem Def. (Sec. 3, "Output"): "When w_k violates N at runtime, the verified prefix a_1…a_{k−1} is committed, the resulting world state becomes the new initial state, and the planner is re-invoked to produce a fresh suffix-replacing plan."
- Sec. 4.2 (misalignment): "a single LLM call produces a predicate-symbol map μ applied to the goal predicates of P just before VAL."
- App. B.1 (worked example coda, p. 19): "The pattern – precondition fail, goal-miss over-correction, partial repair with spurious tail, then a clean trim to the optimum – is typical: the validator artifact converts 'which clause failed' into the next prompt's repair target."
- Table 9 (App. B.4): "The evolutionary loop closes a 13 pp SR gap over single-shot at ∼1.5× the token cost."
