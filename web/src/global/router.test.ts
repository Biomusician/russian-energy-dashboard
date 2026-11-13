import { describe, expect, it } from "vitest";
import { MAX_COMPARE, compareHref, hrefFor, routeFor } from "./router";

describe("routeFor", () => {
  it("opens the global home on a bare URL", () => {
    expect(routeFor("")).toEqual({ view: "home" });
    expect(routeFor("?")).toEqual({ view: "home" });
    expect(routeFor("?utm_source=x")).toEqual({ view: "home" });
  });

  it("opens the theatre for every link shared before iteration 14", () => {
    for (const q of ["?m=ev", "?a=30", "?d=2024-06-01", "?r=RU-PER", "?cls=-", "?cau=kinetic_strike",
                     "?con=confirmed", "?ly=oil", "?cam=45,55,4", "?cmp=RU-PER,RU-SAM"]) {
      expect(routeFor(q), q).toEqual({ view: "theatre" });
    }
  });

  it("honours sys, case-insensitively", () => {
    expect(routeFor("?sys=ru")).toEqual({ view: "theatre" });
    expect(routeFor("?sys=RU&m=ev")).toEqual({ view: "theatre" });
    expect(routeFor("?sys=us")).toEqual({ view: "country", id: "us" });
    // sys wins over theatre parameters: a country link carrying r= is a country link.
    expect(routeFor("?sys=us&r=US-TX")).toEqual({ view: "country", id: "us" });
  });

  it("passes unknown ids through to be refused by the view, never as object keys", () => {
    expect(routeFor("?sys=constructor")).toEqual({ view: "country", id: "constructor" });
    expect(routeFor("?sys=__proto__")).toEqual({ view: "country", id: "__proto__" });
    expect(routeFor("?sys=")).toEqual({ view: "home" });
  });
});

describe("regional overviews", () => {
  it("opens a group by its slug", () => {
    expect(routeFor("?group=gulf")).toEqual({ view: "group", id: "gulf" });
    expect(routeFor("?group=GULF")).toEqual({ view: "group", id: "gulf" });
  });

  it("lets a system win over a group, and a group over old theatre parameters", () => {
    expect(routeFor("?sys=ir&group=gulf")).toEqual({ view: "country", id: "ir" });
    expect(routeFor("?group=gulf&r=RU-PER")).toEqual({ view: "group", id: "gulf" });
    expect(routeFor("?group=")).toEqual({ view: "home" });
  });

  it("passes an unknown slug through to be refused by the view", () => {
    expect(routeFor("?group=__proto__")).toEqual({ view: "group", id: "__proto__" });
  });
});

describe("hrefFor", () => {
  it("builds system links and the home link", () => {
    expect(hrefFor("us")).toBe("?sys=us");
    expect(hrefFor(null)).toBe("?");
  });
});

function ids(q: string): string[] {
  const r = routeFor(q);
  if (r.view !== "compare") throw new Error(`${q} opened ${r.view}`);
  return r.ids;
}

describe("the comparison workspace URL", () => {

  it("opens with the reader's ids in the reader's order, lower-cased", () => {
    expect(ids("?compare=us,ca,sa")).toEqual(["us", "ca", "sa"]);
    expect(ids("?compare=SA,Us")).toEqual(["sa", "us"]);
    expect(ids("?compare=%20ca%20,%20in")).toEqual(["ca", "in"]);
  });

  it("drops duplicates (after case folding) and empty entries", () => {
    expect(ids("?compare=us,US,us,,ca,")).toEqual(["us", "ca"]);
    expect(ids("?compare=")).toEqual([]);
    expect(ids("?compare")).toEqual([]);
    expect(ids("?compare=,,,")).toEqual([]);
  });

  it("treats an encoded comma as a separator and merges repeated parameters", () => {
    expect(ids("?compare=us%2Cca")).toEqual(["us", "ca"]);
    expect(ids("?compare=us&compare=ca,us")).toEqual(["us", "ca"]);
  });

  it("keeps hostile ids as plain strings for the view to refuse", () => {
    expect(ids("?compare=__proto__,constructor,us")).toEqual(["__proto__", "constructor", "us"]);
    expect(ids("?compare=%3Cscript%3E")).toEqual(["<script>"]);
  });

  it("bounds a long link before the view resolves it", () => {
    const many = Array.from({ length: 40 }, (_, i) => `x${i}`).join(",");
    expect(ids(`?compare=${many}`)).toHaveLength(12);
  });

  it("loses to sys and group, and wins over the theatre's old parameters", () => {
    expect(routeFor("?sys=us&compare=ca,sa")).toEqual({ view: "country", id: "us" });
    expect(routeFor("?sys=ru&compare=ca,sa")).toEqual({ view: "theatre" });
    expect(routeFor("?group=gulf&compare=ca,sa")).toEqual({ view: "group", id: "gulf" });
    expect(routeFor("?compare=ca,sa&r=RU-PER")).toEqual({ view: "compare", ids: ["ca", "sa"] });
    // The theatre's own region comparison is `cmp`, not `compare`.
    expect(routeFor("?cmp=RU-PER,RU-SAM")).toEqual({ view: "theatre" });
  });
});

describe("compareHref", () => {
  it("writes the selection and nothing else, in order", () => {
    expect(compareHref(["us", "ca", "sa"])).toBe("?compare=us,ca,sa");
    expect(compareHref(["sa", "us"])).toBe("?compare=sa,us");
    expect(compareHref([])).toBe("?compare=");
  });

  it("normalises: case, duplicates, empties, and at most four", () => {
    expect(compareHref(["US", "us", "", " ca "])).toBe("?compare=us,ca");
    expect(compareHref(["a", "b", "c", "d", "e", "f"])).toBe(`?compare=a,b,c,d`);
    expect(MAX_COMPARE).toBe(4);
  });

  it("round-trips through routeFor for any selection", () => {
    const pool = ["us", "ca", "sa", "cn", "in", "ru", "ae", "US", "__proto__", "a b", "x&y=z", "é"];
    let seed = 7;
    const rnd = () => { seed = (seed * 1103515245 + 12345) % 2 ** 31; return seed / 2 ** 31; };
    let checked = 0;
    for (let n = 0; n < 300; n++) {
      const sel = Array.from({ length: Math.floor(rnd() * 7) }, () => pool[Math.floor(rnd() * pool.length)]);
      const href = compareHref(sel);
      const back = ids(href);
      const expected = [...new Set(sel.map((s) => s.trim().toLowerCase()).filter(Boolean))].slice(0, 4);
      expect(back, href).toEqual(expected);
      expect(compareHref(back)).toBe(href);
      checked++;
    }
    expect(checked).toBe(300);
  });
});
