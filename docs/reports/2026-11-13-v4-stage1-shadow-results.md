# v4 Stage 1 Per-Cluster Live Shadow: S1b Results

**Prepared:** 2026-11-13

**Revision history:**

- Initial draft: results of the 7-episode Stage 1 live shadow cell (seed positions 21-27), scored against the Stage 1 exit criteria; the corrected tranche-1 dispatch counts.

---

## Scope

- **What ran.** The Stage 1 live shadow of
  `docs/superpowers/specs/2026-11-12-per-cluster-live-path-design.md` (Section
  5), with the runbook `docs/guides/v4_s1b_pc_shadow_runbook.md`, on the 5-robot
  S1b scene (`mapd_5_s1b`). In every analysis the ordinary Arm A loop
  decided and dispatched as in prereg-v3 tranche 1. After it, M5 made a second,
  per-group M2 call on its own worker, grounded each group's choice, ran the
  joint check, and wrote the result into the decision artifact as
  `per_cluster_shadow`.
- **What the shadow does not do.** It dispatches nothing. Every
  robot motion in these episodes came from the ordinary loop. This report says
  nothing about what would happen if per-group choices were dispatched (Stage
  2, not started).
- **Evidence grade: exploratory.** It is not a prereg-v3 cell and does not
  pool with A32-A36. The exit thresholds are proposals (see Exit Criteria).
- **All numbers** are from the gitignored bundles and were re-derived for this
  report by re-running the analysis scripts (commands in Reproduction). Where
  a number differs from an earlier summary, the artifact value is used and
  the difference is listed in Corrections.

---

## Summary

| Question | Answer (artifact) |
|---|---|
| Episodes | 7 (`v4pcs_pos{21..27}_armA_a1`), one attempt each, all `outcome=ran`, every GATE and RESTORE OK |
| Seeds | `config/s1_seeds.yaml` positions 21-27. Positions 21-26 were used before as S1b pilot seeds (E21-E23, `docs/reports/2026-10-12-shield-fix-and-minibatch.md` §1.2; E24-E26, `docs/reports/2026-10-17-escort-filter-minibatch.md`). Position 27 is new |
| Model | `gemini-robotics-er-2-preview` (ordinary and shadow) |
| Analyses | 50 (4 / 7 / 11 / 6 / 13 / 6 / 3) |
| Shadow blocks | 50/50 `ok`; parse valid at the first attempt 50/50; no `pending`, `timeout`, `error` or `skipped` |
| Multi-group analyses | 12 (3 / 0 / 1 / 0 / 2 / 4 / 2); 38 single-group |
| Joint-check flags | 0/12 on every flag (exact conflict, shared robots, retreat clashes, path proximity) |
| Latency (ms) | shadow total median 8089, p90 9701.5, max 11062 (M2 share median 97.5 %); ordinary analysis median 8045, p90 9883.9, max 18319 (one outlier, pos25) |
| Live outcome per analysis | dispatched 14, withheld 33, no decision 3 |
| Section 2 branch | not settled: 4 Branch-1 cases, 1 indeterminate, 0 group-only concurrent starts |
| Safety | floor armed (0.20 m) in 7/7, 0 floor stops, GT minimum pair distance 0.2151 m (pos27) |
| Spend (estimated) | $0.7727 total, of which shadow $0.4061 |
| VM | stopped and verified `TERMINATED` at the end of the follow driver |

---

## Runtime, Config and Evidence

### Runtime

- **Code:** `feat/v4-per-cluster-parity` at fdf333d. The kit's
  `mac_build_delta_v4.log` records `WORKTREE HEAD == fdf333d over reasoning
  ros2_ws`, `NO UNCOMMITTED runtime edits` and `MANIFEST == code diff
  1624db1..fdf333d minus orchestrator.yaml / v4 overlays / offline script`.
  The 14 deployed files in `kit/manifest_v4.txt` match the md5s of the files at
  fdf333d (checked file by file for this report).
- **Base runtime:** the prereg-v3 tranche-1 VM runtime (A27 M4 pins), with the
  14-file delta. `orchestrator.yaml` was not deployed (pin 1f656533; the
  overlay replaces it whole).
- **Safety floor:** `safety.yaml` installed c41913f02cf4e988162c30a44a5dda04
  (`hard_contact_floor_m: 0.20`), swapped in for the run and restored to
  pristine afterwards (`RESTORE_V4 OK`).
- **Grounding:** `config/grounding/s1b_dynamic_shield_escort.yaml`
  (409688866d25289309e081dcb9433037), `config/rag.yaml`
  (e18c723cff9cada3f320d564c2ecee5a).

### Per-episode inputs

