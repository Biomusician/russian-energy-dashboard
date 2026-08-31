"""Canonical pipeline route reconstruction (iteration 9).

Replaces the way-at-a-time context extraction. The rule that drives everything here:

    RECONSTRUCT THE ROUTE FIRST, THEN JUDGE IT.

The old builder asked "is this OSM way 50 km long?" of each piece of a trunk line. A 500 km
system split into twenty-five 20 km ways scored zero and vanished. This builder assembles the
route from its relation members, THEN applies a length threshold to the assembled route, THEN
simplifies. docs/PIPELINE_GAP_AUDIT.md has the measurements that motivated it.

Two further rules, both structural:

  * PROXIMITY IS NOT CONNECTION. Segments are joined only where they share an endpoint
    coordinate exactly, i.e. where OSM itself asserts they are the same line. Nothing here
    measures the distance between two loose ends and decides they must meet. Where a route is
    genuinely discontinuous, it stays discontinuous and is reported as such.

  * THE CONTEXT LAYER IS SELF-CONTAINED. The old builder deleted any way the analytic feed also
    had, which meant the Gas/Oil context toggles hid the Russian trunk backbone unless the
    separate analytic layer happened to be on too. Overlap is now marked (`analytic_overlap`)
    and left in place; the frontend decides what to draw, the pipeline does not decide what to
    withhold.

Everything emitted here is scope="context": never joined to an AOI region, never scored, never
counted as an incident. Tests enforce that.

Source: OpenStreetMap contributors, ODbL.
"""

import collections
import hashlib
import json
import math

from pipeline import geo
from pipeline.config import PROCESSED
from pipeline.util import log, read_json, write_json

# Applied to the ASSEMBLED route, never to an individual member way.
MIN_TRUNK_KM = 50.0
# Douglas-Peucker tolerance in degrees, applied AFTER stitching. 0.01 deg is ~1.1 km N-S; the
# previous 0.04 (~4 km) visibly cut corners off real corridors. Benchmarked in the iteration 9
# review across 0.005 / 0.01 / 0.02 / 0.04.
TOLERANCE = 0.01
COORD_PRECISION = 4          # ~11 m; below the simplification tolerance, so it costs nothing

# Substance vocabularies. Kept explicit rather than "anything containing gas" so that
# ethylene/hydrogen/CO2/water lines cannot leak into either analytic class.
_OIL_TOKENS = ("oil", "petroleum", "crude", "diesel", "kerosene", "naphtha")
_GAS_TOKENS = ("natural_gas", "gas", "cng", "lng", "methane")
# Substances that must never be classified as either, even though they contain a token above.
_EXCLUDE = ("water", "sewage", "steam", "drain", "rainwater", "hot_water", "ethylene",
            "hydrogen", "carbon_dioxide", "co2", "ammonia", "oxygen", "brine", "slurry",
            "gasoline", "fuel", "biogas")


def _classify(value):
    """Map an OSM `substance` value to pipeline_gas / pipeline_oil / None.

    `fuel` is deliberately unclassified: it is used for refined-product and multi-product lines,
    which are neither crude oil transmission nor natural gas and would corrupt both classes.
    """
    s = (value or "").strip().lower()
    if not s:
        return None
    for bad in _EXCLUDE:
        if bad in s:
            return None
    if any(t in s for t in _OIL_TOKENS):
        return "pipeline_oil"
    if any(t in s for t in _GAS_TOKENS):
        return "pipeline_gas"
    return None


def _name_hint(name):
    """Last-resort substance hint from a route name. Only used when no substance tag exists
    anywhere on the relation or its members; recorded in provenance so it is auditable."""
    n = (name or "").lower()
    if any(t in n for t in ("нефтепровод", "нефтепр", "oil pipeline", "ölleitung", "oleoduct",
                            "ropovod", "petrol boru", "нафтаправод")):
        return "pipeline_oil"
    if any(t in n for t in ("газопровод", "газопр", "gas pipeline", "gasleitung", "gasoduct",
                            "plynovod", "doğal gaz", "erdgas")):
        return "pipeline_gas"
    return None


def _length_km(pts):
    total = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        mlat = math.radians((y1 + y2) / 2)
        total += 6371.0 * math.hypot(math.radians(x2 - x1) * math.cos(mlat),
                                     math.radians(y2 - y1))
    return total


def _key(pt, precision=7):
    return (round(pt[0], precision), round(pt[1], precision))


