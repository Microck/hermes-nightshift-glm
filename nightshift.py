#!/usr/bin/env python3
"""
Nightshift v3 — Full implementation of marcus/nightshift for Hermes Agent.
61 task types across 7 categories with plan-implement-review architecture.
Budget tracking, multi-repo, GLM 5.1 powered.
"""

import json
import math
import os
import random
import shutil
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE_DIR = Path(os.environ.get("NIGHTSHIFT_STATE_DIR", os.path.expanduser("~/.nightshift")))
WORKSPACE = Path(os.environ.get("NIGHTSHIFT_WORKSPACE", os.path.expanduser("~/nightshift-workspace")))
STATE_FILE = STATE_DIR / "state.json"
CONFIG_FILE = STATE_DIR / "config.yaml"
TASKS_FILE = Path(__file__).parent / "nightshift_tasks.json"

# --- Org Allowlist ---
# ONLY these orgs/users are authorized for nightshift operations.
# Any repo from an unauthorized org is silently skipped (not an error —
# the token may have access to orgs for legitimate non-nightshift reasons).
AUTHORIZED_ORGS = {"Microck", "nightshift-micr", "micr-dev"}
REFERENCE_DIR = Path(__file__).parent / "references"

# --- Cost Tiers (token ranges from nightshift) ---

COST_TOKENS = {
    "low": (10_000, 50_000),
    "medium": (50_000, 150_000),
    "high": (150_000, 500_000),
    "very_high": (500_000, 1_000_000),
}

# --- Task Categories ---

CATEGORIES = {
    "pr": {
        "name": "PR",
        "description": "It's done - here's the PR",
        "produces_pr": True,
        "review_loop": True,
    },
    "analysis": {
        "name": "Analysis",
        "description": "Here's what I found",
        "produces_pr": False,
        "review_loop": False,
    },
    "options": {
        "name": "Options",
        "description": "Here are options",
        "produces_pr": False,
        "review_loop": False,
    },
    "safe": {
        "name": "Safe",
        "description": "I tried it safely",
        "produces_pr": False,
        "review_loop": False,
    },
    "map": {
        "name": "Map",
        "description": "Here's the map",
        "produces_pr": None,  # Determined per task: only reviewed map tasks produce PRs.
        "review_loop": None,
    },
    "emergency": {
        "name": "Emergency",
        "description": "For when things go sideways",
        "produces_pr": False,
        "review_loop": False,
    },
    "review": {
        "name": "Review",
        "description": "Expert code review + fixes",
        "produces_pr": True,
        "review_loop": True,
    },
}

# --- Config ---

DEFAULT_CONFIG = {
    "exclude_repos": [
        "*-backup", "pi-backup", "testweb", "gitlab-acc-creator",
        "opencode-gitlab-multi-pat", "lucidus-45", "lucid-track-span",
        "chalcopyrite", "Microck", "Celeste-QuarziteSkin",
    ],
    "public_only": True,  # Only run on public repos
    "max_inactive_days": 30,  # Skip repos with no pushes in last X days (0 = disabled)
    "min_size_kb": 10,
    "max_repos_to_consider": 30,
    "tasks_per_run": 3,
    "max_prs_per_repo": 2,
    "max_review_iterations": 3,
    "enabled_categories": None,  # None = all
    "enabled_tasks": None,  # None = all
    "disabled_tasks": [],  # Tasks to skip
    "max_cost_tier": "very_high",  # Cap task cost
    "budget_reserve_percent": 20,  # Reserve 20% quota
}

KNOWN_CONFIG_KEYS = set(DEFAULT_CONFIG)

# --- Prompt Templates (from nightshift orchestrator.go) ---

