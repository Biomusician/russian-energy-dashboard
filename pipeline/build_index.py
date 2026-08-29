"""Compute the Energy System Disruption Exposure Index over time.

Read methodology/scoring.json alongside this file -- every weight, half-life and
sector definition lives there, not here. This module is the arithmetic only.

The measure, stated precisely, is: what share of the tracked installed base sits at
facilities disrupted recently enough to still be plausibly impaired, weighted by
evidence strength, cause, and time since the event.

It is not measured capacity loss. Open reporting rarely says how much throughput a
strike removed, and nothing here fills that gap with an estimate. Where a source does
quantify the loss the figure rides along on the incident and is displayed, but it is
not what drives the score, so quantified and unquantified events are treated
consistently rather than the unquantified ones silently scoring zero.

Per facility the strongest single live contribution wins rather than the sum of its
incidents: a refinery hit four times in a month is heavily disrupted, but it cannot be
more than 100% disrupted, and summing would let repeat strikes on one site outweigh
the rest of the sector.
"""

import collections
import datetime as dt

from pipeline import recovery
from pipeline.config import METHODOLOGY_DIR, SECTOR_OF_CLASS, SECTORS, WINDOW_START
from pipeline.util import read_json

SCORING = read_json(METHODOLOGY_DIR / "scoring.json")

# Categories the brief asks for that this MVP cannot derive from available open data.
# They are emitted as null with a reason rather than filled with a plausible-looking
# number, so the UI can show the gap instead of hiding it.
NOT_MODELLED = {
    "industrial_impact": "No open regional industrial-consumption data ingested.",
    "civilian_electricity_reliability": "No outage-duration or customer-minutes-lost data source.",
    "military_industrial": "Out of scope: would require mapping defence production to energy supply.",
    "cross_region_dependencies": "Requires grid topology and inter-regional flow data not yet ingested.",
}


def _dates(start, end, step_days):
    out = []
    d = dt.date.fromisoformat(start)
    end = dt.date.fromisoformat(end)
    while d <= end:
        out.append(d)
        d += dt.timedelta(days=step_days)
    if out[-1] != end:
        out.append(end)
    return out


def _incident_date(incident):
    """Month-precision dates are anchored to the first of the month.

    The precision is preserved on the record, so the UI can show it as a month; this
    is only so the decay arithmetic has a day to work from.
    """
    raw = incident["date"]
    return dt.date.fromisoformat(raw if len(raw) == 10 else raw + "-01")


def _weight_at(incident, when, record=None):
    """Decayed contribution of ONE incident at a point in time, in [0, 1].

    `record` is that incident's own recovery record (incident-level, iteration 2). The
    half-life is set by rule-based evidence precedence (pipeline/recovery.py): observed
    full/substantial reconstitution or a credible sourced estimate overrides the generic
    per-sector assumption; a mere partial restart or a low-confidence estimate does not.
    A credibly-sourced full reconstitution caps the contribution at the residual.
    """
    when_date = when
    occurred = _incident_date(incident)
    if occurred > when_date:
        return 0.0

    conf = SCORING["confidence_weights"].get(incident.get("confidence") or "possible", 0.45)
    cause = SCORING["cause_weights"].get(incident.get("cause") or "unknown", 0.7)
    base = conf * cause

    half_life, kind = recovery.effective_half_life(incident.get("asset_class"), record)
    days = (when_date - occurred).days
    value = base * (0.5 ** (days / half_life))

    if recovery.is_resolved(record, when_date):
        value = min(value, base * recovery.RESIDUAL)
    elif kind == "modelled":
        # No overriding recovery TIMING — either no record at all, or a record that falls back
        # to the modelled horizon (partial_restart, low-confidence estimate, bare impaired,
        # unknown). In all of these the incident's own reported status severity still governs.
        # Applying it only when `record is None` was a latent bug: attaching a partial-restart
        # record (which by design does NOT change the decay) silently DROPPED the 'degraded'
        # damping and scored the facility HIGHER than with no evidence at all. A partial
        # restart must never raise a score. (observed/estimated kinds override with real
        # timing and are intentionally exempt.)
        value *= SCORING["status_multipliers"].get(incident.get("status") or "unknown", 1.0)

    return value if value >= SCORING["cutoff"]["min_contribution"] else 0.0


def _incident_record(incident, recovery_by_incident):
    """The recovery record for a specific incident, if any."""
    return recovery_by_incident.get(incident.get("incident_id"))


def _facility_weight(incs, when, recovery_by_incident):
    """Strongest single live incident contribution for a facility, and which incident.

    Per-incident recovery is the point of iteration 2: a facility hit four times has
    four independent trajectories, and the current impairment is the strongest one still
    live -- not a single facility-level state smeared across all of them.
    """
    best_w, best_inc = 0.0, None
    for i in incs:
        w = _weight_at(i, when, _incident_record(i, recovery_by_incident))
        if w > best_w:
            best_w, best_inc = w, i
    return best_w, best_inc


