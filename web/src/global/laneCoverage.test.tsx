import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import ResearchCoverage from "./ResearchCoverage";
import { shapeProblems, type CountryBundle, type CountrySystem, type ResearchLane, type ResearchPass } from "./manifest";
import {
  COVERAGE_STATE_TEXT, coverageState, coverageSummary, countStates, isCampaignRestricted, latestLanes,
  missingLanguages, passOutcomeText, reviewLine,
} from "./laneCoverage";

// The served payloads: the layer that ships.
const DATA = new URL("../../public/data/", import.meta.url);
const read = (p: string) => JSON.parse(readFileSync(fileURLToPath(new URL(p, DATA)), "utf-8"));
const COUNTRIES: string[] = read("global/manifest.json").systems
  .filter((s: { kind: string }) => s.kind === "country").map((s: { id: string }) => s.id);

const lane = (x: Partial<ResearchLane>): ResearchLane => ({
  lane: "T1", universe_kind: "declared_query_set", execution: "declared_search_complete",
  source_window: "no_census_exists", languages_required: ["en"], languages_executed: ["en"],
  queries_declared: 4, queries_run: 4, ...x,
});

function render(sys: CountrySystem): string {
  const bundle = { system: sys, events: [], episodes: [], regions: { type: "FeatureCollection", features: [] } } as CountryBundle;
  return renderToStaticMarkup(<ResearchCoverage bundle={bundle} />);
}

/** Visible text of the markup, without tags or attribute values. */
const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/\s+/g, " ");

describe("lane state mapping", () => {
  it("a source that refused access is Source unavailable, whatever the analyst did", () => {
    expect(coverageState(lane({ execution: "partial", source_window: "inaccessible" }))).toBe("unavailable");
    expect(coverageState(lane({ execution: "not_started", source_window: "inaccessible" }))).toBe("unavailable");
    // The build refuses this combination; the reader is still never told "complete".
    expect(coverageState(lane({ execution: "declared_search_complete", source_window: "inaccessible" }))).toBe("unavailable");
    expect(coverageState(lane({ execution: "partial", source_window: "inaccessible", stopped_by: "search_limit" }))).toBe("unavailable");
  });

  it("a lane stopped by the search limit is never complete", () => {
    expect(coverageState(lane({ execution: "partial", stopped_by: "search_limit" }))).toBe("stopped");
    expect(coverageState(lane({ execution: "declared_search_complete", stopped_by: "search_limit" }))).toBe("stopped");
    expect(coverageState(lane({ execution: "partial", source_window: "rolling_archive_gap", stopped_by: "search_limit" }))).toBe("stopped");
  });

  it("complete only when the lane's own execution says so", () => {
    expect(coverageState(lane({}))).toBe("complete");
    expect(coverageState(lane({ universe_kind: "census", execution: "enumerated_complete", source_window: "publisher_not_yet_released" }))).toBe("complete");
    for (const win of ["current_through_end_date", "no_census_exists", "publisher_not_yet_released", "unknown"]) {
      expect(coverageState(lane({ execution: "partial", source_window: win }))).toBe("partial");
    }
    expect(coverageState(lane({ execution: "enumerated_complete", source_window: "unknown" }))).toBe("partial");
    expect(coverageState(lane({ execution: "not_started", source_window: "no_census_exists" }))).toBe("not_started");
    expect(coverageState(lane({ execution: "partial", source_window: "rolling_archive_gap" }))).toBe("archive_limit");
    expect(coverageState({ lane: "OLD", status: "complete" })).toBe("earlier_format");
  });

  it("a missing language is detected, and blocks complete", () => {
    const l = lane({ languages_required: ["en", "fa"], languages_executed: ["en"] });
    expect(missingLanguages(l)).toEqual(["fa"]);
    expect(coverageState(l)).toBe("partial");
    expect(missingLanguages(lane({ languages_required: ["ar", "en"], languages_executed: ["en", "ar"] }))).toEqual([]);
    expect(missingLanguages(lane({ languages_required: ["ar"], languages_executed: undefined }))).toEqual(["ar"]);
    const html = render(synthetic({ lanes: [l] }));
    expect(text(html)).toContain("Not run in: Persian");
    expect(html).toContain('class="rc-lane rc-lane-partial"');
    expect(html).not.toContain("rc-lane-complete");
    // The overview row says Partial, in words.
    expect(text(html.slice(html.indexOf("<tbody>"), html.indexOf("</tbody>")))).toContain(COVERAGE_STATE_TEXT.partial);
  });

  it("each lane is read from the latest pass that logged it; a same-day continuation wins", () => {
    const passes = [
      pass({ date: "2026-11-03", lanes: [lane({ lane: "A", execution: "partial" }), lane({ lane: "B", execution: "partial" })] }),
      pass({ date: "2026-11-10", lanes: [lane({ lane: "A" })] }),
      pass({ date: "2026-11-10", lanes: [lane({ lane: "A", execution: "partial", stopped_by: "search_limit" })] }),
      pass({ date: "2026-11-11", kind: "targeted", lanes: [lane({ lane: "B" })] }),
    ];
    const rows = latestLanes(passes);
    expect(rows.map((r) => [r.lane.lane, r.state, r.pass.date])).toEqual([["B", "partial", "2026-11-03"], ["A", "stopped", "2026-11-10"]]);
  });

  it("the summary is words and counts, never a percentage", () => {
    const rows = latestLanes([pass({ lanes: [lane({ lane: "A" }), lane({ lane: "B", execution: "partial", stopped_by: "search_limit" }),
      lane({ lane: "C", execution: "partial", source_window: "inaccessible" })] })]);
    expect(coverageSummary(rows, 1)).toBe("1 of 3 lanes declared complete; 1 stopped by the search limit; 1 with the source unavailable.");
    expect(coverageSummary([], 0)).toBe("No search has been run yet.");
    expect(coverageSummary([], 2)).toMatch(/targeted/);
  });
});

