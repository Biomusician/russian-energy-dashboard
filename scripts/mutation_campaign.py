"""Mutation campaign for the governance and safety rules of iterations 16 to 19.

    .venv\\Scripts\\python.exe scripts\\mutation_campaign.py

Each mutation deliberately breaks ONE rule in an isolated copy of the repository and runs the
tests that are supposed to guard it. A mutation that leaves those tests green has SURVIVED,
which means the rule is not actually protected; the script exits non-zero if any survive.

The copy holds the code, tests, curated and processed data and the Natural Earth cache; the real
repository is never modified. Tests that need git history read it from the real repository
(read-only) through EDM_GIT_ROOT.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

COPY_DIRS = ("pipeline", "scripts", "tests", "methodology", "data/curated", "data/processed",
             "web/public/data", "web/src", "docs")
COPY_FILES = ("pyproject.toml", "data/raw/ne_10m_admin_1.geojson", "data/raw/ne_50m_admin_0.geojson",
              "CLAUDE.md", "README.md")


def _text(old, new):
    def mutate(s):
        assert s.count(old) == 1, f"mutation anchor not found exactly once: {old[:70]!r}"
        return s.replace(old, new)
    return mutate


def _episodes(fn):
    def mutate(s):
        d = json.loads(s)
        fn({e["episode_id"]: e for e in d["episodes"]})
        return json.dumps(d, ensure_ascii=False, indent=2)
    return mutate


def _drop_helene_member(eps):
    eps["us-2024-09-hurricane-helene"]["event_ids"].pop()


def _helene_member_into_francine(eps):
    eps["us-2024-09-hurricane-francine"]["event_ids"].append(
        eps["us-2024-09-hurricane-helene"]["event_ids"][0])


CTX = "web/public/data/global/energy_context.json"


def _artifact(fn):
    """Change a JSON file as a whole. `fn` edits the parsed document in place."""
    def mutate(s):
        d = json.loads(s)
        fn(d)
        return json.dumps(d, ensure_ascii=False, indent=2)
    return mutate


def _prepend(line):
    return lambda s: line + s


def _ctx_first_unmonitored(fn):
    def edit(d):
        fn(next(r for r in d["countries"] if r["system_id"] is None))
    return edit


def _nulls_to_zero(d):
    for r in d["countries"]:
        for k, v in r["values"].items():
            if v is None:
                r["values"][k] = 0


def _unblind_one(d):
    e = next(x for x in d["events"] if x["review"]["reviewed_at"] >= "2026-11-10")
    e["review"]["review_status"] = "dual_reviewed"


def _split_helene(d):
    ep = next(e for e in d["episodes"] if e["episode_id"] == "us-2024-09-hurricane-helene")
    moved = [ep["event_ids"].pop(), ep["event_ids"].pop()]
    d["episodes"].append({**ep, "episode_id": "us-2024-09-hurricane-helene-b", "event_ids": moved})


def _median_on_small_n(d):
    r = d["recovery_by_class"]["rows"][0]
    r["n"] = 2
    r["median_days"] = 1


def _effect_on_withheld(d):
    m = next(x for ep in d["episodes"] for x in ep["members"] if x["withheld"])
    m["effect"] = "Refinery back in service."


# (name, [(file, mutate)], pytest -k expression)
MUTATIONS = [
    ("one statement => one episode shortcut restored",
     [("pipeline/build_systems.py", _text("\nEPISODE_BASES = {\n",
       '\nEPISODE_BASES = {\n    "single_statement": "One source statement reported these records together.",\n')),
      ("pipeline/build_systems.py", _text("        if basis in RETIRED_EPISODE_BASES:", "        if False:"))],
     "one_source_statement_is_not_an_episode"),
    ("second reviewer omitted (import gate)",
     [("scripts/import_candidates.py", _text('        if not indep.get("completed"):\n', "        if False:\n"))],
     "import_gate_holds_what_it_should"),
    ("second reviewer omitted (build)",
     [("pipeline/build_systems.py", _text('        if not r.get("independent_review_complete"):\n',
                                          "        if False:\n"))],
     "refuses_a_record_without_two_reviews"),
    ("research completeness inferred from source freshness",
     [("pipeline/build_systems.py", _text('{"complete": "met", "partial": "partial"}.get(rf["completeness"], "unmet"),',
                                          '"met" if not unstated else "partial",'))],
     "not_inferred_from_source_freshness"),
    ("current reconstruction labelled as-published",
     [("pipeline/production_history.py", _text('            "mode": RECONSTRUCTION,', '            "mode": CONCEPT,'))],
     "reconstruction_never_as_published"),
    ("Oct-9 backfilled event appears in the as-published snapshot",
     [("pipeline/production_history.py", _text('ids = _event_ids(root, e["sha"])', 'ids = _event_ids(root, "HEAD")'))],
     "backfill_fixture_holds_when_history_is_rebuilt"),
    ("active-campaign recovery status exposed (import)",
     [("scripts/import_candidates.py", _text("    if campaigns and build_systems.campaign_of(ev, system_id, campaigns):",
                                             "    if False:"))],
     "writes_the_withheld_marker"),
    ("active-campaign recovery status exposed (build)",
     [("pipeline/build_systems.py", _text(
         '        if rec["research_status"] != WITHHELD or any(rec[k] for k in ("kind", "date", "evidence", "url")):',
         "        if False:"))],
     "active_campaign_withholds_facility_status"),
    # Added after the iteration-16 safety review: status leaked through citation addresses.
    ("active-campaign status citation published (import)",
     [("scripts/import_candidates.py", _text(
         '        ev["sources"] = [s for s in ev["sources"] if not build_systems.status_wording(s["url"])\n'
         '                         and not build_systems.late_citation(ev, s)]\n',
         ""))],
     "writes_the_withheld_marker"),
    ("active-campaign status citation published (build)",
     [("pipeline/build_systems.py", _text(
         '        texts += [("citation", s.get("url")) for s in e["sources"]]\n', ""))],
     "active_campaign_withholds_facility_status or no_served_record_under_an_active_campaign"),
    ("source stale threshold alters analytics",
     [("pipeline/build_systems.py", _text('    events = [e for e in events if e["date"] <= as_of]\n',
       '    events = [e for e in events if e["date"] <= as_of]\n'
       '    events = [e for e in events if min(p["days"] for p in STALE_POLICIES.values()) > 30]\n'))],
     "stale_limits_never_change_what_a_system_publishes"),
    ("US research marked complete with a skipped source lane",
     [("pipeline/build_systems.py", _text(
         '            if p.get("status") == "complete" and not all(_lane_done(lane) for lane in lanes):',
         "            if False:"))],
     "complete_means_every_declared_lane_was_executed"),
    ("one episode loses a member",
     [("data/curated/systems/us/episodes.json", _episodes(_drop_helene_member))],
     "every_shipped_episode_obeys_the_iteration_16_invariants"),
    ("one record enters two episodes",
     [("data/curated/systems/us/episodes.json", _episodes(_helene_member_into_francine))],
     "every_shipped_episode_obeys_the_iteration_16_invariants"),
    # ---- iteration 17 ------------------------------------------------------------------------
    ("a past --as-of is accepted as a current build",
     [("pipeline/outputs.py", _text("        if as_of != today:", "        if False:"))],
     "output_plan_refuses_the_dangerous_combinations or a_refused_build_touches_nothing"),
    ("a reconstruction may write into the production payload",
     # Both layers: the protected-root check and (since the final red team) the in-repo rule.
     [("pipeline/outputs.py", _text("def _protected(path):\n", "def _protected(path):\n    return False\n")),
      ("pipeline/outputs.py", _text("    if in_repo and not _protected(output_root)", "    if False and not _protected(output_root)"))],
     "output_plan_refuses_the_dangerous_combinations or a_refused_build_touches_nothing"),
    ("the second line of defence grants everything",
     [("pipeline/outputs.py", _text("    if not grants(capability):", "    if False:"))],
     "a_reconstruction_target_refuses_mirror_and_current_state"),
    ("CURRENT_STATE accepts a reconstruction snapshot",
     [("pipeline/current_state.py", _text('    if (snapshot.get("build_mode") or "current") != "current":',
                                          "    if False:"))],
     "a_reconstruction_target_refuses_mirror_and_current_state"),
    ("young campaign recovery evidence is released at once",
     [("pipeline/recovery.py", _text("        if rel is not None and rel <= when:", "        if True:"))],
     "recovery_evidence_is_released_only_once_it_is_history"),
    ("an open repair estimate is not treated as current status",
     [("pipeline/recovery.py", _text("    if horizon and start:", "    if False:"))],
     "recovery_evidence_is_released_only_once_it_is_history"),
    ("the policy summary names what it withholds",
     [("pipeline/recovery.py", _text('        "withheld_records": withheld,',
                                     '        "withheld_records": withheld, "withheld_ids": sorted(set(records) - set(kept)),'))],
     "policy_summary_counts_and_never_names"),
    ("a later effect report is published as occurrence",
     [("pipeline/recovery.py", _text("    if start and (seen - start).days <= AT_THE_TIME_DAYS:", "    if True:"))],
     "effect_reported_at_the_time_is_occurrence"),
    ("the index reads recovery before the embargo",
     [("pipeline/run.py", _text("    recovery_by_incident, campaign_policy = recovery_mod.apply_campaign_embargo(",
                                "    _ignored, campaign_policy = recovery_mod.apply_campaign_embargo("))],
     "applies_the_embargo_before_the_index_reads_recovery"),
    ("blind review: two accepts outvote a hold (import)",
     [("scripts/import_candidates.py", _text('                return f"blind review: role(s) {failed} did not accept"',
                                             "                return None"))],
     "blind_reviewed_record_needs_every_role_to_accept"),
    ("a blind packet leaks the researcher's disposition",
     [("scripts/review_packets.py", _text("    out = {k: record[k] for k in VISIBLE if k in record}",
                                          "    out = dict(record)"))],
     "blind_review_packet_carries_no_earlier_conclusion"),
    ("criticality framing returns to a theatre note",
     [("data/curated/incidents.csv", _text("Drone strike set the Feodosia oil terminal in occupied Crimea ablaze",
                                           "Drone strike set the largest oil terminal in occupied Crimea ablaze"))],
     "theatre_text_holds_the_same_abstraction_rules_as_the_countries"),
    # ---- iteration 17, final red team ---------------------------------------------------------
    ("the ledger names a facility whose evidence the campaign withholds",
     [("pipeline/diff_builds.py", _text('        if (cr.get("publication_note")', '        if (False'))],
     "campaign_policy_withholds"),
    ("an undated observed status is released at once",
     [("pipeline/recovery.py", _text('    if record.get("recovery_status") in _OBSERVED_STATUSES:\n        return None\n', ''))],
     "undated_campaign_evidence_fails_closed"),
    ("an undated effect counts as reported at the time",
     [("pipeline/recovery.py", _text('    seen = _date(effect.get("as_of_date"))\n', '    seen = _date(effect.get("as_of_date")) or start\n'))],
     "undated_campaign_evidence_fails_closed"),
    ("a campaign record publishes when its outage ended",
     [("pipeline/build_systems.py", _text('        if e.get("date_end"):', '        if False:'))],
     "end_date_on_an_active_campaign_record"),
    ("a reconstruction may write over the curated files",
     [("pipeline/outputs.py", _text("    if in_repo and not _protected(output_root)", "    if False and not _protected(output_root)"))],
     "inside_the_repo_only_under_data_reconstruction"),
    ("bot refreshes vanish from the as-published history",
     [("pipeline/production_history.py", _text('"--fixed-strings", ', ''))],
     "bot_refresh_commits_enter_the_as_published_history"),
    ("a source title carries strike distance",
     [("pipeline/fetch_wikipedia.py", _text("    if title and _UNSAFE_TITLE.search(title):", "    if False:"))],
     "source_title_never_carries"),
    ("episodes merge two named hazards",
     [("pipeline/build_systems.py", _text("        if len(hazards) > 1:", "        if False:"))],
     "merge_two_named_hazards"),
    ("an unknown review disposition is read as acceptance",
     [("scripts/merge_reviews.py", _text("    if unknown:", "    if False:"))],
     "outcome_rule_has_no_majority"),
    ("a single-reviewed record is grandfathered again",
     [("data/curated/systems/review_grandfathered.json", _text('"event_ids": []', '"event_ids": ["us-2024-09-26-hurricane-helene-georgia-outages"]'))],
     "grandfather_list_only_shrinks"),
    # ---- iteration 18 ------------------------------------------------------------------------
    ("a context-only country is treated as monitored",
     [(f"{CTX}", _artifact(_ctx_first_unmonitored(lambda r: r.__setitem__("system_id", "us"))))],
     "context_rows_are_monitored_only"),
    ("an unmonitored country gets a zero incident count",
     [(f"{CTX}", _artifact(_ctx_first_unmonitored(lambda r: r.__setitem__("incident_count", 0))))],
     "context_rows_carry_no_incident"),
    ("national production enters the scoring code",
     [("pipeline/build_index.py", _prepend("from pipeline import global_context  # noqa: F401\n"))],
     "no_analytic_module_can_reach"),
    ("the context source year disappears",
     [("data/curated/global_context/energy_context.json", _artifact(lambda d: d.pop("comparison_year")))],
     "the_committed_context_is_valid"),
    ("a null national value becomes zero",
     [(f"{CTX}", _artifact(_nulls_to_zero))],
     "null_stays_null"),
    ("a publisher that has not released reads as analyst work unfinished",
     [("pipeline/build_systems.py", _text(
         'return "current_through_latest_release" if win == "publisher_not_yet_released" else "universe_searched"',
         'return "partially_searched"'))],
     "the_reader_state_keeps"),
    ("a declared query set is called a completed census",
     [("pipeline/build_systems.py", _text('        if kind == "declared_query_set":\n', "        if False:\n"))],
     "lane_cannot_claim_more"),
    ("an English-only run of a bilingual lane is complete",
     [("pipeline/build_systems.py", _text(
         '        if not ran_all_languages:\n            out.append(f"lane {name!r}: declared_search_complete without',
         '        if False:\n            out.append(f"lane {name!r}: declared_search_complete without'))],
     "lane_cannot_claim_more"),
    ("Arabic restart wording passes the status check",
     [("pipeline/build_systems.py", _text('    r"\u0627\u0633\u062a\u0626\u0646\u0627\u0641|', '    r"zzzzzz|\u0627\u0633\u062a\u0626\u0646\u0627\u0641_never|'))],
     "arabic_status_wording"),
    ("a Saudi restart is published on a campaign record",
     [("data/processed/systems/sa/events.json", _text("Refinery shut on 8 April 2026 (TotalEnergies).",
                                                      "Refinery shut on 8 April 2026 and restarted (TEST PLACEHOLDER, not a fact).")),
      ("web/public/data/systems/sa/events.json", _text("Refinery shut on 8 April 2026 (TotalEnergies).",
                                                       "Refinery shut on 8 April 2026 and restarted (TEST PLACEHOLDER, not a fact)."))],
     "no_served_record_under_an_active_campaign"),
    ("a country's raw event count enters the cross-country file",
     [("web/public/data/global/data_quality.json", _artifact(lambda d: d["systems"][0].__setitem__("recorded_events", 7)))],
     "data_quality_holds_no"),
    ("a world-map metric loses its unit",
     [(f"{CTX}", _artifact(lambda d: d["metrics"][d["map_metrics"][0]].__setitem__("unit", "")))],
     "every_map_metric"),
    ("a context-only country opens an incident dossier",
     [("web/src/global/WorldContext.tsx", _text("if (sid) navigate(sid);", "navigate(String(p?.a3).toLowerCase());"))],
     "context_country_can_never_open_a_dossier"),
    ("a unit conversion is dropped",
     [("scripts/build_global_context.py", _text("values[mid] = None if v is None else rnd(v * mult, unit)",
                                                "values[mid] = None if v is None else rnd(v, unit)"))],
     "unit_conversion_and_no_fallback"),
    ("a missing comparison year quietly borrows the year before",
     [("scripts/build_global_context.py", _text("v = by_year.get(COMPARISON_YEAR)\n",
                                                "v = by_year.get(COMPARISON_YEAR) or by_year.get(COMPARISON_YEAR - 1)\n"))],
     "unit_conversion_and_no_fallback"),
    ("a record of this pass published without blind review",
     [("web/public/data/systems/ca/events.json", _artifact(_unblind_one))],
     "every_record_reviewed_in_this_pass"),
    ("two episodes carry one named hazard",
     [("data/curated/systems/us/episodes.json", _artifact(_split_helene))],
     "every_shipped_episode_obeys_the_iteration_16_invariants"),
    ("a median is printed for fewer than three cases",
     [("web/public/data/global/data_quality.json", _artifact(_median_on_small_n))],
     "recovery_statistics_respect"),
    ("the recent list shows an effect on a withheld campaign record",
     [("web/public/data/global/recent_evidence.json", _artifact(_effect_on_withheld))],
     "campaign_record_shows_no_effect"),
    ("the recent list is reordered",
     [("web/public/data/global/recent_evidence.json", _artifact(lambda d: d["episodes"].reverse()))],
     "chronological_safe"),
]


# --- iteration 19: the Gulf expansion ------------------------------------------------------------

GULF_NEW = ("ae", "bh", "iq", "ir", "kw", "om", "qa")
KINETIC = ("kinetic_strike", "sabotage")


def _gulf_payload(pred, order=("ir", "kw", "qa", "ae", "bh", "om", "iq")):
    """The first new Gulf system whose served events hold a record matching `pred`. The mutation is
    aimed at a real record, so it stays meaningful whichever countries the research populated."""
    for sid in order:
        path = ROOT / "web" / "public" / "data" / "systems" / sid / "events.json"
        if path.exists() and any(pred(e) for e in json.loads(path.read_text(encoding="utf-8"))["events"]):
            return sid
    return order[0]


def _covered(e):
    return e["cause"] in KINETIC and (e.get("publication") or {}).get("rule") == "active_campaign_current_status_withheld"


def _on_event(pred, fn):
    def edit(d):
        fn(next(e for e in d["events"] if pred(e)))
    return edit


def _both(sid, name, mutate):
    return [(f"data/processed/systems/{sid}/{name}", mutate), (f"web/public/data/systems/{sid}/{name}", mutate)]


def _restart_in_effect(e):
    e["effect"] = "A fire was reported and the unit has since restarted (TEST PLACEHOLDER, not a fact)."


def _province_on_attack(e):
    e["geography_precision"] = "admin1"
    e["region_code"] = "XX-00"


def _status_in_url(e):
    e["sources"][0]["url"] = e["sources"][0]["url"].rstrip("/") + "/facility-restart-announced"


def _no_sources(e):
    e["sources"] = []


def _nuclear_row(d):
    d["profile"]["metrics"].append({"metric": "nuclear_unit_status", "value": 4, "unit": "units", "year": 2026,
                                    "source": "TEST PLACEHOLDER", "url": "https://example.org"})


def _gulf_by_size(d):
    d["systems"].sort(key=lambda s: -(s["values"].get("total_production") or 0))


def _zero_index(d):
    s = next(x for x in d["systems"] if x["id"] == "ir")
    s["index"] = {"id": "esdi", "name": "ESDI"}
    s["headline"] = {"value": 0, "as_of": "2026-11-11", "label": "ESDI", "meaning": "TEST PLACEHOLDER"}


def _merge_two_attacks(d):
    a = [e for e in d["events"] if e["cause"] in KINETIC][:2]
    a[1]["episode_id"] = a[0]["episode_id"]


GULF = "web/public/data/global/gulf.json"
SID_COVERED = _gulf_payload(_covered)
SID_ATTACK = _gulf_payload(lambda e: e["cause"] in KINETIC and e["geography_precision"] == "country", ("ir", "kw", "qa", "ae", "bh", "om"))
SID_ANY = _gulf_payload(lambda e: True)

GULF_MUTATIONS = [
    # 1-5: campaign and precision
    ("an Iranian or Gulf attack record carries restart wording",
     _both(SID_COVERED, "events.json", _artifact(_on_event(_covered, _restart_in_effect))),
     "no_served_record_under_an_active_campaign"),
    ("an attack record is placed in a province where the policy says country",
     _both(SID_ATTACK, "events.json", _artifact(_on_event(lambda e: e["cause"] in KINETIC, _province_on_attack))),
     "emitted_kinetic_records_obey"),
    ("Bahrain's records may be placed in a governorate",
     [("data/curated/systems/bh/system.json", _artifact(lambda d: d["geography"]["precision_policy"].__setitem__("other", "admin1")))],
     "bahrain_places_no_record"),
    ("the import gate stops downgrading attack records (Qatar, Kuwait, UAE)",
     [("scripts/import_candidates.py", _text(
         'return (policy or {}).get("kinetic") == "country" and r.get("cause") in build_systems.KINETIC_CAUSES',
         "return False"))],
     "downgrades_an_attack_record or kinetic_country_policy_is_by_cause"),
    ("a small state's precision policy is relaxed to admin-1 for attacks",
     [("data/curated/systems/qa/system.json", _artifact(lambda d: d["geography"]["precision_policy"].__setitem__("kinetic", "admin1")))],
     "small_gulf_states_never_place"),
    # 6-8: groups and context
    ("the Gulf group loses Iraq",
     [("pipeline/systems.py", _text('"members": ("bh", "ir", "iq", "kw", "om", "qa", "sa", "ae"),',
                                    '"members": ("bh", "ir", "kw", "om", "qa", "sa", "ae"),'))],
     "gulf_group_is_exactly"),
    ("the GCC gains Iran",
     [("pipeline/systems.py", _text('"members": ("bh", "kw", "om", "qa", "sa", "ae"),',
                                    '"members": ("bh", "ir", "kw", "om", "qa", "sa", "ae"),'))],
     "gcc_is_exactly"),
    ("OPEC still lists the UAE",
     [("pipeline/systems.py", _text('"members": ("ir", "iq", "kw", "sa"),', '"members": ("ir", "iq", "kw", "sa", "ae"),'))],
     "opec_membership_is_todays"),
    ("national production reaches a scoring module",
     [("pipeline/build_index.py", _prepend("from pipeline import gulf_context  # noqa: F401\n"))],
     "no_analytic_module_imports_the_gulf_context"),
    # 9-12: what is not an event
    ("an OPEC production cut becomes an incident",
     [("pipeline/build_systems.py", _text(
         'r"\\bOPEC\\+?\\b[^.]{0,80}\\b(cut|cuts|quota|quotas|curb|curbs|reduction|agreement)\\b|"', 'r"zzzOPECzzz|"'))],
     "policy_decision_or_planned_maintenance"),
    ("an unexplained decline in a statistic becomes an incident",
     [("pipeline/build_systems.py", _text(
         '    if e.get("cause") == "unknown" and UNEXPLAINED_DECLINE.search(text):', "    if False:"))],
     "unexplained_decline"),
    ("planned maintenance becomes an event",
     [("pipeline/build_systems.py", _text(
         'r"\\b(planned|scheduled|routine|annual|periodic) (maintenance|turnaround|overhaul|shutdown|outage)\\b|"', 'r"zzzMAINTzzz|"'))],
     "policy_decision_or_planned_maintenance"),
    ("a sanction becomes a physical outage",
     [("pipeline/build_systems.py", _text('r"\\bturnaround\\b|\\bsanction(s|ed)?\\b|\\bembargo\\b", re.I)',
                                          'r"\\bturnaround\\b|\\bembargo\\b", re.I)'))],
     "policy_decision_or_planned_maintenance"),
    # 13-16: languages, calendars, numerals
    ("an English-only run of a Persian-required lane is written as complete",
     [("scripts/write_gulf_pass.py", _text(
         'missing_lang = not set(body["languages_required"]) <= set(body["languages_executed"])', "missing_lang = False"))],
     "pass_writer_never_calls"),
    ("a lane run in one of two required languages validates as complete",
     [("pipeline/build_systems.py", _text("    ran_all_languages = required <= executed\n",
                                          "    ran_all_languages = bool(required & executed)\n"))],
     "fewer_languages_than_required"),
    ("a Solar Hijri year is read as Gregorian",
     [("pipeline/calendars.py", _text("GREGORIAN_PLAUSIBLE = (1900, 2100)", "GREGORIAN_PLAUSIBLE = (1000, 2100)"))],
     "1404_is_never_read or misread_calendar"),
    ("the Solar Hijri conversion is a day out",
     [("pipeline/calendars.py", _text("_ANCHOR_YEAR, _ANCHOR_DATE = 1400, dt.date(2021, 3, 21)",
                                      "_ANCHOR_YEAR, _ANCHOR_DATE = 1400, dt.date(2021, 3, 22)"))],
     "solar_hijri_dates_convert_exactly"),
    ("the Solar Hijri conversion is a year out",
     [("pipeline/calendars.py", _text("_ANCHOR_YEAR, _ANCHOR_DATE = 1400, dt.date(2021, 3, 21)",
                                      "_ANCHOR_YEAR, _ANCHOR_DATE = 1401, dt.date(2021, 3, 21)"))],
     "solar_hijri_dates_convert_exactly"),
    ("Persian digits are not normalised",
     [("pipeline/calendars.py", _text("**{chr(0x06F0 + i): str(i) for i in range(10)}}", "}"))],
     "persian_and_arabic_digits"),
    ("an ambiguous number is guessed",
     [("pipeline/calendars.py", _text('r"[+-]?(\\d{1,3}(,\\d{3})+|\\d+)(\\.\\d+)?"', 'r"[+-]?[\\d,]+(\\.\\d+)?"'))],
     "ambiguous_number"),
    ("a Hijri conversion claims to be exact",
     [("pipeline/calendars.py", _text("tabular calendar (may differ", "astronomical calendar (may differ"))],
     "hijri_conversion_says"),
    # 17-19: nulls, sources, citations
    ("a missing national value is summed as zero",
     [("pipeline/gulf_context.py", _text("    vals = list(values_by_member.values())\n",
                                         "    vals = [v or 0 for v in values_by_member.values()]\n"))],
     "partial_regional_sum"),
    ("a Gulf record is published with no source",
     _both(SID_ANY, "events.json", _artifact(_on_event(lambda e: True, _no_sources))),
     "every_gulf_event_has_a_source"),
    ("a campaign record's citation address announces a restart",
     _both(SID_COVERED, "events.json", _artifact(_on_event(_covered, _status_in_url))),
     "no_served_record_under_an_active_campaign"),
    # 20-25: episodes, context file
    ("a regional context metric loses its year",
     [(GULF, _artifact(lambda d: d["metrics"][next(iter(d["metrics"]))].__setitem__("year", None)))],
     "gulf_null_is_null"),
    ("nuclear detail beyond the national mix enters a profile",
     _both("ae", "system.json", _artifact(_nuclear_row)),
     "shipping_route_or_nuclear"),
    ("national context gains an export-route share",
     [(GULF, _artifact(lambda d: d["systems"][0].__setitem__("export_route_share", 0.4)))],
     "emitted_gulf_payload_holds_national_context"),
    ("the Gulf overview is ordered by a figure",
     [(GULF, _artifact(_gulf_by_size))],
     "emitted_gulf_payload_holds_national_context"),
    ("tanker-flow data appears in the regional file",
     [(GULF, _artifact(lambda d: d["metrics"].__setitem__("tanker_flows", {"label": "x", "unit": "x", "year": 2026, "source_id": "x"})))],
     "emitted_gulf_payload_holds_national_context"),
    ("a per-country incident count enters the regional file",
     [(GULF, _artifact(lambda d: d["systems"][0].__setitem__("records", 12)))],
     "emitted_gulf_payload_holds_national_context"),
    # 26-30: titles, identity, backfill, switching, zero
    ("an unsafe publisher headline is rendered",
     [("scripts/import_candidates.py", _text(
         "if t and safe_title(t) and not build_systems.status_wording(t) and not build_systems.LOADED_WORDING.search(t):",
         "if t:"))],
     "status_bearing_headline or headline_that_weighs"),
    ("a withheld facility comes back through the citation list",
     [("scripts/import_candidates.py", _text(
         'r = {**r, "sources": [s for s in r["sources"] if not unpublishable_address(s.get("url"), tokens)],',
         'r = {**r, "sources": list(r["sources"]),'))],
     "citation_address_that_names"),
    ("a record that names its facility in text passes the gate",
     [("scripts/import_candidates.py", _text("        named = [n for n in names if n.lower() in text]\n", "        named = []\n"))],
     "holds_a_record_that_names_its_facility"),
    ("a historical backfill reads as a deteriorating region",
     [("web/src/global/GroupView.tsx", _text("a long list is a larger dataset, not a deteriorating region.", "the list is growing."))],
     "gulf_recent_list_is_in_event_date_order"),
    ("the Gulf recent list is reordered",
     [(GULF, _artifact(lambda d: d["recent"]["episodes"].reverse()))],
     "gulf_recent_list_is_in_event_date_order"),
    ("switching country can show the previous country's data",
     [("web/src/Root.tsx", _text("<CountryView key={route.id} id={route.id} />", "<CountryView id={route.id} />"))],
     "views_are_keyed"),
    ("a new system gets a default index of zero",
     [("web/public/data/global/manifest.json", _artifact(_zero_index))],
     "manifest_carries_groups_and_no_rankable"),
    # further guards on the scaffold itself
    ("an uncertain campaign stops restricting",
     [("pipeline/build_systems.py", _text(
         'RESTRICTING_STATES = ("ACTIVE_KINETIC_CAMPAIGN", "RECENT_ENDED_CAMPAIGN", "UNCERTAIN")',
         'RESTRICTING_STATES = ("ACTIVE_KINETIC_CAMPAIGN", "RECENT_ENDED_CAMPAIGN")'))],
     "uncertain_restricts or restricted_state_needs"),
    ("an open campaign can switch its policy off",
     [("pipeline/build_systems.py", _text(
         '        if c.get("status") in ("active", "uncertain") and not c.get("policy_applied"):', "        if False:"))],
     "open_campaign_cannot_switch"),
    ("a policy is lifted the day a campaign ends",
     [("pipeline/build_systems.py", _text("            if not ended or (today - dt.date.fromisoformat(ended)).days < wait:",
                                          "            if not ended:"))],
     "ended_campaign_keeps_its_policy"),
    ("a Gulf system with no campaign classification builds",
     [("pipeline/build_systems.py", _text('    for sid in systems.GROUPS["gulf_littoral"]["members"]:\n        if sid not in states:',
                                          '    for sid in ():\n        if sid not in states:'))],
     "no_classification_fails"),
    ("Iran's provinces fall back to the old numbering",
     [("pipeline/build_systems.py", _text('"West Azarbaijan": "IR-04", "Kermanshah": "IR-05", "Khuzestan": "IR-06", "Fars": "IR-07",',
                                          '"West Azarbaijan": "IR-04", "Kermanshah": "IR-05", "Khuzestan": "IR-06", "Fars": "IR-14",'))],
     "irans_provinces"),
    ("Persian restart wording passes the status check",
     [("pipeline/build_systems.py", _text('    r"راه[\\u200c ]?انداز[یي] مجدد|از ?سرگ[یي]ر[یي]|از سر گرفته|',
                                          '    r"zzzz|'))],
     "status_wording_is_caught"),
    ("route wording in a citation address is published",
     [("pipeline/build_systems.py", _text("        for s in e.get(\"sources\", []):\n            words = unquote(s.get(\"url\") or \"\")",
                                          "        for s in []:\n            words = unquote(s.get(\"url\") or \"\")"))],
     "route_and_shipping_wording or citation_address_with_route"),
    ("a nuclear-site record is published",
     [("pipeline/build_systems.py", _text('            out.append(f"{e[\'event_id\']}: a record at or about a nuclear site is not published")', "            pass"))],
     "nuclear_content_is_a_national"),
    ("the frontend gains a hardcoded list of Gulf countries",
     [("web/src/global/GroupView.tsx", _prepend('const GULF_IDS = ["ir", "iq", "kw", "sa"];\n'))],
     "frontend_holds_no_list"),
    ("an empty country reads as zero disruptions",
     [("web/src/global/GroupView.tsx", _text("No qualifying records in the current reviewed corpus for this region.",
                                             "0 disruptions in this region."))],
     "gulf_view_states_what_it_is_not"),
    ("onboarding accepts a draft with loaded wording",
     [("scripts/onboard_system.py", _text("    if bad:\n        problems.append(f\"loaded wording", "    if False:\n        problems.append(f\"loaded wording"))],
     "onboarding_refuses"),
    ("a membership becomes a page of its own",
     [("pipeline/systems.py", _text('        "label": "GCC",\n', '        "label": "GCC",\n        "slug": "gcc",\n        "context": "global/gulf.json",\n'))],
     "manifest_carries_groups" ),
]

# Found by the blind safety review of iteration 19, then turned into rules.
REVIEW_MUTATIONS = [
    ("the gate stops reading how an attack was carried out in a citation address",
     [("pipeline/build_systems.py", _text("    return bool(METHOD_WORDING.search(path))", "    return False"))],
     "naming_any_region_the_operator_or_the_method or refuses_method_wording"),
    ("the gate stops reading first-level unit names in a citation address",
     [("scripts/import_candidates.py", _text('    return name_tokens(r) | set((policy or {}).get("unit_words") or [])',
                                           "    return name_tokens(r)"))],
     "naming_any_region_the_operator_or_the_method"),
    ("the gate stops reading the operator's name in a citation address",
     [("scripts/import_candidates.py", _text('for k in ("facility_name", "facility_name_local", "admin1_name", "operator"):',
                                           'for k in ("facility_name", "facility_name_local", "admin1_name"):'))],
     "naming_any_region_the_operator_or_the_method"),
    ("a headline may be shown on an attack record published without its place",
     [("pipeline/build_systems.py", _text('                if s.get("title_original") or s.get("title_en"):',
                                        "                if False:"))],
     "refuses_method_wording_and_headlines"),
    ("a month-precision date crashes the late-citation check again",
     [("pipeline/build_systems.py", _text(
         'start = dt.date.fromisoformat((e["date"] + "-01-01")[:10] if len(e["date"]) < 10 else e["date"][:10])',
         'start = dt.date.fromisoformat(e["date"][:10])'))],
     "month_precision_date_does_not_crash"),
    ("a lane that only points at another lane's record replaces it in the queue",
     [("scripts/merge_sweep.py", _text(
         "if same_pass and RANK.get(r.get(\"suggested_disposition\"), 1) <= RANK.get(old.get(\"suggested_disposition\"), 1):",
         "if False:"))],
     "two_lanes_reporting_one_event"),
    ("a recent-events list states a number of systems again",
     [("pipeline/build_systems.py", _text('def recent_evidence(all_events, scope="The country systems.", regional=False):',
                                        'def recent_evidence(all_events, scope="The five country systems.", regional=False):')),
      ("data/processed/global/recent_evidence.json", _artifact(lambda d: d.__setitem__("scope", "The five country systems."))),
      ],
     "no_recent_list_states_a_number"),
    ("a research lane's own prose is published beside the fixed notes",
     [("scripts/write_gulf_pass.py", _text('    return " ".join(out) or NOTE_DEFAULT', '    return " ".join(out + [raw or ""]) or NOTE_DEFAULT'))],
     "lane_note_publishes_fixed_sentences"),
    ("a published research log carries a strike tally in a lane note",
     [(f"data/curated/systems/kw/research_log.json", _artifact(lambda d: d["passes"][-1]["lanes"][0].__setitem__(
         "finding", "TEST PLACEHOLDER: the third attack since the war began."))),
      (f"web/public/data/systems/kw/system.json", _artifact(lambda d: d["research_log"]["passes"][-1]["lanes"][0].__setitem__(
         "finding", "TEST PLACEHOLDER: the third attack since the war began.")))],
     "published_research_log_of_a_gulf_system"),
    ("the gate accepts a recovery status outside the vocabulary",
     [("scripts/import_candidates.py", _text("    if status not in build_systems.RECOVERY_STATUSES:", "    if False:"))],
     "recovery_status_outside_the_vocabulary"),
    ("a reviewer's free-text reason for an abstracted record is committed",
     [("scripts/apply_reviews.py", _text("                why = GENERIC_REASON if abstract else e.get(\"reason\")",
                                       "                why = e.get(\"reason\")")),
      ("data/curated/systems/review_edits.json", _artifact(lambda d: next(
          e for e in d["edits"] if e["event_id"] == "kw-2026-03-20-refinery-attack-1").__setitem__(
          "reason", "Blind review, role(s) B: removed the citation naming TEST PLACEHOLDER refinery")))],
     "committed_review_edits_hand_back_nothing"),
]
MUTATIONS += REVIEW_MUTATIONS
MUTATIONS += GULF_MUTATIONS

def _sandbox():
    box = Path(tempfile.mkdtemp(prefix="edm-mutation-"))
    for d in COPY_DIRS:
        shutil.copytree(ROOT / d, box / d, ignore=shutil.ignore_patterns("__pycache__"))
    for f in COPY_FILES:
        src = ROOT / f
        if src.exists():
            (box / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, box / f)
    return box


def _run(box, k):
    env = {**os.environ, "EDM_GIT_ROOT": str(ROOT), "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([PY, "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
                        "tests/test_pipeline.py", "tests/test_iteration18.py", "tests/test_iteration19.py", "-k", k], cwd=box, capture_output=True, text=True,
                       encoding="utf-8", env=env)
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    return r.returncode, tail


def main():
    box = _sandbox()
    try:
        failures = []
        for name, edits, k in MUTATIONS:
            code, tail = _run(box, k)
            if code != 0 or "skipped" in tail and "passed" not in tail:
                failures.append(f"BASELINE not green for {k!r}: {tail}")
                print(f"  baseline  {name}: {tail}")
                continue
            originals = {}
            for rel, mutate in edits:
                p = box / rel
                originals.setdefault(rel, p.read_text(encoding="utf-8"))
                p.write_text(mutate(p.read_text(encoding="utf-8")), encoding="utf-8")
            code, tail = _run(box, k)
            for rel, text in originals.items():
                (box / rel).write_text(text, encoding="utf-8")
            caught = code != 0
            print(f"  {'CAUGHT  ' if caught else 'SURVIVED'}  {name}  ({tail})")
            if not caught:
                failures.append(f"survived: {name}")
        print(f"{len(MUTATIONS)} mutations, {len(MUTATIONS) - sum(1 for f in failures if f.startswith('survived'))} caught")
        if failures:
            print("\n".join(failures))
            sys.exit(1)
    finally:
        shutil.rmtree(box, ignore_errors=True)


if __name__ == "__main__":
    main()
