#!/usr/bin/env python3
"""Check GLM Coding Plan usage via the Zhipu monitor API.

All 3 endpoints:
  /api/monitor/usage/quota/limit      — quota percentages (no params needed)
  /api/monitor/usage/model-usage      — hourly model calls + tokens (needs startTime/endTime)
  /api/monitor/usage/tool-usage       — hourly MCP tool usage (needs startTime/endTime)

Auth: header "Authorization: <GLM_API_KEY>" (no Bearer prefix)
Host: open.bigmodel.cn
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import URLError

GLM_KEY = os.environ.get("GLM_API_KEY", "")
BASE_URL = "https://open.bigmodel.cn"
CACHE_DIR = Path(os.environ.get("NIGHTSHIFT_STATE_DIR", os.path.expanduser("~/.nightshift")))
CACHE_FILE = CACHE_DIR / "glm-quota-cache.json"
CACHE_TTL_SECONDS = 300


def _cache_key(path, params=None):
    return json.dumps({"path": path, "params": params or {}}, sort_keys=True)


def _load_cache():
    if not CACHE_FILE.exists():
        return {}
    with open(CACHE_FILE) as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _save_cache(cache):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def _read_cached_response(path, params=None):
    cache = _load_cache()
    entry = cache.get(_cache_key(path, params))
    if not isinstance(entry, dict):
        return None

    fetched_at = entry.get("fetched_at")
    data = entry.get("data")
    if not fetched_at or data is None:
        return None

    fetched_at_dt = datetime.fromisoformat(fetched_at)
    age = (datetime.now(timezone.utc) - fetched_at_dt).total_seconds()
    if age > CACHE_TTL_SECONDS:
        return None
    return data


def _write_cached_response(path, params, data):
    cache = _load_cache()
    cache[_cache_key(path, params)] = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    _save_cache(cache)


def _fetch(path, params=None):
    if not GLM_KEY:
        raise RuntimeError("GLM_API_KEY is not set")

    cached = _read_cached_response(path, params)
    if cached is not None:
        return cached

    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": GLM_KEY,
        "Content-Type": "application/json",
        "Accept-Language": "en-US",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except URLError:
        raise

    _write_cached_response(path, params, data)
    return data


def _time_params():
    """Default time window: last 24h at hourly granularity."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = datetime(now.year, now.month, now.day - 1, now.hour, 0, 0)
    end = datetime(now.year, now.month, now.day, now.hour, 59, 59)
    return {"startTime": start.strftime("%Y-%m-%d %H:%M:%S"),
            "endTime": end.strftime("%Y-%m-%d %H:%M:%S")}


def fetch_quota():
    data = _fetch("/api/monitor/usage/quota/limit")
    if not data.get("success"):
        return None
    result = {"plan": data["data"].get("level", "unknown"), "limits": {}}
    for lim in data["data"].get("limits", []):
        t = lim["type"]
        reset = datetime.fromtimestamp(lim["nextResetTime"] / 1000, tz=timezone.utc).isoformat() if lim.get("nextResetTime") else None
        if t == "TIME_LIMIT":
            # This is actually MCP usage (1 month), not time limit
            result["limits"]["mcp"] = {
                "used": lim.get("currentValue", 0),
                "total": lim.get("usage", 0),
                "remaining": lim.get("remaining", 0),
                "percentage": lim.get("percentage", 0),
                "reset_utc": reset,
            }
        elif t == "TOKENS_LIMIT":
            result["limits"]["tokens"] = {
                "percentage": lim.get("percentage", 0),
                "reset_utc": reset,
            }
    return result


def fetch_model_usage():
    data = _fetch("/api/monitor/usage/model-usage", _time_params())
    if not data.get("success"):
        return None
    d = data["data"]
    return {
        "hours": d.get("x_time", []),
        "calls": d.get("modelCallCount", []),
        "tokens": d.get("tokensUsage", []),
        "total_calls": d.get("totalUsage", {}).get("totalModelCallCount", 0),
        "total_tokens": d.get("totalUsage", {}).get("totalTokensUsage", 0),
    }


