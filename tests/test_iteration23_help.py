"""Iteration 23: the reader's Help page and `global/help_facts.json`.

The Help page is the one place the site explains itself. Its live values come from a small served
file the build writes from the payloads it has just produced (pipeline/help_facts.py), and its
prose must keep the distinctions the site exists to keep. These tests build that file from the
sources, and RUN the shipped Help page (bundled from web/src with esbuild, rendered in Node with
the served data) so the mutation campaign can see a broken sentence, a broken route or a link to a
section that does not exist. The browser-level proof (deep links, Back, the phone picker) is in
web/e2e/help.e2e.ts; the prose rules are also in web/src/global/help/help.test.tsx.
"""
import json
import re

import pytest

from test_iteration21_testarch import ROOT, SRC, needs_bundler, run_ts

from pipeline import data_quality, help_facts, systems, whats_new

PROCESSED = ROOT / "data" / "processed"
WEB = ROOT / "web" / "public" / "data"
needs_payload = pytest.mark.skipif(not (PROCESSED / "global" / "help_facts.json").exists(), reason="no built payload")

# A file or repository path, a release label, or a raw key, anywhere in a reader string.
PATHLIKE = re.compile(r"\b[\w.-]+\.(?:json|csv|md|py|tsx?|geojson)\b|\bdocs/|\bdata/|\bpipeline/|\bmethodology/")
RELEASE = re.compile(r"\biterations?\b", re.I)
RAW_ID = re.compile(r"(?<![\w/.-])[a-z]+(?:_[a-z]+)+(?![\w/.-])|\b[A-Z]{2,}(?:_[A-Z]+)+\b")


def _strings(x, key=""):
    """Every string value in a document, with the key it sits under."""
    if isinstance(x, str):
        yield key, x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from _strings(v, k)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v, key)


def _built():
    return help_facts.build(PROCESSED)


# ---------------- help_facts.json ----------------

@needs_payload
def test_help_facts_is_built_from_the_payloads_and_carries_every_derived_value():
    built = _built()
    served = json.loads((PROCESSED / help_facts.OUT).read_text(encoding="utf-8"))
    assert built == served, "the served help facts are not what the build makes from this build's payloads"
    assert (WEB / help_facts.OUT).read_bytes() == (PROCESSED / help_facts.OUT).read_bytes()
    snap = json.loads((PROCESSED / "snapshot.json").read_text(encoding="utf-8"))
    impacts = json.loads((PROCESSED / "global" / "impacts.json").read_text(encoding="utf-8"))
    t = built["theatre"]
    # Each value is the source's own, not a copy typed somewhere.
    assert t["transmission_saturation_events"] == snap["denominators"]["transmission_saturation_events"]
    assert t["status_delay_days"] == snap["campaign_policy"]["evidence_embargo_days"]
    assert t["recovery_horizon_sensitivity"]["low"] == snap["recovery_horizon_sensitivity"]["esdi_range"][0]
    assert t["coverage"]["incident_total"] == snap["incident_total"]
    assert len(t["sectors_uncovered"]) == len(snap["sectors_uncovered"]) and t["sectors_uncovered"]
    assert t["earliest_published_date"] and re.fullmatch(r"\d{4}-\d{2}-\d{2}", t["earliest_published_date"])
    assert [c["question"] for c in t["cannot_tell_you"]]
    assert built["impacts"]["caveats"] == impacts["caveats"] and built["impacts"]["scope_statement"] == impacts["scope_statement"]
    assert built["impacts"]["research"]["window"] == impacts["research"]["window"]
    assert built["regional_context"]["statement"] and built["context_vintage"]["source"]
    # Small: Help never downloads the snapshot or the impact corpus.
    assert (PROCESSED / help_facts.OUT).stat().st_size < 30_000


@needs_payload
def test_help_facts_has_no_file_path_no_release_label_and_no_raw_key():
    checked = 0
    for key, s in _strings(_built()):
        if key in ("as_of", "build_time", "release", "retrieved", "start", "end", "latest_research_date",
                   "earliest_published_date", "method_version") or " " not in s:
            continue
        checked += 1
        assert not PATHLIKE.search(s), (key, s)
        assert not RELEASE.search(s), (key, s)
        assert not RAW_ID.search(s), (key, s)
    assert checked > 30


@needs_payload
def test_the_theatres_cannot_tell_you_names_sectors_in_words_and_no_file():
    snap = json.loads((PROCESSED / "snapshot.json").read_text(encoding="utf-8"))
    items = data_quality.cannot_tell_you(snap, snap.get("explanations") or {})
    text = json.dumps(items, ensure_ascii=False)
    assert items and not PATHLIKE.search(text), "a repository path reaches the reader"
    first = items[0]
    assert first["basis"] == "sectors_uncovered"
    for sid in snap["sectors_uncovered"]:
        assert re.search(rf"\b{sid}, |, {sid}\b|^{sid} ", first["answer"]) is None, "a raw sector id reaches the reader"


def test_the_gulf_selection_rule_carries_no_release_label():
    assert not RELEASE.search(systems.GULF_SELECTION["rule"])