PLAN_PROMPT_TEMPLATE = """You are a planning agent. Create a detailed execution plan for this task.

## Task
|ID: {task_id}
|Title: {task_name}
|Description: {task_description}
|Category: {task_category}
{reference_section}## Instructions
0. You are running autonomously. If the task is broad or ambiguous, choose a concrete, minimal scope that delivers value and state any assumptions in the description.
1. Work on a new branch and plan to submit a PR. Never work directly on the primary branch.
   Create your feature branch from `{default_branch}`.
2. Before creating your branch, record the current branch name and plan to switch back after the PR is opened.
3. If you create commits, include a concise message with these git trailers:
   Nightshift-Task: {task_id}
4. Analyze the task requirements by reading the codebase at {clone_dir}
5. Identify files that need to be modified
6. Create step-by-step implementation plan
7. Output only valid JSON (no markdown, no extra text):

{{
  "steps": ["step1", "step2", ...],
  "files": ["file1", "file2", ...],
  "description": "overall approach"
}}"""

IMPLEMENT_PROMPT_TEMPLATE = """You are an implementation agent. Execute the plan for this task.

## Task
ID: {task_id}
Title: {task_name}
Description: {task_description}
Category: {task_category}

## Plan
{plan_description}

## Steps
{plan_steps}
{iteration_note}

## Instructions
0. Before creating your branch, record the current branch name. Create and work on a new branch: nightshift/{task_id}-{timestamp}. Never modify the primary branch.
   Checkout `{default_branch}` before creating your feature branch.
1. If you create commits, include a concise message with these git trailers:
   Nightshift-Task: {task_id}
2. Implement the plan step by step in {clone_dir}
3. Make all necessary code changes
4. Ensure tests pass if tests exist
5. Output a summary as JSON:

{{
  "files_modified": ["file1", ...],
  "summary": "what was done"
}}

IMPORTANT RULES:
- Do NOT run formatters (no ruff format, no biome format, no prettier) — only lint fixes
- Do NOT add new dependencies — revert package.json/lockfile changes from installing tools
- Make targeted changes, not sweeping rewrites
- If the task is analysis-only, do NOT make code changes — just output findings as the summary"""

REVIEW_PROMPT_TEMPLATE = """You are a code review agent. Review this implementation.

## Task
ID: {task_id}
Title: {task_name}
Description: {task_description}

## Implementation Summary
{impl_summary}

## Files Modified
{impl_files}

## Instructions
1. Confirm work was done on a branch (not primary)
2. Check if implementation meets task requirements
3. Verify code quality and correctness
4. Check for bugs, security issues, or unintended changes
5. Output your review as JSON:

{{
  "passed": true/false,
  "feedback": "detailed feedback",
  "issues": ["issue1", "issue2", ...]
}}

Set "passed" to true ONLY if the implementation is correct and complete.
Be strict — if changes look risky, overly broad, or could break things, fail them."""

ANALYSIS_PROMPT_TEMPLATE = """You are Nightshift, an autonomous code quality bot working on {clone_dir}.

## Task: {task_name}
{task_description}

## Category: {task_category}

## Instructions
1. Analyze the codebase thoroughly
2. Focus on the specific task description above
3. Report findings in a structured format with severity levels (P0-P3)
4. Be specific — reference file paths and line numbers
5. If you find nothing noteworthy, explicitly say so

Output a structured report with findings, organized by severity."""

# --- Reference Docs ---

def load_reference(ref_name):
    """Load a reference doc by filename. Returns None if not found."""
    if not ref_name:
        return None
    path = REFERENCE_DIR / ref_name
    if path.exists():
        with open(path) as f:
            return f.read()
    return None

# --- Task Loading ---

def load_tasks():
    """Load task definitions from JSON file."""
    if TASKS_FILE.exists():
        with open(TASKS_FILE) as f:
            return json.load(f)
    return {}

# --- State ---

def _parse_iso_datetime(value):
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

