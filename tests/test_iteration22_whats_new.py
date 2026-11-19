"""Iteration 22: "What's new in the data" at record level (pipeline/whats_new.py and its panel).

Three additions, each with the refusal that keeps it safe:

1. Outside the campaign rule a row carries its record's public id and the panel links to the record.
   Under the rule nothing changes: no id anywhere, whatever the record.
2. A coverage or method change says where the page explains it: a tab of the country, a section of
   the home page. Never a record.
3. The impact layer's changes are listed once, apart from any country: a record added (a backfill
   is told apart from a new event), evidence strengthened or weakened, attribution or AI status
   updated ("not a new incident"), regional context updated. A first release is one sentence, never
   a list of every record. Nothing here reads a candidate queue or counts what is held.

The derivation is tested on fixtures built to the contract (GLOBAL_IMPACT_METHODOLOGY §4, §11): the
artifacts are written by another module, and may be absent.
"""
import copy
import json
import re

import pytest

from pipeline import whats_new as W
from tests import test_whats_new as T
from tests.test_iteration21_testarch import needs_bundler, run_ts

FACILITY_ID = "us-2023-02-23-big-refinery-fire"


def _derive(prev, curr, cmp=None):
    return W.derive(prev, curr, T.QUIET, cmp or T.CMP)


def _items(payload, sid, cat):
    return (T._cat(T._changes(payload, sid), cat) or {}).get("items") or []


# --- 1. record ids, outside the campaign rule only -----------------------------------------------------

def test_outside_the_campaign_rule_an_added_or_corrected_record_carries_its_public_id():
    prev = T._state(us=(T._system("us"), [T._event("us-old", "2022-02-03")]))
    curr = T._bump(prev)
    curr["systems"]["us"]["events"]["events"][0]["effect"] = "Plant shut for three weeks."
    curr["systems"]["us"]["events"]["events"].append(T._event(FACILITY_ID, "2023-02-23"))
    d = _derive(prev, curr)
    assert [it["record_id"] for it in _items(d, "us", "records_added")] == [FACILITY_ID]
    assert [it["record_id"] for it in _items(d, "us", "data_correction")] == ["us-old"]
    # The row key is still there, as the row's identity on the page.
    assert all(re.fullmatch(r"us-change-\d\d", it["key"]) for c in T._changes(d, "us") for it in c.get("items") or [])


def test_recovery_evidence_outside_the_rule_links_to_its_record():
    prev = T._state(us=(T._system("us"), [T._event("us-old", "2022-02-03")]))
    curr = T._bump(prev)
    curr["systems"]["us"]["events"]["events"][0]["recovery"] = {
        "research_status": "EVIDENCE_FOUND", "kind": "full_restart", "date": "2022-03-01"}
    assert [it["record_id"] for it in _items(_derive(prev, curr), "us", "recovery_evidence")] == ["us-old"]


def test_a_withdrawn_record_carries_no_id_because_no_page_holds_it_any_more():
    prev = T._state(us=(T._system("us"), [T._event(FACILITY_ID, "2023-02-23"), T._event("us-b", "2024-01-01")]))
    curr = T._bump(prev)
    curr["systems"]["us"]["events"]["events"].pop(0)
    d = _derive(prev, curr)
    assert _items(d, "us", "records_withdrawn") and "record_id" not in _items(d, "us", "records_withdrawn")[0]
    assert "big-refinery" not in json.dumps(d)


