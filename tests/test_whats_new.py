"""Iteration 21: the global "What's new in the data" panel (pipeline/whats_new.py).

The derivation is tested on synthetic before/after states, because the cases that matter — a
historical backfill, a record held on review, a methodology version change, a decay-only day —
cannot be waited for in the real corpus. The served file is then checked for the same refusals.
"""
import copy
import json
import re
from pathlib import Path

import pytest

from pipeline import artifacts, build_manifest, diff_builds, systems, whats_new as W

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "public" / "data"
SERVED = WEB / "global" / "whats_new.json"
GULF = ("ae", "bh", "iq", "ir", "kw", "om", "qa", "sa")
CMP = {"previous_as_of": "2026-11-11", "current_as_of": "2026-11-12", "mode": "production",
       "basis": "the last published build dated before this one"}


def _event(eid, date, region="US-TX", region_name="Texas", cls="refinery", **kw):
    e = {"event_id": eid, "date": date, "date_precision": "month" if len(date) == 7 else "day",
         "region_code": region, "region_name": region_name, "geography_precision": "admin1",
         "regions_affected": [], "facility_name": f"{eid} refinery", "operator": "Operator Co",
         "asset_class": cls, "cause": "technical_accident", "summary": "s", "effect": "Plant shut for two weeks.",
         "capacity_affected": None, "sources": [{"url": f"https://example.org/{eid}"}],
         "recovery": {"research_status": "NOT_YET_RESEARCHED", "kind": None, "date": None},
         "review": {"reviewed_at": "2026-11-01"}, "episode_id": eid, "publication": None}
    e.update(kw)
    return e


def _system(sid, campaign=None, **kw):
    s = {"system_id": sid, "as_of": "2026-11-11", "campaign_state": campaign,
         "publication_policy": {"withheld_records": 0, "campaigns": [], "release_rule": {"id": "A"}},
         "research_log": {"passes": []}, "research_freshness": {"completeness": "partial"},
         "sectors": [], "sources": [], "research_gaps": [], "citation_quality": {}, "geography": {},
         "profile": {"year": 2024}, "inclusion_threshold": {"version": "2026-10-30.1"},
         "stale_policies": {"monthly": {"days": 120}}, "record_reviewed": "2026-11-01",
         "reporting_environment": "media_only"}
    s.update(kw)
    return s


def _state(**by_sid):
    """{sid: (system, [events])} -> a published state with every other country absent."""
    return {"systems": {sid: {"system": s, "events": {"as_of": s["as_of"], "events": ev, "episodes": []}}
                        for sid, (s, ev) in by_sid.items()},
            "energy_context": {"source": {"release": "2026-10-16"}, "comparison_year": 2024, "countries": []}}


def _bump(state, as_of="2026-11-12"):
    out = copy.deepcopy(state)
    for v in out["systems"].values():
        v["system"]["as_of"] = v["events"]["as_of"] = as_of
    return out


def _ids(rows):
    return [r["system_id"] for r in rows]


def _changes(payload, sid):
    return next((r["changes"] for r in payload["systems"] if r["system_id"] == sid), [])


def _cat(changes, cat):
    return next((c for c in changes if c["category"] == cat), None)


def _snap(as_of, esdi):
    return {"as_of": as_of, "esdi": esdi, "build_time": f"{as_of}T05:00:00+00:00",
            "build_inputs": {"groups": {g: "same" for g in build_manifest.INPUT_GROUPS}}}


# The theatre's ledger for a day on which nothing changed there.
QUIET = diff_builds.diff(_snap("2026-11-12", 7.0), _snap("2026-11-12", 7.0), [], [], [], [])
ACTIVE = {"state": "ACTIVE_KINETIC_CAMPAIGN"}
COVERED = {"rule": "A", "campaign_id": "x", "withheld": ["recovery"], "note": "n"}


# --- backfill versus new ---------------------------------------------------------------------------

