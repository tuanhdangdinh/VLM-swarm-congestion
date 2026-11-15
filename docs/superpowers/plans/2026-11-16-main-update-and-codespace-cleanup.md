# Main Update and Codespace Cleanup Plan

**Prepared:** 2026-11-16

**Revision history:**

- Initial draft: owner decisions, frozen branch tips, staged execution steps, verification gates, cleanup inventory. Builds on the 2026-11-15 consolidation plan; nothing has been changed yet.
- Rev 3 (2026-11-16): additions from session vgu-vlm-swarm-34, sent with the owner's consent: archive tag for the old `main`; "merged as it stands, not reviewed" wording; preservation of the dirty June worktree's uncommitted changes (Step 0.0).
- Rev 2 (2026-11-16): contact-logging key moved after Stage 5 (three frozen tips carry the logging), kit key-on via overlay fragment, archive SHAs frozen, exact end-state checks, per-key default-off check, baseline uses `make test`'s `pytest`.

---

## Purpose

`main` (`f2ca3c6`, 2026-09-19) is two months stale. Every November line lives on separate branches, about 80 worktrees exist, and some local material is on no branch. This plan brings `main` up to date with the November work listed in the Frozen Inputs table, merged as it stands. The owner has not reviewed this work (it was pushed on 2026-11-16 as a plain backup), so the consolidation is not a record of review, archives the older lines, and lists the remaining clutter for a later owner decision.

The source for branch contents, dependency order and pairwise conflicts is the consolidation plan: `docs/superpowers/plans/2026-11-15-branch-consolidation.md` on `demo/campaign-kits` (Rev 3, sections 3 and A.1–A.4). This document does not repeat it. It records the owner's rulings, freezes the inputs, and adds the steps and checks needed to execute.

## Owner Decisions (2026-11-16)

| Question | Ruling |
|---|---|
| What goes into `main` | Full staged merge on a new `integration/2026-11` cut from the pin `68e67b5`, then fast-forward `main` to it |
| `feat/gt-contact-logging` (not default-off) | Lands behind a new config key, default off |
| `docs/thesis` | Stays a separate branch; not merged into `main` |
| Older branches in no stage | Archived as `archive/<name>` tags; kept out of `main` |
| Untracked `reports/`, `research_notes/`, `uv.lock` in the primary checkout | Committed to the integration branch |
| Tag for the pin `68e67b5` | Yes: annotated tag `prereg-v3-pin`, pushed |
| Worktree and branch cleanup | Deletion list only; nothing is removed without separate approval |

Rules that still apply (from the consolidation plan A.4 and the experiments session): new safety mechanisms stay default-off; pinned configs (`orchestrator.yaml`, `rag.yaml`, `safety.yaml` md5 `598396622ca50baddc3e19b4608fa3e3`) are not edited except for default-off additions; frozen evidence branches are merged, never rewritten; no force-push; no `.env` or keys; commits follow repo CLAUDE.md (Conventional Commits, subject only, no trailer).

## Preconditions

1. Session `vgu-vlm-swarm-34` reports that the evidence upload (release `evidence-2026-11-16`) finished and was verified. Until then only read-only checks run, and no full test suite.
2. No heavy job is running in another session. One pytest process at a time; free disk at least 7 GiB (9.2 GiB at writing).
3. Branch tips are unchanged from the table below. If a tip moved, refresh the table before starting that stage.

## Frozen Inputs

Merged by SHA, not by branch name. All match `origin/` except `feat/v4-per-cluster`, which is one commit ahead locally. That local tip `48234f2` is an ancestor of parity `105fff4` (verified), so nothing is lost.

