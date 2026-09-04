/** Briefing/export tests (iteration 11 P8 §28).
 *
 *  The failure these guard against is an image that leaves the application and is then read
 *  wrongly, with nobody present to correct it. Every assertion here is about what the pixels
 *  say — the caveat matched to the metric, the dates that are actually shown, and the claims
 *  that must never appear.
 */

import { describe, expect, it } from "vitest";
import {
  CRIMEA_NOTE, DEFAULT_OPTIONS, EPISODE_FAMILY_CAVEAT, HISTORICAL_CAVEAT, METRIC_CAVEAT,
  PIPELINE_CAVEAT, TRANSMISSION_CAVEAT, briefingFilename, briefingSummaryLine,
  buildBriefingContext, caveatsFor, episodeSummary, exportPixelSize,
} from "./briefing";
import type { Bundle, HistorySeries, LifecycleEpisode } from "./types";

function bundle(over: Record<string, unknown> = {}): Bundle {
  return {
    snapshot: {
      as_of: "2026-09-03",
      schema_version: 2,
      incident_total: 175,
      sectors_covered: ["refining", "electric_generation", "transmission", "oil_logistics"],
      regions: { "RU-KDA": { code: "RU-KDA", name: "Krasnodar Krai" } },
      ...(over.snapshot as object ?? {}),
    },
    national: { dates: ["2026-08-27", "2026-09-03"], esdi: [17.5, 16.98] },
    regional: { regions: { "RU-KDA": { esdi: [3.1, 2.9] } } },
    regions: [{ code: "RU-KDA", name: "Krasnodar Krai" }, { code: "UA-43", name: "Crimea" }],
    incidents: [],
    assets: [],
    buildChanges: null,
    ...over,
  } as unknown as Bundle;
}

const history = {
  dates: ["2025-08-30", "2026-09-03"],
  esdi: [4.34, 16.98],
} as unknown as HistorySeries;

function ctx(over: Record<string, unknown> = {}) {
  return buildBriefingContext({
    bundle: bundle(),
    step: 1,
    currentDate: "2026-09-03",
    metricId: "esdi",
    selectedRegion: null,
    selectionLabel: null,
    pipelinesVisible: false,
    history: null,
    compare: null,
    pointA: null,
    pointB: null,
    episode: null,
    now: "2026-09-03",
    ...over,
  } as Parameters<typeof buildBriefingContext>[0]);
}

describe("exported context", () => {
  it("states the data as-of date", () => {
    // §28.3. An image with no date is undatable once it leaves the app.
    expect(ctx().asOf).toBe("2026-09-03");
    expect(ctx().analyticalDate).toBeNull();
  });

  it("distinguishes an analytical date from the data as-of date", () => {
    // §28.4. Scrubbed into the past, the headline is a historical value and the image must not
    // present it as current.
    const c = ctx({ currentDate: "2026-08-27", step: 0 });
    expect(c.analyticalDate).toBe("2026-08-27");
    expect(c.asOf).toBe("2026-09-03");
    expect(briefingSummaryLine(c)).toContain("analytical date");
    expect(briefingSummaryLine(c)).toContain("data as of");
  });

  it("carries the export timestamp separately from both", () => {
    expect(ctx({ now: "2026-09-10" }).exportedAt).toBe("2026-09-10");
  });
});