| Episode | Seed | Scenario yaml md5 | USD md5 | Overlay md5 |
|---|---|---|---|---|
| pos21 | 2107305794 | 61fd6faf31f594186c101a9b671c52ca | 8a21596e7fafc11feaf8f42789b2ea63 | 242204df8b0adcbc32abbbba8a577489 |
| pos22 | 1949376341 | ccb674e850c2246444081a66336abe5d | 7b87e464735ece9560bd34450192b692 | 7512fc62c5198e9ca984435f255b60df |
| pos23 | 1256773113 | ea69ed93de0e9efddabfd061a5e0a911 | 7cf07059ecdf1c46ce4c2b630cd1ace6 | 060a3650bb341606b4c115527c7e2aa8 |
| pos24 | 1151798991 | 03b7ac0628f500654c502986d89dced8 | 9f8a01d9d1987ad9674bcd6367f9ed1b | 461c20fdfce4608b16aa65ba27dc0b9b |
| pos25 | 1556492460 | b72efe4513caa0ed1ea55ca0f8f5fb3e | c4c975769443d32f083e5d7ff193d098 | 48cc58180386d794aaccc744740e891f |
| pos26 | 387918679 | 167ce05d1f577265ca10f5085710c454 | 8d6ff8172df3de3a61ea3b47c5087cfe | e463318742bd03b01baddfcda7e38681 |
| pos27 | 978392064 | b1a64d044c48d63deb8d667dfc262a1b | f4f056ec6676a1fd8b7396f064180697 | a971227c7bb484872b6c694f4aa689bb |

Sources: each episode's `runs/<bundle>.outer.log` (`scenario yaml md5`,
`overlay copied from ... (md5 ...)`). The seed-27 USD was built for this run
and removed again by `restore_v4` (it is absent from the VM snapshot).

### Evidence directories (gitignored, unreproducible paid output)

| Path (under `vgu-vlm-swarm-v6d/`) | Files | Key file md5 |
|---|---|---|
| `data/logs/vm_runs/v4_s1b_pc_shadow/` (931 MB) | 539 | `driver_smoke_20261113T073434Z.log` dd3c5cb9a173e282bea57da1aea5585f; `driver_follow_20261113T092551Z.log` 6041e92c1b3c9b2dd47aeee81fac91cd; `kit/manifest_v4.txt` 66c0f24ee282f76434ea4f9607ef1f32; `kit/kit_md5_v4.txt` 586a0e2a68c6d02bceabae0ca6157424; `kit/smoke_check_v4.py` 764d3b6826e292dbf9a9d2b4214256cd; `SMOKE_ACCEPTED` ae2f43f7f8bce42ae4ff22bad7a04a57 |
| `.../v4_s1b_pc_shadow/runs/v4pcs_pos{21..27}_armA_a1/` | 39 / 45 / 53 / 44 / 57 / 43 / 37 | per-episode `decisions/`, `trigger_trace_*.jsonl`, `m4.log`, `m5.log`, `gt/`, `frames/` |
| `data/logs/vm_runs/v4_s1b_pc_shadow_analysis/` | 4 | `analyze_stage1.py` f154028123cb5013bb808328f3dc2965; `stage1_summary_all.json` 97cba79a58bc77ef7f59ded8f6a75440; `real_summary.json` (smoke episode only) 8e262d73fd75d80059632440db1113bd |

---

## Results

### Per episode

| Episode | Analyses | Multi-group | Real dispatch | Withheld | No decision | GT min pair (m) | Est. $ (shadow $) | Billed calls |
|---|---|---|---|---|---|---|---|---|
| pos21 | 4 | 3 | 1 | 3 | 0 | 0.3069 | 0.0627 (0.0330) | 8 |
| pos22 | 7 | 0 | 1 | 6 | 0 | 0.2683 | 0.1040 (0.0584) | 14 |
| pos23 | 11 | 1 | 3 | 8 | 0 | 0.3942 | 0.1657 (0.0856) | 22 |
| pos24 | 6 | 0 | 1 | 3 | 2 | 0.3990 | 0.0977 (0.0513) | 13 |
| pos25 | 13 | 2 | 3 | 10 | 0 | 0.3907 | 0.2078 (0.1101) | 26 |
| pos26 | 6 | 4 | 3 | 2 | 1 | 0.2854 | 0.0888 (0.0447) | 12 |
| pos27 | 3 | 2 | 2 | 1 | 0 | 0.2151 | 0.0460 (0.0230) | 6 |
| **Total** | **50** | **12** | **14** | **33** | **3** | **0.2151** | **0.7727 (0.4061)** | **101** |

