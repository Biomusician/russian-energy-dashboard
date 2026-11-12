"""The Gulf regional context artifact (iteration 19): `global/gulf.json`.

A REGIONAL ENERGY PICTURE, NOT A TARGET SET. National aggregates for the eight Gulf systems, with
the regional sum and its share of the world total where every member reports a value. It answers
"which Gulf countries are monitored, and what is each one's broad national energy role?" and
nothing about facilities, routes, straits or dependence.

WHAT IT MAY HOLD. National values from `global/energy_context.json` (one source, one year), plus
any extra national metric in `data/curated/global_context/gulf_regional.json` whose source terms
were read and allow it. Each metric names its own source and year; two sources never share a
column.

WHAT IT MAY NEVER HOLD. A facility, a route, a share attributed to a facility, a prospective
calculation, an importance score, or any field combining metrics. `validate` refuses those keys.

No analytic module may import this one (tests/test_iteration19.py).
"""
from pipeline import outputs, systems
from pipeline.config import CURATED
from pipeline.util import read_json, write_json

EXTRA_FILE = CURATED / "global_context" / "gulf_regional.json"
OUTPUT = "global/gulf.json"
GROUP = "gulf_littoral"
# Shown as columns, in this order. All national, all from the common context source.
BASE_METRICS = ("total_production", "crude_production", "gas_production", "electricity_generation")
FORBIDDEN_KEY_PARTS = ("rank", "score", "vulnerab", "critical", "target", "importance", "severity", "route",
                       "strait", "hormuz", "bypass", "chokepoint", "tanker", "facility", "dependen", "incident",
                       "lat", "lon", "coord",
                       # A regional context file carries no direction of travel either: a count
                       # that grew because records were backfilled is not a region getting worse.
                       "trend", "delta", "worsen", "deteriorat", "change_since", "new_since")


def _walk(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from _walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from _walk(v)


def validate_extra(doc):
    """The curated extra metrics, or ValueError. Every metric states source, licence verdict, year,
    unit and definition, and covers only Gulf members."""
    problems = []
    a3s = {a3 for s in systems.SYSTEMS if s["id"] in systems.GROUPS[GROUP]["members"] for a3 in s["admin0_a3"]}
    for mid, m in (doc.get("metrics") or {}).items():
        for k in ("label", "unit", "definition", "year", "source_id"):
            if not m.get(k):
                problems.append(f"{mid}: no {k}")
        src = (doc.get("sources") or {}).get(m.get("source_id"))
        if not src:
            problems.append(f"{mid}: source {m.get('source_id')!r} is not declared")
        elif src.get("redistribution") != "permitted_with_attribution":
            problems.append(f"{mid}: source terms do not clearly allow redistribution")
        for a3, v in (m.get("values") or {}).items():
            if a3 not in a3s:
                problems.append(f"{mid}: {a3} is not a Gulf member")
            if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0):
                problems.append(f"{mid}.{a3}: {v!r} is not a non-negative number or null")
    bad = sorted({k for k in _walk(doc.get("metrics") or {}) if any(p in k.lower() for p in FORBIDDEN_KEY_PARTS)})
    if bad:
        problems.append(f"forbidden field(s) {bad}")
    if problems:
        raise ValueError("gulf regional context: " + "; ".join(problems))
    return doc


def _region(values_by_member, world_value):
    """Sum and world share, only when every member reports. A partial sum would look like the
    region's figure and be smaller than it."""
    vals = list(values_by_member.values())
    if not vals or any(v is None for v in vals):
        return {"value": None, "world_share": None,
                "reason": f"{sum(1 for v in vals if v is None)} of {len(vals)} members have no value"}
    total = sum(vals)
    return {"value": round(total, 3),
            "world_share": round(total / world_value, 4) if world_value else None, "reason": None}


