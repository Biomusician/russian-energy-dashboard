"""Iteration 23: the map-first home, the rules a refactor could quietly undo.

Behaviour is tested in the browser (web/e2e/home.e2e.ts); these tests run the shipped TypeScript
(homeSelection.ts, searchIndex.ts) against the served world map and manifest, and read the source
where a rule is structural, so the mutation campaign (pytest only) can see every one of them:

- the impact-presence list is the Impact Atlas's own rule, and carries no figure;
- one click means one unit: the theatre is one shape, Crimea is never Russian, eastern Russia is
  outside the monitored area, Hong Kong is China's and Taiwan is not;
- a country with impact records links the atlas filtered to it, an attempt-only country links it
  unfiltered, and a country with neither gets no button and never reads "no disruption";
- the panel keeps the manifest's order; no option, label or card carries a count;
- the default map colours say only "monitored", "occupied" or nothing, in one neutral colour that
  clears 3:1 against the base;
- a selection lives in the home's history entry, never in a new address.
"""

import json
import re

import pytest

from test_iteration21_testarch import ROOT, SRC, needs_bundler, run_ts

from pipeline import global_impacts as G

WEB = ROOT / "web" / "public" / "data"
GLOBAL = SRC / "global"
HOME = {"hs": "global/homeSelection.ts", "si": "global/searchIndex.ts"}
ATLAS = {"atlas": "global/impacts/atlasModel.ts", "model": "global/impacts/model.ts"}
# The home's React and model files: none may name a member of a group or a country by itself.
HOME_FILES = ("GlobalHome.tsx", "HomeStage.tsx", "SystemPanel.tsx", "SelectionCard.tsx", "homeSelection.ts", "WorldContext.tsx")
DATE = r"\b\d{1,2} [A-Z][a-z]{2} \d{4}\b"


def _json(rel):
    return json.loads((WEB / rel).read_text(encoding="utf-8"))


def _code(name):
    """Source without comments, so a rule is neither satisfied nor broken by prose."""
    text = (GLOBAL / name).read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    return re.sub(r"\{/\*.*?\*/\}", "", text, flags=re.S)


@pytest.fixture(scope="module")
def served():
    return {"manifest": _json("global/manifest.json"), "world": _json("global/world.geojson")}


# ---------------- the presence list ----------------

@needs_bundler
def test_impact_presence_is_the_atlas_rule_and_the_pipeline_reproduces_it(tmp_path_factory):
    """The served list equals the atlas's countriesPresent over its disruptions, MULTI expanded and
    attempts excluded, and pipeline.global_impacts.impact_presence rebuilds exactly what is served."""
    impacts = _json("global/impacts.json")
    presence = _json("global/manifest.json")["impact_presence"]
    out = run_ts(tmp_path_factory, ATLAS, """
      const P = input.impacts;
      const present = atlas.countriesPresent(model.disruptions(P), P.countries).map((c) => c.a3);
      const attempted = new Set(model.attempts(P).flatMap((r) => model.countryCodes(r)));
      return { present, attemptOnly: [...attempted].filter((a) => !present.includes(a)).sort() };
    """, {"impacts": impacts})
    assert presence["countries"] == sorted(out["present"])
    assert presence["attempt_only"] == out["attemptOnly"]
    assert G.impact_presence(impacts) == presence, "rebuild: the served list is not what the pipeline writes"
    assert "MULTI" not in presence["countries"]
    assert not set(presence["countries"]) & set(presence["attempt_only"])
    assert presence["attempt_only"], "the data has an attempt-only country; the state must be exercised"


def test_impact_presence_is_codes_only_and_carries_no_figure():
    p = _json("global/manifest.json")["impact_presence"]
    assert set(p) == {"countries", "attempt_only", "note"}
    for key in ("countries", "attempt_only"):
        assert p[key] == sorted(set(p[key])), f"{key} must be sorted and unique: a list in any other order is a ranking"
        assert all(isinstance(a, str) and re.fullmatch(r"[A-Z]{3}", a) for a in p[key]), key
    assert isinstance(p["note"], str) and not re.search(r"\d", p["note"])


