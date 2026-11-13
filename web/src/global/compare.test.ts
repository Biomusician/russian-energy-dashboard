import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  COMPARE_ROW_IDS, EXPORT_CONTEXT_CAVEAT, EXPORT_NOT_COMPARABLE, compareBriefLines, compareFilename, compareRows, laneBuckets, resolveCompare,
  type CompareColumn,
} from "./compare";
import { fmtValue, type EnergyContext } from "./context";
import type { CountrySystem, Manifest } from "./manifest";

/** The comparison is tested on the payloads the site serves, plus a few hand-made edge cases. */

const DATA = new URL("../../public/data/", import.meta.url);
const read = (p: string) => JSON.parse(readFileSync(fileURLToPath(new URL(p, DATA)), "utf-8"));
const manifest = read("global/manifest.json") as Manifest;
const ctx = read("global/energy_context.json") as EnergyContext;

function columns(ids: string[]): CompareColumn[] {
  return resolveCompare(ids, manifest).columns.map((entry) => entry.kind === "theatre"
    ? { entry, system: null, status: "theatre" as const }
    : { entry, system: read(`${entry.root}/system.json`) as CountrySystem, status: "loaded" as const });
}

const countries = manifest.systems.filter((s) => s.kind === "country");
// Words that would make a row a disruption tally or a ranking.
const FORBIDDEN_ROW = /event|attack|held|withheld|severity|rank|score|count|incident|record count|candidates/i;

describe("resolveCompare", () => {
  it("keeps the reader's order, drops unknown ids, and caps at four", () => {
    const r = resolveCompare(["us", "zz", "ca", "__proto__", "sa", "cn", "in"], manifest);
    expect(r.columns.map((s) => s.id)).toEqual(["us", "ca", "sa", "cn"]);
    expect(r.unknown).toEqual(["zz", "__proto__"]);
    expect(r.over).toEqual([manifest.systems.find((s) => s.id === "in")!.name]);
  });

  it("does not let an inherited key or a constructor through", () => {
    expect(resolveCompare(["constructor", "toString", "hasOwnProperty"], manifest).columns).toEqual([]);
  });
});

