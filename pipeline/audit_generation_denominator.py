"""Sensitivity of the ESDI headline to the electric-generation denominator.

    python -m pipeline.audit_generation_denominator

THIS SCRIPT CHANGES NOTHING. It reports. Iteration 10 §22/§32 forbid deploying a corrected
denominator; the point is to size the error, not to fix it silently.

THE FRAMING THAT MATTERS. The obvious reading of the iteration-9 finding is "WRI carries ~23 GW
that GEM says is retired, so subtract 23 GW". That reading is wrong in both directions:

  - WRI's Russian fleet tops out at commissioning year 2018 with generation data ending 2019, and
    its `year_of_capacity_data` column is empty for every Russian row. So it also MISSES everything
    commissioned 2019-2026.
  - GEM's operating status is an AUGUST 2026 observation. Applying it across a 2022-2026 index
    series would assert that a plant retired in 2024 was already gone in 2022.

The denominator is therefore not one number that is wrong by 23 GW. It is a CENSUS AT A DATE, and
the index needs the census as it stood at each scoring date. That needs per-unit commissioning and
retirement YEARS, which neither source in this repo currently supplies. See the `historical`
section of the output for exactly what is missing and what file would close it.
"""

import json
from pathlib import Path

from pipeline.util import log

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "data" / "processed" / "snapshot.json"
SCORING = ROOT / "methodology" / "scoring.json"

# From docs/POWER_SOURCE_RECONCILIATION.md, measured in iteration 9 against GEM's Global
# Integrated Power Tracker (August 2026) for Russia + Belarus. Reproduced here as the sensitivity
# INPUT, not as a new denominator.
GEM_AUG_2026 = {
    "operating_mw": 251687,
    "retired_mw": 22831 + 160,      # Russia + Belarus
    "mothballed_mw": 50,
    "wri_comparable_mw": 236755,    # WRI RU+BLR on the same technology split
}


def composite(sector_scores, weights):
    """Renormalised weighted mean over sectors that carry a denominator (score is not None)."""
    covered = {k: v for k, v in sector_scores.items() if v is not None}
    total_w = sum(weights[k] for k in covered)
    if not total_w:
        return 0.0
    return sum(weights[k] * v for k, v in covered.items()) / total_w


def run():
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    weights = json.loads(SCORING.read_text(encoding="utf-8"))["sector_weights"]

    sectors = dict(snap["sectors"])
    denom_now = snap["denominators"]["electric_generation_mw"]
    gen_now = sectors["electric_generation"]

    # `gas` and `coal` sit at 0.0 because they are UNCOVERED, not because they are undisrupted;
    # the published composite renormalises over covered sectors only. Reproduce that exactly, or
    # the sensitivity is measured against the wrong baseline.
    covered = {k: v for k, v in sectors.items() if k in snap["sectors_covered"]}
    baseline = composite(covered, weights)

    # The sector score is a capacity SHARE: disrupted / installed. It is therefore exactly
    # inversely proportional to the denominator, so a scenario is a single multiplication.
    disrupted_mw = gen_now / 100.0 * denom_now

    scenarios = {
        "published (WRI, ~2018 census)": denom_now,
        "GEM Aug-2026 operating basis": GEM_AUG_2026["operating_mw"],
        "WRI less GEM-retired (the naive '-23 GW' fix)": denom_now - GEM_AUG_2026["retired_mw"],
        "hypothetical: generation denominator halved": denom_now / 2,
        "hypothetical: generation disruption forced to zero": None,
    }

    log("generation-denominator sensitivity")
    log(f"  published ESDI                {snap['esdi']}")
    log(f"  recomputed from sectors       {baseline:.4f}   (arithmetic check)")
    log(f"  published generation score    {gen_now}%  on {denom_now:,} MW")
    log(f"  implied disrupted capacity    {disrupted_mw:,.0f} MW")
    log("")
    results = {}
    for label, d in scenarios.items():
        alt = dict(covered)
        alt["electric_generation"] = 0.0 if d is None else (disrupted_mw / d * 100.0)
        esdi = composite(alt, weights)
        results[label] = {
            "denominator_mw": None if d is None else round(d),
            "generation_score": round(alt["electric_generation"], 4),
            "esdi": round(esdi, 4),
            "delta_vs_published": round(esdi - baseline, 4),
        }
        d_txt = "n/a" if d is None else f"{d:>9,.0f} MW"
        log(f"  {label:46s} {d_txt}  gen={alt['electric_generation']:.4f}%  "
            f"ESDI={esdi:.4f}  Δ={esdi - baseline:+.4f}")

    # The bound that settles it: even deleting the sector entirely.
    worst = max(abs(r["delta_vs_published"]) for r in results.values())
    log("")
    log(f"  MAXIMUM movement across every scenario, including zeroing the sector: {worst:+.4f}")
    log(f"  headline is published to 2 dp, so the denominator "
        f"{'CANNOT' if worst < 0.005 else 'CAN'} change it")
    return {"baseline_esdi": round(baseline, 4), "published_esdi": snap["esdi"],
            "disrupted_mw": round(disrupted_mw), "scenarios": results,
            "max_abs_delta": round(worst, 4)}


