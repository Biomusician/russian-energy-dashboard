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


# Route names that identify a REFINED-PRODUCTS or multi-product system.
#
# OSM's substance=oil is used loosely and is applied to product pipelines as well as crude.
# Exolum's "Canalización de Derivados del Petróleo" ("petroleum derivatives") tags 235 of its
# members substance=oil and NONE as fuel — so no substance-vote rule can catch it, and only the
# NAME can. NATO's CEPS is likewise a multi-product military network. Neither is crude oil
# transmission, which is what this class means and what GOIT scopes.
#
# The list is deliberately short and literal: each entry is a phrase in which the system states
# that it carries products. Nothing here is inferred from context.
_REFINED_PRODUCT_NAME_TOKENS = (
    "derivados del petróleo", "derivados del petroleo", "productos petrolíferos",
    "produits pétroliers", "refined product", "products pipeline", "multiproduct",
    "produktenleitung", "produkten",
    "multi-product", "central europe pipeline system", "нефтепродукт",
)


def _is_refined_products(name):
    n = (name or "").lower()
    return any(t in n for t in _REFINED_PRODUCT_NAME_TOKENS)


# Common nouns that describe a piece of pipe rather than name a route. Grouping ways by these
# manufactured entities: every way tagged "перемычка" (jumper) across a 3,000 km corridor became
# one 153-component "route" with an id and a length. A descriptive noun is not an identity.
_GENERIC_NAME_TOKENS = {
    "перемычка", "лупинг", "отвод", "нитка", "газопровод", "нефтепровод", "труба",
    "loop", "spur", "branch", "connector", "interconnector", "jumper", "pipeline",
    "gasleitung", "leitung", "gasoducto", "oleoducto", "pipe",
}


def _is_generic_name(name):
    """True when a name is a bare descriptive noun with nothing identifying attached."""
    n = (name or "").strip().lower()
    if not n:
        return True
    # Strip punctuation-ish separators and see what is left.
    words = [w for w in n.replace("«", " ").replace("»", " ").replace("-", " ").split() if w]
    if not words:
        return True
    return all(w in _GENERIC_NAME_TOKENS for w in words)


def _bbox_diagonal_km(chains):
    xs = [p[0] for c in chains for p in c]
    ys = [p[1] for c in chains for p in c]
    if not xs:
        return 0.0
    return _haversine((min(xs), min(ys)), (max(xs), max(ys)))


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

    # A node where three or more ways meet is a JUNCTION — a branch, a parallel string joining,
    # a spur. Walking through one arbitrarily lets a chain run out along one string and back
    # along its twin, producing a single LineString laid on top of itself: measured on the real
    # corpus, 7 components drew 757 km of line for ~379 km of corridor. Chains therefore stop at
    # junctions, and each edge-disjoint path is emitted as its own component.
    def degree(node):
        return len(ends.get(node, ()))

    used = [False] * len(segs)
    chains = []
    for start in range(len(segs)):
        if used[start]:
            continue
        used[start] = True
        chain = list(segs[start])
        for direction in (1, 0):
            while True:
                tip = _key(chain[-1] if direction else chain[0])
                if degree(tip) != 2:
                    break                       # dead end, or a junction: stop here
                nxt = next((c for c in ends.get(tip, ()) if not used[c]), None)
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