# ---------------- units and states ----------------

STATE_JS = """
const idx = hs.indexWorld(input.world);
const m = input.manifest;
const feats = input.world.features.map((f) => f.properties);
const states = feats.map((p) => ({ a3: p.a3, name: p.name, status: p.status, system: p.system_id,
  unit: hs.unitOf(p), state: hs.stateOf(hs.unitOf(p), idx, m), hover: hs.hoverLabel(p, idx, m) }));
"""


@needs_bundler
def test_every_feature_is_one_unit_in_exactly_one_state(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, HOME, STATE_JS + "return states;", served)
    m = served["manifest"]
    by_kind = {s["id"]: s["kind"] for s in m["systems"]}
    presence = set(m["impact_presence"]["countries"])
    attempt_only = set(m["impact_presence"]["attempt_only"])
    seen = set()
    for f in out:
        seen.add(f["state"])
        if f["system"]:
            assert f["unit"] == f["system"], f"{f['name']}: a click must open its system, not its country"
            assert f["state"] == ("theatre" if by_kind[f["system"]] == "theatre" else "country_system"), f["name"]
        elif f["a3"] == "RUS":
            assert f["state"] == "outside_area", "eastern Russia is outside the monitored area, not a country of its own"
        elif f["a3"] in presence:
            assert f["state"] == "impact_only", f["name"]
        elif f["a3"] in attempt_only:
            assert f["state"] == "attempt_only", f["name"]
        else:
            assert f["state"] == "no_record", f["name"]
    assert seen == {"theatre", "country_system", "outside_area", "impact_only", "attempt_only", "no_record"}
    occupied = [f for f in out if f["status"] == "occupied"]
    assert occupied and all(f["unit"] == "ru" for f in occupied), "Crimea and Sevastopol open the theatre, as one unit with it"
    units = {f["a3"]: f["unit"] for f in out if f["status"] != "occupied"}
    assert units["HKG"] == units["MAC"] == "cn" and units["TWN"] == "TWN", "Taiwan is not part of the China system"


@needs_bundler
def test_crimea_is_never_described_as_russian(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, HOME, STATE_JS + """
      return { hovers: states.filter((s) => s.status === "occupied").map((s) => s.hover),
               phrase: hs.OCCUPIED_PHRASE,
               card: hs.cardFor("ru", idx, m, { name: "Crimea", occupied: true }),
               ukraine: hs.cardFor("UKR", idx, m) };
    """, served)
    russian = re.compile(r"(region|part|territory|province|oblast) of Russia|Russian (region|territory|province)(?! under)|Russia's", re.I)
    texts = out["hovers"] + out["card"]["lines"] + out["ukraine"]["lines"]
    assert out["phrase"] == "Ukrainian territory under Russian occupation"
    for t in out["hovers"]:
        assert out["phrase"] in t and "Russia, Belarus & Crimea" in t, t
    for t in texts:
        assert not russian.search(t), t
    assert any("Crimea and Sevastopol" in t for t in out["ukraine"]["lines"]), "Ukraine's card says where Crimea is monitored"


# ---------------- what a click or a tap does ----------------

@needs_bundler
def test_systems_open_in_one_click_and_a_finger_gets_the_card_first(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, HOME, """
      const m = input.manifest;
      return { mouse: Object.fromEntries(["ru", "ir", "bh", "us", "FRA", "MNG", "RUS"].map((u) => [u, hs.pickAction(u, m, false)])),
               touch: Object.fromEntries(["ru", "ir", "FRA"].map((u) => [u, hs.pickAction(u, m, true)])) };
    """, served)
    assert out["mouse"] == {"ru": "open", "ir": "open", "bh": "open", "us": "open", "FRA": "select", "MNG": "select", "RUS": "select"}
    assert set(out["touch"].values()) == {"select"}, "a tap opens the sheet first, systems included"


