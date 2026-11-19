"""Iteration 22: shared record filters and the safe CSV export, executed as shipped.

The filter model (web/src/global/recordFilters.ts), the CSV builder (recordCsv.ts), the country
page's use of both (countryFilters.ts) and the filter bar (RecordFilterBar.tsx) are bundled from
web/src with esbuild and run in Node, the way tests/test_iteration21_testarch.py does it, so the
mutation campaign (scripts/mutation_campaign.py, ITER22_FILTER_MUTATIONS) breaks the code a reader's
browser runs. The CSV is read back with Python's own csv module: an independent RFC 4180 reader.

What is pinned here is what must never regress quietly:
- the export carries only its allow-listed columns, whatever a record carries;
- a record under attack-campaign safeguards, or abstracted to its country, exports no place,
  facility, operator, source headline or later status;
- a cell a spreadsheet would run as a formula is made text;
- a filter never hides a record silently, and a link's unknown filter or value is said, not obeyed;
- the address keeps the filters, so a reload shows the same list.

The browser-level proof (a real download's bytes, reload, Back, the phone sheet) is in
web/e2e/filters.e2e.ts; the wider unit tests are in web/src/global/record*.test.ts.
"""
import csv
import io
import json
import re
from pathlib import Path

import pytest

from tests.test_iteration21_testarch import SRC, WEB, needs_bundler, needs_payload, run_ts

MODS = {"rf": "global/recordFilters.ts", "rc": "global/recordCsv.ts", "cf": "global/countryFilters.ts"}
BAR = {"rf": "global/recordFilters.ts", "bar": "global/RecordFilterBar.tsx"}
TODAY = "2026-11-19"
SECRET = "SENTINEL-NOT-FOR-EXPORT"
PLACE_COLUMNS = ("region_code", "region_name", "regions_affected", "facility", "operator", "source_headlines",
                 "recovery_research_status", "recovery_kind", "recovery_date")


def _read(rel):
    return json.loads((WEB / rel).read_text(encoding="utf-8"))


def _country_ids():
    return [s["id"] for s in _read("global/manifest.json")["systems"] if s["kind"] == "country"]


def _system(sid):
    return _read(f"systems/{sid}/system.json")


def _events(sid):
    return _read(f"systems/{sid}/events.json")["events"]


def _rows(text):
    """The file as a spreadsheet reads it: BOM off, then RFC 4180."""
    assert text.startswith("﻿"), "no byte-order mark: Excel would misread Arabic and Persian"
    data = list(csv.reader(io.StringIO(text[1:], newline="")))
    head, body = data[0], data[1:]
    assert all(len(r) == len(head) for r in body), "a row has a different number of cells from the header"
    return head, [dict(zip(head, r)) for r in body]


def _plant(e):
    """A served record with something planted in every field the export must not carry, and in
    fields no served record has (an export that dumped the record would carry them)."""
    e = json.loads(json.dumps(e))
    e["facility_name_local"] = SECRET
    e["threshold_basis"] = SECRET
    if e.get("capacity_affected"):
        e["capacity_affected"]["source_says"] = SECRET
    e["review"]["process"] = SECRET
    e["review"]["source_access"] = SECRET
    for s in e["sources"]:
        s["internal_note"] = SECRET
        s["reviewer_rationale"] = SECRET
    e.update({"reviewer_rationale": SECRET, "candidate_id": SECRET, "lat": 51.5007, "lon": -0.1246,
              "coordinates": [51.5007, -0.1246]})
    return e


# ---------------- the CSV: allow-list ----------------

