import { describe, it, expect } from "vitest";
import { encodeDeepLink, decodeDeepLink } from "./urlState";

// §20-22 shareable state. The contract: an untouched dashboard produces a CLEAN url, every
// non-default field round-trips, and a malformed link degrades to defaults instead of throwing.
const ALL_CLASSES = ["refinery", "oil_terminal", "substation", "power_plant_thermal"];
const ALL_CAUSES = ["kinetic_strike", "sabotage"];
const ALL_CONF = ["confirmed", "probable", "possible", "unverified"];

function baseView(over: Partial<Parameters<typeof encodeDeepLink>[0]> = {}) {
  return {
    metric: "esdi" as const,
    activityWindow: "cumulative" as const,
    date: "2026-08-28",
    latestDate: "2026-08-28",
    selected: null,
    classes: new Set(ALL_CLASSES),
    causes: new Set(ALL_CAUSES),
    confidences: new Set(ALL_CONF),
    allClasses: ALL_CLASSES,
    allCauses: ALL_CAUSES,
    allConfidences: ALL_CONF,
    showLines: false,
    showAssets: true,
    showRivers: false,
    showGasNetwork: false,
    showOilNetwork: false,
    camera: null,
    compare: [] as string[],
    ...over,
  };
}

describe("encodeDeepLink", () => {
  it("emits an empty query for a fully-default view", () => {
    expect(encodeDeepLink(baseView())).toBe("");
  });

  it("omits the date when it equals the latest (present) date", () => {
    expect(encodeDeepLink(baseView({ date: "2026-08-28", latestDate: "2026-08-28" }))).toBe("");
  });

  it("omits filter sets that are the full universe, writes strict subsets", () => {
    const q = encodeDeepLink(baseView({ classes: new Set(["refinery", "oil_terminal"]) }));
    expect(q).toContain("cls=refinery%2Coil_terminal");
    expect(q).not.toContain("cau=");
    expect(q).not.toContain("con=");
  });

  it("encodes only the layer departures (assets default on, rest off)", () => {
    const q = new URLSearchParams(encodeDeepLink(baseView({ showLines: true, showRivers: true, showAssets: false })));
    expect(q.get("ly")).toBe("lines,noassets,rivers");
  });
});

describe("decodeDeepLink", () => {
  it("round-trips a rich view", () => {
    const view = baseView({
      metric: "esdi_delta_30d",
      activityWindow: "90d",
      date: "2026-06-01",
      latestDate: "2026-08-28",
      selected: "RU-ROS",
      classes: new Set(["refinery"]),
      confidences: new Set(["confirmed", "probable"]),
      showLines: true,
      showRivers: true,
      camera: { lng: 42.5, lat: 49, zoom: 4.2 },
      compare: ["RU-KDA", "RU-LEN"],
    });
    const decoded = decodeDeepLink(encodeDeepLink(view));
    expect(decoded.metric).toBe("esdi_delta_30d");
    expect(decoded.activityWindow).toBe("90d");
    expect(decoded.date).toBe("2026-06-01");
    expect(decoded.selected).toBe("RU-ROS");
    expect(decoded.classes).toEqual(["refinery"]);
    expect(decoded.confidences).toEqual(["confirmed", "probable"]);
    expect(decoded.showLines).toBe(true);
    expect(decoded.showRivers).toBe(true);
    expect(decoded.showAssets).toBe(true);
    expect(decoded.camera).toEqual({ lng: 42.5, lat: 49, zoom: 4.2 });
    expect(decoded.compare).toEqual(["RU-KDA", "RU-LEN"]);
  });

  it("reads noassets as assets-off", () => {
    expect(decodeDeepLink("ly=noassets").showAssets).toBe(false);
  });

  it("ignores a malformed camera and a malformed date without throwing", () => {
    const d = decodeDeepLink("cam=abc,def&d=not-a-date&m=nonsense");
    expect(d.camera).toBeUndefined();
    expect(d.date).toBeUndefined();
    expect(d.metric).toBeUndefined();
  });

  it("caps the compare list at three", () => {
    expect(decodeDeepLink("cmp=A,B,C,D,E").compare).toEqual(["A", "B", "C"]);
  });

  it("accepts a leading question mark", () => {
    expect(decodeDeepLink("?a=30").activityWindow).toBe("30d");
  });
});
