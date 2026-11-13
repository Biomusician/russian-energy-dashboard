/** What one country record's evidence does and does not show (iteration 21).
 *
 *  Pure functions over a served record, so the event card and the Evidence Inspector say the
 *  same thing and the tests can check it without a browser. Type imports only: the Python tests
 *  load this file in Node, and a value import of manifest.ts would need the Vite runtime.
 */
import type { CountryEvent, CountrySystem } from "./manifest";
import type { Placement } from "./placement";

// ---- originating statements ------------------------------------------------------------------
// A MIRROR of pipeline/build_systems.py (WIRE_ORIGINS, DISCOVERY_ONLY_DOMAINS, registered_domain,
// source_origin, event_origins). The country's source-health totals are computed there; the card
// computes the same thing per record here. tests/test_iteration21_country.py runs this file
// against the Python rule on every served record, so the two cannot drift apart unnoticed.

/** Wire services a republisher names in its publisher field: the wire is the origin, not the outlet. */
export const WIRE_ORIGINS: readonly (readonly [string, string])[] = [
  ["reuters", "Reuters"], ["bloomberg", "Bloomberg"], ["associated press", "Associated Press"],
  ["canadian press", "The Canadian Press"], ["xinhua", "Xinhua"], ["pti", "PTI"], ["ians", "IANS"],
  ["afp", "AFP"], ["spa", "Saudi Press Agency"], ["kuna", "KUNA"], ["wam", "WAM"], ["qna", "QNA"],
  ["irna", "IRNA"], ["wire copy", "an unnamed wire"],
];
/** Discovery aids, never an origin: an encyclopedia and a content aggregator restate others' reporting. */
export const DISCOVERY_ONLY_DOMAINS: readonly string[] = ["wikipedia.org", "indexbox.io"];
const SECOND_LEVEL = new Set(["co", "com", "gov", "org", "net", "ac", "edu", "nic"]);

export function registeredDomain(url: string | null | undefined): string {
  let host = url ?? "";
  const i = host.indexOf("://");
  if (i >= 0) host = host.slice(i + 3);
  host = host.split("/", 1)[0].split(":", 1)[0].toLowerCase();
  const labels = host.split(".").filter((x) => x && x !== "www");
  const n = labels.length;
  if (n >= 3 && labels[n - 1].length === 2 && SECOND_LEVEL.has(labels[n - 2])) return labels.slice(-3).join(".");
  return labels.slice(-2).join(".");
}

type Cited = { url: string; publisher?: string | null };

/** The originating statement a citation carries, as far as the record shows it; null for a
 *  discovery aid. Republication the record does not name stays invisible, so this can only
 *  undercount independence, never overstate it. */
export function sourceOrigin(s: Cited): string | null {
  const domain = registeredDomain(s.url);
  const publisher = (s.publisher ?? "").toLowerCase();
  if (DISCOVERY_ONLY_DOMAINS.includes(domain) || publisher.includes("wikipedia")) return null;
  const words = ` ${publisher.replace(/[^a-z]+/g, " ")} `;
  for (const [key, name] of WIRE_ORIGINS) {
    if (words.includes(` ${key} `)) return `wire:${name}`;
  }
  return domain || publisher;
}

export function eventOrigins(e: { sources: Cited[] }): Set<string> {
  const out = new Set<string>();
  for (const s of e.sources) {
    const o = sourceOrigin(s);
    if (o) out.add(o);
  }
  return out;
}

export interface OriginSummary {
  /** Distinct addresses cited. */
  pages: number;
  /** Distinct originating statements, alphabetical. */
  origins: string[];
  /** Citations that are Wikipedia or a content aggregator. */
  discoveryCitations: number;
  /** Every citation is a discovery aid: no originating statement is cited at all. */
  discoveryOnly: boolean;
}

export function originSummary(e: { sources: Cited[] }): OriginSummary {
  const origins = [...eventOrigins(e)].sort();
  const discoveryCitations = e.sources.filter((s) => sourceOrigin(s) === null).length;
  return {
    pages: new Set(e.sources.map((s) => s.url)).size,
    origins,
    discoveryCitations,
    discoveryOnly: origins.length === 0,
  };
}

/** The same totals the pipeline publishes as source_health.single_origin_events and
 *  discovery_only_events, recomputed from the records. */
export function originTotals(events: { sources: Cited[] }[]): { single_origin_events: number; discovery_only_events: number } {
  let single = 0;
  let none = 0;
  for (const e of events) {
    const n = eventOrigins(e).size;
    if (n === 1) single += 1;
    if (n === 0) none += 1;
  }
  return { single_origin_events: single, discovery_only_events: none };
}

/** "Reuters (wire service)" for a wire, the website otherwise. */
export function originLabel(origin: string): string {
  return origin.startsWith("wire:") ? `${origin.slice(5)} (wire service)` : origin;
}

