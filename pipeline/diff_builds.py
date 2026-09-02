"""Build-to-build change ledger (iteration 11 §7-§10).

THE PROBLEM THIS SOLVES. The index moves between builds for reasons that are not alike, and the
dashboard has until now shown only the movement. A reader watching ESDI fall from 18.5 to 17.3
cannot tell whether refineries were repaired, whether a source was corrected, whether an event
was withdrawn, or whether nothing at all happened in the world and modelled impairment simply
aged. Those are four different facts and only one of them is news.

So every change carries a `nature`:

    world       something happened: a new strike, an observed restoration
    data        the record changed, the world did not: a correction, a new source, a revision
    decay       nothing changed; elapsed time reduced modelled impairment
    methodology we changed how we measure: weights, saturation constant, denominators

A build whose entire delta is `decay` must be able to say so in those words. "Nothing new was
reported; the index fell because impairment ages" is the single most common honest summary of a
quiet day, and it is exactly the one a naive delta cannot produce.

HOW THE INDEX DELTA IS ATTRIBUTED, AND WHERE THAT STOPS BEING EXACT. Both builds emit a
decomposition that reconciles to their published index exactly, so the per-sector index-point
deltas sum to the headline delta exactly. That much is arithmetic, not inference.

Below the sector it is not exact, and the ledger says so rather than presenting a tidy
attribution it cannot support:

  - A sector at its 100% cap absorbs facility changes without moving.
  - A changed denominator re-scales every facility in that sector at once, so a facility's
    delta is not "what happened to that facility".
  - A methodology change moves everything simultaneously.

In those cases `attribution_exact` is false and `non_additive_reason` states which one applies.
The facility-level figures are still shown, because they are the best available account of where
the movement sits — but they are labelled as an account, not a decomposition.

THE PREVIOUS BUILD comes from `web/public/data/`, which still holds the last build's payload
until the mirror overwrites it. No new persisted history, nothing to keep in sync, and the diff
is reproducible from two artefacts that already exist.
"""

import json


# The categories the ledger can report. Keeping them in one closed list means a new kind of
# change is a deliberate addition rather than an unlabelled row appearing in the UI.
CATEGORIES = {
    "incident_added": "world",
    "incident_removed": "data",
    "incident_revised": "data",
    "source_added": "data",
    "recovery_evidence_added": "world",
    "recovery_status_changed": "world",
    "asset_added": "data",
    "asset_capacity_revised": "data",
    "denominator_changed": "methodology",
    "methodology_changed": "methodology",
    "coverage_changed": "data",
}

NATURES = ("world", "data", "decay", "methodology")


def _r(x, n=2):
    return round(x + 0.0, n)


def _by_id(rows, key):
    return {r[key]: r for r in rows if r.get(key)}


# Fields whose change is a substantive revision of what we assert about an event. Deliberately
# not every field: a re-ordered source list or a regenerated note is not a revision, and a ledger
# that reported those would bury the real ones.
INCIDENT_TRACKED = (
    "date", "date_start", "date_end", "date_precision", "cause", "attribution",
    "attribution_confidence", "confidence", "status", "asset_id", "region_code",
    "capacity_affected_mw", "capacity_affected_mtpa", "capacity_affected_pct",
    "conflicting_reports",
)


