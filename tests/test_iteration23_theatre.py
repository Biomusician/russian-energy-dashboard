"""Iteration 23, theatre / ESDI / history red-team fixes.

Each test pins one finding of the iteration-23 methodology red teams (ESDI, concept, cross-layer,
implementation, information architecture). None changes a score: the ESDI is the same number
before and after; what changes is what the served data and the page SAY about it.

Frontend rules are pinned by running the shipped TypeScript (the esbuild harness of
tests/test_iteration21_testarch.py), so a mutant in Ribbon.tsx or Methodology.tsx is a mutant in
what these tests execute.
"""
import csv
import copy
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_iteration21_testarch import needs_bundler, run_ts

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
WEB = ROOT / "web" / "public" / "data"
SRC = ROOT / "web" / "src"
needs_build = pytest.mark.skipif(not (PROCESSED / "snapshot.json").exists(), reason="pipeline not run")
needs_web = pytest.mark.skipif(not (WEB / "snapshot.json").exists(), reason="no mirrored payload")


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _snap():
    return _read(PROCESSED / "snapshot.json")


def _payload():
    """The theatre bundle as the page loads it, from the mirrored web payload."""
    return {
        "snapshot": _read(WEB / "snapshot.json"),
        "national": _read(WEB / "index_national.json"),
        "regional": _read(WEB / "index_regional.json"),
        "taxonomy": _read(WEB / "taxonomy.json"),
        "incidents": _read(WEB / "incidents.json"),
        "buildChanges": _read(WEB / "build_changes.json") if (WEB / "build_changes.json").exists() else None,
    }


THEATRE = {
    "ribbon": "components/Ribbon.tsx", "insp": "components/Inspector.tsx", "meth": "components/Methodology.tsx",
    "ui": "components/ui.tsx", "sd": "statusDelay.ts", "it": "indexText.ts", "tabs": "components/tabs.tsx",
    "brief": "briefing.ts",
}

RENDER_RIBBON = """
  const b = { ...input, regions: [], assets: [] };
  const step = b.national.dates.length - 1;
  const el = React.createElement(ribbon.default, {
    bundle: b, step, currentDate: b.national.dates[step], onOpenMethodology: () => {}, onExplain: () => {},
    theatreName: "Russia, Belarus & Crimea", mode: "analyze", onMode: () => {} });
  return renderToStaticMarkup(el);
"""


def _text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).replace("&#x27;", "'").replace("&amp;", "&")


# ---------------- ESDI-03: the "no restoration report" count is a model count ----------------

def test_the_still_in_index_count_says_how_many_carry_a_recovery_report():
    """ESDI-03. `unresolved_count` counts facilities still above the scoring cutoff that no full
    reconstitution has closed. Six of the fifty carried a partial-restart or restoration report, so
    the label "with no restoration report" was false for them; the build now serves that number."""
    from pipeline import build_index
    def fac(status, resolved=False):
        return {"asset_id": status, "sector": "refining", "recovery": {
            "recovery_status": status, "resolved": resolved, "impairment_age_days": 10,
            "scoring_evidence_kind": "modelled"}}
    live = [fac("impaired"), fac("unknown"), fac("partial_restart"), fac("substantially_restored"),
            fac("fully_reconstituted", resolved=True)]
    rs = build_index._recovery_stats(live, [], {}, {})
    assert rs["unresolved_count"] == 4
    assert rs["unresolved_with_recovery_report"] == 2


@needs_build
def test_the_served_recovery_report_count_matches_the_served_facilities():
    snap = _snap()
    live = snap["live_disruptions"]
    assert len(live) < 80, "live_disruptions is capped at 80; this check needs the whole list"
    rs = snap["recovery_stats"]
    unresolved = [x for x in live if not x["recovery"]["resolved"]]
    assert rs["unresolved_count"] == len(unresolved)
    assert rs["unresolved_with_recovery_report"] == sum(
        1 for x in unresolved if x["recovery"]["recovery_status"] not in ("impaired", "unknown"))


