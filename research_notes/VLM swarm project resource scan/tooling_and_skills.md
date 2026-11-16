# Research Tooling and Claude Code Skills for the VGU VLM Swarm Bench

Scan date: 2026-11-12. GitHub activity figures ("pushed", stars) come from the GitHub REST API (`gh api repos/<owner>/<repo>`) on 2026-11-12. Each item ends with "Here:", a one-line note on how it maps to the bench's pain points: the prompt-hash response cache, the SHA-256 run-config provenance, the git-tagged prereg docs, the n=187 paired model comparison, cost tracking, position-bias shuffles, and sprawl across many Claude Code sessions and worktrees.

## Q1. LLM eval/replay frameworks with caching and provenance: which fit a custom multimodal bench with minimal rewrite?

### Takeaway
Inspect AI is the closest structural fit, but adopting it means a port, not a drop-in. It has a content-hashed response cache, git revision and package versions in every log, logged images, and an `eval-retry` that reuses completed samples. The cheapest high-value change is to keep the custom bench and borrow ideas from Inspect: scope-tagged cache keys, a revision and packages block in the run JSON, and a cache prune CLI. If one gateway is wanted for caching and cost across all three providers, LiteLLM is the low-rewrite choice. promptfoo, DeepEval, lm-eval-harness, HELM and OpenAI evals fit this bench poorly.