describe("metric-specific caveats", () => {
  it("uses the ESDI caveat for the index", () => {
    // §28.6.
    expect(ctx().caveat).toContain("not measured capacity loss");
  });

  it("uses a change caveat for a delta surface, not the exposure one", () => {
    // §28.7. A change surface invites a different misreading and gets a different sentence.
    const c = ctx({ metricId: "esdi_delta_30d" });
    expect(c.caveat).toContain("Not necessarily observed physical damage or repair");
    expect(c.caveat).not.toContain("capacity AT disrupted sites");
  });

  it("adds the transmission proxy caveat where transmission is in the index", () => {
    // §28.8.
    expect(ctx().caveat).toContain("event-burden proxy, not percent of grid offline");
  });

  it("adds the pipeline geometry caveat only when networks are shown", () => {
    expect(ctx().caveat).not.toContain("generalised");
    expect(ctx({ pipelinesVisible: true }).caveat).toContain("generalised");
  });

  it("adds the reconstruction caveat for any historical view", () => {
    const c = ctx({ currentDate: "2026-08-27", step: 0 });
    expect(c.caveat).toContain("Not an archive of what was known");
  });

  it("never applies one generic disclaimer to every metric", () => {
    const a = ctx().caveat;
    const b = ctx({ metricId: "incidents" }).caveat;
    expect(a).not.toEqual(b);
  });

  it("composes only the caveats a view actually needs", () => {
    const only = caveatsFor({
      metricId: "esdi", transmissionVisible: false, pipelinesVisible: false, historical: false,
    });
    expect(only).toEqual([METRIC_CAVEAT.esdi]);
    const all = caveatsFor({
      metricId: "esdi", transmissionVisible: true, pipelinesVisible: true, historical: true,
    });
    expect(all).toEqual([METRIC_CAVEAT.esdi, TRANSMISSION_CAVEAT, PIPELINE_CAVEAT,
      HISTORICAL_CAVEAT]);
  });
});

describe("scope wording", () => {
  it("keeps the Crimea sovereignty note when Crimea is in scope", () => {
    // §28.9. Never dropped to produce a cleaner graphic.
    const c = ctx();
    expect(c.crimeaNote).toBe(CRIMEA_NOTE);
    expect(c.crimeaNote).toContain("internationally recognised as part of Ukraine");
    expect(c.crimeaNote).toContain("analytical choice");
  });

  it("omits it when Crimea is not in the displayed scope", () => {
    const b = bundle({ regions: [{ code: "RU-KDA", name: "Krasnodar Krai" }] });
    expect(ctx({ bundle: b }).crimeaNote).toBeNull();
  });

  it("always states the monitored area", () => {
    expect(ctx().scopeNote).toContain("Belarus, western Russia");
    expect(ctx().scopeNote).toContain("administrative region");
  });
});

describe("comparison export", () => {
  const compare = { a: "2025-08-30", b: "2026-09-03", mode: "delta" };
  const pointA = { requested_date: "2025-08-30", resolved_series_date: "2025-08-30", step: 0, exact: true };
  const pointB = { requested_date: "2026-09-03", resolved_series_date: "2026-09-03", step: 1, exact: true };

  it("carries both dates and the delta with its sign convention", () => {
    // §28.5.
    const c = ctx({ compare, pointA, pointB, history });
    expect(c.comparison).toBeTruthy();
    expect(c.comparison!.aValue).toBe("4.34");
    expect(c.comparison!.bValue).toBe("16.98");
    expect(c.comparison!.delta).toBe("+12.64");
  });

  it("exposes a resolved series date when the requested day was not one", () => {
    const inexact = { ...pointA, requested_date: "2025-09-01", exact: false };
    const c = ctx({ compare: { ...compare, a: "2025-09-01" }, pointA: inexact, pointB, history });
    expect(c.comparison!.resolvedNote).toContain("resolved to");
    expect(c.comparison!.resolvedNote).toContain("2025-08-30");
  });

  it("says nothing about resolution when both dates were exact series points", () => {
    expect(ctx({ compare, pointA, pointB, history }).comparison!.resolvedNote).toBeNull();
  });
});

describe("build ledger in exports", () => {
  const valid = {
    lineage: { valid: true, current_commit: "abc1234" },
    esdi_delta: -0.17,
    previous_as_of: "2026-09-02",
    current_as_of: "2026-09-03",
  };

  it("includes the build delta with both dates when lineage is provable", () => {
    // §28.11.
    const c = ctx({ bundle: bundle({ buildChanges: valid }) });
    expect(c.buildDelta).toEqual({
      previousAsOf: "2026-09-02", currentAsOf: "2026-09-03", delta: "−0.17",
    });
  });

  it("omits it entirely when lineage is invalid", () => {
    // §28.10. "No prior build" is a fact about a git repository, not an analytical finding, and
    // must never leave the application looking like one.
    const invalid = { lineage: { valid: false }, esdi_delta: null,
      previous_as_of: null, current_as_of: "2026-09-03" };
    const c = ctx({ bundle: bundle({ buildChanges: invalid }) });
    expect(c.buildDelta).toBeNull();
  });

  it("omits it when there is no ledger at all", () => {
    expect(ctx().buildDelta).toBeNull();
  });
});

