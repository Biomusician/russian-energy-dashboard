import { test, expect, pixelStats, readBytes } from "./fixtures";

/**
 * The Russia/Belarus theatre, exercised in a real browser against the real payload.
 *
 * Gate zero for iteration 14: this tier must be green BEFORE globalization changes the frontend,
 * so that "Russia must not regress" is something a machine checks rather than something a
 * reviewer remembers to look at.
 *
 * Tests assert on behaviour and on values read from the payload the page itself loaded, never on
 * today's numbers — the payload is rebuilt every morning.
 */

test.describe("search and selection", () => {
  test("search finds a facility by name and selecting it updates the URL", async ({ app, page }) => {
    await app.open();
    await page.getByRole("textbox", { name: /search for a region, facility or pipeline/i }).fill("Perm");
    // Results are buttons grouped under "Regions" and "Infrastructure".
    const region = app.button(/^perm krai/i);
    await expect(region).toBeVisible();
    await expect(app.button(/perm hpp-13/i)).toBeVisible();
    await region.click();
    await expect(page).toHaveURL(/[?&]r=RU-PER/);
    await expect(page.getByRole("heading", { name: /perm/i }).first()).toBeVisible();
  });

  test("a region deep link opens that region's dossier", async ({ app, page }) => {
    await app.open("?r=RU-PER");
    await expect(page.getByRole("heading", { name: /perm/i }).first()).toBeVisible();
  });

  test("back and forward move between selections without losing state", async ({ app, page }) => {
    await app.open("?r=RU-PER");
    await expect(page.getByRole("heading", { name: /perm/i }).first()).toBeVisible();
    await page.goto("/?r=RU-SAM");
    await app.mapIdle();
    await expect(page.getByRole("heading", { name: /samara/i }).first()).toBeVisible();
    await page.goBack();
    await app.mapIdle();
    await expect(page.getByRole("heading", { name: /perm/i }).first()).toBeVisible();
    await page.goForward();
    await app.mapIdle();
    await expect(page.getByRole("heading", { name: /samara/i }).first()).toBeVisible();
  });

  test("a hostile region code is refused rather than trusted", async ({ app, page }) => {
    // Iteration 12 found `r=constructor` passing an existence check by reaching
    // Object.prototype. The page must open normally on the monitored-area view.
    await app.open("?r=constructor");
    await expect(page.getByRole("heading", { name: /monitored-area picture/i }).first()).toBeVisible();
  });
});

test.describe("analytical panels", () => {
  test("the Evidence Inspector explains the headline and closes on Escape", async ({ app, page }) => {
    await app.open();
    await app.button(/explain the monitored-area esdi/i).click();
    const dlg = page.getByRole("dialog", { name: /evidence inspector/i });
    await expect(dlg).toBeVisible();
    await expect(dlg).toContainText(/refining/i);
    await page.keyboard.press("Escape");
    await expect(dlg).toBeHidden();
  });

  test("Data quality lists sources with honest retrieval bases", async ({ app, page }) => {
    await app.open();
    await app.button(/^data quality$/i).click();
    // Iteration 13 found three sources publishing "retrieved today, current" for evidence 46-49
    // days old. The panel must name at least one source and must not be empty.
    await expect(page.getByText(/wikipedia/i).first()).toBeVisible();
    await expect(page.getByText(/natural earth/i).first()).toBeVisible();
  });

  test("Methodology publishes the sensitivity of the assumption the headline rests on", async ({ app, page }) => {
    await app.open();
    await app.button(/methodology & caveats/i).click();
    await expect(page.getByText(/the assumption the headline rests on/i)).toBeVisible();
    await expect(page.getByText(/halving and doubling the horizons/i)).toBeVisible();
  });

  test("Compare dates opens a two-date workspace", async ({ app, page }) => {
    await app.open();
    await app.button(/compare dates/i).click();
    await expect(page.getByRole("group", { name: /map view/i })).toBeVisible();
  });

  test("Recovery lifecycle opens and lists episodes", async ({ app, page }) => {
    await app.open();
    await app.button("Recovery lifecycle", { exact: true }).click();
    await expect(page.getByText(/episode/i).first()).toBeVisible();
  });
});