@needs_bundler
def test_the_count_meaning_says_it_is_a_model_count(tmp_path_factory):
    out = run_ts(tmp_path_factory, THEATRE, """
      const P = { applied: true, evidence_embargo_days: 60 };
      return { label: sd.NO_REPORT_LABEL, six: sd.noReportMeaning("2026-11-20", P, 6),
               none: sd.noReportMeaning("2026-11-20", P, 0), unknown: sd.noReportMeaning("2026-11-20", P),
               noPolicy: sd.noReportMeaning("2026-11-20", { applied: false }, 1) };
    """)
    assert "no restoration report" not in out["label"].lower()
    assert "still in the index" in out["label"].lower()
    for key in ("six", "none", "unknown", "noPolicy"):
        assert "model count, not a reporting fact" in out[key]
        assert "decayed away is not counted" in out[key]
    assert "6 of them carry a partial-restart or restoration report" in out["six"]
    assert "None of them carries" in out["none"]
    assert "Some may carry" in out["unknown"] and not re.search(r"\d+ of them", out["unknown"])
    assert "1 of them carries" in out["noPolicy"]


@needs_bundler
@needs_web
def test_the_ribbon_counts_say_what_they_count(tmp_path_factory):
    payload = _payload()
    html = run_ts(tmp_path_factory, THEATRE, RENDER_RIBBON, payload)
    text = _text(html)
    assert "with no restoration report by the cut-off" not in text
    assert "still in the index, no full-restoration report by the cut-off" in text
    n = payload["snapshot"]["recovery_stats"]["unresolved_with_recovery_report"]
    assert f"{n} of them carr" in html.replace("&#x27;", "'"), "the tooltip must carry the served count"


# ---------------- ESDI-02: the horizon sweep where the headline is explained ----------------

@needs_bundler
@needs_web
def test_the_horizon_range_is_shown_where_the_headline_is_explained(tmp_path_factory):
    """ESDI-02. The served sweep moves the headline far more than the two sensitivities "Why this
    number?" showed. It is now in the headline inspector and on the ribbon's number."""
    payload = _payload()
    h = payload["snapshot"]["recovery_horizon_sensitivity"]
    out = run_ts(tmp_path_factory, THEATRE, """
      const b = { ...input, regions: [], assets: [] };
      const html = renderToStaticMarkup(React.createElement(insp.default, {
        bundle: b, target: [{ kind: "headline" }], onNavigate: () => {}, onClose: () => {} }));
      const [l, r] = input.snapshot.recovery_horizon_sensitivity.esdi_range;
      return { insp: html, none: it.horizonSensitivityText(null), lo: it.fmtIndex(l), hi: it.fmtIndex(r) };
    """, payload)
    # Rounded by the page's own formatter: Python's "{:.1f}" turns the served 1.65 into "1.6" (the
    # binary value is just under 1.65) where the page writes 1.7, and this test failed on a build
    # whose range happened to end in 5 (iteration 23, first gate on the merged branch).
    lo, hi = out["lo"], out["hi"]
    assert (lo, hi) != ("—", "—") and h["esdi_range"]
    text = _text(out["insp"])
    assert f"{lo} to {hi}" in text, "the inspector must show the served horizon range"
    assert "The assumption most of this number rests on" in text
    # Shown before the smaller sensitivities, not after them.
    assert text.index(f"{lo} to {hi}") < text.index("Removing transmission")
    assert out["none"] is None
    ribbon = run_ts(tmp_path_factory, THEATRE, RENDER_RIBBON, payload)
    value_title = re.search(r'class="esdi-value"[^>]*title="([^"]*)"', ribbon) or \
        re.search(r'title="([^"]*)"[^>]*class="esdi-value"', ribbon)
    assert value_title and f"{lo} to {hi}" in value_title.group(1)


# ---------------- ESDI-04: every scoring.json key is read or marked unread ----------------

# Maps whose children are taxonomy values the code looks up by data, not parameter names.
_DATA_KEYED = {"confidence_weights", "cause_weights", "recovery.sector_fallback_horizon_days",
               "recovery_precedence.confidence_rank", "damage_severity", "sector_weights",
               "transmission.voltage_weight", "sector_basis", "status_multipliers"}


def _pipeline_source():
    return "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "pipeline").glob("*.py"))


def _scoring_paths(d, prefix=""):
    for k, v in d.items():
        if k.startswith("_"):
            continue
        path = f"{prefix}{k}"
        yield path, k
        if isinstance(v, dict) and path not in _DATA_KEYED:
            yield from _scoring_paths(v, f"{path}.")


