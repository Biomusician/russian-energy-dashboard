"""Iteration 23 red-team fixes: the first-time user (H-), the map-first user (MU-) and the expert
analyst (AN-, V-) reports.

Each test runs the shipped TypeScript (bundled with esbuild, as test_iteration21_testarch does) or
reads the shipped source where the rule is structural, so the mutation campaign (pytest only) can
see a regression. The browser-level proof (clicking every system at the default view, keyboard
focus, the phone pages in a wide font) is in web/e2e/home.e2e.ts and the files it names.
"""
import json
import re

import pytest

from test_iteration21_testarch import ROOT, SRC, needs_bundler, run_ts
from test_iteration23_help import HELP, RENDER, _served

from pipeline import systems

WEB = ROOT / "web" / "public" / "data"
GLOBAL = SRC / "global"
HOME = {"hs": "global/homeSelection.ts", "si": "global/searchIndex.ts", "gl": "global/help/glossary.ts",
        "anchors": "global/help/anchors.ts"}


def _json(rel):
    return json.loads((WEB / rel).read_text(encoding="utf-8"))


def _code(rel):
    """Source without comments, so a rule is neither satisfied nor broken by prose."""
    text = (SRC / rel).read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    return re.sub(r"\{/\*.*?\*/\}", "", text, flags=re.S)


@pytest.fixture(scope="module")
def served():
    return {"manifest": _json("global/manifest.json"), "world": _json("global/world.geojson"),
            "regions": _json("regions.json")}


@pytest.fixture(scope="module")
def help_page(tmp_path_factory):
    if not (WEB / "global" / "help_facts.json").exists():
        pytest.skip("no built payload")
    out = run_ts(tmp_path_factory, HELP, RENDER + """
      return { page: render(input.method), glossary: glossary.GLOSSARY, start: glossary.START_HERE };
    """, _served())
    return out


# ---------------- Help (H-02, H-05, H-07, H-11) ----------------

@needs_bundler
def test_h02_help_names_both_home_map_modes(help_page):
    nav = help_page["page"]["sections"]["navigating-the-map"]
    assert "“Where to explore”, the default, colours only what one click does" in nav
    assert "“National energy”, the second mode, shades every country by a national energy figure" in nav
    assert "The world map is shaded by a national energy figure." not in help_page["page"]["all"]
    mon = next(g for g in help_page["glossary"] if g["id"] == "monitored-system")["plain"]
    assert "default mode" in mon and "National energy mode" in mon
    maps = next(s for s in help_page["start"] if s["title"].startswith("Maps mean"))["text"]
    assert "default mode colours only the monitored systems" in maps and "National energy mode" in maps


@needs_bundler
def test_h05_the_index_is_said_not_to_be_a_percentage(help_page, tmp_path_factory):
    assert "It is not a percentage. A reading on its scale is not a share of capacity lost" in help_page["page"]["sections"]["esdi"]
    esdi = next(g for g in help_page["glossary"] if g["id"] == "esdi")
    assert "It is not a percentage of capacity lost." in esdi["plain"] and "percentage" in esdi["aliases"]
    out = run_ts(tmp_path_factory, HOME, "return hs.THEATRE_MEANING;")
    assert "not a percentage" in out and not re.search(r"\d", out)


@needs_bundler
def test_h07_the_theatres_labels_are_defined_and_kept_apart_from_evidence_confidence(help_page):
    g = next((g for g in help_page["glossary"] if g["id"] == "theatre-evidence-labels"), None)
    assert g, "the theatre's confirmed / probable / possible labels are not in the glossary"
    assert {"confirmed", "probable", "possible"} <= set(g["aliases"])
    assert "not Evidence Confidence" in g["plain"] and "cannot be compared" in g["plain"]
    esdi = help_page["page"]["sections"]["esdi"]
    assert "These labels cannot be compared with Evidence Confidence." in esdi
    assert "confirmed means at least two different websites are cited" in esdi


@needs_bundler
def test_h11_help_says_where_a_csvs_caveats_travel(help_page):
    ex = help_page["page"]["sections"]["exports"]
    assert "The caveats are not inside the CSV." in ex
    assert "“About this file”, beside the download, gives a separate note" in ex
    assert "caveats inside the file" not in ex and "their caveats inside the file" not in help_page["page"]["all"]


# ---------------- search (H-03, MU-06) ----------------