@pytest.mark.parametrize("how", ["campaign_state", "covered_record", "withheld_count", "left_the_rule"])
def test_a_system_under_the_campaign_rule_never_carries_a_record_id(how):
    """Every way a system can be under the rule, with records that are and are not covered, added
    and corrected: no id reaches the panel, in a field or in any text."""
    system = T._system("sa", campaign=T.ACTIVE if how == "campaign_state" else None)
    if how == "withheld_count":
        system["publication_policy"]["withheld_records"] = 1
    covered = T._event("sa-2026-03-01-named-plant-strike", "2026-03-01", region=None, region_name=None,
                       publication=T.COVERED if how in ("covered_record", "left_the_rule") else None)
    prev = T._state(sa=(copy.deepcopy(system), [T._event("sa-2024-named-substation-fault", "2024-05-01"), covered]))
    curr = T._bump(prev)
    events = curr["systems"]["sa"]["events"]["events"]
    if how == "left_the_rule":
        events[1]["publication"] = None          # covered in the previous build only
    events[0]["effect"] = "Corrected wording."
    events.append(T._event("sa-2025-named-terminal-storm", "2025-01-10"))                 # not covered, added
    events.append(T._event("sa-2026-04-02-named-refinery-strike", "2026-04-02", publication=T.COVERED if how != "campaign_state" else None))
    d = _derive(prev, curr)
    assert T._changes(d, "sa"), "the fixture produced no change to check"
    text = json.dumps(d)
    assert '"record_id"' not in text
    for e in events:
        assert e["event_id"] not in text, e["event_id"]
    assert "named-" not in text


def test_a_covered_record_never_carries_an_id_whatever_the_caller_asks():
    covered = T._event("sa-2026-03-01-named-plant-strike", "2026-03-01", publication=T.COVERED)
    assert "record_id" not in W._item(covered, {}, with_id=True)
    assert W._item(T._event("us-a", "2024-01-01"), {}, with_id=True)["record_id"] == "us-a"
    assert "record_id" not in W._item(T._event("us-a", "2024-01-01"), {})


def test_the_theatre_rows_carry_no_record_id():
    ledger = {"changes": [{"category": "incident_added", "record_class": "current_event", "effective_date": "2026-11-10"}],
              "esdi_delta": 0.1, "time_progression_only": False}
    assert '"record_id"' not in json.dumps(W.theatre_changes(ledger))


# --- 2. where a kind of change is explained ----------------------------------------------------------------

def test_a_coverage_or_method_change_links_to_the_countrys_tab_and_never_to_a_record():
    prev = T._state(us=(T._system("us"), [T._event("us-a", "2022-02-03")]))
    curr = T._bump(prev)
    curr["systems"]["us"]["system"]["research_gaps"] = ["A gap."]
    curr["systems"]["us"]["system"]["reporting_environment"] = "mixed_regulatory"
    changes = {c["category"]: c for c in T._changes(_derive(prev, curr), "us")}
    assert changes["research_coverage"]["link"] == {"system_id": "us", "tab": "research"}
    assert changes["methodology"]["link"] == {"system_id": "us", "tab": "method"}
    assert set(W.CHANGE_TAB) == {"research_coverage", "methodology"}
    for c in changes.values():
        assert set(c.get("link") or {}) <= {"system_id", "tab"}


def test_a_new_system_links_to_its_research_coverage():
    curr = T._bump(T._state(us=(T._system("us"), [])))
    c = T._changes(_derive({"systems": {}}, curr), "us")
    assert c == [{"category": "research_coverage", "notes": ["Monitoring of this system was first published."],
                  "link": {"system_id": "us", "tab": "research"}}]


def _with_confidence(state, version="2.0"):
    out = copy.deepcopy(state)
    for side in out["systems"].values():
        side["system"]["evidence_confidence_summary"] = {"by_category": {"HIGH": 1}, "method_version": version}
        for e in side["events"]["events"]:
            e["evidence_confidence"] = {"category": "HIGH", "score": 80}
    return out


