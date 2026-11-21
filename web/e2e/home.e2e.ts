import { test, expect, mapPoint } from "./fixtures";
import type { Page } from "@playwright/test";

/**
 * The global home (iteration 21; map-first since iteration 23): the strip, the map and the panel
 * beside it, one selection shared by the map, the panel, the A to Z list and the search, the
 * search itself, the glossary and navigation. Values come from the payload the page loaded, never
 * typed in here; a country is clicked by its longitude and latitude, and the hover label is read
 * first to prove the pointer is on it.
 */

const SEARCH = /Search systems, regions and terms/;
const DATE = /\b\d{1,2} [A-Z][a-z]{2} \d{4}\b/g;

type Manifest = {
  systems: { id: string; name: string; kind: string; record_reviewed?: string | null; bounds?: number[]; headline?: { value: number } | null }[];
  groups: Record<string, { label: string; slug: string | null; context: string | null; members: string[] }>;
  impact_presence: { countries: string[]; attempt_only: string[] };
};

async function manifest(page: Page): Promise<Manifest> {
  return page.evaluate(async () => (await fetch("/data/global/manifest.json")).json());
}

/** The search's own options. */
function results(page: Page) {
  return page.getByRole("listbox", { name: "Search results" }).getByRole("option");
}

function panel(page: Page) {
  return page.locator("#where-to-explore");
}

function card(page: Page) {
  return page.locator(".sel-card");
}

/** Hover a place and return the label the map shows for it. */
async function hoverAt(page: Page, lon: number, lat: number): Promise<string> {
  const p = await mapPoint(page, lon, lat);
  await page.mouse.move(p.x, p.y);
  await page.waitForTimeout(150);
  return page.locator(".home-map-label").innerText();
}

// Candidate places, each with a point inside it. The test picks the first whose served state is the
// one it needs, so a change in the data moves the test to another country instead of breaking it.
const IMPACT_CANDIDATES: [string, string, number, number][] = [["FRA", "France", 2.5, 46.5], ["DEU", "Germany", 10.4, 51.1], ["BRA", "Brazil", -51, -10], ["AUS", "Australia", 134, -25]];
const EMPTY_CANDIDATES: [string, string, number, number][] = [["MNG", "Mongolia", 103, 46.8], ["TCD", "Chad", 18.7, 15.5], ["NER", "Niger", 9, 17.5], ["BOL", "Bolivia", -64.7, -16.7]];

function pick(m: Manifest, list: [string, string, number, number][], want: "impact" | "empty") {
  const p = new Set(m.impact_presence.countries);
  const a = new Set(m.impact_presence.attempt_only);
  const hit = list.find(([a3]) => (want === "impact" ? p.has(a3) : !p.has(a3) && !a.has(a3)));
  expect(hit, `no ${want} candidate in this build`).toBeTruthy();
  return hit!;
}

