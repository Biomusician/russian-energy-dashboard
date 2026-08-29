"""Continental oil & gas pipeline CONTEXT network (iteration 5, §3-§8).

This is a SEPARATE ingestion path from the analytic OSM feed (pipeline/fetch_osm.py). The
analytic feed joins pipelines to AOI regions and feeds the transmission context counts; this
one deliberately does the opposite -- it collects the major trunk oil and gas transmission
lines across Eurasia purely as geographic/network CONTEXT, so the map can show where Russia's
export system connects into Europe without any of it entering the degradation model.

Everything here carries scope="context". It is never joined to an AOI region, never scored,
never counted as an incident. Regression tests enforce that (tests/test_pipeline.py).

Source: OpenStreetMap via Overpass (ODbL). Global Energy Monitor's GGIT/GOIT are the
authoritative trackers for this layer, but their bulk data is delivered behind a per-request
download form with no stable CI-fetchable URL (verified iteration 5), so per the iteration
brief the automatable OSM path is the feed and GEM is the cited cross-reference in
docs/SOURCES.md. Route geometry from OSM is traced ("mapped"); OSM carries no route-accuracy
field, so every feature is route_quality="osm_mapped". The frontend keeps a dashed treatment
for route_quality="approximate" so a future GEM snapshot can populate that distinction (§5)
without a code change.

Only MAJOR TRUNKS are kept -- named, usage=transmission, and at least MIN_TRUNK_KM long --
because rendering every local transmission connector across a continent is spaghetti, not
context (§29). Geometry is simplified hard; the files are lazy-loaded by the frontend so the
analytic dashboard's first paint is unaffected (§16).
"""

import json
import math
import time

from pipeline import geo
from pipeline.config import PROCESSED
from pipeline.util import fetch, log

ENDPOINT = "https://overpass-api.de/api/interpreter"

# Overpass bbox order is south,west,north,east. Tiled so no single query is huge: western
# and eastern Europe, the Black Sea / Caucasus / Türkiye corridor, and the Russian Far East
# beyond the Siberian analytic boundary. Together with the analytic feed's 19-120E box these
# span the Russia-Europe export system end to end.
BANDS = {
    "europe_w": "34.0,-10.0,72.0,12.0",
    "europe_e": "34.0,12.0,72.0,32.0",
    "south":    "34.0,25.0,48.0,56.0",
    "far_east": "42.0,120.0,78.0,160.0",
}

SUBSTANCE = '"substance"~"gas|natural_gas|cng|oil|petroleum|crude",i'
MIN_TRUNK_KM = 50.0        # a trunk line; drops the local transmission mesh
TOLERANCE = 0.04           # ~4 km Douglas-Peucker; context geometry is scenery
PAUSE_SECONDS = 10
CACHE_HOURS = 24 * 30      # pipelines change monthly at most; be gentle on Overpass


def _fetch_band(name, bbox, max_age_hours):
    query = (f'[out:json][timeout:600];'
             f'(way["man_made"="pipeline"]["usage"="transmission"]["name"][{SUBSTANCE}]({bbox}););'
             f'out geom qt;')
    log(f"context-network: {name}")
    raw = fetch(ENDPOINT, f"ctxnet_{name}.json", max_age_hours=max_age_hours,
                data=query, content_type="application/x-www-form-urlencoded")
    els = json.loads(raw.decode("utf-8")).get("elements", [])
    log(f"context-network: {name} -> {len(els)} ways ({len(raw) / 1e6:.1f} MB)")
    return els


def _length_km(pts):
    total = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        # equirectangular approximation, fine for a length threshold
        mlat = math.radians((y1 + y2) / 2)
        dx = math.radians(x2 - x1) * math.cos(mlat)
        dy = math.radians(y2 - y1)
        total += 6371.0 * math.hypot(dx, dy)
    return total


def _substance_class(tags):
    s = (tags.get("substance") or "").lower()
    if any(t in s for t in ("oil", "petroleum", "crude")):
        return "pipeline_oil"
    return "pipeline_gas"


def build(analytic_osm_ids=None, max_age_hours=CACHE_HOURS):
    """Fetch, filter to trunks, de-duplicate against the analytic feed by OSM id, and emit
    context_oil_network.geojson + context_gas_network.geojson. Returns {class: count}."""
    analytic_osm_ids = set(analytic_osm_ids or ())
    seen_ids = set()
    gas, oil = [], []

    for i, (name, bbox) in enumerate(BANDS.items()):
        if i:
            time.sleep(PAUSE_SECONDS)
        for el in _fetch_band(name, bbox, max_age_hours):
            oid = el.get("id")
            # A trunk crossing a tile boundary appears in two bands; and a line already in
            # the analytic feed must not be redrawn as context (§6 -- one corridor, one line).
            if oid in seen_ids or oid in analytic_osm_ids:
                continue
            pts = [(p["lon"], p["lat"]) for p in el.get("geometry") or [] if p]
            if len(pts) < 2 or _length_km(pts) < MIN_TRUNK_KM:
                continue
            seen_ids.add(oid)
            simple = geo.round_coords(
                {"type": "LineString", "coordinates": _simplify(pts, TOLERANCE)}, 3)
            tags = el.get("tags", {})
            cls = _substance_class(tags)
            feat = {
                "type": "Feature",
                "properties": {
                    "asset_class": cls,
                    "scope": "context",
                    "route_quality": "osm_mapped",
                    "osm_id": oid,
                    "name": tags.get("name") or tags.get("name:en"),
                    "operator": tags.get("operator") or None,
                },
                "geometry": simple,
            }
            (oil if cls == "pipeline_oil" else gas).append(feat)

    from pipeline.util import write_json
    write_json(PROCESSED / "context_gas_network.geojson",
               {"type": "FeatureCollection", "features": gas})
    write_json(PROCESSED / "context_oil_network.geojson",
               {"type": "FeatureCollection", "features": oil})
    total_mb = sum((PROCESSED / f).stat().st_size for f in
                   ("context_gas_network.geojson", "context_oil_network.geojson")) / 1e6
    log(f"context-network: {len(gas)} gas + {len(oil)} oil trunk routes (context), {total_mb:.2f} MB")
    return {"pipeline_gas": len(gas), "pipeline_oil": len(oil)}


def _simplify(pts, tolerance):
    """Douglas-Peucker for an open polyline (never closes it)."""
    if len(pts) <= 2:
        return [[round(x, 3), round(y, 3)] for x, y in pts]
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        md, idx = -1.0, first
        for i in range(first + 1, last):
            d = geo._perpendicular_distance(pts[i], pts[first], pts[last])
            if d > md:
                md, idx = d, i
        if md > tolerance:
            keep[idx] = True
            stack.append((first, idx))
            stack.append((idx, last))
    return [[x, y] for (x, y), k in zip(pts, keep) if k]


if __name__ == "__main__":
    build()
