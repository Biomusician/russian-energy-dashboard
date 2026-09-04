"""Machine-generated decomposition of every headline number (iteration 11 §2-§6).

WHY THIS LIVES IN THE PIPELINE AND NOT IN REACT. The dashboard asks a reader to trust a composite
built from weights, renormalisation, capacity shares, a saturation proxy, damage multipliers and
time decay. If the frontend re-derived any of that in order to explain it, there would be two
scoring models: the real one and the one shown to the analyst. They would drift, and the
explanation would eventually be a confident lie about a number it no longer describes.

So the decomposition is computed HERE, beside the arithmetic it explains, from the same inputs —
and, for the per-incident factors, by the same function that produced the score.

RAW IS AUTHORITATIVE; DISPLAY IS DERIVED. The contract this file guarantees is

    sum(c["raw_index_points"]) == raw composite        (machine precision)
    round(raw composite, 2)    == published ESDI

Both are exact. The two-decimal figures beside them are a rendering of that arithmetic, and six
independent roundings can leave the displayed components summing a hundredth away from the
displayed total. That residual is published as `display_rounding_residual` and named as rounding.
It is never absorbed into a sector to make the column add up — an explanation that quietly
reassigns a residual has stopped describing the model.

MECHANISMS DIFFER BY SECTOR. Refining, oil logistics and generation divide a facility's capacity
by a national capacity base. Transmission does not: it counts weighted facility-events against a
chosen saturation constant. Emitting both as "share" would tell a reader transmission measures
percent-of-grid-offline, which it does not. Each contribution therefore names its own mechanism
and carries only the fields that mechanism actually has.
"""

from pipeline.config import SECTORS

# How each sector turns a disrupted facility into sector points. Not cosmetic: the Inspector
# renders different fields per mechanism, and conflating them is the specific misreading the
# transmission proxy has always been vulnerable to.
MECHANISM = {
    "refining": "capacity_share",
    "oil_logistics": "capacity_share",
    "electric_generation": "capacity_share",
    "transmission": "event_burden",
    "gas": "unscored",
    "coal": "unscored",
}

# The four ways a published 0.00 can arise. They are different facts and the UI must be able to
# say which one applies; collapsing them is how UNKNOWN silently becomes ZERO.
ZERO_NO_IMPAIRMENT = "NO_RECORDED_IMPAIRMENT"
ZERO_UNCOVERED_ONLY = "IMPAIRMENT_ONLY_IN_UNCOVERED_SECTOR"
ZERO_ROUNDS_TO_ZERO = "COVERED_SECTOR_SIGNAL_ROUNDS_TO_ZERO"
ZERO_NOT_APPLICABLE = "NOT_APPLICABLE"

ZERO_NOTES = {
    ZERO_NO_IMPAIRMENT:
        "No facility here is contributing to the index on this date. Nothing is recorded as "
        "impaired — which is not the same as a positive finding that nothing is wrong.",
    ZERO_UNCOVERED_ONLY:
        "Documented impairment here falls only in sectors with no capacity denominator, which "
        "are excluded from the composite. This reads 0.00 because the index cannot score it, "
        "NOT because nothing happened.",
    ZERO_ROUNDS_TO_ZERO:
        "There is a real but very small contribution here that rounds to 0.00 at two decimal "
        "places. The raw value is published alongside so it is not mistaken for absence.",
    ZERO_NOT_APPLICABLE:
        "The composite is not defined here: no sector has a usable denominator.",
}


def _r(x, n=2):
    return round(x + 0.0, n)


def _classify_zero(raw_total, unscored_sectors, has_covered_denominator):
    """Which kind of zero a 0.00 is. Returns None when the figure is not actually zero."""
    if _r(raw_total) != 0.0:
        return None
    if not has_covered_denominator:
        return ZERO_NOT_APPLICABLE
    # A real signal too small to survive two-decimal display is not an absence, and saying so
    # is the difference between "nothing here" and "something here, below the resolution shown".
    if raw_total > 0:
        return ZERO_ROUNDS_TO_ZERO
    if unscored_sectors:
        return ZERO_UNCOVERED_ONLY
    return ZERO_NO_IMPAIRMENT


