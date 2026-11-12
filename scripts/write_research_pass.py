"""Merge the lane logs of a research pass into each country's research log (iteration 18).

    .venv\\Scripts\\python.exe scripts\\write_research_pass.py [cc ...]

Reads the researcher logs in `data/candidates/sweep18/*_lanes.json` (local), combines them with
what iteration 17 established for lanes this pass did not touch, and writes one `systematic` pass
into `data/curated/systems/<cc>/research_log.json`, replacing an earlier run of the same pass.

Counts and process facts only: the per-record narratives stay in the local queue. Lane order is
the plan's, because a test compares the log with Part A as committed.

WHAT IT REFUSES TO DO. A lane is never upgraded here. CARRIED holds iteration-17 evidence in the
new vocabulary; the merge takes the researcher's state where one exists, and the weakest execution
when two researchers shared a lane.
"""
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SWEEP = ROOT / "data" / "candidates" / "sweep18"
SYS = ROOT / "data" / "curated" / "systems"
PASS_DATE = "2026-11-10"
PASS_BY = "iteration-18 research pass"
PLAN_COMMIT = "1a793d5"
PLAN = {"us": "US", "ca": "CA", "cn": "CN", "in": "IN", "sa": "SA"}
ORDER = ("not_started", "partial", "declared_search_complete", "enumerated_complete")
OUTCOMES = ("candidates", "accepted", "rejected", "duplicate", "held", "out_of_scope")

# lane: universe_kind, languages required
KINDS = {
    "us": {"G1": ("census", ["en"]), "G2": ("report_archive", ["en"]), "H1": ("report_archive", ["en"]),
           "H2": ("report_archive", ["en"]), "U1": ("report_archive", ["en"]), "P1": ("census", ["en"]),
           "L1": ("declared_query_set", ["en"]), "R1": ("declared_query_set", ["en"]), "C1": ("declared_query_set", ["en"])},
    "ca": {"CG1": ("census", ["en"]), "CG2": ("report_archive", ["en"]), "CG3": ("report_archive", ["en", "fr"]),
           "CH1": ("report_archive", ["en"]), "CP1": ("census", ["en"]), "CR1": ("declared_query_set", ["en"]),
           "CU1": ("declared_query_set", ["en"]), "CL1": ("declared_query_set", ["en"])},
    "cn": {"CN1": ("report_archive", ["zh"]), "CN2": ("report_archive", ["zh", "en"]), "CN3": ("declared_query_set", ["zh"]),
           "CN4": ("report_archive", ["zh", "en"]), "CN5": ("declared_query_set", ["zh"]), "CN6": ("declared_query_set", ["en"])},
    "in": {"IN1": ("census", ["en"]), "IN2": ("report_archive", ["en"]), "IN3": ("report_archive", ["en"]),
           "IN4": ("report_archive", ["en"]), "IN5": ("report_archive", ["en"]), "IN6": ("declared_query_set", ["en", "hi"]),
           "IN7": ("declared_query_set", ["en"])},
    "sa": {"SA1": ("report_archive", ["ar", "en"]), "SA2": ("report_archive", ["ar", "en"]), "SA3": ("report_archive", ["ar", "en"]),
           "SA4": ("report_archive", ["en"]), "SA5": ("declared_query_set", ["ar", "en"])},
}