| Stage | Branch | Tip |
|---|---|---|
| base | pin (`feat/v3-integration`) | `68e67b5` |
| 1 | `fix/safety-exemption-scope` | `8933863` |
| 2 | `feat/ib10-live-resolution` | `5f098b7` |
| 2 | `feat/ib10-safety-default-arm` | `dead48d` |
| 3 | `docs/head-on-vlm-vs-rule` | `1f77bf1` |
| 3 | `docs/vlm-plan-influence-trace` | `1400533` |
| 3 | `demo/ib10-recorded-demo` | `64e9b83` |
| 3 | `feat/convoy-live-resolution` | `5c7bf22` |
| 3 | `exp/head-on-swapped-id-replay` | `abc28fe` |
| 3 | `exp/head-on-json-only-replay` | `29696f9` |
| 4 | `fix/escort-obstacle-guard` | `92158d3` |
| 4 | `feat/gt-contact-logging` | `b5eaee5` |
| 4 | `fix/m4-stall-abort` | `1016e0b` |
| 4 | `fix/plan-dispatch-mismatch-visibility` | `93655fc` |
| 5 | `demo/vlm-order-channel` | `52aea51` |
| 5 | `demo/campaign-kits` | `52b4275` |
| 5 | `analysis/failure-cause-classification` | `0b6a91b` |
| 5 | `demo/validation-guard-contacts` | `a412949` |
| 5 | `test/safety-mechanisms-scripted` | `74dd45c` |
| 5 | `fix/convoy-hold-queued-robots` | `d85d1ed` |
| 5 | `fix/convoy-yielder-feasibility` | `272ad4a` |
| 6 | `feat/demo-panel-renderer` | `51d9b1a` |
| 7 | `feat/v4-gf-cluster` | `c16b1a7` |
| 7 | `feat/v4-vlm-bench` | `7850f5a` |
| 7 | `feat/v4-per-cluster` | `48234f2` |
| 7 | `feat/v4-per-cluster-parity` | `105fff4` |
| 7 | `feat/v4-refusal-feedback` | `384e948` |
| 8 | `fix/deadlock-collision-resolution` | `fc73151` |
| 8 | `feat/v3-design` | `ad67a18` |

Not merged: `docs/thesis` (`bdf3bab`, owner ruling), and the archived branches in Step 11.

## Execution Steps

### Step 0 — Workspace and Baseline

0. Preserve the uncommitted June changes before anything touches that worktree. Done read-only on 2026-11-16: `git -C .claude/worktrees/m4-phase2-nav2-stack diff` saved as `m4-phase2-nav2-stack-uncommitted-2026-11-16.patch` (423 lines, 6 files) in the session scratchpad. Owner ruling (2026-11-16): commit it on a side branch `wip/m4-watchdog-forward-stop-2026-06` created from `bb22915` in a new worktree, add that branch to the Step 11 archive tags, and keep it out of `main`. Do not commit, stash or reset in that worktree. The untracked session-transcript `.txt` there is listed, never committed.
0b. Safety net: write `git bundle create <scratchpad>/refs-2026-11-16.bundle --all` (about 100 MB), so every ref can be restored exactly as it was today, even after local deletions.
1. Tag the old `main`: `git tag -a archive/main-2026-09-19 f2ca3c6 -m "main before the 2026-11 consolidation"`. Once `main` moves forward, going back would need a force push, so the tag keeps the old tip findable.
2. Tag the pin: `git tag -a prereg-v3-pin 68e67b5 -m "prereg-v3 runtime pin"`. Push it after the owner's go (Step 12).
3. Create the integration worktree from the pin with `git worktree add ../vgu-vlm-swarm-int -b integration/2026-11 68e67b5`. Use plain git, not the native worktree tool. Reuse the primary checkout's `.venv` (no disk for another); `colcon` builds are not needed for the unit gates.
4. Capture the test baseline **by test ID** on the pin, with the same command `make test` runs (plain `pytest` from the repo root): `pytest -p no:cacheprovider -q -rfE`, written to the session scratchpad, not the repo. Extract the failing and erroring node IDs into a sorted ID file. Expected: the known 57 failures plus 3 `pxr` collection errors. Every later gate compares ID sets, not counts.
5. Run the four suites still pending, one at a time, at their tips: `fix/plan-dispatch-mismatch-visibility`, `fix/convoy-yielder-feasibility`, `test/safety-mechanisms-scripted`, `fix/m4-stall-abort`. Record each failing-ID set. A failure that is not in the baseline blocks that branch's stage until explained.
6. Cumulative dry run. The consolidation plan's checks are pairwise only. Replay the whole stage order with `git merge-tree --write-tree` chained on the previous result tree (no refs written), and list every conflicting path per step. Compare with the plan's expected conflicts, and report any new conflict to the owner before Stage 1.

### Steps 1–8 — Staged Merges

Follow the consolidation plan sections 3 and A.3 in this order, with Step 9 inserted between Stage 5 and Stage 6: Stage 1 → 2 → 3 → 4 (guard → contact logging → stall abort → mismatch record) → 5 (order channel → campaign kits → failure classification → validation take → scripted safety tests → queued-robot hold → yielder correction) → 6 → 7 (gf-cluster → vlm-bench → per-cluster → parity → refusal feedback) → 8 (W, then `feat/v3-design`).

For every merge:

