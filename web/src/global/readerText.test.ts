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

  it("no served country text keeps a file name once read through it", () => {
    const root = join(__dirname, "..", "..", "public", "data", "systems");
    for (const id of readdirSync(root)) {
      const walk = (x: unknown): void => {
        if (typeof x === "string") expect(readerText(x)).not.toMatch(/[A-Z][A-Z0-9_]*\.md\b|WebFetch|this agent/);
        else if (Array.isArray(x)) x.forEach(walk);
        else if (x && typeof x === "object") Object.values(x).forEach(walk);
      };
      walk(JSON.parse(readFileSync(join(root, id, "system.json"), "utf-8")));
    }
  });
});
