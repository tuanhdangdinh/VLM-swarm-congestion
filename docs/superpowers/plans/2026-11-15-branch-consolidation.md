# Branch Consolidation Proposal - November Branches

**Prepared:** 2026-11-15

**Revision history:**

- Initial draft: inventory of local branches and worktrees, dependency diagram, staged merge proposal, conflict check, open questions and risks. Proposal only; nothing was merged, pushed, fetched or deleted.

---

## Purpose

Many local branches and worktrees from the last weeks are unpushed and unmerged. This document is a factual inventory and a proposed order for the owner to review. It changes no branch. Nothing should be merged, pushed or removed until the owner has ruled on the open questions.

Every fact names the read-only command that produced it. The inventory was taken at 2026-11-15, with `demo/campaign-kits` at `41f1e13` and the other tips as listed. Branches in active use change after this snapshot: `feat/v4-per-cluster-parity` (worktree `v6d`), `demo/validation-guard-contacts` (`v7n`) and `fix/convoy-hold-queued-robots` (`v7o`).

**Method.** All commands ran in `/Users/tuanhdangdinh/Documents/vgu-vlm-swarm`:

- `git worktree list`; `git branch -vv`; `git branch -r`.
- Per branch: `git merge-base <b> {main, fix/deadlock-collision-resolution, 68e67b5}`, `git merge-base --is-ancestor`, `git rev-list --count`, and `git rev-list --left-right --count <b>...origin/<b>` where a same-name remote branch exists.
- `git diff --name-only <fork point> <b>` for changed files.
- `git --no-optional-locks -C <worktree> status --porcelain` for cleanliness.
- `git merge-tree --write-tree --name-only --no-messages <a> <b>` for conflicts. It writes objects only, no refs and no worktree changes.
- No `git fetch` was run. Remote facts are **as of the last fetch**, not live.

Terms used throughout:

- **W** is `fix/deadlock-collision-resolution`, the main working branch.
- **Pin** is `68e67b5` (`feat/v3-integration`), the VM runtime pin of prereg-v3 and of every November run.

---

## 1. Inventory

### 1.1 The Two Lineages (Verified)

| Fact | Value | Command |
|---|---|---|
| Merge base of W and the pin | `4307aa1` | `git merge-base fix/deadlock-collision-resolution 68e67b5` |
| W commits not in the pin / pin commits not in W | 84 / 445 | `git rev-list --left-right --count W...68e67b5` |
| What W's 84 commits change against `4307aa1` | 14 files under `docs/` plus one `research_notes/` file; no runtime, test, script or config file | `git diff --name-only 4307aa1 W` |
| `main` | `f2ca3c6` (2026-09-19), an ancestor of W, 0/0 against `origin/main` | `git branch -vv` |
| Fork point of every November branch | the pin `68e67b5` (all contain it); merge base with W is `4307aa1` and with `main` is `f2ca3c6` for every one | `git merge-base --is-ancestor 68e67b5 <b>` |
| Tags | `prereg-v1` only; no tag at `68e67b5` | `git tag` |

So W is ahead of the pin only in documentation. All November code descends from the pin, not from W.

### 1.2 November Branches

"Fork" is the branch's nearest parent branch at the shown commit. "+N" is the commit count since that fork. File counts are from `git diff --name-only <fork> <b>`:

- **rt:** runtime (`reasoning/`, `ros2_ws/`, `isaac/` outside config);
- **t:** `tests/`;
- **d:** `docs/` and `*.md`;
- **s:** `scripts/` and `benchmarks/`;
- **cfg:** configs, including tracked `data/experiments/` JSON.

Other tracked files are noted in the row. No November branch has an upstream configured, and none has a same-name remote branch, except `feat/v4-gf-cluster`, `feat/v4-vlm-bench` and `feat/v4-per-cluster`.

