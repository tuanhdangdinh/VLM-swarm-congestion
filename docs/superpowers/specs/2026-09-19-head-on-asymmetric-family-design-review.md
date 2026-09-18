# Design Review — Head-On Asymmetric Scenario Family (T1/T2a)

**Prepared:** 2026-09-19

**Reviews:** `docs/superpowers/specs/2026-09-18-head-on-asymmetric-family-design.md` (Rev 2, Status "Approved for implementation")

**Status of this review:** Advisory. It does **not** change the spec's decisions. Two of them rest on assumptions that measurement has since contradicted, and the spec's owner should decide what to do before implementation begins. At the time of writing, implementation had **not** started — `isaac/scripts/generate_head_on_family.py`, `isaac/vgu_sim/family_oracle.py`, `scripts/vm/fc_launch.sh` and `isaac/config/scenarios/family/` did not exist on any branch.

**Source of evidence:** the Gemini Robotics-ER 2 evaluation and image-grounding study of 2026-09-18, on branch `feat/gemini-er2-backend`. See `docs/reports/2026-09-18-research-findings-register.md` (findings A1, A3, A6, A8, B1) and `docs/reports/2026-09-18-gemini-er2-image-grounding.md` (Experiments 1–6). Those files are on that branch, not this one.

---

## Summary

The family design is sound as scenario engineering, and its RQ5 (recovery) value is confirmed by live evidence. But **the T2a contrast is not answerable by Arm A as currently prompted**, for two independent and separately measured reasons. Left unchanged, variant `w0p2_eopen_o0` will record a near-deterministic first-shot failure that reads as a model result but is an interface artifact.

Both fixes are small, and one is already in the backlog as deferred.

---

## Finding 1 — The blocker is not observable by the reasoner

**The spec's asymmetry mechanism is a parked box.** `reasoning/vlm/prompt_builder.py` renders, per robot: `robot_id`, `x`, `y`, `theta`, velocities, `status`, `goal`; plus the derived pairwise distance/facing block; plus known robot ids and the guidance list. **There is no obstacle, blocker, barrier, wall, rack or occupancy channel in the prompt at all.**

Verify:

```bash
grep -niE "obstacle|blocker|barrier|wall|rack|occupanc" reasoning/vlm/prompt_builder.py
```

So the only channel through which the VLM could learn *which side is blocked* is the camera image. Finding **A1** measured that the decision does not use the image: in a 2×2 of congruent and deliberately incongruent (image, state) pairs on real frames measured at 0.251 m and 4.884 m separation, **gpt-4o followed the text in 10/10 incongruent calls and Gemini ER-2 in 10/10** under the production prompt (n = 5 per cell, both congruent gates passing 5/5). No justification in 79 such calls cited visual evidence.

Consequence: the family's asymmetry is invisible to the thing the battery is testing. `correct_yielder` can only be guessed.

Two secondary warnings attached to this:

- An `include_visual_crosscheck` prompt modality exists on `feat/gemini-er2-backend` and does make the image decisive — **but only on ER-2** (10/10), not on gpt-4o (1/10). It is not a fix for the `openai` arm (finding A6).
- Do **not** try to audit image use from `justification` text. Finding **A8**: with the cross-check enabled, gpt-4o's justifications mentioned the visual channel in 18/25 calls, and **9 of the 10 contradiction-cell calls asserted that the image agreed with the states** while the frame flatly contradicted them. The prose manufactures corroboration that the decision does not reflect.

## Finding 2 — The yielder-selection channel is a constant, not a choice

The spec states (Explicitly not changed / YAGNI): *"No new M2/M3 fields (`yield_robot` role fields remain Phase 1 Task 1); the VLM chooses the yielder by listing it first, which M3 already honours."* `reasoning/rag/command_grounder.py:146` (`robot_ids = decision.involved_robots`) confirms order is load-bearing downstream.

Measured across **every decision artifact on the VM** (524 files, `data/logs/**/*decision*.json`, all parsed, none unparseable):

| `involved_robots` | count |
|---|---|
| `['robot_1', 'robot_2']` | **71** |
| `['robot_2']` | 1 |
| empty (`congestion_detected=false`) | 442 |

Of the **44 `deadlock`/`yield` decisions, 44 listed `robot_1` first.** Not once `robot_2`. The one `['robot_2']` entry is a single-robot list from an `anomaly`/`priority_override` call under the experimental cross-check prompt, not a yielder choice.

The prompt itself renders states under the header *"Robot states (sorted by ID)"*, so ascending order is the path of least resistance and nothing asks the model to treat position as meaningful. Reproduce with:

```bash
# on the VM, from /home/ubuntu/vgu-vlm-swarm
python3 -c "
import json,glob,collections
c=collections.Counter()
for f in (f for f in glob.glob('data/logs/**/*.json',recursive=True) if 'decision' in f):
    d=json.load(open(f)); dec=d.get('decision') or {}
    ir=dec.get('involved_robots')
    if ir: c[tuple(ir)]+=1
print(c)"
```

Consequence: first-listed-robot is not a channel the model uses to express a decision. It is a formatting artifact.

## Combined effect on the v1 grid

With `arrival_offset_m = 0`, `fcfs_yielder` is `robot_1` in all three v1 variants.