# Below this, two endpoints are the same OSM node rather than a gap across one. 1 mm.
_ZERO_GAP_KM = 1e-6


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
                        # A gap of exactly zero is not a gap: the endpoints ARE the same node,
                        # which means stitch() already saw it and refused to walk through —
                        # because it is a junction of degree != 2. Welding there re-joins what
                        # the junction rule deliberately separated, letting a chain run out
                        # along one string and back along its twin. Weld closes GAPS; it must
                        # never re-make a decision stitch() already made.
                        if d <= _ZERO_GAP_KM:
                            continue
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
    """Douglas-Peucker, dispatching on whether the chain is CLOSED.

    `simplify_line` keeps `points[0]` and `points[-1]`. On a closed loop those are the same
    coordinate, so it keeps one point twice, `_round` collapses the pair, and the component is
    dropped for having fewer than 2 points. That silently erased 646 components (201.3 km) of
    real pipe — loops around compressor stations and terminals — which then vanished from the map
    while remaining inside `route_length_km`.

    `simplify_ring` exists for exactly this shape and preserves closure, so a closed chain is
    routed to it. Same failure class as the iteration-9 erasure bug, reached from a different
    direction: an open-line algorithm applied to a shape that is not an open line.
    """
    pts = [tuple(p) for p in pts]
    if len(pts) > 3 and pts[0] == pts[-1]:
        return [list(p) for p in geo.simplify_ring(pts, tolerance)]
    return [list(p) for p in geo.simplify_line(pts, tolerance)]


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
    # A system whose own name says it carries products is not crude transmission, whatever its
    # members are tagged. Checked first so no downstream rule can override it.
    if _is_refined_products(name):
        return None, "refined_products_excluded"

    direct = _classify(rel_tags.get("substance"))
    if direct:
        return direct, "relation_substance_tag"

    # Vote over the RAW member substance values, not over the ones that happen to classify.
    # Filtering first lets a refined-product system be captured by a handful of loosely-tagged
    # members: Exolum's "Canalización de Derivados del Petróleo" has 188 members tagged `fuel`
    # and a few tagged `oil`, and the pre-filtered vote made a Spanish products network into a
    # crude oil trunk. If the DOMINANT tagged substance is one we exclude, the route is excluded.
    raw = collections.Counter(
        (t.get("substance") or "").strip().lower() for t in member_tags if t.get("substance"))
    if raw:
        top = raw.most_common(1)[0][0]
        cls = _classify(top)
        if cls:
            return cls, "member_substance_majority"
        return None, "member_substance_excluded"
    hint = _name_hint(name)
    if hint:
        return hint, "route_name_hint"
    return None, "unresolved"


def _pipeline_id(kind, ident):
    return f"osm-{kind}-{ident}"


# Mean distance between consecutive SOURCE vertices, above which a route is not a traced line.
# OSM contains both 5,387-vertex corridors and 3-point placeholders under identical tags — one
# shipped route averages 173 km between vertices and another contains a single 632 km straight
# run. Publishing both as "mapped" asserts a confidence the geometry does not have, so quality is
# measured from the source geometry rather than assumed from the source NAME.
GENERALIZED_SPACING_KM = 10.0
SCHEMATIC_SPACING_KM = 50.0


def _measured_quality(chains):
    """Route quality inferred from source vertex density, with the measurement that decided it.

    Deliberately computed BEFORE simplification: this describes how finely the SOURCE traced the
    route, not how finely we chose to draw it.
    """
    verts = sum(len(c) for c in chains)
    length = sum(_length_km(c) for c in chains)
    segments = max(1, verts - len(chains))
    spacing = length / segments
    if spacing >= SCHEMATIC_SPACING_KM:
        q = "topology_only"
    elif spacing >= GENERALIZED_SPACING_KM:
        q = "osm_generalized"
    else:
        q = "osm_mapped"
    return q, round(spacing, 2)


