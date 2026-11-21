"""What changed in the published data since the previous published build, for every system.

THE QUESTION A READER ASKS. "Something on this page is different from last week. Did something
happen?" Usually nothing happened in the world. Research found an old record, a link was
re-checked, a rule was tightened, or the theatre's index aged by a day. Each of those is a
different fact, and only the categories below may describe them. None of them says "new
disruption today": the country records are found by research, so a record added now can be four
years old, and the panel prints the dates the events happened, never the date we found them as if
it were news.

THE CATEGORIES ARE CLOSED. A change that fits none of them is a build-only change, never a guess at
something more interesting. In particular:

  * a historical backfill is "new published records" with the event dates beside it;
  * a methodology or rule change is never "the country improved";
  * daily decay of the theatre's index is "time decay only", never a source event.

WHAT IT REFUSES TO SAY. No counts: a list of countries with a number beside each is a league table
whatever the caption says, so lists are capped and flagged as truncated rather than counted. For a
system under the active-campaign publication rule (the Gulf systems), a record appears only as the
aggregating surfaces already publish it — date, class, "National" for a campaign-covered record,
and a row key in place of an id that may name the facility. Withdrawn or held records there are
one sentence with no count and no dates, recovery changes are not reported at all, and nothing here
reads the candidate queue: held candidates never reach this file because it is built from published
payloads only.

RECORD LEVEL (iteration 22). Outside the campaign rule a row also carries its record's public id
(`record_id`), so the panel can link to the record on its country page; that id is already in the
address of the record's own "Link to this record". Under the rule nothing changed: no id, for any
record of such a system, covered or not. A withdrawn record carries none anywhere: no page holds it.
A coverage or method change carries a `link` to where the page explains it (a tab of the country,
a section of the home page), never to a record. The impact layer's changes are derived from its two
served artifacts and listed once, apart from any country (`impact_layer`): its first release is one
sentence, a backfilled historical record is told apart from a new event by its own dates, and an
attribution or AI-status change is an update to an existing record, never a new incident.

WHERE THE BASELINE COMES FROM. The last build readers were served that is dated before this one,
read out of git (`lineage.previous_dated_build`, served builds per `lineage.served_builds`), never
the worktree copy. The theatre part re-runs the
theatre's own ledger (`diff_builds.diff`) against that same baseline, so one panel never mixes two
"previous builds".
"""

import datetime as dt
import json

from pipeline import diff_builds, lineage, systems
from pipeline.build_systems import DERIVED_EVENT_FIELDS, RESTRICTING_STATES, TAXONOMY_EXTENSIONS
from pipeline.config import ASSET_CLASSES, SECTORS

SCHEMA_VERSION = 1
PAYLOAD_DIR = lineage.PAYLOAD_DIR

# (id, label, meaning). The order is the order a reader sees them in.
CATEGORIES = (
    ("records_added", "New published records",
     "Records found by research and reviewed before publication. The dates shown are when the events "
     "happened, not when they were found: a record dated before the previous build is the record catching "
     "up, not a new disruption."),
    ("records_withdrawn", "Records withdrawn or held on review",
     "Records the previous build showed and this one does not: withdrawn, or held while a review is "
     "repeated. The record changed, not the world."),
    ("research_coverage", "Research coverage changed",
     "A research pass was logged, the state of a search changed, or published records were re-reviewed. "
     "This describes the search, not events."),
    ("link_health", "Source link health re-checked",
     "Cited pages or registry sources were visited again. A re-check says something about the sources, "
     "not about any event."),
    ("methodology", "Methodology or rule change",
     "How records are admitted, placed, published or scored changed. A rule change can move what is "
     "shown with nothing changing in the world; it never means a country improved or worsened."),
    ("data_correction", "Data correction",
     "A published record's date, place, class, figure, wording or sources were corrected, or a reference "
     "input was edited."),
    ("national_context", "National context updated",
     "National energy statistics were refreshed. Context only: never a disruption record, never part of "
     "an index."),
    ("recovery_evidence", "Recovery evidence added (where publishable)",
     "A report about recovery was added to an existing record. It may describe a restoration long before "
     "this build. Facility status under an active attack campaign is never shown here."),
    # Iteration 22: the global impact layer (global/impacts.json, global/regional_context.json).
    ("impact_record_added", "Impact records added",
     "Reviewed records were added to the global impact layer. A record whose event is more than 30 days "
     "older than its first publication is a historical record found by research (a backfill), not a new event."),
    ("evidence_strengthened", "Evidence strengthened",
     "The evidence-confidence category of an existing impact record rose: more or better public evidence "
     "was found or read. The evidence changed, not the event."),
    ("evidence_weakened", "Evidence weakened",
     "The evidence-confidence category of an existing impact record fell, or the record is now disputed. "
     "The evidence changed, not the event."),
    ("attribution_updated", "Attribution updated",
     "The public attribution status of an existing impact record changed. Not a new incident: what changed "
     "is who is reported to attribute it, and how firmly."),
    ("ai_status_updated", "AI-involvement status updated",
     "What sources say about AI in an existing impact record changed. Not a new incident."),
    ("regional_context_updated", "Regional context updated",
     "Dated, sourced statements in the Gulf and Strait of Hormuz context were added or revised. Context "
     "only: never a disruption record, never part of an index."),
    ("decay_only", "Index moved by time decay only",
     "No input changed. The evaluation date moved and modelled impairment aged. This is not evidence that "
     "anything was repaired."),
    ("build_only", "Build-only change",
     "The site was rebuilt. No published record, rule or context changed."),
)
CATEGORY_IDS = tuple(c[0] for c in CATEGORIES)

