"""Recovery / reconstitution model.

Replaces the flat repair half-life with an evidence-driven one. The core decay is still
`0.5 ^ (days_since_disruption / half_life)`, so the index stays continuous with the MVP,
but the half-life is now chosen by the strongest available evidence:

  observed  -- a source reported how long restoration/reconstitution actually took
  estimated -- a source gave an expected reconstitution window
  modelled  -- neither exists; fall back to the per-sector assumption

The `kind` travels with every number so the UI can render an observed restart and a
modelled guess in visibly different language, and never present one as the other. That
distinction is the whole reason this module exists.

Recovery evidence is carried in data/curated/recovery.csv, one row per facility
(asset_id), describing that facility's most recent recovery assessment. It attaches to
the facility's incidents because reconstitution is a property of the facility returning
to service after its latest damage, not of a single dated event.
"""

import datetime as dt

from pipeline.config import CURATED, METHODOLOGY_DIR
from pipeline.util import log, read_csv, read_json

_SCORING = read_json(METHODOLOGY_DIR / "scoring.json")
_R = _SCORING["recovery"]

RESIDUAL = _R["reconstitution_residual"]
FACTOR = _R["horizon_to_halflife_factor"]
FALLBACK = _R["sector_fallback_horizon_days"]
RESOLVED_STATUSES = set(_R["resolved_statuses"])
PARTIAL_FLOOR = _R["partial_operations_floor"]


def _date(value):
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value if len(value) == 10 else value + "-01")
    except (ValueError, TypeError):
        return None


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_recovery_records():
    """Return {asset_id: record}. Every row must cite at least one source."""
    path = CURATED / "recovery.csv"
    if not path.exists():
        return {}
    out = {}
    for row in read_csv(path):
        asset_id = row.get("asset_id")
        if not asset_id:
            continue
        urls = [u for u in (row.get("source_urls") or "").split("|") if u]
        if not urls:
            log(f"  WARN recovery record for {asset_id} has no source URL; skipped")
            continue
        out[asset_id] = {
            "asset_id": asset_id,
            "status": row.get("status") or "unknown",
            "restoration_started_at": row.get("restoration_started_at"),
            "partial_operations_resumed_at": row.get("partial_operations_resumed_at"),
            "restoration_observed_days": _num(row.get("restoration_observed_days")),
            "reconstituted_at": row.get("reconstituted_at"),
            "reconstitution_observed_days": _num(row.get("reconstitution_observed_days")),
            "reconstitution_level": row.get("reconstitution_level"),
            "estimate_lower_days": _num(row.get("est_lower_days")),
            "estimate_central_days": _num(row.get("est_central_days")),
            "estimate_upper_days": _num(row.get("est_upper_days")),
            "estimate_basis": row.get("estimate_basis"),
            "estimate_method": row.get("estimate_method"),
            "estimate_confidence": row.get("estimate_confidence"),
            "evidence": row.get("evidence"),
            "source_types": [t for t in (row.get("source_types") or "").split("|") if t],
            "sources": [{"url": u} for u in urls],
        }
    log(f"recovery: {len(out)} facility recovery records")
    return out


def effective_horizon(asset_class, record):
    """Return (horizon_days, kind) for an incident's reconstitution.

    kind is one of observed / estimated / modelled, matching the strongest evidence.
    """
    if record:
        obs = record.get("reconstitution_observed_days") or record.get("restoration_observed_days")
        if obs and obs > 0:
            return obs, "observed"
        est = record.get("estimate_central_days")
        if est and est > 0:
            return est, "estimated"
    return FALLBACK.get(asset_class, FALLBACK["_default"]), "modelled"


def effective_half_life(asset_class, record):
    horizon, kind = effective_horizon(asset_class, record)
    return horizon / FACTOR, kind


def recovery_kind(asset_class, record):
    return effective_horizon(asset_class, record)[1]


def is_resolved(record, when):
    """True if credible evidence says the facility was substantially restored by `when`.

    Only an explicit reconstitution date or a resolved status counts. A generic decay
    never marks a facility resolved -- absence of reporting is not evidence of recovery.
    """
    if not record:
        return False
    recon = _date(record.get("reconstituted_at"))
    if recon and when >= recon:
        return True
    if record.get("status") in RESOLVED_STATUSES and record.get("reconstituted_at"):
        return _date(record["reconstituted_at"]) is not None and when >= _date(record["reconstituted_at"])
    return False


def partial_since(record, when):
    """The date partial operations resumed, if that has happened by `when`, else None."""
    if not record:
        return None
    resumed = _date(record.get("partial_operations_resumed_at"))
    return resumed if resumed and when >= resumed else None


def impairment_age_days(incident_date, record, as_of):
    """Days a facility has been impaired, for UNRESOLVED incidents. None if resolved.

    Measured from the disruption to either the reconstitution date (if resolved) or to
    `as_of` (if still unresolved).
    """
    start = _date(incident_date)
    if not start:
        return None
    if record:
        recon = _date(record.get("reconstituted_at"))
        if recon:
            return max(0, (recon - start).days)
    return max(0, (as_of - start).days)


def observed_restoration_days(record):
    """The observed restoration duration, or None. Distinct from the modelled horizon."""
    if not record:
        return None
    return record.get("restoration_observed_days") or record.get("reconstitution_observed_days")