def build(incidents, facilities, assets, refinery_total_mtpa, region_meta, as_of,
          recovery_by_incident=None, transmission_lines_by_region=None, region_context=None):
    """Return (national_series, regional_series, snapshot)."""
    recovery_by_incident = recovery_by_incident or {}
    region_context = region_context or {}
    step = SCORING["timeline"]["step_days"]
    timeline = _dates(WINDOW_START, as_of, step)

    facility_info = _facility_registry(facilities, incidents, assets)
    denominators = _denominators(assets, refinery_total_mtpa, region_meta,
                                 transmission_lines_by_region)

    # Regions excluded from the Russia+Belarus headline composite (Crimea). Their events
    # are still tracked and get their own regional exposure, but never feed the national
    # ESDI or its denominators. See docs/METHODOLOGY.md.
    esdi_excluded = {code for code, m in region_meta.items() if not m.get("esdi_included", True)}

    incidents_by_facility = collections.defaultdict(list)
    for inc in incidents:
        incidents_by_facility[inc["asset_id"]].append(inc)

    sector_weights = SCORING["sector_weights"]
    covered = [s for s in SECTORS if denominators["national"].get(s, 0) > 0]

    national = {"dates": [d.isoformat() for d in timeline], "esdi": [], "esdi_all_sectors": [],
                "sectors": {s: [] for s in SECTORS}}
    regional = {
        code: {"esdi": [], "sectors": {s: [] for s in SECTORS}} for code in region_meta
    }

    for when in timeline:
        nat_sector = collections.defaultdict(float)
        reg_sector = collections.defaultdict(lambda: collections.defaultdict(float))

        for asset_id, incs in incidents_by_facility.items():
            info = facility_info.get(asset_id)
            if not info or not info["sector"]:
                continue
            weight, _driver = _facility_weight(incs, when, recovery_by_incident)
            if weight <= 0:
                continue
            share = _share(info, denominators)
            if share <= 0:
                continue
            region_code = info["region_code"]
            # Crimea (and any esdi-excluded region) contributes to its own regional
            # exposure but never to the national composite.
            if region_code not in esdi_excluded:
                nat_sector[info["sector"]] += share * weight
            if region_code:
                reg_sector[region_code][info["sector"]] += share * weight

        for s in SECTORS:
            national["sectors"][s].append(round(min(1.0, nat_sector[s]) * 100, 2))
        national["esdi"].append(_composite(nat_sector, sector_weights, covered))
        national["esdi_all_sectors"].append(_composite_all(nat_sector, sector_weights))

        for code in region_meta:
            rs = reg_sector.get(code, {})
            for s in SECTORS:
                regional[code]["sectors"][s].append(round(min(1.0, rs.get(s, 0.0)) * 100, 2))
            regional[code]["esdi"].append(_composite(rs, sector_weights, covered))

    # Bottom-up gas-processing census for the EXPERIMENTAL sub-index (§18). Only assets that
    # carry an explicit bcm/y figure (structured, never parsed from prose) are counted.
    gpp_census = [
        {"asset_id": a["asset_id"], "name": a.get("name"), "bcm_y": a["capacity_bcm_y"],
         "basis": a.get("capacity_basis"), "status": a.get("capacity_status"),
         "region_code": a.get("region_code")}
        for a in assets
        if a.get("asset_class") == "gas_processing" and a.get("capacity_bcm_y")
    ]

    snapshot = _snapshot(
        incidents, incidents_by_facility, facility_info, denominators,
        region_meta, national, regional, timeline, as_of, covered, recovery_by_incident,
        region_context, gpp_census=gpp_census,
    )
    return national, regional, snapshot


def _composite(sector_values, weights, covered):
    """Weighted mean across sectors that have a usable denominator.

    Sectors without one are excluded and the weights renormalised, rather than
    counted as zero -- an absent measurement is not evidence of no disruption.
    """
    total_w = sum(weights[s] for s in covered)
    if not total_w:
        return 0.0
    acc = sum(weights[s] * min(1.0, sector_values.get(s, 0.0)) for s in covered)
    return round(acc / total_w * 100, 2)


def _composite_all(sector_values, weights):
    """The composite if EVERY sector were counted, including the uncovered ones (gas, coal)
    treated as present-at-zero -- i.e. the headline WITHOUT the covered-sector renormalisation.
    The gap between this and the headline `esdi` is the uplift that excluding gas and coal
    adds, and is disclosed alongside the headline (red-team, iteration 5) so a reader can see
    that the number rests on renormalising two sectors away -- one of which (gas) is not
    unmeasured but has documented strikes we deliberately do not score."""
    total_w = sum(weights[s] for s in SECTORS)
    if not total_w:
        return 0.0
    acc = sum(weights[s] * min(1.0, sector_values.get(s, 0.0)) for s in SECTORS)
    return round(acc / total_w * 100, 2)


