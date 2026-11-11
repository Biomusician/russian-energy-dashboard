"""Build the country systems and the global manifest (iteration 14).

For every system in `systems.COUNTRY_SYSTEMS` this reads the curated sources under
`data/curated/systems/<id>/` and emits `data/processed/systems/<id>/`:

  system.json      what the system is, what its evidence supports, and why it has no score
  events.json      reviewed, publicly reported major disruptions, admin-1 precision at most,
                   and the episodes they group into (one hazard or one statement = one episode)
  regions.geojson  the first-level units the events are aggregated to

and, once for all systems, `data/processed/global/manifest.json` and `global/world.geojson`.

WHAT IT DELIBERATELY DOES NOT DO.
- It computes no index, no sector value and no decay. Every sector's published state is at
  most CONTEXT_ONLY until a recovery model for that country is approved
  (GLOBAL_METHODOLOGY.md §2, §8.3). A country with no score shows no score: never a zero.
- It reads no candidate file. `data/candidates/` is a research queue; only the reviewed events
  in `data/curated/systems/<id>/events.json` (written by `scripts/import_candidates.py`) reach a
  payload. The same human-gated rule that has kept discovery out of the Russia build since
  iteration 6.
- It emits no coordinate for any event, and no field that orders systems by any figure.
"""

import datetime as dt
import re
from urllib.parse import unquote

from pipeline import geo, global_context, gulf_context, systems
from pipeline.config import ASSET_CLASSES, CURATED, DISRUPTION_CAUSES, RAW, SECTORS
from pipeline import outputs
from pipeline.util import fetch, log, read_json, write_json

SYSTEMS_CURATED = CURATED / "systems"
ADMIN1_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
              "geojson/ne_10m_admin_1_states_provinces.geojson")
ADMIN0_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
              "geojson/ne_50m_admin_0_countries.geojson")

# ISO 3166-2 changed four Indian codes in November 2023; Natural Earth (last released 2022)
# still carries the old ones. The events use the current codes, so the geometry is moved to them.
ISO_CODE_FIXES = {"IN-CT": "IN-CG", "IN-UT": "IN-UK", "IN-OR": "IN-OD", "IN-TG": "IN-TS"}
# Iran. Natural Earth carries the ISO 3166-2:IR numbering from before the November 2020 revision,
# in which all but two codes mean a different province today ("IR-07" was Tehran and is now Fars),
# and it gives Alborz its parent Tehran's code. A code a researcher takes from any current source
# would land on the wrong province with no error, so the units are moved to today's codes by name
# (docs/countries/IR_SOURCE_AUDIT.md, geography; checked against an independent listing).
NAME_CODE_FIXES = {("IRN", name): code for name, code in {
    "Markazi": "IR-00", "Gilan": "IR-01", "Mazandaran": "IR-02", "East Azarbaijan": "IR-03",
    "West Azarbaijan": "IR-04", "Kermanshah": "IR-05", "Khuzestan": "IR-06", "Fars": "IR-07",
    "Kerman": "IR-08", "Razavi Khorasan": "IR-09", "Esfahan": "IR-10", "Sistan and Baluchestan": "IR-11",
    "Kordestan": "IR-12", "Hamadan": "IR-13", "Chahar Mahall and Bakhtiari": "IR-14", "Lorestan": "IR-15",
    "Ilam": "IR-16", "Kohgiluyeh and Buyer Ahmad": "IR-17", "Bushehr": "IR-18", "Zanjan": "IR-19",
    "Semnan": "IR-20", "Yazd": "IR-21", "Hormozgan": "IR-22", "Tehran": "IR-23", "Ardebil": "IR-24",
    "Qom": "IR-25", "Qazvin": "IR-26", "Golestan": "IR-27", "North Khorasan": "IR-28",
    "South Khorasan": "IR-29", "Alborz": "IR-30",
}.items()}
# A system whose every unit must be renamed: a unit the table misses is an error, not a fallback
# to the old code, which would be another province's.
NAME_CODE_COMPLETE = {"IRN": 31}

# Special administrative regions that Natural Earth files as their own admin-0 units. They are
# part of the China system as single units. Their admin-1 districts are not used.
SAR_UNITS = {"cn": {"HKG": ("CN-HK", "Hong Kong"), "MAC": ("CN-MO", "Macau")}}

# Simplification tolerance in degrees. Canada's Arctic coastline is enormous at 0.01; 0.02 halves
# it with no visible loss at country zoom (measured in GLOBAL_GEOGRAPHY.md).
REGION_TOLERANCE = {"ca": 0.02}
DEFAULT_TOLERANCE = 0.01
WORLD_TOLERANCE = 0.15

# Vocabulary the country systems need and the Russia theatre does not. Kept OUT of the Russia
# taxonomy on purpose: adding a cause there changes what its filters and cause weights mean,
# which is an owner decision (GLOBAL_METHODOLOGY §8.5).
TAXONOMY_EXTENSIONS = {
    "asset_classes": {
        "system_wide": "System-wide (grid area or supply system)",
        "upstream_production": "Upstream production",
    },
    "causes": {
        "natural_hazard": "Natural hazard (weather, wildfire, flood, earthquake)",
        "labour": "Labour action",
    },
}

# The only fields an emitted event may carry. Anything else a lane wrote stays in the queue.
EVENT_FIELDS = (
    "event_id", "date", "date_precision", "date_end", "region_code", "region_name",
    "geography_precision", "regions_affected", "facility_name", "facility_name_local", "operator",
    "asset_class", "cause", "summary", "effect", "inclusion_basis", "criterion_met",
    "threshold_basis", "capacity_affected", "sources", "recovery", "review", "episode_id",
    "hazard_name", "publication",
)
# No `title`: headlines are the publishers' words, not ours, and the page shows the publisher.
SOURCE_FIELDS = ("url", "publisher", "date", "language", "source_role", "opened")
# Iteration 19. A non-English source keeps its title in its own script with an English gloss, and a
# date converted from another calendar keeps what the source wrote. Emitted only where present.
OPTIONAL_SOURCE_FIELDS = ("title_original", "title_en")
OPTIONAL_EVENT_FIELDS = ("source_date_text", "date_calendar", "conversion_basis")
DATE_CALENDARS = ("gregorian", "solar_hijri", "hijri")
# What the campaign classification of a system may be (conflict_campaigns.json, system_states).
CAMPAIGN_STATES = ("ACTIVE_KINETIC_CAMPAIGN", "RECENT_ENDED_CAMPAIGN", "NO_ACTIVE_CAMPAIGN", "UNCERTAIN")
RESTRICTING_STATES = ("ACTIVE_KINETIC_CAMPAIGN", "RECENT_ENDED_CAMPAIGN", "UNCERTAIN")
MATURITY = ("monitored", "research_preview")
# Id of a kinetic record where policy puts such records at country level: date, class, a counter or
# hash. It names no facility, because an id travels into feeds, ledgers and review files.
OPAQUE_ID = r"{cc}-\d{{4}}-\d{{2}}(-\d{{2}})?-[a-z-]+-attack-[0-9a-z]{{1,6}}"
RECOVERY_FIELDS = ("research_status", "kind", "date", "evidence", "url")
# WITHHELD_ACTIVE_CAMPAIGN is a PUBLICATION state, not a research result: the record belongs to a
# kinetic campaign that is still active, so its facility-specific recovery status is not published
# (docs/CURRENT_EVENT_PUBLICATION_POLICY.md). It is never "no evidence" and never "not researched".
WITHHELD = "WITHHELD_ACTIVE_CAMPAIGN"
RECOVERY_STATUSES = ("EVIDENCE_FOUND", "RESEARCHED_NO_PUBLIC_EVIDENCE", "NOT_YET_RESEARCHED", WITHHELD)
# What KIND of recovery evidence was found. Required whenever the status is EVIDENCE_FOUND: the
# iteration-14 red team found an estimate, a "nothing was lost" case and a supply-continuity
# statement all rendered as "recovery evidence found". Service restored is not a facility
# rebuilt; an estimate is not an observation; partial is not full.
RECOVERY_KINDS = ("full_restart", "partial_restart", "service_restored", "partial_restoration",
                  "estimate", "supply_unaffected_statement", "no_supply_lost")
# The kinds that report a facility or service actually coming back (fully or partly).
OBSERVED_RECOVERY_KINDS = ("full_restart", "partial_restart", "service_restored", "partial_restoration")
# What a lane may say a sector COULD reach. Published beside, never as, the sector state.
ASSESSMENTS = ("READY", "EXPERIMENTAL", "INCOMPLETE", "UNSUITABLE", "INSUFFICIENT_EVIDENCE",
               "NOT_APPLICABLE", "NOT_YET_RESEARCHED")

RESEARCH_STATUSES = ("complete", "partial")
# Iteration 16 splits research into two kinds. A TARGETED pass chases named gaps and leads; a
# SYSTEMATIC pass declares its source lanes and window before searching and executes every lane.
# Only a systematic pass can make research coverage complete (onboarding gate item 7B).
RESEARCH_KINDS = ("systematic", "targeted")
RESEARCH_OUTCOME_KEYS = ("candidates", "records", "accepted", "insufficient_evidence", "rejected",
                         "duplicate", "out_of_scope", "held")
RESEARCH_LANE_KEYS = ("lane", "source_family", "registry", "status", "reason", "covered_through")
# Iteration 18: two independent dimensions replace the binary lane status (GLOBAL_METHODOLOGY,
# "Research coverage vocabulary"). EXECUTION is what the analyst did; SOURCE WINDOW is what the
# publisher has made available. "The publisher has not released 2026" and "we ran 2 of 90 searches"
# were both "partial", and read the same. Earlier passes keep the status they were logged with:
# re-describing them would be moving the goalposts.
EXECUTION_STATES = ("not_started", "partial", "declared_search_complete", "enumerated_complete")
SOURCE_WINDOW_STATES = ("current_through_end_date", "publisher_not_yet_released", "inaccessible",
                        "no_census_exists", "rolling_archive_gap", "unknown")
UNIVERSE_KINDS = ("census", "report_archive", "declared_query_set")
RESEARCH_LANE_KEYS_V2 = ("lane", "source_family", "registry", "universe_kind", "execution", "source_window",
                         "covered_through", "languages_required", "languages_executed", "queries_declared",
                         "queries_run", "items_enumerated", "items_in_universe", "limitation", "finding",
                         "carried_forward", "stopped_by")
# The window every country system covers. A systematic pass that starts later is a top-up: it can
# never make the whole record "complete" (iteration 16, research red team).
COVERAGE_START = "2022-01-01"

