"""Iteration 22: the Impact Atlas and the shared impact components, executed.

Every test here RUNS the TypeScript that ships (bundled from web/src with esbuild and run in Node,
the harness of tests/test_iteration21_testarch.py), against the pipeline's own synthetic corpus
built in-process as it is served. A mutant in web/src/global/impacts/ is therefore a mutant in what
these tests execute, which is what lets scripts/mutation_campaign.py see a frontend rule at all.

The rules (docs/GLOBAL_IMPACT_METHODOLOGY.md):
- an AI line is rendered only where a source reports AI; never for NONE_REPORTED;
- unknown attribution is "not established": never a confidence level, never "low";
- not-applicable attribution renders nothing;
- an attempt is never in the timeline, a count, the country list or the presence map;
- the presence map marks presence in one colour and cannot encode a count;
- no count stands beside a country;
- "cyber" is a malicious cyber cause, and an IT failure is in no cyber preset;
- an abstracted (attack or sabotage) record shows no place and no headline;
- the home page never requests the impact corpus.

The browser-level proof of the same rules is in web/e2e/impacts.e2e.ts; component states are in
web/src/global/impacts/*.test.tsx.
"""
import copy
import json
import re
import subprocess

import pytest

from test_iteration21_testarch import NODE, NODE_MODULES, ROOT, SRC, needs_bundler, run_ts

from pipeline import global_impacts as G

AS_OF = "2026-11-19"
NO_AI = "NONE_REPORTED"

IMPACT_MODULES = {
    "model": "global/impacts/model.ts",
    "atlas": "global/impacts/atlasModel.ts",
    "vocab": "global/impacts/vocab.ts",
    "load": "global/impacts/load.ts",
    "filters": "global/recordFilters.ts",
    "AiLine": "global/impacts/AiLine.tsx",
    "AttributionLine": "global/impacts/AttributionLine.tsx",
    "ImpactCard": "global/impacts/ImpactCard.tsx",
    "ImpactInspector": "global/impacts/ImpactInspector.tsx",
    "ContextTimeline": "global/impacts/ContextTimeline.tsx",
    "ConfidenceChip": "global/impacts/ConfidenceChip.tsx",
}

# Registers the served words, then gives each test `text(el)`: the markup as a reader's text.
PRELUDE = """
vocab.forgetVocabularies();
vocab.registerVocabularies(input.payload.vocabularies);
vocab.registerVocabularies({ context_types: input.context.context_types });
vocab.registerMethod(input.method);
const html = (el) => renderToStaticMarkup(el);
const text = (el) => html(el).replace(/<[^>]+>/g, " ").replace(/&#x27;/g, "'").replace(/&amp;/g, "&").replace(/\\s+/g, " ").trim();
const h = React.createElement;
const P = input.payload;
"""


@pytest.fixture(scope="module")
def served():
    """The three impact files as the build serves them, from the synthetic fixture corpus."""
    ctx = G.load_context(link_states=G.read_json(G.FIXTURE_DIR / "link_health.json")["link_states"])
    out = G.build_payloads(*G.load_curated(G.FIXTURE_DIR), ctx, AS_OF)
    return {"payload": out[G.IMPACTS_OUT], "context": out[G.CONTEXT_OUT], "method": out[G.METHOD_OUT]}


def _ts(tmp_path_factory, served, body, extra=None):
    return run_ts(tmp_path_factory, IMPACT_MODULES, PRELUDE + body, {**served, **(extra or {})})


def _it_failure(served):
    """A non-malicious IT failure, made from a served technical-failure record (methodology §4)."""
    base = next(r for r in served["payload"]["records"]
                if r["cause_family"] == "industrial_technical" and r["cyber_mechanism"] is None
                and r["ai_involvement"]["status"] == NO_AI)
    r = copy.deepcopy(base)
    r["impact_id"] = "imp-2026-06-01-zzz-transport-synthetic-it-failure"
    r["cyber_mechanism"] = "it_outage_affecting_operations"
    return r


def test_atlas_fixture_corpus_exercises_every_state_these_tests_rely_on(served):
    recs = served["payload"]["records"]
    assert {r["attribution"]["status"] for r in recs} >= {"NOT_APPLICABLE", "UNKNOWN", "CLAIMED", "ASSESSED", "ATTRIBUTED", "DISPUTED"}
    assert any(r["ai_involvement"]["status"] != NO_AI for r in recs)
    assert any(r["cause_family"] == "cyber" and r["ai_involvement"]["status"] == NO_AI for r in recs)
    assert any(r["publication_policy"] == "country_abstracted" for r in recs)
    assert served["payload"]["attempts"], "the fixture must carry an attempt"
    assert all(r["record_kind"] == "disruption" for r in recs)


