import { test, expect } from "./fixtures";

/**
 * One vocabulary, one site bar (iteration 21, first-time-user fixes).
 *
 * A first-time reader met the same research state described three ways on one country ("planned
 * searches run", "5 of 6 source groups finished", "5 of 6 lanes declared complete"), five words for
 * where a record is placed, a "What's new" panel at the bottom of the home page with no way to it,
 * and a site bar that took five rows of a phone screen. Each block below checks the shipped page.
 */

type Page = import("@playwright/test").Page;
const PHONE = { width: 390, height: 844 };

async function openView(page: Page, q: string) {
  await page.goto(`/${q}`);
  if (q.startsWith("?compare")) await expect(page.locator(".compare-colhead > a").first()).toBeVisible();
  else await expect(page.locator('[data-map-state="idle"]')).toHaveCount(1, { timeout: 45_000 });
}

const STALE_WORDS = /declared complete|groups finished|lanes declared|Declared search complete|blocked by the source|All listed sources searched/i;

test.describe("one research-coverage vocabulary", () => {
  test("Iran: the header, the Research coverage tab, the home page and Compare say the same line", async ({ app, page }) => {
    await openView(page, "?sys=ir");
    const header = (await page.locator(".research-status .lane-state-line").textContent())!.trim();
    expect(header).toMatch(/^\d+ source groups: .+\.$/);
    await expect(page.locator(".research-status")).not.toContainText(STALE_WORDS);
    await app.button("Research coverage").click();
    await expect(page.locator(".rc-summary-line")).toHaveText(header);
    await expect(page.locator("section.rc")).not.toContainText(STALE_WORDS);
    await expect(page.locator("section.rc")).not.toContainText(/\blanes?\b/);

    // Home: the data-quality line for Iran is the same sentence.
    await openView(page, "");
    const dq = page.locator("details.dq-system").filter({ has: page.locator("summary strong", { hasText: /^Iran$/ }) });
    await expect(dq.locator("summary .dim")).toHaveText(header);
    await expect(page.locator(".corpus-totals")).toContainText(/Research process: \d+ source groups: /);
    await expect(page.locator("main")).not.toContainText(STALE_WORDS);

    // Compare: each state in the same words, no merged "complete" bucket.
    await openView(page, "?compare=ir,cn");
    const cell = page.locator('tr[data-row="lanes"] td').first();
    await expect(cell).not.toHaveText("Loading…");
    await expect(cell).toContainText("planned searches run (not exhaustive)");
    await expect(page.locator("main")).not.toContainText(STALE_WORDS);
    expect(app.errors).toEqual([]);
  });

  test("China: the same states on its home line and in Compare", async ({ page }) => {
    await openView(page, "");
    const line = (await page.locator("details.dq-system").filter({ has: page.locator("summary strong", { hasText: /^China$/ }) })
      .locator("summary .dim").textContent())!;
    const chips = line.replace(/^\d+ source groups?: /, "").replace(/\.$/, "").split(" · ");
    expect(chips.length).toBeGreaterThan(0);
    await openView(page, "?compare=cn,us");
    const cell = page.locator('tr[data-row="lanes"] td').first();
    await expect(cell).not.toHaveText("Loading…");
    // Every non-zero state on the home page appears in Compare, word for word and count for count.
    for (const c of chips) await expect(cell).toContainText(c);
  });

  test("the glossary lists the states and the placement words from the same definitions", async ({ page }) => {
    await page.goto("/?help=glossary");
    const dlg = page.getByRole("dialog", { name: "Glossary" });
    await expect(dlg).toBeVisible();
    await expect(dlg.locator("#gl-research-coverage")).toContainText("planned searches run (not exhaustive)");
    await expect(dlg.locator("#gl-research-coverage")).toContainText("source unavailable");
    const place = dlg.locator("#gl-placement");
    for (const w of ["National:", "Several regions:", "One region:", "National, under safeguards:"]) await expect(place).toContainText(w);
  });
});

test.describe("one placement vocabulary", () => {
  test("the home and Gulf lists use the shared words, and a safeguarded record keeps an opaque list entry", async ({ app, page }) => {
    await openView(page, "");
    const feed = page.locator(".recent-evidence .feed");
    const places = await feed.locator(".feed-place").allTextContents();
    expect(places.length).toBeGreaterThan(0);
    for (const p of places) expect(p).toMatch(/^(National|Several regions|One region|National, under safeguards)\b|\+/);
    expect(places.join("|")).not.toMatch(/Country level|First-level region|Multiple regions/);
    const keys = feed.locator(".row-key");
    if (await keys.count()) {
      await expect(keys.first()).toHaveText(/^list entry \d+$/);
      expect(await keys.first().getAttribute("data-row")).toMatch(/-row-\d+$/);
    }

    await openView(page, "?group=gulf");
    const gulf = page.locator(".recent-evidence .feed");
    await expect(gulf).not.toContainText(/Multiple regions/);
    // A single safeguarded record carries its list entry; a run of them is one line with no count.
    const single = gulf.locator(".row-key");
    const runs = gulf.locator(".covered-run");
    expect((await single.count()) + (await runs.count()), "no safeguarded record in the Gulf list").toBeGreaterThan(0);
    for (const k of await single.allTextContents()) expect(k).toMatch(/^list entry \d+$/);
    for (const r of await runs.allTextContents()) expect(r).not.toMatch(/list entry|\b\d+ records?\b/);
    await expect(gulf).toContainText("National, under safeguards");
    // The served list's "Multiple regions" members read in the shared word.
    await expect(gulf).toContainText("Several regions:");
    expect(app.errors).toEqual([]);
  });
});