| Branch (worktree) | Tip, date | Fork | +N | rt/t/d/s/cfg | Remote (as of last fetch) | Tree |
|---|---|---|---|---|---|---|
| `feat/v4-gf-cluster` (v6b) | `c16b1a7` 10-23 | pin | 18 | 0/20/6/17/0, `.gitignore` | upstream, 0/0 | clean |
| `feat/v4-vlm-bench` (v6a) | `7850f5a` 11-12 | `v4-gf-cluster` (merged in by `8a373bb`) | 3 | 0/0/3/0/0 | same-name, 0/0 | clean |
| `feat/v4-per-cluster` (v6c) | `48234f2` 11-12 | `v4-vlm-bench` | 9 | 0/2/4/7/0 | upstream, **ahead 1** | clean |
| `feat/v4-per-cluster-parity` (v6d, **in use**) | `b534d17` 11-15 | `v4-per-cluster` | 24 | 14/8/10/5/3 | none | clean at snapshot |
| `feat/v4-refusal-feedback` (v7b) | `384e948` 11-14 | `v4-per-cluster`, plus parity up to `fdf333d` | 25 | 19/16/5/11/5 | none | clean |
| `docs/thesis` (thesis) | `90b03d9` 11-14 | `v4-per-cluster`, plus parity to `cbe3dcf` and refusal to `fdf333d` | 69 | 14/8/13/5/3, 29 `thesis/` files | none | **1 modified (`thesis/main.typ`)** |
| `feat/ib10-live-resolution` (v7a) | `5f098b7` 11-15 | pin | 6 | 0/0/3/0/0 | none | clean |
| `fix/safety-exemption-scope` (v7c) | `8933863` 11-14 | pin | 14 | 2/1/2/0/1 | none | clean |
| `feat/ib10-safety-default-arm` (v7d) | `dead48d` 11-15 | `fix/safety-exemption-scope` | 8 | 0/0/3/0/0 | none | clean |
| `docs/head-on-vlm-vs-rule` (no worktree) | `1f77bf1` 11-14 | `ib10-safety-default-arm@9ca0932` | 1 | 0/0/2/0/0 | none | - |
| `exp/head-on-swapped-id-replay` (swapid) | `abc28fe` 11-14 | `docs/head-on-vlm-vs-rule` | 14 | 0/3/6/5/5, 28 `data/experiments/` files | none | clean |
| `exp/head-on-json-only-replay` (jsononly) | `29696f9` 11-14 | `docs/head-on-vlm-vs-rule` | 18 | 2/3/7/4/5, 32 `data/experiments/` files | none | clean |
| `feat/convoy-live-resolution` (v7f) | `5c7bf22` 11-14 | `ib10-safety-default-arm@9ca0932` | 3 | 0/0/3/0/0 | none | clean |
| `feat/demo-panel-renderer` (v7g) | `8069734` 11-15 | `feat/convoy-live-resolution` | 8 | 0/2/2/12/0, `.gitignore` | none | clean |
| `demo/ib10-recorded-demo` (v7h) | `64e9b83` 11-15 | `ib10-safety-default-arm@9ca0932` | 3 | 0/0/3/0/0 | none | clean |
| `docs/vlm-plan-influence-trace` (v7i) | `1400533` 11-15 | `ib10-safety-default-arm@9ca0932` | 3 | 0/0/2/0/0 | none | clean |
| `demo/vlm-order-channel` (v7k) | `52aea51` 11-15 | `docs/vlm-plan-influence-trace` | 13 | 5/1/4/3/9, 7 `data/experiments/` files | none | clean |
| `demo/campaign-kits` (v7j) | `41f1e13` 11-15 | `demo/ib10-recorded-demo`; merged `demo/vlm-order-channel` at `aa16b0d` | 41 | 5/2/24/4/14, 12 `data/experiments/` files | none | clean |
| `fix/escort-obstacle-guard` (v7l) | `72c08c8` 11-15 | `fix/safety-exemption-scope` | 3 | 6/3/2/1/1 | none | clean |
| `feat/gt-contact-logging` (v7m) | `b5eaee5` 11-15 | `fix/safety-exemption-scope` | 5 | 2/3/3/1/45 (recompute summaries) | none | clean |
| `demo/validation-guard-contacts` (v7n, **in use**) | `9a68539` 11-15 | `demo/campaign-kits@cc1313d`; merged guard (`4bbe4db`) and contact logging (`4c78593`) | 11 | 8/6/5/2/46 | none | clean at snapshot |
| `fix/convoy-hold-queued-robots` (v7o, **in progress**) | `4e5476b` 11-15 | `demo/campaign-kits@4e5476b` | 0 | none yet | none | clean at snapshot |

