/** The map-first home (iteration 23), worked out without React so it can be tested as it ships.
 *
 *  ONE CLICK, ONE MEANING. A "unit" is what one click on the world map means: a monitored system
 *  (its id, so the theatre's Russian regions, Belarus, Crimea and Sevastopol are one unit, and Hong
 *  Kong and Macao are China's) or else a country (its a3 code). The map's default colours say only
 *  that: a monitored system, Crimea's occupied status, everything else. Impact-record presence is
 *  told on hover and on selection, never painted: a lit country reads as "disruption happened
 *  here" and an unlit one as "nothing happened", the inference the impact layer forbids.
 *
 *  THREE SERVED TRUTHS. world.geojson (a3, name, system_id, status, note) and the manifest
 *  (systems, groups, impact_presence). No second registry and no country constant here.
 *
 *  NO NEW ADDRESS. A selection on the home lives in the home's own history entry
 *  (`history.state`), written just before the reader leaves, so Back lands on it with focus
 *  restored and every address stays one the site already had.
 */

import type { Manifest, ManifestSystem } from "./manifest";
import { LOCATION_EVENT, hrefFor, impactsHref, navigateTo, routeFor } from "./router";
import { fmtDate, fmtNum } from "../data";

export type Bbox = [number, number, number, number];
type Props = Record<string, unknown>;

/** What one click on a feature means: its system, or else its country. */
export function unitOf(p: Props): string {
  return p.system_id ? String(p.system_id) : String(p.a3);
}

/** The same rule as a map expression, so the map outlines exactly the unit a click opens. */
export const UNIT_EXPR = ["coalesce", ["get", "system_id"], ["get", "a3"]];

export interface WorldIndex {
  /** a3 unit -> the country's name. Systems are named by the manifest. */
  name: Map<string, string>;
  /** unit -> the box around every feature that belongs to it. */
  bounds: Map<string, Bbox>;
  /** A country drawn partly inside a system and partly outside (Russia): its code -> that system. */
  partOf: Map<string, string>;
  /** A country with occupied features (Ukraine): their names, their note and the system they are in. */
  occupied: Map<string, { names: string[]; note: string; system: string }>;
  /** Every country on the map, A to Z, with the unit a click on it means. */
  countries: { a3: string; name: string; unit: string }[];
}

function extend(box: Bbox | undefined, coords: unknown): Bbox | undefined {
  if (!Array.isArray(coords)) return box;
  if (typeof coords[0] === "number" && typeof coords[1] === "number") {
    const [x, y] = coords as number[];
    return box ? [Math.min(box[0], x), Math.min(box[1], y), Math.max(box[2], x), Math.max(box[3], y)] : [x, y, x, y];
  }
  let out = box;
  for (const c of coords) out = extend(out, c);
  return out;
}

export function indexWorld(world: GeoJSON.FeatureCollection): WorldIndex {
  const idx: WorldIndex = { name: new Map(), bounds: new Map(), partOf: new Map(), occupied: new Map(), countries: [] };
  const systemsOf = new Map<string, Set<string | null>>();
  for (const f of world.features) {
    const p = (f.properties ?? {}) as Props;
    if (typeof p.a3 !== "string") continue;
    const unit = unitOf(p);
    const g = f.geometry as { coordinates?: unknown } | null;
    const box = extend(idx.bounds.get(unit), g?.coordinates);
    if (box) idx.bounds.set(unit, box);
    if (p.status === "occupied") {
      // Crimea and Sevastopol carry Ukraine's code. They are not a country of their own and they
      // never decide what Ukraine is; they are described in Ukraine's card instead.
      const o = idx.occupied.get(p.a3) ?? { names: [], note: String(p.note ?? ""), system: String(p.system_id ?? "") };
      o.names.push(String(p.name));
      idx.occupied.set(p.a3, o);
      continue;
    }
    if (!idx.name.has(p.a3)) idx.name.set(p.a3, String(p.name ?? p.a3));
    const set = systemsOf.get(p.a3) ?? new Set<string | null>();
    set.add(p.system_id ? String(p.system_id) : null);
    systemsOf.set(p.a3, set);
  }
  for (const [a3, set] of systemsOf) {
    const systems = [...set].filter((s): s is string => s !== null);
    let unit = a3;
    if (systems.length === 1 && !set.has(null)) unit = systems[0];
    else if (systems.length === 1) idx.partOf.set(a3, systems[0]);
    idx.countries.push({ a3, name: idx.name.get(a3) ?? a3, unit });
  }
  // A to Z by name: a list to find a country in, never an order by any figure.
  idx.countries.sort((a, b) => a.name.localeCompare(b.name, "en"));
  return idx;
}

