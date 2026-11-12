# v4 Stage 1 Per-Cluster Shadow: S1b Cell Runbook

**Prepared:** 2026-11-13

**Revision history:**

- Initial draft: pre-flight, deploy with import check, floor swap and arm gates, smoke acceptance, episode chain, pull, VM stop, wall-clock cap. Not run.

---

## Scope

- **What this is.** The operator steps for the Stage 1 live shadow cell of
  `docs/superpowers/specs/2026-11-12-per-cluster-live-path-design.md`
  (Section 5). It has **not been run**. A review must approve it, and the
  owner must rule on the open items below, before any VM time.
- **Exploratory only.** Not a prereg-v3 cell. Its bundles never pool with
  A32-A36. The shadow is a second billed M2 call per analysis.
- **What changes in the run.** Nothing that reaches M4. The ordinary
  analysis dispatches as in tranche 1. After it, M5 runs the per-group call on
  its own worker and writes the result into that analysis's decision
  artifact as `per_cluster_shadow`. With the shadow on, M5 also writes
  `trigger_trace_<session_id>.jsonl` beside the artifacts.
- **Where the kit lives.** VM kits stay untracked under
  `data/logs/vm_runs/<batch>/` (the tranche-1 kit is
  `data/logs/vm_runs/batch6/p10/` in the `vgu-vlm-swarm-v3` checkout, with
  `NOTES_vm_b6.md`). This tracked page is the source the new kit's notes copy.

---

## Inputs

| Item | Value |
|---|---|
| Overlay, seed position 1 | `config/overlays/v4_s1b_pc_shadow/orch_seed1.yaml` |
| Overlay delta (other seeds) | `config/overlays/v4_s1b_pc_shadow/pc_shadow_delta.yaml` |
| Base it was made from | p10 `overlays/s1b_shield_escort_orch_seed1.yaml` md5 d55cf3373d2712e6e3e33d2be2fa19e5 |
| Grounding (unchanged) | `config/grounding/s1b_dynamic_shield_escort.yaml` md5 409688866d25289309e081dcb9433037 |
| Classical params (grouping radius) | `config/rag.yaml` md5 e18c723cff9cada3f320d564c2ecee5a, `r_conflict_m` 1.5 |
| Backend | `gemini` (ER-2, `force_schema: false`); shadow inherits 2 attempts x 120 s |
| Safety floor | p10 `floor_p10.sh` (pristine 598396622ca50baddc3e19b4608fa3e3, floor c41913f02cf4e988162c30a44a5dda04) |

An overlay for seed k is p10's `s1b_shield_escort_orch_seed{k}.yaml` with
exactly two changes: line `keep_debug_frames: false` becomes `true`, and the
non-comment lines of `pc_shadow_delta.yaml` are appended. A
comment-stripped diff against the base must show exactly those two hunks.
Which seeds the cell uses is an owner ruling. The positions after the
confirmatory first 20 are the natural choice, so no confirmatory seed is
spent.

---

## Required Kit Changes (Not Made Here)

`scripts/vm` and the p10 kit were not edited. A new kit derived from p10
needs these changes:

1. **Collector: the trace.** `ep_run_p10.sh` lines 205-218 copy only
   `m5_decisions/*.json` and `tasks_*.jsonl` files that contain
   `"run_id": "<STAMP>"`. The trace is named `trigger_trace_*.jsonl`, so it is
   not copied. Add `trigger_trace_${SESSION_ID}.jsonl` next to the
   `tasks_${SESSION_ID}.jsonl` copy. Every trace line carries
   `"run_id": "<STAMP>"` in default `json.dumps` spacing.
2. **Collector: frames.** No change needed. Lines 226-230 copy every
   `m5_frames` file newer than the overlay copy. Tranche-1 `frames/` was empty
   because every Arm A overlay set `keep_debug_frames: false` (line 63), not
   because of the collector.
