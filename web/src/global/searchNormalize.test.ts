import { describe, expect, it } from "vitest";
import { matchScore, normalizeForSearch as n } from "./searchNormalize";
import { searchEntries, systemEntries, groupEntries, CONCEPT_ENTRIES, VIEW_ENTRIES, theatreRegionEntries, countryRegionEntries } from "./searchIndex";
import type { Manifest } from "./manifest";
import { GLOSSARY } from "./glossary";

// Every way the same Arabic/Persian letter is typed on common keyboards.
const VARIANTS: [string, string[]][] = [
  ["ي", ["ی", "ى", "ئ"]],            // ي ← ی ى ئ
  ["ك", ["ک"]],                                // ك ← ک
  ["ه", ["ة", "ۀ", "ە", "ھ"]],  // ه ← ة ۀ ە ھ
  ["ا", ["أ", "إ", "آ", "ٱ"]],  // ا ← أ إ آ ٱ
  ["و", ["ؤ"]],                                // و ← ؤ
];
const WORDS = ["ایران", "عراق", "کویت", "قطر", "عمان", "البحرين", "السعودية", "الإمارات", "کرمانشاه", "مشهد"];

describe("normalizeForSearch", () => {
  it("folds every Arabic/Persian letter variant to one form, in every word position", () => {
    let checked = 0;
    for (const [canon, alts] of VARIANTS) {
      for (const alt of alts) {
        for (const w of WORDS) {
          for (const pos of [0, 1, w.length]) {
            const a = w.slice(0, pos) + canon + w.slice(pos);
            const b = w.slice(0, pos) + alt + w.slice(pos);
            expect(n(b), `${b} vs ${a}`).toBe(n(a));
            checked++;
          }
        }
      }
    }
    expect(checked).toBeGreaterThan(300);
  });

  it("ignores tatweel, short vowels, zero-width joiners and direction marks", () => {
    let checked = 0;
    for (const w of WORDS) {
      const chars = [...w];
      for (const junk of ["ـ", "َ", "ِ", "ّ", "ْ", "‌", "‍", "‏", "؜"]) {
        for (let i = 1; i < chars.length; i++) {
          const mangled = [...chars.slice(0, i), junk, ...chars.slice(i)].join("");
          expect(n(mangled)).toBe(n(w));
          checked++;
        }
      }
    }
    expect(checked).toBeGreaterThan(200);
  });

  it("folds case and Latin diacritics", () => {
    const pairs = [["Québec", "quebec"], ["ÎLE-DE-FRANCE", "ile de france"], ["São Paulo", "sao paulo"],
                   ["Nordrhein-Westfalen", "nordrhein westfalen"], ["IRAN", "iran"], ["Zürich", "zurich"]];
    for (const [a, b] of pairs) expect(n(a)).toBe(n(b));
    for (let c = 65; c <= 90; c++) expect(n(String.fromCharCode(c))).toBe(String.fromCharCode(c + 32));
  });

  it("turns punctuation into word breaks and Persian/Arabic digits into 0-9", () => {
    expect(n("Russia, Belarus & Crimea")).toBe("russia belarus crimea");
    expect(n("  Gulf—littoral (overview) ")).toBe("gulf littoral overview");
    expect(n("۱۴۰۳")).toBe("1403");
    expect(n("٢٠٢٤")).toBe("2024");
  });

  it("never changes the string it is given (display text stays as written)", () => {
    const originals = [...WORDS, "Québec", "Russia, Belarus & Crimea", "عُمان"];
    for (const o of originals) {
      const copy = String(o);
      n(o);
      expect(o).toBe(copy);
    }
  });
});

describe("matchScore", () => {
  it("prefers exact, then prefix, then word prefix, then substring", () => {
    expect(matchScore("iran", "iran")).toBe(4);
    expect(matchScore("ira", "iran")).toBe(3);
    expect(matchScore("bel", "russia belarus crimea")).toBe(2);
    expect(matchScore("ussia", "russia")).toBe(1);
    expect(matchScore("xyz", "russia")).toBe(0);
  });
});

