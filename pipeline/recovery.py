"""Incident-level recovery / reconstitution model (iteration 2).

Iteration 1 attached recovery evidence to *facilities*. That smears a single recovery
assessment across every strike a facility ever took. Iteration 2 attaches it to
*incidents*: each disruption has its own trajectory, and recovery from one strike never
resolves a later one. A facility hit four times has four independent recovery states.

Evidence precedence is RULE-BASED, not confidence-as-a-multiplier (see
`recovery_precedence` in methodology/scoring.json):

  observed full reconstitution (conf >= min)  -> closes the incident (cap at residual)
  observed substantial restoration (conf>=min)-> observed days become the horizon
  credible sourced estimate (conf >= min)      -> estimate central becomes the horizon
  partial restart                              -> DISPLAY ONLY; never implies full recovery
  low-confidence estimate (conf < min)         -> shown, but does not drive the decay
  otherwise                                    -> modelled sector fallback

The distinction the brief insists on: "operations resumed" is a partial_restart, not a
full reconstitution. A restart is recorded and shown, but it never drives impairment to
the residual and never invents a restored-capacity percentage.
"""

import datetime as dt

from pipeline.config import CURATED, METHODOLOGY_DIR
from pipeline.util import log, read_csv, read_json

_SCORING = read_json(METHODOLOGY_DIR / "scoring.json")
_R = _SCORING["recovery"]
_P = _SCORING["recovery_precedence"]

RESIDUAL = _R["reconstitution_residual"]
FACTOR = _R["horizon_to_halflife_factor"]
FALLBACK = _R["sector_fallback_horizon_days"]

_CONF_RANK = _P["confidence_rank"]
_MIN_OVERRIDE = _CONF_RANK[_P["min_confidence_to_override"]]
_CLOSES = set(_P["closes_incident_states"])
_HORIZON_STATES = set(_P["horizon_override_states"])
VALID_STATES = set(_P["recovery_states"])

# Concept A (iteration 7): initial DAMAGE severity, applied orthogonally to recovery.
_DAMAGE_SEVERITY = _SCORING.get("damage_severity", {"unknown": 1.0, "_default": 1.0})
_DAMAGE_DEFAULT = _DAMAGE_SEVERITY.get("_default", 1.0)


def damage_severity(status):
    """Concept A: the incident's INITIAL damage severity, in (0, 1]. Applied ALWAYS and
    independently of any recovery record — recovery evidence changes the decay/cap (concepts
    B/C), never this multiplier. That orthogonality is what makes adding a recovery record
    monotonic: it can only speed decay or cap the tail, never strip this multiplier.

    'repaired'/'restored' are RECOVERY states, not damage states — they belong in a recovery
    record, are not keys in the damage_severity map, and fall through to the 1.0 default. A
    test rejects an incident whose status contradicts its recovery record.
    """
    return _DAMAGE_SEVERITY.get((status or "unknown"), _DAMAGE_DEFAULT)


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
    """Return {incident_id: record}. Every row must cite at least one source.

    Backward compatible: a legacy row keyed only by `asset_id` (no `incident_id`) is
    accepted and flagged, so the older facility-level file still loads, but new records
    should be incident-keyed.
    """
    path = CURATED / "recovery.csv"
    if not path.exists():
        return {}
    out = {}
    for row in read_csv(path):
        incident_id = row.get("incident_id") or row.get("asset_id")
        if not incident_id:
            continue
        urls = [u for u in (row.get("source_urls") or "").split("|") if u]
        if not urls:
            log(f"  WARN recovery record for {incident_id} has no source URL; skipped")
            continue
        status = (row.get("recovery_status") or row.get("status") or "unknown").strip()
        if status not in VALID_STATES:
            # Map legacy iteration-1 statuses onto the new state vocabulary.
            status = {"repaired": "fully_reconstituted", "active": "impaired",
                      "degraded": "partial_restart"}.get(status, "unknown")
        out[incident_id] = {
            "incident_id": incident_id,
            "recovery_status": status,
            # §13: granular description of what the source establishes (flow_rerouted,
            # partial_line_energised, unit_restarted, station_rebuilt, throughput_restored…).
            # Free-vocabulary, display-only; never widens the scoring bucket above.
            "recovery_kind": (row.get("recovery_kind") or "").strip() or None,
            # §15: which EVIDENCE FAMILY this restart belongs to (service restoration vs unit
            # restart vs physical reconstitution vs flow rerouting vs estimate). Derived, so a
            # curator sets recovery_status + recovery_kind and this stays consistent.
            "evidence_family": evidence_family(status, (row.get("recovery_kind") or "").strip()),
            # §31: lightweight source-quality tier for triage/provenance — NOT a hidden
            # confidence score; occurrence confidence stays separate (source_confidence).
            "source_quality": (row.get("source_quality") or "").strip() or None,
            "source_confidence": (row.get("source_confidence") or "unknown").strip(),
            "observed_date": row.get("observed_date") or row.get("reconstituted_at"),
            "observed_days": _num(row.get("observed_days")) or _num(row.get("reconstitution_observed_days")),
            "partial_operations_resumed_at": row.get("partial_operations_resumed_at"),
            "partial_or_full": row.get("partial_or_full"),
            "estimate_lower_days": _num(row.get("est_lower_days")),
            "estimate_central_days": _num(row.get("est_central_days")),
            "estimate_upper_days": _num(row.get("est_upper_days")),
            "estimate_basis": row.get("estimate_basis"),
            "estimate_method": row.get("estimate_method"),
            "what_source_establishes": row.get("what_source_establishes") or row.get("evidence"),
            "source_types": [t for t in (row.get("source_types") or "").split("|") if t],
            "sources": [{"url": u} for u in urls],
        }
    log(f"recovery: {len(out)} incident recovery records")
    return out


