"""Recovery lifecycle episodes and defensible duration statistics (iteration 11 P7).

FOUR TEMPORAL CONCEPTS, AND WHICH ONE WE ACTUALLY HAVE (addendum §1-§3). A lifecycle built on a
field called "date" would silently average four different things:

    incident_date               when the disruption occurred                    AVAILABLE
    restoration_effective_date  when service/unit/facility restoration occurred  AVAILABLE
    evidence_publication_date   when the supporting report was published         NOT AVAILABLE
    dashboard_first_seen_build  first production build carrying this record      VIA LEDGER ONLY

The third is audited, not assumed: every recovery source in this corpus carries a URL and nothing
else, and none of those URLs appears as a dated incident source either. So the field is emitted as
null with an explicit reason. It is never back-filled from a retrieval timestamp, a URL fragment,
a git commit date, or the first build that happened to contain the row — each of those answers a
different question, and three of them are facts about this repository rather than about the world.

The fourth comes from the build ledger and ONLY when lineage is provable. A first-seen date is
also not "when we learned it": the report may have existed long before this dataset ingested it.
It is labelled "first present in dashboard" and nothing stronger.

STAGES ARE EVIDENCE-DRIVEN, NOT A TEMPLATE (§4, §5). An episode gets a milestone only where a
source establishes one. A pipeline whose only evidence is `flow_rerouting` shows disruption and
rerouting and NOTHING else — rerouting gas around a broken segment is not a repair, and a
lifecycle that padded the row out to a full template would say it was. The evidence families stay
distinct for the same reason: SERVICE RESTORED IS NOT FACILITY REBUILT.

TWO LAYERS, NEVER MERGED (§7). Discrete observed milestones are one thing; the continuous modelled
disruption weight that actually feeds ESDI is another. The latter is labelled as a model output,
because it is a decay curve, not a measurement of repair progress.

DURATIONS ARE ONLY COMPARABLE WITHIN A FAMILY (§11). Incident-to-service-restoration and
incident-to-physical-reconstitution measure different endpoints. Substations here restore service
in 0 days while refinery unit restarts run 7-72; a pooled "recovery time" across them would be
arithmetic without meaning. Statistics are therefore computed per (asset class, evidence family),
and a mixed-endpoint summary is labelled mixed and demoted.
"""

import datetime as dt
import statistics

# Below this, a set of observations is a list of anecdotes, not a distribution. Two points have a
# median, a min and a max, and reporting them invites a reader to treat noise as a norm.
MIN_SAMPLE = 3

# What each source family establishes, as a lifecycle stage. Deliberately NOT a linear ladder: an
# episode reaches only the stages its evidence supports, in whatever combination that is.
FAMILY_STAGE = {
    "flow_rerouting": "flow_rerouting",
    "service_restoration": "service_restoration",
    "unit_restart": "unit_restart",
    "facility_reconstitution": "physical_reconstitution",
    "estimate": "estimated_restoration",
}

STAGE_MEANING = {
    "disruption": "The facility was disrupted.",
    "flow_rerouting": (
        "Throughput was routed around the damage. The damaged asset itself is NOT repaired, and "
        "this stage says nothing about its condition."),
    "partial_operations_resumed": "Some operations resumed. The facility is not fully restored.",
    "service_restoration": (
        "The service the facility provides was restored. This does not establish that the "
        "facility was rebuilt."),
    "unit_restart": "A specific unit restarted. Other units may remain down.",
    "physical_reconstitution": "The physical asset was rebuilt or replaced.",
    "estimated_restoration": (
        "No restoration was observed. This is a modelled or estimated horizon, not a report."),
}

# Ordering for display only. A stage's absence from an episode is never rendered as completed.
STAGE_ORDER = [
    "disruption", "flow_rerouting", "partial_operations_resumed", "service_restoration",
    "unit_restart", "physical_reconstitution", "estimated_restoration",
]


def _d(value):
    if value is None:
        return None
    raw = str(value)[:10]
    try:
        return dt.date.fromisoformat(raw if len(raw) == 10 else raw + "-01")
    except (TypeError, ValueError):
        return None


def _r(x, n=4):
    return None if x is None else round(x + 0.0, n)