CARDS_JS = STATE_JS + """
const units = [...new Set(states.map((s) => s.unit))];
const cards = units.map((u) => ({ unit: u, state: hs.stateOf(u, idx, m), card: hs.cardFor(u, idx, m) }));
"""


@needs_bundler
def test_each_card_offers_only_what_is_true_for_its_state(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, HOME, CARDS_JS + "return cards;", served)
    occupied = {f["properties"]["a3"] for f in served["world"]["features"] if f["properties"]["status"] == "occupied"}
    states = {c["state"] for c in out}
    assert {"impact_only", "attempt_only", "no_record", "outside_area"} <= states
    for c in out:
        card, hrefs = c["card"], [a["href"] for a in c["card"]["actions"]]
        text = " ".join([card["status"], *card["lines"]])
        assert not re.search(r"\bno (reported )?disruptions?\b|nothing happened|no incidents?", text, re.I), (c["unit"], text)
        if c["state"] == "impact_only":
            assert f"?view=impacts&f.country={c['unit']}" in hrefs, c["unit"]
            assert card["status"] == "Impact records available · Not a monitored country system"
        if c["state"] == "attempt_only":
            assert "?view=impacts" in hrefs and not any("f.country" in h for h in hrefs), \
                f"{c['unit']}: the atlas ignores a country filter with no disruption, so the link is unfiltered"
        if c["state"] == "no_record":
            assert not [h for h in hrefs if "view=impacts" in h], c["unit"]
            assert "has not searched" in text and "nothing here says whether disruptions happened" in text, c["unit"]
            assert card["status"] == "No dedicated monitored system · No published impact record"
            # A country with occupied territory links the system that monitors it; any other no-record
            # card has no button at all.
            if c["unit"] not in occupied:
                assert hrefs == [], f"{c['unit']}: no system and no record means no button and no dashboard"
        if c["state"] == "outside_area":
            # Chosen as a whole (no map click), iteration 23 (MU-05): "the rest lies outside the monitored area".
            assert "?sys=ru" in hrefs and re.search(r"outside the (area monitored|monitored area)", text)


@needs_bundler
def test_without_a_presence_list_the_card_says_it_could_not_check(tmp_path_factory, served):
    m = {k: v for k, v in served["manifest"].items() if k != "impact_presence"}
    out = run_ts(tmp_path_factory, HOME, """
      const idx = hs.indexWorld(input.world);
      return ["FRA", "MNG"].map((u) => [hs.stateOf(u, idx, input.manifest), hs.cardFor(u, idx, input.manifest)]);
    """, {"world": served["world"], "manifest": m})
    for state, card in out:
        assert state == "unchecked"
        text = " ".join([card["status"], *card["lines"]])
        assert "could not be checked" in text and "No published impact record" not in text


# ---------------- no count, no maturity, the manifest's order ----------------

@needs_bundler
def test_no_digit_in_any_label_card_or_option_except_the_headline_and_dates(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, HOME, CARDS_JS + """
      const groups = Object.keys(m.groups ?? {}).map((g) => hs.cardFor("group:" + g, idx, m)).filter(Boolean);
      const theatre = m.systems.find((s) => s.kind === "theatre");
      const options = [...si.systemEntries(m), ...si.countryEntries(idx, m), ...si.groupEntries(m)].map((e) => e.label + " " + e.sub);
      const rows = hs.panelRows(m).map((r) => [r.label, r.tag ?? ""].join(" "));
      return { texts: [...states.map((s) => s.hover), ...[...cards.map((c) => c.card), ...groups].flatMap((c) =>
                 [c.heading, c.status, ...c.lines, ...c.actions.map((a) => a.label), ...c.links.map((a) => a.label)]),
                 ...options, ...rows, hs.THEATRE_MEANING],
               headline: theatre.headline ? hs.headlineText(theatre) : null };
    """, served)
    texts = out["texts"]
    assert len(texts) > 500
    for t in texts:
        stripped = re.sub(DATE, "", t.replace(out["headline"] or "\0", ""))
        assert not re.search(r"\d", stripped), t
        assert "research preview" not in t.lower(), f"no maturity on the navigation surface: {t}"


