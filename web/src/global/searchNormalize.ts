/** Text folding for search matching.
 *
 *  Used ONLY to compare a query with a name. Displayed text is never passed through it: a reader
 *  who types "ایران" with a Persian yeh must find a name stored with an Arabic yeh, and must still
 *  see the name exactly as the source wrote it.
 *
 *  What is folded, and why:
 *  - case, and Latin diacritics ("Québec" = "quebec"), by NFKD then dropping combining marks;
 *  - Arabic short vowels and hamza/madda carried as combining marks, dropped the same way, so
 *    أ إ آ all reach ا;
 *  - letter variants that differ between Arabic and Persian keyboards: ی/ى → ي, ک → ك, ة/ۀ/ە/ھ → ه,
 *    ٱ → ا, ؤ → و, ئ → ي;
 *  - tatweel (the stretching stroke), zero-width joiners and direction marks, removed;
 *  - Arabic-Indic and Persian digits → 0-9;
 *  - punctuation and symbols → a space, so "Russia, Belarus & Crimea" = "russia belarus crimea".
 */

const LETTER_FOLD: Record<string, string> = {
  "ی": "ي", // Persian yeh ی → Arabic yeh ي
  "ى": "ي", // alef maksura ى → ي
  "ئ": "ي", // yeh with hamza ئ → ي (survives NFKD in some inputs)
  "ک": "ك", // keheh ک → kaf ك
  "ة": "ه", // teh marbuta ة → heh ه
  "ۀ": "ه", // heh with yeh above ۀ → ه
  "ە": "ه", // ae ە → ه
  "ھ": "ه", // heh doachashmee ھ → ه
  "ہ": "ه", // heh goal ہ → ه
  "ٱ": "ا", // alef wasla ٱ → ا
  "آ": "ا", // alef with madda آ → ا (in case NFKD left it composed)
  "أ": "ا", // أ → ا
  "إ": "ا", // إ → ا
  "ؤ": "و", // waw with hamza ؤ → و
};

// Tatweel, ZWNJ, ZWJ, ZWSP, LRM, RLM, ALM, BOM.
const REMOVE = /[ـ​‌‍‎‏؜﻿]/g;

function foldDigit(ch: string): string {
  const c = ch.charCodeAt(0);
  if (c >= 0x0660 && c <= 0x0669) return String(c - 0x0660);
  if (c >= 0x06F0 && c <= 0x06F9) return String(c - 0x06F0);
  return ch;
}

/** The comparison form of `text`. Pure; never use the result for display. */
export function normalizeForSearch(text: string): string {
  let s = text.normalize("NFKD").replace(/\p{M}/gu, "").replace(REMOVE, "");
  s = s.replace(/[؀-ۿ]/g, (ch) => LETTER_FOLD[ch] ?? foldDigit(ch));
  s = s.toLowerCase();
  // Every punctuation mark or symbol separates words; the standalone hamza ء carries no letter.
  s = s.replace(/[\p{P}\p{S}ء]/gu, " ");
  return s.replace(/\s+/g, " ").trim();
}

/** How well a folded query matches one folded name. 0 = no match. Higher is better.
 *  Exact > name starts with the query > every query word starts a word of the name > substring. */
export function matchScore(query: string, name: string): number {
  if (!query || !name) return 0;
  if (name === query) return 4;
  if (name.startsWith(query)) return 3;
  const words = name.split(" ");
  const parts = query.split(" ");
  if (parts.every((p) => words.some((w) => w.startsWith(p)))) return 2;
  if (name.includes(query)) return 1;
  return 0;
}
