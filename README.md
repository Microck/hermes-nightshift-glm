<div align="center">
  <img src="https://litter.catbox.moe/0ukv28xe0omhwwcg.png" alt="hermes-nightshift-glm" width="300">

<h1>hermes-nightshift-glm</h1>
</div>

<p align="center">
  autonomous overnight code quality bot. 63 tasks, plan-implement-review, 21 PR tasks + 42 issue tasks.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-mit-000000?style=flat-square" alt="license badge"></a>
</p>

---

`nightshift` runs on a cron schedule during GLM's quota burn window, selects from your public GitHub repos, and autonomously executes code quality tasks. it picks a repo, clones it, delegates to a coding agent that plans → implements → reviews, then opens a PR or issue depending on the task type.

## how it works

1. **quota gate** — checks GLM token quota. only runs in the burn window (5–50 min before quota reset)
2. **discover** — lists your public, non-fork, non-archived repos with recent pushes
3. **select** — picks tasks based on cooldowns, cost tiers, and recent run history
4. **execute** — clones the repo, runs the task via a coding agent (GLM 5.1)
5. **output** — PR tasks: commit + fork + pull request. Issue tasks: analysis + github issue
6. **cleanup** — deletes the clone, logs the run to state

all commits are authored as `Nightshift <contact+nightshift@micr.dev>`. PRs and issues come from a bot github account (not your personal account) to keep repo activity clean.

## architecture

PR tasks use a **plan → implement → review** loop:

```
plan ──→ implement ──→ git diff check ──→ review ──→ PR
              ↑                              │
              └──── retry (max 3×) ←──────── failed
```

- **plan** — agent analyzes the repo, outputs JSON with steps/files
- **implement** — agent makes targeted code changes (no formatters, no new deps)
- **review** — agent checks correctness, security, unintended changes. if review fails, loops back to implement with feedback (up to 3 iterations)

issue tasks are **analysis only** — no branches, no commits. the agent reads the codebase and writes a structured markdown report with severity levels (P0–P3), file paths, and actionable recommendations.

## quickstart