const MANIFEST = {
  systems: [
    { id: "ir", name: "Iran", kind: "country", aliases: ["ایران", "Persia"], maturity: "research_preview" },
    { id: "ru", name: "Russia, Belarus & Crimea", kind: "theatre" },
    { id: "us", name: "United States", kind: "country", aliases: ["USA"], maturity: "monitored" },
  ],
  groups: {
    gulf_littoral: { label: "Gulf littoral", kind: "geographic", note: "", slug: "gulf", context: "global/gulf.json", members: ["ir"] },
    gcc: { label: "GCC", kind: "membership", note: "", slug: null, context: null, members: [] },
  },
} as unknown as Manifest;

describe("search index", () => {
  const entries = [...systemEntries(MANIFEST), ...groupEntries(MANIFEST), ...VIEW_ENTRIES, ...CONCEPT_ENTRIES];

  it("finds Iran by its English name in any case and by its Persian name in either yeh", () => {
    for (const q of ["Iran", "iran", "IRAN", "ایران", "ايران", "  ایـران "]) {
      const hits = searchEntries(entries, q);
      expect(hits[0]?.entry.label, q).toBe("Iran");
    }
    // The alias that matched is shown as written in the manifest, not in its folded form.
    expect(searchEntries(entries, "ايران")[0].matched).toBe("ایران");
  });

  it("finds groups, views and glossary concepts; a membership list with no page is not offered", () => {
    expect(searchEntries(entries, "gulf")[0].entry.action).toEqual({ type: "group", slug: "gulf" });
    expect(searchEntries(entries, "GCC")).toHaveLength(0);
    expect(searchEntries(entries, "compare")[0].entry.action).toEqual({ type: "href", href: "?compare=" });
    expect(searchEntries(entries, "exposure")[0].entry.kind).toBe("concept");
    expect(searchEntries(entries, "methodology")[0].entry.action).toEqual({ type: "concept", id: "how-it-works" });
  });

  it("orders by match quality, then kind, then name; never by any figure", () => {
    const hits = searchEntries(entries, "i");
    const kinds = hits.map((h) => h.entry.kind);
    expect(hits.length).toBeGreaterThan(0);
    for (let i = 1; i < hits.length; i++) expect(hits[i - 1].score).toBeGreaterThanOrEqual(hits[i].score);
    expect(kinds.length).toBe(hits.length);
  });

  it("describes Crimea as an occupied unit and never as a region of Russia", () => {
    const e = theatreRegionEntries([{ code: "UA-43", name: "Crimea", country: "UA" }, { code: "RU-AD", name: "Republic of Adygea", country: "RU" }], "Russia, Belarus & Crimea");
    expect(e[0].sub).toMatch(/^Occupied unit, internationally Ukrainian/);
    expect(e[0].sub).not.toMatch(/Region of Russia/);
    expect(e[1].sub).toMatch(/^Region of Russia/);
    expect(e[0].action).toEqual({ type: "href", href: "?sys=ru&r=UA-43" });
  });

  it("a loaded country's region is found by a local alias and opens that region", () => {
    const e = countryRegionEntries({ systemId: "ir", systemName: "Iran", unitLabel: "province",
      units: [{ code: "IR-06", name: "Khuzestan" }], aliases: { "IR-06": ["خوزستان", "Ahvaz"] } });
    const hit = searchEntries(e, "خوزستان")[0];
    expect(hit.entry.label).toBe("Khuzestan");
    expect(hit.entry.sub).toBe("Province · Iran");
    expect(hit.entry.action).toEqual({ type: "href", href: "?sys=ir&r=IR-06" });
  });
});

describe("glossary", () => {
  it("is alphabetical and covers every term the product uses", () => {
    const terms = GLOSSARY.map((g) => g.term.toLowerCase());
    expect(terms).toEqual([...terms].sort());
    for (const id of ["esdi", "exposure", "transmission-burden", "episode", "research-preview", "originating-statement",
                      "research-coverage", "as-published", "sector-state", "publication-safeguard", "no-index", "national-context"]) {
      expect(GLOSSARY.some((g) => g.id === id), id).toBe(true);
    }
    for (const g of GLOSSARY) {
      expect(g.plain.length).toBeGreaterThan(40);
      expect(g.detail.length).toBeGreaterThan(40);
      // Reader copy: no build vocabulary.
      expect(`${g.plain} ${g.detail}`).not.toMatch(/iteration|payload|pipeline|\.json|D-\d\d/i);
    }
  });
});