def test_a_historical_backfill_is_new_published_records_with_event_dates_never_new_disruption():
    prev = _state(us=(_system("us"), [_event("us-a", "2022-02-03")]))
    curr = _bump(prev)
    curr["systems"]["us"]["events"]["events"].append(_event("us-2023-hidden", "2023-03-01"))
    d = W.derive(prev, curr, QUIET, CMP)
    added = _cat(_changes(d, "us"), "records_added")
    assert added["event_dates"] == ["2023-03-01", "2023-03-01"]
    assert added["all_predate_previous_build"] is True
    label = dict((c["id"], c["label"]) for c in d["categories"])["records_added"]
    assert "new disruption" not in label.lower() and "today" not in label.lower()
    assert "not a new disruption" in dict((c["id"], c["meaning"]) for c in d["categories"])["records_added"]


@pytest.mark.parametrize("date,historical", [("2026-11-10", True), ("2026-10", True),
                                             ("2026-11-11", False), ("2026-11-12", False)])
def test_only_a_record_dated_before_the_previous_build_is_called_historical(date, historical):
    prev = _state(us=(_system("us"), []))
    curr = _bump(prev)
    curr["systems"]["us"]["events"]["events"].append(_event("us-x", date))
    added = _cat(_changes(W.derive(prev, curr, QUIET, CMP), "us"), "records_added")
    assert added["all_predate_previous_build"] is historical


def test_without_a_previous_date_no_record_is_called_historical():
    prev = _state(us=(_system("us"), []))
    curr = _bump(prev)
    curr["systems"]["us"]["events"]["events"].append(_event("us-x", "2022-01-05"))
    added = _cat(_changes(W.derive(prev, curr, QUIET, {**CMP, "previous_as_of": None}), "us"), "records_added")
    assert added["all_predate_previous_build"] is False


def test_the_theatre_keeps_its_ledgers_own_backfill_judgement():
    ledger = {"changes": [{"category": "incident_added", "record_class": "historical_record_added",
                           "effective_date": "2024-05-01"},
                          {"category": "incident_corpus_changed", "record_class": "input_change"}],
              "esdi_delta": 0.1, "time_progression_only": False}
    rows = W.theatre_changes(ledger)
    assert [c["category"] for c in rows] == ["records_added"]
    assert rows[0]["all_predate_previous_build"] is True and rows[0]["event_dates"] == ["2024-05-01", "2024-05-01"]
    ledger["changes"][0]["record_class"] = "current_event"
    assert W.theatre_changes(ledger)[0]["all_predate_previous_build"] is False


# --- withdrawn or held on review ----------------------------------------------------------------------

def test_a_withdrawn_record_outside_a_campaign_is_listed_by_date_region_and_class_never_by_id():
    prev = _state(us=(_system("us"), [_event("us-2023-02-23-refinery-fire", "2023-02-23"), _event("us-b", "2024-01-01")]))
    curr = _bump(prev)
    curr["systems"]["us"]["events"]["events"].pop(0)
    w = _cat(_changes(W.derive(prev, curr, QUIET, CMP), "us"), "records_withdrawn")
    assert w["items"] == [{"date": "2023-02-23", "date_precision": "day", "region": "Texas",
                           "class": "Oil refinery", "key": "us-change-01"}]
    assert "refinery-fire" not in json.dumps(w)


@pytest.mark.parametrize("sid", GULF)
def test_a_record_held_in_a_campaign_system_is_one_sentence_with_no_count_no_dates_no_items(sid):
    prev = _state(**{sid: (_system(sid, campaign=ACTIVE), [
        _event(f"{sid}-1", "2026-03-01", publication=COVERED), _event(f"{sid}-2", "2026-03-04", publication=COVERED),
        _event(f"{sid}-3", "2026-03-09", publication=COVERED)])})
    curr = _bump(prev)
    del curr["systems"][sid]["events"]["events"][:2]
    w = _cat(_changes(W.derive(prev, curr, QUIET, CMP), sid), "records_withdrawn")
    assert w["aggregated"] is True
    assert "items" not in w and "more" not in w and "event_dates" not in w
    text = json.dumps(w)
    assert not re.search(r"\d", text), text
    assert "2026-03" not in text