test.describe("home first screen", () => {
  for (const [w, h] of [[1440, 900], [1024, 768], [430, 932], [390, 844]] as const) {
    test(`at ${w}x${h} the purpose, the search, the map and the theatre headline open the page`, async ({ app, page }) => {
      await page.setViewportSize({ width: w, height: h });
      await app.open("");
      await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeInViewport();
      await expect(page.getByRole("combobox", { name: SEARCH })).toBeInViewport();
      await expect(page.locator(".home-meta")).toContainText(/Built \d{1,2} \w{3} \d{4} · rebuilt daily · What's new/);
      await expect(page.locator(".home-newhere")).toHaveAttribute("href", "?view=help#start-here");
      // The map is on the first screen, not two to six screens down.
      const map = (await page.locator(".home-map-box").boundingBox())!;
      expect(map.y, "the map starts below the first screen").toBeLessThan(h * 0.5);
      if (w >= 1000) {
        // Desktop: the panel sits beside the map, its theatre row and every system on the first screen.
        await expect(panel(page).locator(".hp-theatre")).toBeInViewport();
        const m = await manifest(page);
        for (const s of m.systems.filter((x) => x.kind === "country")) {
          await expect(panel(page).getByRole("link", { name: new RegExp(`^${s.name}( |$)`) }), s.name).toBeVisible();
        }
      }
      // No drop-down and one search box on the home's first screen.
      await expect(page.locator("main select")).toHaveCount(0);
      await expect(page.locator('main input[type="search"], main input[role="combobox"]')).toHaveCount(1);
      const sideways = await page.evaluate(() => Math.max(document.documentElement.scrollWidth - window.innerWidth,
        ...[...document.querySelectorAll(".global-page")].map((e) => e.scrollWidth - e.clientWidth)));
      expect(sideways).toBeLessThanOrEqual(0);
    });
  }

  test("the first screen does not move while its files arrive (CLS under 0.1)", async ({ app, page }) => {
    // One observer per page load: an init script runs on every navigation, so it is added once.
    await page.addInitScript(() => {
      (window as unknown as { __cls: number }).__cls = 0;
      new PerformanceObserver((l) => {
        for (const e of l.getEntries() as unknown as { value: number; hadRecentInput: boolean }[]) {
          if (!e.hadRecentInput) (window as unknown as { __cls: number }).__cls += e.value;
        }
      }).observe({ type: "layout-shift", buffered: true });
    });
    for (const [w, h] of [[1440, 900], [390, 844]] as const) {
      await page.setViewportSize({ width: w, height: h });
      await app.open("");
      await page.waitForTimeout(500);
      const cls = await page.evaluate(() => (window as unknown as { __cls: number }).__cls);
      console.log(`home CLS at ${w}x${h}: ${cls.toFixed(4)}`);
      expect(cls).toBeLessThan(0.1);
    }
  });

  test("the panel lists the theatre, the atlas, the Gulf row, the twelve systems and Compare, in manifest order, with no count", async ({ app, page }) => {
    await app.open("");
    const m = await manifest(page);
    const theatre = m.systems.find((s) => s.kind === "theatre")!;
    const countries = m.systems.filter((s) => s.kind === "country");
    const names = await panel(page).locator("a.hp-row .hp-name").allInnerTexts();
    const regional = Object.values(m.groups).filter((g) => g.slug && g.context).map((g) => g.label);
    expect(names).toEqual([theatre.name, "Impact Atlas", ...regional, ...countries.map((s) => s.name), "Compare systems"]);
    // The theatre row: its served headline, what it means, and that it is the only index.
    const row = panel(page).locator(".hp-theatre");
    await expect(row.locator(".home-headline-num")).toHaveText(theatre.headline!.value.toFixed(1));
    await expect(row).toContainText("Exposure, not loss and not a percentage; the only system with an index.");
    // Gulf membership is a quiet tag; no maturity anywhere in the panel.
    const gulf = m.groups.gulf_littoral;
    for (const s of countries) {
      const link = panel(page).getByRole("link", { name: new RegExp(`^${s.name}( |$)`) });
      await expect(link.locator(".hp-tag")).toHaveCount(gulf.members.includes(s.id) ? 1 : 0);
    }
    await expect(panel(page)).not.toContainText(/research preview/i);
    // No digit but the headline and dates.
    const text = (await panel(page).locator(".hp-body").innerText()).replace(theatre.headline!.value.toFixed(1), "").replace(DATE, "");
    expect(text).not.toMatch(/\d/);
    // Every row is a real link to an address the site already has.
    const hrefs = await panel(page).locator("a.hp-row").evaluateAll((as) => as.map((a) => a.getAttribute("href")));
    for (const h of hrefs) expect(h).toMatch(/^\?(sys=[a-z]{2}|view=impacts|group=[a-z]+|compare=)$/);
  });

  test("the home has no system picker, no Start here panel and no second country search", async ({ app, page }) => {
    await app.open("");
    await expect(page.getByRole("combobox", { name: "Monitored system", exact: true })).toHaveCount(0);
    await expect(page.getByRole("region", { name: /Start here/ })).toHaveCount(0);
    await expect(page.getByRole("searchbox", { name: "Find a country" })).toHaveCount(0);
  });

  test("tab title follows the route", async ({ app, page }) => {
    await app.open("");
    await expect(page).toHaveTitle(/overview/);
    await panel(page).locator(".hp-theatre").click();
    await expect(page).toHaveURL(/sys=ru/);
    await expect(page).not.toHaveTitle(/overview/);
    await page.goBack();
    await expect(page).toHaveTitle(/overview/);
  });
});

test.describe("map-first navigation (desktop pointer)", () => {
  test("a monitored country opens in one click, and its hover label says so first", async ({ app, page }) => {
    await app.open("");
    expect(await hoverAt(page, 54, 32.5)).toBe("Iran · Monitored country system · no index · Click to open");
    const p = await mapPoint(page, 54, 32.5);
    await page.mouse.click(p.x, p.y);
    await expect(page).toHaveURL(/\?sys=ir$/);
    await expect(page.getByRole("heading", { name: "Iran", level: 1 })).toBeVisible();
  });

  test("the theatre is one unit: Belarus and Crimea both open it, and Crimea is named as Ukrainian", async ({ app, page }) => {
    await app.open("");
    const belarus = await hoverAt(page, 28, 53.5);
    expect(belarus).toContain("Belarus: in the Russia, Belarus & Crimea theatre · The one indexed system");
    const crimea = await hoverAt(page, 34.2, 45.2);
    expect(crimea).toBe("Crimea: Ukrainian territory under Russian occupation · Monitored as a separate unit in the Russia, Belarus & Crimea theatre · Click to open the theatre");
    expect(crimea).not.toMatch(/(region|part|territory) of Russia|Russia's/i);
    const p = await mapPoint(page, 34.2, 45.2);
    await page.mouse.click(p.x, p.y);
    await expect(page).toHaveURL(/\?sys=ru$/);
    await page.goBack();
    await app.mapIdle();
    const b = await mapPoint(page, 28, 53.5);
    await page.mouse.click(b.x, b.y);
    await expect(page).toHaveURL(/\?sys=ru$/);
  });

  test("eastern Russia says it is outside the monitored area and offers the theatre", async ({ app, page }) => {
    await app.open("");
    expect(await hoverAt(page, 140, 63)).toBe("Russia: outside the monitored area · Click for details");
    const p = await mapPoint(page, 140, 63);
    await page.mouse.click(p.x, p.y);
    await expect(card(page)).toContainText("Outside the monitored area");
    await expect(card(page)).toContainText("lies outside the area monitored in the Russia, Belarus & Crimea theatre");
    await expect(card(page).getByRole("link", { name: "Open the Russia, Belarus & Crimea theatre" })).toHaveAttribute("href", "?sys=ru");
    await expect(page).toHaveURL(/\/$/);
  });

  test("an impact-record country selects, says so, and opens the atlas filtered to it", async ({ app, page }) => {
    await app.open("");
    const [a3, name, lon, lat] = pick(await manifest(page), IMPACT_CANDIDATES, "impact");
    expect(await hoverAt(page, lon, lat)).toBe(`${name} · Impact records available · Not a monitored country system · Click for details`);
    const p = await mapPoint(page, lon, lat);
    await page.mouse.click(p.x, p.y);
    await expect(page).toHaveURL(/127\.0\.0\.1:\d+\/$/);
    await expect(card(page).getByRole("heading", { name })).toBeVisible();
    await expect(card(page)).toContainText("Impact records available · Not a monitored country system");
    await expect(page.getByRole("status").filter({ hasText: `Selected ${name}` })).toBeAttached();
    const link = card(page).getByRole("link", { name: "Open impact records" });
    await expect(link).toHaveAttribute("href", `?view=impacts&f.country=${a3}`);
    await link.click();
    await expect(page).toHaveURL(new RegExp(`\\?view=impacts&f\\.country=${a3}$`));
    // The atlas honours the filter: its country filter is on, naming the country.
    await expect(page.getByRole("heading", { name: "Impact atlas", level: 1 })).toBeVisible();
    await expect(page.locator(".rf-count")).toContainText(name);
  });

  test("a country with no system and no record never says 'no disruption' and offers no dashboard", async ({ app, page }) => {
    await app.open("");
    const [, name, lon, lat] = pick(await manifest(page), EMPTY_CANDIDATES, "empty");
    expect(await hoverAt(page, lon, lat)).toBe(`${name} · No dedicated monitored system · No published impact record · Click for details`);
    const p = await mapPoint(page, lon, lat);
    await page.mouse.click(p.x, p.y);
    await expect(card(page)).toContainText(`This site has not searched ${name} systematically, so nothing here says whether disruptions happened.`);
    await expect(card(page)).not.toContainText(/no (reported )?disruptions?\b|nothing happened/i);
    await expect(card(page).locator(".sel-actions a")).toHaveCount(0);
    await expect(page).toHaveURL(/127\.0\.0\.1:\d+\/$/);
  });

  test("an attempt-only country links the atlas unfiltered, never with its country filter", async ({ app, page }) => {
    await app.open("");
    const m = await manifest(page);
    type F = { properties: { a3: string; name: string; system_id: string | null } };
    const world = await page.evaluate(async () => (await fetch("/data/global/world.geojson")).json()) as { features: F[] };
    // An attempt-only country outside every system (one inside the theatre opens the theatre instead).
    const a3 = m.impact_presence.attempt_only.find((c) => {
      const fs = world.features.filter((f) => f.properties.a3 === c);
      return fs.length > 0 && fs.every((f) => !f.properties.system_id);
    });
    test.skip(!a3, "every attempt-only country is inside a system in this build");
    const name = world.features.find((f) => f.properties.a3 === a3)!.properties.name;
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.fill(name);
    await expect(results(page).first()).toContainText("No dedicated monitored system · No published impact record · selects it on the map");
    await box.press("Enter");
    await expect(card(page)).toContainText("an attempt is not a disruption");
    const hrefs = await card(page).locator("a").evaluateAll((as) => as.map((a) => a.getAttribute("href") ?? ""));
    expect(hrefs).toContain("?view=impacts");
    for (const h of hrefs) expect(h).not.toContain("f.country");
  });

  test("Show on map selects the Gulf littoral from the manifest, lists its members and zooms to them", async ({ app, page }) => {
    await app.open("");
    const m = await manifest(page);
    const g = m.groups.gulf_littoral;
    const before = await page.locator(".home-map-box [data-map-view]").getAttribute("data-map-view");
    await panel(page).getByRole("button", { name: /Show on map/ }).click();
    await expect(card(page).getByRole("heading", { name: g.label })).toBeVisible();
    const names = g.members.map((id) => m.systems.find((s) => s.id === id)!.name);
    await expect(card(page).locator(".sel-links a")).toHaveText(names);
    await expect(card(page).getByRole("link", { name: `Open the ${g.label} overview` })).toHaveAttribute("href", `?group=${g.slug}`);
    await expect.poll(() => page.locator(".home-map-box [data-map-view]").getAttribute("data-map-view")).not.toBe(before);
    await app.mapIdle();
    // At the group's zoom a small member is an ordinary click target.
    const view = (await page.locator(".home-map-box [data-map-view]").getAttribute("data-map-view"))!.split(",").map(Number);
    expect(view[2]).toBeGreaterThan(3);
    await card(page).getByRole("link", { name: `Open the ${g.label} overview` }).click();
    await expect(page).toHaveURL(/\?group=gulf$/);
  });

  test("Escape closes the card and gives focus back to what opened it", async ({ app, page }) => {
    await app.open("");
    const az = panel(page).locator(".hp-az");
    await az.locator("summary").click();
    const [, name] = pick(await manifest(page), EMPTY_CANDIDATES, "empty");
    const item = az.getByRole("button", { name, exact: true });
    await item.focus();
    await page.keyboard.press("Enter");
    await expect(card(page)).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(card(page)).toHaveCount(0);
    await expect(item).toBeFocused();
  });
});

test.describe("one selection, kept in history", () => {
  test("the search and the map select the same card, and an option says what choosing it does", async ({ app, page }) => {
    await app.open("");
    const [a3, name, lon, lat] = pick(await manifest(page), IMPACT_CANDIDATES, "impact");
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.fill(name);
    const opt = results(page).filter({ hasText: name }).first();
    await expect(opt).toContainText("Impact records available · Not a monitored country system · selects it on the map");
    await box.press("Enter");
    await expect(card(page)).toHaveAttribute("data-sel", a3);
    const fromSearch = await card(page).innerText();
    await page.keyboard.press("Escape");
    const p = await mapPoint(page, lon, lat);
    await page.mouse.click(p.x, p.y);
    await expect(card(page)).toHaveAttribute("data-sel", a3);
    expect(await card(page).innerText()).toBe(fromSearch);
    // A monitored system's option says it opens; the theatre's says it is the indexed one.
    await box.fill("Iran");
    await expect(results(page).first()).toContainText("Monitored country system · no index · opens it");
    await expect(results(page).first()).not.toContainText(/research preview/i);
  });

  test("Back restores the selection and the focus, Forward returns, and no address carries sel=", async ({ app, page }) => {
    const urls: string[] = [];
    page.on("framenavigated", (f) => { if (f === page.mainFrame()) urls.push(f.url()); });
    await app.open("");
    const [a3, name] = pick(await manifest(page), IMPACT_CANDIDATES, "impact");
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.fill(name);
    await box.press("Enter");
    await expect(card(page)).toHaveAttribute("data-sel", a3);
    urls.push(page.url());
    await card(page).getByRole("link", { name: "Open impact records" }).click();
    await expect(page).toHaveURL(new RegExp(`f\\.country=${a3}`));
    urls.push(page.url());
    await page.goBack();
    await expect(card(page)).toHaveAttribute("data-sel", a3);
    await expect(card(page).getByRole("link", { name: "Open impact records" })).toBeFocused();
    expect(page.url()).toMatch(/127\.0\.0\.1:\d+\/$/);
    await page.goForward();
    await expect(page).toHaveURL(new RegExp(`f\\.country=${a3}`));
    await page.goBack();
    // A system opened from the map: Back focuses its row and marks it as last opened.
    await page.keyboard.press("Escape");
    await app.mapIdle();
    const p = await mapPoint(page, 54, 32.5);
    await page.mouse.click(p.x, p.y);
    await expect(page).toHaveURL(/\?sys=ir$/);
    urls.push(page.url());
    await page.goBack();
    const row = panel(page).getByRole("link", { name: /^Iran/ });
    await expect(row).toBeFocused();
    await expect(row).toHaveClass(/opened/);
    urls.push(page.url());
    for (const u of urls) expect(u).not.toContain("sel=");
  });

  test("deep links open exactly the views they always did", async ({ app, page }) => {
    for (const [q, heading] of [["?sys=ir", "Iran"], ["?sys=ru", null], ["?group=gulf", "Gulf littoral overview"],
                                ["?view=impacts&f.country=FRA", "Impact atlas"], ["?compare=us,ca", null]] as const) {
      await page.goto(`/${q}`);
      await expect(page).toHaveURL(new RegExp(`${q.replace(/[?.]/g, "\\$&")}$`));
      if (heading) await expect(page.getByRole("heading", { name: heading, level: 1 })).toBeVisible();
      else await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toHaveCount(0);
    }
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
    expect(app.errors).toEqual([]);
  });

  test("small countries have text routes: the Bahrain row and the Bahrain search result open it", async ({ app, page }) => {
    await app.open("");
    await panel(page).getByRole("link", { name: /^Bahrain/ }).click();
    await expect(page).toHaveURL(/\?sys=bh$/);
    await page.goBack();
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.fill("Bahrain");
    await box.press("ArrowDown");
    await box.press("Enter");
    await expect(page).toHaveURL(/\?sys=bh$/);
  });

  test("the A to Z list holds every country on the map, each reachable by keyboard", async ({ app, page }) => {
    await app.open("");
    const world = await page.evaluate(async () => (await fetch("/data/global/world.geojson")).json());
    const a3s = new Set<string>(world.features.filter((f: { properties: { status: string } }) => f.properties.status !== "occupied")
      .map((f: { properties: { a3: string } }) => f.properties.a3));
    const az = panel(page).locator(".hp-az");
    await az.locator("summary").focus();
    await page.keyboard.press("Enter");
    const items = az.locator("button.hp-az-item");
    await expect(items).toHaveCount(a3s.size);
    const codes = await items.evaluateAll((bs) => bs.map((b) => b.getAttribute("data-ret")!.slice(3)));
    expect(new Set(codes)).toEqual(a3s);
    await items.first().focus();
    await page.keyboard.press("Tab");
    await expect(items.nth(1)).toBeFocused();
  });
});

test.describe("phone: a tap opens a sheet first", () => {
  for (const [w, h] of [[390, 844], [430, 932]] as const) {
    test.describe(`${w}x${h}`, () => {
      test.use({ viewport: { width: w, height: h }, hasTouch: true, isMobile: true });

      test("tapping a system shows its sheet, leaves the address alone, and the sheet button opens it", async ({ app, page }) => {
        await app.open("");
        const p = await mapPoint(page, 78, 22);
        await page.touchscreen.tap(p.x, p.y);
        const sheet = page.locator(".sel-sheet");
        await expect(sheet).toBeVisible();
        await expect(sheet.getByRole("heading", { name: "India" })).toBeVisible();
        await expect(page).toHaveURL(/127\.0\.0\.1:\d+\/$/);
        // Non-modal: the map is still there and usable; no hover-only text is left on a touch screen.
        await expect(page.locator(".home-map-label")).toBeHidden();
        const open = sheet.getByRole("link", { name: "Open India" });
        expect((await open.boundingBox())!.height).toBeGreaterThanOrEqual(43.5);
        const text = (await sheet.innerText()).replace(DATE, "");
        expect(text).not.toMatch(/\d/);
        await open.click();
        await expect(page).toHaveURL(/\?sys=in$/);
      });

      test("Escape or Close dismisses the sheet", async ({ app, page }) => {
        await app.open("");
        const p = await mapPoint(page, 78, 22);
        await page.touchscreen.tap(p.x, p.y);
        await page.locator(".sel-sheet").getByRole("button", { name: /^Close/ }).click();
        await expect(page.locator(".sel-sheet")).toHaveCount(0);
      });
    });
  }
});

test.describe("without WebGL", () => {
  test("the panel, the search and the theatre link still work", async ({ app, page }) => {
    await page.addInitScript(() => {
      const real = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, kind: string, ...rest: unknown[]) {
        if (/webgl/i.test(kind)) return null;
        return (real as (...a: unknown[]) => unknown).call(this, kind, ...rest);
      } as typeof HTMLCanvasElement.prototype.getContext;
    });
    app.allowConsoleError(/webgl/i);
    await page.goto("/");
    await expect(page.locator(".home-map-box .map-load")).toHaveAttribute("data-map-load", "failed");
    await expect(page.locator(".home-map-box .map-load")).toContainText("The list beside the map has every destination");
    // The search selects a country without the map.
    const [a3, name] = pick(await manifest(page), IMPACT_CANDIDATES, "impact");
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.fill(name);
    await box.press("Enter");
    await expect(card(page)).toHaveAttribute("data-sel", a3);
    await page.keyboard.press("Escape");
    // The A to Z list and the theatre row work too.
    await panel(page).locator(".hp-theatre").click();
    await expect(page).toHaveURL(/\?sys=ru$/);
  });
});

test.describe("map modes", () => {
  test("National energy is the second mode: its legend, metric, outline note and PNG; the default mode loads no figures", async ({ app, page }) => {
    const asked: string[] = [];
    page.on("request", (r) => { if (r.url().includes("/data/")) asked.push(new URL(r.url()).pathname); });
    await app.open("");
    expect(asked).not.toContain("/data/global/energy_context.json");
    const legend = page.getByLabel("Map legend");
    await expect(legend).toContainText("Monitored system: the theatre or a country system (one colour; not a measure");
    await expect(legend).toContainText("Crimea and Sevastopol: Ukrainian territory under Russian occupation");
    await page.getByRole("button", { name: "National energy" }).click();
    await expect(page.getByRole("button", { name: "National energy" })).toHaveAttribute("aria-pressed", "true");
    await app.mapIdle();
    await expect(legend).toContainText("Thick outline: systematically monitored");
    await expect(page.getByLabel("Map metric")).toBeVisible();
    expect(asked.filter((u) => u === "/data/global/energy_context.json")).toHaveLength(1);
    const dl = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download PNG" }).click();
    expect((await dl).suggestedFilename()).toMatch(/^global-energy-context-total_production-\d{4}\.png$/);
    await page.getByRole("button", { name: "Where to explore" }).click();
    await expect(page.getByLabel("Map metric")).toHaveCount(0);
  });
});

test.describe("global search", () => {
  test("finds Iran by ایران, ايران, Iran and iran, shows the alias as written, and opens it", async ({ app, page }) => {
    await app.open("");
    const box = page.getByRole("combobox", { name: SEARCH });
    for (const q of ["ایران", "ايران", "Iran", "iran"]) {
      await box.fill(q);
      await expect(box).toHaveAttribute("aria-expanded", "true");
      const first = results(page).first();
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

  test("every country is found: Australia, the United Kingdom by UK, and Belarus inside the theatre", async ({ app, page }) => {
    await app.open("");
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.fill("Australia");
    await expect(results(page).first()).toContainText("Australia");
    await expect(results(page).first()).toContainText("selects it on the map");
    await box.fill("UK");
    await expect(results(page).filter({ hasText: "United Kingdom" })).toHaveCount(1);
    await box.fill("Belarus");
    await expect(results(page).filter({ hasText: "In the Russia, Belarus & Crimea theatre · opens it" })).toHaveCount(1);
    // No digit in any option but a date.
    await box.fill("a");
    for (const t of await results(page).allInnerTexts()) expect(t.replace(DATE, "")).not.toMatch(/\d/);
  });

  test("/ focuses the search, and its label says so", async ({ app, page }) => {
    await app.open("");
    const box = page.getByRole("combobox", { name: SEARCH });
    await expect(box).toHaveAccessibleName(/press \/ to focus/);
    await page.locator(".home-meta").click({ position: { x: 2, y: 2 } });
    await page.keyboard.press("/");
    await expect(box).toBeFocused();
    await expect(box).toHaveValue("");
    // In a field "/" is just a character.
    await page.keyboard.type("a/b");
    await expect(box).toHaveValue("a/b");
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
    // The world map is already loaded on the home: the search reuses it.
    expect(seen.filter((s) => s.url === "/data/global/world.geojson")).toHaveLength(1);
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

  test("from a country page, a country without a system opens the home with it selected", async ({ app, page }) => {
    await app.open("?sys=us");
    const [a3, name] = pick(await manifest(page), IMPACT_CANDIDATES, "impact");
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.fill(name);
    await expect(results(page).filter({ hasText: name }).first()).toContainText("selects it on the map");
    await box.press("Enter");
    await expect(page).toHaveURL(/127\.0\.0\.1:\d+\/$/);
    await expect(card(page)).toHaveAttribute("data-sel", a3);
    await page.goBack();
    await expect(page).toHaveURL(/\?sys=us$/);
  });

  test("a glossary concept opens its entry on the Help page, and Back returns", async ({ app, page }) => {
    await app.open("");
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.fill("exposure");
    await results(page).filter({ hasText: "Glossary" }).first().click();
    await expect(page).toHaveURL(/\?view=help#g-exposure$/);
    await expect(page.getByRole("heading", { name: "Exposure", level: 3, exact: true })).toBeFocused();
    await page.goBack();
    await expect(page).toHaveURL(/127\.0\.0\.1:\d+\/$/);
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
  });
});

test.describe("Help link", () => {
  test("Help on a country page opens Help without losing the page: Back returns to it", async ({ app, page }) => {
    await app.open("?sys=ca");
    await page.locator(".global-nav").getByRole("link", { name: "Help", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Help: how to read this site", level: 1 })).toBeVisible();
    await page.goBack();
    await expect(page).toHaveURL(/\?sys=ca$/);
    await expect(page.getByRole("heading", { name: "Canada", level: 1 })).toBeVisible();
  });
});

test.describe("glossary", () => {
  test("lives on the Help page: every term, each with More detail, reached from the old link", async ({ page }) => {
    await page.goto("/?help=glossary");
    await expect(page).toHaveURL(/\?view=help#glossary$/);
    const glossary = page.locator("section[aria-labelledby=glossary]");
    for (const term of ["ESDI", "Exposure", "Transmission burden", "Episode", "Research preview", "Originating statement",
                        "Source health", "As published", "Sector state", "Publication safeguards", "No index", "National energy context"]) {
      await expect(glossary).toContainText(term);
    }
    await expect(page.getByRole("heading", { name: "Glossary (A–Z)", level: 2 })).toBeFocused();
    await glossary.locator("summary", { hasText: "More detail" }).first().click();
    await expect(glossary.locator("details").first()).toHaveAttribute("open", "");
  });

  test("New here? on the home page opens Help at Start here", async ({ app, page }) => {
    await app.open("");
    await page.getByRole("link", { name: "New here? How to use this dashboard" }).click();
    await expect(page).toHaveURL(/\?view=help#start-here$/);
    await expect(page.getByRole("heading", { name: "Start here", level: 2 })).toBeFocused();
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

  test("the skip link takes the first Tab and moves focus into the page", async ({ app, page }) => {
    await app.open("");
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("main")).toBeFocused();
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

test.describe("below the map, one click away", () => {
  test("six collapsed parts in order, each opening its content", async ({ app, page }) => {
    await app.open("");
    const folds = page.locator(".home-below > details.home-fold");
    await expect(folds.locator("> summary")).toHaveText([
      "Recent published evidence", "What's new in the data", "Data freshness and quality",
      "Why these systems, and how this works", "The country record so far", "National energy figures table"]);
    for (const d of await folds.all()) await expect(d).not.toHaveAttribute("open", "");
  });

  test("recent evidence: each item links to its country, covered runs collapse, and the caveat is stated", async ({ app, page }) => {
    await app.open("");
    await page.locator("#fold-recent > summary").click();
    const feed = page.getByRole("region", { name: "Recent evidence" });
    await expect(feed).toContainText("Newest is not worst, and a country with no item here is not a quiet country");
    const items = feed.locator(".feed-item");
    expect(await items.count()).toBeGreaterThan(0);
    for (const href of await feed.locator(".feed-country").evaluateAll((a) => a.map((x) => x.getAttribute("href")))) {
      expect(href).toMatch(/^\?sys=[a-z]{2}$/);
    }
    const rows = await items.evaluateAll((els) => els.map((e) => ({
      country: e.querySelector(".feed-country")?.textContent, covered: /safeguards/.test(e.textContent ?? "") })));
    for (let i = 1; i < rows.length; i++) {
      expect(rows[i].covered && rows[i - 1].covered && rows[i].country === rows[i - 1].country, `rows ${i - 1}-${i}`).toBe(false);
    }
    await expect(feed).not.toContainText(/Not summarised in this list/);
    await expect(feed).not.toContainText(/\d+ (records|attacks|held)/);
  });

  test("the wheel over the world map scrolls the page, not the map", async ({ app, page }) => {
    await page.setViewportSize({ width: 1024, height: 600 });
    await app.open("");
    const map = page.locator(".home-map-box [data-map-state]");
    const box = (await map.boundingBox())!;
    const before = await page.evaluate(() => document.querySelector(".global-page")!.scrollTop);
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.wheel(0, 400);
    await expect.poll(() => page.evaluate(() => document.querySelector(".global-page")!.scrollTop)).toBeGreaterThan(before);
    await expect(page.locator(".home-map .map-credits")).toContainText("Ctrl");
  });

  test("data quality is a set of plain questions with one site-wide build date", async ({ app, page }) => {
    await app.open("");
    await page.locator("#fold-quality > summary").click();
    const panelDq = page.getByRole("region", { name: "Data quality" });
    for (const q of ["When was the site last rebuilt?", "How recently were the sources checked?", "How complete is the research?",
                     "What is observed and what is modelled?", "What is withheld?", "Can countries be compared?"]) {
      await expect(panelDq.getByText(q)).toBeVisible();
    }
    const m = await page.evaluate(async () => (await fetch("/data/global/manifest.json")).json());
    const theatre = m.systems.find((s: { kind: string }) => s.kind === "theatre");
    const line = panelDq.locator(".theatre-delay");
    await expect(line).toContainText(theatre.name);
    await expect(line).toContainText("never shows whether a facility is working now");
    await expect(line).toContainText(typeof theatre.status_delay_days === "number"
      ? `only once it is ${theatre.status_delay_days} days old` : "only after a delay");
  });

  test("the country record states what its totals mostly reflect and carries no recovery rate", async ({ app, page }) => {
    await app.open("");
    await page.locator("#fold-corpus > summary").click();
    const totals = page.locator(".corpus-totals");
    await expect(totals).toContainText("sources are on the countries' check lists");
    await expect(totals).toContainText("These totals mostly reflect how much each country reports publicly, not how much happened.");
    await expect(totals).not.toContainText(/came back|recovery|independently reviewed/i);
  });

  test("home JS and data on load (measured): no impact file, no national figures, no country file", async ({ app, page }) => {
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
    const urls = data.map((s) => s.url);
    expect(urls.filter((u) => u.startsWith("/data/systems/"))).toEqual([]);
    expect(urls.filter((u) => /impacts|regional_context|evidence_confidence/.test(u))).toEqual([]);
    expect(urls).not.toContain("/data/global/energy_context.json");
  });
});
