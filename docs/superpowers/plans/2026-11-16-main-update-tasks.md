# Main Update and Codespace Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fast-forward `main` to a new `integration/2026-11` that holds all November work merged as it stands, with old lines archived as tags and nothing lost.

**Architecture:** All work happens in a new worktree `~/Documents/vgu-vlm-swarm-int` on `integration/2026-11`, cut from the pin `68e67b5`. Branches are merged by frozen SHA in stage order, with a test-ID gate after each stage. Nothing is pushed until the owner's explicit go in Task 10.

**Tech Stack:** git (worktree, merge-tree, bundle, tags), pytest via the primary `.venv`, Python 3 for the one code change.

**Spec:** `docs/superpowers/plans/2026-11-16-main-update-and-codespace-cleanup.md` (Rev 3, owner-approved 2026-11-16). Executors read both. The spec's Frozen Inputs table and the 2026-11-15 consolidation plan on `demo/campaign-kits` (sections 3, A.1–A.4) are the source for SHAs, stage order and expected conflicts.

## Global Constraints

- Start only after session `vgu-vlm-swarm-34` sends the upload-verified message for release `evidence-2026-11-16`.
- One pytest process at a time, never parallel workers (`-n`). Free disk ≥ 7 GiB before each suite run (`df -h /Users`).
- No force-push. No push of any kind before Task 10's owner go.
- Commits: Conventional Commits, subject only, under 72 chars, no body, no Co-Authored-By trailer (repo CLAUDE.md).
- Never commit `.env`, `state/`, keys, or session-transcript `.txt` files.
- Never commit, stash, reset or checkout inside another session's worktree (`v7j`, `vgu-vlm-swarm-thesis`, `.claude/worktrees/m4-phase2-nav2-stack`, any `v*`).
- Pinned files: `ros2_ws/src/swarm_execution/config/safety.yaml` md5 `598396622ca50baddc3e19b4608fa3e3`; `orchestrator.yaml` and `config/rag.yaml` may differ from `68e67b5` only by default-off blocks.
- Every new safety key stays default-off. Registered kit files and `data/experiments/` results are never edited.
- Merge commit subject: `chore: merge <branch> as it stands`.
- Scratch outputs (baseline files, dry-run logs) go to `/private/tmp/claude-501/-Users-tuanhdangdinh-Documents-vgu-vlm-swarm/3c0ee83d-c295-412c-9932-9ca95f1e0f00/scratchpad`, referred to below as `$S`. Durable backups go to `~/Documents/vgu-vlm-swarm-backup-2026-11-16/`, referred to as `$B`.

## Review Focus

1. **A tip moved after freezing.** Before each merge, `git rev-parse <branch>` must equal the frozen SHA. A mismatch stops the task and gets reported; never merge the new tip silently.
2. **Test IDs that change but keep the count.** The gate compares sorted ID sets. A fixed test plus a new failure is still a failure.
3. **Conflict resolution that silently turns a key on.** After every hand resolution, grep the resolved files for the feature keys and confirm their defaults are unchanged.
4. **Notes merge losing bullets.** After resolving `docs/implementation_notes.md`, the line count must be at least max(ours, theirs) minus overlap. Check it with `git diff --stat` against both parents.
5. **Disk running out mid-suite.** Check free disk before each suite. If it's under 7 GiB, stop and report; don't delete anything to make room.

---

### Task 1: Safety Net, Tags and the June Side Branch

**Files:**
- Create: `$B/refs-2026-11-16.bundle`, `$B/m4-phase2-nav2-stack-uncommitted-2026-11-16.patch`
- Create worktrees: `~/Documents/vgu-vlm-swarm-int` (`integration/2026-11`), `~/Documents/vgu-vlm-swarm-june` (`wip/m4-watchdog-forward-stop-2026-06`)

**Interfaces:**
- Produces: local tags `archive/main-2026-09-19` → `f2ca3c6` and `prereg-v3-pin` → `68e67b5`; branch `integration/2026-11` at `68e67b5`; branch `wip/m4-watchdog-forward-stop-2026-06` with one commit on `bb22915`.