# ---------------- AI involvement ----------------

@needs_bundler
def test_atlas_ai_line_never_renders_for_none_reported(tmp_path_factory, served):
    """No source reports AI: no AI line, on its own or on the card. Ordinary cyber records included."""
    out = _ts(tmp_path_factory, served, """
      return P.records.map((r) => ({
        id: r.impact_id, status: r.ai_involvement.status, cyber: r.cause_family === "cyber",
        line: html(h(AiLine.AiLine, { ai: r.ai_involvement })),
        card: text(h(ImpactCard.ImpactCard, { record: r })),
      }));
    """)
    none = [x for x in out if x["status"] == NO_AI]
    some = [x for x in out if x["status"] != NO_AI]
    assert none and some and any(x["cyber"] for x in none)
    for x in none:
        assert x["line"] == "", x["id"]
        assert "AI involvement" not in x["card"], x["id"]
    for x in some:
        assert "AI involvement:" in x["line"] and "AI involvement:" in x["card"], x["id"]


@needs_bundler
def test_atlas_ai_assisted_is_never_merged_with_ai_as_operational_cause(tmp_path_factory, served):
    out = _ts(tmp_path_factory, served, """
      return P.records.filter((r) => r.ai_involvement.status !== "NONE_REPORTED")
        .map((r) => ({ relation: r.ai_involvement.relation, line: text(h(AiLine.AiLine, { ai: r.ai_involvement })) }));
    """)
    by = {x["relation"]: x["line"] for x in out}
    assert set(by) == {"ai_assisted", "ai_operational_cause"}
    assert "AI-assisted (not AI-caused)" in by["ai_assisted"]
    assert "AI as operational cause" not in by["ai_assisted"]
    assert "AI as operational cause" in by["ai_operational_cause"]
    assert "not AI-caused" not in by["ai_operational_cause"]


# ---------------- attribution ----------------

@needs_bundler
def test_atlas_unknown_attribution_never_renders_as_low_confidence(tmp_path_factory, served):
    """UNKNOWN is "not established". It shows no confidence word at all, even if a malformed record
    carried one, and it never falls through to the line a named actor gets."""
    out = _ts(tmp_path_factory, served, """
      const unknown = P.records.find((r) => r.attribution.status === "UNKNOWN").attribution;
      const forced = { ...unknown, confidence: "LOW" };
      const labels = input.method.attribution.labels;
      return {
        line: text(h(AttributionLine.AttributionLine, { a: unknown })),
        forced: text(h(AttributionLine.AttributionLine, { a: forced })),
        label: model.attributionConfidenceLabel(unknown, labels),
        forcedLabel: model.attributionConfidenceLabel(forced, labels),
        has: model.hasAttribution(unknown),
        low: model.attributionConfidenceLabel(P.records.find((r) => r.attribution.confidence === "LOW").attribution, labels),
      };
    """)
    for line in (out["line"], out["forced"]):
        assert line.startswith("Attribution: unknown (not established)"), line
        assert not re.search(r"confidence\s*:", line, re.I), line
        assert not re.search(r"\blow\b", line.split("—")[0], re.I), line
        assert "actor not named" not in line
    assert out["label"] is None and out["forcedLabel"] is None and out["has"] is False
    assert out["low"] == "Low", "a real low-confidence attribution still says so"


@needs_bundler
def test_atlas_not_applicable_attribution_renders_nothing(tmp_path_factory, served):
    out = _ts(tmp_path_factory, served, """
      return P.records.map((r) => ({ status: r.attribution.status, line: html(h(AttributionLine.AttributionLine, { a: r.attribution })),
                                     card: text(h(ImpactCard.ImpactCard, { record: r })) }));
    """)
    na = [x for x in out if x["status"] == "NOT_APPLICABLE"]
    assert na
    for x in na:
        assert x["line"] == "" and "Attribution:" not in x["card"]
    for x in out:
        if x["status"] != "NOT_APPLICABLE":
            assert "Attribution:" in x["line"]
        assert not re.search(r"\battacked\b", x["line"], re.I), "copy reports who attributes; it never says an actor attacked"


@needs_bundler
def test_atlas_disputed_attribution_lists_every_competing_attribution(tmp_path_factory, served):
    out = _ts(tmp_path_factory, served, """
      const a = P.records.find((r) => r.attribution.status === "DISPUTED").attribution;
      return { line: text(h(AttributionLine.AttributionLine, { a })), actors: a.competing.map((c) => c.actor) };
    """)
    assert len(out["actors"]) >= 2
    for actor in out["actors"]:
        assert f"attributed this to {actor}" in out["line"]
    assert "does not choose" in out["line"]


