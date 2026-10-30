"""Build the country systems and the global manifest (iteration 14).

For every system in `systems.COUNTRY_SYSTEMS` this reads the curated sources under
`data/curated/systems/<id>/` and emits `data/processed/systems/<id>/`:

  system.json      what the system is, what its evidence supports, and why it has no score
  events.json      reviewed, publicly reported major disruptions, admin-1 precision at most
  regions.geojson  the first-level units the events are aggregated to

and, once for all systems, `data/processed/global/manifest.json` and `global/world.geojson`.

WHAT IT DELIBERATELY DOES NOT DO.
- It computes no index, no sector value and no decay. Every sector's published state is at
  most CONTEXT_ONLY until a recovery model for that country is approved
  (GLOBAL_METHODOLOGY.md §2, §8.3). A country with no score shows no score: never a zero.
- It reads no candidate file. `data/candidates/` is a research queue; only the reviewed events
  in `data/curated/systems/<id>/events.json` (written by `scripts/import_candidates.py`) reach a
  payload. The same human-gated rule that has kept discovery out of the Russia build since
  iteration 6.
- It emits no coordinate for any event, and no field that orders systems by any figure.
"""

import datetime as dt

from pipeline import geo, systems
from pipeline.config import ASSET_CLASSES, CURATED, DISRUPTION_CAUSES, PROCESSED, RAW, SECTORS
from pipeline.util import fetch, log, read_json, write_json

SYSTEMS_CURATED = CURATED / "systems"
ADMIN1_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
              "geojson/ne_10m_admin_1_states_provinces.geojson")
ADMIN0_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
              "geojson/ne_50m_admin_0_countries.geojson")

# ISO 3166-2 changed four Indian codes in November 2023; Natural Earth (last released 2022)
# still carries the old ones. The events use the current codes, so the geometry is moved to them.
ISO_CODE_FIXES = {"IN-CT": "IN-CG", "IN-UT": "IN-UK", "IN-OR": "IN-OD", "IN-TG": "IN-TS"}

# Special administrative regions that Natural Earth files as their own admin-0 units. They are
# part of the China system as single units. Their admin-1 districts are not used.
SAR_UNITS = {"cn": {"HKG": ("CN-HK", "Hong Kong"), "MAC": ("CN-MO", "Macau")}}

# Simplification tolerance in degrees. Canada's Arctic coastline is enormous at 0.01; 0.02 halves
# it with no visible loss at country zoom (measured in GLOBAL_GEOGRAPHY.md).
REGION_TOLERANCE = {"ca": 0.02}
DEFAULT_TOLERANCE = 0.01
WORLD_TOLERANCE = 0.15

# Vocabulary the country systems need and the Russia theatre does not. Kept OUT of the Russia
# taxonomy on purpose: adding a cause there changes what its filters and cause weights mean,
# which is an owner decision (GLOBAL_METHODOLOGY §8.5).
TAXONOMY_EXTENSIONS = {
    "asset_classes": {
        "system_wide": "System-wide (grid area or supply system)",
        "upstream_production": "Upstream production",
    },
    "causes": {
        "natural_hazard": "Natural hazard (weather, wildfire, flood, earthquake)",
        "labour": "Labour action",
    },
}

# The only fields an emitted event may carry. Anything else a lane wrote stays in the queue.
EVENT_FIELDS = (
    "event_id", "date", "date_precision", "date_end", "region_code", "region_name",
    "geography_precision", "regions_affected", "facility_name", "facility_name_local", "operator",
    "asset_class", "cause", "summary", "effect", "inclusion_basis", "criterion_met",
    "threshold_basis", "capacity_affected", "sources", "recovery", "review",
)
# No `title`: headlines are the publishers' words, not ours, and the page shows the publisher.
SOURCE_FIELDS = ("url", "publisher", "date", "language", "source_role", "opened")
RECOVERY_FIELDS = ("research_status", "kind", "date", "evidence", "url")
RECOVERY_STATUSES = ("EVIDENCE_FOUND", "RESEARCHED_NO_PUBLIC_EVIDENCE", "NOT_YET_RESEARCHED")
# What KIND of recovery evidence was found. Required whenever the status is EVIDENCE_FOUND: the
# iteration-14 red team found an estimate, a "nothing was lost" case and a supply-continuity
# statement all rendered as "recovery evidence found". Service restored is not a facility
# rebuilt; an estimate is not an observation; partial is not full.
RECOVERY_KINDS = ("full_restart", "partial_restart", "service_restored", "partial_restoration",
                  "estimate", "supply_unaffected_statement", "no_supply_lost")