def test_whats_new_links_a_rule_change_to_a_help_section_never_a_home_heading():
    src = (ROOT / "pipeline" / "whats_new.py").read_text(encoding="utf-8")
    assert '"anchor": "why-head"' not in src
    assert '{"help": help_anchor}' in src


# ---------------- the shipped Help page, run ----------------

HELP = {
    "page": "global/help/HelpPage.tsx",
    "anchors": "global/help/anchors.ts",
    "content": "global/help/content.ts",
    "glossary": "global/help/glossary.ts",
    "detail": "global/help/glossaryDetail.ts",
    "derived": "global/help/HelpDerived.tsx",
    "router": "global/router.ts",
}

RENDER = """
const text = (html) => html.replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/\\s+/g, " ");
const render = (method) => {
  const data = { facts: { value: input.facts, failed: false }, manifest: { value: input.manifest, failed: false },
                 method: { value: method, failed: false }, whatsNew: { value: input.whatsNew, failed: false } };
  const html = renderToStaticMarkup(React.createElement(page.HelpDocument, { data }));
  const sections = {};
  for (const part of html.split("<section").slice(1)) {
    const id = /aria-labelledby="([^"]+)"/.exec(part)[1];
    sections[id] = text(part.split("</section>")[0]);
  }
  return { all: text(html), sections, h1: (html.match(/<h1\\b/g) || []).length };
};
"""


def _served():
    read = lambda rel: json.loads((WEB / rel).read_text(encoding="utf-8"))  # noqa: E731
    return {"facts": read("global/help_facts.json"), "manifest": read("global/manifest.json"),
            "method": read("global/evidence_confidence.json"), "whatsNew": read("global/whats_new.json")}


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    if not (WEB / "global" / "help_facts.json").exists():
        pytest.skip("no built payload")
    data = _served()
    calibrated = {**data["method"], "version": "2.0", "status": "a served status"}
    return run_ts(tmp_path_factory, HELP, RENDER + """
      return { draft: render(input.method), calibrated: render(input.calibrated),
               draftNote: derived.ECI_DRAFT_NOTE };
    """, {**data, "calibrated": calibrated})


def _sentences(text):
    return [s for s in re.split(r"(?<=[.;:])\s+", text) if s.strip()]


NEGATION = re.compile(r"\b(?:not|never|nor|no)\b|n't\b", re.I)


@needs_bundler
def test_help_takes_the_evidence_confidence_status_from_the_served_file_and_warns_while_it_is_a_draft(rendered):
    m = _served()["method"]
    eci = rendered["draft"]["sections"]["evidence-confidence"]
    assert f"Method version {m['version']}." in eci
    assert m["version"].endswith("-draft"), "the served method is calibrated: update this test with the release"
    assert m["status"] in eci and rendered["draftNote"] in eci, "the draft warning is missing while the method is a draft"
    cal = rendered["calibrated"]["sections"]["evidence-confidence"]
    assert "Status: a served status." in cal and rendered["draftNote"] not in cal


@needs_bundler
def test_help_never_calls_evidence_confidence_a_probability_or_a_count_a_rate(rendered):
    page = rendered["draft"]["all"]
    probability = [s for s in _sentences(page) if re.search(r"\bprobabilit", s, re.I)]
    rates = [s for s in _sentences(page) if re.search(r"\brates?\b", s, re.I)]
    assert probability and rates, "nothing to check"
    for s in probability + rates:
        assert NEGATION.search(s), s
    assert "it is not a probability" in rendered["draft"]["sections"]["evidence-confidence"]
    assert "Counts are not rates." in rendered["draft"]["sections"]["do-not-infer"]
    assert "Counts are not rates." in rendered["draft"]["sections"]["impact-records"]


@needs_bundler
def test_help_says_no_index_is_not_zero(rendered):
    s = rendered["draft"]["sections"]
    assert "a missing index is not a zero" in s["why-no-country-score"]
    assert "“No index” means no figure was computed; it never means zero" in s["glossary"]
    assert "No index is not zero." in s["start-here"]


@needs_bundler
def test_help_never_calls_the_impact_records_complete(rendered):
    imp = rendered["draft"]["sections"]["impact-records"]
    assert "not a complete list of disruptions in any country" in imp
    for s in _sentences(imp):
        if re.search(r"\bcomplete\b|\bcensus\b", s, re.I):
            assert NEGATION.search(s), s


@needs_bundler
def test_help_says_the_latest_gulf_statement_is_not_the_current_status(rendered):
    s = rendered["draft"]["sections"]
    assert "The latest statement is not the current status" in s["gulf-context"]
    assert "Latest is not current. The latest Gulf context statement is not the current status." in s["do-not-infer"]
    for part in (s["gulf-context"], s["do-not-infer"]):
        for sentence in _sentences(part):
            if re.search(r"\blatest\b", sentence, re.I) and re.search(r"\bcurrent\b", sentence, re.I):
                assert NEGATION.search(sentence), sentence


@needs_bundler
def test_help_says_no_record_is_not_no_disruption(rendered):
    s = rendered["draft"]["sections"]
    assert "No record is not no disruption." in s["absence"]
    assert "is not evidence that no disruption occurred" in s["absence"]
    assert "A missing record is not evidence that nothing happened." in s["start-here"]