describe("compareRows", () => {
  it("has exactly the declared rows, none of them a count, severity or rank", () => {
    const rows = compareRows(columns(["us", "ca"]), ctx, manifest);
    expect(rows.map((r) => r.id)).toEqual([...COMPARE_ROW_IDS]);
    for (const r of rows) {
      expect(r.id, r.id).not.toMatch(FORBIDDEN_ROW);
      // Row labels may say what a row is about ("published record") but never name a tally.
      expect(r.label, r.label).not.toMatch(/event|attack|held|severity|rank|score|count/i);
    }
  });

  it("never prints any system's event count, held count or the theatre's index value", () => {
    let checked = 0;
    // Every country with the theatre, in groups of up to four, so each column is exercised.
    for (let i = 0; i < countries.length; i += 3) {
      const ids = ["ru", ...countries.slice(i, i + 3).map((s) => s.id)];
      const cols = columns(ids);
      const rows = compareRows(cols, ctx, manifest);
      const text = rows.flatMap((r) => r.cells.flatMap((c) => [c.text, c.detail ?? "", ...(c.lines ?? [])])).join(" | ");
      const theatre = manifest.systems.find((s) => s.kind === "theatre")!;
      expect(text).not.toContain(String(theatre.headline!.value));
      for (const c of cols) {
        if (!c.system) continue;
        const n = c.system.event_summary.recorded_events;
        if (n > 9) expect(text, `${c.entry.id} event count`).not.toMatch(new RegExp(`\\b${n}\\b`));
        expect(text).not.toMatch(/qualifying (events|records)|held back|withheld/i);
        checked++;
      }
    }
    expect(checked).toBe(countries.length);
  });

  it("gives one cell per column, in the reader's order, for every row", () => {
    const orders = [["sa", "us", "ca"], ["ca", "sa", "us"], ["us", "ru"]];
    for (const ids of orders) {
      const rows = compareRows(columns(ids), ctx, manifest);
      for (const r of rows) expect(r.cells).toHaveLength(ids.length);
      const total = rows.find((r) => r.id === "ctx_total_production")!;
      const expected = ids.map((id) => {
        if (id === "ru") return "No single national figure";
        const row = ctx.countries.filter((c) => c.system_id === id)
          .reduce((a, b) => ((b.values.total_production ?? 0) > (a.values.total_production ?? 0) ? b : a));
        return fmtValue(row.values.total_production, ctx.metrics.total_production.unit);
      });
      expect(total.cells.map((c) => c.text)).toEqual(expected);
    }
  });

  it("says no index in words for every country, and never a zero", () => {
    const cols = columns(["us", "sa", "qa", "ru"]);
    const index = compareRows(cols, ctx, manifest).find((r) => r.id === "index")!;
    expect(index.cells.slice(0, 3).map((c) => c.text)).toEqual(["No index", "No index", "No index"]);
    expect(index.cells[3].text).toMatch(/own index .*not comparable/);
    for (const c of index.cells) expect(c.text).not.toMatch(/\b0\b/);
    expect(index.basisNote).toContain("No index is not a zero.");
  });

  it("keeps a missing national figure as no data, never zero", () => {
    const fake: EnergyContext = {
      ...ctx,
      countries: ctx.countries.map((r) => (r.system_id === "us"
        ? { ...r, values: { ...r.values, crude_production: null, gas_production: 0 } } : r)),
    };
    const rows = compareRows(columns(["us", "ca"]), fake, manifest);
    const crude = rows.find((r) => r.id === "ctx_crude_production")!.cells[0];
    expect(crude).toMatchObject({ kind: "no_data", text: "no data" });
    // A reported zero stays the source's own zero: it is a figure, not a missing one.
    expect(rows.find((r) => r.id === "ctx_gas_production")!.cells[0].text).toMatch(/^0 /);
  });

  it("states that the theatre has no single national row, and why", () => {
    const rows = compareRows(columns(["ru", "us"]), ctx, manifest);
    for (const r of rows.filter((x) => x.basis === "context")) {
      expect(r.cells[0]).toMatchObject({ kind: "not_applicable", text: "No single national figure" });
      expect(r.cells[0].detail).toMatch(/several countries/);
    }
  });

  it("labels every national row with its unit, year and definition", () => {
    const rows = compareRows(columns(["us", "ca"]), ctx, manifest).filter((r) => r.basis === "context");
    expect(rows).toHaveLength(4);
    for (const r of rows) {
      expect(r.label).toContain(String(ctx.comparison_year));
      expect(r.label).toMatch(/\((quadrillion Btu|thousand barrels per day|billion cubic metres|terawatt-hours), \d{4}\)/);
      expect(r.basisNote.length).toBeGreaterThan(10);
    }
    expect(rows[0].basisNote).toContain(ctx.accounting_convention!);
  });

  it("answers loading, failure and a missing context in words", () => {
    const [us, ca] = columns(["us", "ca"]);
    const rows = compareRows([{ ...us, system: null, status: "loading" }, { ...ca, system: null, status: "failed" }], null, manifest, true);
    const lanes = rows.find((r) => r.id === "lanes")!;
    expect(lanes.cells.map((c) => c.kind)).toEqual(["loading", "unavailable"]);
    expect(rows.find((r) => r.id === "ctx_total_production")!.cells[0].kind).toBe("unavailable");
  });

  it("puts lane states in the five words, never a percentage", () => {
    const rows = compareRows(columns(["us", "sa", "qa"]), ctx, manifest);
    for (const c of rows.find((r) => r.id === "lanes")!.cells) {
      expect(c.text).toMatch(/declared complete .* partial .* not started .* stopped by search limit .* source unavailable/);
      expect(c.text).not.toMatch(/%|per ?cent/);
    }
  });

  it("marks source health as true within its own system only", () => {
    const rows = compareRows(columns(["us", "ca"]), ctx, manifest);
    for (const id of ["reporting", "sourcing", "source_checks"]) expect(rows.find((r) => r.id === id)!.basis).toBe("within");
    const sourcing = rows.find((r) => r.id === "sourcing")!;
    for (const c of sourcing.cells) expect(c.text).not.toMatch(/%/);
  });
});

