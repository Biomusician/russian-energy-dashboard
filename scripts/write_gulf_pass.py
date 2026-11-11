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
whether the search allowance stopped it. Counts and process facts only: per-record narratives and
the names of unpublished facilities stay in the local queue.
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

SWEEP = ROOT / "data" / "candidates" / "gulf19"
SYS = ROOT / "data" / "curated" / "systems"
PASS_DATE = "2026-11-11"
PASS_BY = "iteration-19 Gulf research pass"
PLAN_DOC = {cc: f"docs/countries/{cc.upper()}_SYSTEMATIC_SWEEP.md" for cc in ("ae", "bh", "iq", "ir", "kw", "om", "qa")}
PLAN_DOC["sa"] = "docs/countries/SA_LANE_PASS_19.md"
ORDER = ("not_started", "partial", "declared_search_complete", "enumerated_complete")
# The more limiting source window wins: blocked before anything else.
WINDOWS = ("inaccessible", "unknown", "rolling_archive_gap", "publisher_not_yet_released", "no_census_exists",
           "current_through_end_date")
OUTCOMES = ("candidates", "accepted", "rejected", "duplicate", "held", "out_of_scope")
KIND = {"declared query set": "declared_query_set", "report archive": "report_archive", "census": "census"}
SEARCH_LIMIT = re.compile(r"search (limit|allowance|cap|budget)", re.I)


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
    for path in sorted(glob.glob(str(SWEEP / f"{cc}_*_lanes.json"))):
        for lane in read(path).get("lanes", []):
            out.setdefault(lane["lane"], []).append(lane)
    return out


def unpublished_names(cc):
    """Facility and operator names in the queue that are not on a published record. A limitation
    that names one would publish what review held back."""
    qpath = ROOT / "data" / "candidates" / f"{cc}.json"
    if not qpath.exists():
        return []
    published = json.dumps(read(SYS / cc / "events.json"), ensure_ascii=False).lower()
    names = set()
    for r in read(qpath):
        for k in ("facility_name", "facility_name_local", "operator"):
            n = r.get(k)
            if n and len(n) >= 5 and n.lower() not in published:
                names.add(n)
    return sorted(names, key=len, reverse=True)


def public_text(text, names):
    """`text` with unpublished names and status wording taken out, or a plain fallback."""
    if not text:
        return text
    for n in names:
        text = re.sub(re.escape(n), "a facility", text, flags=re.I)
    if build_systems.status_wording(text):
        sentences = [s for s in re.split(r"(?<=[.;])\s+", text) if not build_systems.status_wording(s)]
        text = " ".join(sentences) or "See the plan document; the researcher's note is kept in the local queue."
    return text.strip()


def merged(entries, kind, langs):
    ex = min((e["execution"] for e in entries), key=ORDER.index)
    win = min((e.get("source_window") or "unknown" for e in entries), key=WINDOWS.index)
    ct = [e.get("covered_through") for e in entries]
    executed = sorted(set.intersection(*[set(e.get("languages_executed") or []) for e in entries]) & set(langs)
                      | (set.intersection(*[set(e.get("languages_executed") or []) for e in entries]) - set(langs)))
    out = {"universe_kind": kind, "execution": ex, "source_window": win,
           "covered_through": None if any(c is None for c in ct) else min(ct),
           "languages_required": langs, "languages_executed": executed}
    for field in ("queries_declared", "queries_run", "items_enumerated", "items_in_universe"):
        vals = [e.get(field) for e in entries if isinstance(e.get(field), int)]
        if vals:
            # Two researchers on one lane share its declared set: the declared count is the plan's,
            # not their sum.
            out[field] = max(vals) if field == "queries_declared" else sum(vals)
    finding = " ".join(e["finding"] for e in entries if e.get("finding"))
    if finding:
        out["finding"] = finding
    out["limitation"] = " ".join(e["limitation"] for e in entries if e.get("limitation")) or None
    stopped = any(e.get("stopped_by") == "search_limit" for e in entries)
    return out, stopped


def honest(body, stopped):
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
    if ex in ("not_started", "partial") and (stopped or (short and SEARCH_LIMIT.search(body.get("limitation") or ""))):
        body["stopped_by"] = "search_limit"
    if ex in ("not_started", "partial") or body["source_window"] != "current_through_end_date":
        body["limitation"] = body.get("limitation") or "Not run in this pass."
    return body


def pass_for(cc, commit):
    path = SYS / cc / "research_log.json"
    log = read(path)
    logs, reg, names = logs_for(cc), registry_for(cc), unpublished_names(cc)
    lanes = []
    for lid, kind, langs in plan_lanes(cc, commit):
        family, registry = reg[lid]["source_family"], reg[lid]["registry"]
        if lid in logs:
            body, stopped = merged(logs[lid], kind, langs)
        else:
            body, stopped = {"universe_kind": kind, "execution": "not_started", "source_window": "unknown",
                             "covered_through": None, "languages_required": langs, "languages_executed": [],
                             "limitation": "No researcher was assigned to this lane in this pass."}, False
        body = honest(body, stopped)
        body["limitation"] = public_text(body.get("limitation"), names)
        if body.get("finding"):
            body["finding"] = public_text(body["finding"], names)
        body["carried_forward"] = False
        lanes.append({"lane": lid, "source_family": family, "registry": registry, **body})
    outcome = {k: 0 for k in OUTCOMES}
    qpath = ROOT / "data" / "candidates" / f"{cc}.json"
    for r in (read(qpath) if qpath.exists() else []):
        if r.get("research_pass") != f"iteration-19-{cc}":
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
    for lane in lanes:
        problems = build_systems.lane_problems(lane, entry["window"])
        if problems:
            raise SystemExit(f"{cc}: " + "; ".join(problems))
    log["passes"] = [p for p in log["passes"] if not (p["date"] == PASS_DATE and p["by"] == PASS_BY)] + [entry]
    path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(cc, {k: sum(1 for x in lanes if x["execution"] == k) for k in ORDER}, outcome)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for cc in (sys.argv[2:] or sorted(PLAN_DOC)):
        pass_for(cc, sys.argv[1])