# §15 evidence families — what KIND of restoration the source actually established. Kept
# separate so the UI never collapses a service re-energisation and a physical rebuild into one
# "recovery" number. Derived from (recovery_status, recovery_kind), never a stored duplicate.
_SERVICE_KINDS = {"grid_reenergised", "partial_line_energised", "loadings_resumed",
                  "partial_operations_resumed", "interim_restart", "service_restored"}
_FLOW_KINDS = {"flow_rerouted"}
_UNIT_KINDS = {"unit_restarted", "primary_unit_repaired", "throughput_restored", "capacity_restored"}
_RECON_KINDS = {"unit_rebuilt", "substation_rebuilt", "transformer_replaced", "primary_unit_offline"}

EVIDENCE_FAMILIES = ("facility_reconstitution", "unit_restart", "service_restoration",
                     "flow_rerouting", "estimate", "unknown")


def evidence_family(recovery_status, recovery_kind):
    """Map a recovery record to its evidence family (§15). Physical reconstitution is only ever
    claimed when the source proves the damaged equipment itself returned — a service/flow
    restart never counts as facility repair."""
    k = (recovery_kind or "").strip()
    if recovery_status == "impaired":
        return "estimate"
    if recovery_status == "fully_reconstituted":
        return "facility_reconstitution"
    if k in _FLOW_KINDS:
        return "flow_rerouting"
    if k in _RECON_KINDS:
        return "facility_reconstitution"
    if k in _UNIT_KINDS:
        return "unit_restart"
    if k in _SERVICE_KINDS:
        return "service_restoration"
    if recovery_status == "substantially_restored":
        return "unit_restart"
    if recovery_status == "partial_restart":
        return "service_restoration"
    return "unknown"


def _conf_ok(record):
    return _CONF_RANK.get(record.get("source_confidence"), 0) >= _MIN_OVERRIDE


def assess(asset_class, record):
    """Resolve the effective (horizon_days, scoring_kind, closes) for an incident.

    scoring_kind is observed / estimated / modelled — what actually drives the decay.
    closes is True when a credible full reconstitution should cap impairment at residual.
    """
    fallback = FALLBACK.get(asset_class, FALLBACK["_default"])
    if not record:
        return fallback, "modelled", False

    status = record.get("recovery_status")
    conf_ok = _conf_ok(record)

    if conf_ok and status in _CLOSES:
        # Full reconstitution, credibly sourced: horizon from observed days if present,
        # and the incident is closed (capped at residual after the observed date).
        days = record.get("observed_days")
        return (days if days and days > 0 else fallback), "observed", True

    if conf_ok and status in _HORIZON_STATES and record.get("observed_days"):
        return record["observed_days"], "observed", False

    est = record.get("estimate_central_days")
    if conf_ok and est and est > 0:
        return est, "estimated", False

    # partial_restart, low-confidence estimate, impaired, unknown -> modelled scoring.
    return fallback, "modelled", False


def effective_half_life(asset_class, record):
    horizon, kind, _closes = assess(asset_class, record)
    return horizon / FACTOR, kind