# What a lane may say a sector COULD reach. Published beside, never as, the sector state.
ASSESSMENTS = ("READY", "EXPERIMENTAL", "INCOMPLETE", "UNSUITABLE", "INSUFFICIENT_EVIDENCE",
               "NOT_APPLICABLE", "NOT_YET_RESEARCHED")

# Exact UI wording (GLOBAL_METHODOLOGY §6.4), carried in the payload so every surface says the
# same thing and a test can hold it.
COMPARABILITY_STATEMENT = (
    "Each country is measured on its own terms. Event counts reflect what is publicly reported "
    "under that country's reporting rules, not how often disruption happens. A country with "
    "fewer recorded events is not shown to be safer, more resilient or less disrupted. Figures "
    "are not comparable across countries and are never ranked."
)


def load_admin1():
    fetch(ADMIN1_URL, "ne_10m_admin_1.geojson", max_age_hours=24 * 30)
    return read_json(RAW / "ne_10m_admin_1.geojson")


def load_admin0():
    fetch(ADMIN0_URL, "ne_50m_admin_0.geojson", max_age_hours=24 * 30)
    return read_json(RAW / "ne_50m_admin_0.geojson")


def _code(props):
    c = props.get("iso_3166_2") or ""
    return ISO_CODE_FIXES.get(c, c)


def units(system_id, admin1, admin0):
    """[(code, name, geometry)] for a country system's first-level units.

    Membership is by the unit's admin-0 code in Natural Earth's DEFAULT edition, which draws the
    line of actual control. Its country-viewpoint editions each move several borders and no two
    agree, so none of them is used (GLOBAL_GEOGRAPHY.md).
    """
    a3s = set(systems.system(system_id)["admin0_a3"])
    sars = SAR_UNITS.get(system_id, {})
    out = []
    for f in admin1["features"]:
        p = f["properties"]
        if p.get("adm0_a3") in a3s and p.get("adm0_a3") not in sars:
            out.append((_code(p), p.get("name") or _code(p), f["geometry"]))
    for f in admin0["features"]:
        a3 = f["properties"].get("ADM0_A3")
        if a3 in sars:
            code, name = sars[a3]
            out.append((code, name, f["geometry"]))
    return sorted(out, key=lambda u: u[0])


def _bounds(geoms):
    """[w, s, e, n] over several geometries, kept on one side of the antimeridian.

    The Aleutians cross 180°, so a plain min/max gives the US a bounding box spanning the whole
    globe and the map would open zoomed out to the planet. When the span exceeds 180° the
    eastern-hemisphere longitudes are shifted by -360 so the box is contiguous.
    """
    lons, lats = [], []
    for g in geoms:
        for poly in geo._polygons(g):
            for x, y in poly[0]:
                lons.append(x)
                lats.append(y)
    if max(lons) - min(lons) > 180:
        lons = [x - 360 if x > 0 else x for x in lons]
    return [round(min(lons), 2), round(min(lats), 2), round(max(lons), 2), round(max(lats), 2)]


def _region_status(code, rulings):
    for r in rulings:
        if r["code"] == code:
            return r["status"], r["note"]
    return "normal", None


def _event(raw, unit_names):
    ev = {k: raw.get(k) for k in EVENT_FIELDS}
    ev["sources"] = [{k: s.get(k) for k in SOURCE_FIELDS} for s in raw["sources"]]
    ev["recovery"] = {k: (raw.get("recovery") or {}).get(k) for k in RECOVERY_FIELDS}
    ev["region_name"] = unit_names.get(ev["region_code"]) if ev["region_code"] else None
    return ev