# Every category the theatre's ledger can report, and the panel category it is shown as. A new
# ledger category with no entry here fails a test rather than appearing unlabelled.
THEATRE_CATEGORY = {
    "incident_added": "records_added",
    "incident_removed": "records_withdrawn",
    "incident_revised": "data_correction",
    "source_added": "data_correction",
    "asset_added": "data_correction",
    "asset_capacity_revised": "data_correction",
    "asset_inventory_changed": "data_correction",
    "pipeline_registry_changed": "data_correction",
    "source_refresh": "data_correction",
    "recovery_evidence_added": "recovery_evidence",
    "recovery_status_changed": "recovery_evidence",
    "recovery_withheld_campaign_policy": "methodology",
    "denominator_changed": "methodology",
    "denominator_inputs_changed": "methodology",
    "methodology_changed": "methodology",
    "coverage_changed": "research_coverage",
    # A corpus fingerprint moves whenever a live source is re-read, even with nothing new in it.
    # It explains nothing a reader can see, so it is build-only unless a visible change sits beside it.
    "incident_corpus_changed": "build_only",
    "recovery_corpus_changed": "build_only",
}
THEATRE_NOTE = {
    "incident_revised": "Published event records were corrected.",
    "source_added": "Sources were added to published event records.",
    "asset_added": "Facilities were added to the infrastructure inventory.",
    "asset_capacity_revised": "Facility capacities in the inventory were revised.",
    "asset_inventory_changed": "The infrastructure inventory was edited.",
    "pipeline_registry_changed": "The pipeline register was edited.",
    "source_refresh": "A reference source snapshot or the source register was refreshed.",
    "recovery_evidence_added": "Recovery evidence on existing records was added or improved.",
    "recovery_status_changed": "Recovery status on existing records changed on new evidence.",
    "recovery_withheld_campaign_policy": "The active-campaign rule now withholds recovery evidence the previous build showed.",
    "denominator_changed": "A capacity denominator of the index changed.",
    "denominator_inputs_changed": "The inputs to a capacity denominator changed.",
    "methodology_changed": "The scoring method or the campaign classification changed.",
    "coverage_changed": "The benchmark of how much reported activity the record covers changed.",
    "incident_corpus_changed": "Sources were re-read; no published record changed.",
    "recovery_corpus_changed": "Recovery sources were re-read; no published record changed.",
}

ITEM_CAP = 5

# Event fields whose change is a correction a reader would recognise, and the word for each.
FIELD_LABEL = {
    "date": "date", "date_precision": "date", "date_end": "date",
    "region_code": "region", "geography_precision": "region", "regions_affected": "region",
    "asset_class": "class", "cause": "cause", "capacity_affected": "reported figure",
    "summary": "wording", "effect": "wording", "hazard_name": "wording",
    "facility_name": "facility name", "facility_name_local": "facility name", "operator": "operator",
    "episode_id": "episode grouping", "inclusion_basis": "inclusion basis",
    "criterion_met": "inclusion basis", "threshold_basis": "inclusion basis",
}

COMPLETENESS_TEXT = {
    "complete": "every declared source group searched",
    "partial": "systematic search under way",
    "never_systematic": "targeted searches only, no systematic search yet",
}
SECTOR_STATE_TEXT = {
    "SCORED": "scored", "EXPERIMENTAL": "experimental", "CONTEXT_ONLY": "tracked, not scored",
    "INSUFFICIENT_EVIDENCE": "unknown", "NOT_APPLICABLE": "not applicable",
    "NOT_YET_RESEARCHED": "not yet researched",
}
RECOVERY_KIND_TEXT = {
    "full_restart": "full restart reported", "partial_restart": "partial restart only",
    "service_restored": "service restored (physical repair not implied)",
    "partial_restoration": "partial restoration only", "estimate": "estimate only, not an observed restoration",
    "supply_unaffected_statement": "supply-continuity statement, not a facility restart",
    "no_supply_lost": "no supply was lost",
}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _day(iso):
    """A date as the pages print it, at whatever precision it has ("Apr 2026" for a month)."""
    if not iso:
        return "undated"
    parts = str(iso).split("-")
    if len(parts) == 1:
        return parts[0]
    mon = MONTHS[int(parts[1]) - 1]
    return f"{int(parts[2])} {mon} {parts[0]}" if len(parts) > 2 else f"{mon} {parts[0]}"


def _wholly_before(iso, previous_as_of):
    """Whether every day a date of day, month or year precision can mean falls before the previous
    build. Positive evidence only (iteration 23, XL-04): "2026-11" beside a previous build of
    2026-11-19 may be 20 November, so it is not called historical. An unreadable date claims nothing."""
    try:
        return _period_end(iso).isoformat() < previous_as_of
    except (TypeError, ValueError):
        return False