# SOURCE STALE LIMITS ARE DISPLAY POLICY, NOT METHODOLOGY (iteration 16). They decide when the
# page tells a reader to re-check a source before relying on it. They never decide whether an
# event is accepted, never enter a number, and never touch a historical reconstruction; a test
# holds that. Each source names a class; its limit is the class's, never typed per source, so a
# limit cannot drift away from its stated rationale.
STALE_POLICIES = {
    "monthly": {"days": 120, "rationale": "three monthly releases missed, plus a month of publication lag"},
    "quarterly": {"days": 180, "rationale": "two quarterly releases missed"},
    "semiannual": {"days": 400, "rationale": "two half-yearly releases missed, plus about a month of lag"},
    "annual": {"days": 400, "rationale": "one annual release missed, plus about a month of lag"},
    "event_driven": {"days": 180, "rationale": "no release cycle; the registry entry (access, licence, "
                                               "address) is re-checked at least twice a year"},
}
# How often a SYSTEMATIC research pass should be repeated before research coverage reads as due.
# Also display policy; like the stale limits it never changes an accepted event.
RESEARCH_CADENCE_DAYS = 365


def _in_use(source):
    return not source["role"].startswith("rejected")


def validate_sources(system_id, doc, research_log):
    """Every source a country relies on says when it was last checked, how often it publishes and
    which stale policy applies; every research pass says what it covered and whether it finished.

    Source freshness and research completeness are validated separately and never derived from
    one another: a fresh registry says nothing about whether the event search was systematic."""
    problems = []
    for s in doc["sources"]:
        if not s.get("last_checked"):
            problems.append(f"source {s['name']!r} has no last-checked date")
        if not _in_use(s):
            continue
        pol = s.get("stale_policy")
        if not s.get("publication_cadence") or pol not in STALE_POLICIES:
            problems.append(f"source {s['name']!r} is used but states no cadence or stale policy")
        elif s.get("stale_after_days") != STALE_POLICIES[pol]["days"]:
            problems.append(f"source {s['name']!r}: stale_after_days must be the {pol!r} policy's "
                            f"{STALE_POLICIES[pol]['days']}, not {s.get('stale_after_days')!r}")
    for p in research_log["passes"]:
        tag = f"research pass {p.get('date')} ({p.get('by')})"
        if p.get("status") not in RESEARCH_STATUSES:
            problems.append(f"{tag}: status must be one of {RESEARCH_STATUSES}")
        if p.get("kind") not in RESEARCH_KINDS:
            problems.append(f"{tag}: kind must be one of {RESEARCH_KINDS}")
        if p.get("status") == "partial" and not p.get("status_reason"):
            problems.append(f"{tag}: a partial pass must say why")
        if not (p.get("window") and len(p["window"]) == 2 and p["window"][0] <= p["window"][1]):
            problems.append(f"{tag}: window must be [start, end]")
        # Counts only. A narrative field here would publish what the queue keeps private.
        outcome = p.get("outcome", {})
        extra = set(outcome) - set(RESEARCH_OUTCOME_KEYS)
        if extra:
            problems.append(f"{tag}: outcome carries non-count fields {sorted(extra)}")
        if any(not isinstance(v, int) or isinstance(v, bool) for v in outcome.values()):
            problems.append(f"{tag}: outcome values must be integer counts")
        lanes = p.get("lanes") or []
        for lane in lanes:
            if "execution" in lane:
                problems.extend(f"{tag}: {x}" for x in lane_problems(lane, p.get("window")))
            elif set(lane) - set(RESEARCH_LANE_KEYS) or lane.get("status") not in RESEARCH_STATUSES:
                problems.append(f"{tag}: lane {lane.get('lane')!r} must hold only "
                                f"{RESEARCH_LANE_KEYS} with a status in {RESEARCH_STATUSES}")
        if p.get("kind") == "systematic":
            if not lanes:
                problems.append(f"{tag}: a systematic pass declares its source lanes")
            # The lanes are those of a plan committed BEFORE searching; the plan is named so a
            # test can compare the two (tests/test_pipeline.py, the plan-commit test).
            plan = p.get("plan") or {}
            if not (plan.get("document") and plan.get("commit")):
                problems.append(f"{tag}: a systematic pass names its plan document and commit")
            registry = {x["name"] for x in doc["sources"] if _in_use(x)}
            for lane in lanes:
                if "status" in lane and lane.get("status") == "partial" and not lane.get("reason"):
                    problems.append(f"{tag}: lane {lane.get('lane')!r} is partial without a reason")
                # The lane completion contract (iteration 17): a lane says how far its universe was
                # searched. Complete means searched to the end of the pass window; a source that
                # has not yet published the tail of the window leaves the lane partial.
                ct = lane.get("covered_through")
                if ct is not None and (not isinstance(ct, str) or (p.get("window") and ct > p["window"][1])):
                    problems.append(f"{tag}: lane {lane.get('lane')!r} covered_through {ct!r} is not a date "
                                    "within the pass window")
                ends_early = ct is not None and p.get("window") and ct < p["window"][1]
                if lane.get("status") == "complete" and ends_early:
                    problems.append(f"{tag}: lane {lane.get('lane')!r} is complete but covered only "
                                    f"through {ct}")
                # A lane searched sources the registry must list, or source freshness would be
                # stated for a different set of sources than the search used.
                names = lane.get("registry") or []
                if not names or set(names) - registry:
                    problems.append(f"{tag}: lane {lane.get('lane')!r} names no registry source, or "
                                    f"one not in use: {sorted(set(names) - registry)}")
            # Complete is a process claim: every declared lane executed. One skipped lane and the
            # pass is partial, however quiet the other lanes were.
            if p.get("status") == "complete" and not all(_lane_done(lane) for lane in lanes):
                problems.append(f"{tag}: complete, but a declared lane is not")
        elif p.get("status") == "complete":
            problems.append(f"{tag}: only a systematic pass can be complete")
    if problems:
        raise ValueError(f"system {system_id} sources: " + "; ".join(problems))


def lane_problems(lane, window):
    """The two-dimension lane contract (iteration 18). Each rule stops a lane reading as more
    finished than it is: a query set is never a census, a blocked source is never searched, an
    English-only run of a bilingual lane is never declared complete."""
    name = lane.get("lane")
    out = []
    if set(lane) - set(RESEARCH_LANE_KEYS_V2):
        out.append(f"lane {name!r} carries unexpected fields {sorted(set(lane) - set(RESEARCH_LANE_KEYS_V2))}")
    ex, win, kind = lane.get("execution"), lane.get("source_window"), lane.get("universe_kind")
    if ex not in EXECUTION_STATES:
        out.append(f"lane {name!r}: execution {ex!r} is not one of {EXECUTION_STATES}")
    if win not in SOURCE_WINDOW_STATES:
        out.append(f"lane {name!r}: source_window {win!r} is not one of {SOURCE_WINDOW_STATES}")
    if kind not in UNIVERSE_KINDS:
        out.append(f"lane {name!r}: universe_kind {kind!r} is not one of {UNIVERSE_KINDS}")
    required, executed = set(lane.get("languages_required") or []), set(lane.get("languages_executed") or [])
    if not required:
        out.append(f"lane {name!r} names no required language")
    ran_all_languages = required <= executed
    ct, end = lane.get("covered_through"), (window or [None, None])[1]
    if ex == "enumerated_complete":
        if kind == "declared_query_set":
            out.append(f"lane {name!r}: a declared query set can never be enumerated_complete")
        if win not in ("current_through_end_date", "publisher_not_yet_released"):
            out.append(f"lane {name!r}: enumerated_complete with source_window {win!r}")
        if not ran_all_languages:
            out.append(f"lane {name!r}: enumerated_complete without its required languages")
    if ex == "declared_search_complete":
        if kind != "declared_query_set":
            out.append(f"lane {name!r}: only a declared query set can be declared_search_complete")
        if win != "no_census_exists":
            out.append(f"lane {name!r}: a declared query set has no census, so its window is no_census_exists")
        if not ran_all_languages:
            out.append(f"lane {name!r}: declared_search_complete without its required languages")
        qd, qr = lane.get("queries_declared"), lane.get("queries_run")
        if not (isinstance(qd, int) and qd > 0 and isinstance(qr, int) and qr >= qd):
            out.append(f"lane {name!r}: declared_search_complete needs every declared query run ({qr} of {qd})")
    if lane.get("stopped_by") not in (None, "search_limit"):
        out.append(f"lane {name!r}: stopped_by {lane.get('stopped_by')!r} is not a known reason")
    if lane.get("stopped_by") and ex in ("enumerated_complete", "declared_search_complete"):
        out.append(f"lane {name!r}: stopped early, so it cannot be complete")
    if win == "inaccessible" and ex in ("enumerated_complete", "declared_search_complete"):
        out.append(f"lane {name!r}: a source that refused access was not searched")
    if ex == "not_started" and (lane.get("queries_run") or lane.get("items_enumerated")):
        out.append(f"lane {name!r}: not_started but records work done")
    if ex in ("not_started", "partial") or win != "current_through_end_date":
        if not lane.get("limitation"):
            out.append(f"lane {name!r} states no limitation")
    if ct is not None and end and ct > end:
        out.append(f"lane {name!r}: covered_through {ct} is after the window end")
    if win == "current_through_end_date" and ex == "enumerated_complete" and ct != end:
        out.append(f"lane {name!r}: current through the end date but covered_through is {ct}")
    if win == "publisher_not_yet_released" and (ct is None or (end and ct >= end)):
        out.append(f"lane {name!r}: publisher_not_yet_released needs a covered_through before the window end")
    return out


def _lane_done(lane):
    """Every declared lane executed as far as the public evidence permits. Blocked or unknown
    sources do not qualify, whatever the analyst did."""
    if "execution" in lane:
        return (lane["execution"] in ("enumerated_complete", "declared_search_complete")
                and lane["source_window"] not in ("inaccessible", "unknown"))
    return lane.get("status") == "complete"


# The state a reader is told, computed from the two dimensions, never stored or typed. Order
# matters: a blocked source reads as blocked however much of the rest was done.
def lane_summary_state(lane):
    if "execution" not in lane:
        return "legacy"
    ex, win = lane["execution"], lane["source_window"]
    # Our own search allowance ran out: not the publisher's doing, and the queries can still be run.
    if lane.get("stopped_by") == "search_limit":
        return "stopped_by_search_limit"
    if ex == "not_started":
        return "blocked_by_source" if win == "inaccessible" else "not_started"
    if win == "inaccessible":
        return "blocked_by_source"
    if ex == "enumerated_complete":
        return "current_through_latest_release" if win == "publisher_not_yet_released" else "universe_searched"
    if ex == "declared_search_complete":
        return "declared_query_set_run"
    return "partially_searched"


LANE_SUMMARY_STATES = ("stopped_by_search_limit", "universe_searched", "current_through_latest_release", "declared_query_set_run",
                       "partially_searched", "blocked_by_source", "not_started", "legacy")


