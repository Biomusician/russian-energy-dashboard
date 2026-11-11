import { describe, expect, it } from "vitest";
import { fillFor, scaleFor } from "./countryScale";

describe("scaleFor", () => {
  it("builds classes from the country's own range, top class always the hottest", () => {
    expect(scaleFor([0, 1, 2])).toEqual({
      thresholds: [1, 2], colors: ["#a8871f", "#c26326"], labels: ["1", "2"] });
    const six = scaleFor([0, 6, 3, 1]);
    expect(six.thresholds).toEqual([1, 2, 4, 5]);
    expect(six.labels).toEqual(["1", "2–3", "4", "5–6"]);
    expect(scaleFor([12]).labels.at(-1)).toBe("10–12");
  });

  it("has no positive class when nothing was recorded", () => {
    expect(scaleFor([0, 0]).thresholds).toEqual([]);
    expect(scaleFor([]).thresholds).toEqual([]);
  });

  it("keeps thresholds strictly increasing for every maximum", () => {
    for (let max = 1; max < 60; max++) {
      const t = scaleFor([max]).thresholds;
      t.forEach((v, i) => { if (i) expect(v).toBeGreaterThan(t[i - 1]); });
      expect(t[0]).toBe(1);
    }
  });

  it("still draws a country with no record: a step with no stops is not an expression", () => {
    const f = fillFor(scaleFor([0, 0])) as unknown[];
    expect(JSON.stringify(f)).not.toContain('"step"');
    expect(f[0]).toBe("case");
    expect(f.at(-1)).toBe("#16202a");
    expect(JSON.stringify(f)).toContain('"#2b2b33"');
  });

  it("draws disputed units apart from zero", () => {
    const f = JSON.stringify(fillFor(scaleFor([3])));
    expect(f).toContain('["==",["get","recorded_events"],null],"#2b2b33"');
  });
});