requires a GLM coding plan key from [open.bigmodel.cn](https://open.bigmodel.cn)

```bash
mkdir -p ~/nightshift-workspace ~/.nightshift
curl -sL https://raw.githubusercontent.com/Microck/hermes-nightshift-glm/main/nightshift.py > ~/nightshift-workspace/nightshift.py
curl -sL https://raw.githubusercontent.com/Microck/hermes-nightshift-glm/main/nightshift_tasks.json > ~/nightshift-workspace/nightshift_tasks.json
curl -sL https://raw.githubusercontent.com/Microck/hermes-nightshift-glm/main/glm_quota.py > ~/nightshift-workspace/glm_quota.py
```

set your key in `~/.hermes/.env`:
```
GLM_API_KEY=your-key
```

check quota, preview, run:
```bash
python3 ~/nightshift-workspace/glm_quota.py --check
python3 ~/nightshift-workspace/nightshift.py --dry-run
python3 ~/nightshift-workspace/nightshift.py
```

schedule with hermes agent cron:
```bash
hermes cron create "nightshift" --skill nightshift --schedule "*/15 * * * *" --model glm-5.1 --deliver discord
```

## tasks

63 tasks across 7 categories. 21 create pull requests with code changes, 42 create github issues with analysis findings.

### PR tasks (21) — create pull requests

| task | description | cost |
|------|-------------|------|
| lint-fix | fix linting errors and style issues | low |
| bug-finder | identify and fix potential bugs | high |
| auto-dry | refactor duplicate code | high |
| skill-groom | clean up and organize skill configs | medium |
| api-contract-verify | verify API contracts and schemas | medium |
| backward-compat | check backward compatibility | medium |
| build-optimize | optimize build configuration | high |
| docs-backfill | fill in missing documentation | medium |
| commit-normalize | normalize commit messages | low |
| changelog-synth | synthesize changelogs from git history | low |
| release-notes | generate release notes | low |
| adr-draft | draft architecture decision records | medium |
| ci-fixes | fix CI pipeline issues | low |
| dependency-updates | update dependencies | medium |
| readme-improvements | improve README quality | low |
| dead-code | remove dead/unused code | medium |
| code-quality | improve code quality patterns | medium |
| code-review | expert review + fixes (SOLID, security, perf) | medium |
| visibility-instrument | add observability instrumentation | high |
| perf-audit | audit and fix performance issues | high |
| autoresearch | automated research experiment loop | high |

### issue tasks (42) — create github issues

<details>
<summary><strong>analysis (17 tasks)</strong></summary>

doc-drift, semantic-diff, dependency-risk, test-gap, test-flakiness, logging-audit, metrics-coverage, perf-regression, cost-attribution, security-footgun, pii-scanner, privacy-policy, schema-evolution, event-taxonomy, roadmap-entropy, bus-factor, knowledge-silo

</details>

<details>
<summary><strong>options (13 tasks)</strong></summary>

task-groomer, guide-improver, tech-debt-classify, why-annotator, edge-case-enum, error-msg-improve, slo-suggester, ux-copy-sharpener, a11y-lint, service-advisor, ownership-boundary, oncall-estimator, idea-generator

</details>

<details>
<summary><strong>safe (5 tasks)</strong> — expensive, use sparingly</summary>

migration-rehearsal, contract-fuzzer, golden-path, perf-profile, allocation-profile

</details>

<details>
<summary><strong>map (7 tasks)</strong></summary>

visibility-instrument (PR), repo-topology, permissions-mapper, data-lifecycle, feature-flag-monitor, ci-signal-noise, historical-context

</details>

<details>
<summary><strong>emergency (3 tasks)</strong> — 4-week cooldown</summary>

runbook-gen, rollback-plan, postmortem-gen

</details>

## quota & burn window

GLM operates on a 5-hour rolling quota. nightshift only runs in a **burn window** of 5–50 minutes before quota reset to maximize value from remaining budget:

- **< 50% used** → up to 3 tasks
- **< 75% used** → up to 2 tasks
- **< 95% used** → 1 task
- **≥ 95% used** → scrape remaining with cheapest tasks only

the cron runs every 15 min but the quota gate means it only actually executes during the burn window. the reset time drifts, so the dynamic check adapts automatically.

## config

optional `~/.nightshift/config.yaml`:
```yaml
exclude_repos:
  - "*-backup"
tasks_per_run: 3
max_prs_per_repo: 2
max_cost_tier: "very_high"
public_only: true
max_inactive_days: 30
enabled_categories:
  - pr
  - analysis
  - options
```

| option | default | description |
|--------|---------|-------------|
| `exclude_repos` | `[]` | repo name patterns to skip |
| `tasks_per_run` | `3` | max tasks per cron invocation |
| `max_prs_per_repo` | `2` | max open nightshift PRs per repo |
| `max_cost_tier` | `very_high` | highest cost tier to run |
| `public_only` | `true` | only run on public repos |
| `max_inactive_days` | `30` | skip repos with no recent pushes |
| `enabled_categories` | all | restrict to specific categories |

## bot account setup

nightshift operates from a separate github account to keep your repos' "last updated" timestamps clean:

1. create a github account for the bot (e.g. `nightshift-micr`)
2. generate a personal access token with `repo` and `read:org` scopes
3. save the token: `echo "ghp_..." > ~/.nightshift/.gh-token-nightshift`
4. nightshift forks repos under the bot account, pushes branches there, and opens PRs from the fork

all PRs and issues will appear as authored by the bot account.

## files

| file | description |
|------|-------------|
| `nightshift.py` | repo discovery, task selection, output generation |
| `nightshift_tasks.json` | 63 task definitions with output_mode, cost tier, cooldown |
| `glm_quota.py` | quota check via zhipu API with burn window calculation |
| `SKILL.md` | hermes agent skill documentation |
| `references/*.md` | code review checklists (SOLID, security, code quality) |

## for llm agents

if a user asks you to install hermes-nightshift-glm, follow these steps:

1. create directories:
   ```bash
   mkdir -p ~/nightshift-workspace ~/.nightshift ~/.hermes/skills/nightshift/references
   ```

2. download all files using curl (see quickstart section above)

3. ask user for `GLM_API_KEY` or check if it exists in `~/.hermes/.env`. if missing, user needs to get one from open.bigmodel.cn

4. verify installation:
   ```bash
   python3 ~/nightshift-workspace/glm_quota.py --check
   ```
   should show quota status or error if key is missing

5. test dry run:
   ```bash
   python3 ~/nightshift-workspace/nightshift.py --dry-run
   ```
   should show selected repos/tasks

done. user can now run nightshift manually or schedule it via hermes cron.

## license

[mit license](LICENSE)