def research_freshness(research_log, kind="systematic"):
    """When the event search was last done SYSTEMATICALLY, over what window, and when it is due.

    Derived from the research log only, never from the source registry: sources being current
    does not mean the search was. `next_due` is a date; whether it has passed is computed on the
    reader's clock, like every other age on these pages."""
    systematic = [p for p in research_log.get("passes", []) if p.get("kind") == kind]
    last = max(systematic, key=lambda p: p["date"]) if systematic else None
    due = None
    completeness = "never_systematic"
    lanes = []
    summary = {}
    if last:
        due = (dt.date.fromisoformat(last["date"]) + dt.timedelta(days=RESEARCH_CADENCE_DAYS)).isoformat()
        lanes = last.get("lanes") or []
        # A complete top-up over a later window does not complete the record from 2022.
        covers = last["window"][0] <= COVERAGE_START
        completeness = "complete" if last["status"] == "complete" and covers else "partial"
        summary = {}
        for lane in lanes:
            s = lane_summary_state(lane)
            summary[s] = summary.get(s, 0) + 1
        # A partial pass does not reset the clock: its unfinished lanes are owed now (analytics
        # red team: every country read "next due" a year out with 0 of N lanes complete).
        if completeness != "complete":
            due = last["date"]
    return {
        "last_systematic_pass": last["date"] if last else None,
        "coverage_window": last["window"] if last else None,
        "covers_full_window": bool(last) and last["window"][0] <= COVERAGE_START,
        "lanes_declared": len(lanes),
        "lanes_complete": sum(1 for x in lanes if _lane_done(x)),
        # Not a percentage, on purpose: a lane waiting on a publisher and a lane that ran 2 of 90
        # searches must not add up to one number.
        "lane_states": summary,
        "first_systematic_pass": min((p["date"] for p in systematic), default=None),
        "completeness": completeness,
        "research_cadence_days": RESEARCH_CADENCE_DAYS,
        "next_due": due,
        "note": ("Research coverage describes the event search, not the sources: a country's sources "
                 "can all be current while its search is unfinished, and a finished search can rest "
                 "on a source whose own data is old. A fully executed search procedure is not "
                 "complete knowledge: it means the declared sources were searched, not that nothing "
                 "else happened."),
    }


# Why two records may share an episode (iteration 15, tightened in iteration 16). One hurricane
# yields an outage record per state plus shut-ins and port closures; counting records would make
# hazard-prone regions look several times more disrupted than they were. But a grouping is itself
# a claim, so every basis is EXPLICIT: something a source says, never something inferred from
# being close in time or place.
EPISODE_BASES = {
    "named_hazard": "The records name the same storm, flood, heat wave or other hazard.",
    "explicit_common_event": "A source explicitly says these records belong to one common event.",
    "coordinated_wave": "A source explicitly identifies these records as one coordinated attack or wave.",
    "explicit_continuation": "A later record reports the same operational disruption continuing.",
}
SINGLETON = "singleton"
SINGLETON_TEXT = "No other record is tied to this one by a named hazard or an explicit common event."
# Retired in iteration 16. A source that LISTS several incidents in one statement is provenance,
# not evidence that they are one event: the Saudi energy ministry's April 2026 statement listed
# attacks it also said were separate. Named so the build can say why it refuses them.
RETIRED_EPISODE_BASES = {
    "single_statement": "one statement listing several records is not evidence they are one episode",
    "continuing_shortfall": "renamed explicit_continuation",
    "single_record": f"renamed {SINGLETON}",
}
# A shared basis other than a named hazard must point at the source that says so.
EVIDENCED_BASES = ("explicit_common_event", "coordinated_wave", "explicit_continuation")

# Causes whose records fall under an active campaign's publication rule.
KINETIC_CAUSES = ("kinetic_strike", "sabotage")
# Wording that reports a facility's CURRENT operating state. Not allowed in the summary or effect
# of a record under an active campaign: it would publish there what the withheld recovery block
# does not (docs/CURRENT_EVENT_PUBLICATION_POLICY.md §4).
STATUS_WORDING = re.compile(
    r"restart|resum|reopen|back (online|in service)|returned to|recover(ed|y)|restor|"
    r"still (shut|offline|halted|closed|down)|remain(s|ed)? (shut|offline|halted|closed)|"
    r"operating at|running at|operat(ing|ion) at \d|postpon|planned restart|"
    r"not (yet )?resumed|had not resumed|knock-on|cancel|expected|extended|repair|re started|"
    # Arabic: restart, resumption, repair, return to service. The English-only check let Arabic
    # addresses through unread (iteration 18, Saudi safety audit).
    r"استئناف|استأنف|[إا]عادة (ال)?تشغيل|[إا]صلاح|عودة (ال)?إنتاج|عاد إلى العمل|"
    # Persian (iteration 19): restart, resumption, back on the grid, repair, reconstruction, still
    # stopped. Either yeh is accepted, and the half-space in a compound may be a space or absent,
    # because agencies and their addresses write all three.
    r"راه[\u200c ]?انداز[یي] مجدد|از ?سرگ[یي]ر[یي]|از سر گرفته|بازگشت به مدار|به مدار بازگشت|"
    r"در مدار قرار گرفت|تعم[یي]ر|ترم[یي]م|بازساز[یي]|باز[یي]اب[یي]|همچنان متوقف",
    re.I)


def status_wording(text):
    """The match in `text`, reading an address's slug as words and decoding percent-escapes, so
    "back-online" and an encoded Arabic path are read like the prose they are."""
    return STATUS_WORDING.search(unquote(text or "").replace("-", " ").replace("_", " "))


# Exact UI wording (GLOBAL_METHODOLOGY §6.4), carried in the payload so every surface says the
# same thing and a test can hold it.
COMPARABILITY_STATEMENT = (
    "Each country is measured on its own terms. Event counts reflect what is publicly reported "
    "under that country's reporting rules, not how often disruption happens. A country with "
    "fewer recorded events is not shown to be safer, more resilient or less disrupted. Figures "
    "are not comparable across countries and are never ranked."
)


# Roles whose author is the body that ran, regulated or measured the system, as against a
# publisher reporting on it. Used only to describe a country's citations (iteration 17, source
# health); it never decides whether an event is included.
FIRST_PARTY_ROLES = ("official", "government", "regulator", "operator", "dataset")


def _first_party(source):
    # Wikipedia is curated as a "dataset" in some records, but it is an aggregator of other
    # publishers, not the body that ran or measured the system (analytics red team).
    return (source["source_role"] in FIRST_PARTY_ROLES
            and "wikipedia" not in (source.get("publisher") or "").lower()
            and "wikipedia.org" not in (source.get("url") or "").lower())


def source_health(events):
    """Describe the citations behind a country's published events, inside that country only.

    Counts, not judgements: how many citations, from how many publishers, in which roles and
    languages, how many carry their own date, and whether the research lane recorded opening
    them. "Not recorded" is kept apart from "not opened": most lanes before iteration 16 never
    said. Nothing here is comparable across countries, and no count enters a number.
    """
    cites = [s for e in events for s in e["sources"]]
    roles, langs = {}, {}
    for s in cites:
        roles[s["source_role"]] = roles.get(s["source_role"], 0) + 1
        langs[s["language"]] = langs.get(s["language"], 0) + 1
    return {
        "events": len(events),
        "citations": len(cites),
        "publishers": len({s["publisher"] for s in cites}),
        "by_role": dict(sorted(roles.items())),
        "by_language": dict(sorted(langs.items())),
        "opened": {"opened": sum(1 for s in cites if s.get("opened") is True),
                   "not_opened": sum(1 for s in cites if s.get("opened") is False),
                   "not_recorded": sum(1 for s in cites if s.get("opened") is None)},
        "dated": sum(1 for s in cites if s.get("date")),
        "single_source_events": sum(1 for e in events if len(e["sources"]) == 1),
        "events_with_first_party_source": sum(
            1 for e in events if any(_first_party(s) for s in e["sources"])),
        "first_party_roles": list(FIRST_PARTY_ROLES),
        "first_party_excludes": "Wikipedia, whatever role a record gives it",
        "note": ("Describes the citations of the published events in this country. Not opened and "
                 "not recorded are different: a lane that did not record whether it opened a "
                 "source is not evidence that it did not. Nothing here is comparable across "
                 "countries and nothing here enters a number."),
    }


# Normalised source roles for reporting-environment transparency (iteration 18). A role a lane
# wrote maps to one family; an unmapped role stays visible as "other" rather than being guessed.
SOURCE_FAMILY_OF_ROLE = {"government": "government_news", "official": "government_news", "regulator": "regulator",
                         "operator": "company_operator", "dataset": "structured_dataset",
                         "industry": "specialist_media", "aggregator": "specialist_media",
                         "statistics": "national_statistics", "system_operator": "system_operator"}
SOURCE_FAMILY_LABEL = {"national_statistics": "National statistics", "regulator": "Regulator",
                       "system_operator": "System operator", "company_operator": "Company or operator",
                       "government_news": "Government or government news", "structured_dataset": "Structured dataset",
                       "international_media": "International media", "national_media": "National media",
                       "specialist_media": "Specialist media", "other": "Other"}
INTERNATIONAL_PUBLISHERS = ("reuters", "bloomberg", "associated press", "ap news", "afp", "bbc", "financial times",
                            "al jazeera", "wall street journal", "new york times", "guardian", "cnn")


def _source_family(s):
    role = s.get("source_role")
    if role == "media":
        pub = (s.get("publisher") or "").lower()
        return "international_media" if any(p in pub for p in INTERNATIONAL_PUBLISHERS) else "national_media"
    return SOURCE_FAMILY_OF_ROLE.get(role, "other")


def source_families(doc, events):
    """Which families of source appear behind this country's events. A set, not a score."""
    present = sorted({_source_family(s) for e in events for s in e["sources"]})
    return {"present": present, "labels": {k: SOURCE_FAMILY_LABEL[k] for k in present},
            "note": "Which kinds of source the published events cite. Shows the reporting environment; it is not a quality score."}


def citation_quality(system_id, events):
    """How the citations behind one country's events stand. Inside a country only: never summed,
    never set beside another's, and deliberately not reduced to one number. A dated publication
    is the date the record's researcher or the page itself states; it is never inferred from an
    address or a retrieval date."""
    cites = [s for e in events for s in e["sources"]]
    languages, precision = {}, {}
    for s in cites:
        lang = s.get("language") or "not recorded"
        languages[lang] = languages.get(lang, 0) + 1
    for e in events:
        precision[e["date_precision"]] = precision.get(e["date_precision"], 0) + 1
    health = read_json(LINK_HEALTH) if LINK_HEALTH.exists() else {}
    return {
        "citations": len(cites),
        "with_publication_date": sum(1 for s in cites if s.get("date")),
        "languages": dict(sorted(languages.items())),
        "event_date_precision": dict(sorted(precision.items())),
        "link_check": (health.get("by_system") or {}).get(system_id),
        "link_check_date": health.get("checked"),
        "link_check_note": health.get("note"),
    }


