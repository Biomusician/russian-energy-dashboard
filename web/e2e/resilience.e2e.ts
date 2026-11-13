import { test, expect } from "./fixtures";

/**
 * Route performance and failure containment, in a real browser (iteration 21).
 *
 * WHAT IS FIXED HERE. Timings vary run to run on software WebGL, so this file asserts the
 * structural facts that make a route fast and keep a failure local: which files a route fetches,
 * that a file is fetched once per page, that the home's first screen does not jump, and that a
 * broken or missing file costs the view (or panel) that reads it and nothing else.
 *
 * Every broken file is broken in the browser only (route interception); nothing on disk changes.
 * Each test ends by proving the rest of the app still works: another view opens and draws.
 */

type Page = import("@playwright/test").Page;

/** Every same-origin data file the page requests from now on, in order. */
function recordData(page: Page): string[] {
  const seen: string[] = [];
  page.on("request", (r) => {
    const u = new URL(r.url());
    if (u.pathname.includes("/data/")) seen.push(u.pathname.replace(/^.*\/data\//, ""));
  });
  return seen;
}

const picker = (page: Page) => page.getByRole("combobox", { name: "Monitored system" });

/** The rest of the app still works: another country opens and its map draws, then the theatre. */
async function restStillWorks(page: Page, app: { mapIdle: () => Promise<void> }, country = ["ca", "Canada"]) {
  await picker(page).selectOption(country[0]);
  await expect(page.getByRole("heading", { name: country[1], level: 1 })).toBeVisible();
  await app.mapIdle();
  await picker(page).selectOption("ru");
  await app.mapIdle();
  await expect(page.locator(".ribbon")).toContainText("ESDI");
}

// Whatever a file says, the response is valid JSON of the wrong shape: the case a parse error does
// not catch, and the one that used to throw while rendering.
const wrongShape = (route: import("@playwright/test").Route, body: unknown) =>
  route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

test.describe("what each route fetches", () => {
  test("the home loads no country payload, and a hover fetches exactly one country", async ({ app, page }) => {
    const seen = recordData(page);
    await app.open("");
    await page.waitForLoadState("networkidle");
    expect(seen.length, "the home fetched no data at all: this test proved nothing").toBeGreaterThan(0);
    expect(seen.filter((p) => p.startsWith("systems/")), "the home fetched a country payload").toEqual([]);
    expect(seen.filter((p) => /events\.json$/.test(p))).toEqual([]);
    // Each home file once.
    expect(seen.length).toBe(new Set(seen).size);

    // An explicit hover on one card prefetches that country, and only that one.
    await app.button("Open Canada").hover();
    await expect.poll(() => seen.filter((p) => p.startsWith("systems/")).sort())
      .toEqual(["systems/ca/events.json", "systems/ca/regions.geojson", "systems/ca/system.json"]);
    await app.button("Open Canada").click();
    await expect(page.getByRole("heading", { name: "Canada", level: 1 })).toBeVisible();
    await app.mapIdle();
    // Opening it used the prefetched files: nothing for Canada was fetched twice.
    const ca = seen.filter((p) => p.startsWith("systems/ca/"));
    expect(ca.length).toBe(3);
  });

  test("hovering a country whose payload fails leaves the home untouched, and the failure is not kept", async ({ app, page }) => {
    app.allowConsoleError(/status of 500/);
    // The first request fails, as a flaky connection would; later ones succeed.
    let calls = 0;
    await page.route("**/data/systems/bh/events.json", (r) => (++calls === 1 ? r.fulfill({ status: 500, body: "" }) : r.continue()));
    await app.open("");
    const failed = page.waitForResponse("**/data/systems/bh/events.json");
    await app.button("Open Bahrain").hover();
    await failed;
    await page.waitForLoadState("networkidle");
    // No unhandled rejection reached the page, and the home is unchanged.
    expect(app.errors).toEqual([]);
    await expect(page.getByRole("alert")).toHaveCount(0);
    await expect(page.getByRole("article").first()).toBeVisible();
    // The failed prefetch was not kept: opening Bahrain asks again, and this time it loads.
    await app.button("Open Bahrain").click();
    await expect(page.getByRole("heading", { name: "Bahrain", level: 1 })).toBeVisible();
    await app.mapIdle();
    await expect(page.getByRole("alert")).toHaveCount(0);
    expect(calls).toBe(2);
    await restStillWorks(page, app);
  });

  test("moving between countries and overviews never fetches the manifest or the world map again", async ({ app, page }) => {
    const seen = recordData(page);
    await app.open("?sys=ir");
    for (const [id, name] of [["sa", "Saudi Arabia"], ["kw", "Kuwait"], ["ir", "Iran"]]) {
      await picker(page).selectOption(id);
      await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
      await app.mapIdle();
    }
    await picker(page).selectOption("group:gulf");
    await app.mapIdle();
    await picker(page).selectOption("");
    await app.mapIdle();
    await picker(page).selectOption("group:gulf");
    await app.mapIdle();
    const count = (f: string) => seen.filter((p) => p === f).length;
    expect(count("global/manifest.json")).toBe(1);
    expect(count("global/world.geojson")).toBe(1);
    expect(count("global/gulf.json")).toBe(1);
    // Returning to Iran used the files already loaded.
    expect(count("systems/ir/events.json")).toBe(1);
  });

  test("a country page does not fetch the national context until a tab that shows it is opened", async ({ app, page }) => {
    const seen = recordData(page);
    await app.open("?sys=us");
    await page.waitForLoadState("networkidle");
    expect(seen).toContain("systems/us/events.json");
    expect(seen).not.toContain("global/energy_context.json");
    await page.getByRole("button", { name: "Energy context" }).click();
    await expect(page.locator(".country-side")).toContainText("National energy picture");
    expect(seen.filter((p) => p === "global/energy_context.json")).toHaveLength(1);
  });

  test("the home's first screen does not jump while its files arrive", async ({ app, page }) => {
    await page.addInitScript(() => {
      const w = window as unknown as { __cls: number };
      w.__cls = 0;
      new PerformanceObserver((l) => {
        for (const e of l.getEntries() as unknown as { value: number; hadRecentInput: boolean }[]) if (!e.hadRecentInput) w.__cls += e.value;
      }).observe({ type: "layout-shift", buffered: true });
    });
    await app.open("");
    await page.waitForLoadState("networkidle");
    // 0.86 before iteration 21. Under 0.1 is what browsers call good; this asserts well under it.
    const cls = await page.evaluate(() => (window as unknown as { __cls: number }).__cls);
    expect(cls).toBeLessThan(0.05);
  });
});

test.describe("a broken file costs only the view that reads it", () => {
  for (const file of ["system.json", "events.json", "regions.geojson"]) {
    test(`a missing ${file} for one country`, async ({ app, page }) => {
      app.allowConsoleError(/status of 404/);
      await page.route(`**/data/systems/om/${file}`, (r) => r.fulfill({ status: 404, body: "" }));
      await page.goto("/?sys=om");
      await expect(page.getByRole("alert")).toContainText("could not be loaded");
      await expect(page.getByRole("alert")).toContainText("Other systems are unaffected");
      await restStillWorks(page, app);
      // The home is untouched by it.
      await picker(page).selectOption("");
      await app.mapIdle();
      await expect(page.getByRole("article", { name: "Oman" })).toBeVisible();
    });
  }

  const shapes: [string, string, (d: Record<string, unknown>) => void][] = [
    ["system.json", "profile.metrics", (d) => { d.profile = { metrics: "x" }; }],
    ["system.json", "geography.bounds", (d) => { (d.geography as Record<string, unknown>).bounds = "x"; (d.geography as Record<string, unknown>).view_bounds = null; }],
    ["system.json", "source_health", (d) => { d.source_health = { opened: 3 }; }],
    ["system.json", "research_log", (d) => { d.research_log = { passes: [{ date: "2025-01-01" }] }; }],
    ["events.json", "an event's sources", (d) => { (d.events as Record<string, unknown>[])[0].sources = "x"; }],
    ["regions.geojson", "the region features", (d) => { d.features = [null]; }],
  ];
  for (const [file, what, edit] of shapes) {
    test(`a country's ${file} with a malformed ${what} is refused at load`, async ({ app, page }) => {
      app.allowConsoleError(/malformed/);
      await page.route(`**/data/systems/kw/${file}`, async (route) => {
        const res = await route.fetch();
        const d = await res.json();
        expect((d.events ?? d.features ?? [1]).length, "nothing to break").toBeGreaterThan(0);
        edit(d);
        await route.fulfill({ response: res, json: d });
      });
      await page.goto("/?sys=kw");
      await expect(page.getByRole("alert")).toContainText("malformed");
      await restStillWorks(page, app);
    });
  }

  test("a malformed regional context: the overview says so, the countries and the theatre still work", async ({ app, page }) => {
    app.allowConsoleError(/malformed/);
    await page.route("**/data/global/gulf.json", async (route) => {
      const res = await route.fetch();
      const g = await res.json();
      g.systems = g.systems.map((s: Record<string, unknown>) => ({ ...s, lane_states: undefined, values: "x" }));
      await route.fulfill({ response: res, json: g });
    });
    await page.goto("/?group=gulf");
    await expect(page.getByRole("alert")).toContainText("The regional context could not be loaded");
    await expect(page.locator(".group-table")).toHaveCount(0);
    await restStillWorks(page, app, ["ir", "Iran"]);
  });

  test("the theatre never reads a Gulf or country payload, so breaking them all leaves it whole", async ({ app, page }) => {
    const seen = recordData(page);
    await page.route("**/data/global/gulf.json", (r) => wrongShape(r, { systems: "x" }));
    await page.route("**/data/systems/**", (r) => wrongShape(r, { broken: true }));
    await app.open("?sys=ru");
    await expect(page.locator(".ribbon")).toContainText("ESDI");
    await page.waitForLoadState("networkidle");
    expect(seen.length).toBeGreaterThan(5);
    expect(seen.filter((p) => p === "global/gulf.json" || p.startsWith("systems/"))).toEqual([]);
  });

  test("a malformed national context file: the home and a country's context tab say so; the rest works", async ({ app, page }) => {
    await page.route("**/data/global/energy_context.json", (r) => wrongShape(r, { countries: [{ a3: "X" }], comparison_year: 2024 }));
    await app.open("");
    await expect(page.getByRole("alert").filter({ hasText: "Global energy context unavailable" })).toBeVisible();
    await expect(page.getByRole("article")).not.toHaveCount(0);
    await app.button("Open India").click();
    await app.mapIdle();
    await page.getByRole("button", { name: "Energy context" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Global energy context unavailable" })).toBeVisible();
    await page.getByRole("button", { name: "Reported events" }).click();
    await expect(page.locator(".event-item").first()).toBeVisible();
  });

  test("a malformed optional manifest part is dropped; everything else stays", async ({ app, page }) => {
    await page.route("**/data/global/manifest.json", async (route) => {
      const res = await route.fetch();
      const m = await res.json();
      m.corpus = "corrupt";
      m.systems[0].aliases = 7;
      m.systems[0].bounds = ["x"];
      await route.fulfill({ response: res, json: m });
    });
    await app.open("");
    await expect(page.locator(".corpus-totals")).toHaveCount(0);
    const m = await page.evaluate(() => fetch("/data/global/manifest.json").then((r) => r.json()));
    await expect(page.getByRole("article")).toHaveCount(m.systems.length);
    await restStillWorks(page, app);
  });

  test("a malformed manifest: the home says so and offers the theatre, which still works", async ({ app, page }) => {
    app.allowConsoleError(/manifest malformed/);
    await page.route("**/data/global/manifest.json", (r) => wrongShape(r, { systems: "corrupt", selection: null }));
    await page.goto("/");
    await expect(page.getByRole("alert").filter({ hasText: "The list of monitored systems could not be loaded" })).toBeVisible();
    await page.getByRole("link", { name: "open it" }).click();
    await app.mapIdle();
    await expect(page.locator(".ribbon")).toContainText("ESDI");
    await expect(page.getByText("System list unavailable")).toBeVisible();
  });

  test("malformed world geometry: no map is drawn, and the cards, the overview table and the countries still work", async ({ app, page }) => {
    app.allowConsoleError(/malformed/);
    await page.route("**/data/global/world.geojson", (r) => wrongShape(r, { type: "FeatureCollection", features: "x" }));
    await page.goto("/");
    await expect(page.getByRole("region", { name: "World energy context" })).toContainText("Map unavailable");
    await expect(page.getByRole("article").first()).toBeVisible();
    await page.goto("/?group=gulf");
    await expect(page.locator(".group-table")).toBeVisible();
    await expect(page.getByText("Map unavailable. The table below has every figure.")).toBeVisible();
    await restStillWorks(page, app, ["qa", "Qatar"]);
  });

  test("one region with unreadable geometry: the map draws the rest and the page works", async ({ app, page }) => {
    await page.route("**/data/systems/ae/regions.geojson", async (route) => {
      const res = await route.fetch();
      const d = await res.json();
      expect(d.features.length).toBeGreaterThan(1);
      d.features[0].geometry = { type: "Polygon", coordinates: [[["a", "b"], [null, 3]]] };
      await route.fulfill({ response: res, json: d });
    });
    await app.open("?sys=ae");
    await expect(page.getByRole("heading", { name: "United Arab Emirates", level: 1 })).toBeVisible();
    const px = await app.mapPixels();
    expect(px.distinct).toBeGreaterThan(3);
    await restStillWorks(page, app);
  });

  test("a malformed data-quality summary and recent list: those panels say so, the home works", async ({ app, page }) => {
    app.allowConsoleError(/malformed/);
    await page.route("**/data/global/data_quality.json", (r) => wrongShape(r, { systems: [{ name: "x" }] }));
    await page.route("**/data/global/recent_evidence.json", (r) => wrongShape(r, { episodes: [{ members: 3 }] }));
    await app.open("");
    await expect(page.getByRole("alert").filter({ hasText: "The data-quality summary could not be loaded" })).toBeVisible();
    await expect(page.getByRole("alert").filter({ hasText: "The recent list could not be loaded" })).toBeVisible();
    await expect(page.getByRole("article").first()).toBeVisible();
    await restStillWorks(page, app);
  });
});

test.describe("error boundaries: what validation cannot enumerate", () => {
  test("a leaf of the wrong type in the recent list costs that panel, not the home", async ({ app, page }) => {
    // Shape validation checks the containers a panel iterates; a single value of the wrong type
    // passes it and throws while rendering. The panel boundary is the net.
    app.allowConsoleError(/Recent evidence panel failed|Objects are not valid as a React child|above error|react\.dev/i);
    await page.route("**/data/global/recent_evidence.json", async (route) => {
      const res = await route.fetch();
      const d = await res.json();
      expect(d.episodes.length).toBeGreaterThan(0);
      d.episodes[0].members[0].region = { not: "a string" };
      await route.fulfill({ response: res, json: d });
    });
    await app.open("");
    await expect(page.getByRole("alert", { name: "Recent evidence: could not be shown" })).toBeVisible();
    // The rest of the home is all there.
    await expect(page.getByLabel("Map legend")).toContainText("Total primary energy production");
    await expect(page.getByRole("region", { name: "Data quality" })).toBeVisible();
    await expect(page.getByRole("article").first()).toBeVisible();
    await restStillWorks(page, app);
  });

  test("a view whose code cannot be downloaded fails alone, with a way home", async ({ app, page }) => {
    app.allowConsoleError(/failed:|Failed to fetch dynamically imported module|Failed to load resource|above error|react\.dev/i);
    await page.route(/\/assets\/CountryView-[^/]*\.js$/, (r) => r.fulfill({ status: 404, body: "" }));
    await app.open("");
    await app.button("Open Oman").click();
    const failed = page.getByRole("alert", { name: "This country's page could not be shown" });
    await expect(failed).toBeVisible();
    await expect(failed).toContainText("could not be downloaded");
    // The picker is still there, and so is the way home.
    await expect(picker(page)).toBeVisible();
    await page.getByRole("button", { name: "Return to the overview" }).click();
    await app.mapIdle();
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
    await expect(page.getByRole("article").first()).toBeVisible();
    // Another kind of view still opens: the boundary was the country view's alone.
    await picker(page).selectOption("group:gulf");
    await app.mapIdle();
    await expect(page.getByRole("heading", { name: "Gulf littoral overview", level: 1 })).toBeVisible();
    await picker(page).selectOption("ru");
    await app.mapIdle();
  });
});