- "Real dispatch" is an artifact with `dispatched_command` and no
  `dispatch_withheld`. A withheld artifact keeps its would-be
  `dispatched_command`, but M4 never receives it. This was checked against M4:
  in every episode the set of request ids in `m4.log` `command received`
  lines equals the real-dispatch set, and no withheld request id appears.
- **pos24 billed 13 calls for 6 analyses.** The extra call is the one
  answered stage-2 M2 call of analysis `c0f78c5f` (`stage2.status`
  `answered`, with token usage); `cost_watch_v4.py` counts stage-2 usage.
  It is accounted for, not an untraced call.
- Spend is the last `cost.log` line of each episode (estimated from token
  usage at the kit's ER-2 rate, not from an invoice).

### Exit criteria

The design note lists six criteria and says "The thresholds are proposals for
the owner to set". `analyze_stage1.py` adds three proposals of its own.

| Criterion | Threshold | Observed | Status |
|---|---|---|---|
| Per-group parse validity after re-ask | >= 95 % (design-note proposal) with >= 20 calls (script proposal) | 50/50 (100 %); first attempt 50/50 | PASS |
| Artifact completeness | 100 % (design note) | 50/50, strict (no forgiven last-analysis `pending`) | PASS |
| Added worker latency measured | measured (no number set) | shadow median 8089 ms vs ordinary 8045 ms (see Results) | PASS (measured) |
| Joint-gate flag rates on live multi-group scenes | reported (no number set) | 12 multi-group blocks, every flag 0/12 | PASS (reported) |
| Section 2 branch settled | any Branch-2 case, or >= 3 Branch-1 cases with 0 indeterminate (script proposal) | 4 Branch-1, 1 indeterminate, 0 Branch-2 | **INSUFFICIENT** |
| About 10 multi-group analyses | >= ~10 (design note) | 12 | PASS |

- Parse validity is per call, not per group: one answer covers every group
  of an analysis.
- The latency criterion measures the shadow's own duration. Its effect on the
  ordinary loop is not isolated: the shadow runs on a separate worker after
  dispatch. As a cross-check, no shadow overlapped the next analysis. Over the
  43 consecutive analysis pairs, start plus ordinary latency plus shadow total
  stayed at least 4.1 s before the next `start_analysis` (computed from the
  trace `wall_t` and artifact timings for this report).

### Section 2: does a group-B-only event start an analysis?

- 19 unserved groups in multi-group analyses. 14 are not informative,
  because the ordinary loop dispatched nothing, so no first command was in
  flight. 5 were served later.
- **Branch 1 (4 cases):** the group was served only by a later scene-wide
  analysis, which started after the first command resolved. Delays: 13.0,
  13.17, 36.63 and 44.73 sim-s (pos25 `42b1b1f8`, pos26 `c0f80ada`, pos27
  `5d51cf8d`, pos26 `211d297b`).
- **Indeterminate (1 case):** pos23 `25d5a4e8`. A group-only analysis started,
  but only after the first command resolved (57.73 sim-s). The trace cannot
  tell whether it would have started earlier.
- Over all 5 served groups, the delay is median 36.6, p90 52.5, max 57.7
  sim-s. The first gate was `analysis_in_flight` in 4 and the busy gate in 1.
- **0 concurrent group-only starts.** The design note's Branch 2 was never
  observed. With 4 clean Branch-1 cases and one indeterminate, the
  script's proposal is not met, so the branch is not settled.
- **Trace limits:** a `SUPPRESSED` event cannot separate the busy gate from
  cooldown or frame-not-ready. Silent detector gaps (a group not yet
  stalled) leave no event. The trace has no dispatch lines, so "served" needs
  the later analysis's own artifact.

### Shadow versus the ordinary decision

- Where the ordinary loop really dispatched (n = 14), the shadow's choice
  included the live action in 2/14, and every shadow choice equalled live in
  1/14. Relations: same robots, other action 10; same action 2; untouched 4;
  none feasible 3. The categories overlap across slots.
- In the 5 multi-group analyses with a live dispatch, live left a group
  unserved in 5/5, and the shadow selected an action for that group in 4.
- `none_feasible` per slot: slot A 7/50, slot B 3/12.
- The shadow's choices were never executed. Whether they would resolve
  anything is untested.

### Safety

- Floor armed in 7/7 (smoke check `CHECK floor PASS armed=True`), 0
  `hard_contact_floor` stops, GT minimum pair distances 0.2151-0.3990 m
  (threshold 0.18 m).
- `kit/smoke_check_v4.py` printed `SMOKE_V4 PASS` on all 7 bundles. One WARN:
  pos25's ordinary latency (n=13, p50 8719, p95 11040, max 18319 ms) exceeds
  the tranche-1 Arm A max (12004 ms).

---

## Corrections

### Tranche-1 dispatch counts

The tranche-1 report (`docs/reports/2026-10-21-s1b-confirmatory-tranche1.md`,
§4 table, lines 292-300) gives "Analyses: dispatched / not dispatched" as 9/2,
4/0, 5/0, 5/0 and 3/0. Its note at line 303 says "A refused yield degrades to
`temporary_wait` and is still dispatched". The smoke check at acceptance
printed the same 9/4/5/5/3 as "dispatched"
(`driver_smoke_20261113T073434Z.log` line 803).

Under `refusal_no_action` this is not what reached M4. A withheld artifact
keeps the would-be `dispatched_command`, as already noted in the 2026-10-09
gotcha of `docs/implementation_notes.md`. The corrected per-episode counts
for E27-E31 Arm A are:

| Episode | Analyses | Real dispatch | Withheld (`dispatch_withheld`) | Old "dispatched" |
|---|---|---|---|---|
| E27 | 11 | 5 | 4 | 9 |
| E28 | 4 | 2 | 2 | 4 |
| E29 | 5 | 2 | 3 | 5 |
| E30 | 5 | 1 | 4 | 5 |
| E31 | 3 | 2 | 1 | 3 |

**How it was verified.** The corrected `smoke_check_v4.dispatched()` (lines
83-87) separates real from withheld. Independently, for this report, each
E27-E31 Arm A bundle's `m4.log` was read (`vgu-vlm-swarm-v3/data/logs/vm_runs/batch6/s1b_E*_seed*_armA_er2_confT1_a1`,
read only). The request ids in `command_bus_node` `command received` lines
are exactly the real-dispatch set (5/2/2/1/2), and none of the withheld ids
appear.