export function countLine(s: OriginSummary): string {
  const p = `${s.pages} cited ${s.pages === 1 ? "page" : "pages"}`;
  const o = s.origins.length === 0
    ? "no originating statement"
    : `${s.origins.length} originating ${s.origins.length === 1 ? "statement" : "statements"}`;
  return `${p} · ${o}`;
}

// ---- placement and publication safeguards ------------------------------------------------------

export const KINETIC_CAUSES: readonly string[] = ["kinetic_strike", "sabotage"];

export type PlacementKind = "region" | "national" | "country_attack" | "country_rule";

/** How precisely a record is placed. A country-level attack record names no region or facility. */
export function placementKind(e: CountryEvent, sys: CountrySystem): PlacementKind {
  if (e.geography_precision === "admin1" && e.region_code) return "region";
  const policy = sys.geography.precision_policy;
  if (policy?.kinetic === "country" && KINETIC_CAUSES.includes(e.cause)) return "country_attack";
  if (policy?.other === "country") return "country_rule";
  return "national";
}

/** The record's placement in the shared reader words (placement.ts). A record not placed in one
 *  region that names regions it affected spans several; one that names none is national. */
export function eventPlacement(e: CountryEvent, sys: CountrySystem): Placement {
  const kind = placementKind(e, sys);
  if (kind === "region") return "one_region";
  if (kind === "country_attack") return "national_safeguarded";
  return Array.isArray(e.regions_affected) && e.regions_affected.length > 0 ? "several_regions" : "national";
}

/** An original-language headline may be shown. Never on a record under active-campaign
 *  safeguards or on a country-level attack record: a headline can name the place, the facility
 *  or a restart the record itself withholds. The build refuses such headlines; this is the
 *  page's own line of defence, so a gate change upstream cannot put one on screen. */
export function headlinesAllowed(e: CountryEvent, sys: CountrySystem): boolean {
  if (e.publication) return false;
  return placementKind(e, sys) !== "country_attack";
}

// ---- stable anchors -----------------------------------------------------------------------------

/** The opaque id the build gives an attack record under a country-level rule:
 *  `<system>-<date>-<class>-attack-<token>`. Every part but the token is already public. */
export function isOpaqueAttackId(e: CountryEvent, systemId: string): boolean {
  const prefix = `${systemId}-${e.date}-${e.asset_class.replace(/_/g, "-")}-attack-`;
  return e.event_id.startsWith(prefix) && /^[0-9a-z]{1,6}$/.test(e.event_id.slice(prefix.length));
}

/** The page anchor of one record, for deep links from other views: `?sys=<id>#ev-<event id>`;
 *  null when the record has no safe stable anchor.
 *
 *  A record published under active-campaign safeguards gets an anchor only if its id is the
 *  opaque one the build gives attack records under a country-level rule. An older system's id
 *  can name the facility ("...-ras-tanura-refinery-shutdown"), and every list that sets records
 *  side by side shows such a record as "National" with no facility, so a link from one must not
 *  carry that id. No other stable key that names nothing exists in the served record (the feeds'
 *  row keys are list positions), so such a record has no anchor rather than an invented one. */
export function eventAnchor(e: CountryEvent, systemId: string): string | null {
  if (e.publication && !isOpaqueAttackId(e, systemId)) return null;
  return `ev-${e.event_id.replace(/[^A-Za-z0-9_-]/g, "-")}`;
}

// ---- why the record is included, in plain words -----------------------------------------------

/** The inclusion-rule version these sentences were written against. A different served version
 *  falls back to the served rule's own wording rather than a paraphrase of a rule that changed. */
export const PLAIN_BASIS_VERSION = "2026-10-30.1";

export const PLAIN_BASIS: Record<number, string> = {
  1: "A refinery, gas-processing plant or LNG terminal was reported shut down, or its throughput was materially cut, and the effect was reported.",
  2: "Operations at an energy export or import terminal were reported suspended.",
  3: "A trunk pipeline was reported shut down, or force majeure was declared on it.",
  4: "A power plant of about 500 MW or more was forced offline with a reported effect, or a shortage of generation forced rotating power cuts.",
  5: "A power-grid event was reported to affect about 100,000 customers or more, or the grid operator declared an emergency.",
  6: "An event at a coal mine was reported to have materially cut supply.",
  7: "Oil or gas production was reported shut in at a material volume.",
};

export function plainBasis(e: CountryEvent, threshold: CountrySystem["inclusion_threshold"]): string {
  const n = e.criterion_met;
  if (n == null) return "The record meets the inclusion rule; which part of the rule it meets is not recorded.";
  if (threshold.version === PLAIN_BASIS_VERSION && PLAIN_BASIS[n]) return PLAIN_BASIS[n];
  const served = threshold.clauses[String(n)];
  return served ?? "The record meets the inclusion rule; which part of the rule it meets is not recorded.";
}

// ---- what the report does not establish --------------------------------------------------------

