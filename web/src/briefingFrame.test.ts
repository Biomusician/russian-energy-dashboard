/** What the EXPORTED IMAGE says (iteration 11 P10).
 *
 *  These exist because of a defect that shipped through P8 and was caught only in the release
 *  gate: the exporter wrote the raw MapLibre canvas to a file, so the caveat, scope note, Crimea
 *  note and sources were on the reader's screen and NOT in the PNG. The suite at the time was
 *  green, because every briefing test asserted on the pure context builder — the object feeding
 *  the overlay — and nothing asserted on what reached the image.
 *
 *  So these tests drive the real compositor against a recording 2D context and assert on the
 *  text actually drawn. A future refactor that stops painting the caveat fails here.
 */

import { describe, expect, it } from "vitest";
import { drawBriefingFrame } from "./briefingFrame";
import { DEFAULT_OPTIONS, type BriefingContext, type BriefingOptions } from "./briefing";

/** Records every string drawn, and enough geometry to tell a footer from a header. */
function recorder() {
  const texts: { text: string; x: number; y: number }[] = [];
  const rects: { x: number; y: number; w: number; h: number }[] = [];
  const ctx = {
    canvas: null as unknown,
    font: "",
    fillStyle: "",
    textAlign: "left",
    textBaseline: "alphabetic",
    drawImage: () => {},
    fillRect: (x: number, y: number, w: number, h: number) => rects.push({ x, y, w, h }),
    fillText: (text: string, x: number, y: number) => texts.push({ text, x, y }),
    // Proportional enough that wrapping actually happens at realistic widths.
    measureText: (t: string) => ({ width: t.length * 8 }),
    createLinearGradient: () => ({ addColorStop: () => {} }),
  };
  return { ctx, texts, rects };
}

function fakeCanvas(width = 1920, height = 1080) {
  const r = recorder();
  const canvas = { width, height, getContext: () => r.ctx } as unknown as HTMLCanvasElement;
  return { canvas, ...r };
}

/** drawBriefingFrame creates its own output canvas via document.createElement.
 *
 *  The suite runs in the node environment, so there may be no document at all — the stub stands
 *  in for one rather than pulling in jsdom for a single factory call. */
function install(width = 1920, height = 1080) {
  const made = fakeCanvas(width, height);
  const g = globalThis as unknown as { document?: { createElement: (t: string) => unknown } };
  const had = g.document;
  g.document = {
    createElement: (tag: string) => (tag === "canvas" ? made.canvas : {}),
  };
  return { ...made, restore: () => { g.document = had; } };
}

const CTX: BriefingContext = {
  title: "Energy Disruption Monitor",
  metricId: "esdi",
  metricLabel: "Energy System Disruption Exposure Index",
  metricValue: "16.69",
  asOf: "2026-09-03",
  analyticalDate: null,
  exportedAt: "2026-09-03",
  caveat: "Modelled disruption exposure — capacity AT disrupted sites, not measured capacity "
    + "loss. Transmission disruption burden is an event-burden proxy, not percent of grid offline.",
  scopeNote: "Monitored area: Belarus, western Russia and the Siberian Federal District, plus "
    + "occupied Crimea. Aggregated to administrative region.",
  crimeaNote: "Crimea is internationally recognised as part of Ukraine and is shown separately; "
    + "its inclusion in the Monitored-Area index is an analytical choice.",
  sourceFooter: "Public open sources only. Boundaries: Natural Earth.",
  comparison: null,
  episode: null,
  buildDelta: null,
  selection: null,
  provenance: {},
};

function draw(ctx: BriefingContext = CTX, options: BriefingOptions = DEFAULT_OPTIONS,
              w = 1920, h = 1080) {
  const h2 = install(w, h);
  try {
    drawBriefingFrame(h2.canvas, ctx, options);
    return { drawn: h2.texts.map((t) => t.text).join(" "), texts: h2.texts, rects: h2.rects, h, w };
  } finally {
    h2.restore();
  }
}