def test_every_scoring_key_is_read_or_marked_unread():
    """ESDI-04. `recovery.partial_operations_floor` (with a note saying impairment is "held no lower
    than" it) and `resolved_statuses` were read by no code, so the file described a rule the score
    does not apply. Every key is now either read by the pipeline or listed in `_unread_keys`."""
    scoring = _read(ROOT / "methodology" / "scoring.json")
    marked = scoring["_unread_keys"]
    unread = set(marked["descriptive"]) | set(marked["not_applied"])
    src = _pipeline_source()
    bad = []
    for path, key in _scoring_paths(scoring):
        if any(path == u or path.startswith(u + ".") for u in unread):
            assert not re.search(rf"[\"']{re.escape(key)}[\"']", src) or key in ("version",), \
                f"{path} is marked unread but the pipeline reads it"
            continue
        if not re.search(rf"[\"']{re.escape(key)}[\"']", src):
            bad.append(path)
    assert not bad, f"scoring.json keys read by no code and not marked unread: {bad}"
    for u in unread:
        node = scoring
        for part in u.split("."):
            assert part in node, f"_unread_keys names a key that does not exist: {u}"
            node = node[part]
    assert "NOT APPLIED" in scoring["recovery"]["_partial_note"]
    assert "held no lower than" not in scoring["recovery"]["_partial_note"]


def test_the_published_sector_basis_is_the_declared_one():
    """ESDI-04, adjacent: `sector_basis` was declared in scoring.json and restated by hand in
    explain.py. The explanation now reads the declared one."""
    from pipeline import explain
    declared = {k: v for k, v in _read(ROOT / "methodology" / "scoring.json")["sector_basis"].items()
                if not k.startswith("_")}
    assert explain.SECTOR_BASIS == declared


# ---------------- ESDI-05 / 06 / 07 / 12, C14, F7: served and on-screen copy ----------------

def test_the_horizon_comparison_is_computed_not_written_down():
    """ESDI-06. "The transmission saturation constant is worth under one index point" was a fixed
    string, true only on the day it was written."""
    from pipeline import horizon_sensitivity as H
    s = H._comparison(1.73, 13.89, {"esdi": 5.87, "esdi_excluding_transmission": 9.12})
    assert "12.16 index points" in s and "3.25 points" in s
    assert "under one index point" not in s
    assert "not available" in H._comparison(1.0, 2.0, {"esdi": 5.0, "esdi_excluding_transmission": None})


def test_the_renormalisation_note_says_transmission_is_not_a_capacity_share():
    """ESDI-07. The note said every included sector has a capacity denominator."""
    from pipeline import explain
    note = explain._renormalisation_note(["refining", "electric_generation", "transmission", "oil_logistics"])
    assert note.startswith("gas, coal have no basis")
    assert "event-burden figure, not a capacity share" in note
    assert "Transmission" not in explain._renormalisation_note(["refining"])


@needs_build
def test_served_copy_carries_no_retracted_or_false_statement():
    snap = _snap()
    verdict = snap["transmission_sensitivity"]["red_team_verdict"]
    assert "never needs a reconstitution duration" not in verdict, "ESDI-06: transmission decays on modelled horizons"
    assert "RETAINED" not in verdict and "independent" not in verdict
    h = snap["recovery_horizon_sensitivity"]["why_this_matters_more_than_the_transmission_sweep"]
    assert "under one index point" not in h
    assert f"{abs(snap['esdi_excluding_transmission'] - snap['esdi']):.2f} points" in h
    for s in ("data_quality.json", "refinery_reconciliation"):
        assert s not in snap["publication_freshness"]["note"] + snap["denominator_basis"]["refining_mtpa"]["census_vintage"]
    threshold = _read(ROOT / "data" / "curated" / "systems" / "inclusion_threshold.json")
    assert not any("not yet grouped" in w for w in threshold["known_weaknesses"]), "C14: episodes are grouped"


def test_methodology_doc_quotes_no_live_figure_it_cannot_keep():
    """ESDI-12 / C14. METHODOLOGY.md quoted 127 events and ~42% coverage six iterations after
    both changed. Live figures belong in CURRENT_STATE.md."""
    text = (ROOT / "docs" / "METHODOLOGY.md").read_text(encoding="utf-8")
    assert "127 " not in text and "~42%" not in text
    assert "219,992" not in text
    assert "broadly consistent with reported" not in text