# ---------------- attempts ----------------

@needs_bundler
def test_atlas_attempts_never_enter_the_timeline_or_the_count(tmp_path_factory, served):
    """Also with an attempt wrongly filed among the records: it is still not a disruption."""
    out = _ts(tmp_path_factory, served, """
      const stray = { ...P.attempts[0], impact_id: "imp-stray-attempt" };
      const mixed = { ...P, records: [stray, ...P.records] };
      const res = {};
      for (const [name, p] of [["served", P], ["mixed", mixed]]) {
        const shown = filters.applyFilters(model.disruptions(p), atlas.atlasFilterDefs(p, input.method), filters.NO_FILTERS, input.today);
        res[name] = {
          timeline: atlas.groupByMonth(shown).flatMap((y) => y.months.flatMap((m) => m.records.map((r) => r.impact_id))),
          summary: atlas.corpusSummary(p),
          countries: atlas.countriesPresent(model.disruptions(p), p.countries).map((c) => c.a3),
          map: atlas.presenceCodes(p.records),
          attempts: model.attempts(p).map((r) => r.impact_id),
          forCountry: load.impactsFor(p, { a3: stray.country_a3 }).map((r) => r.record_kind),
        };
      }
      return res;
    """, {"today": AS_OF})
    recs = served["payload"]["records"]
    attempt = served["payload"]["attempts"][0]
    only_attempted = attempt["country_a3"]
    assert only_attempted not in {c for r in recs for c in ([r["country_a3"]] + (r.get("countries_a3") or []))}, \
        "the fixture's attempt must be in a country with no disruption"
    for name in ("served", "mixed"):
        got = out[name]
        assert got["timeline"] == [r["impact_id"] for r in recs], name
        assert got["summary"]["records"] == len(recs), name
        assert only_attempted not in got["countries"] and only_attempted not in got["map"], name
        assert got["summary"]["countries"] == len(got["countries"]), name
        assert got["forCountry"] == [], name
    assert out["served"]["attempts"] == [attempt["impact_id"]]
    assert out["mixed"]["attempts"] == [attempt["impact_id"], "imp-stray-attempt"]


# ---------------- counts and the presence map ----------------

@needs_bundler
def test_atlas_presence_map_never_encodes_a_count(tmp_path_factory, served):
    """One record or forty: the same fill. The map is built from a set of country codes."""
    out = _ts(tmp_path_factory, served, """
      const one = P.records.find((r) => r.country_a3 !== "MULTI");
      const many = [...P.records, ...Array.from({ length: 40 }, (_, i) => ({ ...one, impact_id: `dup-${i}` }))];
      return {
        base: atlas.presenceFill(atlas.presenceCodes(P.records)), heavy: atlas.presenceFill(atlas.presenceCodes(many)),
        codes: atlas.presenceCodes(many), none: atlas.presenceFill(atlas.presenceCodes([])),
        mark: atlas.PRESENCE_MARK, blank: atlas.PRESENCE_NONE,
      };
    """)
    assert out["base"] == out["heavy"], "forty more records in one country must not change the map"
    assert out["codes"] == sorted(set(out["codes"]))
    flat = json.dumps(out["base"])
    assert set(re.findall(r"#[0-9a-fA-F]{6}", flat)) == {out["mark"], out["blank"]}, "exactly one mark colour"
    assert not re.search(r"interpolate|step|\bget\b\W+\"(n|count|records)\"", flat)
    assert not [x for x in _walk(out["base"]) if isinstance(x, (int, float)) and not isinstance(x, bool)], "no number in the fill"
    assert out["none"] == out["blank"]


def _walk(x):
    if isinstance(x, list):
        for y in x:
            yield from _walk(y)
    else:
        yield x


@needs_bundler
def test_atlas_counts_are_never_per_country(tmp_path_factory, served):
    """The country filter declines the per-option counts the shared bar prints, the country list is
    names and codes only, in the served alphabetical order, and the summary is one corpus count."""
    out = _ts(tmp_path_factory, served, """
      const defs = atlas.atlasFilterDefs(P, input.method);
      const country = defs.find((d) => d.id === "country");
      return {
        counts: defs.filter((d) => d.kind === "choice").map((d) => [d.id, d.counts !== false]),
        options: country.options, list: atlas.countriesPresent(model.disruptions(P), P.countries),
        summary: atlas.corpusSummary(P),
      };
    """)
    counts = dict(out["counts"])
    assert counts["country"] is False
    assert all(v for k, v in counts.items() if k != "country"), "category filters keep their in-list counts"
    names = [o["label"] for o in out["options"]]
    assert names == [c["name"] for c in out["list"]]
    assert names == [c["name"] for c in served["payload"]["countries"] if c["name"] in names], "served (alphabetical) order"
    for c in out["list"]:
        assert not [k for k, v in c.items() if isinstance(v, (int, float)) and not isinstance(v, bool)], c
    assert set(out["summary"]) == {"records", "countries", "first", "last", "researched"}