def build_routes(relations, member_tags, analytic_osm_ids=None, min_km=MIN_TRUNK_KM,
                 tolerance=TOLERANCE):
    """Reconstruct canonical routes from OSM pipeline route relations.

    Returns (routes, stats, way_km). `way_km` maps each member way id to its own measured
    length, so network extent can be an exact union rather than an apportionment.

    Each route is a dict carrying its canonical identity, the stitched components, and full
    provenance. Nothing is dropped for overlapping the analytic feed.
    """
    analytic_osm_ids = set(analytic_osm_ids or ())
    routes = []
    stats = collections.Counter()
    way_km = {}

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

        # A relation may list the same way twice (12 do, for 1,320.8 km of redundant
        # geometry). It is still ONE piece of pipe: using it twice doubles it on the map and
        # inflates the member count that `distinct_network_km` divides by.
        seen_refs, ways, member_ids = set(), [], []
        for m in members:
            ref = m["ref"]
            if ref in seen_refs:
                continue
            seen_refs.add(ref)
            pts = [(p["lon"], p["lat"]) for p in m["geometry"] if p]
            ways.append(pts)
            member_ids.append(ref)
            way_km[ref] = _length_km(pts)
        chains = stitch(ways)
        raw_components = len(chains)
        chains, welds, max_weld_km = weld(chains)
        total_km = sum(_length_km(c) for c in chains)
        if total_km < min_km:
            stats["routes_below_min_km"] += 1
            continue

        overlap = bool(set(member_ids) & analytic_osm_ids)
        quality, spacing_km = _measured_quality(chains)
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
            "drawn_length_km": round(sum(_length_km([tuple(p) for p in c]) for c in simplified), 1),
            "analytic_overlap": overlap,
            "route_quality": quality,
            "source_vertex_spacing_km": spacing_km,
            "geometry_source": "osm_relation",
        })
        stats["routes_built"] += 1
        stats[f"routes_{cls}"] += 1
    return routes, stats, way_km


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
        if not name or _is_generic_name(name):
            continue
        # Goes through the full substance resolver, so the refined-products rules apply here too
        # rather than only on the relation path.
        cls, _basis = _route_substance({"substance": tags.get("substance")}, [tags], name)
        if cls is None:
            continue
        pts = [(p["lon"], p["lat"]) for p in (el.get("geometry") or []) if p]
        if len(pts) >= 2:
            groups[(name, cls)].append((el["id"], pts, tags))

    routes = []
    way_km = {}
    for (name, cls), items in groups.items():
        for wid, pts, _tags in items:
            way_km[wid] = _length_km(pts)
        # NO weld here. Welding is justified only by shared relation membership — OSM asserting
        # two components are one pipeline. A shared name string is not that assertion, so joining
        # name-grouped components across a gap would be exactly the proximity rule this module
        # refuses. They stay as separate components.
        chains = stitch([pts for _, pts, _ in items])
        raw_components = len(chains)
        welds, max_weld_km = 0, 0.0
        total_km = sum(_length_km(c) for c in chains)
        if total_km < min_km:
            continue
        # A name shared by scattered fragments across a continent is a coincidence of wording,
        # not a route. If the group's bounding box is far larger than the pipe it contains, the
        # "route" is an artefact of grouping and must not be published as an entity.
        if _bbox_diagonal_km(chains) > max(200.0, total_km * 1.5):
            continue
        ids = [i for i, _, _ in items]
        simplified = [s for s in (_round(_simplify(c, tolerance)) for c in chains) if len(s) >= 2]
        if not simplified:
            continue
        quality, spacing_km = _measured_quality(chains)
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
            "drawn_length_km": round(sum(_length_km([tuple(p) for p in c]) for c in simplified), 1),
            "analytic_overlap": bool(set(ids) & analytic_osm_ids),
            "route_quality": quality,
            "source_vertex_spacing_km": spacing_km,
            "geometry_source": "osm_named_ways",
        })
    return routes, way_km


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
                    "canonical_pipeline_id": r.get("canonical_pipeline_id"),
                    "canonical_name": r.get("canonical_name_registry"),
                    "entity_level": r.get("entity_level") or "pipeline",
                    "parent_id": r.get("parent_id"),
                    "match_confidence": r.get("match_confidence") or "unresolved",
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
                    "drawn_length_km": r["drawn_length_km"],
                    "source_vertex_spacing_km": r["source_vertex_spacing_km"],
                    "welds": r["welds"],
                    "max_weld_km": r["max_weld_km"],
                    "component_index": i,
                    "component_count": n,
                },
                "geometry": {"type": "LineString", "coordinates": coords},
            })
    return feats


def _containment(routes, min_share=0.9):
    """Measured parent->child edges: route B is inside route A when >=90% of B's member ways are
    also A's and A is larger.

    This is how OSM's superroutes are detected without guessing from names — Сияние Севера
    contains 12 strings, Yamal–Lubmin contains 6 — and it is the same overlap that made a naive
    sum of route lengths double-count ~13% of the network.
    """
    ways = {r["pipeline_id"]: set(r["osm_way_ids"]) for r in routes}
    parent = {}
    for b, wb in ways.items():
        if not wb:
            continue
        best = None
        for a, wa in ways.items():
            if a == b or len(wa) <= len(wb):
                continue
            if len(wa & wb) / len(wb) >= min_share:
                # smallest qualifying parent = the immediate one
                if best is None or len(wa) < len(ways[best]):
                    best = a
        if best:
            parent[b] = best
    return parent


