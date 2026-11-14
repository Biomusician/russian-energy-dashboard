import { test, expect } from "./fixtures";
import type { Page } from "@playwright/test";

/**
 * The global home's first screen, search, Start-here, glossary and navigation (iteration 21).
 * Values come from the payload the page loaded, never typed in here.
 */

// No "Search systems" action: the search box above the actions is the search (iteration 21 review).
const ACTIONS = [/Explore the Gulf littoral/, /Compare systems/, /Russia, Belarus & Crimea \(indexed\)/];
const SEARCH = /Search systems, regions and terms/;

async function manifest(page: Page) {
  return page.evaluate(async () => (await fetch("/data/global/manifest.json")).json());
}

/** The search's own options (the system picker's <option>s share the role). */
function results(page: Page) {
  return page.getByRole("listbox", { name: "Search results" }).getByRole("option");
}

function action(page: Page, name: string | RegExp) {
  return page.getByRole("navigation", { name: "Main actions" }).getByRole(typeof name === "string" ? "button" : "link", { name });
}

test.describe("home first screen", () => {
  for (const [w, h] of [[1600, 900], [390, 844]] as const) {
    test(`at ${w}x${h} the purpose, the search and all three actions are on the first screen`, async ({ app, page }) => {
      await page.setViewportSize({ width: w, height: h });
      await app.open("");
      await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeInViewport();
      await expect(page.getByRole("combobox", { name: SEARCH })).toBeInViewport();
      for (const a of ACTIONS) {
        const el = action(page, a);
        await expect(el).toBeVisible();
        const box = await el.boundingBox();
        expect(box, String(a)).not.toBeNull();
        expect(box!.y + box!.height, `${a} is below the first screen`).toBeLessThanOrEqual(h);
      }
      await expect(page.getByRole("note")).toBeInViewport();
      const sideways = await page.evaluate(() => Math.max(document.documentElement.scrollWidth - window.innerWidth,
        ...[...document.querySelectorAll(".global-page")].map((e) => e.scrollWidth - e.clientWidth)));
      expect(sideways).toBeLessThanOrEqual(0);
    });
  }

  test("the three actions go where they say, and Back returns home each time", async ({ app, page }) => {
    await app.open("");
    await action(page, /Russia, Belarus & Crimea \(indexed\)/).click();
    await expect(page).toHaveURL(/[?&]sys=ru\b/);
    await page.goBack();
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
    await action(page, /Explore the Gulf/).click();
    await expect(page).toHaveURL(/[?&]group=gulf\b/);
    await page.goBack();
    await expect(action(page, /Compare systems/)).toHaveAttribute("href", "?compare=");
    await expect(page.getByRole("navigation", { name: "Main actions" }).getByRole("button", { name: "Search systems" })).toHaveCount(0);
  });

  test("cards: indexed theatre first, countries alphabetical, no count, no score, no status colour", async ({ app, page }) => {
    await app.open("");
    const m = await manifest(page);
    const countries = m.systems.filter((s: { kind: string }) => s.kind === "country");
    expect(countries.length).toBeGreaterThan(0);
    const region = page.getByRole("region", { name: "Monitored systems" });
    const theatre = region.getByRole("article").first();
    await expect(theatre).toContainText("Indexed system");
    // The build that adds record_reviewed must be the one served (a missing field would hide it).
    for (const s of countries) expect(s, s.id).toHaveProperty("record_reviewed");
    let zero = 0;
    for (const s of countries) {
      const card = region.getByRole("article", { name: s.name, exact: true });
      await expect(card).toContainText("No index");
      await expect(card).not.toContainText(/\b\d+ (events?|records?|incidents?|attacks?|held|withheld|disruptions?)\b/i);
      await expect(card).not.toContainText(/Site rebuilt|Reported events, no index|score/i);
      if (s.record_reviewed === null) {
        zero++;
        await expect(card).toContainText("No qualifying records yet");
      } else {
        await expect(card).toContainText(/Record reviewed \d+ \w+ \d{4}/);
      }
      await expect(card).toContainText(/Last researched|No systematic search yet/);
    }
    expect(zero, "the data has systems with no record yet; the zero state must be exercised").toBeGreaterThan(0);
    // Every text colour inside the country cards is a neutral or the link accent: no amber, red or green.
    const colours = await region.locator(".home-card").evaluateAll((cards) => {
      const out = new Set<string>();
      for (const c of cards) for (const el of [c, ...c.querySelectorAll("*")]) out.add(getComputedStyle(el).color);
      return [...out];
    });
    const neutral = await page.evaluate(() => {
      const probe = document.createElement("span");
      document.body.appendChild(probe);
      const out = ["--text", "--text-dim", "--text-faint", "--accent"].map((v) => { probe.style.color = `var(${v})`; return getComputedStyle(probe).color; });
      probe.remove();
      return out;
    });
    for (const c of colours) expect(neutral, c).toContain(c);
  });

  test("tab title follows the route", async ({ app, page }) => {
    await app.open("");
    await expect(page).toHaveTitle(/overview/);
    await action(page, /Russia, Belarus & Crimea \(indexed\)/).click();
    await expect(page).toHaveURL(/sys=ru/);
    await expect(page).not.toHaveTitle(/overview/);
    await page.goBack();
    await expect(page).toHaveTitle(/overview/);
  });
});

