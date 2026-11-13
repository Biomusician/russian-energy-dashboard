"""Iteration 21: route performance and failure containment, the source-level guards.

The behaviour is tested in a real browser (web/e2e/resilience.e2e.ts) and the loaders in vitest
(web/src/global/loading.test.ts). These guards are the ones the mutation campaign can run, since its
sandbox has no browser and no node_modules: each pins a structural fact the browser tests rely on,
so a refactor that quietly drops it fails here first.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "web" / "src"


def _read(rel):
    return (SRC / rel).read_text(encoding="utf-8")


def _function_body(text, signature):
    """The text of one top-level function, from its signature to the next top-level declaration."""
    start = text.index(signature)
    nxt = re.search(r"\n(export |function |const |let |async function )", text[start + len(signature):])
    return text[start:start + len(signature) + (nxt.start() if nxt else len(text))]


def test_every_route_renders_inside_a_view_boundary_keyed_on_the_route():
    root = _read("Root.tsx")
    open_at = root.index("<ViewBoundary key={view.key}")
    close_at = root.index("</ViewBoundary>")
    inside = root[open_at:close_at]
    routes = re.findall(r'route\.view === "(\w+)" &&', root)
    assert len(routes) >= 4, routes
    for view in routes:
        assert f'route.view === "{view}" &&' in inside, f"the {view} route renders outside the boundary"
    assert "<Suspense" in inside, "a chunk that fails to download must land in the boundary"
    # Keyed per route and per id: a failed view never carries over into the next one.
    assert 'key: `country:${route.id}`' in root and 'key: "home"' in root


def test_the_home_panels_each_have_their_own_boundary():
    home = _read("global/GlobalHome.tsx")
    for panel in ("<WorldContext", "<RecentEvidencePanel", "<DataQualityPanel", 'className="sys-cards"'):
        at = home.index(panel)
        opened = home.rfind("<PanelBoundary", 0, at)
        closed = home.rfind("</PanelBoundary>", 0, at)
        assert opened > closed, f"{panel} is not inside a PanelBoundary"


def test_boundaries_catch_and_offer_a_way_out():
    text = _read("components/ViewBoundary.tsx")
    assert text.count("static getDerivedStateFromError") == 2
    assert "navigate(null)" in text and "Return to the overview" in text
    assert "<SystemSwitcher" in text, "the picker must survive a failed view"


def test_every_global_loader_goes_through_the_one_request_cache():
    manifest = _read("global/manifest.ts")
    for sig in ("export function loadManifest(", "export function loadCountry(", "export function loadWorld(",
                "export function loadRecentEvidence(", "export function loadGroupContext(",
                "export function loadDataQuality("):
        body = _function_body(manifest, sig)
        assert "once(" in body or "validated<" in body, f"{sig} bypasses the request cache"
    assert "function validated<" in manifest and "return once(path" in manifest
    # A failure is not kept: the cache forgets a rejected request.
    once = _function_body(manifest, "export function once<")
    assert "loads.delete(key)" in once
    context = _read("global/context.ts")
    assert "if (!contextPromise)" in context


def test_no_component_fetches_on_its_own():
    """Every fetch in the global views goes through manifest.ts or context.ts, which hold one request
    per file. A component calling fetch directly would bypass that and fetch on every mount."""
    checked = 0
    for path in (SRC / "global").glob("*.tsx"):
        checked += 1
        assert "fetch(" not in path.read_text(encoding="utf-8"), path.name
    assert checked > 3


def test_prefetch_never_reports_and_never_fetches_every_system():
    pre = _read("global/prefetch.ts")
    manifest = _read("global/manifest.ts")
    body = _function_body(manifest, "export function prefetchCountry(")
    assert ".catch(() => undefined)" in body, "a failed prefetch must not become an unhandled rejection"
    assert "const quiet = (p: Promise<unknown>) => { p.catch(() => undefined); };" in pre
    # One system per hover; nothing loops over the manifest's systems to load them.
    assert not re.search(r"systems\.(forEach|map)\([^)]*load", pre + manifest)


def test_shape_validation_covers_what_the_views_read_unguarded():
    manifest = _read("global/manifest.ts")
    for name in ("manifestProblems", "groupContextProblems", "recentProblems", "dataQualityProblems", "geometryProblems"):
        assert f"export function {name}(" in manifest
    assert "validated<GroupContext>(path, groupContextProblems)" in manifest
    assert "validated<GeoJSON.FeatureCollection>(\"global/world.geojson\", geometryProblems)" in manifest
    assert "manifestProblems(m)" in _function_body(manifest, "export function loadManifest(")