- `git merge --no-ff <SHA>` with subject `chore: merge <branch> into integration`.
- Resolve `docs/implementation_notes.md` by keeping both sides' bullets, newest first.
- Resolve the real conflicts as the plan prescribes:
  - `orchestrator_node.py` at the mismatch record (Stage 4);
  - the four-file refusal-feedback conflict and the `reasoning_pipeline.py` conflicts with the hold and the mismatch record (Stage 7);
  - `prereg-v2-design.md` (Stage 8): keep both amendments, do not reword frozen sections;
  - `.gitignore` (Stage 7): keep both sides' lines;
  - the IB10 results report (Stage 5): take blob `c3151bc1e3`.
- Hand resolutions of runtime code get a review subagent that reads both features' diffs before the merge commit is made.

Gate after each stage (not each merge, except where the plan names one):

- The unit tests the plan lists for that stage.
- The full unit suite, compared by ID with the baseline. The failing set must not grow, and the 3 `pxr` errors stay identical.
- `git diff 68e67b5 -- ros2_ws/src/swarm_execution/config/safety.yaml` is empty, and `orchestrator.yaml` / `config/rag.yaml` differ only by default-off blocks.

### Step 9 — Contact Logging Behind a Key

One new commit on `integration/2026-11` **after Stage 5**, not after Stage 4. Contact logging enters with `feat/gt-contact-logging` (`b5eaee5`, Stage 4) and again with `demo/validation-guard-contacts` (`a412949`) and `test/safety-mechanisms-scripted` (`74dd45c`), both Stage 5; their tests assume the fields exist. No later frozen tip changes `acceptance_logging.py` or the contact tools (checked with `git diff --name-only 68e67b5 <SHA>`). Through Stages 4 and 5 the logging is therefore always-on on the integration branch, as on those branches; the gates there compare against that state. Do not rewrite the pushed branch.

- Add a key (proposed name `gt_contact_logging.enabled`, default `false`) that gates the contact computation in `isaac/vgu_sim/acceptance_logging.py`. Key off: GT rows are field-identical to the pin, with lists hard-coded `[]` as before.
- Key on for the runs that already used it (the five-robot validation take, the scripted safety-test kit `sft`) through a new overlay fragment, for example `config/gt/contact_logging_on.fragment.yaml`, in the same way as the other mechanisms. Do not edit the registered kit files: their md5s are cited in reports. If a kit cannot pick up a fragment without an edit, stop and ask the owner.
- Make the branch's tests, `test_recompute_gt_contacts.py` and the recompute tool set the key explicitly. Add one test that key-off output equals the pin's row schema.
- `_assert_no_static_contacts` in `tests/simulation/test_m6_scenarios.py` stays trivial when the key is off; note that in the test.
- Add an implementation-notes entry: the evaluated experiment runs (`68e67b5`) never had contact logging; the key exists so reruns stay comparable.

### Step 10 — Untracked Material

On the integration branch, after Stage 8:

1. Secret scan of `reports/`, `research_notes/` and `uv.lock`: grep for key patterns, then read every hit.
2. Move each `reports/<Title>.md` into `research_notes/<Title>/` beside its folder where one exists. Otherwise keep it under `research_notes/`.
3. Commit as `docs: add research notes from local workspace` and `chore: track uv lockfile`. `uv.lock` is tracked for reproducibility only; `make` stays the documented path, per CLAUDE.md. Checked: the local `uv.lock` is byte-identical to the one on `origin/wip/untracked-local-state`, and `pyproject.toml`/`requirements*.txt` are identical between the pin and W. Re-check against the final integration tree's `pyproject.toml` before committing.

### Step 11 — Archive Tags

Annotated tag `archive/<branch>` at the frozen SHA; branches are not deleted. Where a local and a remote branch both exist they were 0/0 at writing; re-check before tagging. The `worktree-m4-phase2-nav2-stack` worktree is dirty: list its uncommitted changes for the owner, do not commit them.

| Branch | Tip | Where | Unique commits | Content |
|---|---|---|---|---|
| `prereg-v1-hotfix` | `3988524` | local = remote | 6 | VLM code and tests (v1 hotfix) |
| `feat/v3-vjepa-probe` | `53a4b78` | local only | 6 | V-JEPA pilot scripts and report |
| `feat/trail-probe-pilot` | `cb1c171` | local only | 4 | trail-probe pilot script and report |
| `feat/prereg-v2-composite` | `dd5f93c` | local = remote | 1 | VM recorder fix |
| `feat/robot-order-counterbalance` | `d20cc97` | local = remote | 1 | counterbalance pre-registration |
| `m1-isaac-camera-wiring` | `8e8e1ca` | local = remote | 1 | spec and plan docs |
| `claude/laughing-volta-fwnqvs` | `df720f0` | remote only | 2 | audit finding A15 |
| `wip/untracked-local-state` | `4224645` | local = remote | 2 | reports and a lockfile snapshot |
| `worktree-m4-phase2-nav2-stack` | `bb22915` | local = remote, dirty worktree | 35 | June M4 Nav2 stack line |
| `probe/shutdown-timing` | `8da4964` | local only | 0 | already contained elsewhere; tag for findability only |