def test_the_arrival_of_evidence_confidence_is_one_method_note_not_a_change_to_every_country():
    prev = T._state(us=(T._system("us"), [T._event("us-a", "2022-02-03")]), ca=(T._system("ca"), [T._event("ca-a", "2023-01-01")]))
    curr = _with_confidence(T._bump(prev))
    d = _derive(prev, curr)
    assert d["systems"] == [], "a derived label on every record read as a change to each country"
    assert d["global"] == [{"category": "methodology", "link": {"anchor": "why-head"}, "notes": [
        "Each published country record now shows an evidence-confidence category, computed from its "
        "published citations. No record changed."]}]
    # Once it is there, a build that changes nothing says so...
    again = _derive(curr, T._bump(curr, "2026-11-13"))
    assert again["global"] == [{"category": "build_only", "notes": ["Rebuilt; nothing published changed."]}]
    # ...and a revised method is one note, however many labels it moves.
    revised = _with_confidence(T._bump(prev, "2026-11-13"), version="2.1")
    for side in revised["systems"].values():
        side["events"]["events"][0]["evidence_confidence"] = {"category": "LIMITED", "score": 40}
    d3 = _derive(curr, revised)
    assert d3["systems"] == [] and "version 2.1" in d3["global"][0]["notes"][0]


# --- 3. the impact layer -----------------------------------------------------------------------------------

def _rec(iid, date, first_published="2026-11-12", category="MODERATE", attribution="UNKNOWN", ai="NONE_REPORTED", **kw):
    r = {"impact_id": iid, "date": date, "date_precision": "month" if len(date) == 7 else "day",
         "country_a3": "UKR", "country_name": "Ukraine", "sector": "telecom", "record_kind": "disruption",
         "first_published": first_published, "evidence_confidence": {"category": category, "score": 60},
         "attribution": {"status": attribution}, "ai_involvement": {"status": ai}}
    r.update(kw)
    return r


def _layer(records, entries=None, base=None):
    """A published state with an impact layer (and, optionally, a regional context)."""
    state = copy.deepcopy(base) if base else T._state(us=(T._system("us"), []))
    state["impacts"] = None if records is None else {"records": records}
    state["regional_context"] = None if entries is None else {"entries": entries}
    return state


def _impact(prev, curr):
    return _derive(prev, T._bump(curr))["impact_layer"]


def test_no_impact_layer_in_this_build_is_null_not_an_empty_list():
    prev = T._state(us=(T._system("us"), []))
    d = _derive(prev, T._bump(prev))
    assert d["impact_layer"] is None
    assert W.unavailable("no baseline")["impact_layer"] is None
    # A layer that exists and did not change is an empty list: a different fact.
    same = _layer([_rec("imp-a", "2024-01-01")])
    assert _impact(same, same) == []


def test_the_first_release_of_the_impact_layer_is_one_sentence_never_a_list_of_every_record():
    records = [_rec(f"imp-2024-01-{i:02d}-ukr-telecom-x{i}", f"2024-01-{i:02d}") for i in range(1, 29)]
    prev = T._state(us=(T._system("us"), []))                 # a build from before the layer existed
    layer = _impact(prev, _layer(records, entries=[{"id": "ctx-1"}]))
    assert layer == [{"category": "impact_record_added", "first_release": True, "notes": [W.FIRST_IMPACT_RELEASE]}]
    text = json.dumps(layer)
    assert "First release of the impact layer" in text and text.count("First release") == 1
    assert "imp-2024" not in text and '"items"' not in text
    assert not re.search(r"\b\d+ (records|events)\b", text)


@pytest.mark.parametrize("event,published,timing", [
    ("2023-12-12", "2026-11-12", "backfill"),      # found years later
    ("2026-10-12", "2026-11-12", "backfill"),      # 31 days
    ("2026-10-13", "2026-11-12", "new_event"),     # 30 days: not older than thirty
    ("2026-11-10", "2026-11-12", "new_event"),
    ("2026-09", "2026-11-12", "backfill"),         # the whole month is more than thirty days back
    ("2026-10", "2026-11-12", "new_event"),        # its last day is not
    ("2026-11-10", None, "unknown"), (None, "2026-11-12", "unknown"), ("soon", "2026-11-12", "unknown"),
])
def test_a_backfilled_historical_record_is_told_apart_from_a_new_event(event, published, timing):
    assert W.impact_timing({"date": event, "first_published": published}) == timing


