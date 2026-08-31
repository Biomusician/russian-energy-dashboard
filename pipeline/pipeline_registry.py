"""Canonical pipeline registry: identity, hierarchy and TEMPORAL status.

WHY A REGISTRY. Iteration 9 gave every reconstructed route a `pipeline_id`, but those ids are
source identifiers (`osm-rel-8197671`), not identities. A canonical entity has to survive a source
changing its mind, has to be able to map to SEVERAL source records, and has to say what KIND of
thing it is — because OSM models "Сияние Севера" (a multi-string system), "Ухта — Торжок 3" (one
of its strings) and "BOTAŞ Doğal Gaz Boru Hatları" (a national network) as the same kind of
object, and counting those as three equivalent "pipelines" is how a network gets double-counted.

FOUR RULES THIS MODULE EXISTS TO ENFORCE:

  1. IDENTITY IS NOT NAME EQUALITY. A canonical id is assigned, never derived from a display
     string. Sources attach to it through an explicit many-to-many map, so one canonical entity
     may aggregate several source records and one source record may be split across several
     canonical children where the sources genuinely disagree about aggregation level.

  2. HIERARCHY IS STRUCTURAL. `entity_level` comes from a closed vocabulary and `parent_id` is a
     real edge. Hierarchy is never encoded in a name or a note, because then nothing can count
     correctly.

  3. STATUS IS TEMPORAL AND MULTI-DIMENSIONAL. There is no single mutable `status` column. A
     status record carries what KIND of status it is (physical / operational / commercial flow),
     its validity interval, when it was observed, and its source. A physically intact pipeline
     carrying zero contracted transit is not destroyed, and a plant GEM calls retired in 2026 was
     not retired in 2022 — both facts need somewhere to live before either can be reasoned about.

  4. A NODE NEED NOT HAVE GEOGRAPHY. Connection points carry `geography_precision`, and `none` is
     a legitimate, common value. A documented connection at a named compressor station is real
     topology; it is not a licence to invent a coordinate so the connection can be drawn.

Curated files are the source of truth; anything not curated is auto-derived from the reconstructed
OSM routes so the registry always covers the whole network.
"""

import collections
import csv

from pipeline.config import CURATED
from pipeline.util import log

# --- closed vocabularies -----------------------------------------------------------------
# Ordered coarse -> fine. A `system` aggregates `corridor`s, which aggregate `pipeline`s, which
# may have `branch`es, which are made of `physical_segment`s.
ENTITY_LEVELS = ("system", "corridor", "pipeline", "branch", "physical_segment")

COMMODITIES = ("gas", "oil")

# GGIT and GOIT are kept apart rather than folded into one `gem_project`: they are separately
# versioned releases on different schedules, so a citation has to name which tracker it came from.
SOURCE_SYSTEMS = ("osm_relation", "osm_named_way_group", "gem_ggit", "gem_goit", "entsog_point",
                  "operator_doc")

# How a source record relates to the canonical entity. `aggregates` is the case that makes the
# map genuinely many-to-many: one GEM project may cover what OSM splits into several relations,
# and one OSM superroute may cover several GEM projects.
RELATIONSHIPS = ("represents", "part_of", "aggregates")

MATCH_CONFIDENCE = ("exact", "strong", "possible", "unresolved")
AUTO_MERGE_CONFIDENCE = ("exact", "strong")     # nothing weaker may become canonical silently

STATUS_KINDS = ("physical", "operational", "commercial_flow")

# Deliberately separate vocabularies: "intact" and "flowing" are different questions.
PHYSICAL_STATUS = ("intact", "damaged", "destroyed", "dismantled", "under_construction",
                   "planned", "cancelled", "unknown")
OPERATIONAL_STATUS = ("operating", "idle", "mothballed", "suspended", "retired", "never_operated",
                      "unknown")
COMMERCIAL_FLOW_STATUS = ("flowing", "reduced", "zero_transit", "reversed", "contracted_only",
                          "unknown")