- [ ] **Step 1:** `mkdir -p $B && git bundle create $B/refs-2026-11-16.bundle --all`. Then run `git bundle verify $B/refs-2026-11-16.bundle`. Expected: "is okay".
- [ ] **Step 2:** `cp $S/m4-phase2-nav2-stack-uncommitted-2026-11-16.patch $B/`. Then run `git -C .claude/worktrees/m4-phase2-nav2-stack diff | cmp - $B/m4-phase2-nav2-stack-uncommitted-2026-11-16.patch`. Expected: no output (identical).
- [ ] **Step 3:** Create the annotated tags `archive/main-2026-09-19` and `prereg-v3-pin` with the messages in spec Step 0. Then run `git rev-parse archive/main-2026-09-19^{} prereg-v3-pin^{}`. Expected: `f2ca3c6…`, `68e67b5…`.
- [ ] **Step 4:** `git worktree add ~/Documents/vgu-vlm-swarm-june -b wip/m4-watchdog-forward-stop-2026-06 bb22915`, then `git -C ~/Documents/vgu-vlm-swarm-june apply --index $B/m4-phase2-nav2-stack-uncommitted-2026-11-16.patch`. Then run `git -C ~/Documents/vgu-vlm-swarm-june diff --cached --stat`. Expected: 6 files, +216/−38.
- [ ] **Step 5:** Commit in the june worktree: `git commit -m "wip: preserve June watchdog forward-stop changes"`. Check that `git -C .claude/worktrees/m4-phase2-nav2-stack status --porcelain` is unchanged: 6 `M` and 1 `??`.
- [ ] **Step 6:** `git worktree add ~/Documents/vgu-vlm-swarm-int -b integration/2026-11 68e67b5`. Then run `git -C ~/Documents/vgu-vlm-swarm-int log -1 --format=%h`. Expected: `68e67b5`.
- [ ] **Step 7:** Copy both plan files from the primary checkout into the int worktree's `docs/superpowers/plans/`. Commit them as `docs: add main-update plan and task breakdown`.

### Task 2: Test Baseline and Pending Suites

**Files:**
- Create: `$S/baseline-pin.ids`, `$S/pending-<branch-slug>.ids` (four files), `$S/collect-ids.sh`

**Interfaces:**
- Produces: `$S/collect-ids.sh <worktree> <out.ids>`. It runs `pytest -p no:cacheprovider -q -rfE` in that worktree with the primary `.venv` and writes the sorted unique node IDs from the `FAILED`/`ERROR` summary lines. Every later gate uses this script.

- [ ] **Step 1:** Write `collect-ids.sh`. It activates `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm/.venv`, `cd`s into the worktree, runs the command above with output teed to `<out>.log`, and greps `^(FAILED|ERROR) ` into `<out.ids>` after `sort -u`.
- [ ] **Step 2:** Run it on `~/Documents/vgu-vlm-swarm-int` (at the pin) to get `$S/baseline-pin.ids`. Expected: 57 FAILED and 3 ERROR lines that name `pxr`. If the counts differ, record them; the set itself becomes the baseline.
- [ ] **Step 3:** Run it, one at a time, at the tips `93655fc`, `272ad4a`, `74dd45c` and `1016e0b`. Use a detached temporary worktree per tip (`git worktree add --detach $S/wt-<sha> <sha>`) and remove each with `git worktree remove` right after its run.
- [ ] **Step 4:** For each tip, run `comm -13 baseline-pin.ids pending-X.ids`. Expected: empty. Any line printed is a new failure: stop and report it with the test output. Its stage cannot proceed until the owner rules on it.

### Task 3: Cumulative Dry Run

**Files:**
- Create: `$S/dryrun.log`

- [ ] **Step 1:** In the int worktree, chain `git merge-tree --write-tree --name-only --no-messages <prev-tree-commit> <SHA>` through the spec's merge order (Stages 1–5, 6–8; Task 7's commit is not modeled). Build each step's result tree into a throwaway commit with `git commit-tree`. Use the stage's ours-side for the notes file so the chain continues. Write no refs.
- [ ] **Step 2:** For each step, write the conflicting paths to `dryrun.log`.
- [ ] **Step 3:** Compare against the expected conflicts in spec Steps 1–8. Expected: only those paths plus `docs/implementation_notes.md`. If any extra path shows up, report it to the owner before Task 4.