@needs_bundler
@needs_payload
def test_csv_exports_only_the_allow_listed_columns_whatever_a_record_carries(tmp_path_factory):
    sys_ = _system("us")
    events = [_plant(e) for e in _events("us")[:12]]
    out = run_ts(tmp_path_factory, MODS, """
      return { csv: rc.countryEventsCsv(input.events, input.sys), columns: [...rc.COUNTRY_EVENT_COLUMNS] };
    """, {"events": events, "sys": sys_})
    head, rows = _rows(out["csv"])
    assert head == out["columns"]
    assert len(rows) == len(events)
    assert SECRET not in out["csv"], "a field outside the allow-list reached the file"
    assert "51.5007" not in out["csv"] and "0.1246" not in out["csv"], "a coordinate reached the file"
    for name in head:
        assert not re.search(r"(^|_)(lat|lon|lng|latitude|longitude)(_|$)|coord|geometry|reviewer|rationale|candidate|process|distance", name), name
    # The citations cell is publisher, date and address, never a raw source object.
    for r, e in zip(rows, events):
        assert "{" not in r["citations"] and "link_check" not in r["citations"] and "opened" not in r["citations"]
        for s in e["sources"]:
            assert s["url"] in r["citations"]


@needs_bundler
@needs_payload
def test_csv_exports_exactly_the_list_it_is_given(tmp_path_factory):
    """Only the shown list is read, so nothing that is not on screen (and nothing held in review,
    which is never served) can be exported. The Python side works out the expected ids itself."""
    checked = 0
    for sid in _country_ids():
        events = _events(sid)
        causes = sorted({e["cause"] for e in events})
        if len(causes) < 2:
            continue
        want = sorted(e["event_id"] for e in events if e["cause"] == causes[0] and not e.get("publication"))
        out = run_ts(tmp_path_factory, MODS, """
          const { defs } = cf.countryFilters(input.sys, input.events);
          const state = { choices: { cause: [input.cause] }, dates: {} };
          const shown = rf.applyFilters(input.events, defs, state, input.today);
          const files = cf.countryExport(input.sys, shown, input.events.length, rf.describeFilters(defs, state, input.today), null, input.today);
          return { csv: files.csv, readme: files.readme, name: files.csvName, readmeName: files.readmeName, shown: shown.length };
        """, {"sys": _system(sid), "events": events, "cause": causes[0], "today": TODAY})
        _, rows = _rows(out["csv"])
        total = sum(1 for e in events if e["cause"] == causes[0])
        assert out["shown"] == total == len(rows), sid
        assert sorted(r["record_id"] for r in rows if r["record_id"]) == want, sid
        assert all(r["cause"] == causes[0] for r in rows)
        assert out["name"] == f"edm-{sid}-events-{_system(sid)['as_of']}.csv"
        assert out["readmeName"] == f"edm-{sid}-events-{_system(sid)['as_of']}-README.txt"
        # The README carries what the CSV cannot: the count, the filter, the caveat.
        assert f"Records in this file: {total} of {len(events)}" in out["readme"]
        assert "not a census" in out["readme"] and "not comparable across countries" in out["readme"]
        assert f"leave out {len(events) - total}" in out["readme"]
        checked += 1
    assert checked >= 3, "too few served systems have two causes to check anything"


# ---------------- the CSV: safeguarded and abstracted records ----------------

@needs_bundler
@needs_payload
def test_csv_campaign_covered_records_export_no_place_facility_operator_or_status(tmp_path_factory):
    covered = 0
    for sid in _country_ids():
        events = [e for e in _events(sid) if e.get("publication")]
        if not events:
            continue
        out = run_ts(tmp_path_factory, MODS, "return rc.countryEventsCsv(input.events, input.sys);",
                     {"events": events, "sys": _system(sid)})
        _, rows = _rows(out)
        assert len(rows) == len(events)
        for e in events:
            for name in (e.get("facility_name"), e.get("facility_name_local"), e.get("operator"),
                         e.get("region_name"), e.get("region_code")):
                if name:
                    assert name not in out, f"{sid}: the file names {name!r}, which the safeguards withhold"
        for r in rows:
            covered += 1
            for col in PLACE_COLUMNS:
                assert r[col] == "", (sid, col, r[col])
            assert "attack-campaign safeguards" in r["publication_note"]
            assert r["date"] and r["asset_class"] and r["cause"]
            assert r["placement"] == "National, under safeguards"
    assert covered > 0, "no served record is under the campaign rule, so this checks nothing"


