"""One-off: count OSM features per candidate tag over the AOI bbox.

Kept in the repo because the tag choices in build_assets.py are otherwise
unexplained magic. Re-run it if a layer looks thin and you suspect the tagging
convention has moved. Not part of the build.
"""

import sys
import time
import urllib.error
import urllib.request

# south, west, north, east -- covers Kaliningrad (19E) to the Yamal peninsula (88E).
BBOX = "41.0,19.0,74.0,88.0"
ENDPOINT = "https://overpass-api.de/api/interpreter"

CANDIDATES = [
    ("power_plant",          'nwr["power"="plant"]'),
    ("power_substation_all", 'nwr["power"="substation"]'),
    ("power_line",           'way["power"="line"]'),
    ("refinery_industrial",  'nwr["industrial"="oil_refinery"]'),
    ("refinery_manmade",     'nwr["man_made"="works"]["product"~"oil|petroleum|fuel"]'),
    ("refinery_landuse",     'nwr["landuse"="industrial"]["industrial"~"refinery|oil"]'),
    ("refinery_name_ru",     'nwr["man_made"="works"]["name"~"НПЗ|нефтеперераб"]'),
    ("pipeline_gas",         'way["man_made"="pipeline"]["substance"="gas"]'),
    ("pipeline_oil",         'way["man_made"="pipeline"]["substance"~"oil|petroleum"]'),
    ("storage_tank_oil",     'nwr["man_made"="storage_tank"]["content"~"oil|fuel|petroleum"]'),
    ("lng",                  'nwr["industrial"="lng"]'),
    ("gas_processing",       'nwr["industrial"~"gas|well_cluster"]'),
    ("coal_mine",            'nwr["man_made"="mineshaft"]["resource"="coal"]'),
    ("coal_landuse",         'nwr["landuse"="quarry"]["resource"="coal"]'),
]


def count(selector):
    query = f"[out:json][timeout:300];({selector}({BBOX}););out count;"
    req = urllib.request.Request(
        ENDPOINT,
        data=query.encode("utf-8"),
        headers={"User-Agent": "russian-energy-dashboard/0.1 probe"},
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=360) as resp:
                body = resp.read().decode("utf-8")
            import json

            return json.loads(body)["elements"][0]["tags"]["total"]
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError) as exc:
            if attempt == 3:
                return f"FAILED ({type(exc).__name__})"
            time.sleep(20 * (attempt + 1))


if __name__ == "__main__":
    only = sys.argv[1:] or None
    for label, selector in CANDIDATES:
        if only and label not in only:
            continue
        print(f"{label:24} {count(selector)}", flush=True)
        time.sleep(8)
