/** What a map is waiting for, as one small state (iteration 22).
 *
 *  Every map on the site (the theatre's MapPanel, and SimpleMap for a country, the Gulf overview and
 *  the world context) used to sit blank for two to three seconds while MapLibre started and parsed
 *  its geometry. The indicator that fills that gap is driven by this reducer, and the reducer is
 *  driven only by things that actually happened: a load promise that resolved or failed, and
 *  MapLibre's own `sourcedata` and `idle` events. There is no timer anywhere in it, so the words on
 *  screen are never a guess about how long loading "usually" takes.
 *
 *  Pure, with no imports, so the tests run it without a map.
 */

/** A file asked for after the map's first paint (the theatre's network lines). */
export interface LateLayer {
  id: string;
  /** In reader words, lower case: "network lines". */
  label: string;
  failed: boolean;
}

export interface MapLoadState {
  /** The geometry source has been parsed and is in the map. */
  geometry: boolean;
  /** MapLibre has gone idle at least once: every source loaded and a frame drawn. */
  drawn: boolean;
  /** The caller's own data file (the figures that colour the map) has not arrived yet. */
  dataPending: boolean;
  late: LateLayer[];
  /** Why the map could not be drawn; null while it can. */
  error: string | null;
}

export type MapLoadEvent =
  | { type: "geometry_loaded" }
  | { type: "idle" }
  | { type: "data_pending"; pending: boolean }
  | { type: "late_requested"; id: string; label: string }
  | { type: "late_arrived"; id: string }
  | { type: "late_failed"; id: string; label: string }
  | { type: "failed"; message: string }
  | { type: "retry" };

export const MAP_LOAD_INITIAL: MapLoadState = { geometry: false, drawn: false, dataPending: false, late: [], error: null };

export function mapLoadReducer(s: MapLoadState, e: MapLoadEvent): MapLoadState {
  switch (e.type) {
    case "geometry_loaded":
      return s.geometry ? s : { ...s, geometry: true };
    case "idle":
      // Idle means every source is in and a frame is on screen: whatever was reported before, the
      // map did draw, so an earlier error no longer describes it.
      return s.geometry && s.drawn && s.error == null ? s : { ...s, geometry: true, drawn: true, error: null };
    case "data_pending":
      return s.dataPending === e.pending ? s : { ...s, dataPending: e.pending };
    case "late_requested":
      return { ...s, late: [...s.late.filter((l) => l.id !== e.id), { id: e.id, label: e.label, failed: false }] };
    case "late_arrived":
      return { ...s, late: s.late.filter((l) => l.id !== e.id) };
    case "late_failed":
      // Also when it was never "requested" here: a reader can switch a layer on after its file failed.
      return { ...s, late: [...s.late.filter((l) => l.id !== e.id), { id: e.id, label: e.label, failed: true }] };
    case "failed":
      // A map that is already drawn stays on screen: MapLibre reports many errors that cost one
      // layer, not the map, and covering a working map with an error would be the worse lie.
      return s.drawn ? s : { ...s, error: e.message };
    case "retry":
      // The caller's data and late files are their own promises; a retry rebuilds only the map.
      return { ...MAP_LOAD_INITIAL, dataPending: s.dataPending, late: s.late.filter((l) => !l.failed) };
  }
}

export type MapLoadPhase = "failed" | "geometry" | "data" | "late" | "late_failed" | "ready";

/** The one thing the map is waiting for now, most basic first. */
export function mapLoadPhase(s: MapLoadState): MapLoadPhase {
  if (s.error != null) return "failed";
  if (!s.geometry) return "geometry";
  if (!s.drawn || s.dataPending) return "data";
  if (s.late.some((l) => !l.failed)) return "late";
  if (s.late.some((l) => l.failed)) return "late_failed";
  return "ready";
}

const upperFirst = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

/** The words in the map box; null when the map is drawn and waiting for nothing. */
export function mapLoadMessage(s: MapLoadState): string | null {
  switch (mapLoadPhase(s)) {
    case "failed": return "The map could not be drawn.";
    case "geometry": return "Loading map geometry…";
    case "data": return "Loading data…";
    case "late": return `Loading ${s.late.filter((l) => !l.failed).map((l) => l.label).join(" and ")}…`;
    case "late_failed": return `${upperFirst(s.late.filter((l) => l.failed).map((l) => l.label).join(" and "))} could not be loaded. The rest of the map is complete.`;
    case "ready": return null;
  }
}

/** Whether the reader is offered "Try again": the map failed, or a late file did. */
export function mapLoadCanRetry(s: MapLoadState): boolean {
  const p = mapLoadPhase(s);
  return p === "failed" || p === "late_failed";
}