def _incident_changes(prev, curr):
    out = []
    p = _by_id(prev, "incident_id")
    c = _by_id(curr, "incident_id")

    for iid in sorted(set(c) - set(p)):
        i = c[iid]
        out.append({
            "category": "incident_added",
            "nature": "world",
            "id": iid,
            "asset_id": i.get("asset_id"),
            "label": f"{i.get('asset_name') or i.get('asset_id')} — {i.get('cause')}",
            "date": i.get("date"),
            "detail": f"new event dated {i.get('date')}, confidence {i.get('confidence')}",
            "sources": len(i.get("sources") or []),
        })

    for iid in sorted(set(p) - set(c)):
        i = p[iid]
        out.append({
            "category": "incident_removed",
            "nature": "data",
            "id": iid,
            "asset_id": i.get("asset_id"),
            "label": f"{i.get('asset_name') or i.get('asset_id')} — {i.get('cause')}",
            "date": i.get("date"),
            # A withdrawal is a statement about the record, never about the world. An event that
            # leaves the dataset was not un-happened; we stopped asserting it.
            "detail": "event no longer asserted by the dataset",
            "sources": len(i.get("sources") or []),
        })

    for iid in sorted(set(p) & set(c)):
        a, b = p[iid], c[iid]
        fields = [f for f in INCIDENT_TRACKED if a.get(f) != b.get(f)]
        if fields:
            out.append({
                "category": "incident_revised",
                "nature": "data",
                "id": iid,
                "asset_id": b.get("asset_id"),
                "label": f"{b.get('asset_name') or b.get('asset_id')} — {b.get('cause')}",
                "date": b.get("date"),
                "detail": "; ".join(
                    f"{f}: {a.get(f)!r} -> {b.get(f)!r}" for f in fields),
                "fields": fields,
            })
        old_urls = {s.get("url") for s in (a.get("sources") or [])}
        new_urls = [s for s in (b.get("sources") or []) if s.get("url") not in old_urls]
        if new_urls:
            out.append({
                "category": "source_added",
                "nature": "data",
                "id": iid,
                "asset_id": b.get("asset_id"),
                "label": f"{b.get('asset_name') or b.get('asset_id')}",
                "date": b.get("date"),
                "detail": f"{len(new_urls)} new source(s): " +
                          ", ".join(s.get("url", "") for s in new_urls[:3]),
                "urls": [s.get("url") for s in new_urls],
            })
    return out


def _recovery_changes(prev_snap, curr_snap):
    """Recovery movement, read from the live-disruption records rather than from the index.

    A status moving from `impaired` to `substantially_restored` is a WORLD change — someone
    observed a restart. That is categorically different from the same facility's contribution
    shrinking because 90 days elapsed, which is `decay` and appears nowhere in this function.
    """
    out = []
    p = {d["asset_id"]: d for d in (prev_snap.get("live_disruptions") or [])}
    c = {d["asset_id"]: d for d in (curr_snap.get("live_disruptions") or [])}
    for aid in sorted(set(p) & set(c)):
        pr = (p[aid].get("recovery") or {})
        cr = (c[aid].get("recovery") or {})
        if pr.get("recovery_status") != cr.get("recovery_status"):
            out.append({
                "category": "recovery_status_changed",
                "nature": "world",
                "id": aid,
                "asset_id": aid,
                "label": c[aid].get("name") or aid,
                "date": cr.get("as_of") or c[aid].get("latest"),
                "detail": f"{pr.get('recovery_status')} -> {cr.get('recovery_status')}"
                          f" ({cr.get('scoring_evidence_kind') or 'evidence kind unstated'})",
            })
        elif pr.get("scoring_evidence_kind") != cr.get("scoring_evidence_kind"):
            # Same status, better evidence for it. Worth reporting: an estimate becoming an
            # observation changes how much the reader should trust the same number.
            out.append({
                "category": "recovery_evidence_added",
                "nature": "world",
                "id": aid,
                "asset_id": aid,
                "label": c[aid].get("name") or aid,
                "date": cr.get("as_of") or c[aid].get("latest"),
                "detail": f"evidence {pr.get('scoring_evidence_kind')} -> "
                          f"{cr.get('scoring_evidence_kind')}",
            })
    return out


def _asset_changes(prev, curr):
    out = []
    p = _by_id(prev, "asset_id")
    c = _by_id(curr, "asset_id")
    for aid in sorted(set(c) - set(p)):
        a = c[aid]
        out.append({
            "category": "asset_added", "nature": "data", "id": aid, "asset_id": aid,
            "label": a.get("name") or aid, "date": None,
            "detail": f"{a.get('asset_class')} added to the inventory",
        })
    for aid in sorted(set(p) & set(c)):
        a, b = p[aid], c[aid]
        moved = [f for f in ("capacity_mw", "capacity_mtpa", "capacity_bcm_y")
                 if a.get(f) != b.get(f)]
        if moved:
            out.append({
                "category": "asset_capacity_revised", "nature": "data", "id": aid,
                "asset_id": aid, "label": b.get("name") or aid, "date": None,
                "detail": "; ".join(f"{f}: {a.get(f)} -> {b.get(f)}" for f in moved),
            })
    return out