def validate_config(config):
    if not isinstance(config, dict):
        raise ValueError("config.yaml must contain a top-level mapping")

    unknown_keys = sorted(set(config) - KNOWN_CONFIG_KEYS)
    if unknown_keys:
        raise ValueError(f"Unknown config keys: {', '.join(unknown_keys)}")

    list_or_none_fields = {"enabled_categories", "enabled_tasks"}
    int_fields = {
        "min_size_kb",
        "max_repos_to_consider",
        "tasks_per_run",
        "max_prs_per_repo",
        "max_review_iterations",
        "budget_reserve_percent",
        "max_inactive_days",
    }

    for field in int_fields:
        value = config.get(field)
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ValueError(f"{field} must be a non-negative integer")

    for field in list_or_none_fields:
        value = config.get(field)
        if value is not None and not isinstance(value, list):
            raise ValueError(f"{field} must be a list or null")

    for field in ("exclude_repos", "disabled_tasks"):
        value = config.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(f"{field} must be a list of strings")

    if not isinstance(config.get("public_only"), bool):
        raise ValueError("public_only must be true or false")

    max_cost_tier = config.get("max_cost_tier")
    if max_cost_tier not in COST_TOKENS:
        raise ValueError(f"max_cost_tier must be one of: {', '.join(COST_TOKENS)}")

    enabled_categories = config.get("enabled_categories")
    if enabled_categories is not None:
        invalid = sorted(set(enabled_categories) - set(CATEGORIES))
        if invalid:
            raise ValueError(f"enabled_categories contains unknown values: {', '.join(invalid)}")

def get_state_retention_days(all_tasks):
    max_interval_hours = max((task.get("interval_hours", 72) for task in all_tasks.values()), default=72)
    return max(30, math.ceil(max_interval_hours / 24))

def prune_state_runs(state, retention_days):
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    kept_runs = []
    removed = 0
    for run in state.get("runs", []):
        if not isinstance(run, dict):
            removed += 1
            continue
        timestamp = _parse_iso_datetime(run.get("timestamp"))
        if timestamp is None or timestamp < cutoff:
            removed += 1
            continue
        kept_runs.append(run)
    state["runs"] = kept_runs
    return removed

def cleanup_workspace(preserve_dirs=None):
    preserve = set(preserve_dirs or [])
    if not WORKSPACE.exists():
        return []

    removed = []
    for entry in WORKSPACE.iterdir():
        if not entry.is_dir() or entry.name in preserve:
            continue
        shutil.rmtree(entry, ignore_errors=False)
        removed.append(entry.name)
    return removed

def cleanup_stale_nightshift_branches(owner, repo):
    closed_prs = gh_api(f"/repos/{owner}/{repo}/pulls?state=closed")
    if not isinstance(closed_prs, list):
        return 0

    deleted = 0
    seen_refs = set()
    repo_full_name = f"{owner}/{repo}"
    for pr in closed_prs:
        head = pr.get("head") or {}
        branch = head.get("ref", "")
        head_repo = (head.get("repo") or {}).get("full_name")
        if not branch.startswith("nightshift/"):
            continue
        if head_repo and head_repo != repo_full_name:
            continue
        if branch in seen_refs:
            continue
        seen_refs.add(branch)

        ref_path = urllib.parse.quote(f"heads/{branch}", safe="")
        if gh_api(f"/repos/{owner}/{repo}/git/refs/{ref_path}", method="DELETE") is not None:
            deleted += 1
    return deleted

def load_config():
    if CONFIG_FILE.exists():
        import yaml
        with open(CONFIG_FILE) as f:
            cfg = yaml.safe_load(f) or {}
        validate_config(cfg)
        merged = {**DEFAULT_CONFIG, **cfg}
        return merged
    return DEFAULT_CONFIG.copy()

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"runs": [], "last_run": None}

def save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# --- GitHub API ---

def gh_api(path, method="GET"):
    cmd = ["gh", "api"]
    if method != "GET":
        cmd.extend(["--method", method])
    if method == "GET" and "per_page" not in path:
        sep = "&" if "?" in path else "?"
        path = f"{path}{sep}per_page=100"
    cmd.append(path)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout) if result.stdout.strip() else {}

def get_all_repos():
    repos, page = [], 1
    while True:
        data = gh_api(f"/user/repos?sort=updated&direction=desc&page={page}")
        if not data or not isinstance(data, list) or len(data) == 0:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos

def get_open_prs_count(owner, repo):
    data = gh_api(f"/repos/{owner}/{repo}/pulls?state=open")
    if not data or not isinstance(data, list):
        return 0
    return sum(1 for pr in data if "[nightshift]" in pr.get("title", ""))

