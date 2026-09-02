"""Build-to-build change ledger (iteration 11 §7-§10, addendum §2-§7).

THE PROBLEM THIS SOLVES. The index moves between builds for reasons that are not alike, and the
dashboard has until now shown only the movement. A reader watching ESDI fall from 18.5 to 17.3
cannot tell whether refineries were repaired, whether a source was corrected, whether an event
was withdrawn, or whether nothing at all happened in the world and modelled impairment simply
aged. Those are four different facts and only one of them is news.

FOUR NATURES:

    world             something happened in the world and was reported
    data              the record changed, the world did not — a correction, a withdrawal, a
                      historical event or a historical restoration added by later research
    time_progression  no input changed; only the evaluation date moved
    methodology       we changed how we measure

`time_progression` rather than `decay` on purpose. Decay names a direction, and a comparison run
backwards — a current build against an earlier-dated one — makes the same mechanism raise the
index. Direction lives in `as_of_direction`, which the production path requires to be forward.

EFFECTIVE DATE IS NOT DISCOVERY DATE (addendum §7). A strike that happened yesterday and was
reported today is world news. The same strike from four months ago, added today because research
found it, is a change to the record — the world did not change, our account of it did. The cut is
principled rather than a tuned constant: an event dated at or after the PREVIOUS build's as_of
happened since we last looked; anything earlier predates our last look and we simply did not have
it. The same rule applies to recovery evidence, so "evidence arrived this build" is never
rendered as "restored this build".

WHERE THE BASELINE COMES FROM. `pipeline/lineage.py` — an immutable commit, never the mutable
worktree. See that module for why.

HOW THE INDEX DELTA IS ATTRIBUTED, AND WHERE THAT STOPS BEING EXACT. Both builds emit a
decomposition that reconciles to their published index exactly, so the per-sector index-point
deltas sum to the headline delta exactly. That much is arithmetic, not inference.

Below the sector it is not exact, and the ledger says so rather than presenting a tidy
attribution it cannot support: a capped sector absorbs facility changes, a changed denominator
re-scales every facility at once, and a methodology change moves everything simultaneously.

METHODOLOGY CHANGES ARE NOT DECOMPOSABLE HERE (addendum §5). Separating a methodology change from
a data change would need a four-corner replay — old data under old methodology, new data under
old methodology, and so on — which requires executing the previous build's scoring code
deterministically. This pipeline cannot do that. So when the methodology fingerprint moves, the
ledger sets `attribution_separable = false` and says the movement is not separable, rather than
manufacturing an exact split it has no basis for.
"""

import json

from pipeline import build_manifest

# The categories the ledger can report, and the nature each defaults to. Keeping them in one
# closed list means a new kind of change is a deliberate addition rather than an unlabelled row
# appearing in the UI. Some categories are re-natured per row (see EFFECTIVE DATE above).
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
    # Fingerprint-derived: these catch changes the emitted payloads cannot reveal on their own.
    "asset_inventory_changed": "data",
    "denominator_inputs_changed": "methodology",
    "source_refresh": "data",
    "pipeline_registry_changed": "data",
    "recovery_corpus_changed": "data",
    "incident_corpus_changed": "data",
}

NATURES = ("world", "data", "time_progression", "methodology")

# How a row relates to the world's timeline versus the record's.
RECORD_CLASSES = (
    "current_event",              # happened since the last build
    "historical_record_added",    # predates the last build; research found it
    "historical_evidence_added",  # evidence arriving now about an older restoration
    "correction",                 # what we assert changed
    "withdrawal",                 # we stopped asserting it
    "input_change",               # an input fingerprint moved
)

# Fingerprint group -> the category its movement is reported as.
GROUP_CATEGORY = {
    "incident_corpus": "incident_corpus_changed",
    "recovery_corpus": "recovery_corpus_changed",
    "asset_inventory": "asset_inventory_changed",
    "denominator_inputs": "denominator_inputs_changed",
    "methodology": "methodology_changed",
    "pipeline_registry": "pipeline_registry_changed",
    "source_snapshots": "source_refresh",
}


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


def _is_new_in_world(effective_date, previous_as_of):
    """Did this happen since we last looked?

    No tuned window: the previous build's as_of IS the last moment we had a view of the world.
    Anything dated at or after it is new; anything earlier is a gap in the record we have just
    filled. When we cannot tell, the answer is no — claiming a world event needs positive
    evidence, and the failure mode of guessing wrong is announcing something that did not happen.
    """
    if not effective_date or not previous_as_of:
        return False
    return effective_date >= previous_as_of