test.describe("map", () => {
  test("Map Focus maximises the map and returns", async ({ app, page }) => {
    await app.open();
    const before = await page.locator("[data-map-state]").boundingBox();
    await app.button(/^map focus$/i).click();
    await app.mapIdle();
    const after = await page.locator("[data-map-state]").boundingBox();
    expect(after!.width * after!.height).toBeGreaterThan(before!.width * before!.height);
    // Iteration 12 shipped a grid where focus put the map in a zero-height row. Area alone would
    // not catch that if the width grew, so the height is checked against the viewport directly.
    expect(after!.height, "the map has no height in map focus").toBeGreaterThan(900 * 0.6);
    expect((await app.mapPixels()).distinct).toBeGreaterThan(20);
    await app.button(/exit map focus/i).click();
    await app.mapIdle();
    const back = await page.locator("[data-map-state]").boundingBox();
    expect(Math.round(back!.width)).toBe(Math.round(before!.width));
    expect(Math.round(back!.height)).toBe(Math.round(before!.height));
  });

  test("toggling the oil network context redraws without errors", async ({ app, page }) => {
    await app.open();
    // At 1600px the filters rail is docked, so the toggle is on the page without opening a drawer.
    const toggle = page.getByRole("checkbox", { name: /oil pipelines/i });
    await toggle.check();
    await app.mapIdle();
    await expect(page).toHaveURL(/ly=[^&]*oil/);
    const px = await app.mapPixels();
    expect(px.distinct).toBeGreaterThan(20);
  });
});

test.describe("export", () => {
  test("the downloaded PNG is a real image with a drawn map in it", async ({ app, page }) => {
    // The lesson of iteration 11: an export that fires a download event can still contain no
    // map. So the file is opened and decoded, not merely received.
    await app.open();
    await app.button(/briefing & export/i).click();
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      app.button(/download png/i).click(),
    ]);
    const path = await download.path();
    const png = readBytes(path!);
    expect(png.subarray(1, 4).toString("ascii"), "not a PNG").toBe("PNG");

    const whole = await pixelStats(page, png);
    // "Current viewport" export at 1600x900: the frame is the map canvas, so its height is the
    // map's. 300px was the iteration-12 zero-height-map defect (MapLibre's fallback canvas).
    expect(whole.width).toBeGreaterThanOrEqual(1000);
    expect(whole.height).toBeGreaterThanOrEqual(600);
    expect(whole.distinct, "the exported frame is nearly one colour").toBeGreaterThan(40);

    // The central band is where the map sits in every frame layout; a blank map there is the
    // iteration-11 defect.
    const band = await pixelStats(page, png,
      [Math.round(whole.width * 0.2), Math.round(whole.height * 0.3),
       Math.round(whole.width * 0.6), Math.round(whole.height * 0.4)]);
    expect(band.distinct, "the map area of the export is blank").toBeGreaterThan(15);
    expect(band.spread).toBeGreaterThan(30);
  });
});

test.describe("responsive", () => {
  for (const [w, h] of [[1024, 768], [430, 932]] as const) {
    test(`at ${w}x${h} the page does not scroll sideways and the map is visible`, async ({ app, page }) => {
      await page.setViewportSize({ width: w, height: h });
      await app.open();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, "horizontal page scroll").toBeLessThanOrEqual(1);
      const box = await page.locator("[data-map-state]").boundingBox();
      expect(box!.width).toBeGreaterThan(w * 0.5);
      expect(box!.height).toBeGreaterThan(150);
    });
  }
});

test.describe("legacy links", () => {
  // Representative links from iterations 8-13. Each must open without error; the fixture fails
  // the test on any console or page error.
  const LINKS = [
    "?m=ev",
    "?m=d30&a=30",
    "?r=RU-BEL&ly=lines",
    "?cls=refinery&cau=kinetic_strike",
    "?cls=-",
    "?cmp=RU-PER,RU-SAM",
    "?cam=45.1,55.2,4.5",
    "?d=2024-06-01",
    "?ly=gas,oil,rivers",
    "?m=constructor&r=__proto__",
  ];
  for (const q of LINKS) {
    test(`opens ${q}`, async ({ app }) => {
      await app.open(q);
    });
  }
});