The tranche-1 confirmatory measures do not use this column, so this is a
descriptive correction to that table only. The tranche-1 report itself is not
edited here.

### Numbers that differ from the session brief

- The 36.6 sim-s median delay is over all 5 served groups (4 Branch-1 plus 1
  indeterminate). The 4 Branch-1 cases alone have median 24.9 sim-s (computed
  from the four listed delays).
- The pos24 "13 billed calls for 6 analyses" is the stage-2 call above, not an
  untraced call.

---

## What This Does Not Show

- **No per-group dispatch.** Stage 1 cannot show that per-group choices
  resolve anything, or that the joint gate is sufficient. The 0/12 flags are
  on shadow choices that never moved a robot.
- **Never exercised:** overlapping Gemini calls (no shadow overlapped the next
  analysis), the backlog / `skipped` path (`max_backlog: 2`, 0 skips), shadow
  timeouts, parse failures, and re-asks (all first attempts valid).
- **Section 2** is open (above).
- **Scene coverage:** 7 seeds of one 5-robot scene. 12 multi-group analyses
  came from 5 of the 7 episodes.
- **Ordinary-loop invariance** live is supported only indirectly: latency
  within range except one outlier, and dispatch counts within the tranche-1
  range. The offline invariance test is in the 2026-11-13 Stage 1 build entry
  of `docs/implementation_notes.md`.
- **No task-level outcome** is reported or claimed. The episodes are not
  scored for throughput. Why the scene does not resolve is in
  `docs/reports/2026-11-13-s1b-grounding-bottleneck.md`.

---

## Reproduction

```bash
cd /Users/tuanhdangdinh/Documents/vgu-vlm-swarm-v6d/data/logs/vm_runs
python3 -I v4_s1b_pc_shadow_analysis/analyze_stage1.py v4_s1b_pc_shadow/runs --json-out <scratch>/stage1.json
for p in 21 22 23 24 25 26 27; do python3 -I v4_s1b_pc_shadow/kit/smoke_check_v4.py v4_s1b_pc_shadow/runs/v4pcs_pos${p}_armA_a1; done
```

- The re-run JSON equals `stage1_summary_all.json` except the `path` field
  (relative vs repo-relative).
- `--json-out` must point outside `data/`. The script's default writes next
  to itself.
- `smoke_check_v4.py` reads the tranche-1 baseline from the `vgu-vlm-swarm-v3`
  checkout (read only).

---

## References

- Design note: `docs/superpowers/specs/2026-11-12-per-cluster-live-path-design.md` (§2 branches, §5 Stage 1).
- Runbook: `docs/guides/v4_s1b_pc_shadow_runbook.md`.
- Build entry: `docs/implementation_notes.md`, 2026-11-13 Stage 1 build.
- Bench result motivating the lever: `docs/reports/2026-11-12-v4-per-cluster-choice.md`.
- Why S1b does not resolve: `docs/reports/2026-11-13-s1b-grounding-bottleneck.md`.
