/** Deterministic layout measurement (§18).
 *
 *  This exists because the responsive regression it guards against is invisible to unit tests
 *  and to CSS review: the dashboard rendered "correctly" at 1280x720 in the sense that nothing
 *  overlapped or errored — it just gave the map ~300px of height and handed the rest to chrome.
 *  A map-first product with a 30% map is broken, and nothing in the build caught it.
 *
 *  Everything here reads real bounding rectangles from a live document. It is deliberately not
 *  a React hook and holds no state, so a test, a console session and a CI script all measure the
 *  same way.
 */

export interface LayoutMetrics {
  viewportWidth: number;
  viewportHeight: number;
  devicePixelRatio: number;
  mapWidth: number;
  mapHeight: number;
  /** Map area as a fraction of viewport area, 0-1. The headline number for this hotfix. */
  mapAreaRatio: number;
  /** Fraction of the viewport taken by chrome that is ALWAYS on screen in this mode. */
  persistentUiRatio: number;
  /** documentElement.scrollWidth - innerWidth. Must be <= tolerance: the page never scrolls sideways. */
  horizontalOverflow: number;
  ribbonHeight: number;
  timelineHeight: number;
  /** 0 when the panel is a closed drawer or absent — i.e. width actually stolen from the map. */
  filtersVisibleWidth: number;
  dossierVisibleWidth: number;
  /** Map area obscured by overlays that sit on top of it (legend, scope note, tray, controls). */
  overlayObstructionRatio: number;
  /** MapLibre's own canvas, to catch a stale map that never resized to its container. */
  canvasWidth: number;
  canvasHeight: number;
  canvasMatchesContainer: boolean;
  mode: string | null;
}

const SEL = {
  ribbon: ".ribbon",
  filters: ".filters",
  map: ".mapwrap",
  dossier: ".dossier",
  timeline: ".timeline",
  canvas: ".maplibregl-canvas",
} as const;

function rect(sel: string): DOMRect | null {
  const el = document.querySelector(sel);
  return el ? el.getBoundingClientRect() : null;
}

/** Width a docked panel actually steals from the map. A drawer sitting off-canvas, a
 *  display:none panel, or an overlay drawer all steal nothing, and must measure zero. */
function dockedWidth(sel: string): number {
  const el = document.querySelector(sel) as HTMLElement | null;
  if (!el) return 0;
  const cs = getComputedStyle(el);
  if (cs.display === "none" || cs.visibility === "hidden" || Number(cs.opacity) === 0) return 0;
  // An overlay drawer floats above the map rather than displacing it.
  if (cs.position === "absolute" || cs.position === "fixed") return 0;
  const r = el.getBoundingClientRect();
  if (r.width === 0 || r.height === 0) return 0;
  // Translated off-canvas.
  if (r.right <= 0 || r.left >= window.innerWidth) return 0;
  return r.width;
}

/** Fraction of the map rectangle covered by overlay elements drawn on top of it. Rectangles are
 *  unioned on a coarse grid rather than analytically: overlays overlap each other, and summing
 *  their areas would double-count and overstate the obstruction. */
export function overlayObstruction(mapRect: DOMRect, selectors: string[]): number {
  if (mapRect.width <= 0 || mapRect.height <= 0) return 0;
  const boxes: DOMRect[] = [];
  for (const sel of selectors) {
    for (const el of Array.from(document.querySelectorAll(sel))) {
      const cs = getComputedStyle(el as HTMLElement);
      if (cs.display === "none" || cs.visibility === "hidden" || Number(cs.opacity) === 0) continue;
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) boxes.push(r);
    }
  }
  if (!boxes.length) return 0;
  const STEPS = 48;
  const dx = mapRect.width / STEPS;
  const dy = mapRect.height / STEPS;
  let covered = 0;
  for (let i = 0; i < STEPS; i++) {
    const px = mapRect.left + (i + 0.5) * dx;
    for (let j = 0; j < STEPS; j++) {
      const py = mapRect.top + (j + 0.5) * dy;
      if (boxes.some((b) => px >= b.left && px <= b.right && py >= b.top && py <= b.bottom)) {
        covered++;
      }
    }
  }
  return covered / (STEPS * STEPS);
}

