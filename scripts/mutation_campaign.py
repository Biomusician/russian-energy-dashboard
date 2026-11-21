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
COPY_FILES = ("pyproject.toml", "web/package.json", "data/raw/ne_10m_admin_1.geojson", "data/raw/ne_50m_admin_0.geojson",
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


def _attack_in_a_province(d):
    """An attack record placed in a first-level region: an existing one if served, else a copy of
    the first record turned into one. Either way the country-level policy is broken."""
    target = next((e for e in d["events"] if e["cause"] in KINETIC), None)
    if target is None:
        import copy
        target = copy.deepcopy(d["events"][0])
        target.update({"event_id": target["event_id"] + "-injected", "cause": "kinetic_strike", "episode_id": None})
        d["events"].append(target)
    _province_on_attack(target)


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
SID_COVERED = _gulf_payload(_covered, ("ir", "kw", "qa", "ae", "bh", "om", "iq", "sa"))
# A country-policy system with any served record: if none of its attack records is published (the
# iteration-20 strict reading held them), the mutation injects one placed in a province.
SID_ATTACK = _gulf_payload(lambda e: True, ("kw", "iq", "ir", "qa", "ae", "bh", "om"))
SID_ANY = _gulf_payload(lambda e: True)

GULF_MUTATIONS = [
    # 1-5: campaign and precision
    ("an Iranian or Gulf attack record carries restart wording",
     _both(SID_COVERED, "events.json", _artifact(_on_event(_covered, _restart_in_effect))),
     "no_served_record_under_an_active_campaign"),
    ("an attack record is placed in a province where the policy says country",
     _both(SID_ATTACK, "events.json", _artifact(_attack_in_a_province)),
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
     [("pipeline/calendars.py", _text('        return None                                   # "1.500": thousands or decimal?',
                                      '        pass                                          # "1.500": thousands or decimal?'))],
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
     [("pipeline/build_systems.py", _text("        for s in e.get(\"sources\", []):\n            words = address_words(s.get(\"url\") or \"\")",
                                          "        for s in []:\n            words = address_words(s.get(\"url\") or \"\")"))],
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
     [("pipeline/build_systems.py", _text('def recent_evidence(all_events, scope="The country systems.", regional=False, restricted=frozenset()):',
                                        'def recent_evidence(all_events, scope="The five country systems.", regional=False, restricted=frozenset()):')),
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
          e for e in d["edits"] if e["event_id"].split("-")[0] in ("kw", "iq", "sa")).__setitem__(
          "reason", "Blind review, role(s) B: removed the citation naming TEST PLACEHOLDER refinery")))],
     "committed_review_edits_hand_back_nothing or campaign_policy_keep_the_result"),
    ("a short link is accepted as a citation for a record published without its place",
     [("scripts/import_candidates.py", _text("        or (short_link(url) and url not in FINAL_ADDRESSES) or opaque_unresolved(url)",
                                             "        or opaque_unresolved(url)"))],
     "short_link_is_not_a_citation"),
    ("half a headline pair is shown",
     [("scripts/import_candidates.py", _text('        if not ("title_en" in out and "title_original" in out):', '        if False:'))],
     "headline_is_shown_with_its_gloss"),
    ("the gate stops looking for the confirmation of the final text",
     [("scripts/import_candidates.py", _text("            if m and int(m.group(1)) >= 19:", "            if False:"))],
     "only_with_three_confirmations"),
    ("a campaign basis names a region and a day",
     [("data/curated/systems/conflict_campaigns.json", _artifact(lambda d: d["system_states"]["iq"].__setitem__(
         "basis", "Attacks on gas fields in the north are reported, the most recent on 2026-11-08."))),
      ("web/public/data/systems/iq/system.json", _artifact(lambda d: d["campaign_state"].__setitem__(
         "basis", "Attacks on gas fields in the north are reported, the most recent on 2026-11-08.")))],
     "campaign_bas"),
    ("the build stops reading campaign bases",
     [("pipeline/build_systems.py", _text("    return out + campaign_text_problems(campaigns)", "    return out"))],
     "campaign_basis_says_only"),
    ("a campaign status source is an address again",
     [("data/curated/systems/conflict_campaigns.json", _artifact(lambda d: d["campaigns"][0].__setitem__(
         "status_sources", ["https://example.org/mapping-attacks"])))],
     "campaign_bas"),
    ("a reviewer's wording comes back into the public edits of a restricted system",
     [("data/curated/systems/review_edits.json", _artifact(lambda d: next(
         e for e in d["edits"] if e["event_id"].startswith("sa-")).__setitem__(
         "reason", "Active-campaign policy: TEST PLACEHOLDER 'briefly' states how soon loadings resumed")))],
     "review_edits_of_a_system_under_the_campaign_policy"),
    ("a replace pair comes back into the public edits of a restricted system",
     [("data/curated/systems/review_edits.json", _artifact(lambda d: d["edits"].append(
         {"event_id": "kw-2026-03-20-refinery-attack-1", "field": "summary", "replace": ["TEST PLACEHOLDER", "x"],
          "reason": "Review correction: reconciled correction; the reviewers' wording is kept in the local review file"})))],
     "review_edits_of_a_system_under_the_campaign_policy"),
    ("the regional list shows a campaign record's own region",
     [("web/public/data/global/gulf.json", _artifact(lambda d: next(
         m for ep in d["recent"]["episodes"] for m in ep["members"] if m["withheld"]).__setitem__("region", "TEST PLACEHOLDER region")))],
     "recent_list_shows_of_each_record"),
    ("the regional list carries a country's episode id",
     [("web/public/data/global/gulf.json", _artifact(lambda d: d["recent"]["episodes"][0].__setitem__(
         "episode_id", "sa-2026-test-placeholder-refinery-shutdown")))],
     "recent_list_shows_of_each_record"),
    ("the regional list shows effect text for a campaign record",
     [("web/public/data/global/gulf.json", _artifact(lambda d: next(
         m for ep in d["recent"]["episodes"] for m in ep["members"] if m["withheld"]).update(
         {"effect": "TEST PLACEHOLDER effect", "withheld": False})))],
     "recent_list_shows_of_each_record"),
    ("a Gulf figure is not the national context's own",
     [("web/public/data/global/gulf.json", _artifact(lambda d: d["region"][next(iter(d["region"]))].__setitem__("world_share", 3.2)))],
     "gulf_figure_is_the_national_contexts_own"),
    ("a unit where no record can be placed serves a zero",
     [("web/public/data/systems/bh/regions.geojson", _artifact(lambda d: d["features"][0]["properties"].__setitem__("recorded_events", 0)))],
     "no_record_can_be_placed_serves_no_count"),
    ("an attack record published for the country joins a named episode",
     [("pipeline/build_systems.py", _text('            if e.get("cause") in KINETIC_CAUSES and e.get("episode_id") not in (None, e.get("event_id")):',
                                        "            if False:"))],
     "is_its_own_episode"),
    ("a lane nobody started reads as stopped by the search limit",
     [("pipeline/build_systems.py", _text('''    if ex == "not_started":
        return "blocked_by_source" if win == "inaccessible" else "not_started"
    if win == "inaccessible":
        return "blocked_by_source"
    # Our own''', '''    if lane.get("stopped_by") == "search_limit":
        return "stopped_by_search_limit"
    if ex == "not_started":
        return "blocked_by_source" if win == "inaccessible" else "not_started"
    if win == "inaccessible":
        return "blocked_by_source"
    # Our own'''))],
     "nobody_started_is_not_stopped"),
    ("the gate reads addresses against Natural Earth's spellings only",
     [("pipeline/build_systems.py", _text('''    rows += [(code, name) for code, name in (geo_doc.get("display_names") or {}).items()]
    rows += [(code, alias) for code, aliases in (geo_doc.get("unit_aliases") or {}).items() for alias in aliases]
''', ""))],
     "unit_goes_by_every_name"),
    ("a served headline the gate would refuse today",
     [("web/public/data/systems/iq/events.json", _artifact(lambda d: next(
         s for e in d["events"] if e["cause"] not in ("kinetic_strike", "sabotage") for s in e["sources"]).update(
         {"title_original": "TEST PLACEHOLDER", "title_en": "Largest plant restarted", "language": "ar"})))],
     "served_headline_is_one_the_import_gate_would_publish"),
]
MUTATIONS += REVIEW_MUTATIONS
MUTATIONS += GULF_MUTATIONS


# --- Iteration 20 (§109): one mutant per new rule, at the code or at the artifact it governs -------

def _append(line):
    return lambda s: s + line


def _first(seq, pred):
    return next(x for x in seq if pred(x))


def _recent_members(d):
    return [m for ep in d["episodes"] for m in ep["members"]]


def _readd_strict_hold(d):
    import copy
    e = copy.deepcopy(d["events"][0])
    e["event_id"] = "us-2025-10-02-chevron-el-segundo-fire"
    d["events"].append(e)


def _criterion(n, **fields):
    def edit(d):
        e = d["events"][0]
        e["criterion_met"] = n
        e.update(fields)
    return edit


def _people_as_customers(d):
    e = d["events"][0]
    e["criterion_met"] = 5
    e["threshold_basis"] = "About 200,000 people were without power (TEST PLACEHOLDER)."
    e["capacity_affected"] = {"value": 200000, "value_min": None, "value_max": None, "qualifier": "about",
                              "measure": "affected", "unit": "people", "source_says": "about 200,000 people"}


def _edit_for(event_id, field, value, reason):
    return lambda d: d["edits"].append({"event_id": event_id, "field": field, "set": value, "reason": reason})


def _untag_hold(d):
    e = _first(d["edits"], lambda x: x["event_id"] == "us-2025-10-02-chevron-el-segundo-fire" and x["field"] == "suggested_disposition")
    e["reason"] = "Held on review."


def _drop_single_site(cc, cls=None, basis=None):
    def edit(d):
        classes = d["geography"]["precision_policy"]["single_site_classes"]
        if basis is None:
            classes.pop(cls or next(iter(classes)))
        else:
            classes[cls]["basis"] = basis
    return edit


def _context_row(a3, newer):
    def edit(d):
        _first(d["countries"], lambda r: r["a3"] == a3)["newer"] = newer
    return edit


ITER20_MUTATIONS = [
    # §46 campaign text, every country system and every field
    ("a campaign sentence may say what state an attacked facility is in",
     [("pipeline/build_systems.py", _text("m = CAMPAIGN_TEXT.search(text) or METHOD_WORDING.search(text) or CAMPAIGN_STATUS.search(text)",
                                        "m = CAMPAIGN_TEXT.search(text) or METHOD_WORDING.search(text)"))],
     "campaign_text_rule_reads_every"),
    ("the campaign text rule reads the Gulf group only again",
     [("pipeline/build_systems.py", _text("        if sid not in systems.COUNTRY_SYSTEMS:\n            continue\n        cid = c.get(\"campaign_id\")",
                                        "        if sid not in systems.GROUPS[\"gulf_littoral\"][\"members\"]:\n            continue\n        cid = c.get(\"campaign_id\")"))],
     "campaign_text_rule_reads_every"),
    ("a campaign's name is printed without being read",
     [("pipeline/build_systems.py", _text("        check(f\"{cid} name\", sid, c.get(\"name\"))\n", ""))],
     "campaign_text_rule_reads_every"),
    ("a campaign's notes are printed without being read",
     [("pipeline/build_systems.py", _text("        check(f\"{cid} notes\", sid, c.get(\"notes\"))\n", ""))],
     "campaign_text_rule_reads_every"),
    ("a system state's notes are printed without being read",
     [("pipeline/build_systems.py", _text("\n        check(f\"system state {sid} notes\", sid, s.get(\"notes\"))", ""))],
     "campaign_text_rule_reads_every"),
    ("the served campaign basis states a restart of production",
     [("web/public/data/systems/iq/system.json", _artifact(lambda d: d["campaign_state"].__setitem__(
         "basis", d["campaign_state"]["basis"] + " Production has resumed (TEST PLACEHOLDER).")))],
     "served_campaign_bases"),
    ("the committed campaign name names a place",
     [("data/curated/systems/conflict_campaigns.json", _artifact(lambda d: _first(
         d["campaigns"], lambda c: c["system_id"] == "sa").__setitem__("name", "Attacks on Eastern Province energy facilities, 2026")))],
     "served_campaign_bases"),

    # §42, §47 held counts beside a campaign
    ("a campaign page serves the held count",
     [("pipeline/build_systems.py", _text('PUBLIC_OUTCOME_UNDER_CAMPAIGN = ()', 'PUBLIC_OUTCOME_UNDER_CAMPAIGN = ("held",)'))],
     "under_review_never_how_many"),
    ("the research log is served unchanged under the campaign policy",
     [("pipeline/build_systems.py", _text("    if not restricted:\n        return research_log\n    out = {**research_log",
                                        "    if True:\n        return research_log\n    out = {**research_log"))],
     "under_review_never_how_many"),
    ("records short of evidence no longer count as under review",
     [("pipeline/build_systems.py", _text('else bool(o.get("held") or o.get("insufficient_evidence"))',
                                        'else bool(o.get("held"))'))],
     "under_review_never_how_many"),
    ("a served campaign research log carries a held count",
     [("web/public/data/systems/iq/system.json", _artifact(lambda d: d["research_log"]["passes"][-1]["outcome"].__setitem__("held", 3)))],
     "no_served_research_log"),
    ("a served campaign research log drops the under-review statement",
     [("web/public/data/systems/kw/system.json", _artifact(lambda d: d["research_log"]["passes"][-1].pop("under_review")))],
     "no_served_research_log"),

    ("the committed research log of a campaign system carries a held count",
     [("data/curated/systems/iq/research_log.json", _artifact(lambda d: d["passes"][-1]["outcome"].__setitem__("held", 3)))],
     "committed_research_log_of_a_campaign"),
    ("a campaign country's own profile serves a figure newer than the comparison year",
     [("web/public/data/systems/sa/system.json", _artifact(lambda d: d["profile"]["metrics"].append({**d["profile"]["metrics"][0], "year": 2026})))],
     "no_profile_figure_newer"),

    ("the address gate stops folding letter forms and escapes",
     [("pipeline/build_systems.py", _text('    return unicodedata.normalize("NFKC", s).translate(_FOLD).lower()', '    return (text or "").lower()'))],
     "reads_a_place_in_any_common_spelling or fold_makes_one_word"),
    ("the address gate stops reading multi-word names as phrases",
     [("scripts/import_candidates.py", _text("        if \" \" in t:\n            if f\" {t} \" in padded", "        if False:\n            if f\" {t} \" in padded"))],
     "reads_a_place_in_any_common_spelling"),
    ("the address gate stops stripping Arabic attached prefixes",
     [("scripts/import_candidates.py", _text("            if w.startswith(pre) and len(w) - len(pre) >= 3:", "            if False:"))],
     "reads_a_place_in_any_common_spelling"),
    ("the address gate ignores a place in a subdomain",
     [("scripts/import_candidates.py", _text('    text = " ".join(labels) + " " + path', '    text = path'))],
     "reads_a_place_in_any_common_spelling"),
    ("Iran's provinces lose their Persian names",
     [("data/curated/systems/ir/system.json", _artifact(lambda d: d["geography"].__setitem__("unit_aliases", {})))],
     "native_script_and_a_latin_name or reads_a_place_in_any_common_spelling"),
    ("mortar and artillery wording passes the method check",
     [("pipeline/build_systems.py", _text("|mortars?|ieds?|artillery|air ?strikes?)", ")"))],
     "method_and_route_wording"),
    ("a methodology-red-team hold is published again",
     [("data/curated/systems/us/events.json", _artifact(lambda d: d["events"].append({**d["events"][0], "event_id": "us-2024-02-03-tgp-line-100-1-mississippi"})))],
     "no_record_held_on_a_strict"),
    ("clause 5 rests on a count of people written in the basis",
     [("data/curated/systems/us/events.json", _artifact(_criterion(5, threshold_basis="About 250,000 people lost power (TEST PLACEHOLDER).")))],
     "counts_people_as_customers"),

    ("a republished wire story counts as a second origin",
     [("pipeline/build_systems.py", _text('            return "wire:" + name', '            pass'))],
     "counted_by_origin_not_by_url"),
    ("Wikipedia counts as an origin",
     [("pipeline/build_systems.py", _text('    if domain in DISCOVERY_ONLY_DOMAINS or "wikipedia" in (source.get("publisher") or "").lower():\n        return None',
                                          '    if False:\n        return None'))],
     "counted_by_origin_not_by_url"),
    ("the crude label loses its condensate qualifier",
     [("web/public/data/global/energy_context.json", _artifact(lambda d: d["metrics"]["crude_production"].__setitem__("label", "Crude oil production")))],
     "label_carries_its_definition_qualifier"),
    ("the accounting convention is not served to the Gulf view",
     [("web/public/data/global/gulf.json", _artifact(lambda d: d.pop("accounting_convention")))],
     "label_carries_its_definition_qualifier"),

    ("simplification drops small holes again",
     [("pipeline/geo.py", _text("if len(s) >= min_ring_points or (i > 0 and len(s) >= 4):", "if len(s) >= min_ring_points:"))],
     "keeps_a_small_hole"),

    # Test-architecture red team, round two: its own mutants that survived, ported here.
    ("an abstracted attack record may carry an English headline",
     [("pipeline/build_systems.py", _text('if s.get("title_original") or s.get("title_en"):\n                    out.append(f"{eid}: a headline on a record published without its place")',
                                          'if s.get("title_original"):\n                    out.append(f"{eid}: a headline on a record published without its place")'))],
     "refuses_either_headline_and_method_text"),
    ("the build stops reading method wording in an abstracted record's text",
     [("pipeline/build_systems.py", _text("            if METHOD_WORDING.search(text):\n                out.append(f\"{eid}: the record's text",
                                          "            if False:\n                out.append(f\"{eid}: the record's text"))],
     "refuses_either_headline_and_method_text"),
    ("an opaque id may name the facility",
     [("pipeline/build_systems.py", _text("or not eid.startswith(\n                    f\"{system_id}-{e.get('date')}-{e.get('asset_class', '').replace('_', '-')}-attack-\"):",
                                          "or False:"))],
     "opaque_id_names_the_class"),
    # Iteration 21 (safety red team): no lane-written id is kept at all, strict form or not.
    ("the import keeps a lane-written id with free-text middle words",
     [("scripts/import_candidates.py", _text('    material = f"{system_id}|{r[\'candidate_id\']}".encode("utf-8")\n',
                                             '    if "-attack-" in r["candidate_id"]:\n        return r["candidate_id"]\n'
                                             '    material = f"{system_id}|{r[\'candidate_id\']}".encode("utf-8")\n'))],
     "lane_written_id_is_never_kept"),
    ("the build trusts the import to strip a campaign record's headline",
     [("pipeline/build_systems.py", _text('        if any(s.get("title_original") or s.get("title_en") for s in e["sources"]):\n            problems.append',
                                          '        if False:\n            problems.append')),
      ("scripts/import_candidates.py", _text('            s.pop("title_original", None)\n            s.pop("title_en", None)\n', ''))],
     "import_should_have_removed"),
    ("a campaign record serves a headline",
     [("web/public/data/systems/sa/events.json", _artifact(lambda d: next(e for e in d["events"] if e.get("publication"))["sources"][0].update(
         title_original="TEST PLACEHOLDER", title_en="TEST PLACEHOLDER")))],
     "no_served_campaign_record_carries_a_headline"),
    ("the build trusts a stale source count on a campaign record",
     [("pipeline/build_systems.py", _text('        if rv.get("source_count") is not None and rv["source_count"] != len(e["sources"]):',
                                          '        if False:'))],
     "import_should_have_removed"),
    ("the status rule stops reading publishers",
     [("pipeline/build_systems.py", _text('        texts += [("publisher", s.get("publisher")) for s in e["sources"]]\n', ''))],
     "hazard_name_and_the_publisher"),
    ("the status rule stops reading the hazard name",
     [("pipeline/build_systems.py", _text('                 ("hazard name", e.get("hazard_name"))]', '                 ]'))],
     "hazard_name_and_the_publisher"),
    ("the gate stops reading a facility named in the capacity note",
     [("scripts/import_candidates.py", _text('text = (text + " " + str((r.get("capacity_affected") or {}).get("source_says") or "")).lower()', 'text = text.lower()'))],
     "capacity_note_and_short_arabic"),
    ("the gate stops reading three-letter Arabic words in an address",
     [("scripts/import_candidates.py", _text('    seq = [w for w in re.findall(r"[^\\W\\d_]+", build_systems.fold(text))]',
                                           '    seq = [w for w in re.findall(r"[^\\W\\d_]{4,}", build_systems.fold(text))]'))],
     "capacity_note_and_short_arabic"),
    ("a capacity block defaults to the facility's size",
     [("pipeline/build_systems.py", _text('out["measure"] = out["measure"] or "affected"', 'out["measure"] = out["measure"] or "facility_size"'))],
     "defaults_to_the_amount_affected"),
    ("a range may have equal ends",
     [("pipeline/build_systems.py", _text("hi is not None and lo < hi,", "hi is not None and lo <= hi,"))],
     "defaults_to_the_amount_affected"),
    ("a capacity figure needs no source words",
     [("pipeline/build_systems.py", _text('if not cap.get("unit") or not cap.get("source_says"):', 'if not cap.get("unit"):'))],
     "defaults_to_the_amount_affected"),
    ("a partial pass resets the research clock",
     [("pipeline/build_systems.py", _text('        if completeness != "complete":\n            due = last["date"]', '        if False:\n            due = last["date"]'))],
     "partial_pass_is_owed_now"),
    ("the recent list names an episode that contains a covered record",
     [("pipeline/build_systems.py", _text('ep["name"] if ep["records"] > 1 and not covered else None', 'ep["name"] if ep["records"] > 1 else None'))],
     "recent_list_keeps_precision"),
    ("the recent list claims day precision",
     [("pipeline/build_systems.py", _text('"date_precision": first["date_precision"],', '"date_precision": "day",'))],
     "recent_list_keeps_precision"),
    ("recovery durations from one country are shown",
     [("pipeline/build_systems.py", _text("if len(systems_in[(cls, kind)]) < 2:", "if len(systems_in[(cls, kind)]) < 1:"))],
     "recovery_durations_need_two"),
    ("a partial restart counts as completed recovery",
     [("pipeline/build_systems.py", _text('COMPLETED_RECOVERY_KINDS = ("full_restart", "service_restored")',
                                          'COMPLETED_RECOVERY_KINDS = ("full_restart", "service_restored", "partial_restart", "partial_restoration")'))],
     "recovery_durations_need_two"),
    ("the context accepts the current year as its comparison year",
     [("pipeline/global_context.py", _text("elif year >= today.year:", "elif year > today.year:"))],
     "current_year_and_serves_true_coverage"),
    ("context coverage counts missing values",
     [("web/public/data/global/energy_context.json", _artifact(lambda d: d["coverage"].update({m: len(d["countries"]) for m in d["coverage"]})))],
     "current_year_and_serves_true_coverage"),
    ("national context rows are ordered by production",
     [("web/public/data/global/energy_context.json", _artifact(lambda d: d["countries"].sort(key=lambda r: -(r["values"].get("total_production") or 0))))],
     "current_year_and_serves_true_coverage"),
    ("a Gulf extra metric newer than the comparison year is built",
     [("pipeline/gulf_context.py", _text('    late = sorted(mid for mid, m in extra["metrics"].items() if m["year"] > context["comparison_year"])',
                                         '    late = []'))],
     "gulf_extra_metric_newer"),

    # §43 newer national totals
    ("a campaign-year national total is served for a country under the campaign policy",
     [(CTX, _artifact(_context_row("SAU", {"oil_production": {"year": 2026, "value": 1.0}})))],
     "comparison_year_only"),
    ("the newer-year guard hides a newer total of a country outside the campaign policy",
     [(CTX, _artifact(_context_row("USA", {})))],
     "comparison_year_only"),

    # §44 single-site classes
    ("an attack record of a single-site class is not refused by the build",
     [("pipeline/build_systems.py", _text('        if e.get("cause") in KINETIC_CAUSES and e.get("asset_class") in single:',
                                        '        if False:'))],
     "one_site_of_is_refused"),
    ("a single-site class needs no basis",
     [("pipeline/build_systems.py", _text('        if not (why or {}).get("basis"):', '        if False:'))],
     "one_site_of_is_refused"),
    ("a single-site class need not be an asset class",
     [("pipeline/build_systems.py", _text('        if cls not in set(ASSET_CLASSES) | set(TAXONOMY_EXTENSIONS["asset_classes"]):', '        if False:'))],
     "one_site_of_is_refused"),
    ("the import gate stops holding an attack record of a single-site class",
     [("scripts/import_candidates.py", _text('    if r.get("cause") in build_systems.KINETIC_CAUSES and r.get("asset_class") in ((policy or {}).get("single_site_classes") or {}):',
                                           '    if False:'))],
     "single_site_class"),
    ("Qatar's LNG is no longer declared a single site",
     [("data/curated/systems/qa/system.json", _artifact(_drop_single_site("qa", "lng_terminal")))],
     "every_declared_single_site"),
    ("Bahrain's single refinery loses its basis",
     [("data/curated/systems/bh/system.json", _artifact(_drop_single_site("bh", "refinery", "")))],
     "every_declared_single_site"),

    # §10 canonical citation addresses
    ("an amp host is published as the citation",
     [("scripts/import_candidates.py", _text('    final = re.sub(r"^(https?://)amp\\.", r"\\1", final)\n', ""))],
     "lands_on"),
    ("a leading amp path segment is published as the citation",
     [("scripts/import_candidates.py", _text('    final = re.sub(r"^(https?://[^/]+)/amp/", r"\\1/", final)\n', ""))],
     "lands_on"),
    ("an ampArticle address is published as the citation",
     [("scripts/import_candidates.py", _text('    return re.sub(r"/ampArticle/", "/article/", final)', "    return final"))],
     "lands_on"),
    ("the citation keeps the short link a reader is redirected from",
     [("scripts/import_candidates.py", _text('    final = re.sub(r"/amp/?$", "/", FINAL_ADDRESSES.get(url, url))',
                                           '    final = re.sub(r"/amp/?$", "/", url)'))],
     "lands_on"),
    ("the gate judges only the address as cited, not where it lands",
     [("scripts/import_candidates.py", _text("for u in {url, final})", "for u in {url})"))],
     "judged_by_where"),
    ("an opaque link whose destination was never read is published",
     [("scripts/import_candidates.py", _text('    return bool(path) and not words and bool(re.search(r"\\d{4,}", path))', "    return False"))],
     "judged_by_where"),
    ("a bot challenge is read as the article",
     [("scripts/check_source_links.py", _text('    if CHALLENGE.search(final):\n        return "challenge"\n', ""))],
     "redirect_is_classed"),
    ("an article id in the path is not read",
     [("scripts/check_source_links.py", _text(' or re.search(r"\\d{4,}", urllib.parse.urlsplit(final).path)', ""))],
     "redirect_is_classed"),
    ("a home page counts as the article",
     [("scripts/check_source_links.py", _text('if w]) >= 3', 'if w]) >= 0'))],
     "redirect_is_classed"),
    ("an adopted address keeps its tracking parameters",
     [("scripts/check_source_links.py", _text("                                    if not TRACKING.match(k)])", "                                    ])"))],
     "redirect_is_classed"),

    # Pass order, the absent index, review edits
    ("of two passes on one day the earlier wins",
     [("pipeline/build_systems.py", _text('    last = max(enumerate(systematic), key=lambda ip: (ip[1]["date"], ip[0]))[1] if systematic else None',
                                        '    last = max(systematic, key=lambda p: p["date"]) if systematic else None'))],
     "later_in_the_log"),
    ("a country page loses the statement that no index is not a zero",
     [("web/public/data/systems/ca/system.json", _artifact(lambda d: d.__setitem__("no_index_reason", "No index; see GLOBAL_METHODOLOGY.json.")))],
     "no_index_is_not_a_zero"),
    ("the public review edits keep a held record of a system under the campaign policy",
     [("data/curated/systems/review_edits.json", _artifact(_edit_for(
         "kw-2026-03-20-refinery-attack-1", "effect", "TEST PLACEHOLDER",
         "Blind review, role(s) safety: reconciled correction; the reviewers' wording is kept in the local review file")))],
     "keep_nothing_for_an_unpublished"),

    # §26-27 capacity
    ("an at-least figure is left as a point value",
     [("pipeline/build_systems.py", _text('        out["value"] = None\n    elif q == "at_most":', '        pass\n    elif q == "at_most":'))],
     "bound_is_never_left"),
    ("a disputed figure may carry a point value",
     [("pipeline/build_systems.py", _text('"disputed": v is None and lo is None and hi is None,', '"disputed": lo is None and hi is None,'))],
     "shape_contradicts"),
    ("a range may run backwards",
     [("pipeline/build_systems.py", _text(' and hi is not None and lo < hi,', ' and hi is not None,'))],
     "shape_contradicts"),
    ("an unknown capacity measure is accepted",
     [("pipeline/build_systems.py", _text('    if cap["measure"] not in CAPACITY_MEASURES:', '    if False:'))],
     "shape_contradicts"),
    ("'over 2,000 MW' is read as an exact figure",
     [("pipeline/build_systems.py", _text('r"\\b(more than|over(?=\\s+\\d)|at least|', 'r"\\b(more than|at least|'))],
     "qualifier_follows"),
    ("a served capacity block contradicts its qualifier",
     [("web/public/data/systems/us/events.json", _artifact(_on_event(lambda e: e.get("capacity_affected"),
                                                                    lambda e: e["capacity_affected"].update({"qualifier": "range", "value_min": None}))))],
     "served_capacity_block"),
    ("a capacity total is computed downstream",
     [("pipeline/build_systems.py", _append('\n\ndef _total(evs):\n    return sum(e["capacity_affected"]["value"] for e in evs)\n'))],
     "nothing_sums"),

    # §50-53 dates and numbers
    ("a queue month date keeps its first-of-month form",
     [("pipeline/build_systems.py", _text('    return {"month": date[:7], "year": date[:4]}.get(precision, date)', "    return date"))],
     "compatibility_path_canonicalises"),
    ("the build accepts the old first-of-month form",
     [("pipeline/build_systems.py", _text('DATE_SHAPES = {"day": r"\\d{4}-\\d{2}-\\d{2}", "month": r"\\d{4}-\\d{2}",',
                                        'DATE_SHAPES = {"day": r"\\d{4}-\\d{2}-\\d{2}", "month": r"\\d{4}-\\d{2}(-01)?",')),
      ("pipeline/build_systems.py", _text('{"month": e["date"] + "-01",', '{"month": e["date"][:7] + "-01",'))],
     "refuses_the_old_month_form"),
    ("the build accepts a day the calendar does not have",
     [("pipeline/build_systems.py", _text("""            out.append(f"{eid}: {e['date']!r} is not a calendar date")""", "            pass"))],
     "refuses_the_old_month_form"),
    ("the build accepts an end date before the start",
     [("pipeline/build_systems.py", _text('        elif end < e.get("date", ""):', "        elif False:"))],
     "refuses_the_old_month_form"),
    ("a served month record drifts to a day",
     [("web/public/data/systems/us/events.json", _artifact(_on_event(lambda e: e["date_precision"] == "month",
                                                                    lambda e: e.__setitem__("date", e["date"] + "-01"))))],
     "served_month_records"),
    ("a curated month record drifts to a day",
     [("data/curated/systems/us/events.json", _artifact(_on_event(lambda e: e["date_precision"] == "month",
                                                                 lambda e: e.__setitem__("date", e["date"] + "-01"))))],
     "every_curated_date_is_written"),
    ("'10 20' is read as 1020",
     [("pipeline/calendars.py", _text('    if not s or "\u060c" in s:', '    s = s.replace(" ", "")\n    if not s or "\u060c" in s:'))],
     "ambiguous_number_forms"),
    ("a leading zero is read through",
     [("pipeline/calendars.py", _text('    if len(digits) > 1 and digits[0] == "0":', "    if False:"))],
     "ambiguous_number_forms"),
    ("the Arabic comma is read as a thousands separator",
     [("pipeline/calendars.py", _text('    if not s or "\u060c" in s:\n        return None\n    s = s.replace(',
                                    '    s = s.replace("\u060c", ",")\n    if not s:\n        return None\n    s = s.replace('))],
     "ambiguous_number_forms"),
    ("a Solar Hijri month is shown as one Gregorian month",
     [("pipeline/calendars.py", _text('        normalized = None\n        basis += "; month precision',
                                    '        normalized = first.isoformat()[:7]\n        basis += "; month precision'))],
     "solar_hijri_month_keeps_month_precision"),
    ("the tabular Hijri leap month is forgotten",
     [("pipeline/calendars.py", _text("return 30 if month % 2 == 1 or (month == 12 and _hijri_leap(year)) else 29",
                                    "return 30 if month % 2 == 1 else 29"))],
     "hijri_month_lengths"),
    ("a day-month order is guessed when both are 12 or below",
     [("pipeline/calendars.py", _text("            if a <= 12 and b <= 12 and a != b:", "            if False:"))],
     "ambiguous_or_impossible_date"),

    # §13-24 strict reading, every system
    ("a record held on the strict reading is published again",
     [("data/curated/systems/us/events.json", _artifact(_readd_strict_hold))],
     "no_record_held_on_a_strict"),
    ("a clause-5 record rests on extent alone",
     [("data/curated/systems/us/events.json", _artifact(_criterion(5, threshold_basis="Outages by extent across many counties (TEST PLACEHOLDER).")))],
     "clause_5_record_rests_on_extent"),
    ("a clause-5 record counts people as customers",
     [("data/curated/systems/us/events.json", _artifact(_people_as_customers))],
     "counts_people_as_customers"),
    ("a clause-4 record rests on demand alone",
     [("data/curated/systems/us/events.json", _artifact(_criterion(4, threshold_basis="Programmed cuts tied to a load rise (TEST PLACEHOLDER).",
                                                                  effect="Programmed cuts were announced (TEST PLACEHOLDER).")))],
     "clause_4_record_rests_on_demand"),
    ("a partial refinery effect is accepted under clause 1",
     [("data/curated/systems/us/events.json", _artifact(_criterion(1, effect="A number of units were shut (TEST PLACEHOLDER).")))],
     "clause_1_record_rests_on_an_unquantified"),
    ("a public strict hold loses its tag",
     [("data/curated/systems/review_edits.json", _artifact(_untag_hold))],
     "strict_hold_is_on_file"),
    ("a restricted system's strict hold is a public edit",
     [("data/curated/systems/review_edits.json", _artifact(_edit_for(
         "kw-2025-04-09-programmed-power-cuts-demand-above-generation", "suggested_disposition", "held",
         "[C4-DEMAND] TEST PLACEHOLDER")))],
     "strict_hold_is_on_file"),

    # Option B on the global recent list (derived artifact)
    ("the global recent list shows a campaign record's own region",
     [("web/public/data/global/recent_evidence.json", _artifact(lambda d: _first(
         _recent_members(d), lambda m: m["withheld"]).__setitem__("region", "Eastern Province")))],
     "recent_list_shows_of_each_record"),
    ("the global recent list carries a campaign record's own episode id",
     [("web/public/data/global/recent_evidence.json", _artifact(lambda d: _first(
         d["episodes"], lambda ep: any(m["withheld"] for m in ep["members"])).__setitem__("episode_id", "sa-2026-03-01-refinery-strike")))],
     "recent_list_shows_of_each_record"),
    ("the global recent list shows effect text for a record of a restricted system",
     [("web/public/data/global/recent_evidence.json", _artifact(lambda d: _first(
         _recent_members(d), lambda m: m["effect_on_country_page"]).__setitem__("effect", "Output fell by 300 MW (TEST PLACEHOLDER).")))],
     "recent_list_shows_of_each_record"),
    ("the global recent list stops pointing to the country page for an effect",
     [("web/public/data/global/recent_evidence.json", _artifact(lambda d: _first(
         _recent_members(d), lambda m: m["effect_on_country_page"]).__setitem__("effect_on_country_page", False)))],
     "recent_list_shows_of_each_record"),

]
MUTATIONS += ITER20_MUTATIONS