3. **Shadow block.** No change needed. The block sits inside
   `<request_id>.json`, which already carries the run id. `cond_p10.py` counts
   the same artifacts as before. No new `*.json` file is written; the
   temporary file of the in-place replace is `<request_id>.json.tmp`.
4. **Cost guard.** `cost_watch.py` reads only each artifact's `diagnostics`
   usage, so it does not see shadow spend. Add
   `per_cluster_shadow.m2.attempt_token_usage` to its sum, or halve `CAP_EP`.
   Without one of these, the dollar guard undercounts by about one call per
   analysis.
5. **Pins.** The kit's `pins_ok`, manifest and deploy gates must list the new
   runtime files (next section) at this branch's commit, not tranche-1's.
6. **Stale-loader guard.** `OrchestratorConfig` ignores unknown keys. A
   runtime without this build would therefore run the overlay as a plain
   Arm A episode. The per-episode arm check (`ep_run_p10.sh` line 128 analogue)
   must assert `per_cluster_shadow.enabled is True` and
   `keep_debug_frames is True` through the deployed loader.

---

## Runtime Files to Deploy

Changed since the tranche-1 runtime (`git diff --name-only 68e67b5 HEAD --
reasoning ros2_ws`). The kit builder records their md5s at its commit.

- **Live mount (`/ws`, no build):**
  - `reasoning/rag/cluster_options.py`
  - `reasoning/rag/grounding_provenance.py`
  - `reasoning/rag/joint_check.py`
  - `reasoning/vlm/__init__.py`
  - `reasoning/vlm/backend_factory.py`
  - `reasoning/vlm/executable_options.py`
  - `reasoning/vlm/per_cluster_choice.py`
  - `reasoning/vlm/per_cluster_runner.py`
  - `reasoning/vlm/reasoner.py`
- **Colcon (`swarm_orchestrator`, purge build/install first):**
  - `models.py`
  - `orchestrator_node.py`
  - `per_cluster_shadow.py` (new)
  - `reasoning_pipeline.py`
  - `trigger_trace.py` (new)
  - `config/orchestrator.yaml`: default-off block only. The episode overlay
    replaces it whole, so this file never decides the cell.

---

## Steps

Each step's sentinel must print before the next. Any FAILED, MISMATCH or
ABORT stops the run, and then the stop step (step 9) runs.

0. **Pre-flight (Mac, no VM).**
   - Gemini credit probe: one minimal text call on the cell's key. Stop if it
     answers 429 quota or the monthly cap. The cap was hit on 2026-10-23.
   - VM state: `gcloud compute instances describe <vm> --zone <zone>
     --format='get(status)'`. It must print `TERMINATED`; note the zone.
   - Record the wall-clock start. The cap is owner-set; proposed: 8 h from
     VM start to `TERMINATED`.
1. **Start VM** (`gcloud compute instances start ...`). Re-read the
   ephemeral IP. Wait for `vgu_ros`.
2. **Record the deployed state and the restore path.** Before copying
   anything:
   - md5 every file in the deploy list, in both the host repo and the
     colcon install;
   - md5 the installed `safety.yaml`, `orchestrator.yaml` and `rag.yaml`;
   - back up the host repo files that will be overwritten into
     `~/v4s1/deploy/pre/`.

   The restore path is: copy the backups back, purge and rebuild
   `swarm_orchestrator`, and re-check the md5s.
3. **Deploy.**
   - Untar the delta into the host repo.
   - Purge and rebuild `swarm_orchestrator`
     (`colcon build --merge-install --packages-select swarm_orchestrator`).
   - Check installed == source for every row.