@needs_bundler
def test_atlas_timeline_grouping_never_reorders(tmp_path_factory, served):
    out = _ts(tmp_path_factory, served, """
      const groups = atlas.groupByMonth(P.records);
      return { flat: groups.flatMap((y) => y.months.flatMap((m) => m.records.map((r) => r.impact_id))),
               years: groups.map((y) => y.year), months: groups.flatMap((y) => y.months.map((m) => m.ym)) };
    """)
    assert out["flat"] == [r["impact_id"] for r in served["payload"]["records"]]
    assert out["years"] == sorted(set(out["years"]), reverse=True)
    assert out["months"] == sorted(set(out["months"]), reverse=True)


# ---------------- presets, cyber and IT failure ----------------

@needs_bundler
def test_atlas_cyber_presets_never_include_an_it_failure(tmp_path_factory, served):
    """A non-malicious IT failure is not cyber: no cyber preset shows it, the cyber-mechanism filter
    does not offer it, and its own preset shows it and nothing else."""
    it = _it_failure(served)
    out = _ts(tmp_path_factory, served, """
      const p = { ...P, records: [input.it, ...P.records] };
      const defs = atlas.atlasFilterDefs(p, input.method);
      const res = { presets: {}, isCyber: model.isCyber(input.it), isIt: model.isItFailure(input.it) };
      for (const preset of atlas.atlasPresets(p)) {
        const state = atlas.presetState(preset, defs);
        res.presets[preset.id] = { ids: filters.applyFilters(model.disruptions(p), defs, state, input.today).map((r) => r.impact_id),
                                   query: atlas.presetQuery(preset, defs), filters: Object.keys(state.choices) };
      }
      const mech = defs.find((d) => d.id === "mech");
      res.mechValues = mech.values(input.it);
      res.mechOffersItOutage = mech.options.some((o) => o.value === "it_outage_affecting_operations");
      res.all = filters.applyFilters(model.disruptions(p), defs, filters.NO_FILTERS, input.today).length;
      res.maliciousSameMechanism = model.isItFailure({ ...input.it, cause_family: "cyber" });
      return res;
    """, {"it": it, "today": AS_OF})
    assert out["isCyber"] is False and out["isIt"] is True and out["maliciousSameMechanism"] is False
    presets = out["presets"]
    cyber_ids = {r["impact_id"] for r in served["payload"]["records"] if r["cause_family"] == "cyber"}
    assert set(presets["cyber"]["ids"]) == cyber_ids and cyber_ids
    for pid, got in presets.items():
        if pid == "it-failure":
            assert got["ids"] == [it["impact_id"]]
        else:
            assert it["impact_id"] not in got["ids"], pid
        if "cyber" in pid:
            assert set(got["ids"]) <= cyber_ids, pid
            assert "f.cause=cyber" in got["query"], pid
    assert out["mechValues"] == []
    assert out["all"] == len(served["payload"]["records"]) + 1


@needs_bundler
def test_atlas_default_view_shows_every_record_and_no_preset_filters_on_confidence(tmp_path_factory, served):
    """Hiding low-confidence records is never a default: an address with no filter shows all of them,
    and no preset touches evidence confidence."""
    out = _ts(tmp_path_factory, served, """
      const defs = atlas.atlasFilterDefs(P, input.method);
      const { state, notes } = filters.decodeFilters("?view=impacts", defs);
      return { shown: filters.applyFilters(model.disruptions(P), defs, state, input.today).map((r) => r.evidence_confidence.category),
               notes, active: filters.activeFilters(defs, state), preset: atlas.activePreset(atlas.atlasPresets(P), defs, state),
               presetFilters: atlas.atlasPresets(P).map((p) => Object.keys(p.choices)),
               ids: defs.map((d) => d.id) };
    """, {"today": AS_OF})
    cats = [r["evidence_confidence"]["category"] for r in served["payload"]["records"]]
    assert out["shown"] == cats and {"PRELIMINARY", "LIMITED"} <= set(cats)
    assert out["notes"] == [] and out["active"] == [] and out["preset"] is None
    assert all("conf" not in f and "date" not in f for f in out["presetFilters"])
    assert out["ids"] == ["date", "country", "domain", "sector", "tech", "cause", "mech", "it", "attr", "ai", "conf"]