def apply_registry(routes, entities):
    """Attach canonical identity to each reconstructed route.

    A route is matched to a canonical entity through the explicit source map, never by name. The
    mapping is many-to-many by design, so a route may be claimed by more than one entity (a
    superroute AND the string it contains); the FINEST-grained claim wins for display, because a
    reader clicking a line wants the pipeline, not the continent-spanning system it belongs to.
    """
    by_source = {}
    for e in entities.values():
        for sr in e["source_records"]:
            by_source.setdefault(sr["source_id"], []).append((e, sr))
    depth = {}

    def _depth(cid):
        if cid in depth:
            return depth[cid]
        e = entities.get(cid)
        depth[cid] = 0 if not e or not e["parent_id"] else _depth(e["parent_id"]) + 1
        return depth[cid]

    for r in routes:
        sid = str(r.get("osm_relation_id") or r["pipeline_id"])
        claims = by_source.get(sid, [])
        if claims:
            # deepest entity = most specific
            e, sr = max(claims, key=lambda c: _depth(c[0]["canonical_pipeline_id"]))
            r["canonical_pipeline_id"] = e["canonical_pipeline_id"]
            r["canonical_name_registry"] = e["canonical_name"]
            r["entity_level"] = e["entity_level"]
            r["parent_id"] = e["parent_id"]
            r["match_confidence"] = sr["confidence"]
            r["all_canonical_claims"] = [c[0]["canonical_pipeline_id"] for c in claims]
        else:
            r["canonical_pipeline_id"] = None
            r["canonical_name_registry"] = None
            r["entity_level"] = "pipeline"       # an uncurated route is a pipeline by default
            r["parent_id"] = None
            r["match_confidence"] = "unresolved"
            r["all_canonical_claims"] = []
    return routes


def geometry_completeness(route):
    """Segment-weighted geometry breakdown for one route.

    Route COUNT is a poor measure: a 2,000 km line with a 10 km gap and a 200 km line missing
    180 km are both "fragmented". Kilometres of each quality are measurable and reported.

    Unresolved length deliberately is NOT estimated. The distance between two mapped components
    is not the length of the missing pipe — the real route between them may be far longer, and
    inventing a figure would be exactly the false precision this project refuses. The gap COUNT
    is reported instead.
    """
    drawn = route["drawn_length_km"]
    q = route["route_quality"]
    detailed = drawn if q == "osm_mapped" else 0.0
    generalized = drawn if q in ("osm_generalized", "gem_generalized") else 0.0
    return {
        "detailed_geometry_km": round(detailed, 1),
        "generalized_geometry_km": round(generalized, 1),
        "unresolved_gap_count": max(0, len(route["components"]) - 1),
        "detailed_geometry_pct": round(100.0 * detailed / drawn, 1) if drawn else 0.0,
        "generalized_geometry_pct": round(100.0 * generalized / drawn, 1) if drawn else 0.0,
    }


def canonical_coverage(routes, entities):
    """How canonical the "canonical registry" actually is — measured in KILOMETRES.

    Entity counts flatter the result: 36 curated entities against 464 routes reads as 8% coverage,
    while those 36 include the largest trunk systems in the dataset. Kilometres of DISTINCT mapped
    pipe attached to a curated identity is the honest measure, and it is the one reported.

    Deduplicated by OSM way, so a corridor and the strings inside it cannot both claim the same
    kilometre — otherwise curated coverage would be inflated precisely where hierarchy is richest.
    """
    curated = {cid for cid, e in entities.items() if e.get("curated")}
    # Curated routes claim their ways FIRST, so a kilometre shared between a curated corridor and
    # an auto-derived route counts once, on the curated side. Deterministic: sorted by id.
    ordered = sorted(routes, key=lambda r: (r.get("canonical_pipeline_id") not in curated,
                                            r["pipeline_id"]))
    seen, total_km, cur_km = set(), 0.0, 0.0
    for r in ordered:
        ids = r["osm_way_ids"]
        new_ids = [w for w in ids if w not in seen]
        if not new_ids:
            continue
        # Same attribution as `distinct_network_km`: km apportioned by SHARE OF MEMBER WAYS, not
        # by per-way length, because per-way lengths are not carried. Ways within one route are
        # of broadly similar size, so this is a close approximation — but it is an approximation,
        # and it is described as one wherever the number is published.
        km = r["length_km"] * (len(new_ids) / max(1, len(ids)))
        total_km += km
        if r.get("canonical_pipeline_id") in curated:
            cur_km += km
        seen.update(new_ids)
    return {
        "curated_entities": len(curated),
        "auto_derived_entities": len(entities) - len(curated),
        "routes": len(routes),
        "routes_attached_to_curated": sum(
            1 for r in routes if r.get("canonical_pipeline_id") in curated),
        "distinct_km_total": round(total_km, 1),
        "distinct_km_curated": round(cur_km, 1),
        "distinct_km_curated_pct": round(100.0 * cur_km / total_km, 1) if total_km else 0.0,
    }