describe("laneBuckets", () => {
  it("counts by bucket, keeps zeros, and never drops an unknown state", () => {
    expect(laneBuckets({ universe_searched: 1, declared_query_set_run: 2, legacy: 1 })).toEqual([
      { label: "declared complete", n: 3 }, { label: "partial", n: 0 }, { label: "not started", n: 0 },
      { label: "stopped by search limit", n: 0 }, { label: "source unavailable", n: 0 },
      { label: "logged under the earlier format", n: 1 },
    ]);
    expect(laneBuckets(JSON.parse('{"__proto__": 3}')).map((b) => b.n)).toEqual([0, 0, 0, 0, 0, 3]);
  });
});

describe("compareBriefLines", () => {
  it("carries title, systems, build date, year, source and every caveat", () => {
    const cols = columns(["us", "ca", "sa"]);
    const b = compareBriefLines(cols, compareRows(cols, ctx, manifest), ctx, manifest.build_time);
    expect(b.title).toContain("United States, Canada, Saudi Arabia");
    expect(b.names).toEqual(["United States", "Canada", "Saudi Arabia"]);
    expect(b.sub).toMatch(/^Built \d{1,2} \w{3} \d{4}\./);
    expect(b.sub).toContain(String(ctx.comparison_year));
    expect(b.sub).toContain(ctx.source.name);
    expect(b.sub).toContain("never ranked");
    const foot = b.foot.join(" ");
    expect(foot).toContain("Research coverage differs by system");
    expect(foot).toContain("No index is not a zero.");
    expect(b.foot).toContain(EXPORT_NOT_COMPARABLE);
    expect(EXPORT_NOT_COMPARABLE).toBe("Not comparable: event counts; this is context and research state only.");
    // The context rows travel with the page's "a larger figure is not more important" caveat.
    expect(b.foot).toContain(EXPORT_CONTEXT_CAVEAT);
    expect(EXPORT_CONTEXT_CAVEAT).toMatch(/not a more important or more disrupted country/);
    // No context loaded, no context rows, so no context caveat either.
    expect(compareBriefLines(cols, compareRows(cols, null, manifest), null, manifest.build_time).foot)
      .not.toContain(EXPORT_CONTEXT_CAVEAT);
  });

  it("draws research state and context rows only, with no within-system row", () => {
    const cols = columns(["us", "ru"]);
    const b = compareBriefLines(cols, compareRows(cols, ctx, manifest), ctx, manifest.build_time);
    expect(b.rows.map((r) => r.label.join(" ")).join(" ")).not.toMatch(/sourced|Reporting environment|last checked/);
    expect(b.rows.every((r) => r.basis !== "within")).toBe(true);
    for (const r of b.rows) expect(r.cells).toHaveLength(2);
    // A national row keeps its unit and year, on its own line.
    const total = b.rows.find((r) => r.basis === "context")!;
    expect(total.label[1]).toMatch(/^\(quadrillion Btu, \d{4}\)$/);
    expect(b.groupTitles.context).toContain(String(ctx.comparison_year));
    expect(b.rows.flatMap((r) => r.cells.flat()).join(" ")).not.toContain(String(manifest.systems.find((s) => s.id === "ru")!.headline!.value));
  });

  it("says when national context is missing rather than leaving it out silently", () => {
    const cols = columns(["us", "ca"]);
    const b = compareBriefLines(cols, compareRows(cols, null, manifest, true), null, manifest.build_time);
    expect(b.sub).toContain("National context could not be loaded");
    expect(compareFilename(cols, manifest.build_time)).toMatch(/^energy-systems-compared-us-ca-\d{4}-\d{2}-\d{2}\.png$/);
  });
});