@needs_bundler
def test_the_panel_keeps_the_manifest_order(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, HOME, "return hs.panelRows(input.manifest);", served)
    m = served["manifest"]
    sections = [r["section"] for r in out]
    assert sections[0] == "indexed" and sections[1] == "beyond" and sections[-1] == "tools"
    assert sections == sorted(sections, key=["indexed", "beyond", "regional", "countries", "tools"].index), "sections out of order"
    assert [r["systemId"] for r in out if r["section"] == "countries"] == [s["id"] for s in m["systems"] if s["kind"] == "country"]
    assert [r["groupId"] for r in out if r["section"] == "regional"] == [g for g, d in m["groups"].items() if d["slug"] and d["context"]]
    # The Gulf is a quiet tag on its members, never a block that pushes other systems down.
    gulf = m["groups"]["gulf_littoral"]
    for r in out:
        if r["section"] == "countries":
            assert (r.get("tag") == gulf["label"]) == (r["systemId"] in gulf["members"]), r


def test_the_home_never_sorts_its_systems_and_has_no_picker_or_start_here():
    for name in ("GlobalHome.tsx", "HomeStage.tsx", "SystemPanel.tsx"):
        code = _code(name)
        assert not re.search(r"\.sort\(|\.reverse\(|\.toSorted\(|localeCompare", code), f"{name} re-orders something"
    body = _code("homeSelection.ts")
    panel = body[body.index("export function panelRows("):body.index("export function unitsOf(")]
    assert not re.search(r"\.sort\(|\.reverse\(|localeCompare", panel), "panelRows re-orders the systems"
    home = _code("GlobalHome.tsx")
    assert "<SystemSwitcher" not in home and "<StartHere" not in home


# ---------------- the map's colours ----------------

def _gets(expr):
    """Every feature property an expression reads."""
    if isinstance(expr, list):
        if len(expr) == 2 and expr[0] == "get" and isinstance(expr[1], str):
            return {expr[1]}
        return set().union(*(_gets(e) for e in expr)) if expr else set()
    return set()


@needs_bundler
def test_the_default_map_colours_only_what_one_click_does(tmp_path_factory):
    simple = (GLOBAL / "SimpleMap.tsx").read_text(encoding="utf-8")
    bg = re.search(r'"background-color": "(#[0-9a-f]{6})"', simple).group(1)
    alpha = float(re.search(r'"fill-opacity": ([0-9.]+) \} \}\);\n      m\.addLayer\(\{ id: "line"', simple).group(1))
    out = run_ts(tmp_path_factory, HOME, """
      const c = hs.MAP_COLOURS;
      const on = (x) => hs.blend(x, input.bg, input.alpha);
      return { fill: hs.NAV_FILL, hatch: hs.NAV_HATCH, unit: hs.UNIT_EXPR, colours: c,
               contrast: hs.contrast(on(c.monitored), on(c.base)) };
    """, {"bg": bg, "alpha": alpha})
    assert _gets(out["fill"]) <= {"status", "system_id"}, "the default fill reads a count, a score or another property"
    assert _gets(out["hatch"]) == {"status"} and _gets(out["unit"]) == {"system_id", "a3"}
    assert out["contrast"] >= 3, f"monitored against base is {out['contrast']:.2f}:1, under WCAG 1.4.11's 3:1"
    for name, hexc in out["colours"].items():
        r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
        assert not (r > g + 60 and r > b + 60), f"{name} {hexc} is a red: a severity colour has no place here"
    # The colours the explore mode passes are these ones, and the hatch is the occupied filter.
    world = _code("WorldContext.tsx")
    assert "explore || !energy ? NAV_FILL : energy.fill" in world and "filter: NAV_HATCH" in world
    assert "matchExpr={UNIT_EXPR}" in world and "dissolve" in world


