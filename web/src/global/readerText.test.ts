import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { readerText } from "./readerText";

describe("readerText", () => {
  it("drops methodology file references and keeps the sentence", () => {
    expect(readerText("No model has been approved (GLOBAL_METHODOLOGY.md §2 and §8.3)."))
      .toBe("No model has been approved.");
    expect(readerText("Kept off the public record (data/candidates/README.md). A pass declares lanes."))
      .toBe("Kept off the public record. A pass declares lanes.");
    expect(readerText("Weak on extent. See GLOBAL_METHODOLOGY.md §5.1 for the full red-team."))
      .toBe("Weak on extent.");
    expect(readerText("lanes as declared in docs/countries/AE_SYSTEMATIC_SWEEP.md; every record reviewed"))
      .toBe("lanes as declared in the published research plan; every record reviewed");
  });

  it("drops iteration labels a reader cannot follow", () => {
    expect(readerText("Blind reviewed (since iteration 17): three reviewers")).toBe("Blind reviewed: three reviewers");
    expect(readerText("iteration-19 Gulf research pass")).toBe("Gulf research pass");
    expect(readerText("Compiled by the UAE lane (iteration 19, Wave A). Context only.")).toBe("Compiled by the UAE lane. Context only.");
    expect(readerText("Territories are outside this system's geography this iteration; their events are held."))
      .toBe("Territories are outside this system's geography; their events are held.");
  });

  it("states the research tools in plain words, never drops the limitation", () => {
    const t = readerText("each page was read through WebFetch, which returns a model's reading of the page rather than the raw text; the model declined to reproduce full bodies");
    expect(t).toContain("automated reader");
    expect(t).toContain("declined to reproduce full bodies");
    expect(readerText("budget exhausted before this agent's first search")).toBe("budget exhausted before the first search of this source group");
  });

  it("leaves empty values empty", () => {
    expect(readerText(null)).toBe("");
    expect(readerText("")).toBe("");
  });

  it("puts internal pass numbering, roles and vocabulary keys into words", () => {
    expect(readerText("The execution value restates iteration 17's finding in the two-dimension vocabulary"))
      .toBe("This state restates an earlier pass's finding in the current vocabulary");
    expect(readerText("the other 41 keep their iteration-16 dispositions")).toBe("the other 41 keep their earlier-pass dispositions");
    expect(readerText("continuation of the iteration-19 pass: lanes as declared in docs/countries/AE_SYSTEMATIC_SWEEP.md, work order in docs/countries/GULF_CONTINUATION_PLAN_20.md; each lane"))
      .toBe("continuation of the earlier pass: lanes as declared in the published research plan; each lane");
    expect(readerText("Iteration 20 added four searches.")).toBe("A later pass added four searches.");
    expect(readerText("The shared search allowance ran out before every declared query was run."))
      .toBe("The pass reached its search limit before every declared query was run.");
    expect(readerText("proposed, awaiting owner approval")).toBe("proposed, not yet approved");
    expect(readerText("Partial by construction (plan A.1: no census source)")).toBe("Partial by construction (no census source)");
    expect(readerText("Compiled by the UAE source-audit lane. CONTEXT ONLY: never a scoring input."))
      .toBe("Compiled by the UAE source audit. Context only: never a scoring input.");
  });

  // Every served prose string of every country system, read as a page shows it. A prose string is
  // one with spaces: enum values (state keys) and ids are labelled by the components, not shown raw.
  it("no developer term survives in any country system's served text", () => {
    const FORBIDDEN = new RegExp([
      String.raw`\biteration\b`, String.raw`\biteration-\d`, String.raw`\bpayloads?\b`,
      String.raw`\b[\w-]+\.(?:md|py|csv)\b`, "§", String.raw`\bD-\d{2}\b`, "open decision", "project owner",
      String.raw`\bowner (?:approval|rules|decides|accepts)`, String.raw`\bonboard`, "search allowance",
      "WebFetch", "this agent", "two-dimension", String.raw`\b[a-z]+_[a-z_]+\b`,
      String.raw`\b(?:MODELLED|SCORED|EXPERIMENTAL|SYSTEMATIC|TARGETED|PARTIAL|CONTEXT ONLY|CONTEXT_ONLY|NOT_RESEARCHED)\b`,
    ].join("|"));
    // fields that hold ids, addresses or citations rather than prose a component shows as a sentence
    const SKIP = new Set(["url", "archive_url", "event_id", "episode_id", "id", "audit_docs", "document",
      "lanes_from", "source_id", "file", "title", "quote", "source_says", "headline", "facility_name", "publisher"]);
    const root = join(__dirname, "..", "..", "public", "data", "systems");
    let checked = 0;
    const survivors: string[] = [];
    const ids = readdirSync(root);
    for (const id of ids) {
      walk(JSON.parse(readFileSync(join(root, id, "system.json"), "utf-8")), "", id);
      walk(JSON.parse(readFileSync(join(root, id, "events.json"), "utf-8")), "", id);
    }
    expect(ids.length).toBeGreaterThan(0);
    expect(checked).toBeGreaterThan(500);
    const countryChecked = checked;
    // the shared files the home page, the Gulf littoral view and What's new read
    const global = join(__dirname, "..", "..", "public", "data", "global");
    for (const f of ["manifest.json", "gulf.json", "whats_new.json", "data_quality.json", "recent_evidence.json"]) {
      walk(JSON.parse(readFileSync(join(global, f), "utf-8")), "", f);
    }
    expect(checked).toBeGreaterThan(countryChecked);
    expect(survivors).toEqual([]);

    function walk(x: unknown, key: string, where: string): void {
      if (typeof x === "string") {
        if (SKIP.has(key) || !x.includes(" ")) return;
        checked += 1;
        const shown = readerText(x);
        const m = shown.match(FORBIDDEN);
        if (m) survivors.push(`${where}.${key}: "${m[0]}" in ${shown.slice(0, 160)}`);
      } else if (Array.isArray(x)) x.forEach((v) => walk(v, key, where));
      else if (x && typeof x === "object") Object.entries(x).forEach(([k, v]) => walk(v, k, where));
    }
  });
});
