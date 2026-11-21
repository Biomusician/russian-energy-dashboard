"""Iteration 21: the global home, search, Start-here and navigation.

Behaviour is tested in the browser (web/e2e/home.e2e.ts) and in vitest (searchNormalize,
homeModel). These Python tests guard the rules a refactor could quietly undo, so the mutation
campaign (which runs pytest only) can see them: a home card never reads a count, a score or a
held figure; the home page never re-orders the systems; the Start-here memory never lets a storage
failure escape; and the manifest carries each country's review date as a date, never a count.
"""

import json
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB_SRC = ROOT / "web" / "src" / "global"
SERVED = ROOT / "web" / "public" / "data"


def _code(path):
    """Source with comments removed, so a rule is not satisfied (or broken) by prose."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    return re.sub(r"\{/\*.*?\*/\}", "", text, flags=re.S)


def _function_body(text, name):
    start = text.index(f"function {name}(")
    nxt = re.search(r"\n(?:function |export |const |/\*\*)", text[start + 1:])
    return text[start: start + 1 + nxt.start()] if nxt else text[start:]


# Iteration 23: the country cards became rows of the "Where to explore" panel (SystemPanel.tsx,
# built by panelRows in homeSelection.ts), and their detail moved to the selection card (cardFor).
# What a row or a card may read from a system: its identity, the theatre's served headline, and
# dates. Never a count, a held figure, a maturity or a reporting tally.
ROW_FIELDS = {"id", "name", "kind", "headline"}
CARD_FIELDS = ROW_FIELDS | {"record_reviewed", "as_of"}
# Read as properties: the reader copy may say "records"; the code may not read a field of that name.
COUNTS = r"\.(length|corpus|held|withheld|events?|records|episodes|maturity|campaign_restricted)\b"


@pytest.mark.repo_hygiene
def test_a_country_card_reads_no_count_score_or_held_figure():
    panel = _code(WEB_SRC / "SystemPanel.tsx")
    model = _code(WEB_SRC / "homeSelection.ts")
    rows = _function_body(model, "panelRows")
    card = _function_body(model, "cardFor")
    for name, body, allowed in (("SystemPanel", panel, ROW_FIELDS), ("panelRows", rows, ROW_FIELDS), ("cardFor", card, CARD_FIELDS)):
        read = set(re.findall(r"\b(?:s|sys|within)\??\.(\w+)", body))
        assert read, f"{name} reads its system"
        assert read <= allowed, f"{name} reads {sorted(read - allowed)}: a count, score or held figure has no place on it"
        assert not re.search(COUNTS, body), f"{name} shows a count, a held figure or a maturity"


@pytest.mark.repo_hygiene
def test_the_theatre_entry_reads_no_count_or_held_figure():
    """The theatre row reads its served headline (value, label, date) and nothing else."""
    panel = _code(WEB_SRC / "SystemPanel.tsx")
    assert "s.headline.value" in panel and "s.headline.as_of" in panel
    assert not re.search(r"\bevent_count\b|\bsectors\b|\bcoverage\b", panel)


@pytest.mark.repo_hygiene
def test_the_home_page_never_reorders_systems():
    """The manifest's order is alphabetical by name. The home page filters it, never sorts it: an
    order by any figure (a date, a count, a size) is a ranking."""
    rows = _function_body(_code(WEB_SRC / "homeSelection.ts"), "panelRows")
    assert "m.systems.filter(" in rows
    for name, code in (("panelRows", rows), ("SystemPanel", _code(WEB_SRC / "SystemPanel.tsx")),
                       ("GlobalHome", _code(WEB_SRC / "GlobalHome.tsx"))):
        assert not re.search(r"\.sort\(|\.reverse\(|\.toSorted\(|\.toReversed\(|localeCompare", code), \
            f"{name} re-orders systems"


@pytest.mark.repo_hygiene
def test_start_here_memory_never_lets_a_storage_failure_escape():
    code = _code(WEB_SRC / "startHereMemory.ts")
    funcs = re.findall(r"(?ms)^(?:export )?function (\w+)\(.*?^\}", code)
    assert {"readDismissed", "writeDismissed", "defaultStorage"} <= set(funcs)
    for name in ("readDismissed", "writeDismissed", "defaultStorage"):
        body = _function_body(code, name)
        assert re.search(r"try \{", body) and re.search(r"\} catch", body), f"{name} lets a storage error escape"
        # Every storage access sits after the try.
        for m in re.finditer(r"getItem|setItem|removeItem|localStorage|getStorage\(\)", body):
            assert body.rfind("try {", 0, m.start()) != -1, f"{name}: storage touched outside the try"


def test_the_manifest_carries_each_countrys_review_date_and_null_for_no_record():
    import sys
    sys.path.insert(0, str(ROOT))
    from pipeline import build_systems as B, systems

    payloads = {sid: json.loads((SERVED / systems.root(sid) / "system.json").read_text(encoding="utf-8"))
                for sid in systems.COUNTRY_SYSTEMS}
    snap = json.loads((SERVED / "snapshot.json").read_text(encoding="utf-8"))
    m = B.build_manifest(payloads, snap, "2026-01-01T00:00:00+00:00")
    countries = [s for s in m["systems"] if s["kind"] == "country"]
    assert countries
    dates = nulls = 0
    for s in countries:
        assert "record_reviewed" in s, s["id"]
        assert s["record_reviewed"] == payloads[s["id"]]["record_reviewed"], s["id"]
        if s["record_reviewed"] is None:
            nulls += 1
        else:
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", s["record_reviewed"]), s["id"]
            dates += 1
    assert dates > 0 and nulls > 0, "both states must be exercised by the real data"
    # Still nothing rankable: no number on any country entry.
    for s in countries:
        assert not [k for k, v in s.items() if isinstance(v, (int, float)) and not isinstance(v, bool)], s["id"]


@pytest.mark.repo_hygiene
def test_reader_copy_on_the_new_surfaces_has_no_build_vocabulary():
    for name in ("GlobalHome.tsx", "GlobalNav.tsx", "StartHere.tsx", "glossary.ts", "GlobalPanels.tsx",
                 "SystemPanel.tsx", "SelectionCard.tsx", "homeSelection.ts", "WorldContext.tsx"):
        strings = re.findall(r'"([^"\n]{12,})"|>([^<>{}\n]{12,})<', _code(WEB_SRC / name))
        text = " ".join(a or b for a, b in strings)
        assert strings, name
        assert not re.search(r"\biteration\b|\bpayload\b|\bpipeline\b|\.json\b|\bD-\d\d\b", text, re.I), name


@pytest.mark.repo_hygiene
def test_search_folds_only_for_matching():
    """The search must never show its folded form: results render the entry's own label and the
    term as written."""
    nav = _code(WEB_SRC / "GlobalNav.tsx")
    assert "normalizeForSearch" not in nav, "the view must not fold displayed text"
    assert "{h.entry.label}" in nav and "{h.matched}" in nav