**Still-open partial merges** (from `git rev-list --count <b>..<a>`):

- `demo/campaign-kits` lacks 1 commit of `demo/vlm-order-channel` (merge base `89419a3`).
- `demo/validation-guard-contacts` lacks the 3 latest commits of `demo/campaign-kits` (merge base `cc1313d`).
- Both lack 3 commits of `feat/ib10-safety-default-arm`: the two contact-erratum commits and today's plan erratum.
- `docs/thesis` lacks 5 parity commits and 12 refusal-feedback commits.

**Pinned configuration files.** These were checked with `git diff --name-only 68e67b5 <b> -- '*orchestrator.yaml' '*rag.yaml' '*safety.yaml' '*prompt*'`:

- `ros2_ws/src/swarm_orchestrator/config/orchestrator.yaml` changes only on the v4 parity, refusal and thesis branches. The added block is `per_cluster_shadow: enabled: false`, so it is default-off (verified in the refusal-feedback diff).
- `config/rag.yaml` and `ros2_ws/src/swarm_execution/config/safety.yaml` change on no November branch. The safety fix ships a separate fragment, `config/safety/scoped_clearing_exemption.fragment.yaml`, and the guard ships `config/grounding/escort_obstacle_guard.fragment.yaml`. Both are overlay fragments, so no pinned file is edited.
- `reasoning/vlm/prompt_builder.py` changes on `demo/vlm-order-channel`, `demo/campaign-kits`, `demo/validation-guard-contacts` and `feat/v4-refusal-feedback`. The demo-line changes sit behind request flags. Tests pin byte-identical default rendering: `test_rules_off_renders_byte_identically_to_default` and `test_off_renders_byte_identically_to_default` (verified by name, not run).

**Behaviour that is not default-off.** `feat/gt-contact-logging` changes `isaac/vgu_sim/acceptance_logging.py`, so every ground-truth row gains computed contact fields. No switch was found in its diff (inferred from a grep of the diff for `enable`, `flag`, `config` and `env`). This changes GT output for any run made from a tree that contains it.

### 1.3 Older Local Branches

| Branch | Tip date | In W? | Notes |
|---|---|---|---|
| `main` | 09-19 | yes | `origin/main` 0/0 |
| `biarritz`, `ironwood-turquoise`, `kingsnake-viga` | 06-05 | yes | same commit `2404ecd` |
| `continue-m4-phase2-nav2`, `harrisburg` | 06-11 | yes | same commit `cb307ff` |
| `feat/m2-cosmos-reason2-prompt`, `feat/m2-input-ablation` | 06-15 | yes | |
| `m1-isaac-camera-wiring` | 06-11 | no (1 ahead) | upstream 0/0 |
| `worktree-m4-phase2-nav2-stack` | 06-24 | no (35 ahead) | upstream 0/0; worktree has 7 dirty entries |
| `feat/failure-context-closed-loop`, `feat/gemini-er2-backend` | 09-19 | yes | upstream 0/0 |
| `feat/robot-order-counterbalance` | 09-22 | no (1 ahead) | upstream 0/0 |
| `wip/untracked-local-state` | 09-23 | no (2 ahead) | upstream 0/0 |
| `feat/m3-yield-feasibility`, `feat/order-random` | 09-25 | yes | |
| `feat/arm-b-classical` | 09-26 | yes | |
| `feat/m1-sim-time`, `feat/pillar2-retreat` | 09-27 | yes | |
| `feat/trail-probe-pilot` | 10-06 | no (183 ahead) | not in the pin either |
| `probe/shutdown-timing` | 10-07 | yes | |
| `prereg-v1-hotfix` | 10-09 | no (6 ahead) | same-name remote 0/0; fork `569d95c` = `prereg-v1` |
| `feat/prereg-v2-composite` | 10-09 | no (230 ahead) | same-name remote 0/0; not in the pin |
| 38 `feat/v3-*` branches (`v3-closed-loop` ... `v3-confirm-t1`) | 10-06 to 10-22 | no | all ancestors of the pin, so merged into `feat/v3-integration`; 6 have same-name remotes at 0/0 (`arm-b-mode`, `confirm-t1`, `escort-live`, `freeflow-freeze`, `s1-scorers`, `s1b-freeze`) |
| `feat/v3-vjepa-probe` | 10-11 | no | not in the pin (fork `9e18639`) |
| `feat/v3-design` | 10-22 | no (28 ahead) | merged into W by `ef1b1b1` and has moved on since; remote 0/0 |
| `feat/v3-integration` | 10-22 | no | **the pin**; remote 0/0 |

