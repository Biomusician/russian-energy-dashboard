"""Write the iteration-19 research pass into each Gulf system's research log.

    .venv\\Scripts\\python.exe scripts\\write_gulf_pass.py <plan-commit> [cc ...]

For the seven systems onboarded in iteration 19 this is their FIRST systematic pass; for Saudi
Arabia it is a further pass on the lanes of its own plan. Lanes, their universe kind and their
required languages are read from Part A of the plan document AS COMMITTED at <plan-commit>, so
the log cannot declare a lane the plan did not. What each lane did comes from the researchers'
local logs in `data/candidates/gulf19/<cc>_*_lanes.json`.

WHAT IT REFUSES TO DO. A lane is never upgraded here: where two researchers shared a lane the
weaker execution is kept; a lane no researcher logged is `not_started`; a lane searched in fewer
languages than its plan required is `partial`; a lane with a query left unrun is `partial` and says
whether the search allowance stopped it. Counts and fixed sentences only: none of a researcher's
own prose is published, so per-record narratives and names stay in the local queue.
"""
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import build_systems  # noqa: E402

import os  # noqa: E402

# EDM_PASS=20 writes the iteration-20 continuation (iteration 20 §4-5). The iteration-19 pass is
# history: this script never rewrites a pass other than its own.
PASS = os.environ.get("EDM_PASS", "19")
SWEEP = ROOT / "data" / "candidates" / f"gulf{PASS}"
SYS = ROOT / "data" / "curated" / "systems"
PASS_DATE = {"21": "2026-11-12"}.get(PASS, "2026-11-11")
GULF_PASS_BY = {"19": "iteration-19 Gulf research pass", "20": "iteration-20 Gulf continuation pass",
                "21": "iteration-21 Gulf continuation pass"}
PASS_BY = GULF_PASS_BY[PASS]
LANE_GLOB = {"19": "{cc}_*_lanes.json", "20": "{cc}_lanes20.json", "21": "{cc}_lanes21.json"}[PASS]
# Iteration 21 worked only the lanes its plan named (the ones the search allowance stopped, and SA4).
# A lane file states a lane's cumulative state, so the newest entry replaces the earlier one, and a
# lane nobody worked keeps its iteration-20 state, marked carried forward.
CARRY_FROM = {"21": ROOT / "data" / "candidates" / "gulf20"}.get(PASS)
CONTINUES = {"20": {"date": "2026-11-11", "by": "iteration-19 Gulf research pass"},
             "21": {"date": "2026-11-11", "by": "iteration-20 Gulf continuation pass"}}.get(PASS)
CONTINUATION_PLAN = "docs/countries/GULF_CONTINUATION_PLAN_20.md"
PLAN_DOC = {cc: f"docs/countries/{cc.upper()}_SYSTEMATIC_SWEEP.md" for cc in ("ae", "bh", "iq", "ir", "kw", "om", "qa")}
PLAN_DOC["sa"] = "docs/countries/SA_LANE_PASS_19.md"
ORDER = ("not_started", "partial", "declared_search_complete", "enumerated_complete")
# The more limiting source window wins: blocked before anything else.
WINDOWS = ("inaccessible", "unknown", "rolling_archive_gap", "publisher_not_yet_released", "no_census_exists",
           "current_through_end_date")
OUTCOMES = ("candidates", "accepted", "rejected", "duplicate", "held", "out_of_scope")
KIND = {"declared query set": "declared_query_set", "report archive": "report_archive", "census": "census"}
SEARCH_LIMIT = re.compile(r"search (limit|allowance|cap|budget)", re.I)