def _facility_registry(facilities, incidents, assets):
    """asset_id -> capacity, region and sector, for everything an incident can hit."""
    by_asset = {a["asset_id"]: a for a in assets}
    reg = {}
    for f in facilities:
        cls = f.get("asset_class")
        reg[f["asset_id"]] = {
            "name": f.get("name"),
            "asset_class": cls,
            "sector": SECTOR_OF_CLASS.get(cls),
            "region_code": f.get("region_code"),
            "capacity_mtpa": f.get("capacity_mtpa"),
            "capacity_mw": f.get("capacity_mw"),
            "capacity_bcm_y": f.get("capacity_bcm_y"),
        }
    # Curated incidents may name a facility that no source table lists.
    for inc in incidents:
        if inc["asset_id"] in reg:
            continue
        cls = inc.get("asset_class")
        # A curated incident may name an inventoried asset via linked_asset_id. When
        # it does, the facility's FULL capacity becomes the exposure base -- the same
        # treatment refineries get, since the index measures capacity exposed to
        # disruption rather than capacity proven lost.
        linked = by_asset.get(inc.get("linked_asset_id") or "")
        self_asset = by_asset.get(inc["asset_id"])  # incident hitting an inventoried asset directly
        reg[inc["asset_id"]] = {
            "name": inc.get("asset_name"),
            "asset_class": cls,
            "sector": SECTOR_OF_CLASS.get(cls),
            "region_code": inc.get("region_code"),
            "capacity_mtpa": inc.get("capacity_affected_mtpa") or (linked or {}).get("capacity_mtpa"),
            "capacity_mw": inc.get("capacity_affected_mw") or (linked or {}).get("capacity_mw"),
            # bcm/y is carried for the experimental gas-processing index only (never MTPA/MW,
            # so the headline denominators are untouched); a GPP incident resolves to its own
            # inventoried supplement asset for the capacity figure.
            "capacity_bcm_y": (linked or {}).get("capacity_bcm_y") or (self_asset or {}).get("capacity_bcm_y"),
            "voltage_kv": inc.get("voltage_kv") or (linked or {}).get("voltage_kv"),
            "linked_asset_id": inc.get("linked_asset_id"),
        }
    return reg


SATURATION_EVENTS = SCORING["transmission"]["saturation_events"]


def _denominators(assets, refinery_total_mtpa, region_meta, transmission_lines_by_region=None):
    """National and per-region bases each sector's exposure is measured against."""
    transmission_lines_by_region = transmission_lines_by_region or {}
    nat = {s: 0.0 for s in SECTORS}
    per_region = {code: {s: 0.0 for s in SECTORS} for code in region_meta}
    # Crimea and any esdi-excluded region never contribute to the national denominator.
    esdi_excluded = {code for code, m in region_meta.items() if not m.get("esdi_included", True)}

    nat["refining"] = refinery_total_mtpa

    # Electric GENERATION: installed MW from power plants (a capacity share).
    for a in assets:
        if SECTOR_OF_CLASS.get(a["asset_class"]) != "electric_generation":
            continue
        if a["region_code"] in esdi_excluded:
            continue
        mw = a.get("capacity_mw") or 0
        nat["electric_generation"] += mw
        if a["region_code"] in per_region:
            per_region[a["region_code"]]["electric_generation"] += mw

    # Transmission network CONTEXT (not a hard denominator): tracked substation and
    # HV-line counts per region. Shown alongside the event-burden exposure.
    tx_context = {code: {"substations": 0, "lines": 0} for code in region_meta}
    for a in assets:
        if a["asset_class"] == "substation" and a["region_code"] in tx_context:
            tx_context[a["region_code"]]["substations"] += 1
    for code, n in transmission_lines_by_region.items():
        if code in tx_context:
            tx_context[code]["lines"] += n

    # oil_logistics has no published national throughput base; measure it against the
    # refining base, which is the volume the logistics chain exists to move. Flagged
    # as a proxy in the emitted metadata.
    nat["oil_logistics"] = refinery_total_mtpa

    # Transmission's "denominator" is the saturation constant (event-burden basis).
    nat["transmission"] = SATURATION_EVENTS

    return {"national": nat, "regional": per_region, "tx_context": tx_context}


def _share(info, denominators):
    """Per-facility contribution to its sector's exposure.

    Capacity sectors return the facility's fraction of the national capacity base.
    Transmission (event_burden) returns a saturation-scaled unit: each disrupted
    transmission facility is one weighted event out of `saturation_events`, so the
    summed burden saturates at exposure 100 -- never a capacity-offline claim.
    """
    sector = info["sector"]
    if sector in ("refining", "oil_logistics"):
        nat = denominators["national"].get(sector, 0)
        cap = info.get("capacity_mtpa")
        return (cap / nat) if (nat and cap) else 0.0
    if sector == "electric_generation":
        nat = denominators["national"].get(sector, 0)
        cap = info.get("capacity_mw")
        return (cap / nat) if (nat and cap) else 0.0
    if sector == "transmission":
        return _voltage_weight(info) / SATURATION_EVENTS
    return 0.0


def _voltage_weight(info):
    """Weight a transmission facility by voltage class where known; default 1.0."""
    vw = SCORING["transmission"]["voltage_weight"]
    kv = info.get("voltage_kv")
    if kv:
        for band in ("750", "500", "330", "220", "110"):
            if kv >= int(band):
                return vw[band]
    return vw["default"]