@needs_bundler
@needs_payload
def test_csv_a_covered_record_whose_own_text_names_its_facility_exports_no_text(tmp_path_factory):
    """Saudi Arabia's older records name the facility in the id, the summary and the citation
    addresses. The file lists them the way the cross-country lists do: date, class and cause."""
    events = [e for e in _events("sa") if e.get("publication")]
    assert events
    out = run_ts(tmp_path_factory, MODS, "return rc.countryEventsCsv(input.events, input.sys);",
                 {"events": events, "sys": _system("sa")})
    _, rows = _rows(out)
    for r in rows:
        assert r["record_id"] == "" and r["summary"] == "" and r["reported_effect"] == "" and r["citations"] == ""
        assert "not exported either" in r["publication_note"]
    for e in events:
        assert e["event_id"] not in out
        for s in e["sources"]:
            assert s["url"] not in out


@needs_bundler
@needs_payload
def test_csv_an_abstracted_attack_record_keeps_its_text_and_exports_no_place(tmp_path_factory):
    """A made record: no system under a country-level attack rule has a published attack yet."""
    systems = {sid: _system(sid) for sid in _country_ids()}
    sid = next(s for s, v in sorted(systems.items()) if (v["geography"].get("precision_policy") or {}).get("kinetic") == "country")
    e = json.loads(json.dumps(_events("us")[0]))
    e.update({"event_id": f"{sid}-2026-03-01-refinery-attack-a1b2c3", "date": "2026-03-01", "asset_class": "refinery",
              "cause": "kinetic_strike", "geography_precision": "country", "region_code": None,
              "region_name": "PLANTED REGION", "facility_name": "PLANTED FACILITY", "operator": "PLANTED OPERATOR",
              "regions_affected": ["XX-01"], "summary": "An attack on a refinery was reported.",
              "effect": "Output was reported cut.", "publication": None,
              "sources": [{"url": "https://example.org/report", "publisher": "Example", "title_original": "PLANTED HEADLINE"}]})
    out = run_ts(tmp_path_factory, MODS, "return rc.countryEventsCsv([input.e], input.sys);", {"e": e, "sys": systems[sid]})
    _, rows = _rows(out)
    r = rows[0]
    assert "PLANTED" not in out and "XX-01" not in out
    assert r["record_id"] == e["event_id"] and r["summary"] == e["summary"]
    assert "https://example.org/report" in r["citations"]
    for col in PLACE_COLUMNS:
        assert r[col] == "", col
    assert "attack-campaign safeguards" in r["publication_note"]


@needs_bundler
def test_csv_an_abstracted_impact_record_exports_no_region_or_headline(tmp_path_factory):
    base = {"impact_id": "imp-2024-01-01-xxx-electricity-attack-a1b2c3", "record_kind": "disruption", "date": "2024-01-01",
            "country_a3": "XXX", "country_name": "Example", "admin1": {"code": "XX-01", "name": "PLANTED REGION"},
            "geographic_precision": "admin1", "domain": "energy", "sector": "electricity", "cause_family": "cyber",
            "summary": "A disruption was reported.", "lat": 1.2345, "operator": SECRET, "review": {"rationale": SECRET},
            "sources": [{"url": "https://example.org/a", "publisher": "Example", "title_original": "PLANTED HEADLINE"}]}
    cases = [dict(base, publication_policy="country_abstracted"), dict(base, cause_family="kinetic"),
             dict(base, cause_family="sabotage", publication_policy="standard"), dict(base, contributing_factors=["kinetic"])]
    out = run_ts(tmp_path_factory, MODS, """
      return { abstracted: rc.impactRecordsCsv(input.cases), standard: rc.impactRecordsCsv([input.base]), columns: [...rc.IMPACT_COLUMNS] };
    """, {"cases": cases, "base": base})
    head, rows = _rows(out["abstracted"])
    assert head == out["columns"] and len(rows) == len(cases)
    assert "PLANTED" not in out["abstracted"] and "XX-01" not in out["abstracted"]
    for r in rows:
        assert r["admin1_code"] == "" and r["admin1_name"] == "" and r["source_headlines"] == ""
        assert r["geographic_precision"] == "country"
        assert "abstraction rule" in r["publication_note"]
    # A standard, non-kinetic record keeps its first-level region; nothing outside the columns leaves.
    _, std = _rows(out["standard"])
    assert std[0]["admin1_code"] == "XX-01" and std[0]["publication_note"] == ""
    for text in (out["abstracted"], out["standard"]):
        assert SECRET not in text and "1.2345" not in text


