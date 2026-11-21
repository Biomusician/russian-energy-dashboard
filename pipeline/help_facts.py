"""The live values the reader-facing Help page shows (iteration 23): `global/help_facts.json`.

WHY A FILE OF ITS OWN. The Help page states facts that move with every build: which sectors the
index leaves out, the transmission saturation point, how far the headline moves with the recovery
assumption, the impact layer's caveats and research window, the date published history starts.
Typed into the page, each of those is true on the day it is typed and silently false afterwards.
Read from `snapshot.json` (280 KB) and `impacts.json` (over 1 MB), they would make a page of prose
download the two largest files on the site. So the build copies the few strings Help needs, from
the payloads it has just written, into one small file.

WHAT IT NEVER DOES. It adds no wording of its own and cleans nothing: a served string that a reader
should not see (a file path, a release label, a raw key) is fixed where it is written, and
`tests/test_iteration23_help.py` fails if one reaches this file. It carries no record, no place,
no count per country, and nothing the impact layer's own payload does not already serve.
"""

from pipeline.config import METHODOLOGY_DIR, SECTORS
from pipeline.util import read_json

OUT = "global/help_facts.json"
SCHEMA_VERSION = 1


def _labels(ids):
    """Sector ids as the page names them ("gas" -> "Gas"). An id with no label stays an id, so a
    new sector is visible to the test that forbids raw ids rather than silently renamed."""
    return [SECTORS.get(i, i) for i in ids]


def _contributions(snapshot):
    """Each sector's part of the headline, under its reader label. No mechanism key, no raw value."""
    out = []
    for c in (snapshot.get("explanations") or {}).get("headline", {}).get("contributions") or []:
        out.append({
            "sector": SECTORS.get(c["sector"], c["sector"]),
            "included": bool(c.get("included")),
            "sector_value": c.get("sector_value"),
            "nominal_weight": c.get("nominal_weight"),
            "effective_weight": c.get("effective_weight"),
            "index_points": c.get("index_points"),
            "excluded_reason": c.get("excluded_reason"),
        })
    return out


def build(processed):
    """The Help facts, read from the payloads this build has already written under `processed`."""
    snapshot = read_json(processed / "snapshot.json")
    quality = read_json(processed / "data_quality.json")
    history = read_json(processed / "production_history.json")
    impacts = read_json(processed / "global" / "impacts.json")
    regional = read_json(processed / "global" / "regional_context.json")
    global_quality = read_json(processed / "global" / "data_quality.json")
    scoring = read_json(METHODOLOGY_DIR / "scoring.json")

    sens = snapshot.get("recovery_horizon_sensitivity") or {}
    low, high = (sens.get("esdi_range") or [None, None])[:2]
    bench = (snapshot.get("coverage") or {}).get("oil_benchmark") or {}
    research = impacts.get("research") or {}
    vocab = impacts.get("vocabularies") or {}
    vintage = global_quality.get("context_vintage") or {}

    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": snapshot.get("as_of"),
        "build_time": snapshot.get("build_time"),
        "theatre": {
            "method_version": scoring.get("version"),
            "sectors_uncovered": _labels(snapshot.get("sectors_uncovered") or []),
            "contributions": _contributions(snapshot),
            "transmission_saturation_events": (snapshot.get("denominators") or {}).get("transmission_saturation_events"),
            "recovery_horizon_sensitivity": {
                "declared": sens.get("declared_esdi"),
                "low": low,
                "high": high,
                "note": sens.get("note"),
            },
            "status_delay_days": (snapshot.get("campaign_policy") or {}).get("evidence_embargo_days"),
            "coverage": {
                "enumerated_oil_strikes": bench.get("enumerated_oil_strikes"),
                "reported_oil_strikes": bench.get("reported_oil_strikes"),
                "coverage_ratio": bench.get("coverage_ratio"),
                "incidents_with_quantified_capacity": snapshot.get("incidents_with_quantified_capacity"),
                "incidents_with_reported_effect": snapshot.get("incidents_with_reported_effect"),
                "incident_total": snapshot.get("incident_total"),
            },
            "cannot_tell_you": [{"question": c["question"], "answer": c["answer"]}
                                for c in quality.get("cannot_tell_you") or []],
            "build_date_note": quality.get("build_date_is_not_a_source_date"),
            # What was actually served starts here; nothing earlier is filled in (production_history.py).
            "earliest_published_date": history.get("earliest_reliable_as_published_date"),
        },
        "impacts": {
            "as_of": impacts.get("as_of"),
            "scope_statement": impacts.get("scope_statement"),
            "caveats": impacts.get("caveats") or [],
            # The window, status, date and limits only: the source families carry internal pass names.
            "research": {
                "window": research.get("window"),
                "status": research.get("status"),
                "latest_research_date": research.get("latest_research_date"),
                "limitations": research.get("limitations") or [],
            },
            "cyber_mechanisms": [{"label": m["label"], "definition": m.get("definition")}
                                 for m in vocab.get("cyber_mechanisms") or []],
            "absence_words": [{"label": w["label"], "definition": w.get("definition")}
                              for w in vocab.get("absence_words") or []],
        },
        "regional_context": {
            "as_of": regional.get("as_of"),
            "statement": regional.get("statement"),
            "not_built": regional.get("not_built"),
        },
        "context_vintage": {k: vintage.get(k) for k in
                            ("source", "release", "retrieved", "comparison_year", "update_cadence", "note")},
    }