describe("the exported image carries its own context", () => {
  it("paints the caveat into the picture, not just the overlay", () => {
    // THE REGRESSION. A PNG with no caveat is a coloured map of Russia that a reader will take
    // for measured damage.
    expect(draw().drawn).toContain("not measured capacity loss");
  });

  it("paints the transmission proxy caveat when it applies", () => {
    expect(draw().drawn).toContain("event-burden proxy");
  });

  it("paints the scope note and the Crimea sovereignty note", () => {
    const d = draw().drawn;
    expect(d).toContain("Belarus, western Russia");
    expect(d).toContain("internationally recognised as part of Ukraine");
  });

  it("paints the metric, its value and the as-of date", () => {
    const d = draw().drawn;
    expect(d).toContain("Energy System Disruption Exposure Index");
    expect(d).toContain("16.69");
    expect(d).toContain("3 Sep 2026");
  });

  it("paints the source footer", () => {
    expect(draw().drawn).toContain("Public open sources only");
  });

  it("distinguishes an analytical date from the data as-of date in the image", () => {
    const d = draw({ ...CTX, analyticalDate: "2026-08-27" }).drawn;
    expect(d).toContain("analytical date");
    expect(d).toContain("data as of");
  });

  it("keeps the caveat in the lower half, where a caption belongs", () => {
    const { texts, h } = draw();
    const caveat = texts.find((t) => t.text.includes("not measured capacity loss"));
    expect(caveat).toBeTruthy();
    expect(caveat!.y).toBeGreaterThan(h * 0.5);
  });
});

describe("optional annotation actually changes the image", () => {
  it("drops the scope and Crimea notes when the reader turns them off", () => {
    // The Include toggles previously affected only the on-screen overlay: the PNG ignored them.
    const off = draw(CTX, { ...DEFAULT_OPTIONS, scopeNote: false }).drawn;
    expect(off).not.toContain("Belarus, western Russia");
    expect(off).not.toContain("internationally recognised as part of Ukraine");
  });

  it("drops the source footer when turned off", () => {
    expect(draw(CTX, { ...DEFAULT_OPTIONS, sourceFooter: false }).drawn)
      .not.toContain("Public open sources only");
  });

  it("never drops the caveat, whatever is switched off", () => {
    const none: BriefingOptions = {
      title: false, selectionLabel: false, scopeNote: false, legend: false,
      sourceFooter: false, comparisonSummary: false,
    };
    expect(draw(CTX, none).drawn).toContain("not measured capacity loss");
  });
});

describe("comparison and episode framing reach the image", () => {
  it("paints both dates, both values and the delta", () => {
    const d = draw({
      ...CTX,
      comparison: {
        aRequested: "2025-08-30", aResolved: "2025-08-30",
        bRequested: "2026-09-03", bResolved: "2026-09-03",
        aValue: "4.34", bValue: "16.69", delta: "+12.35",
        resolvedNote: null, mode: "delta",
      },
    }).drawn;
    expect(d).toContain("4.34");
    expect(d).toContain("16.69");
    expect(d).toContain("+12.35");
    expect(d).toContain("30 Aug 2025");
  });

  it("paints the recovery episode's family and outcome, not just its name", () => {
    const d = draw({
      ...CTX,
      episode: {
        facility: "Orsk refinery", assetClass: "refinery", disruptionDate: "2026-08-11",
        family: "estimate", familyLabel: "estimate",
        outcome: "projected repair horizon, no observed restoration", durationDays: null,
      },
    }).drawn;
    expect(d).toContain("Orsk refinery");
    expect(d).toContain("estimate");
    expect(d).toContain("projected repair horizon");
  });

  it("paints a build delta only when one is present", () => {
    expect(draw().drawn).not.toContain("Since last build");
    const d = draw({
      ...CTX,
      buildDelta: { previousAsOf: "2026-09-02", currentAsOf: "2026-09-03", delta: "−0.17" },
    }).drawn;
    expect(d).toContain("Since last build");
  });
});

describe("the frame scales with the image", () => {
  it("keeps the caveat inside a 2560-wide export", () => {
    const { texts, h } = draw(CTX, DEFAULT_OPTIONS, 2560, 1440);
    const caveat = texts.find((t) => t.text.includes("not measured capacity loss"));
    expect(caveat).toBeTruthy();
    expect(caveat!.y).toBeLessThan(h);
    expect(caveat!.y).toBeGreaterThan(h * 0.5);
  });

  it("draws a backing band so text stays readable over any choropleth colour", () => {
    expect(draw().rects.length).toBeGreaterThan(0);
  });
});
