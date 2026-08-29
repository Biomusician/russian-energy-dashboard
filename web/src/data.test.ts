import { describe, it, expect, vi, afterEach } from "vitest";
import { schemaCompatibility, grabOptional, SUPPORTED_SCHEMA } from "./data";

// §27/§32 deploy-window resilience: a partially-propagated Vercel deploy may serve older
// data (or lack an optional layer) to a newer bundle. It must degrade, never white-screen.
describe("schemaCompatibility", () => {
  it("accepts an exact schema match (N data, N app)", () => {
    const r = schemaCompatibility(SUPPORTED_SCHEMA);
    expect(r.ok).toBe(true);
    expect(r.mode).toBe("exact");
  });

  it("accepts supported N-1 data (back-compat during a deploy)", () => {
    const r = schemaCompatibility(SUPPORTED_SCHEMA - 1, SUPPORTED_SCHEMA, SUPPORTED_SCHEMA - 1);
    expect(r.ok).toBe(true);
    expect(r.mode).toBe("back");
  });

  it("treats a payload with no schema_version as version 1", () => {
    const r = schemaCompatibility(undefined, 1, 1);
    expect(r.dataVersion).toBe(1);
    expect(r.ok).toBe(true);
  });

  it("still renders newer (forward) data rather than white-screening", () => {
    const r = schemaCompatibility(SUPPORTED_SCHEMA + 1);
    expect(r.mode).toBe("forward");
    expect(r.ok).toBe(true);
  });

  it("flags a genuinely unsupported (too-old) payload as not ok", () => {
    const r = schemaCompatibility(1, 5, 3);
    expect(r.mode).toBe("unsupported");
    expect(r.ok).toBe(false);
  });
});

describe("grabOptional", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns the fallback when the optional file is missing (404)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 404 }) as Response));
    const fc: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
    const out = await grabOptional("rivers.geojson", fc);
    expect(out).toBe(fc);
  });

  it("returns the fallback when fetch throws (network error mid-deploy)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new Error("network");
    }));
    const fc: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
    const out = await grabOptional("pipelines_context.geojson", fc);
    expect(out).toBe(fc);
  });

  it("returns parsed JSON when the file is present", async () => {
    const payload = { type: "FeatureCollection", features: [{ id: 1 }] };
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => payload }) as unknown as Response));
    const out = await grabOptional<unknown>("rivers.geojson", { type: "FeatureCollection", features: [] });
    expect(out).toEqual(payload);
  });
});

// §16 lazy-load: loadContextLayer fetches once and caches; a missing file degrades to empty.
describe("loadContextLayer (lazy context layers)", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("fetches a layer once, then serves it from cache", async () => {
    const { loadContextLayer } = await import("./data");
    const payload = { type: "FeatureCollection", features: [{ id: 1 }] };
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => payload }) as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);
    const a = await loadContextLayer("context_oil_network.geojson");
    const b = await loadContextLayer("context_oil_network.geojson");
    expect(a).toEqual(payload);
    expect(b).toBe(a); // same cached object
    expect(fetchMock).toHaveBeenCalledTimes(1); // cached, not refetched
  });

  it("degrades to an empty FeatureCollection when the layer is absent", async () => {
    const { loadContextLayer } = await import("./data");
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 404 }) as Response));
    const fc = await loadContextLayer("rivers.geojson");
    expect(fc.type).toBe("FeatureCollection");
    expect(fc.features).toEqual([]);
  });
});