# The Research Coverage Explorer. The lane logic is the shipped TypeScript, executed under Node by
# tests/test_research_coverage.py, so these break the frontend rule itself, not a copy of it.
LANES = "web/src/global/laneCoverage.ts"
RESEARCH_MUTATIONS = [
    ("a lane whose source refused access reads as complete",
     [(LANES, _text('  if (win === "inaccessible") return "blocked_by_source";', '  if (win === "inaccessible") return "declared_query_set_run";'))],
     "blocked_and_stopped_lanes_are_never_complete"),
    ("a lane stopped by the search allowance reads as complete",
     [(LANES, _text('  if (lane.stopped_by === "search_limit") return "stopped_by_search_limit";', '  if (lane.stopped_by === "search_limit") return "declared_query_set_run";'))],
     "blocked_and_stopped_lanes_are_never_complete"),
    ("a lane that skipped a required language reads as complete",
     [(LANES, _text('  const doneOk = win !== "unknown" && missingLanguages(lane).length === 0;', '  const doneOk = win !== "unknown";'))],
     "missing_a_language"),
    ("source health is shown as research coverage",
     [("web/src/global/ResearchCoverage.tsx", _text(
         'className="eyebrow rc-sh-head">Source health: the citations behind the published events</h3>',
         'className="eyebrow rc-sh-head">Research coverage: the citations behind the published events</h3>'))],
     "kept_apart_from_source_health"),
    ("a campaign system's pass history shows its held count",
     [(LANES, _text("  if (restricted) {\n    // \"Remain under review\"", "  if (restricted && false) {\n    // \"Remain under review\""))],
     "render_no_count_from_the_research_outcome"),
]
MUTATIONS += RESEARCH_MUTATIONS

# Iteration 21: the regional overview's map, member list and brief.
GULF_MAP_MUTATIONS = [
    ("a chosen figure's definition is hidden",
     [("web/src/global/GroupView.tsx", _text('<p className="metric-definition small">{facts.definition}</p>',
                                             '<p className="metric-definition small"></p>'))],
     "iter21_gulf_metric_definition"),
    ("the regional map opens coloured by a metric",
     [("web/src/global/GroupView.tsx", _text("const colourBy = metric && ctx?.metrics[metric] ? metric : null;",
                                             "const colourBy = metric && ctx?.metrics[metric] ? metric : (ctx ? Object.keys(ctx.metrics)[0] : null);"))],
     "iter21_gulf_default_map"),
    ("the member list is sorted by a figure",
     [("web/src/global/groupMap.ts", _text('a.name.localeCompare(b.name, "en")',
                                           "(b.values[Object.keys(b.values)[0]] ?? 0) - (a.values[Object.keys(a.values)[0]] ?? 0)"))],
     "iter21_gulf_member_list"),
    ("the accounting convention is dropped beside the figure",
     [("web/src/global/groupMap.ts", _text("accounting: ctx.accounting_convention ?? null,", "accounting: null,"))],
     "iter21_gulf_accounting"),
    ("the regional brief keeps the reader's selection mark",
     [("web/src/global/GroupView.tsx", _text("const clean = withoutHighlight(style);", "const clean = style;"))],
     "iter21_gulf_brief_drops"),
]
MUTATIONS += GULF_MAP_MUTATIONS

# Iteration 21: the comparison workspace. Caught by tests/test_compare.py at the source; the same
# rules are tested in the browser and in vitest, which this pytest-only harness cannot run.
CMP = "web/src/global/compare.ts"
CMP_VIEW = "web/src/global/CompareView.tsx"
ROUTER = "web/src/global/router.ts"
ITER21_COMPARE_MUTATIONS = [
    ("the comparison gains an event-count row",
     [(CMP, _text('    { id: "reporting", label: "Reporting environment", basis: "within",',
                  '    { id: "events", label: "Recorded events", basis: "common", basisNote: "",\n'
                  '      cells: cols.map((c) => value(String(c.system?.event_summary.recorded_events))) },\n'
                  '    { id: "reporting", label: "Reporting environment", basis: "within",'))],
     "compare_rows_are_declared or compare_never_reads_a_tally"),
    ("the comparison columns are sorted by a figure",
     [(CMP_VIEW, _text("  const cols: CompareColumn[] = (resolved?.columns ?? []).map((entry) => {",
                       "  const cols: CompareColumn[] = [...(resolved?.columns ?? [])].sort((a, b) => (b.bounds?.[2] ?? 0) - (a.bounds?.[2] ?? 0)).map((entry) => {"))],
     "compare_never_sorts"),
    ("the compared systems are re-ordered by name",
     [(CMP, _text("return { columns: known.slice(0, MAX_COMPARE),",
                  "return { columns: [...known].sort((a, b) => a.name.localeCompare(b.name)).slice(0, MAX_COMPARE),"))],
     "compare_never_sorts"),
    ("a missing national figure becomes zero in the comparison",
     [(CMP, _text("row.values[metric] : null;", "row.values[metric] ?? 0 : 0;"))],
     "compare_missing_figure_stays_missing"),
    ("a missing national figure loses its no-data cell",
     [(CMP, _text('if (v == null) return { kind: "no_data", text: "no data"', 'if (v === undefined) return { kind: "no_data", text: "no data"'))],
     "compare_missing_figure_stays_missing"),
    ("no index renders as zero in the comparison",
     [(CMP, _text('return value("No index", col.system?.no_index_reason', 'return value(String(col.entry.headline?.value ?? 0), col.system?.no_index_reason'))],
     "compare_no_index_is_words or compare_never_reads_a_tally"),
    ("the theatre's index value is set beside systems with none",
     [(CMP, _text("return value(`Has its own index (${col.entry.index.name}), not comparable`,",
                  "return value(`Index ${col.entry.headline?.value}`,"))],
     "compare_never_reads_a_tally"),
    ("the comparison export drops its not-comparable caveat",
     [(CMP, _text("      EXPORT_NOT_COMPARABLE,\n", ""))],
     "compare_export_carries"),
    ("the comparison export drops its research-coverage caveat",
     [(CMP, _text("Research coverage differs by system and is incomplete everywhere: ", ""))],
     "compare_export_carries"),
    ("the compare selection is dropped from the URL (route)",
     [(ROUTER, _text('if (p.has("compare")) return', 'if (false) return'))],
     "compare_selection_lives_in_the_url"),
    ("the compare selection is dropped from the URL (link)",
     [(ROUTER, _text(".slice(0, MAX_COMPARE).map(encodeURIComponent)", ".slice(0, 0).map(encodeURIComponent)"))],
     "compare_selection_lives_in_the_url"),
    ("a compare edit is not written to the URL",
     [(CMP_VIEW, _text("navigateCompare(next, true)", "void next"))],
     "compare_selection_lives_in_the_url"),
]
MUTATIONS += ITER21_COMPARE_MUTATIONS

# Iteration 21: route performance and failure containment. The browser tests in
# web/e2e/resilience.e2e.ts catch each of these too; these guards are the ones this sandbox can run.
ITER21_PERF_MUTATIONS = [
    ("the views lose their error boundary",
     [("web/src/Root.tsx", _text('<ViewBoundary key={view.key} label={view.label} cleanHref={view.cleanHref} home={route.view === "home"}>', "<>")),
      ("web/src/Root.tsx", _text("</ViewBoundary>", "</>"))],
     "every_route_renders_inside_a_view_boundary"),
    ("a failed view's boundary carries over into the next view",
     [("web/src/Root.tsx", _text("<ViewBoundary key={view.key} ", "<ViewBoundary "))],
     "every_route_renders_inside_a_view_boundary"),
    ("the manifest is fetched again by every caller",
     [("web/src/global/manifest.ts", _text('return once("global/manifest.json", async () => {', "return (async () => {")),
      ("web/src/global/manifest.ts", _text("    return sanitizeManifest(m);\n  });\n}", "    return sanitizeManifest(m);\n  })();\n}"))],
     "every_global_loader_goes_through or loaders_keep_a_success_and_retry_a_failure"),
    ("a failed request is kept, so a broken file never loads again",
     [("web/src/global/manifest.ts", _text("  p.catch(() => { if (loads.get(key) === p) loads.delete(key); });\n", "  p.catch(() => undefined);\n"))],
     "every_global_loader_goes_through or loaders_keep_a_success_and_retry_a_failure"),
    ("a broken country payload hovered on the home becomes an unhandled rejection",
     [("web/src/global/manifest.ts", _text("      return e ? loadCountry(e) : undefined;\n    })\n    .catch(() => undefined);",
                                           "      return e ? loadCountry(e) : undefined;\n    });"))],
     "prefetch_never_reports"),
    ("a home panel failure takes the whole home down",
     [("web/src/global/GlobalHome.tsx", _text('        <PanelBoundary label="Recent evidence">\n          <RecentEvidencePanel />\n        </PanelBoundary>',
                                              "        <RecentEvidencePanel />"))],
     "home_panels_each_have_their_own_boundary"),
    ("the regional context is drawn without validation",
     [("web/src/global/manifest.ts", _text("validated<GroupContext>(path, groupContextProblems)", "validated<GroupContext>(path, () => [])"))],
     "shape_validation_covers"),
]
MUTATIONS += ITER21_PERF_MUTATIONS

# Iteration 21: the global home. Each breaks one rule of the home cards, their order, or the
# Start-here memory, and must be caught by tests/test_iteration21_home.py.
ITER21_HOME_MUTATIONS = [
    ("a home card shows an event count",
     [("web/src/global/GlobalHome.tsx", _text(
         "      {record && <div className=\"small\">{record}</div>}\n",
         "      {record && <div className=\"small\">{record}</div>}\n      <div className=\"small\">{s.files.length} events</div>\n"))],
     "card_reads_no_count"),
    ("the home page is sorted by a figure",
     [("web/src/global/GlobalHome.tsx", _text(
         "const countries = manifest?.systems.filter((s) => s.kind === \"country\" && inFilter(s)) ?? [];",
         "const countries = (manifest?.systems.filter((s) => s.kind === \"country\" && inFilter(s)) ?? [])"
         ".sort((a, b) => (b.record_reviewed ?? \"\").localeCompare(a.record_reviewed ?? \"\"));"))],
     "never_reorders_systems"),
    ("a home card shows a held count",
     [("web/src/global/GlobalHome.tsx", _text(
         "      {record && <div className=\"small\">{record}</div>}\n",
         "      {record && <div className=\"small\">{record}</div>}\n"
         "      {s.campaign_restricted && <div className=\"small\">{manifest.corpus?.records} held for review</div>}\n"))],
     "card_reads_no_count"),
    ("the Start-here memory crashes when storage throws",
     [("web/src/global/startHereMemory.ts", _text(
         "  try {\n    return getStorage()?.getItem(START_HERE_KEY) === \"1\";\n  } catch {\n    return false;\n  }\n",
         "  return getStorage()?.getItem(START_HERE_KEY) === \"1\";\n"))],
     "storage_failure_escape"),
]
MUTATIONS += ITER21_HOME_MUTATIONS

# Iteration 21: theatre UX rules (tests/test_iteration21_theatre_ux.py; behaviour in
# web/e2e/theatre-ux.e2e.ts).
ITER21_MUTATIONS = [
    ("a withheld row shows a status chip",
     [("web/src/components/ui.tsx", _text(
         "  if (statusWithheld(r)) return <WithheldStatus note={r.publication_note!} />;\n", ""))],
     "withheld_row_shows_no_status_chip"),
    ("the withheld line carries the modelled status",
     [("web/src/components/ui.tsx", _text(
         "      <summary>Status withheld</summary>",
         '      <summary>Status withheld</summary><EvidenceChip kind="modelled" />'))],
     "withheld_row_shows_no_status_chip"),
    ("the Why-this-number path loses the inspector link",
     [("web/src/components/Ribbon.tsx", _text("onClick={explainHeadline}>", "onClick={onOpenMethodology}>"))],
     "why_this_number_opens_the_inspector"),
    ("the Why-this-number path opens today's decomposition for a past date",
     [("web/src/components/Ribbon.tsx", _text(
         'onExplain(isLatest ? { kind: "headline" } : { kind: "historical", step })',
         'onExplain({ kind: "headline" })'))],
     "why_this_number_opens_the_inspector"),
    ("a mode switch drops URL state",
     [("web/src/App.tsx", _text(
         '    if (briefing) exitBriefing();\n    setMapFocus(target === "focus");',
         '    if (briefing) exitBriefing();\n    setSelected(null);\n    setMapFocus(target === "focus");'))],
     "mode_switch_keeps_url_state"),
    ("closed drawers can scroll the app sideways again",
     [("web/src/styles/theatre.css", _text("#root, .shell { overflow: clip; }", "#root, .shell { overflow: hidden; }"))],
     "closed_drawers_cannot_scroll_the_app"),
]
MUTATIONS += ITER21_MUTATIONS

# Iteration 21: the country page's event card and Evidence Inspector. The TypeScript mirror of the
# origin rule is run in Node against the Python rule (tests/test_iteration21_country.py).
EVIDENCE_TS = "web/src/global/evidence.ts"
ITER21_COUNTRY_MUTATIONS = [
    ("the card's origin count becomes a count of addresses",
     [(EVIDENCE_TS, _text("    if (o) out.add(o);\n", "    if (o) out.add(s.url);\n"))],
     "counts_origins"),
    ("a wire story republished by two outlets counts as two origins",
     [(EVIDENCE_TS, _text("if (words.includes(` ${key} `)) return `wire:${name}`;",
                          "if (words.includes(` ${key} `)) return `wire:${name}:${domain}`;"))],
     "counts_origins_as_the_pipeline_does_on_constructed"),
    ("Wikipedia counts as an originating statement on the card",
     [(EVIDENCE_TS, _text('if (DISCOVERY_ONLY_DOMAINS.includes(domain) || publisher.includes("wikipedia")) return null;',
                          "if (false) return null;"))],
     "counts_origins"),
    ("an empty country page says 0 disruptions",
     [("web/src/global/countryCopy.ts", _text(
         '"No qualifying records in the current reviewed corpus — this is not evidence that no disruption occurred."',
         '"0 disruptions in the current reviewed corpus."'))],
     "empty_country_page"),
    ("a campaign-covered record shows its headline",
     [(EVIDENCE_TS, _text("  if (e.publication) return false;\n", "  if (false) return false;\n"))],
     "no_headline_is_allowed"),
    ("the card renders a headline without the campaign guard",
     [("web/src/global/EventCard.tsx", _text("{headlines && s.title_original && (", "{s.title_original && ("))],
     "no_headline_is_allowed"),
]
MUTATIONS += ITER21_COUNTRY_MUTATIONS


# Iteration 21: the global "What's new in the data" panel (pipeline/whats_new.py).
ITER21_MUTATIONS = [
    ("a historical backfill is labelled as dated since the previous build",
     [("pipeline/whats_new.py", _text("            _anchor(d) < previous_as_of for d in dates)",
                                      "            _anchor(d) >= previous_as_of for d in dates)"))],
     "backfill or historical"),
    ("the theatre's backfill judgement is replaced by 'current event'",
     [("pipeline/whats_new.py", _text('all(r.get("record_class") == "historical_record_added" for r in added)',
                                      'all(r.get("record_class") == "current_event" for r in added)'))],
     "ledgers_own_backfill"),
    ("a Gulf system's withdrawn or held records carry a count",
     [("pipeline/whats_new.py", _text('out.append({"category": "records_withdrawn", "aggregated": True, "notes": [',
                                      'out.append({"category": "records_withdrawn", "aggregated": True, "held": len(gone), "notes": ['))],
     "held_in_a_campaign_system"),
    ("a Gulf system's withdrawn or held records are listed one by one",
     [("pipeline/whats_new.py", _text("        if is_restricted:\n            # Which records",
                                      "        if False:\n            # Which records"))],
     "held_in_a_campaign_system"),
    ("time decay of the index is labelled a source event",
     [("pipeline/whats_new.py", _text('return [{"category": "decay_only", "notes": [',
                                      'return [{"category": "records_added", "notes": ['))],
     "decay"),
    ("the panel's file is not a declared artifact",
     [("pipeline/artifacts.py", _text('                   "global/whats_new.json",\n', ""))],
     "declared_artifact"),
]
MUTATIONS += ITER21_MUTATIONS


# Iteration 21 safety red team (tests/test_iteration21_safety.py): opaque ids, the committed
# link-health file, What's new re-review notes and held-record wording under the campaign rule.
SA_GAP = ("Non-conflict incidents remain thin: Saudi outage reporting found states residents affected rather than "
          "customers, so the customer threshold usually cannot be shown met.")
ITER21_SAFETY_MUTATIONS = [
    ("an opaque id's token is the unkeyed hash of the queue id",
     [("scripts/import_candidates.py", _text("hmac.new(key or opaque_key(), material, hashlib.sha256).hexdigest()[:6]",
                                             'hashlib.sha1(r["candidate_id"].encode("utf-8")).hexdigest()[:6]'))],
     "cannot_be_matched_by_hashing"),
    ("the build accepts a lane's own numbering as an opaque token",
     [("pipeline/build_systems.py", _text('            elif not re.fullmatch(OPAQUE_TOKEN, eid.rsplit("-attack-", 1)[1]):',
                                          '            elif False:'))],
     "token_is_not_the_keyed_hash"),
    ("the build no longer checks the committed link-health file",
     [("pipeline/build_systems.py", _text("        problems = link_health_problems(read_json(LINK_HEALTH), curated)",
                                          "        problems = []"))],
     "build_runs_the_link_health_gate"),
    ("a withdrawn record's citation may stay in the link-health states",
     [("pipeline/build_systems.py", _text('    for key in ("link_states", "page_stated_dates"):', "    for key in ():"))],
     "withdrawn_records_citation_left or unpublished_address"),
    ("a withdrawn record's citation may stay in a country's link-check count",
     [("pipeline/build_systems.py", _text("        elif sum(counts.values()) > len(per_system[sid]):", "        elif False:"))],
     "withdrawn_records_citation_left"),
    ("What's new announces a re-review in a campaign system",
     [("pipeline/whats_new.py", _text('    if not is_restricted and (curr_sys.get("record_reviewed") or "")',
                                      '    if (curr_sys.get("record_reviewed") or "")'))],
     "re_review_of_a_campaign_record"),
    ("a campaign system's re-review shows as a build-only change",
     [("pipeline/whats_new.py", _text('"publication_policy", "record_reviewed")', '"publication_policy")'))],
     "re_review_of_a_campaign_record"),
    ("the held-wording gate is not applied to campaign systems",
     [("pipeline/build_systems.py", _text("        problems += held_wording_problems(doc, research_log)", "        pass"))],
     "held_wording_gate_to_campaign_systems_only"),
    ("a campaign system's stated gap counts a held record again",
     [("data/curated/systems/sa/system.json", _text(
         SA_GAP, "Non-conflict incidents remain thin: one 2024 power outage is reported in residents, not customers, "
                 "and is held rather than converted."))],
     "no_campaign_system_states_a_held_record"),
    ("the held-wording rule sees only the word withheld",
     [("pipeline/build_systems.py", _text(r'HELD_WORDING = re.compile(r"\b(held|holds?|withheld|candidates?|on hold)\b", re.I)',
                                          r'HELD_WORDING = re.compile(r"\b(withheld)\b", re.I)'))],
     "held_count_in_a_campaign"),
]
MUTATIONS += ITER21_SAFETY_MUTATIONS