### Cited Findings
- **Inspect AI (UK AISI).** MIT licence, about 3.2k stars, last push 2026-11-11, so very active. [GitHub](https://github.com/UKGovernmentBEIS/inspect_ai). A PyPI mirror listed 0.3.224 (May 2026), with point releases roughly every week. [CERN PyPI mirror](https://simple-repository.app.cern.ch/project/inspect_ai)
  - Here: the strongest candidate if the bench is ever rewritten. Its Task/Sample/Solver/Scorer model maps onto replaying 187 recorded decision items.
- **Inspect cache key.** A cached response is reused only when all of these match: model name and base URL, the prompt (full message history), epoch, generate config, and tools/tool_choice. Default expiry is 1 week. `CachePolicy(expiry=..., scopes={...}, per_epoch=...)` controls it, `expiry=None` means never expire, and the directory is set with `INSPECT_CACHE_DIR`. The CLI has `inspect cache list --pruneable`, `inspect cache clear --model`, and `inspect cache prune`. [Inspect caching docs](https://inspect.aisi.org.uk/caching.html)
  - Here: `scopes` is a clean answer to cache invalidation. Put the prompt-template version, the shuffle seed and the prereg tag into the key on purpose, instead of relying on prompt-hash alone.
- **What goes into the hash.** In the source, `_cache_key` hashes the generate config (runtime-only fields made inert), the `model_dump()` of every input message (only `id` and `cache_breakpoint` excluded), base_url, tool_choice, tools, expiry, and the policy scopes. [inspect_ai `_cache.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/model/_cache.py)
- **Inspect logs and provenance.** `EvalSpec` carries `revision: EvalRevision` (type "git", origin, commit) and `packages: dict[str, str]`. [inspect_ai `log/_log.py`](https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/src/inspect_ai/log/_log.py)
  - `EvalStats` records input and output token usage. `.eval` binary logs are about 1/8 the size of `.json`. [Inspect eval-logs docs](https://inspect.aisi.org.uk/eval-logs.html)
  - Image bytes are kept in logs by default and deduplicated as attachments; `--no-log-images` turns this off. [Inspect eval-logs docs](https://inspect.aisi.org.uk/eval-logs.html)
  - `inspect eval-retry` writes a new log and reuses completed samples. Reuse is skipped if `dataset.shuffle()` is detected. [Inspect eval-logs docs](https://inspect.aisi.org.uk/eval-logs.html)
  - Inspect also has multimodal input docs and eval sets. [Multimodal](https://inspect.aisi.org.uk/multimodal.html); [Eval sets](https://inspect.aisi.org.uk/eval-sets.html)
  - Here: this covers what the SHA-256 run-config JSON does, plus git commit and package versions for free. `inspect view` would replace ad-hoc JSONL browsing.
- **LiteLLM.** About 63k stars, last push 2026-11-11. Calls 100+ LLM APIs in OpenAI format "with cost tracking". [GitHub](https://github.com/BerriAI/litellm)
  - Supports a disk cache (`type: disk`, default dir `./.litellm_cache`). Exact-match caches key on a hash of the whole request. [LiteLLM proxy caching docs](https://docs.litellm.ai/docs/proxy/caching); SDK-level cache docs: [LiteLLM caching](https://docs.litellm.ai/docs/caching/all_caches); token/cost docs: [LiteLLM token usage](https://docs.litellm.ai/docs/completion/token_usage)
  - Here: a thin swap under the existing Gemini/Anthropic/OpenAI adapters would give one cache and one cost ledger. This works only if `VLMBackend` stays the boundary, as CLAUDE.md requires.
- **promptfoo.** MIT licence, about 27k stars, last push 2026-11-11. [GitHub](https://github.com/promptfoo/promptfoo)
  - Disk cache in `~/.promptfoo/cache`, keyed on provider id, prompt content, provider config and context vars; `--no-cache` bypasses it. [promptfoo caching docs](https://promptfoo.dev/docs/configuration/caching/)
  - Promptfoo's own blog post: "Promptfoo is joining OpenAI"; the open-source project continues. [promptfoo blog](https://www.promptfoo.dev/blog/promptfoo-joining-openai)
  - Here: declarative YAML side-by-side model comparison is good for quick prompt A/B checks. It is not built for preregistered statistics on recorded multimodal items.
- **DeepEval.** Apache-2.0, about 19k stars, last push 2026-11-11. [GitHub](https://github.com/confident-ai/deepeval)
  - Here: it centres on LLM-as-judge metrics. Low fit, because the bench scores structured decisions against recorded ground truth.
- **lm-evaluation-harness.** MIT licence, last push 2026-11-04. Few-shot evaluation of LMs. [GitHub](https://github.com/EleutherAI/lm-evaluation-harness)
  - Here: built for benchmark-task text LM evaluation. Poor fit for a custom multimodal API replay.
- **HELM (Stanford CRFM).** Apache-2.0, last push 2026-09-01. Describes itself as "holistic, reproducible and transparent" evaluation including multimodal models. [GitHub](https://github.com/stanford-crfm/helm)
  - Here: a heavy framework; rewrite cost is high for 187 items.
- **openai/evals.** Last push 2026-04-14, so activity is low. [GitHub](https://github.com/openai/evals)
  - Here: not recommended.
- **Langfuse and Arize Phoenix.** LLM trace/observability tools, both pushed 2026-11-11. Langfuse is about 37k stars and Phoenix about 12k. [Langfuse](https://github.com/langfuse/langfuse); [Phoenix](https://github.com/Arize-ai/phoenix)
  - Here: useful mainly if per-call traces with cost must be shared with collaborators. The JSONL outputs already cover the offline case.

### Inferences
- Inspect hashes `message.model_dump()`, so image content is part of the cache key in whatever form it holds in the message (base64 data URI or a URL/path string). If images are passed by file path, re-rendering an annotated frame at the same path might not invalidate the cache. This is not verified; a test is needed.
- The current custom bench already has Inspect's key ideas. Ranked by value per hour, the recommendation is:
  1. Add `scopes`-style explicit cache-key components and a `prune` command.
  2. Record git commit and package versions in the run JSON.
  3. Only then consider porting.
- Inspect's `eval-retry` skips reuse when `dataset.shuffle()` is detected. If ported, the position-bias shuffles should be done per-sample with a fixed seed inside the solver, not by dataset shuffle, or retries will re-bill every item.

### Gaps
- Not verified: whether Inspect's Anthropic/Google/OpenAI providers send identical image encodings, and whether provider-specific encoding changes the key.
- LiteLLM disk-cache TTL defaults, per-request `no-cache`/`no-store` controls, and `response_cost` field names were not read from a primary page.
- No head-to-head comparison of these frameworks for small custom multimodal benches was found.

## Q2. Experiment tracking light enough for a small lab

### Takeaway
All mainstream trackers are active in Nov 2026, except Sacred. For a solo or small-lab offline bench, the lightest-weight options are:
- **DVC experiments**: git-native, matching the existing git-tagged prereg and SHA-256 provenance.
- **Local MLflow or Aim**: a browsable run table with metrics and cost.

W&B is the most polished but hosted. Hydra solves run-variant config sprawl.

### Cited Findings
- **MLflow.** Apache-2.0, about 28.8k stars, last push 2026-11-11. Now describes itself as an AI engineering platform for agents and LLMs "while controlling costs". [GitHub](https://github.com/mlflow/mlflow)
  - Here: a local `mlruns/` store can log each replay run's config hash, cost, and metrics without a server.
- **Weights & Biases.** MIT client, about 11.3k stars, last push 2026-11-11. [GitHub](https://github.com/wandb/wandb)
  - Here: the best UI for comparing many variants. Hosted, so check data-sharing comfort before uploading frames.
- **Aim.** Apache-2.0, about 6.3k stars, last push 2026-11-07. A self-hosted, open-source experiment tracker. [GitHub](https://github.com/aimhubio/aim)
  - Here: a local alternative to W&B for a run table across many variants.
- **DVC.** Repo is now `treeverse/dvc`. Apache-2.0, about 16k stars, last push 2026-11-09. "Data Versioning and ML Experiments". [GitHub](https://github.com/treeverse/dvc)
  - Here: `dvc.yaml` stages with params and metrics files version the replay outputs and results JSON next to git tags. This is the closest fit to the prereg-tag workflow.
- **Hydra.** Repo is now `hydra-ecosystem/hydra`. MIT licence, about 10.7k stars, last push 2026-11-11. [GitHub](https://github.com/hydra-ecosystem/hydra)
  - Here: config composition and multirun sweeps would replace hand-built variant JSONs. Each resolved config can still be SHA-256 hashed.
- **Sacred.** Last push 2025-10-22, so it fails the 2026-activity bar. [GitHub](https://github.com/IDSIA/sacred)
  - Here: not recommended.
- **Metaflow.** Apache-2.0, last push 2026-11-09. [GitHub](https://github.com/Netflix/metaflow)
  - Here: workflow orchestration is overkill for an offline bench.

### Inferences
- The bench already writes run config JSON, a SHA-256 hash, and JSONL. The missing piece is an index across runs (variant, model, n, cost, metric, prereg tag). A tiny SQLite or CSV ledger, or a local MLflow store, gives that with the least new machinery.
- DVC plus Hydra keeps everything in git, which suits a prereg workflow where confirmatory runs must point to a tagged commit.

### Gaps
- Cost-tracking features of MLflow, W&B and Aim for LLM API calls were not read from primary docs. MLflow's "controlling costs" wording comes from its repo description only.

## Q3. Preregistration practice for ML/LLM evals, and statistics tooling for small-n paired comparison

### Takeaway
2026 has primary literature specifically on preregistering LLM and AI-agent experiments. It recommends locking prompts, decoding settings, model lists and evaluator prompts in advance. For the stats, question-level paired differences are the recommended framing. SciPy now provides paired bootstrap (BCa) and permutation tests, and statsmodels and pingouin cover McNemar and effect sizes.

### Cited Findings
- **"Preregistration for Experiments with AI Agents"** (Vaccaro), arXiv 2606.11217, ICML 2026 Spotlight position paper.
  - It lists the researcher degrees of freedom: model selection, prompt wording, settings, and redesign after seeing outcomes.
  - It proposes a preregistration template tailored to AI agent experiments; the template is inside the paper, not a separate tool. [arXiv](https://arxiv.org/abs/2606.11217)
  - Here: use its template fields as a checklist against the existing git-tagged prereg docs.
- **"Mitigating LLM-based p-Hacking by Preregistering for the Next LLM"** (Thomas, Gligoric, Shah), arXiv 2606.27687.
  - Protocol: preregister the analysis and a set of eligible future models, then run the confirmatory analysis on the first eligible model released after preregistration.
  - Across 20 models, the protocol blocked p-hack transfer in 73.9% and 72.7% of cases. [arXiv](https://arxiv.org/abs/2606.27687)
  - Here: directly usable. Name "the next Gemini/Claude/GPT release" in a prereg as the held-out confirmatory model.
- **Search-snippet-only 2026 papers** (not opened; treat with caution):
  - arXiv 2608.09942 (OSF-preregistered CoT study). [arXiv PDF](https://arxiv.org/pdf/2608.09942)
  - arXiv 2607.07184 (OSF prereg plus amendment). [arXiv PDF](https://arxiv.org/pdf/2607.07184)
  - arXiv 2609.04198 (preregistered campaigns finding black-box judge endpoint drift). [papers.cool](https://papers.cool/arxiv/2609.04198)
  - Here: endpoint drift argues for caching raw responses and recording endpoint/model version in provenance. The bench already does the caching.
- **Prereg registries.** OSF Preregistration [osf.io/prereg](https://osf.io/prereg/) and [COS prereg initiative](https://www.cos.io/initiatives/prereg) both resolved HTTP 200. AsPredicted [aspredicted.org](https://aspredicted.org/) returned HTTP 406 to an automated client, so it was not machine-verified.
  - Here: an OSF registration timestamps the prereg externally, complementing git tags, which can be re-pointed.
- **Miller, "Adding Error Bars to Evals"**, arXiv 2411.00640.
  - Recommends inference on question-level paired differences when comparing models.
  - Covers CLT standard errors, with the bootstrap needed only for complex estimators.
  - Covers variance reduction by resampling answers, and power analysis for whether an eval can test a hypothesis. [arXiv](https://arxiv.org/abs/2411.00640)
  - Here: with n=187 paired items, a power analysis tells whether a planned model comparison is even detectable before spending API credits.
- **SciPy.** `scipy.stats.bootstrap` supports `paired=True` and methods `'BCa'` (default), `'percentile'` and `'basic'` (SciPy 1.18.0 docs). [SciPy docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html). BSD-3, last push 2026-11-10. [GitHub](https://github.com/scipy/scipy)
  - Here: paired BCa CIs on per-item score differences need no new dependency.
- **statsmodels.** BSD-3, last push 2026-11-11. [GitHub](https://github.com/statsmodels/statsmodels)
  - Here: McNemar's exact test for paired binary correctness.
- **pingouin.** GPL-3.0, last push 2026-10-24. [GitHub](https://github.com/raphaelvallat/pingouin)
  - Here: convenient paired tests and effect sizes. The GPL licence matters if the bench is redistributed.

### Inferences
- For binary per-item outcomes (feasible/infeasible, correct strategy) across 2 models on the same 187 items:
  - Run McNemar's exact test on the discordant pairs.
  - Report a paired bootstrap CI on the accuracy difference.
  - Pre-specify both in the prereg doc before unblinding.
- Position-bias shuffles should be preregistered as part of the design: seed, number of permutations, and whether to condition on draw. This matches the existing presentation-order findings.

### Gaps
- No dedicated software tool was found that enforces "metric chosen before data" for ML evals. Enforcement is still a process: tag, hash and OSF timestamp. A CI check could refuse confirmatory runs whose analysis config hash is absent from a prereg tag (an inference, not a found tool).
- "Registered reports" tracks at ML venues were not researched in detail.

## Q4. Claude Code skills, plugins, subagents and MCP servers useful for this research codebase

### Takeaway
The official Anthropic plugin marketplace now lists 317 plugins. Of these:
- **Directly useful here:** `session-report` (token and cost visibility across sessions), `hookify` (guardrails as rules), `claude-md-management` (keeping CLAUDE.md and memory current), `pyright-lsp`, and `pr-review-toolkit`.
- **ROS2 MCP:** `robotmcp/ros-mcp-server` is the most active option.
- **Already configured, not new:** the paper-search MCP (its tools `search_papers`/`download_paper`/`read_paper` match `blazickjp/arxiv-mcp-server`), isaacsim-mcp, Context7, superpowers, and Anthropic's document skills.

### Cited Findings
- **Official skills repo `anthropics/skills`.** About 193k stars, last push 2026-11-06. Contains: academy-guide, algorithmic-art, brand-guidelines, canvas-design, claude-api, discernment-nudge, doc-coauthoring, docx, frontend-design, internal-comms, mcp-builder, pdf, pptx, skill-creator, slack-gif-creator, theme-factory, web-artifacts-builder, webapp-testing, xlsx. [GitHub](https://github.com/anthropics/skills)
  - Here: `mcp-builder` could scaffold a small MCP over the bench's results JSONL so sessions can query run outcomes. `skill-creator` and the doc skills are already installed in this environment.
- **Official plugin marketplace `anthropics/claude-plugins-official`.** Apache-2.0, last push 2026-11-11, 317 plugins in `marketplace.json`. [GitHub](https://github.com/anthropics/claude-plugins-official)
  - **`session-report`**: an explorable HTML report of session usage (tokens, cache efficiency, subagents, skills, most expensive prompts) built from `~/.claude/projects` transcripts. [marketplace](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/session-report)
    - Here: shows where Claude Code spend goes across the many sessions and worktrees.
  - **`hookify`**: custom hooks defined as markdown rules. [marketplace](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/hookify)
    - Here: could block edits to tagged prereg docs or confirmatory analysis configs, or warn before `git push` (both are existing memory rules).
  - **`claude-md-management`**: audits CLAUDE.md and captures session learnings. [marketplace](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-md-management)
    - Here: the MEMORY.md index is large and partly stale, so this helps keep it current.
  - **`claude-code-setup`**: recommends hooks, skills, MCP servers and subagents for a codebase. [marketplace](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-code-setup)
  - **`pyright-lsp`**: Python type checking. [marketplace](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/pyright-lsp)
    - Here: supports CLAUDE.md's full-type-hint rule.
  - **`pr-review-toolkit`** and **`code-review`**: multi-agent PR review. [marketplace](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/pr-review-toolkit)
  - **`project-artifact`**: a living project status page as a claude.ai artifact. [marketplace](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/project-artifact)
    - Here: could replace the hand-maintained "next actions" memory entries.
  - **External `serena`**: semantic code navigation via LSP. [marketplace](https://github.com/anthropics/claude-plugins-official/tree/main/external_plugins/serena)
- **ROS2 MCP servers.**
  - **`robotmcp/ros-mcp-server`**: Apache-2.0, about 1.5k stars, last push 2026-11-11. "Connect AI models like Claude & GPT with robots using MCP and ROS." [GitHub](https://github.com/robotmcp/ros-mcp-server)
    - Here: topic and service introspection for debugging Nav2 and orchestrator topics on the VM from a Claude session.
  - **`wise-vision/ros2_mcp`**: MPL-2.0, 99 stars, last push 2026-10-21. A README mirror says it supports Humble and Jazzy. [GitHub](https://github.com/wise-vision/ros2_mcp); [README mirror](https://cdn.jsdelivr.net/gh/wise-vision/mcp_server_ros_2@main/README.md)
    - Here: Jazzy support matches the Nav2 container.
  - **`Ranch-Hand-Robotics/rde-mcp-ros-2`**: 2 stars, last push 2026-01-25. [GitHub](https://github.com/Ranch-Hand-Robotics/rde-mcp-ros-2)
    - Here: low adoption; not recommended.
- **Notebook MCP.** `datalayer/jupyter-mcp-server`: BSD-3, about 1.3k stars, last push 2026-11-11. [GitHub](https://github.com/datalayer/jupyter-mcp-server)
  - Here: lets a session run and inspect bootstrap or McNemar analysis notebooks interactively.
- **Community collections.**
  - **`K-Dense-AI/scientific-agent-skills`**: MIT licence, about 57k stars, last push 2026-11-09. "177 ready-to-use validated skills" mostly for biology, chemistry and medicine. [GitHub](https://github.com/K-Dense-AI/scientific-agent-skills)
  - **`hesreallyhim/awesome-claude-code`**: about 58k stars, last push 2026-11-11. [GitHub](https://github.com/hesreallyhim/awesome-claude-code)
  - **`travisvn/awesome-claude-skills`**: last push 2026-04-28, so activity is lower. [GitHub](https://github.com/travisvn/awesome-claude-skills)
- **PDF to markdown.** `datalab-to/marker`: about 41k stars, last push 2026-11-11. [GitHub](https://github.com/datalab-to/marker)
  - Here: complements the existing paper MCP when papers must be converted for notes.
- **Already present in this environment (do not re-recommend):**
  - The paper-search MCP: tools `search_papers`, `download_paper`, `list_papers`, `read_paper`; likely [blazickjp/arxiv-mcp-server](https://github.com/blazickjp/arxiv-mcp-server), last push 2026-10-08.
  - isaacsim-mcp.
  - Context7 (`resolve-library-id`/`get-library-docs`).
  - `obra/superpowers` skills (last push 2026-11-03). [GitHub](https://github.com/obra/superpowers)
  - Anthropic docx/pdf/pptx/xlsx/skill-creator/deep-research skills.
  - usd-code-mcp (configured, but it failed to connect this session).
  - Project openspec skills in `.claude/skills`.

### Inferences
- The highest-leverage custom build is a project skill or subagent for the bench. It would:
  - check that a run config hash is listed in a prereg tag before a confirmatory run;
  - add the run to the ledger;
  - run the preregistered paired tests.

  No existing published skill does this; `skill-creator` can scaffold it.
- `hookify` plus `session-report` cover two pain points cheaply: prereg guardrails and cost across sessions.

### Gaps
- The `K-Dense-AI/scientific-agent-skills` directory layout could not be listed (API 404 on the guessed path). Whether it contains a statistics or experiment-design skill is unverified.
- No dedicated research was done on multi-session or worktree coordination tools beyond `session-report` and `hookify`. Community orchestration plugins exist in the awesome lists but were not vetted.
- No maintained W&B or MLflow MCP server was verified.
- The 317 marketplace entries were scanned only by name and description for the subset listed above.
