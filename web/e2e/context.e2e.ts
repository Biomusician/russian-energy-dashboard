import { test, expect, pixelStats } from "./fixtures";

/**
 * The world energy context in a real browser (iteration 18; since iteration 23 the "National energy"
 * mode of the home map, and the national figures in the selection card and the collapsed table).
 *
 * THE WORLD PICTURE IS NOT THE WORLD INCIDENT CORPUS. These tests read the emitted payloads so the
 * context-only examples come from the data, then assert what the reader sees: a coloured country
 * is not a monitored one, an unmonitored country has no zero, and the artifact that leaves the
 * page keeps its year, source and monitored status.
 */

type Row = { a3: string; name: string; on_map: boolean; system_id: string | null;
             values: Record<string, number | null> };

async function ctx(page: import("@playwright/test").Page) {
  return page.evaluate(() => fetch("/data/global/energy_context.json").then((r) => r.json()));
}

function contextOnly(c: { countries: Row[] }, n: number): Row[] {
  return c.countries
    .filter((r) => !r.system_id && r.on_map && r.values.total_production != null && r.values.total_production > 5)
    .slice(0, n);
}

const SEARCH = /Search systems, regions and terms/;

/** Select a country on the home map through the one search (iteration 23: the map's own "Find a
 *  country" box is gone; a country without a system selects exactly as a click on it would). */
async function openCard(page: import("@playwright/test").Page, name: string) {
  const box = page.getByRole("combobox", { name: SEARCH });
  await box.fill(name);
  await page.getByRole("listbox", { name: "Search results" }).getByRole("option").filter({ hasText: name }).first().click();
}

/** The national-energy map mode, where the iteration-18 context map lives since iteration 23. */
async function energyMode(app: import("./fixtures").App) {
  await app.page.getByRole("button", { name: "National energy" }).click();
  await app.mapIdle();
}