def recovery_coverage(events):
    """Four separate answers, and the withheld state apart from them (iteration 18). No modelled
    fallback exists: an event with no report says so, and never ages out as recovered."""
    out = {"observed": 0, "estimate": 0, "other_statement": 0, "researched_no_public_evidence": 0,
           "not_researched": 0, "withheld_active_campaign": 0}
    by_class = {}
    for e in events:
        r = e["recovery"]
        if r["research_status"] == WITHHELD:
            k = "withheld_active_campaign"
        elif r["research_status"] == "NOT_YET_RESEARCHED":
            k = "not_researched"
        elif r["research_status"] == "RESEARCHED_NO_PUBLIC_EVIDENCE":
            k = "researched_no_public_evidence"
        elif r["kind"] in OBSERVED_RECOVERY_KINDS:
            k = "observed"
        elif r["kind"] == "estimate":
            k = "estimate"
        else:
            k = "other_statement"
        out[k] += 1
        if k == "not_researched":
            by_class[e["asset_class"]] = by_class.get(e["asset_class"], 0) + 1
    # Aggregated research priorities only: named facilities never appear in a queue on the site.
    out["unresearched_by_class"] = dict(sorted(by_class.items()))
    out["policy"] = ("Observed recovery, or a sourced estimate labelled as an estimate. Nothing is modelled, and an "
                     "event never ages out as recovered.")
    return out


def load_admin1():
    fetch(ADMIN1_URL, "ne_10m_admin_1.geojson", max_age_hours=24 * 30)
    return read_json(RAW / "ne_10m_admin_1.geojson")


def load_admin0():
    fetch(ADMIN0_URL, "ne_50m_admin_0.geojson", max_age_hours=24 * 30)
    return read_json(RAW / "ne_50m_admin_0.geojson")


def _code(props):
    c = props.get("iso_3166_2") or ""
    fixed = NAME_CODE_FIXES.get((props.get("adm0_a3"), props.get("name")))
    return fixed or ISO_CODE_FIXES.get(c, c)


def units(system_id, admin1, admin0):
    """[(code, name, geometry)] for a country system's first-level units.

    Membership is by the unit's admin-0 code in Natural Earth's DEFAULT edition, which draws the
    line of actual control. Its country-viewpoint editions each move several borders and no two
    agree, so none of them is used (GLOBAL_GEOGRAPHY.md).
    """
    a3s = set(systems.system(system_id)["admin0_a3"])
    sars = SAR_UNITS.get(system_id, {})
    out = []
    for f in admin1["features"]:
        p = f["properties"]
        if p.get("adm0_a3") in a3s and p.get("adm0_a3") not in sars:
            out.append((_code(p), p.get("name") or _code(p), f["geometry"]))
    for f in admin0["features"]:
        a3 = f["properties"].get("ADM0_A3")
        if a3 in sars:
            code, name = sars[a3]
            out.append((code, name, f["geometry"]))
    for a3, n in NAME_CODE_COMPLETE.items():
        if a3 in a3s:
            mapped = {c for (a, _), c in NAME_CODE_FIXES.items() if a == a3}
            got = [u[0] for u in out]
            if sorted(got) != sorted(mapped) or len(got) != n:
                raise ValueError(f"system {system_id}: units {sorted(set(got) ^ mapped)} are not covered "
                                 "by the name-to-code table; a renamed or new unit must be added to it")
    return sorted(out, key=lambda u: u[0])


def _bounds(geoms):
    """[w, s, e, n] over several geometries, kept on one side of the antimeridian.

    The Aleutians cross 180°, so a plain min/max gives the US a bounding box spanning the whole
    globe and the map would open zoomed out to the planet. When the span exceeds 180° the
    eastern-hemisphere longitudes are shifted by -360 so the box is contiguous.
    """
    lons, lats = [], []
    for g in geoms:
        for poly in geo._polygons(g):
            for x, y in poly[0]:
                lons.append(x)
                lats.append(y)
    if max(lons) - min(lons) > 180:
        lons = [x - 360 if x > 0 else x for x in lons]
    return [round(min(lons), 2), round(min(lats), 2), round(max(lons), 2), round(max(lats), 2)]


def _region_status(code, rulings):
    for r in rulings:
        if r["code"] == code:
            return r["status"], r["note"]
    return "normal", None


def _event(raw, unit_names):
    ev = {k: raw.get(k) for k in EVENT_FIELDS}
    ev.update({k: raw[k] for k in OPTIONAL_EVENT_FIELDS if raw.get(k)})
    ev["sources"] = [{**{k: s.get(k) for k in SOURCE_FIELDS},
                      **{k: s[k] for k in OPTIONAL_SOURCE_FIELDS if s.get(k)}} for s in raw["sources"]]
    ev["recovery"] = {k: (raw.get("recovery") or {}).get(k) for k in RECOVERY_FIELDS}
    ev["region_name"] = unit_names.get(ev["region_code"]) if ev["region_code"] else None
    return ev


# DUAL REVIEW (iteration 16, docs/REVIEW_GOVERNANCE.md). One researcher may find a record; a
# record reaches the canonical public corpus only after a second, independent reviewer has opened
# the evidence. Records published before the rule existed are grandfathered BY ID in a frozen list
# that can only shrink; a new record cannot be added to it, so "legacy" is not a way round review.
REVIEW_STATUSES = ("blind_reviewed", "dual_reviewed", "legacy_single_review")
# Iteration 17: three blind roles, every one of which must have accepted (REVIEW_GOVERNANCE §7).
BLIND_ROLES = ("evidence", "safety", "taxonomy")
BLIND_PASS = ("accept", "accept_with_correction")
REVIEW_DISPOSITIONS = ("confirmed", "corrected")
GRANDFATHERED = SYSTEMS_CURATED / "review_grandfathered.json"
CAMPAIGNS = SYSTEMS_CURATED / "conflict_campaigns.json"


def load_grandfathered():
    return set(read_json(GRANDFATHERED)["event_ids"])


def review_problems(e, grandfathered):
    """Why this record's review block cannot be published, or [] if it can."""
    eid, r = e["event_id"], e.get("review") or {}
    status = r.get("review_status")
    if status not in REVIEW_STATUSES:
        return [f"{eid}: review status {status!r} is not one of {REVIEW_STATUSES}"]
    out = []
    if not r.get("primary_review_complete"):
        out.append(f"{eid}: primary review not complete")
    if r.get("source_count") != len(e["sources"]):
        out.append(f"{eid}: review source_count {r.get('source_count')!r} != {len(e['sources'])} sources")
    if status == "legacy_single_review":
        if eid not in grandfathered:
            out.append(f"{eid}: single-reviewed, and not a grandfathered pre-iteration-16 record")
        if r.get("independent_review_complete") or r.get("reviewer_count") != 1:
            out.append(f"{eid}: a legacy record claims an independent review it did not have")
    else:
        if not r.get("independent_review_complete"):
            out.append(f"{eid}: no independent review")
        if (r.get("reviewer_count") or 0) < (4 if status == "blind_reviewed" else 2):
            out.append(f"{eid}: {status} needs {'a researcher and three blind reviewers' if status == 'blind_reviewed' else 'two reviewers'}")
        if status == "blind_reviewed":
            roles = r.get("roles") or {}
            failed = [k for k in BLIND_ROLES if roles.get(k) not in BLIND_PASS]
            if failed:
                out.append(f"{eid}: blind review role(s) {failed} did not accept")
        if (r.get("sources_opened_by_reviewer") or 0) < 1:
            out.append(f"{eid}: the independent reviewer opened no source")
        if r.get("disposition") not in REVIEW_DISPOSITIONS:
            out.append(f"{eid}: review disposition {r.get('disposition')!r} is not one of {REVIEW_DISPOSITIONS}")
    return out


LINK_HEALTH = SYSTEMS_CURATED / "source_link_health.json"


def load_campaigns():
    return read_json(CAMPAIGNS)


def campaign_of(e, system_id, campaigns):
    """The ACTIVE campaign whose publication rule covers this record, or None.

    A record is covered by cause and date, or by name in `member_rule.also_covers`: a record at a
    struck site whose own cause is not kinetic still reports that site's status (iteration 16,
    safety red team: the Juaymah LPG halt traced a struck facility's outage for seven months)."""
    for c in campaigns.get("campaigns", []):
        rule = c.get("member_rule") or {}
        # `policy_applied` is the switch, not `status`: an uncertain or recently ended campaign
        # still withholds, and `campaign_problems` refuses to let the switch be turned off early.
        if c["system_id"] != system_id or not c.get("policy_applied"):
            continue
        named = {x["event_id"] for x in rule.get("also_covers", [])}
        if e["event_id"] in named or (e["cause"] in rule.get("causes", KINETIC_CAUSES)
                                      and e["date"] >= rule.get("from", "")):
            return c
    return None


def campaign_problems(campaigns, today=None):
    """Why the campaign file cannot be trusted to withhold what it should. Fail closed: an active or
    uncertain campaign always applies the policy, an ended one keeps applying it until the release
    period has passed, and a system classified as restricted has a campaign that covers it."""
    today = today or dt.date.today()
    wait = (campaigns.get("release_rule") or {}).get("release_after_end_days", 30)
    out = []
    for c in campaigns.get("campaigns", []):
        cid = c.get("campaign_id")
        if c.get("status") not in ("active", "uncertain", "ended"):
            out.append(f"{cid}: status {c.get('status')!r}")
        if c.get("status") in ("active", "uncertain") and not c.get("policy_applied"):
            out.append(f"{cid}: {c.get('status')} but the publication policy is not applied")
        if c.get("status") == "ended" and not c.get("policy_applied"):
            ended = c.get("ended")
            if not ended or (today - dt.date.fromisoformat(ended)).days < wait:
                out.append(f"{cid}: policy lifted before {wait} days after its recorded end")
        if c.get("status") == "ended" and not c.get("ended"):
            out.append(f"{cid}: ended with no end date")
    states = campaigns.get("system_states") or {}
    for sid, s in states.items():
        if s.get("state") not in CAMPAIGN_STATES:
            out.append(f"system state {sid}: {s.get('state')!r} is not one of {CAMPAIGN_STATES}")
        if not (s.get("checked") and s.get("basis")):
            out.append(f"system state {sid}: needs a dated basis")
        covered = any(c["system_id"] == sid and c.get("policy_applied") for c in campaigns.get("campaigns", []))
        if s.get("state") in RESTRICTING_STATES and not covered:
            out.append(f"system state {sid}: {s.get('state')} with no campaign applying the policy")
    for sid in systems.GROUPS["gulf_littoral"]["members"]:
        if sid not in states:
            out.append(f"system {sid}: no campaign classification; a Gulf system must state one")
    return out


