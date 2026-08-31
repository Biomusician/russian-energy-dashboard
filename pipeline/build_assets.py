"""Unify power plants, grid infrastructure and struck facilities into one asset layer.

Three sources, each used only where it is actually reliable:

  WRI Global Power Plant Database  -- generation. Carries capacity in MW, fuel type
      and a per-plant source URL, which OSM's power=plant does not.
  OpenStreetMap (Overpass)         -- substations, transmission lines, pipelines.
  Wikipedia strike tables          -- refineries, terminals and pumping stations.

Facilities from the Wikipedia tables have no coordinates and none are looked up.
The brief stops the MVP at administrative-region level, and geocoding a struck
refinery would add locational precision the analysis does not need. They are carried
as region-scoped assets with no point geometry.

Assets are never merged across sources. A refinery named in the strike tables and an
industrial polygon in OSM stay separate records rather than being auto-matched on a
fuzzy name, because a wrong merge silently reassigns capacity and damage.
"""

import collections
import csv

from pipeline import geo
from pipeline.build_regions import build as build_regions
from pipeline.config import PROCESSED, RAW
from pipeline.fetch_osm import fetch_all as fetch_osm
from pipeline.util import log, write_json

WRI_URL = (
    "https://raw.githubusercontent.com/wri/global-power-plant-database/master/"
    "output_database/global_power_plant_database.csv"
)

# WRI primary_fuel -> our asset class. Fuel detail is preserved separately; the class
# is about what kind of thing it is, not what it burns.
FUEL_CLASS = {
    "Nuclear": "power_plant_nuclear",
    "Hydro": "power_plant_hydro",
    "Coal": "power_plant_thermal",
    "Gas": "power_plant_thermal",
    "Oil": "power_plant_thermal",
    "Petcoke": "power_plant_thermal",
    "Biomass": "power_plant_thermal",
    "Waste": "power_plant_thermal",
    "Cogeneration": "power_plant_thermal",
}

# Lines are decoration at region zoom; simplify hard. ~2 km.
LINE_TOLERANCE = 0.02
MIN_LINE_POINTS = 2


def load_wri():
    from pipeline.util import fetch

    fetch(WRI_URL, "wri_gppd.csv", max_age_hours=24 * 30)
    with open(RAW / "wri_gppd.csv", encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if r["country"] in ("RUS", "BLR")]


def build_power_plants(index):
    assets = []
    unplaced = 0
    for row in load_wri():
        try:
            lon, lat = float(row["longitude"]), float(row["latitude"])
        except (TypeError, ValueError):
            continue
        region = index.find(lon, lat)
        if region is None:
            unplaced += 1
            continue
        fuel = row.get("primary_fuel") or None
        try:
            capacity = float(row["capacity_mw"]) if row.get("capacity_mw") else None
        except ValueError:
            capacity = None
        assets.append(
            {
                "asset_id": "wri-" + row["gppd_idnr"],
                "name": row["name"],
                "asset_class": FUEL_CLASS.get(fuel, "power_plant_other"),
                "fuel": fuel,
                "region_code": region,
                "capacity_mw": capacity,
                "commissioning_year": _int(row.get("commissioning_year")),
                "owner": row.get("owner") or None,
                "lon": round(lon, 4),
                "lat": round(lat, 4),
                "scope": "analytic",
                "source": "WRI Global Power Plant Database v1.3",
                "source_url": row.get("url") or None,
            }
        )
    log(f"assets: {len(assets)} power plants in AOI ({unplaced} outside AOI, dropped)")
    return assets


def build_osm_points(index, elements):
    assets = []
    outside = 0
    for el in elements:
        lon, lat = _coords(el)
        if lon is None:
            continue
        region = index.find(lon, lat)
        if region is None:
            outside += 1
            continue
        tags = el.get("tags", {})
        assets.append(
            {
                "asset_id": f"osm-{el['type']}-{el['id']}",
                "name": tags.get("name") or tags.get("name:en") or None,
                "asset_class": "substation",
                "region_code": region,
                "voltage_kv": _max_voltage(tags.get("voltage")),
                "operator": tags.get("operator") or None,
                "lon": round(lon, 4),
                "lat": round(lat, 4),
                "scope": "analytic",
                "source": "OpenStreetMap (ODbL)",
                "source_url": f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
            }
        )
    log(f"assets: {len(assets)} substations in AOI ({outside} outside, dropped)")
    return assets


def build_osm_lines(index, elements, asset_class):
    """Line features, assigned to the region containing their midpoint.

    A 500 kV line can cross four oblasts; the midpoint is a deliberate
    simplification, recorded in docs/METHODOLOGY.md. Lines are counted, never used as
    a capacity input to the index, so a misassigned line cannot move a score.
    """
    features = []
    counts = collections.Counter()
    for el in elements:
        pts = [(p["lon"], p["lat"]) for p in el.get("geometry") or [] if p]
        if len(pts) < 2:
            continue
        mid = pts[len(pts) // 2]
        region = index.find(*mid)
        if region is None:
            continue
        simple = _simplify_line(pts, LINE_TOLERANCE)
        if len(simple) < MIN_LINE_POINTS:
            continue
        tags = el.get("tags", {})
        counts[region] += 1
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "asset_class": asset_class,
                    "scope": "analytic",
                    "osm_id": el.get("id"),
                    "region_code": region,
                    "name": tags.get("name") or tags.get("name:en") or None,
                    "voltage_kv": _max_voltage(tags.get("voltage")),
                    "operator": tags.get("operator") or None,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[round(x, 3), round(y, 3)] for x, y in simple],
                },
            }
        )
    log(f"assets: {len(features)} {asset_class} lines in AOI")
    return features, counts


def _simplify_line(points, tolerance):
    """Douglas-Peucker on an open line. Delegates to geo.simplify_line so every simplifier in the
    project shares one (correct, point-to-SEGMENT) metric — this copy previously carried the
    infinite-line bug fixed in iteration 9's pipeline builder."""
    return geo.simplify_line(points, tolerance)


def _coords(el):
    if "center" in el:
        return el["center"]["lon"], el["center"]["lat"]
    if "lon" in el and "lat" in el:
        return el["lon"], el["lat"]
    return None, None


def _max_voltage(raw):
    """OSM voltage is sometimes a semicolon list; take the highest, in kV."""
    if not raw:
        return None
    best = None
    for part in str(raw).split(";"):
        try:
            v = int(part.strip())
        except ValueError:
            continue
        best = v if best is None else max(best, v)
    return round(best / 1000) if best else None


def _int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def build():
    index, region_meta = build_regions()

    plants = build_power_plants(index)
    osm = fetch_osm()
    substations = build_osm_points(index, osm["substation"])

    line_features = []
    line_counts = collections.Counter()
    for key, cls in (
        ("transmission_line", "transmission_line"),
        ("pipeline_gas", "pipeline_gas"),
        ("pipeline_oil", "pipeline_oil"),
    ):
        feats, counts = build_osm_lines(index, osm[key], cls)
        line_features.extend(feats)
        line_counts.update(counts)

    point_assets = plants + substations

    # assets.json is written by run.py AFTER the curated supplement is merged in, so the
    # emitted file and the facet counts see the same asset list.
    write_json(
        PROCESSED / "assets_lines.geojson",
        {"type": "FeatureCollection", "features": line_features},
    )

    size = (PROCESSED / "assets_lines.geojson").stat().st_size / 1e6
    log(f"assets: line layer {size:.2f} MB")

    return point_assets, line_features, region_meta


if __name__ == "__main__":
    build()
