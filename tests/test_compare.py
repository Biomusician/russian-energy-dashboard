"""Iteration 21: the comparison workspace (`?compare=`).

The behaviour is tested where it ships: vitest on the row derivation and URL parsing
(web/src/global/compare.test.ts, router.test.ts) and Playwright on the page and its PNG
(web/e2e/compare.e2e.ts). These tests guard the same rules at the source, because the mutation
campaign runs pytest alone: a comparison that grows an event-count row, re-orders its columns by a
figure, turns a missing figure or "No index" into a zero, loses its export caveat, or stops writing
the selection into the URL must fail here too.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "web" / "src"
COMPARE_FILES = ("global/compare.ts", "global/CompareView.tsx", "global/compareExport.ts")


def _src(rel):
    return (SRC / rel).read_text(encoding="utf-8")


def _code(rel):
    """The file without comments, so a comment explaining a refusal is not read as the thing refused."""
    text = re.sub(r"/\*.*?\*/", "", _src(rel), flags=re.S)
    return re.sub(r"(?m)(^|\s)//.*$", r"\1", text)


EXPECTED_ROWS = [
    "view_type", "as_of", "index", "maturity", "last_pass", "lanes", "safeguards", "placement",
    "ctx_total_production", "ctx_crude_production", "ctx_gas_production", "ctx_electricity_generation",
    "reporting", "sourcing", "source_checks",
]

# Fields of a system payload that hold disruption tallies, held candidates or an index value.
TALLY_FIELDS = ("event_summary", "recorded_events", "withheld_records", "recovery_coverage", "outcome",
                "under_review", ".headline", "episodes", "country_level", "placed_in_a_region")


def test_compare_rows_are_declared_and_none_is_a_count():
    text = _src("global/compare.ts")
    m = re.search(r"export const COMPARE_ROW_IDS = \[(.*?)\] as const;", text, re.S)
    assert m, "COMPARE_ROW_IDS is declared in compare.ts"
    ids = re.findall(r'"([a-z_]+)"', m.group(1))
    assert ids == EXPECTED_ROWS
    for i in ids:
        assert not re.search(r"event|attack|held|severity|rank|score|count|incident", i), i
    # Every row the builder emits has a declared id.
    emitted = re.findall(r'\{ id: "([a-z_]+)"', text)
    assert len(emitted) > 0
    assert set(emitted) <= set(ids), set(emitted) - set(ids)


def test_compare_never_reads_a_tally_or_an_index_value():
    checked = 0
    for rel in COMPARE_FILES:
        code = _code(rel)
        for field in TALLY_FIELDS:
            assert field not in code, f"{rel} reads {field}"
        checked += 1
    assert checked == len(COMPARE_FILES)


def test_compare_never_sorts_its_columns():
    for rel in COMPARE_FILES:
        code = _code(rel)
        for op in (".sort(", ".toSorted(", "localeCompare", ".reverse("):
            assert op not in code, f"{rel} re-orders something with {op}"


def test_compare_missing_figure_stays_missing():
    for rel in COMPARE_FILES:
        code = _code(rel)
        assert not re.search(r"\?\?\s*0\b|\|\|\s*0\b", code), f"{rel} turns a missing value into zero"
    text = _src("global/compare.ts")
    assert 'if (v == null) return { kind: "no_data", text: "no data"' in text
    assert "row.values[metric] : null;" in text


def test_compare_no_index_is_words_never_zero():
    text = _src("global/compare.ts")
    assert 'export const NO_INDEX_MEANING = "No index is not a zero.";' in text
    assert 'return value("No index", col.system?.no_index_reason ?? GENERIC_NO_INDEX, ["No index (not a zero)"]);' in text
    assert "its value is not shown beside systems without one" in text


def test_compare_export_carries_its_caveats():
    text = _src("global/compare.ts")
    assert 'export const EXPORT_NOT_COMPARABLE = "Not comparable: event counts; this is context and research state only.";' in text
    foot = re.search(r"foot: \[(.*?)\],\n  \};", text, re.S)
    assert foot, "compareBriefLines has a footer"
    body = foot.group(1)
    assert "EXPORT_NOT_COMPARABLE" in body
    assert "NO_INDEX_MEANING" in body
    assert "Research coverage differs by system" in body
    sub = re.search(r"sub: `(.*?)`,", text, re.S).group(1)
    assert "Built " in sub and "ctxLine" in sub and "never ranked" in sub
    # The drawing draws the footer it is given, every line of it.
    draw = _code("global/compareExport.ts")
    assert "brief.foot.forEach(" in draw


def test_compare_selection_lives_in_the_url():
    router = _src("global/router.ts")
    assert 'if (p.has("compare")) return { view: "compare", ids: compareIdsFrom(p.getAll("compare").join(",")) };' in router
    assert "return `?compare=${compareIdsFrom(ids.join(\",\")).slice(0, MAX_COMPARE).map(encodeURIComponent).join(\",\")}`;" in router
    # sys and group are decided before compare.
    assert router.index('if (sys === "ru")') < router.index('p.has("compare")')
    assert router.index("if (group)") < router.index('p.has("compare")')
    view = _code("global/CompareView.tsx")
    assert "navigateCompare(next, true)" in view, "every edit rewrites the URL"
    assert "useState<string[]" not in view, "the selection is not held anywhere but the URL"
    assert "<CompareView ids={route.ids} />" in _src("Root.tsx")
    assert "navigateCompare([id])" in _src("global/CountryView.tsx"), "the country page leads to the workspace"


def test_compare_holds_no_list_of_systems():
    """The manifest says which systems exist; a list in the workspace would go stale silently."""
    for rel in COMPARE_FILES:
        code = _code(rel)
        assert not re.search(r"""["'](us|ca|cn|in|sa|ru|ir|iq|kw|bh|qa|om|ae)["']\s*,\s*["'][a-z]{2}["']""", code), rel