def precision_problems(system_id, doc, events):
    """Admin-1 is a maximum, never an entitlement (iteration 19). Where a system's policy puts
    kinetic and sabotage events at country level, such a record carries no region, no facility, no
    operator and an opaque id: in a small state a governorate plus a class already names the plant."""
    policy = (doc.get("geography") or {}).get("precision_policy") or {}
    out = []
    if policy.get("kinetic") not in (None, "admin1", "country"):
        out.append(f"precision policy kinetic {policy.get('kinetic')!r}")
    if policy.get("other") not in (None, "admin1", "country"):
        out.append(f"precision policy other {policy.get('other')!r}")
    if policy.get("other") == "country" and policy.get("kinetic") != "country":
        out.append("a system that places no ordinary event in a region cannot place an attack in one")
    if policy and not policy.get("reason"):
        out.append("a precision policy states its reason")
    barred = set(policy.get("no_event_units") or [])
    for e in events:
        eid = e["event_id"]
        if e.get("region_code") in barred or barred & set(e.get("regions_affected") or []):
            out.append(f"{eid}: placed in a unit that is drawn but never used for events")
        if policy.get("kinetic") == "country" and e["cause"] in KINETIC_CAUSES:
            if e["geography_precision"] != "country" or e.get("region_code") or e.get("regions_affected"):
                out.append(f"{eid}: a kinetic record here is published at country level only")
            for k in ("facility_name", "facility_name_local", "operator"):
                if e.get(k):
                    out.append(f"{eid}: {k} on a kinetic record under a country-level policy")
            if not re.fullmatch(OPAQUE_ID.format(cc=system_id), eid):
                out.append(f"{eid}: a kinetic record under a country-level policy needs an opaque id")
        if policy.get("other") == "country" and (e["geography_precision"] != "country" or e.get("region_code")
                                                 or e.get("regions_affected")):
            # The drawn units are not the current ones, or the state is too small for a region to
            # be an abstraction: every record is the country's.
            out.append(f"{eid}: every record in this system is published at country level")
        cal = e.get("date_calendar")
        if cal and cal not in DATE_CALENDARS:
            out.append(f"{eid}: unknown calendar {cal!r}")
        if cal and cal != "gregorian" and not (e.get("source_date_text") and e.get("conversion_basis")):
            out.append(f"{eid}: a converted date must keep the source's text and the conversion basis")
    if doc.get("maturity", "monitored") not in MATURITY:
        out.append(f"maturity {doc.get('maturity')!r}")
    return out


# A citation published long after a covered event is where restart and operating status live, and
# an opaque address ("/news/1996027") cannot be read for it. Such citations stay in the queue with
# the other status evidence while the campaign is active.
LATE_CITATION_DAYS = 7