describe("filenames", () => {
  it("is deterministic and describes the view", () => {
    // §28.17.
    expect(briefingFilename(ctx())).toBe("energy-disruption-monitor_2026-09-03_esdi.png");
    expect(briefingFilename(ctx({ metricId: "esdi_delta_30d" })))
      .toBe("energy-disruption-monitor_2026-09-03_30d-change.png");
  });

  it("names both endpoints for a comparison", () => {
    const c = ctx({
      compare: { a: "2025-08-30", b: "2026-09-03", mode: "delta" },
      pointA: { requested_date: "2025-08-30", resolved_series_date: "2025-08-30", step: 0, exact: true },
      pointB: { requested_date: "2026-09-03", resolved_series_date: "2026-09-03", step: 1, exact: true },
      history,
    });
    expect(briefingFilename(c))
      .toBe("energy-disruption-monitor_2025-08-30_to_2026-09-03.png");
  });

  it("uses the analytical date when scrubbed into the past", () => {
    expect(briefingFilename(ctx({ currentDate: "2026-08-27", step: 0 })))
      .toContain("2026-08-27");
  });

  it("produces filesystem-safe names", () => {
    const name = briefingFilename(ctx());
    expect(name).toMatch(/^[a-z0-9._-]+$/);
  });
});

describe("provenance", () => {
  it("records build, dates and metric without relying on them being visible", () => {
    // §21: metadata is a bonus. The visible image already carries the same facts.
    const c = ctx({ bundle: bundle({ buildChanges: { lineage: { valid: true, current_commit: "deadbee" } } }) });
    expect(c.provenance.build_sha).toBe("deadbee");
    expect(c.provenance.data_as_of).toBe("2026-09-03");
    expect(c.provenance.metric).toBe("esdi");
    expect(c.sourceFooter).toContain("Public open sources only");
  });

  it("defaults produce a complete graphic", () => {
    expect(DEFAULT_OPTIONS.title).toBe(true);
    expect(DEFAULT_OPTIONS.scopeNote).toBe(true);
    expect(DEFAULT_OPTIONS.sourceFooter).toBe(true);
  });
});

describe("selection labelling", () => {
  it("marks a region-centroid asset as administrative placement", () => {
    // §28.12. The marker is not where the facility is, and an exported label must say so.
    const c = ctx({ selectionLabel: "Ryazan refinery — administrative-region placement, not facility location" });
    expect(c.selection).toContain("administrative-region placement");
    expect(c.selection).not.toMatch(/\d+\.\d+°/);
  });

  it("never carries coordinates", () => {
    const blob = JSON.stringify(ctx({ selectionLabel: "Some Facility · Krasnodar Krai" }));
    expect(blob).not.toMatch(/"lat"|"lon"|coordinates/);
  });
});

describe("export dimensions", () => {
  it("renders a named size at exactly those pixels", () => {
    // The defect this pins: a 1.25 device ratio turned a requested 1920x1080 into a 2400x1350
    // file. Sharper, but not the size someone building a slide asked for.
    expect(exportPixelSize("1920x1080", 1067, 562, 1.25))
      .toEqual({ width: 1920, height: 1080, pixelRatio: 1 });
    expect(exportPixelSize("2560x1440", 1067, 562, 2))
      .toEqual({ width: 2560, height: 1440, pixelRatio: 1 });
  });

  it("matches the reader's screen for a viewport export", () => {
    expect(exportPixelSize("viewport", 1289, 845, 1.25))
      .toEqual({ width: 1289, height: 845, pixelRatio: 1.25 });
  });

  it("clamps the device ratio so a 3x screen does not produce an enormous file", () => {
    expect(exportPixelSize("viewport", 1000, 800, 3).pixelRatio).toBe(2);
    expect(exportPixelSize("viewport", 1000, 800, 0).pixelRatio).toBe(1);
  });

  it("never distorts geography by changing only one axis", () => {
    const a = exportPixelSize("1920x1080", 1067, 562, 1);
    expect(a.width / a.height).toBeCloseTo(16 / 9, 5);
  });
});


