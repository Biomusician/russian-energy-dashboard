/** Shareable deep-link state (§20-22). The full analyst view — choropleth surface, activity
 *  window, timeline position, selected region, layer toggles, filter subsets, and camera — is
 *  encoded into the URL query so a link reproduces exactly what the sender was looking at, and
 *  a bookmark survives a reload. Encoding rules:
 *    - only NON-DEFAULT values are written, so an untouched dashboard keeps a clean URL;
 *    - the timeline is stored as a DATE (survives a dataset rebuild that changes step counts),
 *      resolved back to a step via stepFor() on load;
 *    - filter sets are written only when they are a strict subset of "everything".
 *  Nothing here is operational: it is view state over public, aggregated data. */

import type { ActivityWindow, Metric } from "./App";

export interface CameraState {
  lng: number;
  lat: number;
  zoom: number;
}

/** Everything a link can carry. All optional — absent means "use the app default". */
export interface DeepLink {
  metric?: Metric;
  activityWindow?: ActivityWindow;
  date?: string;
  selected?: string;
  classes?: string[];
  causes?: string[];
  confidences?: string[];
  showLines?: boolean;
  showAssets?: boolean;
  showRivers?: boolean;
  showGasNetwork?: boolean;
  showOilNetwork?: boolean;
  camera?: CameraState;
  compare?: string[];
}

const METRIC_CODE: Record<Metric, string> = {
  esdi: "esdi",
  incidents: "ev",
  esdi_delta_30d: "d30",
  esdi_delta_90d: "d90",
};
const CODE_METRIC: Record<string, Metric> = { ev: "incidents", d30: "esdi_delta_30d", d90: "esdi_delta_90d", esdi: "esdi" };
const ACT_CODE: Record<ActivityWindow, string> = { cumulative: "cum", "30d": "30", "90d": "90" };
const CODE_ACT: Record<string, ActivityWindow> = { "30": "30d", "90": "90d", cum: "cumulative" };

/** Build the query string (without a leading "?") for the given view. `allClasses` etc. are the
 *  full key universes, so a set equal to "all" is omitted rather than spelled out. */
export function encodeDeepLink(
  v: {
    metric: Metric;
    activityWindow: ActivityWindow;
    date: string | null;
    latestDate: string;
    selected: string | null;
    classes: Set<string>;
    causes: Set<string>;
    confidences: Set<string>;
    allClasses: string[];
    allCauses: string[];
    allConfidences: string[];
    showLines: boolean;
    showAssets: boolean;
    showRivers: boolean;
    showGasNetwork: boolean;
    showOilNetwork: boolean;
    camera: CameraState | null;
    compare: string[];
  },
): string {
  const p = new URLSearchParams();
  if (v.metric !== "esdi") p.set("m", METRIC_CODE[v.metric]);
  if (v.activityWindow !== "cumulative") p.set("a", ACT_CODE[v.activityWindow]);
  if (v.date && v.date !== v.latestDate) p.set("d", v.date);
  if (v.selected) p.set("r", v.selected);

  const subset = (set: Set<string>, all: string[]) =>
    set.size < all.length ? all.filter((k) => set.has(k)).join(",") : null;
  const cls = subset(v.classes, v.allClasses);
  const cau = subset(v.causes, v.allCauses);
  const con = subset(v.confidences, v.allConfidences);
  if (cls !== null) p.set("cls", cls);
  if (cau !== null) p.set("cau", cau);
  if (con !== null) p.set("con", con);

  // Layers: assets default ON, the rest default OFF — encode only the departures.
  const ly: string[] = [];
  if (v.showLines) ly.push("lines");
  if (!v.showAssets) ly.push("noassets");
  if (v.showRivers) ly.push("rivers");
  if (v.showGasNetwork) ly.push("gas");
  if (v.showOilNetwork) ly.push("oil");
  if (ly.length) p.set("ly", ly.join(","));

  if (v.camera) {
    p.set("cam", `${v.camera.lng.toFixed(3)},${v.camera.lat.toFixed(3)},${v.camera.zoom.toFixed(2)}`);
  }
  if (v.compare.length) p.set("cmp", v.compare.join(","));
  return p.toString();
}

/** Parse a query string (with or without a leading "?") into a partial DeepLink. Unknown or
 *  malformed values are ignored, never thrown — a bad link degrades to defaults, not a crash. */
export function decodeDeepLink(search: string): DeepLink {
  const p = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const out: DeepLink = {};

  const m = p.get("m");
  if (m && CODE_METRIC[m]) out.metric = CODE_METRIC[m];
  const a = p.get("a");
  if (a && CODE_ACT[a]) out.activityWindow = CODE_ACT[a];
  const d = p.get("d");
  if (d && /^\d{4}-\d{2}-\d{2}$/.test(d)) out.date = d;
  const r = p.get("r");
  if (r) out.selected = r;

  const list = (key: string) => {
    const raw = p.get(key);
    return raw ? raw.split(",").filter(Boolean) : undefined;
  };
  const cls = list("cls"); if (cls) out.classes = cls;
  const cau = list("cau"); if (cau) out.causes = cau;
  const con = list("con"); if (con) out.confidences = con;

  const ly = p.get("ly");
  if (ly != null) {
    const set = new Set(ly.split(","));
    out.showLines = set.has("lines");
    out.showAssets = !set.has("noassets");
    out.showRivers = set.has("rivers");
    out.showGasNetwork = set.has("gas");
    out.showOilNetwork = set.has("oil");
  }

  const cam = p.get("cam");
  if (cam) {
    const [lng, lat, zoom] = cam.split(",").map(Number);
    if ([lng, lat, zoom].every(Number.isFinite)) out.camera = { lng, lat, zoom };
  }
  const cmp = p.get("cmp");
  if (cmp) out.compare = cmp.split(",").filter(Boolean).slice(0, 3);
  return out;
}