**Worktrees that look disposable** (branch fully merged into W or into the pin, tree clean). These are marked only, and nothing was removed:

- Merged into W, clean:
  - `.warp/.../ironwood-turquoise` and `.../kingsnake-viga`;
  - `conductor/.../kelowna`;
  - `vgu-vlm-swarm-timing`;
  - `.worktrees/arm-b-classical`, `failure-context-closed-loop`, `gemini-er2`, `m1-sim-time` and `pillar2-retreat`.
- Merged into the pin, clean: `vgu-vlm-swarm-v3a` to `v3w`, `v3y`, `v3z`, `v4a` to `v4d`, and `v5a` to `v5e`, all except `v3x`. Their branches are ancestors of `68e67b5`.
- Not disposable:
  - `v3`, which holds the pin;
  - `v7e`, the `main` checkout;
  - `thesis`, which is dirty;
  - `.claude/worktrees/m4-phase2-nav2-stack`, which is dirty;
  - every November worktree.

---

## 2. Dependency Diagram

```text
main f2ca3c6 ── ... ── 4307aa1 ─┬─ W fix/deadlock-collision-resolution fc73151 (+84, docs only; merged feat/v3-design)
                                 └─ ... 38 feat/v3-* ... ── PIN 68e67b5 feat/v3-integration
                                                              │
   ┌──────────────────────────────────────────────────────────┼─────────────────────────────┐
   │ v4 line                                                  │ IB10 / demo line            │
   │ v4-gf-cluster ─▶ v4-vlm-bench (merge 8a373bb)            │ ib10-live-resolution (+6)   │
   │                     └─▶ v4-per-cluster                   │                             │
   │                           ├─▶ v4-per-cluster-parity      │ fix/safety-exemption-scope 8933863
   │                           ├─▶ v4-refusal-feedback        │   ├─▶ ib10-safety-default-arm ── 9ca0932 ── dead48d
   │                           │     (has parity to fdf333d)  │   │                              │
   │                           └─▶ docs/thesis                │   ├─▶ fix/escort-obstacle-guard ─┐
   │                                 (parity to cbe3dcf,      │   └─▶ feat/gt-contact-logging ───┤
   │                                  refusal to fdf333d)     │                                  │
   └──────────────────────────────────────────────────────────┘                                  │
     from 9ca0932:                                                                               │
       docs/head-on-vlm-vs-rule ─▶ exp/head-on-swapped-id-replay                                 │
                                └▶ exp/head-on-json-only-replay                                  │
       feat/convoy-live-resolution ─▶ feat/demo-panel-renderer                                   │
       docs/vlm-plan-influence-trace ─▶ demo/vlm-order-channel ──(merge aa16b0d)──┐              │
       demo/ib10-recorded-demo ─▶ demo/campaign-kits ◀───────────────────────────┘              │
                                     ├─ cc1313d ─▶ demo/validation-guard-contacts ◀─(4bbe4db, 4c78593)
                                     └─ 4e5476b ─▶ fix/convoy-hold-queued-robots (in progress)
```

---

## 3. Proposed Consolidation