@needs_bundler
def test_atlas_search_addresses_open_the_matching_presets(tmp_path_factory, served):
    """The search entries are links written by hand; each must be exactly what its preset writes."""
    out = run_ts(tmp_path_factory, {**IMPACT_MODULES, "search": "global/searchIndex.ts"}, PRELUDE + """
      const defs = atlas.atlasFilterDefs(P, input.method);
      const q = Object.fromEntries(atlas.atlasPresets(P).map((p) => [p.id, atlas.presetQuery(p, defs)]));
      return { q, entries: search.IMPACT_ENTRIES.map((e) => [e.key, e.action.href]) };
    """, served)
    entries = dict(out["entries"])
    assert entries["view:impacts"] == "?view=impacts"
    assert entries["view:impacts:cyber"] == f"?view=impacts&{out['q']['cyber']}"
    assert entries["view:impacts:ai"] == f"?view=impacts&{out['q']['ai']}"
    assert entries["view:impacts:attributed"] == f"?view=impacts&{out['q']['attributed-cyber']}"


# ---------------- abstraction ----------------

@needs_bundler
def test_atlas_abstracted_record_shows_no_place_and_no_headline(tmp_path_factory, served):
    """Even if a region or a headline reached an attack record, the card and the inspector show
    neither; and a kinetic record is abstracted whatever its policy field says."""
    out = _ts(tmp_path_factory, served, """
      const r = P.records.find((x) => x.publication_policy === "country_abstracted");
      const leak = (x) => ({ ...x, admin1: { code: "ZZ-99", name: "Leakedregion" }, geographic_precision: "admin1",
                             sources: x.sources.map((s) => ({ ...s, title_original: "Leakedheadline", title_en: "Leakedheadline" })) });
      const a = leak(r);
      const b = { ...leak(r), publication_policy: "standard" };
      const std = leak(P.records.find((x) => x.publication_policy === "standard" && x.cause_family === "natural_hazard"));
      const both = (x) => text(h(ImpactCard.ImpactCard, { record: x })) + " " + text(h(ImpactInspector.ImpactInspector, { record: x }));
      return { cause: r.cause_family, a: both(a), b: both(b), std: both(std), place: [model.placeText(a), model.placeText(b)], country: r.country_name };
    """)
    assert out["cause"] in ("kinetic", "sabotage")
    for shown in (out["a"], out["b"]):
        assert "Leakedregion" not in shown and "Leakedheadline" not in shown
        assert "Published under safeguards: place withheld" in shown
    assert out["place"] == [out["country"], out["country"]]
    assert "Leakedregion" in out["std"] and "Leakedheadline" in out["std"], "a standard record does show its region and headline"


# ---------------- the inspector and the confidence chip ----------------

@needs_bundler
def test_atlas_inspector_says_which_source_supports_which_claim(tmp_path_factory, served):
    out = _ts(tmp_path_factory, served, """
      const r = P.records.find((x) => x.attribution.status === "ATTRIBUTED");
      const chain = model.claimSupport(r, P.vocabularies.claims.map((c) => String(c.id)));
      return { chain: chain.map((c) => [c.claim, c.sources.map((s) => s.ref)]), sources: r.sources.map((s) => [s.ref, s.supports]),
               shown: text(h(ImpactInspector.ImpactInspector, { record: r })) };
    """)
    want = {}
    for ref, supports in out["sources"]:
        for claim in supports:
            want.setdefault(claim, []).append(ref)
    assert dict(out["chain"]) == want
    assert [c for c, _ in out["chain"]] == ["occurrence", "effect", "attribution"], "claims in the served order"
    assert "What each claim rests on" in out["shown"] and "What the evidence does not establish" in out["shown"]


@needs_bundler
def test_atlas_confidence_is_words_with_the_served_caveat(tmp_path_factory, served):
    out = _ts(tmp_path_factory, served, """
      const r = P.records.find((x) => x.evidence_confidence.category === "MODERATE");
      return { chip: text(h(ConfidenceChip.ConfidenceChip, { value: r.evidence_confidence })),
               none: text(h(ConfidenceChip.ConfidenceChip, { value: null })),
               why: text(h(ConfidenceChip.ConfidenceBreakdown, { value: r.evidence_confidence, method: input.method })),
               score: r.evidence_confidence.score, reasons: r.evidence_confidence.reasons };
    """)
    assert out["chip"].startswith("Evidence confidence: Moderate")
    assert out["none"].startswith("Evidence confidence: Not assessed") and not re.search(r"Preliminary|Limited|Low", out["none"])
    assert f"{out['score']} points : ordinal score, not a probability" in out["why"]
    assert not re.search(r"/\s*100|of 100|\d\s*%|percent", out["why"], re.I), "points only: never out of a hundred, never a percentage"
    assert served["method"]["statement"] in out["why"]
    for reason in out["reasons"]:
        assert reason in out["why"]


