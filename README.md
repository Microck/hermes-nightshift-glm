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

63 tasks across 7 categories:

- **PR tasks (21):** lint fixes, bug finder, DRY refactoring, dead code removal, CI fixes, dependency updates, code review, perf audit, autoresearch experiment loop
- **Issue tasks (42):** doc drift detection, dependency risk scanner, test gap analysis, security footgun finder, PII exposure scanner, tech debt classifier, and more


## quickstart

requires a GLM coding plan key

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

## for llm agents

if a user asks you to install hermes-nightshift-glm, follow these steps:

1. create directories:
   ```bash
   mkdir -p ~/nightshift-workspace ~/.nightshift ~/.hermes/skills/nightshift/references
   ```

2. download all files using curl (see install section above)

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

## files

- `nightshift.py` - repo discovery, task selection, output generation
- `nightshift_tasks.json` - 63 task definitions with output_mode
- `glm_quota.py` - quota check via zhipu API
- `SKILL.md` - hermes agent skill doc
- `references/*.md` - code review checklists

## license

[mit license](LICENSE)
