import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  ABSTRACTED_CSV_NOTE, COUNTRY_EVENT_COLUMNS, COUNTRY_EVENT_FIELDS, CSV_BOM, IMPACT_COLUMNS, IMPACT_FIELDS, LEGACY_CSV_NOTE,
  SAFEGUARD_CSV_NOTE, citationsCell, countryEventRow, countryEventsCsv, csvCell, csvFilename, impactRecordsCsv, impactRow,
  readmeFilename, readmeText, toCsv, type ImpactRecordForCsv,
} from "./recordCsv";
import { countryExport, countryFilters, countrySearch, exportOrder } from "./countryFilters";
import { applyFilters, decodeFilters, describeFilters, encodeFilters, filterQueryOf } from "./recordFilters";
import type { CountryEvent, CountrySystem, Manifest } from "./manifest";

/** Iteration 22: the safe CSV export, and the country page as its first consumer. Served payloads
 *  where they reach the rule; made records where no served record does. The pytest twins that the
 *  mutation campaign can see are in tests/test_iteration22_filters.py. */

const DATA = new URL("../../public/data/", import.meta.url);
const read = (p: string) => JSON.parse(readFileSync(fileURLToPath(new URL(p, DATA)), "utf-8"));
const manifest = read("global/manifest.json") as Manifest;
const countryIds = manifest.systems.filter((s) => s.kind === "country").map((s) => s.id);
const system = (id: string) => read(`systems/${id}/system.json`) as CountrySystem;
const events = (id: string) => read(`systems/${id}/events.json`).events as CountryEvent[];

