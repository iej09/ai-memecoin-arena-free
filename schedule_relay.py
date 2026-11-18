#!/usr/bin/env python3
"""One-week GitHub Actions heartbeat relay for the PAPER-ONLY arena.

GitHub cron events are best-effort. The separate relay job waits until the next
15-minute checkpoint then uses the repository-scoped GITHUB_TOKEN to dispatch
the existing tournament workflow. An ordinary cron run can rescue the relay
when it has been absent for over 30 minutes.

This script NEVER trades, changes the tournament ledger, stores API keys, or
extends the original seven-day deadline. It stops when the ledger is FINISHED.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

WORKFLOW = "free-paper-tournament.yml"
INTERVAL = 15 * 60
RELAY_STALE_AFTER = 30 * 60


def as_epoch(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def relay_plan(state, event_name, now, latest_dispatch_at=None):
    """Return (should_dispatch, seconds_to_wait, explanation). No side effects."""
    meta = state.get("meta", {})
    if not isinstance(meta, dict):
        return False, 0, "missing-metadata"
    if state.get("status") == "FINISHED" or meta.get("finished"):
        return False, 0, "tournament-finished"
    start, deadline = as_epoch(meta.get("started_at")), as_epoch(meta.get("deadline"))
    if start is None or deadline is None:
        return False, 0, "tournament-not-initialized"
    if abs((deadline - start) - 7 * 86400) > 0.1:
        return False, 0, "unexpected-deadline-immutable-clock"
    if event_name not in {"workflow_dispatch", "push", "schedule"}:
        return False, 0, "unrecognized-launch-event"
    if event_name in {"schedule", "push"} and latest_dispatch_at is not None:
        age = now - latest_dispatch_at
        if 0 <= age < RELAY_STALE_AFTER:
            return False, 0, "existing-dispatch-chain-is-active"
    latest_tick = as_epoch(meta.get("last_completed_tick"))
    if latest_tick is None:
        return True, 0, "no-completed-tick"
    # Wait on a lightweight runner, but never beyond 15 minutes. Deadline runs
    # still dispatch once, allowing the trading worker to finalize and stop.
    wait = max(0.0, min(float(INTERVAL), latest_tick + INTERVAL - now))
    return True, wait, "dispatch-next-paper-tick"


def github_request(url, token, data=None, method=None):
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AI-Memecoin-Arena-7Day-Paper-Relay",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        url, headers=headers, data=json.dumps(data).encode("utf-8") if data is not None else None,
        method=method or ("POST" if data is not None else "GET"),
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.status, json.load(response) if (method or ("POST" if data is not None else "GET")) == "GET" else None


def latest_dispatch_time(repo, token):
    url = (f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW}/runs"
           "?event=workflow_dispatch&per_page=5")
    status, data = github_request(url, token)
    if status != 200:
        return None
    runs = data.get("workflow_runs") or []
    return as_epoch(runs[0].get("created_at")) if runs else None


def disable_completed_workflow(repo, token):
    """Stop free-runner usage after the seven-day paper trial is saved."""
    endpoint = (f"https://api.github.com/repos/{repo}/actions/workflows/"
                f"{WORKFLOW}/disable")
    status, _ = github_request(endpoint, token, method="PUT")
    if status != 204:
        raise RuntimeError("GitHub workflow disable returned unexpected HTTP " + str(status))
    print("Saved seven-day results are FINAL: tournament workflow disabled", flush=True)


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    event_name = os.environ["GITHUB_EVENT_NAME"]
    state = json.loads(Path("docs/data.json").read_text(encoding="utf-8"))
    now = time.time()
    recent = None
    if event_name != "workflow_dispatch":
        # On GitHub API read outages prefer the cron watchdog; never guess a
        # dispatch was made or modify the tournament state.
        try:
            recent = latest_dispatch_time(repo, token)
        except (urllib.error.URLError, ValueError, KeyError) as ex:
            print("Cannot inspect recent dispatch:", type(ex).__name__, flush=True)
    should, delay, why = relay_plan(state, event_name, now, recent)
    print("Paper relay plan:", why, "wait seconds", int(delay), flush=True)
    if not should:
        if why == "tournament-finished":
            try:
                disable_completed_workflow(repo, token)
            except (urllib.error.URLError, RuntimeError) as ex:
                print("Auto-disable unavailable:", type(ex).__name__, flush=True)
        return 0
    if delay > 0:
        time.sleep(delay)
    # Re-read the latest committed public ledger after sleeping. A scheduled
    # watchdog run may have finalized the competition in the meantime.
    try:
        url = f"https://raw.githubusercontent.com/{repo}/main/docs/data.json"
        req = urllib.request.Request(url, headers={"User-Agent": "Arena-Paper-Relay"})
        with urllib.request.urlopen(req, timeout=25) as response:
            fresh = json.load(response)
        if fresh.get("meta", {}).get("finished") or fresh.get("status") == "FINISHED":
            print("Tournament finished while relay slept; no dispatch", flush=True)
            try:
                disable_completed_workflow(repo, token)
            except (urllib.error.URLError, RuntimeError) as ex:
                print("Auto-disable unavailable:", type(ex).__name__, flush=True)
            return 0
        # Check that the original clock was not modified by a later runner.
        _, _, reason = relay_plan(fresh, "workflow_dispatch", time.time())
        if reason == "unexpected-deadline-immutable-clock":
            raise RuntimeError("Original seven-day deadline changed; refusing dispatch")
    except urllib.error.URLError as ex:
        print("Public scoreboard unavailable for recheck:", type(ex).__name__, flush=True)
    api_url = (f"https://api.github.com/repos/{repo}/actions/workflows/"
               f"{WORKFLOW}/dispatches")
    status, _ = github_request(api_url, token, {"ref": "main"})
    if status != 204:
        raise RuntimeError("GitHub rejected paper relay dispatch: HTTP " + str(status))
    print("Next paper-only workflow dispatched, without storing a GitHub PAT", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