def _source_records(raw):
    """Recovery sources, with an explicitly null publication date.

    Audited rather than assumed: no recovery source in this corpus carries a publication date,
    and none of their URLs appears as a dated incident source. The field exists so a later
    enrichment pass can fill it; it is never inferred.
    """
    out = []
    for src in (raw or []):
        url = src.get("url") if isinstance(src, dict) else str(src)
        published = src.get("published") if isinstance(src, dict) else None
        out.append({
            "url": url,
            "published": published,
            "published_basis": "sourced" if published else "unavailable",
        })
    return out


def _trajectory(incident, record, timeline, weight_fn):
    """The MODELLED disruption weight over time — the actual ESDI input, not repair progress.

    Sampled from the same function that scores, so the curve a reader sees is the curve the index
    used. It starts at the incident and runs to the end of the series.
    """
    start = _d(incident.get("date"))
    if not start:
        return []
    points = []
    for when in timeline:
        if when < start:
            continue
        w = weight_fn(incident, when, record)
        points.append({"date": when.isoformat(), "weight": _r(w)})
    return points


def build_episode(incident, record, event, timeline, weight_fn, trace_fn, first_seen=None):
    """One episode: what happened, what was observed, and what the model did about it."""
    incident_date = incident.get("date")
    milestones = [{
        "stage": "disruption",
        "date": incident_date,
        "date_precision": incident.get("date_precision"),
        "status": "observed",
        "evidence_family": None,
        "what_source_establishes": None,
        "meaning": STAGE_MEANING["disruption"],
    }]

    # A partial restart is its own milestone and is NEVER folded into a restoration: resuming
    # some operations is a different claim from the facility being restored.
    partial = (record or {}).get("partial_operations_resumed_at")
    if partial:
        milestones.append({
            "stage": "partial_operations_resumed",
            "date": partial,
            "date_precision": "day",
            "status": "observed",
            "evidence_family": (record or {}).get("evidence_family"),
            "what_source_establishes": (record or {}).get("what_source_establishes"),
            "meaning": STAGE_MEANING["partial_operations_resumed"],
        })

    # The family can come from the RECORD as well as from a dated event. Three episodes here
    # carry a sourced repair ESTIMATE — a governor, an industry source via Reuters — with no
    # observed restoration date, and reading only dated events labelled them "no recovery
    # evidence". That is the opposite of true: someone published a horizon, and the estimate is
    # what the model decays against.
    family = (event or {}).get("evidence_family") or (record or {}).get("evidence_family")
    stage = FAMILY_STAGE.get(family)
    if stage == "estimated_restoration" and (record or {}).get("estimate_central_days"):
        milestones.append({
            "stage": "estimated_restoration",
            # Deliberately undated: an estimate is a projected horizon, not an event that
            # happened on a day. Giving it a date would make it look observed.
            "date": None,
            "date_precision": None,
            "status": "estimated",
            "drives_scoring_as": "estimated",
            "evidence_family": family,
            "estimate_days": {
                "lower": record.get("estimate_lower_days"),
                "central": record.get("estimate_central_days"),
                "upper": record.get("estimate_upper_days"),
            },
            "estimate_method": record.get("estimate_method"),
            "what_source_establishes": record.get("estimate_basis"),
            "meaning": STAGE_MEANING["estimated_restoration"],
        })
    elif stage and (event or {}).get("evidence_date"):
        milestones.append({
            "stage": stage,
            "date": event["evidence_date"],
            "date_precision": "day",
            # The MILESTONE's epistemic status, which is not the same as how the decay is
            # scored. A sourced service-restoration report is an observed milestone even when
            # the decay half-life behind it stays modelled — a partial restart does not override
            # the modelled horizon. Taking `scoring_evidence_kind` here labelled real, sourced
            # milestones "modelled", which reads as though nobody reported them.
            "status": "observed" if event.get("sources") else "estimated",
            "drives_scoring_as": event.get("scoring_evidence_kind") or "modelled",
            "evidence_family": family,
            "recovery_kind": event.get("recovery_kind"),
            "what_source_establishes": event.get("what_source_establishes"),
            "meaning": STAGE_MEANING.get(stage, ""),
        })

    # A record that asserts a restoration but records no date for it. Rare, and worth naming:
    # the claim exists, the date does not, and neither "restored" nor "no evidence" is right.
    reached = {m["stage"] for m in milestones}
    # A record that asserts a restoration but produced no dated milestone for it. The claim
    # exists, the date does not, and neither "restored" nor "no evidence" describes that.
    undated_restoration = bool(
        record
        and record.get("recovery_status") in ("substantially_restored", "fully_reconstituted")
        and reached <= {"disruption", "partial_operations_resumed"})

    # Absent stages are reported as UNKNOWN, never as pending-or-complete. For most episodes we
    # simply have no evidence either way, and saying so is the whole point.
    unknown = [s for s in STAGE_ORDER
               if s not in reached and s not in ("disruption", "estimated_restoration")]

    trace = trace_fn(incident, record) if trace_fn else None
    days = None
    a, b = _d(incident_date), _d((event or {}).get("evidence_date"))
    if (event or {}).get("observed_days") is not None:
        days = event["observed_days"]
    elif a and b:
        days = (b - a).days

    return {
        "episode_id": (event or {}).get("episode_id") or incident.get("incident_id"),
        "incident_id": incident.get("incident_id"),
        "asset_id": incident.get("asset_id"),
        "asset_name": incident.get("asset_name"),
        "asset_class": incident.get("asset_class"),
        "sector": (event or {}).get("sector"),
        "region_code": incident.get("region_code"),
        "incident_date": incident_date,
        "cause": incident.get("cause"),
        "confidence": incident.get("confidence"),
        "status": incident.get("status"),
        "recovery_status": (event or {}).get("recovery_status"),
        "evidence_family": family,
        "undated_restoration_claim": undated_restoration,
        "undated_restoration_note": (
            "A source states this facility was restored but records no date for it, so it "
            "appears on no timeline and drives no scoring change."
            if undated_restoration else None),
        "scoring_evidence_kind": (event or {}).get("scoring_evidence_kind")
        or ((record and "estimated") or "modelled"),
        # Chronological, with stage order only as a tie-break. Sorting by stage alone would
        # place a partial restart after a rerouting that happened weeks later, presenting a
        # sequence of events in an order they did not occur in.
        # Chronological, with stage order as a tie-break. Undated milestones sort LAST, not
        # first: an undated estimate is a projection about the future, and floating it above the
        # disruption that caused it inverts the story.
        "milestones": sorted(
            milestones,
            key=lambda m: (_d(m["date"]) or dt.date.max, STAGE_ORDER.index(m["stage"]))),
        "stages_unknown": unknown,
        "duration_days": days,
        "duration_start": "incident_date" if days is not None else None,
        "duration_end": stage if days is not None else None,
        "initial_impairment": _r((trace or {}).get("initial_impairment")),
        "half_life_days": _r((trace or {}).get("half_life_days"), 1),
        "half_life_kind": (trace or {}).get("half_life_kind"),
        "trajectory": _trajectory(incident, record, timeline, weight_fn),
        "sources": _source_records(
            (event or {}).get("sources") or (record or {}).get("sources")),
        "publication_date_available": False,
        "first_seen": first_seen,
    }


