import { describe, it, expect } from "vitest";
import { ICON_SHAPES, ICON_CLASS_ORDER, hasIcon, iconSVG, iconImageId, unknownPointClasses } from "./icons";
import taxonomy from "../public/data/taxonomy.json";
import assets from "../public/data/assets.json";

/** §8 of the release gate. The icon registry is the single source of truth for symbology; these
 *  tests are what stop it silently regressing to an undifferentiated dot. */

const POINT_CLASSES: string[] = [...new Set((assets as { asset_class: string }[]).map((a) => a.asset_class))];

describe("icon coverage", () => {
  it("gives every class the built dataset renders as a POINT a deliberate shape", () => {
    // If this fails, a new taxonomy class started producing point assets without a designed
    // glyph — draw one in ICON_SHAPES rather than letting it inherit the fallback diamond.
    expect(unknownPointClasses(POINT_CLASSES)).toEqual([]);
  });

  it("gives every taxonomy class a shape, including the line-only ones used by the legend", () => {
    const missing = Object.keys((taxonomy as { asset_classes: Record<string, string> }).asset_classes)
      .filter((k) => !hasIcon(k));
    expect(missing).toEqual([]);
  });

  it("lists every shape in the legend order, and nothing extra", () => {
    expect([...ICON_CLASS_ORDER].sort()).toEqual(Object.keys(ICON_SHAPES).sort());
  });
});

describe("unknown-class fallback", () => {
  it("flags an unrecognised class rather than absorbing it silently", () => {
    expect(unknownPointClasses(["refinery", "fusion_reactor"])).toEqual(["fusion_reactor"]);
  });

  it("routes an unknown class to a distinct image id, never a real class's icon", () => {
    const unknown = iconImageId("fusion_reactor", false);
    expect(unknown).toBe("asset-unknown");
    expect(unknown).not.toBe(iconImageId("refinery", false));
  });

  it("draws a visibly hollow fallback glyph, not an invisible or generic filled dot", () => {
    const svg = iconSVG("fusion_reactor");
    expect(svg).toContain("<svg");
    expect(svg).toContain('fill="none"'); // hollow diamond outline
    expect(svg).not.toBe(iconSVG("refinery"));
  });
});

describe("precision and multiplicity variants", () => {
  it("keeps mapped, region-placed, and stacked ids distinct", () => {
    const ids = new Set([
      iconImageId("lng_terminal", false, false),
      iconImageId("lng_terminal", true, false),
      iconImageId("lng_terminal", false, true),
      iconImageId("lng_terminal", true, true),
    ]);
    expect(ids.size).toBe(4);
  });

  it("adds a dashed frame ONLY for administrative-region placement", () => {
    expect(iconSVG("refinery", { region: true })).toContain("stroke-dasharray");
    expect(iconSVG("refinery", { region: false })).not.toContain("stroke-dasharray");
  });

  it("adds the stacked backplate only when several assets share a centroid", () => {
    expect(iconSVG("lng_terminal", { stacked: true })).toContain("<rect");
    expect(iconSVG("lng_terminal", { stacked: false })).not.toContain("<rect");
  });

  it("produces a self-contained SVG with no external reference (zero-network invariant)", () => {
    for (const cls of ICON_CLASS_ORDER) {
      const svg = iconSVG(cls, { region: true, stacked: true });
      expect(svg).not.toMatch(/https?:\/\/(?!www\.w3\.org)/); // only the XML namespace may appear
      expect(svg).not.toContain("<image");
      expect(svg).not.toContain("url(");
    }
  });
});