test.describe("global search", () => {
  test("finds Iran by ایران, ايران, Iran and iran, shows the alias as written, and opens it", async ({ app, page }) => {
    await app.open("");
    const box = page.getByRole("combobox", { name: SEARCH });
    for (const q of ["ایران", "ايران", "Iran", "iran"]) {
      await box.fill(q);
      await expect(box).toHaveAttribute("aria-expanded", "true");
      const first = page.getByRole("listbox", { name: "Search results" }).getByRole("option").first();
      await expect(first).toContainText("Iran");
      if (q !== "Iran" && q !== "iran") await expect(first).toContainText("ایران");
    }
    await box.press("ArrowDown");
    await expect(box).toHaveAttribute("aria-activedescendant", /opt-0/);
    await box.press("Enter");
    await expect(page).toHaveURL(/[?&]sys=ir\b/);
    await expect(page.getByRole("heading", { name: "Iran", level: 1 })).toBeVisible();
    await page.goBack();
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
  });

  test("/ focuses the search, and its label says so", async ({ app, page }) => {
    await app.open("");
    const box = page.getByRole("combobox", { name: SEARCH });
    await expect(box).toHaveAccessibleName(/press \/ to focus/);
    await page.locator("body").click({ position: { x: 5, y: 600 } });
    await page.keyboard.press("/");
    await expect(box).toBeFocused();
    await expect(box).toHaveValue("");
    // In another field "/" is just a character.
    await page.getByRole("searchbox", { name: "Find a country" }).fill("a/b");
    await expect(page.getByRole("searchbox", { name: "Find a country" })).toHaveValue("a/b");
  });

  test("region names cost one small file, fetched on first focus and never on load", async ({ app, page }) => {
    const seen: { url: string; bytes: number }[] = [];
    page.on("response", async (r) => {
      if (r.url().includes("/data/")) seen.push({ url: new URL(r.url()).pathname, bytes: (await r.body().catch(() => Buffer.alloc(0))).length });
    });
    await app.open("");
    expect(seen.map((s) => s.url)).not.toContain("/data/regions.json");
    expect(seen.filter((s) => s.url.startsWith("/data/systems/"))).toEqual([]);
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.focus();
    await expect.poll(() => seen.filter((s) => s.url === "/data/regions.json").length).toBe(1);
    const cost = seen.find((s) => s.url === "/data/regions.json")!.bytes;
    console.log(`search: region index costs ${cost} bytes on first focus`);
    expect(cost).toBeLessThan(40_000);
    await box.fill("Adygea");
    await expect(results(page).first()).toContainText("Region of Russia");
    await box.fill("Crimea");
    const crimea = results(page).filter({ hasText: "Occupied unit" });
    await expect(crimea).toHaveCount(1);
    await expect(crimea).not.toContainText("Region of Russia");
    expect(seen.filter((s) => s.url.startsWith("/data/systems/"))).toEqual([]);
  });

  test("on a country page its regions join the search and a region result opens that region", async ({ app, page }) => {
    await app.open("?sys=us");
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.fill("Texas");
    await results(page).filter({ hasText: "United States" }).first().click();
    await expect(page).toHaveURL(/r=US-TX/);
    await expect(page.locator(".events-panel h2").first()).toHaveText("Texas");
    await expect(page).toHaveTitle(/United States/);
  });

  test("a glossary concept opens the glossary at that entry", async ({ app, page }) => {
    await app.open("");
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.fill("exposure");
    await results(page).filter({ hasText: "Glossary" }).first().click();
    const dialog = page.getByRole("dialog", { name: "Glossary" });
    await expect(dialog).toBeVisible();
    await expect(page.getByRole("heading", { name: "Exposure", level: 3, exact: true })).toBeFocused();
  });
});

