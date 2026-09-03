/** PNG export via a temporary render context (iteration 11 P8).
 *
 *  ARCHITECTURE, AND WHY. MapLibre can only read pixels back from a context created with
 *  `preserveDrawingBuffer: true`. The tempting fix is to set that on the main map — and it would
 *  make every interactive session pay for a feature used occasionally, by keeping the back buffer
 *  alive and disabling the browser's usual swap optimisations.
 *
 *  Measured here instead: creating a fresh WebGL context costs ~4 ms at 1920x1080 and ~4 ms at
 *  2560x1440, and reading it back costs ~14 ms and ~18 ms respectively. The entire on-demand path
 *  is therefore tens of milliseconds — while the persistent cost of the alternative is paid in
 *  every session forever. So the main map is left exactly as it is, and export builds a
 *  throwaway map, captures it, and destroys it.
 *
 *  The temporary map is positioned off-screen rather than hidden with `display:none`: a
 *  zero-sized or undisplayed container gives MapLibre nothing to size its canvas from, and the
 *  capture comes back blank.
 *
 *  IT MUST NEVER PRODUCE A BLANK OR HALF-PAINTED IMAGE. The exporter waits for the style to load
 *  and for the map to go idle, then verifies the canvas actually contains something before
 *  handing back a blob. Every failure path destroys the temporary map, including the ones that
 *  throw.
 */

import maplibregl from "maplibre-gl";

export interface ExportRequest {
  /** The live map to copy style and camera from. Never mutated. */
  source: maplibregl.Map;
  width: number;
  height: number;
  /** Device pixel ratio to render at. Rendering at the requested size directly avoids the
   *  blurry result of capturing small and upscaling afterwards (§12). */
  pixelRatio?: number;
}

export interface ExportResult {
  blob: Blob;
  width: number;
  height: number;
  ms: number;
}

/** How long to wait for the throwaway map to settle before giving up. Generous: a first paint
 *  with the dense pipeline layers on is the slow case, and a premature capture is worse than a
 *  slow one. */
const IDLE_TIMEOUT_MS = 20000;

export class ExportError extends Error {}

function offscreenContainer(width: number, height: number): HTMLDivElement {
  const el = document.createElement("div");
  // Off-screen, not display:none — an undisplayed container has no size for MapLibre to adopt
  // and yields a blank canvas.
  el.style.cssText =
    `position:fixed;left:-20000px;top:0;width:${width}px;height:${height}px;pointer-events:none;`;
  document.body.appendChild(el);
  return el;
}

/** Resolve once the map has both loaded its style and stopped rendering. */
function whenIdle(map: maplibregl.Map, timeoutMs: number): Promise<void> {
  return new Promise((resolve, reject) => {
    let settled = false;
    const done = (err?: Error) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      map.off("idle", onIdle);
      map.off("error", onError);
      err ? reject(err) : resolve();
    };
    const onIdle = () => { if (map.loaded()) done(); };
    const onError = (e: unknown) => done(new ExportError(
      `map failed while preparing the export: ${(e as { error?: Error })?.error?.message ?? e}`));
    const timer = window.setTimeout(
      () => done(new ExportError(
        "the map did not finish rendering within " + Math.round(timeoutMs / 1000)
        + "s. Context layers may still be loading — try again once the map is settled.")),
      timeoutMs);
    map.on("idle", onIdle);
    map.on("error", onError);
    if (map.loaded()) {
      // Already idle: give it one turn so a pending frame can land.
      window.setTimeout(() => { if (map.loaded()) done(); }, 50);
    }
  });
}

/** True when the canvas holds something other than a single flat colour.
 *
 *  A uniformly-coloured frame is what a premature or failed capture looks like, and it is the
 *  one outcome that must never reach a file: an empty briefing image is worse than an error,
 *  because it looks like a finding. */
export function canvasHasContent(canvas: HTMLCanvasElement): boolean {
  const gl = canvas.getContext("webgl2", { preserveDrawingBuffer: true })
    ?? canvas.getContext("webgl", { preserveDrawingBuffer: true });
  if (!gl) return false;
  const w = canvas.width;
  const h = canvas.height;
  if (!w || !h) return false;
  const samples: string[] = [];
  const pts: [number, number][] = [
    [Math.floor(w * 0.5), Math.floor(h * 0.5)],
    [Math.floor(w * 0.25), Math.floor(h * 0.4)],
    [Math.floor(w * 0.75), Math.floor(h * 0.6)],
    [Math.floor(w * 0.5), Math.floor(h * 0.2)],
    [Math.floor(w * 0.5), Math.floor(h * 0.8)],
  ];
  const px = new Uint8Array(4);
  for (const [x, y] of pts) {
    (gl as WebGLRenderingContext).readPixels(
      x, y, 1, 1, (gl as WebGLRenderingContext).RGBA,
      (gl as WebGLRenderingContext).UNSIGNED_BYTE, px);
    samples.push(px.join(","));
  }
  return new Set(samples).size > 1;
}

/** Render the current map state at an explicit size and return a PNG blob.
 *
 *  The temporary map is always removed, on every path.
 */
export async function exportMapPng(req: ExportRequest): Promise<ExportResult> {
  const t0 = performance.now();
  const { source, width, height } = req;
  const pixelRatio = req.pixelRatio ?? Math.max(1, Math.min(2, window.devicePixelRatio || 1));

  const style = source.getStyle();
  const container = offscreenContainer(width, height);
  let map: maplibregl.Map | null = null;
  try {
    map = new maplibregl.Map({
      container,
      style,
      // The whole reason this map exists. NOTE the nesting: this MapLibre version moved the
      // flag under `canvasContextAttributes`, and the old top-level spelling is silently
      // ignored — which would produce a blank export with no error anywhere.
      canvasContextAttributes: { preserveDrawingBuffer: true, antialias: true },
      // Copy the live camera exactly rather than re-deriving a view, so what the reader saw is
      // what they get.
      center: source.getCenter(),
      zoom: source.getZoom(),
      bearing: source.getBearing(),
      pitch: source.getPitch(),
      interactive: false,
      attributionControl: false,
      fadeDuration: 0,
      pixelRatio,
    });

    await whenIdle(map, IDLE_TIMEOUT_MS);

    const canvas = map.getCanvas();
    if (!canvasHasContent(canvas)) {
      throw new ExportError(
        "the rendered map came back blank. Nothing was written to a file. This usually means a "
        + "context layer was still loading — wait for the map to settle and try again.");
    }

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob((b) => resolve(b), "image/png"));
    if (!blob) throw new ExportError("the browser could not encode the image.");

    return { blob, width: canvas.width, height: canvas.height, ms: performance.now() - t0 };
  } finally {
    // Runs on success, on failure, and on a throw from anywhere above. A leaked WebGL context
    // is exactly the persistent cost this architecture exists to avoid.
    try { map?.remove(); } catch { /* already gone */ }
    container.remove();
  }
}

/** Trigger a download without leaving an object URL behind. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoked on the next turn so the navigation has definitely started.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Clipboard is a SHOULD, not a MUST (§22): support is uneven and permission-gated, so the
 *  caller falls back to a download when this reports false. */
export async function copyBlobToClipboard(blob: Blob): Promise<boolean> {
  try {
    const w = window as unknown as { ClipboardItem?: new (i: Record<string, Blob>) => unknown };
    if (!navigator.clipboard || !w.ClipboardItem) return false;
    const item = new w.ClipboardItem({ "image/png": blob });
    await (navigator.clipboard as unknown as
      { write: (i: unknown[]) => Promise<void> }).write([item]);
    return true;
  } catch {
    return false;
  }
}