def _summary(values):
    """Summary statistics, or an explicit refusal. Never a distribution from one or two points."""
    n = len(values)
    if n < MIN_SAMPLE:
        return {
            "n": n,
            "sufficient": False,
            "reason": (f"{n} observation{'' if n == 1 else 's'} — below the {MIN_SAMPLE} needed "
                       "to describe a distribution. The individual values are shown instead."),
            "values": sorted(values),
        }
    ordered = sorted(values)
    out = {
        "n": n,
        "sufficient": True,
        "median": statistics.median(ordered),
        "min": ordered[0],
        "max": ordered[-1],
        "values": ordered,
    }
    if n >= 4:
        q = statistics.quantiles(ordered, n=4, method="inclusive")
        out["q1"], out["q3"] = q[0], q[2]
    return out


def distributions(episodes):
    """Durations grouped so that only like endpoints are compared (§11)."""
    by_class_family = {}
    by_family = {}
    for e in episodes:
        if e["duration_days"] is None or not e["evidence_family"]:
            continue
        key = f"{e['asset_class']}|{e['evidence_family']}"
        by_class_family.setdefault(key, []).append(e["duration_days"])
        by_family.setdefault(e["evidence_family"], []).append(e["duration_days"])

    return {
        "min_sample": MIN_SAMPLE,
        "by_class_family": {
            k: {
                "asset_class": k.split("|")[0],
                "evidence_family": k.split("|")[1],
                "duration_start": "incident_date",
                "duration_end": FAMILY_STAGE.get(k.split("|")[1]),
                "mixed_endpoints": False,
                **_summary(v),
            } for k, v in sorted(by_class_family.items())
        },
        "by_family": {
            k: {
                "evidence_family": k,
                "duration_start": "incident_date",
                "duration_end": FAMILY_STAGE.get(k),
                # Pooled across asset classes, which is a real limitation: a substation and a
                # refinery restore service on entirely different timescales.
                "mixed_endpoints": False,
                "pooled_across_classes": True,
                **_summary(v),
            } for k, v in sorted(by_family.items())
        },
        "note": (
            "Durations are grouped by what the evidence actually establishes. "
            "Incident-to-service-restoration and incident-to-physical-reconstitution measure "
            "different endpoints and are never pooled into one 'recovery time'."),
    }