| Variant | `correct_yielder` | Expected Arm A first answer | Reads as |
|---|---|---|---|
| `wopen_eopen_o0` (T1 control) | `robot_1` (FCFS) | `robot_1` | correct — but for no reason |
| `wopen_e0p2_o0` (T2a, FCFS happens to be right) | `robot_1` | `robot_1` | correct — but for no reason |
| `w0p2_eopen_o0` (T2a contrast) | `robot_2` | `robot_1` | **failure — but an interface artifact** |

The two "correct" cells are correct by coincidence of the default ordering, and the contrast cell fails without the model ever having had the information or the channel. As designed, the grid cannot distinguish a reasoning failure from an observability failure — which is precisely what T2a exists to measure.

Note the mirrored variant does still do useful work: it was included partly to expose robot-id bias, and given Finding 2 it will do exactly that.

---

## What is unaffected and worth keeping

**RQ5 is well served, and there is now live precedent.** Verification step 3 of the spec expects `yield(robot_1)` → FAILED → previous-attempt block → retry with a feasible yielder. On 2026-09-18 that loop was observed end to end on the simpler `head_on_deadlock` scenario with a live model: first decision `deadlock`/`reverse`, which failed; third decision cited the failure explicitly — *"Since the previous attempt to reverse both robots did not successfully resolve the deadlock, the yield strategy is now selected…"* — and `yield` cleared it. Both robots reached their goals. So the recovery mechanism the T2a episodes depend on demonstrably works on a real second decision rather than a fixture.

The computed-oracle approach, the tuning-parity rule (oracle and M3 sharing `reasoning.rag.scene_geometry`), the 0.3 m box sizing rationale, and the authoring-time mock-backend validity check all stand as written and are not affected by either finding.

---

## Recommended changes, in priority order

1. **Un-defer the explicit `yield_robot` field** (Phase 1 Task 1, currently listed under YAGNI). The 44/44 evidence says list order is not a usable channel. Until the model has a named field for "who yields", T2a measures ordering convention rather than choice. This is the cheaper of the two changes and it unblocks the contrast on its own.

2. **Add a free-space / obstacle block to the prompt as a declared modality**, following the existing pattern of `include_pairwise_geometry` (rev 8.5) and `include_visual_crosscheck`. Then run T2a **both ways**:
   - modality **on** → the battery tests spatial reasoning about retreat space, which is what T2a is for;
   - modality **off** → a clean, pre-registered demonstration of the information bound.

   That is a stronger result than either arm alone, it reuses machinery that already exists, and it keeps the off condition comparable with every run collected so far. If only one is affordable, run **on** for the contrast cell and cite the off condition from finding A1.

3. **Expect `reverse` as a likely first answer, not only `yield`.** On the simpler scenario the live model chose `deadlock`/`reverse` first. Finding **B1**: `reverse` is dispatched symmetrically to both robots, so they back up together and re-converge — it cannot resolve a two-robot head-on regardless of blockers. On a blocked side it will also fail, but for a *different* reason than a blocked yield. The analysis plan should separate "failed because the strategy cannot work" from "failed because the chosen side has no retreat space", or the T2a failure counts will conflate them.

4. **Merge the launch scripts rather than adding a second one.** The spec plans `scripts/vm/fc_launch.sh` (merging the VM-only `fc_check_launch.sh` / `fc_record_launch.sh`). `scripts/run_gemini_er2_demo.sh` on `feat/gemini-er2-backend` already does most of that job: scenario selection, `localization:=camera`, M1-before-Nav2 ordering, the recorder plus its fps re-timing caveat, `-w /ws` on every `docker exec`, key sourced inside the container, and a `BACKEND_ID` switch that restores the previous `reasoning_backend_id` on exit (including on `INT`/`TERM`/`HUP`). It lacks the spec's per-scenario spawn-pose reading and `warehouse_map_<name>` resolution. Extending it is less work than writing a parallel script, and two VM launchers will drift.

---

## Evidence locations

- `docs/reports/2026-09-18-research-findings-register.md` — findings A1, A3, A6, A8, B1 with sample sizes and `directional` labels (branch `feat/gemini-er2-backend`).
- `docs/reports/2026-09-18-gemini-er2-image-grounding.md` — Experiments 1–6: stimuli with measured separations, pre-stated criteria, per-cell tables (same branch).
- `scripts/probe_gemini_er2_grounding.py` — the 2×2 harness; `--backend`, `--experiment`, `--repeats`, `--visual-crosscheck`, `--dry-run` (same branch).
- VM `data/logs/er2_grounding/*.jsonl` — every call logged with condition, response, diagnostics, usage (git-ignored).
- VM `data/logs/**/*decision*.json` — the 524 artifacts behind Finding 2.

**Caveats on this review's own evidence.** Both findings are single-scenario. Finding 1 is measured at n = 5 per cell on two models with one contradiction stimulus pair. Finding 2 is a census of what has been collected so far, not an experiment — it shows the model has never used the ordering channel, not that it could not if asked. Temperature 0.0 on the OpenAI endpoint is near-deterministic but not deterministic (2–5 unique raw responses per 5 repeats), so each gpt-4o "5/5" carries roughly the information of n = 1 plus a stability check.