describe("recovery episode exports", () => {
  function ep(over: Partial<LifecycleEpisode> = {}): LifecycleEpisode {
    return {
      episode_id: "ep-1",
      asset_id: "ru-ref-ryazan",
      asset_name: "Ryazan refinery",
      asset_class: "Refinery",
      incident_date: "2026-08-02",
      evidence_family: "service_restoration",
      undated_restoration_claim: false,
      duration_days: 14,
      duration_start: "2026-08-02",
      duration_end: "2026-08-16",
      ...over,
    } as unknown as LifecycleEpisode;
  }

  it("names the facility, the family and the observed span", () => {
    // The gap this closes: entering Briefing Mode from the recovery explorer produced a graphic
    // that said nothing about the episode on screen.
    const e = episodeSummary(ep());
    expect(e.facility).toBe("Ryazan refinery");
    expect(e.familyLabel).toBe("service restoration");
    expect(e.outcome).toContain("14 days");
    expect(e.outcome).toContain("2 Aug 2026");
  });

  it("never states a restoration date for an estimated horizon", () => {
    // A projected horizon rendered as a date is how a model becomes an observation in a slide.
    const e = episodeSummary(ep({ evidence_family: "estimate", duration_days: 45 }));
    expect(e.outcome).toBe("projected repair horizon, no observed restoration");
    expect(e.durationDays).toBeNull();
  });

  it("distinguishes an undated restoration claim from both restored and no evidence", () => {
    const e = episodeSummary(ep({
      undated_restoration_claim: true, duration_days: null, duration_end: null,
    }));
    expect(e.outcome).toContain("no date recorded");
    expect(e.outcome).toContain("drives no scoring change");
  });

  it("says so plainly when there is no recovery evidence", () => {
    const e = episodeSummary(ep({
      evidence_family: null, duration_days: null, duration_end: null,
    }));
    expect(e.familyLabel).toBe("no recovery evidence");
    expect(e.outcome).toBe("no recovery evidence");
  });

  it("adds the family caveat and the reconstruction caveat even at the live date", () => {
    // A trajectory is rebuilt from the current evidence set whatever date the map is on.
    const c = ctx({ episode: ep() });
    expect(c.caveat).toContain(EPISODE_FAMILY_CAVEAT);
    expect(c.caveat).toContain(HISTORICAL_CAVEAT);
    expect(c.analyticalDate).toBeNull();
  });

  it("names the episode in the filename", () => {
    expect(briefingFilename(ctx({ episode: ep() })))
      .toBe("energy-disruption-monitor_2026-08-02_recovery_ryazan-refinery.png");
  });

  it("lets an active comparison keep the filename, since that is what the map shows", () => {
    const c = ctx({
      episode: ep(),
      compare: { a: "2025-08-30", b: "2026-09-03", mode: "delta" },
      pointA: { requested_date: "2025-08-30", resolved_series_date: "2025-08-30", step: 0, exact: true },
      pointB: { requested_date: "2026-09-03", resolved_series_date: "2026-09-03", step: 1, exact: true },
      history,
    });
    expect(briefingFilename(c)).toBe("energy-disruption-monitor_2025-08-30_to_2026-09-03.png");
    // ...but the episode is still described in the frame.
    expect(c.episode!.facility).toBe("Ryazan refinery");
  });

  it("carries no coordinates", () => {
    const blob = JSON.stringify(ctx({ episode: ep() }));
    expect(blob).not.toMatch(/"lat"|"lon"|coordinates/);
  });
});