@needs_bundler
def test_help_keeps_modelled_recovery_apart_from_observed(rendered):
    esdi = rendered["draft"]["sections"]["esdi"]
    assert "Observed means a source reported the restoration." in esdi
    assert "Modelled means no source said anything, and an assumption for that type of facility is used." in esdi
    assert "the three kinds are never merged into one figure" in esdi
    assert "no restoration report is not known still offline" in rendered["draft"]["sections"]["do-not-infer"]


@needs_bundler
def test_help_keeps_a_reconstruction_apart_from_what_was_published(rendered):
    hist = rendered["draft"]["sections"]["history"]
    assert "The first answer is the as-published history: what the site actually served on each day." in hist
    assert "The second is a current-evidence reconstruction: today's evidence and today's method applied to that past date." in hist
    assert "A reconstruction is never presented as what was published." in hist


@needs_bundler
def test_help_has_one_h1_a_section_per_anchor_and_a_text_alternative_to_the_maps(rendered, tmp_path_factory):
    out = run_ts(tmp_path_factory, HELP, "return { anchors: anchors.helpAnchors(), glossary: glossary.GLOSSARY.map((g) => g.id) };")
    assert rendered["draft"]["h1"] == 1
    for a in out["anchors"]:
        if a not in ("how-it-works", "recovery"):
            assert a in rendered["draft"]["sections"], a
    assert "The maps are never the only way in." in rendered["draft"]["sections"]["navigating-the-map"]


def _help_targets(tmp_path_factory):
    out = run_ts(tmp_path_factory, HELP, "return { anchors: anchors.helpAnchors(), glossary: glossary.GLOSSARY.map((g) => g.id) };")
    return set(out["anchors"]) | {f"g-{g}" for g in out["glossary"]}


@needs_bundler
def test_every_learn_more_link_in_the_source_names_a_help_section(tmp_path_factory):
    targets = _help_targets(tmp_path_factory)
    found = []
    for path in SRC.rglob("*.ts*"):
        if ".test." in path.name:
            continue
        code = path.read_text(encoding="utf-8")
        for m in re.finditer(r'<LearnMore[^>]*?\banchor="([^"]+)"|\blearnMore="([^"]+)"|helpHref\("([^"]+)"\)', code):
            found.append((path.relative_to(SRC).as_posix(), next(g for g in m.groups() if g)))
    files = {f for f, _ in found}
    # The places the brief names, each still linking to Help.
    for f in ("components/Ribbon.tsx", "global/CountryView.tsx", "global/Disclosure.tsx", "global/GroupView.tsx",
              "global/GroupImpactSections.tsx", "global/impacts/ImpactAtlas.tsx", "global/impacts/ConfidenceChip.tsx",
              "global/impacts/AttributionLine.tsx", "global/impacts/AiLine.tsx", "global/WhatsNew.tsx", "components/Briefing.tsx"):
        assert f in files, f"{f} lost its Learn more link"
    assert [x for x in found if x[1] not in targets] == []
    # The served What's New link too.
    wn = json.loads((WEB / "global" / "whats_new.json").read_text(encoding="utf-8"))
    for c in wn.get("global") or []:
        if (c.get("link") or {}).get("help"):
            assert c["link"]["help"] in targets
    for anchor in ("evidence-confidence", "whats-new"):
        assert anchor in targets, "whats_new.py writes a Help anchor that does not exist"


@needs_bundler
def test_help_routes_and_the_old_glossary_link_is_rewritten(tmp_path_factory):
    out = run_ts(tmp_path_factory, HELP, """
      const r = (q) => router.routeFor(q).view;
      return { help: r("?view=help"), legacy: r("?help=glossary"), sys: r("?sys=ir&view=help"), group: r("?group=gulf&help=glossary"),
               cmp: r("?compare=us&view=help"), home: r(""),
               url: router.legacyHelpUrl("?help=glossary", ""), term: router.legacyHelpUrl("?help=glossary&term=esdi", ""),
               bad: router.legacyHelpUrl("?help=glossary&term=%3Cx%3E", ""), none: router.legacyHelpUrl("?sys=us&help=glossary", "") };
    """)
    assert out == {"help": "help", "legacy": "help", "sys": "country", "group": "group", "cmp": "compare", "home": "home",
                   "url": "?view=help#glossary", "term": "?view=help#g-esdi", "bad": "?view=help#glossary", "none": None}


@needs_bundler
def test_the_home_bundle_never_carries_the_help_text(tmp_path):
    from test_iteration22_atlas import _home_graph
    inputs = _home_graph(tmp_path)
    assert any(i.endswith("src/global/GlobalNav.tsx") for i in inputs)
    for name in ("help/HelpPage.tsx", "help/content.ts", "help/glossaryDetail.ts", "help/HelpDerived.tsx", "help/facts.ts"):
        assert not [i for i in inputs if i.endswith(name)], f"{name} is loaded with the home page"
    root = (SRC / "Root.tsx").read_text(encoding="utf-8")
    assert 'lazy(() => import("./global/help/HelpPage"))' in root