def test_country_page_describes_the_theatre_method_correctly():
    """F7. The theatre's sector weights are a judgement, not shares of monitored capacity, and
    its decay is evidence-driven, not a fixed half-life."""
    text = (SRC / "global" / "CountryView.tsx").read_text(encoding="utf-8")
    assert "share of the monitored" not in text and "fixed half-life" not in text
    assert "fixed fading rate" not in text


@needs_bundler
@needs_web
def test_the_methodology_panel_says_what_the_model_does(tmp_path_factory):
    """ESDI-05, ESDI-06, ESDI-12, IA-09, IA-16, C6, run on the shipped panel with the served data."""
    payload = _payload()
    html = run_ts(tmp_path_factory, THEATRE, """
      const b = { ...input, regions: [], assets: [] };
      return renderToStaticMarkup(React.createElement(meth.default, { bundle: b, onClose: () => {} }));
    """, payload)
    text = _text(html)
    # ESDI-12: the per-event formula names damage severity; reconstitution caps, it does not collapse.
    assert "confidence × cause × damage severity × 0.5" in text
    assert "collapses" not in text
    # ESDI-05: the invariance claim was retracted in iteration 13.
    assert "essentially unchanged" not in text and "doesn't systematically bias" not in text
    # IA-16: no named attacked facility reads as "live-disrupted"; no hard-coded infrastructure sentence.
    assert "Live-disrupted" not in text and "carry a live disruption" not in text
    assert "not an operating status" in text
    for word in ("Kerch", "power bridge", "Taman"):
        assert word not in text
    top = payload["snapshot"]["transmission_concentration"]["top"][0]["name"]
    assert top not in text, "the top transmission contributor is a share, not a named facility"
    # IA-09: no repository file names or internal process labels.
    for s in ("scoring.json", "Red-team verdict", "Decision: stays", "attribution_confidence", "red-team."):
        assert s not in text, s
    # C6: theatre attribution is reported, never confirmed.
    assert "never as confirmed" in text
    # ESDI-07: the headline is not one capacity share.
    assert "mostly capacity shares" in text and "plus a transmission event count" in text
    # C1: the coverage numerator states the benchmark's window.
    assert "where the benchmark's table ends" in text


# ---------------- C1: coverage numerator inside the benchmark's window ----------------

def test_the_benchmark_window_is_read_from_its_last_period():
    from pipeline.run import benchmark_window_end as end
    assert end([{"period": "1st"}, {"period": "Feb '26– Jun '26"}]) == "2026-06-30"
    assert end([{"period": "Nov ’25–Dec ’25"}]) == "2025-12-31"
    assert end([{"period": "4th"}]) == "2026-02-23"
    assert end([{"period": "recent"}]) is None and end([]) is None and end(None) is None


def test_strikes_after_the_benchmark_window_are_not_in_the_ratio():
    """C1. The ribbon divided strikes up to the build date by a benchmark that ends in June 2026,
    so the ratio climbed every build with no new benchmark."""
    from pipeline import run
    inc = lambda d, cls="refinery", cause="kinetic_strike": {"date": d, "asset_class": cls, "cause": cause}
    in_aoi = [inc("2026-06-30"), inc("2026-06"), inc("2026-07-01"), inc("2026-11-19"),
              inc("2026-05-01", "substation"), inc("2026-05-01", cause="technical")]
    snapshot = {"recovery_stats": {"by_sector": {}}, "facet_counts": {"asset_class": {}}, "as_of": "2026-11-20"}
    bench = {"reported_total_strikes": 10, "by_period": [{"period": "Feb '26– Jun '26"}]}
    oil, _ = run._build_coverage(in_aoi, bench, snapshot)
    assert oil["enumerated_oil_strikes"] == 2 and oil["enumerated_after_window"] == 2
    assert oil["coverage_ratio"] == 0.2
    assert oil["numerator_window_end"] == "2026-06-30" and "2026-06-30" in oil["numerator_definition"]
    unread, _ = run._build_coverage(in_aoi, {**bench, "by_period": [{"period": "??"}]}, snapshot)
    assert unread["enumerated_oil_strikes"] == 4 and unread["numerator_window_end"] is None
    assert "could not be read" in unread["numerator_definition"]


# ---------------- C6 / F6 / XL-06: theatre attribution ----------------

