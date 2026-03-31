---
name: nightshift
description: Autonomous overnight code quality bot. 61 tasks across 7 categories with plan-implement-review architecture. Powered by GLM 5.1.
trigger: nightshift
---

# Nightshift v3

Full implementation of [marcus/nightshift](https://github.com/marcus/nightshift) for Hermes Agent. 61 task types, plan-implement-review architecture, budget tracking.

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

## Task Categories (7 categories, 61 tasks)

| Category | Tasks | Output | Review Loop |
|----------|-------|--------|-------------|
| pr | 17 | PR with code changes | Yes |
| analysis | 17 | Findings report | No |
| options | 11 | Options/suggestions | No |
| safe | 5 | Safe experiment results | No |
| map | 7 | Map/visualization | Yes (1 task) |
| emergency | 3 | Operational docs | No |
| review | 1 | PR with code review fixes | Yes |

### PR Tasks (17)
lint-fix, bug-finder, auto-dry, skill-groom, api-contract-verify, backward-compat, build-optimize, docs-backfill, commit-normalize, changelog-synth, release-notes, adr-draft, ci-fixes, dependency-updates, readme-improvements, dead-code, code-quality

### Analysis Tasks (17)
doc-drift, semantic-diff, dependency-risk, test-gap, test-flakiness, logging-audit, metrics-coverage, perf-regression, cost-attribution, security-footgun, pii-scanner, privacy-policy, schema-evolution, event-taxonomy, roadmap-entropy, bus-factor, knowledge-silo

### Options Tasks (11)
tech-debt-classify, why-annotator, edge-case-enum, error-msg-improve, slo-suggester, ux-copy-sharpener, a11y-lint, service-advisor, ownership-boundary, oncall-estimator, idea-generator

### Safe Tasks (5)
migration-rehearsal, contract-fuzzer, golden-path, perf-profile, allocation-profile

### Map Tasks (7)
visibility-instrument, repo-topology, permissions-mapper, data-lifecycle, feature-flag-monitor, ci-signal-noise, historical-context

### Emergency Tasks (3)
runbook-gen, rollback-plan, postmortem-gen

### Review Tasks (1)
code-review — Expert review + fixes using SOLID, security, perf, error handling checklists (references/ directory). Creates PR with fixes.

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
```bash
python3 ~/nightshift-workspace/nightshift.py
```
Parse NIGHTSHIFT_TASKS_START/NIGHTSHIFT_TASKS_END JSON array. Each task has:
- repo, task, task_name, task_description, category, cost_tier, cost_tokens_min/max
- prompt_type: "plan_implement_review" | "analysis"
- clone_dir, default_branch, branch_name, max_review_iterations, produces_pr, has_review

### STEP 2 — EXECUTE EACH TASK

**prompt_type = "plan_implement_review":**
1. **Plan** — delegate_task: "Analyze {clone_dir} and create a plan for {task_name}. {task_description}. Output JSON with steps, files, description."
2. **Implement** — delegate_task: "Execute plan in {clone_dir}. {task_description}. Rules: no formatters, no new deps, targeted changes only."
3. **Check** — git status --porcelain. If empty → "no changes", continue.
4. **Review** — delegate_task: "Review git diff in {clone_dir}. Check correctness, security, unintended changes. Output JSON: {passed, feedback, issues}"
5. If failed and iterations < max → implement again with feedback.
6. **PR** — branch, commit, push, `gh pr create`. Must use `--head BRANCH_NAME` because the main agent's working directory may not be on the feature branch (subagent commits on it).

**prompt_type = "analysis":**
- delegate_task with analysis prompt. Report findings. No PR.

**code-review task (plan_implement_review):**
- Load references/ checklists (solid-checklist.md, security-checklist.md, code-quality-checklist.md)
- Plan: analyze codebase using checklists, identify issues
- Implement: fix identified issues (SOLID violations, security risks, error handling gaps)
- Review: verify fixes are correct and don't introduce new issues
- Create PR with fixes

### STEP 3 — CLEANUP
```python
import shutil; shutil.rmtree("{clone_dir}")
```

### STEP 4 — REPORT
For each task: repo, task_name, category, result (PR URL / findings / no changes).

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
- **Delivery:** Discord
- **Model:** glm-5.1 (via api.z.ai, regular GLM_API_KEY, no Bearer prefix)
- **Tasks/run:** 3 (configurable)
- **Repeat:** forever

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

## Pitfalls

- rm -rf blocked. Use shutil.rmtree() via execute_code.
- No formatters (ruff format, biome format, prettier) — only lint fixes.
- No new deps — revert package.json/lockfile changes.
- Most repos are clean — analysis tasks more valuable than lint-only.
- Safe category tasks are expensive (500k-1M tokens) — use sparingly.
- Emergency tasks have 4-week cooldown for a reason.
- `gh pr create` requires `--head BRANCH_NAME` — the main agent runs from a different directory than the subagent that created the branch.
- Subagents may already commit changes before the main agent checks `git status --porcelain` — check `git log main..HEAD --oneline` instead to verify commits exist.