def test_every_new_map_mark_is_a_highlight_layer_so_an_export_drops_it():
    simple = (GLOBAL / "SimpleMap.tsx").read_text(encoding="utf-8")
    listed = json.loads(re.search(r"export const HIGHLIGHT_LAYERS = (\[[^\]]*\]);", simple).group(1))
    added = set(re.findall(r'm\.addLayer\(\{ id: "([\w-]+)"', simple))
    content = {"fill", "line", "outline", "hatch"}
    assert added - content, "no layer found"
    assert added - content <= set(listed), f"{sorted(added - content - set(listed))} would be drawn into an export"
    assert "!HIGHLIGHT_LAYERS.includes(l.id)" in simple
    world = _code("WorldContext.tsx")
    assert "withoutHighlight(s)" in world, "the national-energy PNG must drop the reader's marks"


# ---------------- groups and small places ----------------

@needs_bundler
def test_a_regional_group_is_its_manifest_members_and_their_bounds(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, HOME, """
      const m = input.manifest;
      return Object.keys(m.groups).map((g) => ({ g, units: hs.unitsOf("group:" + g, m), box: hs.groupBounds(m, g),
        card: hs.cardFor("group:" + g, null, m) }));
    """, served)
    m = served["manifest"]
    bounds = {s["id"]: s.get("bounds") for s in m["systems"]}
    for row in out:
        members = m["groups"][row["g"]]["members"]
        assert row["units"] == members
        bs = [bounds[s] for s in members if bounds.get(s)]
        assert row["box"] == [min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)]
        if m["groups"][row["g"]]["slug"]:
            assert [a["href"] for a in row["card"]["links"]] == [f"?sys={s}" for s in members]
            assert row["card"]["actions"][0]["href"] == f"?group={m['groups'][row['g']]['slug']}"


def test_no_home_file_names_a_member_or_a_country_by_itself(served):
    ids = {s["id"] for s in served["manifest"]["systems"] if s["kind"] == "country"}
    names = {s["name"] for s in served["manifest"]["systems"]}
    for name in HOME_FILES:
        code = _code(name)
        for i in ids:
            assert not re.search(rf'["\'`]{i}["\'`]', code), f"{name} hardcodes the system id {i}"
        for n in names - {"Russia, Belarus & Crimea"}:
            assert n not in code, f"{name} hardcodes {n}"
        assert not re.search(r'"[A-Z]{3}"', code), f"{name} hardcodes a country code"


# ---------------- search ----------------

@needs_bundler
def test_search_reaches_every_country_and_a_country_without_a_system_selects(tmp_path_factory, served):
    out = run_ts(tmp_path_factory, HOME, """
      const idx = hs.indexWorld(input.world);
      const m = input.manifest;
      const entries = [...si.systemEntries(m), ...si.countryEntries(idx, m)];
      const reach = idx.countries.map((c) => ({ a3: c.a3, unit: c.unit, name: c.name,
        hit: si.searchEntries(entries, c.name, 50).filter((h) => (h.entry.action.type === "select" && h.entry.action.key === c.unit)
                                                              || (h.entry.action.type === "system" && h.entry.action.id === c.unit)).length > 0,
        country: entries.find((e) => e.key === "country:" + c.a3) ?? null }));
      const az = idx.countries.map((c) => c.a3);
      const world = [...new Set(input.world.features.filter((f) => f.properties.status !== "occupied").map((f) => f.properties.a3))];
      return { reach, az, world };
    """, served)
    assert sorted(out["az"]) == sorted(out["world"]), "the A to Z list must hold every country on the map"
    systems = {s["id"] for s in served["manifest"]["systems"]}
    for c in out["reach"]:
        assert c["hit"], f"searching {c['name']} does not reach what a click on it does"
        if c["unit"] not in systems:
            e = c["country"]
            assert e and e["action"] == {"type": "select", "key": c["unit"]}, f"{c['name']} must select on the map, not navigate"
            assert e["sub"].endswith("selects it on the map")