def is_excluded(name, patterns):
    for p in patterns:
        if p.startswith("*") and name.endswith(p[1:]):
            return True
        elif name == p:
            return True
    return False

# --- Core Logic ---

def get_enabled_tasks(config, all_tasks, repo_language=None):
    enabled = config.get("enabled_tasks")
    disabled = set(config.get("disabled_tasks", []))
    enabled_cats = config.get("enabled_categories")
    repo_lang = repo_language or ""

    result = {}
    for tid, task in all_tasks.items():
        if tid in disabled:
            continue
        if enabled is not None and tid not in enabled:
            continue
        if enabled_cats is not None and task["category"] not in enabled_cats:
            continue
        # Check cost tier cap
        cost_order = ["low", "medium", "high", "very_high"]
        task_cost_idx = cost_order.index(task.get("cost_tier", "medium"))
        max_cost_idx = cost_order.index(config.get("max_cost_tier", "very_high"))
        if task_cost_idx > max_cost_idx:
            continue
        # Language filter: skip if task specifies skip_langs and repo matches
        skip_langs = task.get("skip_langs", [])
        if skip_langs and repo_lang in skip_langs:
            continue
        # Language filter: if task requires specific langs, repo must match
        lang_filter = task.get("lang_filter", [])
        if lang_filter and repo_lang not in lang_filter:
            continue
        result[tid] = task
    return result

def select_repos(config, state):
    all_repos = get_all_repos()
    now = datetime.now(timezone.utc)
    max_inactive_days = config.get("max_inactive_days", 0)
    candidates = []
    for repo in all_repos:
        name, owner = repo["name"], repo["owner"]["login"]
        # Org allowlist gate — skip repos from unauthorized orgs
        if owner not in AUTHORIZED_ORGS:
            continue
        if is_excluded(name, config.get("exclude_repos", [])):
            continue
        if repo.get("archived") or repo.get("fork"):
            continue
        if config.get("public_only", False) and repo.get("private", False):
            continue
        if max_inactive_days > 0:
            pushed_at = repo.get("pushed_at", "")
            if pushed_at:
                pushed_dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                if (now - pushed_dt).days > max_inactive_days:
                    continue
        if (repo.get("size", 0) or 0) < config.get("min_size_kb", 10):
            continue
        if not repo.get("language"):
            continue
        cleanup_stale_nightshift_branches(owner, name)
        if get_open_prs_count(owner, name) >= config.get("max_prs_per_repo", 2):
            continue
        candidates.append({
            "full_name": repo["full_name"], "name": name, "owner": owner,
            "language": repo["language"],
            "default_branch": repo.get("default_branch", "main"),
            "updated_at": repo.get("updated_at", ""),
        })
    candidates.sort(key=lambda x: x["updated_at"], reverse=True)
    return candidates[:config.get("max_repos_to_consider", 30)]

def select_task(repo_info, enabled_tasks, config, state):
    now = datetime.now(timezone.utc)
    key = repo_info["full_name"]
    repo_lang = repo_info.get("language", "")

    eligible = []
    for task_id, task in enabled_tasks.items():
        # Language filter: skip if task requires specific langs
        lang_filter = task.get("lang_filter", [])
        skip_langs = task.get("skip_langs", [])
        if lang_filter and repo_lang not in lang_filter:
            continue
        if skip_langs and repo_lang in skip_langs:
            continue
        # Check cooldown
        last_run = None
        for run in state.get("runs", []):
            if run["repo"] == key and run["task"] == task_id:
                ts = run.get("timestamp", "")
                if not last_run or ts > last_run:
                    last_run = ts
        if last_run:
            last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            cooldown = timedelta(hours=task.get("interval_hours", 72))
            if now - last_dt < cooldown:
                continue
        eligible.append(task_id)

    if not eligible:
        return None

    # Weight by cost (prefer cheaper tasks) + randomness
    weights = []
    cost_weights = {"low": 4, "medium": 3, "high": 2, "very_high": 1}
    for t in eligible:
        weights.append(cost_weights.get(enabled_tasks[t].get("cost_tier", "medium"), 2))

    return random.choices(eligible, weights=weights, k=1)[0]