# Iteration 21, test-architecture red team. Each mutant here left every test green before (or was
# caught only by vitest, Playwright or a source-text guard while the rule is behavioural). The
# catching tests run the SHIPPED TypeScript, bundled from web/src with esbuild and executed in Node
# (tests/test_iteration21_testarch.py); the browser-level proof of the same rules is in
# web/src/global/testarch.test.tsx and web/e2e/. The bundler is found in a web/node_modules of the
# checkout the campaign was started from, so the sandbox needs no node_modules of its own.
ITER21_TESTARCH_MUTATIONS = [
    ('a repeated id in the URL becomes two columns',
     [('web/src/global/compare.ts', _text('    else if (!known.includes(s)) known.push(s);', '    else known.push(s);'))],
     'compare_a_repeated_id_is_one_column'),
    ('the four-column cap is dropped',
     [('web/src/global/compare.ts', _text('return { columns: known.slice(0, MAX_COMPARE), unknown,', 'return { columns: known, unknown,'))],
     'compare_caps_at_four_and_names_what_it_left_out'),
    ('a failed country file reads as Loading for ever',
     [('web/src/global/compare.ts', _text('  if (col.status === "failed" || (col.status === "loaded" && !col.system)) return UNAVAILABLE;', '  if (col.status === "loaded" && !col.system) return UNAVAILABLE;'))],
     'compare_a_failed_file_says_so_and_a_loading_one_says_loading'),
    ('safeguards ignore the manifest flag and treat UNCERTAIN as no campaign',
     [('web/src/global/compare.ts', _text('  const on = col.entry.campaign_restricted === true || (state != null && state !== "NO_ACTIVE_CAMPAIGN");', '  const on = state != null && state !== "NO_ACTIVE_CAMPAIGN" && state !== "UNCERTAIN";'))],
     'compare_safeguards_follow_the_manifest_flag_for_every_campaign_system'),
    ('attack records of a country-level system are said to be placed by region',
     [('web/src/global/compare.ts', _text('      if (pp?.kinetic === "country") {', '      if (pp?.kinetic === "country" && pp?.other === "nowhere") {'))],
     'compare_placement_states_each_systems_own_rule'),
    ('a lane blocked by its source is bucketed as declared complete',
     [('web/src/global/compare.ts', _text('  const out = LANE_BUCKETS.map((b) => ({ ...b, n: own(b.state) }));', '  const out = LANE_BUCKETS.map((b) => ({ ...b, n: own(b.state) + (b.state === "universe_searched" ? own("blocked_by_source") : 0) }));'))],
     'compare_lane_buckets_never_call_a_blocked_or_stopped_lane_complete or compare_lane_cells_agree_with_each_served_systems_own_counts'),
    ('an unknown lane state is dropped from the bucket counts',
     [('web/src/global/compare.ts', _text('    if (!listed.has(k) && own(k) > 0) {', '    if (false) {'))],
     'compare_lane_buckets_never_call_a_blocked_or_stopped_lane_complete'),
    ('the export carries the within-system rows too',
     [('web/src/global/compare.ts', _text('    rows: rows.filter((r) => EXPORT_ROW_IDS.includes(r.id)).map((r) => {', '    rows: rows.map((r) => {'))],
     'compare_export_rows_are_research_state_and_context_only'),
    ("a small share reads as 'about 0 in 10'",
     [('web/src/global/compare.ts', _text('  if (part > 0 && r === 0) return "fewer than 1 in 10";\n', ''))],
     'compare_sourcing_shares_are_never_rounded_to_none_or_all'),
    ('the export runs while columns are still loading',
     [('web/src/global/compare.ts', _text('  if (cols.some((c) => c.status === "loading") || (!ctxLoaded && !ctxFailed)) return "Still loading; try again in a moment.";\n', ''))],
     'compare_export_waits_for_every_column_and_a_move_swaps_one_neighbour'),
    ('the drawing omits every footer line but the first',
     [('web/src/global/compareExport.ts', _text('  brief.foot.forEach((t, i) => {', '  brief.foot.slice(0, 1).forEach((t, i) => {'))],
     'compare_png_draws_every_caveat_and_the_columns_in_the_readers_order'),
    ('moving a column does nothing',
     [('web/src/global/compare.ts', _text('  [next[i], next[j]] = [next[j], next[i]];', '  [next[i], next[j]] = [next[i], next[j]];'))],
     'compare_export_waits_for_every_column_and_a_move_swaps_one_neighbour'),
    ('an unknown id is dropped silently',
     [('web/src/global/compare.ts', _text('    if (!s) unknown.push(id);', '    if (!s) continue;'))],
     'compare_caps_at_four_and_names_what_it_left_out'),
    ('the drawing draws the names in reverse',
     [('web/src/global/compareExport.ts', _text('  brief.names.forEach((name, i) => fit(name, colX(i), y, colW - 14));', '  brief.names.forEach((name, i) => fit(name, colX(brief.names.length - 1 - i), y, colW - 14));'))],
     'compare_png_draws_every_caveat_and_the_columns_in_the_readers_order'),
    ('isCampaignRestricted ignores campaign_state',
     [('web/src/global/laneCoverage.ts', _text('  return !!sys.campaign_state && sys.campaign_state.state !== "NO_ACTIVE_CAMPAIGN";', '  return false;'))],
     'research_any_one_campaign_signal_restricts'),
    ('isCampaignRestricted ignores the publication policy',
     [('web/src/global/laneCoverage.ts', _text('  if ((sys.publication_policy?.campaigns ?? []).some((c) => c.policy_applied)) return true;\n', ''))],
     'research_any_one_campaign_signal_restricts'),
    ('isCampaignRestricted ignores under_review',
     [('web/src/global/laneCoverage.ts', _text('  if (passes.some((p) => p.under_review !== undefined)) return true;\n', ''))],
     'research_any_one_campaign_signal_restricts'),
    ('the pass history is rendered as if unrestricted',
     [('web/src/global/ResearchCoverage.tsx', _text('<td>{passOutcomeText(p, restricted, p === newestSystematic)}</td>', '<td>{passOutcomeText(p, false, p === newestSystematic)}</td>'))],
     'research_history_says_remain_under_review_only_on_the_newest_systematic_pass or research_tab_renders_no_count_for_a_campaign_system_whatever_the_log_carries'),
    ('every old pass claims candidates remain under review now',
     [('web/src/global/ResearchCoverage.tsx', _text('<td>{passOutcomeText(p, restricted, p === newestSystematic)}</td>', '<td>{passOutcomeText(p, restricted, true)}</td>'))],
     'research_history_says_remain_under_review_only_on_the_newest_systematic_pass'),
    ("targeted passes' lanes are read as systematic",
     [('web/src/global/laneCoverage.ts', _text('    .filter(({ p }) => p.kind === "systematic")', '    .filter(() => true)'))],
     'research_lanes_come_from_the_newest_systematic_pass_only'),
    ('a lane whose source window is unknown can read as complete',
     [('web/src/global/laneCoverage.ts', _text('  const doneOk = win !== "unknown" && missingLanguages(lane).length === 0;', '  const doneOk = missingLanguages(lane).length === 0;'))],
     'research_complete_needs_a_readable_source_and_every_language'),
    ('the summary drops every shortfall clause',
     [('web/src/global/laneCoverage.ts', _text('  const known = COVERAGE_STATES.filter((k) => states[k]);', '  const known = DONE_STATES.filter((k) => states[k]);'))],
     'research_summary_names_every_shortfall'),
    ('an earlier-format lane is promoted to complete',
     [('web/src/global/laneCoverage.ts', _text('  if (!lane.execution) {\n    return "legacy";', '  if (!lane.execution) {\n    return "declared_query_set_run";'))],
     'research_complete_needs_a_readable_source_and_every_language'),
    ('a zero-record system lists recovery research zeros',
     [('web/src/global/ResearchCoverage.tsx', _text('{rc && bundle.events.length > 0 && (<>', '{rc && (<>'))],
     'research_tab_states_what_it_owes_marks_missing_languages_and_lists_no_zeros'),
    ('unfinished lanes are said to be due next year',
     [('web/src/global/ResearchCoverage.tsx', _text('  const owed = rf.completeness !== "complete" && rows.length > 0;', '  const owed = false;'))],
     'research_tab_states_what_it_owes_marks_missing_languages_and_lists_no_zeros'),
    ('a missing language is not marked on the lane card',
     [('web/src/global/ResearchCoverage.tsx', _text('            {missing.length > 0 && (', '            {missing.length > 99 && ('))],
     'research_tab_states_what_it_owes_marks_missing_languages_and_lists_no_zeros'),
    ('a member with no figure is coloured as zero',
     [('web/src/global/groupMap.ts', _text('  if (v == null) return NO_DATA;', '  if (v == null) return ZERO;'))],
     'gulf_fill_keeps_no_data_zero_filtered_and_geography_apart'),
    ('the membership filter no longer greys members on the map',
     [('web/src/global/groupMap.ts', _text('  for (const s of systems) expr.push(s.a3, memberColour(s, metricId, inView(s), max));', '  for (const s of systems) expr.push(s.a3, memberColour(s, metricId, true, max));'))],
     'gulf_fill_keeps_no_data_zero_filtered_and_geography_apart'),
    ("the brief's rows are sorted by the figure",
     [('web/src/global/groupExport.ts', _text('    rows: ctx.systems.map((s) =>', '    rows: [...ctx.systems].sort((a, b) => (b.values[metricId] ?? 0) - (a.values[metricId] ?? 0)).map((s) =>'))],
     'gulf_brief_draws_every_member_in_name_order_with_its_caveats or gulf_view_never_turns_a_missing_figure_into_zero'),
    ('a withheld feed member shows its effect text',
     [('web/src/global/GroupView.tsx', _text('{mm.withheld ? <span className="dim">Not summarised', '{false ? <span className="dim">Not summarised'))],
     'gulf_a_lone_covered_record_says_it_is_not_summarised_whatever_the_payload_carries'),
    ("the brief drops 'event counts are not comparable'",
     [('web/src/global/groupExport.ts', _text('"Countries in alphabetical order. No index is published for any of them. Event counts are not comparable between countries.",', '"Countries in alphabetical order.",'))],
     'gulf_brief_draws_every_member_in_name_order_with_its_caveats'),
    ("the brief drops 'no facilities, no routes, no status'",
     [('web/src/global/groupExport.ts', _text('"National context only: no facilities, no routes or shipping, no current status of any facility. Energy Disruption Monitor', '"Energy Disruption Monitor'))],
     'gulf_brief_draws_every_member_in_name_order_with_its_caveats'),
    ('the legend never names zero or no-data',
     [('web/src/global/groupMap.ts', _text('  return { zero: shown.some((s) => s.values[metricId] === 0), noData: shown.some((s) => s.values[metricId] == null) };', '  return { zero: false, noData: false };'))],
     'gulf_fill_keeps_no_data_zero_filtered_and_geography_apart'),
    ("the selected member's missing figure prints as 0",
     [('web/src/global/GroupView.tsx', _text('{m.label}: {fmtValue(sel.values[colourBy], m.unit)}', '{m.label}: {fmtValue(sel.values[colourBy] ?? 0, m.unit)}'))],
     'gulf_view_never_turns_a_missing_figure_into_zero'),
    ('a missing table figure prints as 0',
     [('web/src/global/GroupView.tsx', _text('<td key={k} className="mono small">{fmtValue(s.values[k], x.unit)}</td>', '<td key={k} className="mono small">{fmtValue(s.values[k] ?? 0, x.unit)}</td>'))],
     'gulf_view_never_turns_a_missing_figure_into_zero'),
    ('a brief of an uncoloured map is allowed',
     [('web/src/global/GroupView.tsx', _text('    if (!colourBy) { setExportMsg(', '    if (false) { setExportMsg('))],
     'gulf_brief_refuses_an_uncoloured_map'),
    ('a figure of zero is drawn as the smallest value',
     [('web/src/global/groupMap.ts', _text('  if (v === 0) return ZERO;\n', ''))],
     'gulf_fill_keeps_no_data_zero_filtered_and_geography_apart'),
    ('a successful request is never kept',
     [('web/src/global/manifest.ts', _text('  const p = load();\n  loads.set(key, p);', '  const p = load();'))],
     'loaders_keep_a_success_and_retry_a_failure'),
    ('a country route prefetches every country',
     [('web/src/global/prefetch.ts', _text('      const e = m.systems.find((s) => s.id === route.id && s.kind === "country");\n      return e ? loadCountry(e) : undefined;', '      return Promise.all(m.systems.filter((s) => s.kind === "country").map((s) => loadCountry(s)));'))],
     'a_country_route_prefetches_that_country_alone'),
    ('a panel boundary does not contain its failure',
     [('web/src/components/ViewBoundary.tsx', _text('    if (!error) return this.props.children;\n    return (\n      <section className="panel global-note panel-failed"', '    if (!error || true) return this.props.children;\n    return (\n      <section className="panel global-note panel-failed"'))],
     'boundaries_replace_a_failed_view_or_panel_and_say_why'),
    ('a failed chunk is described as a drawing failure',
     [('web/src/components/ViewBoundary.tsx', _text('const CHUNK_FAILURE = /dynamically imported module|Importing a module script failed|error loading dynamically imported|Unable to preload/i;', 'const CHUNK_FAILURE = /(?!)/;'))],
     'boundaries_replace_a_failed_view_or_panel_and_say_why'),
    ('every country shares one boundary key',
     [('web/src/Root.tsx', _text('case "country": return { key: `country:${route.id}`,', 'case "country": return { key: "country",'))],
     'every_country_view_gets_its_own_error_boundary_key'),
    ('the clean-link offer is shown only when it changes nothing',
     [('web/src/components/ViewBoundary.tsx', _text('    const stateful = !!cleanHref && new URLSearchParams(window.location.search).toString()\n      !==', '    const stateful = !!cleanHref && new URLSearchParams(window.location.search).toString()\n      ==='))],
     'boundaries_replace_a_failed_view_or_panel_and_say_why'),
    ('system.json alone is not shape-validated',
     [('web/src/global/manifest.ts', _text('    const bad = shapeProblems(system, { events: [] });', '    const bad: string[] = [];'))],
     'a_malformed_system_file_is_refused_and_a_malformed_manifest_part_dropped'),
    ('a failed energy-context request is kept',
     [('web/src/global/context.ts', _text('      .catch((err) => { contextPromise = null; throw err; });', '      .catch((err) => { throw err; });'))],
     'loaders_keep_a_success_and_retry_a_failure'),
    ('a failed theatre region list is kept',
     [('web/src/global/searchIndex.ts', _text('      .catch((err) => { theatrePromise = null; throw err; });', '      .catch((err) => { throw err; });'))],
     'loaders_keep_a_success_and_retry_a_failure'),
    ('malformed manifest aliases are no longer dropped',
     [('web/src/global/manifest.ts', _text('    if (t.aliases !== undefined && !strings(t.aliases)) delete t.aliases;\n', ''))],
     'a_malformed_system_file_is_refused_and_a_malformed_manifest_part_dropped'),
    ('malformed manifest bounds are no longer dropped',
     [('web/src/global/manifest.ts', _text('    if (t.bounds !== undefined && !box(t.bounds)) delete t.bounds;\n', ''))],
     'a_malformed_system_file_is_refused_and_a_malformed_manifest_part_dropped'),
    ('a malformed manifest corpus is no longer dropped',
     [('web/src/global/manifest.ts', _text('  if (out.corpus !== undefined && !obj(out.corpus)) delete out.corpus;\n', ''))],
     'a_malformed_system_file_is_refused_and_a_malformed_manifest_part_dropped'),
    ('covered is read from the row key again (a Gulf grid fault reads as a campaign record; a keyless withheld record names its place)',
     [('web/src/global/homeModel.ts', _text('  return ep.members.some((m) => m.withheld);', '  return /-row-\\d+$/.test(ep.episode_id);'))],
     'home_covered_is_read_from_withheld_members_never_from_the_row_key or record_feeds_fold_only_one_countrys_covered_runs_and_drop_nothing'),
    ('a run of covered records vanishes from the feed',
     [('web/src/global/homeModel.ts', _text('    out.push({\n      kind: "covered-run",', '    if (false) out.push({\n      kind: "covered-run",'))],
     'home_feed_runs_never_cross_countries_and_served_covered_items_name_no_place or record_feeds_fold_only_one_countrys_covered_runs_and_drop_nothing'),
    ('the method-change caveat is attached to the separable case (indexText.ts)',
     [('web/src/indexText.ts', _text('  return separable ? base :', '  return !separable ? base :'))],
     'whats_new_text_keeps_backfill_method_and_clock_distinctions'),
    ('a covered record names its regions',
     [('web/src/global/homeModel.ts', _text('  if (isCovered(ep)) return one("national_safeguarded");', '  if (isCovered(ep)) return one("national_safeguarded", [...new Set(ep.members.map((m) => m.region))]);'))],
     'home_covered_is_read_from_withheld_members_never_from_the_row_key or home_feed_runs_never_cross_countries_and_served_covered_items_name_no_place'),
    ('covered runs fold across countries',
     [('web/src/global/homeModel.ts', _text('    while (j < episodes.length && isCovered(episodes[j]) && episodes[j].system_id === ep.system_id) j++;', '    while (j < episodes.length && isCovered(episodes[j])) j++;'))],
     'home_feed_runs_never_cross_countries_and_served_covered_items_name_no_place or record_feeds_fold_only_one_countrys_covered_runs_and_drop_nothing'),
    ('Crimea is labelled a region of Russia in search',
     [('web/src/global/searchIndex.ts', _text('    sub: r.country === "UA" ? `Occupied unit', '    sub: r.country === "XX" ? `Occupied unit'))],
     'home_search_folds_keyboard_variants_ranks_by_match_and_never_calls_crimea_russian'),
    ("a date in the reader's future gets a negative age",
     [('web/src/global/homeModel.ts', _text('  if (n < 0) return "";\n', ''))],
     'home_dates_and_record_lines_never_invent_a_figure'),
    ('no record reads as 0 records',
     [('web/src/global/homeModel.ts', _text('  if (recordReviewed === null) return "No qualifying records yet";', '  if (recordReviewed === null) return "0 records";'))],
     'home_dates_and_record_lines_never_invent_a_figure'),
    ('the Persian yeh is no longer folded',
     [('web/src/global/searchNormalize.ts', _text('  "ی": "ي", // Persian yeh', '  "ی_": "ي", // Persian yeh'))],
     'home_search_folds_keyboard_variants_ranks_by_match_and_never_calls_crimea_russian'),
    ('search orders by kind before match quality',
     [('web/src/global/searchIndex.ts', _text('  hits.sort((a, b) => b.score - a.score || KIND_ORDER[a.entry.kind] - KIND_ORDER[b.entry.kind]', '  hits.sort((a, b) => KIND_ORDER[a.entry.kind] - KIND_ORDER[b.entry.kind] || b.score - a.score'))],
     'home_search_folds_keyboard_variants_ranks_by_match_and_never_calls_crimea_russian'),
    ('a withheld record whose status is absent shows its status',
     [('web/src/components/ui.tsx', _text('    && (r.recovery_status == null || r.recovery_status === "impaired"', '    && (r.recovery_status === null || r.recovery_status === "impaired"'))],
     'theatre_withheld_rows_render_nothing_but_status_withheld'),
    ("a released record shows the facility's current modelled status",
     [('web/src/components/ui.tsx', _text('  const releasedOnly = Boolean(r.publication_note);', '  const releasedOnly = false;'))],
     'theatre_withheld_rows_render_nothing_but_status_withheld'),
    ('map focus outranks briefing in the mode',
     [('web/src/theatreMode.ts', _text('  if (briefing) return "brief";\n  return mapFocus ? "focus" : "analyze";', '  if (mapFocus) return "focus";\n  return briefing ? "brief" : "analyze";'))],
     'theatre_withheld_rows_render_nothing_but_status_withheld'),
    ("the withheld line drops the record's own note",
     [('web/src/components/ui.tsx', _text('        {note} This dashboard does not publish', '        This dashboard does not publish'))],
     'theatre_withheld_rows_render_nothing_but_status_withheld'),
    ('a campaign record with a named id gets an anchor',
     [('web/src/global/evidence.ts', _text('  if (e.publication && !isOpaqueAttackId(e, systemId)) return null;', '  if (false) return null;'))],
     'country_no_anchor_from_a_named_campaign_id_and_no_headline_on_a_country_attack'),
    ('any id of the system counts as opaque',
     [('web/src/global/evidence.ts', _text('  return e.event_id.startsWith(prefix) && /^[0-9a-z]{1,6}$/.test(e.event_id.slice(prefix.length));', '  return e.event_id.startsWith(`${systemId}-`);'))],
     'country_no_anchor_from_a_named_campaign_id_and_no_headline_on_a_country_attack'),
    ('a campaign record shows its capacity figure',
     [('web/src/global/evidence.ts', _text('  const covered = !!e.publication;', '  const covered = false;'))],
     'country_what_a_record_does_not_establish_keeps_its_uncertainty'),
    ("an 'at least' figure loses its qualifier",
     [('web/src/global/evidence.ts', _text(': c.qualifier === "at_least" ? "at least "', ': c.qualifier === "at_least" ? ""'))],
     'country_what_a_record_does_not_establish_keeps_its_uncertainty'),
    ('no public evidence of recovery reads as no recovery',
     [('web/src/global/evidence.ts', _text('      return "Researched, and no public report that service came back was found. That is not a finding that it did not.";', '      return "Service has not come back.";'))],
     'country_what_a_record_does_not_establish_keeps_its_uncertainty'),
    ('an unchecked citation reads as reachable',
     [('web/src/global/EventCard.tsx', _text('{s.link_check ? LINK_STATE_LABEL[s.link_check] ?? s.link_check : "not link-checked"}', '{s.link_check ? LINK_STATE_LABEL[s.link_check] ?? s.link_check : LINK_STATE_LABEL.reachable}'))],
     'country_inspector_says_not_link_checked_where_no_check_was_recorded'),
    ('the build marks every citation reachable',
     [('pipeline/build_systems.py', _text('            if states.get(s["url"]) in LINK_STATES:\n                s["link_check"] = states[s["url"]]', '            s["link_check"] = states.get(s["url"], "reachable")'))],
     'country_link_states_are_attached_only_where_a_known_state_was_recorded'),
    ('the build copies any curated value into link_check',
     [('pipeline/build_systems.py', _text('            if states.get(s["url"]) in LINK_STATES:', '            if s["url"] in states:'))],
     'country_link_states_are_attached_only_where_a_known_state_was_recorded'),
    ('an empty UNCERTAIN-campaign page drops its safeguard statement',
     [('web/src/global/EmptyCorpus.tsx', _text('  const campaign = s.campaign_state && s.campaign_state.state !== "NO_ACTIVE_CAMPAIGN" ? s.campaign_state : null;', '  const campaign = s.campaign_state && s.campaign_state.state === "ACTIVE_KINETIC_CAMPAIGN" ? s.campaign_state : null;'))],
     'country_empty_page_states_the_safeguards_of_every_campaign_state'),
    ('the backfill sentence is attached to new records and vice versa',
     [('web/src/global/whatsNewText.ts', _text('    return c.all_predate_previous_build\n      ?', '    return !c.all_predate_previous_build\n      ?'))],
     'whats_new_text_keeps_backfill_method_and_clock_distinctions'),
    ('a system that could not be compared lists its kinds as if compared',
     [('web/src/global/WhatsNew.tsx', _text('{s.unavailable ? "could not be compared" :', '{false ? "could not be compared" :'))],
     'whats_new_panel_never_shows_unknown_as_unchanged_or_nothing_changed'),
    ("a build dated in the reader's future reads as built today",
     [('web/src/global/whatsNewText.ts', _text('  if (d < -1) return "dated after today on your device\'s clock";\n', ''))],
     'whats_new_text_keeps_backfill_method_and_clock_distinctions'),
    ('an unavailable comparison reads as nothing changed',
     [('web/src/global/WhatsNew.tsx', _text('No comparison with an earlier published build is available for this build, so no changes are listed. That is not the same as nothing having changed.', 'Nothing changed since the previous build.'))],
     'whats_new_panel_never_shows_unknown_as_unchanged_or_nothing_changed'),
    ('restricted() ignores campaign-covered records',
     [('pipeline/whats_new.py', _text('        if any(e.get("publication") for e in (side.get("events") or {}).get("events") or []):\n            return True', '        if False:\n            return True'))],
     'whats_new_restriction_is_read_from_either_build_and_from_any_covered_record'),
    ('restricted() reads only the current build',
     [('pipeline/whats_new.py', _text('    for side in (prev, curr):\n        if not side:', '    for side in (curr,):\n        if not side:'))],
     'whats_new_restriction_is_read_from_either_build_and_from_any_covered_record'),
    ('systems are ordered by how much changed',
     [('pipeline/whats_new.py', _text('    glob = global_changes(prev, curr)\n    if not glob and not rows:', '    rows.sort(key=lambda r: -len(r["changes"]))\n    glob = global_changes(prev, curr)\n    if not glob and not rows:'))],
     'whats_new_order_is_by_name_however_much_each_system_changed'),
    ('campaign fields are compared for the build-only line',
     [('pipeline/whats_new.py', _text('        sys_doc = {k: v for k, v in sys_doc.items() if k not in _CAMPAIGN_HIDDEN_SYSTEM}\n        events = [', '        events = ['))],
     'whats_new_a_campaign_systems_hidden_fields_never_surface_as_a_wording_change'),
    ('a diverged baseline is accepted',
     [('pipeline/lineage.py', _text('    if _git(root, "merge-base", "--is-ancestor", sha, "HEAD") is None:\n        lineage["reason"] = (f"baseline {sha[:8]} is not an ancestor', '    if False:\n        lineage["reason"] = (f"baseline {sha[:8]} is not an ancestor'))],
     'whats_new_refuses_a_baseline_on_a_diverged_history'),
]
MUTATIONS += ITER21_TESTARCH_MUTATIONS