def test_added_impact_records_say_which_are_backfill_and_which_are_new_events():
    prev = _layer([_rec("imp-old", "2022-05-01", "2026-11-01")])
    curr = _layer([_rec("imp-old", "2022-05-01", "2026-11-01"), _rec("imp-2023-backfill", "2023-12-12"),
                   _rec("imp-2026-new", "2026-11-10")])
    (added,) = _impact(prev, curr)
    assert added["category"] == "impact_record_added" and "first_release" not in added
    assert {it["impact_id"]: it["timing"] for it in added["items"]} == {"imp-2023-backfill": "backfill", "imp-2026-new": "new_event"}
    assert added["all_backfill"] is False and added["all_new_events"] is False
    only_old = _impact(prev, _layer([_rec("imp-old", "2022-05-01", "2026-11-01"), _rec("imp-2023-backfill", "2023-12-12")]))
    assert only_old[0]["all_backfill"] is True and only_old[0]["all_new_events"] is False
    assert all(re.fullmatch(r"impact-change-\d\d", it["key"]) for it in added["items"])


def test_a_long_list_of_added_impact_records_is_capped_and_flagged_never_counted():
    prev = _layer([_rec("imp-old", "2022-05-01")])
    curr = _layer([_rec("imp-old", "2022-05-01")] + [_rec(f"imp-{i:02d}", f"2024-02-{i:02d}") for i in range(1, 20)])
    (added,) = _impact(prev, curr)
    assert len(added["items"]) == W.ITEM_CAP and added["more"] is True
    assert not re.search(r'"(count|n|total|records)"\s*:', json.dumps(added))


@pytest.mark.parametrize("before,after,category", [
    ("MODERATE", "HIGH", "evidence_strengthened"), ("PRELIMINARY", "LIMITED", "evidence_strengthened"),
    ("HIGH", "MODERATE", "evidence_weakened"), ("HIGH", "DISPUTED", "evidence_weakened"),
    ("DISPUTED", "LIMITED", "evidence_strengthened")])
def test_a_changed_evidence_category_is_evidence_strengthened_or_weakened(before, after, category):
    layer = _impact(_layer([_rec("imp-a", "2024-01-01", category=before)]), _layer([_rec("imp-a", "2024-01-01", category=after)]))
    assert [c["category"] for c in layer] == [category]
    assert layer[0]["items"][0]["from"] == before and layer[0]["items"][0]["to"] == after
    assert "impact_record_added" not in json.dumps(layer)


def test_an_attribution_update_is_an_update_to_an_existing_record_not_a_new_incident():
    layer = _impact(_layer([_rec("imp-a", "2024-01-01", attribution="CLAIMED")]),
                    _layer([_rec("imp-a", "2024-01-01", attribution="ATTRIBUTED")]))
    assert [c["category"] for c in layer] == ["attribution_updated"]
    assert layer[0]["notes"] == ["The attribution of an existing record was updated. Not a new incident."]
    assert (layer[0]["items"][0]["from"], layer[0]["items"][0]["to"]) == ("CLAIMED", "ATTRIBUTED")
    meaning = dict((c[0], c[2]) for c in W.CATEGORIES)["attribution_updated"]
    assert "Not a new incident" in meaning


def test_an_ai_status_update_is_its_own_kind_and_not_a_new_incident():
    layer = _impact(_layer([_rec("imp-a", "2024-01-01")]), _layer([_rec("imp-a", "2024-01-01", ai="SUSPECTED")]))
    assert [c["category"] for c in layer] == ["ai_status_updated"]
    assert "Not a new incident" in layer[0]["notes"][0]


def test_regional_context_changes_are_sentences_with_no_counts():
    base = [_rec("imp-a", "2024-01-01")]
    e1, e2 = {"id": "ctx-1", "claim": "a"}, {"id": "ctx-2", "claim": "b"}
    added = _impact(_layer(base, [e1]), _layer(base, [e1, e2]))
    assert added == [{"category": "regional_context_updated",
                      "notes": ["Dated statements were added to the Gulf and Strait of Hormuz regional context."]}]
    revised = _impact(_layer(base, [e1, e2]), _layer(base, [dict(e1, claim="a, corrected")]))
    assert revised[0]["notes"] == ["Statements in the regional context were revised or withdrawn."]
    first = _impact(_layer(base, None), _layer(base, [e1]))
    assert first[0]["notes"] == ["The Gulf and Strait of Hormuz regional context was first published."]
    assert _impact(_layer(base, [e1]), _layer(base, [e1])) == []