SEARCH_JS = """
const all = [...si.VIEW_ENTRIES, ...si.CONCEPT_ENTRIES, ...si.HELP_ENTRIES];
const find = (q) => si.searchEntries(all, q, 12).map((h) => ({ key: h.entry.key, label: h.entry.label, action: h.entry.action, score: h.score }));
"""

H03_QUERIES = ["export", "csv", "download", "print", "what's new", "ranking", "probability", "provisional",
               "reviewer", "who reviewed", "coordinates", "targeting", "occupied", "percentage", "capacity lost", "corrections"]


@needs_bundler
def test_h03_every_term_help_explains_is_found_and_opens_help(tmp_path_factory):
    out = run_ts(tmp_path_factory, HOME, SEARCH_JS + """
      return { hits: Object.fromEntries(input.q.map((q) => [q, find(q)])),
               anchors: anchors.helpAnchors(),
               entries: si.HELP_ENTRIES.map((e) => ({ key: e.key, href: e.action.href, kind: e.kind })),
               reviewers: gl.GLOSSARY.find((g) => g.id === "reviewers") ?? null };
    """, {"q": H03_QUERIES})
    anchors = set(out["anchors"])
    assert {e["href"].split("#")[1] for e in out["entries"]} == anchors, "one search option per Help section"
    assert all(e["kind"] == "help" and e["href"].startswith("?view=help#") for e in out["entries"])
    for q, hits in out["hits"].items():
        assert any(h["action"].get("href", "").startswith("?view=help#") or h["action"]["type"] == "concept" for h in hits), \
            f"searching {q!r} finds nothing that explains it"
    r = out["reviewers"]
    assert r and "separate sessions of the same AI model" in r["plain"] and "reviewer" in r["aliases"]


@needs_bundler
def test_h03_matching_respects_word_boundaries(tmp_path_factory):
    out = run_ts(tmp_path_factory, HOME, SEARCH_JS + """
      const russia = [si.makeEntry({ key: "x", kind: "country", label: "Russia", sub: "", terms: ["Russia"], action: { type: "select", key: "RUS" } })];
      return { review: find("review").map((h) => h.label), fallback: si.searchEntries(russia, "ussia").map((h) => h.entry.label) };
    """)
    assert out["review"], "nothing found for review"
    assert "Research preview" not in out["review"], "'review' still matches inside 'preview'"
    assert out["review"][0].startswith("Reviewers")
    assert out["fallback"] == ["Russia"], "a match inside a word is still the fallback when nothing starts a word"


@needs_bundler
def test_mu06_sevastopol_finds_the_crimea_unit_from_the_served_regions(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, HOME, """
      const regions = input.regions.map((x) => ({ code: x.code, name: x.name, country: String(x.country ?? ""),
                                                  aliases: si.unitAliases(x.name, x.natural_earth_name) }));
      const e = si.theatreRegionEntries(regions, "Russia, Belarus & Crimea");
      return si.searchEntries(e, "Sevastopol").map((h) => ({ label: h.entry.label, sub: h.entry.sub, href: h.entry.action.href }));
    """, served)
    crimea = next(r for r in served["regions"] if r["country"] == "UA")
    assert out and out[0]["href"] == f"?sys=ru&r={crimea['code']}"
    assert out[0]["sub"].startswith("Occupied unit, internationally Ukrainian") and "Region of Russia" not in out[0]["sub"]
    search = (GLOBAL / "searchIndex.ts").read_text(encoding="utf-8")
    assert "aliases: unitAliases(x.name, x.natural_earth_name)" in search, "the loader drops the boundary source's names"


# ---------------- the home (MU-01, MU-02, MU-03, MU-04, MU-05, MU-07, H-08, H-10) ----------------

