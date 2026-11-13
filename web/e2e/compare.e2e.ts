import { test, expect, pixelStats, readBytes } from "./fixtures";

/**
 * The comparison workspace, in a real browser (iteration 21).
 *
 * What is fixed here is the behaviour and the refusals: columns in the reader's order, unknown ids
 * dropped with a note and never a crash, no event count, no index value set beside "No index", a
 * national figure always with its unit, year and source, and an export that carries its own caveats
 * in its pixels. Values are read from the payloads the page itself loaded.
 */

type Page = import("@playwright/test").Page;
const json = (page: Page, path: string) => page.evaluate((p) => fetch(p).then((r) => r.json()), path);

async function openCompare(page: Page, q: string) {
  await page.goto(`/${q}`);
  await expect(page.getByRole("heading", { name: "Compare systems", level: 1 })).toBeVisible();
}

const table = (page: Page) => page.locator(".compare-table");
// The heading renders before the manifest arrives; read the columns only once the table is drawn.
async function colNames(page: Page): Promise<string[]> {
  await expect(page.locator(".compare-colhead > a").first()).toBeVisible();
  return page.locator(".compare-colhead > a").allInnerTexts();
}
const row = (page: Page, id: string) => page.locator(`tr[data-row="${id}"]`);
// Wording a comparison must never carry. The page's own refusals ("never sorted") are allowed.
const RANKING = /\b(ranked (first|second|third|\d)|top \d|#\d|most (important|vulnerable|critical|exposed)|worst[- ]hit|hardest[- ]hit|winner|safest|least disrupted)\b/i;

test.describe("Compare systems", () => {
  test("opens from the URL with columns in the reader's order and only common-basis rows", async ({ app, page }) => {
    await openCompare(page, "?compare=sa,us,ca");
    expect(await colNames(page)).toEqual(["Saudi Arabia", "United States", "Canada"]);
    await expect(row(page, "lanes").locator("td").first()).not.toHaveText("Loading…");
    const text = await table(page).innerText();
    expect(text).not.toMatch(/qualifying|held back|withheld|severity/i);
    expect(text).not.toMatch(RANKING);
    // No event count of any column appears anywhere in the table.
    let checked = 0;
    for (const id of ["sa", "us", "ca"]) {
      const s = await json(page, `/data/systems/${id}/system.json`);
      const n = s.event_summary.recorded_events as number;
      if (n > 9) expect(text, `${id} count ${n}`).not.toMatch(new RegExp(`\\b${n}\\b`));
      checked++;
    }
    expect(checked).toBe(3);
    await expect(row(page, "index").locator("td")).toHaveText([/^No index/, /^No index/, /^No index/]);
    // Common-basis, context and within-system rows are told apart in words.
    await expect(page.locator(".compare-basis-tag.basis-common").first()).toHaveText("Common basis");
    await expect(page.locator(".compare-basis-tag.basis-within").first()).toHaveText("Within this system");
    await expect(page.locator(".compare-group-head").nth(2)).toContainText("not a comparison");
  });

  test("the theatre's index is said to be not comparable, and its value is never shown", async ({ app, page }) => {
    await openCompare(page, "?compare=us,ru");
    const m = await json(page, "/data/global/manifest.json");
    const ru = m.systems.find((s: { id: string }) => s.id === "ru");
    const cells = row(page, "index").locator("td");
    await expect(cells.nth(0)).toContainText("No index");
    await expect(cells.nth(1)).toContainText("not comparable");
    expect(await page.locator("main").innerText()).not.toContain(String(ru.headline.value));
    await expect(row(page, "ctx_total_production").locator("td").nth(1)).toContainText("No single national figure");
  });

  test("national figures carry unit, year and source, and match the context file", async ({ app, page }) => {
    await openCompare(page, "?compare=us,ca");
    const ctx = await json(page, "/data/global/energy_context.json");
    const head = page.locator(".compare-group-head").nth(1);
    await expect(head).toContainText(ctx.source.name);
    await expect(head).toContainText(`year ${ctx.comparison_year} for every country`);
    for (const id of ["ctx_total_production", "ctx_crude_production", "ctx_gas_production", "ctx_electricity_generation"]) {
      await expect(row(page, id).locator("th .compare-row-label")).toContainText(`, ${ctx.comparison_year})`);
    }
    const us = ctx.countries.find((r: { system_id: string }) => r.system_id === "us");
    const v = Math.round(us.values.crude_production).toLocaleString("en-GB");
    await expect(row(page, "ctx_crude_production").locator("td").first()).toHaveText(`${v} kb/d`);
    // The definition is a click away, not a hover.
    const def = row(page, "ctx_total_production").locator("details.compare-def");
    await def.locator("summary").click();
    await expect(def).toContainText(ctx.accounting_convention);
  });

  test("unknown ids are dropped with a note, extra ids beyond four are named, and nothing crashes", async ({ app, page }) => {
    await openCompare(page, "?compare=zz,US,__proto__,ca,us");
    await expect(page.getByText(/Not recognised and left out: “zz”, “__proto__”/)).toBeVisible();
    expect(await colNames(page)).toEqual(["United States", "Canada"]);

    await openCompare(page, "?compare=us,ca,sa,cn,in");
    expect(await colNames(page)).toHaveLength(4);
    await expect(page.getByText(/At most 4 systems can be compared at once; left out: India/)).toBeVisible();
    await expect(page.getByLabel("Add a system to compare")).toBeDisabled();

    await openCompare(page, "?compare=constructor");
    await expect(page.getByText("Choose at least two systems to compare.")).toBeVisible();
    await expect(table(page)).toHaveCount(0);
    await expect(app.button("Download comparison (PNG)")).toBeDisabled();

    // sys still wins over compare.
    await app.open("?sys=ca&compare=us,sa");
    await expect(page.getByRole("heading", { name: "Canada", level: 1 })).toBeVisible();
  });

  test("is usable from the keyboard alone, and every edit is in the URL", async ({ app, page }) => {
    await openCompare(page, "?compare=us");
    const add = page.getByLabel("Add a system to compare");
    await add.focus();
    await page.keyboard.press("ArrowDown");  // the first addable system, in manifest (alphabetical) order
    await expect(page).toHaveURL(/[?&]compare=us,[a-z]+$/);
    const second = new URL(page.url()).searchParams.get("compare")!.split(",")[1];
    await expect(table(page)).toBeVisible();

    const firstName = (await colNames(page))[0];
    const secondName = (await colNames(page))[1];
    await page.getByRole("button", { name: `Move ${secondName} left` }).focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(new RegExp(`[?&]compare=${second},us$`));
    expect(await colNames(page)).toEqual([secondName, firstName]);

    await page.getByRole("button", { name: `Remove ${secondName}` }).focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/[?&]compare=us$/);

    // A definition opens with Enter: a disclosure, not a hover.
    await openCompare(page, "?compare=us,ca");
    const summary = row(page, "maturity").locator("details.compare-def summary");
    await summary.focus();
    await page.keyboard.press("Enter");
    await expect(row(page, "maturity").locator("details.compare-def")).toHaveAttribute("open", "");

    // A column heading is a real link to that system, by keyboard too.
    await page.locator(".compare-colhead > a", { hasText: "Canada" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Canada", level: 1 })).toBeVisible();
    await expect(page).toHaveURL(/[?&]sys=ca\b/);
  });

  test("the country page leads to the workspace, and Back returns", async ({ app, page }) => {
    await app.open("?sys=ca");
    await page.getByRole("button", { name: "Compare Canada with other systems" }).click();
    await expect(page).toHaveURL(/[?&]compare=ca$/);
    await expect(page.getByText(/Choose at least two systems to compare: Canada is chosen/)).toBeVisible();
    await page.getByLabel("Add a system to compare").selectOption("us");
    await expect(page).toHaveURL(/[?&]compare=ca,us$/);
    expect(await colNames(page)).toEqual(["Canada", "United States"]);
    await page.goBack();
    await expect(page.getByRole("heading", { name: "Canada", level: 1 })).toBeVisible();
  });

  test("at phone width the page does not scroll sideways; the table does, with its first column held", async ({ app, page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openCompare(page, "?compare=us,ru,sa,ca");
    await expect(row(page, "lanes").locator("td").first()).not.toHaveText("Loading…");
    const sideways = await page.evaluate(() => Math.max(document.documentElement.scrollWidth - window.innerWidth,
      ...[...document.querySelectorAll(".global-page")].map((e) => e.scrollWidth - e.clientWidth)));
    expect(sideways, "horizontal page scroll").toBeLessThanOrEqual(1);
    await expect(page.locator(".compare-scroll-cue")).toBeVisible();
    const box = page.locator(".compare-scroll");
    const [sw, cw] = await box.evaluate((e) => [e.scrollWidth, e.clientWidth]);
    expect(sw).toBeGreaterThan(cw);
    const label = row(page, "index").locator("th");
    const before = (await label.boundingBox())!.x;
    await box.evaluate((e) => { e.scrollLeft = 400; });
    expect(Math.abs((await label.boundingBox())!.x - before), "the first column moved with the scroll").toBeLessThan(2);
    await expect(page.getByRole("button", { name: "Download comparison (PNG)" })).toBeVisible();
    await expect(page.getByLabel("Add a system to compare")).toBeVisible();
  });

  test("loads only the chosen countries' system files, never their events", async ({ app, page }) => {
    const seen: string[] = [];
    page.on("request", (r) => { if (r.url().includes("/data/")) seen.push(new URL(r.url()).pathname); });
    await openCompare(page, "?compare=us,ru,sa");
    await expect(row(page, "lanes").locator("td").nth(2)).not.toHaveText("Loading…");
    const systems = seen.filter((p) => p.startsWith("/data/systems/"));
    expect(systems.sort()).toEqual(["/data/systems/sa/system.json", "/data/systems/us/system.json"]);
    expect(seen).toContain("/data/global/energy_context.json");
  });

  test("an edit while a country is still loading never strands its column", async ({ app, page }) => {
    // Regression: an edit used to abort the slow load, and nothing started it again.
    // The request is held open until the edits are done, so a slow machine cannot close the
    // "still loading" window before the test has used it.
    let release!: () => void;
    const held = new Promise<void>((res) => { release = res; });
    await page.route("**/data/systems/us/system.json", async (r) => {
      await held;
      await r.continue();
    });
    await openCompare(page, "?compare=us,ca");
    await expect(row(page, "lanes").locator("td").nth(0)).toHaveText("Loading…");
    await page.getByLabel("Add a system to compare").selectOption("sa");
    await page.getByRole("button", { name: "Move Canada left" }).click();
    await expect(page).toHaveURL(/[?&]compare=ca,us,sa$/);
    await expect(row(page, "lanes").locator("td").nth(1)).toHaveText("Loading…");
    release();
    await expect(row(page, "lanes").locator("td").nth(1)).toContainText("planned searches run (not exhaustive)", { timeout: 10_000 });
  });

  test("a corrupt country file is contained to its own column", async ({ app, page }) => {
    await page.route("**/data/systems/ca/system.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: '{"system_id":"ca"}' }));
    await openCompare(page, "?compare=us,ca");
    await expect(row(page, "lanes").locator("td").nth(1)).toHaveText(/Could not be loaded/);
    await expect(row(page, "lanes").locator("td").nth(0)).toContainText("planned searches run (not exhaustive)");
    await expect(row(page, "lanes").locator("td").nth(0)).not.toContainText(/declared complete|\bfinished\b/);
    // The manifest-level rows still describe it.
    await expect(row(page, "index").locator("td").nth(1)).toContainText("No index");
  });

  test("the comparison downloads as a real 1600x900 image carrying its framing", async ({ app, page }) => {
    await openCompare(page, "?compare=us,ru,sa,ca");
    await expect(row(page, "lanes").locator("td").nth(3)).not.toHaveText("Loading…");
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      app.button("Download comparison (PNG)").click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/^energy-systems-compared-us-ru-sa-ca-\d{4}-\d{2}-\d{2}\.png$/);
    const png = readBytes((await download.path())!);
    // Set COMPARE_PNG_OUT to a path to keep the image for a look by eye.
    if (process.env.COMPARE_PNG_OUT) await download.saveAs(process.env.COMPARE_PNG_OUT);
    expect(png.subarray(1, 4).toString("ascii")).toBe("PNG");
    const whole = await pixelStats(page, png);
    expect([whole.width, whole.height]).toEqual([1600, 900]);
    expect(whole.distinct).toBeGreaterThan(8);
    expect(whole.spread).toBeGreaterThan(120);
    // Text drawn in the title band, the table body, the column headings and the footer caveats.
    for (const [name, region] of [["title", [24, 10, 1000, 70]], ["table", [354, 160, 1200, 420]],
                                  ["headings", [354, 110, 1200, 24]], ["footer", [24, 800, 1200, 90]]] as const) {
      const s = await pixelStats(page, png, region as unknown as [number, number, number, number]);
      expect(s.spread, `${name} region of the export is blank`).toBeGreaterThan(80);
    }
    await expect(page.getByText("Exported 1600×900.")).toBeVisible();
  });
});
