import { describe, expect, it } from "vitest";
import { fillFitted } from "./canvasText";

/** A canvas context whose glyphs are as wide as the given factor of the font size: a wide
 *  fallback font (the Linux CI case) is a larger factor. */
function fakeContext(widthFactor: number) {
  const drawn: { text: string; width: number; font: string }[] = [];
  const c = {
    font: "600 30px Inter, system-ui, sans-serif",
    measureText(t: string) {
      const px = Number(/(\d+(?:\.\d+)?)px/.exec(this.font)![1]);
      return { width: t.length * px * widthFactor };
    },
    fillText(t: string) {
      drawn.push({ text: t, width: this.measureText(t).width, font: this.font });
    },
  };
  return { c: c as unknown as CanvasRenderingContext2D, drawn };
}

describe("export text fitting", () => {
  const line = "National context only: no facilities, no routes or shipping, no current status of any facility.";

  it("draws a line that fits at its designed size", () => {
    const { c, drawn } = fakeContext(0.1);
    fillFitted(c, line, 24, 10, 1552);
    expect(drawn[0].font).toContain("30px");
  });

  it("shrinks a line that would overflow instead of cutting it, and restores the font", () => {
    const { c, drawn } = fakeContext(0.9);
    fillFitted(c, line, 24, 10, 1552);
    expect(drawn[0].text).toBe(line);
    expect(drawn[0].width).toBeLessThanOrEqual(1552);
    expect(drawn[0].font).not.toContain("30px");
    expect(c.font).toBe("600 30px Inter, system-ui, sans-serif");
  });
});
