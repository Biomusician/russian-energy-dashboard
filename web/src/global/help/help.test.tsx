import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { HELP_SECTIONS_TOC, HELP_SUBSECTIONS, anchorTitle, helpAnchors, helpHref } from "./anchors";
import { HELP_SECTIONS, type HelpBlock } from "./content";
import { GLOSSARY, START_HERE } from "./glossary";
import { GLOSSARY_DETAIL, HOW_IT_WORKS } from "./glossaryDetail";
import { ECI_DRAFT_NOTE, type HelpData } from "./HelpDerived";
import { HelpDocument } from "./HelpPage";
import { legacyHelpUrl, routeFor } from "../router";
import type { HelpFacts } from "./facts";

/** The Help page (iteration 23): its addresses, its prose rules, and what it must always say. */

const DATA = join(__dirname, "..", "..", "..", "public", "data");
const read = (f: string) => JSON.parse(readFileSync(join(DATA, f), "utf-8"));

function served(over: Partial<{ method: unknown }> = {}): HelpData {
  return {
    facts: { value: read("global/help_facts.json") as HelpFacts, failed: false },
    manifest: { value: read("global/manifest.json"), failed: false },
    method: { value: (over.method ?? read("global/evidence_confidence.json")) as never, failed: false },
    whatsNew: { value: read("global/whats_new.json"), failed: false },
  };
}

/** The page's visible words: tags out, entities back. */
function text(html: string): string {
  return html.replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&quot;/g, "\"").replace(/&#x27;/g, "'")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/\s+/g, " ");
}

/** Every string of prose typed into the Help modules. */
function proseStrings(): string[] {
  const out: string[] = [];
  const walk = (blocks: HelpBlock[]) => {
    for (const b of blocks) {
      if (b.kind === "p") out.push(b.text);
      else if (b.kind === "list") out.push(...b.items);
      else if (b.kind === "details") { out.push(b.summary); walk(b.blocks); }
    }
  };
  for (const s of HELP_SECTIONS) { out.push(s.answer); walk(s.blocks); for (const sub of s.subsections ?? []) walk(sub.blocks); }
  for (const g of GLOSSARY) out.push(g.term, g.plain, GLOSSARY_DETAIL[g.id].detail);
  for (const s of HOW_IT_WORKS) out.push(s.step, s.text);
  for (const s of START_HERE) out.push(s.title, s.text);
  out.push(ECI_DRAFT_NOTE, ...HELP_SECTIONS_TOC.map((s) => s.title), ...HELP_SUBSECTIONS.map((s) => s.title));
  return out;
}