# Iteration 22: shared record filters, the safe CSV export and the map loading states. The catching
# tests run the SHIPPED TypeScript in Node (tests/test_iteration22_filters.py); the browser-level
# proof is in web/e2e/filters.e2e.ts and web/e2e/maploading.e2e.ts.
R_CSV = "web/src/global/recordCsv.ts"
R_FILTERS = "web/src/global/recordFilters.ts"
R_BAR = "web/src/global/RecordFilterBar.tsx"
R_COUNTRY = "web/src/global/countryFilters.ts"
R_VIEW = "web/src/global/CountryView.tsx"
R_MAPLOAD = "web/src/mapLoad.ts"
R_MAPIND = "web/src/components/MapLoadIndicator.tsx"
ITER22_FILTER_MUTATIONS = [
    ("the CSV dumps each source object instead of its allow-listed parts (a hidden field is exported)",
     [(R_CSV, _text('    citations: bare ? "" : citationsCell(e.sources),', '    citations: bare ? "" : JSON.stringify(e.sources),'))],
     "csv_exports_only_the_allow_listed_columns"),
    ("the CSV exports a campaign-covered record's region, facility, operator and status",
     [(R_CSV, _text("  const open = !restricted;", "  const open = true;"))],
     "csv_campaign_covered_records_export_no_place or csv_an_abstracted_attack_record"),
    ("an attack record kept at country level is exported as an ordinary record",
     [(R_CSV, _text('  return !!e.publication || placementKind(e, sys) === "country_attack";', "  return !!e.publication;"))],
     "csv_an_abstracted_attack_record"),
    ("a covered record whose own text names its facility exports that text",
     [(R_CSV, _text("  const bare = restricted && !abstracted;", "  const bare = false;"))],
     "csv_a_covered_record_whose_own_text or csv_campaign_covered_records_export_no_place"),
    ("an abstracted impact record exports its region",
     [(R_CSV, _text('    admin1_code: abstracted ? "" : text(r.admin1?.code),', "    admin1_code: text(r.admin1?.code),"))],
     "csv_an_abstracted_impact_record"),
    ("a kinetic impact record without the policy field is exported as standard",
     [(R_CSV, _text('  return r.publication_policy === "country_abstracted" || ABSTRACT_CAUSES.includes(text(r.cause_family))',
                    '  return r.publication_policy === "country_abstracted" || false'))],
     "csv_an_abstracted_impact_record"),
    ("a formula cell reaches the spreadsheet unguarded",
     [(R_CSV, _text("  if (/^[=+\\-@\\t\\r]/.test(s)) s = `'${s}`;\n", ""))],
     "csv_a_formula_in_any_cell"),
    ("the CSV loses its byte-order mark",
     [(R_CSV, _text('  return `${CSV_BOM}${lines.join("\\r\\n")}\\r\\n`;', '  return `${lines.join("\\r\\n")}\\r\\n`;'))],
     "csv_is_rfc_4180_with_a_bom"),
    ("a quote inside a cell is not doubled",
     [(R_CSV, _text("""`"${s.replace(/"/g, '""')}"`""", '`"${s}"`'))],
     "csv_is_rfc_4180_with_a_bom"),
    ("filters widen the list instead of narrowing it (any filter admits)",
     [(R_FILTERS, _text("  return records.filter((r) => defs.every((d) => admits(d, state, r, today)));",
                        "  return records.filter((r) => defs.some((d) => admits(d, state, r, today)));"))],
     "filters_combine_and_never_widen"),
    ("the filter bar hides records without saying so",
     [(R_BAR, _text("      {hidden > 0 && <> The filters hide <strong>{hidden}</strong>.</>}\n      {on.length > 0 &&",
                    "      {on.length > 0 &&"))],
     "filter_bar_always_says_how_many"),
    ("a link's unknown filter value is dropped silently",
     [(R_FILTERS, _text("    if (bad.length > 0) {", "    if (false) {"))],
     "unknown_value_or_filter_is_dropped_with_a_note"),
    ("a link's unknown filter is dropped silently",
     [(R_FILTERS, _text("  if (unknownIds.length > 0) {", "  if (false) {"))],
     "unknown_value_or_filter_is_dropped_with_a_note"),
    ("a link's unknown filter value is obeyed (the list is emptied)",
     [(R_FILTERS, _text("      if (known.has(v)) { if (!good.includes(v)) good.push(v); } else if (!bad.includes(v)) bad.push(v);",
                        "      if (!good.includes(v)) good.push(v);"))],
     "unknown_value_or_filter_is_dropped_with_a_note"),
    ("the country address drops the filters, so a reload shows the full list",
     [(R_COUNTRY, _text("  return withFilterQuery(q.toString(), filterQuery);", "  return q.toString();"))],
     "country_address_keeps_the_filters"),
    ("the country page does not read its filters from the address on load",
     [(R_VIEW, _text("useState(() => filterQueryOf(window.location.search))", 'useState("")'))],
     "country_view_reads_its_filters_from_the_address"),
    ("the country page exports every record instead of the shown list",
     [(R_VIEW, _text("countryExport(bundle.system, shown, scope.length,", "countryExport(bundle.system, scope, scope.length,"))],
     "country_view_exports_the_shown_list"),
    ("a link to a hidden record clears every filter instead of the ones that hide it",
     [(R_FILTERS, _text("  return defs.filter((d) => !admits(d, state, record, today)).map((d) => d.id);",
                        "  return defs.map((d) => d.id);"))],
     "a_link_to_a_record_the_filters_hide"),
    # --- map loading states and the theatre's line network (tests/test_iteration22_maploading.py) ---
    ("a map box says nothing while its geometry is loading",
     [(R_MAPLOAD, _text('  if (!s.geometry) return "geometry";\n', ""))],
     "map_loading_says_geometry_then_data_then_nothing"),
    ("a drawn map goes on saying 'Loading data…'",
     [(R_MAPLOAD, _text("{ ...s, geometry: true, drawn: true, error: null };", "{ ...s, geometry: true, error: null };"))],
     "map_loading_says_geometry_then_data_then_nothing"),
    ("the caller's pending data file is ignored once the polygons are drawn",
     [(R_MAPLOAD, _text('  if (!s.drawn || s.dataPending) return "data";', '  if (!s.drawn) return "data";'))],
     "map_loading_waits_for_the_callers_own_data_file"),
    ("a late file is never named while it loads",
     [(R_MAPLOAD, _text('  if (s.late.some((l) => !l.failed)) return "late";\n', ""))],
     "map_loading_names_a_late_file"),
    ("a late file's failure is silent",
     [(R_MAPLOAD, _text('  if (s.late.some((l) => l.failed)) return "late_failed";\n', ""))],
     "map_loading_names_a_late_file"),
    ("an error reported after the first paint covers a drawn map",
     [(R_MAPLOAD, _text("      return s.drawn ? s : { ...s, error: e.message };", "      return { ...s, error: e.message };"))],
     "map_loading_a_failure_is_an_error_with_a_retry"),
    ("a failed map offers no retry",
     [(R_MAPIND, _text("      {retry && onRetry && <button", "      {false && <button"))],
     "map_indicator_is_a_polite_live_region"),
    ("a failed map does not name the list or table that works without it",
     [(R_MAPIND, _text('{message}{phase === "failed" && alternative ? ` ${alternative}` : ""}', "{message}"))],
     "map_indicator_is_a_polite_live_region"),
    ("the theatre waits for the 2.4 MB line file again",
     [("web/src/data.ts", _text("  loadLines().catch(() => undefined);\n  const [", "  await loadLines();\n  const ["))],
     "theatre_bundle_does_not_wait_for_the_line_network"),
    ("the line file is fetched only when first asked for, after the bundle",
     [("web/src/data.ts", _text("  loadLines().catch(() => undefined);\n  const [", "  const ["))],
     "theatre_bundle_does_not_wait_for_the_line_network"),
    ("a failed line request is kept, so Try again can never work",
     [("web/src/data.ts", _text("    p.catch(() => { if (linesPromise === p) linesPromise = null; });\n", "    p.catch(() => undefined);\n"))],
     "theatre_a_failed_line_file_never_fails_the_dashboard"),
    ("the PNG export does not wait for the lines when their layer is on",
     [("web/src/App.tsx", _text("          lineData = await loadLines();", "          lineData = null;"))],
     "theatre_png_export_waits_for_the_lines"),
    ("the map's loading state is driven by a guess instead of MapLibre's idle event",
     [("web/src/global/SimpleMap.tsx", _text('      if (m.getSource("polys")) dispatch({ type: "idle" });',
                                             '      window.setTimeout(() => dispatch({ type: "idle" }), 2000);'))],
     "map_loading_is_driven_by_real_events"),
]
MUTATIONS += ITER22_FILTER_MUTATIONS


# Iteration 22: the global impact layer (pipeline/global_impacts.py, scripts/import_impacts.py).
# Each breaks ONE rule of the gate, the build or the import; tests/test_iteration22_impacts.py
# must fail. The first group is the gate (methodology §13), the second the build, the third the import.
GI = "pipeline/global_impacts.py"
II = "scripts/import_impacts.py"

ITER22_IMPACT_MUTATIONS = [
    # --- the gate ---
    ('impacts: a coordinate-like key passes',
     [(GI, _text('        if key is not None and set(re.split(r"[^a-z]+", key.lower())) & COORD_KEY_TOKENS:', '        if False:'))],
     'gate_refuses_a_coordinate_like_key_anywhere'),
    ('impacts: a latitude and longitude pair passes',
     [(GI, _text('                    and abs(v[0]) <= 180 and abs(v[1]) <= 180:', '                    and abs(v[0]) <= 180 and abs(v[1]) <= 180 and False:'))],
     'gate_refuses_a_number_pair_that_reads_as_a_position'),
    ('impacts: coordinate text and map links pass',
     [(GI, _text('        if isinstance(v, str) and COORD_TEXT.search(v):', '        if False:'))],
     'gate_refuses_coordinate_text_and_map_links'),
    ('impacts: a kinetic record that is not abstracted passes',
     [(GI, _text('    if attack and policy != ABSTRACTED:', '    if False:'))],
     'gate_refuses_a_kinetic_or_sabotage_record_that_is_not_abstracted'),
    ('impacts: a headline is kept on an abstracted record',
     [(GI, _text('            out.append(f"source {s.get(\'ref\')!r}: a headline on a record published without its place")', '            pass'))],
     'gate_refuses_a_headline_on_an_abstracted_record'),
    ('impacts: an address that states the method passes on an abstracted record',
     [(GI, _text('        if B.method_in_address(url) or ABSTRACTED_ADDRESS_METHOD.search(B.address_words(path)):', '        if False:'))],
     'gate_refuses_method_wording_on_an_abstracted_record_and_in_its_addresses'),
    ('impacts: status wording passes on an abstracted record',
     [(GI, _text('    hit = B.status_wording(_prose(r))', '    hit = None'))],
     'gate_refuses_status_wording_on_an_abstracted_record_and_in_its_addresses'),
    ('impacts: an abstracted id keeps a lane counter or a place name',
     [(GI, _text('    if not iid.startswith(stem) or not re.fullmatch(B.OPAQUE_TOKEN, iid[len(stem):]):', '    if not iid.startswith(stem):'))],
     'gate_refuses_an_abstracted_id_that_is_not_the_keyed_form'),
    ('impacts: a region passes on a record in a campaign system',
     [(GI, _text('        if r.get("admin1") is not None or r.get("geographic_precision") == "admin1":', '        if False:'))],
     'gate_refuses_a_region_on_any_record_in_a_campaign_system'),
    ('impacts: a campaign system region name passes in text',
     [(GI, _text('        if found:', '        if False:'))],
     'gate_refuses_a_campaign_systems_region_name_in_text_or_id'),
    ('impacts: a headline passes in a campaign system',
     [(GI, _text('            out.append(f"a record in a campaign-restricted system ({sid}) carries a headline")', '            pass'))],
     'gate_refuses_a_headline_in_a_campaign_system'),
    ('impacts: route wording passes in an impact record',
     [(GI, _text('        out.append(f"shipping, strait or route wording ({hit.group(0)!r}); it belongs to the regional context only")', '        pass'))],
     'gate_refuses_route_wording_anywhere_in_an_impact_record or gate_refuses_route_wording_in_a_citation_address_or_headline'),
    ('impacts: vessel, route and port wording passes in the regional context',
     [(GI, _text('        hit = CONTEXT_CASED.search(text) or CONTEXT_FORBIDDEN.search(text)', '        hit = None'))],
     'context_gate_refuses_vessel_route_port_dependence_and_naval_wording'),
    ('impacts: the aggregate words are refused in the regional context',
     [(GI, _text('    r"\\bbypass\\w*", r"\\balternat(e|ive) (export )?routes?\\b",', '    r"\\bbypass\\w*", r"\\bshipping\\b", r"\\balternat(e|ive) (export )?routes?\\b",'))],
     'context_gate_allows_the_aggregate_words'),
    ('impacts: an IP address passes',
     [(GI, _text('        if IPV4.search(v) or IPV6.search(v):', '        if False:'))],
     'gate_refuses_ip_addresses_cve_identifiers_and_exploit_wording'),
    ('impacts: a CVE identifier passes',
     [(GI, _text('        if CVE.search(v):', '        if False:'))],
     'gate_refuses_ip_addresses_cve_identifiers_and_exploit_wording'),
    ('impacts: exploit wording passes',
     [(GI, _text('        if key != "url" and EXPLOIT_WORDING.search(v):', '        if False:'))],
     'gate_refuses_ip_addresses_cve_identifiers_and_exploit_wording'),
    ('impacts: a record with no source for occurrence passes',
     [(GI, _text('        out.append("no source supports occurrence")', '        pass'))],
     'gate_refuses_a_record_with_no_source_for_occurrence'),
    ('impacts: a stated effect with no source passes',
     [(GI, _text('            and not backing("effect")):', '            and not backing("effect") and False):'))],
     'gate_refuses_a_stated_effect_with_no_source_for_it'),
    ('impacts: an attribution its sources do not support passes',
     [(GI, _text('    out += EC.attribution_problems(r.get("attribution"), sources)\n', ''))],
     'gate_refuses_an_attribution_its_sources_do_not_support'),
    ('impacts: an AI status with no incident source passes',
     [(GI, _text('    out += EC.ai_problems(r.get("ai_involvement"), sources)\n', ''))],
     'gate_refuses_an_ai_status_without_an_incident_source_or_a_relation'),
    ('impacts: an unverified post is the sole evidence of occurrence',
     [(GI, _text('    elif all(_weak_for_occurrence(s) for s in occurrence):', '    elif False:'))],
     'gate_refuses_an_unofficial_post_as_the_sole_evidence_of_occurrence or every_reject_case_in_the_fixture'),
    ('impacts: a journalist post alone may establish occurrence',
     [(GI, _text('    return s.get("medium") == "social" and (s.get("social") or {}).get("account_tier") not in SOLE_EVIDENCE_TIERS',
                 '    return s.get("medium") == "social" and (s.get("social") or {}).get("account_tier") in ("S3", "S4")'))],
     'gate_refuses_an_unofficial_post_as_the_sole_evidence_of_occurrence'),
    ('impacts: a social source without a tier passes',
     [(GI, _text('                if social.get("account_tier") not in ids("social_tiers"):', '                if False:'))],
     'gate_refuses_a_social_source_without_tier_or_identity_basis'),
    ('impacts: a value without a unit passes',
     [(GI, _text('                out.append(f"{w}: a value without a unit")', '                pass'))],
     'gate_refuses_a_value_without_a_unit_or_without_the_sources_words'),
    ('impacts: an absence written as zero passes',
     [(GI, _text('            if not _number(value) or not math.isfinite(value) or value <= 0:', '            if not _number(value) or not math.isfinite(value) or value < 0:'))],
     'gate_refuses_an_absence_written_as_zero_or_as_an_empty_string'),
    ('impacts: a field outside the contract passes',
     [(GI, _text('    out = _unknown_keys(r, RECORD_FIELDS, "record")', '    out = []'))],
     'gate_refuses_a_field_that_is_not_part_of_the_contract'),
    ('impacts: importance wording about an asset passes in the summary',
     [(GI, _text('    hit = importance_hit(', '    hit = (lambda text: None)('))],
     'gate_refuses_a_claim_of_an_assets_size_or_importance'),
    ('impacts: the allowed phrases are no longer read as absent',
     [(GI, _text('    return IMPORTANCE_WORDING.search(_blank(IMPORTANCE_ALLOWED, text))', '    return IMPORTANCE_WORDING.search(str(text))'))],
     'importance_gate_allows_words_that_say_nothing_about_an_asset'),
    ('impacts: "only" is read just before the noun and nowhere else',
     [(GI, _text("{{0,{int(_IMPORTANCE['only_within_words']) - 1}}}", "{{0,0}}"))],
     'gate_refuses_a_claim_of_an_assets_size_or_importance'),
    ('impacts: every use of the blunt country word list is refused again',
     [(GI, _text('    hit = importance_hit(', '    hit = B.LOADED_WORDING.search('))],
     'importance_gate_allows_words_that_say_nothing_about_an_asset or importance_words_are_data'),
    ('impacts: every tanker is a road tanker',
     [(GI, _text('    return B.ROUTE_WORDING.search(_blank(ROUTE_ALLOWED, text))', '    return None'))],
     'every_other_tanker_is_still_refused'),
    ('impacts: a water tanker is refused as shipping',
     [(GI, _text('    return B.ROUTE_WORDING.search(_blank(ROUTE_ALLOWED, text))', '    return B.ROUTE_WORDING.search(str(text))'))],
     'road_tanker_delivering_water_is_not_shipping'),
    ('impacts: a source may be dateless without saying its page is undated',
     [(GI, _text('        undated = "date" in s and s["date"] is None and s.get("date_basis") == UNDATED and s.get("medium") != "social"',
                 '        undated = "date" in s and s["date"] is None'))],
     'undated_page_is_cited_with_no_date_only_when_it_says_so'),
    ('impacts: a social post may be an undated page',
     [(GI, _text('        undated = "date" in s and s["date"] is None and s.get("date_basis") == UNDATED and s.get("medium") != "social"',
                 '        undated = "date" in s and s["date"] is None and s.get("date_basis") == UNDATED'))],
     'undated_page_is_cited_with_no_date_only_when_it_says_so'),
    ('impacts: a dated source may claim to be undated',
     [(GI, _text('        if s.get("date_basis") is not None and not undated:', '        if False:'))],
     'undated_page_is_cited_with_no_date_only_when_it_says_so'),
    ('impacts: a lead normalisation flag needs no date',
     [(GI, _text('            v.get("lead_normalisation") is not True or not _date_ok(v.get("lead_normalisation_at"))):', '            False):'))],
     'review_block_may_state_a_lead_normalisation_only_with_its_date'),
    ('impacts: an attempt filed as a disruption passes',
     [(GI, _text('            out.append("the stated effect says no service was affected: an attempt is filed as a disruption")', '            pass'))],
     'gate_refuses_an_attempt_filed_as_a_disruption_and_the_reverse'),
    ('impacts: a record with no first_published passes',
     [(GI, _text('    out += [f"no {k}" for k in RECORD_FIELDS if k not in r and k not in OPTIONAL_RECORD_FIELDS]\n', '')),
      (GI, _text('    if first is not None and not _date_ok(first):', '    if False:'))],
     'gate_requires_first_published_and_a_well_formed_id'),
    ('impacts: the safety role need not have accepted',
     [(GI, _text('        if got.get(role) not in B.BLIND_PASS:', '        if got.get(role) not in B.BLIND_PASS and role != "safety":'))],
     'gate_requires_every_review_role_to_have_accepted or context_entries_are_dated_as_of_sourced_and_reviewed'),
    ('impacts: an IT failure may carry any attribution',
     [(GI, _text('        elif (r.get("attribution") or {}).get("status") != "NOT_APPLICABLE":', '        elif False:'))],
     'it_failure_is_the_one_mechanism_on_a_record_that_is_not_cyber'),
    ('impacts: a held or rejected wording passes in the research note',
     [(GI, _text('        if isinstance(v, str) and LOG_FORBIDDEN.search(v):', '        if False:'))],
     'research_note_publishes_process_facts_only'),
    # --- the build ---
    ('impacts: records are ordered by how many sources they have',
     [(GI, _text('    return sorted(sorted(rows, key=lambda r: r[id_key]), key=lambda r: _start(r[key]), reverse=True)',
                 '    return sorted(rows, key=lambda r: len(r.get("sources") or []), reverse=True)'))],
     'records_are_newest_first_then_by_id_and_countries_alphabetical'),
    ('impacts: a count per country is emitted',
     [(GI, _text('    out = {"a3": a3, "name": ctx["names"][a3], "system_id": ctx["system_of"].get(a3)}',
                 '    out = {"a3": a3, "name": ctx["names"][a3], "system_id": ctx["system_of"].get(a3), "record_count": 1}'))],
     'artifact_carries_no_count_per_country_and_no_rankable_field'),
    ('impacts: an attempt is served among the disruptions',
     [(GI, _text('    records = [r for r in served if r["record_kind"] != ATTEMPT]', '    records = list(served)'))],
     'attempts_are_served_apart_and_never_among_the_records'),
    ('impacts: an IT failure is folded into cyber',
     [(GI, _text('    return "it_failure" if r.get("cyber_mechanism") == IT_FAILURE_MECHANISM else None',
                 '    return "cyber" if r.get("cyber_mechanism") == IT_FAILURE_MECHANISM else None'))],
     'it_failure_is_the_one_mechanism_on_a_record_that_is_not_cyber or fixture_exercises_every_branch'),
    ('impacts: every context entry is flagged the latest of its type',
     [(GI, _text('        out["is_latest_of_type"] = e["as_of"] == newest[e["context_type"]]', '        out["is_latest_of_type"] = True'))],
     'context_entries_carry_their_age_and_only_the_newest_of_a_type_is_latest'),
    ('impacts: a record dated after the build date is served',
     [(GI, _text('    known = [r for r in events_doc["records"] if (r["date"] + "-01-01")[:10] <= as_of]', '    known = list(events_doc["records"])'))],
     'record_dated_after_the_build_date_is_not_served'),
    ('impacts: the theatre is given a country system id',
     [(GI, _text('        "system_of": {a3: s["id"] for s in systems.SYSTEMS if s["kind"] == "country" for a3 in s["admin0_a3"]},',
                 '        "system_of": {a3: s["id"] for s in systems.SYSTEMS for a3 in s["admin0_a3"]},'))],
     'each_served_record_adds_what_the_contract_says'),
    ('impacts: an attempt scores an effect it did not have',
     [(GI, _text('    specificity = "vague" if r["record_kind"] == ATTEMPT else r["effect_specificity"]', '    specificity = r["effect_specificity"] or "vague"'))],
     'attempts_confidence_never_scores_an_effect'),
    ('impacts: an analytic module imports the impact layer',
     [('pipeline/explain.py', _prepend('import pipeline.global_impacts  # mutation\n'))],
     'no_analytic_module_imports_the_impact_layer'),
    # --- the import ---
    ('impacts import: a record held from a country system enters',
     [(II, _text('            if entry["outcome"].startswith("refused"):', '            if False:'))],
     'candidate_matching_a_record_held_from_a_country_system_is_refused'),
    ('impacts import: a threshold hold can be overridden',
     [(II, _text('            if ruling is None:\n',
                 '            if ruling is None and kind == "threshold":\n'
                 '                entry["outcome"] = "allowed: the country threshold does not bind this layer"\n'
                 '            elif ruling is None:\n'))],
     'no_hold_from_a_country_system_can_be_overridden_whatever_it_was_for'),
    ('impacts import: the old override file is read as rulings',
     [(II, _text('    ruled_distinct = read_json(queue / "reconcile_distinct.json") if (queue / "reconcile_distinct.json").exists() else {}',
                 '    ruled_distinct = read_json(queue / "reconcile_allow.json") if (queue / "reconcile_allow.json").exists() else {}'))],
     'no_hold_from_a_country_system_can_be_overridden_whatever_it_was_for'),
    ('impacts import: a ruling that a match is a different event needs no reason',
     [(II, _text('            elif not reason:', '            elif False:'))],
     'ruling_without_a_reason_for_another_record_or_under_a_bare_id_changes_nothing'),
    ('impacts import: a ruling under a bare id is honoured',
     [(II, _text('            listed = ruled_distinct.get(item["key"]) or []',
                 '            listed = ruled_distinct.get(item["key"]) or ruled_distinct.get(item["original_id"]) or []'))],
     'ruling_without_a_reason_for_another_record_or_under_a_bare_id_changes_nothing'),
    ('impacts import: an attack record is ruled distinct from a held country record',
     [(II, _text('            elif G.is_attack(record):', '            elif False:'))],
     'attack_record_can_never_be_ruled_distinct'),
    ('impacts import: the lead patch need not be accept_with_correction',
     [(II, _text('    if patch.get("verdict") != "accept_with_correction":', '    if False:'))],
     'lead_patch_that_oversteps_refuses_the_record'),
    ('impacts import: a lead patch may carry sources_opened',
     [(II, _text('    extra = sorted(set(patch) - set(LEAD_KEYS))', '    extra = []'))],
     'lead_patch_that_oversteps_refuses_the_record'),
    ('impacts import: a source the lead appends keeps the opened flag the patch gave it',
     [(II, _text('        new = {**copy.deepcopy(src), "opened": False, "added_by": "lead"}', '        new = {**copy.deepcopy(src), "added_by": "lead"}'))],
     'lead_patch_can_append_a_source_never_opened'),
    ('impacts import: a source the lead appends skips the source validators',
     [(II, _text('        found = G.source_problems([new])', '        found = []'))],
     'source_the_lead_appends_runs_through_every_source_validator'),
    ('impacts import: a source the lead appends may take an existing or removed ref',
     [(II, _text('        if ref in used:', '        if False:'))],
     'source_the_lead_appends_runs_through_every_source_validator or cannot_reuse_the_ref_of_a_source_it_removes'),
    ('impacts build: the address of an abstracted record may say the attack was a strike',
     [(GI, _text('        if B.method_in_address(url) or ABSTRACTED_ADDRESS_METHOD.search(B.address_words(path)):',
                 '        if B.method_in_address(url):'))],
     'method_wording_on_an_abstracted_record_and_in_its_addresses'),
    ('impacts import: a held record keeps the name a reviewer gave it in the curated file',
     [(II, _text('                    known_ids.add(str(shape(trial, original_id, key, False, [])["impact_id"]))',
                 '                    pass'))],
     'served_under_a_reviewers_or_the_leads_name_and_then_held_is_withdrawn'),
    ('impacts build: a served research note may speak in the first person or name a tool, a file or a lane',
     [(GI, _text('            hit = LOG_PROCESS_WORDING.search(str(f.get(k) or ""))', '            hit = None'))],
     'research_note_refuses_first_person_and_pipeline_wording'),
    ('evidence confidence: a source the lead added counts as a reviewed independent origin',
     [("pipeline/evidence_confidence.py", _text('        origin_count = min(origin_count, reviewed_only)', '        pass'))],
     'source_the_lead_added_is_never_counted_as_a_reviewed_origin'),
    ('impacts import: a source the lead appends is not marked as the lead\'s',
     [(II, _text('        new = {**copy.deepcopy(src), "opened": False, "added_by": "lead"}', '        new = {**copy.deepcopy(src), "opened": False}'))],
     'lead_patch_can_append_a_source_never_opened'),
    ('impacts import: a lead patch gives a record a region',
     [(II, _text('    if reviewed.get("admin1") is None and r.get("admin1") is not None:', '    if False:'))],
     'lead_patch_that_oversteps_refuses_the_record'),
    ('impacts import: a lead patch changes the cause of an attack',
     [(II, _text('    if G.is_attack(reviewed) and (not G.is_attack(r) or ', '    if False and (not G.is_attack(r) or '))],
     'lead_patch_cannot_change_an_attacks_cause'),
    ('impacts import: a lead patch weakens the publication policy',
     [(II, _text('    if reviewed.get("publication_policy") == G.ABSTRACTED and r.get("publication_policy") != G.ABSTRACTED:', '    if False:'))],
     'lead_patch_cannot_change_an_attacks_cause'),
    ('impacts import: a lead patch marks a source opened',
     [(II, _text('            src["opened"] = opened.get(src.get("ref"), False)', '            pass'))],
     'lead_patch_cannot_mark_a_source_opened'),
    ('impacts import: the lead patches a record before the roles have accepted it',
     [(II, _text('            why = review_state(verdicts, ROLE_ORDER)\n            if why:',
                 '            why = review_state(verdicts, ROLE_ORDER)\n            if why and lead_patch(reviews, lane, original_id)[0] is None:'))],
     'leads_normalisation_cannot_rescue_a_record_a_role_rejected'),
    ('impacts import: the lead normalisation is not stated in the review block',
     [(II, _text('    lead = {"lead_normalisation": True, "lead_normalisation_at": lead_at} if lead_at else {}', '    lead = {}'))],
     'leads_normalisation_applies_after_safety or leads_normalisation_works_for_context_entries'),
    ('impacts import: the lead normalisation is not read for context entries',
     [(II, _text('            patch, lead_at = lead_patch(reviews, lane, cid) if not why else (None, None)', '            patch, lead_at = None, None'))],
     'leads_normalisation_works_for_context_entries'),
    ('impacts import: a lead file needs no date',
     [(II, _text('    if not G._date_ok(patched_at):', '    if False:'))],
     'lead_file_without_a_date_refuses_its_patches'),
    ('impacts import: an abstracted energy record keeps a null technology',
     [(II, _text('            r["technology"] = "withheld"', '            pass'))],
     'abstracted_energy_record_that_names_no_technology_says_it_is_withheld'),
    ('impacts import: every energy record without a technology is called withheld',
     [(II, _text('        if r.get("domain") == "energy" and r.get("technology") is None:\n            # An energy record names',
                 '        pass\n    if r.get("domain") == "energy" and r.get("technology") is None:\n        if True:\n            # An energy record names'))],
     'abstracted_energy_record_that_names_no_technology_says_it_is_withheld'),
    ('impacts import: an empty end date is left for the gate',
     [(II, _text('    if r.get("date_end") in G.ABSENCE or r.get("date_end") == "":', '    if r.get("date_end") in G.ABSENCE:'))],
     'empty_or_unknown_end_date_is_written_as_null'),
    ('impacts import: UNKNOWN attribution on a storm is left as it is',
     [(II, _text('        a["status"], a["actor"], a["actor_type"] = "NOT_APPLICABLE", None, None', '        pass'))],
     'unknown_attribution_on_a_cause_that_is_not_malicious'),
    ('impacts import: UNKNOWN is rewritten on a cause nobody established',
     [(II, _text('and r.get("cause_family") in G.NOT_MALICIOUS', 'and r.get("cause_family") not in G.MALICIOUS'))],
     'unknown_attribution_on_a_cause_that_is_not_malicious'),
    ('impacts import: a competing attribution with no surviving source is kept',
     [(II, _text('        kept = [c for c in a["competing"] if not isinstance(c, dict) or c.get("source_refs")]', '        kept = list(a["competing"])'))],
     'competing_attribution_whose_source_did_not_survive'),
    ('impacts import: addenda of a held duplicate are lost',
     [(II, _text('                for held_key in duplicates_of.get(item["key"], []):', '                for held_key in []:'))],
     'addenda_of_a_copy_held_as_a_duplicate_go_to_the_record_that_survives'),
    ('impacts import: the same address is cited twice',
     [(II, _text('                    if why is None and any(s.get("url") == src.get("url") for s in base["sources"]):', '                    if False:'))],
     'addenda_of_a_copy_held_as_a_duplicate_go_to_the_record_that_survives'),
    ('impacts import: addenda move from any held record',
     [(II, _text('                if hold_survivor(hold):\n                    duplicates_of.setdefault(hold_survivor(hold), []).append(item["key"])',
                 '                for other in [x["key"] for x in accepted]:\n                    duplicates_of.setdefault(other, []).append(item["key"])'))],
     'addenda_of_a_held_copy_stay_put_when_the_hold_names_no_survivor'),
    ('impacts import: a moved addendum needs no accepting review',
     [(II, _text('        why = "not reviewed" if not verdicts else review_state(verdicts, ADDENDA_ROLES)',
                 '        why = None if moved else ("not reviewed" if not verdicts else review_state(verdicts, ADDENDA_ROLES))'))],
     'addenda_of_a_held_copy_stay_put_when_the_hold_names_no_survivor'),
    ('impacts import: a review role name counts as a safety hold',
     [(II, _text('            parts += [r[k].get("reason"), r[k].get("note"), r[k].get("outcome")]',
                 '            parts += [r[k].get("reason"), r[k].get("note"), r[k].get("outcome"), json.dumps(r[k].get("roles"))]'))],
     'hold_is_classified_from_its_reasons_not_from_the_names_of_the_review_roles'),
    ('impacts import: first_published is restamped on a rerun',
     [(II, _text('    out["first_published"] = served\n', '    out["first_published"] = served if old is None else date\n'))],
     'import_is_idempotent_and_never_restamps'),
    ('impacts import: a changed record gets no last_revised',
     [(II, _text('        if body(new) != body(old):', '        if False:'))],
     'changed_record_keeps_first_published_and_gains_last_revised'),
    ('impacts import: a safety reject is ignored',
     [(II, _text('        if v == "reject":', '        if v == "reject" and role != "safety":'))],
     'role_that_did_not_review_or_rejected_stops_the_record'),
    ('impacts import: a role that did not review is not required',
     [(II, _text('    missing = [role for role in roles if role not in verdicts]', '    missing = []; roles = [role for role in roles if role in verdicts]'))],
     'role_that_did_not_review_or_rejected_stops_the_record'),
    ('impacts import: dedupe across lanes is disabled',
     [(II, _text('    for group in duplicate_groups([i for i in accepted if "refused" not in i], distinct):', '    for group in []:'))],
     'same_event_filed_by_two_lanes_is_refused_until_a_reviewer_chooses'),
    ('impacts import: the safety patch is applied first, not last',
     [(II, _text('ROLE_ORDER = ("evidence", "attribution_source", "safety")', 'ROLE_ORDER = ("safety", "attribution_source", "evidence")'))],
     'patches_apply_in_role_order_and_safety_wins'),
    ('impacts import: opened is what the lane wrote',
     [(II, _text('        s["opened"] = (s.get("ref") in listed) if isinstance(listed, list) else s.get("opened") is True',
                 '        s["opened"] = s.get("opened") is True or (isinstance(listed, list) and s.get("ref") in listed)'))],
     'opened_is_what_the_evidence_reviewer_opened_whatever_the_lane_wrote'),
    ('impacts import: the abstracted id is an unkeyed hash',
     [(II, _text('    tag = hmac.new(key, f"impact|{original_id}".encode("utf-8"), hashlib.sha256).hexdigest()[:6]\n    return f"{G.abstracted_stem(record)}{tag}"',
                 '    tag = hashlib.sha256(f"impact|{original_id}".encode("utf-8")).hexdigest()[:6]\n    return f"{G.abstracted_stem(record)}{tag}"'))],
     'attack_record_is_abstracted_and_given_a_keyed_id or keyed_id_is_not_a_plain_hash'),
    ('impacts import: a reviewer rename replaces the keyed id of an attack record',
     [(II, _text('        r["impact_id"] = abstract_id(r, original_id, key)', '        pass'))],
     'attack_record_is_abstracted_and_given_a_keyed_id'),
    ('impacts import: an attack record keeps its region',
     [(II, _text('        r["geographic_precision"] = "country"\n        r["admin1"] = None\n        r["episode_id"]', '        r["episode_id"]'))],
     'attack_record_is_abstracted_and_given_a_keyed_id'),
    ('impacts import: the build gate is not run on what is imported',
     [(II, _text('        return stamped, G.one_record_problems(stamped, ctx)', '        return stamped, []'))],
     'import_runs_the_builds_gate_and_writes_contract_fields_only'),
    ('impacts import: a rename may collide with another record',
     [(II, _text('        if clash:', '        if False:'))],
     'rename_that_collides_with_another_record_is_refused'),
    ('impacts import: a record that stops being accepted stays published',
     [(II, _text('    kept = {rid: r for rid, r in existing.items() if rid not in known_ids}', '    kept = dict(existing)'))],
     'record_that_stops_being_accepted_is_withdrawn'),
    ('impacts import: the research note keeps a family that speaks of held work',
     [(II, _text('            problems = [p for p in G.log_problems({**out, "source_families": [entry]}) if p not in standing]', '            problems = []'))],
     'research_note_takes_process_facts_only_from_each_lane_log'),
    ('impacts import: a lead hold is ignored',
     [(II, _text('            if hold is not None:', '            if False:'))],
     'lead_hold_refuses_a_record_whatever_the_reviewers_said'),
    ('impacts import: an unreviewed social addendum is added',
     [(II, _text('        why = "not reviewed" if not verdicts else review_state(verdicts, ADDENDA_ROLES)',
                 '        why = None if not verdicts else review_state(verdicts, ADDENDA_ROLES)'))],
     'social_addendum_is_added_only_when_every_role_accepted_it'),
    ('impacts import: a dry run writes the curated files',
     [(II, _text('    if write:', '    if True:'))],
     'dry_run_reports_everything_and_writes_nothing'),
    ('impacts import: a removed or narrowed source keeps its citations',
     [(II, _text('    prune_refs(r, {s.get("ref") for s in sources}, {s.get("ref"): tuple(s.get("supports") or ()) for s in sources})', '    pass'))],
     'citation_the_reviewers_narrowed_is_no_longer_cited or removed_source_takes_its_citations_with_it'),
    ('impacts import: a context entry needs one role only',
     [(II, _text('            why = review_state(verdicts, CONTEXT_ROLES)', '            why = None'))],
     'context_entries_need_two_roles_and_pass_the_context_gate'),
]
MUTATIONS += ITER22_IMPACT_MUTATIONS


