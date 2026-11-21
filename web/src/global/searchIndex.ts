/** What the global search can find, and how results are ordered.
 *
 *  SOURCES, AND WHAT THEY COST. Systems, their aliases and the regional overviews come from the
 *  manifest, which every view has already loaded. Glossary concepts are in the bundle. Region
 *  names are added only where they are cheap: the theatre's region list (one small file, fetched
 *  the first time the search box is focused) and the regions of any country whose page this tab
 *  has already loaded. The home page never fetches a country's files to build the index. Every
 *  country on the world map (iteration 23) comes from the world geometry: on the home page it is
 *  already loaded; elsewhere it is fetched the first time the box is focused.
 *
 *  WHAT AN OPTION SAYS. What choosing it does: a monitored system opens; a country without one is
 *  selected on the home map, as a click there would, and says whether the Impact Atlas holds
 *  records for it. Never a maturity, a count or a score.
 *
 *  ORDER. How well the words match, then kind, then name. Never a figure: a search result list
 *  is not a ranking of systems.
 */

import type { Manifest } from "./manifest";
import { STATUS, stateOf, systemOf, type WorldIndex } from "./homeSelection";
import { GLOSSARY } from "./glossary";
import { matchScore, normalizeForSearch } from "./searchNormalize";
import { loadRegionRows } from "../data";

export type SearchKind = "system" | "group" | "country" | "view" | "region" | "concept";

export type SearchAction =
  | { type: "system"; id: string }
  | { type: "group"; slug: string }
  | { type: "href"; href: string }
  | { type: "concept"; id: string }
  /** Select a place on the home map (a unit: a system id or a country code). */
  | { type: "select"; key: string };

export interface SearchEntry {
  key: string;
  kind: SearchKind;
  label: string;
  sub: string;
  /** Every name the entry goes by, as written. Displayed unchanged when one of them matched. */
  terms: string[];
  folded: string[];
  action: SearchAction;
}

export interface SearchHit { entry: SearchEntry; score: number; matched: string }

const KIND_ORDER: Record<SearchKind, number> = { system: 0, group: 1, country: 2, view: 3, region: 4, concept: 5 };

export const KIND_LABEL: Record<SearchKind, string> = {
  system: "System", group: "Regional overview", country: "Country", view: "View", region: "Region", concept: "Glossary",
};

export function makeEntry(e: Omit<SearchEntry, "folded">): SearchEntry {
  return { ...e, folded: e.terms.map(normalizeForSearch) };
}

export function systemEntries(m: Manifest): SearchEntry[] {
  return m.systems.map((s) => makeEntry({
    key: `system:${s.id}`, kind: "system", label: s.name,
    sub: s.kind === "theatre" ? "The indexed system · opens it" : `${STATUS.country_system} · opens it`,
    terms: [s.name, ...(s.aliases ?? [])],
    action: { type: "system", id: s.id },
  }));
}

/** Regional overviews only: a membership list (GCC, OPEC) has no page of its own. */
export function groupEntries(m: Manifest): SearchEntry[] {
  return Object.entries(m.groups ?? {}).filter(([, g]) => g.slug && g.context).map(([id, g]) => makeEntry({
    key: `group:${id}`, kind: "group", label: `${g.label} overview`,
    sub: "National energy context and links to each country's record",
    terms: [g.label, `${g.label} overview`],
    action: { type: "group", slug: g.slug as string },
  }));
}

/** The Impact Atlas and its preset views (iteration 22). Links only: no impact record is loaded
 *  for search, and none is fetched until the reader opens the atlas. Each address is the one the
 *  atlas's own preset chip writes (a test holds the two together). */
export const IMPACT_ENTRIES: SearchEntry[] = [
  makeEntry({ key: "view:impacts", kind: "view", label: "Impact atlas", sub: "Reviewed impact records across countries · no score, not a census",
              terms: ["Impact atlas", "impacts", "impact records", "civilian services", "service disruptions", "atlas"],
              action: { type: "href", href: "?view=impacts" } }),
  makeEntry({ key: "view:impacts:cyber", kind: "view", label: "Cyber disruptions", sub: "Impact atlas, filtered to a reported malicious cyber cause",
              terms: ["Cyber disruptions", "cyber", "cyberattack", "cyber attack", "ransomware", "hacking"],
              action: { type: "href", href: "?view=impacts&f.cause=cyber" } }),
  makeEntry({ key: "view:impacts:ai", kind: "view", label: "AI involvement: records", sub: "Impact atlas, filtered to records where a source ties AI to the incident",
              terms: ["AI involvement records", "AI involved", "artificial intelligence", "AI-assisted", "AI incidents"],
              action: { type: "href", href: "?view=impacts&f.ai=ASSESSED,CLAIMED,CONFIRMED,SUSPECTED" } }),
  makeEntry({ key: "view:impacts:attributed", kind: "view", label: "Attributed cyber disruptions", sub: "Impact atlas, filtered to cyber records with an assessed or formal attribution",
              terms: ["Attributed cyber", "attribution records", "who was responsible"],
              action: { type: "href", href: "?view=impacts&f.attr=ASSESSED,ATTRIBUTED&f.cause=cyber" } }),
];