export function measureLayout(): LayoutMetrics {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const area = Math.max(1, vw * vh);

  const map = rect(SEL.map);
  const ribbon = rect(SEL.ribbon);
  const timeline = rect(SEL.timeline);
  const canvas = rect(SEL.canvas);

  const mapWidth = map?.width ?? 0;
  const mapHeight = map?.height ?? 0;
  const ribbonHeight = ribbon?.height ?? 0;
  const timelineHeight = timeline?.height ?? 0;
  const filtersVisibleWidth = dockedWidth(SEL.filters);
  const dossierVisibleWidth = dockedWidth(SEL.dossier);

  // Persistent chrome = the full-width bars plus the docked rails beside the map. Drawers are
  // excluded on purpose: they are dismissible, and the point of this hotfix is that dismissible
  // chrome is not the same cost as permanent chrome.
  const persistentUi =
    ribbonHeight * vw +
    timelineHeight * vw +
    (filtersVisibleWidth + dossierVisibleWidth) * Math.max(0, mapHeight);

  return {
    viewportWidth: vw,
    viewportHeight: vh,
    devicePixelRatio: window.devicePixelRatio,
    mapWidth: Math.round(mapWidth),
    mapHeight: Math.round(mapHeight),
    mapAreaRatio: +((mapWidth * mapHeight) / area).toFixed(4),
    persistentUiRatio: +(persistentUi / area).toFixed(4),
    horizontalOverflow: document.documentElement.scrollWidth - vw,
    ribbonHeight: Math.round(ribbonHeight),
    timelineHeight: Math.round(timelineHeight),
    filtersVisibleWidth: Math.round(filtersVisibleWidth),
    dossierVisibleWidth: Math.round(dossierVisibleWidth),
    overlayObstructionRatio: map
      ? +overlayObstruction(map, [
          ".map-scope-note", ".map-legend", ".camera-controls",
          ".comparison-tray", ".maplibregl-ctrl-top-left", ".maplibregl-ctrl-bottom-right",
        ]).toFixed(4)
      : 0,
    canvasWidth: Math.round(canvas?.width ?? 0),
    canvasHeight: Math.round(canvas?.height ?? 0),
    // A canvas that has drifted from its container is the classic symptom of a map that was
    // initialised at one size and never told the container changed.
    canvasMatchesContainer:
      !!canvas && !!map &&
      Math.abs(canvas.width - map.width) <= 2 &&
      Math.abs(canvas.height - map.height) <= 2,
    mode: document.documentElement.getAttribute("data-layout") ?? null,
  };
}

/** Minimum share of the viewport the map must occupy by default, chosen per viewport class.
 *  Smaller screens demand a HIGHER share because chrome is close to fixed in absolute terms:
 *  a 92px ribbon is 6% of a 1440px-tall viewport and 13% of a 720px one. */
export function mapAreaTarget(vw: number, vh: number): number {
  if (vw <= 1100 || vh <= 700) return 0.55;
  if (vw <= 1400 || vh <= 800) return 0.58;
  if (vw <= 1700) return 0.55;
  return 0.50;
}

export function checkLayout(m: LayoutMetrics): { ok: boolean; failures: string[] } {
  const failures: string[] = [];
  const target = mapAreaTarget(m.viewportWidth, m.viewportHeight);
  if (m.mapAreaRatio < target) {
    failures.push(
      `map is ${(m.mapAreaRatio * 100).toFixed(1)}% of the viewport, target >= ${(target * 100).toFixed(0)}%`);
  }
  if (m.horizontalOverflow > 2) {
    failures.push(`page scrolls horizontally by ${m.horizontalOverflow}px`);
  }
  if (m.mapHeight < 360) {
    failures.push(`map is only ${m.mapHeight}px tall`);
  }
  if (!m.canvasMatchesContainer) {
    failures.push(
      `MapLibre canvas ${m.canvasWidth}x${m.canvasHeight} does not fill container ${m.mapWidth}x${m.mapHeight}`);
  }
  if (m.overlayObstructionRatio > 0.35) {
    failures.push(`overlays cover ${(m.overlayObstructionRatio * 100).toFixed(0)}% of the map`);
  }
  return { ok: failures.length === 0, failures };
}