NOT_ASSESSED_REASON = "Cited through a discovery aid only; a primary source is not yet attached."


@needs_bundler
def test_atlas_not_assessed_confidence_is_its_own_state_with_its_reason(tmp_path_factory, served):
    """A null category is "Not assessed", shown with the served reason: never Preliminary, never an
    empty chip, its own bucket in the filter, and refused at load if it comes without a reason."""
    out = _ts(tmp_path_factory, served, """
      const na = { category: null, label: null, score: null, disputed: false, reason: input.reason };
      const recs = P.records.map((r, i) => (i < 2 ? { ...r, evidence_confidence: na } : r));
      const p = { ...P, records: recs };
      const defs = atlas.atlasFilterDefs(p, input.method);
      const conf = defs.find((d) => d.id === "conf");
      const pick = (v) => filters.applyFilters(model.disruptions(p), defs, filters.decodeFilters("?f.conf=" + v, defs).state, input.today).map((r) => r.impact_id);
      return {
        chip: text(h(ConfidenceChip.ConfidenceChip, { value: na })), chipHtml: html(h(ConfidenceChip.ConfidenceChip, { value: na })),
        card: text(h(ImpactCard.ImpactCard, { record: recs[0] })), inspector: text(h(ImpactInspector.ImpactInspector, { record: recs[0] })),
        options: conf.options, notAssessed: pick("NOT_ASSESSED"), preliminary: pick("PRELIMINARY"),
        buckets: conf.options.map((o) => pick(o.value).length), ids: recs.slice(0, 2).map((r) => r.impact_id),
        plainOptions: atlas.atlasFilterDefs(P, input.method).find((d) => d.id === "conf").options.map((o) => o.value),
        okShape: load.impactsProblems(p), bareNull: load.impactsProblems({ ...P, records: [{ ...P.records[0], evidence_confidence: { category: null } }] }),
      };
    """, {"reason": NOT_ASSESSED_REASON, "today": AS_OF})
    for shown in (out["chip"], out["card"], out["inspector"]):
        assert "Evidence confidence: Not assessed" in shown and NOT_ASSESSED_REASON in shown
    assert out["chip"] == f"Evidence confidence: Not assessed {NOT_ASSESSED_REASON}"
    assert "Preliminary" not in out["chip"] and "Preliminary" not in out["card"]
    assert not re.search(r"conf-(preliminary|limited|moderate|high)", out["chipHtml"])
    assert {"value": "NOT_ASSESSED", "label": "Not assessed"} in out["options"]
    assert out["notAssessed"] == out["ids"]
    assert not set(out["preliminary"]) & set(out["ids"])
    assert sum(out["buckets"]) == len(served["payload"]["records"]), "every record is in exactly one confidence bucket"
    assert "NOT_ASSESSED" not in out["plainOptions"]
    assert out["okShape"] == [] and out["bareNull"] == ["a record's evidence confidence is malformed"]


@needs_bundler
def test_atlas_origins_are_worded_by_their_served_basis(tmp_path_factory, served):
    """Publishers counted without review are "N distinct publishers cited; whether they relay one
    statement was not reviewed". No component composes "independent originating statements": only
    served text (the method's component label, a served reason) may say it."""
    out = _ts(tmp_path_factory, served, """
      const base = P.records.find((r) => r.evidence_confidence.category === "HIGH");
      const withBasis = (basis) => ({ ...base, evidence_confidence: { ...base.evidence_confidence,
        components: { ...base.evidence_confidence.components, origins: { ...base.evidence_confidence.components.origins, basis } } } });
      const servedText = [...input.method.components.map((c) => c.label), ...input.method.components.map((c) => c.meaning || ""),
                          ...input.method.categories.map((c) => c.meaning)];
      const own = (r) => {
        let t = text(h(ImpactCard.ImpactCard, { record: r })) + " " + text(h(ImpactInspector.ImpactInspector, { record: r }));
        for (const s of [...servedText, ...(r.evidence_confidence.reasons || [])]) if (s) t = t.split(s).join(" ");
        return t;
      };
      return { count: base.evidence_confidence.components.origins.count, n: base.origin_count,
               publishers: own(withBasis("publishers")), reviewed: own(withBasis("reviewed")), none: own(withBasis(undefined)),
               all: P.records.map(own),
               text: [model.originsText(3, "publishers"), model.originsText(1, "publishers"), model.originsText(2, "reviewed"), model.originsText(2, null)] };
    """)
    assert out["text"][0] == "3 distinct publishers cited; whether they relay one statement was not reviewed"
    assert out["text"][1].startswith("1 distinct publisher cited;")
    assert out["text"][3] == "2", "no basis, no claim about what the number counts"
    assert f"{out['count']} distinct publishers cited; whether they relay one statement was not reviewed" in out["publishers"]
    assert f"{out['n']} distinct publishers cited; whether they relay one statement was not reviewed" in out["publishers"]
    assert not re.search(r"originating statement", out["publishers"], re.I), "publishers are never called originating statements"
    assert "as established on review" in out["reviewed"]
    assert not re.search(r"originating statement", out["none"], re.I)
    for shown in out["all"] + [out["publishers"], out["reviewed"], out["none"]]:
        assert not re.search(r"independent originating statements", shown, re.I)