def build(context, country_payloads):
    """Write `global/gulf.json` from the already-built national context and country payloads."""
    group = systems.GROUPS[GROUP]
    members = [s for s in systems.SYSTEMS if s["id"] in group["members"]]      # registry order: alphabetical
    extra = validate_extra(read_json(EXTRA_FILE)) if EXTRA_FILE.exists() else {"metrics": {}, "sources": {}}
    rows = {r["a3"]: r for r in context["countries"]}
    metrics = {m: {**context["metrics"][m], "year": context["comparison_year"], "source_id": context["source"]["id"]}
               for m in BASE_METRICS}
    for mid, m in extra["metrics"].items():
        metrics[mid] = {k: m[k] for k in ("label", "unit", "definition", "year", "source_id")}
    out_systems = []
    for s in members:
        a3 = s["admin0_a3"][0]
        row = rows.get(a3)
        p = country_payloads[s["id"]]
        values = {m: (row["values"].get(m) if row else None) for m in BASE_METRICS}
        for mid, m in extra["metrics"].items():
            values[mid] = m["values"].get(a3)
        lanes = [x for x in (p["research_log"]["passes"][-1].get("lanes") or [])] if p["research_log"]["passes"] else []
        out_systems.append({
            "system_id": s["id"], "name": s["name"], "a3": a3,
            "gcc_member": s["id"] in systems.GROUPS["gcc"]["members"],
            "opec_member": s["id"] in systems.GROUPS["opec"]["members"],
            "maturity": p["maturity"],
            # A flag, never a count: how many records are withheld is that country's own figure.
            "recovery_status_withheld": p["publication_policy"]["withheld_records"] > 0
                                        or (p["campaign_state"] or {}).get("state") in ("ACTIVE_KINETIC_CAMPAIGN", "RECENT_ENDED_CAMPAIGN", "UNCERTAIN"),
            "values": values,
            "role": row["roles"]["overall"] if row else None,
            "last_systematic_pass": p["research_freshness"]["last_systematic_pass"],
            "lane_states": p["research_freshness"].get("lane_states") or {},
            "languages_required": sorted({x for lane in lanes for x in lane.get("languages_required") or []}),
            "languages_executed": sorted({x for lane in lanes for x in lane.get("languages_executed") or []}),
            "reporting_environment": p["reporting_environment"],
        })
    region = {}
    for mid in metrics:
        world = context["world"]["values"].get(mid) if mid in BASE_METRICS else (extra["metrics"][mid].get("world"))
        region[mid] = _region({x["system_id"]: x["values"][mid] for x in out_systems}, world)
    sources = {context["source"]["id"]: {k: context["source"][k] for k in ("name", "url", "release", "attribution")}}
    for sid, src in extra["sources"].items():
        sources[sid] = {k: src.get(k) for k in ("name", "url", "release", "attribution")}
    payload = {
        "group": GROUP, "label": group["label"], "note": group["note"],
        "statement": ("National energy statistics for the eight Gulf systems, for context. A figure here "
                      "is a country's annual total. It says nothing about any facility, and it is never "
                      "used to weigh, rank or score a disruption."),
        "not_built": ("This view has no route, strait, shipping or tanker information, no facility layer "
                      "and no measure of dependence or importance, by design."),
        "memberships": {g: {"label": systems.GROUPS[g]["label"], "note": systems.GROUPS[g]["note"],
                            "members": [s["id"] for s in members if s["id"] in systems.GROUPS[g]["members"]]}
                        for g in ("gcc", "opec")},
        "order": "alphabetical by name; never by any figure",
        "sources": sources,
        "metrics": metrics,
        "systems": out_systems,
        "region": region,
    }
    bad = sorted({k for k in _walk(payload["systems"]) if any(p in k.lower() for p in FORBIDDEN_KEY_PARTS)})
    if bad:
        raise ValueError(f"gulf context: forbidden field(s) {bad}")
    out = outputs.processed() / OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, payload)
    return payload