# What iteration 17 established, for a lane this pass did not touch. Identical to the checkpoint in
# docs/ITERATION_18_REVIEW.md §0.2.
CARRIED = {
    "G1": ("enumerated_complete", "publisher_not_yet_released", "2025-12-31", None, None,
           "DOE has published no 2026 annual summary."),
    "G2": ("partial", "inaccessible", "2025-12-31", None, None,
           "NERC's reports are read, but ferc.gov refuses automated access and no State of Reliability report covers 2026."),
    "H1": ("partial", "current_through_end_date", "2026-10-31", None, None, "Not re-run after 2026-10-31."),
    "H2": ("enumerated_complete", "publisher_not_yet_released", "2026-06-16", None, None,
           "NHC has not published the Tropical Cyclone Reports for four 2026 storms."),
    "U1": ("partial", "inaccessible", "2026-11-03", None, None,
           "BSEE refuses automated access, so its storm releases are unread; the EIA half is covered."),
    "P1": ("partial", "inaccessible", "2026-11-03", None, None,
           "Every corrective action order is enumerated; PHMSA's incident files refused access."),
    "L1": ("partial", "no_census_exists", "2026-11-03", 90, 10, "One terminal of nine was searched."),
    "R1": ("declared_search_complete", "no_census_exists", "2026-11-03", 15, 15,
           "A declared query set has no census behind it."),
    "C1": ("declared_search_complete", "no_census_exists", "2026-11-03", 10, 10,
           "A declared query set has no census behind it."),
    "CG1": ("enumerated_complete", "publisher_not_yet_released", "2022-12-22", None, None,
            "The Canadian Disaster Database has published nothing after 2022-12-22."),
    "CG2": ("enumerated_complete", "publisher_not_yet_released", "2025-12-31", None, None,
            "No NERC State of Reliability report covers 2026."),
    "CG3": ("partial", "rolling_archive_gap", "2025-12-31", None, None,
            "IESO keeps only 90 days of notices and AESO has published no 2026 list."),
    "CH1": ("partial", "publisher_not_yet_released", "2025-12-31", None, None,
            "No 2026 edition exists; two stories lack a utility peak."),
    "CP1": ("partial", "inaccessible", "2026-10-22", None, None, "The CER file is enumerated; TSB refused access."),
    "CR1": ("declared_search_complete", "no_census_exists", "2026-11-03", 15, 15,
            "A declared query set has no census behind it."),
    "CU1": ("partial", "no_census_exists", "2026-06-01", 10, 5, "Five of ten declared queries ran."),
    "CL1": ("not_started", "no_census_exists", None, None, 0, "Not run."),
    "CN1": ("partial", "current_through_end_date", "2026-10-19", None, None, "Two of about 57 releases were read."),
    "CN2": ("partial", "unknown", "2026-11-03", 15, 15, "NEA and the grid companies were not enumerated directly."),
    "CN3": ("partial", "no_census_exists", "2026-11-03", 10, 10, "No provincial official notice was reached."),
    "CN4": ("not_started", "unknown", None, None, 0, "Not run."),
    "CN5": ("partial", "no_census_exists", "2026-11-03", 15, 5, "Five of 15 queries ran."),
    "CN6": ("not_started", "no_census_exists", None, 15, 0, "Not run."),
    "IN1": ("not_started", "inaccessible", None, None, 0, "Every Grid-India host refused connection."),
    "IN2": ("partial", "unknown", "2026-11-03", 5, 5, "PIB was not enumerated."),
    "IN3": ("partial", "unknown", "2026-11-03", 10, 10, "PPAC and MoPNG were not enumerated."),
    "IN4": ("partial", "unknown", "2026-11-03", 5, 5, "Ministry of Coal and Coal India were not enumerated."),
    "IN5": ("not_started", "unknown", None, 3, 0, "Not run."),
    "IN6": ("not_started", "no_census_exists", None, None, 0, "Not run."),
    "IN7": ("partial", "no_census_exists", "2026-11-03", 10, 10, "Results were not restricted to the named outlets."),
    "SA1": ("partial", "inaccessible", "2026-11-03", 10, 6, "SPA is script-rendered and the ministry site did not respond."),
    "SA2": ("partial", "inaccessible", "2026-11-03", 2, 2, "Tadawul refused access; annual reports were unread."),
    "SA3": ("partial", "unknown", None, None, None, "GASTAT was not reached; JODI carries no attribution."),
    "SA4": ("not_started", "inaccessible", None, None, 0, "The OPEC report archive refused access."),
    "SA5": ("partial", "no_census_exists", "2026-11-03", 15, 6, "Six of 15 queries ran."),
}
# A published log says what was done, never what is being held or who found it: a research log is
# not a route for an unpublished record's name to reach a payload. Sentences about held or
# unaccepted material, and pointers at local files, stay in the local log.
PRIVATE_SENTENCE = re.compile(r"\b(held|hold|candidates?|leads?|accepted|unverified|jeddah|riyadh)\b|\.md\b", re.I)


