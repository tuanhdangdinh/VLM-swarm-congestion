# Overnight Findings - New Host, Presentation-Order Probe, Live Counterbalanced Runs

**Prepared:** 2026-09-25

**Revision history:**

- Initial draft: overnight session of 2026-09-24/25 — new GPU host bring-up, closed-loop replication, offline presentation-order probe, and four live counterbalanced M2 runs.
- Rev 2 (2026-09-25): adds the M3 yield feasibility gate and random presentation order, five live validation runs, and a correction to the strength of the live order effect.
- Rev 3 (2026-09-25): adds the Gemini Robotics-ER 2 M2 backend — its offline presentation-order arm and four live closed-loop runs — plus two arithmetic/instrumentation corrections to Rev 1.
- Rev 4 (2026-09-25): adds the decisive ER-2 cell (west-blocked, `id_asc`, gate off, n=3) and the gpt-4o obstacles-OFF arm, a consolidated live tally across both models, and the finding that the offline probe does not predict live order sensitivity.
- Rev 5 (2026-09-25): adds the six-run Arm A pilot on the adopted defaults, the full gpt-4o refusal census, and the real-frame replay that identifies the annotated camera frame as the refusal trigger.
- Rev 6 (2026-09-25): completes the real-frame replay and identifies the obstacle text block as the carrier of the side signal under `id_desc`, adds the six-run ER-2 pilot, and records the position-verified arrival check that a Nav2 false success forced.
- Rev 7 (2026-09-26): re-scores every arrival against position, adds live batches 2 and 3 (gpt-4o random order, ER-2 forced order), reports that the side-carrier effect replicates in direction but not in magnitude, ships an unvalidated refusal mitigation, and corrects two safety metrics.
- Rev 8 (2026-09-26): adds the six-run ER-2 pilot on the `_gshort` goal-short variants — blocker-on-goal-path losses eliminated, a new park-beyond-goal failure introduced by symmetric ±1.5 goals — plus five apparatus notes from the batch.
- Rev 9 (2026-09-26): adds the three-run `_bshort` (blocked-side goal-short) pilot on the west variant — 3/3 position-verified arrivals, no reintroduced blocker-path loss, escort mechanism confirmed from ground truth — and next steps.
- Rev 10 (2026-09-26): adds the six-run `_bshort` validation batch at the widened ±2.6 passer goal — east (first ever) 3/3 and west 3/3, all position-verified — adopting `_bshort` as the pre-registration scenario; records a second G4-class interpenetration (K1, 0.076 m, pre-yield), a realised-goal-margin note, and the prereg amendment set this batch discharges into.
- Rev 11 (2026-09-26): the K1/G4 root-cause analysis (`docs/reports/2026-09-26-close-approach-analysis.md`) lands its corrections — the 0.076 m events were 51 s of driven nose-to-nose **contact**, not interpenetration; M4's coordination exemption had disarmed the monitor during an ER-2 `reroute`; the contact fields are hard-coded `[]` (no detector exists); and, contra Rev 7 §AC, both robots **did** go STALE in both runs.
- Rev 12 (2026-09-26): the M4 exemption fix lands and passes both VM regressions (mock-forced G4/K1 exposure now latches at 0.381 m with no contact; ER-2 yield flow unchanged), closing amendment A5; the Arm B classical reasoner slice (plan Tasks 4, 12–14) merges at `65cc850` with 70 new tests, discharging the "Arm B does not exist" freeze blocker at the reasoning-core level.

---

## Headline

**The yielder M2 names is a positional artifact, not spatial reasoning.** Under
the production default (`id_asc`, `robot_1` first) gpt-4o names
`yield_robot=robot_1` regardless of feasibility — 20/20 greedy offline samples
over both asymmetric variants, 36/39 at T=0.6, 1/1 live tonight (R2), 2/2 on
2026-09-19, plus symmetric E0 — and on the west-blocked variant that is a
deterministic failure (arrested 0.102 m from the blocker; 0.093–0.094 m on
09-19). Under `id_desc` it is a contest: west → `robot_2` at 0.8 / 0.7, east →
`robot_2` at 0.6 / 0.4 (T = 0.0 / 0.6). The correct yielder has no influence
(`P(correct)` 0.40–0.59 pooled; no justification in 360 offline calls or 4 live
runs cites the obstacle). gpt-4o-mini follows the slot (20/20 → 0/20, 40/40 → 2/40).

> Superseded by Rev 2 §C item 3 (Verdicts). The "`id_asc` always yields
> `robot_1`" framing overstates the live effect: pooled live runs put gpt-4o at
> `robot_1` in 7/9 regardless of order, and two identically configured runs
> disagreed. The offline probe numbers above are unchanged.

> Superseded by Rev 4 §L item 3: the offline slot numbers quoted here do not
> predict live behaviour at all — offline `P(robot_1 | id_desc)` = 0.25 pooled
> against 5/6 live. They stand as a result about the synthetic stimulus, not
> about the deployed pipeline.

> Superseded in part by Rev 6 §T: "the correct yielder has no influence" is a
> statement about `id_asc`. Replayed on real frames under `id_desc` with the
> obstacle text on, gpt-4o names the feasible robot in 96.2% of yields
> (p = 8.8e-4 against the text withheld). The model still never verbalises the
> blocker — 0/288 `<think>` traces name it — so "no justification cites the
> obstacle" stands as an observation about the output, not about the input.

---

## Caveat That Must Travel With the Headline

The three live `id_desc` runs all yielded the robot that was in fact feasible.
**This is a coincidence of the scenario design, not evidence of feasibility
reasoning.** On the west-blocked variant the first-listed robot happens to be
the feasible one; on the east-blocked variant `robot_1` happens to be the
feasible one. Each of the two competing biases therefore aligns with feasibility
in exactly one variant. The offline probe samples the same cells and puts
`P(correct)` at chance.

Do **not** report "the model moves to the feasible robot under `id_desc`".

### Consequences for the pre-registration

- Every decision artifact collected before commit `922dd36` was rendered at
  `id_asc` and carries this bias.
- The 2026-09-19 obstacle-channel A/B must be re-labelled **confounded**, not
  reported as a modality result.
- The obstacle channel is ineffective in **both** text and image. With the
  channel off all three variants render a byte-identical prompt and differ only
  in the image; moving the blocker west ↔ east changes nothing detectable.
  *Superseded by Rev 3 §G for the text channel: this holds for gpt-4o and
  gpt-4o-mini only. On ER-2 the obstacle text drives `yield` to zero
  (0/60 named yielders with the channel on against 13/60 off, p = 1.2e-4). The
  image half of the claim stands for all three models.*
  *Superseded for gpt-4o in both halves by Rev 6 §T: the channel is not
  ineffective, it is unobservable under `id_asc`. On real frames under
  `id_desc`, withholding the obstacle text drops P(feasible) from 0.962 to
  0.556 (p = 8.8e-4) and replacing the frame with grey drops it to 0.694
  (p = 0.0095). The 2026-09-19 A/B stays confounded, but the reason it read
  null is the order it was run at.*

---

## Apparatus: New Isaac Sim Host

The previous VM (project `summer-flux-501516-n6`) cannot start: `NVIDIA_L4_GPUS`
quota is 0 in every region and the self-service increase was auto-denied with
`NOT_ENOUGH_USAGE_HISTORY`. A replacement host was built on the
`thule01204@gmail.com` account.

| Item | Value |
|---|---|
| Instance | `vgu-vgu-thule-base-isaac-workstation-vm` |
| Project | `project-355a9186-f6f8-4b89-a44` |
| Zone | `us-central1-c` (zone `-a` was a stockout) |
| Machine | `g2-standard-8` + NVIDIA L4, driver 595.84 |
| IP | `136.112.162.215` |
| Isaac Sim | v6.0.1, source build |
| Container | `vgu_ros` from the 2026-09-16 recipe, plus `requests` |

Isaac Sim was pinned to a source build because Isaac Automator's
`--isaacsim latest` would have installed 7.0.0a1. The full asset chain was
rebuilt on the new host: the robot with all four visual meshes (`burger_base`
48 040 points), six scenario USDs, and `validate` PASS on four scenarios. A
headless smoke run reported `completed: true` with 3 001 ground-truth records
over 300 sim-seconds, at a render mean of 127.94 against 127.95 on the old host.

The VM was left **RUNNING** for the morning. It bills at roughly US$0.9/h, but
stopping it risks an L4 stockout on restart — this is the owner's call.

### Deploy lessons

- `--from-image` is project-scoped, so an image from the old project is not
  reachable from the new one.
- `latest` resolves to `main`, which is how 7.0.0a1 nearly got installed.
- The local Automator docker controller was OOM-killed; the remote build it had
  started survived and completed.
- The NoMachine `.deb` install failure is harmless for headless work.
- `run_simulation.py --duration-sec` is a **dead flag** — it is never wired into
  `ResolvedRunConfig`, and the scenario YAML's 300 s governs instead.

Full detail is in the M6 entries of `docs/implementation_notes.md` dated
2026-09-25.

---

## E0 - Closed Loop Replicated on the New Host

Run `20260924_193112`, scenario `head_on_deadlock`, gpt-4o at temperature 0.0,
obstacle modality **off**.

| Measure | Value |
|---|---|
| First analysis | +34.6 s after components started |
| Onset min pairwise | 0.256 m (M1 scene log) / 0.264 m (ground truth) |
| Maneuvers | 1 `yield` (`yield_robot=robot_1`), COMPLETED after 148 s |
| Arrivals | 2/2 — `robot_2` at +3.3 min, `robot_1` at +5.5 min |
| Wall clock | 12 m 52 s |
| Post-arrival analyses | 0 (2 348 `trigger suppressed` lines) |

The 0.256 m onset is a **third onset mode**, sitting between the 0.08 m contact
onset and the ≈0.45 m planner-stall onset recorded previously.

### Deviation: the congestion gate fires on single-robot stalls

After `robot_2` had already arrived, a solo stall of `robot_1` triggered a
second analysis:

```text
[orchestrator_node]: starting analysis request=0075ff94... robots=['robot_1'] reason=1 robot(s) stalled >= 12.0s distance_to_goal_m={'robot_1': 3.79}
```

The prompt for that request shows the two robots 1.18 m apart and not mutually
facing:

```text
- robot_1 <-> robot_2: distance 1.18 m; robot_1 faces robot_2: no; robot_2 faces robot_1: yes
```

M2 answered `anomaly` / `reroute`, which COMPLETED and was harmless. The
pre-registration's episode rule needs to account for single-robot stalls
entering the M2 pipeline.

---

## Offline Presentation-Order Probe

Commits: `922dd36` (the modality), `dadb3f5` (probe plus raw data), `1c61d7f`
(report).

**Design.** Three scenario variants x order `{id_asc, id_desc}` x obstacle
channel `{on, off}` x temperature `{0.0 with n=5, 0.6 with n=10}`, on gpt-4o and
gpt-4o-mini. 360 calls total, **zero parse failures and zero API errors**, at a
cost of US$1.82.

**Verdicts.** `H_geom` is refuted; `H_id` is refuted; gpt-4o-mini matches
`H_slot` outright; gpt-4o is slot-dominant with a residual `robot_1` pull.

### Pooled order effect

| Model | T | `id_asc` P(robot_1) | `id_desc` P(robot_1) | Fisher exact (two-sided) |
|---|---|---|---|---|
| gpt-4o | 0.0 | 20/20 | 5/20 | p = 7.7e-07 |
| gpt-4o | 0.6 | 36/39 | 19/40 | p = 1.7e-05 |
| gpt-4o-mini | 0.0 | 20/20 | 0/20 | p = 1.5e-11 |
| gpt-4o-mini | 0.6 | 40/40 | 2/40 | p = 1.4e-13 |

*The last row is superseded by Rev 3 §G: the exact Fisher implementation returns
p ≈ 1.6e-20 for 40/40 versus 2/40, not 1.4e-13. The other three rows reproduce
exactly and the direction of this one is unaffected.*

The bias **survives removal** of the old "first listed robot backs up"
instruction, so it is not instruction-compliance.

### Probe caveats

- Synthetic top-down image, not a camera frame.
- No `goal` or `task` fields on the robot states — this mirrors live M5, which
  has never sent them.
- The 0.70 modal-share margin was chosen post hoc and is disclosed as such.
- 128 of the 360 calls needed a retry after an HTTP 429; the reissued payload is
  identical and the prompt SHAs were verified.

Per-cell tables, cost breakdown and the full interpretation are in
`docs/reports/2026-09-25-presentation-order-probe.md`.

---

## Live Counterbalanced Runs

gpt-4o, obstacle modality **on**, on tree `1c61d7f` verified on the VM by
`md5`.

| Stamp | Scenario | Order | First `yield_robot` | Prompt robot order | First maneuver | Yielder backup / clearance | Arrivals | Analyses / dispatches |
|---|---|---|---|---|---|---|---|---|
| `20260924_195708` (R1) | `w0p2_eopen` | `id_desc` | `robot_2` | `[robot_2, robot_1]` | COMPLETED 146.4 s | backed 0.304 m into open space | 2/2 | 5 / 1 |
| `20260924_201328` (R2) | `w0p2_eopen` | `id_asc` | `robot_1` | `[robot_1, robot_2]` | FAILED 243.7 s | backed 0.098 m, arrested 0.102 m from the blocker face at x = -1.70 | 1/2 | 4 / 4 |
| `20260924_203437` (R3) | `wopen_e0p2` | `id_desc` | `robot_1` | `[robot_2, robot_1]` | COMPLETED 150.4 s | backed 0.298 m into open space | 2/2 | 5 / 1 |
| `20260924_205009` (R4) | `wopen_e0p2` | `id_desc` (repeat) | `robot_1` | `[robot_2, robot_1]` | COMPLETED 147.3 s | backed 0.300 m | 2/2 | 5 / 1 |

Pre-dispatch minimum pairwise separations were 0.212 / 0.291 / 0.306 / 0.368 m.
Separately, and over the whole of each run rather than up to dispatch, the
ground-truth stream records **zero contacts** — robot-robot and robot-obstacle
alike — in all four runs.

> Superseded by Rev 7 §AC: this is detector silence, not evidence. Ground truth
> reported `robot_robot_contacts` 0 throughout a sustained 0.076 m centre-to-centre
> wedge in run G4, so the contact flags do not measure contact. Use the minimum
> pairwise distance channel instead.

Later decisions: R1, R3 and R4 each produced post-resolution re-analyses
returning `congestion_detected=false`, plus `decision=None` parse failures — two
in R1, one in R3, three in R4, six in total. R2's chain is set out below.

In R2 the named yielder failed, was re-selected after one intervening maneuver,
failed again, and only then did the episode reach a strategy that moved:

```text
[orchestrator_node]: request=a1672ca1... failure_context attached command=910a0aeb...-yield strategy=yield executed=yield outcome=failed
[orchestrator_node]: request=7482f0ad... failure_context attached command=a1672ca1...-temporary_wait strategy=temporary_wait executed=temporary_wait outcome=completed
[orchestrator_node]: request=e02a8692... failure_context attached command=7482f0ad...-yield strategy=yield executed=yield outcome=failed
```

`robot_1` never arrived in R2; `robot_2` completed under the final `reverse`.

### Prediction check

| Check | Expected | Actual |
|---|---|---|
| west-blocked, `id_desc` | `robot_2` named, maneuver completes | `robot_2`, COMPLETED 146.4 s — PASS |
| west-blocked, `id_asc` | `robot_1` named, FAILED at ≈0.09 m | `robot_1`, FAILED 243.7 s at 0.102 m (2026-09-19: 0.093–0.094 m, 254 s) — PASS |
| east-blocked, `id_desc` | `robot_2` named | `robot_1` named twice (R3, R4) — FAIL |
| No robot-robot or robot-obstacle contact | 0 contacts | 0 contacts in all four runs — PASS |

> Superseded by Rev 7 §AC for the contact row: that PASS rests on a detector that
> stayed silent at 0.076 m centre separation (G4), so it does not establish
> no-contact. Re-run the check against minimum pairwise distance and against
> `safety.yaml` `min_distance_m: 0.45`, which these runs also breach.

Follow-up on the failed check: the east-blocked `id_desc` cell with the obstacle
channel on — the cell these live runs sample — is a near coin flip offline,
`P(robot_2)` = 0.60 at T=0.0 and 0.40 at T=0.6, hence `P(robot_1)` = 0.40 and
0.60. Two `robot_1` draws sit comfortably inside that distribution. That
`robot_1` also happens to be the feasible robot on the east-blocked variant is a
design coincidence, not feasibility reasoning — none of the four live
justifications mentions the obstacle. See the caveat section above.

### Apparatus notes for these runs

`static_obstacles` ships **commented out** in
`ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`. Setting
`prompt_static_obstacles: true` on its own therefore renders **no obstacle
block at all**, while the launcher's `MODALITY` guard still reports the channel
as on. The list had to be uncommented and its `x` set per scenario: `-1.85` for
the west-blocked variant, `+1.85` for the east-blocked one. The rendered block
was confirmed present in all four runs, for example:

```text
Static obstacles (world-frame axis-aligned boxes):
- obstacle_1: centre (-1.85, 0.00) m, extent 0.30 x 0.30 m
```

R3 needed one rerun after a Nav2 lifecycle-timeout abort left a stale Isaac
process alive through the launcher's exit trap. R4 replaced a planned symmetric
run, which would have had no blocker, hence no coherent obstacle list and no
discriminating outcome. Config was restored afterwards (`id_asc`, `false`, list
re-commented, installed YAML `md5` equal to source).

Artifacts live in `data/logs/vm_runs/<STAMP>/` — git-ignored, on the local
workstation only.

---

## Secondary Findings

### (a) Failure-context memory is one attempt deep