type Capacity = NonNullable<CountryEvent["capacity_affected"]>;

const MEASURE_TEXT: Record<Capacity["measure"], string> = {
  affected: "It is an amount affected by the event.",
  facility_size: "It is the facility's size, not the amount lost.",
  other: "It measures something other than the amount affected or the facility's size; read what the source says.",
};

const QUALIFIER_TEXT: Record<Capacity["qualifier"], string> = {
  exact: "The source gives it as a single figure.",
  about: "The source gives it as approximate (\"about\").",
  at_least: "The source gives it as a lower bound (\"at least\"); the true figure may be higher.",
  at_most: "The source gives it as an upper bound (\"at most\").",
  range: "The source gives a range, not one figure.",
  component_only: "It covers one part of the event only, not its total.",
  disputed: "Sources disagree, so no single figure is chosen.",
};

function num(v: number): string {
  return v.toLocaleString("en-GB");
}

/** The figure as the source states it, with its uncertainty in words; null when none is given. */
export function capacityFigure(c: Capacity): string | null {
  const u = c.unit ? ` ${c.unit}` : "";
  if (c.value != null) {
    const pre = c.qualifier === "about" ? "about " : c.qualifier === "at_least" ? "at least "
      : c.qualifier === "at_most" ? "at most " : "";
    return `${pre}${num(c.value)}${u}`;
  }
  if (c.value_min != null && c.value_max != null) return `${num(c.value_min)}–${num(c.value_max)}${u}`;
  if (c.value_min != null) return `at least ${num(c.value_min)}${u}`;
  if (c.value_max != null) return `at most ${num(c.value_max)}${u}`;
  return null;
}

/** One line per thing the record does not establish. Under active-campaign safeguards no figure
 *  and no later status is described: only that they are not published. */
export function notEstablished(e: CountryEvent): string[] {
  const out: string[] = [];
  const covered = !!e.publication;
  const c = e.capacity_affected;
  if (covered) {
    out.push("No capacity figure is shown for a record published under active-campaign safeguards; the reported effect is given as it was reported at the time.");
  } else if (!c) {
    out.push("No capacity figure is recorded, so the report does not establish how much capacity was affected.");
  } else {
    const fig = capacityFigure(c);
    out.push(`${fig ? `Capacity figure: ${fig}. ` : "No single capacity figure. "}${MEASURE_TEXT[c.measure]} ${QUALIFIER_TEXT[c.qualifier]}`);
  }
  if (e.date_precision === "month") out.push("The day is not known: the source gives only the month.");
  out.push(recoveryNotEstablished(e));
  out.push("It does not measure how severe the disruption was, and it is not comparable with records in other countries.");
  return out;
}

export function recoveryNotEstablished(e: CountryEvent): string {
  const r = e.recovery;
  switch (r.research_status) {
    case "WITHHELD_ACTIVE_CAMPAIGN":
      return "The facility's later status is not published while attacks on this country's energy facilities are still being reported.";
    case "NOT_YET_RESEARCHED":
      return "Whether service came back has not been researched yet.";
    case "RESEARCHED_NO_PUBLIC_EVIDENCE":
      return "Researched, and no public report that service came back was found. That is not a finding that it did not.";
    case "EVIDENCE_FOUND":
      if (r.kind === "estimate") return "Only an estimate of when service would come back was found, not an observed restoration.";
      if (r.kind === "supply_unaffected_statement" || r.kind === "no_supply_lost")
        return "A statement about supply was found, not a report about the facility itself.";
      if (r.kind === "partial_restart" || r.kind === "partial_restoration")
        return "An observed report of a partial return was found; full return is not established.";
      if (r.kind === "service_restored") return "An observed report that service was restored was found; physical repair is not implied.";
      return "An observed report of a return to service was found.";
    default:
      return "Whether service came back is not recorded.";
  }
}

// ---- review state, the parts safe to show ------------------------------------------------------

export const ROLE_VERDICT: Record<string, string> = {
  accept: "accepted",
  accept_with_correction: "accepted with a correction",
};

const ROLE_NAME: Record<string, string> = {
  evidence: "evidence check",
  safety: "publication-safety check",
  taxonomy: "classification check",
};

/** Verdicts only, never a reviewer's reasoning. */
export function roleVerdicts(e: CountryEvent): string[] {
  const roles = e.review.roles;
  if (!roles) return [];
  return (["evidence", "safety", "taxonomy"] as const).map((k) => `${ROLE_NAME[k]}: ${ROLE_VERDICT[roles[k]] ?? roles[k].replace(/_/g, " ")}`);
}

export const LINK_STATE_LABEL: Record<string, string> = {
  reachable: "reachable at the last automated check",
  redirected: "reached at a different address at the last automated check",
  blocked: "the site refused the automated check (not evidence that the page is gone)",
  dead: "gone at the last automated check",
  error: "failed to load at the last automated check",
};
