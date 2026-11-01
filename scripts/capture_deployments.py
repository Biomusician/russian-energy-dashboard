"""Capture the production deployment ledger from GitHub's public deployments API (iteration 16).

    .venv\\Scripts\\python.exe scripts\\capture_deployments.py [--status-budget N]

Vercel records every production deploy against the commit it built, through GitHub's
deployments API. That record is the evidence that a commit was actually PUBLISHED, as opposed to
merely committed: a multi-commit push deploys only its tip, so most commits on `main` were never
served to anyone. `pipeline/production_history.py` reads this ledger to decide which committed
snapshots count as as-published history.

This is run by a person at release time, not by the daily build: the build must not depend on a
third-party API, and a deploy cannot be in the ledger before it has happened. Commits the bot
pushes after the last capture are handled by production_history's presumption rule.

Unauthenticated GitHub API calls are limited to 60 an hour. Each deployment's final state needs
one call, so the script keeps states it already knows, spends at most --status-budget calls on
the rest, and can be re-run later to fill them in. Never pass a token through this script.
"""

import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "data" / "curated" / "production_deployments.json"
REPO = "Biomusician/russian-energy-dashboard"


def _get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "energy-disruption-monitor-ledger"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status-budget", type=int, default=40)
    args = ap.parse_args()

    old = {}
    if LEDGER.exists():
        old = {d["deployment_id"]: d for d in json.loads(LEDGER.read_text(encoding="utf-8"))["deployments"]}

    raw, page = [], 1
    while True:
        batch = _get(f"https://api.github.com/repos/{REPO}/deployments?environment=Production&per_page=100&page={page}")
        raw += batch
        if len(batch) < 100:
            break
        page += 1

    budget = args.status_budget
    out = []
    for d in raw:
        prev = old.get(d["id"], {})
        state = prev.get("state")
        if state is None and budget > 0:
            budget -= 1
            statuses = _get(d["statuses_url"])
            # The newest status is first; a deploy with no status yet is still unknown.
            state = statuses[0]["state"] if statuses else None
        out.append({"deployment_id": d["id"], "sha": d["sha"], "environment": d["environment"],
                    "created_at": d["created_at"], "creator": (d.get("creator") or {}).get("login"),
                    "state": state})
    out.sort(key=lambda d: d["created_at"])
    doc = {
        "note": ("Vercel production deployments as recorded by GitHub's public deployments API. "
                 "Captured by scripts/capture_deployments.py; read by pipeline/production_history.py. "
                 "`state` is the deploy's final status, null where it has not been fetched yet."),
        "repo": REPO,
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "deployments": out,
    }
    LEDGER.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    unknown = sum(1 for d in out if d["state"] is None)
    print(f"{len(out)} deployments, {unknown} with state not yet fetched")


if __name__ == "__main__":
    main()