**This corrects the working assumption carried into the write-up.** The
artifacts show that both times M2 was handed a *failed yield* context it did
steer away: `a1672ca1` saw `yield failed after 244 s, yield_robot: robot_1` and
chose `temporary_wait`; `e02a8692` saw `yield failed after 199 s` and chose
`reverse`. The re-yield of `robot_1` happened at `7482f0ad`, whose attached
context was the *intervening completed* maneuver:

```text
Previous attempt in this episode:
- strategy=temporary_wait, outcome=completed
- detail: temporary_wait completed 18 s ago; congestion re-detected for the same robots
```

So the failure of the yield had already been displaced from the prompt by a
single successful maneuver before M2 re-selected the same infeasible yielder.
The defect is **memory depth**, not an absent steering effect. n = 1; worth a
targeted test.

### (b) Parse failures on post-resolution re-analyses

Six re-analyses across R1, R3 and R4 returned `decision=None` with
`parse=failed, attempts=2`:

```text
[orchestrator_node]: request=4a9d0579... no dispatch stage=vlm reason=decision=None
```

None ever affected a dispatch — every one occurred after the congestion had
already resolved — but this is a parse-robustness item.

> Superseded by Rev 5 §P. These six are not a parser defect: the census finds
> every gpt-4o parse failure in the local corpus to be a safety refusal, and
> its per-run table scores exactly these terminal refusals in R1 (2), R3 (1)
> and R4 (3). The item is refusal handling — retry policy and stimulus — not
> JSON-extraction robustness.

### (c) Solo-stall triggering

Covered under E0 above: the congestion gate fires on a single stalled robot.

### (d) Recurring Nav2 planner error

```text
[robot_2.planner_server]: Failed to create a plan from potential when a legal potential was found. This shouldn't happen.
```

Counts: R2 x3, R3 x1, R4 x1. It recurs during stalls and did not by itself
block any run.

### (e) Baseline unit-test failures on the Mac

55 failures plus 3 collection errors: `usd-core` is absent, and 50
`test_aruco_parity` cases fail on this OpenCV build. These are environmental and
unchanged by tonight's commits.

---

## Implications and Next Steps

1. Treat M2's `yield_robot` selection as **invalid as a reasoning channel**.
   Decide between (a) randomising or counterbalancing presentation order per
   episode and recording it in the artifact, (b) moving yielder selection to M3
   feasibility grounding (`reasoning/rag/scene_geometry`, which the oracle
   already uses), or (c) both — before any Arm A/B collection.
   *Superseded by Rev 2 §D item 1 (Recommended Next Steps): both were built and
   live-validated; the decision is settled.*
2. Re-label the 2026-09-19 A/B as confounded in the findings register, and add
   tonight's probe and live runs.
3. Run a targeted test of failure-context memory depth (n >= 3, west-blocked,
   `id_asc`), specifically whether an intervening successful maneuver lets M2
   re-select a yielder that has already failed.
   *Superseded by Rev 2 §D item 3 (Recommended Next Steps): run L4 reproduced
   the behaviour, so the open question is now memory depth policy, not whether
   it happens.*
4. Fix the parse-failure path; start by inspecting the six raw responses stored
   in the decision artifacts.
5. Wire `--duration-sec` through to `ResolvedRunConfig` or remove the flag.
6. Make the launcher's `MODALITY` guard also assert that `static_obstacles`
   renders at least one line, not just that the boolean is set.
7. Decide on the VM: keep it running at ~US$0.9/h, or stop it and accept the L4
   stockout risk on restart.
8. The ER-2 / Gemini arm was **not** run tonight. `GEMINI_API_KEY` is available;
   the backend lives on branch `feat/gemini-er2-backend`, currently 14 ahead and
   17 behind `main`.
   *Superseded by Rev 3 §F–§H: the branch was merged at `c7a08e7` and ER-2 has
   since been run both offline (180 calls) and live (four closed-loop runs).*

---

## Provenance

Work landed on `fix/deadlock-collision-resolution`, which was first
fast-forwarded from `780fa37` to `main` at `f2ca3c6` (it had no unique commits).

| Commit | Content |
|---|---|
| `922dd36` | `feat`: robot presentation-order prompt modality |
| `dadb3f5` | `feat`: presentation-order offline probe and raw data |
| `1c61d7f` | `docs`: presentation-order probe report |
| `d58214c` | `docs`: new Isaac host bring-up and closed-loop replication |
| this commit | `docs`: overnight findings 2026-09-25 (this report plus the notes entry) |

**Nothing has been pushed.**

Run ids: `20260924_193112`, `20260924_195708`, `20260924_201328`,
`20260924_203437`, `20260924_205009`. The VM clock is UTC, so these carry a
`20260924` stamp for a local date of 2026-09-25.

Related documents:

- `docs/reports/2026-09-25-presentation-order-probe.md` — offline probe, per-cell tables.
- `docs/reports/2026-09-18-head-on-family-validity.md` — the 2026-09-19 Runs A/B being replicated.
- `docs/implementation_notes.md` — dated entries under the M2/M5 and M6 sections.

---

## A. What Was Built

Commits landed on `fix/deadlock-collision-resolution` after `22d8857`.

### Random presentation order (`43bf941`, `6a52c94`, branch `feat/order-random`)

M5 gains `prompt_robot_order: random`. `swarm_orchestrator/presentation_order.py`
adds `derive_order_seed(run_id, session_id)` (SHA-256 based),
`PresentationOrderPolicy(mode, seed).order_for_episode(k)` and an
`EpisodeOrderTracker`. One order is drawn per episode, where an episode is the
`AttemptMemory` scope — opened on a disjoint robot set, closed on base-mission
arrival — reusing the drawn order across every re-analysis inside it. The seed
comes from `prompt_robot_order_seed`, else from `VGU_RUN_ID`.

Decision artifacts now carry `robot_presentation_order`,
`prompt_robot_order_mode`, `prompt_robot_order_seed` and `episode_index`, and
the node logs the drawn order on its `starting analysis … order=…` line.

Note: with two robots, a run whose deadlock resolves to arrival is a single
episode, so it draws one order for the whole run. Counterbalancing therefore
happens **across** runs, not within them.

### M3 yield feasibility gate (`06feaf8`, `8362178`, `9d02a70`, branch `feat/m3-yield-feasibility`)

The feasibility math moved into `reasoning/rag/scene_geometry.py` —
`required_room_m`, `room_is_feasible`, `yield_retreat_room_m`, `yield_feasible`
— and is now shared with `isaac/vgu_sim/family_oracle.py`. The regenerated
family YAML oracle blocks are byte-identical to the previous ones, pinned by a
test. `ground_reasoner_result` takes `static_obstacles=()` and
`yield_feasibility_mode="off"|"swap"|"refuse"`, exposed as the M5 key
`grounding_yield_feasibility: "off"`.

The quoting matters: a bare `off` is YAML `false`, so the value must stay
quoted.

### Provenance and merges (`d1152f4`, `17fcddd`, `0873fe4`, `f027d63`)

`d1152f4` and `17fcddd` are the two feature merges. `0873fe4` records the gate's
work in the decision artifact as `grounding_yield_feasibility`,
`yield_robot_grounded_from`, `yield_regrounded_reason` and
`yield_refusal_reason`, with matching node logs
`yield re-grounded request=… from=… to=… reason=…` and
`yield refused request=… reason=…`. `f027d63` pairs the missing-command
artifact test with its real terminal stage.

Suite result: 778 passed, with an environmental failure set identical to the
baseline (55 failed plus 3 collection errors — see Rev 1 §6(e)).

---

## B. Live Validation

Five runs on the VM, gpt-4o at temperature 0.0, obstacle channel **on** with
`static_obstacles` uncommented and `x` set per scenario. Tree `f027d63` was
verified by `md5`, and the installed YAML was verified by content before each
launch.

| Run | STAMP | Scenario | Order mode → effective (seed) | Gate | M2 `yield_robot` | M3 grounded (from → to) | First maneuver | Min gap yielder → box face | Arrivals | Analyses / dispatches |
|---|---|---|---|---|---|---|---|---|---|---|
| L1 | `20260925_002713` | `w0p2_eopen` | `id_asc` → `id_asc` (5185357977762094366) | `swap` | `robot_1` | `robot_1` → `robot_2` | `yield` COMPLETED 148.4 s | 0.200 m (never approached) | 2/2 | 6 / 1 |
| L2 | `20260925_004252` | `wopen_e0p2` | `id_desc` → `id_desc` (11656668545097010666) | `swap` | `robot_1` | none (feasible) | `yield` COMPLETED 148.1 s | 0.200 m | 2/2 | 24 / 1 |
| L3 | `20260925_005754` | `w0p2_eopen` | `random` → `id_asc` (156520638558926371) | `swap` | `robot_2` | none (feasible) | `yield` COMPLETED 145.1 s | 0.200 m | 2/2 | 5 / 1 |
| L4 | `20260925_011246` | `w0p2_eopen` | `random` → `id_desc` (15499629317569465484) | `off` | `robot_1` | none (gate off) | `yield` FAILED 251.2 s | 0.102 m | 0/2 | 4 / 4 |
| L5 | `20260925_012747` | `w0p2_eopen` | `id_asc` → `id_asc` | `refuse` | `robot_1` | refused → `temporary_wait` | `temporary_wait` COMPLETED 19.0 s (not comparable) | `robot_1` 0.200 / `robot_2` 0.150 m | 1/2 | 19 / 4 |

L1's swap, the gate doing the work it was built for:

```text
[orchestrator_node]: yield re-grounded request=035d60ce68e944c989f184b1864c99fd from=robot_1 to=robot_2 reason=yield re-grounded: robot_1 has 0.70 m retreat room < 1.08 m required; robot_2 feasible
```

L5's refusal on the same geometry:

```text
[orchestrator_node]: yield refused request=ad9195b97676451890c570bca3a67db1 reason=yield refused: robot_1 has 0.70 m retreat room < 1.08 m required
```

The matching L1 artifact fields, which make the intervention auditable without
reading the log:

```json
{
  "robot_presentation_order": "id_asc",
  "prompt_robot_order_mode": "id_asc",
  "prompt_robot_order_seed": 5185357977762094366,
  "episode_index": 0,
  "grounding_yield_feasibility": "swap",
  "yield_robot_grounded_from": "robot_1",
  "yield_regrounded_reason": "yield re-grounded: robot_1 has 0.70 m retreat room < 1.08 m required; robot_2 feasible",
  "yield_refusal_reason": null,
  "decision": { "yield_robot": "robot_1" }
}
```

`episode_index` stayed `0` across the re-analyses of an episode — every decision
in L3 and L4 carries `episode_index=0` — confirming one draw per episode.

### Run-level detail

- **L4** never recovered: `yield`(`robot_1`) FAILED → `temporary_wait`
  COMPLETED → `yield`(`robot_1`) FAILED again → `reverse`(`robot_2`).
  `conflict_active` ran from 20.1 s to 293.5 s.
- **L5** after the refusal ran `reverse` → `yield`(`robot_2`) →
  `reroute`(`robot_2`, FAILED). `robot_1` arrived; `robot_2` stalled at
  x = −1.550.
- **L2** needed 8 `Failed to make progress` recoveries for `robot_1` to get
  round the east blocker. That blocker lies on `robot_1`'s own path to goal — a
  property of the scenario family, in which the blocker sits on the opposing
  robot's goal path — so arrival counts absorb the Nav2 recoveries around it.

---

## C. Verdicts

1. **`swap` is the effective fix.** On the cell that failed deterministically
   (`id_asc`, west-blocked — the 09-19 A/B, `20260924_201328`, and L4) it
   produced a completed yield and 2/2 arrivals (L1). It is a no-op when the
   chosen yielder is already feasible (L2, L3), and it never harmed a run.
   `refuse` is inferior (L5). Recommend `swap` as the production and experiment
   default, with the artifact fields making every intervention auditable.
2. **Random order works mechanically but does not change outcomes by itself.**
   Provenance is verified end to end, and L4 still failed. It is a de-biasing
   instrument for the matrix, not a success mechanism.
3. **Correction to Rev 1's framing** (Rev 1 §1's "always yields `robot_1` under
   `id_asc`" is superseded). Live, the slot manipulation is weaker than the
   offline probe measured. Pooling all obstacle-ON live runs on the asymmetric
   variants (09-19 Run B; `20260924_195708`, `201328`, `203437`, `205009`;
   L1–L4; n = 9), gpt-4o named `robot_1` in **7/9 regardless of order**. Under
   `id_desc` live it named `robot_1` in 4/5 (R3, R4, L2, L4; R1 chose
   `robot_2`) against 0.25 pooled offline; under `id_asc` on the west-blocked
   scene it named `robot_1` in 3/4 live (L3 chose `robot_2`). L1 and L3 share an
   identical configuration and produced different yielders, so **temperature 0.0
   is not deterministic run to run** — runs must be treated as samples.
   Unchanged and reinforced: geometry does not drive the choice (the blocked
   `robot_1` was chosen in L1, L4, R2 and the 09-19 A/B), which is exactly why
   the gate is needed. Plausible but unverified reasons for the live/offline
   gap: the live prompt carries the real M1 annotated frame and live distances
   where the probe used a synthetic plan view, and n is small.
   *Superseded by Rev 4 §M: the live tallies here are extended by the
   obstacles-OFF arm (O1, O2) and re-stated per cell for both models; see
   Rev 4 §L item 3 for the live/offline gap, which is now a finding rather than
   a plausible reason.*
   *Further superseded by Rev 6 §T for "geometry does not drive the choice":
   that holds under `id_asc`, where the slot and ID priors agree and swamp the
   evidence. Under `id_desc` on real frames the obstacle text decides the
   yielder (P(feasible) 0.962 against 0.556 with the text withheld). The
   conclusion drawn from it — that the M3 gate is needed — is unchanged,
   because the production-default order is the one where the choice is
   feasibility-blind.*
4. **Caveat, kept from the run agent.** Every run in this batch had the obstacle
   channel ON, so order and channel co-vary within the batch. The offline probe
   found the channel inert, so this is unlikely to matter, but an obstacles-OFF
   live arm would close it.
   *Partly superseded by Rev 3 §G: "inert" is a gpt-4o result and does not
   generalise — the same channel has a large effect on ER-2, so the
   obstacles-OFF arm has to be run per model.*
   *Further superseded by Rev 6 §T: "inert" is not a gpt-4o result either. The
   probe that found it was run at `id_asc`, where the channel cannot show. On
   real frames under `id_desc` the same text block is the dominant input
   (P(feasible) 0.962 with it on against 0.556 with it off, p = 8.8e-4).*

---

## D. Recommended Next Steps

These replace items 1 and 3 of Rev 1 §7 (Implications and Next Steps); the
remaining §7 items stand.

1. Adopt `grounding_yield_feasibility: "swap"` plus `prompt_robot_order: random`
   (seeded per paired run) for Arm A collection, and record both in the
   pre-registration. Keep `static_obstacles` uncommented per scenario, and make
   the launcher's `MODALITY` guard fail when the list renders no line.
2. Run an obstacles-OFF live arm (`id_asc`/`id_desc` × west/east, n ≥ 3 per
   cell) to separate order from channel live, and to estimate the live
   `P(robot_1)` under `id_desc` with a real n.
3. Settle failure-context depth. L4 re-yielded `robot_1` after an intervening
   successful `temporary_wait` — the same one-attempt-deep memory described in
   Rev 1 §6(a). Decide whether the context should carry the last N attempts or
   the last failed one.
4. Note the family scenario asymmetry. The east variant's blocker obstructs
   `robot_1`'s goal path (8 recoveries in L2); consider whether arrival time or
   `conflict_active` duration is the cleaner outcome measure.

---

## E. Rev 2 Provenance

Commits: `43bf941`, `6a52c94`, `06feaf8`, `8362178`, `9d02a70`, `d1152f4`,
`17fcddd`, `0873fe4`, `f027d63`, plus this docs commit.

Run ids: `20260925_002713`, `20260925_004252`, `20260925_005754`,
`20260925_011246`, `20260925_012747`.

The VM config was restored byte-exact to `f027d63`
(`md5` `3ed3795f174c3df079e050e9b4e49572`), the container was restarted, and the
GPU is idle. Artifacts remain git-ignored under `data/logs/vm_runs/`.

---

## F. Gemini Robotics-ER 2 as the M2 Backend

`feat/gemini-er2-backend` was merged at `c7a08e7`. The two crosscheck prompt-SHA
re-pins in `590ac23` are explained by the FR2.1.9 prompt edits, not by a prompt
regression (notes entry `e6be85c`). The suite went from 864 to 878 tests with the
probe's seed-sweep extension.

| Item | Value |
|---|---|
| M5 selection | `reasoning_backend_id: gemini`; launcher `BACKEND_ID=gemini` |
| Model | `config/models.yaml` `vlm.gemini`, `model_id: gemini-robotics-er-2-preview` |
| Thinking | `thinking_level: low`, `force_schema: false` |
| Credential | `GEMINI_API_KEY` from the environment |
| Transport | Interactions API (`POST /v1beta/interactions`), not `:generateContent` |

The Interactions API exposes no `temperature`, `top_p` or `top_k`, so the shared
sampling preset is dropped and recorded rather than applied. Every artifact and
probe record carries the same block:

```json
{"presence_penalty": 0.0, "temperature": 0.6, "top_k": 20.0, "top_p": 0.95}
```

Two structural consequences follow, and both are permanent properties of this
backend rather than configuration choices. Sampling is at provider default and
cannot be pinned, so ER-2 and gpt-4o cannot be matched on decoding. And no
`<think>` block is ever emitted although thinking is billed — 50 to 899 thought
tokens per live decision, 49 857 across the 180 offline calls — so the reasoning
that produced a decision is not inspectable.