@needs_bundler
def test_mu01_every_small_system_gets_one_neutral_marker_and_a_shared_click_is_a_choice(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, HOME, """
      const m = input.manifest;
      const idx = hs.indexWorld(input.world);
      const fc = hs.smallSystemMarkers(m);
      const small = fc.features.map((f) => f.properties.system_id);
      const props = fc.features.map((f) => f.properties);
      const big = m.systems.find((s) => s.kind === "country" && !small.includes(s.id));
      const bigProps = { system_id: big.id, name: big.name, status: "normal" };
      const near = hs.pickMany({ core: props, near: props, under: [] }, m);
      const one = hs.pickMany({ core: [props[0]], near: props, under: [] }, m);
      // Off a dot, on a large monitored neighbour: that neighbour, never a choice.
      const neighbour = hs.pickMany({ core: [], near: props, under: [bigProps] }, m);
      // On a dot over a neighbour: the dot and the neighbour, as a choice.
      const onDot = hs.pickMany({ core: [props[0]], near: props, under: [bigProps] }, m);
      // Off a dot, on the sea: the dots in reach.
      const sea = hs.pickMany({ core: [], near: props, under: [] }, m);
      return { fc, small, near, one, big: big.id, neighbour, onDot: onDot.kind === "near" ? hs.unitsOf(onDot.key, m) : null,
               sea: sea.kind === "near" ? hs.unitsOf(sea.key, m) : null, card: near && near.kind === "near" ? hs.cardFor(near.key, idx, m) : null,
               units: near && near.kind === "near" ? hs.unitsOf(near.key, m) : [] };
    """, served)
    m = served["manifest"]
    spans = {s["id"]: max(s["bounds"][2] - s["bounds"][0], s["bounds"][3] - s["bounds"][1]) for s in m["systems"] if s.get("bounds")}
    smallest = min(spans, key=spans.get)
    assert smallest in out["small"], "the smallest monitored system has no marker"
    assert sorted(out["small"]) == sorted(s for s, v in spans.items() if v < 4)
    for f in out["fc"]["features"]:
        assert set(f["properties"]) == {"system_id", "name", "status"}, "a marker carries something beyond what a click means"
        b = next(s["bounds"] for s in m["systems"] if s["id"] == f["properties"]["system_id"])
        assert f["geometry"]["coordinates"] == [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]
    assert out["one"]["kind"] == "one" and out["one"]["props"]["system_id"] == out["small"][0]
    assert out["near"]["kind"] == "near" and sorted(out["units"]) == sorted(out["small"])
    assert out["neighbour"]["kind"] == "one" and out["neighbour"]["props"]["system_id"] == out["big"], \
        "a click off a dot on a large monitored place must open that place"
    assert sorted(out["onDot"]) == sorted([out["small"][0], out["big"]])
    assert sorted(out["sea"]) == sorted(out["small"])
    names = {s["id"]: s["name"] for s in m["systems"]}
    assert [a["label"] for a in out["card"]["links"]] == sorted(names[s] for s in out["small"]), "a choice is alphabetical"
    assert [a["href"] for a in out["card"]["links"]] == [f"?sys={s}" for s in sorted(out["small"], key=lambda s: names[s])]
    assert not re.search(r"\d", out["card"]["status"] + " ".join(out["card"]["lines"]))


def test_mu01_the_markers_are_drawn_in_the_monitored_colour_in_the_default_mode_only():
    world = _code("global/WorldContext.tsx")
    assert "markers={explore ? markers : null}" in world
    assert "color: MAP_COLOURS.monitored" in world
    simple = _code("global/SimpleMap.tsx")
    assert 'm.addLayer({ id: "markers-hit", type: "circle"' in simple
    assert 'core: at("markers"), near: at("markers-hit")' in simple and "onPickMany(hits, { touch })" in simple


def test_mu02_a_phone_group_zoom_keeps_little_padding_and_show_on_map_scrolls_to_the_map():
    simple = _code("global/SimpleMap.tsx")
    assert "clientWidth < 600 ? FIT_PADDING / 2 : FIT_PADDING * 2" in simple
    stage = _code("global/HomeStage.tsx")
    assert 'if (narrow) stageRef.current?.querySelector(".home-stage-map")?.scrollIntoView(' in stage


def test_mu03_mu07_a_choice_from_the_list_the_search_or_a_restored_entry_focuses_the_card():
    stage = _code("global/HomeStage.tsx")
    assert "focus: opts.fromList" in stage, "a choice from the list or the search no longer moves focus"
    assert "if (!initial.ret) { if (initial.focus) focusCardHeading(); return; }" in stage, "Back with no control to return to leaves focus on the body"
    assert 'document.getElementById("sel-card-title")?.focus();' in stage
    card = _code("global/SelectionCard.tsx")
    assert 'id="sel-card-title" className="sel-card-title" tabIndex={-1}' in card


def test_mu04_the_a_to_z_list_is_one_vertical_column():
    css = (SRC / "styles" / "home.css").read_text(encoding="utf-8")
    rule = re.search(r"\.hp-az-list \{([^}]*)\}", css).group(1)
    assert "columns" not in rule, "the A to Z list is laid out in columns again"
    assert "overflow-x: hidden" in rule