describe("Help addresses", () => {
  it("has every section in the table of contents, in its order, once, and every anchor is unique", () => {
    expect(HELP_SECTIONS.map((s) => s.id)).toEqual(HELP_SECTIONS_TOC.map((s) => s.id));
    const all = [...helpAnchors(), ...GLOSSARY.map((g) => `g-${g.id}`)];
    expect(new Set(all).size).toBe(all.length);
    for (const sub of HELP_SUBSECTIONS) {
      const parent = HELP_SECTIONS.find((s) => s.id === sub.parent)!;
      expect(parent.subsections?.map((x) => x.id), sub.id).toContain(sub.id);
    }
    expect(helpHref("esdi")).toBe("?view=help#esdi");
    expect(anchorTitle("esdi")).toBe("The exposure index (ESDI)");
  });

  it("renders a focusable heading for every anchor, and one h1", () => {
    const html = renderToStaticMarkup(<HelpDocument data={served()} />);
    expect(html.match(/<h1\b/g)).toHaveLength(1);
    for (const id of [...helpAnchors(), ...GLOSSARY.map((g) => `g-${g.id}`)]) {
      expect(html, id).toMatch(new RegExp(`<h[23] id="${id}" tabindex="-1"`));
    }
    expect(html).toContain('<main id="main-content"');
    expect(html).toContain('aria-label="Help sections"');
  });

  it("every Learn more, every glossary 'see' and every See also resolves to a section", () => {
    const anchors = new Set([...helpAnchors(), ...GLOSSARY.map((g) => `g-${g.id}`)]);
    for (const g of GLOSSARY) expect(anchors.has(g.see), g.id).toBe(true);
    for (const s of HELP_SECTIONS) for (const id of s.seeAlso ?? []) expect(anchors.has(id), `${s.id} -> ${id}`).toBe(true);
    // Every link written in the source: <LearnMore anchor="…">, a disclosure's learnMore="…", helpHref("…").
    const src = join(__dirname, "..", "..");
    const found: string[] = [];
    const walk = (dir: string) => {
      for (const f of readdirSync(dir)) {
        const p = join(dir, f);
        if (statSync(p).isDirectory()) walk(p);
        else if (/\.tsx?$/.test(f) && !/\.test\./.test(f)) {
          const code = readFileSync(p, "utf-8");
          for (const m of code.matchAll(/<LearnMore[^>]*?\banchor="([^"]+)"|\blearnMore="([^"]+)"|helpHref\("([^"]+)"\)/g)) found.push(m[1] ?? m[2] ?? m[3]);
        }
      }
    };
    walk(src);
    expect(found.length).toBeGreaterThan(20);
    expect(found.filter((a) => !anchors.has(a))).toEqual([]);
    // The served What's New link names a Help section too.
    for (const c of read("global/whats_new.json").global ?? []) if (c.link?.help) expect(anchors.has(c.link.help), c.link.help).toBe(true);
  });

  it("keeps every glossary id from before, with search aliases, and pairs each term with its detail", () => {
    const before = ["ai-involvement", "as-published", "assessed", "attempt", "attributed", "attribution", "attribution-confidence",
      "civilian-service-impact", "claimed", "cyber-disruption", "disputed", "episode", "esdi", "evidence-confidence", "exposure",
      "impact-atlas", "impact-record-country", "national-context", "no-index", "originating-statement", "placement",
      "publication-safeguard", "reported-effect", "research-coverage", "research-preview", "sector-state", "transmission-burden"];
    for (const id of before) expect(GLOSSARY.find((g) => g.id === id), id).toBeTruthy();
    expect(Object.keys(GLOSSARY_DETAIL).sort()).toEqual(GLOSSARY.map((g) => g.id).sort());
    expect(GLOSSARY.find((g) => g.id === "esdi")!.aliases).toContain("exposure index");
  });

  it("routes ?view=help with the atlas's precedence, and rewrites the old glossary link", () => {
    expect(routeFor("?view=help")).toEqual({ view: "help" });
    expect(routeFor("?view=HELP")).toEqual({ view: "help" });
    expect(routeFor("?help=glossary")).toEqual({ view: "help" });
    expect(routeFor("?sys=ir&view=help")).toEqual({ view: "country", id: "ir" });
    expect(routeFor("?group=gulf&help=glossary")).toEqual({ view: "group", id: "gulf" });
    expect(routeFor("?compare=us&view=help").view).toBe("compare");
    expect(legacyHelpUrl("?help=glossary", "")).toBe("?view=help#glossary");
    expect(legacyHelpUrl("?help=glossary&term=esdi", "")).toBe("?view=help#g-esdi");
    expect(legacyHelpUrl("?help=glossary&term=bad%20id", "")).toBe("?view=help#glossary");
    expect(legacyHelpUrl("?sys=us&help=glossary", "")).toBeNull();
    expect(legacyHelpUrl("?view=help", "#esdi")).toBeNull();
  });
});

describe("Help prose rules", () => {
  const strings = proseStrings();
  // Digits a reader needs: the index scale, the start year, the worked example's dates, the formula.
  const ALLOWED_DIGITS = /\b(0 to 100|since 2022|1 March|10 April|0\.5|3\.3219)\b/g;

  it("has prose to check", () => expect(strings.length).toBeGreaterThan(200));

  it("names no file, no internal id, no build vocabulary, and does not speak in the first person", () => {
    for (const s of strings) {
      expect(s, s).not.toMatch(/\.(json|csv|md|tsx?|py)\b|\bdocs\/|\b[a-z]+_[a-z_]+\b|\b[A-Z]{2,}_[A-Z_]+\b/);
      expect(s, s).not.toMatch(/\biterations?\b|\bpayload\b|\bpipeline\b|\bD-\d\d\b/i);
      expect(s, s).not.toMatch(/\b(we|our|ours|us|me|my)\b|\bI\b|\bWe\b|\bOur\b/);
    }
  });

  it("states no live figure: digits only from the allow-list", () => {
    for (const s of strings) expect(s.replace(ALLOWED_DIGITS, ""), s).not.toMatch(/\d/);
  });

  it("never types the Evidence Confidence method's status: that comes from the served file", () => {
    for (const s of strings) expect(s, s).not.toMatch(/provisional|\bdraft\b|calibrat/i);
  });
});

describe("what Help always says", () => {
  const page = text(renderToStaticMarkup(<HelpDocument data={served()} />));

  it.each([
    ["not a probability"], ["does not cover cause"], ["No index is not zero"], ["Counts are not rates"],
    ["Latest is not current"], ["no restoration report is not known still offline"], ["No record is not no disruption"],
    ["The maps are never the only way in"], ["a missing index is not a zero"], ["not a complete list of disruptions"],
  ])("says %s", (phrase) => expect(page.toLowerCase()).toContain(phrase.toLowerCase()));

  it("takes the method's provisional status from the served file, with the draft note only while it is a draft", () => {
    const m = read("global/evidence_confidence.json");
    expect(page).toContain(`Method version ${m.version}.`);
    if (m.status) expect(page).toContain(m.status);
    expect(page.includes(ECI_DRAFT_NOTE)).toBe(/-draft$/.test(m.version));
    const calibrated = text(renderToStaticMarkup(<HelpDocument data={served({ method: { ...m, version: "2.0", status: "a served status" } })} />));
    expect(calibrated).toContain("Status: a served status.");
    expect(calibrated).not.toContain(ECI_DRAFT_NOTE);
  });

  it("never calls a probability, a rate or a count anything but what it is", () => {
    for (const sentence of page.split(/(?<=[.;:])\s+/)) {
      if (/\bprobability\b/i.test(sentence)) expect(sentence, sentence).toMatch(/\bnot\b|\bnever\b|\bnor\b/i);
      if (/\brates?\b/i.test(sentence)) expect(sentence, sentence).toMatch(/\bnot\b|\bnever\b/i);
    }
  });

  it("says loading, or that a file failed, instead of guessing a value", () => {
    const none = { value: null, failed: false };
    const loading = text(renderToStaticMarkup(<HelpDocument data={{ facts: none, manifest: none, method: none, whatsNew: none }} />));
    expect(loading).toContain("Loading the current index value");
    const failed = { value: null, failed: true };
    const broken = text(renderToStaticMarkup(<HelpDocument data={{ facts: failed, manifest: failed, method: failed, whatsNew: failed }} />));
    expect(broken).toContain("could not be loaded, so it is not shown here");
    expect(broken).not.toMatch(/Method version/);
  });
});
