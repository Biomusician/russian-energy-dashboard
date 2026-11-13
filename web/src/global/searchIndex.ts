/** What the global search can find, and how results are ordered.
 *
 *  SOURCES, AND WHAT THEY COST. Systems, their aliases and the regional overviews come from the
 *  manifest, which every view has already loaded. Glossary concepts are in the bundle. Region
 *  names are added only where they are cheap: the theatre's region list (one small file, fetched
 *  the first time the search box is focused) and the regions of any country whose page this tab
 *  has already loaded. The home page never fetches a country's files to build the index.
 *
 *  ORDER. How well the words match, then kind, then name. Never a figure: a search result list
 *  is not a ranking of systems.
 */

import type { Manifest } from "./manifest";
import { GLOSSARY } from "./glossary";
import { matchScore, normalizeForSearch } from "./searchNormalize";

export type SearchKind = "system" | "group" | "view" | "region" | "concept";

export type SearchAction =
  | { type: "system"; id: string }
  | { type: "group"; slug: string }
  | { type: "href"; href: string }
  | { type: "concept"; id: string };

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

const KIND_ORDER: Record<SearchKind, number> = { system: 0, group: 1, view: 2, region: 3, concept: 4 };

export const KIND_LABEL: Record<SearchKind, string> = {
  system: "System", group: "Regional overview", view: "View", region: "Region", concept: "Glossary",
};

export function makeEntry(e: Omit<SearchEntry, "folded">): SearchEntry {
  return { ...e, folded: e.terms.map(normalizeForSearch) };
}

export function systemEntries(m: Manifest): SearchEntry[] {
  return m.systems.map((s) => makeEntry({
    key: `system:${s.id}`, kind: "system", label: s.name,
    sub: s.kind === "theatre" ? "Indexed theatre"
      : `Country system · no index${s.maturity === "research_preview" ? " · research preview" : ""}`,
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

export const VIEW_ENTRIES: SearchEntry[] = [
  makeEntry({ key: "view:compare", kind: "view", label: "Compare systems", sub: "Side by side, each on its own terms",
              terms: ["Compare systems", "compare", "side by side"], action: { type: "href", href: "?compare=" } }),
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

const BASE = `${import.meta.env.BASE_URL}data`;
let theatrePromise: Promise<TheatreRegion[]> | null = null;

/** The theatre's region list (about 17 kB), fetched once, on first use. A failure is not cached. */
export function loadTheatreRegions(): Promise<TheatreRegion[]> {
  if (!theatrePromise) {
    theatrePromise = fetch(`${BASE}/regions.json`, { cache: "no-cache" })
      .then((r) => {
        if (!r.ok) throw new Error(`regions: HTTP ${r.status}`);
        return r.json();
      })
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
