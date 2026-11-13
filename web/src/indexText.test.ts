import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { buildDeltaTitle, excludedSectorEventsText, fmtIndex, indexMoveText } from "./indexText";
import { localDayOf } from "./freshness";
import { laneChips, laneStatePhrase } from "./global/homeModel";

/** Iteration 21 methodology red team: display rules that keep the theatre's numbers honest. */

const servedSnapshot = JSON.parse(readFileSync(fileURLToPath(new URL("../public/data/snapshot.json", import.meta.url)), "utf-8"));

describe("fmtIndex — a small live value never reads as a measured zero", () => {
  it("prints the headline's one decimal", () => {
    expect(fmtIndex(6.69)).toBe("6.7");
    expect(fmtIndex(14.28)).toBe("14.3");
  });
  it("prints a value above zero but under 0.05 as <0.1, not 0.0", () => {
    expect(fmtIndex(0.03)).toBe("<0.1");
    expect(fmtIndex(0.01)).toBe("<0.1");
    expect(fmtIndex(0.05)).toBe("0.1");
  });
  it("keeps an exact zero (measured) and a null (never computed) distinct", () => {
    expect(fmtIndex(0)).toBe("0.0");
    expect(fmtIndex(null)).toBe("—");
    expect(fmtIndex(undefined)).toBe("—");
  });
  it("covers every scored sector in the served build without a false 0.0", () => {
    const covered: string[] = servedSnapshot.sectors_covered;
    expect(covered.length).toBeGreaterThan(0);
    for (const s of covered) {
      const v: number = servedSnapshot.sectors[s];
      if (v > 0) expect(fmtIndex(v)).not.toBe("0.0");
    }
  });
});

describe("excludedSectorEventsText — claims only the events that exist", () => {
  it("names the count when there are events", () => {
    expect(excludedSectorEventsText(8)).toBe("8 recorded events in this sector are not scored.");
    expect(excludedSectorEventsText(1)).toBe("1 recorded event in this sector is not scored.");
  });
  it("says no event is recorded, and that this is not evidence of none, at zero", () => {
    const t = excludedSectorEventsText(0);
    expect(t).toMatch(/^No event in this sector is recorded/);
    expect(t).toMatch(/not evidence that none occurred/);
    expect(t).not.toMatch(/exist/);
  });
  it("claims nothing either way without a count", () => {
    expect(excludedSectorEventsText(undefined)).toBe("Any events recorded in this sector are not scored.");
  });
  it("is fed by the served per-sector count for every unscored sector", () => {
    const uncovered: string[] = servedSnapshot.sectors_uncovered;
    expect(uncovered.length).toBeGreaterThan(0);
    for (const s of uncovered) {
      expect(typeof servedSnapshot.coverage_matrix[s]?.event_count).toBe("number");
    }
  });
});

describe("indexMoveText — levels at one decimal, movement at two", () => {
  it("never prints a level at two decimals", () => {
    const t = indexMoveText("Monitored-Area ESDI", 6.8, 6.69, true);
    expect(t).toBe("Monitored-Area ESDI 6.8 to 6.7 (−0.11).");
    expect(t).not.toMatch(/\d\.\d\d to|to \d+\.\d\d\b/);
  });
});

describe("buildDeltaTitle — the ribbon names its baseline", () => {
  it("dates the previous build and points to What's new's different baseline", () => {
    const t = buildDeltaTitle("2026-11-12T13:48:46+00:00");
    expect(t).toMatch(/previous build \(built \d{1,2} Nov 2026\)/);
    expect(t).toMatch(/What's new compares with the last build dated before this one/);
    expect(buildDeltaTitle(null)).not.toMatch(/built/);
  });
});

describe("localDayOf — the reader's calendar day", () => {
  it("returns a plain day unchanged, whatever the time zone", () => {
    expect(localDayOf("2026-11-12")).toBe("2026-11-12");
  });
  it("reads a UTC timestamp on the local calendar", () => {
    const ts = "2026-11-13T04:21:45+00:00";
    const d = new Date(ts);
    const p = (n: number) => String(n).padStart(2, "0");
    expect(localDayOf(ts)).toBe(`${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`);
  });
  it("returns null for nothing or nonsense", () => {
    expect(localDayOf(null)).toBeNull();
    expect(localDayOf("not a date")).toBeNull();
  });
});

describe("laneStatePhrase — the number counts source groups, not searches", () => {
  it("keeps 'planned searches run' from reading as a number of searches", () => {
    expect(laneStatePhrase("declared_query_set_run", 5)).toBe("5 with planned searches run (not exhaustive)");
    expect(laneStatePhrase("declared_query_set_run", 1)).not.toMatch(/^1 planned searches/);
    expect(laneStatePhrase("partially_searched", 2)).toBe("2 partly searched");
  });
  it("orders states the same way everywhere and drops none", () => {
    expect(laneChips({ blocked_by_source: 1, declared_query_set_run: 3, mystery_state: 2 }))
      .toBe("3 with planned searches run (not exhaustive) · 1 blocked by the source · 2 mystery state");
  });
});
