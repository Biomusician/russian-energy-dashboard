/** The country page's side tabs and their place in the address (iteration 22).
 *
 *  Eight tabs at most. Two are new: the impact layer's records for this country, and the Gulf and
 *  Strait of Hormuz regional context. The second exists only where the manifest puts the system in
 *  the group that context describes; no country is named here.
 *
 *  A tab is linkable: `?sys=ir&tab=impacts`. The default tab is never written, so every address
 *  shared before this iteration still opens what it opened.
 *
 *  Pure, with type imports only: the Python tests run this file in Node as it ships.
 */
import type { Manifest, ManifestSystem } from "./manifest";

export type Tab = "events" | "impacts" | "regional" | "sectors" | "context" | "research" | "sources" | "method";

/** The order the tabs are listed in: this country's own published record first, then the two
 *  separate corpora, then context and method. */
export const TAB_ORDER: readonly Tab[] = ["events", "impacts", "regional", "sectors", "context", "research", "sources", "method"];

export const DEFAULT_TAB: Tab = "events";

export const TAB_LABEL: Record<Tab, string> = {
  events: "Published energy disruptions",
  impacts: "Cyber & civilian services",
  regional: "Gulf & Hormuz context",
  sectors: "Sectors",
  context: "National energy context",
  research: "Research coverage",
  sources: "Sources & data quality",
  method: "Why no score",
};

/** The manifest group the regional context file describes, by its overview slug. One constant:
 *  `global/regional_context.json` is one artifact about one region (methodology §10). Which systems
 *  belong to that group is read from the manifest. */
export const REGIONAL_CONTEXT_GROUP_SLUG = "gulf";

export interface RegionalGroup {
  id: string;
  label: string;
  slug: string;
}

/** The regional-context group this system belongs to, or null. From the manifest's own member
 *  list; own keys only, and a group without an overview page is not one. */
export function regionalGroupFor(manifest: Pick<Manifest, "groups"> | null | undefined, systemId: string): RegionalGroup | null {
  const groups = manifest?.groups;
  if (!groups) return null;
  for (const id of Object.keys(groups)) {
    const g = groups[id];
    if (g && g.slug === REGIONAL_CONTEXT_GROUP_SLUG && Array.isArray(g.members) && g.members.includes(systemId)) {
      return { id, label: g.label, slug: g.slug };
    }
  }
  return null;
}

/** The tabs this system's page offers, in order. */
export function tabsFor(regional: RegionalGroup | null): Tab[] {
  return TAB_ORDER.filter((t) => t !== "regional" || regional !== null);
}

export function isTab(x: string | null | undefined): x is Tab {
  return !!x && (TAB_ORDER as readonly string[]).includes(x);
}

/** The tab an address names, or null when it names none or one that does not exist. */
export function tabFromSearch(search: string): Tab | null {
  const raw = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search).get("tab");
  const t = (raw ?? "").trim().toLowerCase();
  return isTab(t) ? t : null;
}

/** The tab to show: the one asked for when this system has it, else the default. A link to the
 *  regional tab of a system outside the group opens the country's own record, not an empty tab. */
export function resolveTab(asked: Tab | null, available: readonly Tab[]): Tab {
  return asked && available.includes(asked) ? asked : DEFAULT_TAB;
}

/** `search` with its `tab` set to `tab`; the default tab is removed, not written. Every other
 *  parameter, its order and its encoding are kept as they are, so the filters' short address form
 *  (`f.cause=a,b`) is not re-encoded. No leading "?". */
export function withTab(search: string, tab: Tab): string {
  const q = search.startsWith("?") ? search.slice(1) : search;
  const kept = q.split("&").filter((part) => part && part.split("=", 1)[0] !== "tab");
  if (tab !== DEFAULT_TAB) kept.push(`tab=${tab}`);
  return kept.join("&");
}

/** The link that opens one tab of one system: a real address, so it can be copied or opened in a
 *  new window. */
export function tabHref(systemId: string, tab: Tab): string {
  return `?${withTab(`sys=${encodeURIComponent(systemId)}`, tab)}`;
}

/** Whether the system sits in any regional-context group, from its manifest entry alone. Used
 *  before the manifest's group table is in hand; `regionalGroupFor` decides. */
export function mayHaveRegional(entry: Pick<ManifestSystem, "regional_groups"> | null | undefined): boolean {
  return (entry?.regional_groups ?? []).length > 0;
}
