import { test, expect, mapPoint } from "./fixtures";
import type { Page } from "@playwright/test";

/**
 * Iteration 23 red-team fixes on the home (MU-01..MU-07, H-03): every monitored system can be
 * clicked or tapped at the default view, a choice from the list, the search or a restored entry
 * moves focus to the card, the A to Z list is one column, Russia from the list says it is partly
 * monitored, and the search finds Sevastopol and the Help sections. Places are found from the
 * served files, never typed in here.
 */

const SEARCH = /Search systems, regions and terms/;
type Sys = { id: string; name: string; kind: string; bounds?: number[] };
type Ring = number[][];

/** A point inside each system, from the served geometry: a small system's marker (its bounds'
 *  centre), else a point inside its largest ring (the ring's centroid, or the middle of the first
 *  inside stretch of the centroid's parallel when the centroid falls outside). */
async function systemPoints(page: Page): Promise<{ sys: Sys; lon: number; lat: number }[]> {
  return page.evaluate(async () => {
    const m = await (await fetch("/data/global/manifest.json")).json();
    const w = await (await fetch("/data/global/world.geojson")).json();
    const area = (r: Ring) => Math.abs(r.reduce((a, p, i) => { const q = r[(i + 1) % r.length]; return a + p[0] * q[1] - q[0] * p[1]; }, 0) / 2);
    const inside = (r: Ring, x: number, y: number) => {
      let c = false;
      for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
        const [xi, yi] = r[i], [xj, yj] = r[j];
        if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
      }
      return c;
    };
    return m.systems.map((sys: Sys) => {
      const b = sys.bounds;
      if (b && Math.max(b[2] - b[0], b[3] - b[1]) < 4) return { sys, lon: (b[0] + b[2]) / 2, lat: (b[1] + b[3]) / 2 };
      const rings: Ring[] = [];
      for (const f of w.features) {
        if (f.properties.system_id !== sys.id || f.properties.status === "occupied") continue;
        const g = f.geometry;
        const polys = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
        for (const p of polys) rings.push(p[0]);
      }
      const r = rings.sort((a, b2) => area(b2) - area(a))[0];
      let cx = 0, cy = 0;
      for (const p of r) { cx += p[0]; cy += p[1]; }
      cx /= r.length; cy /= r.length;
      if (!inside(r, cx, cy)) {
        const xs = [...Array(400).keys()].map((i) => -180 + i * 0.9).filter((x) => inside(r, x, cy));
        cx = xs[Math.floor(xs.length / 2)];
      }
      return { sys, lon: cx, lat: cy };
    });
  });
}

/** After a click or tap on `sys`: open it, from the page itself, its sheet or a choice. */
async function reachOpen(page: Page, sys: Sys) {
  const want = new RegExp(`\\?sys=${sys.id}$`);
  await expect.poll(async () => want.test(page.url()) || (await page.locator(".sel-card").count()) > 0).toBe(true);
  if (want.test(page.url())) return;
  const card = page.locator(".sel-card");
  const link = card.getByRole("link", { name: sys.name, exact: true }).or(card.getByRole("link", { name: `Open ${sys.name}`, exact: true }));
  await link.first().click();
  await expect(page).toHaveURL(want);
}

test.describe("MU-01: every monitored system can be clicked at the default view", () => {
  for (const [w, h, touch] of [[1440, 900, false], [390, 844, true]] as const) {
    test.describe(`${w}x${h}`, () => {
      test.use({ viewport: { width: w, height: h }, hasTouch: touch, isMobile: touch });
      test(`${touch ? "tap" : "click"} each system on the world map and it opens`, async ({ app, page }) => {
        await app.open("");
        const points = await systemPoints(page);
        expect(points.length).toBeGreaterThanOrEqual(13);
        for (const { sys, lon, lat } of points) {
          await page.goto("/");
          await app.mapIdle();
          await page.locator(".home-map-box").scrollIntoViewIfNeeded();
          const p = await mapPoint(page, lon, lat);
          if (touch) await page.touchscreen.tap(p.x, p.y); else await page.mouse.click(p.x, p.y);
          await reachOpen(page, sys);
        }
        expect(app.errors).toEqual([]);
      });
    });
  }
});

