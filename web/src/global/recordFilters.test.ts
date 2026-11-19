import { describe, expect, it } from "vitest";
import {
  NO_FILTERS, activeFilters, applyFilters, dateBounds, daysBefore, decodeFilters, describeFilters, encodeFilters,
  filterQueryOf, hidingFilters, isIsoDay, optionCounts, optionsPresent, setDate, toggleChoice, withFilterQuery,
  withoutFilters, type FilterDef, type FilterState,
} from "./recordFilters";

/** Iteration 22: the shared record filters. Made records, because the rules are the model's own;
 *  the country page's use of them against served payloads is in countryFilters.test.ts. */

interface Rec { id: string; date: string; end?: string | null; cause: string; tags: string[] }

const RECS: Rec[] = [
  { id: "a", date: "2026-11-10", cause: "technical", tags: ["x"] },
  { id: "b", date: "2026-09-01", cause: "natural_hazard", tags: ["x", "y"] },
  { id: "c", date: "2025-12-25", end: "2026-01-05", cause: "technical", tags: [] },
  { id: "d", date: "2023-03-03", cause: "unknown", tags: ["y"] },
  { id: "e", date: "2021-06-01", cause: "natural_hazard", tags: ["z"] },
];

const DEFS: FilterDef<Rec>[] = [
  { kind: "date", id: "date", label: "Date", start: (r) => r.date, end: (r) => r.end },
  { kind: "choice", id: "cause", label: "Cause", values: (r) => [r.cause],
    options: [{ value: "natural_hazard", label: "Natural hazard" }, { value: "technical", label: "Technical accident" }, { value: "unknown", label: "Unknown" }] },
  { kind: "choice", id: "tag", label: "Tag", values: (r) => r.tags,
    options: [{ value: "x", label: "X" }, { value: "y", label: "Y" }, { value: "z", label: "Z" }] },
];
const TODAY = "2026-11-19";
const ids = (rs: Rec[]) => rs.map((r) => r.id).join("");
const state = (s: Partial<FilterState>): FilterState => ({ choices: {}, dates: {}, ...s });

describe("applying filters", () => {
  it("no filter shows every record, in the order given", () => {
    expect(ids(applyFilters(RECS, DEFS, NO_FILTERS, TODAY))).toBe("abcde");
  });

  it("values within one filter are alternatives; filters combine", () => {
    expect(ids(applyFilters(RECS, DEFS, state({ choices: { cause: ["technical", "unknown"] } }), TODAY))).toBe("acd");
    expect(ids(applyFilters(RECS, DEFS, state({ choices: { cause: ["technical", "unknown"], tag: ["y"] } }), TODAY))).toBe("d");
  });

  it("a record with several values matches on any of them, and one with none matches no choice", () => {
    expect(ids(applyFilters(RECS, DEFS, state({ choices: { tag: ["y"] } }), TODAY))).toBe("bd");
    expect(ids(applyFilters(RECS, DEFS, state({ choices: { tag: ["x", "y", "z"] } }), TODAY))).toBe("abde");
  });

  it("date presets count back from the reader's day", () => {
    expect(dateBounds({ preset: "30d" }, TODAY)).toEqual({ from: "2026-10-20", to: null });
    expect(dateBounds({ preset: "90d" }, TODAY)).toEqual({ from: "2026-08-21", to: null });
    expect(dateBounds({ preset: "1y" }, TODAY)).toEqual({ from: "2025-11-19", to: null });
    expect(dateBounds({ preset: "2022" }, TODAY)).toEqual({ from: "2022-01-01", to: null });
    expect(ids(applyFilters(RECS, DEFS, state({ dates: { date: { preset: "30d" } } }), TODAY))).toBe("a");
    expect(ids(applyFilters(RECS, DEFS, state({ dates: { date: { preset: "90d" } } }), TODAY))).toBe("ab");
    expect(ids(applyFilters(RECS, DEFS, state({ dates: { date: { preset: "1y" } } }), TODAY))).toBe("abc");
    expect(ids(applyFilters(RECS, DEFS, state({ dates: { date: { preset: "2022" } } }), TODAY))).toBe("abcd");
  });

  it("a record that spans days is shown when any of its days is in a custom range", () => {
    // c runs 25 Dec 2025 to 5 Jan 2026.
    expect(ids(applyFilters(RECS, DEFS, state({ dates: { date: { from: "2026-01-01", to: "2026-01-31" } } }), TODAY))).toBe("c");
    expect(ids(applyFilters(RECS, DEFS, state({ dates: { date: { from: "2026-01-06", to: "2026-01-31" } } }), TODAY))).toBe("");
    expect(ids(applyFilters(RECS, DEFS, state({ dates: { date: { from: null, to: "2023-12-31" } } }), TODAY))).toBe("de");
    expect(ids(applyFilters(RECS, DEFS, state({ dates: { date: { from: "2026-09-01", to: null } } }), TODAY))).toBe("ab");
  });

  it("calendar arithmetic crosses months and leap days without a local clock", () => {
    expect(daysBefore("2024-03-01", 1)).toBe("2024-02-29");
    expect(daysBefore("2026-01-15", 30)).toBe("2025-12-16");
    expect(isIsoDay("2024-02-29")).toBe(true);
    expect(isIsoDay("2023-02-29")).toBe(false);
    expect(isIsoDay("2023-2-9")).toBe(false);
  });
});