def _denominator_changes(prev_snap, curr_snap):
    out = []
    pd = prev_snap.get("denominators") or {}
    cd = curr_snap.get("denominators") or {}
    for k in sorted(set(pd) | set(cd)):
        if pd.get(k) != cd.get(k):
            out.append({
                "category": "denominator_changed", "nature": "methodology", "id": k,
                "asset_id": None, "label": k, "date": None,
                "detail": f"{pd.get(k)} -> {cd.get(k)}",
                # A denominator move re-scales every facility in that sector simultaneously.
                # Nothing below the sector can be attributed to a single facility afterwards.
                "rescales_sector": True,
            })
    return out


def _coverage_changes(prev_snap, curr_snap):
    pc = prev_snap.get("coverage") or {}
    cc = curr_snap.get("coverage") or {}
    if not pc or not cc:
        return []
    fields = ("enumerated_in_this_dataset", "reported_total_strikes", "total_events_all_sectors")
    moved = [f for f in fields if pc.get(f) != cc.get(f)]
    if not moved:
        return []
    return [{
        "category": "coverage_changed", "nature": "data", "id": "coverage",
        "asset_id": None, "label": "Benchmark coverage", "date": None,
        "detail": "; ".join(f"{f}: {pc.get(f)} -> {cc.get(f)}" for f in moved),
    }]


def _methodology_changes(prev_snap, curr_snap):
    """Weights and the saturation constant, read from what each build published about itself."""
    out = []
    pw = (prev_snap.get("explanations") or {}).get("headline", {}).get("nominal_weights") or {}
    cw = (curr_snap.get("explanations") or {}).get("headline", {}).get("nominal_weights") or {}
    for s in sorted(set(pw) | set(cw)):
        if pw.get(s) != cw.get(s):
            out.append({
                "category": "methodology_changed", "nature": "methodology", "id": f"weight:{s}",
                "asset_id": None, "label": f"{s} weight", "date": None,
                "detail": f"{pw.get(s)} -> {cw.get(s)}", "rescales_sector": True,
            })
    ps = (prev_snap.get("transmission_sensitivity") or {}).get("saturation_constant")
    cs = (curr_snap.get("transmission_sensitivity") or {}).get("saturation_constant")
    if ps != cs and (ps is not None or cs is not None):
        out.append({
            "category": "methodology_changed", "nature": "methodology",
            "id": "transmission_saturation", "asset_id": None,
            "label": "Transmission saturation constant", "date": None,
            "detail": f"{ps} -> {cs}", "rescales_sector": True,
        })
    return out


def _sector_attribution(prev_snap, curr_snap, rescaled_sectors):
    """Per-sector index-point deltas, which sum to the headline delta exactly.

    This is the only layer of the attribution that is arithmetic rather than inference, and it is
    exact because both builds' decompositions reconcile to their own published index.
    """
    pe = (prev_snap.get("explanations") or {}).get("headline")
    ce = (curr_snap.get("explanations") or {}).get("headline")
    if not pe or not ce:
        return None

    pc = {c["sector"]: c for c in pe["contributions"]}
    cc = {c["sector"]: c for c in ce["contributions"]}
    rows = []
    for s in sorted(set(pc) | set(cc), key=lambda x: -abs(
            (cc.get(x, {}).get("index_points", 0.0)) - (pc.get(x, {}).get("index_points", 0.0)))):
        before = pc.get(s, {}).get("index_points", 0.0)
        after = cc.get(s, {}).get("index_points", 0.0)
        if before == 0.0 and after == 0.0:
            continue
        rows.append({
            "sector": s,
            "index_points_before": _r(before),
            "index_points_after": _r(after),
            "delta": _r(after - before),
            "sector_value_before": _r(pc.get(s, {}).get("sector_value", 0.0)),
            "sector_value_after": _r(cc.get(s, {}).get("sector_value", 0.0)),
            "weight_changed": pc.get(s, {}).get("effective_weight") != cc.get(s, {}).get("effective_weight"),
            "rescaled": s in rescaled_sectors,
        })

    total = _r(sum(r["delta"] for r in rows))
    headline = _r(ce["value"] - pe["value"])
    return {
        "rows": rows,
        "sum_of_sector_deltas": total,
        "headline_delta": headline,
        # Rounding can leave a hundredth between the two; anything larger means the sector rows
        # are not the whole story and the reader should be told rather than shown a clean sum.
        "exact": abs(total - headline) <= 0.02,
    }