def _incident_changes(prev, curr, previous_as_of):
    out = []
    p = _by_id(prev, "incident_id")
    c = _by_id(curr, "incident_id")

    for iid in sorted(set(c) - set(p)):
        i = c[iid]
        date = i.get("date")
        current = _is_new_in_world(date, previous_as_of)
        out.append({
            "category": "incident_added",
            "nature": "world" if current else "data",
            "record_class": "current_event" if current else "historical_record_added",
            "id": iid,
            "asset_id": i.get("asset_id"),
            "label": f"{i.get('asset_name') or i.get('asset_id')} — {i.get('cause')}",
            "effective_date": date,
            "first_seen_as_of": None,   # filled in by diff(), which knows the build's own as_of
            "date": date,
            "detail": (
                f"new event dated {date}, confidence {i.get('confidence')}" if current else
                f"event dated {date} added to the record now; it predates the previous build "
                f"({previous_as_of}), so this is research catching up, not a new occurrence"),
            "sources": len(i.get("sources") or []),
        })

    for iid in sorted(set(p) - set(c)):
        i = p[iid]
        out.append({
            "category": "incident_removed",
            "nature": "data",
            "record_class": "withdrawal",
            "id": iid,
            "asset_id": i.get("asset_id"),
            "label": f"{i.get('asset_name') or i.get('asset_id')} — {i.get('cause')}",
            "effective_date": i.get("date"),
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
                "record_class": "correction",
                "id": iid,
                "asset_id": b.get("asset_id"),
                "label": f"{b.get('asset_name') or b.get('asset_id')} — {b.get('cause')}",
                "effective_date": b.get("date"),
                "date": b.get("date"),
                "detail": "; ".join(f"{f}: {a.get(f)!r} -> {b.get(f)!r}" for f in fields),
                "fields": fields,
            })
        old_urls = {s.get("url") for s in (a.get("sources") or [])}
        new_urls = [s for s in (b.get("sources") or []) if s.get("url") not in old_urls]
        if new_urls:
            out.append({
                "category": "source_added",
                "nature": "data",
                "record_class": "correction",
                "id": iid,
                "asset_id": b.get("asset_id"),
                "label": f"{b.get('asset_name') or b.get('asset_id')}",
                "effective_date": b.get("date"),
                "date": b.get("date"),
                "detail": f"{len(new_urls)} new source(s): " +
                          ", ".join(s.get("url", "") for s in new_urls[:3]),
                "urls": [s.get("url") for s in new_urls],
            })
    return out


def _recovery_changes(prev_snap, curr_snap, previous_as_of):
    """Recovery movement, read from the live-disruption records rather than from the index.

    A status moving to `substantially_restored` because someone observed a restart TODAY is a
    world change. The same status arriving today on evidence about a restart three months ago is
    a change to the record. Labelling the second as world would tell a reader a plant came back
    this week when it came back in the spring.
    """
    out = []
    p = {d["asset_id"]: d for d in (prev_snap.get("live_disruptions") or [])}
    c = {d["asset_id"]: d for d in (curr_snap.get("live_disruptions") or [])}
    for aid in sorted(set(p) & set(c)):
        pr = (p[aid].get("recovery") or {})
        cr = (c[aid].get("recovery") or {})
        effective = cr.get("as_of") or cr.get("observed_date") or c[aid].get("latest")
        current = _is_new_in_world(effective, previous_as_of)
        base = {
            "id": aid,
            "asset_id": aid,
            "label": c[aid].get("name") or aid,
            "effective_date": effective,
            "date": effective,
            "nature": "world" if current else "data",
            "record_class": "current_event" if current else "historical_evidence_added",
        }
        if pr.get("recovery_status") != cr.get("recovery_status"):
            out.append({**base,
                        "category": "recovery_status_changed",
                        "detail": (
                            f"{pr.get('recovery_status')} -> {cr.get('recovery_status')}"
                            f" ({cr.get('scoring_evidence_kind') or 'evidence kind unstated'})"
                            + ("" if current else
                               f"; the evidence describes {effective}, before the previous build "
                               f"({previous_as_of}) — the record changed, not the facility"))})
        elif pr.get("scoring_evidence_kind") != cr.get("scoring_evidence_kind"):
            # Same status, better evidence for it. Worth reporting: an estimate becoming an
            # observation changes how much a reader should trust the same number.
            out.append({**base,
                        "category": "recovery_evidence_added",
                        "record_class": "historical_evidence_added" if not current
                        else "current_event",
                        "detail": f"evidence {pr.get('scoring_evidence_kind')} -> "
                                  f"{cr.get('scoring_evidence_kind')}"})
    return out