# Iteration 22: the Impact Atlas and the shared impact components (web/src/global/impacts/). Each
# mutant breaks one rule of the impact layer's frontend and is caught by tests/test_iteration22_atlas.py,
# which runs the shipped TypeScript in Node against the pipeline's synthetic corpus as it is served.
IMP = "web/src/global/impacts/"
ITER22_ATLAS_MUTATIONS = [
    ("an AI line is rendered when no source reports AI",
     [(IMP + "model.ts", _text('  return !!ai && !!ai.status && ai.status !== "NONE_REPORTED";', '  return !!ai && !!ai.status;'))],
     "atlas_ai_line_never_renders_for_none_reported"),
    ("AI-assisted is described as AI as operational cause",
     [(IMP + "AiLine.tsx", _text('  ai_assisted: "not AI-caused",', '  ai_assisted: "AI as operational cause",'))],
     "atlas_ai_assisted_is_never_merged_with_ai_as_operational_cause"),
    ("unknown attribution falls through to the line a named actor gets",
     [(IMP + "AttributionLine.tsx", _text('  if (a.status === "UNKNOWN") {', '  if (false) {'))],
     "atlas_unknown_attribution_never_renders_as_low_confidence"),
    ("unknown attribution is given a confidence level",
     [(IMP + "model.ts", _text(
         '  if (!a.confidence || a.status === "UNKNOWN" || a.status === "NOT_APPLICABLE" || a.confidence === "NOT_ESTABLISHED") return null;',
         '  if (!a.confidence) return null;'))],
     "atlas_unknown_attribution_never_renders_as_low_confidence"),
    ("not-applicable attribution renders a line",
     [(IMP + "AttributionLine.tsx", _text('  if (a.status === "NOT_APPLICABLE") {', '  if (false) {'))],
     "atlas_not_applicable_attribution_renders_nothing"),
    ("a disputed attribution shows only its first competing attribution",
     [(IMP + "AttributionLine.tsx", _text('            {a.competing.map((c, i) => (', '            {a.competing.slice(0, 1).map((c, i) => ('))],
     "atlas_disputed_attribution_lists_every_competing_attribution"),
    ("an attempt filed among the records enters the timeline",
     [(IMP + "model.ts", _text('  return payload.records.filter((r) => r.record_kind === DISRUPTION);', '  return payload.records;'))],
     "atlas_attempts_never_enter_the_timeline_or_the_count"),
    ("an attempt's country is marked on the presence map",
     [(IMP + "atlasModel.ts", _text('    if (r.record_kind !== "disruption") continue;\n', ''))],
     "atlas_attempts_never_enter_the_timeline_or_the_count"),
    ("the corpus count includes attempts",
     [(IMP + "atlasModel.ts", _text('    records: records.length,', '    records: records.length + (payload.attempts ?? []).length,'))],
     "atlas_attempts_never_enter_the_timeline_or_the_count"),
    ("a country's impact list returns its attempts",
     [(IMP + "load.ts", _text('    if (r.record_kind !== "disruption") return false;\n', ''))],
     "atlas_attempts_never_enter_the_timeline_or_the_count"),
    ("the presence map keeps one entry per record, so it can weigh a country",
     [(IMP + "atlasModel.ts", _text('  return [...seen].sort();\n}\n\n/** The map\'s fill', '  return records.flatMap(countryCodes).sort();\n}\n\n/** The map\'s fill'))],
     "atlas_presence_map_never_encodes_a_count"),
    ("the presence map gains a second, stronger mark colour",
     [(IMP + "atlasModel.ts", _text(
         '  return ["case", ["in", ["get", "a3"], ["literal", [...codes]]], PRESENCE_MARK, PRESENCE_NONE];',
         '  return ["case", ["in", ["get", "a3"], ["literal", codes.slice(0, 3)]], "#b8382f", ["in", ["get", "a3"], ["literal", [...codes]]], PRESENCE_MARK, PRESENCE_NONE];'))],
     "atlas_presence_map_never_encodes_a_count"),
    ("the country filter prints a count beside each country",
     [(IMP + "atlasModel.ts", _text('           countryCodes, { counts: false }),', '           countryCodes),'))],
     "atlas_counts_are_never_per_country"),
    ("the atlas's country list leaves the served alphabetical order",
     [(IMP + "atlasModel.ts", _text('  return all.filter((c) => seen.has(c.a3));', '  return all.filter((c) => seen.has(c.a3)).reverse();'))],
     "atlas_counts_are_never_per_country"),
    ("grouping the timeline by month re-sorts it",
     [(IMP + "atlasModel.ts", _text('  for (const r of records) {\n    const ym = startDay(r).slice(0, 7);', '  for (const r of [...records].reverse()) {\n    const ym = startDay(r).slice(0, 7);'))],
     "atlas_timeline_grouping_never_reorders"),
    ("an IT failure counts as cyber",
     [(IMP + "model.ts", _text('  return r.cause_family === "cyber";\n}', '  return r.cause_family === "cyber" || r.cyber_mechanism != null;\n}'))],
     "atlas_cyber_presets_never_include_an_it_failure"),
    ("the cyber-mechanism filter folds IT failures in",
     [(IMP + "atlasModel.ts", _text('(r) => (r.cyber_mechanism && !isItFailure(r) ? [r.cyber_mechanism] : [])),', '(r) => (r.cyber_mechanism ? [r.cyber_mechanism] : [])),'))],
     "atlas_cyber_presets_never_include_an_it_failure"),
    ("the IT failure preset is the cyber filter under another name",
     [(IMP + "atlasModel.ts", _text('{ id: "it-failure", label: "IT failure", choices: { it: [IT_FAILURE_VALUE] },', '{ id: "it-failure", label: "IT failure", choices: { cause: ["cyber"] },'))],
     "atlas_cyber_presets_never_include_an_it_failure"),
    ("a preset quietly hides low-confidence records",
     [(IMP + "atlasModel.ts", _text('{ id: "cyber", label: "Cyber", choices: { ...cyber },', '{ id: "cyber", label: "Cyber", choices: { ...cyber, conf: ["HIGH", "MODERATE"] },'))],
     "atlas_default_view_shows_every_record_and_no_preset_filters_on_confidence"),
    ("an abstracted record shows its region",
     [(IMP + "model.ts", _text('  if (!isAbstracted(r) && r.admin1?.name) return', '  if (r.admin1?.name) return'))],
     "atlas_abstracted_record_shows_no_place_and_no_headline"),
    ("an abstracted record's inspector shows source headlines",
     [(IMP + "ImpactInspector.tsx", _text('  const headlines = !isAbstracted(r);', '  const headlines = true;'))],
     "atlas_abstracted_record_shows_no_place_and_no_headline"),
    ("a kinetic record is abstracted only if its policy field says so",
     [(IMP + "model.ts", _text('  return isAbstractedImpact(r);', '  return r.publication_policy === "country_abstracted";'))],
     "atlas_abstracted_record_shows_no_place_and_no_headline"),
    ("the inspector lists every source under every claim",
     [(IMP + "model.ts", _text('sources: r.sources.filter((s) => s.supports.includes(claim)) }));', 'sources: r.sources }));'))],
     "atlas_inspector_says_which_source_supports_which_claim"),
    ("the confidence score is called a probability",
     [(IMP + "ConfidenceChip.tsx", _text(': ordinal score, not a probability and not a share of a maximum.', ': the probability that the report is right.'))],
     "atlas_confidence_is_words_with_the_served_caveat"),
    ("an absent evidence confidence renders as the lowest category",
     [(IMP + "model.ts", _text('  if (!c || c.category == null) return NOT_ASSESSED_LABEL;', '  if (!c || c.category == null) return "Preliminary";'))],
     "atlas_confidence_is_words_with_the_served_caveat or atlas_not_assessed_confidence_is_its_own_state"),
    ("a not-assessed record's chip drops its reason",
     [(IMP + "ConfidenceChip.tsx", _text('        <span className="conf-reason small">{value?.reason ?? NO_CONFIDENCE_REASON}</span>\n', ''))],
     "atlas_not_assessed_confidence_is_its_own_state_with_its_reason"),
    ("not-assessed records are filed under Preliminary in the filter",
     [(IMP + "model.ts", _text('  return c?.category ?? NOT_ASSESSED;', '  return c?.category ?? "PRELIMINARY";'))],
     "atlas_not_assessed_confidence_is_its_own_state_with_its_reason"),
    ("the confidence filter has no bucket for not-assessed records",
     [(IMP + "atlasModel.ts", _text('    out.push({ value: NOT_ASSESSED, label: NOT_ASSESSED_LABEL });\n', ''))],
     "atlas_not_assessed_confidence_is_its_own_state_with_its_reason"),
    ("a null confidence category is accepted without its reason",
     [(IMP + "load.ts", _text('  if (c.category == null) return !isStr(c.reason) || c.reason.trim() === "";', '  if (c.category == null) return false;'))],
     "atlas_not_assessed_confidence_is_its_own_state_with_its_reason"),
    ("counted publishers are called originating statements",
     [(IMP + "model.ts", _text('  if (basis === "publishers") return', '  if (basis === "publishers_never") return'),),
      (IMP + "model.ts", _text('  if (basis === "reviewed") return', '  if (basis === "reviewed" || basis === "publishers") return'))],
     "atlas_origins_are_worded_by_their_served_basis"),
    ("a count with no served basis is called originating statements",
     [(IMP + "model.ts", _text('  return String(count);\n}', '  return `${count} independent originating statements`;\n}'))],
     "atlas_origins_are_worded_by_their_served_basis"),
    ("the inspector words the citation count itself, whatever the basis",
     [(IMP + "ImpactInspector.tsx", _text(
         '{originsText(r.origin_count, originsBasis)}.', '{r.origin_count} originating statements. Republications count once.'))],
     "atlas_origins_are_worded_by_their_served_basis"),
    ("the score is shown out of a hundred",
     [(IMP + "ConfidenceChip.tsx", _text('<span className="mono">{value.score} points</span>', '<span className="mono">{value.score}/100 points</span>'))],
     "atlas_confidence_is_words_with_the_served_caveat"),
    ("a provisional method's status is not shown",
     [(IMP + "ConfidenceChip.tsx", _text('      {method?.status && <p className="conf-status">Method status: {method.status}.</p>}\n', ''))],
     "atlas_confidence_explainer_shows_a_provisional_method_status"),
    ("the cause filter is a fixed list",
     [(IMP + "atlasModel.ts", _text(
         'choice("cause", "Cause family", options(v.cause_families), (r) => [r.cause_family]),',
         'choice("cause", "Cause family", options(v.cause_families).filter((o) => ["kinetic", "cyber", "sabotage", "industrial_technical", "natural_hazard", "supply_shortfall", "civil_disruption", "unknown"].includes(o.value)), (r) => [r.cause_family]),'))],
     "atlas_a_new_cause_family_needs_no_code_change"),
    ("the regional context loses its fixed caveat",
     [(IMP + "ContextTimeline.tsx", _text('        <p><strong>{CONTEXT_CAVEAT}</strong></p>\n', ''))],
     "atlas_context_timeline_keeps_its_caveat_and_has_no_status_flag"),
    ("an older context statement is shown as the latest",
     [(IMP + "ContextTimeline.tsx", _text('latestOfType={latest.has(e) ? counts.get(e.context_type) ?? 1 : 0}', 'latestOfType={counts.get(e.context_type) ?? 1}'))],
     "atlas_context_timeline_keeps_its_caveat_and_has_no_status_flag"),
    ("the context timeline trusts the file's order",
     [(IMP + "ContextTimeline.tsx", _text(
         '  const entries = [...ctx.entries].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : a.id < b.id ? -1 : 1));',
         '  const entries = [...ctx.entries];'))],
     "atlas_context_timeline_keeps_its_caveat_and_has_no_status_flag"),
    ("the home route prefetches the impact corpus",
     [("web/src/global/prefetch.ts", _text(
         '    quiet(loadWorld());\n    quiet(loadContext());\n  } else if (route.view === "country") {',
         '    quiet(loadWorld());\n    quiet(loadContext());\n    quiet(import("./impacts/load").then((m) => m.loadImpacts()));\n  } else if (route.view === "country") {'))],
     "atlas_home_route_never_requests_the_impact_corpus"),
    ("?view=impacts no longer opens the atlas",
     [("web/src/global/router.ts", _text(
         '  if ((p.get("view") ?? "").trim().toLowerCase() === IMPACTS_VIEW) return { view: "impacts" };\n', ''))],
     "atlas_home_route_never_requests_the_impact_corpus"),
    ("the atlas is imported eagerly by the route switch",
     [("web/src/Root.tsx", _text(
         'const ImpactAtlas = lazy(() => import("./global/impacts/ImpactAtlas"));',
         'import ImpactAtlasEager from "./global/impacts/ImpactAtlas";\nconst ImpactAtlas = ImpactAtlasEager;'))],
     "atlas_home_code_never_includes_the_atlas_or_its_loader"),
    ("the home page loads the impact corpus itself",
     [("web/src/global/GlobalHome.tsx", _text(
         'import { loadContext, type EnergyContext } from "./context";',
         'import { loadContext, type EnergyContext } from "./context";\nimport { loadImpacts } from "./impacts/load";\nvoid loadImpacts();'))],
     "atlas_home_code_never_includes_the_atlas_or_its_loader"),
    ("a search link drifts from the preset it names",
     [("web/src/global/searchIndex.ts", _text('action: { type: "href", href: "?view=impacts&f.cause=cyber" } }),', 'action: { type: "href", href: "?view=impacts&f.mech=ransomware" } }),'))],
     "atlas_search_addresses_open_the_matching_presets"),
]
MUTATIONS += ITER22_ATLAS_MUTATIONS
# Iteration 22, Evidence Confidence v2 (tests/test_iteration22_confidence.py) and the record-level
# What's new (tests/test_iteration22_whats_new.py). The model's promises are that links are not
# corroboration, a claim is only a claim, "nobody knows who" is not a low score, and none of it
# reaches the theatre's scoring multiplier; each mutant breaks one of them.
EC_PY = "pipeline/evidence_confidence.py"
EC_JSON = "methodology/evidence_confidence.json"
ITER22_CONFIDENCE_MUTATIONS = [
    ("a second citation from one origin raises the score",
     [(EC_PY, _text("    origin_count = independent_origins(strong)\n", "    origin_count = len(strong)\n"))],
     "second_citation_from_the_same_origin or three_releases_from_one_utility or one_origin_on_the_publishers_basis"),
    ("citation count replaces origin count",
     [(EC_PY, _text("    return len({find(i) for i in range(len(counted))})", "    return len(counted)"))],
     "source_count_never_enters"),
    ("one publisher's website and its account are two origins",
     [(EC_PY, _text('    if _publisher_key(source):\n        keys.add(("publisher", _publisher_key(source)))\n', ""))],
     "one_publisher_on_two_sites"),
    ("an anonymous post counts as the organisation it names",
     [(EC_JSON, _text('"S3": "researcher_social", "S4": "unverified"', '"S3": "researcher_social", "S4": "by_role"'))],
     "anonymous_account_never_counts"),
    ("an unverified claim is worth ninety points",
     [(EC_JSON, _text('"unverified": {"points": 4,', '"unverified": {"points": 90,'))],
     "case_03 or self_claim_alone_cannot_support_occurrence"),
    ("an official source is no longer direct",
     [(EC_JSON, _text('"operator": "direct", "government": "direct"', '"operator": "secondary", "government": "direct"'))],
     "official_source_alone_beats or case_02"),
    ("conflicting sources still read High",
     [(EC_PY, _text('for a in (_claims_of(s, "disputes") or []))', "for a in [])"))],
     "case_06 or recorded_as_disputing"),
    ("a recorded dispute is ignored",
     [(EC_PY, _text("    disputed = _disputed(sources, dispute)", "    disputed = False"))],
     "dispute_overrides_the_score"),
    ("an anonymous denial makes a record disputed",
     [(EC_PY, _text('    return any(tier_of(s) in METHOD["corroborating_tiers"]\n               and any(a in',
                    "    return any(True\n               and any(a in"))],
     "recorded_as_disputing"),
    ("a dispute about attribution disputes the event",
     [(EC_PY, _text('        if not about or any(a in ("occurrence", "effect") for a in about):', "        if True:"))],
     "dispute_about_who_did_it"),
    ("UNKNOWN attribution reads as LOW",
     [(EC_PY, _text('    if status == "UNKNOWN":\n        return "NOT_ESTABLISHED"', '    if status == "UNKNOWN":\n        return "LOW"'))],
     "unknown_attribution_is_not_established or case_08"),
    ("a claim can be ATTRIBUTED",
     [(EC_PY, _text('        if status == "ATTRIBUTED" and not bases & set(cfg["official_bases"]):', "        if False:"))],
     "attributed_without_an_official_basis or case_04"),
    ("a source typed as the actor's claim is no longer a claim",
     [(EC_PY, _text('    return (source.get("source_role") == "actor_self_claim"\n            or source.get("attribution_basis")',
                    '    return (False\n            or source.get("attribution_basis")'))],
     "self_claim_alone_cannot_exceed"),
    ("a self-claim alone reads as LOW",
     [(EC_PY, _text('        return "CLAIM_ONLY" if claims else "NOT_ESTABLISHED"', '        return "LOW" if claims else "NOT_ESTABLISHED"'))],
     "self_claim_alone_cannot_exceed or case_04"),
    ("press restating an attribution corroborates it",
     [(EC_PY, _text('    return (source.get("source_role") not in METHOD["attribution"]["restating_roles"]\n'
                    '            or bool(source.get("attribution_basis")))', "    return True"))],
     "news_coverage_restating"),
    ("an anonymous post attributes",
     [(EC_PY, _text('    if origin_of(source) is None or tier == "unverified":\n        return None',
                    "    if origin_of(source) is None:\n        return None"))],
     "anonymous_post_or_a_discovery_aid_attributes"),
    ("an AI claim becomes CONFIRMED",
     [(EC_PY, _text('    if status == "CONFIRMED" and "direct" not in tiers:', "    if False:"))],
     "confirmed_ai_needs_a_direct_source"),
    ("an AI status needs no incident-specific source",
     [(EC_PY, _text("    if not backing:\n        out.append(f\"ai_involvement is {status} with no source",
                    "    if False:\n        out.append(f\"ai_involvement is {status} with no source"))],
     "ai_status_without_an_incident_specific_source or case_10"),
    ("NONE_REPORTED may carry a role",
     [(EC_PY, _text('        if backing or a.get("relation") or a.get("role"):', "        if backing:"))],
     "none_reported_with_a_role"),
    ("an anonymous post is sole evidence of AI involvement",
     [(EC_PY, _text('    if backing and tiers <= {"unverified"} and not (', "    if False and not ("))],
     "never_the_sole_evidence_of_ai"),
    ("an aggregator counts as an origin",
     [(EC_JSON, _text('"dataset": "secondary", "aggregator": "secondary"', '"dataset": "secondary", "aggregator": "independent"'))],
     "aggregator_or_a_discovery_aid"),
    ("a discovery aid counts as independent reporting",
     [(EC_PY, _text('    if origin_of(source) is None:\n        return "secondary"\n    role = source.get("source_role")',
                    '    role = source.get("source_role")'))],
     "aggregator_or_a_discovery_aid"),
    ("a dataset is promoted to direct in code",
     [(EC_PY, _text('    return METHOD["role_tier"].get(role, "secondary")',
                    '    return "direct" if role == "dataset" else METHOD["role_tier"].get(role, "secondary")'))],
     "dataset_restating_others"),
    ("the unverified cap is removed",
     [(EC_PY, _text('    if best in (None, "researcher_social", "unverified"):\n        category = _category(',
                    "    if False:\n        category = _category("))],
     "unverified_cap_holds"),
    ("the High threshold is moved",
     [(EC_JSON, _text('{"id": "HIGH", "min": 78,', '{"id": "HIGH", "min": 70,'))],
     "case_02 or follow_the_published_thresholds"),
    ("the Limited threshold is moved",
     [(EC_JSON, _text('{"id": "LIMITED", "min": 35,', '{"id": "LIMITED", "min": 50,'))],
     "case_09 or follow_the_published_thresholds"),
    ("the contemporaneous window is widened to forever",
     [(EC_JSON, _text('"contemporaneous_days": 30', '"contemporaneous_days": 100000'))],
     "contemporaneous_is_within_thirty_days"),
    ("a forecast counts as reported at the time",
     [(EC_PY, _text("    return start - dt.timedelta(days=1) <= cited <= stop + dt.timedelta(", "    return cited <= stop + dt.timedelta("))],
     "contemporaneous_is_within_thirty_days"),
    ("a platform badge establishes identity",
     [(EC_JSON, _text('"badge_words": ["badge", "badged", "verified", "verification", "blue",', '"badge_words": ["badged", "verification",'))],
     "official_tier_without_an_established_identity"),
    ("an official tier needs no established identity",
     [(EC_PY, _text('        if not _identity_established(social):\n            return "unverified"\n', ""))],
     "official_tier_without_an_established_identity"),
    ("a secondary source establishes the effect",
     [(EC_PY, _text('    effect_backed = any(_supports(s, "effect") for s in strong)',
                    '    effect_backed = any(_supports(s, "effect") for s in backing)'))],
     "aggregator_or_a_discovery_aid"),
    ("a source nobody recorded opening earns the opened points",
     [(EC_PY, _text('any(s.get("opened") is True for s in strong)', 'any(s.get("opened") is not False for s in strong)'))],
     "only_a_source_a_reviewer_opened"),
    ("an attribution source counts toward occurrence",
     [(EC_PY, _text('    backing = [s for s in sources if _supports(s, "occurrence") or _supports(s, "effect")]\n    basis = ',
                    "    backing = list(sources)\n    basis = "))],
     "supports_only_attribution or case_05"),
    ("a fourth origin keeps adding points",
     [(EC_PY, _text('METHOD["origin_points"][str(min(origin_count, 3))] if origin_count else 0',
                    'METHOD["origin_points"]["3"] * origin_count // 3 if origin_count else 0'))],
     "two_independent_credible_origins"),
    ("a facility's size reads as a quantified effect",
     [("pipeline/build_systems.py", _text(
         '    return "quantified" if has_figure and cap.get("measure") != "facility_size" else "described"',
         '    return "quantified" if has_figure else "described"'))],
     "quantified_only_by_a_figure"),
    ("the country summary drops a category with no records",
     [("pipeline/build_systems.py", _text("    by = {c: 0 for c in evidence_confidence.CATEGORIES}\n", "    by = {}\n"))],
     "gains_evidence_confidence_and_keeps_every_other_field"),
    ("the theatre index imports evidence confidence",
     [("pipeline/build_index.py", _prepend("from pipeline import evidence_confidence  # noqa: F401\n"))],
     "never_imports_evidence_confidence"),
    ("the theatre's probable weight is changed",
     [("methodology/scoring.json", _text('    "probable": 0.75,', '    "probable": 0.8,'))],
     "confidence_multiplier_is_byte_for_byte_unchanged"),
    ("the theatre weight reads the v2 category",
     [("pipeline/build_index.py", _text(
         '    conf = SCORING["confidence_weights"].get(incident.get("confidence") or "possible", 0.45)',
         '    conf = (0.2 if (incident.get("evidence_confidence") or {}).get("category") == "PRELIMINARY" else\n'
         '            SCORING["confidence_weights"].get(incident.get("confidence") or "possible", 0.45))'))],
     "ignores_a_v2_category or byte_for_byte_unchanged"),
    ("the shadow study leaves its substituted weights in place",
     [("scripts/confidence_shadow_study.py", _text(
         '    finally:\n        build_index.SCORING["confidence_weights"].clear()\n'
         '        build_index.SCORING["confidence_weights"].update(declared)', "    finally:\n        pass"))],
     "substitutes_weights_only_for_one_call"),
    ("a blind calibration packet carries the model's result",
     [("scripts/eci_calibration.py", _text(
         '            "sources": [blind_source(s) for s in record.get("sources") or []]}',
         '            "sources": [blind_source(s) for s in record.get("sources") or []],\n'
         '            "model": record.get("evidence_confidence")}'))],
     "blind_packet_never_carries_the_result"),
    ("a blind calibration packet carries each source's address",
     [("scripts/eci_calibration.py", _text('        "publisher": s.get("publisher"),\n        "role"',
                                           '        "publisher": s.get("url"),\n        "role"'))],
     "blind_packet_never_carries_the_result"),
    # What's new, record level (tests/test_iteration22_whats_new.py).
    ("a campaign system's rows carry record ids",
     [("pipeline/whats_new.py", _text("    linkable = not is_restricted\n", "    linkable = True\n"))],
     "under_the_campaign_rule_never_carries_a_record_id"),
    ("a covered record carries its id when a caller asks",
     [("pipeline/whats_new.py", _text('    if with_id and not covered and e.get("event_id"):', '    if with_id and e.get("event_id"):'))],
     "covered_record_never_carries_an_id"),
    ("a withdrawn record carries its id",
     [("pipeline/whats_new.py", _text("            items, more = _capped([(_item(p[i], labels), i) for i in gone])",
                                      "            items, more = _capped([(_item(p[i], labels, with_id=True), i) for i in gone])"))],
     "withdrawn_record_carries_no_id or withdrawn_record_outside_a_campaign"),
    ("a backfilled impact record reads as a new event",
     [("pipeline/whats_new.py", _text(
         '    return "backfill" if (published - event_end).days > BACKFILL_DAYS else "new_event"', '    return "new_event"'))],
     "backfilled_historical_record_is_told_apart or which_are_backfill"),
    ("a month-dated impact event is anchored to its first day",
     [("pipeline/whats_new.py", _text("        event_end = _period_end(record.get(\"date\"))",
                                      "        event_end = dt.date.fromisoformat(_anchor(record.get(\"date\")))"))],
     "backfilled_historical_record_is_told_apart"),
    ("an attribution update reads as a new incident",
     [("pipeline/whats_new.py", _text('            ("attribution_updated", ("attribution", "status"),',
                                      '            ("impact_record_added", ("attribution", "status"),'))],
     "attribution_update_is_an_update_to_an_existing_record"),
    ("the first release of the impact layer lists every record",
     [("pipeline/whats_new.py", _text("    if cur_doc is not None and prev_doc is None:", "    if False:"))],
     "first_release_of_the_impact_layer_is_one_sentence"),
    ("weakened evidence reads as strengthened",
     [("pipeline/whats_new.py", _text("(stronger if EVIDENCE_ORDER.index(b) > EVIDENCE_ORDER.index(a) else weaker)",
                                      "(stronger if EVIDENCE_ORDER.index(b) < EVIDENCE_ORDER.index(a) else weaker)"))],
     "evidence_strengthened_or_weakened"),
    ("a build with no impact layer reads as an unchanged one",
     [("pipeline/whats_new.py", _text("    if cur_doc is None and cur_ctx is None:\n        return None",
                                      "    if cur_doc is None and cur_ctx is None:\n        return []"))],
     "no_impact_layer_in_this_build_is_null"),
    ("a withdrawn impact record is listed by id",
     [("pipeline/whats_new.py", _text(
         '            "One or more impact records shown before are not shown now: withdrawn, or held while a review is repeated."],',
         '            "Withdrawn or held: " + ", ".join(sorted(p.keys() - c.keys()))],'))],
     "withdrawn_impact_record_is_one_sentence"),
    ("the arrival of evidence confidence reads as a change to every country",
     [("pipeline/whats_new.py", _text(
         '    events = [{k: v for k, v in e.items() if k not in _DERIVED_EVENT} for e in ev.get("events") or []]',
         '    events = list(ev.get("events") or [])'))],
     "arrival_of_evidence_confidence_is_one_method_note"),
    ("the panel shows a backfill as a new event",
     [("web/src/global/whatsNewText.ts", _text(
         'if (it.timing === "backfill") s += " — historical record found by research, not a new event";',
         'if (it.timing === "backfill") s += " — new event";'))],
     "panel_says_first_release_once_and_tells_backfill"),
    ("the panel drops 'not a new incident' from an attribution update",
     [("web/src/global/whatsNewText.ts", _text(
         'if (category === "attribution_updated" || category === "ai_status_updated") s += " (existing record, not a new incident)";',
         ""))],
     "panel_says_first_release_once_and_tells_backfill"),
    ("the panel links a row that carries no record id",
     [("web/src/global/whatsNewText.ts", _text("  if (!it.record_id) return null;\n  return `?sys=${encodeURIComponent(systemId)}#ev-${it.record_id.replace(",
                                               "  return `?sys=${encodeURIComponent(systemId)}#ev-${(it.record_id ?? it.key).replace("))],
     "panel_links_a_record_outside_the_campaign_rule"),
    ("the panel's record link is not the record's own anchor",
     [("web/src/global/whatsNewText.ts", _text("#ev-${it.record_id.replace(/[^A-Za-z0-9_-]/g, \"-\")}`;",
                                               "#record-${it.record_id.replace(/[^A-Za-z0-9_-]/g, \"-\")}`;"))],
     "panel_links_a_record_outside_the_campaign_rule"),
    # The methodology red team's findings (tests/test_iteration22_redteam.py): one mutant or more
    # for each failure it reproduced.
    ("the review block's record of opened sources is ignored",
     [(EC_PY, _text('(any(s.get("opened") is True for s in strong) or _reviewer_opened(review))',
                    '(any(s.get("opened") is True for s in strong))'))],
     "opened_points_come_from_the_source_flag_or"),
    ("a review that opened nothing earns the opened points",
     [(EC_PY, _text('.get("sources_opened_by_reviewer") or 0) > 0', '.get("sources_opened_by_reviewer") or 0) >= 0'))],
     "opened_points_come_from_the_source_flag_or"),
    ("the opened reason says a reviewer read the source",
     [(EC_PY, _text('        reasons.append("A cited source was opened during research or review")',
                    '        reasons.append("Read by a reviewer")'))],
     "opened_points_come_from_the_source_flag_or or nothing_served_calls_the_component"),
    ("a declared relay adds an origin",
     [(EC_PY, _text('        keys.add(("statement", str(source["relays"])))', "        pass"))],
     "b1_to_b4_a_relay_never_adds"),
    ("two arms of one organisation are two origins",
     [(EC_PY, _text('    if organisation_of(source):\n        keys.add(("organisation", organisation_of(source)))\n', ""))],
     "b26_b40_and_one_department"),
    ("an organisation's parent is not followed",
     [(EC_PY, _text('            while table.get(oid, {}).get("parent") and oid not in seen:', "            while False:"))],
     "b26_b40_and_one_department"),
    ("a state news agency is not its state",
     [(EC_JSON, _text('"domains": ["irna.ir", "shana.ir"], "domain_suffixes": ["gov.ir"],\n'
                      '       "publishers": ["irna", "islamic republic news agency", "shana"]}',
                      '"domains": ["shana.ir"], "domain_suffixes": ["gov.ir"],\n       "publishers": ["shana"]}'))],
     "b26_b40_and_one_department"),
    ("a filed form and its filer are two origins",
     [(EC_PY, _text("        if form:\n            for j, other in enumerate(counted):",
                    "        if False:\n            for j, other in enumerate(counted):"))],
     "form_filed_by_an_operator_belongs_to_the_operator"),
    ("a record nobody reviewed for independence reaches High",
     [(EC_PY, _text('    if basis != "reviewed" and order.index(category["id"]) < order.index(ceiling):', "    if False:"))],
     "origins_were_not_reviewed_cannot_be_high"),
    ("the cap for unreviewed origins is moved to High",
     [(EC_JSON, _text('"cap_when_not_reviewed": "MODERATE"', '"cap_when_not_reviewed": "HIGH"'))],
     "origins_were_not_reviewed_cannot_be_high"),
    ("a count of publishers is called independent statements",
     [(EC_PY, _text('    elif basis == "reviewed":\n        reasons.append(', "    elif True:\n        reasons.append("))],
     "count_nobody_reviewed_is_a_count_of_publishers"),
    ("the basis of the origin count is always reviewed",
     [(EC_PY, _text('    basis = "reviewed" if origins_reviewed(review) else "publishers"', '    basis = "reviewed"'))],
     "count_nobody_reviewed_is_a_count_of_publishers or origins_were_not_reviewed_cannot_be_high"),
    ("any review block counts as a review of independence",
     [(EC_PY, _text('    return roles.get(cfg["reviewed_by_role"]) in cfg["accepting_verdicts"]', "    return bool(roles)"))],
     "who_counts_as_having_reviewed_the_origins"),
    ("an outlet reporting a claim is a second attribution",
     [(EC_PY, _text('in refs) or not _corroborates(s)]', "in refs)]"))],
     "f2_a_claim_plus_an_outlet"),
    ("the actor's own outlet is press coverage",
     [(EC_PY, _text('            or source.get("attribution_basis") == "actor_self_claim"\n'
                    "            or _published_by_actor(source, attribution))",
                    '            or source.get("attribution_basis") == "actor_self_claim")'))],
     "f8_the_actors_own_outlet or f15_f17"),
    ("a report declared to carry the claim is a finding",
     [(EC_PY, _text('            or source.get("attribution_basis") == "actor_self_claim"\n', ""))],
     "shape_reviewers_were_given"),
    ("a relay of a relay of the claim is a finding",
     [(EC_PY, _text("        moved = bool(relays)", "        moved = False"))],
     "declared_relay_of_a_claim_is_the_claim"),
    ("a one-word actor name matches inside another publisher's name",
     [(EC_PY, _text('(" " in name and f" {name} " in voice)', '(f" {name} " in voice)'))],
     "f8_the_actors_own_outlet"),
    ("a record cited only through a discovery aid reads Preliminary",
     [(EC_PY, _text("    if backing and all(is_discovery_aid(s) for s in backing):\n"
                    "        return _not_assessed(disputed, basis)\n", ""))],
     "cited_only_through_a_discovery_aid_is_not_assessed"),
    ("not assessed is scored zero",
     [(EC_PY, _text('"category": None, "label": cfg["label"], "score": None,', '"category": None, "label": cfg["label"], "score": 0,'))],
     "cited_only_through_a_discovery_aid_is_not_assessed"),
    ("an explicit origin turns a discovery aid into a source",
     [(EC_PY, _text('    if natural is None:\n        return None\n    if source.get("origin"):',
                    '    if natural is None and not source.get("origin"):\n        return None\n    if source.get("origin"):'))],
     "cited_only_through_a_discovery_aid_is_not_assessed"),
    ("the country summary counts not assessed as Preliminary",
     [("pipeline/build_systems.py", _text("        if category is None:\n            not_assessed += 1\n",
                                          '        if category is None:\n            by["PRELIMINARY"] += 1\n'))],
     "summary_counts_not_assessed_apart"),
    ("the statement claims to describe all the public evidence",
     [(EC_JSON, _text('"statement": "Evidence confidence describes the sources this record cites, not everything published about the event.',
                      '"statement": "Evidence confidence describes the quality of the public evidence for the event.'))],
     "statement_says_what_the_category_describes"),
    ("a draft method is served as calibrated",
     [(EC_PY, _text('    return METHOD["status_while_draft"] if METHOD["version"].endswith("-draft") else METHOD["status_when_calibrated"]',
                    '    return METHOD["status_when_calibrated"]'))],
     "while_the_version_is_a_draft"),
    ("the methodology says the thresholds were calibrated",
     [("docs/GLOBAL_IMPACT_METHODOLOGY.md", _text(
         "Thresholds are provisional: one blind calibration has been run and they did not pass it,",
         "Thresholds were calibrated against blind reviewer labels,"))],
     "no_document_says_the_thresholds_were_calibrated"),
    ("a source that disputes a claim still backs it",
     [(EC_PY, _text('    if claim in disputed or (claim == "effect" and "occurrence" in disputed):\n        return False\n', ""))],
     "d8_a_source_that_disputes_a_claim"),
    ("a disputed incident outweighs every category in the shadow index",
     [("scripts/confidence_shadow_study.py", _text("OFF_SCALE_WEIGHTS = {k: min(CANDIDATE_WEIGHTS.values()) for k in OFF_SCALE}",
                                                   "OFF_SCALE_WEIGHTS = {k: max(CANDIDATE_WEIGHTS.values()) for k in OFF_SCALE}"))],
     "off_the_scale_exceeds_the_lowest_mapped"),
    ("the calibration sample is drawn by the model's own category",
     [("scripts/eci_calibration.py", _text("strata.setdefault((row[0], row[1], source_profile(row[3])), []).append(row)",
                                           'strata.setdefault((row[0], row[1], row[4]["category"]), []).append(row)'))],
     "never_drawn_by_the_models_own_category"),
    ("the reviewer instructions carry the model's rubric",
     [("scripts/eci_calibration.py", _text('"HIGH: well supported. MODERATE: supported, with a gap you can name.',
                                           '"HIGH: two independent originating statements. MODERATE: supported, with a gap you can name.'))],
     "question_and_neutral_labels_not_the_models_rubric"),
    ("a record the model does not assess is put in front of reviewers",
     [("scripts/eci_calibration.py", _text('        if row[4]["category"] is not None:\n            strata.setdefault(',
                                           "        if True:\n            strata.setdefault("))],
     "never_drawn_by_the_models_own_category"),
    # The red team's should-fix items.
    ("the affected party's own account is not said to be one",
     [(EC_PY, _text('        reasons.append("The first-party source is the affected party itself")', "        pass"))],
     "partys_own_account_is_said"),
    ("a contested record shows a total",
     [(EC_PY, _text('"score": None if disputed else score,', '"score": score,'))],
     "disputed_record_shows_no_total or dispute_overrides_the_score"),
    ("a dispute outside the vocabulary is ignored",
     [(EC_PY, _text('        about = [a if a in CLAIMS + ("cause",) else "occurrence" for a in about]\n', ""))],
     "disputed_record_shows_no_total"),
    ("attribution confidence says more than the status",
     [(EC_PY, _text("    return order[min(order.index(level), order.index(ceiling))] if ceiling else level", "    return level"))],
     "h1_h2_attribution_confidence_never_says_more"),
    ("a competing attribution on the record is ignored",
     [(EC_PY, _text('    if (attribution or {}).get("competing"):', "    if False:"))],
     "h1_h2_attribution_confidence_never_says_more"),
    ("every outlet carrying one attribution counts as another",
     [(EC_PY, _text("        separate += 1", "        separate += len(relayed)"))],
     "g1_to_g8_a_relayed_attribution"),
    ("a restating outlet that declares a borrowed basis has a finding of its own",
     [(EC_PY, _text('        return source.get("attribution_basis") == "media_investigation"',
                    '        return bool(source.get("attribution_basis"))'))],
     "g1_to_g8_a_relayed_attribution"),
    ("a post or an unknown role corroborates an attribution",
     [(EC_PY, _text('    if tier_of(source) not in METHOD["corroborating_tiers"]:\n        return False\n'
                    '    if source.get("source_role") in METHOD["attribution"]["restating_roles"]:',
                    '    if source.get("source_role") in METHOD["attribution"]["restating_roles"]:'))],
     "f12_f13_posts_datasets_and_unknown_roles"),
    ("a later formal account is marked down",
     [(EC_PY, _text('             else "later_formal_account" if any(_later_formal_account(s, date, date_end) for s in strong)\n', ""))],
     "c2_a_later_formal_account"),
    ("any later first-party line is a formal account",
     [(EC_PY, _text('    return formal and cited > stop + dt.timedelta(', "    return cited > stop + dt.timedelta("))],
     "c2_a_later_formal_account"),
    ("a missing date is not said",
     [(EC_PY, _text('        reasons.append("No cited source carries a date: not recorded")', "        pass"))],
     "c2_a_later_formal_account"),
    ("a reason line shows the points out of a hundred",
     [(EC_PY, _text('        reasons.append("Reported at the time")', '        reasons.append("Reported at the time (10/100)")'))],
     "percentage_or_out_of_a_hundred"),
    ("an archived or AMP copy is a second origin",
     [(EC_PY, _text("        if m:\n            url = shape.format(m.group(1))", "        if False:\n            url = shape.format(m.group(1))"))],
     "b9_to_b21_one_statement_cited_twice"),
    ("a shortened link counts as a source",
     [(EC_JSON, _text('"shortener_hosts": ["bit.ly", "t.co",', '"shortener_hosts": ["bit.example", "t.example",'))],
     "b9_to_b21_one_statement_cited_twice"),
    ("a wire's own site is not that wire",
     [(EC_PY, _text('        ("wire:" + w["name"] for w in METHOD["origins"]["wires"] if _on(host, w["domains"])), None)',
                    "        (None for w in ()), None)"))],
     "b9_to_b21_one_statement_cited_twice"),
    ("one account under two platform names is two accounts",
     [(EC_PY, _text('    platform = METHOD["platform_aliases"].get(platform, platform)\n', ""))],
     "b9_to_b21_one_statement_cited_twice"),
    ("a channel typed as a website is press",
     [(EC_PY, _text('    if _on(_host(source), METHOD["social_hosts"]):\n        return "social"\n', ""))],
     "b22_b24_a_channel_typed_as_a_website"),
    ("badge words establish an account's identity",
     [(EC_PY, _text("    return any(word not in empty for word in", "    return any(True for word in"))],
     "b22_b24_a_channel_typed_as_a_website"),
    ("the gate accepts a medium outside the vocabulary",
     [(EC_PY, _text('    if vocabulary and medium is not None and str(medium).strip().lower() not in METHOD["media"]:', "    if False:"))],
     "b22_b24_a_channel_typed_as_a_website"),
    ("two ministries under one national suffix are one origin",
     [(EC_JSON, _text('"shared_suffixes": ["gouv.fr", ', '"shared_suffixes": ["gouv.example", '))],
     "b34_b35_hosts_under_a_shared_suffix"),
]
MUTATIONS += ITER22_CONFIDENCE_MUTATIONS
# Iteration 22: country pages. The overview ("What this page can tell you"), the impact and
# regional tabs, evidence confidence on event cards, and the image export. The catching tests run
# the SHIPPED TypeScript in Node (tests/test_iteration22_country.py); the browser-level proof is in
# web/e2e/country22.e2e.ts.
C_OVERVIEW = "web/src/global/countryOverview.ts"
C_TABS = "web/src/global/countryTabs.ts"
C_IMPACT_MODEL = "web/src/global/countryImpactModel.ts"
C_IMPACT_TAB = "web/src/global/CountryImpacts.tsx"
C_CARD = "web/src/global/EventCard.tsx"
C_EXPORT = "web/src/global/countryExport.ts"
ITER22_COUNTRY_MUTATIONS = [
    ("the overview of a campaign country states how many records are held",
     [(C_OVERVIEW, _text('    items.push("whether, or how many, records are in review");',
                         "    items.push(`${sys.research_log.passes.map((p) => (p.outcome && p.outcome.held) || 0).reduce((a, b) => a + b, 0)} records in review`);"))],
     "overview_never_states_or_implies_a_held_count"),
    ("the overview of a campaign country says candidates remain under review when a pass is flagged",
     [(C_OVERVIEW, _text('    items.push("whether, or how many, records are in review");',
                         '    items.push(sys.research_log.passes.some((p) => p.under_review) ? "records that remain under review" : "whether, or how many, records are in review");'))],
     "overview_never_states_or_implies_a_held_count"),
    ("the overview treats a campaign country as unrestricted",
     [(C_OVERVIEW, _text("  const restricted = isCampaignRestricted(sys);", "  const restricted = false;"))],
     "overview_never_states_or_implies_a_held_count or overview_of_an_empty_country"),
    ("an empty country's overview prints a zero",
     [(C_OVERVIEW, _text("    published = `No energy-disruption record is published for ${name} yet.`;",
                         "    published = `0 energy-disruption records are published for ${name}.`;"))],
     "overview_of_an_empty_country"),
    ("an empty country's overview drops 'no record is not no disruption'",
     [(C_OVERVIEW, _text("    publishedNote = `Why: ${listOf(why)}. ${NO_RECORD_IS_NOT_NO_DISRUPTION}`;",
                         "    publishedNote = `Why: ${listOf(why)}.`;"))],
     "overview_of_an_empty_country"),
    ("impact records are added to the country's published-record count",
     [(C_OVERVIEW, _text('    published = `${n} reviewed energy-disruption ${plural(n, "record is", "records are")} published for ${name}.`;',
                         '    published = `${n + (impacts.state === "ready" ? impacts.records : 0)} reviewed energy-disruption ${plural(n, "record is", "records are")} published for ${name}.`;'))],
     "never_change_the_published_record_count"),
    ("the impact count loses the words that say it is another corpus",
     [(C_OVERVIEW, _text('  return `${parts.join(" and ")}, in a separate, non-scored corpus.`;', '  return `${parts.join(" and ")}.`;'))],
     "never_change_the_published_record_count"),
    ("every system gets the regional-context tab",
     [(C_TABS, _text("Array.isArray(g.members) && g.members.includes(systemId)", "Array.isArray(g.members)"))],
     "regional_tab_exists_only_for_members"),
    ("the default tab is written into every address",
     [(C_TABS, _text("  if (tab !== DEFAULT_TAB) kept.push(`tab=${tab}`);", "  kept.push(`tab=${tab}`);"))],
     "regional_tab_exists_only_for_members"),
    ("an event with no evidence confidence is drawn with a chip",
     [(C_CARD, _text("        {confidence && <ConfidenceChip value={confidence as EvidenceConfidence} />}", "        <ConfidenceChip value={confidence as EvidenceConfidence} />"))],
     "confidence_chip_is_absent"),
    ("a half-formed evidence confidence is shown as if it were whole",
     [(EVIDENCE_TS, _text('  if (!c.components || typeof c.components !== "object" || !Array.isArray(c.reasons)) return null;\n', ""))],
     "confidence_chip_is_absent"),
    ("the country inspector drops the sentence about what confidence is not",
     [(C_CARD, _text('      {!method && <p className="conf-statement">{statement || CONFIDENCE_IS_NOT}</p>}\n', ""))],
     "confidence_chip_is_absent"),
    ("an abstracted impact record's export row names its region",
     [(C_IMPACT_MODEL, _text('  const place = isAbstracted(r) ? "country level, place withheld"', '  const place = false ? "country level, place withheld"'))],
     "abstracted_impact_record_renders_no_place or draws_the_summary"),
    ("the country page shows an abstracted impact record's region",
     [("web/src/global/impacts/model.ts", _text("  if (!isAbstracted(r) && r.admin1?.name) return `${r.admin1.name}, ${r.country_name}`;",
                                                 "  if (r.admin1?.name) return `${r.admin1.name}, ${r.country_name}`;"))],
     "abstracted_impact_record_renders_no_place"),
    ("an attempt is counted among a country's impact records",
     [(C_IMPACT_MODEL, _text("    records: impactsFor(payload, { systemIds: [systemId] }),",
                             "    records: [...impactsFor(payload, { systemIds: [systemId] }), ...allAttempts(payload).filter((r) => belongsTo(r, systemId))],"))],
     "never_counts_an_attempt"),
    ("the impact tab stops saying it is a separate corpus",
     [(C_IMPACT_TAB, _text('      <p className="small impacts-what" role="note">{IMPACT_CORPUS_LINE}</p>\n', ""))],
     "says_it_is_a_separate_corpus"),
    ("an IT failure is filed under cyber in the country's cause filter",
     [(C_IMPACT_MODEL, _text("  const cause = (r: ImpactRecord) => [r.cause_family];",
                             '  const cause = (r: ImpactRecord) => [isItFailure(r) ? "cyber" : r.cause_family];'))],
     "keep_an_it_failure_out_of_cyber"),
    ("a country's cause counts are ordered by size",
     [(C_IMPACT_MODEL, _text('  return [...known, ...rest].map((id) => ({ id, label: servedLabel(payload, "cause_families", id), n: n.get(id) ?? 0 }));',
                             '  return [...known, ...rest].map((id) => ({ id, label: servedLabel(payload, "cause_families", id), n: n.get(id) ?? 0 })).sort((a, b) => b.n - a.n);'))],
     "keep_an_it_failure_out_of_cyber"),
    ("the exported country image drops the research-preview caveat",
     [(C_EXPORT, _text('  if (sys.maturity !== "research_preview") return null;', "  if (true) return null;"))],
     "research_preview_caveat"),
    ("the impact export drops the separate-corpus line",
     [(C_IMPACT_MODEL, _text("  const lines: string[] = [IMPACT_CORPUS_LINE];", "  const lines: string[] = [];"))],
     "draws_the_summary"),
    ("the impact export changes the image's published-record line",
     [(C_EXPORT, _text("      : `No index. ${sys.event_summary.recorded_events} qualifying events in",
                       "      : `No index. ${sys.event_summary.recorded_events + (impacts ? impacts.rows.length : 0)} qualifying events in"))],
     "leaves_the_published_count_alone"),
    ("the impact summary is not drawn into the image",
     [(C_EXPORT, _text("  if (impacts) drawImpactSummary(c, impacts, s, pad, Math.round(108 * s));\n", ""))],
     "draws_the_summary"),
    ("a record that was not assessed is labelled Preliminary",
     [(EVIDENCE_TS, _text('export const NOT_ASSESSED_LABEL = "Not assessed";', 'export const NOT_ASSESSED_LABEL = "Preliminary";'))],
     "not_assessed_is_its_own_state"),
    ("a record that was not assessed is filed under the lowest category in the filter and the summary",
     [(EVIDENCE_TS, _text("  if (c.category === null) return NOT_ASSESSED;", '  if (c.category === null) return "PRELIMINARY";'))],
     "not_assessed_is_its_own_state"),
    ("a record that was not assessed is treated as carrying no confidence at all",
     [(EVIDENCE_TS, _text('  if (c.category === null) return { category: null, reason: typeof c.reason === "string" && c.reason ? c.reason : NOT_ASSESSED_FALLBACK_REASON };',
                          "  if (c.category === null) return null;"))],
     "not_assessed_is_its_own_state"),
    ("the per-country confidence summary loses the sentence that it is not comparable across countries",
     [("web/src/global/ConfidenceSummary.tsx", _text('      <p className="small dim">{CONFIDENCE_SUMMARY_NOTE}</p>\n', ""))],
     "not_assessed_is_its_own_state"),
]
MUTATIONS += ITER22_COUNTRY_MUTATIONS