# Sectors for which a defensible per-region capacity base exists. Refining and oil
# logistics have no reliable regional denominator (the national refinery inventory is not
# regionalised), so they are excluded from regional intensity and reported as missing.
_INTENSITY_SECTORS = ("electric_generation", "transmission")


def _regional_intensity(code, r_live, facility_info, installed_mw, tx_burden):
    """Disruption relative to the REGION's own tracked base, per sector.

    Returns per-sector intensity (or None where no regional denominator exists), the
    covered/missing sector lists, and a composite renormalised over covered sectors only.
    Unknown is never zero: a sector the region is disrupted in but cannot measure appears
    in `missing_sectors`, not as a low score.
    """
    finfo = lambda x: facility_info[x["asset_id"]]
    per_sector = {}

    # Generation: disrupted installed MW / the region's own installed MW.
    gen_disrupted = sum(
        (finfo(x).get("capacity_mw") or 0) * x["disruption_weight"]
        for x in r_live if finfo(x).get("sector") == "electric_generation"
    )
    per_sector["electric_generation"] = _pct(gen_disrupted, installed_mw) if installed_mw else None

    # Transmission: event-burden against the saturation constant (regional == national
    # basis for this event measure).
    tx_live = any(finfo(x).get("sector") == "transmission" for x in r_live)
    per_sector["transmission"] = (
        round(min(100.0, 100.0 * tx_burden / SATURATION_EVENTS), 2) if tx_live else None
    )

    # Sectors the region is actually disrupted in, so we can flag the ones we cannot score.
    disrupted_sectors = {finfo(x).get("sector") for x in r_live}
    missing = sorted(
        s for s in SECTORS
        if s in disrupted_sectors and s not in _INTENSITY_SECTORS
    )

    sector_weights = SCORING["sector_weights"]
    covered = [s for s in _INTENSITY_SECTORS if per_sector.get(s) is not None]
    if covered:
        total_w = sum(sector_weights.get(s, 0) for s in covered)
        composite = round(
            sum(sector_weights.get(s, 0) * per_sector[s] for s in covered) / total_w, 2
        ) if total_w else None
    else:
        composite = None

    return {
        "composite": composite,
        "sectors": per_sector,
        "covered_sectors": covered,
        "missing_sectors": missing,
    }


def _incident_recovery_state(incident, record, today):
    """Recovery/reconstitution state for ONE incident, evidence-tagged.

    Every duration says whether it drives scoring as observed, estimated or modelled, so
    nothing here can present a guess as a report. A partial restart and a low-confidence
    estimate are shown but marked as not driving the decay.
    """
    asset_class = incident.get("asset_class")
    horizon, kind, closes = recovery.assess(asset_class, record)
    resolved = recovery.is_resolved(record, today)
    age = None if resolved else recovery.impairment_age_days(incident["date"], record, today)
    status = (record or {}).get("recovery_status") or ("impaired" if not resolved else "fully_reconstituted")

    state = {
        "incident_id": incident.get("incident_id"),
        "recovery_status": status,
        # Granular §13 vocabulary describing WHAT the source proves (e.g. flow_rerouted vs
        # station_rebuilt). Distinct from recovery_status, which is the scoring bucket.
        "recovery_kind": None,
        "scoring_evidence_kind": kind,  # observed | estimated | modelled — drives the decay
        "reconstitution_horizon_days": round(horizon),
        "resolved": resolved,
        "impairment_age_days": age,
        "observed_days": None,
        "observed_date": None,
        "partial_operations_resumed_at": None,
        "partial_or_full": None,
        "estimate_days": None,
        "estimate_used_for_scoring": kind == "estimated",
        "what_source_establishes": None,
        "source_confidence": None,
        "recovery_sources": [],
    }
    if record:
        state["recovery_kind"] = record.get("recovery_kind")
        state["observed_days"] = record.get("observed_days")
        state["observed_date"] = record.get("observed_date")
        state["partial_operations_resumed_at"] = record.get("partial_operations_resumed_at")
        state["partial_or_full"] = record.get("partial_or_full")
        state["what_source_establishes"] = record.get("what_source_establishes")
        state["source_confidence"] = record.get("source_confidence")
        state["recovery_sources"] = record.get("sources", [])
        if record.get("estimate_central_days") is not None:
            state["estimate_days"] = {
                "lower": record.get("estimate_lower_days"),
                "central": record.get("estimate_central_days"),
                "upper": record.get("estimate_upper_days"),
                "basis": record.get("estimate_basis"),
                "method": record.get("estimate_method"),
                "confidence": record.get("source_confidence"),
                "used_for_scoring": kind == "estimated",
            }
    return state