/** "Gulf and Hormuz context": offered only when the manifest has that regional overview, and it
 *  opens the overview, which shows the context timeline. Aggregate statements only. */
export function regionalContextEntries(m: Manifest): SearchEntry[] {
  // The group whose overview carries the dated regional statements, as the manifest names it.
  return Object.entries(m.groups ?? {}).filter(([, g]) => g.slug && g.context && g.regional_context).map(([id, g]) => makeEntry({
    key: `context:${id}`, kind: "group", label: "Gulf and Hormuz context",
    sub: `Dated, sourced, aggregate statements · on the ${g.label} overview`,
    terms: ["Gulf and Hormuz context", "Hormuz", "Strait of Hormuz", "Hormuz context", "regional context"],
    action: { type: "group", slug: g.slug as string },
  }));
}

export const VIEW_ENTRIES: SearchEntry[] = [
  makeEntry({ key: "view:compare", kind: "view", label: "Compare systems", sub: "Side by side, each on its own terms",
              terms: ["Compare systems", "compare", "side by side"], action: { type: "href", href: "?compare=" } }),
  ...IMPACT_ENTRIES,
  makeEntry({ key: "view:home", kind: "view", label: "Home", sub: "Overview of every monitored system",
              terms: ["Home", "overview", "all systems"], action: { type: "system", id: "" } }),
];

export const CONCEPT_ENTRIES: SearchEntry[] = [
  makeEntry({ key: "concept:how-it-works", kind: "concept", label: "How this works", sub: "The method in six plain steps",
              terms: ["How this works", "methodology", "method", "how to read"], action: { type: "concept", id: "how-it-works" } }),
  ...GLOSSARY.map((g) => makeEntry({
    key: `concept:${g.id}`, kind: "concept", label: g.term, sub: g.plain.length > 90 ? `${g.plain.slice(0, 88)}…` : g.plain,
    terms: [g.term, ...g.aliases], action: { type: "concept", id: g.id },
  })),
];

export interface TheatreRegion { code: string; name: string; country: string }

/** The theatre's regions. Crimea is described as what it is, an occupied unit, never as a region
 *  of Russia. */
export function theatreRegionEntries(regions: TheatreRegion[], theatreName: string): SearchEntry[] {
  return regions.map((r) => makeEntry({
    key: `region:ru:${r.code}`, kind: "region", label: r.name,
    sub: r.country === "UA" ? `Occupied unit, internationally Ukrainian · ${theatreName}`
      : r.country === "BY" ? `Region of Belarus · ${theatreName}` : `Region of Russia · ${theatreName}`,
    terms: [r.name],
    action: { type: "href", href: `?sys=ru&r=${encodeURIComponent(r.code)}` },
  }));
}

export interface CountryRegionSource {
  systemId: string;
  systemName: string;
  unitLabel: string;
  units: { code: string; name: string }[];
  displayNames?: Record<string, string>;
  aliases?: Record<string, string[]>;
}

/** A loaded country's first-level regions, under the name the country page shows. */
export function countryRegionEntries(src: CountryRegionSource): SearchEntry[] {
  return src.units.map((u) => {
    const shown = src.displayNames?.[u.code] ?? u.name;
    const terms = [shown, ...(shown !== u.name ? [u.name] : []), ...(src.aliases?.[u.code] ?? [])];
    return makeEntry({
      key: `region:${src.systemId}:${u.code}`, kind: "region", label: shown,
      sub: `${src.unitLabel.charAt(0).toUpperCase()}${src.unitLabel.slice(1)} · ${src.systemName}`,
      terms,
      action: { type: "href", href: `?sys=${encodeURIComponent(src.systemId)}&r=${encodeURIComponent(u.code)}` },
    });
  });
}