def headline_explanation(sector_fracs, weights, covered, esdi, raw_esdi, as_of, sensitivities):
    """Decompose the national composite into per-sector index points.

    `sector_fracs` are the UNROUNDED fractions the composite was actually built from, not the
    rounded percentages published in `snapshot.sectors`. Using the published ones would inject
    rounding error into an identity that is supposed to be exact at machine precision.
    """
    total_w = sum(weights[s] for s in covered)
    contributions = []
    raw_total = 0.0
    display_total = 0.0
    for s in SECTORS:
        v = min(1.0, sector_fracs.get(s, 0.0))
        included = s in covered
        eff = (weights[s] / total_w) if (included and total_w) else 0.0
        raw_pts = eff * v * 100
        raw_total += raw_pts
        display_pts = _r(raw_pts)
        display_total += display_pts
        contributions.append({
            "sector": s,
            "mechanism": MECHANISM[s],
            "included": included,
            "sector_value": _r(v * 100),
            "raw_sector_value": v * 100,
            "nominal_weight": weights[s],
            "effective_weight": _r(eff, 4),
            "raw_effective_weight": eff,
            # The whole point: what this sector adds to the headline, in the headline's own units.
            "index_points": display_pts,
            "raw_index_points": raw_pts,
            "excluded_reason": None if included
            else "no capacity denominator; weight redistributed across covered sectors",
        })

    residual = _r(display_total - _r(raw_total))
    return {
        "value": esdi,
        "raw_value": raw_esdi,
        "as_of": as_of,
        "covered": list(covered),
        "uncovered": [s for s in SECTORS if s not in covered],
        "nominal_weights": {s: weights[s] for s in SECTORS},
        "effective_weights": {c["sector"]: c["effective_weight"] for c in contributions},
        "contributions": contributions,
        "sum_of_contributions": _r(raw_total),
        "raw_sum_of_contributions": raw_total,
        # What the visible two-decimal column actually adds up to — a different number from the
        # rounded total whenever the individual roundings do not cancel.
        "display_sum_of_contributions": _r(display_total),
        "display_rounding_residual": residual,
        "rounding_note": (
            None if residual == 0.0 else
            f"The two-decimal components above sum to {_r(display_total)}, a difference of "
            f"{residual} from the published {esdi}. That difference is display rounding, not a "
            "missing contribution: the underlying values reconcile exactly."
        ),
        # The authoritative identities. Both are exact; neither carries a tolerance.
        "reconciles_raw": abs(raw_total - raw_esdi) <= 1e-9,
        "reconciles_published": _r(raw_esdi) == esdi,
        # Older field name, kept meaning the same thing: the raw identity holds.
        "reconciles": abs(raw_total - raw_esdi) <= 1e-9,
        "renormalisation_note": (
            "Sectors without a capacity denominator are EXCLUDED and the remaining weights "
            "renormalised, rather than counted as zero. An absent measurement is not evidence "
            "of no disruption."
        ),
        "decay": {
            "form": "contribution x 0.5 ^ (days_elapsed / half_life_days)",
            "half_life_source": (
                "recovery evidence where it exists (observed beats estimated), otherwise a "
                "modelled per-asset-class fallback"
            ),
            "note": (
                "A falling ESDI means modelled impairment decayed with time. That is NOT by "
                "itself evidence that anything was repaired."
            ),
        },
        "sensitivities": sensitivities,
    }


