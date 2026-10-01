# Prereg-v2 Design — Composite Command, Loop Map, Visual Urgency

**Prepared:** 2026-09-30

**Revision history:**

- Rev 3 (2026-10-01): USER DIRECTION — `proposed_plan` generalized from
  a `junction_clear`-only field to a strategy- and scenario-agnostic
  channel: new top-level section "(a0) Universal `proposed_plan`
  channel" owns the schema, the verify/repair contract, and the
  plan-quality metrics (now scored on **every** v2 decision, with
  oracle-order agreement wherever a cell defines a ground-truth
  order); section (a) keeps only the junction-specific constraints.
- Rev 2 (2026-10-01): USER DIRECTION — the composite command gains a
  VLM-emitted `proposed_plan` channel (propose-verify): the VLM may emit
  the full ordered action list, M3 audits and minimally repairs it
  rather than authoring the sequence outright, and plan agreement /
  edit distance / executed-plan provenance become registered metrics.
  Rewrites section (a)'s "Decision contract" and "Scoring"; the rev-1
  single-token contract survives as the degradation path.
- Rev 1 (2026-09-30): initial design, written immediately after the
  `prereg-v1` checkpoint tag, from the prereg-v2 registry (design spec
  rev 9.5 "Prereg-v2 registry", amendments item 30), the intersection
  resolvability study
  (`docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md`),
  the unified scene design (`3b3a529`), and the two literature reviews
  (`reports/Four way intersection robot congestion.md`,
  `reports/Congestion scenario coverage check.md`).

**Status:** DESIGN — nothing here is built. The v2 freeze happens only
after v1 collection completes and this design survives its own smokes.

---

## Relationship to prereg-v1 (discipline rules)

1. **v1 collection runs from the `prereg-v1` tag.** Every confirmatory
   episode is collected from the tagged tree with the frozen config md5s.
   v2 development proceeds on a separate branch
   (`feat/prereg-v2-composite`) cut from the tag; it never merges into
   the collection tree until collection is complete.
2. **No v1-frozen artifact changes.** Prompts (`prompt_v1.py`, builder,
   stage-2), Arm B rules, oracles, scenario YAMLs in the v1 battery, and
   the two pinned configs are frozen. A v2 build that would touch one of
   them (the Arm B same-axis filter, below, is the known case) lands
   only on the v2 branch; if a defect in a frozen artifact is found
   during collection, that is a protocol deviation logged in the
   amendments doc, not a silent fix.
3. **v2 scoring is registered before v2 collection**, same as v1: this
   document grows the oracle tables and criteria before any scored
   episode runs, and pilots used to size or debug are excluded from
   confirmatory counts.

---

## What v2 measures that v1 cannot

| Gap in v1 | v2 instrument |
|---|---|
| Four-way jam is classification-only (T1-X); no architecture on earth in our survey commands recovery from a formed scrum | (a) composite recede-then-yield → (d) resolution-scored IB10 |
| Whether the VLM can *sequence* a multi-robot resolution (vs only name the situation) is unmeasured in v1 | (a0) universal `proposed_plan` propose-verify channel, scored on every v2 decision in every scenario (rev 3) |
| `reroute` is a no-op re-send on the single-aisle map, so wait-vs-detour judgment is untestable | (b) loop map with a genuine alternative path |
| B2 urgency rides a text label (`priority` field); the visual channel is untested for urgency | (c) loaded-vs-empty prop pair |
| B3 scores only the ordered outcome; who *initiates* the slip is unobserved | (e) B3 first-to-slip variant (Rev 17: "B3 first-to-slip to v2") |

The headline claim v2 targets is the citation gap both literature
reports record: **no published system performs centralized commanded
recovery from a formed multi-robot scrum.** (a)+(d) is that system;
everything else is supporting coverage.

---

## (a0) Universal `proposed_plan` channel (rev 3)

A single optional field on the **stage-1 response for every strategy
and every scenario**, not a `junction_clear` extra: an ordered list of
`{robot_id, action}` entries that is the VLM's full proposed
resolution sequence. This is the channel that exercises multi-step
spatial reasoning (user direction, revs 2–3), and because it rides
every decision, plan-quality is measured across the whole v2 battery —
head-ons, junction scenes, convoys, and the loop map — not just IB10.