def scoring_kind(asset_class, record):
    return assess(asset_class, record)[1]


def is_resolved(record, when, asset_class=None):
    """True if a credible full reconstitution was reached by `when`.

    Only a fully_reconstituted status at/above the confidence threshold, with a date
    that has passed, counts. Nothing else — and never a generic decay — resolves an
    incident. Absence of reporting is not evidence of recovery.
    """
    if not record:
        return False
    if record.get("recovery_status") not in _CLOSES or not _conf_ok(record):
        return False
    d = _date(record.get("observed_date"))
    return d is not None and when >= d


def partial_restart_date(record, when):
    """Observed partial-restart date if it has occurred by `when` — display only."""
    if not record:
        return None
    d = _date(record.get("partial_operations_resumed_at"))
    return d if d and when >= d else None


def impairment_age_days(incident_date, record, as_of):
    """Days impaired, for UNRESOLVED incidents. Measured to reconstitution if resolved."""
    start = _date(incident_date)
    if not start:
        return None
    if record and is_resolved(record, as_of):
        d = _date(record.get("observed_date"))
        if d:
            return max(0, (d - start).days)
    return max(0, (as_of - start).days)


def has_downweighted_estimate(record):
    """True if a sourced estimate exists but its confidence was too low to drive scoring."""
    if not record:
        return False
    return bool(record.get("estimate_central_days")) and not _conf_ok(record)


# --------------------------------------------------------------------------------------------
# Active-campaign publication policy (iteration 17; docs/OPERATIONAL_STATUS_DELAY_OPTIONS.md)
# --------------------------------------------------------------------------------------------
# Every modelled number the theatre publishes is a function of public strike dates and a fixed
# class horizon: it carries no information about any facility's state today. The one channel
# that does is RECOVERY EVIDENCE: a restart reported last week, or a repair estimate whose
# horizon has not yet closed, says what a struck facility is doing now. During an active
# campaign that is withheld until it is history. Withholding it from the dossier alone would not
# do: a region with one struck facility publishes that facility's state through its regional
# index, and the build ledger would announce the day the evidence arrived. So the record is
# removed before anything reads it, and the index scores the incident on the modelled horizon
# exactly as if no evidence existed yet.

# The words a reader sees on every campaign incident without released evidence (brief §45). On
# EVERY one, not only where a record was actually withheld: a note that appeared only on those
# would itself say which facilities have fresh reporting.
WITHHELD_NOTE = ("Current facility status withheld during active campaign; historical recovery "
                 "evidence may be published later.")

_CAMPAIGN_DAYS = _SCORING.get("campaign_publication", {}).get("evidence_embargo_days")
CAMPAIGNS_FILE = CURATED / "systems" / "conflict_campaigns.json"
THEATRE_SYSTEM = "russia_theatre"


def theatre_campaign():
    """The theatre's campaign entry when it is active and its policy applied, else None."""
    if not CAMPAIGNS_FILE.exists():
        return None
    for c in read_json(CAMPAIGNS_FILE)["campaigns"]:
        if c["system_id"] == THEATRE_SYSTEM and c["status"] == "active" and c.get("policy_applied"):
            return c
    return None


def is_campaign_member(incident, campaign):
    rule = campaign["member_rule"]
    return incident.get("cause") in rule["causes"] and (incident.get("date") or "") >= rule["from"]


def evidence_date(record, incident_date):
    """The latest date the record's evidence describes. An undated record (a status or a
    forecast with no observation date) falls back to the incident date: the source's own
    publication date is not curated, so this is a floor, not the publication date."""
    dates = [d for d in (_date(record.get("observed_date")),
                         _date(record.get("partial_operations_resumed_at"))) if d]
    return max(dates) if dates else _date(incident_date)


def release_date(record, incident_date, embargo_days):
    """First date on which the record may be published and scored during an active campaign.
    None means it can never be released (no date at all): fail closed."""
    ev = evidence_date(record, incident_date)
    if ev is None:
        return None
    release = ev + dt.timedelta(days=embargo_days)
    # A forward repair estimate is a statement about the future: until its upper bound has
    # passed it predicts the facility's state today, however old the article.
    horizon = record.get("estimate_upper_days") or record.get("estimate_central_days")
    start = _date(incident_date)
    if horizon and start:
        release = max(release, start + dt.timedelta(days=int(horizon)))
    return release


