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

// §7 of the release gate: a hand-mangled or stale link must sanitise/default, never crash and
// never produce a view that misrepresents what it is showing.
describe("decodeDeepLink — hostile and malformed input", () => {
  it("survives junk without throwing and yields an empty (all-default) link", () => {
    for (const q of [
      "", "?", "&&&", "m=", "a=", "d=", "r=", "cls=", "ly=", "cam=", "cmp=",
      "m=%%%", "cam=,,", "cam=1", "cam=1,2", "d=2026-13-45x", "a=999", "%E0%A4%A",
      "__proto__=x", "cls=__proto__", "ly=" + "x".repeat(5000),
    ]) {
      expect(() => decodeDeepLink(q)).not.toThrow();
    }
    expect(decodeDeepLink("m=%%%&a=999&d=nope").metric).toBeUndefined();
  });

  it("rejects an out-of-vocabulary metric and activity window", () => {
    expect(decodeDeepLink("m=esdi_delta_7d").metric).toBeUndefined();
    expect(decodeDeepLink("a=45").activityWindow).toBeUndefined();
  });

  it("rejects a structurally wrong date but keeps a well-formed one", () => {
    expect(decodeDeepLink("d=28-08-2026").date).toBeUndefined();
    expect(decodeDeepLink("d=2026-08-28").date).toBe("2026-08-28");
  });

  it("clamps an absurd zoom into the map's real range instead of blanking the map", () => {
    expect(decodeDeepLink("cam=40,55,9999").camera!.zoom).toBe(9);
    expect(decodeDeepLink("cam=40,55,-50").camera!.zoom).toBe(0);
  });

  it("clamps an off-globe camera centre", () => {
    const c = decodeDeepLink("cam=999,-999,4").camera!;
    expect(c.lng).toBe(180);
    expect(c.lat).toBe(-85);
  });

  it("drops a camera that is not numeric at all", () => {
    expect(decodeDeepLink("cam=north,west,close").camera).toBeUndefined();
  });

  it("de-duplicates a repeated compare list before capping", () => {
    expect(decodeDeepLink("cmp=RU-ROS,RU-ROS,RU-ROS,RU-KDA").compare).toEqual(["RU-ROS", "RU-KDA"]);
  });

  it("trims whitespace in a compare list", () => {
    expect(decodeDeepLink("cmp=%20RU-ROS%20,%20RU-KDA%20").compare).toEqual(["RU-ROS", "RU-KDA"]);
  });

  it("keeps unknown filter keys as strings for the app to intersect away", () => {
    // Validation against the live taxonomy happens in App (it owns the key universe); the
    // decoder must not silently discard, or a legitimate key could vanish on a taxonomy change.
    expect(decodeDeepLink("cls=refinery,not_a_class").classes).toEqual(["refinery", "not_a_class"]);
  });

  it("never encodes a coordinate for a selected asset (scope)", () => {
    // The link vocabulary has no asset-position key at all; only region code + camera exist.
    const keys = [...new URLSearchParams(
      "m=d30&a=90&r=RU-ROS&d=2026-06-01&cls=refinery&ly=lines&cam=42,49,4&cmp=RU-KDA",
    ).keys()];
    expect(keys).not.toContain("asset");
    expect(keys).not.toContain("lat");
    expect(keys).not.toContain("lon");
  });
});