def late_citation(e, source):
    """True if `source` was published more than LATE_CITATION_DAYS after the event (after the end
    of the month for a month-precision date). An undated source counts as late."""
    if not source.get("date"):
        return True
    start = dt.date.fromisoformat(e["date"][:10])
    if e.get("date_precision") == "month":
        start = (start.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    return (dt.date.fromisoformat(source["date"][:10]) - start).days > LATE_CITATION_DAYS


def apply_publication_policy(system_id, events, campaigns):
    """Mark, and check, every record covered by an active campaign's publication rule.

    The curated record must ALREADY carry the withheld marker: the import gate writes it, so the
    evidence stays in the local queue and never reaches the public repository. The build refuses a
    covered record that still holds recovery evidence or current-status wording, and refuses the
    withheld marker on a record no active campaign covers, so a campaign recorded as ended forces a
    re-import rather than leaving status hidden by accident."""
    problems = []
    for e in events:
        c = campaign_of(e, system_id, campaigns)
        rec = e["recovery"]
        if c is None:
            e["publication"] = None
            if rec["research_status"] == WITHHELD:
                problems.append(f"{e['event_id']}: recovery withheld but no active campaign covers it")
            continue
        e["publication"] = {
            "rule": "active_campaign_current_status_withheld",
            "campaign_id": c["campaign_id"],
            "withheld": ["recovery", "status_citations"],
            # Plain reason first (UX red team, iteration 16); the policy document is named in
            # `rule` and in the sources panel, not as a file path in the reader's way.
            "note": ("Attacks on this country's energy facilities are still being reported. Saying "
                     "whether a struck facility is back in operation could help time another "
                     "attack, so the event is published but the facility's restart, recovery and "
                     "operating status are not, nor are reports of them, until the campaign has "
                     "ended."),
        }
        if rec["research_status"] != WITHHELD or any(rec[k] for k in ("kind", "date", "evidence", "url")):
            problems.append(f"{e['event_id']}: under active campaign {c['campaign_id']} but its "
                            "recovery block is not the withheld marker")
        if e.get("date_end"):
            problems.append(f"{e['event_id']}: under active campaign {c['campaign_id']} but carries "
                            "an end date, which says when the facility's outage ended")
        texts = [("summary", e.get("summary")), ("effect", e.get("effect")),
                 ("threshold basis", e.get("threshold_basis")),
                 ("capacity note", (e.get("capacity_affected") or {}).get("source_says")),
                 ("facility name", e.get("facility_name")), ("operator", e.get("operator")),
                 ("hazard name", e.get("hazard_name"))]
        texts += [("citation", s.get("url")) for s in e["sources"]]
        texts += [("publisher", s.get("publisher")) for s in e["sources"]]
        for src in e["sources"]:
            if late_citation(e, src):
                problems.append(f"{e['event_id']}: citation dated {src.get('date')} is more than "
                                f"{LATE_CITATION_DAYS} days after the event under an active campaign")
        for field, text in texts:
            m = status_wording(text)
            if m:
                problems.append(f"{e['event_id']}: {field} reports current status ({m.group(0)!r}) "
                                "under an active campaign")
        if not e["sources"]:
            problems.append(f"{e['event_id']}: under active campaign {c['campaign_id']} with no "
                            "publishable citation")
    if problems:
        raise ValueError(f"system {system_id} publication policy: " + "; ".join(problems))


def validate(system_id, doc, events, unit_codes, grandfathered=None):
    """Refuse a system whose curated sources break the rules the UI depends on.

    A build failure here is deliberate: a country shown with an unstated sector, an event in a
    region the map cannot draw, or a vocabulary term with no label would render as a blank or a
    plausible-looking guess, which is the one outcome this project exists to avoid.
    """
    problems = []
    seen = {s["sector"] for s in doc["sectors"]}
    if seen != set(SECTORS):
        problems.append(f"sector states must cover exactly {sorted(SECTORS)}; got {sorted(seen)}")
    for s in doc["sectors"]:
        if s["state"] not in systems.SECTOR_STATES:
            problems.append(f"unknown sector state {s['state']!r}")
        if s["state"] in ("SCORED", "EXPERIMENTAL"):
            # Nothing outside the theatre is computed this iteration. A state claiming a value
            # with no value behind it would be a promise the payload cannot keep.
            problems.append(f"{s['sector']}: {s['state']} needs a computed value; none exists")
        if not s.get("reason"):
            problems.append(f"{s['sector']}: a state with no reason")
        if s.get("assessed_readiness") not in ASSESSMENTS:
            problems.append(f"{s['sector']}: unknown assessment {s.get('assessed_readiness')!r}")
    if doc["reporting_environment"] not in systems.REPORTING_ENVIRONMENTS:
        problems.append(f"unknown reporting environment {doc['reporting_environment']!r}")
    classes = set(ASSET_CLASSES) | set(TAXONOMY_EXTENSIONS["asset_classes"])
    causes = set(DISRUPTION_CAUSES) | set(TAXONOMY_EXTENSIONS["causes"])
    ids_seen = set()
    for e in events:
        eid = e["event_id"]
        if eid in ids_seen:
            problems.append(f"duplicate event id {eid}")
        ids_seen.add(eid)
        if e["asset_class"] not in classes:
            problems.append(f"{eid}: unknown asset class {e['asset_class']!r}")
        if e["cause"] not in causes:
            problems.append(f"{eid}: unknown cause {e['cause']!r}")
        if e["geography_precision"] == "admin1" and e["region_code"] not in unit_codes:
            problems.append(f"{eid}: region {e['region_code']!r} is not a unit of this system")
        if e["geography_precision"] != "admin1" and e["region_code"]:
            problems.append(f"{eid}: a country-level event must not carry a region code")
        if not e["sources"] or not all(s.get("url") for s in e["sources"]):
            problems.append(f"{eid}: every event needs at least one source, each with a URL")
        rs, kind = e["recovery"]["research_status"], e["recovery"]["kind"]
        if rs not in RECOVERY_STATUSES:
            problems.append(f"{eid}: recovery research status must be one of {RECOVERY_STATUSES}")
        if rs == "EVIDENCE_FOUND" and kind not in RECOVERY_KINDS:
            problems.append(f"{eid}: evidence found but its kind {kind!r} is not one of {RECOVERY_KINDS}")
        if rs != "EVIDENCE_FOUND" and kind is not None:
            problems.append(f"{eid}: a recovery kind without evidence")
        if not e.get("review"):
            problems.append(f"{eid}: not reviewed")
        else:
            problems += review_problems(e, grandfathered if grandfathered is not None else load_grandfathered())
    if problems:
        raise ValueError(f"system {system_id}: " + "; ".join(problems))


def validate_episodes(system_id, declared, events):
    """Refuse an episode file that would silently merge, drop or double-count records, or group
    them on anything weaker than an explicit statement (iteration 16 invariants):

      * every record belongs to exactly one episode (a record no episode names is a singleton);
      * no record is in two episodes, and every episode stays inside this system;
      * a declared basis is one of the explicit bases, never a retired one or proximity;
      * a named-hazard episode names its hazard, and every member names the same hazard;
      * two records naming the same hazard are in the same episode (so dropping a member fails);
      * an explicit-common-event, wave or continuation episode cites the source that says so,
        and that source is one its members already cite.
    """
    by_id = {e["event_id"]: e for e in events}
    problems, seen_eps, owner = [], set(), {}
    for ep in declared:
        eid = ep["episode_id"]
        if eid in seen_eps or eid in by_id:
            # An undeclared record is its own episode under its own id, so an episode id equal
            # to an event id would merge two different things under one key.
            problems.append(f"episode id {eid!r} is not unique")
        seen_eps.add(eid)
        if not eid.startswith(f"{system_id}-"):
            problems.append(f"{eid}: an episode id must belong to system {system_id!r}")
        basis = ep.get("basis")
        if basis in RETIRED_EPISODE_BASES:
            problems.append(f"{eid}: basis {basis!r} is retired ({RETIRED_EPISODE_BASES[basis]})")
        elif basis not in EPISODE_BASES:
            problems.append(f"{eid}: unknown basis {basis!r}")
        if not ep.get("name"):
            problems.append(f"{eid}: an episode needs a name")
        if len(ep["event_ids"]) < 2:
            problems.append(f"{eid}: a declared episode groups at least two records")
        for m in ep["event_ids"]:
            if m not in by_id:
                problems.append(f"{eid}: no event {m!r} in system {system_id}")
            elif m in owner:
                problems.append(f"{m} is in two episodes ({owner[m]}, {eid})")
            owner[m] = eid
        members = [by_id[m] for m in ep["event_ids"] if m in by_id]
        if basis == "named_hazard":
            hazard = ep.get("hazard")
            if not hazard:
                problems.append(f"{eid}: a named-hazard episode must name its hazard")
            for m in members:
                if m.get("hazard_name") != hazard:
                    problems.append(f"{eid}: member {m['event_id']} names hazard "
                                    f"{m.get('hazard_name')!r}, not {hazard!r}")
        elif basis in EVIDENCED_BASES:
            ev = ep.get("evidence") or {}
            cited = {s["url"] for m in members for s in m["sources"]}
            if not (ev.get("url") and ev.get("says")):
                problems.append(f"{eid}: basis {basis!r} needs evidence {{url, says}} from a source")
            elif ev["url"] not in cited:
                problems.append(f"{eid}: its evidence URL is not a source of any member")
            elif basis != "explicit_continuation" and sum(
                    1 for m in members if any(s["url"] == ev["url"] for s in m["sources"])) < 2:
                # One member's source cannot vouch for the others (test-architecture red team). A
                # continuation is the exception: the later record's own source says what it
                # continues.
                problems.append(f"{eid}: its evidence URL is cited by only one member")
        # Two different named hazards are two events, whatever basis is claimed.
        hazards = {m.get("hazard_name") for m in members if m.get("hazard_name")}
        if len(hazards) > 1:
            problems.append(f"{eid}: members name different hazards {sorted(hazards)}")
    # Same hazard, same episode. Without this, a hurricane's records could be split across a
    # declared episode and a stray singleton and counted twice.
    by_hazard = {}
    for e in events:
        if e.get("hazard_name"):
            by_hazard.setdefault(e["hazard_name"], set()).add(owner.get(e["event_id"], e["event_id"]))
    for hazard, eps in sorted(by_hazard.items()):
        if len(eps) > 1:
            problems.append(f"records naming {hazard!r} are split across episodes {sorted(eps)}")
    if problems:
        raise ValueError(f"system {system_id} episodes: " + "; ".join(problems))
    return owner


def episodes_of(declared, events):
    """One entry per episode among `events`, in date order. A record no episode declares is an
    episode of one, under its own id: every record has an episode, and the count of episodes is
    never smaller than the evidence allows."""
    by_id = {ep["episode_id"]: ep for ep in declared}
    groups = {}
    for e in events:
        groups.setdefault(e["episode_id"], []).append(e)
    out = []
    for eid, members in groups.items():
        ep = by_id.get(eid)
        regions = sorted({e["region_code"] for e in members if e["region_code"]})
        out.append({
            "episode_id": eid,
            "name": ep["name"] if ep else None,
            "basis": ep["basis"] if ep else SINGLETON,
            "hazard": ep.get("hazard") if ep else None,
            "event_ids": [e["event_id"] for e in members],
            "records": len(members),
            "first_date": min(e["date"] for e in members),
            "last_date": max((e.get("date_end") or e["date"]) for e in members),
            "region_codes": regions,
            # A record with no region code is country-level; the episode says so rather than
            # implying its regions are the whole footprint.
            "has_country_level_record": any(not e["region_code"] for e in members),
        })
        # Episode dates are derived from their members, so they always encompass them; asserted
        # anyway because a later change that let an episode carry its own dates would break it.
        assert all(out[-1]["first_date"] <= e["date"] <= out[-1]["last_date"] for e in members)
    out.sort(key=lambda x: (x["first_date"], x["episode_id"]))
    return out


def onboarding_gate(doc, events, profile, research_log=None):
    """The eight-point gate of GLOBAL_METHODOLOGY §7.2, evaluated rather than asserted.

    The five countries are shown before every item is met, so the payload says which are not:
    a research preview that hides its own gaps would be the overclaim this project exists to
    avoid. Items the code cannot check are stated with the reason they are partial.
    """
    metrics = profile.get("metrics", [])
    # Item 7 was one gate meaning two things until iteration 16. It is now two independent items:
    # 7A asks whether every source states its freshness; 7B asks whether the event SEARCH was
    # systematic and finished. Neither is derived from the other: a registry checked yesterday
    # says nothing about whether the search covered the window.
    in_use = [s for s in doc["sources"] if _in_use(s)]
    unstated = [s["name"] for s in in_use
                if not (s.get("last_checked") and s.get("publication_cadence") and s.get("stale_policy"))]
    rf = research_freshness(research_log or {})
    no_basis = [m["metric"] for m in metrics if not m.get("basis")]
    rulings_needed = any(r["status"] != "note" for r in doc["geography"].get("rulings", []))

    def item(n, label, status, note):
        return {"item": n, "label": label, "status": status, "note": note}

    return [
        item(1, "Scope statement and disputed-territory ruling", "met",
             "Geography and rulings stated; no aggregate exists, so whether disputed areas count "
             "in one is not yet a live question." if rulings_needed else "Geography stated; no "
             "disputed units."),
        item(2, "Source registry with licence, cadence and reporting environment", "met",
             "Every source in use states its licence and publication cadence; the reporting "
             "environment is set. The event record itself is curated by hand, and its research "
             "passes are logged with the window each covered."),
        item(3, "Every sector has an explicit state", "met", "Enforced by the build."),
        item(4, "Context statistics carry source, vintage and basis",
             "met" if not no_basis else "partial",
             "All context metrics state a basis." if not no_basis else
             f"{len(no_basis)} of {len(metrics)} context metrics state no basis."),
        item(5, "Threshold declared; every event carries its basis, criterion and episode",
             "met", "Threshold, inclusion basis, criterion and episode on every event. Episodes "
                    "are curated by hand under a stated rule, and counts are given in both "
                    "records and episodes."),
        item(6, "Safety tests extended to the country", "met",
             "The served-data gates recurse into every country payload."),
        item("7A", "Source freshness: last check, cadence and stale policy per source",
             "unmet" if not in_use else "met" if not unstated else "partial",
             "No source is in use, so nothing can be fresh." if not in_use else
             "Every source in use states when it was last checked, how often it publishes and which "
             "stale policy applies. Met means the metadata is stated, not that every source is "
             "within its limit: the page marks any source past its limit on the reader's clock."
             if not unstated else f"{len(unstated)} source(s) in use state no freshness metadata."),
        item("7B", "Systematic research coverage",
             {"complete": "met", "partial": "partial"}.get(rf["completeness"], "unmet"),
             {"complete": f"The newest systematic pass ({rf['last_systematic_pass']}) executed every "
                          "declared source lane over its window.",
              "partial": f"The newest systematic pass ({rf['last_systematic_pass']}) did not execute "
                         "every declared source lane; see the research log for which and why."
              }.get(rf["completeness"],
                    "No systematic pass yet: the record comes from targeted searches only, so "
                    "events that no search looked for are missing.")),
        item(8, "Comparability fields and structural rules", "met",
             "comparability 'none', reporting environment on every count, fixed alphabetical "
             "order, no shared scale."),
    ]


def _readiness(doc):
    """Country-level readiness, derived from sector states rather than declared."""
    states = {s["state"] for s in doc["sectors"]}
    if "SCORED" in states:
        return "INDEX_READY"
    if "EXPERIMENTAL" in states:
        return "EXPERIMENTAL"
    if "CONTEXT_ONLY" in states:
        return "CONTEXT_ONLY"
    return "INSUFFICIENT_EVIDENCE"


def build_system(system_id, admin1, admin0, as_of):
    src = SYSTEMS_CURATED / system_id
    doc = read_json(src / "system.json")
    profile = read_json(src / "profile.json")
    raw_events = read_json(src / "events.json")["events"]
    declared = read_json(src / "episodes.json")["episodes"] if (src / "episodes.json").exists() else []
    research_log = read_json(src / "research_log.json")
    validate_sources(system_id, doc, research_log)
    campaigns = load_campaigns()
    reg = systems.system(system_id)

    us = units(system_id, admin1, admin0)
    unit_codes = {u[0] for u in us}
    unit_names = {u[0]: u[1] for u in us}
    if doc["geography"]["units_expected"] != len(us):
        raise ValueError(f"system {system_id}: expected {doc['geography']['units_expected']} "
                         f"first-level units, Natural Earth gave {len(us)}")
    events = sorted((_event(r, unit_names) for r in raw_events),
                    key=lambda e: (e["date"], e["event_id"]))
    episode_of = validate_episodes(system_id, declared, events)
    for e in events:
        e["episode_id"] = episode_of.get(e["event_id"], e["event_id"])
    validate(system_id, doc, events, unit_codes)
    problems = precision_problems(system_id, doc, events) + campaign_problems(campaigns)
    if problems:
        raise ValueError(f"system {system_id}: " + "; ".join(problems))
    apply_publication_policy(system_id, events, campaigns)
    # An event dated after TODAY is a curation error and fails the build. An event dated after
    # the build's --as-of is not: a historical rebuild (the frozen 2026-08-28 regression) must
    # reconstruct the record as of that date, the way the theatre does, rather than refuse to
    # run because the corpus has grown since (iteration 14 found the refusal).
    today = dt.date.today().isoformat()
    future = [e["event_id"] for e in events if e["date"] > max(as_of, today)]
    if future:
        raise ValueError(f"system {system_id}: events dated in the future: {future}")
    later = sum(1 for e in events if e["date"] > as_of)
    events = [e for e in events if e["date"] <= as_of]
    # Computed after the as-of filter, so a historical build's episodes hold only the records
    # that existed by then.
    episodes = episodes_of(declared, events)

    counts = {}
    for e in events:
        if e["geography_precision"] == "admin1":
            counts[e["region_code"]] = counts.get(e["region_code"], 0) + 1

    tol = REGION_TOLERANCE.get(system_id, DEFAULT_TOLERANCE)
    features, kept = [], []
    for code, name, g in us:
        s = geo.simplify_geometry(g, tol)
        if s is None:
            raise ValueError(f"system {system_id}: unit {code} vanished on simplification")
        status, note = _region_status(code, doc["geography"].get("rulings", []))
        kept.append(s)
        features.append({
            "type": "Feature",
            "properties": {"code": code, "name": name, "status": status, "note": note,
                           # A disputed, unassigned unit never carries an event count: an
                           # absence there is "not applicable", not "nothing happened".
                           "recorded_events": None if status == "disputed_unassigned"
                           else counts.get(code, 0)},
            "geometry": geo.round_coords(s, 3),
        })

    used_classes = sorted({e["asset_class"] for e in events})
    used_causes = sorted({e["cause"] for e in events})
    labels = {**ASSET_CLASSES, **TAXONOMY_EXTENSIONS["asset_classes"]}
    cause_labels = {**DISRUPTION_CAUSES, **TAXONOMY_EXTENSIONS["causes"]}
    recovery_counts = {k: sum(1 for e in events if e["recovery"]["research_status"] == k)
                       for k in RECOVERY_STATUSES}
    kind_counts = {k: sum(1 for e in events if e["recovery"]["kind"] == k) for k in RECOVERY_KINDS}
    reviewed = max((e["review"]["reviewed_at"] for e in events), default=None)
    review_counts = {k: sum(1 for e in events if e["review"]["review_status"] == k) for k in REVIEW_STATUSES}

    payload = {
        "system_id": system_id,
        "name": reg["name"],
        "kind": reg["kind"],
        "as_of": as_of,
        "aliases": list(reg.get("aliases", ())),
        "regional_groups": list(systems.groups_of(system_id)),
        # How far along this system's research is. A preview says so on every surface.
        "maturity": doc.get("maturity", "monitored"),
        "campaign_state": (campaigns.get("system_states") or {}).get(system_id),
        "evidence_readiness": _readiness(doc),
        # No composite exists for any country system. null, never 0: zero would claim
        # "measured, nothing wrong".
        "index": None,
        "headline": None,
        "no_index_reason": (
            "No index is published for this country. The Monitored-Area ESDI's sector weights, "
            "decay horizons and transmission measure were built for a strike campaign and do not "
            "transfer (GLOBAL_METHODOLOGY.md §1-§3). This view shows reported major disruptions "
            "and energy-system context instead."),
        "sectors": [{**s, "label": SECTORS[s["sector"]]} for s in doc["sectors"]],
        "reporting_environment": doc["reporting_environment"],
        "reporting_environment_text": systems.REPORTING_ENVIRONMENTS[doc["reporting_environment"]],
        "reporting_note": doc["reporting_note"],
        "comparability": "none",
        "comparability_statement": COMPARABILITY_STATEMENT,
        "geography": {**doc["geography"], "source": "Natural Earth 1:10m admin-1 (default edition)",
                      "bounds": _bounds(kept),
                      # Where the map opens. Defaults to the full extent; a curated override
                      # exists for the US, whose full extent (the Aleutians to Florida) leaves
                      # the lower 48 a small corner of the frame. Nothing outside it is hidden.
                      "view_bounds": doc["geography"].get("view_bounds") or _bounds(kept)},
        "event_summary": {
            "recorded_events": len(events),
            "episodes": len(episodes),
            "multi_record_episodes": sum(1 for x in episodes if x["records"] > 1),
            "placed_in_a_region": sum(1 for e in events if e["geography_precision"] == "admin1"),
            "country_level": sum(1 for e in events if e["geography_precision"] != "admin1"),
            "recovery_research": recovery_counts,
            "recovery_kinds": kind_counts,
            "excluded_after_as_of": later,
            "first_date": events[0]["date"] if events else None,
            "last_date": events[-1]["date"] if events else None,
            "note": "Counts what was reported and found, not what occurred.",
        },
        "inclusion_threshold": read_json(SYSTEMS_CURATED / "inclusion_threshold.json"),
        "episode_bases": {**EPISODE_BASES, SINGLETON: SINGLETON_TEXT},
        # Who looked at the record before it was published (iteration 16). Counts, not names.
        "review_summary": {
            **review_counts,
            "note": ("Blind reviewed (since iteration 17): three independent reviewers, none of "
                     "whom saw the researcher's reasoning or each other, checked the evidence, the "
                     "safety of the wording and the classification; all three accepted it. Dual "
                     "reviewed: a researcher found the record and a second, independent reviewer "
                     "opened its sources. Legacy: published before independent review was required, "
                     "checked by one reviewer against the threshold and the scope scan; these are "
                     "grandfathered by id and leave the list as they are re-reviewed."),
        },
        "publication_policy": {
            "withheld_records": sum(1 for e in events if e.get("publication")),
            "campaigns": [{k: c.get(k) for k in ("campaign_id", "name", "status", "status_checked",
                                                  "status_basis", "policy_applied")}
                          for c in campaigns.get("campaigns", []) if c["system_id"] == system_id],
            "release_rule": campaigns.get("release_rule"),
        },
        "taxonomy": {"asset_classes": {k: labels[k] for k in used_classes},
                     "causes": {k: cause_labels[k] for k in used_causes}},
        "profile": profile,
        "sources": doc["sources"],
        "source_health": source_health(events),
        "research_gaps": doc["research_gaps"],
        # The build runs daily; the event record does not. Separate dates, so "as of" never
        # implies the corpus was re-checked today (iteration-14 red team).
        "record_reviewed": reviewed,
        "review_freshness_days": doc.get("review_freshness_days", 120),
        "research_log": research_log,
        "research_freshness": research_freshness(research_log),
        "recovery_coverage": recovery_coverage(events),
        "source_families": source_families(doc, events),
        "citation_quality": citation_quality(system_id, events),
        "stale_policies": STALE_POLICIES,
        "onboarding_gate": onboarding_gate(doc, events, profile, research_log),
        "audit_docs": doc["audit_docs"],
    }
    out = outputs.processed() / systems.root(system_id)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "system.json", payload)
    write_json(out / "events.json", {"system_id": system_id, "as_of": as_of, "events": events,
                                     "episodes": episodes})
    write_json(out / "regions.geojson", {"type": "FeatureCollection", "features": features})
    log(f"system {system_id}: {len(events)} events, {len(features)} units, "
        f"readiness {payload['evidence_readiness']}")
    return payload