def test_a_withdrawn_impact_record_is_one_sentence_with_no_id_no_count_and_nothing_about_candidates():
    prev = _layer([_rec("imp-a", "2024-01-01"), _rec("imp-named-operator-b", "2024-02-01"), _rec("imp-c", "2024-03-01")])
    layer = _impact(prev, _layer([_rec("imp-a", "2024-01-01")]))
    assert layer == [{"category": "records_withdrawn", "aggregated": True, "notes": [
        "One or more impact records shown before are not shown now: withdrawn, or held while a review is repeated."]}]
    assert "named-operator" not in json.dumps(layer)
    for c in W.CATEGORIES:
        assert not re.search(r"candidate|queue", c[1] + c[2], re.I), c[0]


def test_impact_changes_alone_are_not_reported_as_nothing_changed():
    prev = _layer([_rec("imp-a", "2024-01-01", attribution="CLAIMED")])
    curr = _layer([_rec("imp-a", "2024-01-01", attribution="ATTRIBUTED")])
    d = _derive(prev, T._bump(curr))
    assert d["global"] == [] and d["impact_layer"]
    quiet = _derive(prev, T._bump(prev))
    assert quiet["global"] == [{"category": "build_only", "notes": ["Rebuilt; nothing published changed."]}]


def test_the_published_state_reads_the_impact_artifacts_and_tolerates_their_absence():
    files = {"global/impacts.json": {"records": []}}
    state = W._published_state(lambda rel: files.get(rel))
    assert state["impacts"] == {"records": []} and state["regional_context"] is None
    assert W._published_state(lambda rel: None)["impacts"] is None


def test_a_malformed_impact_record_is_skipped_never_fatal():
    prev = _layer([_rec("imp-a", "2024-01-01")])
    curr = _layer([_rec("imp-a", "2024-01-01"), {"date": "2024-01-01"}, "not a record",
                   _rec("imp-b", "2024-05-01", evidence_confidence=None, attribution=None, ai_involvement=None)])
    layer = _impact(prev, curr)
    assert [it["impact_id"] for it in layer[0]["items"]] == ["imp-b"]


# --- the panel, as shipped (web/src/global/WhatsNew.tsx run in Node) ---------------------------------------

PANEL = {"wp": "global/WhatsNew.tsx", "wn": "global/whatsNewText.ts", "ev": "global/evidence.ts", "mf": "global/manifest.ts"}
RENDER = """
  globalThis.window = { location: { search: "", hash: "", pathname: "/" }, history: { pushState() {}, replaceState() {} },
                        addEventListener() {}, dispatchEvent() {} };
  const html = (d) => renderToStaticMarkup(React.createElement(wp.WhatsNewPanel, { data: d, failed: false, now: new Date("2026-11-12T12:00:00Z") }));
"""


def _blocks(html):
    """{system id: that system's part of the rendered panel}."""
    parts = html.split('data-system="')[1:]
    return {p.split('"', 1)[0]: p for p in parts}