# Iteration 22, integration rules between the agents' modules (tests/test_iteration22_lead.py).
ITER22_LEAD_MUTATIONS = [
    ("the impact build no longer tells the confidence model the origins were reviewed",
     [("pipeline/global_impacts.py", _text('                                           r.get("dispute"), review=r.get("review"))',
                                           '                                           r.get("dispute"))'))],
     "impact_build_passes_the_review_block"),
    ("an accepted source-and-attribution review no longer counts as an origin review",
     [("pipeline/evidence_confidence.py", _text('    return roles.get(cfg["reviewed_by_role"]) in cfg["accepting_verdicts"]',
                                                '    return False'))],
     "impact_build_passes_the_review_block"),
]
MUTATIONS += ITER22_LEAD_MUTATIONS
ITER22_LEAD_MUTATIONS_2 = [
    ("the country page offers the regional tab to a group with no regional context",
     [("web/src/global/countryTabs.ts", _text('    if (g && typeof g.regional_context === "string" && g.regional_context && typeof g.slug === "string" && g.slug',
                                              '    if (g && typeof g.slug === "string" && g.slug'))],
     "regional_tab_exists_only_for_members"),
    ("the regional context names no group",
     [("pipeline/global_impacts.py", _text('        "group": context_group(),', '        "group": None,'))],
     "regional_context_names_its_group_from_the_registry"),
    ("the confidence breakdown hides that Disputed overrides the score",
     [("web/src/global/impacts/ConfidenceChip.tsx", _text('      {value.disputed && <p className="conf-disputed">Disputed overrides the score: credible sources disagree, and this site does not choose.</p>}', ''))],
     "disputed_confidence_says_disputed_overrides"),
]
MUTATIONS += ITER22_LEAD_MUTATIONS_2