describe("counts beside options", () => {
  it("count the records of this list that the OTHER filters admit", () => {
    const s = state({ choices: { cause: ["technical"] } });
    // The cause filter does not narrow its own options: choosing another cause would show these.
    expect(Object.fromEntries(optionCounts(RECS, DEFS, s, TODAY, "cause"))).toEqual({ natural_hazard: 2, technical: 2, unknown: 1 });
    // The tag filter's numbers are inside the two technical records.
    expect(Object.fromEntries(optionCounts(RECS, DEFS, s, TODAY, "tag"))).toEqual({ x: 1, y: 0, z: 0 });
  });

  it("never exceed the records shown when the option is chosen alone", () => {
    for (const s of [NO_FILTERS, state({ dates: { date: { preset: "1y" } } }), state({ choices: { tag: ["x"] } })]) {
      for (const [value, n] of optionCounts(RECS, DEFS, s, TODAY, "cause")) {
        const alone = { ...s, choices: { ...s.choices, cause: [value] } };
        expect(applyFilters(RECS, DEFS, alone, TODAY)).toHaveLength(n);
      }
    }
  });

  it("an option list can be cut to what the list actually carries", () => {
    const some = RECS.slice(0, 2);
    expect(optionsPresent(DEFS[1].kind === "choice" ? DEFS[1].options : [], some, (r) => [r.cause]).map((o) => o.value))
      .toEqual(["natural_hazard", "technical"]);
  });
});

describe("editing", () => {
  it("toggling the last value of a filter switches the filter off", () => {
    let s = toggleChoice(NO_FILTERS, "cause", "technical");
    expect(activeFilters(DEFS, s)).toEqual(["cause"]);
    s = toggleChoice(s, "cause", "technical");
    expect(s).toEqual(NO_FILTERS);
    expect(NO_FILTERS).toEqual({ choices: {}, dates: {} });
  });

  it("an empty custom range is the filter switched off", () => {
    expect(setDate(NO_FILTERS, "date", { from: null, to: null })).toEqual(NO_FILTERS);
    expect(activeFilters(DEFS, setDate(NO_FILTERS, "date", { from: "2024-01-01", to: null }))).toEqual(["date"]);
  });

  it("names the filters that hide one record, so a link to it can clear exactly those", () => {
    const s = state({ choices: { cause: ["unknown"], tag: ["x"] }, dates: { date: { preset: "2022" } } });
    expect(hidingFilters(RECS[0], DEFS, s, TODAY)).toEqual(["cause"]);
    expect(hidingFilters(RECS[4], DEFS, s, TODAY)).toEqual(["date", "cause", "tag"]);
    const cleared = withoutFilters(s, hidingFilters(RECS[0], DEFS, s, TODAY));
    expect(applyFilters(RECS, DEFS, cleared, TODAY)).toContain(RECS[0]);
    expect(activeFilters(DEFS, cleared)).toEqual(["date", "tag"]);
  });
});

