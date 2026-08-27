/** Loads the static JSON payload the Python pipeline writes into public/data/.
 *  There is no API: every file here is a build artifact served straight off the CDN. */

import type { Bundle } from "./types";

const BASE = `${import.meta.env.BASE_URL}data`;

async function grab<T>(name: string): Promise<T> {
  const res = await fetch(`${BASE}/${name}`);
  if (!res.ok) {
    throw new Error(`could not load ${name} (HTTP ${res.status}) — run the pipeline first`);
  }
  return (await res.json()) as T;
}

export async function loadBundle(): Promise<Bundle> {
  const [
    snapshot, national, regional, incidents, regions, assets, taxonomy,
    regionsGeo, linesGeo, contextLand, contextBorders, ocean,
  ] = await Promise.all([
    grab<Bundle["snapshot"]>("snapshot.json"),
    grab<Bundle["national"]>("index_national.json"),
    grab<Bundle["regional"]>("index_regional.json"),
    grab<Bundle["incidents"]>("incidents.json"),
    grab<Bundle["regions"]>("regions.json"),
    grab<Bundle["assets"]>("assets.json"),
    grab<Bundle["taxonomy"]>("taxonomy.json"),
    grab<Bundle["regionsGeo"]>("regions.geojson"),
    grab<Bundle["linesGeo"]>("assets_lines.geojson"),
    grab<Bundle["contextLand"]>("context_land.geojson"),
    grab<Bundle["contextBorders"]>("context_borders.geojson"),
    grab<Bundle["ocean"]>("ocean.geojson"),
  ]);
  return {
    snapshot, national, regional, incidents, regions, assets, taxonomy,
    regionsGeo, linesGeo, contextLand, contextBorders, ocean,
  };
}

/** Index of the timeline step at or before `date`. */
export function stepFor(dates: string[], date: string): number {
  let lo = 0;
  let hi = dates.length - 1;
  if (date <= dates[0]) return 0;
  if (date >= dates[hi]) return hi;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (dates[mid] <= date) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

export function fmtDate(iso: string): string {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const mon = months[Number(m) - 1] ?? m;
  return d ? `${Number(d)} ${mon} ${y}` : `${mon} ${y}`;
}

export function fmtNum(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString("en-GB", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function titleCase(key: string): string {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