def _gas_processing_index(gpp_census, live, today):
    """EXPERIMENTAL gas-processing exposure (§18). A WITHIN-CENSUS share — the weighted
    disrupted GPP capacity over the total CENSUSED capacity — and nothing more.

    It is deliberately NOT part of the headline ESDI and carries no national denominator: the
    census is a non-exhaustive, bottom-up sample of publicly-sourced GPP capacities (bcm/y raw
    gas). Russia processes far more gas than the census holds, so this ratio OVERSTATES national
    exposure and is gated out of the composite pending an independent red-team (§18, §35).
    """
    if not gpp_census:
        return None
    census_total = sum(g["bcm_y"] for g in gpp_census)
    live_by_id = {x["asset_id"]: x for x in live}
    disrupted, struck = 0.0, []
    for g in gpp_census:
        x = live_by_id.get(g["asset_id"])
        w = x["disruption_weight"] if x else 0.0
        if w > 0:
            disrupted += g["bcm_y"] * w
            struck.append({"asset_id": g["asset_id"], "name": g["name"],
                           "bcm_y": g["bcm_y"], "disruption_weight": round(w, 3)})
    uncertain = sum(g["bcm_y"] for g in gpp_census if g.get("status") == "uncertain")
    aggregate = sum(g["bcm_y"] for g in gpp_census if g.get("status") == "aggregate")
    return {
        "experimental": True,
        "in_headline_esdi": False,
        "census_plants": len(gpp_census),
        "census_bcm_y": round(census_total, 2),
        "struck_plants": len(struck),
        "disrupted_bcm_y_weighted": round(disrupted, 2),
        "within_census_exposure_pct": round(100 * disrupted / census_total, 1) if census_total else None,
        "uncertain_bcm_y": round(uncertain, 2),
        "aggregate_bcm_y": round(aggregate, 2),
        "struck": sorted(struck, key=lambda s: -s["bcm_y"]),
        "caveat": (
            "Within-census share only. The census is a non-exhaustive, bottom-up sample of "
            "publicly-sourced gas-processing capacities (bcm/y raw gas) — NOT a national "
            "denominator — so this is not national gas-processing exposure. Experimental: "
            "excluded from the headline ESDI pending an independent red-team."
        ),
    }