def unpublished_names(cc):
    """Facility names in the local queue that no published record uses."""
    queue = read(ROOT / "data" / "candidates" / f"{cc}.json")
    events = read(SYS / cc / "events.json")["events"]
    published = {e["event_id"] for e in events}
    public = {(e.get("facility_name") or "").lower() for e in events}
    names = {(r.get("facility_name") or "").strip().lower() for r in queue if r.get("candidate_id") not in published}
    return {n for n in names if len(n) >= 8 and n not in public}


def public_text(text, names):
    if not text:
        return text
    kept = [s for s in re.split(r"(?<=[.!?])\s+", text)
            if not PRIVATE_SENTENCE.search(s) and not any(n in s.lower() for n in names)]
    return " ".join(kept) or None


# Text that shows the search allowance, not the source, stopped a lane.
SEARCH_LIMIT = re.compile(r"search limit|search budget|search cap|cap reached|cap was reached", re.I)

# Lanes where the worker's own state would misstate the record. Each keeps what iteration 17 already
# established and says why. None of these raises a lane above what was actually executed.
OVERRIDES = {
    # Re-checked this pass and unchanged; the universe was enumerated in iteration 17. The worker
    # wrote "partial" because it did not re-enumerate, which would have read as a regression.
    "CG1": {"execution": "enumerated_complete", "source_window": "publisher_not_yet_released", "carried_forward": True},
    "CG2": {"execution": "enumerated_complete", "source_window": "publisher_not_yet_released", "carried_forward": True},
    "G1": {"carried_forward": True},
    "C1": {"carried_forward": True},
    # The plan declared a 2026 re-check on top of the iteration-17 set, and it did not run, so the
    # lane did not reach what this pass declared.
    "CR1": {"execution": "partial", "queries_declared": 16, "queries_run": 15, "covered_through": "2026-11-03", "stopped_by": "search_limit",
            "limitation": "Fifteen of 16 declared queries ran, through 2026-11-03. The 2026 re-check declared for this pass did not run because the search limit was reached."},
    "R1": {"execution": "partial", "queries_declared": 16, "queries_run": 15, "covered_through": "2026-11-03", "stopped_by": "search_limit",
           "limitation": "Fifteen of 16 declared queries ran, through 2026-11-03. The 2026 re-check declared for this pass did not run because the search limit was reached."},
    "IN3": {"source_window": "inaccessible", "stopped_by": "search_limit",
            "limitation_suffix": "None of the ten declared queries ran: the search limit was reached."},
    "IN4": {"stopped_by": "search_limit",
            "limitation_suffix": "None of the five declared queries ran: the search limit was reached."},
    # Two workers each logged their own terminals, so the merge summed a shared total. Nine
    # terminals at ten queries is 90; Sabine ran earlier, Cameron and Cove Point ran here.
    "L1": {"queries_declared": 90, "queries_run": 30, "execution": "partial", "source_window": "no_census_exists",
           "stopped_by": "search_limit",
           "limitation": "Three of nine terminals were searched (Sabine Pass, Cameron, Cove Point); twelve queries for "
                         "terminals not yet operating in the window were not applicable. The rest were not run because the search limit was reached."},
}
ALLOWED_OPTIONAL = ("items_enumerated", "items_in_universe", "finding")


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def logs_for(cc):
    out = {}
    for path in sorted(glob.glob(str(SWEEP / f"{cc}_*_lanes.json"))):
        doc = read(path)
        for lane in doc.get("lanes", []):
            out.setdefault(lane["lane"], []).append(lane)
    return out


def merged(lane_id, entries, kinds):
    """One researcher's states, or the weakest of several (a lane shared between two workers is
    no further along than its less finished half)."""
    ex = min((e["execution"] for e in entries), key=ORDER.index)
    # The more limiting source window wins: blocked before anything else.
    pref = ("inaccessible", "unknown", "rolling_archive_gap", "publisher_not_yet_released", "no_census_exists",
            "current_through_end_date")
    win = min((e["source_window"] for e in entries), key=pref.index)
    ct = [e.get("covered_through") for e in entries]
    out = {
        "universe_kind": kinds[0], "execution": ex, "source_window": win,
        "covered_through": None if any(c is None for c in ct) else min(ct),
        "languages_required": kinds[1],
        "languages_executed": sorted(set.intersection(*[set(e.get("languages_executed") or []) for e in entries])),
    }
    for field in ("queries_declared", "queries_run"):
        vals = [e.get(field) for e in entries if e.get(field) is not None]
        out[field] = sum(vals) if vals else None
    for field in ALLOWED_OPTIONAL:
        vals = [e.get(field) for e in entries if e.get(field) not in (None, "")]
        if vals:
            out[field] = sum(vals) if field != "finding" else " ".join(vals)
    limits = [e.get("limitation") for e in entries if e.get("limitation")]
    out["limitation"] = " ".join(limits) or None
    return out