describe("the address", () => {
  it("round-trips every kind of choice", () => {
    const cases: FilterState[] = [
      NO_FILTERS,
      state({ choices: { cause: ["technical"] } }),
      state({ choices: { cause: ["natural_hazard", "unknown"], tag: ["z"] }, dates: { date: { preset: "90d" } } }),
      state({ dates: { date: { from: "2023-01-01", to: "2023-12-31" } } }),
      state({ dates: { date: { from: null, to: "2023-12-31" } } }),
      state({ dates: { date: { from: "2023-01-01", to: null } } }),
    ];
    for (const s of cases) {
      const { state: back, notes } = decodeFilters(encodeFilters(DEFS, s), DEFS);
      expect(back).toEqual(s);
      expect(notes).toEqual([]);
    }
  });

  it("is short, stable and independent of the order things were chosen in", () => {
    const one = toggleChoice(toggleChoice(toggleChoice(NO_FILTERS, "tag", "y"), "cause", "unknown"), "cause", "natural_hazard");
    const two = toggleChoice(toggleChoice(toggleChoice(NO_FILTERS, "cause", "natural_hazard"), "cause", "unknown"), "tag", "y");
    expect(encodeFilters(DEFS, one)).toBe("f.cause=natural_hazard,unknown&f.tag=y");
    expect(encodeFilters(DEFS, two)).toBe(encodeFilters(DEFS, one));
    expect(encodeFilters(DEFS, NO_FILTERS)).toBe("");
    expect(encodeFilters(DEFS, state({ dates: { date: { from: "2023-01-01", to: null } } }))).toBe("f.date=2023-01-01..");
  });

  it("reads a link whose values arrive in another order, repeated or percent-encoded", () => {
    const { state: s, notes } = decodeFilters("?sys=us&f.cause=unknown%2Ctechnical&f.cause=technical&f.tag=x", DEFS);
    expect(s.choices).toEqual({ cause: ["technical", "unknown"], tag: ["x"] });
    expect(notes).toEqual([]);
  });

  it("drops an unknown value with a visible note, and keeps the values it knows", () => {
    const { state: s, notes } = decodeFilters("f.cause=technical,sabotage", DEFS);
    expect(s.choices).toEqual({ cause: ["technical"] });
    expect(notes).toHaveLength(1);
    expect(notes[0]).toContain("Cause");
    expect(notes[0]).toContain("sabotage");
    expect(notes[0]).toMatch(/ignored/);
  });

  it("says so when every value of a filter was unknown, so the filter is off", () => {
    const { state: s, notes } = decodeFilters("f.cause=sabotage", DEFS);
    expect(s).toEqual(NO_FILTERS);
    expect(notes[0]).toMatch(/that filter is off/);
  });

  it("drops an unknown filter with a visible note", () => {
    const { state: s, notes } = decodeFilters("f.sector=telecom&f.cause=unknown", DEFS);
    expect(s.choices).toEqual({ cause: ["unknown"] });
    expect(notes).toHaveLength(1);
    expect(notes[0]).toContain("sector");
  });

  it("refuses a date it cannot read, with a note, instead of guessing", () => {
    for (const bad of ["f.date=yesterday", "f.date=2023-02-31..", "f.date=2024-05-01..2024-01-01", "f.date=.."]) {
      const { state: s, notes } = decodeFilters(bad, DEFS);
      expect(s).toEqual(NO_FILTERS);
      expect(notes).toHaveLength(1);
      expect(notes[0]).toContain("Date");
    }
  });

  it("never reads a value from the address as an object key", () => {
    const { state: s, notes } = decodeFilters("f.constructor=x&f.__proto__=y&f.cause=__proto__,constructor", DEFS);
    expect(s).toEqual(NO_FILTERS);
    expect(notes).toHaveLength(2);
    expect(Object.keys(s.choices)).toEqual([]);
  });

  it("a long unknown value is shown cut, not echoed whole", () => {
    const { notes } = decodeFilters(`f.cause=${"x".repeat(500)}`, DEFS);
    expect(notes[0].length).toBeLessThan(200);
  });

  it("carries the filter parameters beside a view's own, and replaces only them", () => {
    expect(filterQueryOf("?sys=us&r=US-TX&f.cause=technical&f.date=1y")).toBe("f.cause=technical&f.date=1y");
    expect(filterQueryOf("?sys=us&r=US-TX")).toBe("");
    expect(withFilterQuery("sys=us&r=US-TX&f.cause=technical", "f.tag=x")).toBe("sys=us&r=US-TX&f.tag=x");
    expect(withFilterQuery("?sys=us&f.cause=technical", "")).toBe("sys=us");
    expect(withFilterQuery("sys=us", "f.cause=technical")).toBe("sys=us&f.cause=technical");
  });
});

describe("saying what is on", () => {
  it("names each active filter with its labels and its dates", () => {
    const s = state({ choices: { cause: ["unknown", "technical"] }, dates: { date: { preset: "90d" } } });
    expect(describeFilters(DEFS, s, TODAY)).toEqual([
      "Date: Last 90 days (from 2026-08-21)",
      "Cause: Technical accident, Unknown",
    ]);
    expect(describeFilters(DEFS, NO_FILTERS, TODAY)).toEqual([]);
    expect(describeFilters(DEFS, state({ dates: { date: { from: "2023-01-01", to: "2023-06-30" } } }), TODAY)).toEqual(["Date: 2023-01-01 to 2023-06-30"]);
  });
});
