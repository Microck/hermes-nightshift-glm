<p align="center">
  <img src="https://litter.catbox.moe/0ukv28xe0omhwwcg.png" alt="hermes-nightshift-glm" width="600">
</p>

<p align="center">
  autonomous overnight code quality bot. 63 tasks, plan-implement-review, 21 PR tasks + 42 issue tasks.
</p>

<p align="center">
  <a href="https://github.com/Microck/hermes-nightshift-glm/releases"><img src="https://img.shields.io/github/v/release/Microck/hermes-nightshift-glm?display_name=tag&style=flat-square&label=release&color=000000" alt="release badge"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-mit-000000?style=flat-square" alt="license badge"></a>
</p>

---

`nightshift` runs on a cron schedule during GLM's quota burn window, selects from your public GitHub repos, and autonomously executes code quality tasks. it picks a repo, clones it, delegates to a coding agent that plans → implements → reviews, then opens a PR or issue depending on the task type.

63 tasks across 7 categories:

- **PR tasks (21):** lint fixes, bug finder, DRY refactoring, dead code removal, CI fixes, dependency updates, code review, perf audit, autoresearch experiment loop
- **Issue tasks (42):** doc drift detection, dependency risk scanner, test gap analysis, security footgun finder, PII exposure scanner, tech debt classifier, and more

[github](https://github.com/Microck/hermes-nightshift-glm)

## why

if you have repos sitting idle and want a bot that actually opens PRs and issues with useful findings while you sleep, this gives you a practical path.

- autonomous plan-implement-review loop with retry on failed reviews
- dynamic burn window scheduling reads `reset_utc` from the GLM quota API and only runs 5-50 min before the 5h rolling reset
- per-task token cost estimation (low/medium/high/very-high tiers)
- fork-based PR flow via a separate bot account so your main repo timestamps stay clean
- public-only + inactivity filters skip private and stale repos
- customizable config: enable/disable categories, cap cost tiers, set intervals per task

## quickstart

requires a GLM coding plan key (free from open.bigmodel.cn)

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

| category | tasks | output |
|----------|-------|--------|
| pr | 19 | PR (17) + Issue (2) |
| analysis | 17 | issue |
| options | 13 | issue |
| safe | 5 | issue |
| map | 7 | PR (1) + Issue (6) |
| emergency | 3 | issue |
| review | 1 | PR |

PR tasks go through plan → implement → review loop and create pull requests with code changes. issue tasks analyze and create github issues with findings, no commits or branches.

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
```

## files

- `nightshift.py` - repo discovery, task selection, output generation
- `nightshift_tasks.json` - 63 task definitions with output_mode
- `glm_quota.py` - quota check via zhipu API
- `SKILL.md` - hermes agent skill doc
- `references/*.md` - code review checklists

## license

[mit license](LICENSE)