def _asset_changes(prev, curr):
    out = []
    p = _by_id(prev, "asset_id")
    c = _by_id(curr, "asset_id")
    for aid in sorted(set(c) - set(p)):
        a = c[aid]
        out.append({
            "category": "asset_added", "nature": "data", "record_class": "correction",
            "id": aid, "asset_id": aid, "label": a.get("name") or aid,
            "date": None, "effective_date": None,
            "detail": f"{a.get('asset_class')} added to the inventory",
        })
    for aid in sorted(set(p) & set(c)):
        a, b = p[aid], c[aid]
        moved = [f for f in ("capacity_mw", "capacity_mtpa", "capacity_bcm_y")
                 if a.get(f) != b.get(f)]
        if moved:
            out.append({
                "category": "asset_capacity_revised", "nature": "data",
                "record_class": "correction", "id": aid, "asset_id": aid,
                "label": b.get("name") or aid, "date": None, "effective_date": None,
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
                "category": "denominator_changed", "nature": "methodology",
                "record_class": "input_change", "id": k, "asset_id": None, "label": k,
                "date": None, "effective_date": None,
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
        "category": "coverage_changed", "nature": "data", "record_class": "correction",
        "id": "coverage", "asset_id": None, "label": "Benchmark coverage",
        "date": None, "effective_date": None,
        "detail": "; ".join(f"{f}: {pc.get(f)} -> {cc.get(f)}" for f in moved),
    }]


def _methodology_changes(prev_snap, curr_snap):
    """Weights and the saturation constant, read from what each build published about itself."""
    out = []
    pw = (prev_snap.get("explanations") or {}).get("headline", {}).get("nominal_weights") or {}
    cw = (curr_snap.get("explanations") or {}).get("headline", {}).get("nominal_weights") or {}
    # Both sides must actually publish their weights. A baseline that predates the explanation
    # emitter has none, and diffing present-against-absent would report every sector weight as
    # changed on the first build after the emitter shipped — a methodology change that never
    # happened, which would then mark the whole transition non-separable.
    comparable_weights = bool(pw) and bool(cw)
    for s in sorted(set(pw) | set(cw)) if comparable_weights else ():
        if pw.get(s) != cw.get(s):
            out.append({
                "category": "methodology_changed", "nature": "methodology",
                "record_class": "input_change", "id": f"weight:{s}", "asset_id": None,
                "label": f"{s} weight", "date": None, "effective_date": None,
                "detail": f"{pw.get(s)} -> {cw.get(s)}", "rescales_sector": True,
            })
    ps = (prev_snap.get("transmission_sensitivity") or {}).get("saturation_constant")
    cs = (curr_snap.get("transmission_sensitivity") or {}).get("saturation_constant")
    if ps != cs and (ps is not None or cs is not None):
        out.append({
            "category": "methodology_changed", "nature": "methodology",
            "record_class": "input_change", "id": "transmission_saturation", "asset_id": None,
            "label": "Transmission saturation constant", "date": None, "effective_date": None,
            "detail": f"{ps} -> {cs}", "rescales_sector": True,
        })
    return out


def _fingerprint_changes(prev_snap, curr_snap):
    """Input-group movement the emitted payloads cannot reveal on their own.

    A vendor snapshot can be refreshed, or the pipeline registry edited, without moving a single
    published number. Reporting nothing in that case would be wrong: the build IS different, and
    an analyst asking "why did this rebuild" deserves the real answer.
    """
    changed, comparable = build_manifest.compare(
        prev_snap.get("build_inputs"), curr_snap.get("build_inputs"))
    if not comparable:
        return [], False, changed
    out = []
    for group in changed:
        if group == "schema_version":
            continue
        category = GROUP_CATEGORY.get(group)
        if not category:
            continue
        out.append({
            "category": category,
            "nature": CATEGORIES[category],
            "record_class": "input_change",
            "id": f"inputs:{group}",
            "asset_id": None,
            "label": group.replace("_", " "),
            "date": None,
            "effective_date": None,
            "detail": f"the {group.replace('_', ' ')} inputs changed between these builds",
            "rescales_sector": group in ("methodology", "denominator_inputs"),
        })
    return out, True, changed


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
            "weight_changed": (pc.get(s, {}).get("effective_weight")
                               != cc.get(s, {}).get("effective_weight")),
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