test.describe("Start here", () => {
  test("dismissal persists across a reload and How to read this brings it back", async ({ app, page }) => {
    await app.open("");
    const panel = page.getByRole("region", { name: /Start here/ });
    await expect(panel).toBeVisible();
    await expect(panel.getByRole("listitem")).toHaveCount(6);
    await panel.getByRole("button", { name: "Dismiss" }).click();
    await expect(panel).toHaveCount(0);
    await page.reload();
    await app.mapIdle();
    await expect(page.getByRole("region", { name: /Start here/ })).toHaveCount(0);
    await page.getByRole("button", { name: "How to read this" }).click();
    await expect(page.getByRole("region", { name: /Start here/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Start here/ })).toBeFocused();
    // Reopening clears the memory, so a reload shows it again.
    await page.reload();
    await app.mapIdle();
    await expect(page.getByRole("region", { name: /Start here/ })).toBeVisible();
  });

  test("still works, and never crashes the page, when storage throws", async ({ app, page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(window, "localStorage", { configurable: true, get() { throw new DOMException("denied", "SecurityError"); } });
    });
    await app.open("");
    const panel = page.getByRole("region", { name: /Start here/ });
    await expect(panel).toBeVisible();
    await panel.getByRole("button", { name: "Dismiss" }).click();
    await expect(panel).toHaveCount(0);
    await expect(page.getByRole("status").filter({ hasText: "will show again next time" })).toBeAttached();
    await page.reload();
    await app.mapIdle();
    await expect(page.getByRole("region", { name: /Start here/ })).toBeVisible();
  });

  test("How to read this on a country page goes home with the panel open", async ({ app, page }) => {
    await app.open("");
    await page.getByRole("region", { name: /Start here/ }).getByRole("button", { name: "Dismiss" }).click();
    await app.open("?sys=ca");
    await page.getByRole("button", { name: "How to read this" }).click();
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
    await expect(page.getByRole("region", { name: /Start here/ })).toBeVisible();
  });
});

