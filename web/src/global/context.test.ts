import { describe, expect, it } from "vitest";
import {
  NO_DATA, ZERO, breaksFor, contextProblems, dominantFuel, fmtValue, mixShares, modesFor, numericMode, rowForSystem,
  type ContextRow, type EnergyContext,
} from "./context";

function row(a3: string, v: Record<string, number | null>, system_id: string | null = null): ContextRow {
  return { a3, name: a3, on_map: true, system_id, values: v, newer: {}, roles: { overall: "net_producer", by_commodity: {} } };
}

const metrics = {
  total_production: { label: "Total primary energy production", unit: "quadrillion Btu", definition: "d", source_series: "s" },
  crude_production: { label: "Crude oil production", unit: "thousand barrels per day", definition: "d", source_series: "s" },
};
function ctx(countries: ContextRow[]): EnergyContext {
  return { schema_version: 1, kind: "k", statement: "s", not_scoring: "n", comparison_year: 2024, comparison_year_reason: "r", balance_band: 0.15,
    source: { id: "i", name: "EIA", url: "u", release: "2026-10-16", retrieved: "2026-11-10", licence: "l", attribution: "a", update_cadence: "c" },
    map_metrics: ["total_production", "crude_production"], metrics, coverage: {}, world: { values: {} }, countries };
}

describe("fmtValue", () => {
  it("never turns a missing value into zero", () => {
    expect(fmtValue(null, "quadrillion Btu")).toBe("no data");
    expect(fmtValue(undefined, "quadrillion Btu")).toBe("no data");
    expect(fmtValue(0, "quadrillion Btu")).toBe("0 quad Btu");
  });
  it("prints the unit", () => {
    expect(fmtValue(1234.4, "million tonnes")).toBe("1,234 Mt");
    expect(fmtValue(5.5, "terawatt-hours")).toBe("5.5 TWh");
  });
});

describe("numericMode", () => {
  const c = ctx([row("AAA", { total_production: 100, crude_production: 1 }), row("BBB", { total_production: 0, crude_production: 1 }),
                 row("CCC", { total_production: null, crude_production: 1 }), row("DDD", { total_production: 0.001, crude_production: 1 })]);
  const m = numericMode(c, "total_production");
  it("states metric and year in the title and the unit beside it", () => {
    expect(m.title).toBe("Total primary energy production — 2024");
    expect(m.unitNote).toContain("quadrillion Btu");
  });
  it("draws null and zero differently, and neither as a class of magnitude", () => {
    const fill = m.fill as unknown[];
    const colorOf = (a3: string) => {
      for (let i = 2; i < fill.length - 1; i += 2) if ((fill[i] as string[]).includes(a3)) return fill[i + 1];
      return fill[fill.length - 1];
    };
    expect(colorOf("CCC")).toBe(NO_DATA);
    expect(colorOf("BBB")).toBe(ZERO);
    expect(colorOf("AAA")).not.toBe(colorOf("DDD"));
    expect(NO_DATA).not.toBe(ZERO);
  });
  it("labels the empty classes in the legend", () => {
    expect(m.legend[0].label).toMatch(/no data/);
    expect(m.legend[1].label).toMatch(/zero/);
  });
  it("uses none of the ESDI severity colours", () => {
    const sev = ["#a8871f", "#c26326", "#b8382f"];
    for (const l of m.legend) expect(sev).not.toContain(l.color);
  });
});

describe("modes", () => {
  it("every mode carries a year or says what it compares", () => {
    const c = ctx([row("AAA", { total_production: 10, crude_production: 1, prod_coal: 9 })]);
    for (const m of modesFor(c)) {
      expect(m.title).toContain("2024");
      expect(m.unitNote.length).toBeGreaterThan(3);
    }
  });
});

describe("breaksFor", () => {
  it("ascends and handles no positive values", () => {
    const b = breaksFor([1, 10, 100, 1000]);
    expect(b).toEqual([...b].sort((x, y) => x - y));
    expect(breaksFor([])).toEqual([]);
  });
});

describe("rowForSystem", () => {
  it("takes the largest row of a multi-row system and never another system", () => {
    const c = ctx([row("HKG", { total_production: 0.1 }, "cn"), row("CHN", { total_production: 130 }, "cn"), row("USA", { total_production: 100 }, "us")]);
    expect(rowForSystem(c, "cn")?.a3).toBe("CHN");
    expect(rowForSystem(c, "zz")).toBeNull();
  });
});

describe("mix", () => {
  it("shares sum to about one and an empty country has none", () => {
    const r = row("AAA", { total_production: 10, prod_coal: 5, prod_gas: 5 });
    expect(mixShares(r).reduce((a, s) => a + s.share, 0)).toBeCloseTo(1);
    expect(dominantFuel(row("BBB", { total_production: null }))).toBeNull();
  });
});

describe("contextProblems", () => {
  it("refuses a malformed file", () => {
    expect(contextProblems(null).length).toBeGreaterThan(0);
    expect(contextProblems({ comparison_year: "x", countries: [] })).toContain("no comparison year");
    expect(contextProblems({ ...ctx([]), countries: [{ a3: "AAA" }] })).toContain("bad country rows");
  });
  it("passes a well-formed one", () => {
    expect(contextProblems(ctx([row("AAA", {})]))).toEqual([]);
  });
});
