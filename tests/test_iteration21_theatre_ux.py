"""Iteration 21: theatre UX rules that must not quietly regress.

The behaviour itself is exercised in a real browser (web/e2e/theatre-ux.e2e.ts). These tests guard
the same rules at the source and payload level so that the mutation campaign, which runs pytest
only, can show each rule is actually protected.
"""
import json
import re
from pathlib import Path

import pytest

from pipeline import recovery as R

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "web" / "src"
SNAPSHOT = ROOT / "web" / "public" / "data" / "snapshot.json"


def _src(rel):
    return (SRC / rel).read_text(encoding="utf-8")


def _body(text, start, end="\n}\n"):
    """The text of a function from its opening line to its closing brace at column 0."""
    i = text.index(start)
    return text[i:text.index(end, i)]


# --- withheld facility status -----------------------------------------------------------------

@pytest.mark.repo_hygiene
def test_withheld_row_shows_no_status_chip():
    ui = _src("components/ui.tsx")
    line = _body(ui, "export function RecoveryLine(")
    guard = "if (statusWithheld(r)) return <WithheldStatus note={r.publication_note!} />;"
    assert guard in line, "RecoveryLine no longer returns early for a withheld record"
    assert line.index(guard) < line.index("<EvidenceChip"), "a status chip renders before the withheld check"
    withheld = _body(ui, "function WithheldStatus(")
    for forbidden in ("EvidenceChip", "STATUS_LABEL", "impairment_age_days", "reconstitution_horizon_days",
                      "estimate_days", "recovery_status"):
        assert forbidden not in withheld, f"the withheld line shows {forbidden}"
    assert "Status withheld" in withheld
    predicate = _body(ui, "export function statusWithheld(")
    assert "publication_note" in predicate and '"impaired"' in predicate and '"unknown"' in predicate


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="no built payload")
def test_every_withheld_record_is_caught_by_the_frontend_predicate():
    """The frontend treats a record as withheld when its note is present and nothing is released
    (status impaired/unknown). Every record carrying the plain withheld note must satisfy that,
    or a withheld record would fall through to the full status line."""
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    checked = 0
    for d in snap["live_disruptions"]:
        r = d["recovery"]
        if r.get("publication_note") == R.WITHHELD_NOTE:
            assert not r.get("resolved"), d["asset_id"]
            assert r.get("recovery_status") in (None, "impaired", "unknown"), d["asset_id"]
            checked += 1
    assert checked > 0


# --- "Why this number?" -----------------------------------------------------------------------

@pytest.mark.repo_hygiene
def test_why_this_number_opens_the_inspector():
    ribbon = _src("components/Ribbon.tsx")
    m = re.search(r'<button type="button" className="why-btn"(.*?)</button>', ribbon, re.S)
    assert m, "the headline has no 'Why this number?' button"
    button = m.group(1)
    assert "Why this number?" in button
    assert 'aria-label="Why this number? Explain the Monitored-Area ESDI"' in button
    assert "onClick={explainHeadline}" in button
    assert ('const explainHeadline = () => onExplain(isLatest ? { kind: "headline" } : '
            '{ kind: "historical", step });') in ribbon
    # It sits inside the headline region, not somewhere else in the header.
    head = ribbon[ribbon.index('<section className="hl-block" aria-label="Headline">'):]
    assert head.index('className="why-btn"') < head.index("</section>")


# --- the view switch never touches shareable state --------------------------------------------

URL_STATE_SETTERS = ("setSelected", "setSelectedAsset", "setFilters", "setCamera", "setStep",
                     "setCompareRegions", "setCompare(", "replaceState", "pushState", "setFlyTarget")


@pytest.mark.repo_hygiene
def test_mode_switch_keeps_url_state():
    app = _src("App.tsx")
    switch = _body(app, "const switchMode = (target: TheatreMode) => {", "\n  };\n")
    for setter in URL_STATE_SETTERS:
        assert setter not in switch, f"switching views calls {setter}"
    assert "enterBriefing()" in switch and "exitBriefing()" in switch and "setMapFocus(" in switch
    # The URL mirror depends only on shareable state, never on the view.
    effect = app[app.index("const q = encodeDeepLink({"):]
    effect = effect[:effect.index("}, [bundle, filters, selected, step, camera, compareRegions]);")]
    assert "mapFocus" not in effect and "briefing" not in effect.replace("Briefing", "")
    # And the bar's buttons go through it: one handler, three modes.
    assert "onMode={switchMode}" in app


@pytest.mark.repo_hygiene
def test_mode_switch_keeps_the_names_links_and_tests_use():
    mode = _src("theatreMode.ts")
    assert 'label: "Map focus"' in mode and 'label: "Briefing & export"' in mode and 'label: "Analyze"' in mode


# --- the app frame cannot be scrolled sideways ------------------------------------------------

@pytest.mark.repo_hygiene
def test_closed_drawers_cannot_scroll_the_app():
    css = _src("styles/theatre.css")
    assert re.search(r"#root,\s*\.shell\s*\{\s*overflow:\s*clip;\s*\}", css), \
        "the app frame can be scrolled programmatically again"
    assert re.search(r'\.dossier:not\(\.drawer-open\)[^{]*\{[^}]*visibility:\s*hidden', css, re.S), \
        "a closed drawer can take focus again"


# --- one name for the theatre -----------------------------------------------------------------

def test_theatre_has_one_reader_facing_name():
    bar = _src("components/TheatreBar.tsx")
    manifest = json.loads((ROOT / "web" / "public" / "data" / "global" / "manifest.json").read_text(encoding="utf-8"))
    theatre = next(s for s in manifest["systems"] if s["kind"] == "theatre")
    assert f'THEATRE_FALLBACK_NAME = "{theatre["name"]}"' in bar
    index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "Western Russia & Belarus" not in index
    assert "document.title = `Energy Disruption Monitor — ${theatreName}`" in _src("App.tsx")