def restricted(prev, curr):
    """Whether a system is under the active-campaign publication rule in either build. Either is
    enough: a change into or out of the rule must not expose what the rule covered."""
    for side in (prev, curr):
        if not side:
            continue
        sys_doc = side.get("system") or {}
        if ((sys_doc.get("campaign_state") or {}).get("state")) in RESTRICTING_STATES:
            return True
        if (sys_doc.get("publication_policy") or {}).get("withheld_records"):
            return True
        if any(e.get("publication") for e in (side.get("events") or {}).get("events") or []):
            return True
    return False


def _labels():
    return {**ASSET_CLASSES, **TAXONOMY_EXTENSIONS["asset_classes"]}


def _item(e, labels, with_id=False):
    """A record as the aggregating surfaces already publish it: no effect, no cause, and
    "National" for a campaign-covered record whatever its own system records.

    `with_id` (iteration 22): outside the campaign rule a record's id is already public on its
    country page ("Link to this record"), so the panel may carry it and link there. It is never
    set for a system under the rule, and a covered record never carries one whatever the caller
    asks: there the id may name the facility, and the row key stands in for it."""
    covered = bool(e.get("publication"))
    region = ("National" if covered else e.get("region_name")
              or ("Multiple regions" if e.get("regions_affected") else "National"))
    item = {"date": e.get("date"), "date_precision": e.get("date_precision") or "day",
            "region": region, "class": labels.get(e.get("asset_class"), e.get("asset_class"))}
    if with_id and not covered and e.get("event_id"):
        item["record_id"] = e["event_id"]
    return item


def _capped(rows):
    rows = sorted(rows, key=lambda r: (str(r[0].get("date")), r[1]))
    return [r[0] for r in rows[:ITEM_CAP]], len(rows) > ITEM_CAP


def _source_urls(e):
    return sorted({s.get("url") for s in e.get("sources") or [] if s.get("url")})


def _record_changes(prev_events, curr_events, previous_as_of, is_restricted, labels):
    out = []
    p = {e["event_id"]: e for e in prev_events if e.get("event_id")}
    c = {e["event_id"]: e for e in curr_events if e.get("event_id")}

    linkable = not is_restricted
    added = [(_item(c[i], labels, with_id=linkable), i) for i in c.keys() - p.keys()]
    if added:
        items, more = _capped(added)
        dates = sorted(str(c[i].get("date")) for i in c.keys() - p.keys())
        # Positive evidence only: a record is "historical" when its own date precedes the previous
        # build. With no previous date the claim cannot be made either way, so it is not made.
        predates = bool(previous_as_of) and all(
            _wholly_before(d, previous_as_of) for d in dates)
        out.append({"category": "records_added", "event_dates": [dates[0], dates[-1]],
                    "all_predate_previous_build": predates, "items": items, "more": more,
                    "notes": []})

    gone = p.keys() - c.keys()
    if gone:
        if is_restricted:
            # Which records, how many and when would tell a reader what review is holding back
            # during an attack campaign. One sentence, nothing countable.
            out.append({"category": "records_withdrawn", "aggregated": True, "notes": [
                "One or more records shown before are not shown now: withdrawn, or held while a review "
                "is repeated. Which and how many are not shown while the attack-campaign publication "
                "rule applies."]})
        else:
            # No id: the record is on no page any more, so there is nothing to link to, and an id
            # withdrawn for what it named should not be repeated here.
            items, more = _capped([(_item(p[i], labels), i) for i in gone])
            out.append({"category": "records_withdrawn", "items": items, "more": more, "notes": []})

    corrected, recovered = [], []
    for i in sorted(p.keys() & c.keys()):
        a, b = p[i], c[i]
        fields = sorted({FIELD_LABEL[f] for f in FIELD_LABEL if a.get(f) != b.get(f)}
                        | ({"sources"} if _source_urls(a) != _source_urls(b) else set()))
        ra, rb = a.get("recovery") or {}, b.get("recovery") or {}
        rec_moved = any(ra.get(k) != rb.get(k) for k in ("research_status", "kind", "date"))
        if is_restricted:
            # Recovery, review and publication-marker changes are invisible here by design: on a
            # campaign record each one is a statement about the facility's current status.
            # Which fields changed is not said either: "wording" or "reported figure" on an attack
            # record is a hint at what the correction concerned.
            if fields:
                corrected.append((_item(b, labels), i))
            continue
        if rec_moved and rb.get("research_status") == "EVIDENCE_FOUND":
            recovered.append(({**_item(b, labels, with_id=True),
                               "recovery_kind": RECOVERY_KIND_TEXT.get(rb.get("kind"), rb.get("kind")),
                               "evidence_date": rb.get("date")}, i))
        elif rec_moved:
            fields = sorted(set(fields) | {"recovery research status"})
        if fields:
            corrected.append(({**_item(b, labels, with_id=True), "fields": fields}, i))
    if corrected:
        items, more = _capped(corrected)
        out.append({"category": "data_correction", "items": items, "more": more, "notes": []})
    if recovered:
        items, more = _capped(recovered)
        out.append({"category": "recovery_evidence", "items": items, "more": more, "notes": []})
    return out