def test_no_curated_incident_without_an_attribution_carries_an_attribution_confidence():
    """The data bug behind XL-06: cur-naftan-2025-11, a technical fire with attribution none,
    carried attribution_confidence "confirmed"."""
    with open(ROOT / "data" / "curated" / "incidents.csv", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    bad = [r["incident_id"] for r in rows
           if r["attribution"] in ("", "none") and r["attribution_confidence"] not in ("", "not_applicable")]
    assert not bad, bad


def test_the_score_does_not_read_attribution_confidence():
    """The display fix is display-only because the scorer never reads the label. If it ever does,
    changing what the label means becomes a methodology question."""
    for f in ("build_index.py", "recovery.py", "explain.py"):
        assert "attribution_confidence" not in (ROOT / "pipeline" / f).read_text(encoding="utf-8"), f


@needs_bundler
def test_a_curated_confirmed_label_never_reads_as_confirmed(tmp_path_factory):
    """C6 / F6 / XL-06. 38 curated strikes rendered "(confirmed) — reported, not independently
    confirmed", most on a single article."""
    inc = {"incident_id": "x", "asset_name": "SYNTHETIC depot", "date": "2024-04-24", "date_precision": "day",
           "cause": "kinetic_strike", "confidence": "probable", "attribution": "reported_ukrainian_strike",
           "attribution_confidence": "confirmed", "sources": [], "notes": None}
    out = run_ts(tmp_path_factory, THEATRE, """
      const row = (c) => renderToStaticMarkup(React.createElement(ui.EventRow, { incident: { ...input, attribution_confidence: c } }));
      return { confirmed: row("confirmed"), probable: row("probable"), possible: row("possible"),
               none: ui.theatreAttribution("none", "confirmed") };
    """, inc)
    for k in ("confirmed", "probable"):
        t = _text(out[k])
        assert "Attribution: reported Ukrainian strike" in t and "not independent confirmation" in t
        assert "(confirmed)" not in t and "(probable)" not in t
    assert "Possibly a Ukrainian strike".lower() in _text(out["possible"]).lower()
    assert out["none"] is None


# ---------------- F8: null is not zero ----------------

def test_a_percentage_of_nothing_is_null():
    from pipeline import build_index as B
    assert B._pct(5, 0) is None and B._pct(5, None) is None and B._pct(1, 4) == 25.0
    assert B._heating_exposure(10, 100, heating=False) is None
    assert B._heating_exposure(10, 100, heating=True) == 10.0
    assert B._heating_exposure(10, 0, heating=True) is None


@needs_build
def test_uncovered_sectors_and_missing_denominators_are_null_in_every_served_file():
    """F8. Gas and coal were served as 0.0 nationally, in 80 regions and in both series; a region
    with no census capacity was "0 MW" with a 0.0 generation margin."""
    snap = _snap()
    nat = _read(PROCESSED / "index_national.json")
    reg = _read(PROCESSED / "index_regional.json")
    for s in snap["sectors_uncovered"]:
        assert snap["sectors"][s] is None
        assert all(v is None for v in nat["sectors"][s])
        assert snap["explanations"]["sectors"][s]["value"] is None
        for code, r in snap["regions"].items():
            assert r["sectors"][s] is None, code
            assert all(v is None for v in reg["regions"][code]["sectors"][s]), code
    for s in snap["sectors_covered"]:
        assert snap["sectors"][s] is not None and None not in nat["sectors"][s]
    for code, r in snap["regions"].items():
        assert r["installed_mw"] != 0, f"{code}: no capacity figure is null, not 0 MW"
        if r["installed_mw"] is None:
            assert r["effects"]["generation_margin"] is None, code
            assert r["effects"]["heating_season_exposure"] is None, code
    assert set(snap["effects_null_reasons"]) >= {"generation_margin", "heating_season_exposure"}


def _synthetic_build():
    """A two-region build from invented records: region RA has a refinery strike and 1,000 MW in
    the census; region RB has a struck power plant and no census capacity (Crimea's shape)."""
    from pipeline import build_index as B
    inc = lambda iid, aid, cls, region: {
        "incident_id": iid, "asset_id": aid, "asset_class": cls, "region_code": region, "date": "2026-11-01",
        "date_precision": "day", "cause": "kinetic_strike", "confidence": "confirmed", "status": "damaged",
        "asset_name": aid, "attribution": "none", "attribution_confidence": "not_applicable"}
    incidents = [inc("i1", "ref-a", "refinery", "RA"), inc("i2", "plant-b", "power_plant_thermal", "RB")]
    facilities = [{"asset_id": "ref-a", "asset_class": "refinery", "region_code": "RA", "capacity_mtpa": 10, "name": "A"}]
    assets = [{"asset_id": "plant-a", "asset_class": "power_plant_thermal", "region_code": "RA", "capacity_mw": 1000, "name": "P"}]
    meta = {"RA": {"name": "SYNTHETIC A", "district": "X", "country": "RU"},
            "RB": {"name": "SYNTHETIC B", "district": "X", "country": "RU"}}
    return B.build(incidents, facilities, assets, 100.0, meta, "2026-11-20")


def test_a_build_serves_null_for_what_it_cannot_measure():
    """F8, through the real builder rather than the committed payload, so a change to how the
    series are assembled cannot pass on a stale file."""
    nat, reg, snap = _synthetic_build()[:3]
    assert snap["sectors"]["refining"] > 0
    for s in snap["sectors_uncovered"]:
        assert snap["sectors"][s] is None and all(v is None for v in nat["sectors"][s])
        assert all(v is None for v in reg["RB"]["sectors"][s]) and snap["regions"]["RA"]["sectors"][s] is None
    rb = snap["regions"]["RB"]
    assert rb["installed_mw"] is None and snap["regions"]["RA"]["installed_mw"] == 1000
    assert rb["effects"]["generation_margin"] is None
    assert "electric_generation" in rb["regional_intensity"]["missing_sectors"]


@needs_build
def test_a_disrupted_sector_with_no_regional_base_is_listed_missing():
    """F8. Crimea has struck generation plants and no census capacity: its generation intensity
    was null and the sector appeared in neither covered_sectors nor missing_sectors."""
    snap = _snap()
    for code, r in snap["regions"].items():
        ri = r.get("regional_intensity") or {}
        disrupted = {x["sector"] for x in snap["live_disruptions"] if x["region_code"] == code}
        for s in disrupted:
            assert s in ri["covered_sectors"] or s in ri["missing_sectors"], (code, s)


@needs_bundler
def test_no_capacity_figure_never_reads_as_zero_megawatts(tmp_path_factory):
    out = run_ts(tmp_path_factory, THEATRE, "return [tabs.installedText(null), tabs.installedText(0 === 1 ? 0 : 1250)];")
    assert out[0] == "no capacity figure in the census" and out[1] == "1,250 MW"


# ---------------- IA-16: no named facility in the transmission concentration note ----------------

@needs_build
def test_the_transmission_concentration_note_is_built_from_the_data():
    snap = _snap()
    tc = snap["transmission_concentration"]
    for t in tc["top"]:
        assert t["name"] not in tc["note"]
    assert f"{tc['occupied_share_pct']:g}%" in tc["note"]
    src = (ROOT / "pipeline" / "build_index.py").read_text(encoding="utf-8")
    assert "Kerch" not in src and "Taman" not in src
    # ESDI-06: transmission decays on the modelled substation and line horizons like any sector.
    assert "never needs a reconstitution duration" not in src


# ---------------- XL-12: "first served" is never "learned" ----------------

def _strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"(?m)//.*$", "", text)


