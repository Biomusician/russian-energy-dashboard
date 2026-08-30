import { describe, it, expect, vi, afterEach } from "vitest";
import { schemaCompatibility, grabOptional, SUPPORTED_SCHEMA, addDays, fmtDelta } from "./data";

// §13-16 trend windows: addDays underpins every trailing-window computation and must handle
// month/year boundaries and a non-leap February, and must never throw on an empty date (which
// a deep link with a non-default activity window can present before the bundle has loaded).
describe("addDays", () => {
  it("subtracts a 30-day window across a month boundary", () => {
    expect(addDays("2026-08-28", -30)).toBe("2026-07-29");
  });
  it("subtracts a 90-day window across three months", () => {
    expect(addDays("2026-08-28", -90)).toBe("2026-05-30");
  });
  it("crosses a year boundary backwards", () => {
    expect(addDays("2026-01-01", -1)).toBe("2025-12-31");
  });
  it("handles a non-leap February (2026 is not a leap year)", () => {
    expect(addDays("2026-03-01", -1)).toBe("2026-02-28");
  });
  it("is identity for a zero delta", () => {
    expect(addDays("2026-08-28", 0)).toBe("2026-08-28");
  });
  it("passes an empty/malformed date through rather than throwing", () => {
    expect(addDays("", -30)).toBe("");
    expect(addDays("not-a-date", -30)).toBe("not-a-date");
  });
});

// §14-15/§18-19 change views use a real minus sign so a negative delta never reads as a range.
describe("fmtDelta", () => {
  it("prefixes a positive with +", () => expect(fmtDelta(1.21)).toBe("+1.21"));
  it("prefixes a negative with a real minus (U+2212)", () => expect(fmtDelta(-0.69)).toBe("−0.69"));
  it("marks an exact zero with ±", () => expect(fmtDelta(0)).toBe("±0.00"));
  it("respects the digits argument", () => expect(fmtDelta(-4.783, 1)).toBe("−4.8"));
});

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
