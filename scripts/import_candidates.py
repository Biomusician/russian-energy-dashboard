"""Review a country's candidate queue into its curated events (iteration 14).

    .venv\\Scripts\\python.exe scripts\\import_candidates.py us [cn sa ca in]

`data/candidates/<id>.json` is a research queue written by research lanes. Nothing in it is
published. This script is the gate between the two: it applies the review rules below,
writes only the records that pass to `data/curated/systems/<id>/events.json`, and reports
every record it held back and why. Run it when a queue changes, read the report, and commit
the curated file. The build never reads the queue (see pipeline/build_systems.py).

REVIEW RULES. A candidate is imported only if all hold:
  1. The research lane's suggested disposition is "accept".
  2. Every source has a URL, and not every source is marked as unopened. Lanes record
     `opened: true/false` per source; where a lane did not record it the event says
     "access not recorded" rather than being presented as checked (iteration 14 red team:
     a missing value used to count as opened).
  3. It is placed in a first-level unit of this system, or explicitly at country level.
  4. No text field trips the scope scan (coordinates, distances, vulnerability or dependency
     language, weapon, defence or attack-method detail, cyber technique). A hit holds the
     record for a person to read. Reviewer edits in data/curated/systems/review_edits.json
     are applied first, so a record is scanned as it will ship.
  5. Its id is a well-formed slug and unique in the system.

WHAT REVIEW HERE DOES NOT MEAN. It does not mean each claim was independently re-verified.
Every imported event says so in its `review` block, and the dashboard repeats it.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import build_systems, ids, systems  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REVIEW_DATE = "2026-10-30"

# Geography rulings that hold a record back because the system does not cover the place,
# never because of what happened there.
OUT_OF_GEOGRAPHY = {
    "us": {"US-PR", "US-VI", "US-GU", "US-AS", "US-MP"},
}

# Phrases that have no business in a disruption record under this project's scope boundary.
# Deliberately broad: a false positive costs a person one read; a false negative publishes.
# Widened in iteration 14 after a red team found it missed bare decimal coordinates, distance
# phrasing, hyphenated "air-defence", weapon designators, cyber technique and dependency
# language ("sole feed", "in-feed"), and false-positived on "price range of".
SCOPE_SCAN = re.compile(
    "|".join([
        # coordinates and map links
        r"\d+(\.\d+)?\s*°", r"\b\d{1,3}\.\d{3,}\s*[NSEW]\b", r"\b-?\d{1,3}\.\d{3,}\s*,\s*-?\d{1,3}\.\d{3,}",
        r"\blat(itude)?\b\.?\s*-?\d", r"\blon(gitude)?\b\.?\s*-?\d", r"\blatitude\b", r"\blongitude\b",
        r"maps\.google|google\.[a-z.]+/maps|\?q=-?\d",
        # distance and sub-region placement
        r"\b\d+(\.\d+)?\s*(km|kilomet(re|er)s?|mi|miles?)\s+(north|south|east|west|from|away)",
        r"within (about |roughly |some )?\d+\s*(km|kilomet|mi)", r"\bmilepost\b", r"\bkm from\b",
        r"\b(kilomet(re|er)s?|miles) (from|away)\b",
        # vulnerability, dependency, criticality
        r"vulnerab", r"weakest", r"weak point", r"single[- ]point[- ]of[- ]failure", r"choke ?point",
        r"bottleneck", r"\bredundan", r"\bN-1\b", r"critical node", r"\bin-?feed\b", r"sole (feed|source|supply|line)",
        r"only (line|feed|source|route) (supplying|into|to|feeding)", r"no alternative (supply|route|feed)",
        r"draws? [\d,.–-]+\s*(MW|GW)\s+(via|through|from)",
        # defences and weapons
        r"defen[cs]e gap", r"air[- ]defen[cs]e", r"defen[cs]es (were|was) (thin|weak)", r"intercept",
        r"shot down", r"warhead", r"ballistic", r"cruise missile", r"munition", r"\bShahed\b", r"\bQuds\b",
        r"\bPatriot batter", r"\bS-[34]00\b", r"within range\b",
        # cyber technique
        r"\bexploit", r"malware", r"ransomware", r"\bpayload\b", r"\bCVE-\d", r"\bSCADA\b", r"\bHMI\b",
        r"backdoor", r"phishing", r"Industroyer", r"IEC[- ]?104",
    ]),
    re.I)
TEXT_FIELDS = ("summary", "effect", "threshold_basis", "facility_name", "facility_name_local",
               "operator", "attribution_reported")
EDITS = ROOT / "data" / "curated" / "systems" / "review_edits.json"
DEFAULT_PROCESS = ("Single-pass open-source research lane; centrally reviewed against the "
                   "inclusion threshold, source rules and scope scan. Claims were not "
                   "independently re-verified beyond the cited sources.")


def _texts(r):
    yield from (str(r.get(k) or "") for k in TEXT_FIELDS)
    yield json.dumps(r.get("recovery") or {}, ensure_ascii=False)
    yield json.dumps(r.get("capacity_affected") or {}, ensure_ascii=False)


def review(system_id, r, unit_codes):
    """None if the record passes, else the reason it is held."""
    if r.get("suggested_disposition") != "accept":
        return f"disposition {r.get('suggested_disposition')!r}"
    srcs = r.get("sources") or []
    if not srcs or not all(s.get("url") for s in srcs):
        return "a source has no URL"
    if srcs and all(s.get("opened") is False for s in srcs):
        return "no source was opened by the researcher"
    code = r.get("admin1_code")
    if code in OUT_OF_GEOGRAPHY.get(system_id, set()):
        return f"{code} is outside this system's geography this iteration"
    if r.get("geography_precision") == "admin1" and code not in unit_codes:
        return f"region {code!r} is not a unit of this system"
    if r.get("geography_precision") not in ("admin1", "country"):
        return f"geography precision {r.get('geography_precision')!r}"
    for t in _texts(r):
        m = SCOPE_SCAN.search(t)
        if m:
            return f"scope scan hit {m.group(0)!r}: held for a person to read"
    cid = r.get("candidate_id") or ""
    if ids.full_slug(cid) != cid:
        return f"id {cid!r} is not a slug"
    return None


def apply_edits(r, edits):
    """Apply the reviewer edits for this record. Fails loudly if an edit no longer matches:
    a silently skipped edit would publish the text it was written to remove."""
    import copy
    r = copy.deepcopy(r)
    for e in edits:
        if e["event_id"] != r.get("candidate_id"):
            continue
        path = e["field"].split(".")
        holder = r
        for key in path[:-1]:
            holder = holder.setdefault(key, {})
        leaf = path[-1]
        if "set" in e:
            holder[leaf] = e["set"]
        else:
            old, new = e["replace"]
            text = holder.get(leaf) or ""
            if old not in text:
                raise SystemExit(f"review edit for {e['event_id']}.{e['field']} no longer matches: {old!r}")
            holder[leaf] = text.replace(old, new)
    return r


def to_event(system_id, r):
    precise = r["geography_precision"] == "admin1"
    return {
        "event_id": r["candidate_id"],
        "date": r["date"],
        "date_precision": r.get("date_precision") or "day",
        "date_end": r.get("date_end"),
        "region_code": r["admin1_code"] if precise else None,
        "geography_precision": r["geography_precision"],
        # Multi-unit events stay at country precision. The affected units are listed for the
        # reader, never counted per unit: assigning a three-state blackout to one state would
        # be a guess, and to all three would triple-count it.
        "regions_affected": r.get("admin1_codes_affected") or [],
        "facility_name": r.get("facility_name"),
        "facility_name_local": r.get("facility_name_local"),
        "operator": r.get("operator"),
        "asset_class": r["asset_class"],
        "cause": r["cause"],
        "summary": r["summary"],
        "effect": r.get("effect"),
        "inclusion_basis": "reported_effect" if r.get("effect") else "occurrence",
        "criterion_met": r.get("threshold_clause"),
        "threshold_basis": r.get("threshold_basis"),
        "capacity_affected": r.get("capacity_affected"),
        # Titles are the publishers' headlines, not our words, and the page shows the publisher
        # only; `opened` is null where the lane did not record whether it read the source.
        "sources": [{k: s.get(k) for k in ("url", "publisher", "date", "language",
                                            "source_role", "opened")} for s in r["sources"]],
        "recovery": r.get("recovery") or {"research_status": "NOT_YET_RESEARCHED"},
        "review": {
            # A record from a later research pass carries its own date and process (iteration
            # 15); the iteration-14 lanes' records predate the fields and keep the defaults.
            "reviewed": r.get("reviewed") or REVIEW_DATE,
            "threshold_version": "2026-10-30.1",
            "process": r.get("review_process") or DEFAULT_PROCESS,
            "source_access": ("at least one source read" if any(s.get("opened") is True for s in r["sources"])
                              else "not recorded by the research lane"),
        },
    }


def run(system_id):
    queue = json.loads((ROOT / "data" / "candidates" / f"{system_id}.json").read_text(encoding="utf-8"))
    admin1, admin0 = build_systems.load_admin1(), build_systems.load_admin0()
    unit_codes = {u[0] for u in build_systems.units(system_id, admin1, admin0)}
    edits = json.loads(EDITS.read_text(encoding="utf-8"))["edits"]
    known = {r.get("candidate_id") for r in queue}
    stray = sorted({e["event_id"] for e in edits if e["event_id"].startswith(system_id + "-")} - known)
    if stray:
        raise SystemExit(f"review edits name records not in the {system_id} queue: {stray}")
    queue = [apply_edits(r, edits) for r in queue]
    accepted, held = [], []
    for r in queue:
        why = review(system_id, r, unit_codes)
        if why is None:
            accepted.append(to_event(system_id, r))
        elif r.get("suggested_disposition") == "accept":
            held.append((r["candidate_id"], why))
    out = ROOT / "data" / "curated" / "systems" / system_id / "events.json"
    out.write_text(json.dumps({"system_id": system_id, "events": accepted},
                              ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{system_id}: {len(accepted)} imported, {len(held)} lane-accepted records held")
    for cid, why in held:
        print(f"   held {cid}: {why}")


if __name__ == "__main__":
    for sid in sys.argv[1:]:
        if sid not in systems.COUNTRY_SYSTEMS:
            raise SystemExit(f"unknown country system {sid!r}")
        run(sid)
