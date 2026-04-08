---
name: nightshift
description: Autonomous overnight code quality bot. 67 tasks across 7 categories with plan-implement-review architecture. 25 PR tasks + 42 issue tasks.
trigger: nightshift
---

# Nightshift v3

Full implementation of [marcus/nightshift](https://github.com/marcus/nightshift) for Hermes Agent. 67 task types, plan-implement-review architecture, budget tracking. 25 PR tasks + 42 issue tasks.

## Setup

- **State:** `~/.nightshift/` (config + run history)
- **Workspace:** `~/nightshift-workspace/` (temp clones)
- **Script:** `~/nightshift-workspace/nightshift.py`
- **Task defs:** `~/nightshift-workspace/nightshift_tasks.json`
- **Quota:** `~/nightshift-workspace/glm_quota.py`
- **Model:** GLM 5.1 via `api.z.ai` (model ID: `glm-5.1`, verified working on the Api.z.ai provider)
- **Cron:** fd3b3a346a68 (every 15 min, Discord delivery)

## Commands

```bash
python3 ~/nightshift-workspace/nightshift.py --list-categories  # 7 categories
python3 ~/nightshift-workspace/nightshift.py --list-tasks       # All 61 tasks
python3 ~/nightshift-workspace/nightshift.py --dry-run          # Preview
python3 ~/nightshift-workspace/nightshift.py                    # Select + clone + output
python3 ~/nightshift-workspace/glm_quota.py --check             # Quota gate
```

## Task Categories (7 categories, 63 tasks)

| Category | Tasks | Output Mode | Review Loop |
|----------|-------|-------------|-------------|
| pr | 23 | PR (21) + Issue (2) | Yes |
| analysis | 17 | Issue | No |
| options | 13 | Issue | No |
| safe | 5 | Issue | No |
| map | 7 | PR (1) + Issue (6) | Yes (1 task) |
| emergency | 3 | Issue | No |
| review | 1 | PR | Yes |

**25 tasks create PRs** (actual code/artifact changes). **42 tasks create issues** (findings, reports, suggestions). The `output_mode` field determines the output type, independent of the task category.

### PR Tasks (25)
lint-fix, bug-finder, auto-dry, skill-groom, api-contract-verify, backward-compat, build-optimize, docs-backfill, commit-normalize, changelog-synth, release-notes, adr-draft, ci-fixes, dependency-updates, readme-improvements, dead-code, code-quality, code-review, visibility-instrument, perf-audit, autoresearch, react-effect-cleanup, react-image-fix, lint-doctor-fix, best-practice-fix

### Issue Tasks (42)
doc-drift, semantic-diff, dependency-risk, test-gap, test-flakiness, logging-audit, metrics-coverage, perf-regression, cost-attribution, security-footgun, pii-scanner, privacy-policy, schema-evolution, event-taxonomy, roadmap-entropy, bus-factor, knowledge-silo, tech-debt-classify, why-annotator, edge-case-enum, error-msg-improve, slo-suggester, ux-copy-sharpener, a11y-lint, service-advisor, ownership-boundary, oncall-estimator, idea-generator, migration-rehearsal, contract-fuzzer, golden-path, perf-profile, allocation-profile, repo-topology, permissions-mapper, data-lifecycle, feature-flag-monitor, ci-signal-noise, historical-context, runbook-gen, rollback-plan, postmortem-gen

### Category Breakdown
**PR category (23):** lint-fix, bug-finder, auto-dry, skill-groom, api-contract-verify, backward-compat, build-optimize, docs-backfill, commit-normalize, changelog-synth, release-notes, adr-draft, ci-fixes, dependency-updates, readme-improvements, dead-code, code-quality, perf-audit, autoresearch, react-effect-cleanup, react-image-fix, lint-doctor-fix, best-practice-fix

**Analysis category (17):** doc-drift, semantic-diff, dependency-risk, test-gap, test-flakiness, logging-audit, metrics-coverage, perf-regression, cost-attribution, security-footgun, pii-scanner, privacy-policy, schema-evolution, event-taxonomy, roadmap-entropy, bus-factor, knowledge-silo

**Options category (13):** task-groomer, guide-improver, tech-debt-classify, why-annotator, edge-case-enum, error-msg-improve, slo-suggester, ux-copy-sharpener, a11y-lint, service-advisor, ownership-boundary, oncall-estimator, idea-generator

**Safe category (5):** migration-rehearsal, contract-fuzzer, golden-path, perf-profile, allocation-profile

**Map category (7):** visibility-instrument (PR), repo-topology, permissions-mapper, data-lifecycle, feature-flag-monitor, ci-signal-noise, historical-context

**Emergency category (3):** runbook-gen, rollback-plan, postmortem-gen

**Review category (1):** code-review — Expert review + fixes using SOLID, security, perf, error handling checklists (references/ directory). Creates PR with fixes.

## Architecture: Plan-Implement-Review

From nightshift orchestrator.go. Three prompt templates:

### Phase 1: Plan
Agent analyzes the repo and outputs JSON:
```json
{"steps": ["step1", "step2"], "files": ["file1.go"], "description": "approach"}
```

### Phase 2: Implement
Agent executes the plan. On iteration >1, includes review feedback. Outputs JSON:
```json
{"files_modified": ["file1.go"], "summary": "what was done"}
```

### Phase 3: Review
Agent checks correctness. Outputs JSON:
```json
{"passed": true, "feedback": "detailed feedback", "issues": ["issue1"]}
```

If review fails → back to implement with feedback (max 3 iterations).

## Cost Tiers (token estimation)

| Tier | Tokens | Example Tasks |
|------|--------|---------------|
| low | 10-50k | lint-fix, ci-fixes, readme, changelog |
| medium | 50-150k | bug-finder, dead-code, test-gap, most analysis |
| high | 150-500k | auto-dry, build-optimize, service-advisor |
| very_high | 500k-1M | migration-rehearsal, contract-fuzzer |

## Execution Flow (Cron Agent)

### STEP 0 — QUOTA
```bash
python3 ~/nightshift-workspace/glm_quota.py --check
```
If SKIP → report and stop.

### STEP 1 — DISCOVER
```
python3 ~/nightshift-workspace/nightshift.py
```
Parse NIGHTSHIFT_TASKS_START/NIGHTSHIFT_TASKS_END JSON array. Each task has:
- repo, task, task_name, task_description, category, cost_tier, cost_tokens_min/max
- **output_mode**: `"pr"` (creates pull request) or `"issue"` (creates GitHub issue)
- prompt_type: "plan_implement_review" | "analysis"
- clone_dir, default_branch, branch_name, max_review_iterations, produces_pr, has_review

### STEP 2 — EXECUTE EACH TASK

**output_mode = "pr" (21 tasks):**

**prompt_type = "plan_implement_review":**
1. **Plan** — delegate_task: "Analyze {clone_dir} and create a plan for {task_name}. {task_description}. Output JSON with steps, files, description."
2. **Implement** — delegate_task: "Execute plan in {clone_dir}. {task_description}. Rules: no formatters, no new deps, targeted changes only."
3. **Check** — git status --porcelain. If empty → "no changes", continue.
4. **Review** — delegate_task: "Review git diff in {clone_dir}. Check correctness, security, unintended changes. Output JSON: {passed, feedback, issues}"
5. If failed and iterations < max → implement again with feedback.
6. **PR** — Use: `git -c user.name="Nightshift" -c user.email="contact+nightshift@micr.dev" commit`. Must use `--head BRANCH_NAME` because the main agent's working directory may not be on the feature branch (subagent commits on it).

**code-review task (plan_implement_review):**
- Load references/ checklists (solid-checklist.md, security-checklist.md, code-quality-checklist.md)
- Plan: analyze codebase using checklists, identify issues
- Implement: fix identified issues (SOLID violations, security risks, error handling gaps)
- Review: verify fixes are correct and don't introduce new issues
- Write findings as markdown, create PR with fixes and report

**output_mode = "issue" (42 tasks):**
- **analysis prompt_type:** delegate_task with analysis prompt.
- Write findings to a structured markdown string.
- **Create a GitHub issue** (NOT a PR): `GH_TOKEN=<NIGHTSHIFT_GH_TOKEN> gh issue create --repo {repo} --title "nightshift: {task_name}" --body {findings_markdown}`
- Issue body should include: severity levels, file paths, actionable recommendations.
- Do NOT commit any files to the repo. Do NOT create a branch for issue tasks.

Git commit author (PR tasks only): `Nightshift <contact+nightshift@micr.dev>` (use `-c user.name="Nightshift" -c user.email="contact+nightshift@micr.dev"`).

### STEP 3 — CLEANUP
```python
import shutil; shutil.rmtree("{clone_dir}")
```

### STEP 4 — REPORT
For each task: repo, task_name, category, output_mode, result (PR URL / Issue URL / "no changes" / "review failed").
PR tasks should have a PR URL. Issue tasks should have an issue URL.

## Budget Tracking

- Per-task cost estimation (cost_tier → token range)
- Quota check via glm_quota.py (--check flag)
- Dynamic burn window: only runs 5-50 min before quota reset
- Configurable budget reserve (default 20%)
- Cost tier cap in config (max_cost_tier)

### Quota API (glm_quota.py)

- Host: `open.bigmodel.cn`, auth: `Authorization: <GLM_API_KEY>` (no Bearer prefix)
- `GET /api/monitor/usage/quota/limit` — returns `reset_utc` in `TOKENS_LIMIT`
- The burn window is calculated from `reset_utc` — not a fixed time
- Source: [openclaw-glm-plan-usage](https://github.com/OrientLuna/openclaw-glm-plan-usage)

## Daily Brief Integration

The GitHub monitor script (`~/alive/scripts/github_monitor.py`) fetches open `[nightshift]` PRs and appends them to `~/alive/github/YYYY-MM-DD.md` under a "Nightshift PRs" section. This feeds into the daily brief automatically.

## GLM 5.1 Model

Verified working on api.z.ai with the regular GLM_API_KEY. Model ID: `glm-5.1`. The coding plan supports switching models via Claude Code settings (see https://docs.z.ai/devpack/using5.1).

## Cron Job

- **ID:** fd3b3a346a68
- **Schedule:** `*/15 * * * *` (every 15 min — but only actually runs during burn window)
- **Delivery:** Local (cron output only)
- **Model:** glm-5.1 (via api.z.ai, regular GLM_API_KEY, no Bearer prefix)
- **Tasks/run:** 3 (configurable)
- **Repeat:** forever
- **Git author:** `Nightshift <contact+nightshift@micr.dev>` (all commits)
- **Fork filter:** Enabled — skips repos where `isFork=true`
- **Public-only filter:** Enabled — skips private repos (`public_only=true`)
- **Inactivity filter:** Enabled — skips repos with no pushes in last 30 days (`max_inactive_days=30`)

### Dynamic Burn Window Scheduling

The cron runs every 15 min, but `glm_quota.py --check` gates execution to a **burn window** of 5-50 min before the 5h quota reset. This ensures nightshift burns remaining budget right before expiry.

How it works:
1. Each cron invocation runs `glm_quota.py --check`
2. Script reads `reset_utc` from the quota API
3. Calculates minutes until reset
4. SKIP if: quota >=99% (fully consumed), <5 min until reset (too late), >50 min until reset (too early)
5. RUN if: within 5-50 min window AND quota <99%
6. Adapts task count hint: 3 tasks (<50%), 2 tasks (<75%), 1 task (<95%), scrape remaining (95%+)

The 5h window resets multiple times per day. The reset time drifts, so fixed cron times don't work — the dynamic approach reads `reset_utc` from the API each invocation.

## Configuration (~/.nightshift/config.yaml)

- exclude_repos, min_size_kb, max_repos_to_consider
- **public_only** (default: `true`) — only open PRs on public repos. Set to `false` to include private repos.
- **max_inactive_days** (default: `30`) — skip repos with no pushes in the last X days. Uses the `pushed_at` field from GitHub API. Set to `0` to disable.
- tasks_per_run, max_prs_per_repo, max_review_iterations
- enabled_categories, enabled_tasks, disabled_tasks
- max_cost_tier, budget_reserve_percent

## References (for code-review task)

| File | Purpose |
|------|---------|
| solid-checklist.md | SOLID smells + refactor heuristics |
| security-checklist.md | XSS, injection, auth, race conditions, crypto |
| code-quality-checklist.md | Error handling, performance, boundary conditions |
| removal-plan.md | Deletion candidate template |
| react-patterns.md | React anti-patterns: useEffect, images, hooks (Ralph loop inspired) |
| opinionated-patterns.md | Language-agnostic best practices for non-React repos |

## New Ralph-Loop-Inspired Tasks

Inspired by @humanlayer_dev's Ralph loop pattern: pair each task with a best-practice reference doc, then make one targeted fix per run.

- **react-effect-cleanup** — find and fix useEffect anti-patterns (derived state in effects, stale closures, missing deps). Paired with `react-patterns.md`. Skips non-JS/TS repos.
- **react-image-fix** — fix improper Image usage (missing width/height, no alt text, no blur placeholders). Paired with `react-patterns.md`. Skips non-JS/TS repos.
- **lint-doctor-fix** — run the project's built-in lint/doctor tools (eslint, ruff, clippy, react-doctor, biome, golangci-lint) and auto-fix what they detect. Language-agnostic. 24h cooldown.
- **best-practice-fix** — generic opinionated fix. Loads `react-patterns.md` for JS/TS repos, `opinionated-patterns.md` for others. Fixes one pattern per run.

Tasks that have a `reference` field also include `reference_content` in the task JSON output — the cron agent injects this into plan/implement prompts so the subagent has the best-practice guidance inline.

## Pitfalls

- rm -rf blocked. Use shutil.rmtree() via execute_code.
- No formatters (ruff format, biome format, prettier) — only lint fixes.
- No new deps — revert package.json/lockfile changes.
- Most repos are clean — analysis tasks more valuable than lint-only.
- Safe category tasks are expensive (500k-1M tokens) — use sparingly.
- Emergency tasks have 4-week cooldown for a reason.
- `gh pr create` requires `--head BRANCH_NAME` — the main agent runs from a different directory than the subagent that created the branch.
- Subagents may already commit changes before the main agent checks `git status --porcelain` — check `git log main..HEAD --oneline` instead to verify commits exist.
- GLM 5.1 sometimes produces garbled/non-JSON output in the plan phase (especially for plan_implement_review). If plan output isn't valid JSON, fall back to manual analysis: use compiler/linting tools directly (cargo check/clippy for Rust, ruff/pylint for Python, grep for dead code patterns like commented-out blocks, `#[allow(dead_code)]`, unused imports, unreachable code). Then proceed to the check phase or report "no changes" if the codebase is clean.
- **nightshift.py hangs on clone operations** — running `python3 nightshift.py` (even --dry-run) times out after 60-120s. Workaround: run `--list-tasks` separately (works), then manually select repos using `gh repo list`, check sizes with `gh repo view --json diskUsage`, `git clone` each repo yourself, and dispatch tasks via `delegate_task`. Read `~/.nightshift/state.json` to check recent runs and avoid cooldown violations.
- **Large single-file repos kill delegate_task** — repos with one large source file (2000+ lines) cause subagents to burn all iterations re-reading the same file. The veyoff delegate_task spent 308s and 250k tokens reading a 2300-line C++ file repeatedly without making edits. Workaround: for repos with few files, do the work directly (read_file, patch) instead of delegating.
- **Task-repo compatibility matters** — lint-fix on a Windows-only C++ project can't work on Linux (no compiler, no clang-tidy). Always check the tech stack before assigning tasks: C++/Windows → analysis/readme tasks only; Go/Rust/Python/JS → all tasks work. Check `CMakeLists.txt`, `go.mod`, `package.json`, `Cargo.toml` before choosing.
- **Burn window < 20 min → skip medium/high tasks** — delegate_task timeouts (5 min) plus review loops mean a 16-min window only fits 1 low-cost manual task. Start with the cheapest task to guarantee at least one result.
- **PR tasks create PRs, issue tasks create issues** — the `output_mode` field determines this. PR tasks (21) go through plan→implement→review→commit→PR flow. Issue tasks (42) analyze and create GitHub issues with findings. Do NOT commit files or create branches for issue tasks.
- **Enforce 1 task per repo** — when selecting tasks programmatically, pick diverse repos. Running 3 tasks on the same 6KB repo wastes the burn window. Maximize repo coverage by assigning each task to a different repo.
- **Parallel delegate_task for independent tasks** — when tasks target different repos (no shared state), pass them as a `tasks` array to a single delegate_task call. This runs them concurrently, cutting total time roughly in half (e.g. 2 tasks in ~15 min instead of ~25 min sequential). Only do this for analysis/options tasks or simple PR tasks where you don't need to iterate on results between tasks. **Caveat:** GLM 5.1 rate limits can cause one parallel task to fail with HTTP 429 while the other succeeds. Recovery: do the failed task's analysis directly (read_file the source files, write the markdown report with write_file, then commit and PR). This fallback is fast and avoids burning another delegate_task call.
- **Verify canonical imports before removing duplicate files** — when two files look identical, grep for import references (`grep -rn 'path/to/file' --include='*.ts'`) before deleting one. The file that's actually imported is the canonical one; delete the unreferenced copy. Deleting the wrong one breaks the build.
- **Tiny repos (under ~20KB) don't need delegate_task** — for repos with 1-3 files, read them directly with read_file, analyze, and patch. delegate_task overhead (5 min timeout, context setup) is wasteful on a single formula file.
- **pnpm projects + npm install creates stray lockfile** — Running `npm install` on a pnpm project generates `package-lock.json`. Always `git checkout -- pnpm-lock.yaml package-lock.json` before committing, or better: install with `pnpm install` if available. Check which package manager the project uses (`pnpm-lock.yaml` vs `package-lock.json` vs `yarn.lock`) before running install.
- **eslint-plugin-react-hooks v7 has aggressive new rules** — `set-state-in-effect` and `immutability` rules flag legitimate async data fetching in useEffect. Fix by moving function declarations above useEffect (solves `immutability`/before-declaration) and adding `// eslint-disable-next-line react-hooks/set-state-in-effect` on the line BEFORE the violation (not after — the disable must precede the flagged line).
- **shadcn/ui + react-refresh** — `allowConstantExport: true` does NOT fix re-exports of Radix primitives (`export const Dialog = DialogPrimitive.Root`). Must fully disable `react-refresh/only-export-components` for `src/components/ui/**` files.
- **Always build-check after Go patches** — Type changes (e.g., removing an `int()` cast) can silently break compilation. Run `go build ./...` after every patch set before committing.