def _facility_attribution(prev_snap, curr_snap, rescaled_sectors, separable):
    """Where inside each sector the movement sits — an account, not a decomposition.

    Facility deltas do not have to sum to the sector delta: a capped sector absorbs them, a
    changed denominator re-scales them all, and a weight change moves the sector without any
    facility moving at all. Each row therefore carries whether its own sector's arithmetic was
    exact, and a methodology change makes every row non-attributable at once.
    """
    ps = (prev_snap.get("explanations") or {}).get("sectors") or {}
    cs = (curr_snap.get("explanations") or {}).get("sectors") or {}
    # A baseline that publishes no decomposition cannot be differed at facility level. Treating
    # its absence as an empty contributor list would mark every facility in the current build as
    # having just ENTERED — a fabricated story about a build that simply could not report them.
    if not ps or not cs:
        return []
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
            reason = (
                "the measurement itself changed between these builds; data and methodology "
                "effects are not separable" if not separable else
                "sector denominator or weight changed; this facility's movement is not its own"
                if sector in rescaled_sectors else
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


def diff(prev_snap, curr_snap, prev_incidents, curr_incidents, prev_assets, curr_assets,
         lineage=None):
    """Compare two builds. Pure: takes parsed payloads, returns the ledger."""
    previous_as_of = prev_snap.get("as_of")
    current_as_of = curr_snap.get("as_of")

    changes = []
    changes += _incident_changes(prev_incidents, curr_incidents, previous_as_of)
    changes += _recovery_changes(prev_snap, curr_snap, previous_as_of)
    changes += _asset_changes(prev_assets, curr_assets)
    denominator = _denominator_changes(prev_snap, curr_snap)
    methodology = _methodology_changes(prev_snap, curr_snap)
    changes += denominator + methodology
    changes += _coverage_changes(prev_snap, curr_snap)
    fingerprint_rows, fingerprints_comparable, changed_groups = _fingerprint_changes(
        prev_snap, curr_snap)
    changes += fingerprint_rows

    for c in changes:
        assert c["category"] in CATEGORIES, c["category"]
        assert c["nature"] in NATURES, c["nature"]
        assert c.get("record_class") in RECORD_CLASSES, c.get("record_class")
        # setdefault would leave the explicit None that _incident_changes wrote.
        if c.get("first_seen_as_of") is None:
            c["first_seen_as_of"] = current_as_of

    # Sectors whose internal arithmetic was re-scaled by something above the facility level.
    rescaled = set()
    for c in denominator:
        for s in ("refining", "oil_logistics", "electric_generation", "transmission"):
            if c["id"].startswith(s):
                rescaled.add(s)
    for c in methodology:
        if c["id"].startswith("weight:"):
            rescaled.add(c["id"].split(":", 1)[1])
        if c["id"] == "transmission_saturation":
            rescaled.add("transmission")

    # A methodology change makes the whole transition non-separable (addendum §5): telling data
    # effects from measurement effects would need a replay of the old scoring code, which this
    # pipeline cannot execute. Saying so beats a decomposition with no basis.
    methodology_moved = bool(methodology) or "methodology" in changed_groups
    separable = not methodology_moved

    by_nature = {n: sum(1 for c in changes if c["nature"] == n) for n in NATURES}
    by_category = {}
    by_record_class = {}
    for c in changes:
        by_category[c["category"]] = by_category.get(c["category"], 0) + 1
        by_record_class[c["record_class"]] = by_record_class.get(c["record_class"], 0) + 1

    prev_esdi = prev_snap.get("esdi")
    curr_esdi = curr_snap.get("esdi")
    delta = None if prev_esdi is None or curr_esdi is None else _r(curr_esdi - prev_esdi)

    direction = ("forward" if previous_as_of and current_as_of and current_as_of > previous_as_of
                 else "backward" if previous_as_of and current_as_of
                 and current_as_of < previous_as_of else "same_date")

    # The quiet-day case, and the whole reason this file exists. Claiming it requires every input
    # to be unchanged — not merely that nothing was found in the payloads we happened to diff.
    # Without comparable fingerprints we cannot prove that, so we do not assert it.
    inputs_unchanged = fingerprints_comparable and not changed_groups
    time_progression_only = (
        not changes and inputs_unchanged and direction != "same_date"
        and delta is not None and delta != 0)

    return {
        "previous_build": prev_snap.get("build_time"),
        "previous_as_of": previous_as_of,
        "current_build": curr_snap.get("build_time"),
        "current_as_of": current_as_of,
        "previous_build_fingerprint": (prev_snap.get("build_outputs_fingerprint")),
        "current_build_fingerprint": (curr_snap.get("build_outputs_fingerprint")),
        "previous_inputs": prev_snap.get("build_inputs"),
        "current_inputs": curr_snap.get("build_inputs"),
        "input_groups_changed": changed_groups,
        "input_fingerprints_comparable": fingerprints_comparable,
        "lineage": lineage,
        "esdi_before": prev_esdi,
        "esdi_after": curr_esdi,
        "esdi_delta": delta,
        "as_of_direction": direction,
        "time_progression_only": time_progression_only,
        "time_progression_note": (
            None if not time_progression_only else
            "No input to this build changed: the same events, the same recovery evidence, the "
            "same denominators, the same methodology. Only the evaluation date moved, so the "
            "index moved because modelled impairment ages. This is NOT evidence that anything "
            "was repaired." if direction == "forward" else
            "No input to this build changed. This build is evaluated at an EARLIER date than the "
            "one it is compared against, so the index is higher simply because less time had "
            "elapsed. Nothing worsened."),
        "change_count": len(changes),
        "by_nature": by_nature,
        "by_category": by_category,
        "by_record_class": by_record_class,
        "changes": changes,
        "attribution_separable": separable,
        "non_separable_reason": (
            None if separable else
            "The methodology changed between these builds. Separating what moved because the "
            "world changed from what moved because the measurement changed would require "
            "replaying the previous build's scoring code against both datasets, which this "
            "pipeline cannot do. Score movement is therefore NOT fully separable from data "
            "changes, and no exact attribution is offered."),
        "sector_attribution": _sector_attribution(prev_snap, curr_snap, rescaled),
        "facility_attribution": _facility_attribution(
            prev_snap, curr_snap, rescaled, separable),
        "rescaled_sectors": sorted(rescaled),
        "attribution_note": (
            "Per-sector index-point deltas sum to the headline delta exactly — that is "
            "arithmetic. Facility-level figures are an account of where the movement sits, not "
            "a decomposition: a capped sector, a changed denominator or a changed weight all "
            "move the index without any single facility being responsible."
        ),
    }


def unavailable(curr_snap, lineage, reason):
    """No provable baseline. Emitting zeros here would claim a quiet build that never happened."""
    return {
        "previous_build": None, "previous_as_of": None,
        "current_build": curr_snap.get("build_time"), "current_as_of": curr_snap.get("as_of"),
        "previous_build_fingerprint": None,
        "current_build_fingerprint": curr_snap.get("build_outputs_fingerprint"),
        "previous_inputs": None, "current_inputs": curr_snap.get("build_inputs"),
        "input_groups_changed": [], "input_fingerprints_comparable": False,
        "lineage": lineage,
        "esdi_before": None, "esdi_after": curr_snap.get("esdi"), "esdi_delta": None,
        "as_of_direction": None,
        "time_progression_only": False, "time_progression_note": None,
        "change_count": 0, "by_nature": {n: 0 for n in NATURES}, "by_category": {},
        "by_record_class": {},
        "changes": [], "attribution_separable": False, "non_separable_reason": None,
        "sector_attribution": None, "facility_attribution": [], "rescaled_sectors": [],
        "unavailable_reason": reason,
        "attribution_note": None,
    }


def build(root, curr_snap, curr_incidents, curr_assets):
    """Produce the ledger for this build against the previous COMMITTED production build.

    Never reads the worktree payload as a baseline — see pipeline/lineage.py.
    """
    from pipeline import lineage as lin

    payloads, meta = lin.resolve(root, curr_snap.get("as_of"))
    if payloads:
        meta["worktree_payload_differs_from_baseline"] = lin.worktree_differs(
            root, payloads.get("snapshot.json"))
    if not meta.get("valid"):
        return unavailable(curr_snap, meta,
                           meta.get("reason") or "no valid production ancestor")
    return diff(
        payloads["snapshot.json"], curr_snap,
        payloads["incidents.json"], curr_incidents,
        payloads["assets.json"], curr_assets,
        lineage=meta,
    )


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default