def test_the_campaign_rule_is_read_from_the_data_and_covers_all_eight_gulf_systems():
    """The eight Gulf systems are restricted in the served payloads; the US, Canada, China and India
    are not."""
    seen = 0
    for sid in systems.COUNTRY_SYSTEMS:
        p = ROOT / "data" / "processed" / systems.root(sid)
        doc = {"system": json.loads((p / "system.json").read_text(encoding="utf-8")),
               "events": json.loads((p / "events.json").read_text(encoding="utf-8"))}
        assert W.restricted(doc, doc) is (sid in GULF), sid
        seen += 1
    assert seen == len(systems.COUNTRY_SYSTEMS) > 8


# --- campaign safety ---------------------------------------------------------------------------------

def test_a_campaign_record_appears_only_as_already_published():
    sid = "qa"
    prev = _state(qa=(_system(sid, campaign=ACTIVE), [_event("qa-x1", "2026-03-02", region="QA-RA", region_name="Ar Rayyan",
                                                             publication=COVERED)]))
    curr = _bump(prev)
    ev = curr["systems"][sid]["events"]["events"]
    ev.append(_event("qa-2026-03-ras-laffan-lng", "2026-03-18", region="QA-KH", region_name="Al Khor",
                     cls="lng_terminal", publication=COVERED))
    ev[0]["effect"] = "Trains 1-4 back online at 60%."      # a status change on a campaign record
    ev[0]["recovery"] = {"research_status": "EVIDENCE_FOUND", "kind": "partial_restart", "date": "2026-05-01"}
    d = W.derive(prev, curr, QUIET, CMP)
    ch = _changes(d, sid)
    added = _cat(ch, "records_added")
    assert added["items"] == [{"date": "2026-03-18", "date_precision": "day", "region": "National",
                               "class": "LNG terminal", "key": "qa-change-01"}]
    corr = _cat(ch, "data_correction")
    assert corr["items"][0]["region"] == "National" and "fields" not in corr["items"][0]
    assert _cat(ch, "recovery_evidence") is None
    text = json.dumps(d)
    for leak in ("ras-laffan", "Al Khor", "Ar Rayyan", "Trains", "60%", "partial", "x1 refinery", "Operator Co",
                 "technical", "2026-05-01"):
        assert leak not in text, leak


def test_a_recovery_change_alone_on_a_campaign_record_changes_nothing_visible():
    prev = _state(sa=(_system("sa", campaign=ACTIVE), [_event("sa-1", "2026-02-23", publication=COVERED)]))
    curr = _bump(prev)
    curr["systems"]["sa"]["events"]["events"][0]["recovery"] = {
        "research_status": "WITHHELD_ACTIVE_CAMPAIGN", "kind": None, "date": None}
    curr["systems"]["sa"]["events"]["events"][0]["review"] = {"reviewed_at": "2026-11-12"}
    assert _changes(W.derive(prev, curr, QUIET, CMP), "sa") == []


def test_recovery_evidence_outside_a_campaign_is_published_with_the_date_it_describes():
    prev = _state(us=(_system("us"), [_event("us-a", "2022-02-03")]))
    curr = _bump(prev)
    curr["systems"]["us"]["events"]["events"][0]["recovery"] = {
        "research_status": "EVIDENCE_FOUND", "kind": "full_restart", "date": "2022-03-01"}
    r = _cat(_changes(W.derive(prev, curr, QUIET, CMP), "us"), "recovery_evidence")
    assert r["items"][0]["evidence_date"] == "2022-03-01"
    assert r["items"][0]["recovery_kind"] == "full restart reported"


def test_no_number_in_the_panel_can_be_read_as_a_count():
    """The only numbers anywhere are the schema version and the theatre's index before and after."""
    prev = _state(us=(_system("us"), [_event(f"us-{i}", f"2022-0{i}-01") for i in range(1, 9)]),
                  sa=(_system("sa", campaign=ACTIVE), [_event("sa-1", "2026-02-23", publication=COVERED)]))
    curr = _bump(prev)
    curr["systems"]["us"]["events"]["events"] = [_event(f"us-n{i}", f"2023-0{i}-01") for i in range(1, 9)]
    curr["systems"]["sa"]["events"]["events"] = []
    d = W.derive(prev, curr, QUIET, CMP)
    assert _cat(_changes(d, "us"), "records_added")["more"] is True
    assert len(_cat(_changes(d, "us"), "records_added")["items"]) == W.ITEM_CAP
    _assert_no_counts(d)