@needs_bundler
def test_atlas_confidence_explainer_shows_a_provisional_method_status(tmp_path_factory, served):
    out = _ts(tmp_path_factory, served, """
      const r = P.records.find((x) => x.evidence_confidence.category === "MODERATE");
      const why = (m) => text(h(ConfidenceChip.ConfidenceBreakdown, { value: r.evidence_confidence, method: m }));
      return { provisional: why({ ...input.method, status: input.status }), settled: why({ ...input.method, status: null }) };
    """, {"status": "provisional: thresholds not calibrated"})
    assert "Method status: provisional: thresholds not calibrated." in out["provisional"]
    assert "Method status" not in out["settled"]


@needs_bundler
def test_atlas_a_new_cause_family_needs_no_code_change(tmp_path_factory, served):
    """The cause list is the served vocabulary: a family the taxonomy adds is labelled and filterable."""
    out = _ts(tmp_path_factory, served, """
      const fam = { id: "authority_order", label: "Ordered by an authority", definition: "An authority ordered the service stopped." };
      vocab.forgetVocabularies();
      const v = { ...P.vocabularies, cause_families: [...P.vocabularies.cause_families, fam] };
      vocab.registerVocabularies(v);
      const rec = { ...P.records.find((r) => r.attribution.status === "NOT_APPLICABLE"), cause_family: "authority_order" };
      const p = { ...P, vocabularies: v, records: [rec, ...P.records.slice(1)] };
      const defs = atlas.atlasFilterDefs(p, input.method);
      return { card: text(h(ImpactCard.ImpactCard, { record: rec })), options: defs.find((d) => d.id === "cause").options.map((o) => o.label),
               shown: filters.applyFilters(model.disruptions(p), defs, filters.decodeFilters("?f.cause=authority_order", defs).state, input.today).length,
               cyber: model.isCyber(rec), abstracted: model.isAbstracted(rec) };
    """, {"today": AS_OF})
    assert "Cause: ordered by an authority" in out["card"]
    assert "Ordered by an authority" in out["options"] and out["shown"] == 1
    assert out["cyber"] is False and out["abstracted"] is False


@needs_bundler
def test_atlas_context_timeline_keeps_its_caveat_and_has_no_status_flag(tmp_path_factory, served):
    out = _ts(tmp_path_factory, served, """
      const ctx = input.context;
      return { shown: text(h(ContextTimeline.ContextTimeline, { ctx })),
               empty: text(h(ContextTimeline.ContextTimeline, { ctx: { ...ctx, entries: [] } })),
               reversed: text(h(ContextTimeline.ContextTimeline, { ctx: { ...ctx, entries: [...ctx.entries].reverse() } })),
               caveat: ContextTimeline.CONTEXT_CAVEAT };
    """)
    assert "No vessels, routes or bypass capacity are collected" in out["caveat"]
    for shown in (out["shown"], out["empty"]):
        assert out["caveat"] in shown and served["context"]["not_built"] in shown
    entries = served["context"]["entries"]
    older = [e for e in entries if not e["is_latest_of_type"]]
    assert older and out["shown"].count("Historical statement, as of") == len(older)
    assert not re.search(r"\b(is|are|remains?|currently|now) (open|closed|shut|blocked)\b", out["shown"].replace(served["context"]["not_built"], ""), re.I)
    # Newest first, whatever order the file is in.
    at = [out["reversed"].index(e["claim"]) for e in sorted(entries, key=lambda e: e["date"], reverse=True)]
    assert at == sorted(at)


# ---------------- the home page never requests the corpus ----------------

IMPACT_FILES = ("impacts.json", "regional_context.json", "evidence_confidence.json")