test.describe("MU-02: Show on map on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  test("brings the map into view, and every Gulf member can be tapped at the group's zoom", async ({ app, page }) => {
    await app.open("");
    const m = await page.evaluate(async () => (await fetch("/data/global/manifest.json")).json());
    const g = m.groups.gulf_littoral;
    const show = page.locator("#where-to-explore").getByRole("button", { name: /Show on map/ });
    await show.scrollIntoViewIfNeeded();
    const before = await page.locator(".home-map-box [data-map-view]").getAttribute("data-map-view");
    await show.tap();
    await expect.poll(() => page.locator(".home-map-box [data-map-view]").getAttribute("data-map-view")).not.toBe(before);
    await app.mapIdle();
    const box = (await page.locator(".home-map-box").boundingBox())!;
    expect(box.y).toBeGreaterThanOrEqual(-1);
    expect(box.y + box.height).toBeLessThanOrEqual(844);
    const view = (await page.locator(".home-map-box [data-map-view]").getAttribute("data-map-view"))!;
    const points = (await systemPoints(page)).filter((p) => g.members.includes(p.sys.id));
    expect(points.length).toBe(g.members.length);
    for (const { sys, lon, lat } of points) {
      await page.locator(".sel-sheet").getByRole("button", { name: /^Close/ }).click().catch(() => undefined);
      expect(await page.locator(".home-map-box [data-map-view]").getAttribute("data-map-view")).toBe(view);
      const p = await mapPoint(page, lon, lat);
      await page.touchscreen.tap(p.x, p.y);
      const sheet = page.locator(".sel-sheet");
      await expect(sheet).toBeVisible();
      const link = sheet.getByRole("link", { name: sys.name, exact: true }).or(sheet.getByRole("link", { name: `Open ${sys.name}`, exact: true }));
      await expect(link.first(), `${sys.name} is not reachable by a tap at the group zoom`).toBeVisible();
    }
  });
});

test.describe("MU-03 / MU-07: keyboard focus follows the choice", () => {
  test("from the A to Z list, the card's heading takes focus; Escape gives it back", async ({ app, page }) => {
    await app.open("");
    const az = page.locator("#where-to-explore .hp-az");
    await az.locator("summary").focus();
    await page.keyboard.press("Enter");
    const item = az.getByRole("button", { name: "Mongolia", exact: true });
    await item.focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("#sel-card-title")).toBeFocused();
    await expect(page.locator("#sel-card-title")).toHaveText("Mongolia");
    // One Tab reaches the card's own controls, not the end of a long list.
    await page.keyboard.press("Tab");
    await expect(page.locator(".sel-card").getByRole("button", { name: /^Close/ })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(item).toBeFocused();
  });

  test("from the search, a country without a system focuses its card", async ({ app, page }) => {
    await app.open("");
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.focus();
    await page.keyboard.type("Mongolia");
    await page.keyboard.press("Enter");
    await expect(page.locator("#sel-card-title")).toBeFocused();
  });

  test("Back to a restored card with no control to return to focuses the card, never the body", async ({ app, page }) => {
    await app.open("");
    const az = page.locator("#where-to-explore .hp-az");
    await az.locator("summary").focus();
    await page.keyboard.press("Enter");
    await az.getByRole("button", { name: "Mongolia", exact: true }).focus();
    await page.keyboard.press("Enter");
    await page.locator(".global-nav").getByRole("link", { name: "Help", exact: true }).focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/view=help/);
    await page.goBack();
    await expect(page.locator(".sel-card")).toHaveAttribute("data-sel", "MNG");
    await expect(page.locator("#sel-card-title")).toBeFocused();
  });
});

test.describe("MU-04 / MU-05 / MU-06 / H-03", () => {
  test("the A to Z list is one column that never scrolls sideways", async ({ app, page }) => {
    await app.open("");
    const az = page.locator("#where-to-explore .hp-az");
    await az.locator("summary").click();
    const list = az.locator(".hp-az-list");
    const m = await list.evaluate((el) => ({ sw: el.scrollWidth, cw: el.clientWidth }));
    expect(m.sw).toBeLessThanOrEqual(m.cw);
    const xs = await az.locator("button.hp-az-item").evaluateAll((bs) => bs.slice(0, 40).map((b) => Math.round(b.getBoundingClientRect().left)));
    expect(new Set(xs).size).toBe(1);
  });

  test("Russia from the search is partly monitored, as its option says", async ({ app, page }) => {
    await app.open("");
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.fill("Russia");
    const opt = page.getByRole("listbox", { name: "Search results" }).getByRole("option").filter({ hasText: /^Country/ }).first();
    await expect(opt).toContainText("Partly monitored, in the Russia, Belarus & Crimea theatre");
    await opt.click();
    await expect(page.locator(".sel-card .sel-status")).toHaveText("Partly monitored, in the Russia, Belarus & Crimea theatre");
    await expect(page.locator(".sel-card")).not.toContainText("Outside the monitored area");
  });

  test("Sevastopol finds the Crimea unit, described as occupied", async ({ app, page }) => {
    await app.open("");
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.focus();
    await box.fill("Sevastopol");
    const opt = page.getByRole("listbox", { name: "Search results" }).getByRole("option").first();
    await expect(opt).toContainText("Crimea");
    await expect(opt).toContainText("Occupied unit, internationally Ukrainian");
  });

  test("csv finds the Help section on exports and opens it", async ({ app, page }) => {
    await app.open("");
    const box = page.getByRole("combobox", { name: SEARCH });
    await box.fill("csv");
    const opt = page.getByRole("listbox", { name: "Search results" }).getByRole("option").filter({ hasText: "Exports and sharing" });
    await expect(opt).toContainText("Help section");
    await opt.click();
    await expect(page).toHaveURL(/\?view=help#exports$/);
    await expect(page.locator("#exports")).toBeVisible();
  });
});