// Names people type that are not in a country's name on the map. Keyed by that name, so a renamed
// country simply loses its alias.
const NAME_ALIASES: Record<string, string[]> = {
  "united kingdom": ["UK", "Britain", "Great Britain"],
  "united states of america": ["US", "USA"],
  "united arab emirates": ["UAE"],
};

/** Every country on the world map that the system entries do not already find by name. A country
 *  inside a system (Belarus, Hong Kong) opens that system; any other is selected on the home map. */
export function countryEntries(idx: WorldIndex, m: Manifest): SearchEntry[] {
  return idx.countries.flatMap((c) => {
    const aliases = NAME_ALIASES[c.name.toLowerCase()] ?? [];
    const sys = systemOf(m, c.unit);
    if (sys) {
      const [a, b] = [normalizeForSearch(sys.name), normalizeForSearch(c.name)];
      if (a.startsWith(b) || b.startsWith(a)) return [];
      return [makeEntry({
        key: `country:${c.a3}`, kind: "country", label: c.name,
        sub: `In the ${sys.name} ${sys.kind === "theatre" ? "theatre" : "system"} · opens it`,
        terms: [c.name, ...aliases], action: { type: "system", id: sys.id },
      })];
    }
    const state = stateOf(c.unit, idx, m);
    const within = state === "outside_area" ? systemOf(m, idx.partOf.get(c.unit) ?? "") : undefined;
    const sub = within ? `Partly monitored, in the ${within.name} ${within.kind === "theatre" ? "theatre" : "system"}` : STATUS[state];
    return [makeEntry({
      key: `country:${c.a3}`, kind: "country", label: c.name, sub: `${sub} · selects it on the map`,
      terms: [c.name, ...aliases, c.a3], action: { type: "select", key: c.unit },
    })];
  });
}

/** The place an option points at, for the home map to outline: a unit, or `group:<id>`. */
export function previewKey(e: SearchEntry, m: Manifest): string | null {
  const a = e.action;
  if (a.type === "system") return a.id || null;
  if (a.type === "select") return a.key;
  if (a.type === "group") {
    const hit = Object.entries(m.groups ?? {}).find(([, g]) => g.slug === a.slug);
    return hit ? `group:${hit[0]}` : null;
  }
  return null;
}

/** Ranked hits for `query`. Empty query, empty list. */
export function searchEntries(entries: SearchEntry[], query: string, limit = 12): SearchHit[] {
  const q = normalizeForSearch(query);
  if (!q) return [];
  const hits: SearchHit[] = [];
  for (const entry of entries) {
    let best = 0;
    let matched = entry.label;
    entry.folded.forEach((f, i) => {
      const s = matchScore(q, f);
      if (s > best) { best = s; matched = entry.terms[i]; }
    });
    if (best > 0) hits.push({ entry, score: best, matched });
  }
  hits.sort((a, b) => b.score - a.score || KIND_ORDER[a.entry.kind] - KIND_ORDER[b.entry.kind]
    || a.entry.label.localeCompare(b.entry.label));
  return hits.slice(0, limit);
}

// ---- cheap region sources -------------------------------------------------------------------

let theatrePromise: Promise<TheatreRegion[]> | null = null;

/** The theatre's region list (about 17 kB), fetched once, on first use. A failure is not cached. */
export function loadTheatreRegions(): Promise<TheatreRegion[]> {
  if (!theatrePromise) {
    // The same request the theatre's bundle uses (data.ts), so searching first and then opening the
    // theatre downloads regions.json once.
    theatrePromise = loadRegionRows()
      .then((rows: unknown) => {
        if (!Array.isArray(rows)) throw new Error("regions: not a list");
        return rows.filter((x) => x && typeof x.code === "string" && typeof x.name === "string")
          .map((x) => ({ code: x.code, name: x.name, country: String(x.country ?? "") }));
      })
      .catch((err) => { theatrePromise = null; throw err; });
  }
  return theatrePromise;
}

// Regions of countries whose page this tab has loaded. Kept for the session, never fetched for it.
const loaded = new Map<string, SearchEntry[]>();
const listeners = new Set<() => void>();

export function registerCountryRegions(src: CountryRegionSource) {
  loaded.set(src.systemId, countryRegionEntries(src));
  listeners.forEach((f) => f());
}

export function loadedCountryRegions(): SearchEntry[] {
  return [...loaded.values()].flat();
}

export function onCountryRegions(f: () => void): () => void {
  listeners.add(f);
  return () => { listeners.delete(f); };
}