TEMPORAL_MODEL = {
    "concepts": [
        {"field": "incident_date", "label": "Disruption date",
         "available": True, "note": "When the disruption occurred."},
        {"field": "restoration_effective_date", "label": "Restoration date",
         "available": True,
         "note": ("When the restoration the source describes actually happened. This is the "
                  "field that controls scoring.")},
        {"field": "evidence_publication_date", "label": "Source publication date",
         "available": False,
         "note": ("Not recorded for any recovery source in this corpus: every one carries a URL "
                  "and nothing else, and none of them appears as a dated incident source. It is "
                  "left null rather than inferred from a retrieval time, a URL fragment or a "
                  "commit date — none of which is a publication date.")},
        {"field": "dashboard_first_seen_build", "label": "First present in dashboard",
         "available": False,
         "note": ("Available only from the build ledger, and only when its lineage is provable. "
                  "It is NOT when the report was published or when anyone learned of it — the "
                  "report may have existed long before this dataset ingested it.")},
    ],
    "warning": (
        "These four are different questions. A lifecycle that averaged them would produce a "
        "number describing nothing."),
}

RECONSTRUCTION_CAVEAT = (
    "Historical trajectories are reconstructed using the current evidence set. Later evidence "
    "may refine the modelled trajectory before the restoration date. This is not an archive of "
    "what was known at the time.")

LAYER_LABELS = {
    "observed": "Observed milestones — discrete, sourced events",
    "model": "Modelled disruption weight — the value feeding the index, not measured repair "
             "progress",
}


def build(incidents, recovery_by_incident, recovery_events, timeline, weight_fn, trace_fn,
          first_seen_by_incident=None):
    """Episodes for every incident that carries recovery evidence, plus the safe statistics."""
    first_seen_by_incident = first_seen_by_incident or {}
    by_incident = {e.get("incident_id"): e for e in recovery_events}
    episodes = []
    for inc in incidents:
        iid = inc.get("incident_id")
        record = recovery_by_incident.get(iid)
        event = by_incident.get(iid)
        if not record and not event:
            continue
        episodes.append(build_episode(
            inc, record, event, timeline, weight_fn, trace_fn,
            first_seen=first_seen_by_incident.get(iid)))
    episodes.sort(key=lambda e: (e["incident_date"] or ""), reverse=True)

    families = {}
    for e in episodes:
        families[e["evidence_family"] or "none"] = families.get(
            e["evidence_family"] or "none", 0) + 1

    return {
        "temporal_model": TEMPORAL_MODEL,
        "reconstruction_caveat": RECONSTRUCTION_CAVEAT,
        "layer_labels": LAYER_LABELS,
        "stage_order": STAGE_ORDER,
        "stage_meaning": STAGE_MEANING,
        "episode_count": len(episodes),
        "episodes_by_family": families,
        "episodes_with_publication_date": sum(
            1 for e in episodes if any(s["published"] for s in e["sources"])),
        "episodes_with_first_seen": sum(1 for e in episodes if e["first_seen"]),
        "episodes": episodes,
        "distributions": distributions(episodes),
    }