def fetch_tool_usage():
    data = _fetch("/api/monitor/usage/tool-usage", _time_params())
    if not data.get("success"):
        return None
    d = data["data"]
    return {
        "hours": d.get("x_time", []),
        "network_search": d.get("networkSearchCount", []),
        "web_read_mcp": d.get("webReadMcpCount", []),
        "zread_mcp": d.get("zreadMcpCount", []),
        "totals": d.get("totalUsage", {}),
    }


def format_report(quota, model, tools):
    lines = ["GLM Coding Plan"]
    if quota:
        lines.append(f"  Plan level: {quota['plan']}")
        tk = quota["limits"].get("tokens")
        if tk:
            lines.append(f"  Token usage (5h): {tk['percentage']}%")
            lines.append(f"    Resets: {tk['reset_utc']}")
        mcp = quota["limits"].get("mcp")
        if mcp:
            lines.append(f"  MCP usage (1mo): {mcp['percentage']}% ({mcp['used']}/{mcp['total']})")

    if model:
        lines.append(f"  Model calls (24h): {model['total_calls']}")
        lines.append(f"  Tokens (24h): {model['total_tokens']:,}")

    if tools:
        t = tools["totals"]
        lines.append(f"  MCP tools (24h): search={t.get('totalNetworkSearchCount',0)}, webread={t.get('totalWebReadMcpCount',0)}, zread={t.get('totalZreadMcpCount',0)}")

    return "\n".join(lines)


def should_run_nightshift():
    """Returns (should_run, reason, minutes_until_reset).
    
    Designed for pre-expiry quota burning: run when there's remaining
    budget, skip only when quota is fully consumed or about to reset.
    """
    if not GLM_KEY:
        return False, "GLM_API_KEY is not set", None

    quota = fetch_quota()
    if not quota:
        return False, "Could not fetch quota", None
    tk = quota["limits"].get("tokens")
    if not tk:
        return False, "No token limit data", None
    pct = tk["percentage"]
    
    # Calculate minutes until reset
    mins = None
    if tk.get("reset_utc"):
        reset = datetime.fromisoformat(tk["reset_utc"])
        mins = max(0, int((reset - datetime.now(timezone.utc)).total_seconds() / 60))
    
    # No reset time available — can't schedule around expiry
    if mins is None:
        return False, f"Token quota {pct}% used, no reset time available", None
    
    # Already fully consumed — nothing to burn
    if pct >= 99:
        return False, f"Token quota {pct}% used, fully consumed (resets in {mins}min)", mins
    
    # Only run within the burn window: 5-50 min before reset (wider window for 15-min cron)
    if mins > 50:
        return False, f"Token quota {pct}% used, resets in {mins}min — too early (burn window: 5-50 min before reset)", mins
    if mins < 5:
        return False, f"Token quota {pct}% used, resets in {mins}min — too late", mins
    
    # We're in the burn window and there's budget
    tasks_hint = "3 tasks" if pct < 50 else "2 tasks" if pct < 75 else "1 task" if pct < 95 else "scrape remaining"
    return True, f"Token quota {pct}% used, resets in {mins}min — BURN WINDOW ({tasks_hint})", mins


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        result = {
            "quota": fetch_quota(),
            "model_usage": fetch_model_usage(),
            "tool_usage": fetch_tool_usage(),
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif len(sys.argv) > 1 and sys.argv[1] == "--check":
        ok, reason, mins = should_run_nightshift()
        print(f"{'RUN' if ok else 'SKIP'}: {reason}")

    elif len(sys.argv) > 1 and sys.argv[1] == "--quota-only":
        q = fetch_quota()
        print(format_report(q, None, None))

    else:
        q = fetch_quota()
        m = fetch_model_usage()
        t = fetch_tool_usage()
        print(format_report(q, m, t))