def apply_campaign_embargo(records, incidents, as_of, embargo_days=None, campaign="theatre"):
    """Return (records a build at `as_of` may use, policy summary for the snapshot).

    The summary carries a COUNT only. Listing withheld incidents would itself say which
    facilities have fresh recovery reporting."""
    camp = theatre_campaign() if campaign == "theatre" else campaign
    days = _CAMPAIGN_DAYS if embargo_days is None else embargo_days
    if camp is None or days is None:
        return dict(records), {"applied": False, "reason": "no active campaign with the policy applied"}
    when = as_of if isinstance(as_of, dt.date) else dt.date.fromisoformat(as_of)
    inc_by_id = {i["incident_id"]: i for i in incidents}
    kept, withheld = {}, 0
    for iid, rec in records.items():
        inc = inc_by_id.get(iid)
        if inc is None or not is_campaign_member(inc, camp):
            kept[iid] = rec
            continue
        rel = release_date(rec, inc.get("date"), days)
        if rel is not None and rel <= when:
            kept[iid] = rec
        else:
            withheld += 1
    return kept, {
        "applied": True,
        "campaign_id": camp["campaign_id"],
        "evidence_embargo_days": days,
        "rule": ("While the campaign is active, a recovery record for one of its incidents is used "
                 f"only once its evidence is at least {days} days old and any repair estimate it "
                 "carries has run its course. Until then the incident is scored on the modelled "
                 "class horizon and no facility status is shown."),
        "withheld_records": withheld,
    }


def young_campaign_records(records, incidents, today, embargo_days=None):
    """Incident ids whose recovery record is still under embargo TODAY. A current build refuses
    to run while any is in the curated file: the repository is published too, so a record that
    may not be shown may not be committed either. Kept locally until its release date."""
    kept, summary = apply_campaign_embargo(records, incidents, today, embargo_days)
    return sorted(set(records) - set(kept)) if summary["applied"] else []


# An effect reported within this many days of the strike is "the effect reported at the time":
# occurrence, published at once. Reported later, it describes how the facility is doing since --
# status -- and waits like recovery evidence. The same window as a country system's late-citation
# rule (build_systems.LATE_CITATION_DAYS).
AT_THE_TIME_DAYS = 7


def effect_release_date(effect, incident_date, embargo_days):
    start = _date(incident_date)
    seen = _date(effect.get("as_of_date")) or start
    if seen is None:
        return None
    if start and (seen - start).days <= AT_THE_TIME_DAYS:
        return seen
    return seen + dt.timedelta(days=embargo_days)


def embargo_effects(by_incident, incidents, as_of, embargo_days=None):
    """Drop per-incident effects of campaign incidents that are not yet releasable at `as_of`.
    Returns (kept, withheld count, ids still embargoed). National aggregates name no facility
    and are untouched."""
    camp = theatre_campaign()
    days = _CAMPAIGN_DAYS if embargo_days is None else embargo_days
    if camp is None or days is None:
        return by_incident, 0, []
    when = as_of if isinstance(as_of, dt.date) else dt.date.fromisoformat(as_of)
    inc_by_id = {i["incident_id"]: i for i in incidents}
    kept, withheld, ids = {}, 0, set()
    for iid, effects in by_incident.items():
        inc = inc_by_id.get(iid)
        if inc is None or not is_campaign_member(inc, camp):
            kept[iid] = effects
            continue
        ok = []
        for e in effects:
            rel = effect_release_date(e, inc.get("date"), days)
            if rel is not None and rel <= when:
                ok.append(e)
            else:
                withheld += 1
                ids.add(iid)
        if ok:
            kept[iid] = ok
    return kept, withheld, sorted(ids)


def annotate_withheld(live_disruptions, incidents, policy):
    """Put WITHHELD_NOTE on each live disruption whose driving incident belongs to the campaign
    and carries no released recovery evidence (it is scored on the modelled horizon)."""
    camp = theatre_campaign()
    if not policy.get("applied") or camp is None:
        return 0
    inc_by_id = {i["incident_id"]: i for i in incidents}
    n = 0
    for d in live_disruptions:
        r = d.get("recovery") or {}
        inc = inc_by_id.get(r.get("incident_id") or d.get("driving_incident_id"))
        if inc and is_campaign_member(inc, camp) and r.get("scoring_evidence_kind") == "modelled":
            r["publication_note"] = WITHHELD_NOTE
            n += 1
    return n