**Target (open question Q1).** The proposal assumes a **new integration branch cut from the pin**, for example `integration/2026-11` at `68e67b5`. `feat/v3-integration` and `68e67b5` stay untouched. W is brought in at the end, because its 84 commits are documentation only.

**Conflict check.** Each pair below was run through `git merge-tree` once. The check is pairwise against branch tips: it does not simulate the cumulative state after earlier stages, so a later stage may conflict where the pairwise check was clean. `docs/implementation_notes.md` conflicts in almost every pair. These are **expected and trivial**: both sides prepend dated bullets under the same section headers, and the fix is to keep both sides' bullets, newest first. They are listed separately from real conflicts.

| Pair | Real conflicts (beyond notes) | Notes conflict |
|---|---|---|
| `ib10-live-resolution` + `ib10-safety-default-arm` | none | yes |
| `ib10-safety-default-arm` + `demo/validation-guard-contacts` | `docs/reports/2026-11-14-ib10-safety-default-arm-results.md` (docs: the validation branch holds the mirror before today's erratum; take the `ib10-safety-default-arm` side, which equals today's `demo/campaign-kits` blob `c3151bc1e3`) | yes |
| `ib10-live-resolution` + `demo/validation-guard-contacts` | none | yes |
| `demo/validation-guard-contacts` + `demo/campaign-kits` | none | yes |
| `demo/validation-guard-contacts` + `demo/vlm-order-channel` | none | yes |
| `demo/validation-guard-contacts` + `feat/demo-panel-renderer` | none | yes |
| `demo/validation-guard-contacts` + `docs/head-on-vlm-vs-rule` | none | yes |
| `demo/validation-guard-contacts` + `exp/head-on-swapped-id-replay` | none | yes |
| `demo/validation-guard-contacts` + `exp/head-on-json-only-replay` | none | yes |
| `exp/head-on-swapped-id-replay` + `exp/head-on-json-only-replay` | none | yes |
| `fix/escort-obstacle-guard` + `feat/gt-contact-logging` | none | no (clean) |
| `v4-per-cluster-parity` + `v4-refusal-feedback` | none | yes |
| `v4-per-cluster-parity` + `demo/validation-guard-contacts` | none | yes |
| **`v4-refusal-feedback` + `demo/validation-guard-contacts`** | **`reasoning/vlm/models.py`, `reasoning/vlm/prompt_builder.py`, `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/models.py`, `ros2_ws/src/swarm_orchestrator/swarm_orchestrator/reasoning_pipeline.py`** (runtime code) | yes |
| `docs/thesis` + `v4-refusal-feedback` | none | yes |
| `docs/thesis` + `v4-per-cluster-parity` | none | yes |
| W + `feat/v3-integration` | `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` (docs) | yes |
| W + `demo/campaign-kits` | `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` (docs) | yes |
| W + `feat/v3-design` | none | no (clean) |
| `feat/v3-design` + `demo/campaign-kits` | `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` (docs) | no |
| `v4-refusal-feedback` + `exp/head-on-json-only-replay` | none | yes |
| `v4-per-cluster-parity` + `exp/head-on-json-only-replay` | none | yes |
| `feat/demo-panel-renderer` + `feat/v4-gf-cluster` | `.gitignore` (both add ignore lines; keep both) | yes |

### Stage 0 — Backup Without Merging (Owner Decision)

- **What.** Push branches unchanged to the remote as backups. No merge, no rebase.
- **Safe to push as-is:** branches whose diff against their fork is docs, tests or scripts only, plus default-off code. Each still needs a secret scan of its tracked files first:
  - docs only: `feat/ib10-live-resolution`, `feat/ib10-safety-default-arm`, `docs/head-on-vlm-vs-rule`, `docs/vlm-plan-influence-trace`, `demo/ib10-recorded-demo`, `feat/convoy-live-resolution`;
  - tests, docs and scripts: `feat/demo-panel-renderer`, `feat/v4-gf-cluster` (remote exists), `feat/v4-vlm-bench` (remote 0/0) and `feat/v4-per-cluster` (1 commit ahead);
  - default-off code: `fix/safety-exemption-scope` (`scoped_clearing_exemption: bool = False`, `safety.py:265`, verified with `git grep`) and a fragment;
  - older unmerged branches with no remote that exist only on this Mac: `feat/trail-probe-pilot` (183 commits not in W, not in the pin) and `feat/v3-vjepa-probe` (not in the pin). Their content was not reviewed here.
