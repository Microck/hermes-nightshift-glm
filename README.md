# Hermes Nightshift GLM

Autonomous overnight code quality bot for Hermes Agent. 61 task types across 7 categories with plan-implement-review architecture. Powered by GLM 5.1 via api.z.ai.

## Features

- **61 task types** across 7 categories: PR, Analysis, Options, Safe, Map, Emergency, Review
- **Plan-Implement-Review architecture** for code changes
- **Dynamic quota gating** — runs during burn window (5-50 min before reset) to maximize budget usage
- **Automatic PR creation** for applicable tasks
- **Daily brief integration** — PRs appear in your Hermes daily brief

## Installation

```bash
# Clone the repo
git clone https://github.com/Microck/hermes-nightshift-glm.git
cd hermes-nightshift-glm

# Copy files to workspace
mkdir -p ~/nightshift-workspace
cp nightshift.py nightshift_tasks.json glm_quota.py ~/nightshift-workspace/

# Install the skill
mkdir -p ~/.hermes/skills/nightshift/references
cp SKILL.md ~/.hermes/skills/nightshift/
cp references/*.md ~/.hermes/skills/nightshift/references/
```

## Setup

1. **GLM API Key** — Get a key from [open.bigmodel.cn](https://open.bigmodel.cn) (GLM Coding Plan)

```bash
export GLM_API_KEY="your-api-key"
```

Or add to `~/.hermes/.env`:
```
GLM_API_KEY=your-api-key
```

2. **Create state directory**:
```bash
mkdir -p ~/.nightshift
```

3. **Optional config** — Create `~/.nightshift/config.yaml`:
```yaml
exclude_repos:
  - "*-backup"
  - "testweb"
min_size_kb: 10
tasks_per_run: 3
max_prs_per_repo: 2
max_review_iterations: 3
max_cost_tier: "very_high"
```

## Usage

### Manual run

```bash
python3 ~/nightshift-workspace/glm_quota.py --check  # Check quota status
python3 ~/nightshift-workspace/nightshift.py --dry-run  # Preview tasks
python3 ~/nightshift-workspace/nightshift.py  # Run tasks
```

### Scheduled (Cron)

Add a cron job via Hermes:

```bash
hermes cron create "Run Nightshift" --skill nightshift --schedule "*/15 * * * *" --model glm-5.1 --deliver discord
```

## Task Categories

| Category | Tasks | Output | Review Loop |
|----------|-------|--------|-------------|
| pr | 17 | PR with code changes | Yes |
| analysis | 17 | Findings report | No |
| options | 11 | Options/suggestions | No |
| safe | 5 | Safe experiment results | No |
| map | 7 | Map/visualization | Yes (1 task) |
| emergency | 3 | Operational docs | No |
| review | 1 | PR with code review fixes | Yes |

### PR Tasks
lint-fix, bug-finder, auto-dry, skill-groom, api-contract-verify, backward-compat, build-optimize, docs-backfill, commit-normalize, changelog-synth, release-notes, adr-draft, ci-fixes, dependency-updates, readme-improvements, dead-code, code-quality

### Code Review Task
Expert review using SOLID, security, performance, and error handling checklists. Creates PR with fixes.

## Architecture

Each PR task follows Plan-Implement-Review:

1. **Plan** — Analyze repo, output JSON with steps/files/description
2. **Implement** — Execute plan, make targeted changes
3. **Review** — Check correctness, security, unintended changes
4. **PR** — Branch, commit, push, create PR

If review fails → back to implement (max 3 iterations).

## Quota Gating

Runs only during the burn window (5-50 min before quota reset) to maximize budget value:

- **<99% quota** + **within window** → RUN
- **>=99% quota** → SKIP (fully consumed)
- **Outside window** → SKIP (wait for optimal timing)

## Files

| File | Purpose |
|------|---------|
| `nightshift.py` | Main script — repo discovery, task selection, JSON output |
| `nightshift_tasks.json` | 61 task definitions with category, cost tier, interval |
| `glm_quota.py` | Quota check via Zhipu monitor API |
| `SKILL.md` | Hermes skill definition |
| `references/*.md` | Code review checklists (SOLID, security, quality) |

## License

MIT