STATUS_VALUES = {
    "physical": PHYSICAL_STATUS,
    "operational": OPERATIONAL_STATUS,
    "commercial_flow": COMMERCIAL_FLOW_STATUS,
}

NODE_TYPES = ("compressor_station", "border_point", "interconnection", "hub", "terminal",
              "junction", "measuring_station", "landfall", "splitting_point")

# `none` is a first-class value, not a failure. Most documented connection points have no
# defensible public coordinate, and that is fine — see rule 4 above.
GEOGRAPHY_PRECISION = ("none", "country", "region", "named_place", "coordinate")

SOURCE_TIERS = ("operator_primary", "tso_primary", "secondary_citing_operator",
                "secondary_citing_tso", "secondary", "encyclopedic", "derived")


def _rows(name):
    path = CURATED / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if any((v or "").strip() for v in r.values())]


def _split(value):
    return [v.strip() for v in (value or "").split("|") if v.strip()]


# An alias is durable canonical identity, so it carries provenance like any other claim.
# Native-language names, romanisations, translations and standard abbreviations are deterministic
# forms of the canonical name and evidence themselves. A PROJECT NICKNAME does not: it must point
# at an artifact that attests it, or it does not belong in the registry at all. Eight unsourced
# nicknames were removed rather than kept on the strength of sounding familiar.
ALIAS_TYPES = ("native_name", "transliteration", "translation", "abbreviation",
               "project_name", "operator_name", "historical")

# Types that need no external source: each is a mechanical restatement of the canonical name.
SELF_EVIDENCING = ("native_name", "transliteration", "translation", "abbreviation")


def load_aliases():
    """{canonical_pipeline_id: [alias record]} from the sourced alias table."""
    out = {}
    for r in _rows("pipeline_aliases.csv"):
        cid = r["canonical_pipeline_id"].strip()
        out.setdefault(cid, []).append({
            "alias": r["alias"].strip(),
            "alias_type": (r.get("alias_type") or "").strip(),
            "language": (r.get("language") or "").strip() or None,
            "source_url": (r.get("source_url") or "").strip() or None,
            "source_date": (r.get("source_date") or "").strip() or None,
            "note": (r.get("note") or "").strip() or None,
        })
    return out


def load_registry():
    """Curated canonical entities. Returns {canonical_pipeline_id: entity}."""
    out = {}
    aliases = load_aliases()
    for r in _rows("pipeline_registry.csv"):
        cid = r["canonical_pipeline_id"].strip()
        out[cid] = {
            "canonical_pipeline_id": cid,
            "canonical_name": r["canonical_name"].strip(),
            # Flat list for matching and search; the provenance-carrying records alongside it.
            "aliases": [a["alias"] for a in aliases.get(r["canonical_pipeline_id"].strip(), [])],
            "alias_records": aliases.get(r["canonical_pipeline_id"].strip(), []),
            "commodity": (r.get("commodity") or "").strip(),
            "subtype": (r.get("subtype") or "").strip() or None,
            "entity_level": (r.get("entity_level") or "").strip(),
            "parent_id": (r.get("parent_id") or "").strip() or None,
            "operator": (r.get("operator") or "").strip() or None,
            "owner": (r.get("owner") or "").strip() or None,
            "countries": _split(r.get("countries")),
            "start_area": (r.get("start_area") or "").strip() or None,
            "end_area": (r.get("end_area") or "").strip() or None,
            "note": (r.get("note") or "").strip() or None,
            "curated": True,
            "child_ids": [],
            "source_records": [],
            "status": [],
        }
    return out