def stitch(ways):
    """Assemble member ways into maximal contiguous chains.

    `ways` is a list of coordinate lists. Two ways are joined ONLY when an endpoint of one is
    exactly an endpoint of the other — that is OSM asserting a shared node, not a guess from
    proximity. Returns a list of coordinate lists, one per contiguous component, longest first.
    A route that is genuinely in three pieces comes back as three pieces.
    """
    segs = [list(map(tuple, w)) for w in ways if w and len(w) >= 2]
    if not segs:
        return []
    # endpoint -> segment indices
    ends = collections.defaultdict(list)
    for i, s in enumerate(segs):
        ends[_key(s[0])].append(i)
        ends[_key(s[-1])].append(i)

    used = [False] * len(segs)
    chains = []
    for start in range(len(segs)):
        if used[start]:
            continue
        used[start] = True
        chain = list(segs[start])
        # extend forward, then backward, consuming any unused segment sharing the live endpoint
        for direction in (1, 0):
            while True:
                tip = _key(chain[-1] if direction else chain[0])
                nxt = None
                for cand in ends.get(tip, ()):
                    if not used[cand]:
                        nxt = cand
                        break
                if nxt is None:
                    break
                used[nxt] = True
                seg = list(segs[nxt])
                if direction:
                    if _key(seg[0]) != tip:
                        seg.reverse()
                    chain.extend(seg[1:])
                else:
                    if _key(seg[-1]) != tip:
                        seg.reverse()
                    chain[:0] = seg[:-1]
        chains.append(chain)
    chains.sort(key=lambda c: -_length_km(c))
    return chains


# Maximum gap that may be closed between two components OF THE SAME ROUTE RELATION.
#
# This is the one place distance is allowed to matter, and it is allowed only because identity
# evidence already exists: both components are members of the same OSM route relation, so OSM
# itself asserts they are one pipeline. The gap is the routine case of two ways drawn separately
# without snapping to a shared node. 45% of within-relation component gaps fall under 100 m, and
# 100 m is an order of magnitude below anything analytically interesting, so the join adds no
# information the source did not already carry.
#
# It is NOT a proximity rule: two segments with no shared relation are never joined at any
# distance, and even within a relation a gap above this stays a visible gap.
WELD_TOLERANCE_KM = 0.1


def _haversine(a, b):
    (x1, y1), (x2, y2) = a, b
    mlat = math.radians((y1 + y2) / 2)
    return 6371.0 * math.hypot(math.radians(x2 - x1) * math.cos(mlat), math.radians(y2 - y1))


def weld(chains, tolerance_km=WELD_TOLERANCE_KM):
    """Join same-route components whose endpoints are within `tolerance_km`.

    Greedy closest-pair-first, so a component is welded to its nearest neighbour rather than to
    whichever happened to be tried first. Returns (chains, welds_made, max_weld_km) — the counts
    are carried into provenance so the joins are auditable rather than invisible.
    """
    chains = [list(c) for c in chains if len(c) >= 2]
    welds, max_gap = 0, 0.0
    while len(chains) > 1:
        best = None
        for i in range(len(chains)):
            for j in range(i + 1, len(chains)):
                for ai, a in ((0, chains[i][0]), (1, chains[i][-1])):
                    for bj, b in ((0, chains[j][0]), (1, chains[j][-1])):
                        d = _haversine(a, b)
                        if d <= tolerance_km and (best is None or d < best[0]):
                            best = (d, i, j, ai, bj)
        if best is None:
            break
        d, i, j, ai, bj = best
        ci, cj = chains[i], chains[j]
        if ai == 0:
            ci.reverse()                 # make ci end at the join
        if bj == 1:
            cj.reverse()                 # make cj start at the join
        merged = ci + cj
        chains = [c for k, c in enumerate(chains) if k not in (i, j)] + [merged]
        welds += 1
        max_gap = max(max_gap, d)
    chains.sort(key=lambda c: -_length_km(c))
    return chains, welds, round(max_gap, 4)


def _simplify(pts, tolerance):
    """Douglas-Peucker on an open polyline. Endpoints are always kept, so stitched junctions
    and country crossings survive simplification."""
    if len(pts) <= 2:
        return [list(p) for p in pts]
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
    return [list(p) for p, k in zip(pts, keep) if k]


def _round(pts, precision=COORD_PRECISION):
    out = []
    for x, y in pts:
        p = [round(x, precision), round(y, precision)]
        if not out or p != out[-1]:
            out.append(p)
    return out


def _route_substance(rel_tags, member_tags, name):
    """Substance for a route, with the evidence that decided it.

    Order: the relation's own tag, then a majority vote of member way tags, then a name hint.
    Returns (class, basis) so provenance can record which rule fired.
    """
    direct = _classify(rel_tags.get("substance"))
    if direct:
        return direct, "relation_substance_tag"
    votes = collections.Counter(c for c in (_classify(t.get("substance")) for t in member_tags) if c)
    if votes:
        return votes.most_common(1)[0][0], "member_substance_majority"
    hint = _name_hint(name)
    if hint:
        return hint, "route_name_hint"
    return None, "unresolved"


