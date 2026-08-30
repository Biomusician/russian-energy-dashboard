import { describe, it, expect } from "vitest";
import { inWindow, addDays } from "./data";
import type { RecoveryEvent } from "./types";

/** Fixtures for the "What changed" recovery count (§4 of the release gate).
 *
 *  The defect this guards: the panel used to read snapshot.live_disruptions, which contains only
 *  facilities whose disruption weight is still > 0 (and is capped at 80). A FULLY-RECOVERED
 *  facility is absent from that array by construction, so the very episodes the panel asks about
 *  were the ones it could not see — 1 of 9 in the real corpus. It now reads the complete
 *  recovery_events log, so the cases below must all be reachable.
 */
function ev(over: Partial<RecoveryEvent> & { evidence_date: string }): RecoveryEvent {
  return {
    incident_id: "i", episode_id: over.episode_id ?? `ep-${over.evidence_date}`,
    asset_id: "a", asset_name: "Facility", asset_class: "refinery", sector: "refining",
    region_code: "RU-ROS", incident_date: "2026-01-01",
    evidence_date_kind: "observed_restoration",
    recovery_status: "fully_reconstituted", scoring_evidence_kind: "observed",
    observed_days: 10, counts_toward_observed_episodes: true, sources: [],
    ...over,
  } as RecoveryEvent;
}

const NOW = "2026-08-28";
const start30 = addDays(NOW, -30); // 2026-07-29

// The five cases the release gate requires to be represented.
const A_live_unresolved = ev({
  evidence_date: "2026-08-20", episode_id: "A", recovery_status: "partial_restart",
  evidence_date_kind: "partial_restart", counts_toward_observed_episodes: false, observed_days: null,
});
const B_fully_resolved = ev({
  evidence_date: "2026-08-21", episode_id: "B", recovery_status: "fully_reconstituted",
});
// Dated inside 90 days of NOW but outside 30 — so it proves the window bound, not just absence.
const C_outside_window = ev({ evidence_date: "2026-06-15", episode_id: "C" });
const D_service_restoration = ev({
  evidence_date: "2026-08-05", episode_id: "D", evidence_family: "service_restoration",
  scoring_evidence_kind: "modelled", observed_days: null, counts_toward_observed_episodes: false,
});
const E_physical_reconstitution = ev({
  evidence_date: "2026-08-01", episode_id: "E", evidence_family: "facility_reconstitution",
});
const ALL = [A_live_unresolved, B_fully_resolved, C_outside_window, D_service_restoration, E_physical_reconstitution];

const inWin = (rows: RecoveryEvent[], days: number, now = NOW) =>
  inWindow(rows, (e) => e.evidence_date, addDays(now, -days), now);

describe("What changed — recovery evidence completeness (§4)", () => {
  it("counts a FULLY-RESOLVED incident's restoration (the case live_disruptions could not see)", () => {
    const got = inWin(ALL, 30).map((e) => e.episode_id);
    expect(got).toContain("B");
  });

  it("counts a still-unresolved facility's partial restart", () => {
    expect(inWin(ALL, 30).map((e) => e.episode_id)).toContain("A");
  });

  it("counts service restoration and physical reconstitution alike as dated evidence", () => {
    const got = inWin(ALL, 30).map((e) => e.episode_id);
    expect(got).toContain("D");
    expect(got).toContain("E");
  });

  it("excludes evidence older than the window", () => {
    expect(inWin(ALL, 30).map((e) => e.episode_id)).not.toContain("C");
  });

  it("returns exactly the four in-window cases over 30 days", () => {
    expect(inWin(ALL, 30)).toHaveLength(4);
  });

  it("widening to 90 days pulls in the older evidence", () => {
    expect(inWin(ALL, 90).map((e) => e.episode_id)).toContain("C");
    expect(inWin(ALL, 90)).toHaveLength(5);
  });

  it("narrowing the window keeps only the most recent evidence", () => {
    // 10 days back from 2026-08-28 starts at 08-18: A (08-20) and B (08-21) survive; the
    // early-August rows do not.
    expect(inWin(ALL, 10).map((e) => e.episode_id).sort()).toEqual(["A", "B"]);
  });

  it("a window shorter than the gap to the newest evidence is legitimately empty", () => {
    // Nothing is dated in the last 7 days; the panel must say so rather than reach further back.
    expect(inWin(ALL, 7)).toEqual([]);
  });

  it("separates dated evidence from MEASURED durations", () => {
    const win = inWin(ALL, 30);
    expect(win).toHaveLength(4);
    // Only B and E carry a usable observed duration; A is a partial restart and D is modelled.
    expect(win.filter((e) => e.counts_toward_observed_episodes).map((e) => e.episode_id).sort())
      .toEqual(["B", "E"]);
  });

  it("degrades to empty when the payload predates recovery_events (deploy window)", () => {
    expect(inWin([], 30)).toEqual([]);
  });
});

describe("What changed — obeys the timeline scrubber (§6)", () => {
  it("shows nothing dated after a scrubbed historical position", () => {
    const scrubbed = "2026-08-10";
    const got = inWin(ALL, 30, scrubbed);
    expect(got.every((e) => e.evidence_date <= scrubbed)).toBe(true);
    // A (08-20) and B (08-21) are in the FUTURE of this scrubber position and must not appear.
    expect(got.map((e) => e.episode_id).sort()).toEqual(["D", "E"]);
  });

  it("includes evidence dated exactly ON the scrubber date (window end is inclusive)", () => {
    expect(inWin(ALL, 30, "2026-08-21").map((e) => e.episode_id)).toContain("B");
  });

  it("excludes evidence dated exactly ON the window start (start is exclusive)", () => {
    // E is dated 2026-08-01; a window starting exactly there must not re-count it.
    const got = inWindow(ALL, (e) => e.evidence_date, "2026-08-01", NOW);
    expect(got.map((e) => e.episode_id)).not.toContain("E");
  });

  it("adjacent windows never double-count a row", () => {
    const mid = "2026-08-10";
    const older = inWindow(ALL, (e) => e.evidence_date, "2026-07-01", mid).map((e) => e.episode_id);
    const newer = inWindow(ALL, (e) => e.evidence_date, mid, NOW).map((e) => e.episode_id);
    expect(older.filter((id) => newer.includes(id))).toEqual([]);
  });

  it("scrubbing to before all evidence yields nothing", () => {
    expect(inWin(ALL, 90, "2026-01-15")).toEqual([]);
  });

  it("ignores rows with a missing date rather than throwing", () => {
    const broken = [...ALL, ev({ evidence_date: "" }), ev({ evidence_date: null as unknown as string })];
    expect(inWin(broken, 30)).toHaveLength(4);
  });
});