def _snapshot(incidents, by_facility, facility_info, denominators, region_meta,
              national, regional, timeline, as_of, covered, recovery_by_incident,
              region_context=None, gpp_census=None):
    region_context = region_context or {}
    today = dt.date.fromisoformat(as_of)
    heating = today.month in SCORING["heating_season_months"]

    live = []
    for asset_id, incs in by_facility.items():
        w, driver = _facility_weight(incs, today, recovery_by_incident)
        if w > 0:
            info = facility_info.get(asset_id, {})
            driver_rec = _incident_record(driver, recovery_by_incident) if driver else None
            entry = {
                "asset_id": asset_id,
                "name": info.get("name"),
                "asset_class": info.get("asset_class"),
                "sector": info.get("sector"),
                "region_code": info.get("region_code"),
                "disruption_weight": round(w, 3),
                "event_count": len(incs),
                "latest": max(i["date"] for i in incs),
                "driving_incident_id": driver.get("incident_id") if driver else None,
                "recovery": _incident_recovery_state(driver, driver_rec, today),
            }
            live.append(entry)
    live.sort(key=lambda x: -x["disruption_weight"])

    # Transmission-concentration disclosure (red-team, iteration 5). Transmission is an
    # event-burden measure against a small saturation constant, so it is dominated by the
    # freshest strikes in a thinly-populated sector -- currently the Kerch power bridge and
    # occupied-Crimea substations. Surface where the burden actually sits so "transmission N"
    # is not misread as "N% of Russia's grid".
    tx = []
    for x in live:
        if x["sector"] != "transmission":
            continue
        contrib = _share(facility_info.get(x["asset_id"], {}), denominators) * x["disruption_weight"]
        if contrib > 0:
            tx.append((contrib, x["name"] or x["asset_id"], x["region_code"]))
    tx.sort(reverse=True)
    tx_total = sum(c for c, _, _ in tx) or 1.0
    occupied = {code for code, m in region_meta.items() if m.get("analytic_scope", "aoi") != "aoi"}
    transmission_concentration = {
        "top": [{"name": n, "region_code": rc, "pct": round(c / tx_total * 100, 1)}
                for c, n, rc in tx[:5]],
        "occupied_share_pct": round(sum(c for c, _, rc in tx if rc in occupied) / tx_total * 100, 1),
        "note": (
            "Transmission is an event-burden measure against a saturation constant (8), so it "
            "is dominated by the freshest strikes in a thin sector -- currently the Kerch power "
            "bridge (Taman) and occupied-Crimea substations, not the wider Russian grid. Read "
            "it as theatre-concentrated, not national."
        ),
    }

    quantified = sum(
        1 for i in incidents
        if i.get("capacity_affected_mw") or i.get("capacity_affected_mtpa")
    )

    regions_out = {}
    for code, meta in region_meta.items():
        r_inc = [i for i in incidents if i.get("region_code") == code]
        struck = {i["asset_id"] for i in r_inc}
        r_live = [x for x in live if x["region_code"] == code]

        finfo = lambda x: facility_info[x["asset_id"]]
        disrupted_gen_mw = sum(
            (finfo(x).get("capacity_mw") or 0) * x["disruption_weight"]
            for x in r_live if finfo(x).get("sector") == "electric_generation"
        )
        installed_mw = denominators["regional"][code]["electric_generation"]
        disrupted_mtpa = sum(
            (finfo(x).get("capacity_mtpa") or 0) * x["disruption_weight"]
            for x in r_live if finfo(x).get("sector") == "refining"
        )
        thermal_disrupted = sum(
            (finfo(x).get("capacity_mw") or 0) * x["disruption_weight"]
            for x in r_live if finfo(x).get("asset_class") == "power_plant_thermal"
        )
        tx_burden = sum(
            _voltage_weight(finfo(x)) * x["disruption_weight"]
            for x in r_live if finfo(x).get("sector") == "transmission"
        )
        tx_ctx = denominators["tx_context"].get(code, {"substations": 0, "lines": 0})
        unresolved = [x for x in r_live if not x["recovery"]["resolved"]]

        # Active-burden decomposition (transparent columns, not a composite): the oldest
        # open impairment, the median open age, and the summed remaining reconstitution
        # time (modelled/estimated horizon minus elapsed) across unresolved facilities.
        open_ages = [x["recovery"]["impairment_age_days"] for x in unresolved
                     if x["recovery"]["impairment_age_days"] is not None]
        backlog_days = sum(
            max(0, (x["recovery"]["reconstitution_horizon_days"] or 0)
                - (x["recovery"]["impairment_age_days"] or 0))
            for x in unresolved
        )
        affected_sectors = sorted({facility_info[x["asset_id"]].get("sector")
                                   for x in unresolved if facility_info[x["asset_id"]].get("sector")})

        effects = {
            "generation_margin": _pct(disrupted_gen_mw, installed_mw),
            "fuel_production": _pct(disrupted_mtpa, denominators["national"]["refining"]),
            "logistics": round(
                sum(x["disruption_weight"] for x in r_live
                    if finfo(x).get("sector") == "oil_logistics"), 2
            ),
            # Transmission is event-burden, not capacity: show the weighted burden and
            # the tracked network context, never a "% offline".
            "transmission_burden": round(tx_burden, 2),
            "heating_season_exposure": (
                _pct(thermal_disrupted, installed_mw) if heating else 0.0
            ),
            "repair_burden": len(unresolved),
            "recurrence": round(len(r_inc) / len(struck), 2) if struck else 0.0,
        }
        effects.update({k: None for k in NOT_MODELLED})

        # Regional Disruption INTENSITY: disrupted vs the REGION's own tracked base, not
        # the national base (which the ESDI "contribution" uses). Only sectors with a
        # genuine regional denominator are scored; refining/oil-logistics have no reliable
        # per-region capacity base, so they are excluded and reported as missing rather
        # than treated as zero. A region disrupted in an unmeasurable sector shows that
        # gap instead of a falsely low intensity.
        intensity = _regional_intensity(
            code, r_live, facility_info, installed_mw, tx_burden,
        )

        regions_out[code] = {
            "code": code,
            "name": meta["name"],
            "district": meta["district"],
            "country": meta["country"],
            "esdi_included": meta.get("esdi_included", True),
            "analytic_scope": meta.get("analytic_scope", "aoi"),
            "sovereignty": meta.get("sovereignty"),
            "de_facto_control": meta.get("de_facto_control"),
            "status_note": meta.get("status_note"),
            "esdi": regional[code]["esdi"][-1],
            "sectors": {s: regional[code]["sectors"][s][-1] for s in SECTORS},
            "incident_count": len(r_inc),
            "struck_facility_count": len(struck),
            "live_disruption_count": len(r_live),
            "unresolved_count": len(unresolved),
            "oldest_unresolved_days": max(open_ages) if open_ages else 0,
            "median_unresolved_age_days": _median(open_ages),
            "reconstitution_backlog_days": round(backlog_days),
            "affected_sectors": affected_sectors,
            "installed_mw": round(installed_mw),
            "tracked_substations": tx_ctx["substations"],
            "tracked_transmission_lines": tx_ctx["lines"],
            "regional_intensity": intensity,
            # Structural context only: population POTENTIALLY exposed, never population
            # actually affected. A civilian effect is only ever a sourced incident.
            "population_millions": (region_context.get(code) or {}).get("population_millions"),
            "effects": effects,
        }

    return {
        "as_of": as_of,
        "esdi": national["esdi"][-1],
        # The same composite WITHOUT renormalising the uncovered sectors away (gas + coal
        # counted present-at-zero). Disclosed so the headline's renormalisation uplift is
        # visible, not silent (red-team, iteration 5).
        "esdi_all_sectors": national["esdi_all_sectors"][-1],
        "esdi_renormalization_note": (
            "The headline ESDI renormalises the covered sectors (their weights sum to less "
            "than 1 because gas and coal are uncovered). esdi_all_sectors is the same figure "
            "with gas and coal counted as present-at-zero; the gap is the uplift that "
            "excluding them adds. Gas is not unmeasured -- it carries documented strikes that "
            "score zero for want of a defensible denominator."
        ),
        "sectors": {s: national["sectors"][s][-1] for s in SECTORS},
        "sectors_covered": covered,
        "sectors_uncovered": [s for s in SECTORS if s not in covered],
        "transmission_concentration": transmission_concentration,
        "heating_season": heating,
        "denominators": {
            "refining_mtpa": round(denominators["national"]["refining"], 1),
            "electric_generation_mw": round(denominators["national"]["electric_generation"]),
            "transmission_saturation_events": SATURATION_EVENTS,
        },
        "incident_total": len(incidents),
        "incidents_with_quantified_capacity": quantified,
        "assessed_degradation": _assessed_degradation(incidents, live, facility_info, today),
        "recovery_stats": _recovery_stats(live, incidents, recovery_by_incident, facility_info),
        "coverage_detail": _coverage_detail(incidents, recovery_by_incident),
        # Experimental, non-headline measures (§18). Kept in a separate namespace so nothing can
        # mistake them for the composite. Gas processing is the first: a within-census share.
        "experimental_indices": {
            "gas_processing": _gas_processing_index(gpp_census, live, today),
        },
        "live_disruptions": live[:80],
        "regions": regions_out,
        "not_modelled": NOT_MODELLED,
    }


