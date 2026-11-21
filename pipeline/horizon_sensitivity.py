"""How much of the headline rests on the modelled reconstitution horizon.

WHY THIS EXISTS.

When this was written (iteration 13), decomposing the index by the evidence kind driving each
facility's decay gave roughly 97% modelled, 2% sourced-estimate, 0.1% observed; the current split
is served beside the sweep as `evidence_kind_counts`. The transmission saturation constant
shipped a six-point sweep, a concentration split, four alternative models and a review verdict;
how much transmission moves the headline is computed below each build, not written down here. The refinery reconstitution horizon, worth almost
the whole number, shipped no sensitivity anywhere: not in the snapshot, not in data_quality,
not in the frontend. METHODOLOGY.md calls these horizons "the single largest lever" and
`cannot_tell_you` says the decline "is modelled decay, not evidence of repair". Both true,
neither quantified.

That is this project's own standard -- state your uncertainty at the same visual weight as the
headline -- not being met at the one place it matters most.

HOW. The sweep re-runs `build_index.build` with the modelled fallback horizons scaled, so it
measures the real scoring model rather than a reimplementation of it. `history_series` carries
a comment that the comparison series is kept inside the scoring loop precisely so it "can never
become a second scoring model"; the same reasoning applies here, and re-running the one builder
is the cheap way to honour it (no network, a few seconds).

This is a SENSITIVITY, not a tuning knob and not an alternative observation. The declared
horizons are unchanged.
"""

from pipeline import recovery

# Multipliers on the declared modelled horizons. Chosen to bracket the declared value by half
# and double, which is the honest width of an assumption nothing observed supports.
SCALES = (0.5, 0.67, 1.0, 1.5, 2.0)


def sweep(build_index, build_kwargs):
    """[{scale, horizons_days, esdi}] across SCALES, from the real builder.

    `recovery.FALLBACK` is read once at import, so scaling it in place is what reaches the
    scoring path. Restored in a finally block: a sensitivity that leaves the model altered
    would be the worst possible version of this.
    """
    declared = dict(recovery.FALLBACK)
    out = []
    try:
        for scale in SCALES:
            for cls, days in declared.items():
                if isinstance(days, (int, float)):
                    recovery.FALLBACK[cls] = days * scale
            national = build_index.build(**build_kwargs)[0]
            out.append({
                "scale": scale,
                "refinery_horizon_days": round(declared.get("refinery", 0) * scale, 1),
                "esdi": national["esdi"][-1],
            })
    finally:
        recovery.FALLBACK.clear()
        recovery.FALLBACK.update(declared)
    return out


def _comparison(lo, hi, snapshot):
    """The horizon sweep's width beside what removing transmission would move, both from this
    build. The sentence used to say transmission was "worth under one index point" as a fixed
    fact; that was true only on the day it was written (iteration 23, ESDI-06)."""
    span = round(hi - lo, 2)
    ex_tx, esdi = snapshot.get("esdi_excluding_transmission"), snapshot.get("esdi")
    if ex_tx is None or esdi is None:
        tx = "The transmission comparison is not available in this build."
    else:
        tx = (f"Removing transmission from the headline altogether would move it by "
              f"{abs(ex_tx - esdi):.2f} points, and transmission ships a saturation sweep, four "
              "alternative models and a review verdict.")
    return (f"Halving and doubling the modelled horizons spans {span:.2f} index points. {tx} "
            "The horizon assumption shipped no sensitivity at all until iteration 13.")


def build(build_index, build_kwargs, snapshot):
    rows = sweep(build_index, build_kwargs)
    declared = [r for r in rows if r["scale"] == 1.0][0]
    lo, hi = min(r["esdi"] for r in rows), max(r["esdi"] for r in rows)
    kinds = ((snapshot.get("recovery_stats") or {}).get("evidence_kind_counts")
             or (snapshot.get("recovery_stats") or {}).get("by_kind") or {})
    return {
        "parameter": "recovery.sector_fallback_horizon_days",
        "declared_refinery_horizon_days": declared["refinery_horizon_days"],
        "declared_esdi": declared["esdi"],
        "sweep": rows,
        "esdi_range": [lo, hi],
        "evidence_kind_counts": kinds,
        "note": (
            "The modelled reconstitution horizon is an ASSUMPTION, not an observation: no "
            "source says a struck refinery is substantially restored after this many days. "
            "Almost the whole headline decays on it, because observed and estimated recovery "
            "evidence covers only a handful of facilities. Halving and doubling the horizons "
            f"moves the headline between {lo} and {hi} against a declared {declared['esdi']}. "
            "Published as a sensitivity, not a tuning knob — the declared horizons are "
            "unchanged, and the way to narrow this range is recovery evidence, not a better "
            "guess."
        ),
        "why_this_matters_more_than_the_transmission_sweep": _comparison(lo, hi, snapshot),
    }
