/** How old is the PAGE? (iteration 12 P2)
 *
 *  WHY THIS FILE EXISTS. On 2026-09-21 a false test assertion began failing. The refresh workflow
 *  gates its commit on the suite, so eleven consecutive good builds were discarded and the
 *  deployed dashboard served 2026-09-20 data for eleven days. Throughout, the ribbon printed the
 *  build's date followed by "· live", because "live" meant nothing more than "the scrubber is at
 *  the last timeline step" — a condition that is true of a frozen payload too. Nothing anywhere on
 *  the page said the monitor had stopped monitoring.
 *
 *  Two rules shape the design.
 *
 *  1. The age is computed in the BROWSER, against the reader's clock. The pipeline cannot do it:
 *     an age computed at build time freezes with the build and would read "0 days old" forever on
 *     a dashboard that had stopped rebuilding. That is the exact lie being fixed, so the payload
 *     ships reference dates and thresholds, never an age.
 *
 *  2. Unknown, unclassifiable and stale are three different answers and stay three different
 *     answers. A payload that does not state its cadence gets a factual age and no verdict; a
 *     payload with no readable date gets no age at all. Neither is reported as fresh, and neither
 *     is reported as stale.
 *
 *  Distinct from per-source freshness in data_quality.json, which measures how old a SOURCE is
 *  relative to the build. A fresh build of stale sources and a stale build of fresh sources are
 *  different failures and must never collapse into one indicator.
 */

export type FreshnessLevel =
  | "fresh"          // within the published cadence
  | "ageing"         // plausibly one missed run; state the age, do not alarm
  | "stale"          // several missed runs; warn
  | "badly_stale"    // a sustained outage
  | "unclassified"   // age known, no thresholds published — no verdict is available
  | "clock_behind"   // the reader's device clock predates the build; age is not meaningful
  | "unknown";       // no readable build date at all

/** The `publication_freshness` block emitted by pipeline/run.py. Optional throughout, because an
 *  N-1 payload served during a deploy will not carry it. */
export interface PublicationCadence {
  as_of?: string | null;
  build_time?: string | null;
  expected_cadence_days?: number | null;
  cadence_source?: string | null;
  ageing_after_days?: number | null;
  stale_after_days?: number | null;
  badly_stale_after_days?: number | null;
  note?: string | null;
}

export interface FreshnessAssessment {
  level: FreshnessLevel;
  /** Whole days from the build's as-of date to the reader's today, or null when unknowable. */
  days: number | null;
  /** Short suffix for the ribbon, beside the date. Never the word "live" unless it is. */
  shortLabel: string;
  /** Non-null only when the reader must be told something they would otherwise miss. */
  banner: string | null;
  /** True when the banner should be shown at headline weight rather than as a quiet aside. */
  severe: boolean;
}

const ISO_DAY = /^(\d{4})-(\d{2})-(\d{2})$/;

/** Calendar-day index for a plain YYYY-MM-DD, or null if it is not one. */
function dayIndex(iso: string): number | null {
  const m = ISO_DAY.exec(iso);
  if (!m) return null;
  const t = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return Number.isFinite(t) ? t / 86400000 : null;
}

/** A Date rendered as the calendar date the person holding that device would call today.
 *
 *  Local, not UTC, deliberately: the reader's sense of "today" is their own calendar, and the
 *  ±1-day slack below absorbs the timezone offset between them and the build machine. */
export function localISODate(now: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`;
}

function plural(n: number): string {
  return n === 1 ? "day" : "days";
}

/** Assess how old this build is, against a reader's Date. Pure: `now` is injected throughout. */
export function assessFreshness(
  asOf: string | null | undefined,
  cadence: PublicationCadence | null | undefined,
  now: Date,
): FreshnessAssessment {
  return assessFreshnessOn(asOf, cadence, localISODate(now));
}

/** The same assessment against a calendar date already in hand.
 *
 *  The export path has a date string rather than a Date, and routing it through `new Date(str)`
 *  would parse it as UTC midnight and then read it back with local getters — a silent off-by-one
 *  that would UNDERSTATE staleness. Two entry points, one implementation, no conversion. */
export function assessFreshnessOn(
  asOf: string | null | undefined,
  cadence: PublicationCadence | null | undefined,
  todayISO: string,
): FreshnessAssessment {
  const unknown: FreshnessAssessment = {
    level: "unknown", days: null, severe: false,
    shortLabel: "build date not stated",
    // Deliberately not a warning. We cannot establish that this build is stale, and asserting
    // staleness we cannot establish is the same error as asserting freshness we cannot establish.
    banner: null,
  };
  if (!asOf) return unknown;
  const from = dayIndex(asOf);
  const to = dayIndex(todayISO);
  if (from === null || to === null) return unknown;
  const days = to - from;

  // A reader west of the build machine can legitimately be one calendar day "before" its as-of
  // date. Only a genuinely wrong or deliberately-set-back clock goes further than that.
  if (days < -1) {
    return {
      level: "clock_behind", days, severe: false,
      shortLabel: "built after this device's clock",
      banner: "This build is dated after your device's clock, so its age cannot be checked here. "
        + "The figures are from the date shown.",
    };
  }

  const ageing = cadence?.ageing_after_days;
  const stale = cadence?.stale_after_days;
  const badly = cadence?.badly_stale_after_days;
  if (ageing == null || stale == null || badly == null) {
    // The age is a fact; whether it is acceptable is a judgement this payload does not carry.
    return {
      level: "unclassified", days, severe: false,
      shortLabel: days <= 0 ? "built today" : `built ${days} ${plural(days)} ago`,
      banner: null,
    };
  }

  if (days < ageing) {
    return { level: "fresh", days, severe: false, shortLabel: "live", banner: null };
  }

  const span = `${days} ${plural(days)}`;     // "11 days"
  const age = `${span} ago`;                  // "11 days ago" — never both forms in one sentence
  const expected = cadence?.expected_cadence_days;
  const cadenceClause = expected
    ? ` It is built every ${expected === 1 ? "day" : `${expected} days`}, so it has missed at `
      + `least ${days - expected} ${plural(days - expected)} of updates.`
    : "";
  const consequence = " Events after the date shown are not in these figures, and the index has"
    + " continued to decay in this build only up to that date.";

  if (days < stale) {
    return {
      level: "ageing", days, severe: false,
      shortLabel: `built ${age}`,
      banner: `This dashboard last rebuilt ${age}.${cadenceClause}`,
    };
  }
  if (days < badly) {
    return {
      level: "stale", days, severe: true,
      shortLabel: `built ${age}`,
      banner: `NOT CURRENT — this dashboard last rebuilt ${age}.${cadenceClause}${consequence}`,
    };
  }
  return {
    level: "badly_stale", days, severe: true,
    shortLabel: `built ${age}`,
    banner: `NOT CURRENT — this dashboard has not rebuilt in ${span}, which indicates its refresh `
      + `has failed rather than merely slipped.${cadenceClause}${consequence}`,
  };
}