### Task 4: Stages 1–3 (Safety Fix, Intersection-Run Evidence, Docs and Replays)

**Files:**
- Modify: whatever the merges bring. Resolve by hand only `docs/implementation_notes.md`.

- [ ] **Step 1:** Merge `8933863`, `5f098b7`, `dead48d`, `1f77bf1`, `1400533`, `64e9b83`, `5c7bf22`, `abc28fe` and `29696f9` in that order. For each one, check the tip, run `git merge --no-ff <SHA> -m "chore: merge <branch> as it stands"`, and resolve the notes file by keeping both sides' bullets, newest first.
- [ ] **Step 2:** Run the stage tests from consolidation plan §3 (Stages 1 and 3): `pytest tests/unit -k "safety or exemption" -q` and the M2 unit tests (`pytest tests/unit -k "vlm or reasoner or prompt" -q`). Expected: no IDs outside the baseline.
- [ ] **Step 3:** Gate: `collect-ids.sh` on the int worktree, then `comm -13 baseline-pin.ids stage3.ids`. Expected: empty. Then run `md5 -q ros2_ws/src/swarm_execution/config/safety.yaml`. Expected: `598396622ca50baddc3e19b4608fa3e3`.

### Task 5: Stage 4 (Guard, Contact Logging, Stall Abort, Mismatch Record)

- [ ] **Step 1:** Merge `92158d3`, `b5eaee5`, `1016e0b`, then `93655fc`.
- [ ] **Step 2:** At `93655fc`, `orchestrator_node.py` conflicts. Dispatch a review subagent with both features' diffs (`git diff 8933863 92158d3 -- <file>` and `git diff 8933863 93655fc -- <file>`). The resolution must keep both features' code paths and both default-off checks.
- [ ] **Step 3:** Run the stage tests: `tests/unit/test_contact_geometry.py`, `test_m6_acceptance_logging.py`, `test_recompute_gt_contacts.py`, the escort-guard tests, the stall-abort tests and the mismatch-record tests (locate each by `git diff --name-only 8933863 <SHA> -- tests`). Expected: all pass, or fail only with baseline IDs.
- [ ] **Step 4:** Gate as in Task 4 Step 3. Then `git grep -n` for `stall_abort`, `plan_dispatch_mismatch_visibility` and the escort-guard key in code and config. Every default must be false.

### Task 6: Stage 5 (Demo Line, Safety Tests, Hold, Yielder)

- [ ] **Step 1:** Merge `52aea51`, `52b4275`, `0b6a91b`, `a412949`, `74dd45c`, `d85d1ed`, then `272ad4a`. For the IB10 results report conflict, take blob `c3151bc1e3`: `git show c3151bc1e3 > docs/reports/2026-11-14-ib10-safety-default-arm-results.md`.
- [ ] **Step 2:** Run the stage tests: `test_prompt_plan_grammar_rules.py`, `test_prompt_held_robot_state.py`, `test_dispatch_order_source.py`, the hold and yielder tests, and every test touching `command_grounder.py` (`git grep -l command_grounder -- tests`).
- [ ] **Step 3:** Gate as in Task 4 Step 3, plus a default-off grep for `grounding_hold_queued_crossers`, `grounding_yield_counterflow_swap` and the order-channel keys.

### Task 7: Contact Logging Behind a Default-Off Key

**Files:**
- Modify: `isaac/vgu_sim/acceptance_logging.py` (`build_acceptance_record`)
- Modify: `isaac/vgu_sim/config.py` (`ScenarioConfig`, or the runner config that carries sim-side flags; executor picks whichever already carries similar flags)
- Create: an overlay fragment for the two runs that used it, e.g. `config/gt/contact_logging_on.fragment.yaml`
- Test: `tests/unit/test_m6_acceptance_logging.py`, `tests/unit/test_recompute_gt_contacts.py`
- Modify: `docs/implementation_notes.md`

**Interfaces:**
- Produces: `build_acceptance_record(sim_time_sec: float, scenario: ScenarioConfig, states: dict[str, RobotRuntimeState], static_boxes: Sequence[StaticBox] | None = None, contact_logging: bool = False) -> dict[str, object]`; config key `gt_contact_logging.enabled: false`.