# Iteration 22: the Gulf overview's evidence sections, the regional context and the impact briefs.
# Caught by tests/test_iteration22_gulf.py, which runs the shipped TypeScript: the sections through
# react-dom/server and the briefs into a canvas that records its text.
G22_BRIEF = "web/src/global/impacts/brief/impactBrief.ts"
G22_INPUTS = "web/src/global/impacts/brief/briefInputs.ts"
G22_DRAW = "web/src/global/impacts/brief/drawImpactBrief.ts"
G22_MODEL = "web/src/global/groupImpacts.ts"
G22_VIEW = "web/src/global/GroupImpactSections.tsx"
G22_SECTIONS = "web/src/global/groupSections.ts"
ITER22_GULF_MUTATIONS = [
    ("the Gulf brief drops the aggregate-context caveat",
     [(G22_BRIEF, _text('"Aggregate regional context only: no facilities, no routes, no vessels.",', '"Regional context.",'))],
     "iter22_gulf_brief_caveat"),
    ("the Gulf brief drops the not-comparable caveat",
     [(G22_BRIEF, _text('"Event counts are published records in this corpus. They are not comparable across countries, and nothing here ranks a country.",',
                        '"Event counts are published records in this corpus.",'))],
     "iter22_gulf_brief_caveat"),
    ("the Gulf brief drops the later-status caveat",
     [(G22_BRIEF, _text('"The later status of attacked facilities is not published.",', '"Reviewed public reporting only.",'))],
     "iter22_gulf_brief_caveat"),
    ("the caveat band is not drawn",
     [(G22_DRAW, _text("  brief.caveats.forEach((t, i) => {", "  ([] as string[]).forEach((t, i) => {"))],
     "iter22_gulf_brief_caveat"),
    ("the country brief drops the not-comparable line",
     [(G22_BRIEF, _text('"Counts are published records inside this country, in this corpus: not a rate, and not comparable with any other country.",',
                        '"Counts are published records inside this country, in this corpus.",'))],
     "iter22_gulf_country_brief"),
    ("an empty country record is drawn as a zero",
     [(G22_BRIEF, _text("energy.push({ text: `No published energy disruption record. That describes this dataset, not ${where}.`, strong: true });",
                        "energy.push({ text: `0 published energy disruption records.`, strong: true });"))],
     "iter22_gulf_country_brief"),
    ("the Gulf brief counts impact records per country",
     [(G22_INPUTS, _text("rows: a.ctx.systems.map((s) => ({ name: s.name, value: fmtValue(s.values[a.metricId], m.unit) })),",
                         'rows: a.ctx.systems.map((s) => ({ name: s.name, value: fmtValue(s.values[a.metricId], m.unit) + " · " '
                         '+ (a.payload?.records ?? []).filter((r) => r.system_id === s.system_id).length + " records" })),'))],
     "iter22_gulf_brief_has_no_per_country"),
    ("a brief record carries its country",
     [(G22_BRIEF, _text("    cause: r.cause_family,\n", "    cause: r.cause_family,\n    country: (r as { country_name?: string }).country_name,\n"))],
     "iter22_gulf_brief_is_handed_four_fields"),
    ("a context statement in a brief loses its date",
     [(G22_BRIEF, _text("out.push({ text: `As of ${isoDate(s.asOf)} · ${s.type}`, strong: true });", "out.push({ text: s.type, strong: true });"))],
     "iter22_gulf_brief_context_statements"),
    ("a context statement in a brief loses its source",
     [(G22_BRIEF, _text("    out.push({ text: `Source: ${s.source}`, dim: true });\n", ""))],
     "iter22_gulf_brief_context_statements"),
    ("an older statement is drawn beside the newest of its kind",
     [(G22_BRIEF, _text("    if (seen.has(e.context_type)) continue;\n", ""))],
     "iter22_gulf_brief_context_statements"),
    ("a brief carries more than five statements",
     [(G22_BRIEF, _text("export const MAX_BRIEF_STATEMENTS = 5;", "export const MAX_BRIEF_STATEMENTS = 50;"))],
     "iter22_gulf_brief_context_statements"),
    ("a record that was not assessed is counted as Preliminary",
     [(G22_BRIEF, _text("      : null,\n  }));", '      : { id: "PRELIMINARY", label: "Preliminary" },\n  }));'))],
     "iter22_gulf_brief_confidence"),
    ("the Not assessed bucket is dropped from the brief",
     [(G22_BRIEF, _text("  if (notAssessed > 0) byConfidence.push({ ...NOT_ASSESSED, n: notAssessed });\n", ""))],
     "iter22_gulf_brief_confidence"),
    ("a provisional method is not said to be provisional",
     [(G22_BRIEF, _text("...(c.provisional != null ? [", "...(false ? ["))],
     "iter22_gulf_brief_confidence"),
    ("the confidence score is drawn out of a hundred",
     [(G22_BRIEF, _text("label: confidenceLabel(r.evidence_confidence) }",
                        'label: confidenceLabel(r.evidence_confidence) + " " + (r.evidence_confidence as { score?: number }).score + "/100" }'))],
     "iter22_gulf_brief_confidence"),
    ("an IT failure is counted as cyber in a brief",
     [(G22_BRIEF, _text("    const key = r.itFailure ? IT_FAILURE : r.cause;", '    const key = r.itFailure ? "cyber" : r.cause;'))],
     "iter22_gulf_brief_causes"),
    ("the brief's cause rows are ordered by count",
     [(G22_BRIEF, _text("  return { total: records.length, byCause: rows(causeVocab, cause),",
                        "  return { total: records.length, byCause: rows(causeVocab, cause).sort((a, b) => b.n - a.n),"))],
     "iter22_gulf_brief_causes"),
    ("the Gulf page gains a country filter",
     [(G22_MODEL, _text('    { kind: "date", id: "date", label: "Date", start: startDay, end: endDay },\n  ];',
                        '    { kind: "date", id: "date", label: "Date", start: startDay, end: endDay },\n'
                        '    { kind: "choice", id: "country", label: "Country", options: [...new Set(records.map((r) => r.country_name))]'
                        '.map((n) => ({ value: n, label: n })), values: (r) => [r.country_name] },\n  ];'))],
     "iter22_gulf_sections_never_emit"),
    ("services are ordered by how many records name them",
     [(G22_MODEL, _text("  return [...known, ...unknown];", "  return [...known, ...unknown].sort((a, b) => b.rows.length - a.rows.length);"))],
     "iter22_gulf_services_follow"),
    ("an IT failure is listed with the cyber records",
     [(G22_MODEL, _text("  return { cyber: records.filter(isCyber), itFailures: records.filter(isItFailure) };",
                        "  return { cyber: records.filter((r) => isCyber(r) || isItFailure(r)), itFailures: records.filter(isItFailure) };"))],
     "iter22_gulf_services_follow"),
    ("narrowing the context turns an older statement into the latest",
     [(G22_MODEL, _text("  const entries: ContextEntry[] = ctx.entries.filter((e) => types.includes(e.context_type));",
                        "  const entries: ContextEntry[] = ctx.entries.filter((e) => types.includes(e.context_type)).map((e) => ({ ...e, is_latest_of_type: true }));"))],
     "iter22_gulf_context_section"),
    ("the context section states a status",
     [(G22_VIEW, _text("        Each is as of its own date. No single status is given.", "        Each is as of its own date. The strait is closed."))],
     "iter22_gulf_context_section"),
    ("the fixed block no longer says what is not collected",
     [(G22_VIEW, _text(" It does not collect vessel positions, routes, bypass capacity or which facility depends on the strait, because those serve operations, not understanding.", ""))],
     "iter22_gulf_context_section"),
    ("the regional context is shown for a group it does not describe",
     [(G22_INPUTS, _text('  return typeof regional.group === "string" && regional.group !== "" && regional.group === groupId;',
                         '  return true;'))],
     "iter22_gulf_context_section"),
    ("an unknown section name opens a guessed section",
     [(G22_SECTIONS, _text("    return BY_ID.get(name.trim().toLowerCase()) ?? null;", "    return BY_ID.get(name.trim().toLowerCase()) ?? SECTIONS[3];"))],
     "iter22_gulf_sections_have_addresses"),
    ("a section jump drops the filters from the address",
     [(G22_SECTIONS, _text('  const kept = pairs(search).filter(([k]) => k !== "section").map(', '  const kept = pairs(search).filter(([k]) => k === "group").map('))],
     "iter22_gulf_sections_have_addresses"),
    ("the overview speaks of the strait",
     [(G22_SECTIONS, _text('"Dated, sourced statements in aggregate, each shown as of its own date. No single status is given."',
                           '"Dated statements about tanker traffic through the strait."'))],
     "iter22_gulf_sections_have_addresses"),
]
MUTATIONS += ITER22_GULF_MUTATIONS

# Iteration-22 release closure (code worker): first_published means first served; self-claims are not
# competing attributions; the confidence model's source and dispute validators gate the import and
# the build; an end date is observed; ties in the regional context; the Gulf precision wording.
STAMP = "scripts/stamp_first_published.py"
CLOSURE_MUTATIONS = [
    ("impacts import: the run date is stamped as first_published again",
     [(II, _text('    out["first_published"] = served\n', '    out["first_published"] = served or date\n'))],
     "import_never_writes_its_run_date_as_first_published or leaves_first_published_pending"),
    ("impacts import: a re-imported pending record or entry is given the run date",
     [(II, _text('    served = old.get("first_published") if old is not None else None',
                 '    served = (old.get("first_published") or date) if old is not None else None'))],
     "reimport_of_a_pending_record_or_entry_keeps_it_pending"),
    ("stamp_first_published overwrites a date already there",
     [(STAMP, _text('            if row.get("first_published") is None:', '            if True:'))],
     "stamp_first_published_fills_nulls_only"),
    ("stamp_first_published goes backwards",
     [(STAMP, _text('    if newest is not None and date < newest:', '    if False:'))],
     "stamp_first_published_refuses_to_go_backwards"),
    ("stamp_first_published accepts a malformed date",
     [(STAMP, _text('    if not valid_date(date):', '    if not date:'))],
     "stamp_first_published_refuses_a_malformed_date"),
    ("impacts: a record pending its first release may carry last_revised",
     [(GI, _text('        if first is None:\n            out.append("last_revised on a record pending', '        if False:\n            out.append("last_revised on a record pending'))],
     "gate_requires_first_published_and_a_well_formed_id"),
    ("regional context: a tie for the latest statement is broken arbitrarily",
     [(GI, _text('and e["is_latest_of_type"])\n                      for t in TAXONOMY["context_types"]',
                 'and e["is_latest_of_type"])[:1]\n                      for t in TAXONOMY["context_types"]'))],
     "latest_by_type_lists_every_statement"),
    ("the recent lists say 'first-level region at most' again",
     [("pipeline/build_systems.py", _text('{precision_statement({sid: v[0] for sid, v in all_events.items()}, aggregating=True, events_by_system={sid: v[1] for sid, v in all_events.items()})}',
                                          'Precision is first-level region at most.'))],
     "recent_lists_say_where_attack_records_are_placed"),
    # Release closure round 3 (NS-2): site names in a campaign system are gate-only, never served.
    ("a campaign system's site name is served again in its unit aliases",
     [("data/curated/systems/qa/system.json", _artifact(lambda d: (
         d["geography"]["unit_aliases"]["QA-KH"].append("Ras Laffan"),
         d["geography"]["gate_aliases"]["QA-KH"].remove("Ras Laffan"))))],
     "site_names_are_gate_only"),
    ("the served system file carries the gate-only names",
     [("pipeline/build_systems.py", _text('    return {k: v for k, v in geo_doc.items() if k not in GATE_ONLY_GEOGRAPHY}',
                                          '    return dict(geo_doc)'))],
     "served_geography_carries_no_gate_only_key or site_names_are_gate_only"),
    ("a name listed both served and gate-only is served",
     [("pipeline/build_systems.py", _text('    if both:\n        raise ValueError(f"{system_id}: served unit_aliases also listed as gate-only: {both}")',
                                          '    if False:\n        raise ValueError(f"{system_id}: served unit_aliases also listed as gate-only: {both}")'))],
     "listed_both_served_and_gate_only"),
    ("the import gate stops reading the gate-only names",
     [("pipeline/build_systems.py", _text('    rows += [(code, alias) for code, aliases in (geo_doc.get("gate_aliases") or {}).items() for alias in aliases]\n',
                                          ''))],
     "served_geography_carries_no_gate_only_key or reads_a_place_in_any_common_spelling"),
    # Release closure round 3 (NS-3): the sentence says only what served records do.
    ("the precision sentence says a system publishes attack records because its policy allows them",
     [("pipeline/build_systems.py", _text('hits = [e for e in events_by_system.get(sid) or [] if e.get("cause") in KINETIC_CAUSES]',
                                          'hits = [{"cause": "kinetic_strike", "region_code": "x", "facility_name": "x", "publication": {}}]'))],
     "precision_sentence_says_only_what_served_records_do"),
    ("the precision sentence opens with 'never finer than first-level region' beside 'facility detail' again",
     [("pipeline/build_systems.py", _text('out = ["Each country\'s own policy sets where its records are placed."]',
                                          'out = ["Precision is set by each country\'s own policy, and is never finer than first-level region."]'))],
     "precision_sentence_says_only_what_served_records_do"),
    ("the precision sentence says 'under the owner's current decision' of attack records with no campaign block",
     [("pipeline/build_systems.py", _text('covered = any(e.get("publication") for e in hits)', 'covered = True'))],
     "precision_sentence_says_only_what_served_records_do"),
    ("the precision sentence counts Saudi Arabia among the country-only systems",
     [("pipeline/build_systems.py", _text('if p.get("kinetic") == "country" and p.get("other") != "country"]',
                                          'if p.get("other") != "country"]'))],
     "recent_lists_say_where_attack_records_are_placed"),
    ("impacts import: the confidence model's source_problems is not called",
     [(GI, _text('        out += [f"{w}: {p}" for p in EC.source_problems(s, vocabulary=False)]', '        pass'))],
     "import_refuses_a_citation_the_confidence_model_refuses"),
    ("impacts build: the confidence model's dispute_problems is not called",
     [(GI, _text('\n    out += [f"dispute: {p}" for p in EC.dispute_problems(d)]', '\n    pass'))],
     "build_refuses_a_dispute_the_confidence_model_refuses"),
    ("a record dispute about who did it passes",
     [(EC_PY, _text('        if a in ("attribution", "ai_involvement"):', '        if False:')),
      (EC_PY, _text('DISPUTE_ABOUT = ("occurrence", "effect", "cause")', 'DISPUTE_ABOUT = CLAIMS + ("cause",)'))],
     "build_refuses_a_dispute_the_confidence_model_refuses"),
    ("an S1 account whose identity is a badge passes",
     [(GI, _text('elif social.get("account_tier") == "S1" and not EC._identity_established(social):', 'elif False:'))],
     "s1_account_whose_identity_rests_on_a_badge"),
    ("a competing entry resting only on a self-claim passes the validator",
     [(EC_PY, _text('        elif set(basis) == {"actor_self_claim"}:', '        elif False:'))],
     "competing_entry_resting_only_on_a_self_claim"),
    ("a competing entry citing only the actor's own claim passes the validator",
     [(EC_PY, _text('        if cited and all(_own_claim(s, {"actor": c.get("actor")}) for s in cited):', '        if False:'))],
     "competing_entry_whose_every_source_is_the_actors_own_claim"),
    ("self_claims make attribution confidence DISPUTED",
     [(EC_PY, _text('    if (attribution or {}).get("competing"):', '    if (attribution or {}).get("competing") or (attribution or {}).get("self_claims"):'))],
     "self_claims_are_provenance_and_never_make_a_record_disputed"),
    ("a self-claim's own source feeds attribution confidence",
     [(EC_PY, _text('    return [s for s in sources if s.get("ref") not in only]', '    return list(sources)'))],
     "self_claims_are_provenance_and_never_make_a_record_disputed"),
    ("the gate does not call the attribution dispute validator",
     [(GI, _text('    out += EC.attribution_dispute_problems(r.get("attribution"), sources)\n', ''))],
     "competing_entry_resting_only_on_a_self_claim or self_claim_needs_its_actor_type"),
    ("the import drops self_claims as a field outside the contract",
     [(GI, _text('"competing", "self_claims",\n', '"competing",\n'))],
     "leads_normalisation_can_move_a_self_claim_out_of_competing"),
    ("an end date after every source passes",
     [(GI, _text('    if _start(end) > _last_day(newest):', '    if False:'))],
     "end_date_after_the_newest_source_is_refused or import_refuses_a_planned_end_date"),
    ("the end date is judged against the oldest source",
     [(GI, _text('    newest = max((s["date"] for s in sources), key=_last_day)', '    newest = min((s["date"] for s in sources), key=_last_day)'))],
     "end_date_after_the_newest_source_is_refused"),
    ("the end date rule guesses at an undated page",
     [(GI, _text('not sources or not all(_date_ok(s.get("date"), precisions) for s in sources):',
                 'not sources or not any(_date_ok(s.get("date"), precisions) for s in sources):')),
      (GI, _text('    newest = max((s["date"] for s in sources), key=_last_day)',
                 '    newest = max((s["date"] for s in sources if s.get("date")), key=_last_day)'))],
     "end_date_rule_does_not_guess_at_an_undated_page"),
]
MUTATIONS += CLOSURE_MUTATIONS

