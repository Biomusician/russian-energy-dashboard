"""Fetch grid and pipeline infrastructure from OpenStreetMap via Overpass.

OSM is used for exactly three things -- major substations, transmission lines and
pipelines -- because those are the classes it tags consistently across Russia and
Belarus. It is deliberately NOT used for refineries, LNG, gas processing or oil
terminals: probing (pipeline/osm_probe.py) found `industrial=oil_refinery` returns
zero features across the whole AOI, while the looser `industrial~refinery|oil`
selector returns 3,834 features that are overwhelmingly oilfield industrial zones
rather than refineries. Those classes come from curated sources instead.

Substation and line coverage is voltage-filtered. "Major" is taken as 220 kV and
above, which is the transmission/distribution boundary in the Russian grid; the
unfiltered selector returns 157,771 substations, essentially all of them local
distribution and analytically meaningless at region level.

OSM data is ODbL. Attribution is carried in docs/SOURCES.md and in the app footer.
"""

import json
import time

from pipeline.util import fetch, log

ENDPOINT = "https://overpass-api.de/api/interpreter"

# south, west, north, east -- Kaliningrad (19E) to the Yamal peninsula (88E),
# Caucasus (41N) to the Arctic coast (74N). Deliberately wider than the AOI; the
# point-in-region join discards anything outside it. Extended east to 120E and north
# to 78N in iteration 1 to cover the Siberian Federal District (Irkutsk Oblast reaches
# ~119E; the Taymyr peninsula in Krasnoyarsk Krai reaches ~78N). Probing showed the
# eastern strip adds only ~276 substations and ~126 lines, so the wider box is cheap.
BBOX = "41.0,19.0,78.0,120.0"

_V_220_PLUS = '"voltage"~"(^|;)(220000|330000|400000|500000|750000|1150000)(;|$)"'
_V_330_PLUS = '"voltage"~"(^|;)(330000|400000|500000|750000|1150000)(;|$)"'

# (layer key, overpass selector, output mode)
# "center" collapses ways/relations to a single point -- right for substations,
# which are areas we only ever plot as a marker.
# "geom" returns inline node coordinates -- needed for anything drawn as a line.
LAYERS = [
    ("substation", f'nwr["power"="substation"][{_V_220_PLUS}]', "center"),
    ("transmission_line", f'way["power"="line"][{_V_330_PLUS}]', "geom"),
    ("pipeline_gas", 'way["man_made"="pipeline"]["substance"="gas"]["name"]', "geom"),
    ("pipeline_oil", 'way["man_made"="pipeline"]["substance"~"oil|petroleum"]["name"]', "geom"),
]

# Overpass is a shared free service. One query at a time, with a pause between, and
# a 30-day cache so a rebuild does not re-ask for data that changes monthly at most.
PAUSE_SECONDS = 10
CACHE_HOURS = 24 * 30


def fetch_layer(key, selector, mode, max_age_hours=CACHE_HOURS):
    query = f"[out:json][timeout:900];({selector}({BBOX}););out {mode} qt;"
    log(f"osm: {key}")
    raw = fetch(
        ENDPOINT,
        f"osm_{key}.json",
        max_age_hours=max_age_hours,
        data=query,
        content_type="application/x-www-form-urlencoded",
    )
    payload = json.loads(raw.decode("utf-8"))
    elements = payload.get("elements", [])
    log(f"osm: {key} -> {len(elements)} elements ({len(raw) / 1e6:.1f} MB)")
    return elements


def fetch_all(max_age_hours=CACHE_HOURS):
    out = {}
    for i, (key, selector, mode) in enumerate(LAYERS):
        if i:
            time.sleep(PAUSE_SECONDS)
        out[key] = fetch_layer(key, selector, mode, max_age_hours)
    return out


if __name__ == "__main__":
    fetch_all()