- [ ] **Step 1: Write the failing test** `test_contacts_disabled_matches_pin_schema_when_key_off`. Call `build_acceptance_record(...)` with the default `contact_logging`. Assert `row["robot_static_contacts"] == []`, `row["robot_robot_contacts"] == []`, and that the row's key set equals the pin's (no `min_static_gap_m`, `min_robot_robot_gap_m` or `contact_model`). Also add `test_contacts_computed_when_key_on`, which passes `contact_logging=True` and asserts that `contact_model` is present.
- [ ] **Step 2:** Run `pytest tests/unit/test_m6_acceptance_logging.py -q`. Expected: the key-off test FAILS.
- [ ] **Step 3:** Implement the `contact_logging` flag. When it is False, skip `compute_contact_frame` and return the pin's row shape. Thread the config key from the runner to the call. Existing contact tests and `scripts/recompute_gt_contacts.py` pass `contact_logging=True` explicitly, and the recompute tool always computes.
- [ ] **Step 4:** Add the overlay fragment. Find out how the validation-take kit and kit `sft` load fragments (`git grep -n fragment -- scripts config`). If either kit can only enable the key by editing a registered file, STOP and ask the owner.
- [ ] **Step 5:** Run `pytest tests/unit/test_m6_acceptance_logging.py tests/unit/test_recompute_gt_contacts.py tests/unit/test_contact_geometry.py -q`. Expected: PASS. Then run the Task 4 Step 3 gate.
- [ ] **Step 6:** Add a one-line comment above `_assert_no_static_contacts` in `tests/simulation/test_m6_scenarios.py`: the check is trivial when the key is off.
- [ ] **Step 7:** Add a notes entry: the evaluated runs (`68e67b5`) never had contact logging; the key keeps reruns comparable. Commit as `feat: gate GT contact logging behind default-off key`.

### Task 8: Stages 6–7 (Renderer, v4 Line)

- [ ] **Step 1:** Merge `51d9b1a`, then `c16b1a7`. For `.gitignore`, keep both sides' lines. Then merge `7850f5a`, `48234f2`, `105fff4` and `384e948`.
- [ ] **Step 2:** At `105fff4` and `384e948`, the conflicts are `reasoning_pipeline.py` and `orchestrator_node.py` (with the hold and the mismatch record) and the four-file conflict (`reasoning/vlm/models.py`, `prompt_builder.py`, `swarm_orchestrator/models.py`, `reasoning_pipeline.py`). Each gets a review subagent with all involved features' diffs against `68e67b5`. Every added field and prompt condition is kept, and every default stays off.
- [ ] **Step 3:** Run the stage tests: per-cluster, parity and refusal-feedback tests, plus the demo-line prompt tests and `pytest -k renders_byte_identically -q`. Expected: PASS.
- [ ] **Step 4:** Gate as in Task 4 Step 3. Then run `git diff 68e67b5 -- ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml`. Expected: only `per_cluster_shadow: enabled: false` and other default-off blocks.

### Task 9: Stage 8, Untracked Material, Archive Tags and README

**Files:**
- Modify: `README.md` (new section "History and archived lines")
- Create: `research_notes/**` (the 45 files from the primary checkout), `uv.lock`

- [ ] **Step 1:** Merge `fc73151`, then `ad67a18`. For `docs/superpowers/specs/2026-09-30-prereg-v2-design.md`, keep both lineages' amendments and reword no frozen section.
- [ ] **Step 2:** Copy `reports/*.md` and the untracked `research_notes/` folders from the primary checkout into the int worktree. Each `reports/<Title>.md` goes to `research_notes/<Title>/<Title>.md` where that folder exists. Leave the primary checkout's files where they are: the owner's local layout changes only when the primary checkout later moves to `main`.
- [ ] **Step 3:** Secret scan: `grep -rnE '(sk-|AIza|AKIA|ghp_|-----BEGIN|api[_-]?key)' research_notes uv.lock`. Read every hit. Expected: none real.
- [ ] **Step 4:** Commit as `docs: add research notes from local workspace`. Then run `cmp uv.lock <(git show 4224645:uv.lock)`, check that `pyproject.toml` is unchanged from `68e67b5`, add `uv.lock` and commit as `chore: track uv lockfile`.
- [ ] **Step 5:** Create annotated `archive/<branch>` tags at the 10 frozen SHAs in spec Step 11, plus `archive/wip/m4-watchdog-forward-stop-2026-06` at Task 1's commit.
- [ ] **Step 6:** Write the README section. It lists every archive tag with one line of content each. It says that the 2026-11 consolidation merged branches as they stood and is not a record of review. It points to `docs/thesis`, tag `thesis-long-2026-11-15` and release `evidence-2026-11-16`. Commit as `docs: add history and archived lines to README`.
- [ ] **Step 7:** Run the final gate as in Task 4 Step 3. Save the IDs as `$S/final.ids`.