test.describe("glossary", () => {
  test("opens from the bar, Escape closes it, and focus returns to the button", async ({ app, page }) => {
    await app.open("");
    const button = page.getByRole("button", { name: "Glossary", exact: true });
    await button.click();
    const dialog = page.getByRole("dialog", { name: "Glossary" });
    await expect(dialog).toBeVisible();
    for (const term of ["ESDI", "Exposure", "Transmission burden", "Episode", "Research preview", "Originating statement",
                        "source health", "As published", "Sector state", "Publication safeguard", "No index", "National energy context"]) {
      await expect(dialog).toContainText(term);
    }
    await expect(page.getByRole("heading", { name: "Glossary", level: 2 })).toBeFocused();
    await dialog.locator("summary", { hasText: "More detail" }).first().click();
    await expect(dialog.locator("details").first()).toHaveAttribute("open", "");
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(button).toBeFocused();
  });

  test("How this works opens the method, and ?help=glossary opens the glossary on load", async ({ app, page }) => {
    await app.open("");
    await page.getByRole("button", { name: "How this works" }).first().click();
    await expect(page.getByRole("heading", { name: "How this works", level: 3 })).toBeFocused();
    await page.getByRole("dialog").getByRole("button", { name: "Close" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();
    await page.goto("/?help=glossary");
    await expect(page.getByRole("dialog", { name: "Glossary" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page).not.toHaveURL(/help=glossary/);
  });
});

test.describe("navigation", () => {
  test("a Gulf country's breadcrumb runs Home › Gulf littoral › Iran, and each step goes there", async ({ app, page }) => {
    await app.open("?sys=ir");
    const crumbs = page.getByRole("navigation", { name: "Breadcrumb" });
    await expect(crumbs.getByRole("listitem")).toHaveText(["Home", "Gulf littoral", "Iran"]);
    await expect(crumbs.getByText("Iran")).toHaveAttribute("aria-current", "page");
    await crumbs.getByRole("link", { name: "Gulf littoral" }).click();
    await expect(page).toHaveURL(/[?&]group=gulf\b/);
    await page.getByRole("navigation", { name: "Breadcrumb" }).getByRole("link", { name: "Home", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
    await page.goBack();
    await expect(page).toHaveURL(/[?&]group=gulf\b/);
    await page.goBack();
    await expect(page).toHaveURL(/[?&]sys=ir\b/);
  });

  test("the product title links home from a country page", async ({ app, page }) => {
    await app.open("?sys=us");
    await page.getByRole("link", { name: "Energy Disruption Monitor, home" }).click();
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
    await expect(page).toHaveTitle(/overview/);
  });

  test("Copy view link copies the current URL and announces it", async ({ app, page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await app.open("?sys=ca");
    await page.getByRole("button", { name: "Copy view link" }).click();
    await expect(page.getByRole("status").filter({ hasText: "Link to this view copied." })).toBeVisible();
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    expect(copied).toBe(page.url());
  });

  test("Copy view link falls back when the Clipboard API is missing", async ({ app, page }) => {
    await page.addInitScript(() => { Object.defineProperty(navigator, "clipboard", { configurable: true, get: () => undefined }); });
    await app.open("");
    await page.getByRole("button", { name: "Copy view link" }).click();
    await expect(page.getByRole("status").filter({ hasText: /Link to this view copied|address bar/ })).toBeVisible();
  });
});

test.describe("home lists", () => {
  test("recent evidence: each item links to its country, covered runs collapse, and the caveat is stated", async ({ app, page }) => {
    await app.open("");
    const feed = page.getByRole("region", { name: "Recent evidence" });
    await expect(feed).toContainText("Newest is not worst, and a country with no item here is not a quiet country");
    const items = feed.locator(".feed-item");
    expect(await items.count()).toBeGreaterThan(0);
    for (const href of await feed.locator(".feed-country").evaluateAll((a) => a.map((x) => x.getAttribute("href")))) {
      expect(href).toMatch(/^\?sys=[a-z]{2}$/);
    }
    // No two consecutive items are both campaign-covered records of one country.
    const rows = await items.evaluateAll((els) => els.map((e) => ({
      country: e.querySelector(".feed-country")?.textContent, covered: /safeguards/.test(e.textContent ?? "") })));
    for (let i = 1; i < rows.length; i++) {
      expect(rows[i].covered && rows[i - 1].covered && rows[i].country === rows[i - 1].country, `rows ${i - 1}-${i}`).toBe(false);
    }
    await expect(feed).not.toContainText(/Not summarised in this list/);
    await expect(feed).not.toContainText(/\d+ (records|attacks|held)/);
  });

  test("the wheel over the world map scrolls the page, not the map", async ({ app, page }) => {
    await app.open("");
    const map = page.locator(".world-context [data-map-state]");
    await map.scrollIntoViewIfNeeded();
    const box = (await map.boundingBox())!;
    const before = await page.evaluate(() => document.querySelector(".global-page")!.scrollTop);
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.wheel(0, 400);
    await expect.poll(() => page.evaluate(() => document.querySelector(".global-page")!.scrollTop)).toBeGreaterThan(before);
    await expect(page.locator(".map-wheel-hint")).toContainText("hold Ctrl");
  });

  test("data quality is a set of plain questions with one site-wide build date", async ({ app, page }) => {
    await app.open("");
    const panel = page.getByRole("region", { name: "Data quality" });
    for (const q of ["When was the site last rebuilt?", "How recently were the sources checked?", "How complete is the research?",
                     "What is observed and what is modelled?", "What is withheld?", "Can countries be compared?"]) {
      await expect(panel.getByText(q)).toBeVisible();
    }
    // The theatre is under an active campaign too: its status-delay rule has its own line, with
    // the number read from the served manifest when the build carries it (iteration 21).
    const manifest = await page.evaluate(async () => (await fetch("/data/global/manifest.json")).json());
    const theatre = manifest.systems.find((s: { kind: string }) => s.kind === "theatre");
    const line = panel.locator(".theatre-delay");
    await expect(line).toContainText(theatre.name);
    await expect(line).toContainText("never shows whether a facility is working now");
    await expect(line).toContainText(typeof theatre.status_delay_days === "number"
      ? `only once it is ${theatre.status_delay_days} days old` : "only after a delay");
    await expect(page.locator(".corpus-totals")).toContainText("sources are on the countries' check lists");
  });

  test("home JS and data on load (measured)", async ({ app, page }) => {
    const seen: { url: string; bytes: number }[] = [];
    page.on("response", async (r) => {
      const u = new URL(r.url());
      if (u.pathname.startsWith("/assets/") || u.pathname.startsWith("/data/")) {
        seen.push({ url: u.pathname, bytes: (await r.body().catch(() => Buffer.alloc(0))).length });
      }
    });
    await app.open("");
    await expect.poll(() => seen.length).toBeGreaterThan(4);
    const js = seen.filter((s) => s.url.endsWith(".js"));
    const data = seen.filter((s) => s.url.startsWith("/data/"));
    console.log(`home load: ${js.length} JS files, ${js.reduce((a, s) => a + s.bytes, 0)} bytes; ${data.length} data files, ${data.reduce((a, s) => a + s.bytes, 0)} bytes`);
    console.log(seen.map((s) => `  ${s.url} ${s.bytes}`).join("\n"));
    expect(data.map((s) => s.url).filter((u) => u.startsWith("/data/systems/"))).toEqual([]);
  });
});
