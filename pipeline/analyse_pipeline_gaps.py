"""Classify the gaps in fragmented pipeline routes (iteration 10 §10/§11).

    python -m pipeline.analyse_pipeline_gaps            # summary
    python -m pipeline.analyse_pipeline_gaps --ledger   # + write the ledger CSV

A route drawn as several disconnected components has a gap between each pair. The question this
answers is not "how do we close them" — it is "what KIND of gap is each one", because the honest
disposition differs completely:

  a 60 m gap between two ways is almost certainly an OSM topology artefact;
  a 400 km gap across the Baltic is a genuinely unmapped subsea section;
  a gap that lands on an international border is where one country's mapping simply stops.

WHAT THIS DOES NOT DO: it does not close anything. Nothing here writes geometry, and the
classification never becomes a licence to interpolate. `UNRESOLVED GAP > INVENTED LINE`. The
output is a ledger a human reads, and the counts that make the network's incompleteness visible.

Gap length is measured endpoint-to-nearest-endpoint between components of the SAME route, which
is a lower bound on the missing pipe: real pipe does not run in straight lines.
"""

import argparse
import collections
import csv
import json
import math
from pathlib import Path

from pipeline.util import log

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
LEDGER = ROOT / "data" / "review" / "pipeline_gap_ledger.csv"

# Bands chosen from what each size can plausibly BE, not from round numbers.
#   noise      - below OSM's own vertex spacing; a shared node that is not quite shared.
#   artefact   - a missing way or two; the corridor is mapped either side.
#   section    - a real unmapped run. Too long to be a topology slip.
#   major      - a whole limb absent: subsea crossings, or mapping that stops at a frontier.
BANDS = ((0.5, "noise"), (5.0, "artefact"), (50.0, "section"), (float("inf"), "major"))

EARTH_KM = 6371.0088


def haversine(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_KM * math.asin(math.sqrt(h))


def band(km):
    for limit, name in BANDS:
        if km < limit:
            return name
    return "major"


def load_components(path):
    """route key -> [(component_index, coords)]"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    routes = collections.defaultdict(list)
    meta = {}
    for f in data["features"]:
        p = f["properties"]
        key = p["pipeline_id"]
        routes[key].append((p.get("component_index", 0), f["geometry"]["coordinates"]))
        meta.setdefault(key, {
            "canonical_pipeline_id": p.get("canonical_pipeline_id"),
            "name": p.get("canonical_name") or p.get("name"),
            "commodity": "gas" if p["asset_class"] == "pipeline_gas" else "oil",
            "route_quality": p.get("route_quality"),
            "geometry_source": p.get("geometry_source"),
            "route_length_km": p.get("route_length_km"),
            "analytic_overlap": p.get("analytic_overlap"),
        })
    return routes, meta


def gaps_for_route(components):
    """Nearest-endpoint distance from each component to any other, as an undirected chain.

    Greedy nearest-neighbour rather than an exact tour: with up to 125 components the exact
    problem is a TSP, and the ledger only needs each component's closest neighbour to
    characterise the gap. Reported as a LOWER BOUND, and labelled as one.
    """
    ends = [(i, c[0], c[-1]) for i, c in components if len(c) >= 2]
    out = []
    for idx, (i, a_start, a_end) in enumerate(ends):
        best = None
        for jdx, (j, b_start, b_end) in enumerate(ends):
            if idx == jdx:
                continue
            for pa in (a_start, a_end):
                for pb in (b_start, b_end):
                    d = haversine(pa, pb)
                    if best is None or d < best[0]:
                        best = (d, j, pa)
        if best:
            out.append({"component": i, "nearest_component": best[1],
                        "gap_km": round(best[0], 3), "at_lon": round(best[2][0], 4),
                        "at_lat": round(best[2][1], 4)})
    return out


def analyse():
    rows, summary = [], collections.Counter()
    per_route = []
    for fname in ("context_gas_network.geojson", "context_oil_network.geojson"):
        routes, meta = load_components(PROCESSED / fname)
        for key, comps in routes.items():
            if len(comps) < 2:
                continue
            gs = gaps_for_route(comps)
            if not gs:
                continue
            m = meta[key]
            worst = max(g["gap_km"] for g in gs)
            median = sorted(g["gap_km"] for g in gs)[len(gs) // 2]
            per_route.append({
                "pipeline_id": key,
                "canonical_pipeline_id": m["canonical_pipeline_id"],
                "name": m["name"],
                "commodity": m["commodity"],
                "components": len(comps),
                "route_length_km": m["route_length_km"],
                "gap_count": len(gs),
                "median_gap_km": median,
                "max_gap_km": round(worst, 3),
                "worst_band": band(worst),
                "dominant_band": collections.Counter(band(g["gap_km"]) for g in gs).most_common(1)[0][0],
                "geometry_source": m["geometry_source"],
                "analytic_overlap": m["analytic_overlap"],
            })
            for g in gs:
                summary[band(g["gap_km"])] += 1
                rows.append({"pipeline_id": key, "name": m["name"],
                             "commodity": m["commodity"], **g, "band": band(g["gap_km"])})
    return rows, per_route, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", action="store_true", help="write the per-route ledger CSV")
    args = ap.parse_args(argv)

    rows, per_route, summary = analyse()
    total = sum(summary.values())
    log(f"pipeline-gaps: {len(per_route)} fragmented routes, {total} component adjacencies")
    for _, name in BANDS:
        n = summary.get(name, 0)
        if n:
            log(f"  {name:10s} {n:5d}  ({n / total * 100:4.1f}%)")
    log("")
    log("  worst routes by maximum gap:")
    for r in sorted(per_route, key=lambda r: -r["max_gap_km"])[:12]:
        log(f"    {r['max_gap_km']:9,.1f} km  {r['components']:4d} comp  "
            f"{(r['name'] or '?')[:44]:46s} {r['worst_band']}")
    analytic = [r for r in per_route if r["analytic_overlap"]]
    log("")
    log(f"  fragmented routes overlapping the ANALYTIC layer: {len(analytic)}")
    if args.ledger:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(per_route[0]))
            w.writeheader()
            w.writerows(sorted(per_route, key=lambda r: -r["max_gap_km"]))
        log(f"  wrote {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
