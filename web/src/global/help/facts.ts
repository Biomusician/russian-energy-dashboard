/** `global/help_facts.json`: the live values the Help page shows (pipeline/help_facts.py).
 *
 *  One small file instead of the snapshot and the impact corpus. Fetched through the shared
 *  request cache, refused if malformed, and only by the Help page.
 */
import { validated } from "../manifest";

export const HELP_FACTS_PATH = "global/help_facts.json";

export interface HelpContribution {
  sector: string;
  included: boolean;
  sector_value: number | null;
  nominal_weight: number | null;
  effective_weight: number | null;
  index_points: number | null;
  excluded_reason: string | null;
}

export interface HelpFacts {
  schema_version: number;
  as_of: string;
  build_time: string;
  theatre: {
    method_version: string | null;
    sectors_uncovered: string[];
    contributions: HelpContribution[];
    transmission_saturation_events: number | null;
    recovery_horizon_sensitivity: { declared: number | null; low: number | null; high: number | null; note: string | null };
    status_delay_days: number | null;
    coverage: {
      enumerated_oil_strikes: number | null;
      reported_oil_strikes: number | null;
      coverage_ratio: number | null;
      incidents_with_quantified_capacity: number | null;
      incidents_with_reported_effect?: number | null;
      incident_total: number | null;
    };
    cannot_tell_you: { question: string; answer: string }[];
    build_date_note: string | null;
    earliest_published_date: string | null;
  };
  impacts: {
    as_of: string | null;
    scope_statement: string | null;
    caveats: string[];
    research: { window: { start: string; end: string } | null; status: string | null; latest_research_date: string | null; limitations: string[] };
    cyber_mechanisms: { label: string; definition: string | null }[];
    absence_words: { label: string; definition: string | null }[];
  };
  regional_context: { as_of: string | null; statement: string | null; not_built: string | null };
  context_vintage: { source: string | null; release: string | null; retrieved: string | null; comparison_year: number | null;
                     update_cadence: string | null; note: string | null };
}

const isObj = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null && !Array.isArray(x);

/** What the page reads without checking. */
export function helpFactsProblems(x: unknown): string[] {
  if (!isObj(x)) return ["not an object"];
  const out: string[] = [];
  const t = x.theatre, i = x.impacts;
  if (!isObj(t) || !Array.isArray(t.contributions) || !Array.isArray(t.cannot_tell_you) || !Array.isArray(t.sectors_uncovered)
      || !isObj(t.coverage) || !isObj(t.recovery_horizon_sensitivity)) out.push("theatre facts malformed");
  if (!isObj(i) || !Array.isArray(i.caveats) || !isObj(i.research) || !Array.isArray(i.cyber_mechanisms)
      || !Array.isArray(i.absence_words)) out.push("impact facts malformed");
  if (!isObj(x.regional_context) || !isObj(x.context_vintage)) out.push("context facts malformed");
  return out;
}

export function loadHelpFacts(): Promise<HelpFacts> {
  return validated<HelpFacts>(HELP_FACTS_PATH, helpFactsProblems);
}