def pass_for(cc):
    path = SYS / cc / "research_log.json"
    log = read(path)
    previous = [p for p in log["passes"] if p["kind"] == "systematic" and p["date"] != PASS_DATE][-1]
    logs = logs_for(cc)
    names = unpublished_names(cc)
    lanes = []
    for old in previous["lanes"]:
        lid = old["lane"]
        kind = KINDS[cc][lid]
        if lid in logs:
            body = merged(lid, logs[lid], kind)
            body["carried_forward"] = False
            over = dict(OVERRIDES.get(lid, {}))
            suffix = over.pop("limitation_suffix", None)
            body.update(over)
            if suffix:
                body["limitation"] = f"{body.get('limitation') or ''} {suffix}".strip()
            if body["execution"] in ("not_started", "partial") and SEARCH_LIMIT.search(body.get("limitation") or ""):
                body["stopped_by"] = "search_limit"
            body["limitation"] = public_text(body.get("limitation"), names)
            if body.get("finding"):
                body["finding"] = public_text(body["finding"], names)
        else:
            ex, win, ct, qd, qr, limit = CARRIED[lid]
            body = {"universe_kind": kind[0], "execution": ex, "source_window": win, "covered_through": ct,
                    "languages_required": kind[1],
                    # What was run, as iteration 17 logged it; a partial lane is not credited a language.
                    "languages_executed": kind[1] if ex in ("enumerated_complete", "declared_search_complete") else [],
                    "queries_declared": qd, "queries_run": qr, "limitation": limit, "carried_forward": True}
        lanes.append({"lane": lid, "source_family": old["source_family"], "registry": old["registry"], **body})
    outcome = {k: 0 for k in OUTCOMES}
    # Read from the queue after review, so "accepted" means passed blind review, not proposed.
    for r in read(ROOT / "data" / "candidates" / f"{cc}.json"):
        if r.get("research_pass") != f"iteration-18-{cc}":
            continue
        d = r.get("suggested_disposition")
        if d == "accept" and (r.get("independent_review") or {}).get("disposition") not in ("confirmed", "corrected"):
            d = "held"
        outcome["candidates"] += 1
        key = {"accept": "accepted", "reject": "rejected"}.get(d, d)
        if key in outcome:
            outcome[key] += 1
    # A lane carried from an earlier pass is not work this pass did.
    done = sum(1 for x in lanes if x["execution"] in ("enumerated_complete", "declared_search_complete") and not x["carried_forward"])
    entry = {
        "date": PASS_DATE, "by": PASS_BY, "kind": "systematic", "window": ["2022-01-01", PASS_DATE],
        "scope": (f"inclusion clauses 1-7 as written; lanes and queries declared before searching "
                  f"(docs/countries/{PLAN[cc]}_LANE_PASS_18.md); every published record reviewed blind by three "
                  "independent roles and confirmed on its final text"),
        "status": "partial",
        "status_reason": f"{done} of {len(lanes)} lanes executed as far as declared; the rest are stated per lane",
        "outcome": outcome,
        "plan": {"document": f"docs/countries/{PLAN[cc]}_LANE_PASS_18.md", "commit": PLAN_COMMIT},
        "lanes": lanes,
    }
    log["passes"] = [p for p in log["passes"] if not (p["date"] == PASS_DATE and p["by"] == PASS_BY)] + [entry]
    path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(cc, {k: sum(1 for x in lanes if x["execution"] == k) for k in ORDER}, outcome)


if __name__ == "__main__":
    for cc in (sys.argv[1:] or PLAN):
        pass_for(cc)