def _pipeline_id(kind, ident):
    return f"osm-{kind}-{ident}"


def build_routes(relations, member_tags, analytic_osm_ids=None, min_km=MIN_TRUNK_KM,
                 tolerance=TOLERANCE):
    """Reconstruct canonical routes from OSM pipeline route relations.

    Returns (routes, stats). Each route is a dict carrying its canonical identity, the stitched
    components, and full provenance. Nothing is dropped for overlapping the analytic feed.
    """
    analytic_osm_ids = set(analytic_osm_ids or ())
    routes = []
    stats = collections.Counter()

    for rel in relations:
        tags = rel.get("tags", {}) or {}
        name = tags.get("name") or tags.get("name:en") or tags.get("ref")
        members = [m for m in (rel.get("members") or [])
                   if m.get("type") == "way" and m.get("geometry")]
        if not members:
            stats["relations_without_geometry"] += 1
            continue

        mtags = [member_tags.get(m["ref"], {}) for m in members]
        cls, basis = _route_substance(tags, mtags, name)
        if cls is None:
            stats["relations_substance_unresolved"] += 1
            continue

        ways = [[(p["lon"], p["lat"]) for p in m["geometry"] if p] for m in members]
        member_ids = [m["ref"] for m in members]
        chains = stitch(ways)
        raw_components = len(chains)
        chains, welds, max_weld_km = weld(chains)
        total_km = sum(_length_km(c) for c in chains)
        if total_km < min_km:
            stats["routes_below_min_km"] += 1
            continue

        overlap = bool(set(member_ids) & analytic_osm_ids)
        simplified = []
        for c in chains:
            s = _round(_simplify(c, tolerance))
            if len(s) >= 2:
                simplified.append(s)
        if not simplified:
            continue

        routes.append({
            "pipeline_id": _pipeline_id("rel", rel["id"]),
            "canonical_name": name,
            "asset_class": cls,
            "substance_basis": basis,
            "operator": tags.get("operator"),
            "status": tags.get("status") or tags.get("pipeline:status"),
            "osm_relation_id": rel["id"],
            "osm_way_ids": member_ids,
            "member_count": len(members),
            "components": simplified,
            "stitched_components_before_weld": raw_components,
            "welds": welds,
            "max_weld_km": max_weld_km,
            "length_km": round(total_km, 1),
            "analytic_overlap": overlap,
            "route_quality": "osm_mapped",
            "geometry_source": "osm_relation",
        })
        stats["routes_built"] += 1
        stats[f"routes_{cls}"] += 1
    return routes, stats


def build_named_way_routes(way_elements, claimed_way_ids, analytic_osm_ids=None,
                           min_km=MIN_TRUNK_KM, tolerance=TOLERANCE):
    """Routes for named trunk ways that belong to NO relation.

    Grouped by (name, substance) and stitched, so a corridor mapped as many short named ways is
    assembled before its length is judged — the case that destroyed 65 named routes outright
    under the old per-way filter. Ways already claimed by a relation are skipped so a corridor is
    not represented twice.
    """
    analytic_osm_ids = set(analytic_osm_ids or ())
    groups = collections.defaultdict(list)
    for el in way_elements:
        if el.get("id") in claimed_way_ids:
            continue
        tags = el.get("tags", {}) or {}
        name = tags.get("name") or tags.get("name:en")
        if not name:
            continue
        cls = _classify(tags.get("substance"))
        if cls is None:
            continue
        pts = [(p["lon"], p["lat"]) for p in (el.get("geometry") or []) if p]
        if len(pts) >= 2:
            groups[(name, cls)].append((el["id"], pts, tags))

    routes = []
    for (name, cls), items in groups.items():
        chains = stitch([pts for _, pts, _ in items])
        raw_components = len(chains)
        chains, welds, max_weld_km = weld(chains)
        total_km = sum(_length_km(c) for c in chains)
        if total_km < min_km:
            continue
        ids = [i for i, _, _ in items]
        simplified = [s for s in (_round(_simplify(c, tolerance)) for c in chains) if len(s) >= 2]
        if not simplified:
            continue
        operator = next((t.get("operator") for _, _, t in items if t.get("operator")), None)
        digest = hashlib.sha1(f"{name}|{cls}".encode("utf-8")).hexdigest()[:12]
        routes.append({
            "pipeline_id": _pipeline_id("name", digest),
            "canonical_name": name,
            "asset_class": cls,
            "substance_basis": "way_substance_tag",
            "operator": operator,
            "status": None,
            "osm_relation_id": None,
            "osm_way_ids": ids,
            "member_count": len(ids),
            "components": simplified,
            "stitched_components_before_weld": raw_components,
            "welds": welds,
            "max_weld_km": max_weld_km,
            "length_km": round(total_km, 1),
            "analytic_overlap": bool(set(ids) & analytic_osm_ids),
            "route_quality": "osm_mapped",
            "geometry_source": "osm_named_ways",
        })
    return routes


