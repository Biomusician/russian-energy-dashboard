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

    half_life, _kind = recovery.effective_half_life(incident.get("asset_class"), record)
    days = (when_date - occurred).days
    value = base * (0.5 ** (days / half_life))

    if recovery.is_resolved(record, when_date):
        value = min(value, base * recovery.RESIDUAL)
    elif record is None:
        # No recovery record: honour an explicit status on the incident itself.
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
          recovery_by_incident=None):
    """Return (national_series, regional_series, snapshot)."""
    recovery_by_incident = recovery_by_incident or {}
    step = SCORING["timeline"]["step_days"]
    timeline = _dates(WINDOW_START, as_of, step)

    facility_info = _facility_registry(facilities, incidents, assets)
    denominators = _denominators(assets, refinery_total_mtpa, region_meta)

    # Regions excluded from the Russia+Belarus headline composite (Crimea). Their events
    # are still tracked and get their own regional exposure, but never feed the national
    # ESDI or its denominators. See docs/METHODOLOGY.md.
    esdi_excluded = {code for code, m in region_meta.items() if not m.get("esdi_included", True)}

    incidents_by_facility = collections.defaultdict(list)
    for inc in incidents:
        incidents_by_facility[inc["asset_id"]].append(inc)

    sector_weights = SCORING["sector_weights"]
    covered = [s for s in SECTORS if denominators["national"].get(s, 0) > 0]

    national = {"dates": [d.isoformat() for d in timeline], "esdi": [], "sectors": {s: [] for s in SECTORS}}
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

        for code in region_meta:
            rs = reg_sector.get(code, {})
            for s in SECTORS:
                regional[code]["sectors"][s].append(round(min(1.0, rs.get(s, 0.0)) * 100, 2))
            regional[code]["esdi"].append(_composite(rs, sector_weights, covered))

    snapshot = _snapshot(
        incidents, incidents_by_facility, facility_info, denominators,
        region_meta, national, regional, timeline, as_of, covered, recovery_by_incident,
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
        reg[inc["asset_id"]] = {
            "name": inc.get("asset_name"),
            "asset_class": cls,
            "sector": SECTOR_OF_CLASS.get(cls),
            "region_code": inc.get("region_code"),
            "capacity_mtpa": inc.get("capacity_affected_mtpa") or (linked or {}).get("capacity_mtpa"),
            "capacity_mw": inc.get("capacity_affected_mw") or (linked or {}).get("capacity_mw"),
            "linked_asset_id": inc.get("linked_asset_id"),
        }
    return reg


def _denominators(assets, refinery_total_mtpa, region_meta):
    """National and per-region bases each sector's exposure is measured against."""
    nat = {s: 0.0 for s in SECTORS}
    per_region = {code: {s: 0.0 for s in SECTORS} for code in region_meta}
    # Crimea and any esdi-excluded region never contribute to the national denominator.
    esdi_excluded = {code for code, m in region_meta.items() if not m.get("esdi_included", True)}

    nat["refining"] = refinery_total_mtpa

    for a in assets:
        sector = SECTOR_OF_CLASS.get(a["asset_class"])
        if sector != "electric_power":
            continue
        if a["region_code"] in esdi_excluded:
            continue
        mw = a.get("capacity_mw") or 0
        nat["electric_power"] += mw
        if a["region_code"] in per_region:
            per_region[a["region_code"]]["electric_power"] += mw

    # oil_logistics has no published national throughput base; measure it against the
    # refining base, which is the volume the logistics chain exists to move. Flagged
    # as a proxy in the emitted metadata.
    nat["oil_logistics"] = refinery_total_mtpa

    return {"national": nat, "regional": per_region}


def _share(info, denominators):
    """Fraction of the national base this facility represents."""
    sector = info["sector"]
    nat = denominators["national"].get(sector, 0)
    if not nat:
        return 0.0
    if sector in ("refining", "oil_logistics"):
        cap = info.get("capacity_mtpa")
        return (cap / nat) if cap else 0.0
    if sector == "electric_power":
        cap = info.get("capacity_mw")
        return (cap / nat) if cap else 0.0
    return 0.0


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


def _snapshot(incidents, by_facility, facility_info, denominators, region_meta,
              national, regional, timeline, as_of, covered, recovery_by_incident):
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

    quantified = sum(
        1 for i in incidents
        if i.get("capacity_affected_mw") or i.get("capacity_affected_mtpa")
    )

    regions_out = {}
    for code, meta in region_meta.items():
        r_inc = [i for i in incidents if i.get("region_code") == code]
        struck = {i["asset_id"] for i in r_inc}
        r_live = [x for x in live if x["region_code"] == code]

        disrupted_mw = sum(
            (facility_info[x["asset_id"]].get("capacity_mw") or 0) * x["disruption_weight"]
            for x in r_live
        )
        installed_mw = denominators["regional"][code]["electric_power"]
        disrupted_mtpa = sum(
            (facility_info[x["asset_id"]].get("capacity_mtpa") or 0) * x["disruption_weight"]
            for x in r_live
            if facility_info[x["asset_id"]].get("sector") == "refining"
        )
        thermal_disrupted = sum(
            (facility_info[x["asset_id"]].get("capacity_mw") or 0) * x["disruption_weight"]
            for x in r_live
            if facility_info[x["asset_id"]].get("asset_class") == "power_plant_thermal"
        )
        unresolved = [x for x in r_live if not x["recovery"]["resolved"]]

        effects = {
            "generation_margin": _pct(disrupted_mw, installed_mw),
            "fuel_production": _pct(disrupted_mtpa, denominators["national"]["refining"]),
            "logistics": round(
                sum(x["disruption_weight"] for x in r_live
                    if facility_info[x["asset_id"]].get("sector") == "oil_logistics"), 2
            ),
            "heating_season_exposure": (
                _pct(thermal_disrupted, installed_mw) if heating else 0.0
            ),
            "repair_burden": len(unresolved),
            "recurrence": round(len(r_inc) / len(struck), 2) if struck else 0.0,
        }
        effects.update({k: None for k in NOT_MODELLED})

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
            "installed_mw": round(installed_mw),
            "effects": effects,
        }

    return {
        "as_of": as_of,
        "esdi": national["esdi"][-1],
        "sectors": {s: national["sectors"][s][-1] for s in SECTORS},
        "sectors_covered": covered,
        "sectors_uncovered": [s for s in SECTORS if s not in covered],
        "heating_season": heating,
        "denominators": {
            "refining_mtpa": round(denominators["national"]["refining"], 1),
            "electric_power_mw": round(denominators["national"]["electric_power"]),
        },
        "incident_total": len(incidents),
        "incidents_with_quantified_capacity": quantified,
        "assessed_degradation": _assessed_degradation(incidents, live, facility_info, today),
        "recovery_stats": _recovery_stats(live, incidents, recovery_by_incident, facility_info),
        "coverage_detail": _coverage_detail(incidents),
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


# A median under this many observations is not a meaningful descriptive statistic and
# must not be presented as "typical". Enforced here and honoured by the ribbon.
MIN_MEDIAN_SAMPLE = 3


def _recovery_stats(live, incidents, recovery_by_incident, facility_info):
    """Concept 3: incident-level reconstitution statistics. Medians, not means, with n.

    The observed corpus is counted across ALL incident recovery records, not only the
    incident currently driving a facility's score -- a facility whose latest strike is
    modelled may still contribute an earlier, observed reconstitution to the corpus.
    """
    unresolved = [x for x in live if not x["recovery"]["resolved"]]
    resolved = [x for x in live if x["recovery"]["resolved"]]

    # Corpus counts, over incident records.
    records = [recovery_by_incident[i["incident_id"]] for i in incidents
               if i.get("incident_id") in recovery_by_incident]
    observed_durations, partial_restarts, full_reconstitutions, estimate_records = [], 0, 0, 0
    obs_by_sector = collections.defaultdict(list)
    for i in incidents:
        rec = recovery_by_incident.get(i.get("incident_id"))
        if not rec:
            continue
        _h, kind, _c = recovery.assess(i.get("asset_class"), rec)
        status = rec.get("recovery_status")
        if status == "partial_restart":
            partial_restarts += 1
        if status == "fully_reconstituted":
            full_reconstitutions += 1
        if rec.get("estimate_central_days"):
            estimate_records += 1
        if kind == "observed" and rec.get("observed_days"):
            observed_durations.append(rec["observed_days"])
            sector = SECTOR_OF_CLASS.get(i.get("asset_class"))
            if sector:
                obs_by_sector[sector].append(rec["observed_days"])

    ages = [x["recovery"]["impairment_age_days"] for x in unresolved if x["recovery"]["impairment_age_days"] is not None]
    by_kind = collections.Counter(x["recovery"]["scoring_evidence_kind"] for x in live)

    by_sector = {}
    for sector in SECTORS:
        sect_live = [x for x in live if x.get("sector") == sector]
        if not sect_live and sector not in obs_by_sector:
            continue
        sect_obs = obs_by_sector.get(sector, [])
        by_sector[sector] = {
            "disrupted_facilities": len(sect_live),
            "unresolved": sum(1 for x in sect_live if not x["recovery"]["resolved"]),
            "observed_restoration_sample": len(sect_obs),
            "median_observed_restoration_days": _median(sect_obs) if len(sect_obs) >= MIN_MEDIAN_SAMPLE else None,
        }

    n_obs = len(observed_durations)
    median_meaningful = n_obs >= MIN_MEDIAN_SAMPLE
    return {
        "unresolved_count": len(unresolved),
        "resolved_count": len(resolved),
        "min_median_sample": MIN_MEDIAN_SAMPLE,
        # Only expose a median once the corpus is large enough for it to mean anything.
        "median_observed_restoration_days": _median(observed_durations) if median_meaningful else None,
        "median_meaningful": median_meaningful,
        "observed_restoration_sample": n_obs,
        "observed_restoration_values": sorted(int(d) for d in observed_durations),
        "median_impairment_age_days": _median(ages) if len(ages) >= MIN_MEDIAN_SAMPLE else None,
        "impairment_age_sample": len(ages),
        "partial_restart_count": partial_restarts,
        "full_reconstitution_count": full_reconstitutions,
        "estimate_record_count": estimate_records,
        "recovery_record_count": len(records),
        "evidence_kind_counts": dict(by_kind),
        "by_sector": by_sector,
        "note": (
            "Recovery is tracked per incident. Median rather than mean, and suppressed "
            f"below n={MIN_MEDIAN_SAMPLE} so a median-of-one is never shown as 'typical'. "
            "'modelled' scoring means no credible source-reported timing exists and the "
            "generic per-sector assumption was used; a partial restart is recorded but "
            "never treated as full reconstitution."
        ),
    }


def _coverage_detail(incidents):
    """Concept 4: transparent, categorical coverage — never a fabricated confidence interval.

    Splits observed event counts by year, sector, region and cause so a reader can see
    where the record is thin. A low count is explicitly ambiguous between low disruption
    and low reporting; that ambiguity is stated, not resolved with false precision.
    """
    def bucket(key):
        c = collections.Counter()
        for i in incidents:
            c[key(i)] += 1
        return dict(sorted(c.items()))

    return {
        "by_year": bucket(lambda i: i["date"][:4]),
        "by_sector": bucket(lambda i: SECTOR_OF_CLASS.get(i.get("asset_class"), "other")),
        "by_cause": bucket(lambda i: i.get("cause") or "unknown"),
        "by_district": bucket(lambda i: i.get("_district") or "unknown"),
        "note": (
            "Counts of enumerated events only. A low count may mean genuinely low "
            "disruption OR thin open-source reporting for that bucket; this dataset "
            "cannot always distinguish the two, and does not pretend to."
        ),
    }


def _pct(part, whole):
    return round(part / whole * 100, 2) if whole else 0.0