export function systemOf(m: Manifest, id: string): ManifestSystem | undefined {
  return m.systems.find((s) => s.id === id);
}

export function unitName(unit: string, idx: WorldIndex | null, m: Manifest): string {
  return systemOf(m, unit)?.name ?? idx?.name.get(unit) ?? unit;
}

export type UnitState =
  | "theatre" | "country_system" | "outside_area" | "impact_only" | "attempt_only" | "no_record" | "unchecked";

/** Which of the click states a unit is in. `unchecked`: the manifest carries no presence list
 *  (an older build, or a malformed one), so the page says it could not check, never "no record". */
export function stateOf(unit: string, idx: WorldIndex | null, m: Manifest): UnitState {
  const sys = systemOf(m, unit);
  if (sys) return sys.kind === "theatre" ? "theatre" : "country_system";
  if (idx?.partOf.has(unit)) return "outside_area";
  const pres = m.impact_presence;
  if (!pres) return "unchecked";
  if (pres.countries.includes(unit)) return "impact_only";
  if (pres.attempt_only.includes(unit)) return "attempt_only";
  return "no_record";
}

/** What choosing a unit does. With a mouse, a keyboard or the search, a monitored system opens: the
 *  hover label or the option already said so. A place without a system has no page, so it is
 *  selected and its card is the destination. A finger gets the card first for everything. */
export function pickAction(unit: string, m: Manifest, touch: boolean): "open" | "select" {
  return systemOf(m, unit) && !touch ? "open" : "select";
}

/** One status line per state: the hover label, the card, the search option and the announcement
 *  all say the same words. No count and no maturity: those belong on each system's own page. */
export const STATUS: Record<UnitState, string> = {
  theatre: "The indexed system: the only one with an index",
  country_system: "Monitored country system · no index",
  outside_area: "Outside the monitored area",
  impact_only: "Impact records available · Not a monitored country system",
  attempt_only: "No dedicated monitored system · No published impact record",
  no_record: "No dedicated monitored system · No published impact record",
  unchecked: "No dedicated monitored system",
};

/** A country part of which lies inside a system, chosen as a whole (from the A to Z list, the search
 *  or a restored selection), iteration 23 (MU-05). A click on the map lands on one part and keeps
 *  that part's own status; the list and the search mean the whole country, and say the same words. */
export function partlyStatus(within: ManifestSystem): string {
  return `Partly monitored, in the ${within.name} ${within.kind === "theatre" ? "theatre" : "system"}`;
}

/** The status a card and its announcement give a unit. `onMap`: chosen by a click on the map. */
export function statusFor(unit: string, idx: WorldIndex | null, m: Manifest, onMap = false): string {
  const state = stateOf(unit, idx, m);
  const within = state === "outside_area" && !onMap ? systemOf(m, idx?.partOf.get(unit) ?? "") : undefined;
  return within ? partlyStatus(within) : STATUS[state];
}

/** Crimea and Sevastopol: Ukrainian, occupied, and monitored inside the theatre. Never Russian. */
export const OCCUPIED_PHRASE = "Ukrainian territory under Russian occupation";

/** "United States" and "United States of America" are one name; "Belarus" is not the theatre's. */
export function sameName(a: string, b: string): boolean {
  const [x, y] = [a.toLowerCase(), b.toLowerCase()];
  return x.startsWith(y) || y.startsWith(x);
}

function kindWord(s: ManifestSystem): string {
  return s.kind === "theatre" ? "theatre" : "system";
}