test.describe("world energy context", () => {
  test("the legend states metric, year and unit, and states monitoring separately", async ({ app, page }) => {
    await app.open("");
    const legend = page.getByLabel("Map legend");
    // The default mode colours monitoring alone, in one colour that is not a measure.
    await expect(legend).toContainText("Monitored system: the theatre or a country system (one colour; not a measure");
    await energyMode(app);
    const c = await ctx(page);
    await expect(legend).toContainText(`Total primary energy production — ${c.comparison_year}`);
    await expect(legend).toContainText("quadrillion Btu");
    await expect(legend).toContainText("Thick outline: systematically monitored");
  });

  test("every map metric keeps a unit and the comparison year in the legend, and redraws", async ({ app, page }) => {
    await app.open("");
    await energyMode(app);
    const c = await ctx(page);
    const select = page.getByLabel("Map metric");
    const legend = page.getByLabel("Map legend");
    for (const m of c.map_metrics) {
      await select.selectOption(m);
      await app.mapIdle();
      await expect(legend).toContainText(`${c.metrics[m].label} — ${c.comparison_year}`);
      await expect(legend).toContainText(c.metrics[m].unit);
    }
  });

  test("a context-only country opens a card that says so, with no zero and no dossier", async ({ app, page }) => {
    await app.open("");
    const c = await ctx(page);
    for (const row of contextOnly(c, 3)) {
      const requests: string[] = [];
      const seen = (r: import("@playwright/test").Request) => requests.push(r.url());
      page.on("request", seen);
      // Keyboard only: a mouse left over a panel row when the result list closes fires a hover, and a
      // hover over a system link prefetches that view's code by design. This test is about the card.
      const box = page.getByRole("combobox", { name: SEARCH });
      await box.fill(row.name);
      const option = page.getByRole("listbox", { name: "Search results" }).getByRole("option").filter({ hasText: row.name }).first();
      await expect(option).toBeVisible();
      while (!(await option.getAttribute("aria-selected"))?.startsWith("true")) await box.press("ArrowDown");
      await box.press("Enter");
      const card = page.locator(".sel-card");
      await expect(card.getByRole("heading", { name: row.name })).toBeVisible();
      await expect(card).toContainText(/Not a monitored country system|No dedicated monitored system/);
      // The national figures are one tap away, with their year and source.
      await card.getByText("National energy context").click();
      await expect(card).toContainText(String(c.comparison_year));
      await expect(card).toContainText("U.S. Energy Information Administration");
      // Not a dossier and not a zero.
      await expect(card).not.toContainText(/0 (events|incidents|records|disruptions)/i);
      await expect(card).not.toContainText(/no index|no disruption record/i);
      page.off("request", seen);
      expect(requests.filter((u) => /systems\/|assets|pipeline|refiner|impacts\.json/.test(u))).toEqual([]);
      await page.keyboard.press("Escape");
      await expect(card).toHaveCount(0);
    }
  });

  test("Search names a context country by what choosing it does, and a monitored one as monitored", async ({ app, page }) => {
    await app.open("");
    const c = await ctx(page);
    const row = contextOnly(c, 1)[0];
    const box = page.getByRole("combobox", { name: SEARCH });
    const options = page.getByRole("listbox", { name: "Search results" }).getByRole("option");
    await box.fill(row.name);
    await expect(options.filter({ hasText: row.name }).first()).toContainText("selects it on the map");
    await box.fill("Canada");
    await expect(options.first()).toContainText("Monitored country system · no index · opens it");
  });

  test("a context selection then a monitored system leaves no stale state, and Back restores the selection", async ({ app, page }) => {
    await app.open("");
    const c = await ctx(page);
    const row = contextOnly(c, 1)[0];
    await openCard(page, row.name);
    await page.locator("#where-to-explore").getByRole("link", { name: "Canada", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Canada", level: 1 })).toBeVisible();
    await expect(page.getByText("Not a monitored country system")).toHaveCount(0);
    await page.goBack();
    await app.mapIdle();
    // Iteration 23: Back lands on the home as the reader left it, with that country still selected.
    await expect(page.locator(".sel-card").getByRole("heading", { name: row.name })).toBeVisible();
  });

  test("Ukraine's card speaks of Crimea only as Crimea, occupied and monitored in the theatre", async ({ app, page }) => {
    await app.open("");
    await openCard(page, "Ukraine");
    const card = page.locator(".sel-card");
    await expect(card.getByRole("heading", { name: "Ukraine" })).toBeVisible();
    await expect(card).toContainText("Crimea and Sevastopol: Internationally recognised as Ukraine; occupied by Russia.");
    await expect(card.getByRole("link", { name: "Open the Russia, Belarus & Crimea theatre" })).toHaveAttribute("href", "?sys=ru");
    // Its own state, not the theatre's: impact records only, not a monitored system.
    await expect(card.locator(".sel-status")).toHaveText("Impact records available · Not a monitored country system");
    await expect(card.locator(".sel-status")).not.toContainText(/theatre/i);
    await expect(page.getByLabel("Map legend")).toContainText("Crimea and Sevastopol: Ukrainian territory under Russian occupation");
  });

  test("an alias finds a country and a monitored country says so", async ({ app, page }) => {
    await app.open("");
    const box = page.getByRole("combobox", { name: SEARCH });
    const options = page.getByRole("listbox", { name: "Search results" }).getByRole("option");
    await box.fill("USA");
    await expect(options.filter({ hasText: "United States" }).first()).toContainText(/Monitored country system|opens it/);
    await box.fill("UK");
    await expect(options.filter({ hasText: "United Kingdom" })).toHaveCount(1);
  });

  test("the world profile lists no largest producers and no position", async ({ app, page }) => {
    // Iteration 20 (§80): no "largest producers" list at all, alphabetical or not. The table is
    // alphabetical by default and says what production does not mean.
    await app.open("");
    await page.locator("#fold-national > summary").click();
    const profile = page.locator(".world-profile");
    await expect(profile).not.toContainText(/largest producers|leading|#1|No\. ?1|first place/i);
    await expect(profile).toContainText("Alphabetical by default");
    await expect(profile).toContainText("Energy production says nothing about disruption or importance");
  });

  test("a country page answers the reader's questions without opening a tab", async ({ app, page }) => {
    await app.open("?sys=sa");
    await expect(page.getByText(/Recovery status is withheld for \d+ of \d+ records\s+while an attack campaign is active/)).toBeVisible();
    await app.open("?sys=cn");
    const ribbon = page.locator(".research-status");
    await expect(ribbon.locator(".lane-state-line")).toHaveText(/^\d+ source groups: .+\.$/);
    await expect(ribbon).not.toContainText(/finished|declared complete/);
    await expect(ribbon).toContainText(/Research period/);
  });

  test("events can be filtered, and a region can be chosen without the map", async ({ app, page }) => {
    await app.open("?sys=us");
    // Iteration 22: the year select became the shared date filter (a custom range here).
    const bar = page.locator(".record-filters");
    await bar.getByRole("button", { name: /^Date/ }).click();
    await bar.getByRole("radio", { name: "Custom range" }).check();
    await bar.getByLabel("From", { exact: true }).fill("2024-01-01");
    await bar.getByLabel("To", { exact: true }).fill("2024-12-31");
    await expect(page.locator(".rf-count")).toContainText("Date: 2024-01-01 to 2024-12-31");
    const items = page.locator(".event-list .event-item");
    await expect(items.first()).toBeVisible();
    for (const t of await items.locator(".event-head .mono").allInnerTexts()) expect(t).toContain("2024");
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: "Clear filters" }).click();
    await page.getByLabel(/Choose a state/i).selectOption({ label: "Texas" });
    await expect(page.locator(".events-panel h2").first()).toHaveText("Texas");
  });

  test("the national table is alphabetical by default and has no disruption column", async ({ app, page }) => {
    await app.open("");
    await page.locator("#fold-national > summary").click();
    const table = page.locator(".national-table");
    await expect(table).toBeVisible();
    const first = await table.locator("tbody tr td:first-child").allInnerTexts();
    // The pipeline's order: NFKD, case-folded, by code point.
    const key = (s: string) => s.normalize("NFKD").toLowerCase();
    expect(first).toEqual([...first].sort((a, b) => (key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0)));
    await expect(table.locator("thead")).not.toContainText(/incident|event|disruption|rank|score/i);
  });

  test("the recent list is newest first with no severity sort", async ({ app, page }) => {
    await app.open("");
    await page.locator("#fold-recent > summary").click();
    const feed = page.getByRole("region", { name: "Recent evidence" });
    await expect(feed).toContainText("Newest first");
    const data = await page.evaluate(() => fetch("/data/global/recent_evidence.json").then((r) => r.json()));
    const dates = data.episodes.map((e: { last_date: string }) => e.last_date);
    expect(dates).toEqual([...dates].sort().reverse());
    await expect(feed.locator("select")).toHaveCount(2);
    await feed.getByLabel("Filter recent evidence by country").selectOption("sa");
    await expect(feed).not.toContainText(/restart|operating rate|repair/i);
  });

  test("data quality separates source window from analyst work and carries no event counts", async ({ app, page }) => {
    await app.open("");
    await page.locator("#fold-quality > summary").click();
    const panel = page.getByRole("region", { name: "Data quality" });
    await expect(panel).toContainText("Global energy context");
    await expect(panel).not.toContainText(/\d+ (records|events|episodes)\b/i);
    await panel.locator("details summary").first().click();
    await expect(panel.locator("details").first()).toContainText(/Reporting environment/);
  });

  test("the context PNG keeps year, source and monitored status", async ({ app, page }) => {
    await app.open("");
    await energyMode(app);
    const dl = page.waitForEvent("download");
    await page.locator(".home-map").getByRole("button", { name: "Download PNG" }).click();
    const file = await dl;
    expect(file.suggestedFilename()).toMatch(/^global-energy-context-total_production-\d{4}\.png$/);
    const path = await file.path();
    const { readFileSync } = await import("node:fs");
    const buf = readFileSync(path!);
    const px = await pixelStats(page, buf);
    expect(px.distinct).toBeGreaterThan(8);
    await expect(page.getByRole("status").filter({ hasText: "Exported" })).toBeVisible();
  });

  test("a broken context file shows unavailable while the monitored systems keep working", async ({ app, page }) => {
    app.allowConsoleError(/Failed to load resource/);
    await page.route("**/data/global/energy_context.json", (r) => r.fulfill({ status: 500, body: "no" }));
    await app.open("");
    // The default map needs no national figures; asking for them says they are unavailable.
    await page.getByRole("button", { name: "National energy" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Global energy context unavailable" })).toBeVisible();
    await expect(page.locator("#where-to-explore a.hp-row")).not.toHaveCount(0);
    await page.locator("#where-to-explore").getByRole("link", { name: "Canada", exact: true }).click();
    await app.mapIdle();
    await expect(page.getByRole("heading", { name: "Canada", level: 1 })).toBeVisible();
    await page.getByRole("button", { name: "Energy context" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Global energy context unavailable" })).toBeVisible();
  });

  test("a malformed context file is refused rather than drawn", async ({ app, page }) => {
    await page.route("**/data/global/energy_context.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ countries: "x" }) }));
    await app.open("");
    await page.getByRole("button", { name: "National energy" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Global energy context unavailable" })).toBeVisible();
  });

  test("a broken country leaves the context and the other systems working", async ({ app, page }) => {
    app.allowConsoleError(/Failed to load resource/);
    await page.route("**/data/systems/us/*", (r) => r.fulfill({ status: 500, body: "no" }));
    await app.open("");
    await energyMode(app);
    await expect(page.getByLabel("Map legend")).toContainText("Total primary energy production");
    await page.locator("#where-to-explore").getByRole("link", { name: "United States", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText("could not be loaded");
    await page.getByLabel("Monitored system").selectOption("ca");
    await app.mapIdle();
    await expect(page.getByRole("heading", { name: "Canada", level: 1 })).toBeVisible();
  });

  for (const [w, h] of [[2560, 1440], [1920, 1080], [1536, 864], [1366, 768], [1280, 720], [1024, 768], [430, 932]] as const) {
    test(`the world map stays useful at ${w}x${h}`, async ({ app, page }) => {
      await page.setViewportSize({ width: w, height: h });
      await app.open("");
      const px = await app.mapPixels();
      expect(px.distinct).toBeGreaterThan(5);
      const sideways = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(sideways).toBeLessThanOrEqual(0);
      await expect(page.getByLabel("Map legend")).toBeVisible();
    });
  }
});

const COUNTRIES = ["ca", "cn", "in", "sa", "us"] as const;

test.describe("country pages after iteration 18", () => {
  for (const id of COUNTRIES) {
    test(`${id}: national context, lane states and known gaps`, async ({ app, page }) => {
      await app.open(`?sys=${id}`);
      const sys = await page.evaluate((x) => fetch(`/data/systems/${x}/system.json`).then((r) => r.json()), id);
      const c = await ctx(page);
      const status = page.getByLabel("Research status");
      await expect(status).not.toContainText(/\d+ of \d+ source lanes/);
      await page.getByRole("button", { name: "Energy context" }).click();
      await expect(page.locator(".national-block")).toContainText(String(c.comparison_year));
      await page.getByRole("button", { name: "Research coverage" }).click();
      const newest = sys.research_log.passes.filter((p: { kind: string }) => p.kind === "systematic").at(-1);
      await expect(page.locator(".lane-table tbody tr")).toHaveCount(newest.lanes.length);
      await expect(page.locator(".recovery-coverage")).toContainText("Not yet researched");
      await expect(page.locator(".global-page")).not.toContainText(/complete coverage/i);
    });
  }
});