def _contribution_trace(x, info, share, sector, trace):
    """One facility's line in a sector, with the factors that produced it.

    `trace` is the dict `_weight_trace` returned for the incident currently driving this
    facility — the same call that produced the score, not a reconstruction of it.
    """
    mech = MECHANISM.get(sector, "unscored")
    rec = x.get("recovery") or {}
    raw_pts = share * x["disruption_weight"] * 100
    out = {
        "asset_id": x["asset_id"],
        "name": x.get("name"),
        "asset_class": x.get("asset_class"),
        "region_code": x.get("region_code"),
        "driving_incident_id": x.get("driving_incident_id"),
        "mechanism": mech,
        # The impairment multiplier: how damaged, how well attested, how long ago.
        "impairment_weight": _r(x["disruption_weight"], 4),
        # This facility's own addition to the sector value, in sector percentage points.
        "sector_points": _r(raw_pts, 4),
        "raw_sector_points": raw_pts,
        "recovery_status": rec.get("recovery_status"),
        "evidence_kind": rec.get("scoring_evidence_kind"),
        "evidence_family": rec.get("evidence_family"),
    }

    if mech == "capacity_share":
        out["capacity_share_pct"] = _r(share * 100, 4)
        out["capacity_basis"] = ("capacity_mtpa" if sector in ("refining", "oil_logistics")
                                 else "capacity_mw")
        out["capacity_value"] = info.get(out["capacity_basis"])
    elif mech == "event_burden":
        # NOT a capacity share, and deliberately not named like one. This facility is one
        # voltage-weighted event counted against a chosen saturation constant.
        out["event_burden_units"] = _r(share * 100, 4)
        out["voltage_kv"] = info.get("voltage_kv")
        out["burden_note"] = (
            "One voltage-weighted facility-event against the saturation constant. This is not a "
            "share of transmission capacity and implies nothing about how much grid is offline."
        )

    if trace:
        out["impairment_trace"] = {
            "confidence_weight": _r(trace["confidence_weight"], 4),
            "cause_weight": _r(trace["cause_weight"], 4),
            "damage_severity": _r(trace["damage_severity"], 4),
            "initial_impairment": _r(trace["initial_impairment"], 4),
            "days_elapsed": trace["days_elapsed"],
            "half_life_days": trace["half_life_days"],
            "half_life_kind": trace["half_life_kind"],
            "decay_factor": _r(trace["decay_factor"], 4),
            "reconstitution_cap_applied": trace["reconstitution_cap_applied"],
            "form": "confidence x cause x damage_severity x 0.5^(days/half_life)",
        }
    return out


def sector_explanations(sector_fracs, denominators, snapshot, live, facility_info,
                        share_fn, saturation_events, trace_fn=None):
    """Per sector: what the denominator is, what is contributing now, and what is wrong with it."""
    basis = {
        "refining": "capacity_mtpa", "oil_logistics": "capacity_mtpa",
        "electric_generation": "capacity_mw", "transmission": "event_burden",
        "gas": "uncovered", "coal": "uncovered",
    }
    dbasis = snapshot.get("denominator_basis") or {}
    out = {}
    for s in SECTORS:
        contributing = []
        for x in live:
            info = facility_info.get(x["asset_id"]) or {}
            if info.get("sector") != s:
                continue
            trace = trace_fn(x["asset_id"], x.get("driving_incident_id")) if trace_fn else None
            contributing.append(
                _contribution_trace(x, info, share_fn(info, denominators), s, trace))
        contributing.sort(key=lambda c: -c["sector_points"])

        raw_value = min(1.0, sector_fracs.get(s, 0.0)) * 100
        raw_sum = sum(c["raw_sector_points"] for c in contributing)
        scored = MECHANISM[s] != "unscored"
        entry = {
            "sector": s,
            "basis": basis[s],
            "mechanism": MECHANISM[s],
            "value": _r(raw_value),
            "raw_value": raw_value,
            "contributing": contributing,
            "contributing_count": len(contributing),
            "sum_of_contributions": _r(raw_sum),
            "raw_sum_of_contributions": raw_sum,
            "limitations": [],
            "denominator": None,
        }
        # A sector reading 0.00 while facilities are live is a rounding artefact, not an absence.
        entry["zero_basis"] = _classify_zero(raw_value, [], scored)
        entry["zero_note"] = ZERO_NOTES.get(entry["zero_basis"]) if entry["zero_basis"] else None

        if s in ("refining", "oil_logistics"):
            rb = dbasis.get("refining_mtpa") or {}
            entry["denominator"] = {
                "value": _r(denominators["national"].get(s, 0), 1),
                "unit": "MTPA",
                "source": rb.get("source"),
                "vintage": rb.get("census_vintage"),
            }
            rr = snapshot.get("refinery_reconciliation") or {}
            if s == "refining":
                entry["denominator"]["facility_count"] = rr.get("denominator_refineries")
                entry["denominator"]["completeness_pct"] = rr.get("denominator_coverage_pct")
                entry["limitations"].append(
                    "The capacity base is Russia-only, while the monitored area also includes "
                    "Belarus and Crimea.")
            else:
                entry["limitations"].append(
                    "Oil logistics has NO published throughput denominator. It borrows the "
                    "refining capacity base as a proxy, so this value is a share of refining "
                    "capacity, not of terminal throughput.")
        elif s == "electric_generation":
            gb = dbasis.get("electric_generation_mw") or {}
            entry["denominator"] = {
                "value": denominators["national"].get(s, 0),
                "unit": "MW",
                "source": gb.get("source"),
                "vintage": gb.get("census_vintage"),
                "known_bias": gb.get("known_bias"),
            }
            entry["limitations"].append(
                "Fleet census vintage " + str(gb.get("census_vintage")) + ", with no retirement "
                "field: it over-counts post-census retirements and misses post-census additions. "
                "See docs/GENERATION_DENOMINATOR_AUDIT.md.")
        elif s == "transmission":
            ts = snapshot.get("transmission_sensitivity") or {}
            entry["proxy_warning"] = "EVENT-BURDEN PROXY - NOT PERCENT OF GRID OFFLINE"
            entry["denominator"] = {
                "value": saturation_events,
                "unit": "weighted concurrent facility-events (saturation constant)",
                "source": "methodology/scoring.json",
                "vintage": None,
            }
            entry["raw_burden"] = ts.get("raw_burden")
            entry["saturation_sweep"] = ts.get("saturation_sweep")
            entry["concentration"] = snapshot.get("transmission_concentration")
            entry["ex_transmission_composite"] = snapshot.get("esdi_excluding_transmission")
            entry["limitations"].append(
                "This is a disruption-burden proxy, not a percentage of the grid offline. There "
                "is no physical-capacity denominator behind it.")
            entry["limitations"].append(
                "The saturation constant is a judgement, not a measurement: the published sweep "
                "moves this sector roughly fourfold across plausible values.")
            entry["limitations"].append(
                "Geographically concentrated - read the concentration split before treating this "
                "as a national signal.")
        else:
            entry["limitations"].append(
                "No capacity denominator exists for this sector, so it is excluded from the "
                "composite and its weight redistributed. Documented strikes in this sector are "
                "NOT scored. Excluded is not the same as zero.")
        out[s] = entry
    return out