/** What the pointer is over, and what a click on it does. */
export function hoverLabel(p: Props, idx: WorldIndex | null, m: Manifest): string {
  const unit = unitOf(p);
  const state = stateOf(unit, idx, m);
  const name = unitName(unit, idx, m);
  const own = String(p.name ?? unit);
  const sys = systemOf(m, unit);
  if (sys && p.status === "occupied") {
    return `${own}: ${OCCUPIED_PHRASE} · Monitored as a separate unit in the ${sys.name} ${kindWord(sys)} · Click to open the ${kindWord(sys)}`;
  }
  if (sys) {
    const where = sameName(sys.name, own) ? sys.name : `${own}: in the ${sys.name} ${kindWord(sys)}`;
    return state === "theatre"
      ? `${where === sys.name ? `${sys.name} theatre` : where} · The one indexed system · Click to open`
      : `${where} · ${STATUS.country_system} · Click to open`;
  }
  if (state === "outside_area") return `${own}: outside the monitored area · Click for details`;
  return `${name} · ${STATUS[state]} · Click for details`;
}

export interface CardAction { label: string; href: string; ret: string; primary?: boolean }

export interface CardModel {
  key: string;
  heading: string;
  status: string;
  lines: string[];
  /** The one or two things to do next, as buttons. */
  actions: CardAction[];
  /** A regional group's member pages, as a list of links. */
  links: CardAction[];
  /** The country whose national energy figures the card may show, or null. */
  contextA3: string | null;
}

/** "5.9 Monitored-Area ESDI · 20 Nov 2026": the one figure on the home, with its date. */
export function headlineText(s: ManifestSystem): string | null {
  return s.headline ? `${fmtNum(s.headline.value, 1)} ${s.headline.label} · ${fmtDate(s.headline.as_of)}` : null;
}

export function impactRecordsHref(a3: string): string {
  return impactsHref(`f.country=${encodeURIComponent(a3)}`);
}

export const THEATRE_MEANING = "Exposure, not loss and not a percentage; the only system with an index.";
const CRIMEA_IN_THEATRE = `Includes Crimea and Sevastopol, ${OCCUPIED_PHRASE}, as a separate unit. `
  + "Including it in the index is an analytic choice, not a statement about sovereignty.";

/** The regional overview a system belongs to (a group with its own page), or undefined. */
export function regionalGroupOf(m: Manifest, id: string) {
  return Object.entries(m.groups ?? {}).find(([, g]) => g.slug && g.context && g.members.includes(id));
}

function occupiedLines(unit: string, idx: WorldIndex | null, m: Manifest): { lines: string[]; actions: CardAction[] } {
  const o = idx?.occupied.get(unit);
  const sys = o ? systemOf(m, o.system) : undefined;
  if (!o || !sys) return { lines: [], actions: [] };
  return {
    lines: [`${o.names.join(" and ")}: ${o.note}`],
    actions: [{ label: `Open the ${sys.name} ${kindWord(sys)}`, href: hrefFor(sys.id), ret: `card:${sys.id}` }],
  };
}

/** The group id in a selection key ("group:gulf_littoral" -> "gulf_littoral"). */
export function groupIdOf(key: string): string {
  return key.replace(/^group:/, "");
}

/** The feature a tap landed on, when it is not the whole unit (Hong Kong in China, Crimea in the
 *  theatre). */
export interface Feature { name: string; occupied?: boolean }

/** The card for a selection: a group (`group:<id>`), a choice between places too close to tell
 *  apart (`near:<unit>,<unit>`) or a unit. Null for a key nothing on the map or in the manifest
 *  answers to. `onMap`: the unit was chosen by a click on the map, which lands on one part of it. */
