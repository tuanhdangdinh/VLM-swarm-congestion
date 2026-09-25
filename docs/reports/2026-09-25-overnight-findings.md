# Overnight Findings - New Host, Presentation-Order Probe, Live Counterbalanced Runs

**Prepared:** 2026-09-25

**Revision history:**

- Initial draft: overnight session of 2026-09-24/25 — new GPU host bring-up, closed-loop replication, offline presentation-order probe, and four live counterbalanced M2 runs.
- Rev 2 (2026-09-25): adds the M3 yield feasibility gate and random presentation order, five live validation runs, and a correction to the strength of the live order effect.
- Rev 3 (2026-09-25): adds the Gemini Robotics-ER 2 M2 backend — its offline presentation-order arm and four live closed-loop runs — plus two arithmetic/instrumentation corrections to Rev 1.

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
4. **Caveat, kept from the run agent.** Every run in this batch had the obstacle
   channel ON, so order and channel co-vary within the batch. The offline probe
   found the channel inert, so this is unlikely to matter, but an obstacles-OFF
   live arm would close it.
   *Partly superseded by Rev 3 §G: "inert" is a gpt-4o result and does not
   generalise — the same channel has a large effect on ER-2, so the
   obstacles-OFF arm has to be run per model.*

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
3. **Geometry is unused by ER-2 as well.** G1 named the physically blocked
   `robot_1`; no live or offline justification mentions the obstacle; offline
   `P(correct)` is at chance. The M3 gate, not the model, is what made G1
   succeed.
4. **Order sensitivity for ER-2 is not established.** The named yielder was the
   first-presented robot in G1 and G2 and the second in G3, at n = 1 per cell,
   with no temperature control and with G3's geometry differing (§H). The
   slot/ID question stays open for ER-2.
5. **The decisive ER-2 cell was not run** — west-blocked × `id_asc` × gate off.
   "ER-2 fails like gpt-4o without the gate" is inferred from G1's choice, not
   observed.
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