def load_source_map():
    """Many-to-many canonical<->source mappings."""
    out = []
    for r in _rows("pipeline_source_map.csv"):
        out.append({
            "canonical_pipeline_id": r["canonical_pipeline_id"].strip(),
            "source_system": r["source_system"].strip(),
            "source_id": r["source_id"].strip(),
            "relationship": (r.get("relationship") or "represents").strip(),
            "confidence": (r.get("confidence") or "exact").strip(),
            "evidence": (r.get("evidence") or "").strip() or None,
            # Source-native values are preserved verbatim alongside our normalised fields, so a
            # later reconciliation can revisit a judgement without re-fetching the source.
            "source_native": (r.get("source_native") or "").strip() or None,
        })
    return out


def load_status():
    """Temporal status records. Many per entity; overlapping kinds are expected."""
    out = []
    for r in _rows("pipeline_status.csv"):
        out.append({
            "canonical_pipeline_id": r["canonical_pipeline_id"].strip(),
            "status_kind": r["status_kind"].strip(),
            "status_value": r["status_value"].strip(),
            "valid_from": (r.get("valid_from") or "").strip() or None,
            "valid_to": (r.get("valid_to") or "").strip() or None,
            "observed_at": (r.get("observed_at") or "").strip() or None,
            "source_url": (r.get("source_url") or "").strip() or None,
            "source_date": (r.get("source_date") or "").strip() or None,
            "source_tier": (r.get("source_tier") or "").strip() or None,
            "note": (r.get("note") or "").strip() or None,
        })
    return out


def load_topology():
    """Sourced connection assertions. A connection can be KNOWN without being DRAWABLE.

    `linkage` records how far each assertion resolves into the registry:
      full        subject, object and node are all canonical
      partial     at least one end is canonical; the reason says which is not and why
      unresolved  neither end is canonical yet — kept because the assertion itself is sourced

    A partial row is not a defect. Most objects here are foreign networks, terminals and
    non-Russian pipelines that this atlas deliberately does not model; recording the connection
    to them is still real topology.
    """
    out = []
    for r in _rows("pipeline_topology.csv"):
        out.append({
            "subject": (r.get("subject") or "").strip(),
            "subject_id": (r.get("subject_id") or "").strip() or None,
            "relation": (r.get("relation") or "").strip(),
            "object": (r.get("object") or "").strip(),
            "object_id": (r.get("object_id") or "").strip() or None,
            "at_point": (r.get("at_point") or "").strip() or None,
            "node_id": (r.get("node_id") or "").strip() or None,
            "substance": (r.get("substance") or "").strip() or None,
            "source_quality": (r.get("source_quality") or "").strip() or None,
            "source_url": (r.get("source_url") or "").strip() or None,
            "linkage": (r.get("linkage") or "").strip() or None,
            "linkage_reason": (r.get("linkage_reason") or "").strip() or None,
            "note": (r.get("note") or "").strip() or None,
        })
    return out


def load_node_sources():
    """Independent source mappings for canonical nodes (currently ENTSOG).

    Read from the vendor snapshot rather than a curated file: these are produced by an importer
    and re-derived on refresh, so hand-editing them would be overwritten.
    """
    path = CURATED.parent / "vendor" / "entsog" / "node_matches.csv"
    out = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            nid = r["canonical_node_id"]
            rec = {"source_system": r["source_system"], "source_id": r["source_id"],
                   "point_eic": (r.get("point_eic") or "").strip() or None,
                   "confidence": r.get("confidence"),
                   "source_native": r.get("source_native")}
            if rec not in out.setdefault(nid, []):
                out[nid].append(rec)
    return out


def load_nodes():
    """Canonical connection points. Geography is optional by design."""
    out = {}
    for r in _rows("network_nodes.csv"):
        nid = r["canonical_node_id"].strip()
        prec = (r.get("geography_precision") or "none").strip()
        lon = (r.get("lon") or "").strip()
        lat = (r.get("lat") or "").strip()
        out[nid] = {
            "canonical_node_id": nid,
            "node_name": r["node_name"].strip(),
            "node_type": (r.get("node_type") or "").strip(),
            # Sources spell the same border point differently (diacritics, the neighbouring
            # town's name, an operator's own label). Aliases let a match be made by curation
            # rather than by loosening the matcher.
            "aliases": _split(r.get("aliases")),
            "country": (r.get("country") or "").strip() or None,
            "geography_precision": prec,
            # Only a `coordinate`-precision node may carry lon/lat at all. Anything else keeps
            # them null so nothing downstream can quietly treat a name as a position.
            "lon": float(lon) if (prec == "coordinate" and lon) else None,
            "lat": float(lat) if (prec == "coordinate" and lat) else None,
            "source_url": (r.get("source_url") or "").strip() or None,
            "source_date": (r.get("source_date") or "").strip() or None,
            "note": (r.get("note") or "").strip() or None,
        }
    return out