export function cardFor(key: string, idx: WorldIndex | null, m: Manifest, feature?: Feature, onMap = false): CardModel | null {
  if (key.startsWith(NEAR)) {
    // Alphabetical, never by any figure: a list of places is not a ranking.
    const links = unitsOf(key, m).flatMap((u) => {
      const s = systemOf(m, u);
      return s ? [{ label: s.name, href: hrefFor(s.id), ret: `card:${s.id}` }] : [];
    }).sort((a, b) => a.label.localeCompare(b.label, "en"));
    if (!links[0]) return null;
    return { key, heading: "Several places here", status: "Too close together to tell apart at this zoom: choose one",
             lines: ["Or zoom in, or use the list or the search."], actions: [], links, contextA3: null };
  }
  if (key.startsWith("group:")) {
    const id = groupIdOf(key);
    const g = m.groups?.[id];
    if (!g || !g.slug) return null;
    return {
      key, heading: g.label, status: "Regional overview · no index", lines: [g.note],
      actions: [{ label: `Open the ${g.label} overview`, href: `?group=${encodeURIComponent(g.slug)}`, ret: "card:open", primary: true }],
      links: g.members.flatMap((sid) => {
        const s = systemOf(m, sid);
        return s ? [{ label: s.name, href: hrefFor(s.id), ret: `card:${s.id}` }] : [];
      }),
      contextA3: null,
    };
  }
  const state = stateOf(key, idx, m);
  const sys = systemOf(m, key);
  const name = unitName(key, idx, m);
  const base = { key, heading: name, status: STATUS[state], links: [] as CardAction[] };
  if (sys && state === "theatre") {
    const head = headlineText(sys);
    return {
      ...base,
      lines: [...(feature?.occupied ? [`${feature.name}: ${OCCUPIED_PHRASE}, monitored as a separate unit in this theatre.`] : []),
              ...(head ? [head] : []), ...(sys.headline ? [sys.headline.meaning] : []), THEATRE_MEANING, CRIMEA_IN_THEATRE],
      actions: [{ label: `Open ${sys.name}`, href: hrefFor(sys.id), ret: "card:open", primary: true }],
      contextA3: null,
    };
  }
  if (sys) {
    const group = regionalGroupOf(m, sys.id);
    const lines: string[] = [];
    if (feature && !sameName(sys.name, feature.name)) lines.push(`${feature.name} is in the ${sys.name} system.`);
    if (sys.record_reviewed) lines.push(`Record reviewed ${fmtDate(sys.record_reviewed)}.`);
    if (sys.record_reviewed === null) {
      lines.push("No qualifying records yet. Its impact records tab is a separate layer with its own, broader inclusion rule, so it may hold reviewed records.");
    }
    lines.push(`Site built ${fmtDate(sys.as_of)}.`);
    const actions: CardAction[] = [{ label: `Open ${sys.name}`, href: hrefFor(sys.id), ret: "card:open", primary: true }];
    if (sys.record_reviewed === null) actions.push({ label: "Open its impact records tab", href: `?sys=${encodeURIComponent(sys.id)}&tab=impacts`, ret: "card:impacts" });
    if (group?.[1].slug) actions.push({ label: `${group[1].label} overview`, href: `?group=${encodeURIComponent(group[1].slug)}`, ret: "card:group" });
    return { ...base, lines, actions, contextA3: null };
  }
  const occ = occupiedLines(key, idx, m);
  const notSearched = `This site has not searched ${name} systematically, so nothing here says whether disruptions happened.`;
  if (state === "outside_area") {
    const within = systemOf(m, idx?.partOf.get(key) ?? "");
    const present = m.impact_presence?.countries.includes(key);
    const where = onMap || !within
      ? `This part of ${name} lies outside the area monitored${within ? ` in the ${within.name} ${kindWord(within)}` : ""}.`
      : `Part of ${name} is monitored in the ${within.name} ${kindWord(within)}; the rest lies outside the monitored area.`;
    return {
      ...base,
      status: statusFor(key, idx, m, onMap),
      lines: [`${where} National energy figures cover the whole country.`,
              ...(present ? [`The Impact Atlas also holds reviewed records for ${name}, under its own, broader inclusion rule.`] : [])],
      actions: [...(within ? [{ label: `Open the ${within.name} ${kindWord(within)}`, href: hrefFor(within.id), ret: "card:open", primary: true }] : []),
                ...(present ? [{ label: "Open impact records", href: impactRecordsHref(key), ret: "card:impacts" }] : [])],
      contextA3: key,
    };
  }
  if (state === "impact_only") {
    return {
      ...base,
      lines: [`The Impact Atlas holds reviewed reports for ${name} under its own, broader inclusion rule. It has no score and is not a complete record of what happened.`, ...occ.lines],
      actions: [{ label: "Open impact records", href: impactRecordsHref(key), ret: "card:impacts", primary: true }, ...occ.actions],
      contextA3: key,
    };
  }
  if (state === "attempt_only") {
    return {
      ...base,
      lines: [notSearched, "The Impact Atlas lists documented attempts separately; an attempt is not a disruption.", ...occ.lines],
      // Unfiltered: the atlas ignores a country filter that matches no disruption.
      actions: [{ label: "Open the Impact Atlas", href: impactsHref(), ret: "card:impacts" }, ...occ.actions],
      contextA3: key,
    };
  }
  if (state === "unchecked") {
    return {
      ...base,
      lines: [`Whether the Impact Atlas holds records for ${name} could not be checked.`, notSearched, ...occ.lines],
      actions: [{ label: "Open the Impact Atlas", href: impactsHref(), ret: "card:impacts" }, ...occ.actions],
      contextA3: key,
    };
  }
  // No system and no record: no button and no dashboard. Nothing here can say "no disruption".
  return { ...base, lines: [notSearched, ...occ.lines], actions: occ.actions, contextA3: key };
}

