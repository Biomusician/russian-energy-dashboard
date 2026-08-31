"""Relation-aware OSM pipeline extraction (iteration 9).

WHY THIS EXISTS. The previous extraction asked Overpass for pipeline *ways* only, required a
`name` on each way, and then discarded any way under 50 km. A trunk line is not one OSM way — it
is a chain of ways split wherever a tag changes (diameter, operator, a bridge, a border), and its
identity usually lives on a `type=route` + `route=pipeline` RELATION rather than on the pieces.
Judging each piece by its own length therefore threw away most of the network:
docs/PIPELINE_GAP_AUDIT.md measures 97.7% of relation-member ways (161,899 km) missing from the
shipped output, including Сияние Севера and СРТО — Торжок in their entirety.

WHAT THIS DOES. Fetches the route RELATIONS with their member geometry, plus the member ways'
tags (needed because 255 of 478 relations carry no `substance` of their own). Assembly, length
thresholding and simplification all happen afterwards, on the ASSEMBLED ROUTE — see
pipeline/build_pipeline_network.py.

WHY NOT A PBF EXTRACT. A Geofabrik/pyosmium path was evaluated (§3 of the iteration brief). The
whole relation corpus for the Europe–Far East corridor is 21.7 MB and fetches in ~30 s, versus a
multi-GB download, a compiled parser dependency and minutes of CI time for the same relations.
Overpass wins on every axis here; the decision is recorded in docs/ITERATION_9_REVIEW.md.

Source: OpenStreetMap contributors, ODbL. Attribution in docs/SOURCES.md and the app footer.
"""

import json
import time

from pipeline.util import fetch, log

ENDPOINT = "https://overpass-api.de/api/interpreter"

# south, west, north, east. Deliberately continental: the Russia–Europe export system plus the
# eastern systems (Power of Siberia, ESPO, Sakhalin). Unlike the old banded context query this
# has no interior hole — the previous bands left 56°E–120°E unqueried, which is precisely where
# the West Siberian trunk corridors are.
CORRIDOR = "25.0,-12.0,82.0,180.0"

PAUSE_SECONDS = 10
CACHE_HOURS = 24 * 30      # pipeline topology changes monthly at most; be gentle on Overpass


def fetch_relations(max_age_hours=CACHE_HOURS):
    """Pipeline route relations WITH member geometry."""
    query = (f'[out:json][timeout:900];'
             f'(relation["type"="route"]["route"="pipeline"]({CORRIDOR}););'
             f'out geom;')
    log("osm-pipelines: route relations (with member geometry)")
    raw = fetch(ENDPOINT, "osm_pipeline_relations.json", max_age_hours=max_age_hours,
                data=query, content_type="application/x-www-form-urlencoded")
    els = json.loads(raw.decode("utf-8")).get("elements", [])
    members = sum(len(e.get("members") or []) for e in els)
    log(f"osm-pipelines: {len(els)} relations, {members} members ({len(raw) / 1e6:.1f} MB)")
    return els


def fetch_member_tags(max_age_hours=CACHE_HOURS):
    """Tags (no geometry) for every way belonging to those relations.

    Needed because substance is frequently tagged on the members rather than the relation: of 478
    relations only 174 carry a usable `substance` themselves. Returns {way_id: tags}.
    """
    query = (f'[out:json][timeout:900];'
             f'relation["type"="route"]["route"="pipeline"]({CORRIDOR})->.r;'
             f'way(r.r);out tags;')
    log("osm-pipelines: relation member way tags")
    raw = fetch(ENDPOINT, "osm_pipeline_relation_member_tags.json", max_age_hours=max_age_hours,
                data=query, content_type="application/x-www-form-urlencoded")
    els = json.loads(raw.decode("utf-8")).get("elements", [])
    log(f"osm-pipelines: {len(els)} member way tag records ({len(raw) / 1e6:.1f} MB)")
    return {e["id"]: e.get("tags", {}) for e in els}


def fetch_all(max_age_hours=CACHE_HOURS):
    rels = fetch_relations(max_age_hours)
    time.sleep(PAUSE_SECONDS)
    tags = fetch_member_tags(max_age_hours)
    return {"relations": rels, "member_tags": tags}


if __name__ == "__main__":
    fetch_all()