Add a short "History and archived lines" section to `README.md` that lists these tags plus `archive/main-2026-09-19`, says the 2026-11 consolidation merged branches as they stood (not a review), and points to `docs/thesis` and the `evidence-2026-11-16` release.

### Step 12 — Publish (Needs the Owner's Explicit Go)

1. Show the owner:
   - the final failing-ID diff against the baseline (must be empty or explained);
   - the list of resolved conflicts;
   - `git branch -a --no-merged integration/2026-11`, which must list exactly `docs/thesis` and the ten branches in the Step 11 table (local and `origin/` copies). Any other name is a gap and blocks the push;
   - a per-key default-off check, by `git grep` of the default in code and in every tracked config: `scoped_clearing_exemption`, the escort and reverse obstacle guards, `safety.stall_abort.enabled`, `plan_dispatch_mismatch_visibility`, `grounding_hold_queued_crossers`, `grounding_yield_counterflow_swap`, `per_cluster_shadow.enabled`, the order-channel prompt rules, the refusal-feedback keys, and the new contact-logging key. Each must be off;
   - default prompt rendering byte-identical to the pin (the existing `test_*renders_byte_identically_to_default` tests pass).
2. On the owner's go:
   - push `integration/2026-11` and the tags `prereg-v3-pin`, `archive/main-2026-09-19` and `archive/*`;
   - fast-forward `main` in its worktree (`vgu-vlm-swarm-v7e`) with `git merge --ff-only integration/2026-11`;
   - push `main`.
3. Check: `origin/main` equals `integration/2026-11`; `prereg-v1`, `prereg-v3-pin`, `archive/main-2026-09-19`, `thesis-long-2026-11-15` and `evidence-2026-11-16` all still resolve.
4. Add an implementation-notes entry for the consolidation. It states that the work was merged as it stands and is not a record of review. It records that full unit suites were pending on four branches until Step 0.5, and that three mechanisms are validated only as the 2026-11-15 wrap-up index states: the reverse obstacle guard and the stall abort ran live once, in a scripted safety test; the escort obstacle guard and the convoy yielder correction were checked offline only. The integration merge commit subjects and the README history section carry the same "as it stands, not reviewed" note.

## Cleanup Inventory (List Only)

Written after Step 12, as `docs/reports/2026-11-16-cleanup-candidates.md`. Nothing is deleted. For each worktree it records:

- branch;
- whether the branch is contained in `main` or a pushed tag;
- whether the tree is clean;
- the size of its git-ignored `data/`, and whether that data is in the `evidence-2026-11-16` release (checked against the release asset manifest, not assumed).

Proposed buckets:

- **Safe once approved:** clean worktrees whose branch is in `main` or an archive tag, and whose `data/` is empty or released. This covers most of `v3a`–`v5e` and the `.worktrees/` entries.
- **Held for the owner's decision:** `.claude/worktrees/m4-phase2-nav2-stack`, until the owner rules on its uncommitted changes. It is never in the safe bucket before that.
- **Needs a look:** worktrees with unreleased `data/` (for example `vgu-vlm-swarm/data/logs` 6.2 G and `vgu-vlm-swarm-v3/data/logs` 5.9 G, if not in the release), dirty trees, and the Warp and Conductor entries.
- **Keep:** `vgu-vlm-swarm-thesis` (a1's working tree), `v7e` (`main`), the integration worktree, and the primary checkout.
- **Local branches** already in `main` or archived: listed for deletion. Remote branches merged into `main`: listed separately.

Primary-checkout strays for the same list:

- `tmp/` (1.5 M of June helper scripts and video checks);
- `simulation_requirements.md` at the root;
- `.DS_Store`;
- the `.claire`, `.codex` and `.conductor` tool directories.

`state/` holds keys and stays local and ignored; it is never listed for push.

## Where This Plan Lives

This file is written in the primary checkout and stays uncommitted until Step 0. It is then committed on `integration/2026-11`, not on W, so W's frozen tip `fc73151` does not move.

## Left to the Executor

- The exact key name and config location for Step 9, consistent with the other default-off keys.
- How to split the integration work across subagents. Fable sessions plan and review only; code, tests and merges run in sonnet/opus subagents, one heavy job at a time.