4. **In-container import check (before any Isaac launch).** Inside
   `vgu_ros`, with the run's environment, run:

   ```bash
   python3 -c "
   import yaml
   from swarm_orchestrator import orchestrator_node, per_cluster_shadow, trigger_trace
   from swarm_orchestrator.models import load_config, resolve_layer2_gate
   from reasoning.vlm import build_per_cluster_backend
   from reasoning.vlm.per_cluster_runner import run_per_cluster_choice
   from reasoning.rag.cluster_options import generate_cluster_candidates
   from reasoning.rag.joint_check import joint_check
   c = load_config(yaml.safe_load(open('<overlay>')))
   assert c.per_cluster_shadow.enabled and c.keep_debug_frames
   assert resolve_layer2_gate(c).per_cluster_shadow
   print('SMOKE PC_SHADOW imports ok shadow', c.per_cluster_shadow.enabled)
   "
   ```

   The `swarm_orchestrator` import must come from the colcon install, and
   the `reasoning` imports from `/ws`; print both modules' `__file__` and
   check the md5s against step 3.
5. **Floor swap and pre-arm gate.** Run the p10 `floor_p10.sh` analogue and
   require `FLOOR INSTALLED OK`, with the installed `safety.yaml` at
   c41913f0. The pinned source `safety.yaml` (59839662) is swapped only for
   the run, never edited in git. Before every episode, the pin gate re-checks
   installed `safety.yaml` == c41913f0.
6. **Smoke episode (one seed).** Acceptance, all required:
   - **Floor (post-arm gate):** `m4.log` has `Safety monitor started .*
     hard_contact_floor_m=0.2`. No `hard_contact_floor` stop, and no GT pair
     below 0.18 m.
   - **Frames:** `frames/` holds `<request_id>.png` for every artifact.
   - **Artifacts complete:** every `decisions/<request_id>.json` has a
     `per_cluster_shadow` block whose status is not `pending`. Count each of
     `ok`, `parse_failed`, `timeout`, `error` and `skipped`.
   - **Trace:** `trigger_trace_*.jsonl` is present, with one
     `start_analysis` line per artifact.
   - **Added latency:** from each block, `timings.total_ms` and
     `m2.latency_ms`. Offline on the 187 items, enumeration plus grounding
     took p50 20 ms, p95 69 ms and max 141 ms on the Mac. The M2 call
     dominates.
   - **Ordinary loop unchanged:** analysis latency and dispatch counts are in
     the tranche-1 Arm A range. The m5 log has no `per_cluster_shadow ...
     submit failed`.
7. **Chain N episodes.**
   - **Sizing:** in the 187 recorded items, the five tranche-1 Arm A bundles
     (E27-E31) had 0, 0, 1, 3 and 2 analyses with two or more slots, a mean of
     1.2 per episode. Pilot episodes E6-E26 ran higher and more variable (0 to
     39). Reaching the Stage 1 exit of about 10 multi-group analyses takes
     about 8-9 episodes at the tranche-1 rate, against the design note's
     estimate of 4-6. The owner sets N, or a stop rule on the observed count.
   - **Gates** are the same as tranche 1: the pin gate before each episode,
     the floor and condition gates after. The budget gate includes shadow
     spend (kit change 4).
8. **Pull.** Restore pristine safety (`RESTORE PRISTINE OK`) and the
   pre-deploy runtime (step 2 backups, md5 re-check). Then `rsync -a`,
   **never `--delete`**, the bundles, kit logs and notes to the Mac.
9. **Stop the VM on every exit path.** Run `gcloud compute instances stop
   ...`, then `describe` until `status` prints `TERMINATED`, and log it. Do
   this after success, after any gate failure, and when the wall-clock cap
   is reached. The chain driver should hold this in an EXIT trap.

---

## Reading the Results

- **Per-group parse validity:** the share of blocks with
  `m2.parse_status` `valid` or `invalid`, out of every block that made a
  call.
- **Joint-gate flag rates on multi-group scenes:**
  - `joint_exact_conflict` and non-empty `joint_check.path_proximity`, over
    blocks with `n_slots >= 2`;
  - offline with the first option in every group, these were 6 of 85 and 10
    of 85.
- **Section 2 branch:** look for `event` lines with `directive` equal to
  `start_analysis` and `disjoint_from_busy: true`. Each one is an analysis
  started on robots disjoint from every in-flight command. Group them by the
  in-flight command's robots.
- **Frames:** the kept frames lift the bench's text-only limit for later
  replays.