def build_world(admin1, admin0):
    """A light admin-0 world for the global home.

    Russia is drawn from its admin-1 units, not from Natural Earth's admin-0 polygon, because
    that polygon contains Crimea. Crimea and Sevastopol are emitted as their own features with
    sovereignty Ukraine and status occupied — the same rule the theatre map follows. Painting
    the Russian admin-0 polygon would quietly label Crimea Russian on the first screen a reader
    sees.
    """
    owner = {a3: s["id"] for s in systems.SYSTEMS for a3 in s["admin0_a3"]}
    # Only the theatre's own regions are "monitored": the Far Eastern district is drawn as Russia
    # but is not in the area of interest, and the home map must not claim otherwise.
    theatre_names = {r["natural_earth_name"] for r in read_json(outputs.processed() / "regions.json")
                     if r.get("country") == "RU"}
    # Natural Earth's own disputed units at admin-0 (Siachen) are drawn as disputed, never as
    # anyone's.
    disputed_a3 = {"KAS"}
    feats = []
    for f in admin0["features"]:
        p = f["properties"]
        a3 = p.get("ADM0_A3")
        if a3 == "RUS":
            continue
        g = geo.simplify_geometry(f["geometry"], WORLD_TOLERANCE)
        if g is None:
            continue   # specks below a dashboard pixel at world zoom
        feats.append({"type": "Feature",
                      "properties": {"a3": a3, "name": p.get("NAME"),
                                     "system_id": None if a3 in disputed_a3 else owner.get(a3),
                                     "status": "disputed" if a3 in disputed_a3 else "normal"},
                      "geometry": geo.round_coords(g, 2)})
    for f in admin1["features"]:
        p = f["properties"]
        if p.get("adm0_a3") != "RUS":
            continue
        crimea = p.get("iso_3166_2") in ("UA-43", "UA-40")
        g = geo.simplify_geometry(f["geometry"], WORLD_TOLERANCE)
        if g is None:
            continue
        feats.append({"type": "Feature",
                      "properties": {
                          "a3": "UKR" if crimea else "RUS",
                          "name": p.get("name") if crimea else "Russia",
                          "system_id": "ru" if (crimea or p.get("name") in theatre_names) else None,
                          "status": "occupied" if crimea else "normal",
                          "note": ("Internationally recognised as Ukraine; occupied by Russia. "
                                   "Monitored as a separate unit within the theatre.")
                          if crimea else (None if p.get("name") in theatre_names else
                                          "Part of Russia outside the monitored area. National figures cover the whole country.")},
                      "geometry": geo.round_coords(g, 2)})
    return {"type": "FeatureCollection", "features": feats}


def corpus_totals(country_payloads):
    """Descriptive totals across every country system together (brief §50).

    One number per measure for the five countries summed, never one per country: a per-country
    list here would be a ranking. Lanes are counted from each country's newest systematic pass.
    """
    lanes_done = lanes_all = 0
    states = {}
    for p in country_payloads.values():
        passes = [x for x in p["research_log"]["passes"] if x["kind"] == "systematic"]
        if passes:
            newest = max(passes, key=lambda x: x["date"])
            lanes_all += len(newest.get("lanes") or [])
            lanes_done += sum(1 for l in newest.get("lanes") or [] if _lane_done(l))
            for l in newest.get("lanes") or []:
                s = lane_summary_state(l)
                states[s] = states.get(s, 0) + 1
    tot = lambda f: sum(f(p) for p in country_payloads.values())  # noqa: E731
    return {
        "countries": len(country_payloads),
        "records": tot(lambda p: p["event_summary"]["recorded_events"]),
        "episodes": tot(lambda p: p["event_summary"]["episodes"]),
        "independently_reviewed": tot(lambda p: p["review_summary"].get("blind_reviewed", 0)
                                      + p["review_summary"].get("dual_reviewed", 0)),
        "blind_reviewed": tot(lambda p: p["review_summary"].get("blind_reviewed", 0)),
        "registry_sources": tot(lambda p: sum(1 for s in p["sources"] if _in_use(s))),
        # Observed reports only: an estimate or a "no supply lost" statement is not a report that a
        # facility came back (analytics red team). No withheld-status total: every such record is
        # one country's, so the total would be that country's figure.
        "records_with_observed_recovery": tot(lambda p: sum(
            n for k, n in p["event_summary"]["recovery_kinds"].items() if k in OBSERVED_RECOVERY_KINDS)),
        "records_with_recovery_estimate_only": tot(lambda p: p["event_summary"]["recovery_kinds"].get("estimate", 0)),
        "records_reported_fully_back": tot(lambda p: sum(
            p["event_summary"]["recovery_kinds"].get(k, 0) for k in COMPLETED_RECOVERY_KINDS)),
        "research_lanes_complete": lanes_done,
        "research_lane_states": dict(sorted(states.items())),
        "research_lanes": lanes_all,
        "note": ("Totals for the five country systems together. Counts what was reported, found and "
                 "reviewed, not what occurred; reporting environments differ, so no share of these "
                 "totals belongs to any one country in a comparable way. The theatre is not included."),
    }


