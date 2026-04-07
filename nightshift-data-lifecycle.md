# Nightshift Data Lifecycle Analysis

## Overview

Traces data flow through the hermes-nightshift-glm system: from configuration loading through task discovery, execution, and state persistence.

## Data Entities

### 1. Configuration (config.yaml)
- **Source:** `~/.nightshift/config.yaml`
- **Lifecycle:** Read at startup by `_load_config()`. Never written programmatically — user-maintained.
- **Fields:** exclude_repos, min_size_kb, max_repos_to_consider, tasks_per_run, max_prs_per_repo, enabled_categories, max_cost_tier, budget_reserve_percent, public_only, max_inactive_days
- **Consumers:** Repo discovery, task selection, cooldown checks
- **Risk:** P3 — No schema validation. Malformed YAML crashes the orchestrator.

### 2. State History (state.json)
- **Source:** `~/.nightshift/state.json`
- **Lifecycle:** Append-only flat array `{"runs": [...]}`. Each run entry: `{timestamp, repo, task, status}`.
- **Read by:** `_is_on_cooldown()` — scans array for recent repo+task combos.
- **Written by:** `_record_run()` — appends entry after task execution.
- **Growth:** Unbounded. No pruning, no rotation. At 3 tasks/run * 4 runs/hr * 24hr = ~288 entries/day.
- **Risk:** P2 — Will grow indefinitely. Should prune entries older than max cooldown period (30d default).

### 3. Task Definitions (nightshift_tasks.json)
- **Source:** Shipped alongside nightshift.py in the repo
- **Lifecycle:** Static — read at startup by `_load_tasks()`. Never modified.
- **Content:** 61 task definitions with ID, name, description, category, cost_tier, interval, risk level
- **Risk:** P3 — Low risk. Could benefit from JSON schema validation on load.

### 4. Environment Variables
- `NIGHTSHIFT_STATE_DIR` — overrides state dir location (default: `~/.nightshift`)
- `NIGHTSHIFT_WORKSPACE` — overrides workspace dir (default: `~/nightshift-workspace`)
- `GLM_API_KEY` — required for quota API calls
- **Lifecycle:** Read once at module import time
- **Risk:** P3 — No validation or helpful error if GLM_API_KEY is missing (quota check silently fails)

### 5. Git Clone Directories
- **Source:** `git clone` of selected GitHub repos
- **Location:** `NIGHTSHIFT_WORKSPACE/<repo-name>/`
- **Lifecycle:** Created by `git clone`, used by subagent for analysis/modification, cleaned up with `shutil.rmtree()`
- **Risk:** P2 — If cleanup fails (crash, timeout), stale clones accumulate. No garbage collection for orphaned clones.

### 6. GLM Quota Data (glm_quota.py)
- **Source:** `open.bigmodel.cn` API — 3 endpoints:
  - `/api/monitor/usage/quota/limit` — token usage percentage + reset time
  - `/api/monitor/usage/model-usage` — hourly call/token stats
  - `/api/monitor/usage/tool-usage` — MCP tool usage stats
- **Auth:** `Authorization: <GLM_API_KEY>` (no Bearer prefix)
- **Lifecycle:** Fetched on-demand per `--check` invocation. No caching.
- **Consumer:** Burn window calculation (minutes until reset, quota percentage)
- **Risk:** P2 — No caching means every cron invocation hits the API. Rate limit risk. No timeout retry.

### 7. GitHub Repository Metadata
- **Source:** `gh repo list` CLI output + `gh repo view --json`
- **Fields:** name, owner, diskUsage, isFork, pushed_at, visibility
- **Lifecycle:** Fetched per run. Filters: not fork, not excluded, active (pushed in last N days), public_only
- **Risk:** P3 — No caching between runs. `gh` CLI rate limits (5000/hr for authenticated).

### 8. Git Branches & PRs
- **Source:** Created during task execution
- **Naming:** `nightshift/<task-id>-YYYYMMDD-HHMM`
- **Lifecycle:** Branch created from default branch → subagent commits → push → PR created → branch persists
- **Risk:** P2 — Stale branches accumulate. No branch cleanup after PR merge/close.

## Data Flow Diagram

```
Config (YAML) ──┐
                ├─→ Repo Discovery (gh CLI) ─→ Filter (fork/size/activity)
State (JSON) ───┘                                        │
                                                          ▼
Tasks (JSON) ────→ Task Selection ←── Quota API (bigmodel.cn)
                      │
                      ▼
              Git Clone (workspace/)
                      │
                      ▼
              Subagent Execution (delegate_task)
                      │
                      ├──→ Analysis Report (.md file in clone dir)
                      ├──→ Code Changes (patches in clone dir)
                      └──→ Git Commit + Push + PR (gh CLI)
                      │
                      ▼
              State Update (append to state.json)
              Cleanup (shutil.rmtree clone dir)
```

## Recommendations

### P2 — State.json Growth
Add periodic pruning in `_record_run()`:
```python
# Keep only last 30 days of runs
cutoff = datetime.now(timezone.utc) - timedelta(days=30)
state["runs"] = [r for r in state["runs"] if ...]
```

### P2 — Orphaned Clone Cleanup
Add startup garbage collection:
```python
# Remove any clone dirs not from current run
for d in WORKSPACE.iterdir():
    if d.is_dir() and d.name not in current_task_dirs:
        shutil.rmtree(d)
```

### P2 — Stale Branch Cleanup
Add periodic `gh` cleanup for merged/closed nightshift branches.

### P3 — Config Validation
Add YAML schema validation on load to prevent runtime crashes.

### P3 — API Caching
Cache quota API response for 5 min to reduce redundant calls during cron polling.