# ---------------- the CSV: format ----------------

@needs_bundler
@needs_payload
def test_csv_a_formula_in_any_cell_reaches_a_spreadsheet_as_text(tmp_path_factory):
    e = json.loads(json.dumps(_events("us")[0]))
    e.update({"summary": "=cmd|' /C calc'!A0", "operator": "@SUM(A1:A9)", "facility_name": "+1+1", "effect": "-2+3",
              "region_name": "\t=1"})
    e["sources"] = [{"url": "https://example.org/a", "publisher": "=HYPERLINK(\"http://x\")"}]
    out = run_ts(tmp_path_factory, MODS, """
      return { csv: rc.countryEventsCsv([input.e], input.sys),
               cells: ["=1+1", "+1", "-1", "@x", "\\t=1", "\\r=1", "2024-01-01", "a=b", "plain"].map(rc.csvCell) };
    """, {"e": e, "sys": _system("us")})
    _, rows = _rows(out["csv"])
    r = rows[0]
    for col in ("summary", "operator", "facility", "reported_effect", "region_name", "citations"):
        assert r[col].startswith("'"), f"{col} would run as a formula: {r[col]!r}"
    for cell in out["cells"][:6]:
        assert cell.lstrip('"').startswith("'"), cell
    assert out["cells"][6:] == ["2024-01-01", "a=b", "plain"], "ordinary values must not be altered"


@needs_bundler
@needs_payload
def test_csv_is_rfc_4180_with_a_bom_and_survives_awkward_text(tmp_path_factory):
    e = json.loads(json.dumps(_events("us")[0]))
    awkward = 'He said "no", then:\r\nline two, with a comma'
    e["summary"] = awkward
    kw = [x for x in _events("kw") if any(s.get("title_original") for s in x["sources"])]
    assert kw, "no served record carries an Arabic headline"
    out = run_ts(tmp_path_factory, MODS, """
      return { us: rc.countryEventsCsv([input.e], input.us), kw: rc.countryEventsCsv(input.kw, input.kwSys) };
    """, {"e": e, "us": _system("us"), "kw": kw, "kwSys": _system("kw")})
    assert out["us"].encode("utf-8")[:3] == b"\xef\xbb\xbf"
    assert out["us"].endswith("\r\n")
    _, rows = _rows(out["us"])
    assert rows[0]["summary"] == awkward
    _, rows = _rows(out["kw"])
    want = " | ".join(s["title_original"] for s in kw[0]["sources"] if s.get("title_original"))
    assert rows[0]["source_headlines"] == want
    assert re.search(r"[؀-ۿ]", rows[0]["source_headlines"])


# ---------------- filters ----------------

@needs_bundler
@needs_payload
def test_filters_combine_and_never_widen_the_list(tmp_path_factory):
    """Two filters together show only records both admit; the expected ids are worked out here."""
    events = _events("us")
    causes = sorted({e["cause"] for e in events})
    classes = sorted({e["asset_class"] for e in events})
    out = run_ts(tmp_path_factory, MODS, """
      const { defs } = cf.countryFilters(input.sys, input.events);
      const res = {};
      for (const cause of input.causes) for (const cls of input.classes) {
        const state = { choices: { cause: [cause], class: [cls] }, dates: { date: { from: "2023-01-01", to: "2024-12-31" } } };
        res[cause + "|" + cls] = rf.applyFilters(input.events, defs, state, input.today).map((e) => e.event_id);
      }
      return { res, ids: defs.map((d) => d.id) };
    """, {"sys": _system("us"), "events": events, "causes": causes, "classes": classes, "today": TODAY})
    assert out["ids"][:3] == ["date", "cause", "class"]
    some = 0
    for cause in causes:
        for cls in classes:
            # A month-precision date ("2024-04") covers its whole month.
            want = [e["event_id"] for e in events if e["cause"] == cause and e["asset_class"] == cls
                    and e["date"][:7] <= "2024-12" and (e.get("date_end") or e["date"])[:7] >= "2023-01"]
            assert out["res"][f"{cause}|{cls}"] == want, (cause, cls)
            some += len(want)
    assert some > 0


