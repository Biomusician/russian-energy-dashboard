import { describe, expect, it } from "vitest";
import { hrefFor, routeFor } from "./router";

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