def registry_payload(entities, nodes, routes):
    """Everything the route detail panel needs, keyed by canonical id.

    Emitted separately from the GeoJSON on purpose: this is entity-level and the GeoJSON is
    component-level, so folding it into feature properties would repeat the same registry entry
    on all 125 components of a fragmented route.

    Temporal status is emitted as INTERVALS, not as a resolved current value. The client can then
    ask "what was true on date D" instead of being handed one mutable answer — which is the whole
    reason status is modelled with validity intervals rather than a status column.
    """
    from pipeline import pipeline_registry

    status_by_entity = collections.defaultdict(list)
    for s in pipeline_registry.load_status():
        status_by_entity[s["canonical_pipeline_id"]].append(s)
    sources_by_entity = collections.defaultdict(list)
    for m in pipeline_registry.load_source_map():
        sources_by_entity[m["canonical_pipeline_id"]].append(m)

    # Documented connections, attached to BOTH ends when both are canonical. This is the payload
    # that lets the dossier answer "what does this connect to" without a line being drawn: a
    # connection is known when its endpoints are named and sourced, whether or not the route
    # between them is mapped.
    nodes = pipeline_registry.load_nodes()
    node_sources = pipeline_registry.load_node_sources()
    topo_by_entity = collections.defaultdict(list)
    for t in pipeline_registry.load_topology():
        node = nodes.get(t["node_id"] or "")
        entry = {
            **{k: t[k] for k in ("relation", "at_point", "substance", "source_quality",
                                 "source_url", "linkage", "linkage_reason", "note")},
            "node_id": t["node_id"],
            "node_name": node["node_name"] if node else (t["at_point"] or None),
            "node_type": node["node_type"] if node else None,
            "node_country": node["country"] if node else None,
            # Carried so the UI can say WHY nothing is drawn, rather than silently omitting it.
            "node_geography_precision": node["geography_precision"] if node else None,
            "node_sources": node_sources.get(t["node_id"] or "", []),
        }
        if t["subject_id"]:
            topo_by_entity[t["subject_id"]].append(
                {**entry, "other": t["object_id"] or t["object"], "other_id": t["object_id"],
                 "direction": "from"})
        if t["object_id"] and t["object_id"] != t["subject_id"]:
            topo_by_entity[t["object_id"]].append(
                {**entry, "other": t["subject_id"] or t["subject"], "other_id": t["subject_id"],
                 "direction": "to"})

    # Roll route-level geometry up to the canonical entity: one entity may own several routes.
    geom = collections.defaultdict(lambda: {"detailed_geometry_km": 0.0,
                                            "generalized_geometry_km": 0.0,
                                            "unresolved_gap_count": 0, "routes": 0})
    for r in routes:
        cid = r.get("canonical_pipeline_id")
        if not cid:
            continue
        g = geometry_completeness(r)
        agg = geom[cid]
        agg["detailed_geometry_km"] += g["detailed_geometry_km"]
        agg["generalized_geometry_km"] += g["generalized_geometry_km"]
        agg["unresolved_gap_count"] += g["unresolved_gap_count"]
        agg["routes"] += 1

    out = {}
    for cid, e in entities.items():
        agg = geom.get(cid)
        out[cid] = {
            **{k: e.get(k) for k in ("canonical_pipeline_id", "canonical_name", "aliases",
                                     "commodity", "subtype", "entity_level", "parent_id",
                                     "operator", "owner", "countries", "start_area", "end_area",
                                     "note", "curated")},
            "child_ids": sorted(c for c, v in entities.items() if v.get("parent_id") == cid),
            "sources": sources_by_entity.get(cid, []),
            "status": status_by_entity.get(cid, []),
            "connections": topo_by_entity.get(cid, []),
            "alias_records": e.get("alias_records") or [],
            "geometry": ({k: (round(v, 1) if isinstance(v, float) else v)
                          for k, v in agg.items()} if agg else None),
        }
    return {"entities": out, "nodes": nodes,
            "coverage": canonical_coverage(routes, entities),
            "generated_note": ("Status is emitted as validity intervals, never as a single "
                               "current value; geometry is segment-weighted and unresolved gap "
                               "length is deliberately not estimated.")}


