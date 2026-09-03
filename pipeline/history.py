"""The authoritative historical series for two-date comparison (iteration 11 P6).

THE DISTINCTION THIS FILE EXISTS TO PROTECT (addendum §6). There are two different products a
"compare two dates" feature could be, and confusing them is the single most consequential error
available here:

  HISTORICAL STATE      What does the CURRENT dataset and methodology estimate for the system at
  (this file)           date A versus date B? Every correction, every source added since, and
                        every recovery observation made since is applied to both dates.

  HISTORICAL KNOWLEDGE  What did the dashboard actually say on date A? That would require an
  (NOT this file)       archive of past builds. None exists, and nothing here reconstructs one.

So the comparison answers the first question only, and says so in the payload rather than leaving
a reader to assume the second. A 2026 correction to a 2024 event DOES change this reconstruction
of 2024 — correctly, because our best current estimate of 2024 has improved — but it must never be
presented as something the dashboard knew in 2024.

WHICH TEMPORAL FIELD CONTROLS (addendum §7C, §8). Established by reading the scorer, not chosen
to make this feature easier:

  * An incident contributes only from its own `date` onward. `_weight_at` returns 0 before it.
  * A recovery RESOLVES an incident from `observed_date` — the sourced restoration date, i.e.
    when the facility came back, not when the report appeared. `recovery.is_resolved` gates on it.
  * A recovery record's DURATION evidence sets the decay half-life across the incident's entire
    history, including dates before the restoration occurred.

That last point is deliberate and is exactly the historical-state semantics above: knowing a
refinery took 72 days to restart is our best evidence for how impaired it was on day 30, even
though nobody knew it on day 30. It is emitted as an explicit caveat rather than silently applied.

WHAT THIS FILE DOES NOT DO. It performs no scoring. Every value here is read from the series the
scorer already produced, so the comparison workspace cannot become a second scoring model — the
same rule that governs pipeline/explain.py.
"""

import datetime as dt


def _r(x, n=2):
    return round(x + 0.0, n)


def _d(value):
    """Parse a date the way the SCORER does, month precision included.

    `2023-05` is a real value in this corpus — eight events carry month precision — and the
    scorer anchors those to the first of the month so its decay arithmetic has a day to work
    from. A stricter parser here silently dropped seven of them from the cumulative counts, which
    is precisely the kind of quiet under-report this project exists to avoid. Two parsers for one
    concept is the bug; there is now one rule.
    """
    if value is None:
        return None
    raw = str(value)[:10]
    try:
        return dt.date.fromisoformat(raw if len(raw) == 10 else raw + "-01")
    except (TypeError, ValueError):
        return None


def _cumulative(dates, event_dates):
    """How many of `event_dates` had occurred by each step. Undated events are never counted."""
    parsed = sorted(d for d in (_d(v) for v in event_dates) if d)
    out = []
    i = 0
    for step in dates:
        step_date = _d(step)
        while i < len(parsed) and parsed[i] <= step_date:
            i += 1
        out.append(i)
    return out


def build(dates, timeline_fracs, contributor_ids, weights, covered,
          national, incidents, recovery_events):
    """Per-step decomposition and counts, from the values the scorer already computed."""
    total_w = sum(weights[s] for s in covered)
    sectors = sorted(covered)

    index_points = {s: [] for s in sectors}
    raw_index_points = {s: [] for s in sectors}
    sector_values = {s: [] for s in sectors}
    raw_esdi = []
    for fr in timeline_fracs:
        total = 0.0
        for s in sectors:
            v = min(1.0, fr.get(s, 0.0))
            eff = (weights[s] / total_w) if total_w else 0.0
            pts = eff * v * 100
            total += pts
            raw_index_points[s].append(pts)
            index_points[s].append(_r(pts))
            sector_values[s].append(_r(v * 100))
        raw_esdi.append(total)

    # Evidence counts split by the date that MATTERS for each. An incident counts from when it
    # happened; recovery evidence counts from the restoration it documents, which is the same
    # field the scorer resolves on.
    return {
        "dates": list(dates),
        "step_days": ((_d(dates[1]) - _d(dates[0])).days if len(dates) > 1 else None),
        "covered": sectors,
        "effective_weights": {s: _r((weights[s] / total_w) if total_w else 0.0, 4)
                              for s in sectors},
        "esdi": list(national["esdi"]),
        "raw_esdi": raw_esdi,
        "index_points": index_points,
        "raw_index_points": raw_index_points,
        "sector_values": sector_values,
        "contributing_facilities": [len(c) for c in contributor_ids],
        # Identity, not just a count. "Which facilities stopped contributing between A and B" is
        # a question the comparison must answer exactly, and a count cannot answer it.
        "contributing_asset_ids": [list(c) for c in contributor_ids],
        "incidents_to_date": _cumulative(dates, [i.get("date") for i in incidents]),
        "recovery_evidence_to_date": _cumulative(
            dates, [r.get("evidence_date") for r in recovery_events]),
        "reconstitutions_to_date": _cumulative(
            dates, [r.get("evidence_date") for r in recovery_events
                    if r.get("recovery_status") == "fully_reconstituted"]),
        "semantics": SEMANTICS,
    }


# Emitted with the data so the UI cannot describe the comparison in its own words and drift from
# what the pipeline actually did.
SEMANTICS = {
    "kind": "historical_state_comparison",
    "headline": (
        "Values are reconstructed using the current dataset and methodology at each analytical "
        "date. This is not an archive of what the dashboard knew on those dates."),
    "what_this_answers": (
        "What does today's dataset and model estimate for the system at each date?"),
    "what_this_does_not_answer": (
        "What the dashboard displayed on those dates. No archive of past builds exists, and "
        "nothing here reconstructs one."),
    "controlling_dates": [
        {"concept": "Incident contribution",
         "field": "incident date",
         "rule": "An incident contributes nothing before the date it occurred."},
        {"concept": "Recovery resolution",
         "field": "observed_date (sourced restoration date)",
         "rule": ("An incident is resolved from the date the facility actually came back, not "
                  "from the date the report about it appeared.")},
        {"concept": "Decay rate",
         "field": "recovery duration evidence",
         "rule": ("A recovery record's duration sets the decay half-life across the whole "
                  "history of that incident, including dates before the restoration happened. "
                  "This is intentional: knowing a refinery took 72 days to restart is the best "
                  "evidence for how impaired it was on day 30 — even though nobody knew it "
                  "then. It is a current-estimate reconstruction, not a record of past "
                  "knowledge.")},
    ],
    "delta_convention": (
        "Delta is B minus A. Positive means higher modelled disruption exposure at B; negative "
        "means lower. Neither is by itself evidence of new physical damage or of repair."),
    "series_resolution_note": (
        "The series is computed at fixed intervals. A requested date is resolved to the series "
        "point at or before it, and both the requested and resolved dates are reported so a "
        "weekly point is never mistaken for a daily observation."),
}


def resolve_step(dates, requested):
    """Index of the series point at or before `requested` (addendum §11).

    Returns (index, resolved_date). The caller is expected to surface BOTH the requested and the
    resolved date: presenting a weekly series point as though it were an observation on the
    requested day is a small lie that compounds across a comparison.
    """
    if not dates:
        return None, None
    want = _d(requested)
    if want is None:
        return len(dates) - 1, dates[-1]
    if want <= _d(dates[0]):
        return 0, dates[0]
    lo, hi = 0, len(dates) - 1
    if want >= _d(dates[hi]):
        return hi, dates[hi]
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _d(dates[mid]) <= want:
            lo = mid
        else:
            hi = mid - 1
    return lo, dates[lo]
