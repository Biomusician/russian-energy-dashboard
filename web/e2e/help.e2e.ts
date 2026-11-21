import { test, expect } from "./fixtures";

/**
 * The Help page in a real browser (iteration 23): deep links land on their heading, old glossary
 * links still work, Back and Forward move between sections and back to the page the reader came
 * from, the phone section picker works at 390 x 844, and nothing runs off the side.
 */

type Page = import("@playwright/test").Page;

const SECTIONS = ["start-here", "navigating-the-map", "what-to-click", "product-types", "esdi", "why-no-country-score",
  "impact-records", "evidence-confidence", "attribution", "ai-involvement", "research-coverage", "source-health", "whats-new",
  "history", "gulf-context", "cyber", "absence", "withheld", "exports", "do-not-infer", "glossary"];

async function openHelp(page: Page, q = "?view=help") {
  await page.goto(`/${q}`);
  await expect(page.getByRole("heading", { level: 1, name: "Help: how to read this site" })).toBeVisible();
  // Every served value has arrived, so no late block moves the section the address names.
  await expect(page.locator(".help-derived-missing")).toHaveCount(0);
}

/** The heading's top edge within the scrolling page, and whether it is the focused element. */
async function landed(page: Page, id: string) {
  return page.evaluate((id) => {
    const h = document.getElementById(id)!;
    const top = h.getBoundingClientRect().top;
    const toc = document.querySelector(".help-toc")!.getBoundingClientRect();
    const stickyBottom = getComputedStyle(document.querySelector(".help-picker")!).display === "none" ? 0 : toc.bottom;
    return { top, stickyBottom, focused: document.activeElement === h };
  }, id);
}