# Iteration-22 release closure, test-architecture red team: each mutant below survived every earlier test
# when it was tried (one a guard added in the same pass). Stamps, self-claims, end-date precision, the
# latest statement, reconciliation with held country records, the campaign address rules, S1 identity
# and the CSV export.
TESTARCH22_MUTATIONS = [
    ("stamp_first_published reads only the records for the newest date already served",
     [(STAMP, _text('    dated = [row["first_published"] for name, key in FILES for row in docs[name][key]',
                    '    dated = [row["first_published"] for name, key in FILES[:1] for row in docs[name][key]'))],
     "stamp_first_published_reads_the_newest_date_across_both_files"),
    ("a competing entry whose basis repeats the self-claim passes",
     [(EC_PY, _text('        elif set(basis) == {"actor_self_claim"}:', '        elif basis == ["actor_self_claim"]:'))],
     "self_claim_in_competing_is_refused_however_its_basis"),
    ("a competing entry's basis is not read against the vocabulary (a misspelt self-claim is a rival)",
     [(EC_PY, _text(' or any(b not in ATTRIBUTION_BASES for b in basis):', ':'))],
     "self_claim_in_competing_is_refused_however_its_basis"),
    ("a competing entry citing a declared report of the claim, or the actor's own outlet, passes",
     [(EC_PY, _text('        if cited and all(_own_claim(s, {"actor": c.get("actor")}) for s in cited):',
                    '        if cited and all(s.get("source_role") == "actor_self_claim" for s in cited):'))],
     "competing_entry_citing_only_reports_of_the_actors_claim"),
    ("a competing entry with an independent source beside the claim is refused",
     [(EC_PY, _text('        if cited and all(_own_claim(s, {"actor": c.get("actor")}) for s in cited):',
                    '        if cited and any(_own_claim(s, {"actor": c.get("actor")}) for s in cited):'))],
     "competing_entry_citing_only_reports_of_the_actors_claim"),
    ("a month-dated source ends on the 30th of a 31-day month (a valid end date is refused)",
     [(GI, _text('        return (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)\n    return dt.date(int(s[:4]), 12, 31)',
                 '        return (first.replace(day=28) + dt.timedelta(days=3)).replace(day=1) - dt.timedelta(days=1)\n    return dt.date(int(s[:4]), 12, 31)'))],
     "end_date_is_judged_to_the_last_day_of_a_31_day_month"),
    ("a year-dated source is read as 1 January",
     [(GI, _text('    return dt.date(int(s[:4]), 12, 31)\n\n\ndef end_date_problems', '    return dt.date(int(s[:4]), 1, 1)\n\n\ndef end_date_problems'))],
     "end_date_is_judged_to_the_last_day_of_a_31_day_month"),
    ("the end-date rule skips any record with a social source",
     [(GI, _text('    newest = max((s["date"] for s in sources), key=_last_day)\n    if _start',
                 '    if any(s.get("medium") == "social" for s in sources):\n        return []\n    newest = max((s["date"] for s in sources), key=_last_day)\n    if _start'))],
     "end_date_rule_still_applies_to_a_record_with_a_social_source"),
    ("the latest statement of a type is chosen by publication date, not as-of date",
     [(GI, _text('        newest[e["context_type"]] = max(newest.get(e["context_type"], ""), e["as_of"])',
                 '        newest[e["context_type"]] = max(newest.get(e["context_type"], ""), e["date"])')),
      (GI, _text('        out["is_latest_of_type"] = e["as_of"] == newest[e["context_type"]]',
                 '        out["is_latest_of_type"] = e["date"] == newest[e["context_type"]]'))],
     "latest_statement_of_a_type_is_chosen_by_its_as_of_date"),
    ("a multi-country candidate is reconciled with no country (a held record returns inside it)",
     [(II, _text('    for a3 in G._countries(record):\n        sid = ctx["queue_of"].get(a3)\n        if not sid:\n            continue\n        unpublished',
                 '    for a3 in [record.get("country_a3")]:\n        sid = ctx["queue_of"].get(a3)\n        if not sid:\n            continue\n        unpublished'))],
     "multi_country_candidate_is_reconciled_with_every_country"),
    ("a held system-wide country record matches no impact record",
     [(II, _text('    if mapped is None or mapped["sector"] is None:\n        return record.get("domain") == "energy"',
                 '    if mapped is None or mapped["sector"] is None:\n        return False'))],
     "held_country_record_of_a_class_with_no_sector"),
    ("an abstracted record that is not an attack may name a campaign system's region in an address",
     [(GI, _text('        if is_attack(r) or r.get("publication_policy") == ABSTRACTED:\n            for s in _sources(r):',
                 '        if is_attack(r):\n            for s in _sources(r):'))],
     "abstracted_record_in_a_campaign_system_names_no_region"),
    ("a publisher's name is not read for a campaign system's region names",
     [(GI, _text('[_prose(r), _id_words(r)] + [str(s.get("publisher") or "") for s in _sources(r)]', '[_prose(r), _id_words(r)]'))],
     "publisher_that_names_a_campaign_systems_region"),
    ("an abstracted record may carry a declared episode",
     [(GI, _text('        out.append("an abstracted record is its own episode', '        pass  # ("an abstracted record is its own episode'))],
     "abstracted_record_carries_no_episode"),
    ("an S1 identity basis of a badge and a platform name establishes identity",
     [(EC_JSON, _text('"of", "telegram", "bluesky", "bsky", "mastodon",', '"of",'))],
     "s1_basis_that_names_only_a_badge_and_a_platform"),
    ("the CSV writes a row key that is not one of its columns",
     [(R_CSV, _text('    lines.push(columns.map((c) => csvCell(Object.prototype.hasOwnProperty.call(row, c) ? row[c] : "")).join(","));',
                    '    lines.push([...columns, ...Object.keys(row).filter((k) => !columns.includes(k))].map((c) => csvCell(text(row[c]))).join(","));'))],
     "csv_writes_no_key_outside_its_columns"),
    ("the CSV filename takes the scope from the address as given",
     [(R_CSV, _text('  return `edm-${slug(scope)}-${slug(kind)}-${slug(buildDate)}.csv`;', '  return `edm-${scope}-${slug(kind)}-${slug(buildDate)}.csv`;'))],
     "csv_writes_no_key_outside_its_columns"),
    ("the CSV README leaves out the filters in force",
     [(R_CSV, _text('      ? [...i.filters.map((f) => `- ${f}`), `- These filters leave out ${hidden} of the ${i.total} published records in this list.`]',
                    '      ? [`- These filters leave out ${hidden} of the ${i.total} published records in this list.`]'))],
     "csv_readme_states_every_filter_in_force"),
    ("the CSV README leaves out the build date",
     [(R_CSV, _text('    `Site build date: ${i.buildDate}`,\n', ''))],
     "csv_readme_states_every_filter_in_force"),
    ("the CSV exports an abstracted impact record's end date",
     [(R_CSV, _text('    date_end: abstracted ? "" : text(r.date_end),', '    date_end: text(r.date_end),'))],
     "csv_an_abstracted_impact_record_exports_no_end_date"),
]
MUTATIONS += TESTARCH22_MUTATIONS


# Iteration 22 release closure, frontend: self-claims shown apart, a null first_published never a
# date, tied newest context statements kept and spoken of in the plural, and the Gulf page's three
# placement rules. Caught by tests/test_iteration22_closure_frontend.py running the SHIPPED
# TypeScript; the browser-level proof is web/e2e/closure22.e2e.ts and closure22.test.tsx.
CL_ATTR = "web/src/global/impacts/AttributionLine.tsx"
CL_CARD = "web/src/global/impacts/ImpactCard.tsx"
CL_WN = "web/src/global/whatsNewText.ts"
CL_CSV = "web/src/global/recordCsv.ts"
CL_TL = "web/src/global/impacts/ContextTimeline.tsx"
CL_LATEST = "web/src/global/impacts/latestOfType.ts"
CL_REGIONAL = "web/src/global/CountryRegional.tsx"
CL_BRIEF = "web/src/global/impacts/brief/impactBrief.ts"
CL_PRECISION = "web/src/global/groupPrecision.ts"
ITER22_CLOSURE_FRONTEND_MUTATIONS = [
    ("a self-claim is listed with the competing attributions",
     [(CL_ATTR, _text("            {a.competing.map((c, i) => (",
                      '            {[...a.competing, ...selfClaims.map((x) => ({ ...x, basis: ["actor_self_claim"] }))].map((c, i) => ('))],
     "closure22_self_claim_is_never_a_competing"),
    ("a self-claim is shown as the attribution itself",
     [(CL_ATTR, _text("    disputed ? null : actorText(a.actor, a.actor_type),",
                      "    disputed ? null : actorText(selfClaims[0]?.actor ?? a.actor, a.actor_type),"))],
     "closure22_self_claim_is_never_a_competing"),
    ("a self-claim beside an assessed attribution is not shown",
     [(CL_ATTR, _text("      <SelfClaims claims={selfClaims} />\n    </div>", "    </div>"))],
     "closure22_self_claim_is_never_a_competing"),
    ("a card with no first_published says it was added on a placeholder date",
     [(CL_CARD, _text("      {isHistoricalAddition(r) && r.first_published && (", "      {(isHistoricalAddition(r) || r.first_published == null) && ("))],
     "closure22_null_first_published"),
    ("What's New gives a null first_published a date",
     [(CL_WN, _text('isFirstPublishedDay(it.first_published)) s += `; first published ${recordDate(it.first_published)}`;',
                    'true) s += `; first published ${recordDate(it.first_published || new Date(0).toISOString().slice(0, 10))}`;'))],
     "closure22_null_first_published"),
    ("the CSV fills a null first_published with a date",
     [(CL_CSV, _text("    first_published: text(r.first_published),", '    first_published: text(r.first_published ?? "1970-01-01"),'))],
     "closure22_null_first_published"),
    ("the timeline speaks of one latest statement over several",
     [(CL_TL, _text("  if (latestOfType > 1) return `As of ${fmtDate(e.as_of)}: one of the ${latestOfType} most recent ${type} statements on record. Not a current status.`;\n", ""))],
     "closure22_tied_latest"),
    ("an older payload's tie is settled by its one flag",
     [(CL_LATEST, _text("    for (const e of ofType) if (e.is_latest_of_type === true || days.has(e.as_of)) out.add(e);",
                        "    for (const e of ofType) if (e.is_latest_of_type === true || (flagged.length === 0 && days.has(e.as_of))) out.add(e);"))],
     "closure22_tied_latest"),
    ("the country tab keeps one statement per kind",
     [(CL_REGIONAL, _text("  return { ...ctx, entries: ctx.entries.filter((e) => latest.has(e)) };",
                          "  return { ...ctx, entries: ctx.entries.filter((e, i, all) => latest.has(e) && all.findIndex((x) => latest.has(x) && x.context_type === e.context_type) === i) };"))],
     "closure22_tied_latest"),
    ("the country tab's lead stays singular over a tie",
     [(CL_REGIONAL, _text('  const lead = tie ? "The newest statements of each kind (where several share the newest date, all are shown)" : "The newest statement of each kind";',
                          '  const lead = "The newest statement of each kind";'))],
     "closure22_tied_latest"),
    ("a brief carries one of several tied statements",
     [(CL_BRIEF, _text("    for (const x of group) {", "    for (const x of group.slice(0, 1)) {"))],
     "closure22_tied_latest"),
    ("a brief's note stays singular over a tie",
     [(CL_BRIEF, _text("  const tie = statements.some((s) => (s.ofType ?? 1) > 1);", "  const tie = false;"))],
     "closure22_tied_latest"),
    ("the Gulf page drops that impact-layer attacks are always country level",
     [(CL_PRECISION, _text('    "In the impact records on this page that holds for every country, always.",\n', ""))],
     "closure22_gulf_placement"),
    ("the admin1 card loses the impact layer's country-level rule",
     [(CL_PRECISION, _text(" In the impact records on this page they are country level. ${OTHERS}`;", " ${OTHERS}`;"))],
     "closure22_gulf_placement"),
]
MUTATIONS += ITER22_CLOSURE_FRONTEND_MUTATIONS


# --- Iteration 22 release closure, round 2 (rulings R4, R5, R8, R10, R11) --------------------------------
ITER22_ROUND2_MUTATIONS = [
    ("round 2 R4: the served origin count counts a citation the lead added",
     [(EC_PY, _text("    kept = [s for s in sources if isinstance(s, dict) and not lead_added(s)\n",
                    "    kept = [s for s in sources if isinstance(s, dict) and True\n"))],
     "origin_count_leaves_out_lead_added or lead_added_citation_never_raises"),
    ("round 2 R4: the served origin count counts an actor's own claim",
     [(EC_PY, _text('    return source.get("source_role") == "actor_self_claim" or _published_by_actor(source, attribution)',
                    "    return False"))],
     "origin_count_leaves_out_lead_added"),
    ("round 2 R4: the build serves the plain grouping as origin_count again",
     [(GI, _text('    out["origin_count"] = EC.served_origin_count(r["sources"], r.get("attribution"))',
                 '    out["origin_count"] = EC.independent_origins(r["sources"])'))],
     "lead_added_citation_never_raises or each_served_record_adds_what_the_contract_says"),
    ("round 2 R5: the import stamps not_applicable as the AI check on every record",
     [(II, _text('    checks = {"ai_check": "passed"} if ai else {}',
                 '    checks = {"ai_check": "passed" if ai else "not_applicable"}'))],
     "import_writes_no_ai_check"),
    ("round 2 R5: the gate lets an AI check stand on a record with no reported AI involvement",
     [(GI, _text('        if not ai_needed and "ai_check" in v:', "        if False:"))],
     "ai_check_is_passed_where_ai_is_reported"),
    ("round 2 R8: an abstracted record may cite an unresolved short address",
     [(GI, _text("        if alias_unresolved(url, ctx):", "        if False:"))],
     "refuses_an_unresolved_short_address"),
    ("round 2 R8: a redirected short address counts as resolved",
     [(GI, _text('.get("link_states", {}).get(url) != "reachable"',
                 '.get("link_states", {}).get(url) not in ("reachable", "redirected")'))],
     "refuses_an_unresolved_short_address"),
    ("round 2 R10: the gate accepts a null value as no figure",
     [(GI, _text('        if aff.get("value") is None:\n            out.append(f"{w}: affected.value is null',
                 '        if False:\n            out.append(f"{w}: affected.value is null'))],
     "gate_refuses_the_other_spellings"),
    ("round 2 R10: the gate accepts 'unknown' as a unit",
     [(GI, _text('        if aff.get("unit") in ABSENCE:\n            out.append(f"{w}: affected.unit',
                 '        if False:\n            out.append(f"{w}: affected.unit'))],
     "gate_refuses_the_other_spellings"),
    ("round 2 R10: the canonical form keeps a null value",
     [(GI, _text('    out["value"] = value if value in ABSENCE else "unknown"', '    out["value"] = value'))],
     "every_spelling_of_no_figure_becomes_the_one_canonical_form"),
    ("round 2 R10: the build serves the curated spelling as it is",
     [(GI, _text('            c["affected"] = canonical_affected(c.get("affected"))', "            pass"))],
     "build_serves_the_canonical_form"),
    ("round 2 R10: the import keeps a lane's spelling of no figure",
     [(II, _text('            fixed = G.canonical_affected(c["affected"])', '            fixed = c["affected"]'))],
     "import_writes_the_canonical_form"),
    ("round 2 R11: a served research note may carry a figure from a source",
     [(GI, _text('            hit = LOG_FIGURE.search(str(f.get(k) or ""))', "            hit = None"))],
     "research_note_with_a_figure_from_a_source_is_refused"),
]
MUTATIONS += ITER22_ROUND2_MUTATIONS


# Iteration 22: link health of the impact layer and the regional context (scripts/check_source_links.py
# --impacts). Caught by tests/test_iteration22_linkhealth.py, which needs no network.
LC22 = "scripts/check_source_links.py"
ITER22_LINK_MUTATIONS = [
    ("a refusal by the site is recorded as dead",
     [(LC22, _text('        if e.code in BLOCKED_HTTP:\n            state = "blocked"\n',
                   '        if e.code in BLOCKED_HTTP:\n            state = "dead"\n'))],
     "link_health_blocked_is_never_dead"),
    ("a bot challenge behind a 503 is recorded as an error, not a refusal",
     [(LC22, _text('            state = "blocked" if _challenged(e) else "error"', '            state = "error"'))],
     "link_health_blocked_is_never_dead"),
    ("a timeout is recorded as dead",
     [(LC22, _text('        return {"state": "error", "http": None, "detail": "timeout"}',
                   '        return {"state": "dead", "http": None, "detail": "timeout"}'))],
     "link_health_a_checker_failure_is_never_dead"),
    ("a refused connection is recorded as dead",
     [(LC22, _text('        return {"state": "blocked", "http": None, "detail": "the server refused or dropped the connection"}',
                   '        return {"state": "dead", "http": None, "detail": "the server refused or dropped the connection"}'))],
     "link_health_a_checker_failure_is_never_dead"),
    ("one failed DNS lookup marks a host dead",
     [(LC22, _text('            return {"state": "error", "http": None, "detail": "DNS: no such host", "dns_not_found": True}',
                   '            return {"state": "dead", "http": None, "detail": "DNS: no such host", "dns_not_found": True}'))],
     "link_health_a_checker_failure_is_never_dead"),
    ("a host DNS cannot find is dead without a second lookup",
     [(LC22, _text('        sleep(DNS_RETRY_WAIT)\n        r = fetch_one(url)\n', ''))],
     "link_health_dns_not_found_is_dead_only_after_a_second_lookup"),
    ("a removal notice is read from the article body",
     [(LC22, _text('    texts = [title or ""] + [m.group(1)', '    texts = [html, title or ""] + [m.group(1)'))],
     "link_health_removal_is_read_from_the_title_and_description_only"),
    ("a host that refused is asked again in the same run",
     [(LC22, _text('            if results[url]["state"] == "blocked":\n                refused.add(host)\n', ''))],
     "link_health_one_request_per_url_a_pause_per_host"),
    ("the run ignores its request cap",
     [(LC22, _text('        elif asked >= cap:', '        elif False:'))],
     "link_health_one_request_per_url_a_pause_per_host"),
    ("the run no longer pauses between requests to one host",
     [(LC22, _text('            if wait > 0:\n                sleep(wait)\n', ''))],
     "link_health_one_request_per_url_a_pause_per_host"),
    ("the impact layer counts a redirect to a home page as dead",
     [(LC22, _text('            elif kind == "general_page" and gone_is_dead:', '            elif kind == "general_page":'))],
     "link_health_impact_redirect_to_a_home_page_is_not_dead"),
    ("the country file carries a state outside its five",
     [(LC22, _text(' if u in results and results[u]["state"] in SYSTEM_STATES))', ' if u in results))'))],
     "link_health_country_file_carries_only_its_five_states"),
    ("the public impact file speaks of a citation no record publishes",
     [(LC22, _text('for u in published if u in results and', 'for u in results if u in results and'))],
     "link_health_public_file_holds_published_citations"),
    ("the public impact file records unchecked and archived states",
     [(LC22, _text('    allowed = set(impact_states()) - {"unchecked", "archived_copy"}', '    allowed = set(impact_states()) | {"fine"}'))],
     "link_health_public_file_holds_published_citations"),
    ("the redirect-safety scan reads only the cited address",
     [(LC22, _text('        for where, address in (("cited address", url), ("final address", final)):',
                   '        for where, address in (("cited address", url),):'))],
     "link_health_safety_scan_reads_the_final_address"),
    ("the redirect-safety scan stops looking for Gulf region names",
     [(LC22, _text('    if any(GI.names_in(words, L["phrases"][sid]) or IC.names_the_place(url, L["unit_words"][sid]) for sid in gulf_sids):',
                   '    if False:'))],
     "link_health_safety_scan_reads_the_final_address"),
    ("the redirect-safety scan stops looking for facility names",
     [(LC22, _text('    if any(L["facility"].get(sid) and IC.names_the_place(url, L["facility"][sid]) for sid in own_sids):',
                   '    if False:'))],
     "link_health_safety_scan_reads_the_final_address"),
    ("the redirect-safety scan stops looking for an attack method",
     [(LC22, _text('    if B.method_in_address(url):\n        kinds.append("method")', '    if False:\n        kinds.append("method")'))],
     "link_health_safety_scan_reads_the_final_address"),
    ("the redirect-safety scan stops looking for status wording",
     [(LC22, _text('    if B.status_wording(B.address_words(path)):', '    if False:'))],
     "link_health_safety_scan_reads_the_final_address"),
    ("the redirect-safety scan skips the Gulf records",
     [(LC22, _text('    return item.get("publication_policy") == ABSTRACTED or bool(set(_countries(item)) & L["gulf_a3"])',
                   '    return item.get("publication_policy") == ABSTRACTED'))],
     "link_health_safety_scan_reads_the_final_address"),
    ("the redirect-safety scan skips the regional context",
     [(LC22, _text('    if corpus == "context":\n        return True\n', '    if corpus == "context":\n        return False\n'))],
     "link_health_safety_scan_covers_abstracted_gulf_and_context"),
    ("the redirect-safety scan no longer reads the context's own ban list",
     [(LC22, _text('    route = GI.CONTEXT_CASED.search(path) or GI.CONTEXT_FORBIDDEN.search(B.address_words(path))\n',
                   '    route = None\n'))],
     "link_health_safety_scan_covers_abstracted_gulf_and_context"),
    ("the redirect-safety scan stops flagging facility words on an abstracted record",
     [(LC22, _text('    if abstracted and set(re.findall', '    if False and set(re.findall'))],
     "link_health_safety_scan_covers_abstracted_gulf_and_context"),
    ("an unread short link on a sensitive record passes the scan",
     [(LC22, _text('        if not final and _unresolvable(url):', '        if False:'))],
     "link_health_an_unread_short_link_on_a_sensitive_record_is_a_hit"),
    ("a redirect-safety hit quotes the address",
     [(LC22, _text('            hits.append({"corpus": corpus, "id": iid, "field": f"sources[{ref}].url", "kind": kind,',
                   '            hits.append({"corpus": corpus, "id": iid, "field": f"sources[{ref}].url", "kind": kind, "address": final,'))],
     "link_health_safety_scan_reads_the_final_address"),
]
MUTATIONS += ITER22_LINK_MUTATIONS

# Release closure: the two guards the test-architecture red team reported as missing (affected is a
# scale; basis 2 needs the source's figure), added once rounds 2-3 had normalised the corpus.
ITER22_RELEASE_MUTATIONS = [
    ("an affected unit that is a duration or a restoration passes",
     [(GI, _text('            if isinstance(aff.get("unit"), str) and AFFECTED_NOT_A_SCALE.search(aff["unit"]):',
                 '            if False:'))],
     "an_affected_figure_that_is_a_duration_or_a_restoration_is_refused"),
    ("restoration wording is not read in the affected unit",
     [(GI, _text('|restor|recover", re.I)', '", re.I)'))],
     "an_affected_figure_that_is_a_duration_or_a_restoration_is_refused"),
    ("basis 2 passes with no figure",
     [(GI, _text('    if not attempt and basis == 2 and not any(', '    if not attempt and basis == -2 and not any('))],
     "basis_2_without_a_figure_is_refused"),
    ("basis 2 is satisfied by an absence word in the affected value",
     [(GI, _text('isinstance(c.get("affected"), dict) and _number(c["affected"].get("value"))',
                 'isinstance(c.get("affected"), dict) and c["affected"].get("value") is not None'))],
     "basis_2_without_a_figure_is_refused"),
    ("the research-note wording check does not read queue wording",
     [(GI, _text(r'|\b[a-z]+\d\b|\bqueues?\b")', r'|\b[a-z]+\d\b")'))],
     "the_research_note_refuses_first_person_and_pipeline_wording"),
]
MUTATIONS += ITER22_RELEASE_MUTATIONS

# Release closure, found by the iteration-23 UX red team: the US queue holds Puerto Rico's accepted
# events pending the owner's territory decision, and the impact layer published them as PRI records.
ITER22_TERRITORY_MUTATIONS = [
    ("the reconcile reads only a system's own geography (a held Puerto Rico event returns as a PRI record)",
     [(II, _text('        sid = ctx["queue_of"].get(a3)', '        sid = ctx["system_of"].get(a3)'))],
     "held_territory_event_cannot_return_through_the_impact_layer"),
    ("the territories awaiting the owner's decision are dropped from the reconcile",
     [(GI, _text('                     for a3 in (*s["admin0_a3"], *s.get("held_scope_a3", ()))},',
                 '                     for a3 in s["admin0_a3"]},'))],
     "held_territory_event_cannot_return_through_the_impact_layer"),
]
MUTATIONS += ITER22_TERRITORY_MUTATIONS


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


TEST_FILES = ("tests/test_pipeline.py", "tests/test_iteration18.py", "tests/test_iteration19.py",
              "tests/test_iteration20.py", "tests/test_research_coverage.py", "tests/test_iter21_gulf_map.py", "tests/test_compare.py", "tests/test_iteration21_performance.py", "tests/test_iteration21_home.py", "tests/test_iteration21_theatre_ux.py", "tests/test_iteration21_country.py", "tests/test_whats_new.py", "tests/test_iteration21_safety.py", "tests/test_iteration21_testarch.py",
              "tests/test_iteration22_impacts.py")
TEST_FILES += ("tests/test_iteration22_filters.py", "tests/test_iteration22_maploading.py")
TEST_FILES += ("tests/test_iteration22_atlas.py",)
TEST_FILES += ("tests/test_iteration22_confidence.py", "tests/test_iteration22_whats_new.py", "tests/test_iteration22_redteam.py")
TEST_FILES += ("tests/test_iteration22_country.py",)
TEST_FILES += ("tests/test_iteration22_lead.py",)
TEST_FILES += ("tests/test_iteration22_gulf.py",)
TEST_FILES += ("tests/test_iteration22_closure_frontend.py",)
TEST_FILES += ("tests/test_iteration22_round2.py",)
TEST_FILES += ("tests/test_iteration22_round3.py",)
TEST_FILES += ("tests/test_iteration22_linkhealth.py",)
TEST_FILES += ("tests/test_iteration22_release.py",)


def _run(box, k):
    env = {**os.environ, "EDM_GIT_ROOT": str(ROOT), "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([PY, "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
                        *TEST_FILES, "-k", k], cwd=box, capture_output=True, text=True,
                       encoding="utf-8", env=env)
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    return r.returncode, tail


def invalid_anchors(root=ROOT):
    """Every mutation whose anchor is missing, repeated or changes nothing, checked before any
    mutant runs: a drifted anchor used to raise mid-campaign and silently end it."""
    bad = []
    for name, edits, _ in MUTATIONS:
        for rel, mutate in edits:
            text = (root / rel).read_text(encoding="utf-8")
            try:
                if mutate(text) == text:
                    bad.append(f"{name}: changes nothing in {rel}")
            except Exception as err:   # a target that no longer exists raises anything, not only an assertion
                bad.append(f"{name}: {type(err).__name__}: {err}")
    names = [n for n, _, _ in MUTATIONS]
    bad += [f"duplicate mutation name: {n}" for n in sorted({n for n in names if names.count(n) > 1})]
    return bad


def classify(code, tail):
    """pytest exit 1 = a test failed: caught. 0 = survived. Anything else (2 interrupted or a
    collection error, 3 internal error, 4 usage, 5 nothing collected) = errored."""
    if code == 0:
        return "survived"
    if code == 1 and "failed" in tail:
        return "caught"
    return "errored"


def main():
    invalid = invalid_anchors()
    counts = {"attempted": 0, "caught": 0, "survived": 0, "invalid_anchor": len(invalid), "errored": 0,
              "baseline_not_green": 0}
    for x in invalid:
        print(f"  INVALID   {x}")
    bad_names = {x.split(":")[0] for x in invalid}
    box = _sandbox()
    try:
        failures = list(invalid)
        # --from N: start at the Nth mutation, to check new mutants quickly. A release gate runs all.
        start = int(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 0
        for name, edits, k in MUTATIONS[start:]:
            if name in bad_names:
                continue
            code, tail = _run(box, k)
            if code != 0 or "skipped" in tail and "passed" not in tail:
                counts["baseline_not_green"] += 1
                failures.append(f"BASELINE not green for {k!r}: {tail}")
                print(f"  baseline  {name}: {tail}")
                continue
            counts["attempted"] += 1
            originals = {}
            for rel, mutate in edits:
                p = box / rel
                originals.setdefault(rel, p.read_text(encoding="utf-8"))
                p.write_text(mutate(p.read_text(encoding="utf-8")), encoding="utf-8")
            code, tail = _run(box, k)
            for rel, text in originals.items():
                (box / rel).write_text(text, encoding="utf-8")
            outcome = classify(code, tail)
            counts[outcome] += 1
            print(f"  {outcome.upper():9} {name}  ({tail})")
            if outcome != "caught":
                failures.append(f"{outcome}: {name}")
        print(f"{len(MUTATIONS)} mutations, {counts['caught']} caught")
        print("outcome " + " ".join(f"{k}={v}" for k, v in counts.items()))
        if failures:
            print("\n".join(failures))
            sys.exit(1)
    finally:
        shutil.rmtree(box, ignore_errors=True)


if __name__ == "__main__":
    main()