### Schema

- `proposed_plan: list[{robot_id, action}] | null`, Pydantic-validated:
  each robot at most once; unknown robot_ids rejected; list order is
  the proposed execution order.
- **Action vocabulary = the grounded primitives, nothing else:**
  `yield` (backup + sidestep + hold), `reverse`, `cross` (an ordered
  release slot), `wait` (hold in place), `reroute`, `continue`
  (proceed unchanged). Every legal leg maps to a command M3/M4 can
  already ground and execute; the vocabulary grows only when a
  primitive does.
- **Consistency rule:** the strategy token stays the headline answer
  (classification scoring, Arm B comparability, v1 continuity), and
  the plan must refine it — `yield` ⇒ exactly one `yield` leg,
  `temporary_wait` ⇒ a `wait` leg, `reroute` ⇒ a `reroute` leg,
  `junction_clear` ⇒ at least one `reverse` or `yield`. An
  inconsistent plan is treated as unparseable (reason logged), never
  silently reinterpreted.

### Verify/repair contract

Division of labor: **the VLM proposes, M3 verifies and minimally
repairs.** This generalizes the v1 swap gate from one robot to a
sequence, keeping the defense filmed in the 2026-09-30 live gpt-4o
demo. Per decision:

- Plan present, consistent, and every leg feasible (retreat room, band
  limits, exemption pairing, ordering executable) → **executed
  verbatim**, provenance `vlm_verbatim`.
- One or more legs infeasible → M3 applies the **minimal repair**
  (swap-style substitutions and reorderings toward its own derived
  plan, fewest edits first), provenance `repaired`, every edit logged
  with its reason (the sequence analogue of `yield_regrounded_reason`).
- Plan absent, unparseable, inconsistent, or repair distance over a
  registered bound → M3's own derived plan executes, provenance
  `m3_default` — which is exactly v1's behavior, so a plan-less answer
  degrades to the shipped pipeline in every scenario.

In two-robot head-ons the machinery reduces to the existing swap gate
(a one-leg plan repair), so v2 changes no v1 outcome semantics there —
it only starts *measuring* what the VLM proposed.

Rationale for optional, not mandatory: the presentation-order study,
ER-2's unused geometry block, and the live demo's infeasible yielder
all say VLM sequencing may be unreliable; propose-verify turns that
reliability into a measured quantity instead of a source of unresolved
episodes, exactly as B1 turned image-dependence into a measured
quantity. Parse/refusal surface grows by one structured field at
temperature 0, with one scenario-agnostic invitation sentence in the
prompt (v3 template, hash-frozen at the v2 freeze).

### Plan-quality metrics (registered, scored on every v2 decision)

- (i) *plan emission rate* — a parseable, consistent plan was supplied;
- (ii) *plan agreement rate* — verbatim-executable without repair;
- (iii) *plan edit distance* — repairs applied, with reasons;
- (iv) *executed-plan provenance* — `vlm_verbatim` / `repaired` /
  `m3_default`;
- (v) *oracle-order agreement* — wherever a cell defines a
  ground-truth order, the proposed order is scored against it
  **before** repair: T2b's `correct_order` [robot_1, robot_3], B2's
  priority-first, B3's convoy order, IB10's inside-first. This
  separates "can't sequence feasibly" from "sequences feasibly but
  picks the wrong order" — two different failure stories.

Arm B emits its plan through the identical field, so every metric has
a classical comparator. Condition on presentation order per amendments
A2. These are RQ-level outcomes, not diagnostics: they are the direct
measurement of whether the VLM performs multi-robot sequencing or only
situation naming.

---

## (a) Composite recede-then-yield command

### Decision contract

New M2 strategy enum value **`junction_clear`**, consuming the (a0)
channel with junction-specific validation: a consistent plan names the
recede set (≥ 1 `reverse` or `yield`) and a crossing order for the
rest. The VLM may alternatively emit only the strategy token — M3's
χ-ranked derivation then owns the sequence (`m3_default`), the rev-1
contract.

