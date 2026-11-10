"""The national energy context layer (iteration 18).

Reads the committed `data/curated/global_context/energy_context.json` (written by the analyst
script `scripts/build_global_context.py` when EIA publishes a release) and emits
`global/energy_context.json`, one row per country.

WHAT THIS IS. Country-level answers to "which countries are large energy producers, and what do
they produce". WHAT IT IS NOT. A monitored system, an incident corpus, an index or a weight.

CONTEXT IS NOT SCORING. Nothing in the disruption analytics imports this module, and a test holds
that: national production must never change an inclusion threshold, weight an incident, rank an
event or rank a facility. A large energy system is not thereby a more vulnerable one.

THE WORLD PICTURE IS NOT THE WORLD INCIDENT CORPUS. A country's `system_id` comes from the
registry and nowhere else. A row without one is shown for context and is "not systematically
monitored"; it is never given a zero count of anything.

NULL IS NOT ZERO. A metric EIA does not publish for a country for the comparison year is null and
the map says "no data". It is not filled from another year or another source. A zero here is
EIA's own zero.

The output holds no build time, so an unchanged source file produces a byte-identical artifact and
cannot cause a daily commit.
"""

import datetime as dt
import unicodedata

from pipeline import outputs, systems
from pipeline.config import CURATED
from pipeline.util import read_json, write_json

CONTEXT_FILE = CURATED / "global_context" / "energy_context.json"
OUTPUT = "global/energy_context.json"

# The canonical unit of each metric family. A row in another unit is a conversion error.
CANONICAL_UNITS = {
    "total_production": "quadrillion Btu", "total_consumption": "quadrillion Btu",
    "prod_coal": "quadrillion Btu", "prod_gas": "quadrillion Btu", "prod_oil": "quadrillion Btu",
    "prod_nuclear": "quadrillion Btu", "prod_renewables": "quadrillion Btu",
    "oil_production": "thousand barrels per day", "crude_production": "thousand barrels per day",
    "oil_consumption": "thousand barrels per day",
    "gas_production": "billion cubic metres", "gas_consumption": "billion cubic metres",
    "coal_production": "million tonnes", "coal_consumption": "million tonnes",
    "electricity_generation": "terawatt-hours",
    "elec_coal": "terawatt-hours", "elec_gas": "terawatt-hours", "elec_oil": "terawatt-hours",
    "elec_nuclear": "terawatt-hours", "elec_hydro": "terawatt-hours", "elec_wind": "terawatt-hours",
    "elec_solar": "terawatt-hours",
}
# What the world map may colour by. Every entry is a national aggregate.
MAP_METRICS = ("total_production", "crude_production", "gas_production", "coal_production",
               "electricity_generation")
ROLES = ("net_producer", "net_consumer", "about_balanced", None)
# A country row that says one of these is no longer national context.
FORBIDDEN_KEY_PARTS = ("rank", "score", "vulnerab", "critical", "target", "importance", "severity",
                       "incident", "event", "disruption")
SOURCE_FIELDS = ("id", "name", "url", "release", "retrieved", "licence", "attribution",
                 "redistribution", "derivatives", "update_cadence")
# Largest national value EIA could plausibly publish, per unit: a guard against a unit slip
# (thousand tonnes read as million, barrels read as thousand barrels).
PLAUSIBLE_MAX = {"quadrillion Btu": 700, "thousand barrels per day": 110000,
                 "billion cubic metres": 5000, "million tonnes": 10000, "terawatt-hours": 40000}


def _walk(x):
    if isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from _walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from _walk(v)