def _assert_no_counts(d):
    bad = []

    def walk(x, path):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            if path not in ("schema_version",) and not re.fullmatch(r"systems\.\d+\.index\.(before|after)", path):
                bad.append(path)
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}.{i}")
    walk(d, "")
    assert bad == []
    assert not re.search(r'"(count|n|records|total|withheld_records)"\s*:', json.dumps(d))


# --- methodology, decay, build-only --------------------------------------------------------------------

def test_a_threshold_version_change_is_one_rule_change_never_a_country_improving():
    prev = _state(us=(_system("us"), [_event("us-a", "2022-02-03")]), ca=(_system("ca"), []))
    curr = _bump(prev)
    for v in curr["systems"].values():
        v["system"]["inclusion_threshold"] = {"version": "2026-12-01.1"}
    d = W.derive(prev, curr, QUIET, CMP)
    assert d["global"] == [{"category": "methodology", "notes": [
        "The inclusion threshold for country records was revised (version 2026-12-01.1)."]}]
    assert d["systems"] == []
    assert not re.search(r"improv|better|worse|safer", json.dumps([d["global"], d["systems"]]).lower())


def test_a_campaign_rule_switching_on_is_a_rule_change():
    prev = _state(iq=(_system("iq"), []))
    curr = _bump(prev)
    curr["systems"]["iq"]["system"]["publication_policy"]["campaigns"] = [{"policy_applied": True}]
    m = _cat(_changes(W.derive(prev, curr, QUIET, CMP), "iq"), "methodology")
    assert m["notes"] == ["The attack-campaign publication rule now applies here."]


def test_decay_only_is_its_own_category_and_never_a_source_event():
    ledger = diff_builds.diff(_snap("2026-11-11", 7.0), _snap("2026-11-12", 6.9), [], [], [], [])
    assert ledger["time_progression_only"] is True
    prev = _state(us=(_system("us"), []))
    d = W.derive(prev, _bump(prev), ledger, CMP)
    ru = next(r for r in d["systems"] if r["system_id"] == "ru")
    assert [c["category"] for c in ru["changes"]] == ["decay_only"]
    assert ru["index"]["before"] == 7.0 and ru["index"]["after"] == 6.9
    assert _ids(d["unchanged"]) == ["us"]


def test_a_source_re_read_beside_a_moving_index_is_not_labelled_decay():
    prev, curr = _snap("2026-11-11", 7.0), _snap("2026-11-12", 6.9)
    curr["build_inputs"]["groups"]["incident_corpus"] = "moved"
    ledger = diff_builds.diff(prev, curr, [], [], [], [])
    rows = W.theatre_changes(ledger)
    assert [c["category"] for c in rows] == ["build_only"]
    assert any("not labelled time decay only" in n for n in rows[0]["notes"])


def test_a_rebuild_that_changed_nothing_says_build_only_once():
    ledger = diff_builds.diff(_snap("2026-11-12", 7.0), _snap("2026-11-12", 7.0), [], [], [], [])
    prev = _state(us=(_system("us"), [_event("us-a", "2022-02-03")]))
    d = W.derive(prev, copy.deepcopy(prev), ledger, CMP)
    assert d["systems"] == [] and d["global"][0]["category"] == "build_only"
    assert set(_ids(d["unchanged"])) == {"ru", "us"}


def test_a_theatre_that_could_not_be_compared_is_never_listed_unchanged():
    prev = _state(us=(_system("us"), []))
    d = W.derive(prev, _bump(prev), diff_builds.unavailable({}, None, "no baseline"), CMP)
    assert "ru" not in _ids(d["unchanged"])
    assert next(r for r in d["systems"] if r["system_id"] == "ru")["unavailable"] == "no baseline"


