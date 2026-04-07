# hermes-nightshift-glm

overnight code quality bot for hermes agent. 61 tasks, plan-implement-review, powered by glm 5.1.

## install

```bash
mkdir -p ~/nightshift-workspace ~/.nightshift ~/.hermes/skills/nightshift/references

# get the files
curl -sL https://raw.githubusercontent.com/Microck/hermes-nightshift-glm/main/nightshift.py > ~/nightshift-workspace/nightshift.py
curl -sL https://raw.githubusercontent.com/Microck/hermes-nightshift-glm/main/nightshift_tasks.json > ~/nightshift-workspace/nightshift_tasks.json
curl -sL https://raw.githubusercontent.com/Microck/hermes-nightshift-glm/main/glm_quota.py > ~/nightshift-workspace/glm_quota.py

# install skill
curl -sL https://raw.githubusercontent.com/Microck/hermes-nightshift-glm/main/SKILL.md > ~/.hermes/skills/nightshift/SKILL.md
curl -sL https://raw.githubusercontent.com/Microck/hermes-nightshift-glm/main/references/solid-checklist.md > ~/.hermes/skills/nightshift/references/solid-checklist.md
curl -sL https://raw.githubusercontent.com/Microck/hermes-nightshift-glm/main/references/security-checklist.md > ~/.hermes/skills/nightshift/references/security-checklist.md
curl -sL https://raw.githubusercontent.com/Microck/hermes-nightshift-glm/main/references/code-quality-checklist.md > ~/.hermes/skills/nightshift/references/code-quality-checklist.md
curl -sL https://raw.githubusercontent.com/Microck/hermes-nightshift-glm/main/references/removal-plan.md > ~/.hermes/skills/nightshift/references/removal-plan.md
```

## setup

get a glm coding plan key from open.bigmodel.cn:

```bash
export GLM_API_KEY="your-key"
```

or add to `~/.hermes/.env`:
```
GLM_API_KEY=your-key
```

## usage

check quota and preview:
```bash
python3 ~/nightshift-workspace/glm_quota.py --check
python3 ~/nightshift-workspace/nightshift.py --dry-run
```

run:
```bash
python3 ~/nightshift-workspace/nightshift.py
```

schedule with hermes cron:
```bash
hermes cron create "nightshift" --skill nightshift --schedule "*/15 * * * *" --model glm-5.1 --deliver discord
```

## tasks

61 tasks across 7 categories. pr tasks create actual pull requests. analysis tasks just report findings.

| category | tasks | output |
|----------|-------|--------|
| pr | 17 | PR with code changes |
| analysis | 17 | findings report |
| options | 11 | suggestions |
| safe | 5 | experiment results |
| map | 7 | visualization (some PR) |
| emergency | 3 | operational docs |
| review | 1 | PR with review fixes |

pr tasks: lint-fix, bug-finder, auto-dry, skill-groom, api-contract-verify, backward-compat, build-optimize, docs-backfill, commit-normalize, changelog-synth, release-notes, adr-draft, ci-fixes, dependency-updates, readme-improvements, dead-code, code-quality

code-review: finds solid violations, security issues, perf problems, error handling gaps. creates PR with fixes.

## how it works

pr tasks go through plan -> implement -> review loop:
1. plan: analyze repo, output json with steps
2. implement: make targeted changes
3. review: check correctness and security
4. if review fails, back to implement (max 3 loops)
5. create PR

quota gating: runs 5-50 min before reset to burn remaining budget. skips if quota >=99% or outside that window.

runtime hygiene:
- stale clone directories are removed on startup before new work begins
- state entries older than the longest task cooldown are pruned automatically
- quota responses are cached for 5 minutes to avoid hitting the GLM monitor API on every cron poll

## config

optional `~/.nightshift/config.yaml`:
```yaml
exclude_repos:
  - "*-backup"
tasks_per_run: 3
max_prs_per_repo: 2
max_cost_tier: "very_high"
```

nightshift validates config keys and types on load and fails fast with a clear error if `config.yaml` is malformed.

## files

- `nightshift.py` - repo discovery, task selection
- `nightshift_tasks.json` - 61 task definitions
- `glm_quota.py` - quota check via zhipu api
- `SKILL.md` - hermes skill
- `references/*.md` - review checklists

---

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
