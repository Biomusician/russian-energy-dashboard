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
    ("the import keeps a lane-written id with free-text middle words",
     [("scripts/import_candidates.py", _text(' and r["candidate_id"].startswith(prefix):', ':'))],
     "lane_written_id_is_kept_only"),
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
              "tests/test_iteration20.py")


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