def _assessed_degradation(incidents, live, facility_info, today):
    """Concept 2: degradation actually quantified by sources, kept separate from exposure.

    Exposure counts capacity sitting at disrupted sites; assessed degradation counts
    only capacity a source explicitly said was lost. Today that is almost nothing, and
    saying so plainly is the point.
    """
    quantified = [
        i for i in incidents
        if i.get("capacity_affected_mw") or i.get("capacity_affected_mtpa") or i.get("capacity_affected_pct")
    ]
    return {
        "quantified_incident_count": len(quantified),
        "total_incident_count": len(incidents),
        "quantified_mw": round(sum(i.get("capacity_affected_mw") or 0 for i in quantified), 1),
        "quantified_mtpa": round(sum(i.get("capacity_affected_mtpa") or 0 for i in quantified), 2),
        "note": (
            "Assessed degradation counts only capacity a source explicitly quantified. "
            "It is deliberately distinct from exposure, which counts capacity at disrupted "
            "sites regardless of measured loss."
        ),
    }


def _median(values):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    n = len(vals)
    mid = n // 2
    return vals[mid] if n % 2 else round((vals[mid - 1] + vals[mid]) / 2, 1)


# A median observed restoration is shown only with at least this many DISTINCT recovery
# EPISODES (not records). Iteration 3 raised this to 5 and made it episode-based, so a
# multi-day strike counted once and the median is never "median-of-few".
MIN_MEDIAN_EPISODES = 5
# A per-CLASS median needs fewer episodes than the pooled one, because episodes within one
# infrastructure class are commensurable (§12). The pooled cross-class median is kept only as
# labelled "mixed-infrastructure evidence", never a generic repair time.
MIN_SECTOR_MEDIAN_EPISODES = 3


