import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { compareRows, exportBlocker, moveColumn, resolveCompare, type CompareColumn } from "./compare";
import { EmptyCorpus } from "./EmptyCorpus";
import { EvidenceInspector } from "./EventCard";
import { recoveryNotEstablished } from "./evidence";
import { EpisodeItem } from "./GroupView";
import { isCovered } from "./homeModel";
import type { CountryBundle, CountryEvent, CountrySystem, Manifest, RecentEpisode, WhatsNew } from "./manifest";
import { WhatsNewPanel } from "./WhatsNew";
import { RecoveryLine, statusWithheld } from "../components/ui";
import type { RecoveryState } from "../types";

/** Iteration 21, test-architecture red team. Each test fails on a mutant that no test caught before
 *  (scripts/mutation_campaign.py, ITER21_TESTARCH_MUTATIONS; the campaign's pytest twins are in
 *  tests/test_iteration21_testarch.py). Served payloads where they reach the rule; made records
 *  where no served record does. */

const DATA = new URL("../../public/data/", import.meta.url);
const read = (p: string) => JSON.parse(readFileSync(fileURLToPath(new URL(p, DATA)), "utf-8"));
const manifest = read("global/manifest.json") as Manifest;
const countryIds = manifest.systems.filter((s) => s.kind === "country").map((s) => s.id);
const system = (id: string) => read(`systems/${id}/system.json`) as CountrySystem;
const events = (id: string) => read(`systems/${id}/events.json`).events as CountryEvent[];
const bundleOf = (sys: CountrySystem, evs: CountryEvent[] = []): CountryBundle =>
  ({ system: sys, events: evs, episodes: [], regions: { type: "FeatureCollection", features: [] } }) as CountryBundle;
const text = (html: string) => html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");

function columns(ids: string[], loaded = true): CompareColumn[] {
  return resolveCompare(ids, manifest).columns.map((entry) => entry.kind === "theatre"
    ? { entry, system: null, status: "theatre" as const }
    : loaded ? { entry, system: system(entry.id), status: "loaded" as const }
      : { entry, system: null, status: "loading" as const });
}

describe("compare", () => {
  it("a repeated id is one column", () => {
    expect(resolveCompare(["us", "us", "ca", "us"], manifest).columns.map((s) => s.id)).toEqual(["us", "ca"]);
  });

  it("every system under the campaign rule says Yes to safeguards, loaded or not, UNCERTAIN included", () => {
    let checked = 0;
    for (const loaded of [false, true]) {
      for (let i = 0; i < countryIds.length; i += 4) {
        const cols = columns(countryIds.slice(i, i + 4), loaded);
        const row = compareRows(cols, null, manifest).find((r) => r.id === "safeguards")!;
        cols.forEach((c, j) => {
          expect(row.cells[j].text, c.entry.id).toBe(c.entry.campaign_restricted ? "Yes" : "No");
          checked += 1;
        });
      }
    }
    expect(checked).toBe(2 * countryIds.length);
  });

  it("a country-level attack rule is never described as first-level placement", () => {
    let kinetic = 0;
    for (const id of countryIds) {
      const cols = columns([id]);
      const cell = compareRows(cols, null, manifest).find((r) => r.id === "placement")!.cells[0];
      if (cols[0].system?.geography.precision_policy?.kinetic === "country") {
        expect(cell.text, id).toMatch(/^(Attack records: country as a whole|Country as a whole)/);
        kinetic += 1;
      }
    }
    expect(kinetic).toBeGreaterThan(0);
  });

  it("the export waits for every column and the context", () => {
    expect(exportBlocker(columns(["us"]), true, false)).toMatch(/at least two/);
    expect(exportBlocker(columns(["us", "ca"], false), true, false)).toMatch(/Still loading/);
    expect(exportBlocker(columns(["us", "ca"]), false, false)).toMatch(/Still loading/);
    expect(exportBlocker(columns(["us", "ca"]), false, true)).toBeNull();
    expect(exportBlocker(columns(["us", "ca", "ru"]), true, false)).toBeNull();
  });

  it("moving a column swaps it with its neighbour and nothing else", () => {
    expect(moveColumn(["us", "ca", "sa"], 1, -1)).toEqual(["ca", "us", "sa"]);
    expect(moveColumn(["us", "ca", "sa"], 1, 1)).toEqual(["us", "sa", "ca"]);
    expect(moveColumn(["us", "ca"], 0, -1)).toEqual(["us", "ca"]);
  });
});