// ---- the panel ---------------------------------------------------------------------------------

export type PanelSection = "indexed" | "beyond" | "regional" | "countries" | "tools";

export interface PanelRow {
  key: string;
  section: PanelSection;
  label: string;
  href: string;
  systemId?: string;
  groupId?: string;
  /** A quiet membership tag ("Gulf littoral"). Never a maturity, a count or a status. */
  tag?: string;
}

/** The panel's rows in the order the page shows them: the theatre, the Impact Atlas, each
 *  regional overview, the country systems in the manifest's own (alphabetical) order, Compare.
 *  Filtered from the manifest, never sorted here: an order by any figure is a ranking. */
export function panelRows(m: Manifest): PanelRow[] {
  const rows: PanelRow[] = [];
  for (const s of m.systems.filter((x) => x.kind === "theatre")) {
    rows.push({ key: `row:${s.id}`, section: "indexed", label: s.name, href: hrefFor(s.id), systemId: s.id });
  }
  rows.push({ key: "row:atlas", section: "beyond", label: "Impact Atlas", href: impactsHref() });
  for (const [id, g] of Object.entries(m.groups ?? {})) {
    if (g.slug && g.context) rows.push({ key: `row:group:${id}`, section: "regional", label: g.label, href: `?group=${encodeURIComponent(g.slug)}`, groupId: id });
  }
  for (const s of m.systems.filter((x) => x.kind === "country")) {
    rows.push({ key: `row:${s.id}`, section: "countries", label: s.name, href: hrefFor(s.id), systemId: s.id, tag: regionalGroupOf(m, s.id)?.[1].label });
  }
  rows.push({ key: "row:compare", section: "tools", label: "Compare systems", href: "?compare=" });
  return rows;
}

/** The units a selection or a pointer covers: a group's members, a choice's places, or the one unit. */
export function unitsOf(key: string | null, m: Manifest | null): string[] {
  if (!key) return [];
  if (key.startsWith("group:")) return m?.groups?.[groupIdOf(key)]?.members ?? [];
  if (key.startsWith(NEAR)) return key.slice(NEAR.length).split(",").filter(Boolean);
  return [key];
}

const NEAR = "near:";

/** The selection key for a click that landed on several monitored places at once. */
export function nearKey(units: string[]): string {
  return `${NEAR}${[...new Set(units)].sort().join(",")}`;
}

/** What a click on several features means (iteration 23, MU-01): the monitored systems among them.
 *  One system: that system, as an ordinary click. Several: a choice. None: an ordinary click on the
 *  first feature. Whatever else lay under the pointer is reachable by zooming in, the list and the
 *  search. */
export function pickMany(props: Props[], m: Manifest): { kind: "one"; props: Props } | { kind: "near"; key: string } | null {
  const systems = [...new Set(props.map(unitOf))].filter((u) => systemOf(m, u));
  if (systems.length > 1) return { kind: "near", key: nearKey(systems) };
  const one = systems.length === 1 ? props.find((p) => unitOf(p) === systems[0]) : props[0];
  return one ? { kind: "one", props: one } : null;
}

/** A unit whose box spans less than this many degrees is a few pixels wide at world zoom. */
export const SMALL_DEGREES = 4;

/** Points for the monitored systems too small to click at world zoom (iteration 23, MU-01): the
 *  smallest Gulf member had no clickable pixel. A fixed-size dot in the monitored colour, at the centre of the system's
 *  served bounds, with its properties, so a click on it means the system. Every small system gets
 *  one, whatever it holds: a dot sized or coloured by anything would be a severity display. */