function pass(x: Partial<ResearchPass>): ResearchPass {
  return { date: "2026-11-10", by: "test", kind: "systematic", window: ["2022-01-01", "2026-11-10"], scope: "",
           status: "partial", outcome: {}, ...x };
}

function synthetic(x: { lanes: ResearchLane[]; outcome?: Record<string, number>; under_review?: boolean; restricted?: boolean }): CountrySystem {
  const base = read("systems/us/system.json") as CountrySystem;
  const p = pass({ lanes: x.lanes, outcome: x.outcome ?? {}, ...(x.under_review !== undefined ? { under_review: x.under_review } : {}) });
  return {
    ...base,
    research_log: { note: "", passes: [p] },
    publication_policy: { ...base.publication_policy, campaigns: x.restricted
      ? [{ campaign_id: "c", name: "c", status: "active", status_checked: "2026-11-10", status_basis: "", policy_applied: true }] : [] },
  };
}

describe("campaign systems never show a count of candidates, held records or outcomes", () => {
  it("even if the served log carried counts, none is rendered", () => {
    const sys = synthetic({ lanes: [lane({})], outcome: { candidates: 4817, held: 3929, rejected: 5743, accepted: 6151 }, under_review: true, restricted: true });
    expect(isCampaignRestricted(sys)).toBe(true);
    const t = text(render(sys));
    for (const n of ["4817", "3929", "5743", "6151", "4,817", "3,929"]) expect(t).not.toContain(n);
    expect(t).not.toMatch(/\b(held|candidates?) \d/i);
    expect(t).toContain("Additional candidates remain under review and are not shown.");
    expect(passOutcomeText(sys.research_log.passes[0], true)).not.toMatch(/\d/);
  });

  it("the under-review line appears only where under_review is true", () => {
    expect(reviewLine(synthetic({ lanes: [lane({})], under_review: false, restricted: true }))).toBeNull();
    expect(reviewLine(synthetic({ lanes: [lane({})], under_review: true, restricted: true }))).toMatch(/under review/);
    expect(reviewLine(synthetic({ lanes: [lane({})], outcome: { held: 3 } }))).toBeNull();
  });

  it("outside the policy the pass history keeps its counts", () => {
    expect(passOutcomeText(pass({ outcome: { candidates: 28, held: 17 } }), false)).toBe("candidates 28 · held 17");
  });
});

