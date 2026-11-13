import { describe, expect, it } from "vitest";
import { ageText, collapseCovered, isCovered, placementOf, recordLine } from "./homeModel";
import { readDismissed, writeDismissed, START_HERE_KEY } from "./startHereMemory";
import type { RecentEpisode } from "./manifest";

function ep(over: Partial<RecentEpisode> & { system_id: string; episode_id: string }): RecentEpisode {
  return {
    country: over.system_id.toUpperCase(), episode_name: null, basis: "singleton", records: 1,
    first_date: "2026-03-01", last_date: "2026-03-01", date_precision: "day", classes: ["Oil refinery"],
    causes: ["Unknown"], members: [{ date: "2026-03-01", date_precision: "day", region: "Texas", effect: null,
      effect_on_country_page: false, withheld: false }], more_members: 0, ...over,
  };
}
const covered = (sid: string, n: number, date = "2026-03-01") => ep({
  system_id: sid, episode_id: `${sid}-row-${String(n).padStart(2, "0")}`, first_date: date, last_date: date,
  members: [{ date, date_precision: "day", region: "National", effect: null, effect_on_country_page: false, withheld: true }],
});

describe("ages on the reader's clock", () => {
  it("counts calendar days and never shows a negative or precomputed age", () => {
    expect(ageText("2026-11-12", "2026-11-12")).toBe("today");
    expect(ageText("2026-11-11", "2026-11-12")).toBe("1 day ago");
    expect(ageText("2026-10-31", "2026-11-12")).toBe("12 days ago");
    expect(ageText("2026-11-13", "2026-11-12")).toBe("");
    expect(ageText(null, "2026-11-12")).toBe("");
    expect(ageText("2026-11", "2026-11-12")).toBe("");
  });

  it("says 'no qualifying records yet' for null, nothing for an older build, never '0 events'", () => {
    expect(recordLine(null, "2026-11-12")).toBe("No qualifying records yet");
    expect(recordLine(undefined, "2026-11-12")).toBeNull();
    expect(recordLine("2026-11-03", "2026-11-12")).toBe("Record reviewed 3 Nov 2026 · 9 days ago");
    expect(recordLine(null, "2026-11-12")).not.toMatch(/\d/);
  });
});

describe("recent feed", () => {
  it("collapses a run of covered items of one country into one line with no count", () => {
    const list = [ep({ system_id: "us", episode_id: "us-a" }), covered("sa", 1, "2026-04-08"), covered("sa", 2, "2026-04-02"),
                  covered("sa", 3, "2026-03-19"), ep({ system_id: "us", episode_id: "us-b" }), covered("sa", 4), covered("iq", 5)];
    const rows = collapseCovered(list);
    expect(rows.map((r) => r.kind)).toEqual(["item", "covered-run", "item", "item", "item"]);
    const run = rows[1];
    if (run.kind !== "covered-run") throw new Error("expected a run");
    expect(run.first_date).toBe("2026-03-19");
    expect(run.last_date).toBe("2026-04-08");
    // No count, and no row keys that would reveal one.
    expect(JSON.stringify(run)).not.toMatch(/row-0[123]|"records"|"count"|"n"/);
  });

  it("places a covered item as National with no region, and others at the level the list carries", () => {
    expect(isCovered(covered("sa", 1))).toBe(true);
    expect(placementOf(covered("sa", 1))).toEqual({ level: "National", names: [] });
    expect(placementOf(ep({ system_id: "us", episode_id: "x" }))).toEqual({ level: "First-level region", names: ["Texas"] });
    const multi = ep({ system_id: "us", episode_id: "y", members: [{ date: "d", date_precision: "day", region: "Multiple regions", effect: null, effect_on_country_page: false, withheld: false }] });
    expect(placementOf(multi).level).toBe("Several regions");
  });
});

describe("Start-here memory", () => {
  function memory() {
    const m = new Map<string, string>();
    return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => { m.set(k, v); }, removeItem: (k: string) => { m.delete(k); }, m };
  }
  const throwing = {
    getItem: () => { throw new Error("SecurityError"); },
    setItem: () => { throw new Error("QuotaExceeded"); },
    removeItem: () => { throw new Error("SecurityError"); },
  };

  it("remembers a dismissal and forgets it on reopen", () => {
    const s = memory();
    expect(readDismissed(() => s)).toBe(false);
    expect(writeDismissed(true, () => s)).toBe(true);
    expect(s.m.get(START_HERE_KEY)).toBe("1");
    expect(readDismissed(() => s)).toBe(true);
    expect(writeDismissed(false, () => s)).toBe(true);
    expect(readDismissed(() => s)).toBe(false);
  });

  it("never throws when storage throws, is missing, or its accessor throws", () => {
    for (const get of [() => throwing, () => null, () => { throw new Error("blocked"); }]) {
      expect(() => readDismissed(get)).not.toThrow();
      expect(readDismissed(get)).toBe(false);
      expect(() => writeDismissed(true, get)).not.toThrow();
      expect(writeDismissed(true, get)).toBe(false);
    }
  });
});