@needs_bundler
@needs_payload
def test_filters_a_links_unknown_value_or_filter_is_dropped_with_a_note_never_silently(tmp_path_factory):
    events = _events("us")
    known = sorted({e["cause"] for e in events})[0]
    out = run_ts(tmp_path_factory, MODS, """
      const { defs } = cf.countryFilters(input.sys, input.events);
      const run = (q) => { const d = rf.decodeFilters(q, defs); return { state: d.state, notes: d.notes, shown: rf.applyFilters(input.events, defs, d.state, input.today).length }; };
      return { mixed: run("?sys=us&f.cause=" + input.known + ",made_up_cause"), all_bad: run("f.cause=made_up_cause"),
               bad_id: run("f.sector=telecom"), bad_date: run("f.date=not-a-date"), clean: run("f.cause=" + input.known) };
    """, {"sys": _system("us"), "events": events, "known": known, "today": TODAY})
    n_known = sum(1 for e in events if e["cause"] == known)
    assert out["clean"] == {"state": {"choices": {"cause": [known]}, "dates": {}}, "notes": [], "shown": n_known}
    # The value it knows is kept; the one it does not is named in a note.
    assert out["mixed"]["state"]["choices"] == {"cause": [known]} and out["mixed"]["shown"] == n_known
    assert len(out["mixed"]["notes"]) == 1 and "made_up_cause" in out["mixed"]["notes"][0] and "Cause" in out["mixed"]["notes"][0]
    # Nothing it knows: the filter is off, every record is shown, and the page is told why.
    assert out["all_bad"]["state"] == {"choices": {}, "dates": {}} and out["all_bad"]["shown"] == len(events)
    assert len(out["all_bad"]["notes"]) == 1 and "made_up_cause" in out["all_bad"]["notes"][0]
    assert len(out["bad_id"]["notes"]) == 1 and "sector" in out["bad_id"]["notes"][0]
    assert out["bad_id"]["shown"] == len(events)
    assert len(out["bad_date"]["notes"]) == 1 and "Date" in out["bad_date"]["notes"][0]


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


@needs_bundler
@needs_payload
def test_filter_bar_always_says_how_many_records_are_shown_and_how_many_the_filters_hide(tmp_path_factory):
    events = _events("us")
    cause = sorted({e["cause"] for e in events})[0]
    n = sum(1 for e in events if e["cause"] == cause)
    assert 0 < n < len(events)
    out = run_ts(tmp_path_factory, dict(BAR, cf="global/countryFilters.ts"), """
      const { defs } = cf.countryFilters(input.sys, input.events);
      const render = (state, notes) => renderToStaticMarkup(React.createElement(bar.RecordFilterBar, {
        defs, state, onChange() {}, records: input.events, today: input.today, notes,
        shown: rf.applyFilters(input.events, defs, state, input.today).length }));
      return { off: render({ choices: {}, dates: {} }, []),
               on: render({ choices: { cause: [input.cause] }, dates: {} }, ["A note the reader must see."]) };
    """, {"sys": _system("us"), "events": events, "cause": cause, "today": TODAY})
    off, on = _text(out["off"]), _text(out["on"])
    assert f"Showing {len(events)} of {len(events)} published records." in off
    assert "The filters hide" not in off
    assert f"Showing {n} of {len(events)} published records." in on
    assert f"The filters hide {len(events) - n}." in on, "records are hidden and the page does not say so"
    assert f"Filters on: Cause: {_system('us')['taxonomy']['causes'][cause]}." in on
    assert "A note the reader must see." in on
    # The line is a live region and the clear control is there in both states.
    for html in (out["off"], out["on"]):
        assert re.search(r'<p class="rf-count[^"]*" role="status">', html)
        assert "Clear filters" in html
    assert re.search(r"<button[^>]*disabled[^>]*>Clear filters</button>", out["off"])
    assert not re.search(r"<button[^>]*disabled[^>]*>Clear filters</button>", out["on"])