def test_every_ledger_category_has_a_panel_category():
    assert set(W.THEATRE_CATEGORY) == set(diff_builds.CATEGORIES)
    assert set(W.THEATRE_CATEGORY.values()) <= set(W.CATEGORY_IDS)
    assert set(W.THEATRE_NOTE) == set(diff_builds.CATEGORIES) - {"incident_added", "incident_removed"}
    assert W.CATEGORY_IDS == ("records_added", "records_withdrawn", "research_coverage", "link_health",
                              "methodology", "data_correction", "national_context", "recovery_evidence",
                              "decay_only", "build_only")


def test_systems_are_listed_alphabetically_never_by_how_much_changed():
    prev = _state(us=(_system("us"), []), bh=(_system("bh"), []), cn=(_system("cn"), []))
    curr = _bump(prev)
    curr["systems"]["us"]["events"]["events"] = [_event(f"us-{i}", "2022-01-01") for i in range(9)]
    for sid in ("bh", "cn"):
        curr["systems"][sid]["system"]["research_gaps"] = ["new gap"]
    names = [r["name"] for r in W.derive(prev, curr, QUIET, CMP)["systems"]]
    assert names == sorted(names) == ["Bahrain", "China", "United States"]


def test_link_and_research_rechecks_are_their_own_categories():
    prev = _state(us=(_system("us", sources=[{"name": "EIA", "last_checked": "2026-10-30"}]), []))
    curr = _bump(prev)
    s = curr["systems"]["us"]["system"]
    s["sources"] = [{"name": "EIA", "last_checked": "2026-11-12"}]
    s["citation_quality"] = {"link_check_date": "2026-11-12"}
    s["research_log"] = {"passes": [{"date": "2026-11-12", "by": "x", "kind": "systematic"}]}
    ch = _changes(W.derive(prev, curr, QUIET, CMP), "us")
    assert [c["category"] for c in ch] == ["research_coverage", "link_health"]
    assert _cat(ch, "link_health")["notes"] == ["Cited links were re-checked on 12 Nov 2026.",
                                                "Registry sources were re-checked; the latest check is dated 12 Nov 2026."]


def test_national_context_refresh_is_said_once_for_everyone():
    prev = _state(us=(_system("us"), []))
    curr = _bump(prev)
    curr["energy_context"] = {"source": {"release": "2027-10-16"}, "comparison_year": 2025, "countries": []}
    d = W.derive(prev, curr, QUIET, CMP)
    assert d["global"][0]["category"] == "national_context"
    assert "figures for 2025" in d["global"][0]["notes"][0]


# --- the baseline ------------------------------------------------------------------------------------

def test_the_baseline_is_the_last_build_dated_before_today_so_a_same_day_rebuild_changes_nothing(tmp_path, monkeypatch):
    """A second build on the same day (a rerun, or a human commit and then the bot) must compare
    against the same build as the first, or the panel would empty itself and every rerun would
    look like a substantive change to the refresh."""
    import subprocess
    from pipeline import lineage
    monkeypatch.delenv("PRODUCTION_REF", raising=False)
    run = lambda *a: subprocess.run(["git", *a], cwd=tmp_path, capture_output=True, check=True)  # noqa: E731
    run("init", "-q", "-b", "main")
    run("config", "user.email", "t@example.org")
    run("config", "user.name", "T")
    data = tmp_path / "web" / "public" / "data"
    data.mkdir(parents=True)
    shas = {}
    for label, as_of in (("d10", "2026-11-10"), ("d11-am", "2026-11-11"), ("d11-pm", "2026-11-11"), ("d12", "2026-11-12")):
        (data / "snapshot.json").write_text(json.dumps({"as_of": as_of, "label": label}), encoding="utf-8")
        run("add", "-A")
        run("commit", "-qm", label)
        shas[label] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()
    sha, meta = lineage.previous_dated_build(tmp_path, "2026-11-12")
    assert sha == shas["d11-pm"] and meta["previous_as_of"] == "2026-11-11" and meta["mode"] == "production"
    # Rebuilding on 12 Nov after the 12 Nov commit still compares with 11 Nov.
    assert lineage.previous_dated_build(tmp_path, "2026-11-12")[0] == shas["d11-pm"]
    assert lineage.previous_dated_build(tmp_path, "2026-11-11")[0] == shas["d10"]
    none, why = lineage.previous_dated_build(tmp_path, "2026-11-10")
    assert none is None and "no committed build dated before" in why["reason"]