### Task 10: End-State Report and Owner Go

- [ ] **Step 1:** Run `git branch -a --no-merged integration/2026-11 --format='%(refname:short)'`. Expected: exactly `docs/thesis`, the ten branches in spec Step 11 (local and `origin/`), and `wip/m4-watchdog-forward-stop-2026-06`. Anything else blocks the push.
- [ ] **Step 2:** For the per-key default-off table, `git grep` each key in spec Step 12.1 and record file:line and default value. Expected: all off.
- [ ] **Step 3:** Show the owner:
  - `comm -3 baseline-pin.ids final.ids`;
  - the list of hand-resolved conflicts, with commit SHAs;
  - the Step 1 and Step 2 output.

  Wait for an explicit "go". The peer session's relay is not a go.

### Task 11: Publish and Record

- [ ] **Step 1:** Push the branches and tags: `git push origin integration/2026-11 wip/m4-watchdog-forward-stop-2026-06 prereg-v3-pin 'refs/tags/archive/*:refs/tags/archive/*'`. The glob covers `archive/main-2026-09-19`.
- [ ] **Step 2:** In the `main` worktree `~/Documents/vgu-vlm-swarm-v7e`, run `git merge --ff-only integration/2026-11`, then `git push origin main`. Expected: a fast-forward, with no "rejected".
- [ ] **Step 3:** `git fetch origin && git rev-parse origin/main integration/2026-11`. Expected: equal. Then check that `git ls-remote --tags origin prereg-v1 prereg-v3-pin archive/main-2026-09-19 thesis-long-2026-11-15 evidence-2026-11-16` returns all five.
- [ ] **Step 4:** Add the notes entry from spec Step 12.4: merged as it stands, not reviewed; four suites pending before Task 2; validation status of the reverse guard, stall abort, escort guard and yielder. Commit on `integration/2026-11` as `docs: record 2026-11 consolidation`, fast-forward `main` again, and push both.
- [ ] **Step 5:** Owner request 2026-11-16: once `main` is pushed, send session `vgu-vlm-swarm-a1` a message (SendMessage) saying that thesis appendix 09 ("Data availability", `thesis/chapters/09-appendix-evidence.typ:7`) is now out of date. Give the new facts: the November source reports are on GitHub (in `main` at the pushed SHA); the run bundles and videos are in release `evidence-2026-11-16`; `68e67b5` is tagged `prereg-v3-pin`; all cited commits still resolve. Do not edit `docs/thesis` from this session.

### Task 12: Cleanup Inventory (List Only)

**Files:**
- Create: `docs/reports/2026-11-16-cleanup-candidates.md` on `integration/2026-11`

- [ ] **Step 1:** For every row of `git worktree list`, record:
  - branch;
  - `git merge-base --is-ancestor <branch> main` or archive-tag containment;
  - `git --no-optional-locks -C <wt> status --porcelain | wc -l`;
  - `du -sh <wt>/data`;
  - whether that `data/` content appears in the `evidence-2026-11-16` asset manifest (`gh release view evidence-2026-11-16 --json assets`, plus the manifest file that session 34 provides).
- [ ] **Step 2:** Sort the rows into the spec's buckets. `.claude/worktrees/m4-phase2-nav2-stack` goes under "held for the owner", and `vgu-vlm-swarm-thesis`, `v7e`, `-int` and the primary checkout go under "keep".
- [ ] **Step 3:** List the local branches contained in `main` or an archive tag, the remote branches merged into `main`, and the primary-checkout strays from the spec.
- [ ] **Step 4:** Commit as `docs: list cleanup candidates`, push after the owner OKs it, and give the owner the list. Delete nothing.
