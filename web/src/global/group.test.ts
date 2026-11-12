import { describe, expect, it } from "vitest";
import { groupBriefLines } from "./groupExport";
import { dirFor, groupBySlug, type GroupContext, type Manifest } from "./manifest";

const manifest = {
  groups: {
    gulf_littoral: { label: "Gulf", kind: "geographic", note: "n", slug: "gulf", context: "global/gulf.json", members: ["bh", "ir"] },
    gcc: { label: "GCC", kind: "membership", note: "n", slug: null, context: null, members: ["bh"] },
  },
} as unknown as Manifest;

function ctx(): GroupContext {
  const sys = (id: string, name: string, v: number | null, gcc: boolean, opec: boolean) => ({
    system_id: id, name, a3: id.toUpperCase(), gcc_member: gcc, opec_member: opec, maturity: "research_preview" as const,
    recovery_status_withheld: true, values: { crude_production: v }, role: null, last_systematic_pass: null,
    lane_states: {}, languages_required: [], languages_executed: [], reporting_environment: "media_only",
  });
  return {
    group: "gulf_littoral", label: "Gulf", note: "n", statement: "s", not_built: "nb",
    memberships: { gcc: { label: "GCC", note: "n", members: ["bh"] }, opec: { label: "OPEC", note: "n", members: ["ir"] } },
    order: "alphabetical by name; never by any figure",
    sources: { eia: { name: "EIA", url: "https://example.org", release: "2026-10-16", attribution: null } },
    metrics: { crude_production: { label: "Crude oil production", unit: "thousand barrels per day", definition: "d", year: 2024, source_id: "eia" } },
    systems: [sys("bh", "Bahrain", 174, true, false), sys("ir", "Iran", 3947, false, true)],
    region: { crude_production: { value: 4121, world_share: 0.05, reason: null } },
  };
}

describe("groupBySlug", () => {
  it("finds a group that has a page", () => {
    expect(groupBySlug(manifest, "gulf")?.id).toBe("gulf_littoral");
  });

  it("refuses a membership, an unknown slug and an inherited key", () => {
    expect(groupBySlug(manifest, "gcc")).toBeNull();
    expect(groupBySlug(manifest, "levant")).toBeNull();
    expect(groupBySlug(manifest, "constructor")).toBeNull();
    expect(groupBySlug({} as Manifest, "gulf")).toBeNull();
  });
});

describe("the regional brief", () => {
  const lines = groupBriefLines(ctx(), "crude_production");

  it("names the metric, year and source in the image itself", () => {
    expect(lines.title).toContain("Crude oil production");
    expect(lines.title).toContain("2024");
    expect(lines.sub).toContain("EIA");
    expect(lines.sub).toContain("National annual totals");
  });

  it("lists countries in the order given, with memberships and maturity", () => {
    expect(lines.rows[0]).toMatch(/^Bahrain: /);
    expect(lines.rows[0]).toContain("GCC");
    expect(lines.rows[0]).not.toContain("OPEC");
    expect(lines.rows[1]).toContain("OPEC");
    expect(lines.rows[1]).toContain("research preview");
  });

  it("says what it is not, and carries no disruption figure", () => {
    const all = [...lines.rows, ...lines.foot].join(" ").toLowerCase();
    expect(all).toContain("no index");
    expect(all).toContain("no facilities");
    expect(all).toContain("not comparable");
    for (const word of ["records", "incidents", "attacks", "rank", "most"]) expect(all).not.toContain(word);
  });

  it("refuses to print a partial sum", () => {
    const c = ctx();
    c.region.crude_production = { value: null, world_share: null, reason: "1 of 2 members have no value" };
    expect(groupBriefLines(c, "crude_production").foot[0]).toBe("Not summed: 1 of 2 members have no value.");
  });

  it("shows a missing national value as no data, never as zero", () => {
    const c = ctx();
    c.systems[0].values.crude_production = null;
    const row = groupBriefLines(c, "crude_production").rows[0].toLowerCase();
    expect(row).toContain("no data");
    expect(row).not.toMatch(/: 0\b/);
  });
});

describe("dirFor", () => {
  it("lays Arabic, Persian and Kurdish headlines right to left", () => {
    expect(dirFor("ar")).toBe("rtl");
    expect(dirFor("fa")).toBe("rtl");
    expect(dirFor("ku")).toBe("rtl");
    expect(dirFor("en")).toBe("ltr");
    expect(dirFor(undefined)).toBe("ltr");
  });
  it("reads the whole language subtag and a script subtag", () => {
    for (const l of ["ckb", "ug", "ps", "sd", "dv", "ur", "fa-IR", "az-Arab"]) expect(dirFor(l)).toBe("rtl");
    for (const l of ["ku-Latn", "ckx", "en-GB", "zh", "hi"]) expect(dirFor(l)).toBe("ltr");
  });
});