/** A minimal RFC 4180 reader, so the tests read the file the way a spreadsheet would. */
function parseCsv(textIn: string): string[][] {
  const s = textIn.startsWith(CSV_BOM) ? textIn.slice(1) : textIn;
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (quoted) {
      if (ch === '"' && s[i + 1] === '"') { cell += '"'; i++; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\r" && s[i + 1] === "\n") { row.push(cell); rows.push(row); row = []; cell = ""; i++; }
    else cell += ch;
  }
  if (cell !== "" || row.length > 0) { row.push(cell); rows.push(row); }
  return rows;
}

const objects = (csv: string): Record<string, string>[] => {
  const [head, ...rows] = parseCsv(csv);
  return rows.map((r) => Object.fromEntries(head.map((h, i) => [h, r[i]])));
};

describe("the CSV format", () => {
  it("starts with a UTF-8 byte-order mark and uses CRLF line ends", () => {
    const csv = toCsv(["a", "b"], [{ a: "1", b: "2" }]);
    expect(csv.charCodeAt(0)).toBe(0xfeff);
    expect(csv).toBe("﻿a,b\r\n1,2\r\n");
    expect([...new TextEncoder().encode(csv).slice(0, 3)]).toEqual([0xef, 0xbb, 0xbf]);
  });

  it("quotes commas, quotes and line breaks per RFC 4180, and reads back exactly", () => {
    expect(csvCell("plain")).toBe("plain");
    expect(csvCell("a,b")).toBe('"a,b"');
    expect(csvCell('say "hi"')).toBe('"say ""hi"""');
    expect(csvCell("two\nlines")).toBe('"two\nlines"');
    const values = ["a,b", 'say "hi"', "two\r\nlines", "", " padded ", "انقطاع التيار", "قطع برق"];
    const csv = toCsv(values.map((_, i) => `c${i}`), [Object.fromEntries(values.map((v, i) => [`c${i}`, v]))]);
    expect(parseCsv(csv)[1]).toEqual(values);
  });

  it("makes a cell a spreadsheet would run as a formula into text", () => {
    for (const bad of ["=1+1", "+1", "-1", "@SUM(A1)", "\t=1", "\r=1", '=HYPERLINK("http://x","y")']) {
      expect(csvCell(bad).replace(/^"/, "").startsWith("'")).toBe(true);
    }
    expect(csvCell("2024-01-01")).toBe("2024-01-01");
    expect(csvCell("a=b")).toBe("a=b");
    // The guard and the quoting compose: the apostrophe sits inside the quotes.
    expect(csvCell('=A1,"x"')).toBe('"\'=A1,""x"""');
  });

  it("writes only the listed columns, whatever else a row carries", () => {
    const csv = toCsv(["a"], [{ a: "1", secret: "LEAK" } as Record<string, string>]);
    expect(csv).not.toContain("LEAK");
    expect(toCsv(["a", "constructor"], [{ a: "1" }])).toBe("﻿a,constructor\r\n1,\r\n");
  });

  it("puts publisher, date and address of each citation in one cell, never a headline", () => {
    expect(citationsCell([
      { url: "https://example.org/a", publisher: "Example", date: "2024-01-02", title_original: "HEADLINE" } as never,
      { url: "https://news.example.com/b?x=1" },
    ])).toBe("Example, 2024-01-02, https://example.org/a | news.example.com, https://news.example.com/b?x=1");
    expect(citationsCell(null)).toBe("");
  });

  it("names files by scope and build date, from safe characters only", () => {
    expect(csvFilename("us", "events", "2026-11-19")).toBe("edm-us-events-2026-11-19.csv");
    expect(csvFilename("../../etc/passwd", "events", "2026-11-19")).toBe("edm-etc-passwd-events-2026-11-19.csv");
    expect(readmeFilename("edm-us-events-2026-11-19.csv")).toBe("edm-us-events-2026-11-19-README.txt");
  });
});

// A record with something planted in every field the export must not carry.
const SECRET = "SENTINEL-NOT-FOR-EXPORT";
function planted(base: CountryEvent): CountryEvent {
  return {
    ...base,
    facility_name_local: SECRET,
    threshold_basis: SECRET,
    capacity_affected: base.capacity_affected ? { ...base.capacity_affected, source_says: SECRET } : null,
    review: { ...base.review, process: SECRET, source_access: SECRET },
    sources: base.sources.map((s) => ({ ...s, internal_note: SECRET, reviewer_rationale: SECRET })),
    // Fields no served record has; an export that dumped the record would carry them.
    reviewer_rationale: SECRET, lat: 51.5007, lon: -0.1246, coordinates: [51.5007, -0.1246], candidate_id: SECRET,
  } as unknown as CountryEvent;
}

describe("country events", () => {
  it("every column is documented, and the set is the fixed allow-list", () => {
    expect(Object.keys(COUNTRY_EVENT_FIELDS)).toEqual([...COUNTRY_EVENT_COLUMNS]);
    expect(Object.keys(IMPACT_FIELDS)).toEqual([...IMPACT_COLUMNS]);
    for (const cols of [COUNTRY_EVENT_COLUMNS, IMPACT_COLUMNS]) {
      for (const c of cols) expect(c).not.toMatch(/(^|_)(lat|lon|lng|latitude|longitude)(_|$)|coord|geometry|reviewer|rationale|candidate|process|distance/i);
    }
  });

  it("an unexpected or internal field on a record is never exported", () => {
    const sys = system("us");
    const csv = countryEventsCsv(events("us").slice(0, 5).map(planted), sys);
    expect(csv).not.toContain(SECRET);
    expect(csv).not.toContain("51.5007");
    expect(parseCsv(csv)[0]).toEqual([...COUNTRY_EVENT_COLUMNS]);
  });

  it("an ordinary record exports its place, its sources and its recovery research state", () => {
    const sys = system("us");
    const e = events("us").find((x) => x.region_code && x.recovery.research_status === "EVIDENCE_FOUND")!;
    const row = countryEventRow(e, sys);
    expect(row.record_id).toBe(e.event_id);
    expect(row.region_code).toBe(e.region_code);
    expect(row.region_name).toBe(e.region_name);
    expect(row.cause_label).toBe(sys.taxonomy.causes[e.cause]);
    expect(row.recovery_research_status).toBe("EVIDENCE_FOUND");
    expect(row.citations).toContain(e.sources[0].url);
    expect(row.publication_note).toBe("");
  });

  it("every served campaign-covered record exports no place, facility, operator, headline or status", () => {
    let seen = 0;
    for (const id of countryIds) {
      const sys = system(id);
      for (const e of events(id).filter((x) => x.publication)) {
        seen++;
        const row = countryEventRow(e, sys);
        for (const col of ["region_code", "region_name", "regions_affected", "facility", "operator", "source_headlines",
          "recovery_research_status", "recovery_kind", "recovery_date"] as const) {
          expect(row[col], `${e.event_id} ${col}`).toBe("");
        }
        expect(row.publication_note).toContain(SAFEGUARD_CSV_NOTE);
        expect(row.date).toBe(e.date);
        expect(row.asset_class).toBe(e.asset_class);
        // The whole line, not just the named columns: no name the record withholds anywhere in it.
        const line = Object.values(row).join(" ");
        for (const name of [e.facility_name, e.facility_name_local, e.operator, e.region_name, e.region_code]) {
          if (name) expect(line, `${e.event_id} leaks ${name}`).not.toContain(name);
        }
      }
    }
    expect(seen).toBeGreaterThan(0);
  });

  it("a covered record whose id names its facility exports no id, text or citation either", () => {
    const sys = system("sa");
    const e = events("sa").find((x) => x.publication)!;
    const row = countryEventRow(e, sys);
    expect(row.record_id).toBe("");
    expect(row.summary).toBe("");
    expect(row.reported_effect).toBe("");
    expect(row.citations).toBe("");
    expect(row.publication_note).toContain(LEGACY_CSV_NOTE);
  });

  it("an abstracted attack record under a country-level rule keeps its opaque id and text, and no place", () => {
    const sys = system("ir");
    expect(sys.geography.precision_policy?.kinetic).toBe("country");
    const e = {
      ...events("us")[0], event_id: "ir-2026-03-01-refinery-attack-a1b2c3", date: "2026-03-01", asset_class: "refinery",
      cause: "kinetic_strike", geography_precision: "country", region_code: null, region_name: "PLANTED REGION",
      facility_name: "PLANTED FACILITY", operator: "PLANTED OPERATOR", regions_affected: ["IR-01"],
      summary: "An attack on a refinery was reported.", effect: "Output was reported cut.",
      sources: [{ url: "https://example.org/report", publisher: "Example", title_original: "PLANTED HEADLINE" }],
      publication: null,
    } as unknown as CountryEvent;
    const row = countryEventRow(e, sys);
    expect(row.record_id).toBe(e.event_id);
    expect(row.summary).toBe(e.summary);
    expect(row.citations).toContain("https://example.org/report");
    expect(Object.values(row).join(" ")).not.toMatch(/PLANTED|IR-01/);
    expect(row.placement).toBe("National, under safeguards");
    expect(row.recovery_research_status).toBe("");
    expect(row.publication_note).toContain(SAFEGUARD_CSV_NOTE);
  });

  it("a formula in served text cannot reach a spreadsheet as a formula", () => {
    const sys = system("us");
    const e = { ...events("us")[0], summary: "=cmd|' /C calc'!A0", operator: "@evil", facility_name: "+1", effect: "-2" } as CountryEvent;
    const row = objects(countryEventsCsv([e], sys))[0];
    for (const col of ["summary", "operator", "facility", "reported_effect"]) expect(row[col].startsWith("'")).toBe(true);
  });

  it("exports exactly the records it is given: the shown list, nothing else", () => {
    for (const id of countryIds) {
      const sys = system(id);
      const all = events(id);
      const { defs } = countryFilters(sys, all);
      const cause = defs.find((d) => d.id === "cause");
      const state = cause && cause.kind === "choice" ? { choices: { cause: [cause.options[0].value] }, dates: {} } : { choices: {}, dates: {} };
      const shown = applyFilters(all, defs, state, "2026-11-19");
      const rows = objects(countryEventsCsv(shown, sys));
      expect(rows).toHaveLength(shown.length);
      if (cause && cause.kind === "choice") for (const r of rows) expect(r.cause).toBe(cause.options[0].value);
    }
  });

  it("Arabic and Persian text survives the round trip", () => {
    const sys = system("kw");
    const withTitle = events("kw").filter((e) => e.sources.some((s) => s.title_original));
    expect(withTitle.length).toBeGreaterThan(0);
    const rows = objects(countryEventsCsv(withTitle, sys));
    expect(rows[0].source_headlines).toBe(withTitle[0].sources.map((s) => s.title_original).filter(Boolean).join(" | "));
    expect(rows[0].source_headlines).toMatch(/[؀-ۿ]/);
  });
});

describe("the country page's filters, address and files", () => {
  it("offers only filters with something to choose, and says what a single value is", () => {
    for (const id of countryIds) {
      const sys = system(id);
      const all = events(id);
      const { defs, fixed } = countryFilters(sys, all);
      expect(defs[0].id).toBe("date");
      for (const d of defs) if (d.kind === "choice") expect(d.options.length).toBeGreaterThan(1);
      const causes = new Set(all.map((e) => e.cause));
      expect(defs.some((d) => d.id === "cause")).toBe(causes.size > 1);
      if (causes.size === 1) expect(fixed.join(" ")).toContain(sys.taxonomy.causes[[...causes][0]] ?? [...causes][0]);
      // Labels come from the served taxonomy, never from a key.
      const cause = defs.find((d) => d.id === "cause");
      if (cause && cause.kind === "choice") for (const o of cause.options) expect(o.label).toBe(sys.taxonomy.causes[o.value]);
      // Evidence confidence appears only when the served events carry it.
      const served = all.some((e) => (e as { evidence_confidence?: unknown }).evidence_confidence);
      if (!served) expect(defs.some((d) => d.id === "conf")).toBe(false);
    }
  });

  it("offers evidence confidence when the events carry it, labelled by the served label", () => {
    const sys = system("us");
    const all = events("us").slice(0, 4).map((e, i) => ({ ...e, evidence_confidence: i % 2 ? { category: "HIGH", label: "High" } : { category: "LIMITED", label: "Limited" } })) as CountryEvent[];
    const conf = countryFilters(sys, all).defs.find((d) => d.id === "conf");
    expect(conf && conf.kind === "choice" && conf.options).toEqual([{ value: "HIGH", label: "High" }, { value: "LIMITED", label: "Limited" }]);
    const ordered = countryFilters(sys, all, [{ value: "LIMITED", label: "Limited" }, { value: "MODERATE", label: "Moderate" }, { value: "HIGH", label: "High" }])
      .defs.find((d) => d.id === "conf");
    expect(ordered && ordered.kind === "choice" && ordered.options.map((o) => o.value)).toEqual(["LIMITED", "HIGH"]);
  });

  it("the address keeps the system, the region and the filters through a reload", () => {
    const sys = system("us");
    const { defs } = countryFilters(sys, events("us"));
    const state = { choices: { cause: ["technical"] }, dates: { date: { preset: "1y" as const } } };
    const search = countrySearch("us", "US-TX", encodeFilters(defs, state));
    expect(search).toBe("sys=us&r=US-TX&f.cause=technical&f.date=1y");
    const p = new URLSearchParams(search);
    expect(p.get("sys")).toBe("us");
    expect(p.get("r")).toBe("US-TX");
    expect(decodeFilters(filterQueryOf(`?${search}`), defs).state).toEqual(state);
    expect(countrySearch("us", null, "")).toBe("sys=us");
  });

  it("the files carry the system and build date in their names, and the README says what the CSV cannot", () => {
    const sys = system("us");
    const all = events("us");
    const { defs } = countryFilters(sys, all);
    const state = { choices: { cause: ["technical"] }, dates: {} };
    const shown = applyFilters(all, defs, state, "2026-11-19");
    const out = countryExport(sys, shown, all.length, describeFilters(defs, state, "2026-11-19"), null, "2026-11-19");
    expect(out.csvName).toBe(`edm-us-events-${sys.as_of}.csv`);
    expect(out.readmeName).toBe(`edm-us-events-${sys.as_of}-README.txt`);
    expect(objects(out.csv)).toHaveLength(shown.length);
    expect(objects(out.csv).map((r) => r.record_id)).toEqual(exportOrder(shown).map((e) => e.event_id));
    for (const want of [
      `Records in this file: ${shown.length} of ${all.length}`, "Cause: Technical accident", `leave out ${all.length - shown.length}`,
      "not a census", "not comparable across countries", sys.as_of, "us (United States)", sys.comparability_statement,
      "An empty cell is never a zero", "record_id:", "publication_note:",
    ]) expect(out.readme).toContain(want);
    // The CSV itself is data only: no comment rows, no preamble.
    expect(parseCsv(out.csv)[0]).toEqual([...COUNTRY_EVENT_COLUMNS]);
    expect(out.csv).not.toContain("#");
  });

  it("the README says when no filter is on, and names the safeguards when a row is under them", () => {
    const sys = system("sa");
    const all = events("sa");
    const out = countryExport(sys, all, all.length, [], null, "2026-11-19");
    expect(out.readme).toContain("None: every published record in this list is in the file.");
    expect(out.readme).toContain("attack-campaign safeguards");
    for (const e of all) {
      if (e.facility_name) expect(out.csv).not.toContain(e.facility_name);
      if (e.operator) expect(out.csv).not.toContain(e.operator);
    }
  });
});

describe("impact records", () => {
  const base: ImpactRecordForCsv = {
    impact_id: "imp-2023-12-12-ukr-telecom-example", record_kind: "disruption", date: "2023-12-12", date_precision: "day",
    date_end: "2023-12-20", country_a3: "UKR", country_name: "Ukraine", admin1: { code: "UA-30", name: "Kyiv" },
    geographic_precision: "admin1", domain: "civilian_service", sector: "telecom", technology: null, cause_family: "cyber",
    contributing_factors: [], cyber_mechanism: "destructive_malware", summary: "A national operator's network went down.",
    effect: "Mobile service was lost.", effect_specificity: "quantified",
    civilian_service_impact: [{ service: "telecom", geographic_scope: "national", duration_text: "about a week",
      affected: { source_says: "about 24 million mobile subscribers", unit: "subscribers" } }],
    attribution: { status: "ATTRIBUTED", actor: "Example group", actor_type: "state_linked", basis: ["government", "victim_operator"],
      as_of: "2024-01-04", statement: "The security service attributed the attack to the group.", confidence: "MODERATE" },
    ai_involvement: { status: "NONE_REPORTED", relation: null, role: null, as_of: null },
    evidence_confidence: { category: "HIGH", label: "High", score: 90 }, origin_count: 3,
    sources: [{ url: "https://example.org/a", publisher: "Operator", date: "2023-12-12", title_original: "Заголовок" }],
    publication_policy: "standard", first_published: "2026-11-20",
  };

  it("a standard record exports its fields, with units left in the source's own words", () => {
    const row = impactRow(base);
    expect(row.admin1_code).toBe("UA-30");
    expect(row.civilian_service_impact).toBe("telecom, national, about 24 million mobile subscribers, about a week");
    expect(row.attribution_basis).toBe("government; victim_operator");
    expect(row.attribution_confidence).toBe("MODERATE");
    expect(row.evidence_confidence).toBe("High");
    expect(row.evidence_confidence_score).toBe("90");
    expect(row.source_headlines).toBe("Заголовок");
    expect(row.technology).toBe("");
    expect(row.publication_note).toBe("");
  });

  it("an abstracted record exports no region and no headline, by policy or by cause", () => {
    const planted = { ...base, admin1: { code: "XX-01", name: "PLANTED REGION" }, sources: [{ url: "https://example.org/a", title_original: "PLANTED HEADLINE" }] };
    for (const r of [
      { ...planted, publication_policy: "country_abstracted" },
      { ...planted, cause_family: "kinetic", publication_policy: "standard" },
      { ...planted, cause_family: "sabotage", publication_policy: undefined },
      { ...planted, contributing_factors: ["kinetic"] },
    ]) {
      const row = impactRow(r);
      expect(row.admin1_code).toBe("");
      expect(row.admin1_name).toBe("");
      expect(row.source_headlines).toBe("");
      expect(row.geographic_precision).toBe("country");
      expect(row.publication_note).toBe(ABSTRACTED_CSV_NOTE);
      expect(Object.values(row).join(" ")).not.toMatch(/PLANTED|XX-01/);
    }
  });

  it("an unexpected field is never exported, and an absent one never fails the file", () => {
    const csv = impactRecordsCsv([{ ...base, lat: 50.45, lon: 30.52, review: { rationale: SECRET }, operator: SECRET, facility: SECRET } as ImpactRecordForCsv, {}]);
    expect(csv).not.toContain(SECRET);
    expect(csv).not.toContain("50.45");
    const rows = parseCsv(csv);
    expect(rows[0]).toEqual([...IMPACT_COLUMNS]);
    expect(rows).toHaveLength(3);
    expect(rows[2].every((c) => c === "")).toBe(true);
  });
});

describe("the README", () => {
  it("states the caveat, the filters and every column", () => {
    const t = readmeText({
      title: "Impact records", csvName: "edm-atlas-impacts-2026-11-19.csv", scope: "atlas", buildDate: "2026-11-19", downloaded: "2026-11-20",
      shown: 3, total: 10, filters: ["Sector: Telecom"], limitations: ["A limit."], columns: IMPACT_COLUMNS, fields: IMPACT_FIELDS,
    });
    expect(t).toContain("Records in this file: 3 of 10");
    expect(t).toContain("- Sector: Telecom");
    expect(t).toContain("leave out 7 of the 10");
    expect(t).toContain("not a census");
    expect(t).toContain("- A limit.");
    for (const c of IMPACT_COLUMNS) expect(t).toContain(`- ${c}: `);
  });
});