def validate(doc, today=None):
    """Refuse a context file that could mislead. A failure stops the build before anything is
    written, so production keeps serving the last valid file."""
    today = today or dt.date.today()
    problems = []
    year = doc.get("comparison_year")
    if not isinstance(year, int) or isinstance(year, bool):
        problems.append("comparison_year is missing or not a year")
    elif year >= today.year:
        # A year still in progress would be partial data shown as a year's total.
        problems.append(f"comparison_year {year} is not a finished year")
    source = doc.get("source") or {}
    for f in SOURCE_FIELDS:
        if not source.get(f):
            problems.append(f"source.{f} is missing")
    if source.get("redistribution") != "permitted" or source.get("derivatives") != "permitted":
        problems.append("the source's licence does not clearly permit redistribution and derivatives")
    if source.get("retrieved") and source["retrieved"] > today.isoformat():
        problems.append("source.retrieved is in the future")
    metrics = doc.get("metrics") or {}
    if set(metrics) != set(CANONICAL_UNITS):
        problems.append(f"metrics differ from the declared set: {sorted(set(metrics) ^ set(CANONICAL_UNITS))}")
    for m, d in metrics.items():
        if not (d.get("label") and d.get("definition") and d.get("source_series")):
            problems.append(f"metric {m} lacks a label, definition or source series")
        if d.get("unit") != CANONICAL_UNITS.get(m):
            problems.append(f"metric {m} is in {d.get('unit')!r}, not its canonical unit")
    seen = set()
    for c in doc.get("countries") or []:
        a3 = c.get("a3")
        if not (isinstance(a3, str) and len(a3) == 3):
            problems.append(f"bad country code {a3!r}")
        if a3 in seen:
            problems.append(f"duplicate country {a3}")
        seen.add(a3)
        values = c.get("values") or {}
        if set(values) != set(metrics):
            problems.append(f"{a3}: values do not match the declared metrics")
        for m, v in values.items():
            if v is None:
                continue
            if not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0:
                problems.append(f"{a3}.{m}: {v!r} is not a non-negative number or null")
            elif v > PLAUSIBLE_MAX[CANONICAL_UNITS[m]]:
                problems.append(f"{a3}.{m}: {v} is implausible in {CANONICAL_UNITS[m]} (unit error?)")
        for m, n in (c.get("newer") or {}).items():
            if not (isinstance(n.get("year"), int) and year is not None and year < n["year"] < today.year):
                problems.append(f"{a3}.newer.{m}: year {n.get('year')!r} is not a finished year after the comparison year")
        r = c.get("roles") or {}
        if r.get("overall") not in ROLES or any(x not in ROLES for x in (r.get("by_commodity") or {}).values()):
            problems.append(f"{a3}: unknown role")
    if not doc.get("countries"):
        problems.append("no countries")
    bad = sorted({k for k in _walk(doc.get("countries") or []) if any(p in k.lower() for p in FORBIDDEN_KEY_PARTS)})
    if bad:
        problems.append(f"a country row carries a forbidden field: {bad}")
    if problems:
        raise ValueError("global energy context: " + "; ".join(problems[:20]))


def _sort_key(name):
    """Alphabetical as a reader expects: accents and case do not change a name's place."""
    return unicodedata.normalize("NFKD", name).casefold()


def build(world, admin0=None, today=None):
    """Write `global/energy_context.json`. `world` is the world layer, the source of map names."""
    doc = read_json(CONTEXT_FILE)
    validate(doc, today)
    # The registry, and only the registry, says what is monitored.
    owner = {a3: s["id"] for s in systems.SYSTEMS for a3 in s["admin0_a3"]}
    names = {}
    for f in world["features"]:
        p = f["properties"]
        # Crimea and Sevastopol are drawn with a3 UKR but are not Ukraine's name.
        if p.get("status") != "occupied":
            names.setdefault(p.get("a3"), p.get("name"))
    # Natural Earth's short names abbreviate ("S. Sudan"); a table and a card spell them out.
    for f in (admin0 or {}).get("features", []):
        p = f["properties"]
        if "." in (p.get("NAME") or "") and p.get("ADM0_A3") in names and p.get("NAME_LONG"):
            names[p["ADM0_A3"]] = p["NAME_LONG"]
    rows = []
    for c in doc["countries"]:
        rows.append({"a3": c["a3"], "name": names.get(c["a3"], c["name"]), "on_map": c["a3"] in names,
                     "system_id": owner.get(c["a3"]),
                     "values": c["values"], "newer": c.get("newer") or {}, "roles": c["roles"]})
    rows.sort(key=lambda r: _sort_key(r["name"]))
    src = {k: doc["source"][k] for k in SOURCE_FIELDS}
    payload = {
        "schema_version": doc["schema_version"],
        "kind": "national_energy_context",
        "statement": ("National energy statistics, shown for context. Five countries and one theatre are "
                      "systematically monitored for qualifying disruptions; every other country appears "
                      "here only for national context and has no disruption record on this site."),
        "not_scoring": "These figures never change what counts as a disruption, never weight one and never rank one.",
        "source": src,
        "comparison_year": doc["comparison_year"],
        "comparison_year_reason": doc["comparison_year_reason"],
        "balance_band": doc["balance_band"],
        "map_metrics": list(MAP_METRICS),
        "metrics": doc["metrics"],
        "coverage": {m: sum(1 for c in doc["countries"] if c["values"][m] is not None) for m in doc["metrics"]},
        "world": doc["world"],
        "countries": rows,
    }
    out = outputs.processed() / OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(out, payload)
    return payload