describe("record lists", () => {
  const ep = (id: string, withheld: boolean, effect: string | null): RecentEpisode => ({
    system_id: id.slice(0, 2), country: "Country", episode_id: id, episode_name: null, basis: "singleton", records: 1,
    first_date: "2026-04-08", last_date: "2026-04-08", date_precision: "day", classes: ["Oil refinery"], causes: ["Kinetic strike"],
    members: [{ date: "2026-04-08", date_precision: "day", region: withheld ? "National" : "Al Ahmadi", effect,
                effect_on_country_page: false, withheld }],
    more_members: 0,
  } as unknown as RecentEpisode);

  it("a lone covered record on the regional list says it is not summarised, whatever the payload carries", () => {
    const html = renderToStaticMarkup(<ul><EpisodeItem ep={ep("sa-row-01", true, "Refinery back in service.")} /></ul>);
    expect(html).toContain("Not summarised in this list");
    expect(html).not.toContain("back in service");
  });

  it("covered is read from the withheld members, never from a row key", () => {
    expect(isCovered(ep("kw-row-08", false, "Power cuts."))).toBe(false);
    expect(isCovered(ep("sa-2026-04-08-ras-tanura-refinery-shutdown", true, null))).toBe(true);
  });
});

describe("withheld facility status", () => {
  const snap = read("snapshot.json") as { live_disruptions: { recovery: RecoveryState }[] };
  const noted = snap.live_disruptions.map((d) => d.recovery).filter((r) => r.publication_note);

  it("a withheld record whose status field is absent is still withheld", () => {
    expect(noted.length).toBeGreaterThan(0);
    const absent = { ...noted[0] } as Partial<RecoveryState>;
    delete absent.recovery_status;
    expect(statusWithheld(absent as RecoveryState)).toBe(true);
  });

  it("a released record never shows the facility's age, horizon or estimate now", () => {
    const released = noted.find((r) => r.recovery_status === "partial_restart");
    expect(released).toBeTruthy();
    const r = { ...released!, impairment_age_days: 4321, reconstitution_horizon_days: 8765, scoring_evidence_kind: "modelled" } as RecoveryState;
    const html = renderToStaticMarkup(<RecoveryLine r={r} />);
    expect(html).not.toContain("4321");
    expect(html).not.toContain("8765");
  });

  it("the withheld line carries the record's own note", () => {
    const html = renderToStaticMarkup(<RecoveryLine r={noted.find((r) => statusWithheld(r))!} />);
    expect(html).toContain("Status withheld");
    expect(html).toContain(noted.find((r) => statusWithheld(r))!.publication_note!);
  });
});

describe("country page", () => {
  it("no public evidence of a return is not a finding that there was none", () => {
    expect(recoveryNotEstablished({ recovery: { research_status: "RESEARCHED_NO_PUBLIC_EVIDENCE" } } as CountryEvent))
      .toContain("not a finding that it did not");
  });

  it("an unchecked citation says so in the inspector, never reachable", () => {
    const e = structuredClone(events("us")[0]);
    e.sources = [{ ...e.sources[0], url: "https://checked.example/a", link_check: "dead" },
                 { ...e.sources[0], url: "https://unchecked.example/b", link_check: undefined }];
    const t = text(renderToStaticMarkup(<EvidenceInspector id="x" e={e} bundle={bundleOf(system("us"), [e])} onClose={() => {}} />));
    expect(t).toContain("gone at the last automated check");
    expect(t).toContain("not link-checked");
    expect(t).not.toContain("reachable at the last automated check");
  });

  it("every empty page under an attack-campaign state says what is not published, UNCERTAIN included", () => {
    let uncertain = 0;
    for (const id of countryIds) {
      const sys = system(id);
      const state = sys.campaign_state?.state;
      if (events(id).length || !state || state === "NO_ACTIVE_CAMPAIGN") continue;
      const t = text(renderToStaticMarkup(<EmptyCorpus bundle={bundleOf(sys)} ctx={null} onTab={() => {}} />));
      expect(t, id).toContain("is not published");
      if (state === "UNCERTAIN") uncertain += 1;
    }
    expect(uncertain).toBeGreaterThan(0);
  });
});

describe("what's new", () => {
  const served = read("global/whats_new.json") as WhatsNew;
  const panel = (d: WhatsNew) => renderToStaticMarkup(<WhatsNewPanel data={d} failed={false} now={new Date("2026-11-12T12:00:00Z")} />);

  it("a system that could not be compared says so and is never listed as unchanged", () => {
    const d = { ...served, available: true, comparison: { previous_as_of: "2026-11-11", current_as_of: "2026-11-12", mode: "production", basis: "b" },
      systems: [{ system_id: "ru", name: "Russia, Belarus & Crimea", kind: "theatre", changes: [], unavailable: "no comparison" }],
      unchanged: [{ system_id: "us", name: "United States" }] } as unknown as WhatsNew;
    const html = panel(d);
    expect(html.slice(html.indexOf('data-system="ru"'))).toContain("could not be compared");
    expect(html.slice(html.indexOf("wn-unchanged"))).not.toContain("Russia");
  });

  it("no comparison is never 'nothing changed'", () => {
    const d = { ...served, available: false, unavailable_reason: "no baseline", systems: [], global: [], unchanged: [] } as WhatsNew;
    expect(panel(d)).toContain("That is not the same as nothing having changed.");
  });
});
