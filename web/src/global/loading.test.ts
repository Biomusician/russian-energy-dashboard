import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  dataQualityProblems, forgetLoads, geometryProblems, groupContextProblems, loadCountry, loadManifest, manifestProblems,
  once, recentProblems, sanitizeManifest, shapeProblems, type Manifest,
} from "./manifest";

// Iteration 21: one request per file per page, and every file a view reads unguarded is validated.

const DATA = new URL("../../public/data/", import.meta.url);
const read = (p: string) => JSON.parse(readFileSync(fileURLToPath(new URL(p, DATA)), "utf-8"));
const manifest = read("global/manifest.json") as Manifest;
const rootOf = (r: string) => r.replace(/^.*?systems\//, "systems/");

afterEach(() => {
  forgetLoads();
  vi.unstubAllGlobals();
});

function stubFetch(files: Record<string, unknown>) {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    const path = String(url).replace(/^.*?data\//, "");
    calls.push(path);
    if (!(path in files)) return { ok: false, status: 404, json: async () => null };
    return { ok: true, status: 200, json: async () => structuredClone(files[path]) };
  }));
  return calls;
}

describe("published payloads pass every load-time check", () => {
  it("the manifest", () => {
    expect(manifestProblems(manifest)).toEqual([]);
    expect(sanitizeManifest(manifest)).toEqual(manifest);
  });
  const countries = manifest.systems.filter((s) => s.kind === "country");
  it("lists country systems", () => expect(countries.length).toBeGreaterThan(0));
  for (const s of countries) {
    it(`${s.id}: system, events and regions`, () => {
      const root = rootOf(s.root);
      expect(shapeProblems(read(`${root}/system.json`), read(`${root}/events.json`), read(`${root}/regions.geojson`))).toEqual([]);
    });
  }
  it("every regional context file", () => {
    const paths = Object.values(manifest.groups ?? {}).map((g) => g.context).filter((c): c is string => !!c);
    expect(paths.length).toBeGreaterThan(0);
    for (const p of paths) expect(groupContextProblems(read(p))).toEqual([]);
  });
  it("recent evidence, data quality and the world map", () => {
    expect(recentProblems(read("global/recent_evidence.json"))).toEqual([]);
    expect(dataQualityProblems(read("global/data_quality.json"))).toEqual([]);
    expect(geometryProblems(read("global/world.geojson"))).toEqual([]);
  });
});

describe("malformed payloads are named", () => {
  it("a manifest without systems or selection is refused", () => {
    expect(manifestProblems({ ...manifest, systems: "x" })).toContain("systems is not a list");
    expect(manifestProblems({ ...manifest, selection: undefined })).toContain("selection is missing");
    expect(manifestProblems({ ...manifest, systems: [{ id: "x" }] }).length).toBe(1);
    expect(manifestProblems(null).length).toBeGreaterThan(2);
  });
  it("a malformed optional manifest part is dropped, never invented", () => {
    const m = sanitizeManifest({ ...manifest, corpus: "x" as never, groups: { a: { label: 1 } } as never,
      systems: manifest.systems.map((s, i) => (i === 0 ? { ...s, aliases: "x" as never, bounds: [1] as never } : s)) });
    expect(m.corpus).toBeUndefined();
    expect(m.groups).toEqual({});
    expect(m.systems[0].aliases).toBeUndefined();
    expect(m.systems[0].bounds).toBeUndefined();
    expect(m.systems.length).toBe(manifest.systems.length);
  });
  it("a country page's nested lists and boxes", () => {
    const sys = read("systems/us/system.json");
    const ev = read("systems/us/events.json");
    expect(shapeProblems({ ...sys, profile: { metrics: "x" } }, ev)).toEqual(["profile.metrics is not a list"]);
    expect(shapeProblems({ ...sys, geography: { ...sys.geography, bounds: null, view_bounds: "x" } }, ev)).toEqual(["geography.bounds is not a box"]);
    expect(shapeProblems({ ...sys, inclusion_threshold: { rule: "x" } }, ev)).toEqual(["inclusion_threshold.clauses is missing"]);
    expect(shapeProblems({ ...sys, citation_quality: { languages: {} } }, ev)).toEqual(["citation_quality is malformed"]);
    expect(shapeProblems({ ...sys, research_log: { passes: [{}] } }, ev)).toEqual(["a research pass lacks its date, kind or window, or has a lane without an id", "a research pass lacks its outcome"]);
    expect(shapeProblems(sys, ev, { features: [null] })).toEqual(["a region feature is not an object"]);
  });
  it("a regional context, a recent list, a data-quality summary and map geometry", () => {
    const g = read("global/gulf.json");
    expect(groupContextProblems({ ...g, systems: [{ ...g.systems[0], lane_states: undefined }] }))
      .toEqual(["a system lacks its id, values, lane states or languages"]);
    expect(groupContextProblems({ ...g, memberships: {} })).toEqual(["memberships is missing"]);
    expect(groupContextProblems({ ...g, recent: { episodes: [{}] } })).toEqual(["recent is malformed"]);
    expect(groupContextProblems("<html>").length).toBeGreaterThan(3);
    expect(recentProblems({ episodes: [{ system_id: "x", first_date: "2025", classes: [], causes: [], members: "x" }] })).toHaveLength(1);
    expect(dataQualityProblems({ ...read("global/data_quality.json"), systems: [{ name: "x" }] })).toHaveLength(1);
    expect(geometryProblems({ type: "FeatureCollection" })).toEqual(["features is not a list"]);
  });
});

describe("one request per file per page", () => {
  it("two callers share one request; a failure is not kept", async () => {
    let n = 0;
    const load = () => { n += 1; return n === 1 ? Promise.reject(new Error("first fails")) : Promise.resolve(n); };
    await expect(once("k", load)).rejects.toThrow("first fails");
    const [a, b] = await Promise.all([once("k", load), once("k", load)]);
    expect([a, b, n]).toEqual([2, 2, 2]);
  });

  it("the manifest is fetched once however many views ask", async () => {
    const calls = stubFetch({ "global/manifest.json": manifest });
    await Promise.all([loadManifest(), loadManifest()]);
    await loadManifest();
    expect(calls).toEqual(["global/manifest.json"]);
  });

  it("a malformed manifest is refused, and the next call fetches again", async () => {
    const calls = stubFetch({ "global/manifest.json": { systems: "x" } });
    await expect(loadManifest()).rejects.toThrow(/manifest malformed/);
    await expect(loadManifest()).rejects.toThrow(/manifest malformed/);
    expect(calls).toHaveLength(2);
  });

  it("a country is fetched once, and a broken one is retried rather than kept", async () => {
    const entry = manifest.systems.find((s) => s.id === "us")!;
    const root = rootOf(entry.root);
    const files = { [`${root}/system.json`]: read(`${root}/system.json`), [`${root}/events.json`]: read(`${root}/events.json`),
                    [`${root}/regions.geojson`]: read(`${root}/regions.geojson`) };
    const calls = stubFetch(files);
    const [a, b] = await Promise.all([loadCountry(entry), loadCountry(entry)]);
    expect(a).toBe(b);
    expect(calls).toHaveLength(3);

    forgetLoads();
    const broken = stubFetch({ ...files, [`${root}/events.json`]: { events: "x" } });
    await expect(loadCountry(entry)).rejects.toThrow(/malformed payload/);
    await expect(loadCountry(entry)).rejects.toThrow(/malformed payload/);
    expect(broken).toHaveLength(6);
  });
});