# ---------------- the address ----------------

HISTORY_JS = """
const calls = [];
let state = null;
let url = "/";
globalThis.window = {
  location: { get pathname() { return "/"; }, get search() { return url.includes("?") ? url.slice(url.indexOf("?")) : ""; } },
  history: {
    get state() { return state; },
    replaceState(s, _t, u) { calls.push(["replace", s, u ?? null]); state = s; if (u) url = u; },
    pushState(s, _t, u) { calls.push(["push", s, u]); state = s; url = u; },
  },
  dispatchEvent() { return true; },
};
"""


@needs_bundler
def test_a_selection_lives_in_history_state_and_never_in_the_address(tmp_path_factory):
    out = run_ts(tmp_path_factory, HOME, HISTORY_JS + """
      hs.writeHomeState("FRA", null);
      hs.openFromHome("?view=impacts&f.country=FRA", "FRA", "card:impacts");
      const afterOpen = calls.slice();
      calls.length = 0; url = "/?sys=ir";
      hs.selectOnHome("MNG");
      return { afterOpen, fromElsewhere: calls };
    """)
    first, second, third = out["afterOpen"]
    assert first[0] == "replace" and first[1]["homeFocus"] == "FRA" and first[2] is None, "selecting must not touch the address"
    assert second[0] == "replace" and second[1] == {"homeFocus": "FRA", "homeReturn": "card:impacts"} and second[2] is None
    assert third[0] == "push" and third[2] == "/?view=impacts&f.country=FRA", "opening uses the existing address, unchanged"
    push = out["fromElsewhere"][0]
    assert push[0] == "push" and push[2] == "/" and push[1]["homeFocus"] == "MNG"
    for c in out["afterOpen"] + out["fromElsewhere"]:
        assert "sel=" not in str(c[2] or ""), c


def test_no_source_file_writes_a_sel_parameter():
    for path in GLOBAL.rglob("*.ts*"):
        code = path.read_text(encoding="utf-8")
        # ("sel" alone is SimpleMap's selection layer, not an address.)
        assert not re.search(r"[?&]sel=|\.(get|set|has|append)\(['\"]sel['\"]", code), f"{path.name} reads or writes a ?sel= address"



def test_the_home_loads_no_national_figures_until_the_reader_asks():
    """The default map shows no figure, so the 165 KB national-figures file waits for the
    national-energy mode or a part that shows figures (measured: 624 KB of data on load before)."""
    pre = (GLOBAL / "prefetch.ts").read_text(encoding="utf-8")
    home = re.search(r'route\.view === "home"\) \{(.*?)\} else if', pre, re.S).group(1)
    assert "loadContext" not in home, "the home's prefetch starts the national-figures download"
    for name in ("HomeStage.tsx", "SystemPanel.tsx"):
        code = (GLOBAL / name).read_text(encoding="utf-8")
        assert "loadContext" not in code, f"{name} loads the national figures on the first screen"
    # The page asks for them only inside the collapsed national-figures part, which mounts on open.
    gh = (GLOBAL / "GlobalHome.tsx").read_text(encoding="utf-8")
    fold = gh[gh.index("function NationalFold("):]
    fold = fold[:fold.index("\n}\n")]
    assert gh.count("loadContext()") == 1 and "loadContext()" in fold, "the home loads the national figures outside their fold"
    # The map asks for them only once the national-energy mode is on.
    wc = (GLOBAL / "WorldContext.tsx").read_text(encoding="utf-8")
    effect = re.search(r'useEffect\(\(\) => \{\s*if \(mode !== "energy" \|\| ctx\) return;[^}]*loadContext\(\)', wc)
    assert effect, "the map loads the national figures outside the national-energy mode"
    assert wc.count("loadContext()") == 1