@needs_bundler
def test_mu05_russia_chosen_as_a_whole_is_partly_monitored_and_a_map_click_keeps_its_own_status(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, HOME, """
      const idx = hs.indexWorld(input.world);
      const m = input.manifest;
      const [part] = [...idx.partOf.keys()];
      const opt = si.countryEntries(idx, m).find((e) => e.key === "country:" + part);
      return { part, list: hs.cardFor(part, idx, m), map: hs.cardFor(part, idx, m, undefined, true), sub: opt.sub };
    """, served)
    assert out["part"] == "RUS"
    assert out["list"]["status"].startswith("Partly monitored, in the ")
    assert out["sub"].startswith(out["list"]["status"]), "the card and the search option say different things"
    assert out["list"]["lines"][0].startswith("Part of Russia is monitored in the ")
    assert out["map"]["status"] == "Outside the monitored area"
    assert out["map"]["lines"][0].startswith("This part of Russia lies outside the area monitored")


@needs_bundler
def test_h08_a_build_date_is_labelled_as_a_build_date(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, HOME, """
      const m = input.manifest;
      return m.systems.filter((s) => s.kind === "country").map((s) => hs.cardFor(s.id, null, m).lines);
    """, served)
    for lines in out:
        assert any(line.startswith("Site built ") for line in lines)
        assert not any("Data as of" in line for line in lines)
    for rel in ("global/GlobalHome.tsx", "global/help/HelpPage.tsx", "global/homeSelection.ts"):
        assert "Data as of" not in _code(rel) and "data as of" not in _code(rel), rel
    assert "Built {fmtDate(dataDay)}" in _code("global/GlobalHome.tsx")


@needs_bundler
def test_an08_compare_shows_the_record_date_never_the_build_date(tmp_path_factory, served):
    m = served["manifest"]
    out = run_ts(tmp_path_factory, {"cmp": "global/compare.ts"}, """
      const cols = input.manifest.systems.map((entry) => ({ entry, system: null }));
      return cmp.compareRows(cols, null, input.manifest).find((r) => r.id === "as_of");
    """, served)
    assert out["label"] == "Record reviewed"
    for s, cell in zip(m["systems"], out["cells"]):
        if s["kind"] == "theatre":
            assert cell["kind"] == "not_applicable", s["id"]
        elif s["record_reviewed"]:
            d = s["record_reviewed"]
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            assert cell["text"] == f"{int(d[8:10])} {months[int(d[5:7]) - 1]} {d[:4]}", s["id"]
        else:
            assert cell["text"] == "No qualifying record yet", s["id"]
    assert any(s.get("record_reviewed") and s["record_reviewed"] != s["as_of"] for s in m["systems"]), "nothing to tell apart"


@needs_bundler
def test_h10_the_national_table_tells_an_impact_record_country_from_context_only(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, {"nc": "global/NationalContext.tsx"}, """
      const present = new Set(input.manifest.impact_presence.countries);
      const row = (a3) => ({ a3, name: a3, system_id: null });
      const absent = ["ZZZ"].find((a) => !present.has(a));
      return { imp: nc.nationalStatus(row([...present][0]), new Set(), present, {}),
               ctx: nc.nationalStatus(row(absent), new Set(), present, {}) };
    """, served)
    assert out == {"imp": "Impact records, not monitored", "ctx": "Context only"}
    assert "impactRecords={new Set(manifest?.impact_presence?.countries ?? [])}" in _code("global/GlobalHome.tsx")


# ---------------- the theatre (H-06, H-09, AN-09, V-01) ----------------

@needs_bundler
def test_h06_every_list_of_theatre_records_says_where_they_come_from(tmp_path_factory):
    out = run_ts(tmp_path_factory, {"ui": "components/ui.tsx"}, """
      return { note: ui.THEATRE_RECORDS_NOTE, html: renderToStaticMarkup(React.createElement(ui.TheatreRecordsNote)) };
    """)
    assert "did not pass the three-role review" in out["note"] and "They are not Evidence Confidence." in out["note"]
    assert 'href="?view=help#g-theatre-evidence-labels"' in out["html"]
    tabs = _code("components/tabs.tsx")
    assert tabs.count("<TheatreRecordsNote />") >= 2, "a list of theatre records lost its provenance line"