def sweep():
    """The same sensitivity across EVERY timestep, nationally and regionally.

    Today's aggregate is one point in a 245-step series. If generation disruption was materially
    larger at some point in 2022-2026 than it is now, the "analytically inert" conclusion holds
    for today and fails for that period — so the claim is only worth making after the whole
    series has been checked.

    Scenario: multiply the denominator. Because the sector score is a capacity SHARE, that is
    exactly equivalent to dividing the score, and it needs no synthetic historical fleet.
    """
    weights = json.loads(SCORING.read_text(encoding="utf-8"))["sector_weights"]
    nat = json.loads((ROOT / "data" / "processed" / "index_national.json").read_text(encoding="utf-8"))
    reg = json.loads((ROOT / "data" / "processed" / "index_regional.json").read_text(encoding="utf-8"))
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    covered = set(snap["sectors_covered"])

    # Bracket the plausible correction, plus the absolute bound of deleting the sector.
    factors = {
        "GEM Aug-2026 operating basis": GEM_AUG_2026["operating_mw"] / snap["denominators"]["electric_generation_mw"],
        "WRI less GEM-retired": (snap["denominators"]["electric_generation_mw"]
                                 - GEM_AUG_2026["retired_mw"]) / snap["denominators"]["electric_generation_mw"],
        "denominator halved (bound)": 0.5,
        "sector deleted (absolute bound)": None,
    }

    def per_scenario(dates, sectors):
        """-> {scenario: (max_abs_delta, date)}. Per SCENARIO, because the outer bounds and the
        realistic corrections answer different questions and averaging them hides both."""
        gen = sectors.get("electric_generation") or []
        worst = {k: (0.0, None) for k in factors}
        for i, d in enumerate(dates):
            base = {k: v[i] for k, v in sectors.items() if k in covered and i < len(v)}
            if not base:
                continue
            b = composite(base, weights)
            for name, f in factors.items():
                alt = dict(base)
                alt["electric_generation"] = 0.0 if f is None else (gen[i] / f if f else 0.0)
                delta = abs(composite(alt, weights) - b)
                if delta > worst[name][0]:
                    worst[name] = (delta, d)
        return worst

    nat_scen = per_scenario(nat["dates"], nat["sectors"])
    dates = reg["dates"]
    reg_scen = {k: (0.0, None, None) for k in factors}
    for code, r in reg["regions"].items():
        w = per_scenario(dates, r["sectors"])
        for name, (delta, d) in w.items():
            if delta > reg_scen[name][0]:
                reg_scen[name] = (delta, code, d)

    # Would any regional ORDERING flip? Check at EVERY step, not only the last: the ordering that
    # matters is the one a reader saw on the day.
    ranking_changed_at = None
    for i in range(len(dates)):
        def rank(factor):
            vals = []
            for code, r in reg["regions"].items():
                base = {k: v[i] for k, v in r["sectors"].items() if k in covered and i < len(v)}
                if not base:
                    continue
                gen = (r["sectors"].get("electric_generation") or [0])[i]
                base["electric_generation"] = 0.0 if factor is None else (gen / factor if factor else 0.0)
                vals.append((round(composite(base, weights), 2), code))
            return [c for _, c in sorted(vals, key=lambda t: (-t[0], t[1]))]
        b = rank(1.0)
        if any(rank(f) != b for f in factors.values()):
            ranking_changed_at = dates[i]
            break

    log("")
    log("full-series sweep — 245 national steps, 80 regions, per scenario")
    log("  scenario                              max |dESDI| national (date)     max regional (region, date)")
    for name in factors:
        nd, ndate = nat_scen[name]
        rd, rcode, rdate = reg_scen[name]
        log(f"  {name:36s} {nd:8.4f} {str(ndate):12s}  {rd:8.4f} {str(rcode)} {str(rdate)}")
    realistic = max(nat_scen["GEM Aug-2026 operating basis"][0],
                    nat_scen["WRI less GEM-retired"][0],
                    reg_scen["GEM Aug-2026 operating basis"][0],
                    reg_scen["WRI less GEM-retired"][0])
    bound = max(v[0] for v in nat_scen.values()) 
    log("")
    log(f"  worst REALISTIC correction anywhere in the series : {realistic:.4f}")
    log(f"  outer BOUND (halved / sector deleted)             : {bound:.4f}")
    log(f"  regional ranking first changes on                 : {ranking_changed_at}")
    log(f"  realistic correction moves a 2dp displayed value  : {realistic >= 0.005}")
    log(f"  outer bound moves a 2dp displayed value           : {bound >= 0.005}")
    return {
        "national": {k: {"max_abs_delta": round(v[0], 4), "at": v[1]} for k, v in nat_scen.items()},
        "regional": {k: {"max_abs_delta": round(v[0], 4), "region": v[1], "at": v[2]}
                     for k, v in reg_scen.items()},
        "worst_realistic": round(realistic, 4),
        "outer_bound": round(bound, 4),
        "ranking_changed_at": ranking_changed_at,
        "realistic_moves_displayed_value": bool(realistic >= 0.005),
    }


if __name__ == "__main__":
    run()
    sweep()