- **Remote-only branches** (no local branch, as of last fetch): `origin/claude/laughing-volta-fwnqvs`, `origin/feat/v2-audit-fixes`, `origin/feat/v2-conformance-fixes`, `origin/feat/v2-gpt56-sol`, `origin/feat/v2-harness-optionb`. They are listed only, and nothing is proposed for them.
- **Needs review first:**
  - The branches that track `data/experiments/` with model call logs: `exp/head-on-*`, `demo/vlm-order-channel`, `demo/campaign-kits` and `demo/validation-guard-contacts`. The `calls.jsonl` files need a secret and payload review; CLAUDE.md forbids logging base64 images and secrets.
  - `feat/gt-contact-logging` (behaviour not default-off).
  - `feat/v4-refusal-feedback` (real conflicts with the demo line).
  - `docs/thesis` (dirty tree).
  - The branches in active use (`v6d`, `v7n`, `v7o`): wait until their agents finish.

### Stage 1 — Safety Fix

- **Contains.** `fix/safety-exemption-scope`: the default-off `scoped_clearing_exemption`, the fragment and one test file.
- **Why first.** It is the base of 14 November branches (§1.2). Merging it first makes every later merge smaller.
- **Expected conflicts.** None. It is a fast-forward of the pin.
- **Verify after.** `tests/unit` for `swarm_execution` safety, then the full `make test` with zero delta against a pin baseline. The key defaults to False in code (`safety.py:265`). With it off, M4 behaviour must equal the pin's; the branch's key-off identity re-run over 68 bundles (`8933863`) is the existing evidence.
- **Not into the pinned lineage.** The deployed `safety.yaml` must stay `598396622ca50baddc3e19b4608fa3e3`. Do not merge the fragment into it.

### Stage 2 — Frozen IB10 Evidence Branches

- **Contains.** `feat/ib10-live-resolution`, then `feat/ib10-safety-default-arm`. Both are docs only, with registrations, reports and errata.
- **Why here.** Every demo-line branch forks at `9ca0932` on `ib10-safety-default-arm`. Merging it next means later merges only add their own deltas.
- **Expected conflicts.** Notes only.
- **Verify after.** The documentation only: the reports cite md5s and archives, which do not change.
- **Rule.** These branches are **merged, not rewritten**. Keep them as they are and refer to them by commit (`50704c2` and `ed8b203` for the registrations).

### Stage 3 — Documentation and Analysis Branches

- **Contains.** `docs/head-on-vlm-vs-rule`, `docs/vlm-plan-influence-trace`, `demo/ib10-recorded-demo` and `feat/convoy-live-resolution`, all docs only. Then `exp/head-on-swapped-id-replay` and `exp/head-on-json-only-replay`.
- **Why here.** These are low-risk docs, and later demo branches contain them.
- **Expected conflicts.** Notes only, including between the two `exp/` branches.
- **Verify after.** For `exp/head-on-json-only-replay`: `reasoning/vlm/models.py` and `reasoner.py` change, so run `tests/unit` for M2 and confirm that the default prompt and parse paths are unchanged.
- **Not into the pinned lineage.** The tracked `data/experiments/...` results are frozen evidence. Keep them as files and never regenerate them in place.

### Stage 4 — Guard and Contact Logging

- **Contains.** `fix/escort-obstacle-guard` (default-off key and fragment), then `feat/gt-contact-logging`.
- **Why here.** Both fork from the safety fix, and `merge-tree` shows them clean against each other.
- **Expected conflicts.** None between them; notes against the integration branch.
- **Verify after:**
  - `tests/unit/test_contact_geometry.py`, `test_m6_acceptance_logging.py` and `test_recompute_gt_contacts.py`;
  - the guard's unit tests;
  - the full suite at zero delta.
