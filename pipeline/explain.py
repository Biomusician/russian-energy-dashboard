"""Machine-generated decomposition of every headline number (iteration 11 §2-§6).

WHY THIS LIVES IN THE PIPELINE AND NOT IN REACT. The dashboard asks a reader to trust a composite
built from weights, renormalisation, capacity shares, a saturation proxy, damage multipliers and
time decay. If the frontend re-derived any of that in order to explain it, there would be two
scoring models: the real one and the one shown to the analyst. They would drift, and the
explanation would eventually be a confident lie about a number it no longer describes.

So the decomposition is computed HERE, beside the arithmetic it explains, from the same inputs.
The frontend renders it and does no methodology maths of its own.

THE INVARIANT:

    sum(c["index_points"] for c in headline["contributions"]) == snapshot["esdi"]

Because ESDI = round( Sum_covered(w_s * v_s) / Sum_covered(w_s) * 100, 2 ), each sector's
contribution is exactly w_s * v_s / Sum_covered(w_s) * 100. The identity is structural rather
than fitted, and a test enforces it at 2 dp against the real build.
"""

from pipeline.config import SECTORS


def _r(x, n=2):
    return round(x + 0.0, n)


def headline_explanation(sector_fracs, weights, covered, esdi, as_of, sensitivities):
    """Decompose the national composite into per-sector index points.

    `sector_fracs` are the UNROUNDED fractions the composite was actually built from, not the
    rounded percentages published in `snapshot.sectors`. Using the published ones would inject
    rounding error into an identity that is supposed to be exact.
    """
    total_w = sum(weights[s] for s in covered)
    contributions = []
    exact_total = 0.0
    for s in SECTORS:
        v = min(1.0, sector_fracs.get(s, 0.0))
        included = s in covered
        eff = (weights[s] / total_w) if (included and total_w) else 0.0
        # Accumulate UNROUNDED. Summing the per-sector display values instead lets six 2-dp
        # roundings drift the total off the published headline by a couple of hundredths, which
        # would make the reconciliation look approximate when it is in fact exact.
        exact_total += eff * v * 100
        contributions.append({
            "sector": s,
            "included": included,
            "sector_value": _r(v * 100),
            "nominal_weight": weights[s],
            "effective_weight": _r(eff, 4),
            # The whole point: what this sector adds to the headline, in the headline's own units.
            "index_points": _r(eff * v * 100),
            "excluded_reason": None if included
            else "no capacity denominator; weight redistributed across covered sectors",
        })
    total = _r(exact_total)
    return {
        "value": esdi,
        "as_of": as_of,
        "covered": list(covered),
        "uncovered": [s for s in SECTORS if s not in covered],
        "nominal_weights": {s: weights[s] for s in SECTORS},
        "effective_weights": {c["sector"]: c["effective_weight"] for c in contributions},
        "contributions": contributions,
        "sum_of_contributions": total,
        # Published so a reader can check the identity rather than take it on faith.
        "reconciles": abs(total - esdi) <= 0.02,
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


def sector_explanations(sector_fracs, denominators, snapshot, live, facility_info,
                        share_fn, saturation_events):
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
            share = share_fn(info, denominators)
            rec = x.get("recovery") or {}
            contributing.append({
                "asset_id": x["asset_id"],
                "name": x.get("name"),
                "asset_class": x.get("asset_class"),
                "region_code": x.get("region_code"),
                "driving_incident_id": x.get("driving_incident_id"),
                "disruption_weight": _r(x["disruption_weight"], 4),
                "capacity_share_pct": _r(share * 100, 4),
                # This facility's own addition to the sector value, in sector percentage points.
                "sector_points": _r(share * x["disruption_weight"] * 100, 4),
                "recovery_status": rec.get("recovery_status"),
                "evidence_kind": rec.get("scoring_evidence_kind"),
                "evidence_family": rec.get("evidence_family"),
            })
        contributing.sort(key=lambda c: -c["sector_points"])

        entry = {
            "sector": s,
            "basis": basis[s],
            "value": _r(min(1.0, sector_fracs.get(s, 0.0)) * 100),
            "contributing": contributing,
            "contributing_count": len(contributing),
            "sum_of_contributions": _r(sum(c["sector_points"] for c in contributing)),
            "limitations": [],
            "denominator": None,
        }

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


def regional_explanations(regional, region_meta, weights, covered, sector_fracs_by_region):
    """Per-region decomposition, same identity as the headline. Written to its own lazy file.

    An entry is emitted for EVERY region, not only the ones currently scoring above zero. The
    Inspector has to be able to answer "why is this region at 0.00?" when a reader clicks a quiet
    region, and a missing key would make the UI answer that question by saying nothing.

    Zero is not one state. A region can read 0.00 because nothing there is impaired, or because
    everything impaired there sits in a sector the composite cannot score. `zero_basis` says
    which, so the second case cannot be misread as the first.
    """
    total_w = sum(weights[s] for s in covered)
    uncovered = [s for s in SECTORS if s not in covered]
    out = {}
    for code in region_meta:
        fr = sector_fracs_by_region.get(code) or {}
        contributions = []
        exact_total = 0.0
        for s in covered:
            v = min(1.0, fr.get(s, 0.0))
            eff = (weights[s] / total_w) if total_w else 0.0
            exact_total += eff * v * 100
            contributions.append({
                "sector": s,
                "sector_value": _r(v * 100),
                "effective_weight": _r(eff, 4),
                "index_points": _r(eff * v * 100),
            })
        published = regional[code]["esdi"][-1] if code in regional else 0.0
        total = _r(exact_total)

        # Impairment the composite saw nothing of, because the sector has no denominator.
        unscored = [s for s in uncovered if fr.get(s, 0.0) > 0]
        zero_basis = None
        if total == 0.0:
            zero_basis = ("impairment_present_but_unscorable" if unscored
                          else "no_contributing_facilities")

        out[code] = {
            "code": code,
            "name": (region_meta.get(code) or {}).get("name"),
            "value": published,
            "contributions": contributions,
            "sum_of_contributions": total,
            "reconciles": abs(total - published) <= 0.02,
            "zero_basis": zero_basis,
            "unscored_sectors": unscored,
            "zero_note": (
                "Documented impairment here falls only in " + ", ".join(unscored) + ", which has "
                "no capacity denominator and is excluded from the composite. This region reads "
                "0.00 because the index cannot score it, NOT because nothing happened."
                if zero_basis == "impairment_present_but_unscorable" else
                "No facility in this region is contributing to the index on this date."
                if zero_basis == "no_contributing_facilities" else None
            ),
        }
    return out
