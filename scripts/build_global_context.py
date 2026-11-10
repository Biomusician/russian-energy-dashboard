"""Build the curated national energy context from EIA's International Energy Statistics.

    .venv\\Scripts\\python.exe scripts\\build_global_context.py [path-to-INTL.zip]

An ANALYST step, run when EIA publishes a new release, never in the daily refresh: national energy
statistics change about once a year, and fetching them daily would add a way for the refresh to
fail and nothing else. It reads the bulk file (data/raw/global/INTL.zip, gitignored) and writes one
committed file, data/curated/global_context/energy_context.json, which the daily build re-emits
unchanged. If EIA disappears tomorrow the last valid file keeps being served, with its vintage.

WHAT THIS IS FOR. Which countries are large energy producers and what they produce. National
aggregates only: no facility, no route, no region. It never enters any disruption analytic
(docs/GLOBAL_ENERGY_CONTEXT.md).

ONE COMPARISON YEAR, ONE SOURCE. Every map value is the same year from the same dataset. A metric
a country lacks for that year is null: it is not filled from another year or another source.
Series that run later than the comparison year are kept apart as `newer`, for a country's own page.
"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "global" / "INTL.zip"
OUT = ROOT / "data" / "curated" / "global_context" / "energy_context.json"

COMPARISON_YEAR = 2024
RETRIEVED = "2026-11-10"
RELEASE = "2026-10-16"
QBTU, KBD, BCM, MT, TWH = ("quadrillion Btu", "thousand barrels per day", "billion cubic metres",
                           "million tonnes", "terawatt-hours")

# id: (series code, source unit tag, multiplier into the canonical unit, canonical unit, label, definition)
METRICS = {
    "total_production": ("44-1", "QBTU", 1, QBTU, "Total primary energy production",
                         "EIA total energy production: coal, natural gas, petroleum and other liquids, nuclear, and renewables and other, in one energy unit."),
    "total_consumption": ("44-2", "QBTU", 1, QBTU, "Total primary energy consumption",
                          "EIA total energy consumption, in one energy unit."),
    "prod_coal": ("4411-1", "QBTU", 1, QBTU, "Production from coal", "Part of total production."),
    "prod_gas": ("4413-1", "QBTU", 1, QBTU, "Production from natural gas", "Part of total production."),
    "prod_oil": ("4415-1", "QBTU", 1, QBTU, "Production from petroleum and other liquids", "Part of total production."),
    "prod_nuclear": ("4417-1", "QBTU", 1, QBTU, "Production from nuclear", "Part of total production."),
    "prod_renewables": ("4418-1", "QBTU", 1, QBTU, "Production from renewables and other", "Part of total production."),
    "oil_production": ("53-1", "TBPD", 1, KBD, "Oil production",
                       "EIA petroleum and other liquids production: crude oil with lease condensate, natural gas plant liquids, other liquids and refinery processing gain. Wider than crude oil alone."),
    "crude_production": ("57-1", "TBPD", 1, KBD, "Crude oil production", "EIA crude oil including lease condensate."),
    "oil_consumption": ("5-2", "TBPD", 1, KBD, "Oil consumption", "EIA petroleum and other liquids consumption."),
    "gas_production": ("26-1", "BCM", 1, BCM, "Natural gas production", "EIA dry natural gas production."),
    "gas_consumption": ("26-2", "BCM", 1, BCM, "Natural gas consumption", "EIA dry natural gas consumption."),
    "coal_production": ("7-1", "MT", 0.001, MT, "Coal production",
                        "EIA coal production by mass, all ranks; a tonne of lignite and a tonne of hard coal count alike."),
    "coal_consumption": ("7-2", "MT", 0.001, MT, "Coal consumption", "EIA coal consumption by mass, all ranks."),
    "electricity_generation": ("2-12", "BKWH", 1, TWH, "Electricity generation", "EIA net electricity generation, all sources."),
    "elec_coal": ("30-12", "BKWH", 1, TWH, "Electricity from coal", "Part of net generation."),
    "elec_gas": ("31-12", "BKWH", 1, TWH, "Electricity from natural gas", "Part of net generation."),
    "elec_oil": ("32-12", "BKWH", 1, TWH, "Electricity from petroleum", "Part of net generation."),
    "elec_nuclear": ("27-12", "BKWH", 1, TWH, "Electricity from nuclear", "Part of net generation."),
    "elec_hydro": ("33-12", "BKWH", 1, TWH, "Electricity from hydro", "Part of net generation."),
    "elec_wind": ("37-12", "BKWH", 1, TWH, "Electricity from wind", "Part of net generation."),
    "elec_solar": ("116-12", "BKWH", 1, TWH, "Electricity from solar", "Part of net generation."),
}
ROUND = {QBTU: 3, KBD: 1, BCM: 2, MT: 2, TWH: 2}

# EIA aggregates and countries that no longer exist. Everything else with a 2024 total is a
# country or territory row.
NOT_COUNTRIES = {
    "WORL", "AFRC", "ASOC", "CSAM", "EURA", "EURO", "MIDE", "NOAM", "OECD", "OEAO", "OEEU", "OENA",
    "OPEC", "OPAF", "OPNO", "OPSA", "NOEC", "PERG", "EU27", "HITZ", "USIQ", "USOH",
    "SUN", "YUG", "SCG", "DDR", "DEUW", "CSK", "NLDA", "WAK",
}
# EIA's country code where it differs from Natural Earth's ADM0_A3 (the map's key).
EIA_TO_NE = {"SSD": "SDS", "PSE": "PSX", "XKS": "KOS", "ESH": "SAH"}
# The display rule for the broad producer/consumer role: within 15% is "about balanced".
BALANCE_BAND = 0.15


def number(x):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def load(path):
    series = {}
    with zipfile.ZipFile(path).open("INTL.txt") as f:
        for line in f:
            d = json.loads(line)
            if d.get("f") == "A" and "series_id" in d:
                series[d["series_id"]] = d
    return series


def role(prod, cons):
    if prod is None or cons is None or (prod == 0 and cons == 0):
        return None
    if cons == 0 or prod / cons >= 1 + BALANCE_BAND:
        return "net_producer"
    if prod / cons <= 1 - BALANCE_BAND:
        return "net_consumer"
    return "about_balanced"


def row_for(series, code):
    values, newer = {}, {}
    for mid, (s, unit_tag, mult, unit, *_rest) in METRICS.items():
        d = series.get(f"INTL.{s}-{code}-{unit_tag}.A")
        if not d:
            values[mid] = None
            continue
        # A negative national figure (refinery losses netted against output) is not a production\r
        # level; it is treated as not available rather than drawn as a value.\r
        by_year = {int(y): (None if number(v) is None or v < 0 else v) for y, v in d["data"]}
        v = by_year.get(COMPARISON_YEAR)
        values[mid] = None if v is None else round(v * mult, ROUND[unit])
        later = sorted(y for y, x in by_year.items() if y > COMPARISON_YEAR and x is not None)
        if later:
            newer[mid] = {"year": later[-1], "value": round(by_year[later[-1]] * mult, ROUND[unit])}
    return values, newer


def roles(v):
    commodity = {"oil": role(v["oil_production"], v["oil_consumption"]),
                 "gas": role(v["gas_production"], v["gas_consumption"]),
                 "coal": role(v["coal_production"], v["coal_consumption"])}
    return {"overall": role(v["total_production"], v["total_consumption"]), "by_commodity": commodity}


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else RAW
    series = load(path)
    codes = sorted(k.split("-")[2] for k in series
                   if k.startswith("INTL.44-1-") and k.endswith("-QBTU.A"))
    countries, skipped = [], []
    prefix, suffix = "Total energy production, ", ", Annual"
    for code in codes:
        if code in NOT_COUNTRIES or code.startswith("WP"):
            continue
        name = series[f"INTL.44-1-{code}-QBTU.A"]["name"]
        name = name[len(prefix):-len(suffix)] if name.startswith(prefix) else name
        values, newer = row_for(series, code)
        if values["total_production"] is None and values["total_consumption"] is None:
            skipped.append(code)
            continue
        countries.append({"a3": EIA_TO_NE.get(code, code), "eia_code": code, "name": name,
                          "values": values, "newer": newer, "roles": roles(values)})
    world_values, _ = row_for(series, "WORL")
    doc = {
        "schema_version": 1,
        "source": {
            "id": "eia-international-energy-statistics",
            "name": "U.S. Energy Information Administration, International Energy Statistics",
            "url": "https://www.eia.gov/international/data/world",
            "bulk_url": "https://www.eia.gov/opendata/bulk/INTL.zip",
            "release": RELEASE,
            "retrieved": RETRIEVED,
            "bulk_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "licence": "U.S. government work; EIA's bulk file states no copyright on these series (copyright field: None).",
            "attribution": "Source: U.S. Energy Information Administration, International Energy Statistics.",
            "redistribution": "permitted",
            "derivatives": "permitted",
            "update_cadence": "annual, with a monthly oil series; refreshed by an analyst, never by the daily build",
        },
        "comparison_year": COMPARISON_YEAR,
        "comparison_year_reason": ("The latest year EIA publishes across production, consumption, gas, coal and "
                                   "electricity. Oil runs one year later and is shown only on a country's own page."),
        "balance_band": BALANCE_BAND,
        "metrics": {m: {"label": x[4], "unit": x[3], "source_series": f"INTL.{x[0]}", "source_unit_tag": x[1],
                        "definition": x[5]} for m, x in METRICS.items()},
        "world": {"values": world_values},
        "countries": sorted(countries, key=lambda c: c["name"]),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(countries)} countries; no {COMPARISON_YEAR} totals: {skipped}")


if __name__ == "__main__":
    main()