def _recovery_stats(live, incidents, recovery_by_incident, facility_info):
    """Concept 3: incident-level reconstitution statistics, counted by DISTINCT EPISODE.

    Row count is not sample size: a multi-day strike, or the same episode recorded
    twice, must not inflate n. Observed durations are collected per unique episode_id, so
    the median rests on independent disruption/recovery sequences.
    """
    unresolved = [x for x in live if not x["recovery"]["resolved"]]
    resolved = [x for x in live if x["recovery"]["resolved"]]

    inc_by_id = {i["incident_id"]: i for i in incidents}

    # Deduplicate recovery evidence by episode before counting anything.
    records = 0
    observed_by_episode = {}   # episode_id -> observed days (first seen)
    partial_episodes, full_episodes, estimate_episodes = set(), set(), set()
    obs_by_sector = collections.defaultdict(dict)  # sector -> {episode: days}
    partial_by_sector = collections.defaultdict(set)  # sector -> {episode} (partial restarts)
    for incident_id, rec in recovery_by_incident.items():
        inc = inc_by_id.get(incident_id)
        if inc is None:
            continue  # orphaned record (episode merged/removed) — ignored, not counted
        records += 1
        episode = inc.get("episode_id") or incident_id
        _h, kind, _c = recovery.assess(inc.get("asset_class"), rec)
        status = rec.get("recovery_status")
        sector = SECTOR_OF_CLASS.get(inc.get("asset_class"))
        if status == "partial_restart":
            partial_episodes.add(episode)
            if sector:
                partial_by_sector[sector].add(episode)
        if status in ("fully_reconstituted", "substantially_restored"):
            full_episodes.add(episode)
        if rec.get("estimate_central_days"):
            estimate_episodes.add(episode)
        if kind == "observed" and rec.get("observed_days") and episode not in observed_by_episode:
            observed_by_episode[episode] = rec["observed_days"]
            if sector:
                obs_by_sector[sector][episode] = rec["observed_days"]

    observed_durations = list(observed_by_episode.values())
    ages = [x["recovery"]["impairment_age_days"] for x in unresolved if x["recovery"]["impairment_age_days"] is not None]
    by_kind = collections.Counter(x["recovery"]["scoring_evidence_kind"] for x in live)

    by_sector = {}
    for sector in SECTORS:
        sect_live = [x for x in live if x.get("sector") == sector]
        if not sect_live and sector not in obs_by_sector:
            continue
        sect_obs = sorted(int(d) for d in obs_by_sector.get(sector, {}).values())
        by_sector[sector] = {
            "disrupted_facilities": len(sect_live),
            "unresolved": sum(1 for x in sect_live if not x["recovery"]["resolved"]),
            "observed_restoration_episodes": len(sect_obs),
            "observed_restoration_values": sect_obs,
            # Partial restarts are recovery EVIDENCE for the class but not a full-restoration
            # duration — so a class can have partial evidence while showing no observed median.
            "partial_restart_episodes": len(partial_by_sector.get(sector, set())),
            # Per-class median (§12): needs episodes WITHIN the class; below the gate the UI
            # shows the individual durations, which is honest for a small sample.
            "median_observed_restoration_days":
                _median(sect_obs) if len(sect_obs) >= MIN_SECTOR_MEDIAN_EPISODES else None,
        }

    n_episodes = len(observed_durations)
    median_meaningful = n_episodes >= MIN_MEDIAN_EPISODES
    # §12: sectors/classes that clear the per-class gate get their OWN median; these are the
    # only medians a reader should treat as a repair time for that kind of infrastructure.
    sector_medians = {
        sec: m["median_observed_restoration_days"]
        for sec, m in by_sector.items()
        if m["median_observed_restoration_days"] is not None
    }
    return {
        "unresolved_count": len(unresolved),
        "resolved_count": len(resolved),
        "min_median_episodes": MIN_MEDIAN_EPISODES,
        "min_sector_median_episodes": MIN_SECTOR_MEDIAN_EPISODES,
        # The POOLED median mixes infrastructure classes (a refinery CDU and a substation are
        # not the same repair problem), so it is emitted but explicitly labelled mixed and is
        # never the headline (§11). Prefer sector_medians below where they exist.
        "median_observed_restoration_days": _median(observed_durations) if median_meaningful else None,
        "median_meaningful": median_meaningful,
        "median_is_mixed_infrastructure": True,
        "observed_restoration_episodes": n_episodes,
        "observed_restoration_values": sorted(int(d) for d in observed_durations),
        # Per-class medians that individually clear MIN_SECTOR_MEDIAN_EPISODES (may be empty).
        "sector_medians": sector_medians,
        "median_impairment_age_days": _median(ages) if len(ages) >= MIN_MEDIAN_EPISODES else None,
        "impairment_age_sample": len(ages),
        "partial_restart_episodes": len(partial_episodes),
        "full_reconstitution_episodes": len(full_episodes),
        "estimate_episodes": len(estimate_episodes),
        "recovery_record_count": records,
        "evidence_kind_counts": dict(by_kind),
        "by_sector": by_sector,
        "note": (
            "Recovery is tracked per incident and counted by DISTINCT EPISODE: a multi-day "
            f"strike counts once. National observed-restoration evidence is n={n_episodes}. A "
            f"per-CLASS median appears only where a class has >= {MIN_SECTOR_MEDIAN_EPISODES} "
            "independent observed episodes; the pooled cross-class figure is MIXED-"
            "INFRASTRUCTURE evidence, not a generic repair time, and is never the headline. "
            "'modelled' scoring means no credible source-reported timing exists; a partial "
            "restart (including flow rerouted around a still-damaged node) is recorded but "
            "never treated as full reconstitution."
        ),
    }


def _coverage_detail(incidents, recovery_by_incident=None):
    """Concept 4: transparent, categorical coverage — never a fabricated confidence interval.

    Splits observed event counts by year, sector, region and cause so a reader can see
    where the record is thin. A low count is explicitly ambiguous between low disruption
    and low reporting; that ambiguity is stated, not resolved with false precision.
    """
    recovery_by_incident = recovery_by_incident or {}

    def bucket(key):
        c = collections.Counter()
        for i in incidents:
            c[key(i)] += 1
        return dict(sorted(c.items()))

    # Evidence-availability matrix: how many events in each sector carry recovery and
    # cost evidence, so the reader can see where sourcing is thin along each dimension.
    evidence_matrix = {}
    for i in incidents:
        sector = SECTOR_OF_CLASS.get(i.get("asset_class"), "other")
        row = evidence_matrix.setdefault(sector, {"events": 0, "recovery": 0, "cost": 0})
        row["events"] += 1
        if i.get("incident_id") in recovery_by_incident:
            row["recovery"] += 1
        if i.get("repair_cost_reported_usd_m") or i.get("repair_cost_estimate_low_usd_m"):
            row["cost"] += 1

    return {
        "by_year": bucket(lambda i: i["date"][:4]),
        "by_sector": bucket(lambda i: SECTOR_OF_CLASS.get(i.get("asset_class"), "other")),
        "by_cause": bucket(lambda i: i.get("cause") or "unknown"),
        "by_district": bucket(lambda i: i.get("_district") or "unknown"),
        "evidence_matrix": evidence_matrix,
        "note": (
            "Counts of enumerated events only. A low count may mean genuinely low "
            "disruption OR thin open-source reporting for that bucket; this dataset "
            "cannot always distinguish the two, and does not pretend to."
        ),
    }


def _pct(part, whole):
    return round(part / whole * 100, 2) if whole else 0.0