def test_h09_the_index_and_recovery_help_is_reachable_on_a_phone_and_from_the_inspector():
    ribbon = _code("components/Ribbon.tsx")
    help_line = re.search(r'<p className="ribbon-help">(.*?)</p>', ribbon, re.S)
    assert help_line, "the phone's way to Help is gone from the expandable panel"
    assert 'anchor="esdi"' in help_line.group(1) and 'anchor="recovery"' in help_line.group(1)
    assert ribbon.index('className="ribbon-help"') > ribbon.index('id="ribbon-detail"'), "it must sit inside the expandable panel"
    css = (SRC / "theme.css").read_text(encoding="utf-8")
    assert re.search(r"@media \(max-width: 600px\) \{ \.ribbon-help \{ display: block; \} \}", css)
    assert '<LearnMore anchor="esdi"' in _code("components/Inspector.tsx")


def test_an09_the_ribbon_peak_is_labelled_as_the_weekly_reconstructions():
    ribbon = _code("components/Ribbon.tsx")
    assert "title={`The highest point of the weekly reconstruction to date" in ribbon
    assert ">weekly peak<" in ribbon and "highest value of the index to date" not in ribbon


def test_v01_the_crimea_sentence_is_never_folded_away():
    panel = _code("components/MapPanel.tsx")
    assert panel.index('className="scope-crimea"') < panel.index('className="scope-more"')
    css = (SRC / "theme.css").read_text(encoding="utf-8")
    rule = re.search(r'html\[data-chrome="compact"\] \.map-scope-note \{([^}]*)\}', css).group(1)
    assert "max-height" not in rule, "the compact scope note is cut to a height again"
    assert 'html[data-chrome="compact"] .map-scope-note .scope-more { display: none; }' in css


# ---------------- country and group pages (AN-02, AN-03, AN-04, AN-07, AN-10, AN-11) ----------------

def test_an02_a_capped_list_never_points_at_a_page_that_does_not_list_the_rest():
    wn = _code("global/WhatsNew.tsx")
    assert "on the country page" not in wn and "and more, not listed here" in wn


@needs_bundler
def test_an03_the_reporting_line_compares_no_counts_and_names_each_systems_own_environment(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, {"home": "global/GlobalHome.tsx", "mf": "global/manifest.ts"}, """
      const m = input.manifest;
      return { line: home.reportingLine(m),
               each: m.systems.filter((s) => s.kind === "country").map((s) => `${s.name}: ${mf.labelFor(mf.ENVIRONMENT_LABEL, s.reporting_environment).toLowerCase()}`) };
    """, served)
    assert not re.search(r"\b(fewer|more|most|less)\b[^.;]*\brecords?\b", out["line"], re.I), out["line"]
    for e in out["each"]:
        assert e in out["line"], e


@needs_bundler
def test_an04_a_campaign_overview_and_its_recorded_line_never_contradict(tmp_path_factory):
    out = run_ts(tmp_path_factory, {"co": "global/countryOverview.ts"}, """
      const sys = { name: "Synthetic", event_summary: { recorded_events: 1 },
        campaign_state: { state: "ACTIVE_KINETIC_CAMPAIGN" }, publication_policy: { withheld_records: 0 },
        research_log: { passes: [{ kind: "systematic", date: "2026-11-01", under_review: true }] },
        research_freshness: { lane_states: {} }, geography: { precision_policy: { kinetic: "country" } } };
      return co.overviewText(co.countryOverview(sys, { state: "not_loaded" }, null)).join(" ");
    """)
    assert "how many records are in review" in out
    assert not re.search(r"\bwhether\b[^.]*\breview", out), "the overview withholds that review continues, which the page says"
    view = _code("global/CountryView.tsx")
    assert "Additional candidates remain under review and are not shown." in view


@needs_bundler
def test_an07_the_gulf_card_reads_where_every_record_is_placed(tmp_path_factory):
    gulf = _json("global/gulf.json")
    for s in gulf["systems"]:
        p = _json(f"systems/{s['system_id']}/system.json")
        assert s["other_records_placed"] == ((p["geography"].get("precision_policy") or {}).get("other") or "admin1"), s["system_id"]
    whole = [s["name"] for s in gulf["systems"] if s["other_records_placed"] == "country"]
    assert whole, "no served system places every record at country level; the case is not exercised"
    out = run_ts(tmp_path_factory, {"gp": "global/groupPrecision.ts"}, """
      return { card: gp.attackPlacementText("country", "country"), plain: gp.attackPlacementText("country"),
               rules: gp.precisionRulesText(input.systems).body };
    """, {"systems": gulf["systems"]})
    assert "Every other record too is recorded for the country as a whole." in out["card"]
    assert "first-level region at most" not in out["card"] and "first-level region at most" in out["plain"]
    for n in whole:
        assert n in out["rules"].split("Records that are not attacks")[1], n
    assert "attackPlacementText(s.attack_records_placed, s.other_records_placed)" in _code("global/GroupView.tsx")