def quality_report(routes, way_lengths=None):
    way_lengths = way_lengths or {}
    """Deterministic continuity/quality metrics (§12). Topology completeness and geometry
    completeness are reported separately: a single-component route is topologically continuous,
    which is NOT the same as its geometry being accurate."""
    out = {}
    for cls in ("pipeline_gas", "pipeline_oil"):
        rs = [r for r in routes if r["asset_class"] == cls]
        comps = [len(r["components"]) for r in rs]
        continuous = sum(1 for c in comps if c == 1)
        # OSM models some systems as a superroute PLUS its constituent line relations, so the
        # same physical way can belong to two routes. Summing route lengths therefore counts that
        # pipe twice. Both numbers are published: the sum is "length across routes", and the
        # union over distinct member way ids is the actual network extent. Conflating them would
        # overstate the network by ~13%.
        # Exact union over distinct member ways, using each way's own measured length. The
        # previous apportionment (route length x share of member COUNT) assumed every way in a
        # route was the same size; it was wrong by ~1.6% and, worse, ORDER-DEPENDENT — the same
        # data gave a 5,638 km spread across route orderings, and it credited a whole corridor's
        # kilometres to whichever relation the loop happened to reach first. Nord Stream was the
        # visible symptom: an unidentified legacy relation took all 2,448.7 km and the two real
        # pipelines were docked to 349.9 and 704.4.
        seen_ways, distinct_km, unmeasured = set(), 0.0, 0
        for r in rs:
            for w in r["osm_way_ids"]:
                if w in seen_ways:
                    continue
                seen_ways.add(w)
                if w in way_lengths:
                    distinct_km += way_lengths[w]
                else:
                    unmeasured += 1
        # Canonical-entity counts, so a system and the strings inside it are not counted as
        # equivalent "pipelines". Routes with no canonical claim count as their own entity.
        canon = set()
        for r in rs:
            canon.add(r.get("canonical_pipeline_id") or r["pipeline_id"])
        levels = collections.Counter(r.get("entity_level") or "pipeline" for r in rs)
        det = sum(geometry_completeness(r)["detailed_geometry_km"] for r in rs)
        gen = sum(geometry_completeness(r)["generalized_geometry_km"] for r in rs)
        gaps = sum(geometry_completeness(r)["unresolved_gap_count"] for r in rs)
        out[cls] = {
            "routes": len(rs),
            "canonical_entities": len(canon),
            "by_entity_level": dict(levels),
            "detailed_geometry_km": round(det, 1),
            "generalized_geometry_km": round(gen, 1),
            "unresolved_gap_count": gaps,
            "total_length_km": round(sum(r["length_km"] for r in rs), 1),
            "distinct_network_km": round(distinct_km, 1),
            "drawn_length_km": round(sum(r["drawn_length_km"] for r in rs), 1),
            "welds": sum(r["welds"] for r in rs),
            "max_weld_km": round(max([r["max_weld_km"] for r in rs] or [0]), 4),
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

    routes, stats, way_lengths = build_routes(relations, member_tags, analytic_osm_ids,
                                              tolerance=tolerance)
    # Named-way routes are appended BEFORE the registry runs. Previously the registry was built
    # from relation routes only and then these were bolted on, so 183 of 464 routes (244 of 1,292
    # drawn features) carried `canonical_pipeline_id: null` and resolved to nothing in the
    # payload — while the module docstring claimed the registry "always covers the whole network".
    # It now does.
    claimed = {w for r in routes for w in r["osm_way_ids"]}
    if way_elements:
        named, named_km = build_named_way_routes(way_elements, claimed, analytic_osm_ids,
                                                 tolerance=tolerance)
        routes += named
        way_lengths.update(named_km)

    # Canonical identity + hierarchy from the curated registry (never from name equality).
    from pipeline import pipeline_registry
    entities, nodes, problems = pipeline_registry.build(routes, containment=_containment(routes))
    for p in problems:
        log(f"  registry PROBLEM {p}")
    apply_registry(routes, entities)

    gas = to_features([r for r in routes if r["asset_class"] == "pipeline_gas"])
    oil = to_features([r for r in routes if r["asset_class"] == "pipeline_oil"])
    report = quality_report(routes, way_lengths)

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
        write_json(PROCESSED / "pipeline_registry.json",
                   registry_payload(entities, nodes, routes))
        mb = sum((PROCESSED / f).stat().st_size for f in
                 ("context_gas_network.geojson", "context_oil_network.geojson")) / 1e6
        log(f"pipeline-network: {report['pipeline_gas']['routes']} gas + "
            f"{report['pipeline_oil']['routes']} oil canonical routes, "
            f"{len(gas) + len(oil)} components, {mb:.2f} MB")
    return {"pipeline_gas": report["pipeline_gas"]["routes"],
            "pipeline_oil": report["pipeline_oil"]["routes"]}


if __name__ == "__main__":
    build()
