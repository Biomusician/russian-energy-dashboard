"""Iteration 21: the regional overview's map, member list and brief.

The browser tier (web/e2e/gulfmap.e2e.ts) exercises the page itself. These checks pin the rules in
source so the mutation campaign, which has no browser, can show each one is guarded: a chosen
figure shows its definition and the accounting convention, the map opens as geography only, the
member list is in name order, and the brief never carries the reader's selection or zoom.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "web" / "src" / "global"
WEB = ROOT / "web" / "public" / "data"
needs_payload = pytest.mark.skipif(not (WEB / "global" / "gulf.json").exists(), reason="no built payload")


def _src(name):
    return (SRC / name).read_text(encoding="utf-8")


def _function_body(text, name):
    """The text of one exported function, from its signature to the next top-level declaration."""
    m = re.search(rf"export function {name}\b.*?(?=\n(?:export |const |function |type |/\*\*)|\Z)", text, re.S)
    assert m, f"{name} not found"
    return m.group(0)


def _facts_panel(view):
    m = re.search(r'aria-label="About this figure".*?</section>', view, re.S)
    assert m, "the figure's facts panel is missing"
    return m.group(0)


@pytest.mark.repo_hygiene
def test_iter21_gulf_metric_definition_beside_the_control():
    facts = _function_body(_src("groupMap.ts"), "metricFacts")
    for field in ("definition: m.definition", "year: m.year", "unit: m.unit", "source: src?.name"):
        assert field in facts, field
    panel = _facts_panel(_src("GroupView.tsx"))
    for shown in ("{facts.definition}", "{facts.year}", "{facts.unit}", "facts.source"):
        assert shown in panel, shown
    assert re.search(r'className="metric-definition[^"]*">\{facts\.definition\}</p>', panel)


@pytest.mark.repo_hygiene
def test_iter21_gulf_accounting_convention_beside_every_figure():
    facts = _function_body(_src("groupMap.ts"), "metricFacts")
    assert "accounting: ctx.accounting_convention" in facts
    panel = _facts_panel(_src("GroupView.tsx"))
    assert re.search(r"\{facts\.accounting && <p[^>]*metric-accounting[^>]*>.*?\{facts\.accounting\}</p>\}", panel, re.S)


@needs_payload
def test_iter21_gulf_payload_gives_every_metric_a_definition_and_states_its_accounting():
    g = json.loads((WEB / "global" / "gulf.json").read_text(encoding="utf-8"))
    assert g["metrics"], "no metric to check"
    for mid, m in g["metrics"].items():
        assert m["definition"].strip() and m["unit"].strip() and m["year"], mid
        assert m["source_id"] in g["sources"], mid
    assert g.get("accounting_convention", "").strip()


@pytest.mark.repo_hygiene
def test_iter21_gulf_default_map_is_geography_only():
    view = _src("GroupView.tsx")
    assert "const [metric, setMetric] = useState<string | null>(null);" in view
    assert "const colourBy = metric && ctx?.metrics[metric] ? metric : null;" in view
    # The map's colour follows colourBy, never the table's fallback metric.
    assert "groupFill(ctx.systems, colourBy, inSubset)" in view
    fill = _function_body(_src("groupMap.ts"), "memberColour")
    assert "if (!metricId) return NEUTRAL;" in fill
    assert 'note={colourBy ? null : "Geography only' in view


@pytest.mark.repo_hygiene
def test_iter21_gulf_member_list_is_alphabetical():
    order = _function_body(_src("groupMap.ts"), "membersAlphabetical")
    assert "a.name.localeCompare(b.name" in order
    assert "values" not in order, "a figure takes part in the member order"
    view = _src("GroupView.tsx")
    assert "const listed = useMemo(() => membersAlphabetical(shown), [shown]);" in view
    assert "{listed.map((s) => (" in view


@pytest.mark.repo_hygiene
def test_iter21_gulf_brief_drops_the_readers_selection():
    view = _src("GroupView.tsx")
    run = re.search(r"const runExport = async \(\) => \{.*?\n  \};", view, re.S)
    assert run, "runExport not found"
    body = run.group(0)
    assert "transformStyle: (st) => briefStyle(st, ctx, metricId)" in body
    assert "fit: { bounds, padding: GROUP_BRIEF_FIT_PADDING }" in body
    brief = re.search(r"function briefStyle\(.*?\n\}", view, re.S)
    assert brief, "briefStyle not found"
    assert "const clean = withoutHighlight(style);" in brief.group(0)
    # Every member coloured in the brief, whatever the page's membership filter shows.
    assert "groupFill(ctx.systems, metricId, () => true)" in brief.group(0)
    simple = _src("SimpleMap.tsx")
    assert 'export const HIGHLIGHT_LAYERS = ["sel", "hl"];' in simple
    assert "!HIGHLIGHT_LAYERS.includes(l.id)" in simple
    # The brief's text is built from the context and the metric alone: nothing about a selection.
    lines = _function_body(_src("groupExport.ts"), "groupBriefLines")
    assert "export function groupBriefLines(ctx: GroupContext, metricId: string)" in lines