def validate(system_id, doc, events, unit_codes):
    """Refuse a system whose curated sources break the rules the UI depends on.

    A build failure here is deliberate: a country shown with an unstated sector, an event in a
    region the map cannot draw, or a vocabulary term with no label would render as a blank or a
    plausible-looking guess, which is the one outcome this project exists to avoid.
    """
    problems = []
    seen = {s["sector"] for s in doc["sectors"]}
    if seen != set(SECTORS):
        problems.append(f"sector states must cover exactly {sorted(SECTORS)}; got {sorted(seen)}")
    for s in doc["sectors"]:
        if s["state"] not in systems.SECTOR_STATES:
            problems.append(f"unknown sector state {s['state']!r}")
        if s["state"] in ("SCORED", "EXPERIMENTAL"):
            # Nothing outside the theatre is computed this iteration. A state claiming a value
            # with no value behind it would be a promise the payload cannot keep.
            problems.append(f"{s['sector']}: {s['state']} needs a computed value; none exists")
        if not s.get("reason"):
            problems.append(f"{s['sector']}: a state with no reason")
        if s.get("assessed_readiness") not in ASSESSMENTS:
            problems.append(f"{s['sector']}: unknown assessment {s.get('assessed_readiness')!r}")
    if doc["reporting_environment"] not in systems.REPORTING_ENVIRONMENTS:
        problems.append(f"unknown reporting environment {doc['reporting_environment']!r}")
    classes = set(ASSET_CLASSES) | set(TAXONOMY_EXTENSIONS["asset_classes"])
    causes = set(DISRUPTION_CAUSES) | set(TAXONOMY_EXTENSIONS["causes"])
    ids_seen = set()
    for e in events:
        eid = e["event_id"]
        if eid in ids_seen:
            problems.append(f"duplicate event id {eid}")
        ids_seen.add(eid)
        if e["asset_class"] not in classes:
            problems.append(f"{eid}: unknown asset class {e['asset_class']!r}")
        if e["cause"] not in causes:
            problems.append(f"{eid}: unknown cause {e['cause']!r}")
        if e["geography_precision"] == "admin1" and e["region_code"] not in unit_codes:
            problems.append(f"{eid}: region {e['region_code']!r} is not a unit of this system")
        if e["geography_precision"] != "admin1" and e["region_code"]:
            problems.append(f"{eid}: a country-level event must not carry a region code")
        if not e["sources"] or not all(s.get("url") for s in e["sources"]):
            problems.append(f"{eid}: every event needs at least one source, each with a URL")
        rs, kind = e["recovery"]["research_status"], e["recovery"]["kind"]
        if rs not in RECOVERY_STATUSES:
            problems.append(f"{eid}: recovery research status must be one of {RECOVERY_STATUSES}")
        if rs == "EVIDENCE_FOUND" and kind not in RECOVERY_KINDS:
            problems.append(f"{eid}: evidence found but its kind {kind!r} is not one of {RECOVERY_KINDS}")
        if rs != "EVIDENCE_FOUND" and kind is not None:
            problems.append(f"{eid}: a recovery kind without evidence")
        if not e.get("review"):
            problems.append(f"{eid}: not reviewed")
    if problems:
        raise ValueError(f"system {system_id}: " + "; ".join(problems))


def onboarding_gate(doc, events, profile):
    """The eight-point gate of GLOBAL_METHODOLOGY §7.2, evaluated rather than asserted.

    The five countries are shown before every item is met, so the payload says which are not:
    a research preview that hides its own gaps would be the overclaim this project exists to
    avoid. Items the code cannot check are stated with the reason they are partial.
    """
    metrics = profile.get("metrics", [])
    no_basis = [m["metric"] for m in metrics if not m.get("basis")]
    rulings_needed = any(r["status"] != "note" for r in doc["geography"].get("rulings", []))

    def item(n, label, status, note):
        return {"item": n, "label": label, "status": status, "note": note}

    return [
        item(1, "Scope statement and disputed-territory ruling", "met",
             "Geography and rulings stated; no aggregate exists, so whether disputed areas count "
             "in one is not yet a live question." if rulings_needed else "Geography stated; no "
             "disputed units."),
        item(2, "Source registry with licence, cadence and reporting environment", "partial",
             "Licences and reporting environment recorded; no refresh cadence, because the event "
             "record is curated by hand rather than fetched."),
        item(3, "Every sector has an explicit state", "met", "Enforced by the build."),
        item(4, "Context statistics carry source, vintage and basis",
             "met" if not no_basis else "partial",
             "All context metrics state a basis." if not no_basis else
             f"{len(no_basis)} of {len(metrics)} context metrics state no basis."),
        item(5, "Threshold declared; every event carries its basis, criterion and episode",
             "partial", "Threshold, inclusion basis and criterion on every event; events are not "
                        "yet grouped into episodes, so one storm can appear as several records."),
        item(6, "Safety tests extended to the country", "met",
             "The served-data gates recurse into every country payload."),
        item(7, "Freshness: last refresh per source, with a stale notice", "partial",
             "The record's review date is published and the page warns once it is older than "
             "the declared limit; there is no per-source refresh date."),
        item(8, "Comparability fields and structural rules", "met",
             "comparability 'none', reporting environment on every count, fixed alphabetical "
             "order, no shared scale."),
    ]