@needs_bundler
def test_an10_a_country_first_screen_reads_the_manifests_presence_before_the_corpus(tmp_path_factory, served):
    impacts = _json("global/impacts.json")
    m = served["manifest"]
    for s in m["systems"]:
        if s["kind"] == "country":
            reg = next(x for x in systems.SYSTEMS if x["id"] == s["id"])
            assert s["admin0_a3"] == list(reg["admin0_a3"]), s["id"]
    out = run_ts(tmp_path_factory, {"co": "global/countryOverview.ts", "ci": "global/countryImpactModel.ts"}, """
      const m = input.manifest;
      return m.systems.filter((s) => s.kind === "country").map((s) => {
        const got = ci.countryImpacts(input.impacts, s.id);
        return { id: s.id, listed: co.listedPresence(m, s), records: got.records.length, attempts: got.attempts.length,
                 line: co.impactLine(s.name, { state: "not_loaded" }, co.listedPresence(m, s)) };
      });
    """, {**served, "impacts": impacts})
    seen = set()
    for r in out:
        want = "records" if r["records"] else "attempts" if r["attempts"] else "none"
        assert r["listed"] == want, r
        seen.add(want)
        if want == "none":
            assert r["line"].startswith("no impact record yet"), r
        assert "reviewed impact records" not in r["line"] or want == "records", r
    assert "none" in seen and "records" in seen, "the served data must exercise both"


@needs_bundler
def test_an11_the_atlas_span_keeps_the_records_own_precision(tmp_path_factory):
    impacts = _json("global/impacts.json")
    out = run_ts(tmp_path_factory, {"am": "global/impacts/atlasModel.ts", "model": "global/impacts/model.ts"}, """
      const P = input.impacts;
      const synth = { ...P, records: [{ ...P.records[0], date: "2022-01", date_end: null, record_kind: "disruption" }] };
      return { served: am.corpusSummary(P), synth: am.corpusSummary(synth),
               earliest: model.disruptions(P).map((r) => [model.startDay(r), r.date]).sort()[0] };
    """, {"impacts": impacts})
    assert out["synth"]["first"] == "2022-01", "a month-precision record is given a day"
    day, own = out["earliest"]
    assert out["served"]["first"] in (own, day) and (own == day or out["served"]["first"] == own)


# ---------------- smaller fixes (Compare Learn more, V-02, V-03, V-05, V-06, V-10) ----------------

def test_compare_has_a_learn_more_and_a_styled_add_a_system_select():
    assert '<LearnMore anchor="what-to-click" label="How to read Compare" />' in _code("global/CompareView.tsx")
    css = (SRC / "styles" / "compare.css").read_text(encoding="utf-8")
    assert re.search(r"\.compare-picker select \{[^}]*background: var\(--bg-inset\)", css), "V-02: the browser's default select again"


def test_v03_the_home_search_placeholder_fits():
    nav = _code("global/GlobalNav.tsx")
    ph = re.search(r'placeholder=\{compact \? "Search" : "([^"]+)"\}', nav).group(1)
    assert len(ph) <= 52, f"the placeholder is cut off at the home's width: {ph!r}"


def test_v05_the_source_health_heading_has_room_above_it_on_a_wide_screen():
    assert 'className="eyebrow rs-health-head"' in _code("global/CountryView.tsx")
    css = (SRC / "styles" / "country.css").read_text(encoding="utf-8")
    assert "@media (min-width: 601px) { .research-status .rs-health-head { margin-top: 8px; } }" in css


@pytest.mark.parametrize("rel, selector", [
    ("styles/gulf.css", ".member-list ul"), ("styles/gulf.css", ".group-sections ul"),
    ("styles/theatre.css", 'html[data-chrome="compact"] .camera-controls'), ("styles/help.css", ".help-main .table-scroll"),
])
def test_v06_v10_every_phone_sideways_scroller_shows_more_to_the_side(rel, selector):
    css = (SRC / rel).read_text(encoding="utf-8")
    rules = re.findall(re.escape(selector) + r" \{([^}]*)\}", css)
    # Both the standard property and the prefixed one: either alone misses a browser.
    assert any(re.search(r"(?<!-webkit-)mask-image: linear-gradient\(to right", r) and "-webkit-mask-image: linear-gradient(to right" in r
               and "padding-right: 28px" in r for r in rules), selector
