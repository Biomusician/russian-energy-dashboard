import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { shapeProblems } from "./manifest";

// The committed payloads, read from the web bundle the tests run against.
const DATA = new URL("../../public/data/", import.meta.url);
const read = (p: string) => JSON.parse(readFileSync(fileURLToPath(new URL(p, DATA)), "utf-8"));

describe("country payload shape check (iteration 17, error containment)", () => {
  for (const id of ["ca", "cn", "in", "sa", "us"]) {
    it(`${id}: the published payload passes`, () => {
      expect(shapeProblems(read(`systems/${id}/system.json`), read(`systems/${id}/events.json`))).toEqual([]);
    });
  }

  it("an invalid research log is refused at load, by name", () => {
    const sys = read("systems/us/system.json");
    const ev = read("systems/us/events.json");
    expect(shapeProblems({ ...sys, research_log: { passes: "corrupt" } }, ev)).toEqual(["research_log.passes is not a list"]);
    expect(shapeProblems({ ...sys, research_log: undefined }, ev)).toEqual(["research_log.passes is not a list"]);
  });

  it("every field the view reads unguarded is named when missing", () => {
    const sys = read("systems/us/system.json");
    const ev = read("systems/us/events.json");
    const reg = read("systems/us/regions.geojson");
    expect(shapeProblems(sys, ev, reg)).toEqual([]);
    for (const k of ["inclusion_threshold", "episode_bases"]) {
      expect(shapeProblems({ ...sys, [k]: undefined }, ev)).toEqual([`${k} is missing`]);
    }
    expect(shapeProblems({ ...sys, geography: { ...sys.geography, rulings: "x" } }, ev)).toEqual(["geography.rulings is not a list"]);
    expect(shapeProblems({ ...sys, event_summary: { ...sys.event_summary, recovery_kinds: undefined } }, ev))
      .toEqual(["event_summary.recovery_kinds is missing"]);
    const broken = { ...ev, events: [{ ...ev.events[0], review: undefined }, ...ev.events.slice(1)] };
    expect(shapeProblems(sys, broken)).toEqual(["an event lacks its review, sources or recovery"]);
    expect(shapeProblems(sys, ev, { type: "FeatureCollection" })).toEqual(["regions.features is not a list"]);
  });

  it("corrupt or empty payloads are refused, never half-rendered", () => {
    expect(shapeProblems(null, null).length).toBeGreaterThan(5);
    expect(shapeProblems("garbage", [])).toContain("events is not a list");
  });
});