- **Stale items to fix when the contact-logging branch lands:**
  - `docs/specs/module6_simulation.md` already describes `robot_static_contacts` as populated (at the pin, line 794: "lists robot IDs in contact with a wall or rack"). Until this branch lands, `isaac/vgu_sim/acceptance_logging.py:99-100` hard-codes the lists to `[]`, so the spec overstates the runtime. The contact branch edits the spec (adding a field description at line 804), so recheck it after the merge.
  - `_assert_no_static_contacts` in `tests/simulation/test_m6_scenarios.py` (pin lines 65 and 88) passes trivially on the empty field until then. After the merge it starts to assert something, and (inferred, not tested) it may begin to fail on scenes with near-rack poses.
- **Not into the pinned lineage.** GT contact logging is not default-off: it changes GT rows. Runs made from the pin must stay as they are. A rerun of a registered experiment from the integration branch would produce different GT rows and must be registered as such.

### Stage 5 — Demo Line

- **Contains**, in order:
  1. `demo/vlm-order-channel` (default-off order-channel prompt rules);
  2. `demo/campaign-kits`;
  3. `demo/validation-guard-contacts`, which then adds only its own 11 commits, since it contains Stage 4 and `campaign-kits@cc1313d`;
  4. `fix/convoy-hold-queued-robots`, once its owner reports it done (**in progress**).
- **Why here.** Each contains the previous stages. Merging after Stages 1 to 4 keeps each merge to its own delta.
- **Expected conflicts:**
  - notes;
  - possibly `docs/reports/2026-11-14-ib10-safety-default-arm-results.md`: the validation branch holds the pre-erratum mirror, and the pairwise check against `ib10-safety-default-arm` conflicts. Take the erratum-bearing side, blob `c3151bc1e3`, which equals today's `demo/campaign-kits` and `feat/ib10-safety-default-arm`.
- **Verify after:**
  - `tests/unit/test_prompt_plan_grammar_rules.py` and `test_prompt_held_robot_state.py`, especially the byte-identical-default tests;
  - `tests/unit/test_dispatch_order_source.py`;
  - the full suite at zero delta.
- **Not into the pinned lineage.**
  - The prompt version stays pinned. The new prompt conditions remain default-off keys.
  - Kit overlays under `config/` are experiment overlays, not edits to the pinned `orchestrator.yaml` or `rag.yaml`.

### Stage 6 — Demo Renderer

- **Contains.** `feat/demo-panel-renderer`: scripts and tests only. It contains `feat/convoy-live-resolution`.
- **Expected conflicts.** Notes only.
- **Verify after.** The renderer's two test files. The videos it renders are git-ignored (`data/demo/` in `.gitignore`).
- **Later conflict.** In Stage 7, `.gitignore` conflicts with `feat/v4-gf-cluster`, because both add lines. Keep both.

### Stage 7 — v4 Line

- **Contains**, in order:
  1. `feat/v4-gf-cluster`;
  2. `feat/v4-vlm-bench`;
  3. `feat/v4-per-cluster`;
  4. `feat/v4-per-cluster-parity` (active in `v6d`; wait);
  5. `feat/v4-refusal-feedback`;
  6. last, and only if the owner wants it on the integration branch, `docs/thesis`.
- **Why last among code.** It is the only real code conflict found. `v4-refusal-feedback` against the demo line conflicts in `reasoning/vlm/models.py`, `reasoning/vlm/prompt_builder.py`, `swarm_orchestrator/models.py` and `reasoning_pipeline.py`. Both sides add default-off fields and prompt conditions to the same structures.
- **Verify after.** This merge needs a hand resolution reviewed by someone who knows both features:
  - the per-cluster, parity and refusal-feedback unit tests;
  - the demo-line prompt tests;
  - a check that each new key is still default-off and that default prompt rendering is byte-identical to the pin;
  - the full suite at zero delta.
- **Not into the pinned lineage.** `per_cluster_shadow: enabled: false` must stay false in the tracked `orchestrator.yaml`.

### Stage 8 — Reconcile With W