def build_manifest(country_payloads, theatre_snapshot, build_time):
    entries = []
    for s in systems.SYSTEMS:
        if s["id"] == systems.THEATRE:
            entries.append({
                "id": s["id"], "name": s["name"], "kind": s["kind"], "root": systems.root(s["id"]),
                "evidence_readiness": "INDEX_READY",
                "index": {"id": "esdi", "name": "Monitored-Area ESDI"},
                "headline": {"value": theatre_snapshot["esdi"], "as_of": theatre_snapshot["as_of"],
                             "label": "Monitored-Area ESDI",
                             "meaning": "Capacity at disrupted sites, not measured loss."},
                "reporting_environment": "conflict_restricted",
                "as_of": theatre_snapshot["as_of"],
                "files": ["snapshot.json"],
            })
            continue
        p = country_payloads[s["id"]]
        entries.append({
            "id": s["id"], "name": s["name"], "kind": s["kind"], "root": systems.root(s["id"]),
            "aliases": p["aliases"], "regional_groups": p["regional_groups"], "maturity": p["maturity"],
            # Whether recovery status is being withheld here, as a flag. Never a count.
            "campaign_restricted": p["publication_policy"]["withheld_records"] > 0
                                   or (p["campaign_state"] or {}).get("state") in RESTRICTING_STATES,
            "evidence_readiness": p["evidence_readiness"], "index": None, "headline": None,
            "reporting_environment": p["reporting_environment"],
            "as_of": p["as_of"],
            "bounds": p["geography"]["bounds"],
            "files": ["system.json", "events.json", "regions.geojson"],
        })
    return {
        "schema_version": 1,
        "build_time": build_time,
        # Rule, source and caveat only. The production values stay in the registry and the
        # selection document: a descending list of country figures in the manifest is a ranking.
        "selection": {**{k: v for k, v in systems.SELECTION.items() if k != "values"},
                      "regional_rule": systems.GULF_SELECTION["rule"]},
        # Members in the registry's alphabetical order. A group is navigation, never a score.
        "groups": {g: {"label": d["label"], "kind": d["kind"], "note": d["note"],
                       "slug": d.get("slug"), "context": d.get("context"),
                       "members": [s["id"] for s in systems.SYSTEMS if s["id"] in d["members"]]}
                   for g, d in systems.GROUPS.items()},
        "comparability_statement": COMPARABILITY_STATEMENT,
        "reporting_environments": systems.REPORTING_ENVIRONMENTS,
        # Fixed, alphabetical order from the registry. Never sorted by any figure.
        "order": "alphabetical by name; never by any figure",
        "corpus": corpus_totals(country_payloads),
        "systems": entries,
    }


# --- the two cross-system artifacts of iteration 18 ------------------------------------------------

RECENT_EPISODES = 40
RECOVERY_MEDIAN_MIN_N = 5     # a prominent summary needs at least this many cases
RECOVERY_RANGE_MIN_N = 3      # below this, cases are listed and no statistic is computed


def _days(a, b):
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def recent_evidence(all_events):
    """The most recent qualifying episodes across the five countries, newest first.

    A chronological list and nothing else: no severity sort, no impact order, no count per
    country. An active campaign's record names its region, class and date, and carries no effect
    text at all, so this cannot become a running tally of what an attack campaign achieved. The
    theatre is not included: its record has its own page and embargo.
    """
    labels = {**ASSET_CLASSES, **TAXONOMY_EXTENSIONS["asset_classes"]}
    causes = {**DISRUPTION_CAUSES, **TAXONOMY_EXTENSIONS["causes"]}
    items = []
    for sid, (name, events, episodes) in all_events.items():
        by_id = {e["event_id"]: e for e in events}
        for ep in episodes:
            members = [by_id[x] for x in ep["event_ids"] if x in by_id]
            if not members:
                continue
            first = members[0]
            rows = [{"date": m["date"], "date_precision": m["date_precision"],
                     "region": m.get("region_name") or ("Multiple regions" if m["regions_affected"] else "National"),
                     "effect": None if m.get("publication") else m.get("effect"),
                     "withheld": bool(m.get("publication"))} for m in members]
            items.append({
                "system_id": sid, "country": name, "episode_id": ep["episode_id"],
                "episode_name": ep["name"] if ep["records"] > 1 else None, "basis": ep["basis"],
                "records": ep["records"], "first_date": ep["first_date"], "last_date": ep["last_date"],
                "date_precision": first["date_precision"],
                "classes": sorted({labels.get(m["asset_class"], m["asset_class"]) for m in members}),
                "causes": sorted({causes.get(m["cause"], m["cause"]) for m in members}),
                "members": rows[:8], "more_members": max(0, len(rows) - 8),
            })
    items.sort(key=lambda x: (x["last_date"], x["system_id"], x["episode_id"]), reverse=True)
    return {
        "order": "newest first; never by size or severity",
        "scope": "The five country systems. Qualifying records only, grouped by episode. Precision is first-level region.",
        "note": ("What was publicly reported, found and reviewed: counts here are not rates of disruption and "
                 "are not comparable between countries. Events can date back to 2022, but systematic research "
                 "for these systems began in 2026, so older records were found later, not monitored as they happened."),
        "episodes": items[:RECENT_EPISODES],
    }


COMPLETED_RECOVERY_KINDS = ("full_restart", "service_restored")
REPORT_DATE_ONLY = re.compile(r"report date|article date|announcement date|publication date", re.I)


def recovery_by_class(all_events):
    """Days to a report of completed recovery, by class and kind, across at least two countries.

    Completed kinds only: a partial report's date is when someone wrote down that restoration was
    under way, so a duration from it says nothing about how long recovery took. Dates that are only
    the date of a report are left out for the same reason. A class seen in one country is not
    emitted, because a row drawn from one country identifies that country, and a recovery figure by
    country is the comparison the data cannot support (iteration 18, analytic red team)."""
    cases, systems_in = {}, {}
    labels = {**ASSET_CLASSES, **TAXONOMY_EXTENSIONS["asset_classes"]}
    for sid, (_, events, _) in all_events.items():
        for e in events:
            r = e["recovery"]
            if r["research_status"] != "EVIDENCE_FOUND" or r["kind"] not in COMPLETED_RECOVERY_KINDS or not r["date"]:
                continue
            if e["date_precision"] != "day" or REPORT_DATE_ONLY.search(r.get("evidence") or ""):
                continue
            d = _days(e["date"], r["date"])
            if d >= 0:
                key = (e["asset_class"], r["kind"])
                cases.setdefault(key, []).append(d)
                systems_in.setdefault(key, set()).add(sid)
    out = []
    withheld = 0
    for (cls, kind), days in sorted(cases.items()):
        if len(systems_in[(cls, kind)]) < 2:
            withheld += 1
            continue
        days = sorted(days)
        row = {"class": cls, "class_label": labels.get(cls, cls), "kind": kind, "n": len(days)}
        if len(days) < RECOVERY_RANGE_MIN_N:
            row["cases_days"] = days
        else:
            row["range_days"] = [days[0], days[-1]]
            if len(days) >= RECOVERY_MEDIAN_MIN_N:
                mid = len(days) // 2
                row["median_days"] = days[mid] if len(days) % 2 else (days[mid - 1] + days[mid]) / 2
        out.append(row)
    return {"rows": out, "single_country_groups_not_shown": withheld,
            "note": ("Days from the event to a dated report that recovery was complete. Partial restorations and dates that "
                     "are only the date of a report are left out, as is any group seen in just one country. Fewer than three "
                     "cases are listed, three or four give a range, five or more a median. These describe what was reported "
                     "and are not a forecast or a country comparison.")}


def data_quality(country_payloads, all_events, context):
    """Research process and data vintage across the systems, in fixed alphabetical order.

    Research-process status may sit side by side; disruption counts may not. So this file holds
    lane states and source dates and no event, record or episode count per country.
    """
    rows = []
    for sid in systems.COUNTRY_SYSTEMS:
        p = country_payloads[sid]
        passes = [x for x in p["research_log"]["passes"] if x["kind"] == "systematic"]
        newest = max(passes, key=lambda x: x["date"]) if passes else None
        lanes = []
        for l in (newest or {}).get("lanes") or []:
            lanes.append({k: l.get(k) for k in ("lane", "source_family", "execution", "source_window", "covered_through",
                                                "languages_required", "languages_executed", "limitation")}
                         | {"state": lane_summary_state(l)})
        used = [s for s in p["sources"] if _in_use(s)]
        rows.append({
            "system_id": sid, "name": p["name"],
            "reporting_environment": p["reporting_environment"],
            "last_systematic_pass": newest["date"] if newest else None,
            "first_systematic_pass": p["research_freshness"]["first_systematic_pass"],
            "lane_states": p["research_freshness"]["lane_states"],
            "lanes": lanes,
            "source_families": p["source_families"]["labels"],
            "sources_checked": [{"name": s["name"], "last_checked": s.get("last_checked"),
                                 "stale_after_days": s.get("stale_after_days")} for s in used],
        })
    return {
        "note": ("Process and vintage only. No disruption count, score or rank appears here, because reporting "
                 "environments differ too much for those to be compared between countries."),
        "context_vintage": {"source": context["source"]["name"], "url": context["source"]["url"],
                            "release": context["source"]["release"], "retrieved": context["source"]["retrieved"],
                            "comparison_year": context["comparison_year"], "update_cadence": context["source"]["update_cadence"],
                            "countries": len(context["countries"]),
                            "note": "National energy statistics. Separate from how recently each country's incident record was researched."},
        "systems": rows,
        "recovery_by_class": recovery_by_class(all_events),
    }


def build(theatre_snapshot):
    as_of = theatre_snapshot["as_of"]
    admin1, admin0 = load_admin1(), load_admin0()
    payloads = {sid: build_system(sid, admin1, admin0, as_of) for sid in systems.COUNTRY_SYSTEMS}
    (outputs.processed() / "global").mkdir(parents=True, exist_ok=True)
    world = build_world(admin1, admin0)
    write_json(outputs.processed() / "global" / "world.geojson", world)
    context = global_context.build(world, admin0)
    all_events = {}
    for sid in systems.COUNTRY_SYSTEMS:
        ev = read_json(outputs.processed() / systems.root(sid) / "events.json")
        all_events[sid] = (payloads[sid]["name"], ev["events"], ev["episodes"])
    write_json(outputs.processed() / "global" / "recent_evidence.json", recent_evidence(all_events))
    write_json(outputs.processed() / "global" / "data_quality.json", data_quality(payloads, all_events, context))
    gulf = gulf_context.build(context, payloads)
    members = set(systems.GROUPS[gulf_context.GROUP]["members"])
    # The group's own recent list: the cross-system one holds the newest 40 of every system, which
    # can leave a region with none.
    gulf["recent"] = recent_evidence({k: v for k, v in all_events.items() if k in members})
    write_json(outputs.processed() / gulf_context.OUTPUT, gulf)
    build_time = theatre_snapshot.get("build_time") or dt.datetime.now(dt.timezone.utc).isoformat()
    write_json(outputs.processed() / "global" / "manifest.json",
               build_manifest(payloads, theatre_snapshot, build_time), indent=2)
    return payloads