@needs_bundler
@needs_payload
def test_country_address_keeps_the_filters_so_a_reload_shows_the_same_list(tmp_path_factory):
    events = _events("us")
    cause = sorted({e["cause"] for e in events})[-1]
    out = run_ts(tmp_path_factory, MODS, """
      const { defs } = cf.countryFilters(input.sys, input.events);
      const state = { choices: { cause: [input.cause] }, dates: { date: { preset: "1y" } } };
      const search = cf.countrySearch("us", "US-TX", rf.encodeFilters(defs, state));
      // A reload: all the page has is the address.
      const back = rf.decodeFilters(rf.filterQueryOf("?" + search), defs);
      const other = rf.encodeFilters(defs, { dates: { date: { preset: "1y" } }, choices: { cause: [input.cause] } });
      return { search, back: back.state, notes: back.notes, same: rf.encodeFilters(defs, back.state) === rf.encodeFilters(defs, state),
               stable: other === rf.encodeFilters(defs, state), bare: cf.countrySearch("us", null, "") };
    """, {"sys": _system("us"), "events": events, "cause": cause})
    assert out["search"] == f"sys=us&r=US-TX&f.cause={cause}&f.date=1y"
    assert out["back"] == {"choices": {"cause": [cause]}, "dates": {"date": {"preset": "1y"}}}
    assert out["notes"] == [] and out["same"] and out["stable"]
    assert out["bare"] == "sys=us"


@needs_bundler
@needs_payload
def test_a_link_to_a_record_the_filters_hide_names_exactly_the_filters_to_clear(tmp_path_factory):
    events = _events("us")
    causes = sorted({e["cause"] for e in events})
    target = next(e for e in events if e["cause"] != causes[0])
    out = run_ts(tmp_path_factory, MODS, """
      const { defs } = cf.countryFilters(input.sys, input.events);
      const state = { choices: { cause: [input.cause] }, dates: { date: { preset: "2022" } } };
      const hiding = rf.hidingFilters(input.target, defs, state, input.today);
      const cleared = rf.withoutFilters(state, hiding);
      return { hiding, cleared, visible: rf.applyFilters(input.events, defs, cleared, input.today).some((e) => e.event_id === input.target.event_id),
               before: rf.applyFilters(input.events, defs, state, input.today).some((e) => e.event_id === input.target.event_id) };
    """, {"sys": _system("us"), "events": events, "cause": causes[0], "target": target, "today": TODAY})
    assert out["before"] is False
    assert out["hiding"] == ["cause"], "only the filter that hides the record is cleared"
    assert out["cleared"] == {"choices": {}, "dates": {"date": {"preset": "2022"}}}
    assert out["visible"] is True


# ---------------- the country page's wiring (source guards) ----------------
# The view itself needs a browser; web/e2e/filters.e2e.ts runs it. These keep the campaign able to
# see the three lines that connect the tested modules to the page.

VIEW = (SRC / "global" / "CountryView.tsx")


@pytest.mark.repo_hygiene
def test_country_view_reads_its_filters_from_the_address_and_writes_them_back():
    src = VIEW.read_text(encoding="utf-8")
    assert "useState(() => filterQueryOf(window.location.search))" in src, "the filters are not read from the address on load"
    assert "countrySearch(id, region, filterQuery)" in src, "the address is written without the filters"
    assert re.search(r"const sync = \(\) => \{[^}]*setFilterQuery\(filterQueryOf\(window\.location\.search\)\)", src), \
        "Back and Forward do not restore the filters"


@pytest.mark.repo_hygiene
def test_country_view_exports_the_shown_list_and_no_other():
    src = VIEW.read_text(encoding="utf-8")
    assert "countryExport(bundle.system, shown, scope.length," in src
    assert not re.search(r"countryExport\(bundle\.system, (events|bundle\.events|scope),", src)