def status_at(records, kind, when):
    """The status of `kind` in force at date `when` (ISO string), or None.

    This is the whole point of storing intervals: asking "what was true in 2022" must not return
    what is true in 2026. A record with no `valid_from` is treated as always having been true up
    to its `valid_to`; a record with no `valid_to` is still in force.
    """
    best = None
    for r in records:
        if r["status_kind"] != kind:
            continue
        if r["valid_from"] and when < r["valid_from"]:
            continue
        if r["valid_to"] and when >= r["valid_to"]:
            continue
        # Prefer the most recently-starting record that is in force.
        if best is None or (r["valid_from"] or "") >= (best["valid_from"] or ""):
            best = r
    return best


def auto_derive(routes, containment, curated_by_pipeline_id=None):
    """Canonical entities for reconstructed routes that no curated row covers.

    Auto-derived entities are `pipeline` level with a parent taken from measured containment, so
    the registry describes the WHOLE network rather than only the curated headline systems. They
    are marked `curated: False` so an audit can always tell a judgement from a default.
    """
    curated_by_pipeline_id = curated_by_pipeline_id or {}
    out = {}
    for r in routes:
        cid = f"auto-{r['pipeline_id']}"
        parent = containment.get(r["pipeline_id"])
        out[cid] = {
            "canonical_pipeline_id": cid,
            "canonical_name": r["canonical_name"] or r["pipeline_id"],
            "aliases": [],
            "commodity": "oil" if r["asset_class"] == "pipeline_oil" else "gas",
            "subtype": None,
            "entity_level": "pipeline",
            # A containment parent may itself be CURATED (Сияние Севера is NORTHERN_LIGHTS, not
            # auto-osm-rel-8197671), so resolve through the curated map before falling back.
            "parent_id": (curated_by_pipeline_id.get(parent) or f"auto-{parent}") if parent else None,
            "operator": r.get("operator"),
            "owner": None,
            "countries": [],
            "start_area": None,
            "end_area": None,
            "note": None,
            "curated": False,
            "child_ids": [],
            "source_records": [{
                "source_system": "osm_relation" if r["geometry_source"] == "osm_relation"
                                 else "osm_named_way_group",
                "source_id": str(r.get("osm_relation_id") or r["pipeline_id"]),
                "relationship": "represents",
                "confidence": "exact",
                "evidence": "reconstructed route identity",
                "source_native": None,
            }],
            "status": [],
        }
    return out