@needs_bundler
def test_atlas_home_route_never_requests_the_impact_corpus(tmp_path_factory, served):
    """Entering the home route starts no request for an impact file; entering the atlas does."""
    out = run_ts(tmp_path_factory, {"prefetch": "global/prefetch.ts", "router": "global/router.ts"}, """
      const asked = [];
      globalThis.fetch = (url) => { asked.push(String(url)); return Promise.resolve({ ok: true, json: () => Promise.resolve(input.payload) }); };
      const settle = () => new Promise((r) => setTimeout(r, 50));
      const res = {};
      for (const [name, route] of [["home", router.routeFor("")], ["atlas", router.routeFor("?view=impacts&f.cause=cyber")],
                                   ["sysWins", router.routeFor("?sys=us&view=impacts")]]) {
        asked.length = 0;
        prefetch.prefetchRoute(route);
        await settle();
        res[name] = { view: route.view, asked: [...asked] };
      }
      return res;
    """, {"payload": served["payload"]})
    assert out["home"]["view"] == "home" and out["home"]["asked"], "the home route does prefetch its own files"
    assert not [u for u in out["home"]["asked"] if u.endswith(IMPACT_FILES)], out["home"]["asked"]
    assert out["atlas"]["view"] == "impacts"
    assert [u for u in out["atlas"]["asked"] if u.endswith("global/impacts.json")], out["atlas"]["asked"]
    assert out["sysWins"]["view"] == "country"


def _home_graph(tmp_path):
    """Every source file the home page's code needs before anything is clicked: Root's static import
    graph, with each `import()` left as a separate chunk."""
    script = f"""
const esbuild = require({json.dumps(str(NODE_MODULES / "esbuild"))});
const r = esbuild.buildSync({{ entryPoints: [{json.dumps(str(SRC / "Root.tsx"))}], bundle: true, splitting: true, format: "esm",
  platform: "browser", outdir: {json.dumps(str(tmp_path))}, write: false, metafile: true, jsx: "automatic",
  nodePaths: [{json.dumps(str(NODE_MODULES))}], loader: {{ ".css": "empty" }}, logLevel: "error",
  define: {{ "import.meta.env.BASE_URL": '"/"', "import.meta.env.DEV": "false", "import.meta.env.PROD": "true" }} }});
const outs = r.metafile.outputs;
const entry = Object.keys(outs).find((k) => (outs[k].entryPoint || "").replace(/\\\\/g, "/").endsWith("src/Root.tsx"));
const seen = new Set();
const walk = (k) => {{ if (seen.has(k)) return; seen.add(k); for (const i of outs[k].imports) if (i.kind === "import-statement") walk(i.path); }};
walk(entry);
const inputs = new Set();
for (const k of seen) for (const i of Object.keys(outs[k].inputs)) inputs.add(i.replace(/\\\\/g, "/"));
process.stdout.write(JSON.stringify([...inputs]));
"""
    r = subprocess.run([NODE, "-e", script], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-3000:]
    return json.loads(r.stdout)


@needs_bundler
def test_atlas_home_code_never_includes_the_atlas_or_its_loader(tmp_path):
    """The atlas is a lazy route: its view, its loader and its record components are in no file the
    home page downloads up front. (A static import of any of them would also make the home page's
    bundle carry the code that fetches the corpus.)"""
    inputs = _home_graph(tmp_path)
    assert any(i.endswith("src/global/GlobalHome.tsx") for i in inputs), "the graph must be the home page's"
    lazy = ("impacts/ImpactAtlas.tsx", "impacts/load.ts", "impacts/ImpactCard.tsx", "impacts/ImpactPresenceMap.tsx", "impacts/atlasModel.ts")
    for name in lazy:
        assert not [i for i in inputs if i.endswith(name)], f"{name} is loaded with the home page"
    for name in ("GlobalHome.tsx", "StartHere.tsx", "GlobalPanels.tsx", "homeModel.ts"):
        code = (SRC / "global" / name).read_text(encoding="utf-8")
        assert "impacts/" not in code and "loadImpacts" not in code, f"{name} must only link to the atlas"


@pytest.mark.repo_hygiene
def test_atlas_browser_fixture_is_the_pipelines_own_fixture_as_served(served):
    """web/e2e/fixtures/impacts22 feeds vitest and Playwright. It must be exactly what
    `python -m pipeline.global_impacts --fixture --as-of 2026-11-19` writes, so those tests read the
    shapes the build serves."""
    base = ROOT / "web" / "e2e" / "fixtures" / "impacts22"
    if not base.exists():
        pytest.skip("no browser fixtures in this checkout")
    for rel, key in ((G.IMPACTS_OUT, "payload"), (G.CONTEXT_OUT, "context"), (G.METHOD_OUT, "method")):
        on_disk = json.loads((base / rel).read_text(encoding="utf-8"))
        assert on_disk == json.loads(json.dumps(served[key])), f"{rel}: regenerate with --fixture --as-of {AS_OF} --out web/e2e/fixtures/impacts22"
