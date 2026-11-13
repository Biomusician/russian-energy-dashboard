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


CARD_FIELDS = {"id", "name", "maturity", "campaign_restricted", "record_reviewed", "reporting_environment"}


def test_a_country_card_reads_no_count_score_or_held_figure():
    body = _function_body(_code(WEB_SRC / "GlobalHome.tsx"), "SystemCard")
    read = set(re.findall(r"\bs\.(\w+)", body))
    assert read, "the card reads its system"
    assert read <= CARD_FIELDS, f"a card reads {sorted(read - CARD_FIELDS)}: a count, score or held figure has no place on it"
    for obj, field in re.findall(r"\bmanifest\??\.(\w+)(?:\??\.(\w+))?", body):
        assert obj in {"groups", "reporting_environments"}, f"a card reads manifest.{obj}"
    assert not re.search(r"\.length\b|\bcorpus\b|\bheadline\b|\bheld\b|\bwithheld\b|\bevents?\b|\brecords\b|\bepisodes\b",
                         body, re.I), "a card shows a count, a score or a held figure"


def test_the_theatre_entry_reads_no_count_or_held_figure():
    body = _function_body(_code(WEB_SRC / "GlobalHome.tsx"), "TheatreEntry")
    assert not re.search(r"\.length\b|\bcorpus\b|\bheld\b|\bwithheld\b|\bevent_count\b|\brecords\b", body, re.I)


def test_the_home_page_never_reorders_systems():
    """The manifest's order is alphabetical by name. The home page filters it, never sorts it: an
    order by any figure (a date, a count, a size) is a ranking."""
    code = _code(WEB_SRC / "GlobalHome.tsx")
    assert "manifest?.systems.filter(" in code
    assert not re.search(r"\.sort\(|\.reverse\(|\.toSorted\(|\.toReversed\(|localeCompare", code), \
        "the home page re-orders systems"


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


def test_reader_copy_on_the_new_surfaces_has_no_build_vocabulary():
    for name in ("GlobalHome.tsx", "GlobalNav.tsx", "StartHere.tsx", "glossary.ts", "GlobalPanels.tsx"):
        strings = re.findall(r'"([^"\n]{12,})"|>([^<>{}\n]{12,})<', _code(WEB_SRC / name))
        text = " ".join(a or b for a, b in strings)
        assert strings, name
        assert not re.search(r"\biteration\b|\bpayload\b|\bpipeline\b|\.json\b|\bD-\d\d\b", text, re.I), name


def test_search_folds_only_for_matching():
    """The search must never show its folded form: results render the entry's own label and the
    term as written."""
    nav = _code(WEB_SRC / "GlobalNav.tsx")
    assert "normalizeForSearch" not in nav, "the view must not fold displayed text"
    assert "{h.entry.label}" in nav and "{h.matched}" in nav