describe("every served country system", () => {
  it("lists the country systems", () => expect(COUNTRIES.length).toBeGreaterThan(0));

  for (const id of COUNTRIES) {
    it(`${id}: lanes map to states, agree with the build, and render without a score`, () => {
      const sys = read(`systems/${id}/system.json`) as CountrySystem;
      expect(shapeProblems(sys, read(`systems/${id}/events.json`))).toEqual([]);
      const rows = latestLanes(sys.research_log.passes);
      expect(rows.length).toBeGreaterThan(0);
      const n = countStates(rows);
      const rf = sys.research_freshness;
      const newest = sys.research_log.passes.filter((p) => p.kind === "systematic").at(-1)!;
      // While every lane sits in the newest pass, the reader's counts are the build's counts.
      if (rows.every((r) => r.pass === newest)) {
        expect(rows.length).toBe(rf.lanes_declared);
        expect(n.complete).toBe(rf.lanes_complete);
        expect(n.stopped).toBe(rf.lane_states?.stopped_by_search_limit ?? 0);
        expect(n.unavailable).toBe(rf.lane_states?.blocked_by_source ?? 0);
        expect(n.not_started).toBe(rf.lane_states?.not_started ?? 0);
      }
      for (const r of rows) {
        if (r.lane.source_window === "inaccessible") expect(r.state).toBe("unavailable");
        if (r.lane.stopped_by === "search_limit" && r.lane.source_window !== "inaccessible") expect(r.state).toBe("stopped");
        if (r.state === "complete") {
          expect(["enumerated_complete", "declared_search_complete"]).toContain(r.lane.execution);
          expect(missingLanguages(r.lane)).toEqual([]);
        }
      }
      const html = render(sys);
      const t = text(html);
      expect(t).toContain(coverageSummary(rows, sys.research_log.passes.length));
      expect((html.match(/class="rc-lane rc-lane-/g) ?? []).length).toBe(rows.length);
      // No coverage percentage or score in what the explorer itself says (lane notes may quote one
      // from a source, e.g. a production share; that is data, not a coverage figure).
      const own = text(html.slice(0, html.indexOf('<ol class="rc-lanes"')));
      expect(own).not.toMatch(/\d\s?%|\bscore of\b|\d+ ?\/ ?\d+/i);
      expect(t).not.toMatch(/\biteration\b/i);
      if (isCampaignRestricted(sys)) {
        expect(t).not.toMatch(/\b(held|candidates?|rejected|accepted|duplicate|out of scope) \d/i);
        expect(t.includes("Additional candidates remain under review")).toBe(!!newest.under_review);
      }
    });
  }

  it("the campaign rule covers every system the build serves under it", () => {
    let checked = 0;
    for (const id of COUNTRIES) {
      const sys = read(`systems/${id}/system.json`) as CountrySystem;
      if ((sys.publication_policy.campaigns ?? []).some((c) => c.policy_applied)) {
        expect(isCampaignRestricted(sys)).toBe(true);
        checked += 1;
      }
    }
    expect(checked).toBeGreaterThan(0);
  });
});

describe("pass history tense", () => {
  it("only the newest systematic pass says candidates remain under review", () => {
    const p = { date: "2026-11-11", kind: "systematic", by: "x", under_review: true } as unknown as Parameters<typeof passOutcomeText>[0];
    expect(passOutcomeText(p, true, true)).toMatch(/remain under review/);
    expect(passOutcomeText(p, true, false)).not.toMatch(/remain/);
    expect(passOutcomeText(p, true, false)).toMatch(/were under review when this pass was logged/);
  });
});