def public_outcome(cc, entry):
    """A system under the campaign policy keeps its counts in the local queue folder; its public
    log says only whether anything is still under review (iteration 20, safety red team)."""
    states = (json.loads((ROOT / "data" / "curated" / "systems" / "conflict_campaigns.json").read_text(encoding="utf-8"))
              .get("system_states") or {})
    if (states.get(cc) or {}).get("state") not in ("ACTIVE_KINETIC_CAMPAIGN", "RECENT_ENDED_CAMPAIGN", "UNCERTAIN"):
        return entry
    local = ROOT / "data" / "candidates" / "research_outcomes.json"
    store = json.loads(local.read_text(encoding="utf-8")) if local.exists() else {}
    o = entry["outcome"]
    store.setdefault(cc, {})[f"{entry['date']}|{entry['by']}"] = o
    local.write_bytes((json.dumps(store, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return {**entry, "outcome": {}, "under_review": bool(o.get("held") or o.get("insufficient_evidence"))}

def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def plan_lanes(cc, commit):
    """[(lane, universe_kind, [languages])] from Part A of the committed plan."""
    r = subprocess.run(["git", "show", f"{commit}:{PLAN_DOC[cc]}"], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(f"{cc}: {PLAN_DOC[cc]} is not in commit {commit}; commit the plan before the pass")
    part_a = r.stdout.split("## Part B")[0]
    out = []
    for m in re.finditer(r"^\| ([A-Z]{1,2}\d) \| ([^|]+)\| ([^|]+)\|", part_a, flags=re.M):
        kind = KIND[m.group(2).strip().lower()]
        # "ar (+en)" requires Arabic; a language in brackets is optional.
        required = re.sub(r"\([^)]*\)", "", m.group(3))
        langs = sorted(set(re.findall(r"\b(ar|en|fa|ku)\b", required)))
        out.append((m.group(1), kind, langs))
    if not out:
        raise SystemExit(f"{cc}: no lane table in {PLAN_DOC[cc]} at {commit}")
    return out


def registry_for(cc):
    """Lane -> (source family, registry names), from the curated `lane_registry` of system.json."""
    doc = read(SYS / cc / "system.json")
    reg = doc.get("lane_registry")
    if not reg:
        raise SystemExit(f"{cc}: system.json has no lane_registry (lane -> family and registry sources)")
    return reg


def logs_for(cc):
    out = {}
    for path in sorted(glob.glob(str(SWEEP / LANE_GLOB.format(cc=cc)))):
        for lane in read(path).get("lanes", []):
            out.setdefault(lane["lane"], []).append(lane)
    return out


def carried_for(cc):
    """Lanes of the previous pass that this pass did not work (iteration 21 onward)."""
    if not CARRY_FROM:
        return {}
    out = {}
    for path in sorted(glob.glob(str(CARRY_FROM / "{cc}_lanes20.json".format(cc=cc)))):
        for lane in read(path).get("lanes", []):
            out.setdefault(lane["lane"], []).append(lane)
    return out


# A lane note is the researcher's own prose about what the search turned up. It was never reviewed,
# and for these systems most of what a search turns up is reports of attacks. Two filters that
# removed sentences by word list each let paraphrase through ("a contained fire at an oil-industry
# zone", "the June explosion", "supplies were stable"): beside a record published without its
# place, such a sentence gives the place type and the later status back (release safety red team,
# iteration 19). So no researcher prose is published for a Gulf lane at all. The note is read only
# to choose among the fixed sentences below; its numbers travel in the lane's own count fields.
NOTE_REFUSED = "At least one source in this lane refused automated access and was not worked around."
NOTE_SCRIPT = "At least one official listing is built by script in the browser and could not be read."
NOTE_SIZE = "At least one document was too large for the fetch tool or timed out."
NOTE_YEAR = ("The search tool gave little weight to year terms, so earlier years were reached mainly through "
             "publishers' own listings.")
NOTE_RELAYED = "Official statements were read as carried by other publishers, not on the issuing body's own site."
NOTE_PART_LISTING = "The listings that could be read were read in part: by title, or for their newest pages only."
NOTE_UNREAD = "Some declared documents were not read."
NOTE_LANGUAGE = "Not run in every language its plan requires."
NOTE_UNRUN = "Not every declared query was run."
NOTE_ALLOWANCE = "The shared search allowance ran out before every declared query was run."
NOTE_UNASSIGNED = "No researcher was assigned to this lane in this pass."
NOTE_DEFAULT = "Not run as far as declared in this pass."
NOTE_NO_CENSUS = ("No complete public list of events exists for this lane, so a search that finds nothing is not a year "
                  "shown to be quiet.")
LANE_NOTES = (NOTE_UNASSIGNED, NOTE_ALLOWANCE, NOTE_UNRUN, NOTE_LANGUAGE, NOTE_REFUSED, NOTE_SCRIPT, NOTE_SIZE, NOTE_YEAR,
              NOTE_RELAYED, NOTE_PART_LISTING, NOTE_UNREAD, NOTE_NO_CENSUS, NOTE_DEFAULT)
NOTE_SIGNS = (
    (NOTE_REFUSED, re.compile(r"\b(40[123]|429)\b|refus|blocked|bot challenge|captcha|access denied|login wall|paywall", re.I)),
    (NOTE_SCRIPT, re.compile(r"script", re.I)),
    (NOTE_SIZE, re.compile(r"fetch (size|limit)|size limit|too large|exceeds?\b|100,000 characters|\d MB\b|timed out", re.I)),
    (NOTE_YEAR, re.compile(r"year (token|term)|honou?r the year|whatever year", re.I)),
    (NOTE_RELAYED, re.compile(r"relay|as carried|press cop|syndicat|republish|search-result summar", re.I)),
    (NOTE_PART_LISTING, re.compile(r"page 1\b|only the newest|newest days|not paged|by title|titles only|not enumerated|incomplete", re.I)),
    (NOTE_UNREAD, re.compile(r"(was|were) not (read|located|opened)|no reachable address|could not be read", re.I)),
)


def fixed_notes(raw, body, stopped):
    """The lane's published limitation: fixed sentences only, in a fixed order."""
    if body["execution"] == "not_started" and not raw:
        return NOTE_UNASSIGNED
    out = []
    qd, qr = body.get("queries_declared"), body.get("queries_run")
    short = isinstance(qd, int) and qd > 0 and (qr or 0) < qd
    if stopped or body.get("stopped_by") == "search_limit":
        out.append(NOTE_ALLOWANCE)
    elif short:
        out.append(NOTE_UNRUN)
    if not set(body["languages_required"]) <= set(body["languages_executed"]):
        out.append(NOTE_LANGUAGE)
    out += [note for note, sign in NOTE_SIGNS if sign.search(raw or "")]
    if body["source_window"] == "no_census_exists":
        out.append(NOTE_NO_CENSUS)
    return " ".join(out) or NOTE_DEFAULT


def merged(entries, kind, langs):
    ex = min((e["execution"] for e in entries), key=ORDER.index)
    win = min((e.get("source_window") or "unknown" for e in entries), key=WINDOWS.index)
    ct = [e.get("covered_through") for e in entries]
    # A qualified entry ("en (2022 only)") is a language the lane did NOT fully run: only a bare
    # code counts, so the lane is listed among those short of a required language.
    ran = [{x for x in (e.get("languages_executed") or []) if re.fullmatch(r"[a-z]{2}", x)} for e in entries]
    executed = sorted(set.intersection(*ran))
    out = {"universe_kind": kind, "execution": ex, "source_window": win,
           "covered_through": None if any(c is None for c in ct) else min(ct),
           "languages_required": langs, "languages_executed": executed}
    for field in ("queries_declared", "queries_run", "items_enumerated", "items_in_universe"):
        vals = [e.get(field) for e in entries if isinstance(e.get(field), int)]
        if vals:
            # Two researchers on one lane share its declared set: the declared count is the plan's,
            # not their sum.
            out[field] = max(vals) if field == "queries_declared" else sum(vals)
    # Items read against a universe counted in other units ("73 of 3": 73 items on 3 listings) is
    # not a fraction. The universe is kept only where it can be one.
    if isinstance(out.get("items_in_universe"), int) and out.get("items_enumerated", 0) > out["items_in_universe"]:
        del out["items_in_universe"]
    # The researchers' own prose, read to choose the fixed notes and never published.
    raw = " ".join(str(e.get(k)) for e in entries for k in ("limitation", "finding", "universe_note") if e.get(k))
    stopped = any(e.get("stopped_by") == "search_limit" for e in entries)
    return out, stopped, raw


def honest(body, stopped, raw=""):
    """Lower a lane to what its own numbers support. Never raises one."""
    qd, qr = body.get("queries_declared"), body.get("queries_run")
    kind, ex = body["universe_kind"], body["execution"]
    missing_lang = not set(body["languages_required"]) <= set(body["languages_executed"])
    short = isinstance(qd, int) and qd > 0 and (qr or 0) < qd
    if ex in ("declared_search_complete", "enumerated_complete") and (missing_lang or short or stopped):
        body["execution"] = ex = "partial"
    if ex == "declared_search_complete" and kind != "declared_query_set":
        body["execution"] = ex = "partial"
    if ex == "enumerated_complete" and (kind == "declared_query_set"
                                        or body["source_window"] not in ("current_through_end_date", "publisher_not_yet_released")):
        body["execution"] = ex = "partial"
    if kind == "declared_query_set" and body["source_window"] not in ("no_census_exists", "inaccessible"):
        body["source_window"] = "no_census_exists"
    if body["source_window"] == "inaccessible" and ex in ("declared_search_complete", "enumerated_complete"):
        body["execution"] = ex = "partial"
    if ex == "not_started":
        body.pop("queries_run", None)
        body.pop("items_enumerated", None)
        body["languages_executed"] = []
        body["covered_through"] = None
    if ex in ("not_started", "partial") and (stopped or (short and SEARCH_LIMIT.search(raw or ""))):
        body["stopped_by"] = "search_limit"
    return body


def pass_for(cc, commit):
    path = SYS / cc / "research_log.json"
    log = read(path)
    logs, reg = logs_for(cc), registry_for(cc)
    carried = carried_for(cc)
    lanes = []
    for lid, kind, langs in plan_lanes(cc, commit):
        family, registry = reg[lid]["source_family"], reg[lid]["registry"]
        forward = lid not in logs and lid in carried
        if lid in logs or forward:
            body, stopped, raw = merged(logs[lid] if lid in logs else carried[lid], kind, langs)
        else:
            body, stopped, raw = {"universe_kind": kind, "execution": "not_started", "source_window": "unknown",
                                  "covered_through": None, "languages_required": langs, "languages_executed": []}, False, ""
        body = honest(body, stopped, raw)
        body["limitation"] = fixed_notes(raw, body, stopped)
        body["carried_forward"] = forward
        lanes.append({"lane": lid, "source_family": family, "registry": registry, **body})
    outcome = {k: 0 for k in OUTCOMES}
    qpath = ROOT / "data" / "candidates" / f"{cc}.json"
    for r in (read(qpath) if qpath.exists() else []):
        if r.get("research_pass") != f"iteration-{PASS}-{cc}":
            continue
        d = r.get("suggested_disposition")
        # "accepted" means passed blind review, not proposed by a researcher.
        if d == "accept" and (r.get("independent_review") or {}).get("disposition") not in ("confirmed", "corrected"):
            d = "held"
        outcome["candidates"] += 1
        key = {"accept": "accepted", "reject": "rejected"}.get(d, d)
        if key in outcome:
            outcome[key] += 1
    done = sum(1 for x in lanes if x["execution"] in ("enumerated_complete", "declared_search_complete"))
    entry = {
        "date": PASS_DATE, "by": PASS_BY, "kind": "systematic", "window": ["2022-01-01", PASS_DATE],
        "scope": (f"inclusion clauses 1-7 as written; lanes and queries declared before searching ({PLAN_DOC[cc]}); "
                  "every published record reviewed blind by three independent roles and confirmed on its final text"),
        "status": "complete" if done == len(lanes) else "partial",
        "status_reason": f"{done} of {len(lanes)} lanes executed as far as declared; the rest are stated per lane",
        "outcome": outcome,
        "plan": {"document": PLAN_DOC[cc], "commit": commit},
        "lanes": lanes,
    }
    if CONTINUES:
        # The lanes are the iteration-19 plan's (Part A, as committed); the work order is the
        # continuation plan, committed in the same commit before any search.
        entry["plan"] = {"document": CONTINUATION_PLAN, "commit": commit, "lanes_from": PLAN_DOC[cc]}
        entry["continues"] = CONTINUES
        if CARRY_FROM:
            entry["scope"] = (f"continuation of the iteration-20 pass: the remaining declared queries of lanes the shared "
                              f"search allowance had stopped, and one archive lane, as declared in {PLAN_DOC[cc]}; lanes "
                              "not worked in this pass keep their iteration-20 state and are marked carried forward; "
                              "inclusion clauses 1-7 read strictly; every published record reviewed blind by three "
                              "independent roles and confirmed on its final text")
        else:
            entry["scope"] = (f"continuation of the iteration-19 pass: lanes as declared in {PLAN_DOC[cc]}, work order in "
                              f"{CONTINUATION_PLAN}; each lane states its execution after both passes; inclusion clauses 1-7 "
                              "read strictly; every published record reviewed blind by three independent roles and "
                              "confirmed on its final text")
    for lane in lanes:
        problems = build_systems.lane_problems(lane, entry["window"])
        if problems:
            raise SystemExit(f"{cc}: " + "; ".join(problems))
    entry = public_outcome(cc, entry)
    log["passes"] = [p for p in log["passes"] if not (p["date"] == PASS_DATE and p["by"] == PASS_BY)] + [entry]
    path.write_bytes((json.dumps(log, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(cc, {k: sum(1 for x in lanes if x["execution"] == k) for k in ORDER}, outcome)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for cc in (sys.argv[2:] or sorted(PLAN_DOC)):
        pass_for(cc, sys.argv[1])