def _facility_attribution(prev_snap, curr_snap, rescaled_sectors):
    """Where inside each sector the movement sits — an account, not a decomposition.

    Facility deltas do not have to sum to the sector delta: a capped sector absorbs them, a
    changed denominator re-scales them all, and a weight change moves the sector without any
    facility moving at all. Each row therefore carries whether its sector's arithmetic was exact.
    """
    ps = (prev_snap.get("explanations") or {}).get("sectors") or {}
    cs = (curr_snap.get("explanations") or {}).get("sectors") or {}
    rows = []
    for sector in sorted(set(ps) | set(cs)):
        pf = {f["asset_id"]: f for f in (ps.get(sector, {}).get("contributing") or [])}
        cf = {f["asset_id"]: f for f in (cs.get(sector, {}).get("contributing") or [])}
        capped = (cs.get(sector, {}).get("value") or 0) >= 100.0
        for aid in set(pf) | set(cf):
            before = pf.get(aid, {}).get("sector_points", 0.0)
            after = cf.get(aid, {}).get("sector_points", 0.0)
            if abs(after - before) < 0.005:
                continue
            src = cf.get(aid) or pf.get(aid)
            reason = ("sector denominator or weight changed; this facility's movement is not "
                      "its own" if sector in rescaled_sectors else
                      "sector is at its 100% cap; facility movement may not reach the index"
                      if capped else None)
            rows.append({
                "sector": sector,
                "asset_id": aid,
                "name": src.get("name"),
                "sector_points_before": _r(before, 3),
                "sector_points_after": _r(after, 3),
                "delta": _r(after - before, 3),
                "entered": aid not in pf,
                "left": aid not in cf,
                "attribution_exact": reason is None,
                "non_additive_reason": reason,
            })
    rows.sort(key=lambda r: -abs(r["delta"]))
    return rows