def _readiness(doc):
    """Country-level readiness, derived from sector states rather than declared."""
    states = {s["state"] for s in doc["sectors"]}
    if "SCORED" in states:
        return "INDEX_READY"
    if "EXPERIMENTAL" in states:
        return "EXPERIMENTAL"
    if "CONTEXT_ONLY" in states:
        return "CONTEXT_ONLY"
    return "INSUFFICIENT_EVIDENCE"


def build_system(system_id, admin1, admin0, as_of):
    src = SYSTEMS_CURATED / system_id
    doc = read_json(src / "system.json")
    profile = read_json(src / "profile.json")
    raw_events = read_json(src / "events.json")["events"]
    reg = systems.system(system_id)

    us = units(system_id, admin1, admin0)
    unit_codes = {u[0] for u in us}
    unit_names = {u[0]: u[1] for u in us}
    if doc["geography"]["units_expected"] != len(us):
        raise ValueError(f"system {system_id}: expected {doc['geography']['units_expected']} "
                         f"first-level units, Natural Earth gave {len(us)}")
    events = sorted((_event(r, unit_names) for r in raw_events),
                    key=lambda e: (e["date"], e["event_id"]))
    validate(system_id, doc, events, unit_codes)
    # An event dated after TODAY is a curation error and fails the build. An event dated after
    # the build's --as-of is not: a historical rebuild (the frozen 2026-08-28 regression) must
    # reconstruct the record as of that date, the way the theatre does, rather than refuse to
    # run because the corpus has grown since (iteration 14 found the refusal).
    today = dt.date.today().isoformat()
    future = [e["event_id"] for e in events if e["date"] > max(as_of, today)]
    if future:
        raise ValueError(f"system {system_id}: events dated in the future: {future}")
    later = sum(1 for e in events if e["date"] > as_of)
    events = [e for e in events if e["date"] <= as_of]

    counts = {}
    for e in events:
        if e["geography_precision"] == "admin1":
            counts[e["region_code"]] = counts.get(e["region_code"], 0) + 1

    tol = REGION_TOLERANCE.get(system_id, DEFAULT_TOLERANCE)
    features, kept = [], []
    for code, name, g in us:
        s = geo.simplify_geometry(g, tol)
        if s is None:
            raise ValueError(f"system {system_id}: unit {code} vanished on simplification")
        status, note = _region_status(code, doc["geography"].get("rulings", []))
        kept.append(s)
        features.append({
            "type": "Feature",
            "properties": {"code": code, "name": name, "status": status, "note": note,
                           # A disputed, unassigned unit never carries an event count: an
                           # absence there is "not applicable", not "nothing happened".
                           "recorded_events": None if status == "disputed_unassigned"
                           else counts.get(code, 0)},
            "geometry": geo.round_coords(s, 3),
        })

    used_classes = sorted({e["asset_class"] for e in events})
    used_causes = sorted({e["cause"] for e in events})
    labels = {**ASSET_CLASSES, **TAXONOMY_EXTENSIONS["asset_classes"]}
    cause_labels = {**DISRUPTION_CAUSES, **TAXONOMY_EXTENSIONS["causes"]}
    recovery_counts = {k: sum(1 for e in events if e["recovery"]["research_status"] == k)
                       for k in RECOVERY_STATUSES}
    kind_counts = {k: sum(1 for e in events if e["recovery"]["kind"] == k) for k in RECOVERY_KINDS}
    reviewed = max((e["review"]["reviewed"] for e in events), default=None)

    payload = {
        "system_id": system_id,
        "name": reg["name"],
        "kind": reg["kind"],
        "as_of": as_of,
        "evidence_readiness": _readiness(doc),
        # No composite exists for any country system. null, never 0: zero would claim
        # "measured, nothing wrong".
        "index": None,
        "headline": None,
        "no_index_reason": (
            "No index is published for this country. The Monitored-Area ESDI's sector weights, "
            "decay horizons and transmission measure were built for a strike campaign and do not "
            "transfer (GLOBAL_METHODOLOGY.md §1-§3). This view shows reported major disruptions "
            "and energy-system context instead."),
        "sectors": [{**s, "label": SECTORS[s["sector"]]} for s in doc["sectors"]],
        "reporting_environment": doc["reporting_environment"],
        "reporting_environment_text": systems.REPORTING_ENVIRONMENTS[doc["reporting_environment"]],
        "reporting_note": doc["reporting_note"],
        "comparability": "none",
        "comparability_statement": COMPARABILITY_STATEMENT,
        "geography": {**doc["geography"], "source": "Natural Earth 1:10m admin-1 (default edition)",
                      "bounds": _bounds(kept),
                      # Where the map opens. Defaults to the full extent; a curated override
                      # exists for the US, whose full extent (the Aleutians to Florida) leaves
                      # the lower 48 a small corner of the frame. Nothing outside it is hidden.
                      "view_bounds": doc["geography"].get("view_bounds") or _bounds(kept)},
        "event_summary": {
            "recorded_events": len(events),
            "placed_in_a_region": sum(1 for e in events if e["geography_precision"] == "admin1"),
            "country_level": sum(1 for e in events if e["geography_precision"] != "admin1"),
            "recovery_research": recovery_counts,
            "recovery_kinds": kind_counts,
            "excluded_after_as_of": later,
            "first_date": events[0]["date"] if events else None,
            "last_date": events[-1]["date"] if events else None,
            "note": "Counts what was reported and found, not what occurred.",
        },
        "inclusion_threshold": read_json(SYSTEMS_CURATED / "inclusion_threshold.json"),
        "taxonomy": {"asset_classes": {k: labels[k] for k in used_classes},
                     "causes": {k: cause_labels[k] for k in used_causes}},
        "profile": profile,
        "sources": doc["sources"],
        "research_gaps": doc["research_gaps"],
        # The build runs daily; the event record does not. Separate dates, so "as of" never
        # implies the corpus was re-checked today (iteration-14 red team).
        "record_reviewed": reviewed,
        "review_freshness_days": doc.get("review_freshness_days", 120),
        "onboarding_gate": onboarding_gate(doc, events, profile),
        "audit_docs": doc["audit_docs"],
    }
    out = PROCESSED / systems.root(system_id)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "system.json", payload)
    write_json(out / "events.json", {"system_id": system_id, "as_of": as_of, "events": events})
    write_json(out / "regions.geojson", {"type": "FeatureCollection", "features": features})
    log(f"system {system_id}: {len(events)} events, {len(features)} units, "
        f"readiness {payload['evidence_readiness']}")
    return payload