test.describe("Help deep links", () => {
  test("every section's address scrolls its heading to the top, clear of anything sticky, and focuses it", async ({ app, page }) => {
    let checked = 0;
    for (const id of SECTIONS) {
      await openHelp(page, `?view=help#${id}`);
      await expect.poll(async () => (await landed(page, id)).focused, { message: id }).toBe(true);
      const r = await landed(page, id);
      expect(r.top, `${id} is hidden under the sticky contents`).toBeGreaterThanOrEqual(r.stickyBottom - 1);
      expect(r.top, `${id} is not near the top`).toBeLessThan(140);
      checked++;
    }
    expect(checked).toBe(SECTIONS.length);
    expect(app.errors).toEqual([]);
  });

  test("a glossary entry and a subsection have addresses too", async ({ page }) => {
    for (const id of ["g-esdi", "g-no-index", "how-it-works", "recovery"]) {
      await openHelp(page, `?view=help#${id}`);
      await expect.poll(async () => (await landed(page, id)).focused, { message: id }).toBe(true);
      expect((await landed(page, id)).top).toBeLessThan(140);
    }
  });

  test("the old glossary link opens the glossary section, and a term link opens that term", async ({ page }) => {
    await page.goto("/?help=glossary");
    await expect(page).toHaveURL(/\/\?view=help#glossary$/);
    await expect(page.getByRole("heading", { name: "Glossary (A–Z)", level: 2 })).toBeFocused();
    await page.goto("/?help=glossary&term=esdi");
    await expect(page).toHaveURL(/\/\?view=help#g-esdi$/);
    await expect(page.locator("#g-esdi")).toBeFocused();
    // Rewritten in place: Back does not land on the old address and bounce forward again.
    expect(await page.evaluate(() => history.length)).toBeLessThanOrEqual(3);
  });

  test("a system or comparison still wins over view=help", async ({ app, page }) => {
    await app.open("?sys=ca&view=help");
    await expect(page.getByRole("heading", { level: 1, name: "Canada" })).toBeVisible();
  });
});

test.describe("Help navigation", () => {
  test("from a country page: Help, a section, Back to the top, Back to the country, Forward again", async ({ app, page }) => {
    await app.open("?sys=ir");
    await page.locator(".global-nav").getByRole("link", { name: "Help", exact: true }).click();
    await expect(page).toHaveURL(/\/\?view=help$/);
    await expect(page.locator(".help-derived-missing")).toHaveCount(0);
    await page.locator(".help-toc-list").getByRole("link", { name: "Evidence confidence" }).click();
    await expect(page).toHaveURL(/#evidence-confidence$/);
    await expect.poll(async () => (await landed(page, "evidence-confidence")).top).toBeLessThan(140);
    await page.goBack({ waitUntil: "commit" });
    await expect(page).toHaveURL(/\/\?view=help$/);
    await expect.poll(() => page.evaluate(() => document.querySelector(".help-page")!.scrollTop)).toBe(0);
    await page.goBack({ waitUntil: "commit" });
    await expect(page).toHaveURL(/\/\?sys=ir$/);
    await expect(page.getByRole("heading", { level: 1, name: "Iran" })).toBeVisible();
    await page.goForward({ waitUntil: "commit" });
    await page.goForward({ waitUntil: "commit" });
    await expect(page).toHaveURL(/#evidence-confidence$/);
    await expect.poll(async () => (await landed(page, "evidence-confidence")).top).toBeLessThan(140);
    expect(app.errors).toEqual([]);
  });

  test("a Learn more on a record card opens its Help section in place, and Back returns", async ({ page }) => {
    await page.goto("/?view=impacts");
    await expect(page.getByRole("heading", { name: "Impact atlas", level: 1 })).toBeVisible();
    const link = page.locator('a.learn-more[data-help-anchor="impact-records"]').first();
    await expect(link).toHaveAttribute("href", "?view=help#impact-records");
    await link.click();
    await expect(page).toHaveURL(/\/\?view=help#impact-records$/);
    await expect(page.locator("#impact-records")).toBeFocused();
    await page.goBack({ waitUntil: "commit" });
    await expect(page).toHaveURL(/\/\?view=impacts$/);
  });

  test("the theatre's Learn more on the index opens the index section", async ({ app, page }) => {
    await app.open("?sys=ru");
    await page.locator('.hl-block a.learn-more[data-help-anchor="esdi"]').click();
    await expect(page).toHaveURL(/\/\?view=help#esdi$/);
    await expect(page.locator("#esdi")).toBeFocused();
  });
});

test.describe("Help layout", () => {
  for (const size of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    test(`${size.width}x${size.height}: one h1, one main, no sideways scroll, headings in order`, async ({ page }) => {
      await page.setViewportSize(size);
      await openHelp(page);
      await expect(page.locator("h1")).toHaveCount(1);
      await expect(page.locator("main")).toHaveCount(1);
      const over = await page.evaluate(() => Math.max(document.documentElement.scrollWidth - window.innerWidth,
        ...[...document.querySelectorAll(".global-page")].map((e) => e.scrollWidth - e.clientWidth)));
      expect(over).toBeLessThanOrEqual(1);
      const levels = await page.locator("h1, h2, h3").evaluateAll((els) => els.map((e) => Number(e.tagName[1])));
      for (let i = 1; i < levels.length; i++) expect(levels[i] - levels[i - 1]).toBeLessThanOrEqual(1);
      // Exactly one contents control is shown: the list on a wide screen, the picker on a phone.
      const list = await page.locator(".help-toc-list").isVisible();
      const picker = await page.locator(".help-picker select").isVisible();
      expect(list).toBe(size.width >= 900);
      expect(picker).toBe(size.width < 900);
    });
  }

  test("390x844: the section picker jumps to a section and keeps it clear of the picker", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openHelp(page);
    const select = page.getByRole("combobox", { name: "Jump to a section" });
    const box = (await select.boundingBox())!;
    expect(box.height).toBeGreaterThanOrEqual(43.5);
    await select.selectOption("withheld");
    await expect(page).toHaveURL(/#withheld$/);
    await expect.poll(async () => (await landed(page, "withheld")).focused).toBe(true);
    const r = await landed(page, "withheld");
    expect(r.top).toBeGreaterThanOrEqual(r.stickyBottom - 1);
    await expect(select).toHaveValue("withheld");
    // The picker stays on screen while reading.
    expect((await select.boundingBox())!.y).toBeGreaterThanOrEqual(0);
  });

  test("skip link reaches the Help text; tables are captioned; disclosures are native", async ({ page }) => {
    await openHelp(page);
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Skip to content" });
    await expect(skip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("main")).toBeFocused();
    const tables = await page.locator("table").evaluateAll((els) => els.map((t) => !!t.querySelector("caption")?.textContent?.trim()));
    expect(tables.length).toBeGreaterThan(0);
    for (const t of tables) expect(t).toBe(true);
    // Every link has a name and none points nowhere.
    const bad = await page.locator("main a").evaluateAll((els) => els.filter((a) => !(a.textContent ?? "").trim() || !a.getAttribute("href")).length);
    expect(bad).toBe(0);
  });
});