def diff(prev_snap, curr_snap, prev_incidents, curr_incidents, prev_assets, curr_assets):
    """Compare two builds. Pure: takes parsed payloads, returns the ledger."""
    changes = []
    changes += _incident_changes(prev_incidents, curr_incidents)
    changes += _recovery_changes(prev_snap, curr_snap)
    changes += _asset_changes(prev_assets, curr_assets)
    denominator = _denominator_changes(prev_snap, curr_snap)
    methodology = _methodology_changes(prev_snap, curr_snap)
    changes += denominator + methodology
    changes += _coverage_changes(prev_snap, curr_snap)

    for c in changes:
        assert c["category"] in CATEGORIES, c["category"]
        assert c["nature"] in NATURES, c["nature"]

    # Sectors whose internal arithmetic was re-scaled by something above the facility level.
    rescaled = set()
    for c in denominator:
        for s in ("refining", "oil_logistics", "electric_generation", "transmission"):
            if s in c["id"] or c["id"].startswith(s):
                rescaled.add(s)
    for c in methodology:
        if c["id"].startswith("weight:"):
            rescaled.add(c["id"].split(":", 1)[1])
        if c["id"] == "transmission_saturation":
            rescaled.add("transmission")

    by_nature = {n: sum(1 for c in changes if c["nature"] == n) for n in NATURES}
    by_category = {}
    for c in changes:
        by_category[c["category"]] = by_category.get(c["category"], 0) + 1

    prev_esdi = prev_snap.get("esdi")
    curr_esdi = curr_snap.get("esdi")
    delta = None if prev_esdi is None or curr_esdi is None else _r(curr_esdi - prev_esdi)

    # The quiet-day case, and the whole reason this file exists. No substantive change of any
    # kind, but the index still moved — that movement is elapsed time, and saying anything else
    # would be reporting a world event that did not occur.
    substantive = [c for c in changes if c["nature"] in ("world", "data", "methodology")]
    decay_only = not substantive and delta is not None and delta != 0

    # Which way the evaluation date moved. Normally forward, but a current-date build compared
    # against a frozen historical one runs backwards, and then decay makes the index RISE. A
    # ledger that said "the index moved because impairment decays" beside a rise would read as
    # nonsense, so the direction is stated rather than assumed.
    pa, ca = prev_snap.get("as_of"), curr_snap.get("as_of")
    direction = ("forward" if pa and ca and ca > pa
                 else "backward" if pa and ca and ca < pa
                 else "same_date")

    return {
        "previous_build": prev_snap.get("build_time"),
        "previous_as_of": prev_snap.get("as_of"),
        "current_build": curr_snap.get("build_time"),
        "current_as_of": curr_snap.get("as_of"),
        "esdi_before": prev_esdi,
        "esdi_after": curr_esdi,
        "esdi_delta": delta,
        "decay_only": decay_only,
        "as_of_direction": direction,
        "decay_only_note": (
            None if not decay_only else
            "Nothing new was reported, corrected or withdrawn between these builds. The index "
            "moved because modelled impairment decays with elapsed time. This is NOT evidence "
            "that anything was repaired." if direction == "forward" else
            "Nothing new was reported, corrected or withdrawn. This build is evaluated at an "
            "EARLIER date than the one it is compared against, so the index is higher simply "
            "because less time had elapsed for impairment to decay. Nothing worsened."
            if direction == "backward" else
            "Nothing new was reported, corrected or withdrawn, and both builds are evaluated at "
            "the same date. The remaining movement is unexplained by this ledger."),
        "change_count": len(changes),
        "by_nature": by_nature,
        "by_category": by_category,
        "changes": changes,
        "sector_attribution": _sector_attribution(prev_snap, curr_snap, rescaled),
        "facility_attribution": _facility_attribution(prev_snap, curr_snap, rescaled),
        "rescaled_sectors": sorted(rescaled),
        "attribution_note": (
            "Per-sector index-point deltas sum to the headline delta exactly — that is "
            "arithmetic. Facility-level figures are an account of where the movement sits, not "
            "a decomposition: a capped sector, a changed denominator or a changed weight all "
            "move the index without any single facility being responsible."
        ),
    }


def empty(curr_snap, reason):
    """The first-build case. Reporting zero changes would claim a quiet day that never happened."""
    return {
        "previous_build": None, "previous_as_of": None,
        "current_build": curr_snap.get("build_time"), "current_as_of": curr_snap.get("as_of"),
        "esdi_before": None, "esdi_after": curr_snap.get("esdi"), "esdi_delta": None,
        "decay_only": False, "decay_only_note": None,
        "change_count": 0, "by_nature": {n: 0 for n in NATURES}, "by_category": {},
        "changes": [], "sector_attribution": None, "facility_attribution": [],
        "rescaled_sectors": [],
        "unavailable_reason": reason,
        "attribution_note": None,
    }


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def from_directory(prev_dir, curr_snap, curr_incidents, curr_assets):
    """Diff the current build against whatever payload `prev_dir` still holds.

    Called before the mirror overwrites it, so `prev_dir` is the previous build — no new
    persisted history, and both sides are artefacts that already exist.
    """
    prev_snap = _load(prev_dir / "snapshot.json", None)
    if not prev_snap:
        return empty(curr_snap, "no previous build payload found")
    if not prev_snap.get("explanations"):
        # A pre-iteration-11 payload can still be diffed for events and recovery, but its index
        # cannot be decomposed, so the attribution sections are honestly absent.
        pass
    return diff(
        prev_snap, curr_snap,
        _load(prev_dir / "incidents.json", []), curr_incidents,
        _load(prev_dir / "assets.json", []), curr_assets,
    )