def test_a_same_day_rebuild_writes_the_same_panel(tmp_path):
    prev = _state(us=(_system("us"), [_event("us-a", "2022-02-03")]))
    curr = _bump(prev)
    curr["systems"]["us"]["events"]["events"].append(_event("us-b", "2023-02-03"))
    assert json.dumps(W.derive(prev, curr, QUIET, CMP)) == json.dumps(W.derive(prev, copy.deepcopy(curr), QUIET, CMP))


# --- the artifact ------------------------------------------------------------------------------------

def test_the_panel_is_a_declared_artifact_and_every_global_file_the_build_writes_is_declared():
    assert "global/whats_new.json" in artifacts.GLOBAL_PAYLOADS
    assert "data/processed/global/whats_new.json" in artifacts.required_paths()
    assert "web/public/data/global/whats_new.json" in artifacts.required_paths()
    written = set()
    for src in ("pipeline/run.py", "pipeline/build_systems.py"):
        text = (ROOT / src).read_text(encoding="utf-8")
        written |= {f"global/{m}" for m in re.findall(r'"global"\s*/\s*"([\w.]+)"', text)}
    assert "global/whats_new.json" in written
    assert written <= set(artifacts.GLOBAL_PAYLOADS), written - set(artifacts.GLOBAL_PAYLOADS)


def test_a_non_current_build_publishes_an_unavailable_panel_not_an_empty_one():
    d = W.unavailable("a fixture build has no published predecessor", "2026-08-28")
    assert d["available"] is False and d["systems"] == [] and d["global"] == []
    assert d["unavailable_reason"]


@pytest.mark.skipif(not SERVED.exists(), reason="no built payload")
def test_the_served_panel_holds_the_same_refusals():
    d = json.loads(SERVED.read_text(encoding="utf-8"))
    assert d["schema_version"] == W.SCHEMA_VERSION
    assert [c["id"] for c in d["categories"]] == list(W.CATEGORY_IDS)
    _assert_no_counts(d)
    ids = [s["id"] for s in systems.SYSTEMS]
    listed = [r["system_id"] for r in d["systems"]]
    assert listed == [i for i in ids if i in listed]
    assert set(listed) | set(_ids(d["unchanged"])) <= set(ids)
    names = {s["id"]: s["name"] for s in systems.SYSTEMS}
    assert all(r["name"] == names[r["system_id"]] for r in d["systems"] + d["unchanged"])
    checked = 0
    for r in d["systems"]:
        for c in r["changes"]:
            checked += 1
            assert c["category"] in W.CATEGORY_IDS
            for it in c.get("items") or []:
                assert set(it) <= {"date", "date_precision", "region", "class", "key", "fields",
                                   "recovery_kind", "evidence_date"}, it
                assert re.fullmatch(rf"{r['system_id']}-change-\d\d", it["key"])
            if r["system_id"] in GULF:
                assert c["category"] != "recovery_evidence"
                if c["category"] == "records_withdrawn":
                    assert c.get("aggregated") is True and "items" not in c
                for it in c.get("items") or []:
                    assert "fields" not in it
    if d["available"]:
        assert checked > 0 or d["global"]
    # No link target is published: the page links only to the country (?sys=<id>), never to a record.
    assert not re.search(r'"(href|url|link|anchor|event_id|episode_id)"\s*:', json.dumps(d))
    # Every event id that names a facility stays off the panel.
    for sid in systems.COUNTRY_SYSTEMS:
        ev = json.loads((WEB / systems.root(sid) / "events.json").read_text(encoding="utf-8"))["events"]
        for e in ev:
            assert e["event_id"] not in json.dumps(d), e["event_id"]