def _pass_key(x):
    return (x.get("date"), x.get("by"), x.get("kind"))


def _system_level_changes(prev_sys, curr_sys, is_restricted=False):
    """Research, link-health, rule and context changes read from the system document."""
    notes = {k: [] for k in ("research_coverage", "link_health", "methodology", "national_context")}
    old_passes = {_pass_key(x) for x in (prev_sys.get("research_log") or {}).get("passes") or []}
    for x in (curr_sys.get("research_log") or {}).get("passes") or []:
        if _pass_key(x) not in old_passes:
            notes["research_coverage"].append(
                f"A {x.get('kind') or 'research'} search pass dated {_day(x.get('date'))} was logged.")
    pf, cf = prev_sys.get("research_freshness") or {}, curr_sys.get("research_freshness") or {}
    if pf.get("completeness") != cf.get("completeness"):
        notes["research_coverage"].append(
            "Search state is now: " + COMPLETENESS_TEXT.get(cf.get("completeness"), str(cf.get("completeness"))) + ".")
    if pf.get("lane_states") != cf.get("lane_states"):
        notes["research_coverage"].append("The search state of one or more source groups changed.")
    if pf.get("covers_full_window") != cf.get("covers_full_window"):
        notes["research_coverage"].append(
            "The searched period now covers the full window." if cf.get("covers_full_window")
            else "The searched period no longer covers the full window.")
    if prev_sys.get("maturity") != curr_sys.get("maturity"):
        notes["research_coverage"].append(
            "Now a research preview: the systematic search is incomplete." if curr_sys.get("maturity") == "research_preview"
            else "No longer a research preview.")
    # Under the campaign rule a re-review is hidden record by record (_record_changes); announcing
    # it here for the whole system would say the same thing, with its date (safety red team,
    # iteration 21). A new record moves this date too, and "new published records" says that.
    if not is_restricted and (curr_sys.get("record_reviewed") or "") > (prev_sys.get("record_reviewed") or ""):
        notes["research_coverage"].append(
            f"Published records were re-reviewed; the latest review is dated {_day(curr_sys.get('record_reviewed'))}.")
    ps = {s.get("sector"): s.get("state") for s in prev_sys.get("sectors") or []}
    for s in curr_sys.get("sectors") or []:
        if s.get("sector") in ps and ps[s.get("sector")] != s.get("state"):
            label = s.get("label") or SECTORS.get(s.get("sector"), s.get("sector"))
            notes["research_coverage"].append(
                f"{label}: now {SECTOR_STATE_TEXT.get(s.get('state'), s.get('state'))}.")
    if prev_sys.get("research_gaps") != curr_sys.get("research_gaps"):
        notes["research_coverage"].append("The stated research gaps were revised.")
    if {s.get("name") for s in prev_sys.get("sources") or []} != {s.get("name") for s in curr_sys.get("sources") or []}:
        notes["research_coverage"].append("The source register was revised.")

    pq, cq = prev_sys.get("citation_quality") or {}, curr_sys.get("citation_quality") or {}
    if cq.get("link_check_date") and cq.get("link_check_date") != pq.get("link_check_date"):
        notes["link_health"].append(f"Cited links were re-checked on {_day(cq.get('link_check_date'))}.")
    old_checked = {s.get("name"): s.get("last_checked") for s in prev_sys.get("sources") or []}
    moved = [s.get("last_checked") for s in curr_sys.get("sources") or []
             if s.get("name") in old_checked and s.get("last_checked")
             and s.get("last_checked") != old_checked[s.get("name")]]
    if moved:
        notes["link_health"].append(f"Registry sources were re-checked; the latest check is dated {_day(max(moved))}.")

    def applied(doc):
        return any(c.get("policy_applied") for c in (doc.get("publication_policy") or {}).get("campaigns") or [])
    if applied(prev_sys) != applied(curr_sys):
        notes["methodology"].append(
            "The attack-campaign publication rule now applies here." if applied(curr_sys)
            else "The attack-campaign publication rule no longer applies here.")
    pg, cg = prev_sys.get("geography") or {}, curr_sys.get("geography") or {}
    if pg.get("precision_policy") != cg.get("precision_policy"):
        notes["methodology"].append("The rule for where records are placed changed.")
    if pg.get("rulings") != cg.get("rulings"):
        notes["methodology"].append("A boundary ruling was revised.")
    if prev_sys.get("reporting_environment") != curr_sys.get("reporting_environment"):
        notes["methodology"].append("The reporting environment was reclassified.")
    if prev_sys.get("profile") != curr_sys.get("profile"):
        notes["national_context"].append("National profile figures were updated.")
    return [{"category": k, "notes": v} for k, v in notes.items() if v]


# Keys that move with the build date, or whose change is reported once for every country in the
# global list. Neither is a change to this one country.
_NOT_THIS_SYSTEM = ("as_of", "inclusion_threshold", "stale_policies")


# Under the campaign rule a change to these is a statement about a facility's current status (its
# recovery block, its review, the count of withheld records). They must not surface even as a
# "wording changed" line, so the build-only comparison does not see them there.
_CAMPAIGN_HIDDEN_EVENT = ("recovery", "review", "publication")
_CAMPAIGN_HIDDEN_SYSTEM = ("event_summary", "recovery_coverage", "publication_policy", "record_reviewed")


