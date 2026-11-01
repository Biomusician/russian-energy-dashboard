"""As-published history: what the dashboard actually served, and when (iteration 16).

THREE HISTORICAL QUESTIONS, THREE ANSWERS. They are different questions and must never share a
label or a number (docs/HISTORICAL_REPRODUCIBILITY.md):

    current-evidence reconstruction   "Given today's accepted corpus and code, what does the model
                                       estimate for date D?"  -> `--as-of D`, history_series.json
    as-published snapshot              "What did this dashboard actually publish then?"
                                       -> THIS module, production_history.json
    engineering regression fixture     "Did a scoring transformation change unexpectedly?"
                                       -> the synthetic-input tests in tests/

WHERE AS-PUBLISHED VALUES COME FROM. Only from artefacts that were actually served: the payload
committed at a commit that Vercel actually deployed. Nothing here re-runs old code or rebuilds old
state, because a rebuild answers the reconstruction question, not this one.

WHICH COMMITS COUNT. Most commits on `main` were never served: a push of several commits deploys
only its tip. So a commit's payload is as-published only when:

    deployed                      the deployment ledger (data/curated/production_deployments.json,
                                  captured from GitHub's deployments API) records a successful
                                  production deploy of exactly that commit;
    deploy_status_unverified      the ledger records a production deploy of that commit but its
                                  final status has not been fetched (the API is rate-limited);
    bot_refresh_presumed_deployed a daily-refresh bot commit made AFTER the ledger was captured.
                                  Every bot commit pushes alone and Vercel deploys every push to
                                  main; within the captured window this held for every bot commit
                                  after the first deploy. Presumed, and labelled as presumed.

A failed deploy is excluded. Anything before the first recorded deploy is UNAVAILABLE — it is not
reconstructed and relabelled.
"""

import hashlib
import json

from pipeline.lineage import PAYLOAD_DIR, _git, _show_json

LEDGER = "data/curated/production_deployments.json"
BOT_AUTHOR = "dataset-refresh[bot]"
METHODOLOGY_FILE = "methodology/scoring.json"
CONCEPT = "as_published"


def _blob_id(root, sha, relpath):
    """Git's content id of a file at a commit: an exact, free fingerprint of what was served."""
    return _git(root, "rev-parse", "--verify", "--quiet", f"{sha}:{relpath}")


def _event_ids(root, sha):
    doc = _show_json(root, sha, f"{PAYLOAD_DIR}/incidents.json")
    if not isinstance(doc, list):
        return None
    return sorted({i.get("incident_id") for i in doc if i.get("incident_id")})


def _ledger(root):
    try:
        with open(root / LEDGER, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _bot_commits_after(root, since_iso):
    """Daily-refresh commits on HEAD's history committed after `since_iso`, oldest first."""
    out = _git(root, "log", "--reverse", "--format=%H %cI", f"--author={BOT_AUTHOR}",
               f"--since={since_iso}", "HEAD")
    if not out:
        return []
    return [tuple(line.split(" ", 1)) for line in out.splitlines() if line.strip()]


def _entry(root, sha, served_at, lineage):
    snap = _show_json(root, sha, f"{PAYLOAD_DIR}/snapshot.json")
    if not isinstance(snap, dict):
        return None
    inputs = snap.get("build_inputs") or {}
    return {
        "sha": sha,
        "served_from": served_at,
        "committed_at": _git(root, "log", "-1", "--format=%cI", sha),
        "lineage": lineage,
        "as_of": snap.get("as_of"),
        "build_time": snap.get("build_time"),
        "esdi": snap.get("esdi"),
        "incident_total": snap.get("incident_total"),
        "schema_version": snap.get("schema_version"),
        "methodology_fingerprint": _blob_id(root, sha, METHODOLOGY_FILE),
        "inputs_fingerprint": inputs.get("combined") if isinstance(inputs, dict) else None,
        "outputs_fingerprint": snap.get("build_outputs_fingerprint"),
        "snapshot_blob": _blob_id(root, sha, f"{PAYLOAD_DIR}/snapshot.json"),
    }


def build(root):
    """The as-published history, oldest first. Returns a payload even when git or the ledger is
    unavailable, so the absence is stated rather than shown as an empty history."""
    ledger = _ledger(root)
    base = {
        "concept": CONCEPT,
        "label": "As published",
        "what_this_answers": "What this dashboard actually served to readers, and from when.",
        "what_this_does_not_answer": (
            "What today's evidence says about those dates. That is the current-evidence "
            "reconstruction (history_series.json, or a pipeline run with --as-of)."),
        "source": "git payloads at commits recorded as deployed by Vercel",
        "entries": [],
        "earliest_reliable_as_published_date": None,
        "before_earliest": "unavailable",
        "excluded": {},
    }
    if _git(root, "rev-parse", "--git-dir") is None or ledger is None:
        base["unavailable_reason"] = "git history or the deployment ledger is not available to this build"
        return base

    deployments = ledger.get("deployments") or []
    head_ok = lambda sha: _git(root, "merge-base", "--is-ancestor", sha, "HEAD") is not None  # noqa: E731
    excluded = {"failed_deploy": 0, "not_in_this_history": 0, "no_payload": 0}
    seen, rows = set(), []
    for d in sorted(deployments, key=lambda d: d["created_at"]):
        if d.get("state") not in (None, "success"):
            excluded["failed_deploy"] += 1
            continue
        if d["sha"] in seen:
            continue  # a redeploy of an already-served commit serves the same payload
        if not head_ok(d["sha"]):
            excluded["not_in_this_history"] += 1
            continue
        lineage = "deployed" if d.get("state") == "success" else "deploy_status_unverified"
        e = _entry(root, d["sha"], d["created_at"], lineage)
        if e is None:
            excluded["no_payload"] += 1
            continue
        seen.add(d["sha"])
        rows.append(e)

    for sha, committed in _bot_commits_after(root, ledger.get("captured_at") or "9999"):
        if sha in seen:
            continue
        e = _entry(root, sha, committed, "bot_refresh_presumed_deployed")
        if e:
            seen.add(sha)
            rows.append(e)

    rows.sort(key=lambda e: e["served_from"])
    # Which events each served build ADDED or REMOVED relative to the build served before it.
    # This is the knowledge-date record: an event can be dated 2025 and first served in 2026.
    prev_ids = None
    for e in rows:
        ids = _event_ids(root, e["sha"])
        e["event_ids_fingerprint"] = (hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()[:16]
                                      if ids is not None else None)
        if ids is None or prev_ids is None:
            e["events_added"], e["events_removed"] = None, None
        else:
            e["events_added"] = sorted(set(ids) - set(prev_ids))
            e["events_removed"] = sorted(set(prev_ids) - set(ids))
        if ids is not None:
            prev_ids = ids

    base["entries"] = rows
    base["excluded"] = excluded
    base["ledger_captured_at"] = ledger.get("captured_at")
    base["earliest_reliable_as_published_date"] = rows[0]["served_from"][:10] if rows else None
    return base


def as_published_on(history, day):
    """The build being served at the end of `day` (YYYY-MM-DD), or None before history begins.
    Served-from times are UTC; a day is the UTC day."""
    current = None
    for e in history.get("entries") or []:
        if e["served_from"][:10] <= day:
            current = e
        else:
            break
    return current
