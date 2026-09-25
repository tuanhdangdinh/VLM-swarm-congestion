# Overnight Findings - New Host, Presentation-Order Probe, Live Counterbalanced Runs

**Prepared:** 2026-09-25

**Revision history:**

- Initial draft: overnight session of 2026-09-24/25 — new GPU host bring-up, closed-loop replication, offline presentation-order probe, and four live counterbalanced M2 runs.
- Rev 2 (2026-09-25): adds the M3 yield feasibility gate and random presentation order, five live validation runs, and a correction to the strength of the live order effect.
- Rev 3 (2026-09-25): adds the Gemini Robotics-ER 2 M2 backend — its offline presentation-order arm and four live closed-loop runs — plus two arithmetic/instrumentation corrections to Rev 1.
- Rev 4 (2026-09-25): adds the decisive ER-2 cell (west-blocked, `id_asc`, gate off, n=3) and the gpt-4o obstacles-OFF arm, a consolidated live tally across both models, and the finding that the offline probe does not predict live order sensitivity.
- Rev 5 (2026-09-25): adds the six-run Arm A pilot on the adopted defaults, the full gpt-4o refusal census, and the real-frame replay that identifies the annotated camera frame as the refusal trigger.

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
   *Superseded in part by Rev 4 §L item 5: the opening `reverse` is 5/6 live,
   not 3/3 — D1 opened on a pair stall and answered `yield` directly, so it is
   a strong habit, not an invariant. The comparability conclusion stands.*
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
4. **Neither model uses geometry.** D2 chose the blocked robot with the
   obstacle block present in the prompt; O1 and O2 chose it with no obstacle
   information at all, to the same outcome. The M3 gate (`swap`) remains the
   only mechanism that has made the blocked cell succeed (L1, G1).
5. **ER-2's opening `reverse` is 5/6 live, not 3/3.** D1 opened on a pair stall
   and went straight to `yield`; D2 and D3 opened on solo stalls and reversed.
   gpt-4o also opened on solo stalls in O1 and O2 and answered `yield`, so
   trigger shape correlates with the opening `reverse` without forcing it.
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