A one-call pre-flight probe on the VM returned HTTP 200 in 5.6 s. Offline the
seed is deterministic: the symmetric variant's channel-on and channel-off cells
render a byte-identical prompt and returned identical `(strategy, yield_robot)`
pairs on all 15 seeds, seed for seed.

---

## G. Offline Presentation-Order Probe With ER-2

Commits `8df0e92` (probe run), `908d641` (raw data), `58dfa43` (report Rev 2),
`061c6a3` (pacer fix). 180 calls — 12 cells × 15 seeds — with **zero parse
failures and zero API errors**, at approximately US$0.73 on standard pricing
(US$0.00 on the free tier). The stimuli are the gpt-4o arm's: re-rendering the
cells reproduces the committed prompts and images byte-for-byte, so all three
models saw identical text and identical pictures. The synthetic plan-view caveat
weighs more here than in Rev 1, because ER-2 is a vision-first robotics model and
may be reading an out-of-distribution image.

### Headline: ER-2 rarely yields

The strategy split is 155 `reverse` to 25 `yield`. ER-2 mostly declines the
adjudication the prompt asks for and answers "both robots back up" with
`yield_robot=null`.

`named` is how many of the 15 calls returned a non-null `yield_robot`; the three
`P(...)` columns are over those calls only and are `-` when there are none.
`P(strategy != yield)` is over all 15.

| Variant | Order | Obstacles | n | parse fail | named | modal yielder | P(first-listed) | P(robot_1) | P(correct) | P(strategy != yield) |
|---|---|---|---|---|---|---|---|---|---|---|
| `w0p2_eopen` | `id_asc` | off | 15 | 0 | 2 | robot_1 | 1.00 | 1.00 | 0.00 | 0.87 |
| `w0p2_eopen` | `id_asc` | on | 15 | 0 | 0 | - | - | - | - | 1.00 |
| `w0p2_eopen` | `id_desc` | off | 15 | 0 | 4 | robot_1 | 0.25 | 0.75 | 0.25 | 0.73 |
| `w0p2_eopen` | `id_desc` | on | 15 | 0 | 0 | - | - | - | - | 1.00 |
| `wopen_e0p2` | `id_asc` | off | 15 | 0 | 4 | robot_1 | 1.00 | 1.00 | 1.00 | 0.73 |
| `wopen_e0p2` | `id_asc` | on | 15 | 0 | 0 | - | - | - | - | 1.00 |
| `wopen_e0p2` | `id_desc` | off | 15 | 0 | 3 | robot_2 | 0.67 | 0.33 | 0.33 | 0.80 |
| `wopen_e0p2` | `id_desc` | on | 15 | 0 | 0 | - | - | - | - | 1.00 |
| `wopen_eopen` | `id_asc` | off | 15 | 0 | 6 | robot_1 | 1.00 | 1.00 | 1.00 | 0.60 |
| `wopen_eopen` | `id_asc` | on | 15 | 0 | 6 | robot_1 | 1.00 | 1.00 | 1.00 | 0.60 |
| `wopen_eopen` | `id_desc` | off | 15 | 0 | 0 | - | - | - | - | 1.00 |
| `wopen_eopen` | `id_desc` | on | 15 | 0 | 0 | - | - | - | - | 1.00 |

The symmetric variant's on/off pair is not an independent manipulation: with no
blocker the two cells render the same prompt SHA, so they are the reproducibility
pair described in §F.

### The obstacle channel is the one manipulation that moves ER-2

On the asymmetric variants, turning the textual obstacle block on drives the
named-yielder count to zero: 0/60 with the channel on against 13/60 off,
`P(strategy != yield)` 60/60 versus 47/60, Fisher exact p = 1.2e-4. This is the
first non-null modality effect the programme has recorded for the static-obstacle
channel.

> Superseded by Rev 6 §T on the "first" claim and on the implied gpt-4o
> inertness: gpt-4o also responds to the same text block, and in the intended
> direction — it selects the feasible yielder rather than abandoning `yield`.
> The effect was invisible to every earlier gpt-4o probe because those ran at
> `id_asc`. The ER-2 numbers in this section are unchanged, and Rev 3 §I item 3
> ("geometry is unused by ER-2") is not disturbed: Rev 6 §T replays gpt-4o
> artifacts only.

It is not geometric competence. ER-2 responds identically whether the blocker is
west or east (p = 0.65 under `id_asc`, p = 1.00 under `id_desc`, with the prompt
text held byte-identical and only the image differing), and **0 of the 180**
`justification` and `root_cause` strings contain "obstacle", "box", "blocker",
"crate" or "pallet" — including all 60 calls in which the obstacle block was
present and demonstrably drove the strategy. ER-2 is influenced by the channel
without ever mentioning it. It does not switch to the feasible yielder; it
abandons yielding.

### Hypotheses

- **`H_geom` is refuted for ER-2 too.** Among named yielders on the asymmetric
  variants, `P(correct)` = 6/13 = 0.46 — chance, the same value both gpt-4o
  models returned.
- **`H_slot` and `H_id` are underpowered, not answered.** On the named yielder,
  `P(robot_1)` is 6/6 under `id_asc` against 4/7 under `id_desc`, p = 0.192. The
  direction matches gpt-4o's slot preference; 13 informative calls settle
  nothing.
- **ER-2 does not echo presentation order in its own output.**
  `involved_robots[0]` matched the first-listed robot in 90/180 calls — exactly
  chance — against gpt-4o's 167/180.

| Model | Sampling | Obstacles | Verdict |
|---|---|---|---|
| gpt-4o | T=0.0 / T=0.6 | off and on | mixed |
| gpt-4o-mini | T=0.0 / T=0.6 | off and on | `H_slot` |
| ER-2 | seeded | off | mixed, on 13 informative calls |
| ER-2 | seeded | on | insufficient (reverse-dominant) |

`insufficient` is not a collection failure: in those four cells ER-2 named no
yielder at all, so no signature can be matched.

### Two corrections to Rev 1

1. **Latency instrumentation.** The probe's `PacedBackend` waited for its
   rate-limit slot *inside* the call that `invoke_backend` timed, so every record
   but a run's chronologically first carries wait plus response. Only the first
   call of a run is a real measurement. Rev 1's gpt-4o `median_latency_ms` column
   in `summary.csv` and in the probe report is therefore inflated (it ran at
   3 workers × 4.0 s); ER-2's single usable measurement is ≈ 4.9 s, consistent
   with the integration spec's 2.6–3.6 s at this probe's slightly larger payload.
   Fixed in `061c6a3`, which now times only the inner call; the committed records
   pre-date the fix. This corrects instrumentation only — no finding in Rev 1
   rests on the latency column.
2. **Arithmetic.** Rev 1's pooled-order table gives p = 1.4e-13 for gpt-4o-mini
   at T=0.6 (40/40 versus 2/40). The exact Fisher implementation used for this
   arm reproduces the other three rows exactly and returns **p ≈ 1.6e-20** for
   that one. The direction and the conclusion are unaffected.

---

## H. Live ER-2 Runs

Four closed-loop runs on the VM, tree `e6be85c` verified by `md5`. The
orchestrator config was regenerated from the pristine YAML for each run and the
**installed** copy was parsed and checked before every launch.