export function smallSystemMarkers(m: Manifest): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: m.systems.flatMap((s) => {
      const b = s.bounds;
      if (!b || Math.max(b[2] - b[0], b[3] - b[1]) >= SMALL_DEGREES) return [];
      return [{ type: "Feature" as const, properties: { system_id: s.id, name: s.name, status: "normal" },
                geometry: { type: "Point" as const, coordinates: [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2] } }];
    }),
  };
}

/** The box around a group's members, from their manifest bounds. */
export function groupBounds(m: Manifest, id: string): Bbox | null {
  let out: Bbox | null = null;
  for (const sid of m.groups?.[id]?.members ?? []) {
    const b = systemOf(m, sid)?.bounds;
    if (!b) continue;
    out = out ? [Math.min(out[0], b[0]), Math.min(out[1], b[1]), Math.max(out[2], b[2]), Math.max(out[3], b[3])] : [...b];
  }
  return out;
}

// ---- the map's colours ---------------------------------------------------------------------------

/** "Where to explore": one neutral colour for every monitored system, the theatre included (a
 *  different colour would read as "more"), Crimea's occupied hatch, and the base for the rest. No
 *  red, no ramp, no count and no score. */
export const MAP_COLOURS = { monitored: "#5f7c9a", occupied: "#5b4a1e", hatch: "#cdb06a", base: "#141c25" } as const;

export const NAV_FILL = [
  "case",
  ["==", ["get", "status"], "occupied"], MAP_COLOURS.occupied,
  ["!=", ["get", "system_id"], null], MAP_COLOURS.monitored,
  MAP_COLOURS.base,
];

/** The credits under the home map, in each mode. */
export const EXPLORE_ATTRIBUTION = "Boundaries: Natural Earth, line of actual control; Crimea drawn as Ukrainian territory under Russian occupation. Ctrl (⌘) + scroll zooms.";
export const ENERGY_ATTRIBUTION = `Energy data: U.S. EIA International Energy Statistics. ${EXPLORE_ATTRIBUTION}`;

/** The features drawn with the occupied hatch: status, from the geometry. */
export const NAV_HATCH = ["==", ["get", "status"], "occupied"];

function channel(v: number): number {
  const c = v / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

function rgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as [number, number, number];
}

/** A fill as drawn: `alpha` of `fg` over `bg`. */
export function blend(fg: string, bg: string, alpha: number): string {
  const [a, b] = [rgb(fg), rgb(bg)];
  return `#${a.map((x, i) => Math.round(x * alpha + b[i] * (1 - alpha)).toString(16).padStart(2, "0")).join("")}`;
}

/** WCAG contrast ratio between two colours. */
export function contrast(x: string, y: string): number {
  const lum = (hex: string) => { const [r, g, b] = rgb(hex).map(channel); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const [l1, l2] = [lum(x), lum(y)].sort((a, b) => b - a);
  return (l1 + 0.05) / (l2 + 0.05);
}

// ---- the selection in the home's own history entry ----------------------------------------------

interface HomeHistory { homeFocus?: string | null; homeReturn?: string | null }

export function readHomeState(): { focus: string | null; ret: string | null } {
  const s = (window.history.state ?? {}) as HomeHistory;
  return { focus: typeof s.homeFocus === "string" ? s.homeFocus : null, ret: typeof s.homeReturn === "string" ? s.homeReturn : null };
}

/** Remember the selection, and the control to give focus back to, in this entry. The address is
 *  not touched. */
export function writeHomeState(focus: string | null, ret: string | null) {
  const s = window.history.state;
  window.history.replaceState({ ...(s && typeof s === "object" ? s : {}), homeFocus: focus, homeReturn: ret }, "");
}

/** Leave the home for `href` (an existing address), first noting what to restore on Back. */
export function openFromHome(href: string, focus: string | null, ret: string | null) {
  writeHomeState(focus, ret);
  navigateTo(href);
}

export const HOME_SELECT_EVENT = "edm:homeselect";

/** Select a unit on the home map from anywhere: on the home it is selected in place; elsewhere the
 *  home opens (a new history entry, at the bare address) with it selected. */
export function selectOnHome(key: string) {
  if (routeFor(window.location.search).view === "home") {
    window.dispatchEvent(new CustomEvent(HOME_SELECT_EVENT, { detail: key }));
    return;
  }
  window.history.pushState({ homeFocus: key, homeReturn: null }, "", window.location.pathname);
  window.dispatchEvent(new Event(LOCATION_EVENT));
}