def build_world(admin1, admin0):
    """A light admin-0 world for the global home.

    Russia is drawn from its admin-1 units, not from Natural Earth's admin-0 polygon, because
    that polygon contains Crimea. Crimea and Sevastopol are emitted as their own features with
    sovereignty Ukraine and status occupied — the same rule the theatre map follows. Painting
    the Russian admin-0 polygon would quietly label Crimea Russian on the first screen a reader
    sees.
    """
    owner = {a3: s["id"] for s in systems.SYSTEMS for a3 in s["admin0_a3"]}
    # Only the theatre's own regions are "monitored": the Far Eastern district is drawn as Russia
    # but is not in the area of interest, and the home map must not claim otherwise.
    theatre_names = {r["natural_earth_name"] for r in read_json(PROCESSED / "regions.json")
                     if r.get("country") == "RU"}
    # Natural Earth's own disputed units at admin-0 (Siachen) are drawn as disputed, never as
    # anyone's.
    disputed_a3 = {"KAS"}
    feats = []
    for f in admin0["features"]:
        p = f["properties"]
        a3 = p.get("ADM0_A3")
        if a3 == "RUS":
            continue
        g = geo.simplify_geometry(f["geometry"], WORLD_TOLERANCE)
        if g is None:
            continue   # specks below a dashboard pixel at world zoom
        feats.append({"type": "Feature",
                      "properties": {"a3": a3, "name": p.get("NAME"),
                                     "system_id": None if a3 in disputed_a3 else owner.get(a3),
                                     "status": "disputed" if a3 in disputed_a3 else "normal"},
                      "geometry": geo.round_coords(g, 2)})
    for f in admin1["features"]:
        p = f["properties"]
        if p.get("adm0_a3") != "RUS":
            continue
        crimea = p.get("iso_3166_2") in ("UA-43", "UA-40")
        g = geo.simplify_geometry(f["geometry"], WORLD_TOLERANCE)
        if g is None:
            continue
        feats.append({"type": "Feature",
                      "properties": {
                          "a3": "UKR" if crimea else "RUS",
                          "name": p.get("name") if crimea else "Russia",
                          "system_id": "ru" if (crimea or p.get("name") in theatre_names) else None,
                          "status": "occupied" if crimea else "normal",
                          "note": ("Internationally recognised as Ukraine; occupied by Russia. "
                                   "Monitored as a separate unit within the theatre.")
                          if crimea else None},
                      "geometry": geo.round_coords(g, 2)})
    return {"type": "FeatureCollection", "features": feats}