# Evidence confidence (iteration 22) is computed from a record's own citations, dates and figure. A
# change in it is either a change in those, which is reported as a correction, or a change of
# method, which is reported once for every country. It is never a change to this one country.
_DERIVED_EVENT = DERIVED_EVENT_FIELDS
_DERIVED_SYSTEM = ("evidence_confidence_summary",)


def _comparable(side, is_restricted):
    """A system's two documents with everything that is not a change to this country removed."""
    sys_doc = {k: v for k, v in (side.get("system") or {}).items()
               if k not in _NOT_THIS_SYSTEM and k not in _DERIVED_SYSTEM}
    if isinstance(sys_doc.get("publication_policy"), dict):
        sys_doc["publication_policy"] = {k: v for k, v in sys_doc["publication_policy"].items() if k != "release_rule"}
    ev = side.get("events") or {}
    events = [{k: v for k, v in e.items() if k not in _DERIVED_EVENT} for e in ev.get("events") or []]
    if is_restricted:
        sys_doc = {k: v for k, v in sys_doc.items() if k not in _CAMPAIGN_HIDDEN_SYSTEM}
        events = [{k: v for k, v in e.items() if k not in _CAMPAIGN_HIDDEN_EVENT} for e in events]
    return sys_doc, events, ev.get("episodes")


# Where a reader can see what a kind of change describes (iteration 22): a tab of the country's
# own page. Only for country systems; the theatre's page is laid out differently.
CHANGE_TAB = {"research_coverage": "research", "methodology": "method"}


def _with_links(sid, changes):
    for c in changes:
        if c["category"] in CHANGE_TAB:
            c["link"] = {"system_id": sid, "tab": CHANGE_TAB[c["category"]]}
    return changes


def country_changes(sid, prev, curr, previous_as_of):
    """Every change to one country system, in category order. `prev`/`curr` are
    {"system": system.json, "events": events.json}; `prev` is None for a system new in this build."""
    labels = _labels()
    if not prev:
        return _with_links(sid, [{"category": "research_coverage",
                                  "notes": ["Monitoring of this system was first published."]}])
    is_restricted = restricted(prev, curr)
    out = _record_changes((prev.get("events") or {}).get("events") or [],
                          (curr.get("events") or {}).get("events") or [],
                          previous_as_of, is_restricted, labels)
    out += _system_level_changes(prev.get("system") or {}, curr.get("system") or {}, is_restricted)
    if not out and _comparable(prev, is_restricted) != _comparable(curr, is_restricted):
        out.append({"category": "build_only",
                    "notes": ["Wording or presentation changed; no record, rule or context changed."]})
    return _with_links(sid, _ordered(out))


def theatre_changes(ledger):
    """The theatre's own ledger, shown in the panel's categories. No facility, no count."""
    if not ledger or ledger.get("unavailable_reason"):
        return []
    by_cat = {}
    for row in ledger.get("changes") or []:
        by_cat.setdefault(THEATRE_CATEGORY[row["category"]], []).append(row)
    out = []
    added = by_cat.pop("records_added", [])
    if added:
        dates = sorted(str(r.get("effective_date")) for r in added if r.get("effective_date"))
        out.append({"category": "records_added",
                    "event_dates": [dates[0], dates[-1]] if dates else None,
                    # The ledger's own judgement, made against the previous build's date.
                    "all_predate_previous_build": all(r.get("record_class") == "historical_record_added" for r in added),
                    "notes": []})
    if by_cat.pop("records_withdrawn", []):
        out.append({"category": "records_withdrawn", "aggregated": True,
                    "notes": ["Some event records shown before are no longer asserted. The theatre's own "
                              "change list says which."]})
    corpus_only = by_cat.pop("build_only", [])
    for cat, rows in by_cat.items():
        out.append({"category": cat, "notes": sorted({THEATRE_NOTE[r["category"]] for r in rows})})
    if ledger.get("time_progression_only"):
        # Decay is the index ageing, never a source event: it is only ever this category, and only
        # on the ledger's own strict test (every input fingerprint unchanged).
        return [{"category": "decay_only", "notes": [
            "No input changed; only the evaluation date moved, so modelled impairment aged."]}]
    moved = ledger.get("esdi_delta") not in (0, 0.0, None)
    if corpus_only and not out:
        notes = sorted({THEATRE_NOTE[r["category"]] for r in corpus_only})
        if moved:
            notes.append("The index also moved as the evaluation date moved. With a source re-read beside it, "
                         "that is not labelled time decay only.")
        out.append({"category": "build_only", "notes": notes})
    elif not out and moved:
        out.append({"category": "build_only", "notes": [
            "No published record changed. The index moved, but whether time decay alone moved it cannot be "
            "established for this comparison."]})
    return _ordered(out)


def _ordered(changes):
    for c in changes:
        assert c["category"] in CATEGORY_IDS, c["category"]
    return sorted(changes, key=lambda c: CATEGORY_IDS.index(c["category"]))


