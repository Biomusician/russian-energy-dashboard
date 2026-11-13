import { describe, expect, it } from "vitest";
import {
  FILTERED, MEMBER_RAMP, NEUTRAL, NO_DATA, OTHER, ZERO, collapseFeed, groupFill, membersAlphabetical, metricFacts, specialValues,
} from "./groupMap";
import type { GroupContext, GroupSystem, RecentEpisode } from "./manifest";

const sys = (id: string, name: string, v: number | null, gcc = true): GroupSystem => ({
  system_id: id, name, a3: id.toUpperCase(), gcc_member: gcc, opec_member: !gcc, maturity: "research_preview",
  recovery_status_withheld: true, values: { m: v }, role: null, last_systematic_pass: null,
  lane_states: {}, languages_required: [], languages_executed: [], reporting_environment: "media_only",
} as unknown as GroupSystem);

// Names deliberately out of order, and the largest figure first: the list must not follow it.
const SYSTEMS = [sys("zz", "Zeta", 900), sys("aa", "Alpha", 10), sys("mm", "Mu", 0), sys("nn", "Nu", null, false)];
const all = () => true;

function colourOf(expr: unknown, a3: string): unknown {
  const e = expr as unknown[];
  const i = e.indexOf(a3, 2);
  return e[i + 1];
}

describe("the member list", () => {
  it("is in name order whatever the figures say", () => {
    expect(membersAlphabetical(SYSTEMS).map((s) => s.name)).toEqual(["Alpha", "Mu", "Nu", "Zeta"]);
    // Not a figure order in either direction.
    const byFigure = [...SYSTEMS].sort((a, b) => (b.values.m ?? -1) - (a.values.m ?? -1)).map((s) => s.name);
    expect(membersAlphabetical(SYSTEMS).map((s) => s.name)).not.toEqual(byFigure);
  });

  it("does not reorder the array it is given", () => {
    const copy = [...SYSTEMS];
    membersAlphabetical(SYSTEMS);
    expect(SYSTEMS).toEqual(copy);
  });
});

describe("the regional fill", () => {
  it("is one colour for every member until a figure is chosen", () => {
    const f = groupFill(SYSTEMS, null, all);
    for (const s of SYSTEMS) expect(colourOf(f, s.a3)).toBe(NEUTRAL);
    expect((f as unknown[]).at(-1)).toBe(OTHER);
  });

  it("keeps zero, no data, filtered-out and other countries apart", () => {
    const f = groupFill(SYSTEMS, "m", (s) => s.gcc_member);
    expect(colourOf(f, "MM")).toBe(ZERO);
    expect(colourOf(f, "NN")).toBe(FILTERED);
    expect(colourOf(f, "ZZ")).toBe(MEMBER_RAMP[4]);
    const g = groupFill(SYSTEMS, "m", all);
    expect(colourOf(g, "NN")).toBe(NO_DATA);
    expect(new Set([ZERO, NO_DATA, FILTERED, OTHER, NEUTRAL, ...MEMBER_RAMP]).size).toBe(5 + MEMBER_RAMP.length);
  });

  it("says which special values are on the map", () => {
    expect(specialValues(SYSTEMS, "m", all)).toEqual({ zero: true, noData: true });
    expect(specialValues(SYSTEMS, "m", (s) => s.gcc_member && s.values.m !== 0)).toEqual({ zero: false, noData: false });
  });
});

describe("the figure's facts", () => {
  const ctx = {
    metrics: { m: { label: "Total", unit: "quad Btu", definition: "What it counts.", year: 2024, source_id: "eia" } },
    sources: { eia: { name: "EIA", url: "https://example.org", release: "2026-10-16", attribution: null } },
    accounting_convention: "Nuclear by heat, renewables by electricity.",
  } as unknown as GroupContext;

  it("carries definition, year, unit, source and the accounting convention", () => {
    expect(metricFacts(ctx, "m")).toEqual({
      label: "Total", year: 2024, unit: "quad Btu", definition: "What it counts.", source: "EIA",
      sourceUrl: "https://example.org", release: "2026-10-16", accounting: "Nuclear by heat, renewables by electricity.",
    });
    expect(metricFacts(ctx, "missing")).toBeNull();
  });
});

describe("the regional feed", () => {
  const ep = (sid: string, id: string, withheld: boolean, date: string): RecentEpisode => ({
    system_id: sid, country: sid.toUpperCase(), episode_id: id, episode_name: null, basis: "b", records: 1,
    first_date: date, last_date: date, date_precision: "day", classes: ["refinery"], causes: ["attack"],
    members: [{ date, date_precision: "day", region: "National", effect: null, effect_on_country_page: !withheld, withheld }],
    more_members: 0,
  });

  it("folds a run of one country's safeguarded episodes into one line with no count", () => {
    const eps = [ep("sa", "1", true, "2026-04-08"), ep("sa", "2", true, "2026-03-02"), ep("sa", "3", true, "2026-02-23"),
                 ep("iq", "4", false, "2025-12-23"), ep("sa", "5", true, "2025-01-01"), ep("kw", "6", true, "2024-01-01"),
                 ep("kw", "7", true, "2023-01-01")];
    const items = collapseFeed(eps);
    expect(items.map((i) => i.kind)).toEqual(["safeguarded", "episode", "episode", "safeguarded"]);
    const first = items[0];
    if (first.kind !== "safeguarded") throw new Error("expected a folded run");
    expect(first.newest.first_date).toBe("2026-04-08");
    expect(first.oldest.first_date).toBe("2026-02-23");
    // No number of records travels with the folded line.
    expect(JSON.stringify({ ...first, newest: null, oldest: null })).not.toMatch(/\b3\b/);
    expect(Object.keys(first).sort()).toEqual(["causes", "classes", "country", "key", "kind", "newest", "oldest", "system_id"]);
  });

  it("never folds across countries or over an episode that is not safeguarded", () => {
    const eps = [ep("sa", "1", true, "2026-04-08"), ep("kw", "2", true, "2026-03-02"), ep("sa", "3", false, "2026-02-23")];
    expect(collapseFeed(eps).map((i) => i.kind)).toEqual(["episode", "episode", "episode"]);
    expect(collapseFeed([])).toEqual([]);
  });
});