- **Contains.** A merge of `fix/deadlock-collision-resolution` into the integration branch: its 84 docs-only commits. Then `feat/v3-design`, which has 28 commits in neither W nor the pin. Its net diff against its merge base with W (`2c81cbd`) is one file under `docs/`, and it merges into W cleanly.
- **Expected conflicts.**
  - Notes.
  - `docs/superpowers/specs/2026-09-30-prereg-v2-design.md` (docs): both lineages edited this registered spec. Resolve it by keeping both texts' amendments. A registered spec's frozen sections must not be reworded.
- **Verify after.** Documentation only. Owner decides afterwards whether `main` is fast-forwarded to the integration branch.

---

## 4. Open Questions for the Owner

1. **Q1 Integration target.** W, `main`, or a new branch from the pin?
   - W has the pin's code only up to `4307aa1`. Every November branch descends from the pin. W is ahead only in documentation.
   - The proposal assumes a new branch from the pin, then W merged in, then `main` fast-forwarded.
2. **Q2 Backups.** Push the "safe as-is" branches (Stage 0) to the remote as backups before any merge? Which branches need a secret and payload review first?
3. **Q3 Tagging.** Should `68e67b5` get a tag (for example `prereg-v3-pin`) so the pin cannot be lost if `feat/v3-integration` moves? Only `prereg-v1` exists today.
4. **Q4 Contact logging.** It is not default-off. Should it land on the integration branch now, given that any rerun of a registered experiment from that branch would change GT rows? Or should it land behind a key?
5. **Q5 Off-machine evidence backup.** The evidence is git-ignored and exists only on this Mac. Free disk is about 10 GiB of 460 GiB (98 % used, `df -h /Users`).
   Sizes, from one `du -sh` per directory:

   | Directory | Size |
   |---|---|
   | `vgu-vlm-swarm/data/logs` | 6.2 G |
   | `vgu-vlm-swarm-v3/data/logs` | 5.9 G |
   | `vgu-vlm-swarm-v6d/data/logs` | 943 M |
   | `vgu-vlm-swarm-v7j/data/logs` | 720 M |
   | `vgu-vlm-swarm-v7a/data/logs/vm_runs` | 417 M (IB10 live) |
   | `vgu-vlm-swarm-v7d/data/logs/vm_runs` | 281 M (IB10 safety) |
   | `vgu-vlm-swarm-v7g/data/demo` | 271 M (demo videos; git-ignored by `.gitignore:50`) |
   | `vgu-vlm-swarm-v7i/data/logs` | 2.5 M |

   Other worktrees' `data/` directories were not measured. Which of these need an off-machine copy, and where?
6. **Q6 Disposable worktrees.** Remove the worktrees marked in §1.3 to free disk? Each holds its own git-ignored `data/` directory. A removal deletes that directory, so check it for unique evidence first.
7. **Q7 `docs/thesis`.** Should it merge into the integration branch, or stay a separate writing branch? It has a modified `thesis/main.typ`.

---

## 5. Risks

| Risk | Mitigation |
|---|---|
| Pairwise `merge-tree` misses conflicts that only appear after earlier stages land | Re-run `merge-tree` against the integration branch before each stage; one stage per review |
| A merge changes default prompt bytes or a default key, so pinned runs stop being reproducible | Byte-identical-default prompt tests and a zero-delta full suite after each stage; the pin itself is never moved |
| Contact logging changes GT rows and silently changes what scorers read | Q4; re-register any rerun; do not regenerate frozen evidence |
| Active agents (`v6d`, `v7n`, `v7o`) commit after this snapshot | Re-run the inventory commands before each stage |
| Notes conflicts resolved carelessly drop entries | Keep both sides' bullets; check that the dated bullet count after the merge equals the sum of the two sides' unique bullets |
| Tracked `data/experiments/*/calls.jsonl` hold model payloads | Secret and payload scan before any push |
| Evidence exists on one disk at 98 % use | Q5 backup before any worktree removal |
| Remote facts are stale | No fetch was run; fetch and re-check ahead/behind before pushing |