def regional_explanations(regional, region_meta, weights, covered, sector_fracs_by_region,
                          raw_composite_fn=None, unscored_by_region=None):
    """Per-region decomposition, same identities as the headline.

    An entry is emitted for EVERY region, not only the ones currently scoring above zero. The
    Inspector has to be able to answer "why is this region at 0.00?" when a reader clicks a quiet
    region, and a missing key would make the UI answer that question by saying nothing.
    """
    total_w = sum(weights[s] for s in covered)
    uncovered = [s for s in SECTORS if s not in covered]
    out = {}
    for code in region_meta:
        fr = sector_fracs_by_region.get(code) or {}
        contributions = []
        raw_total = 0.0
        display_total = 0.0
        for s in covered:
            v = min(1.0, fr.get(s, 0.0))
            eff = (weights[s] / total_w) if total_w else 0.0
            raw_pts = eff * v * 100
            raw_total += raw_pts
            display_total += _r(raw_pts)
            contributions.append({
                "sector": s,
                "mechanism": MECHANISM[s],
                "sector_value": _r(v * 100),
                "raw_sector_value": v * 100,
                "effective_weight": _r(eff, 4),
                "index_points": _r(raw_pts),
                "raw_index_points": raw_pts,
            })
        published = regional[code]["esdi"][-1] if code in regional else 0.0
        raw_published = raw_composite_fn(fr) if raw_composite_fn else raw_total

        # Impairment the composite saw nothing of, because the sector has no denominator.
        #
        # This CANNOT be read off `fr`: a facility in an uncovered sector contributes a share of
        # zero, so the scoring loop drops it before it ever reaches the per-region fractions, and
        # every region looked identically undisturbed. It comes instead from a map the scorer
        # fills in on the way past, which is the only place the difference is still visible.
        ur = (unscored_by_region or {}).get(code) or {}
        unscored = [s for s in uncovered if ur.get(s, 0.0) > 0 or fr.get(s, 0.0) > 0]
        zero_basis = _classify_zero(raw_total, unscored, bool(total_w))

        out[code] = {
            "code": code,
            "name": (region_meta.get(code) or {}).get("name"),
            "value": published,
            "raw_value": raw_published,
            "contributions": contributions,
            "sum_of_contributions": _r(raw_total),
            "raw_sum_of_contributions": raw_total,
            "display_sum_of_contributions": _r(display_total),
            "display_rounding_residual": _r(display_total - _r(raw_total)),
            "reconciles_raw": abs(raw_total - raw_published) <= 1e-9,
            "reconciles": abs(raw_total - raw_published) <= 1e-9,
            "zero_basis": zero_basis,
            "unscored_sectors": unscored,
            "zero_note": ZERO_NOTES.get(zero_basis) if zero_basis else None,
        }
    return out