def global_changes(prev, curr):
    """Changes that apply to every country system at once, said once rather than per country."""
    out = []
    pick = lambda side, k: next((s["system"].get(k) for s in (side.get("systems") or {}).values()  # noqa: E731
                                 if s and (s.get("system") or {}).get(k) is not None), None)
    pt, ct = pick(prev, "inclusion_threshold") or {}, pick(curr, "inclusion_threshold") or {}
    notes = []
    if pt.get("version") and ct.get("version") and pt.get("version") != ct.get("version"):
        notes.append(f"The inclusion threshold for country records was revised (version {ct['version']}).")
    pr = (pick(prev, "publication_policy") or {}).get("release_rule")
    cr = (pick(curr, "publication_policy") or {}).get("release_rule")
    if pr and cr and pr != cr:
        notes.append("The rule for releasing facility status after an attack campaign changed.")
    if pick(prev, "stale_policies") and pick(prev, "stale_policies") != pick(curr, "stale_policies"):
        notes.append("The rule for when a source counts as stale changed.")
    # Evidence confidence on country records (iteration 22). Its arrival, or a revision of its
    # method, moves a label on every record at once with nothing changing in any of them.
    def confidence(side):
        events = [e for s in (side.get("systems") or {}).values() if s
                  for e in (s.get("events") or {}).get("events") or []]
        return bool(events), any("evidence_confidence" in e for e in events)
    (prev_events, prev_has), (_curr_events, curr_has) = confidence(prev), confidence(curr)
    pv = (pick(prev, "evidence_confidence_summary") or {}).get("method_version")
    cv = (pick(curr, "evidence_confidence_summary") or {}).get("method_version")
    rules = len(notes)
    if prev_events and curr_has and not prev_has:
        notes.append("Each published country record now shows an evidence-confidence category, computed "
                     "from its published citations. No record changed.")
    elif pv and cv and pv != cv:
        notes.append(f"The evidence-confidence method was revised (version {cv}). A record's category can "
                     "move with no change to the record.")
    if notes:
        # The Help section that explains the change (iteration 23): Evidence confidence when that is
        # all that changed, else the section on reading this panel. A Help anchor, never a home-page
        # DOM id: the home's "Why these systems" heading is about selection, not about the change.
        help_anchor = "evidence-confidence" if rules == 0 else "whats-new"
        out.append({"category": "methodology", "notes": notes, "link": {"help": help_anchor}})
    pc, cc = prev.get("energy_context") or {}, curr.get("energy_context") or {}
    ps, cs = pc.get("source") or {}, cc.get("source") or {}
    if pc and cc:
        if ps.get("release") != cs.get("release") or pc.get("comparison_year") != cc.get("comparison_year"):
            out.append({"category": "national_context", "notes": [
                f"National energy statistics were refreshed: release of {_day(cs.get('release'))}, "
                f"figures for {cc.get('comparison_year')}."]})
        elif pc.get("countries") != cc.get("countries"):
            out.append({"category": "national_context", "notes": ["National energy figures were revised."]})
    return _ordered(out)


# --- the global impact layer (iteration 22) ---------------------------------------------------------
#
# Read from the two served artifacts of GLOBAL_IMPACT_METHODOLOGY §11 as published, in the previous
# build and in this one: `global/impacts.json` (records[].impact_id, .date, .first_published,
# .evidence_confidence.category, .attribution.status, .ai_involvement.status) and
# `global/regional_context.json` (entries[].id). Nothing here reads a candidate queue, and nothing
# says how many records anyone is holding.

# A record whose event is more than this many days older than its first publication was found by
# research after the fact: a backfill, not a new event.
BACKFILL_DAYS = 30
# Disputed claims less than any category, so a move into it is a weakening and a move out of it a
# strengthening.
EVIDENCE_ORDER = ("DISPUTED", "PRELIMINARY", "LIMITED", "MODERATE", "HIGH")
FIRST_IMPACT_RELEASE = (
    "First release of the impact layer: reviewed records of disruption to energy and essential civilian "
    "services, each with its evidence confidence, attribution and AI-involvement status. Its records are "
    "listed on the impact pages, not here: none of them is a new event because it is newly published.")
FIRST_CONTEXT_RELEASE = "The Gulf and Strait of Hormuz regional context was first published."


