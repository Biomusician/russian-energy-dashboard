/** From the served payloads to what a brief is allowed to know (iteration 22).
 *
 *  This is the one place a served record meets a brief, and it is where the record is narrowed:
 *  `briefRecords` keeps a cause, an IT-failure flag and the services, and nothing else crosses.
 *  The Gulf input is built from the group's records TOGETHER; no step here reads a record's country,
 *  so no per-country impact figure can be made, by design and not by restraint.
 *
 *  Pure: type imports, the shared model and the formatters. No React, no DOM.
 */
import { fmtDate } from "../../../data";
import { fmtValue, type ContextRow, type EnergyContext } from "../../context";
import type { CountrySystem, GroupContext } from "../../manifest";
import { impactsFor } from "../load";
import type { ConfidenceMethod, ImpactRecord, ImpactsPayload, RegionalContext, VocabEntry } from "../types";
import {
  briefRecords, briefStatements, provisionalNote,
  type BriefConfidence, type BriefImpacts, type BriefStatement, type CountryBriefInput, type GulfBriefInput,
} from "./impactBrief";

const labelled = (v: readonly VocabEntry[] | undefined) => (v ?? []).map((e) => ({ id: String(e.id), label: e.label }));

/** The impact layer for a brief. `payload` null is a failed download, which a brief says in words. */
export function briefImpacts(payload: ImpactsPayload | null, records: readonly ImpactRecord[], method: ConfidenceMethod | null = null): BriefImpacts {
  if (!payload) return "unavailable";
  return {
    records: briefRecords(records),
    vocab: {
      cause_families: labelled(payload.vocabularies.cause_families),
      sectors: labelled(payload.vocabularies.sectors),
      digital_categories: labelled(payload.vocabularies.digital_categories),
      // The method's own order of categories, when the method has loaded.
      confidence: method ? method.categories.filter((c) => c.id).map((c) => ({ id: String(c.id), label: c.label })) : undefined,
    },
    window: payload.research.window ?? null,
    limitations: payload.research.limitations ?? [],
    latestResearch: payload.research.latest_research_date,
  };
}

export function briefContextStatements(regional: RegionalContext): BriefStatement[] {
  return briefStatements(regional.entries, labelled(regional.context_types));
}

export function briefConfidence(method: ConfidenceMethod | null): BriefConfidence | null {
  if (!method) return null;
  return {
    statement: method.statement,
    categories: method.categories.map((c) => ({ label: c.label, meaning: c.meaning })),
    provisional: provisionalNote(method.status),
  };
}

/** Which regional group a served context file describes. The file names itself (`context_id`) but
 *  not the group it belongs to, so the pairing is written here once; if the build serves `group`,
 *  that wins and this table is not read. */
const CONTEXT_GROUP: Record<string, string> = { gulf_hormuz: "gulf_littoral" };

export function contextDescribes(regional: Pick<RegionalContext, "context_id"> & { group?: string | null }, groupId: string): boolean {
  if (regional.group) return regional.group === groupId;
  return Object.prototype.hasOwnProperty.call(CONTEXT_GROUP, regional.context_id) && CONTEXT_GROUP[regional.context_id] === groupId;
}

export interface GulfBriefSources {
  ctx: GroupContext;
  /** The national figure the brief shows: the one the reader chose, or the page's first. */
  metricId: string;
  /** The manifest group's member system ids. */
  members: readonly string[];
  payload: ImpactsPayload | null;
  regional: RegionalContext | null;
  method: ConfidenceMethod | null;
  buildDate: string;
}

export function gulfBriefInput(a: GulfBriefSources): GulfBriefInput {
  const m = a.ctx.metrics[a.metricId];
  const src = a.ctx.sources[m.source_id];
  const r = a.ctx.region[a.metricId];
  return {
    group: { label: a.ctx.label, members: a.ctx.systems.length },
    energy: {
      label: m.label, unit: m.unit, year: m.year,
      source: `${src?.name ?? "source not stated"}${src?.release ? `, release of ${fmtDate(src.release)}` : ""}`,
      // Served alphabetically. A national energy total and its unit: the one figure a member has here.
      rows: a.ctx.systems.map((s) => ({ name: s.name, value: fmtValue(s.values[a.metricId], m.unit) })),
      total: r.value != null
        ? `${fmtValue(r.value, m.unit)}${r.world_share != null ? `, ${Math.round(r.world_share * 1000) / 10}% of the world total (a descriptive annual share, not an order of importance)` : ""}`
        : null,
      totalReason: r.reason,
    },
    impacts: briefImpacts(a.payload, a.payload ? impactsFor(a.payload, { systemIds: a.members }) : [], a.method),
    statements: a.regional ? briefContextStatements(a.regional) : null,
    confidence: briefConfidence(a.method),
    buildDate: a.buildDate,
  };
}

export interface CountryBriefSources {
  /** The country, and its ISO alpha-3 code when it is not a monitored system (a system is found by its id). */
  name: string;
  a3: string | null;
  /** The country system, when the country is one. */
  system: CountrySystem | null;
  /** One line on how far the country's search got (laneCoverage.coverageSummary), when known. */
  coverage: string | null;
  campaignLine: string | null;
  reportingEnvironment: string | null;
  national: { row: ContextRow | null; ctx: EnergyContext } | null;
  payload: ImpactsPayload | null;
  /** The regional context, only when this system is in the group it describes. */
  regional: RegionalContext | null;
  method: ConfidenceMethod | null;
  buildDate: string;
}

export function countryBriefInput(a: CountryBriefSources): CountryBriefInput {
  const metric = a.national?.ctx.metrics.total_production;
  const value = a.national?.row?.values.total_production;
  return {
    name: a.name,
    buildDate: a.buildDate,
    national: a.national && a.national.row && metric
      ? { label: metric.label, value: fmtValue(value, metric.unit), year: a.national.ctx.comparison_year, source: a.national.ctx.source.name }
      : null,
    system: a.system
      ? { energyEvents: a.system.event_summary.recorded_events, reportingEnvironment: a.reportingEnvironment ?? a.system.reporting_environment,
          coverage: a.coverage, campaignLine: a.campaignLine }
      : null,
    // Inside this country only. A multi-country record that names it is included.
    impacts: briefImpacts(a.payload, a.payload ? impactsFor(a.payload, a.system ? { systemIds: [a.system.system_id] } : { a3: a.a3 ?? undefined }) : [], a.method),
    regional: a.regional ? { label: a.regional.label, statements: briefContextStatements(a.regional) } : null,
    confidence: briefConfidence(a.method),
  };
}

export function gulfBriefFilename(slug: string, buildDate: string): string {
  return `${slug}-impact-brief-${buildDate.slice(0, 10)}.png`;
}

export function countryBriefFilename(systemIdOrA3: string, buildDate: string): string {
  return `impact-brief-${systemIdOrA3.toLowerCase()}-${buildDate.slice(0, 10)}.png`;
}