def build(routes, containment=None):
    """Assemble the registry: curated entities + source map + status + auto-derived remainder.

    Returns (entities, nodes, problems). `problems` is never raised — a malformed curated row is
    reported, not silently dropped, because a registry that quietly ignores its own data is worse
    than one that complains.
    """
    problems = []
    entities = load_registry()
    nodes = load_nodes()

    # --- attach source records (many-to-many) ---
    for m in load_source_map():
        cid = m["canonical_pipeline_id"]
        if cid not in entities:
            problems.append(f"source_map references unknown canonical id {cid}")
            continue
        if m["source_system"] not in SOURCE_SYSTEMS:
            problems.append(f"{cid}: unknown source_system {m['source_system']!r}")
        if m["relationship"] not in RELATIONSHIPS:
            problems.append(f"{cid}: unknown relationship {m['relationship']!r}")
        if m["confidence"] not in MATCH_CONFIDENCE:
            problems.append(f"{cid}: unknown confidence {m['confidence']!r}")
        entities[cid]["source_records"].append(m)

    # --- attach temporal status ---
    for st in load_status():
        cid = st["canonical_pipeline_id"]
        if cid not in entities:
            problems.append(f"status references unknown canonical id {cid}")
            continue
        if st["status_kind"] not in STATUS_KINDS:
            problems.append(f"{cid}: unknown status_kind {st['status_kind']!r}")
        elif st["status_value"] not in STATUS_VALUES[st["status_kind"]]:
            problems.append(f"{cid}: {st['status_kind']} value {st['status_value']!r} not in vocabulary")
        entities[cid]["status"].append(st)

    # --- auto-derive the remainder ---
    claimed = {sr["source_id"] for e in entities.values() for sr in e["source_records"]}
    # pipeline_id -> canonical id, so an auto-derived child can name a curated parent correctly.
    curated_by_pid = {}
    for r in (routes or []):
        sid = str(r.get("osm_relation_id") or r["pipeline_id"])
        for e in entities.values():
            if any(sr["source_id"] == sid for sr in e["source_records"]):
                curated_by_pid[r["pipeline_id"]] = e["canonical_pipeline_id"]
                break
    uncovered = [r for r in (routes or [])
                 if str(r.get("osm_relation_id") or r["pipeline_id"]) not in claimed]
    entities.update(auto_derive(uncovered, containment or {}, curated_by_pid))

    # --- resolve hierarchy edges ---
    for cid, e in entities.items():
        p = e["parent_id"]
        if p and p not in entities:
            problems.append(f"{cid}: parent_id {p} does not exist")
            e["parent_id"] = None
        elif p:
            entities[p]["child_ids"].append(cid)
    for cid in entities:
        if _has_cycle(entities, cid):
            problems.append(f"{cid}: hierarchy contains a cycle")
            break

    for e in entities.values():
        for a in e.get("alias_records") or []:
            if a["alias_type"] not in ALIAS_TYPES:
                problems.append(f"{e['canonical_pipeline_id']}: bad alias_type "
                                f"{a['alias_type']!r} on {a['alias']!r}")
            # A nickname is a CLAIM about what something is called. It needs a source, or it is
            # hearsay that has quietly become identity.
            elif a["alias_type"] not in SELF_EVIDENCING and not a["source_url"]:
                problems.append(f"{e['canonical_pipeline_id']}: alias {a['alias']!r} is a "
                                f"{a['alias_type']} with no source_url")
        if e["entity_level"] not in ENTITY_LEVELS:
            problems.append(f"{e['canonical_pipeline_id']}: bad entity_level {e['entity_level']!r}")
        if e["commodity"] not in COMMODITIES:
            problems.append(f"{e['canonical_pipeline_id']}: bad commodity {e['commodity']!r}")

    return entities, nodes, problems


def _has_cycle(entities, start):
    seen, cur = set(), start
    while cur:
        if cur in seen:
            return True
        seen.add(cur)
        cur = entities.get(cur, {}).get("parent_id")
    return False


def summary(entities):
    """Counts that do NOT treat a system and its child pipelines as equivalent entities."""
    by_level = collections.Counter(e["entity_level"] for e in entities.values())
    curated = sum(1 for e in entities.values() if e["curated"])
    with_status = sum(1 for e in entities.values() if e["status"])
    return {
        "entities": len(entities),
        "curated": curated,
        "auto_derived": len(entities) - curated,
        "by_entity_level": dict(by_level),
        "with_temporal_status": with_status,
        "roots": sum(1 for e in entities.values() if not e["parent_id"]),
    }


if __name__ == "__main__":
    ents, nodes, probs = build([])
    log(f"registry: {summary(ents)}")
    log(f"registry: {len(nodes)} canonical nodes")
    for p in probs:
        log(f"  PROBLEM {p}")
