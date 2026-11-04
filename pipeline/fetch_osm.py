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


def provenance(raw_dir):
    """What OSM data this build drew its geometry from (iteration 16).

    OSM feeds substations, transmission lines and pipeline routes: map context, and the
    transmission CONTEXT counts. None of it enters a scored number (docs/HISTORICAL_REPRODUCIBILITY.md
    §4), so OSM is deliberately not pinned like the Wikipedia inputs. This records enough to say
    which OSM state a published map showed: Overpass's own data timestamp, a content hash and the
    query identity. It does not make old maps rebuildable; Overpass serves only current data."""
    import hashlib
    import re
    from pipeline import fetch_osm_pipelines as P
    queries = {f"osm_{k}.json": f"[out:json][timeout:900];({sel}({BBOX}););out {mode} qt;"
               for k, sel, mode in LAYERS}
    queries["osm_pipeline_relations.json"] = P.RELATIONS_QUERY
    queries["osm_pipeline_relation_member_tags.json"] = P.MEMBER_TAGS_QUERY
    out = []
    for path in sorted(raw_dir.glob("osm_*.json")):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            head = fh.read(1024)
            h.update(head)
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        m = re.search(rb'"timestamp_osm_base"\s*:\s*"([^"]+)"', head)
        q = queries.get(path.name)
        entry = {
            "file": path.name,
            "osm_data_timestamp": m.group(1).decode("ascii") if m else None,
            "sha256": h.hexdigest()[:16],
            "bytes": path.stat().st_size,
            "query_sha256": hashlib.sha256(q.encode("utf-8")).hexdigest()[:16] if q else None,
        }
        if path.name == "osm_pipeline_relations.json":
            # Which route relations the pipeline network was assembled from: a count and a hash
            # of the sorted ids, so two builds can be told apart without listing every id.
            ids = sorted(e["id"] for e in json.loads(path.read_text(encoding="utf-8")).get("elements", [])
                         if e.get("type") == "relation")
            entry["relation_count"] = len(ids)
            entry["relation_ids_sha256"] = hashlib.sha256(
                ",".join(map(str, ids)).encode("ascii")).hexdigest()[:16]
        out.append(entry)
    return {"endpoint": ENDPOINT, "scored": False, "files": out}
