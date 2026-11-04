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
RECONSTRUCTION = "current_evidence_reconstruction"
CURRENT = "current_build"
FIXTURE = "engineering_fixture"


def history_concept(as_of, today, build_mode=None):
    """Which historical question a pipeline build answers. A build for a past date is a
    current-evidence reconstruction, never an as-published value: it runs today's code over
    today's corpus. Only `build()` below, reading what was deployed, can say what was published.
    A fixture build (iteration 17) is an engineering test input and says so."""
    if build_mode == "fixture":
        return {"mode": FIXTURE, "label": f"Engineering fixture build for {as_of}",
                "note": "A test or experiment build. Never published, never a history of anything."}
    if as_of < today:
        return {
            "mode": RECONSTRUCTION,
            # "Pinned-source", not just "current-evidence": the timeline and comparison series
            # are also current-evidence reconstructions but read TODAY's article revisions, so the
            # two give different values for the same week under what used to be one label.
            "label": f"Pinned-source reconstruction for {as_of}",
            "note": ("Today's code and accepted corpus evaluated at a past date, with live article "
                     "inputs pinned to their revision on that date. Not what the dashboard published "
                     "then (production_history.json), and not the timeline series, which reads "
                     "today's article revisions."),
        }
    return {"mode": CURRENT, "label": "Current build",
            "note": "Today's code and accepted corpus evaluated at today's date."}


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
    # --fixed-strings: git reads --author as a regex, and "[bot]" is a character class that
    # matches no commit, so no bot refresh ever entered the history (iteration 17, operations red
    # team).
    out = _git(root, "log", "--reverse", "--format=%H %cI", "--fixed-strings", f"--author={BOT_AUTHOR}",
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
        # One digest over the build's per-group input fingerprints (build_manifest), present from
        # iteration 11 on; earlier builds did not record their inputs and say so with null.
        "inputs_fingerprint": (hashlib.sha256(json.dumps(inputs["groups"], sort_keys=True).encode("utf-8"))
                               .hexdigest()[:16] if isinstance(inputs, dict) and inputs.get("groups") else None),
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
    # First served build carrying each record (iteration 17, first-seen audit). A record already in
    # the first reliable build was present BEFORE tracking began: when it first appeared is not
    # known, and it is labelled so rather than given the tracking start as a fabricated date.
    first_seen = {}
    for e in rows:
        ids = _event_ids(root, e["sha"])
        if ids is not None:
            for eid in ids:
                if eid not in first_seen:
                    first_seen[eid] = ({"status": "present_before_tracking", "served_from": None, "sha": None}
                                       if prev_ids is None else
                                       {"status": "first_served", "served_from": e["served_from"], "sha": e["sha"]})
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
    base["first_seen"] = first_seen
    base["excluded"] = excluded
    base["ledger_captured_at"] = ledger.get("captured_at")
    base["earliest_reliable_as_published_date"] = rows[0]["served_from"][:10] if rows else None
    return base


def known_on(history, day):
    """The as-published history as it could have been known at the end of `day` (iteration 17,
    lane-D red team). A reconstruction for D must not carry builds served after D, nor first-seen
    facts learned after D. Before the first reliable build nothing is known at all: not even
    "present before tracking", which is itself a fact learned on that first build."""
    out = dict(history)
    out["entries"] = [e for e in history.get("entries") or [] if e["served_from"][:10] <= day]
    earliest = history.get("earliest_reliable_as_published_date")
    if earliest is None or day < earliest:
        out["first_seen"] = {}
    else:
        out["first_seen"] = {k: v for k, v in (history.get("first_seen") or {}).items()
                             if not v.get("served_from") or v["served_from"][:10] <= day}
    out["known_on"] = day
    return out


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