def test_no_reader_text_says_the_dashboard_learned_of_an_event():
    """XL-12. Comparison.tsx said events were "Counted by when the dashboard LEARNED of each
    event"; a first-served date is when the dashboard served a record, not when anyone learned of
    it. The semantic lint in test_pipeline.py exempts any sentence containing "not ", so it never
    saw that sentence; this check has no exemption."""
    pat = re.compile(r"\b(?:dashboard|dataset|we|site)\s+learned\b", re.I)
    hits = []
    for p in SRC.rglob("*.ts*"):
        if ".test." in p.name:
            continue
        for m in pat.finditer(_strip_comments(p.read_text(encoding="utf-8"))):
            hits.append(f"{p.relative_to(ROOT)}: {m.group(0)}")
    assert not hits, hits


# ---------------- H-M3, H-M4: history labels ----------------

def test_a_past_date_build_is_labelled_a_reconstruction_at_the_call_site():
    """H-M3. The call site compares as_of with today's calendar date. Comparing it with itself
    would label every reconstruction a current build, and no test ran the call site."""
    from pipeline import run
    past = run.history_concept(SimpleNamespace(as_of="2026-01-01", mode="reconstruction"))
    assert past["mode"] == "current_evidence_reconstruction"
    assert run.history_concept(SimpleNamespace(as_of="2026-01-01", mode="fixture"))["mode"] == "engineering_fixture"


