import { describe, it, expect } from "vitest";
import assets from "../public/data/assets.json";
import incidents from "../public/data/incidents.json";

/** Shared-administrative-centroid representative selection.
 *
 *  Regression guard for a defect the UX red-team caught: 14 of 35 curated region-precision assets
 *  share a centroid with another, and the representative that actually gets drawn was originally
 *  fixed as members[0]. Because the real groups are CLASS-MIXED, that meant
 *    - Novoshakhtinsk Refinery was drawn as a coal-terminal glyph (Port of Azov was members[0]),
 *    - Orsk Refinery was drawn as a gas-processing glyph (Orenburg GPP was members[0]),
 *  and under a "refineries only" filter both — the two most recently struck refineries — vanished
 *  from the map entirely while their cards still promised a marker.
 *
 *  These tests mirror MapPanel's selection rule against the real shipped data. */

type Asset = {
  asset_id: string; name: string | null; asset_class: string; precision?: string | null;
  lon: number; lat: number; capacity_mw?: number | null; capacity_mtpa?: number | null;
  capacity_bcm_y?: number | null; voltage_kv?: number | null;
};

const ASSETS = assets as Asset[];
const STRUCK = new Set((incidents as { asset_id?: string }[]).map((i) => i.asset_id).filter(Boolean) as string[]);

// Must stay in step with MapPanel.CLASS_PRIO / assetPrio.
const CLASS_PRIO: Record<string, number> = {
  refinery: 0, gas_processing: 1, lng_terminal: 1, oil_terminal: 2,
  power_plant_nuclear: 2, power_plant_hydro: 3, power_plant_thermal: 3,
  coal_terminal: 4, coal_mine: 4, interconnector: 4, power_plant_other: 5, substation: 7,
};
function prio(a: Asset): number {
  const base = (CLASS_PRIO[a.asset_class] ?? 6) * 1000;
  const cap = Math.min(400, (a.capacity_mw ?? 0) / 12 + (a.capacity_mtpa ?? 0) * 25 + (a.capacity_bcm_y ?? 0) * 20);
  const v = Math.min(300, (a.voltage_kv ?? 0) / 2);
  return Math.round(base - cap - v - (STRUCK.has(a.asset_id) ? 600 : 0) - (a.precision === "region" ? 250 : 0));
}

function groups(): Asset[][] {
  const byPoint = new Map<string, Asset[]>();
  for (const a of ASSETS) {
    if (a.precision !== "region") continue;
    const k = `${a.lon},${a.lat}`;
    (byPoint.get(k) ?? byPoint.set(k, []).get(k)!).push(a);
  }
  return [...byPoint.values()];
}

/** The rule MapPanel applies: most salient member that passes the active class filter. */
function representative(members: Asset[], active: Set<string>): Asset | null {
  const eligible = members.filter((a) => active.has(a.asset_class));
  if (!eligible.length) return null;
  return eligible.reduce((best, a) => (prio(a) < prio(best) ? a : best));
}

const ALL_CLASSES = new Set(ASSETS.map((a) => a.asset_class));

describe("shared-centroid representative selection", () => {
  it("the shipped data really does contain class-mixed collision groups", () => {
    // If this ever becomes empty the hazard is gone, but so is the reason for these tests —
    // fail loudly rather than pass vacuously.
    const mixed = groups().filter((g) => g.length > 1 && new Set(g.map((a) => a.asset_class)).size > 1);
    expect(mixed.length).toBeGreaterThan(0);
  });

  it("never leaves a struck asset unrepresented when its own class is enabled", () => {
    for (const g of groups()) {
      for (const a of g) {
        if (!STRUCK.has(a.asset_id)) continue;
        const rep = representative(g, new Set([a.asset_class]));
        expect(rep, `${a.name}: no marker drawn with its own class filtered on`).not.toBeNull();
        expect(rep!.asset_class).toBe(a.asset_class);
      }
    }
  });

  it("draws the two struck refineries as REFINERIES, not as their co-located neighbours", () => {
    const struckRefineries = ASSETS.filter(
      (a) => a.asset_class === "refinery" && a.precision === "region" && STRUCK.has(a.asset_id),
    );
    expect(struckRefineries.length).toBeGreaterThan(0);
    for (const r of struckRefineries) {
      const g = groups().find((m) => m.some((a) => a.asset_id === r.asset_id))!;
      // Unfiltered, the refinery outranks a coal terminal / gas plant on the same point.
      expect(representative(g, ALL_CLASSES)!.asset_class).toBe("refinery");
      // And filtered to refineries it is still the one drawn.
      expect(representative(g, new Set(["refinery"]))!.asset_id).toBe(r.asset_id);
    }
  });

  it("yields no representative only when every member is filtered out", () => {
    for (const g of groups()) {
      const none = representative(g, new Set(["__nothing__"]));
      expect(none).toBeNull();
      expect(representative(g, ALL_CLASSES)).not.toBeNull();
    }
  });

  it("picks a member of the group, never a synthesised position", () => {
    for (const g of groups()) {
      const rep = representative(g, ALL_CLASSES)!;
      expect(g).toContain(rep);
      // Members are never displaced: every one keeps the shared centroid exactly.
      for (const a of g) {
        expect(a.lon).toBe(rep.lon);
        expect(a.lat).toBe(rep.lat);
      }
    }
  });
});