def clone_repo(repo_info):
    clone_dir = WORKSPACE / repo_info["name"]
    if clone_dir.exists():
        shutil.rmtree(clone_dir)
    url = f"https://github.com/{repo_info['full_name']}.git"
    result = subprocess.run(
        ["git", "clone", "--depth", "50", url, str(clone_dir)],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        return None
    return str(clone_dir)

def determine_prompt_type(task):
    category = task["category"]
    has_review = task.get("has_review", False)
    if category in {"pr", "map", "review"} and has_review:
        return "plan_implement_review"
    if category == "review":
        return "code_review"
    return "analysis"


def produces_pr(task, prompt_type):
    output_mode = task.get("output_mode")
    if output_mode is not None:
        return output_mode == "pr"
    if task["category"] == "pr":
        return True
    if task["category"] == "map":
        return prompt_type == "plan_implement_review"
    if task["category"] == "review":
        return prompt_type == "plan_implement_review"
    return False


def build_task_output(repo_info, task_id, task, timestamp, max_review_iterations):
    cat = CATEGORIES.get(task["category"], {})
    clone_dir = str(WORKSPACE / repo_info["name"])
    branch = f"nightshift/{task_id}-{timestamp.strftime('%Y%m%d-%H%M')}"
    prompt_type = determine_prompt_type(task)

    # Load reference doc content if specified
    ref_name = task.get("reference")
    ref_content = load_reference(ref_name) if ref_name else None

    return {
        "repo": repo_info["full_name"],
        "owner": repo_info["owner"],
        "name": repo_info["name"],
        "language": repo_info["language"],
        "task": task_id,
        "task_name": task["name"],
        "task_description": task["description"],
        "category": task["category"],
        "category_name": cat.get("name", task["category"]),
        "cost_tier": task.get("cost_tier", "medium"),
        "cost_tokens_min": COST_TOKENS.get(task.get("cost_tier", "medium"), (50000, 150000))[0],
        "cost_tokens_max": COST_TOKENS.get(task.get("cost_tier", "medium"), (50000, 150000))[1],
        "risk": task.get("risk", "low"),
        "has_review": task.get("has_review", False),
        "output_mode": task.get("output_mode", "pr"),
        "produces_pr": produces_pr(task, prompt_type),
        "prompt_type": prompt_type,
        "reference": task.get("reference", None),
        "reference_content": ref_content,
        "clone_dir": clone_dir,
        "default_branch": repo_info["default_branch"],
        "branch_name": branch,
        "max_review_iterations": max_review_iterations,
    }

def run(dry_run=False, single_repo=None, single_task=None, json_output=False):
    config = load_config()
    all_tasks = load_tasks()
    state = load_state()
    retention_days = get_state_retention_days(all_tasks)
    pruned_runs = prune_state_runs(state, retention_days)
    enabled_tasks = get_enabled_tasks(config, all_tasks)
    max_review_iterations = config.get("max_review_iterations", 3)

    print("Nightshift v3 starting...", file=sys.stderr)
    print(f"Config: {len(enabled_tasks)} tasks, max {config.get('tasks_per_run', 3)}/run", file=sys.stderr)
    if pruned_runs:
        print(f"Pruned {pruned_runs} stale state entries older than {retention_days} days", file=sys.stderr)
        save_state(state)
    removed_dirs = cleanup_workspace()
    if removed_dirs:
        print(f"Removed {len(removed_dirs)} stale clone directories", file=sys.stderr)

    if single_repo:
        single_owner = single_repo.split("/")[0]
        if single_owner not in AUTHORIZED_ORGS:
            print(f"ERROR: Repo '{single_repo}' is from unauthorized org '{single_owner}'. "
                  f"Authorized orgs: {AUTHORIZED_ORGS}", file=sys.stderr)
            sys.exit(1)
        repos = [{"full_name": single_repo, "name": single_repo.split("/")[-1],
                   "owner": single_repo.split("/")[0], "language": "?",
                   "default_branch": "main"}]
    else:
        repos = select_repos(config, state)

    if not repos:
        if json_output:
            print(json.dumps([]))
        else:
            print("No candidate repos found.")
        return

    print(f"Found {len(repos)} candidate repos", file=sys.stderr)

    completed = 0
    max_tasks = config.get("tasks_per_run", 3)
    results = []
    now = datetime.now(timezone.utc)

    for repo in repos:
        if completed >= max_tasks:
            break

        if single_task and single_task in enabled_tasks:
            task_id = single_task
        else:
            task_id = select_task(repo, enabled_tasks, config, state)

        if not task_id:
            print(f"  {repo['full_name']}: no eligible tasks", file=sys.stderr)
            continue

        task = enabled_tasks[task_id]
        print(f"  Selected: {repo['full_name']} -> {task['name']} [{task['category']}]", file=sys.stderr)

        if dry_run:
            completed += 1
            continue

        clone_dir = clone_repo(repo)
        if not clone_dir:
            print(f"  Clone failed, skipping", file=sys.stderr)
            continue

        output = build_task_output(repo, task_id, task, now, max_review_iterations)
        results.append(output)
        completed += 1

    if not results:
        if json_output:
            print(json.dumps([]))
        else:
            print("No tasks to execute.")
        return

    # Record runs
    for r in results:
        state["runs"].append({
            "timestamp": now.isoformat(),
            "repo": r["repo"],
            "task": r["task"],
            "task_name": r["task_name"],
            "category": r["category"],
            "cost_tier": r["cost_tier"],
            "status": "dispatched",
        })
    state["last_run"] = now.isoformat()
    save_state(state)

    output_json = json.dumps(results, indent=2)
    print(f"\nNIGHTSHIFT_TASKS_START")
    print(output_json)
    print(f"NIGHTSHIFT_TASKS_END")

    print(f"\nNightshift complete. {completed} tasks dispatched.", file=sys.stderr)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Nightshift v3 - Autonomous code quality bot")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repo", help="Specific repo (owner/repo)")
    parser.add_argument("--task", help="Specific task ID")
    parser.add_argument("--list-tasks", action="store_true")
    parser.add_argument("--list-categories", action="store_true")
    parser.add_argument("--json", action="store_true", help="Output only JSON")
    args = parser.parse_args()

    all_tasks = load_tasks()

    if args.list_categories:
        for cat_id, cat in CATEGORIES.items():
            category_tasks = [t for t in all_tasks.values() if t["category"] == cat_id]
            count = len(category_tasks)
            prompt_types = {determine_prompt_type(task) for task in category_tasks}
            produces_pr_values = {produces_pr(task, determine_prompt_type(task)) for task in category_tasks}

            if produces_pr_values == {True}:
                produces = "PR"
            elif produces_pr_values == {False}:
                produces = "findings"
            else:
                produces = "mixed"

            if prompt_types == {"plan_implement_review"}:
                review = "+review"
            elif "plan_implement_review" in prompt_types:
                review = "+mixed-review"
            else:
                review = ""

            print(f"  {cat_id:15s} {cat['name']:15s} ({count:2d} tasks) -> {produces}{review}")
        sys.exit(0)

    if args.list_tasks:
        print(f"{'ID':<30s} {'Category':<12s} {'Cost':<12s} {'Risk':<8s} {'Interval':>8s}  {'Name'}")
        print("-" * 100)
        for tid, task in all_tasks.items():
            interval = task.get("interval_hours", 72)
            if interval >= 336:
                interval_s = f"{interval // 168}w"
            else:
                interval_s = f"{interval // 24}d"
            print(f"  {tid:<28s} {task['category']:<12s} {task.get('cost_tier', '?'):<12s} {task.get('risk', '?'):<8s} {interval_s:>8s}  {task['name']}")
        sys.exit(0)

    run(dry_run=args.dry_run, single_repo=args.repo, single_task=args.task, json_output=args.json)