@needs_bundler
def test_the_panel_links_a_record_outside_the_campaign_rule_and_never_inside_it(tmp_path_factory):
    prev = T._state(us=(T._system("us"), [T._event("us-old", "2022-02-03")]),
                    sa=(T._system("sa", campaign=T.ACTIVE), [T._event("sa-old", "2024-05-01")]))
    curr = T._bump(prev)
    curr["systems"]["us"]["events"]["events"].append(T._event(FACILITY_ID, "2023-02-23"))
    curr["systems"]["sa"]["events"]["events"].append(T._event("sa-2025-named-terminal-storm", "2025-01-10"))
    curr["systems"]["us"]["system"]["research_gaps"] = ["A gap."]
    data = json.loads(json.dumps(_derive(prev, curr)))
    out = run_ts(tmp_path_factory, PANEL, RENDER + """
      const item = input.data.systems.find((s) => s.system_id === "us").changes[0].items[0];
      return { html: html(input.data), problems: mf.whatsNewShapeProblems(input.data),
               href: wn.recordHref("us", item), none: wn.recordHref("us", { ...item, record_id: undefined }),
               anchor: ev.eventAnchor({ event_id: item.record_id, publication: null }, "us") };
    """, {"data": data})
    assert out["problems"] == []
    assert out["href"] == f"?sys=us#ev-{FACILITY_ID}" and out["none"] is None
    assert out["href"].endswith("#" + out["anchor"]), "the panel's link is not the record's own anchor"
    us, sa = _blocks(out["html"])["us"], _blocks(out["html"])["sa"]
    assert f'href="?sys=us#ev-{FACILITY_ID}"' in us
    assert 'href="?sys=us#tab-research"' in us and "Open Research coverage" in us
    assert "#ev-" not in sa and "named-terminal" not in sa and "sa-old" not in sa
    assert "10 Jan 2025" in sa, "the campaign system's row is still listed, as text"


@needs_bundler
def test_the_panel_says_first_release_once_and_tells_backfill_from_new_and_update_from_incident(tmp_path_factory):
    before_layer = T._state(us=(T._system("us"), []))
    first = json.loads(json.dumps(_derive(before_layer, T._bump(_layer(
        [_rec(f"imp-2024-01-{i:02d}-ukr-telecom-x{i}", f"2024-01-{i:02d}") for i in range(1, 12)])))))
    prev = _layer([_rec("imp-old", "2022-05-01", "2026-11-01", attribution="CLAIMED", category="MODERATE")])
    curr = _layer([_rec("imp-old", "2022-05-01", "2026-11-01", attribution="ATTRIBUTED", category="HIGH"),
                   _rec("imp-2023-backfill", "2023-12-12"), _rec("imp-2026-new", "2026-11-10")])
    later = json.loads(json.dumps(_derive(prev, T._bump(curr))))
    quiet = json.loads(json.dumps(_derive(prev, T._bump(prev))))
    out = run_ts(tmp_path_factory, PANEL, RENDER + """
      return { first: html(input.first), later: html(input.later), quiet: html(input.quiet),
               problems: [input.first, input.later, input.quiet].map(mf.whatsNewShapeProblems) };
    """, {"first": first, "later": later, "quiet": quiet})
    assert out["problems"] == [[], [], []]
    assert out["first"].count("First release of the impact layer") == 1
    assert "imp-2024" not in out["first"] and "Jan 2024" not in out["first"], "a first release listed its records"
    later_html = out["later"]
    assert "12 Dec 2023" in later_html and "historical record found by research, not a new event" in later_html
    assert re.search(r"10 Nov 2026[^<]*new event", later_html)
    assert not re.search(r"12 Dec 2023[^<]*— new event", later_html), "a backfill read as a new event"
    assert "attribution: Claimed → Attributed (existing record, not a new incident)" in later_html
    assert "evidence confidence: Moderate → High" in later_html
    assert "Some are historical records found by research and some are new events" in later_html
    assert "Impact layer: no published change." in out["quiet"]


@needs_bundler
def test_the_panel_shows_no_impact_block_when_the_build_has_no_impact_layer(tmp_path_factory):
    prev = T._state(us=(T._system("us"), [T._event("us-a", "2022-02-03")]))
    data = json.loads(json.dumps(_derive(prev, T._bump(prev))))
    legacy = {k: v for k, v in data.items() if k != "impact_layer"}       # a file from before iteration 22
    out = run_ts(tmp_path_factory, PANEL, RENDER + """
      return { now: html(input.data), legacy: html(input.legacy), problems: mf.whatsNewShapeProblems(input.legacy) };
    """, {"data": data, "legacy": legacy})
    assert out["problems"] == []
    for page in (out["now"], out["legacy"]):
        assert "Impact layer" not in page