def _period_end(iso):
    """The last day a date of day, month or year precision can mean."""
    s = str(iso)
    if len(s) >= 10:
        return dt.date.fromisoformat(s[:10])
    if len(s) == 7:
        first = dt.date(int(s[:4]), int(s[5:7]), 1)
        return (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    return dt.date(int(s[:4]), 12, 31)


def impact_timing(record):
    """"backfill", "new_event" or "unknown" for a newly published impact record.

    A backfill needs positive evidence: both dates present, and the whole of the event (its observed
    end day where the record gives one, else the end of its month for a month-precision date) more
    than BACKFILL_DAYS before the record was first published. With either date missing or
    unreadable nothing is claimed either way.

    The same rule as the card's "Historical record added" line (`isHistoricalAddition` in
    web/src/global/impacts/model.ts; iteration 23, XL-05): this one used to read the start date
    only, so an outage that began six weeks before publication and ended last week was a backfill
    here and current on the card. A test runs both on every served record."""
    try:
        published = dt.date.fromisoformat(str(record.get("first_published"))[:10])
        end = record.get("date_end")
        event_end = dt.date.fromisoformat(end) if isinstance(end, str) and len(end) == 10 else _period_end(record.get("date"))
    except (TypeError, ValueError):
        return "unknown"
    return "backfill" if (published - event_end).days > BACKFILL_DAYS else "new_event"


def _impact_item(r, **extra):
    """An impact record as its own artifact already publishes it: its public id (an opaque token
    for an abstracted attack record, by the import's own rule), date, country and sector."""
    return {"impact_id": r.get("impact_id"), "date": r.get("date"),
            "date_precision": r.get("date_precision") or "day",
            "country": r.get("country_name") or r.get("country_a3"), "sector": r.get("sector"), **extra}


def _records(doc):
    return {r["impact_id"]: r for r in (doc or {}).get("records") or [] if isinstance(r, dict) and r.get("impact_id")}


def _moved(prev, curr, path):
    def value(r):
        for k in path:
            r = (r or {}).get(k) if isinstance(r, dict) else None
        return r
    return [(i, value(prev[i]), value(curr[i])) for i in sorted(prev.keys() & curr.keys())
            if value(prev[i]) != value(curr[i]) and value(curr[i]) is not None and value(prev[i]) is not None]


def impact_changes(prev, curr):
    """Changes to the impact layer between two published states, or None when this build has none.

    A layer with no predecessor is one sentence, never a list: every record in a first release is
    "new" to the file and none is a new event."""
    cur_doc, cur_ctx = curr.get("impacts"), curr.get("regional_context")
    if cur_doc is None and cur_ctx is None:
        return None
    prev_doc, prev_ctx = prev.get("impacts"), prev.get("regional_context")
    if cur_doc is not None and prev_doc is None:
        first = [{"category": "impact_record_added", "first_release": True, "notes": [FIRST_IMPACT_RELEASE]}]
        # The regional context published with it is its own first publication, said in its own
        # sentence (iteration 23, XL-02: this branch returned before the context was looked at).
        if cur_ctx is not None and prev_ctx is None:
            first.append({"category": "regional_context_updated", "notes": [FIRST_CONTEXT_RELEASE]})
        return _ordered(first)

    out = []
    p, c = _records(prev_doc), _records(cur_doc)
    added = [(_impact_item(c[i], timing=impact_timing(c[i]), first_published=c[i].get("first_published")), i)
             for i in c.keys() - p.keys()]
    if added:
        items, more = _capped(added)
        timings = {it[0]["timing"] for it in added}
        out.append({"category": "impact_record_added", "items": items, "more": more, "notes": [],
                    # Said of the whole set only when it is true of every record in it.
                    "all_backfill": timings == {"backfill"}, "all_new_events": timings == {"new_event"}})
    if p.keys() - c.keys():
        # Which and how many would say what review is holding back. One sentence.
        out.append({"category": "records_withdrawn", "notes": [
            "One or more impact records shown before are not shown now: withdrawn, or held while a review is repeated."],
            "aggregated": True})

    stronger, weaker = [], []
    for i, a, b in _moved(p, c, ("evidence_confidence", "category")):
        if a in EVIDENCE_ORDER and b in EVIDENCE_ORDER:
            (stronger if EVIDENCE_ORDER.index(b) > EVIDENCE_ORDER.index(a) else weaker).append(
                (_impact_item(c[i], **{"from": a, "to": b}), i))
    for cat, rows in (("evidence_strengthened", stronger), ("evidence_weakened", weaker)):
        if rows:
            items, more = _capped(rows)
            out.append({"category": cat, "items": items, "more": more, "notes": []})
    for cat, path, note in (
            ("attribution_updated", ("attribution", "status"),
             "The attribution of an existing record was updated. Not a new incident."),
            ("ai_status_updated", ("ai_involvement", "status"),
             "The AI-involvement status of an existing record was updated. Not a new incident.")):
        rows = [(_impact_item(c[i], **{"from": a, "to": b}), i) for i, a, b in _moved(p, c, path)]
        if rows:
            items, more = _capped(rows)
            out.append({"category": cat, "items": items, "more": more, "notes": [note]})

    if cur_ctx is not None:
        entries = lambda doc: {e["id"]: e for e in (doc or {}).get("entries") or [] if isinstance(e, dict) and e.get("id")}  # noqa: E731
        pe, ce = entries(prev_ctx), entries(cur_ctx)
        notes = []
        if prev_ctx is None:
            notes.append(FIRST_CONTEXT_RELEASE)
        else:
            if ce.keys() - pe.keys():
                notes.append("Dated statements were added to the Gulf and Strait of Hormuz regional context.")
            if pe.keys() - ce.keys() or any(pe[i] != ce[i] for i in pe.keys() & ce.keys()):
                notes.append("Statements in the regional context were revised or withdrawn.")
        if notes:
            out.append({"category": "regional_context_updated", "notes": notes})
    n = 0
    for change in out:
        for it in change.get("items") or []:
            n += 1
            it["key"] = f"impact-change-{n:02d}"
    return _ordered(out)


def _assign_row_keys(sid, changes):
    """Ids may name a facility; the panel carries a row key instead, for every system."""
    n = 0
    for c in changes:
        for it in c.get("items") or []:
            n += 1
            it["key"] = f"{sid}-change-{n:02d}"
    return changes


def derive(prev, curr, theatre_ledger, comparison):
    """Pure: the panel from two published states. Each state is
    {"systems": {sid: {"system", "events"} | None}, "energy_context": {...}}."""
    previous_as_of = comparison.get("previous_as_of")
    rows, unchanged = [], []
    for s in systems.SYSTEMS:
        sid = s["id"]
        if sid == systems.THEATRE:
            changes = theatre_changes(theatre_ledger)
            row = {"system_id": sid, "name": s["name"], "kind": s["kind"], "changes": changes}
            if not theatre_ledger or theatre_ledger.get("unavailable_reason"):
                # Unknown is not unchanged: a theatre that could not be compared is listed as such.
                row["unavailable"] = (theatre_ledger or {}).get("unavailable_reason") or "no comparison"
                rows.append(row)
                continue
            row["index"] = {"label": "Monitored-Area ESDI", "before": theatre_ledger.get("esdi_before"),
                            "after": theatre_ledger.get("esdi_after"),
                            "separable": bool(theatre_ledger.get("attribution_separable"))}
        else:
            c = (curr.get("systems") or {}).get(sid)
            if not c:
                continue
            changes = _assign_row_keys(sid, country_changes(sid, (prev.get("systems") or {}).get(sid), c, previous_as_of))
            row = {"system_id": sid, "name": s["name"], "kind": s["kind"], "changes": changes}
        if row["changes"]:
            rows.append(row)
        else:
            # With its name: the page holds no country list of its own.
            unchanged.append({"system_id": sid, "name": s["name"]})
    impact = impact_changes(prev, curr)
    glob = global_changes(prev, curr)
    if not glob and not rows:
        # Nothing changed in any system or rule. If the impact layer changed, its own block says
        # so, and "nothing published changed" would be false.
        glob = [] if impact else [{"category": "build_only", "notes": ["Rebuilt; nothing published changed."]}]
    return _payload(comparison, glob, rows, unchanged, impact=impact)


def _payload(comparison, glob, rows, unchanged, reason=None, impact=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "available": reason is None,
        "unavailable_reason": reason,
        "comparison": comparison,
        "categories": [{"id": i, "label": l, "meaning": m} for i, l, m in CATEGORIES],
        "order": "systems alphabetically by name; never by size, count or severity",
        "note": ("What changed in the published data, by cause. Dates on records are when the events happened. "
                 "No counts are shown: reporting differs too much between countries for a number beside each "
                 "to mean anything but a ranking."),
        "global": glob,
        # null when this build publishes no impact layer; an empty list when it does and nothing in
        # it changed. The two are different and the panel says which.
        "impact_layer": impact,
        "systems": rows,
        "unchanged": unchanged,
    }


def unavailable(reason, current_as_of=None):
    """No provable baseline. An empty change list here would claim a quiet build that never happened."""
    return _payload({"previous_as_of": None, "current_as_of": current_as_of, "mode": "unavailable",
                     "basis": None}, [], [], [], reason=reason)


def _published_state(read):
    """A published state through `read(relpath)` -> parsed JSON or None."""
    out = {}
    for sid in systems.COUNTRY_SYSTEMS:
        sys_doc = read(f"{systems.root(sid)}/system.json")
        ev = read(f"{systems.root(sid)}/events.json")
        out[sid] = {"system": sys_doc, "events": ev} if sys_doc and ev else None
    return {"systems": out, "energy_context": read("global/energy_context.json"),
            # Absent in a build that predates the impact layer: None, which impact_changes reads as
            # "no predecessor", not as an empty layer.
            "impacts": read("global/impacts.json"), "regional_context": read("global/regional_context.json")}


def build(root, processed, snapshot, incidents, assets):
    """The panel for this build against the last served production build dated before it."""
    current_as_of = snapshot.get("as_of")
    sha, meta = lineage.previous_dated_build(root, current_as_of)
    if not sha:
        return unavailable(meta.get("reason") or "no previous published build", current_as_of)

    def prev_read(rel):
        return lineage.show_json(root, sha, f"{PAYLOAD_DIR}/{rel}")

    def curr_read(rel):
        p = processed / rel
        if not p.is_file():
            return None
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)

    prev_snap = prev_read("snapshot.json")
    prev_inc, prev_assets = prev_read("incidents.json"), prev_read("assets.json")
    if prev_inc is None or prev_assets is None:
        ledger = diff_builds.unavailable(snapshot, None, "the previous build's theatre records could not be read")
    else:
        ledger = diff_builds.diff(prev_snap, snapshot, prev_inc, incidents, prev_assets, assets)
    comparison = {
        "previous_as_of": meta["previous_as_of"],
        "current_as_of": current_as_of,
        "mode": meta["mode"],
        "basis": "the last published build dated before this one",
    }
    if meta["mode"] == "development":
        comparison["note"] = ("Built from a development copy, compared with the last published build: this "
                              "shows what would change if this copy were published.")
    return derive(_published_state(prev_read), _published_state(curr_read), ledger, comparison)