| Run | STAMP | Scenario | Order | Gate | Obstacles | ER-2 `yield_robot` (analysis #) | M3 grounded | First maneuver(s) | Arrivals | Analyses / dispatches | Latency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| G0 | `20260925_021549` | `head_on_deadlock` | `id_asc` | `off` | OFF | `robot_1` (#1) | verbatim | `yield` COMPLETED 143.0 s | 2/2 | 3 / 1 | 3.4–3.7 s |
| G1 | `20260925_023122` | `w0p2_eopen` | `id_asc` | `swap` | ON −1.85 | `robot_1` (#3) | `robot_1` → `robot_2` | `reverse` COMPLETED 34.2 s → `yield` COMPLETED 147.7 s | 2/2 | 8 / 2 | 2.6–4.4 s |
| G2 | `20260925_024628` | `w0p2_eopen` | `id_desc` | `off` | ON −1.85 | `robot_2` (#3) | verbatim (feasible) | `reverse` COMPLETED 35.0 s → `yield` COMPLETED 148.6 s | 2/2 | 9 / 2 | 2.8–4.2 s |
| G3 | `20260925_030129` | `wopen_e0p2` | `id_desc` | `off` | ON +1.85 | `robot_1` (#2) | verbatim (feasible) | `reverse` COMPLETED 35.8 s → `yield` COMPLETED 143.9 s | 2/2 | 5 / 2 | 3.0–6.6 s |

G1's swap, the only gate intervention in the batch:

```text
[orchestrator_node]: yield re-grounded request=3785a224fbef4052bd6c42566305cb56 from=robot_1 to=robot_2 reason=yield re-grounded: robot_1 has 0.70 m retreat room < 1.08 m required; robot_2 feasible
```

The opening `reverse` on every asymmetric scene, and the `yield` that follows it
only after the failure-context loop re-analyses:

```text
[orchestrator_node]: dispatch request=b492970d345843658d3eba6382e8b962 command=b492970d345843658d3eba6382e8b962-reverse robot=robot_1
[orchestrator_node]: request=3785a224fbef4052bd6c42566305cb56 failure_context attached command=b492970d345843658d3eba6382e8b962-reverse strategy=reverse executed=reverse outcome=completed
```

### Conformance

All 25 decision artifacts across the four runs carry `attempts=1` and
`parse_status=valid`, and **none** returned `decision=None`. No HTTP 429 was
observed. The ground-truth stream records `robot_static_contacts` 0 in every
frame of all four runs (3 001 frames each). Component errors stayed within the
known-benign set, and every post-resolution re-analysis returned
`congestion_detected=false`.

> Superseded by Rev 7 §AC for the contact clause: a zero `robot_static_contacts`
> (or `robot_robot_contacts`) count records what the detector reported, not that
> no contact occurred. The conformance conclusions on attempts, parse status and
> component errors are unaffected.

### G3 caveat

G3's yield was decided on a frame with the robots **1.08 m apart and both
MOVING**, not the 0.35–0.38 m STOPPED standoff that G1 and G2 were decided on. It
is therefore a weaker instance of the same cell and should not be pooled with
them without noting the difference.

---

## I. Adjudication

1. **ER-2 is a working drop-in Arm.** It matches gpt-4o on the symmetric
   baseline (G0 versus E0: both named `yield_robot=robot_1`, 143 s against
   148 s, 2/2 arrivals) and on the gate cell (G1 versus L1: both named the
   physically blocked `robot_1`, both were swapped to `robot_2`, both 2/2).
2. **Its distinctive behaviour is an opening `reverse` on every asymmetric
   scene** — 3/3 live, 155/180 offline. The `reverse` completes in roughly 35 s
   without resolving the standoff, and the failure-context loop then steers ER-2
   to `yield`. Each episode therefore costs one extra analysis and about 35 s
   against gpt-4o. Offline with the obstacle channel on ER-2 never reached
   `yield` at all (0/60); live it does, but only as decision #2 or #3 by way of
   failure context. This is the loop working as designed. It also means **ER-2's
   first decision is not comparable to gpt-4o's first decision** in the
   pre-registration's "first answer" metrics.
   *Superseded in part by Rev 4 §L item 5: the opening `reverse` is 5/6 live,
   not 3/3 — D1 opened on a pair stall and answered `yield` directly, so it is
   a strong habit, not an invariant. The comparability conclusion stands.*
   *Further qualified by Rev 6 §U: the opening strategy is trigger-confounded
   and must be stated by trigger. In the ER-2 pilot `reverse` is 3/4 on
   solo-stall openings and 2/2 on pair stalls; all six gpt-4o Arm A runs opened
   on solo stalls, so the matched contrast is 3/4 against 0/6, not 5/6 against
   0/6. The comparability conclusion still stands.*
3. **Geometry is unused by ER-2 as well.** G1 named the physically blocked
   `robot_1`; no live or offline justification mentions the obstacle; offline
   `P(correct)` is at chance. The M3 gate, not the model, is what made G1
   succeed.
   *Qualified — not superseded — by Rev 7 §AC. The obstacle is still never
   mentioned, so the channel claim stands. What changes is the reason: in the
   forced-order batch ER-2 named `robot_1` in only 1/3 of west/`id_asc` runs
   where gpt-4o's §T control is 124/125, so ER-2 has no `robot_1` anchor at all.
   The statement now reads: ER-2's yielder choice is near chance and unanchored
   (n small), still with no obstacle mention. The first-slot/ID mechanism is
   model-specific.*
4. **Order sensitivity for ER-2 is not established.** The named yielder was the
   first-presented robot in G1 and G2 and the second in G3, at n = 1 per cell,
   with no temperature control and with G3's geometry differing (§H). The
   slot/ID question stays open for ER-2.
5. **The decisive ER-2 cell was not run** — west-blocked × `id_asc` × gate off.
   "ER-2 fails like gpt-4o without the gate" is inferred from G1's choice, not
   observed.
   *Superseded by Rev 4 §K and §L item 1: that cell was run at n = 3 (D1–D3).
   The failure is now observed (D2) but is not deterministic — D1 and D3 named
   the feasible `robot_2` on the same seed and scene.*
6. **All four runs reached 2/2 arrivals**, three of them only because the gate
   fired (G1) or because the model happened to name the feasible robot (G2, G3).

---

## J. Next Steps

1. Run the decisive ER-2 cell (west-blocked, `id_asc`, gate `off`, n ≥ 3), and
   the same cell for gpt-4o with obstacles OFF (Rev 2 §D item 2), to complete the
   live 2×2 per model.
2. Pre-registration: keep ER-2 as the **secondary** arm (cost, latency,
   conformance) per the handoff; document the two structural confounds — no
   sampling control and hidden thinking — and the opening-`reverse` habit as a
   model characteristic; define the primary metric as **episode outcome, not
   first answer**.
3. Decide on the symmetric-`reverse` dispatch (B1), now exercised on every ER-2
   asymmetric episode: keep it, as the handoff recommends, for RQ5 evidence, or
   fix it before Arm B.
4. Re-run the gpt-4o offline latency column with the fixed pacer if latency is
   reported anywhere.
5. Adopt Rev 2 §D item 1 (gate `swap` plus random presentation order) for both
   arms.

---

## Rev 3 Provenance

Commits after `82098f8`: `c7a08e7`, `590ac23`, `e6be85c`, `8df0e92`, `908d641`,
`58dfa43`, `061c6a3`, plus this docs commit.

Run ids: `20260925_021549`, `20260925_023122`, `20260925_024628`,
`20260925_030129`.

The VM config was restored byte-exact (`md5`
`3ed3795f174c3df079e050e9b4e49572`), the container was restarted, and the GPU was
idle at 03:17 UTC. Artifacts remain git-ignored under `data/logs/vm_runs/`.

---

## K. The Decisive Cells: ER-2 Without the Gate, gpt-4o Without the Channel

Five runs, all on `head_on_asymmetric_w0p2_eopen_o0` with
`grounding_yield_feasibility: "off"`, on tree `e6be85c`. The **installed**
orchestrator YAML was parsed and asserted before each launch.

| Run | STAMP | Backend | Order | Obstacles | Opening strategy | First `yield_robot` (analysis #) | First yield status / duration | Min dist to box face (−1.70) | Arrivals | Analyses / dispatches | Later decisions |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 | `20260925_035042` | ER-2 | `id_asc` | ON −1.85 | `yield` (no `reverse`; first trigger was a pair stall) | `robot_2` (#1) | COMPLETED 146.1 s | never approached | 2/2 | 7 / 2 | 6 × none |
| D2 | `20260925_040539` | ER-2 | `id_asc` | ON −1.85 | `reverse` COMPLETED 36.1 s | `robot_1` (#3) | FAILED 245.9 s | 0.1020 m | 2/2 (loop cleared it later) | 7 / 6 | `reverse`(`robot_1`) FAILED 195.1 s; 3 × none |
| D3 | `20260925_042022` | ER-2 | `id_asc` | ON −1.85 | `reverse` COMPLETED 35.3 s | `robot_2` (#3) | COMPLETED 171.0 s | never approached | 1/2 | 23 / 4 | 20 × none |
| O1 | `20260925_043512` | gpt-4o | `id_asc` | OFF | refusal (#1), then `yield` | `robot_1` (#2) | FAILED 250.1 s | 0.1020 m | 2/2 | 7 / 4 | `reverse`(`robot_1`) FAILED 195.1 s; 4 × none |
| O2 | `20260925_045004` | gpt-4o | `id_desc` (prompt led with `robot_2`) | OFF | `yield` | `robot_1` (#1) | FAILED 239.8 s | 0.1020 m | 0/2 | 15 / 4 | `reverse`(`robot_1`) FAILED 195.2 s; 2 refusals; 11 × none |

D3's 1/2 is **not** a yield failure: `robot_2` stuck at x = −1.662 on its own
goal run past the blocker — the same east/west blocker-on-goal-path property
recorded for L2 in Rev 2 §B.

> Metric note: see Rev 5 §O. The 0.1020 m figures here are `min|x − face|` and
> mean *arrested short of the face*; that statistic collapses to ~0 for any
> robot that transits the gap, so the Rev 5 pilot reports a signed extremum
> plus final `x` instead. The two columns are not comparable.

D1's first trigger, the reason it never opened with `reverse`:

```text
[orchestrator_node]: starting analysis request=458573a434ab44e193a96730741599af robots=['robot_1', 'robot_2'] reason=2 robot(s) stalled >= 12.0s order=id_asc distance_to_goal_m={'robot_2': 2.63, 'robot_1': 2.64}
[orchestrator_node]: dispatch request=458573a434ab44e193a96730741599af command=458573a434ab44e193a96730741599af-yield robot=robot_2
```

Conformance across the batch: ER-2 latency 2.8–4.9 s with
`unsupported_sampling` on every call, and 37/37 decisions at `attempts=1` /
`parse_status=valid`; gpt-4o latency 1.8–4.7 s. The rendered prompt order
matched the configured order in all five runs, and the obstacle block was
present in D1–D3 only. The ground-truth stream records `robot_static_contacts`
0 across all 15 005 frames. Zero errors in the `isaac`, `m1`, `m4` and `m5`
logs; Nav2 errors stayed within the known-benign set.

> Superseded by Rev 7 §AC for the contact clause only: the zero count is detector
> silence, not a no-contact result. Minimum pairwise distance is the trustworthy
> channel.

---

## L. Verdicts

1. **ER-2 without the gate reproduces the gpt-4o failure mechanism, but not
   deterministically.** D2 named the blocked `robot_1`, its yield FAILED, and
   the chassis was arrested at the identical 0.1020 m from the blocker face.
   The yielder tally over D1–D3 — same seed, same scene, no sampling control —
   is `robot_2` × 2 / `robot_1` × 1, so this cell is decision variance, not a
   deterministic failure. Across all six ER-2 asymmetric live runs (G1 `r1`,
   G2 `r2`, G3 `r1`, D1 `r2`, D2 `r1`, D3 `r2`) ER-2 named `robot_1` in 3/6.
   This closes Rev 3 §I item 5.
2. **gpt-4o with the obstacle channel OFF is ID-driven and
   channel-invariant.** O1 and O2 both named `robot_1` and both failed at
   0.1020 m — O2 despite `robot_2` being presented first. The live gpt-4o tally
   on the asymmetric variants is now `robot_1` in 9/11 regardless of order or
   channel (exceptions R1 and L3), and 5/6 under `id_desc` (R3, R4, L2, L4, O2
   against R1). This only **partly** addresses Rev 2 §D item 2, which asked for
   `id_asc`/`id_desc` × west/east at n ≥ 3 per cell: O1 and O2 give n = 1 per
   cell on the west variant, and the two east × OFF cells remain unrun.
   *"Channel-invariant" superseded by Rev 6 §T: it describes the channel-OFF
   arm only. Under `id_desc` on real frames, turning the obstacle text on moves
   P(`robot_1`) from 0.704 to 0.500 and P(feasible) from 0.556 to 0.962
   (p = 8.8e-4) — O1 and O2 measured the model with its one working geometric
   input removed. The ID-anchoring half of the item stands.*
3. **The offline probe does not predict live order sensitivity for gpt-4o.**
   Offline, on the synthetic plan-view stimulus, `P(robot_1 | id_desc)` = 0.25
   pooled; live it is 5/6. The live pipeline — a real M1 annotated frame with
   robot IDs drawn on it, and live detector distances — is ID-anchored where
   the probe was slot-anchored. The offline result stands as a statement about
   the text-only/synthetic stimulus, **not** about the deployed system, and
   every offline→live generalisation in this report family must be read that
   way. Mechanism unverified; candidates are the annotated frame's ID labels,
   the image's role in each model's attention, and the synthetic image lacking
   those cues.
   *Refined by Rev 6 §S and §T: the failure to predict is a property of the
   synthetic plan-view stimulus, not of offline replay as such. Replayed on the
   real live frames the offline arms reproduce the live pattern — under
   `id_desc` the choice tracks the blocker side rather than the slot — so
   offline replay on real artifacts is a valid instrument where the plan-view
   probe is not.*
4. **Neither model uses geometry.** D2 chose the blocked robot with the
   obstacle block present in the prompt; O1 and O2 chose it with no obstacle
   information at all, to the same outcome. The M3 gate (`swap`) remains the
   only mechanism that has made the blocked cell succeed (L1, G1).
   *Superseded for gpt-4o by Rev 6 §T: gpt-4o does use the obstacle text, but
   only under `id_desc`. The evidence here is not contradicted — O1 and O2 had
   the channel off, and D2 is ER-2, for which Rev 3 §I item 3 still stands. The
   gate conclusion is unchanged: under the production-default order the model's
   own choice ignores feasibility.*
5. **ER-2's opening `reverse` is 5/6 live, not 3/3.** D1 opened on a pair stall
   and went straight to `yield`; D2 and D3 opened on solo stalls and reversed.
   gpt-4o also opened on solo stalls in O1 and O2 and answered `yield`, so
   trigger shape correlates with the opening `reverse` without forcing it.
   *Further qualified by Rev 6 §U: stated by trigger, the ER-2 pilot gives
   `reverse` 3/4 on solo-stall openings against gpt-4o's 0/6, and 2/2 on pair
   stalls with no gpt-4o counterpart. The contrast survives the control at
   n = 4 against 6, and the pilot's one `yield` opening (E1) came on a solo
   stall where D1's came on a pair stall, so trigger type does not determine
   the opening strategy either.*
6. **Metric sensitivity is real and must be pre-registered away.** D2 reached
   2/2 arrivals after its failed yield because the loop cleared it later, while
   the gpt-4o equivalents (L4, `20260924_201328`, O2) reached 0/2. First-answer
   and episode-outcome metrics disagree on the same mechanism; the
   pre-registration must pick one as primary and report both.
7. **New failure class for gpt-4o: a safety refusal.** Three of the 22
   obstacles-OFF analyses (O1 #1; O2 #4 and #5) returned a refusal string that
   carries no JSON:

   ```json
   {"raw_text": "I'm sorry, I can't assist with that.",
    "diagnostics": {"attempts": 2, "error_type": "VLMOutputParseError",
                    "error_message": "VLM output contains no JSON object.",
                    "parse_status": "failed"}}
   ```

   None occurred across the 37 ER-2 decisions. This is distinct from the
   post-resolution parse failures in Rev 1 §6(b): those fired after the
   congestion had already cleared, whereas O1's refusal consumed the run's
   **first** analysis slot.

   > Superseded by Rev 5 §P on three counts: the census over all 101 live
   > gpt-4o calls finds 23 attempt-1 and 12 terminal refusals, not three; nine
   > of the 12 terminal ones are obstacle-**ON**, so the class is not confined
   > to the obstacles-OFF arm; and the post-resolution parse failures of Rev 1
   > §6(b) are the same refusal class, not a distinct one. The count here was
   > missed by a literal string match that does not cover the "but" phrasing
   > (`raw_text="I'm sorry, but I can't assist with that."`). O1's refusal
   > consuming the run's first analysis slot stands.

---

## M. Consolidated Live Tallies

All live runs on the asymmetric variants, 2026-09-19 → 2026-09-25. The 09-19
Runs A and B are cited **as recorded** in
`docs/reports/2026-09-18-head-on-family-validity.md`, not re-verified here.

| Model | Cell (variant × order × channel) | Gate | n | `robot_1` | `robot_2` | First yield FAILED | Runs |
|---|---|---|---|---|---|---|---|
| gpt-4o | `w0p2_eopen` × `id_asc` × OFF | pre-gate ×1, off ×1 | 2 | 2 | 0 | 2 | 09-19 Run A, O1 |
| gpt-4o | `w0p2_eopen` × `id_asc` × ON | pre-gate ×2, `swap` ×2 | 4 | 3 | 1 | 2 (+1 swapped) | 09-19 Run B, R2, L1, L3 |
| gpt-4o | `w0p2_eopen` × `id_desc` × OFF | off | 1 | 1 | 0 | 1 | O2 |
| gpt-4o | `w0p2_eopen` × `id_desc` × ON | pre-gate ×1, off ×1 | 2 | 1 | 1 | 1 | R1, L4 |
| gpt-4o | `wopen_e0p2` × `id_desc` × ON | pre-gate ×2, `swap` ×1 | 3 | 3 | 0 | 0 | R3, R4, L2 |
| **gpt-4o total** | | | **12** | **10** | **2** | **6 (+1 swapped)** | |
| ER-2 | `w0p2_eopen` × `id_asc` × ON | `swap` ×1, off ×3 | 4 | 2 | 2 | 1 (+1 swapped) | G1, D1, D2, D3 |
| ER-2 | `w0p2_eopen` × `id_desc` × ON | off | 1 | 0 | 1 | 0 | G2 |
| ER-2 | `wopen_e0p2` × `id_desc` × ON | off | 1 | 1 | 0 | 0 | G3 |
| **ER-2 total** | | | **6** | **3** | **3** | **1 (+1 swapped)** | |

Reading the table:

- `robot_1` / `robot_2` count the yielder **M2 named**, before any M3
  re-grounding.
- `(+1 swapped)` marks a run in which M2 named the blocked `robot_1` and the
  first dispatched yield nevertheless COMPLETED **only because the M3 `swap`
  gate re-grounded it** — L1 in the gpt-4o `id_asc` × ON cell, G1 in the ER-2
  `id_asc` × ON cell. Without the gate those cells read as failures.
- The gate column varies **within** cells 2, 4, 5 and 6, so those rows pool
  runs that differ on the variable that determines the outcome. They are a
  yielder-identity tally, not an outcome comparison.
- §L item 2's 9/11 excludes 09-19 Run A. Including it, as this table does,
  gives `robot_1` in 10/12 for gpt-4o.

---

## N. Next Steps

1. Adopt gate `swap` plus random presentation order for **both** arms (Rev 2
   §D item 1) — now justified for ER-2 as well, since D2 shows ER-2 fails the
   blocked cell without it.
2. Treat the offline probe as a stimulus study, not a predictor. If an offline
   harness is kept, it must use real M1 annotated frames from recorded runs
   (the `data/logs/m5_frames/` artifacts) instead of synthetic plan views.
3. Investigate the gpt-4o refusal class before Arm A collection — inspect the
   three raw responses, most likely a prompt or image safety trigger. A refusal
   costs a retry and an analysis slot.
4. Pre-register **episode outcome as primary** and first answer as secondary;
   D2 against L4 is the case that forces the choice.
5. Decide how to handle the east/west blocker-on-goal-path property of the
   scenario family (D3, L2) — it contaminates arrival counts.
6. Keep ER-2 as the secondary arm. Its opening `reverse` and its lack of
   sampling control are model characteristics to document, not defects to fix.

---

## Rev 4 Provenance

Run ids: `20260925_035042`, `20260925_040539`, `20260925_042022`,
`20260925_043512`, `20260925_045004`.

The VM config was restored byte-exact (`md5`
`3ed3795f174c3df079e050e9b4e49572`), the container was restarted, and the GPU
was idle at 05:05 UTC. Artifacts remain git-ignored under
`data/logs/vm_runs/`. No new code commits — this revision is documentation
only.

---

## O. Arm A Pilot With the Adopted Defaults

Six runs on the configuration adopted in Rev 4 §N item 1: gpt-4o at
`temperature=0.0`, obstacle channel **on**, `grounding_yield_feasibility:
"swap"`, `prompt_robot_order: random` with `prompt_robot_order_seed: null`, and
`keep_debug_frames: true`. The installed YAML was parsed and asserted before
every launch. Tree `e6be85c` on the VM; local branch
`fix/deadlock-collision-resolution` at `2ff8baf`. Summary:
`data/logs/vm_runs/ARM_A_PILOT_SUMMARY.txt`; artifacts under
`data/logs/vm_runs/20260925_{063520,065143,070637,072130,073621,075116}/`.

| Run | STAMP | Scenario | Drawn order (seed) | First `yield_robot` | Gate | First yield status / duration | Arrivals | First analysis → both arrived | Analyses / commands | Refusals (attempt-1) | Nav2 recoveries `r1`/`r2` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | `20260925_063520` | `w0p2_eopen` | `id_desc` (11692839038650319742) | `robot_1` | fired `r1`→`r2` | COMPLETED 147.4 s | 1/2 | — | 23 / 3 | 2 | 0 / 7 |
| P2 | `20260925_065143` | `w0p2_eopen` | `id_asc` (6655140194514512915) | `robot_1` | fired `r1`→`r2` | COMPLETED 144.7 s | 2/2 | 326.8 s | 8 / 1 | 0 | 0 / 1 |
| P3 | `20260925_070637` | `w0p2_eopen` | `id_asc` (12886736765469768478) | `robot_1` | fired `r1`→`r2` | COMPLETED 145.8 s | 2/2 | 328.5 s | 7 / 1 | 1 | 0 / 2 |
| P4 | `20260925_072130` | `wopen_e0p2` | `id_asc` (11377275926542616640) | `robot_1` | no-op (feasible) | COMPLETED 147.9 s | 2/2 | 321.6 s | 7 / 1 | 0 | 2 / 0 |
| P5 | `20260925_073621` | `wopen_e0p2` | `id_asc` (2010951348925484183) | `robot_1` | no-op (feasible) | COMPLETED 145.8 s | 2/2 | 281.2 s | 3 / 1 | 0 | 1 / 0 |
| P6 | `20260925_075116` | `wopen_e0p2` | `id_desc` (2727189488213636520) | `robot_2` | fired `r2`→`r1` | COMPLETED 142.2 s | 1/2 | — | 26 / 1 | 0 | 9 / 0 |

Notes on the table:

- The two episodes that did not reach 2/2 ended at the blocker, not at a failed
  maneuver. In P1, `robot_2` was wedged 0.064 m past the west face in the
  0.20 m gap on its own goal run; in P6, `robot_1` was arrested 0.004 m past
  the east face on its own goal run.
- Metric note: `min|x − face|` collapses to ~0 for any robot that transits the
  gap — P5 passes 0.005 m from the face plane and arrives, P6 stops 0.000 m
  from it and does not — so the pilot reports the **signed extremum in the
  travel direction plus final `x`**. These figures are not comparable to Rev 4
  §K's "0.1020 m short".
- The ground-truth stream is capped at 3001 rows / 300 sim-s per run by the
  logger, not by run length, so the P1 and P6 extrema are bounds rather than
  settled minima.
- Commands count **distinct dispatched** commands, comparable to Rev 4 §K.

### Findings

- **M2 named an infeasible yielder in 4/6 runs** (P1, P2, P3 west → `robot_1`;
  P6 east → `robot_2`), and the M3 gate re-grounded every one:

  ```text
  strategy=yield yield_robot=robot_1 type=deadlock congestion=True terminal=ok failure_reason=None
  gate=swap grounded_from=robot_1 regrounded=yield re-grounded: robot_1 has 0.70 m retreat room < 1.08 m required; robot_2 feasible
  ```

- **The dispatched first yield COMPLETED in 6/6 runs**, 142.2–147.9 s, mean
  145.6 s, tight across both variants and both yielder identities. Gate
  intervention rate 4/6; it was a no-op exactly when M2 named a feasible
  yielder (P4, P5) and never harmful. Without it, those four are the known
  pre-gate failure mode.
- **Episode outcome (both arrived) is 4/6**, 2/3 per variant. Both misses are
  the blocker-on-goal-path property of the scenario family (Rev 2 §D item 4,
  Rev 4 §N item 5), not coordination failures: in each the yield completed and
  the yielder arrived before the other robot stalled at the box. Read
  unqualified, 4/6 understates the coordination result.

  > Superseded by Rev 6 §V: this 4/6 is Nav2-reported, not position-verified.
  > The arrival line M5 emitted here trusted `bt_navigator`. All four gpt-4o
  > completed runs are within 0.09 m of goal by ground truth, so the figure is
  > expected to survive, but it must be re-scored offline from the scene log at
  > the 0.35 m tolerance before it is quoted as an outcome.

  > Confirmed by Rev 7 §X: the re-scoring is done and P1–P6 stays 4/6. This
  > figure is now position-verified and quotable. Separately superseded by
  > Rev 7 §AC on safety: these runs breach `safety.yaml` `min_distance_m: 0.45`
  > in 5–7% of ground-truth rows by design, which §O does not report.
- **First `yield_robot` was `robot_1` in 5/6**, the exception being P6
  (`id_desc`, east). This is the ID-anchored live behaviour of Rev 4 §L item 2,
  now observed under random order.
- **Resolution time** (first analysis → both arrived) 281.2–328.5 s, mean
  314.5 s, range 47 s.
- **Zero `reverse` openings for gpt-4o.** All six opened `yield` at episode 0
  on a solo-stall trigger, against ER-2's 5/6 `reverse` in Rev 4 §L item 5.
  This closes that item for gpt-4o under these defaults.
- **Order draws**: `id_asc` 4, `id_desc` 2. An independent `sha256(STAMP)`
  recomputation matched the recorded `robot_presentation_order` for every
  episode in all six runs. `EpisodeOrderTracker` closes an episode only when a
  robot in the tracked set arrives; on the east variant the tracked set was
  `{robot_1}` and `robot_2` arrived first, so P4 and P5 drew once for the whole
  run.
- **Parse**: 74 analyses — 64 valid at attempt 1, 7 recovered at attempt 2, 3
  terminal refusals (P1 ×2, P3 ×1). All three were post-resolution re-analyses
  in a later episode; none consumed a run's first analysis slot, unlike O1 in
  Rev 4 §K. 69/74 raw responses open with a literal `<think>` block echoing the
  prompt's reasoning checklist — the normal output shape here, present on valid
  responses too.
- **Frames**: `keep_debug_frames` wrote one PNG per analysis, joining 1:1 as
  `m5_frames/<request_id>.png` ↔ `decisions/<request_id>.json` ↔
  `prompt.user_sha256`, with zero orphans in either direction in all six runs.
  74 PNGs, 48 MB.

---

## P. gpt-4o Refusal Census

Commits `5a27fc3` and `26419e0`; report
`docs/reports/2026-09-25-gpt4o-refusals.md`.

Over every live gpt-4o decision of 2026-09-24/25 (n = 101): **23 attempt-1
refusals (22.8%) and 12 terminal (11.9%)** — not the three counted in Rev 4 §L
item 7. The undercount has two causes: the literal string match missed
`I'm sorry, **but** I can't assist with that.`, and only terminal failures were
scored. Nine of the 12 terminal refusals are obstacle-**ON**, so the class is
not tied to the obstacles-OFF arm. Every gpt-4o parse failure in the local
corpus is a safety refusal; there is no other failure mode in the data.

- One re-ask rescues about 48% of attempt-1 refusals; within a request the
  refusal persists with conditional probability 0.52.
- ER-2 refused 0/62 (p = 8.9e-6 against gpt-4o on attempt 1).
- **No prompt-side factor explains attempt-1 refusals**: obstacle channel
  p = 1.0; failure context 0.0030 raw → 0.094 after correction; solo vs pair
  stall is a null. Failure context does predict **non-recovery** (p = 0.012,
  n = 23).
- Instrumentation: `Reasoner` records `backend_id="openai"` on failures and
  `"gpt-4o"` on successes, which splits one model into two rows — group by run,
  not by that field.
- Offline replay of the exact refusing prompts plus controls — T = 0.0/0.6,
  re-ask arm, ablations dropping failure context and the `<think>` block,
  wording groups, `gpt-4o-mini` — with grey and synthetic images produced
  **0/240 refusals** ($1.21). The prompt text is not the trigger.

---

## Q. Real-Frame Replay

Commits `f70c444`, `f7bb200`, `f8d48bb`, `1e8551c`; report
`docs/reports/2026-09-25-frame-replay.md`.

**Reconstruction integrity.** Re-rendering each artifact through
`build_reasoner_request` from its stored `scene`, the run's
`orchestrator.yaml.used` and the real PNG reproduced the stored user-prompt
SHA-256 in **74/74** artifacts, the 19 carrying a failure-context block
included — M5 persists `failure_context` structurally.

**Arm R (36 artifacts × n = 3 = 108 calls, real frames).** Attempt-1 refusals
27/108 = 25.0%, against 8/36 = 22.2% live on the same artifacts (p = 0.83) and
0/240 with synthetic images (p = 1.2e-13, cross-experiment). Terminal 11.1%
(census 11.9%); the re-ask recovered 15/27 = 55.6%. Refusals are
**stimulus-locked**: artifacts that refused live refuse 13/24 on replay against
14/84 for live-valid artifacts (p = 8.0e-4).

**Verdict: the annotated camera frame is the refusal trigger.**

**Arm O (order sensitivity on real stimuli)** ran only at n = 1 per cell:
`id_asc` → `robot_1` 6/6, `id_desc` → `robot_1` 3/5 (p = 0.18). The direction
matches the ID-anchored live reading of Rev 4 §L item 2, but this is not
evidence. **Arm M (mitigations)** and the paired grey-image sub-arm did not
run.

**Blocker.** The OpenAI account exhausted its credits mid-run (HTTP 429
`insufficient_quota`); $0.85 of the ≈$3 budget spent over 151 calls. Resume
with `python scripts/replay_live_decisions.py --arm R|grey|O|M|analyze` —
completed cells are keyed and skipped.

Recommendation, as stated in that report: **keep the re-ask** (without it the
terminal rate goes from 11% to 25%), test `max_attempts` 3–4 in Arm M, budget
≈1.25 calls and ≈0.11 lost analysis slots per gpt-4o analysis, and prefer ER-2
(0/62) wherever a lost analysis slot is costly.

---

## R. Next Steps

1. Add OpenAI credits and resume the replay: `--arm O` at n = 8 to settle
   real-stimulus order sensitivity, `--arm M` for the retry policy, `--arm
   grey` for the image pairing.
2. Investigate **what in the frame** triggers the refusal before Arm A
   collection. Candidates: ArUco marker patterns, annotation text, image size.
   The cheap tests are the grey sub-arm and a downscaled-frame arm via
   `frame_downscale_width`.
3. Decide the scenario question on the blocker-on-goal-path property — 2/6
   pilot episodes were lost to it. Either move the blocker off the goal path or
   score the non-yielder's arrival separately.
4. Pre-register: gate `swap` plus random presentation order, episode outcome as
   primary, `max_attempts` per Arm M, and frames kept for every run
   (`keep_debug_frames: true`, ≈0.65 MB per analysis).
5. Run an ER-2 arm pilot on the same six-run design for the cost, latency and
   conformance comparison. The Gemini credit balance is unaffected.
6. Wire `--duration-sec` and lift the ground-truth logger cap (3001 rows)
   before running longer episodes.

---

## Rev 5 Provenance

Commits after `2ff8baf`: `5a27fc3`, `26419e0`, `f70c444`, `f7bb200`,
`f8d48bb`, `1e8551c`, plus this documentation commit.

Run ids: `20260925_063520`, `20260925_065143`, `20260925_070637`,
`20260925_072130`, `20260925_073621`, `20260925_075116`.

The VM config was restored byte-exact (`md5`
`3ed3795f174c3df079e050e9b4e49572`, `keep_debug_frames` back to `false`), the
container was restarted, and the GPU was idle. Artifacts remain git-ignored
under `data/logs/vm_runs/`. Local test suite: 898 passed, 55 failed, 3 errors —
the same environmental set as previous revisions.

---

## S. Real-Frame Replay Completed

Rev 2 of `docs/reports/2026-09-25-frame-replay.md` (commits `3e31079`,
`add1378`). The Rev 5 §Q blocker — exhausted OpenAI credits — is cleared and
all four planned arms ran.

- **The frame is the trigger, settled within one design.** Pairing real frames
  against grey PNGs of identical dimensions on byte-identical prompts: 22/60
  refusals with the real frame against 0/120 with grey, Fisher p = 1.5e-12. The
  earlier 0/240 cross-experiment comparison of Rev 5 §Q is no longer
  load-bearing.
- **Arm R, complete** (74 artifacts × 3 replicates): attempt-1 refusal 18.9%,
  terminal 9.9%, the re-ask recovers 47.6%. The refusal is stimulus-locked —
  artifacts that were refused live refuse again at 60% against 12.5% for
  live-valid artifacts, p = 5.4e-8.
- **Arm O, order sensitivity on real stimuli** (6 first-yield artifacts × order
  × n = 8, obstacle text on, real frame): `P(robot_1)` is 47/48 under `id_asc`
  against 22/47 under `id_desc`, p = 5.0e-9. Under `id_desc` the choice tracks
  the blocker side — west → `robot_1` 2/23, east → `robot_1` 20/24.
- **Arm M, retry policy**, conditional on a refused first attempt:

  | policy | terminal refusal | n |
  |---|---|---|
  | shipped re-ask (`max_attempts` 2) | 57.1% | 28 |
  | original-prompt retry | 85.7% | 28 |
  | `max_attempts` 4 | 26.9% | 26 |

  `max_attempts=4` against the shipped policy is p = 0.031, so
  **`vlm.openai.reasoner.max_attempts: 4` was adopted** (commit `3c06e08`;
  `gemini` and `llama` stay at 2, with a new config test pinning both).

Replay spend for Rev 2: $3.97.

---

## T. The Obstacle Text Block Carries the Side Signal

Rev 3 of the replay report (commits `4942fae`, `21e5eb9`, `1162933`). Arm S is
288 attempt-1 runs over the same six genuine standoff artifacts — 3 west-blocked,
3 east-blocked, none carrying failure context — in eight cells: presentation
order × obstacle text × image, n = 6 per artifact per cell. All 288 are gpt-4o
replays; no ER-2 artifact is involved.

`P(feasible)` is the share of yields naming the robot whose retreat is
unobstructed. Any side-blind rule — always `robot_1`, always first-listed, or a
coin flip — scores 0.5 pooled, because the feasible robot is first-listed on
west scenes and second-listed on east scenes.

| order | obstacle text | image | n | P(`robot_1`) | P(feasible) |
|---|---|---|---|---|---|
| `id_asc` | on | real | 32 | 1.000 | 0.562 |
| `id_asc` | on | grey | 36 | 0.972 | 0.472 |
| `id_asc` | off | real | 21 | 1.000 | 0.429 |
| `id_asc` | off | grey | 36 | 1.000 | 0.500 |
| `id_desc` | on | real | 26 | 0.500 | **0.962** |
| `id_desc` | on | grey | 36 | 0.694 | 0.694 |
| `id_desc` | off | real | 27 | 0.704 | 0.556 |
| `id_desc` | off | grey | 36 | 0.583 | 0.583 |

The three contrasts, all under `id_desc`:

| contrast | P(feasible) | Fisher (two-sided) | reading |
|---|---|---|---|
| (a) real frame, text on → off | 0.962 → 0.556 | p = 8.8e-4 | strong, within-artifact |
| (b) text on, image real → grey | 0.962 → 0.694 | p = 0.0095 | moderate |
| (c) states only (text off, grey) | 0.583, side p = 0.50 | — | null |

In (a) the west-versus-east split collapses from p = 2.7e-6 to p = 0.68. In (b)
the two arms are structurally asymmetric — the grey image never refuses — so the
attenuation is a bound, not a clean effect size. The `id_asc` control is
unbroken in every channel condition: `robot_1` is named 124/125 times. Mentions
of the obstacle in the model's own `<think>` block: **0 of 288**. The replay
also reproduces the refusal trigger as a by-product, 38/144 real against 0/144
grey.

### Interpretation

This supersedes "geometry is unused" for gpt-4o. The obstacle **text** block is
read and acted on, the real frame amplifies it, and the robot states alone carry
nothing — but the effect is visible only when the two positional priors conflict.
A consistent model is

```text
choice ≈ argmax(first-slot prior + robot_1 prior + feasibility evidence)
```

Under `id_asc` the two priors agree and swamp the evidence: 0/48 deviations
toward the feasible `robot_2` on the west scenes. Under `id_desc` they cancel
and feasibility decides, at roughly 96%. The model never verbalises the
obstacle in either regime.

Caveats: the side → robot mapping rests on 3 artifacts per side; all eight cells
share the same six stimuli; the primary rows are attempt-1 only, because
`max_attempts` is now 4.

> Superseded in part by Rev 7 §AA. The **direction** of contrast (a) replicates
> on batch-2 standoffs — pooled `id_desc` text on 0.714 versus off 0.375,
> p = 1.1e-3, 7/9 scenes moving in direction and none reversing — but the
> **magnitude** above does not: batch-1 west is 13/14 feasible against batch-2
> west 6/17 (p = 0.0023) on prompts differing only in pose decimals, and the gap
> survives grey images, so it is not the frame. Contrast (b), "the real frame
> amplifies it", is now neither confirmed nor refuted pooled (p = 0.17). The
> states-only null (c) replicates (p = 0.37). Revised statement: the obstacle
> text is read when the positional priors cancel; the effect size is
> scene-dependent, 0–1 across scenes. The `id_asc` control and the 0/288 trace
> silence are unaffected.

### Consequences

1. The 2026-09-19 obstacle-channel A/B read null because it was run under
   `id_asc`, where the channel cannot show. That is a design fact, not a model
   fact.
2. `prompt_robot_order: random` makes the channel observable in about half the
   episodes. Any analysis of channel effects must condition on the drawn order.
3. The M3 gate remains necessary. Under the production-default order the
   model's own choice ignores feasibility.

### Arm D - frame resolution is not the trigger

Downscaled frames (640 px wide) against full-size, on 10 live-refused artifacts,
n = 3: attempt-1 refusals 15/30 against 23/30 (p = 0.060), terminal 5 against 17
(p = 0.0028). Downscaling makes refusals **worse**, so `frame_downscale_width`
is ruled out as a mitigation.

Replay spend for Rev 3: $2.66; cumulative $6.63.

---

## U. ER-2 Pilot on the Adopted Defaults

Six runs mirroring the gpt-4o Arm A pilot of Rev 5 §O cell for cell: gate
`swap`, `prompt_robot_order: random`, obstacle channel on, `keep_debug_frames:
true`. Tree `e6be85c` on the VM, local branch at `2ade04d`; the installed YAML
was parsed and asserted before every launch. Summary
`data/logs/vm_runs/ER2_PILOT_SUMMARY.txt`; artifacts under
`data/logs/vm_runs/20260925_{124609,130115,132335,133841,135334,140824}/`.

| Run | STAMP | Scenario | Order | Opening (trigger) | First `yield_robot` (#) | Gate | First yield | Arrivals log / physical | First analysis → both | Analyses / commands | Latency mean | Recoveries `r1`/`r2` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | `20260925_124609` | `w0p2_eopen` | `id_asc` | `yield` (solo) | `robot_2` (#1) | no-op | COMPLETED 146.3 s | 2/2 / **1/2** | 308.9 s * | 25 / 1 | 3341 ms | 0 / 1 |
| E2 | `20260925_130115` | `w0p2_eopen` | `id_asc` | `reverse` (pair) | `robot_1` (#3) | fired `r1`→`r2` | COMPLETED 147.6 s | 2/2 / 2/2 | 404.3 s | 9 / 2 | 3486 ms | 0 / 2 |
| E3 | `20260925_132335` | `w0p2_eopen` | `id_desc` | `reverse` (solo) | `robot_1` (#3) | fired `r1`→`r2` | COMPLETED 149.6 s | 1/2 / 1/2 | — | 25 / 2 | 3339 ms | 0 / 7 |
| E4 | `20260925_133841` | `wopen_e0p2` | `id_asc` | `reverse` (solo) | `robot_1` (#3) | no-op | COMPLETED 141.5 s | 1/2 / 1/2 | — | 25 / 2 | 3754 ms | 7 / 0 |
| E5 | `20260925_135334` | `wopen_e0p2` | `id_asc` | `reverse` (solo) | `robot_1` (#3) | no-op | COMPLETED 145.5 s | 1/2 / 1/2 | — | 25 / 2 | 3575 ms | 7 / 0 |
| E6 | `20260925_140824` | `wopen_e0p2` | `id_asc` | `reverse` (pair) | `robot_1` (#3) | no-op | COMPLETED 149.1 s | 2/2 / 2/2 | 376.8 s | 6 / 2 | 3977 ms | 1 / 0 |

`*` E1's second arrival is the Nav2 false success of §V, so its resolution time
is not a real one. Parse failures are 0 on all 115 calls. Blocker approach:
E1 `robot_2` cleared the west face and then stalled 0.59 m from its goal,
0.257 m off the corridor axis; E3 `robot_2` was arrested 0.038 m short of the
west face; E4 and E5 `robot_1` 0.038 m short of the east face; E2 and E6 were
full transits.

| Measure | ER-2 | gpt-4o (Rev 5 §O) |
|---|---|---|
| Episode outcome | 3/6 by log, 2/6 physically | 4/6 by log |
| First yield COMPLETED | 6/6, mean 146.6 s | 6/6, mean 145.6 s |
| Gate intervention | 2/6 | 4/6 |
| Mean resolution time | 363.3 s | 314.5 s |
| Analyses per episode | 19.2 | 12.3 |
| Refusal / parse failure | 0 / 115 | 10 / 74 |
| Backend latency, mean | 3526 ms | 2751 ms |
| Tokens per call, mean | 2413 (+242 thought) | 1916 |

Notes and caveats:

- ER-2 named `robot_1` in 5/6 regardless of which side the blocker was on. It
  is right on the east variant by coincidence of the anchor matching
  feasibility, not by reading the obstacle; Rev 3 §I item 3 stands. E3 is the
  one `id_desc` draw and ER-2 still named `robot_1`, the second-presented robot
  — ID over slot, at n = 1.
- The opening `reverse` is trigger-confounded. The matched solo-stall cell is
  3/4 against gpt-4o's 0/6; the pair-stall cell is 2/2 with no gpt-4o
  counterpart. Rev 3 §I item 2 and Rev 4 §L item 5 are marked accordingly.
- Sampling is uncontrolled on all 115 calls: the Interactions API has no
  sampling fields, so `{temperature 0.6, top_p 0.95, top_k 20.0,
  presence_penalty 0.0}` was dropped and recorded as `unsupported_sampling`.
  This structural confound must travel with every number in this section.
- E3's first attempt (`20260925_131122`) aborted with 0 analyses because it
  launched before the previous run's exit trap had finished cleaning up. The
  harness lesson is to wait for the launcher's `logs saved to` line rather than
  polling `pgrep`.

> Rev 7 §X confirms the physical column: re-scored against M1 and ground truth,
> E1–E6 is 3/6 by log → **2/6** position-verified, the single flip in the whole
> 31-run corpus being E1 `robot_2`. Rev 7 §AC narrows the first bullet's "Rev 3
> §I item 3 stands": ER-2 still never reads the obstacle, but it has no
> `robot_1` anchor either, so "named `robot_1` in 5/6" is not an ID anchor at
> this n. Rev 7 §AC also supersedes any zero-contact reading of these runs.

---

## V. Apparatus: Arrival Is Now Position-Verified

E1 exposed a Nav2 false success. `bt_navigator` reported the goal reached for
`robot_2` while M1 placed it 0.59 m away, and M5 logged the arrival 5 ms later:

```text
[bt_navigator-5] [INFO] [1790340781.524683836] [robot_2.bt_navigator]: Goal succeeded
[orchestrator_node-1] [INFO] [1790340781.529723700] [orchestrator_node]: robot robot_2 arrived at base goal (-2.5, 0.0)
```

M5 then reported `distance_to_goal_m={'robot_2': 0.59}` on all 21 subsequent
analyses while the robot never moved again. This is one false success in nine
ER-2 arrival events; every other arrival in the pilot, and all four completed
gpt-4o pilot runs, are within 0.09 m of goal, so the criterion is normally
sound.

Fix, in commits `4f39899`, `c7c189e` and `069e1f2`:

- `swarm_orchestrator/arrival.py` with `classify_arrival` and `ArrivalGate`,
  cross-checking M4's base-goal report against the M1 position estimate.
- Config keys `arrival_position_check: true`,
  `arrival_position_tolerance_m: 0.35` — above M1's ≈0.1 m bias and at or below
  `arrived_radius_m` (0.5) — and `arrival_estimate_max_age_sec: 2.0`.
- The accepted arrival line gains `distance_m=… check=…`; a new WARNING
  `arrival rejected robot=…` and INFO `arrival accepted late robot=…` cover the
  other verdicts. Episodes — and therefore the random-order draws — close only
  on accepted arrivals.
- +24 tests; local suite 942 passed, 55 failed, 3 errors (the same
  environmental set as previous revisions).

Pre-registration consequence: episode outcome must be position-verified in both
arms. Every run before this fix is Nav2-reported and must be re-scored offline
from the scene log at the 0.35 m tolerance — Rev 5 §O's 4/6 and the Rev 4 and
Rev 5 arrival counts included. Offline scorers must match **both** acceptance
lines, the plain one and the late one.

> Discharged by Rev 7 §X: all 31 runs and 55 arrival events are re-scored and
> exactly one flips (this one). Rev 7 §Y confirms "the criterion is normally
> sound" live — 17/17 batch-2 plus 11/11 batch-3 true arrivals accepted at
> 0.03–0.08 m, zero rejections and zero late acceptances. Rev 7 §AC supersedes
> any zero-contact reading of this section's runs.

---

## W. Next Steps

1. Re-score every 2026-09-24/25 run's arrivals from the scene logs at 0.35 m
   and publish corrected outcome tables.
   *Done — superseded by Rev 7 §X: 31 runs / 55 arrival events re-scored with
   `scripts/rescore_arrivals.py`, corrected tables published, one flip (ER-2
   E1 `robot_2`).*
2. Ship the arrival check and `max_attempts: 4` to the VM — rebuilding
   `swarm_orchestrator` — before any further runs.
   *Done — superseded by Rev 7 §Y and §Z: both shipped and exercised live in
   batches 2 and 3. `max_attempts=4` rescued 13/21 attempt-1 refusals in batch 2,
   and the arrival check accepted 28/28 true arrivals with zero rejections.*
3. Pre-register: gate `swap` plus random order, analysis conditioned on the
   drawn order (channel effects are visible only under `id_desc`), episode
   outcome as the position-verified arrival, first answer secondary.
4. Replicate the side-carrier result on more standoff scenes. Record additional
   pilot runs with frames kept; 3 artifacts per side is the floor, not a
   target.
5. Chase the refusal trigger inside the frame: un-annotated frames (which
   requires saving the raw camera frame alongside the annotated one) and
   marker-masked frames. Downscaling is ruled out.
   *Partly superseded by Rev 7 §Y, §AA and §AB. `keep_raw_frames` ships
   (`fa98ed6`), but the raw/annotated pairs are −1.36…+1.33 s apart (|skew| mean
   0.40 s, 24/56 within 0.2 s), so they are not same-instant and the comparison
   must be gated on the low-skew subset. The replay arm that would run it
   (Arm F, 336 cells) never executed — OpenAI credit ran out. A mitigation
   shipped ahead of the diagnosis: `image_fallback_after_attempts: 2` (§AB),
   itself unvalidated because Arm X aborted before its first call.*
6. Decide the scenario question on the blocker-on-goal-path property — 2/6 plus
   3/6 episodes lost to it across the two pilots.
   *Partly superseded by Rev 8 §AD. The `_gshort` variants settle the
   blocker-on-goal-path half of the question — 0/6 losses to it, no passer
   within 0.36 m of a box face — but symmetric ±1.5 goals put the yielder's
   park point beyond the passer's goal and cost 2/6 episodes to a new
   park-beyond-goal hold. The scenario question is therefore still open; the
   candidate is `_bshort` (§AD, §AF item 1).*
7. Keep ER-2 as the secondary arm, noting its zero-refusal robustness and its
   trigger-dependent `reverse` opening.

---

## Rev 6 Provenance

Commits after `2ade04d`: `3c06e08`, `3e31079`, `add1378`, `4f39899`, `c7c189e`,
`069e1f2`, `4942fae`, `21e5eb9`, `1162933`, plus this documentation commit.

ER-2 run ids: `20260925_124609`, `20260925_130115`, `20260925_132335`,
`20260925_133841`, `20260925_135334`, `20260925_140824`.

The VM config was restored byte-exact (`md5`
`3ed3795f174c3df079e050e9b4e49572`), the container was restarted, and the GPU
was idle. Artifacts remain git-ignored under `data/logs/vm_runs/`. Replay spend
today: $6.63. Local test suite: 942 passed, 55 failed, 3 errors.

---

## X. Arrival Re-Scoring: Position-Verified Outcomes for Every Run

Commits `0e377c7`, `261e8ab`, `8953126`; report
`docs/reports/2026-09-25-arrival-rescoring.md`; row-level output
`data/logs/vm_runs/ARRIVALS_RESCORED.csv`.

31 runs and 55 M5-reported arrival events were re-scored against M1 and against
ground truth. The scene log is selected by the M5 `session_id`, never by glob —
stray scene files from earlier sessions share the directory, so a glob picks the
wrong log. M1 against ground truth carries a bias of mean −6 mm over the corpus,
range −11…+4 mm, which is well inside the 0.35 m tolerance.

**Exactly one event flips**: ER-2 E1 `robot_2`, at M1 0.591 m and ground truth
0.598 m — the Nav2 false success of Rev 6 §V. Every other arrival survives.

Corrected batch outcomes:

| Batch | Runs | Outcome (position-verified) | Change |
|---|---|---|---|
| Arm A pilot 1 | P1–P6 | 4/6 | unchanged |
| ER-2 pilot | E1–E6 | 2/6 | 3/6 → 2/6 |
| Rev 1 live | R1–R4 | 3/4 | unchanged |
| Gate validation | L1–L5 | 3/5 | unchanged |
| ER-2 Rev 3 | G0–G3 | 4/4 | unchanged |
| ER-2 decisive cell | D1–D3 | 2/3 | unchanged |
| Obstacles-OFF | O1–O2 | 1/2 | unchanged |
| Closed-loop replication | E0 | 1/1 | unchanged |

P1's five duplicate arrival lines are explained: M4 re-dispatches the base
mission on each strategy change, so one physical arrival is reported once per
dispatch. This is a logging artifact, not five arrivals.

Tool: `scripts/rescore_arrivals.py`, 12 tests. It matches both acceptance lines,
the plain one and the late one, as Rev 6 §V required.

---

## Y. Apparatus Additions

**`reasoner_config_effective` in every artifact** (commit `b518ed4`): backend,
model, temperature, `top_p`/`top_k`, `max_attempts`, seed, `thinking_level` and
`unsupported_sampling` are now recorded on every decision. This is the **first
live confirmation that gpt-4o ran at `temperature=0.0` with `max_attempts=4`** —
no prior artifact proved it, which is the gap the ER-2 pilot logged as "sampling
uncontrolled" in Rev 6 §U.

**`keep_raw_frames`** (commit `fa98ed6`) dumps `<request_id>_raw.png` beside the
annotated frame and logs the skew. The pairs are **not same-instant**: they are
−1.36…+1.33 s apart, with |skew| mean 0.40 s and only 24/56 within 0.2 s. An
annotated-versus-raw refusal comparison must therefore be gated on the low-skew
subset, or it confounds annotation with scene change.

**The arrival position check is validated live**: 17/17 true arrivals in batch 2
and 11/11 in batch 3 (ER-2) were accepted at 0.03–0.08 m, with zero rejections
and zero late acceptances.

---

## Z. Pilot Batch 2 — gpt-4o on the Adopted Defaults

Six runs on tree `fa98ed6`: gpt-4o at `temperature=0.0`, obstacle channel on,
gate `swap`, `prompt_robot_order: random`, arrival position check on,
`max_attempts: 4`. Summary `data/logs/vm_runs/ARM_A_PILOT2_SUMMARY.txt`;
artifacts under
`data/logs/vm_runs/20260925_{155433,160951,162451,163949,165442,170938}/` —
the first three west-blocked, the last three east.

| Run | Scen. | Drawn order | First `yield_robot` | Gate | First yield | Arrivals (dist) | Outcome | First analysis → both | Analyses / cmds | Refusals a-1 / terminal | Attempts | Recoveries `r1`/`r2` | Blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | W | `id_desc` | `robot_1` | fired `r1`→`r2` | COMPLETED 154.1 s | 2/2 (0.08/0.05) | ✓ | 354.1 s | 6 / 2 | 2 / 0 | 1×4, 2×1, 3×1 | 0 / 2 | transit |
| Q2 | W | `id_desc` | `robot_1` | fired | COMPLETED 151.1 s | 2/2 | ✓ | 325.3 s | 7 / 1 | 2 / 2 | 1×5, 4×2 | 0 / 1 | transit |
| Q3 | W | `id_desc` | `robot_1` | fired | COMPLETED 154.8 s | 2/2 | ✓ | 471.1 s | 8 / 2 | 2 / 1 | 1×6, 2×1, 4×1 | 0 / 4 | transit |
| Q4 | E | `id_asc` | `robot_1` | no-op | COMPLETED 153.8 s | 2/2 (0.03/0.07) | ✓ | 349.0 s | 4 / 2 | 2 / 0 | 1×2, 2×1, 3×1 | 1 / 0 | transit |
| Q5 | E | `id_asc` | `robot_1` | no-op | COMPLETED 152.2 s | 2/2 | ✓ | 323.1 s | 4 / 1 | 2 / 2 | 1×2, 4×2 | 1 / 0 | transit |
| Q6 | E | `id_asc` | `robot_1` | no-op | COMPLETED 148.2 s | 1/2 | ✗ | — | 27 / 1 | 11 / 3 | 1×16, 2×7, 3×1, 4×3 | 8 / 0 | see below |

### Findings

- **Outcome 5/6, position-verified**, against batch 1's 4/6. The first
  dispatched yield COMPLETED in **6/6**, mean 152.4 s.
- **The gate fired 3/6** — but the random draws aligned *perfectly* with side:
  all three west runs drew `id_desc` and all three east runs drew `id_asc`. The
  gate frequency therefore reflects less work under that alignment, not a lower
  intervention rate, and **batch 2 cannot answer the order-conditioned question
  on its own**. This is the confound Rev 6 §W item 3 warned about, realised.
- **Refusals rose sharply**: 21/56 attempt-1 (37.5%, of which Q6 alone
  contributes 11) and 8/56 terminal (14.3%). `max_attempts=4` rescued 13 of the
  21, and all 8 terminal cases exhausted four attempts. The offline Arm M
  prediction of 26.9% conditional terminal is **compatible** with the observed
  8/21 (p = 0.53) but is not clearly reproduced at this n.
- **Q6 is a third arrest mode.** `robot_1` never entered the gap:

  ```text
  r1 max_x +1.673 = 0.027 m SHORT of east face; final x +1.622; 0.88 m short of goal
  ENTERED the gap and stopped in or at it; Q6 never entered it -- robot_1 stopped 0.027 m short of the
  face and settled back to +1.622. Same scenario property (blocker on the goal path), two distinct
  arrest modes: wedged-in-gap vs refused-entry.
  ```

  So the three Arm A losses are 2 wedged-in-gap (P1, P6) plus 1 refused-entry
  (Q6), not three of a kind. Rev 6 §W item 6 turns on this distinction.
- **Two new M4 errors**, `nav2 leg watchdog fired`, both on reroute legs and
  both in runs that still reached 2/2:

  ```text
  [command_bus_node]: nav2 leg watchdog fired command=<id>-reroute robot=robot_1   (Q3)
  [command_bus_node]: nav2 leg watchdog fired command=<id>-reroute robot=robot_2   (Q4)
  ```

### Pooled live gpt-4o 2×2 after batches 1–2

Under the adopted defaults: west/`id_asc` n = 2, west/`id_desc` n = 4,
east/`id_asc` n = 5, east/`id_desc` n = 1. Across those twelve runs,
`robot_1` 11/12, gate 7/12, first yield COMPLETED 12/12, outcome 9/12. The
`id_desc` × east cell — the one where the obstacle channel is observable — is
still n = 1.

---

## AA. Replay Rev 4 — Replication and Raw-Frame Arms

Commits `0cebbcc`, `e1fc5f5`, `6d34db8`; `docs/reports/2026-09-25-frame-replay.md`
Rev 4. OpenAI credit ran out at **187 of 288** Arm S2 calls, and **Arm F never
ran at all** (0 of 336).

**The side-carrier result replicates in direction.** On batch-2 standoffs
(3 west : 1 east reached), pooled `id_desc` with real text scores 0.714 (35/49)
feasible against 0.375 (18/48) with the text withheld, p = 1.1e-3. Seven of nine
scenes move in the predicted direction and **none reverses**.

**The Rev 6 §T magnitude does not replicate.** Batch-1 west is 13/14 feasible
against batch-2 west 6/17, p = 0.0023 — on prompts that differ only in pose
decimals. The gap **survives grey images**, so it is not a property of the
frame.

Two further readings:

- Real → grey amplification (Rev 6 §T contrast (b)) is **neither confirmed nor
  refuted** pooled, p = 0.17. Batch 2 has no headroom to test it.
- The states-only null replicates, p = 0.37.

**Revised statement:** the obstacle text is read when the positional priors
cancel, but the effect size is **scene-dependent, ranging 0–1 across scenes**.
The qualitative finding stands; the 0.962 level does not.

> Pooling caveat on the Arm S2 rows above: `reasoner.py` was rewritten seven
> minutes after they were produced, to add the image fallback of §AB. Rows
> recorded after that rewrite are **not poolable** with them.

Arm F — annotated versus raw frame refusal rates — is coded and unrun. Resume
with `--arm F`.

---

## AB. Refusal Mitigation Shipped, Validation Pending

Commits `9d7328f`, `a255cc8`, `00a1cfc`, `9c61635`.

`vlm.openai.reasoner.image_fallback_after_attempts: 2`: after two refused
attempts the reasoner re-sends the **unchanged** prompt with a mid-grey image of
the frame's dimensions — no re-ask suffix, once per request. Diagnostics
`refusal_attempts`, `image_fallback_used` and `image_fallback_attempt` flow into
the artifacts, so the cost is visible per decision.

Production `is_refusal` is deliberately broader than the census regex. Over
1 407 recorded response texts it produced **0 false positives**, and it catches
forms the census regex missed, such as `I'm sorry, but I can't help with that.`

The change is justified by the grey-image evidence — 0/120 refusals on grey
against 22/60 on real frames — and by §T/§AA showing the text, not the image,
carries the decision. It is **not yet validated**: Arm X (168 cells, ≈ $1.5)
aborted before its first call on `insufficient_quota`.

- **Reporting rule until validated:** report decisions carrying
  `image_fallback_used: true` **separately**.
- **Resume:**

  ```text
  python scripts/replay_live_decisions.py --arm X --runs batch2 --n 4 --pace-sec 8.0
  python scripts/replay_live_decisions.py --arm analyze --runs batch2
  ```

- Live batch 3's gpt-4o run F1 (`20260925_181526`) is **invalid**: 46/46
  `decision=None`, a transport failure into the dead quota. It must not be
  pooled with anything.
- The gpt-4o forced cells west × `id_asc` (×3) and east × `id_desc` (×3) remain
  unrun. VM helpers: `/home/ubuntu/p3_mkcfg.sh <ox> <order> openai` plus
  `f1–f6.sh`.

---

## AC. ER-2 Forced-Order Cells and Two Metric Corrections

Six ER-2 runs with presentation order forced rather than drawn, closing the
cells batch 2's aligned draws could not reach. Summary
`data/logs/vm_runs/ARM_A_PILOT3_SUMMARY.txt`; artifacts under
`data/logs/vm_runs/20260925_{183343,184840,190322,191810,193307,194800}/` —
the first three west × `id_asc`, the last three east × `id_desc`.

| Run | Cell | First `yield_robot` (#) | Gate | First yield | Arrivals | Outcome |
|---|---|---|---|---|---|---|
| G1 | W / `id_asc` | `robot_2` (#2) | no-op | COMPLETED 153.3 s | 2/2 | ✓ |
| G2 | W / `id_asc` | `robot_2` (#2) | no-op | COMPLETED 146.3 s | 2/2 | ✓ |
| G3 | W / `id_asc` | `robot_1` (#2) | fired `r1`→`r2` | COMPLETED 151.1 s | 2/2 | ✓ |
| G4 | E / `id_desc` | `robot_1` (#4) | no-op | COMPLETED 150.6 s | 1/2 | ✗ |
| G5 | E / `id_desc` | `robot_2` (#2) | fired `r2`→`r1` | COMPLETED 156.3 s | 2/2 | ✓ |
| G6 | E / `id_desc` | `robot_1` (#2) | no-op | COMPLETED 150.7 s | 2/2 | ✓ |

Outcome **5/6**, position-verified. All 54 decisions were valid at attempt 1
with **zero refusals**, the forced order was asserted per artifact 54/54, and
ER-2 opened `reverse` **6/6** — against gpt-4o's `yield` 12/12 across batches 1
and 2. G4's loss is the blocker-on-goal-path property again, refused-entry mode,
0.200 m short.

### ER-2 has no `robot_1` anchor

In west × `id_asc` — the cell where gpt-4o's §T control names `robot_1` 124/125
— ER-2 named `robot_1` in **1 of 3** runs. The first-slot/ID mechanism is
therefore **model-specific**, not a general VLM property. Rev 3 §I item 3 is
qualified rather than overturned: ER-2's yielder choice is **near chance and
unanchored** (n small), still with no obstacle mention anywhere. Rev 6 §U's
"named `robot_1` in 5/6" reads as coincidence at this n, not as an anchor.

### Metric correction 1 — the 0.45 m safety invariant is breached in every run

`ros2_ws/src/swarm_execution/config/safety.yaml` sets `min_distance_m: 0.45`.
Measured against ground truth:

```text
G4  min 0.0760 m ; 785 of 3001 GT rows (26.2%) below 0.45, spanning sim_t 20.7-191.9
G1/G6/Q1/Q4 (spot-checked)  min 0.2275-0.2792 m ; 146-224 rows (4.9-7.5%) below 0.45
```

The ordinary case is **by design**: a yield parks the pair at 0.23–0.28 m, which
is 5–7% of ground-truth rows below the limit, because head-on robots must close
to pass. G4 is not that. It breaches by roughly 6× in depth and 3.5–5× in
exposure, and it is not a fleeting near-miss:

```text
t=70.0 r1=(+0.036,+0.074) r2=(+0.096,+0.027) d=0.0762
t=76.0 r1=(+0.024,+0.080) r2=(+0.085,+0.034) d=0.0762
```

Both robots are stationary and interpenetrated at the origin from sim-t ≈ 66 s
to ≈ 84 s and beyond — 0.076 m between the centres of two ≈ 0.35 m robots. This
is the same geometry as the July "Run D" incident that `safety.yaml`'s own
comment cites at 0.078 m. M1 did **not** go STALE in G4, so the
`stale_pose_is_unsafe` fail-safe was not what was exercised.

### Metric correction 2 — "zero contacts" is detector silence

Ground truth reported `robot_robot_contacts` **0 throughout that wedge**. A
contact detector that stays silent at 0.076 m centre separation is not measuring
contact. Every "zero contacts" line in Rev 5–6, and the same line in the Rev 1,
Rev 3 §H and Rev 4 §K conformance blocks, therefore records **what the detector
reported, not that no contact occurred**. Use **minimum pairwise distance** as
the trustworthy channel; the contact flags are not one.

Both corrections go into the pre-registration's safety reporting.

> Superseded in detail by Rev 11 §AK (root-cause analysis). Three statements
> above are wrong: (1) "interpenetrated" — the robots were in driven
> nose-to-nose **contact**; the collision box is 0.14 m long with its nose
> 0.038 m from the logged centre, so 0.076 m centre-to-centre is exactly
> touching, and "≈0.35 m robots" overstates the chassis. (2) "M1 did not go
> STALE in G4" — both robots were STALE for ≈133 s wall in G4 (≈136 s in K1);
> the monitor ignored it under its coordination exemption. (3) "detector
> silence" understates it: `robot_robot_contacts` is written as a literal
> `[]` (`isaac/vgu_sim/acceptance_logging.py`) — no contact detector exists.
> Also: "Run D" was 2026-09-16, not July. The conclusion that minimum
> pairwise distance is the trustworthy channel is unchanged.

### Goal-short variants prepared

Commit `c2d8491` adds `_gshort` YAMLs to remove the blocker-on-goal-path losses
that cost 5 of 12 pilot episodes, with G4 a sixth. Goals move to the opponent's
spawn (±1.5). The maps are byte-identical and the oracle is unchanged; 9 tests.

- **Operator step:** M5 takes goals from `orchestrator.yaml` `initial_tasks`,
  not from the scenario YAML, so that file must be set to ±1.5 and
  `swarm_orchestrator` rebuilt.
- **Known risk:** the passer's terminal pose sits 0.461 m from the parked
  yielder, inside the 0.50 m proximity threshold, so a spurious second episode
  is possible.

> Superseded by Rev 8 §AD in both directions. The spurious second episode did
> not occur — proximity re-analyses after both arrivals are 0/6 — but the
> terminal separation came in tighter than predicted, 0.437 m rather than
> 0.461 m, which is inside M4's 0.45 m `min_distance_m` rather than merely
> inside the 0.50 m proximity threshold. The realised failure is therefore a
> permanent M4 safety hold on the yielder, not a spurious re-analysis, and it
> cost 2 of the 6 pilot episodes.

ER-2 runs on the `_gshort` variants are in progress at the time of writing;
results will appear in a later revision.

> Superseded by Rev 8 §AD: those six runs are reported there. Outcome 4/6
> position-verified (west 1/3, east 3/3), blocker-path losses 0/6, refusals
> 0/83.

---

## Rev 7 Provenance

Commits after `6855552`: `b518ed4`, `fa98ed6`, `0e377c7`, `261e8ab`, `8953126`,
`0cebbcc`, `9d7328f`, `e1fc5f5`, `6d34db8`, `a255cc8`, `00a1cfc`, `9c61635`,
`c2d8491`, plus this documentation commit.

Batch-2 run ids: `20260925_155433`, `20260925_160951`, `20260925_162451`,
`20260925_163949`, `20260925_165442`, `20260925_170938`. Batch-3 run ids:
`20260925_183343`, `20260925_184840`, `20260925_190322`, `20260925_191810`,
`20260925_193307`, `20260925_194800`, plus the invalid `20260925_181526`.

OpenAI spend today ≈ $9; the credit was exhausted at roughly 02:00 ICT on
2026-09-26, which is what truncated Arm S2, Arm F and Arm X. The VM is left
running at the owner's instruction. Artifacts remain git-ignored under
`data/logs/vm_runs/`. Local test suite: ≈ 1 021 passed, 55 failed, 3 errors —
the same environmental set as previous revisions.

---

## AD. Goal-Short Pilot: the Blocker Leaves the Goal Path, a New Failure Arrives

Six ER-2 runs on the `_gshort` variants prepared in Rev 7 §AC, tree `c2d8491`:
obstacle channel on, gate `swap`, `prompt_robot_order: random`, annotated and
raw frames kept, every arrival position-verified at 0.35 m. Goals are the
opponent's spawn, ±1.5, on both sides. Summary
`data/logs/vm_runs/gshort/GSHORT_PILOT_SUMMARY.txt`; artifacts under
`data/logs/vm_runs/gshort/H{1..6}_20260925_{202701,204525,210339,212153,214006,215822}/`.

| Run | Side | Both arrived | Analyses | First yield | Resolution | Min pairwise | GT samples < 0.45 m | Min distance to box | M4 safety stops |
|---|---|---|---|---|---|---|---|---|---|
| H1 | west | ✓ | 7 | 155.7 s | 400.5 s | — | — | — | 8 728 |
| H2 | west | ✗ | 26 | 146.7 s | — | 0.213 m | 65.7% | 1.809 m | 67 666 |
| H3 | west | ✗ | 22 | 156.1 s | — | 0.275 m | 65.5% | 1.839 m | 61 132 |
| H4 | east | ✓ | 8 | 149.1 s | 339.2 s | 0.246 m | 7.0% | 0.362 m | 3 406 |
| H5 | east | ✓ | 15 | 148.4 s | 461.3 s | 0.308 m | 5.7% | 0.367 m | 2 514 |
| H6 | east | ✓ | 5 | 147.9 s | 369.4 s | 0.244 m | 16.2% | 0.378 m | 5 270 |

H1's ground-truth columns are empty because its `ground_truth.jsonl` was
overwritten before the rescue driver was fixed (§AE item 4); its positions come
from the M5 scene log, which is M1 camera estimate rather than ground truth.
The `_rescue` directory holds 3 of the 6 files for the same reason.

Against the ±2.5 ER-2 pilot of Rev 6 §U (E1–E6), cell for cell:

| Measure | `_gshort` (H1–H6) | ±2.5 (E1–E6) |
|---|---|---|
| Episode outcome, position-verified | 4/6 | 2/6 |
| Blocker-path losses | 0/6 | 3/6 |
| First yield COMPLETED | 6/6, mean 150.7 s | 6/6, mean 146.6 s |
| Mean resolution time | 392.6 s | 363.3 s |
| Refusals | 0/83 | 0/115 |
| Proximity re-analyses after both arrived | 0/6 | — |

H1 is the direct contrast case: `robot_2` stopped 0.294 m clear of the west box
face, where E3, E4 and E5 were arrested at roughly 0.038 m. The oracle's
yielder was chosen and no spurious proximity episode followed.

### Verdict 1 — `_gshort` removes the blocker-on-goal-path losses

Decisively: no run's passer came within 0.36 m of a box face, against 3 of 6 on
±2.5 and 5 of 12 across the two earlier pilots. That half of the Rev 6 §W item 6
scenario question is settled.

### Verdict 2 — symmetric ±1.5 goals create a park-beyond-goal failure

Worse than the 0.461 m terminal separation predicted in Rev 7 §AC. The
open-side yielder parks at |x| = `park_offset_m` = 1.789 m
(`reasoning/rag/scene_geometry.py`), which is **beyond** the passer's goal at
1.5 m, so the arrived passer comes to rest on the corridor axis at |x| ≈ 1.58 m,
inside the yielder's return path. On H2 and H3 the yielder `robot_2` is
stranded at (1.18, −0.16), 2.68 m from its goal, with the pair 0.437 m apart —
inside M4's 0.45 m `min_distance_m` — and M4 safety-stopped for roughly 65% of
ground-truth samples. ER-2 correctly declines to intervene:

```text
Although the robots are within 0.43 meters of each other, neither faces the
other, indicating they are not head-on and no deadlock exists.
```

Moving the goals to ±1.3 would make this worse, not better: the obstruction
stays on the axis and moves closer to the corridor mouth. Not attempted.

### East is not protected; east 3/3 is a race, at n = 3

The bracketing question for this pilot was whether the east variant is
geometrically safe. It is not. The two variants are mirror images: on west the
yielder is `robot_2` (goal −1.5) parking at +1.789 while the passer `robot_1`
stops at its goal +1.5; on east the yielder is `robot_1` (goal +1.5) parking at
−1.789 while the passer `robot_2` stops at −1.5. Measured park poses are
(1.81, −0.01) west and (−1.81, 0.00) east. The park-beyond-goal conflict is
present identically on both sides.

What separates the outcomes is sequencing — whether the passer is still
outboard of the park point when the yielder pulls out. On H4 the yielder
crossed the corridor centre at 350 s while the passer was still dwelling at
|x| ≈ 2.46 m and did not return inside the park radius until 360 s; on H5 the
margin is 349 s against 487 s. On H2 and H3 the passer returned to its goal
within 15–30 s of reaching its clearing pose — back at 1.59 m by 283–299 s —
while the yielder was still at 1.18 m, and the pair locked there.

Two runs cut against any cleaner rule. H1 is the same west geometry that
happened to sequence correctly. H6 is an east run whose passer *did* return
early (291 s, against the yielder's centre crossing at 385 s) and which
completed anyway, with the pair at 0.391 m — below the same 0.45 m limit that
held H2 and H3. So the 0.45 m threshold alone does not discriminate the
outcomes either. Read east 3/3 as three favourable draws on a race condition,
not as evidence of side-safety, and treat the west/east split in the table as
sampling rather than as a property of the side.

### Follow-up in progress at the time of writing

`_bshort` variants shorten **only** the blocked-side goal — the yielder's goal
beyond the box — and keep ±2.5 on the open side, so the passer's goal lies
beyond the park point instead of inside it. Three ER-2 runs on the west side
are being run; results in a later revision.

> Superseded by Rev 9 §AG.

---

## AE. Apparatus Notes From This Batch

1. `reasoning/vlm/reasoner.py` has imported `PIL` at module level since the
   image-fallback commit `9d7328f`. M5 died at import inside the container until
   `pillow` was installed. Add `pillow` to the container recipe, or make the
   import lazy.
2. `git archive` stamps files with the commit time, which is older than the
   previous VM build, so `colcon build` "succeeded" in 1.5 s and left the **old**
   config installed. Verify installs by `md5`, never by exit code, and touch
   shipped sources before rebuilding.
3. `scripts/vm/fc_launch.sh` exits 141 — SIGPIPE from an `ls | head` under
   `set -o pipefail` — after its cleanup, so the final `done: STAMP=…` line
   never prints. Parse the STAMP from the `fc_run_<STAMP>` directory instead.
4. `data/logs/simulation/<scenario>-seed42-rep000/ground_truth.jsonl` is keyed
   only by scenario, seed and rep, so the next run overwrites it. Rescue it
   before each launch; H1's was lost this way.
5. `orchestrator.yaml` pristine `md5` on the VM is now
   `8750bdb04f048775b7794aefe2770ba6` at tree `c2d8491`.

---

## AF. Next Steps

1. Adopt `_bshort` if J1–J3 succeed, then re-run the family pilots on it with
   both models for the pre-registration.
   *Superseded by Rev 9 §AG: J1–J3 succeeded (3/3 position-verified). See
   Rev 9 §AH item 1 for the follow-on runs.*
2. Add `pillow` to the container recipe in the implementation notes' M6 section
   and make the reasoner's image import lazy.
3. Resume the OpenAI-dependent arms when credits return: replay `--arm F`, the
   `--arm S2` remainder, `--arm X`, and the forced gpt-4o cells.
4. Report minimum pairwise distance and percentage of samples below 0.45 m as
   standard safety columns. Ground-truth contact flags are not evidence
   (Rev 7 §AC, metric correction 2).
5. Stop the VM when the batch is done unless more runs are planned.

---

## Rev 8 Provenance

Commits after `b5a0bf9`: `e708ffa` (the `_bshort` variants the follow-up runs
use), plus this documentation commit.

Run ids from `data/logs/vm_runs/gshort/GSHORT_PILOT_SUMMARY.txt`:
`H1_20260925_202701`, `H2_20260925_204525`, `H3_20260925_210339`,
`H4_20260925_212153`, `H5_20260925_214006`, `H6_20260925_215822`.

VM state per this batch's restore: config `md5`
`8750bdb04f048775b7794aefe2770ba6`, container restarted, GPU idle. Sampling is
uncontrolled on all 83 ER-2 calls for the reason given in Rev 6 §U —
`unsupported_sampling` is recorded on every one. Artifacts remain git-ignored
under `data/logs/vm_runs/`.

---

## AG. `_bshort` Pilot: the Blocked-Side Goal Alone

Blocked-side goal short, commit `e708ffa`. ER-2, west variant, gate `swap`,
obstacles ON, order `random`, annotated and raw frames kept; every arrival
position-verified.

**Design.** Shorten **only** the goal that lies beyond the box — the open-side
yielder's goal moves to the blocked robot's spawn, ±1.5 — and keep ±2.5 on the
open side. The passer's goal (2.5) then lies 0.711 m beyond the yielder's park
point (`park_offset_m` 1.789) and 0.061 m beyond the M3 escort endpoint
(2.439), the binding margin, asserted positive in a test. The yielder's goal
(−1.5) leaves 0.130 m chassis-front clearance to the box near face (−1.70).
Documented hazard: `arrival_position_tolerance_m` 0.35 would accept a pose
whose chassis overlaps the box span; the goal was deliberately not moved
because the box is baked into the static map. Generator flag
`--goal-mode blocked_short`; the v1 and `_gshort` YAMLs are byte-identical to
this variant's twins (test-pinned); the map PGMs are identical to their twins;
USDs built and `validate` PASS; 61 tests collected across
`test_generate_head_on_family.py` and `test_generate_warehouse_map.py`.

| Run | STAMP | Both arrived | Analyses | First yield (s) | Resolution (s) | Min pairwise (m) | % GT samples < 0.45 m | Min dist to box (m) | Safety stops |
|---|---|---|---|---|---|---|---|---|---|
| J1 | `20260925_223245` | ✓ | 5 | 149.6 | 346.0 | 0.225 | 7.1% | 0.232 | 3 654 |
| J2 | `20260925_225104` | ✓ | 7 | 148.1 | 345.8 | 0.280 | 7.0% | 0.222 | 3 540 |
| J3 | `20260925_230902` | ✓ | 7 | 148.0 | 350.5 | 0.216 | 6.9% | 0.184 | 3 620 |

0 refusals (0/19), the M3 gate fired exactly once per run, and 0 post-arrival
proximity re-analyses occurred. The gate's intervention, identical across all
three runs:

```text
[orchestrator_node]: yield re-grounded request=75b0cc74… from=robot_1 to=robot_2 reason=yield re-grounded: robot_1 has 0.70 m retreat room < 1.08 m required; robot_2 feasible
```

`robot_2` completed the full westward transit in all three runs (final x
−1.397 / −1.407 / −1.444):

```text
[orchestrator_node]: robot robot_1 arrived at base goal (2.5, 0.0) distance_m=0.05 check=within_tolerance
[orchestrator_node]: robot robot_2 arrived at base goal (-1.5, 0.0) distance_m=0.09 check=within_tolerance
```

Versus gshort west H1–H3, 1/3 (H2/H3: 65% of samples < 0.45 m, 61–68 k safety
stops), and ±2.5 west E1–E3, 1/3.

**Verdict.** `_bshort` fixes the west side with no reintroduced blocker-path
loss (n = 3, west only; the east `_bshort` variant is built and validated but
not yet run). Mechanism confirmed from ground truth: the passer's backtrack
after its maximum x was 0.000 m in all three runs (max x 2.455–2.460; yielder
park 1.801–1.804), versus 0.580 m in gshort H2. This corrects Rev 8 §AD's
east/west reading: gshort's east and west geometries are mirror-symmetric;
east "won" because the escort leg completed (H4's passer reached −2.450 and
held) while west lost a race (H2's passer turned back at +2.163, short of the
+2.439 endpoint, and both released simultaneously, latching at 0.430 m).
Known risk: the escort-endpoint margin (0.050–0.061 m) is thin against the
≈0.1 m drift the `FEASIBILITY_MARGIN_M` comment cites.

---

## AH. Next Steps

1. Run the east `_bshort` variant (n ≥ 3) and then re-run the family pilots
   for both models on `_bshort` as the pre-registration scenario.
2. Consider widening the escort-endpoint margin (goal 2.6 or escort 2.35)
   before data collection.
3. The arrival-tolerance-vs-box hazard: either shrink
   `arrival_position_tolerance_m` for goals adjacent to obstacles, or verify
   no box overlap in re-scoring.
4. Unchanged: OpenAI-dependent arms pending credits; stop the VM when done.

---

## Rev 9 Provenance

Commit `e708ffa` plus this documentation commit. Run ids:
`20260925_223245` (J1), `20260925_225104` (J2), `20260925_230902` (J3). VM
restored: `orchestrator.yaml` `md5` `584ebf60728ec0611145b4b3280ce44e`,
container restarted, GPU idle, instance still running.

---

## AI. `_bshort` Validation Batch: Both Sides at the Widened Goal

Six ER-2 runs on tree `cf4899f`: the `_bshort` open-side passer goal widened
±2.5 → ±2.6 (`dcfa144`), taking the designed escort-endpoint margin from
0.061 m to 0.161 m. East variant (never run before) K1–K3, then west re-run
K4–K6 on the new goal. Gate `swap`, obstacles ON (block verified in all 39
prompts), `prompt_robot_order: random`, annotated and raw frames kept, every
arrival position-verified online and re-scored offline (`box_overlap` column
included, `8e77bc4`). Goals: east `robot_1` (1.5, 0) / `robot_2` (−2.6, 0);
west `robot_1` (2.6, 0) / `robot_2` (−1.5, 0). Summary
`data/logs/vm_runs/bshort2/BSHORT2_PILOT_SUMMARY.txt`; artifacts under
`data/logs/vm_runs/bshort2/20260926_{063238,065219,071034,072849,074705,080521}/`.

| Run | Side | Order at yield analysis | First `yield_robot` | Gate | First yield | Both arrived | Analyses / commands | Min pairwise (m) | % GT < 0.45 m | Passer backtrack (m) | `box_overlap` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| K1 | east | `id_asc` | `robot_1` | no-op | COMPLETED 148.9 s | ✓ | 9 / 4 | **0.076** | **25.7** | 0.003 | 0/2 |
| K2 | east | `id_desc` | `robot_2` | fired `r2`→`r1` | COMPLETED 149.9 s | ✓ | 5 / 1 | 0.230 | 4.8 | 0.003 | 0/2 |
| K3 | east | `id_asc` | `robot_1` | no-op | COMPLETED 144.9 s | ✓ | 7 / 2 | 0.316 | 7.1 | 0.003 | 0/2 |
| K4 | west | `id_desc` | `robot_1` | fired `r1`→`r2` | COMPLETED 147.1 s | ✓ | 3 / 2 | 0.250 | 4.9 | 0.141 | 0/2 |
| K5 | west | `id_desc` | `robot_2` | no-op | COMPLETED 149.3 s | ✓ | 10 / 2 | 0.231 | 7.4 | 0.000 | 0/2 |
| K6 | west | `id_desc` | `robot_2` | no-op | COMPLETED 149.1 s | ✓ | 5 / 1 | 0.278 | 4.6 | 0.000 | 0/2 |

All 12 arrivals were accepted `check=within_tolerance` (M1 distance
0.055–0.202 m), and the offline rescore plus ground truth agree — 0 flips.
The correct (feasible) robot executed the yield in all six runs: named
outright in four, produced by the `swap` gate in two (K2, K4). 39 ER-2
calls, 0 refusals, 0 parse or API failures, all at attempt 1. Zero Nav2
recovery behaviours ran.

### Verdict — `_bshort` is the pre-registration scenario

East 3/3 discharges the side left open in Rev 9 §AG, and west 3/3 confirms
the widened goal changed nothing mechanistically (passer backtrack 0.000 m
in K5/K6 and ground-truth jitter elsewhere; K4's 0.141 m is its own goal
overshoot to 2.815 settling back to ≈2.68, never inside the 2.439 escort
endpoint). This closes the scenario question of Rev 6 §W item 6 for both
sides. The 12-run `_bshort` tally is now 9/9 position-verified at the
adopted defaults (J1–J3, K1–K6, one geometry change between them) with zero
losses to the blocker-on-goal-path property and zero park-beyond-goal holds.
Adopted into the pre-registration as amendment A1 of
`docs/superpowers/specs/2026-09-26-prereg-v1-amendments.md`, whose condition
this batch satisfies. Still open on the scenario axis: the gpt-4o `_bshort`
family pilot (OpenAI credits).

### Realised goal margin is smaller than the designed margin

Nav2 stops the passer at ≈2.50–2.53, not at the 2.6 goal, so the realised
margin past the 2.439 escort endpoint is 0.063–0.096 m against the designed
0.161 m — still 3–6× the J-batch's realised 0.016–0.021 m. The widening
bought real margin, but goal-position designs must budget for Nav2's early
stop inside the arrival tolerance, not for the nominal goal.

### K1 — a second G4-class interpenetration

K1's minimum pairwise distance is 0.076 m — the same depth as G4 (Rev 7
§AC) — with 25.7% of ground-truth rows below 0.45 m. It occurred at the
corridor centre during the opening `reverse` → failed `reroute` sequence at
sim 50–107 s, before any yield, and the ground-truth contact list stayed
empty throughout, reconfirming that the contact flags are not a measurement.
Two instances in 12 ER-2 east-side runs, both during ER-2's opening
non-yield phase, sharpen the pre-Arm-B safety question (amendment A5): M4's
safety monitor, the contact detector and M1's STALE fail-safe were all
silent while two ≈0.14 × 0.18 m chassis overlapped for tens of seconds.

> Superseded by Rev 11 §AK: this was 51.6 s of driven nose-to-nose
> **contact** (sim 53.3–104.9), not overlap, and the layers were not
> "silent" — M1 went STALE and the monitor had latched 0.8 s before the
> `reroute` exemption lifted the latch and disarmed it. "East-side" is not
> supported as a factor at n = 2; the exposure is a `reroute` grounded onto
> the re-approach after a `reverse`.

### Metric definition note — passer backtrack

Two defensible definitions of the backtrack statistic disagree on gshort
H2: peak-|x|-minus-minimum-after-peak gives 0.878 m where Rev 9 §AG's
first-turnaround reading gives 0.580 m (2.163 − 1.583). Both give 0.000 m
on J1–J3 and the table above uses the peak-minus-minimum form. The
pre-registration must pin one definition before the statistic is quoted
comparatively.

### Apparatus notes

- The J-batch VM helper scripts hard-code the ±2.5 goals; this batch used
  new drivers (`_vm_driver/`, synced locally) whose config check also
  asserts the installed goals against the scenario YAML and installed
  md5 = source md5.
- `box_overlap` fired 0/12, but every box-side robot was accepted on the
  corridor side of its goal (0.08–0.20 m short), so the flag's target case
  never arose; this is not evidence the flag works.
- The per-run `orchestrator_used.yaml` is written **after** the launcher
  restores the `openai` backend; the config actually in force is preserved
  as `orchestrator_installed_during_run.yaml` (md5
  `ad6c6e74802301e9d92cb6c0ce679a07` east,
  `ce6d31eed3ecf0376a93321eb331e8b7` west).

---

## AJ. Next Steps

1. **The ER-2 side of the pre-registration baseline is done.** All
   remaining data collection is gpt-4o-side and blocked on OpenAI credits:
   the `_bshort` family pilot, replay `--arm F`, the `--arm S2` remainder,
   `--arm X` (image-fallback validation), and the forced-order live cells.
2. **Decide the VM now.** No further runs are possible until credits
   return; it bills ≈US$0.9/h against an L4 stockout risk on restart.
   Owner's call, but the idle case for keeping it warm is gone.
3. **Root-cause the K1/G4 interpenetration class before Arm B** (amendment
   A5): two instances, both in ER-2's opening non-yield phase, three
   silent safety layers.
4. **Build Arm B** — `reasoning/baselines/classical_reasoner.py` is
   specified in the research design but absent from the tree (prereg
   amendment freeze blocker 1), and it is the largest work item between
   here and the `prereg-v1` tag.
5. **Decide failure-context memory depth** (last-N vs last-failed) before
   Arm A collection — freeze blocker 3.
6. Pin the passer-backtrack definition (§AI metric note) in the
   pre-registration's measurement plan.

---

## Rev 10 Provenance

No new code commits — the batch ran on tree `cf4899f` (`dcfa144`,
`8e77bc4`, `cf4899f` reported in Rev 9's follow-on work plus the amendment
set `4d7d33b`); this revision is documentation only. Run ids:
`20260926_063238` (K1), `20260926_065219` (K2), `20260926_071034` (K3),
`20260926_072849` (K4), `20260926_074705` (K5), `20260926_080521` (K6).

VM restored to tree `cf4899f` (525 files verified), `orchestrator.yaml`
`md5` `aa93f55045c63e956088790ea6848e8a` on source and installed copy,
container restarted, GPU idle (0%, 170 MiB, no processes), instance left
RUNNING. Sampling is uncontrolled on all 39 ER-2 calls
(`unsupported_sampling` recorded per call, Rev 6 §U). Artifacts remain
git-ignored under `data/logs/vm_runs/bshort2/`.

---

## AK. K1/G4 Root Cause: the Coordination Exemption, Not a Silent Stack

Full analysis: `docs/reports/2026-09-26-close-approach-analysis.md`
(commit `d638b5b`); this section is the digest and the supersession record
for Rev 7 §AC and Rev 10 §AI.

**What the events were.** Driven nose-to-nose contact for ≈51 sim-s in each
run (G4 sim 53.2–104.2, K1 53.3–104.9). The URDF collision box puts the
nose 0.038 m ahead of the logged centre, so 0.076 m centre-to-centre is
exactly touching; at every wedge row the gap between collision shapes is
0.0000 ± 0.0003 m. Not interpenetration — Isaac's physics held the contact.

**Why every layer stayed quiet.** M4's safety monitor exempts a robot pair
from both the 0.45 m rule and the STALE fail-safe whenever either robot has
an ACTIVE command (`safety.py`). ER-2's `reroute` grounds to an
empty-waypoint reroute — into which M5 injects the robot's own base goal —
plus a 15 s `temporary_wait` for the partner, so both robots went ACTIVE,
the exemption disarmed the monitor (in K1 it lifted a latch that had fired
0.8 s earlier), and robot_1 drove into its waiting partner; when the wait
expired the partner pushed back. The Nav2-leg watchdog that eventually
failed the leg is 120 s wall, not the 20 s the M4 spec claims. M1 behaved
correctly throughout: it tracked to 7 mm, lost both markers at contact
(overlapping 0.12 m quads) and went STALE on schedule — the monitor ignored
it under the same exemption. The "5880 safety stops" in the K1 analyzer are
40 Hz hold-rate log lines (≈58 s latched), not events. And the ground-truth
contact fields are hard-coded `[]` — no contact detector exists to be
silent.

**Exposure shape.** A `reroute` landing on the re-approach after a
`reverse`, before any yield: M5's stall memory survives the reverse, so the
next analysis fires mid-approach. Across 27 archived reverse-opened runs,
the only two that got `reroute` next (G4, K1) are the only two contact
runs; the 25 that yielded, and the 6 post-yield reroutes, had none.
East-side is not established as a factor at n = 2. Arm B's policy table
also emits `reroute` (`blocked_path`), so the classical arm inherits the
same exposure until the fix lands.

**Recommended fix (not yet implemented).** Restrict the exemption to
clearing maneuvers: only `yield` and `reverse` exempt a pair; Nav2-goal
legs (`reroute`, `convoy`, `navigate`) and wait commands do not. Yield
still works — the pair is already 0.73–0.76 m apart at yield completion.
Pair it with a prompt no-progress failure for Nav2 legs and correct the
spec's 20 s claim. A bare hard floor was evaluated and rejected: travel
after the 0.45 m trigger reaches 0.29 m, so a floor works only with a
closing-speed cap.

**Side findings.** M1 speeds are metres per *wall*-second (≈0.38× real at
this RTF), so the monitor's 0.2 m/s speed-limit rule cannot fire in
simulation. `safety.yaml` `command_timeout_sec` is loaded but ignored.
`docs/specs/module4/safety-monitor.md` §7's 20 s exemption bound is wrong
(120 s wall). Rev 7 §AC's "Run D in July" should read 2026-09-16.

---

## AL. Next Steps (Rev 11 delta)

1. Implement the exemption fix (§AK) as the pre-Arm-B safety change, with
   unit tests over the latch/exemption transitions and an ER-2
   reverse→reroute regression run on the VM. Amendment A5 stays open until
   this lands and is verified.
   *Done — superseded by Rev 12 §AM: landed at `45e55f4` and verified by
   runs M1/M2; A5 is closed with two tracked residuals.*
2. Fold the M1 wall-clock speed scaling into the monitor's speed rule (or
   document it as inoperative in sim) and wire `command_timeout_sec` or
   delete the key.
3. The rest of Rev 10 §AJ stands: Arm B build, failure-context depth,
   credit-blocked gpt-4o arms, VM stop decision.

---

## Rev 11 Provenance

Commit `d638b5b` (analysis report + implementation notes) plus this
documentation commit. No code or config changed; no runs. Analysis inputs:
the G4 and K1 artifacts, 88 archived Nav2 logs, and the M4/M5/M6 sources at
`cf4899f`.

---

## AM. M4 Exemption Fix Landed and Verified; Arm B Reasoning Core Merged

### The exemption fix (`45e55f4`, `1c53844`, `994b2b1`)

The rule now in force: a robot is exempt while its current ACTIVE
coordination command's own **action** is `yield` or `reverse`; a pair is
exempt while at least one member is exempt; nothing else exempts —
`reroute`, `convoy`, `navigate`, waits, and any action the monitor has not
seen all fail closed. The action comes from `/coordination/commands`, not
from the command id: the id carries the **decision's strategy** shared by
every robot of the decision (`<request>-<strategy>`), so id-parsing would
have exempted a yield's passer-wait and a refused reverse's waits. A
ROS-free `CoordinationTracker` joins commands and statuses at evaluation
time, and a robot's exemption ends only on a terminal status for the
command it is ACTIVE on. `test_safety_monitor.py` grows to 65 tests,
covering both mixed pairs, the K1 latch-continuity order, the G4
latch-during-reroute order, and the STALE fail-safe staying armed under
non-clearing commands.

VM verification on the west `_bshort` scenario (artifacts
`data/logs/vm_runs/m4fix/`):

| Run | STAMP | Design | Result |
|---|---|---|---|
| M1 | `20260926_101653` | mock-forced `reverse` → `reroute` → `yield` (the G4/K1 exposure) | Reroute + partner wait went ACTIVE `exempt=False`; latch fired 8.7 s later; pair held at **0.381 m** by ground truth, no contact; the scripted yield then COMPLETED 141.2 s with both arrivals in tolerance |
| M2 | `20260926_103507` | ER-2, gate `swap`, order random, obstacles on (yield non-regression) | Opening `reverse` exempted normally; yield COMPLETED 152.8 s; arrivals 0.10 / 0.09 m; min pairwise 0.276 m; escort passed the parked yielder at 0.392 m with no spurious latch |

M1's pair rested 0.381 m apart — marginally under the ~0.40 m the
regression brief named, and nowhere near the 0.076 m driven contact the
same forcing produced pre-fix. Two residuals, tracked but non-blocking:
the K1 ordering (latch before the leg goes ACTIVE) is unit-covered but not
host-reproducible with a zero-latency mock; and a Nav2 leg that goes
ACTIVE after a latch keeps its goal until the 120 s wall watchdog — the
root-cause report's mitigation 2, still open by design. The M4 spec
(`docs/specs/module4/safety-monitor.md`) gains §10 for the rule and
corrects §7's 20 s claim to the 120 s bound in force. **Amendment A5 is
closed.**

### Arm B reasoning core (`f345c7a`…`072315d`, merged at `65cc850`)

`reasoning/baselines/` now exists: the rev-8 geometry classifier
(`classify_scene`), the policy table with FCFS + commitment tiebreak
(`decide_classical` / `resolve_classical`), the shadow comparator
(`compare_decisions`), the trimmed motion table
(`derive_motion_table` with `arrival_stamp`), and
`load_classical_params` over a new `config/rag.yaml` `classical:` section
with `extra="forbid"`. Arm B emits today's `CongestionDecision`
unchanged; the classifier's forced `blocker_kind="object"` and the full
passing order live on `ClassicalResolution` for shadow logging. Two plan
bugs were corrected against the spec (head-on's "exactly 2 stopped
robots" is measured within `r_conflict` of each other, not scene-wide;
FCFS measures arrival at the zone that produced the verdict, not
`zones[0]`). 70 new tests; merged suite 1 144 passed with the
environmental failure set unchanged.

Tracked follow-ups from the review, recorded in the amendment set:

1. **Contract fields**: `CongestionDecision` has no `blocker_kind` or
   `crossing_order`, which costs nothing on two-robot cells but degrades
   Arm B's executed decision at 3+-robot intersections and blocks the T3a
   blocker-verdict comparison. The fix is the plan's Task 1 additive
   optional fields — a shared-contract decision.
2. **M1 wall-clock speed scaling** (root-cause analysis side finding):
   M1 speeds are metres per wall-second (≈0.38× real at this RTF), so
   M4's 0.2 m/s speed rule cannot fire in sim and Arm B's 0.05 m/s
   stopped threshold becomes ≈0.13 m/s real when Phase 2 wires it to live
   M1 states. One shared fix or a documented sim-time convention is
   needed before Arm B's T1 parameter tuning.
3. **Phase 2 wiring**: shadow logging in the live M5 loop (the spec's
   per-decision classical answer) is the remaining Arm B work item.

---

## Rev 12 Provenance

Commits `45e55f4`, `1c53844`, `994b2b1` (M4 fix) on
`fix/deadlock-collision-resolution`; `f345c7a`, `6c27f04`, `de994c6`,
`20669c3`, `072315d` on `feat/arm-b-classical`, merged at `65cc850`; plus
this documentation commit. Run ids `20260926_101653` (M1),
`20260926_103507` (M2). VM restored to tree `cf4899f` with the fix
uninstalled (all five md5s verified on source and installed copies),
container restarted, instance left RUNNING. Merged local suite: 1 144
passed, 55 failed, 3 collection errors (the environmental set).