def build_manifest(country_payloads, theatre_snapshot, build_time):
    entries = []
    for s in systems.SYSTEMS:
        if s["id"] == systems.THEATRE:
            entries.append({
                "id": s["id"], "name": s["name"], "kind": s["kind"], "root": systems.root(s["id"]),
                "evidence_readiness": "INDEX_READY",
                "index": {"id": "esdi", "name": "Monitored-Area ESDI"},
                "headline": {"value": theatre_snapshot["esdi"], "as_of": theatre_snapshot["as_of"],
                             "label": "Monitored-Area ESDI",
                             "meaning": "Capacity at disrupted sites, not measured loss."},
                "reporting_environment": "conflict_restricted",
                "as_of": theatre_snapshot["as_of"],
                "files": ["snapshot.json"],
            })
            continue
        p = country_payloads[s["id"]]
        entries.append({
            "id": s["id"], "name": s["name"], "kind": s["kind"], "root": systems.root(s["id"]),
            "evidence_readiness": p["evidence_readiness"], "index": None, "headline": None,
            "reporting_environment": p["reporting_environment"],
            "as_of": p["as_of"],
            "bounds": p["geography"]["bounds"],
            "files": ["system.json", "events.json", "regions.geojson"],
        })
    return {
        "schema_version": 1,
        "build_time": build_time,
        # Rule, source and caveat only. The production values stay in the registry and the
        # selection document: a descending list of country figures in the manifest is a ranking.
        "selection": {k: v for k, v in systems.SELECTION.items() if k != "values"},
        "comparability_statement": COMPARABILITY_STATEMENT,
        "reporting_environments": systems.REPORTING_ENVIRONMENTS,
        # Fixed, alphabetical order from the registry. Never sorted by any figure.
        "order": "alphabetical by name; never by any figure",
        "systems": entries,
    }


def build(theatre_snapshot):
    as_of = theatre_snapshot["as_of"]
    admin1, admin0 = load_admin1(), load_admin0()
    payloads = {sid: build_system(sid, admin1, admin0, as_of) for sid in systems.COUNTRY_SYSTEMS}
    (PROCESSED / "global").mkdir(parents=True, exist_ok=True)
    write_json(PROCESSED / "global" / "world.geojson", build_world(admin1, admin0))
    build_time = theatre_snapshot.get("build_time") or dt.datetime.now(dt.timezone.utc).isoformat()
    write_json(PROCESSED / "global" / "manifest.json",
               build_manifest(payloads, theatre_snapshot, build_time), indent=2)
    return payloads