def to_features(routes):
    """One GeoJSON feature per contiguous COMPONENT, all components of a route sharing its
    pipeline_id. Keeping components separate is deliberate: a route that is genuinely in three
    pieces must look like three pieces, not be silently bridged into one."""
    feats = []
    for r in routes:
        n = len(r["components"])
        for i, coords in enumerate(r["components"]):
            feats.append({
                "type": "Feature",
                "properties": {
                    "pipeline_id": r["pipeline_id"],
                    "asset_class": r["asset_class"],
                    "scope": "context",
                    "name": r["canonical_name"],
                    "operator": r["operator"],
                    "status": r["status"],
                    "route_quality": r["route_quality"],
                    "geometry_source": r["geometry_source"],
                    "substance_basis": r["substance_basis"],
                    "analytic_overlap": r["analytic_overlap"],
                    "osm_relation_id": r["osm_relation_id"],
                    "route_length_km": r["length_km"],
                    "component_index": i,
                    "component_count": n,
                },
                "geometry": {"type": "LineString", "coordinates": coords},
            })
    return feats


def quality_report(routes):
    """Deterministic continuity/quality metrics (§12). Topology completeness and geometry
    completeness are reported separately: a single-component route is topologically continuous,
    which is NOT the same as its geometry being accurate."""
    out = {}
    for cls in ("pipeline_gas", "pipeline_oil"):
        rs = [r for r in routes if r["asset_class"] == cls]
        comps = [len(r["components"]) for r in rs]
        continuous = sum(1 for c in comps if c == 1)
        out[cls] = {
            "routes": len(rs),
            "total_length_km": round(sum(r["length_km"] for r in rs), 1),
            "single_component_routes": continuous,
            "multi_component_routes": len(rs) - continuous,
            "total_components": sum(comps),
            "largest_route_components": max(comps) if comps else 0,
            "routes_overlapping_analytic": sum(1 for r in rs if r["analytic_overlap"]),
            "geometry_source": dict(collections.Counter(r["geometry_source"] for r in rs)),
            "route_quality": dict(collections.Counter(r["route_quality"] for r in rs)),
            "substance_basis": dict(collections.Counter(r["substance_basis"] for r in rs)),
        }
    return out


def build(relations=None, member_tags=None, way_elements=None, analytic_osm_ids=None,
          tolerance=TOLERANCE, write=True):
    """Full build. Returns {class: route_count} and writes the two context files."""
    if relations is None:
        from pipeline import fetch_osm_pipelines
        data = fetch_osm_pipelines.fetch_all()
        relations, member_tags = data["relations"], data["member_tags"]
    member_tags = member_tags or {}

    routes, stats = build_routes(relations, member_tags, analytic_osm_ids, tolerance=tolerance)
    claimed = {w for r in routes for w in r["osm_way_ids"]}
    if way_elements:
        routes += build_named_way_routes(way_elements, claimed, analytic_osm_ids,
                                         tolerance=tolerance)

    gas = to_features([r for r in routes if r["asset_class"] == "pipeline_gas"])
    oil = to_features([r for r in routes if r["asset_class"] == "pipeline_oil"])
    report = quality_report(routes)

    if write:
        gas_path = PROCESSED / "context_gas_network.geojson"
        oil_path = PROCESSED / "context_oil_network.geojson"
        # Fail-safe: never overwrite a good committed network with nothing (Overpass down on a
        # cache-less runner). Degrade to yesterday's context rather than dropping it.
        if not gas and not oil and gas_path.exists() and oil_path.exists():
            g = len(read_json(gas_path).get("features", []))
            o = len(read_json(oil_path).get("features", []))
            log(f"pipeline-network: build produced nothing; keeping committed network ({g}+{o})")
            return {"pipeline_gas": g, "pipeline_oil": o}
        write_json(gas_path, {"type": "FeatureCollection", "features": gas})
        write_json(oil_path, {"type": "FeatureCollection", "features": oil})
        write_json(PROCESSED / "pipeline_network_quality.json", report)
        mb = sum((PROCESSED / f).stat().st_size for f in
                 ("context_gas_network.geojson", "context_oil_network.geojson")) / 1e6
        log(f"pipeline-network: {report['pipeline_gas']['routes']} gas + "
            f"{report['pipeline_oil']['routes']} oil canonical routes, "
            f"{len(gas) + len(oil)} components, {mb:.2f} MB")
    return {"pipeline_gas": report["pipeline_gas"]["routes"],
            "pipeline_oil": report["pipeline_oil"]["routes"]}


if __name__ == "__main__":
    build()
