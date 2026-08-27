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


def _weight_at(incident, when):
    """Decayed contribution of one incident at a point in time, in [0, 1]."""
    when_date = when
    occurred = _incident_date(incident)
    if occurred > when_date:
        return 0.0

    conf = SCORING["confidence_weights"].get(incident.get("confidence") or "possible", 0.45)
    cause = SCORING["cause_weights"].get(incident.get("cause") or "unknown", 0.7)
    status = SCORING["status_multipliers"].get(incident.get("status") or "unknown", 1.0)

    half_lives = SCORING["repair_half_life_days"]
    half_life = half_lives.get(incident.get("asset_class"), half_lives["_default"])

    days = (when_date - occurred).days
    decay = 0.5 ** (days / half_life)

    value = conf * cause * status * decay
    return value if value >= SCORING["cutoff"]["min_contribution"] else 0.0


def build(incidents, facilities, assets, refinery_total_mtpa, region_meta, as_of):
    """Return (national_series, regional_series, snapshot)."""
    step = SCORING["timeline"]["step_days"]
    timeline = _dates(WINDOW_START, as_of, step)

    facility_info = _facility_registry(facilities, incidents, assets)
    denominators = _denominators(assets, refinery_total_mtpa, region_meta)

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
            weight = max((_weight_at(i, when) for i in incs), default=0.0)
            if weight <= 0:
                continue
            share = _share(info, denominators)
            if share <= 0:
                continue
            nat_sector[info["sector"]] += share * weight
            if info["region_code"]:
                reg_sector[info["region_code"]][info["sector"]] += share * weight

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
        region_meta, national, regional, timeline, as_of, covered,
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

    nat["refining"] = refinery_total_mtpa

    for a in assets:
        sector = SECTOR_OF_CLASS.get(a["asset_class"])
        if sector != "electric_power":
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


def _snapshot(incidents, by_facility, facility_info, denominators, region_meta,
              national, regional, timeline, as_of, covered):
    today = dt.date.fromisoformat(as_of)
    heating = today.month in SCORING["heating_season_months"]

    live = []
    for asset_id, incs in by_facility.items():
        w = max((_weight_at(i, today) for i in incs), default=0.0)
        if w > 0:
            info = facility_info.get(asset_id, {})
            live.append(
                {
                    "asset_id": asset_id,
                    "name": info.get("name"),
                    "asset_class": info.get("asset_class"),
                    "region_code": info.get("region_code"),
                    "disruption_weight": round(w, 3),
                    "event_count": len(incs),
                    "latest": max(i["date"] for i in incs),
                }
            )
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
            "repair_burden": len(r_live),
            "recurrence": round(len(r_inc) / len(struck), 2) if struck else 0.0,
        }
        effects.update({k: None for k in NOT_MODELLED})

        regions_out[code] = {
            "code": code,
            "name": meta["name"],
            "district": meta["district"],
            "country": meta["country"],
            "esdi": regional[code]["esdi"][-1],
            "sectors": {s: regional[code]["sectors"][s][-1] for s in SECTORS},
            "incident_count": len(r_inc),
            "struck_facility_count": len(struck),
            "live_disruption_count": len(r_live),
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
        "live_disruptions": live[:60],
        "regions": regions_out,
        "not_modelled": NOT_MODELLED,
    }


def _pct(part, whole):
    return round(part / whole * 100, 2) if whole else 0.0