### Grounding (M3)

- **Cost-ranked recede selection:** χ = s·D_SPACE + t·N_f per A-DRIVE
  ([arXiv:2204.04910](https://arxiv.org/pdf/2204.04910)) — distance to a
  free evacuation pocket plus followers stacked behind. Single yielder
  by default; a two-robot recede (the IB10 cross pair) is a **staggered
  sequential** fallback, never simultaneous.
- **Geometry (from the study's Prereg-v2 Path):** the cross pair
  reverses along its own arms to |y| ≈ 1.2 (legs 0.93–0.95 m from
  ±0.25–0.27), landing in C′'s phase-1 geometry; the E-W yield then runs
  as already tabulated in the study.
- **Sequencing:** remaining robots cross in a per-episode priority
  order, inside-first; the yielder re-enters last. Reuses M4's ordered
  hold-until-last release (`crossing_chain.py`) unchanged.

### Prerequisites (build-order gates)

1. **J2 — junction-scoped backup clearance** (study build list item 1,
   ~10 lines + tests in shared M3). Binding: any N-S pass under the
   shipped `backup_clearance_m: 1.7` ends 0.28–0.45 m outside the
   tracked band and latches permanently for standoff offsets ≤ 0.13 m.
   Nothing else in (a)/(d) is smokeable before J2.
2. **Arm B same-axis filter** (study standing finding 2): waiting robots
   held in-zone from the first buffered frame lead Arm B's intersection
   order, making it inexecutable (escort through the partner at
   0.000 m). Mandatory for Arm B to be a fair v2 comparator. This edits
   a v1-frozen file → v2 branch only.
3. **M1 y-extent verification**: the study flags M1's y detection extent
   as unverified beyond the standoff band; the |y| ≈ 1.2 recede
   endpoints must be confirmed tracked before oracle design.

### Safety (M4)

No new M4 rules expected: `admitted_partners` already pairs a `reverse`
with every member of its own command, so the reverse legs (starting
0.24–0.34 m from the E-W pair) are exempt as-is. The standing
raw-`cmd_vel` obstacle-blindness note (amendments item 25) applies to
the recede legs — the scenario design must keep recede corridors free of
static obstacles, or M4 grows a leg-level check (decide at build time,
default: constrain the scene, not the safety code).

### M5

`junction_clear` dispatch is phased: recede phase (sequential, each leg
confirmed by odometry like `backup()`), then the yield phase, then the
ordered crossing. Failure at any phase falls back to the v1 behavior for
the remaining robots (single yield or no-op) and logs the phase reached
— partial credit is scorable.

### Scoring

- **Resolution-scored IB10** replaces T1-X's RQ1-only scoring: episode
  succeeds when all four robots reach goals, position-verified; phase
  reached is the ordinal partial score.
- **Plan-quality metrics:** per (a0), scored on every decision; IB10
  is simply the cell where the plan is hardest (four robots, two
  phases, inside-first oracle order).
- **Oracle:** correct recede pair by χ; correct order inside-first. The
  C′ caveat (GT oracle inactive at h = 1.2) applies to the *staged*
  variant, not the formed-jam composite — the jam forms first here, so
  `head_on_conflict_active`-style oracles need an intersection
  generalization; registered as design work, sized before freeze.
- **Regret:** extend the forced-strategy harness with `junction_clear`
  forced vs best single-yield forced; the v1 finding that single-yield
  cannot complete at all would make regret a censored feasibility
  contrast, mirroring T2b's cost model.

---

## (b) Loop map

A second E-W aisle plus two N-S connectors creates a cycle: `reroute`
becomes a genuine alternative with a measurable detour cost, not a
re-send.

- **Scene family:** blocker in the primary aisle; the manipulated
  variable is **blocker persistence**, encoded *visually* (prop class:
  fallen box = permanent vs a paused/faulted robot = plausibly
  transient) with no persistence hint in any text channel — B1's
  aperture logic applied to the temporal judgment. Oracle: timed cost of
  wait vs detour per episode; the correct answer flips with persistence
  and detour length.
- **Builds:** USD/map authoring (second aisle), Nav2 map + costmap
  update, M3 reroute grounding to a concrete alternate path (waypoint
  via the far aisle, not a goal re-send), scenario YAMLs, oracle cost
  tables from forced-wait and forced-reroute sweeps.
- **Risk:** Nav2 on a loop map may reroute *on its own* when the global
  costmap sees the blocker, pre-empting the decision layer. Design
  control: blocker placed so the global planner's path stays viable
  (narrowed-not-blocked, below costmap lethal threshold) while transit
  is throttled — the decision to detour must remain M2/M3's. This is
  the first thing the loop-map smoke must verify.

---

## (c) B2-visual urgency pair

v1 B2's `priority` field is read by M3 only and never rendered; v2 adds
the pair where urgency is *only* visual: one robot loaded (pallet prop
via the existing prop machinery), one empty, priority field absent.
Same 2-robot junction geometry, same oracle as B2 (priority robot
passes first). Scored as a modality contrast against the v1 B2 cell:
text-only (v1) vs image-only (v2) urgency. No new prompt version —
the prompt already carries no urgency text in the v2 cell by
construction.

---

## (e) B3 first-to-slip

Registered "to v2" at Rev 17. The convoy_counterflow variant where the
scored question is which convoy member initiates the slip (first-to-slip
identity and latency), not just the ordered outcome. Needs only scenario
YAML + oracle additions on the built B3 scene; no contract changes.
Design detail deferred until (a) and (b) are smoked — it shares no
machinery with them.

---

## Explicitly not in v2 (unchanged from rev 9.5)

The robot-blocker anomaly, the token-scale crowding scene, and the
three-active-robot B2 junction variant remain unregistered candidates.
The last is structurally impossible under v1 primitives (unified scene
design, B2 section); re-assess only after (a) exists, since
`junction_clear` may make it feasible — recorded here so the v2 freeze
makes an explicit include/exclude call.

---

## Build order

1. J2 + tests (shared M3; v2 branch).
2. Arm B same-axis filter + tests (v2 branch; protocol note that this
   diverges from the v1-frozen Arm B).
3. M1 y-extent verification run at |y| ≈ 1.2 (one VM session, mock).
4. (a0) universal plan channel: schema + consistency rules, the M3
   verify/repair engine with provenance logging, the plan-metrics
   scorer, Arm B plan emission, and the scenario-agnostic prompt
   invitation (`prompt_v2 → v3` template, hash-frozen at v2). Smoked
   first on the two-robot head-on, where it must reproduce v1's
   outcomes exactly (the swap gate as a one-leg repair) — that
   equivalence is the regression gate for everything after it.
5. `junction_clear` contract on top of (a0): M3 χ-ranked grounding +
   staggered recede, M5 phased dispatch, junction consistency rules.
   The repair-distance bound for falling back to `m3_default` is sized
   from the mock sweep in step 6 and frozen before live smokes.
6. IB10 composite mock smoke → live smoke (phase-by-phase).
7. Intersection oracle + regret extension; freeze IB10 scoring.
8. Loop map: USD + Nav2 + reroute grounding; the pre-emption control
   smoke before any scenario authoring.
9. B2-visual pair + B3 first-to-slip scenarios + oracles.
10. prereg-v2 freeze: hash table, pins, veto list — same procedure as v1.

Steps 1–3 are independent of v1 collection and can start immediately;
step 4 onward should be sequenced against collection so GPU-VM time and
API spend go to collection first.

---

## References

- Intersection resolvability study (S1):
  `docs/superpowers/specs/2026-09-29-intersection-resolvable-design.md`
- Unified scene design: `docs/superpowers/specs/2026-09-29-unified-scene-design.md` (`3b3a529`)
- Research design rev 9.5: `docs/superpowers/specs/2026-07-05-general-spatial-congestion-resolution-design.md`
- Amendments (decision record): `docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`
- Literature: `reports/Four way intersection robot congestion.md`,
  `reports/Congestion scenario coverage check.md`
