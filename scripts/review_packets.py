"""Build BLIND review packets: the proposed record and its sources, nothing else.

    .venv\\Scripts\\python.exe scripts\\review_packets.py grandfathered      # the iteration-14 records
    .venv\\Scripts\\python.exe scripts\\review_packets.py queue <cc> <pass>  # lane-accepted candidates

WHY (iteration 17). An independent reviewer who reads the researcher's rationale and disposition
first tends to confirm it. A packet therefore carries only what the record claims and where the
claim comes from. Everything that says what someone already concluded about the record is
removed: the researcher's disposition and reason, earlier reviews, primary-review notes and the
lane that surfaced it. `blind()` is the one place that decides what a reviewer may see, and a test
holds it to that.

Packets are written to the local, gitignored queue (`data/candidates/review18/`): they name
records that may never be published.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import systems  # noqa: E402

# The local review directory of the current pass. Earlier passes keep theirs (review18); set
# EDM_REVIEW_DIR to work on one of those.
OUT = ROOT / "data" / "candidates" / os.environ.get("EDM_REVIEW_DIR", "review19")
CURATED = ROOT / "data" / "curated" / "systems"

# What a blind reviewer may see: the claim, its place and time, its sources.
VISIBLE = ("event_id", "candidate_id", "date", "date_precision", "date_end", "region_code",
           "admin1_code", "admin1_name", "geography_precision", "regions_affected",
           "admin1_codes_affected", "facility_name", "facility_name_local", "operator",
           "asset_class", "cause", "hazard_name", "summary", "effect", "criterion_met",
           "threshold_clause", "threshold_basis", "capacity_affected", "recovery", "episode_id",
           # Iteration 19: what the source wrote for the date, so a reviewer can redo the conversion.
           "source_date_text", "date_calendar")
# The source's own headline and its gloss are part of the claim about a non-English source.
SOURCE_FIELDS = ("url", "publisher", "date", "language", "source_role", "title_original", "title_en")


def blind(record):
    """The record as a blind reviewer sees it. Sources keep their address and publisher, never
    whether the researcher opened them or what they thought of them."""
    out = {k: record[k] for k in VISIBLE if k in record}
    out["sources"] = [{k: s.get(k) for k in SOURCE_FIELDS} for s in record.get("sources", [])]
    return out


# Data-governance order, not strategic importance (iteration 17 brief §16).
def priority(e):
    if e["cause"] in ("kinetic_strike", "sabotage") and e["date"] >= "2026":
        return 1
    if len(e["sources"]) == 1:
        return 2
    if len(e["sources"]) <= 2 and all(s.get("source_role") in ("media", "aggregator", None) for s in e["sources"]):
        return 3
    if e["geography_precision"] != "admin1":
        return 4
    if e["cause"] not in ("natural_hazard", "technical"):
        return 5
    return 6


def _write(name, records, note, extra=None):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps({"packet": name, "note": note, **(extra or {}), "records": records},
                               ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{path.relative_to(ROOT)}: {len(records)} records")


def grandfathered():
    gf = set(json.loads((CURATED / "review_grandfathered.json").read_text(encoding="utf-8"))["event_ids"])
    for sid in systems.COUNTRY_SYSTEMS:
        events = json.loads((CURATED / sid / "events.json").read_text(encoding="utf-8"))["events"]
        mine = sorted((e for e in events if e["event_id"] in gf), key=lambda e: (priority(e), e["date"]))
        _write(f"gf_{sid}", [{**blind(e), "priority": priority(e)} for e in mine],
               "Iteration-14 records published under single review, in review-priority order.")


def queue(sid, research_pass):
    q = json.loads((ROOT / "data" / "candidates" / f"{sid}.json").read_text(encoding="utf-8"))
    mine = [r for r in q if r.get("research_pass") == research_pass and r.get("suggested_disposition") == "accept"]
    _write(f"new_{sid}", [blind(r) for r in mine], f"Lane-accepted candidates of {research_pass}.",
           {"system_policy": system_policy(sid)})


def system_policy(sid):
    """What a reviewer must hold this country's records to: the rules, never a conclusion about
    any record. A safety reviewer cannot check "no facility in an attack record" without knowing
    that this is a country where attacks are published at country level."""
    doc = json.loads((CURATED / sid / "system.json").read_text(encoding="utf-8"))
    campaigns = json.loads((CURATED / "conflict_campaigns.json").read_text(encoding="utf-8"))
    covering = [c for c in campaigns["campaigns"] if c["system_id"] == sid and c.get("policy_applied")]
    policy = (doc.get("geography") or {}).get("precision_policy") or {}
    return {
        "kinetic": policy.get("kinetic", "admin1"),
        "other": policy.get("other", "admin1"),
        "no_event_units": policy.get("no_event_units", []),
        "campaign_state": (campaigns.get("system_states") or {}).get(sid, {}).get("state"),
        "recovery_withheld_for_attack_records_from": min((c["member_rule"]["from"] for c in covering), default=None),
        "unit_label": doc["geography"]["unit_label"],
    }


if __name__ == "__main__":
    if sys.argv[1:2] == ["grandfathered"]:
        grandfathered()
    elif sys.argv[1:2] == ["queue"] and len(sys.argv) == 4:
        queue(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