test.describe("What's new from the site bar", () => {
  test("on the home page it scrolls to the panel and focuses its heading", async ({ page }) => {
    await openView(page, "");
    const link = page.locator(".global-nav").getByRole("link", { name: "What's new" });
    await expect(link).toBeVisible();
    await link.click();
    const head = page.getByRole("heading", { name: "What's new in the data" });
    await expect(head).toBeFocused();
    await expect(head).toBeInViewport();
    expect(new URL(page.url()).hash).toBe("#whats-new");
  });

  test("from a country page it goes home to the panel, and Back returns", async ({ page }) => {
    await openView(page, "?sys=us");
    await page.locator(".global-nav").getByRole("link", { name: "What's new" }).click();
    const head = page.getByRole("heading", { name: "What's new in the data" });
    await expect(head).toBeFocused({ timeout: 30_000 });
    await expect(head).toBeInViewport();
    await page.goBack();
    await expect(page).toHaveURL(/[?&]sys=us\b/);
  });
});

test.describe("phone: the site bar's secondary tools fold behind Menu", () => {
  for (const q of ["?sys=us", "?group=gulf", "?compare=us,ca,sa", ""]) {
    test(`${q || "home"}: search and the picker stay visible; the tools open from Menu`, async ({ app, page }) => {
      await page.setViewportSize(PHONE);
      await openView(page, q);
      const bar = page.locator(".global-nav");
      const toggle = bar.getByRole("button", { name: "Menu" });
      await expect(toggle).toBeVisible();
      await expect(toggle).toHaveAttribute("aria-expanded", "false");
      const menuId = await toggle.getAttribute("aria-controls");
      expect(menuId).toBeTruthy();
      const menu = page.locator(`[id="${menuId}"]`);
      for (const name of ["How to read this", "How this works", "Glossary", "Copy view link"]) {
        await expect(bar.getByRole("button", { name, exact: true })).toBeHidden();
      }
      await expect(bar.getByRole("link", { name: "What's new" })).toBeHidden();
      await expect(bar.getByLabel("Monitored system")).toBeVisible();
      if (q) await expect(bar.getByRole("combobox", { name: /Search systems/ })).toBeVisible();
      // The bar costs far less of the screen than the five rows it used to take.
      const h = (await bar.boundingBox())!.height;
      expect(h, "site bar height").toBeLessThan(PHONE.height * 0.22);

      // Keyboard: open, Tab into the menu, Escape closes and returns focus to the toggle.
      await toggle.focus();
      await page.keyboard.press("Enter");
      await expect(toggle).toHaveAttribute("aria-expanded", "true");
      await expect(menu).toBeVisible();
      for (const el of await menu.locator("button, a").all()) {
        const b = (await el.boundingBox())!;
        expect(b.height).toBeGreaterThanOrEqual(43.5);
      }
      await page.keyboard.press("Tab");
      expect(await menu.evaluate((m) => m.contains(document.activeElement))).toBe(true);
      await page.keyboard.press("Escape");
      await expect(toggle).toHaveAttribute("aria-expanded", "false");
      await expect(toggle).toBeFocused();
      await expect(menu).toBeHidden();
      const tb = (await toggle.boundingBox())!;
      expect(Math.min(tb.width, tb.height)).toBeGreaterThanOrEqual(43.5);
      expect(app.errors).toEqual([]);
    });
  }

  test("the glossary opened from the menu returns focus to Menu when closed", async ({ page }) => {
    await page.setViewportSize(PHONE);
    await openView(page, "?sys=us");
    const toggle = page.locator(".global-nav").getByRole("button", { name: "Menu" });
    await toggle.click();
    await page.locator(".global-nav").getByRole("button", { name: "Glossary", exact: true }).click();
    const dlg = page.getByRole("dialog", { name: "Glossary" });
    await expect(dlg).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dlg).toBeHidden();
    await expect(toggle).toBeFocused();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  test("on a wide screen there is no Menu toggle and every tool is in the bar", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await openView(page, "?sys=us");
    const bar = page.locator(".global-nav");
    await expect(bar.getByRole("button", { name: "Menu" })).toBeHidden();
    for (const name of ["How to read this", "How this works", "Glossary", "Copy view link"]) {
      await expect(bar.getByRole("button", { name, exact: true })).toBeVisible();
    }
    await expect(bar.getByRole("link", { name: "What's new" })).toBeVisible();
  });
});

test.describe("country page selects", () => {
  test("the page's own filters are styled like the site's other selects", async ({ page }) => {
    await openView(page, "?sys=us");
    const styles = await page.locator(".region-select select, .event-filters select").evaluateAll((els) => els.map((e) => {
      const s = getComputedStyle(e);
      return { bg: s.backgroundColor, border: s.borderTopColor, radius: s.borderTopLeftRadius };
    }));
    expect(styles.length).toBeGreaterThanOrEqual(2);
    const ref = await page.locator(".global-nav .sys-switch select").evaluate((e) => getComputedStyle(e).backgroundColor);
    for (const s of styles) {
      expect(s.bg).toBe(ref);
      expect(s.radius).not.toBe("0px");
    }
  });
});