@needs_bundler
@needs_web
def test_a_reconstructed_payload_says_so_on_the_ribbon(tmp_path_factory):
    """H-M4. A --as-of payload at its own last step is a reconstruction; the ribbon must say so
    and must not call it fresh."""
    payload = _payload()
    payload["snapshot"] = {**payload["snapshot"], "history_concept": {
        "mode": "current_evidence_reconstruction", "label": "Pinned-source reconstruction for 2026-01-01", "note": "x"}}
    text = _text(run_ts(tmp_path_factory, THEATRE, RENDER_RIBBON, payload))
    assert "Pinned-source reconstruction for 2026-01-01" in text
    current = _text(run_ts(tmp_path_factory, THEATRE, RENDER_RIBBON, _payload()))
    assert "reconstruction" not in current.lower()


def test_h01_the_cannot_tell_you_list_never_calls_the_model_count_no_restoration_report():
    """H-01 (first-time-user red team). recovery_stats.unresolved_count is a model count of facilities
    still in the index; the served "cannot tell you" sentence called it disruptions with no
    published restoration report, though some of them carry one."""
    from pipeline import data_quality as DQ
    snap = copy.deepcopy(_snap())
    snap["recovery_stats"] = {**snap["recovery_stats"], "unresolved_count": 49, "unresolved_with_recovery_report": 6}
    explanations = json.loads((ROOT / "data" / "processed" / "explanations_regional.json").read_text(encoding="utf-8"))
    text = " ".join(i["answer"] for i in DQ.cannot_tell_you(snap, explanations))
    assert "have no published restoration report" not in text
    assert "49 struck facilities are still counted in the index with no report that closes the disruption" in text
    assert "(6 of them carry a partial-restart or restoration report that did not close it)" in text


# --- final methodology red team (iteration 23) ------------------------------------------------------

@needs_build
def test_f3_reported_effects_are_counted_apart_from_capacity_removed():
    """F-3: "0 of N events state how much capacity they removed" sat beside events whose observed
    halt or outage the dashboard publishes. Each figure now says what it counts."""
    snap = _read(PROCESSED / "snapshot.json")
    by_incident = snap["strategic_effects"]["by_incident"]
    assert snap["incidents_with_reported_effect"] == sum(1 for v in by_incident.values() if v)
    ribbon = (ROOT / "web" / "src" / "components" / "Ribbon.tsx").read_text(encoding="utf-8")
    assert "events state how much capacity they removed" not in ribbon
    assert "incidents_with_reported_effect" in ribbon and "MW or Mt/yr" in ribbon and "not scored" in ribbon
    method = (ROOT / "web" / "src" / "components" / "Methodology.tsx").read_text(encoding="utf-8")
    assert "carry a quantified\n            capacity effect" not in method and "incidents_with_reported_effect" in method
    facts = _read(PROCESSED / "global" / "help_facts.json")
    assert facts["theatre"]["coverage"]["incidents_with_reported_effect"] == snap["incidents_with_reported_effect"]


def _px(css, selector_line):
    m = re.search(re.escape(selector_line) + r"[^}]*?font-size:\s*([\d.]+)px", css)
    assert m, selector_line
    return float(m.group(1))


def test_f4_ratios_at_headline_weight():
    """F-4: CLAUDE.md puts the coverage ratios at the headline's visual weight. They were 19 px
    regular beside a 40 px semibold index."""
    css = (ROOT / "web" / "src" / "styles" / "theatre.css").read_text(encoding="utf-8")
    rule = re.search(r"\n\.known-num \{([^}]*)\}", css).group(1)
    assert "font-family: var(--mono)" in rule and "font-weight: 600" in rule
    head = _px(css, ".theatre-ribbon .esdi-value {")
    head_compact = _px(css, 'html[data-chrome="compact"] .theatre-ribbon .esdi-value {')
    assert _px(css, "\n.known-num {") >= head * 0.66
    assert _px(css, 'html[data-chrome="compact"] .known-num {') >= head_compact * 0.66
    phone = css[css.index("  .hl-block { flex: 1 1 100%"):]
    assert _px(phone, ".known-num, html[data-chrome=\"compact\"] .known-num {") >= _px(phone, ".theatre-ribbon .esdi-value") * 0.66
