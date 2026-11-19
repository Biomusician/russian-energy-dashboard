import { test, expect, readBytes } from "./fixtures";

/**
 * What a map says while it loads (iteration 22), in a real browser.
 *
 * Every map used to sit blank for two to three seconds. Each now says, inside its own box, what it
 * is waiting for, driven by real load events (src/mapLoad.ts); the words are gone when the map is
 * drawn, and the box never changes size. A request is HELD open here, not slowed by a timer, so the
 * test sees the waiting state for as long as it needs and releases it when it has looked.
 *
 * The theatre's line network (2.4 MB) no longer blocks the theatre: the regions, the choropleth and
 * the controls draw without it, the lines join when the file lands, and a PNG made with the line
 * layer on waits for the file.
 */

type Page = import("@playwright/test").Page;

/** Hold every request for `glob` until `release()` is called. */
async function hold(page: Page, glob: string) {
  let release!: () => void;
  const held = new Promise<void>((res) => { release = res; });
  let seen = 0;
  await page.route(glob, async (route) => { seen += 1; await held; await route.continue(); });
  return { release, requests: () => seen };
}

/** Record, from before any page script runs, every text the map-load indicators show and the size
 *  of the map box each time: the proof that the words appeared and that nothing moved. */
async function recordIndicator(page: Page) {
  await page.addInitScript(() => {
    const w = window as unknown as { __mapLoad: { text: string; phase: string; w: number; h: number }[] };
    w.__mapLoad = [];
    const note = (el: Element) => {
      const box = (el.closest(".simple-map-stage, .mapwrap") ?? el).getBoundingClientRect();
      const text = el.querySelector(".map-load-text")?.textContent ?? "";
      const phase = el.getAttribute("data-map-load") ?? "";
      const last = w.__mapLoad[w.__mapLoad.length - 1];
      if (!last || last.text !== text || last.phase !== phase) w.__mapLoad.push({ text, phase, w: Math.round(box.width), h: Math.round(box.height) });
    };
    new MutationObserver(() => document.querySelectorAll(".map-load").forEach(note))
      .observe(document, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ["data-map-load"] });
  });
}
const recorded = (page: Page) =>
  page.evaluate(() => (window as unknown as { __mapLoad: { text: string; phase: string; w: number; h: number }[] }).__mapLoad);

/** How many pixels differ visibly between two PNGs of the same size, counted in the browser. */
async function pixelsDiffering(page: Page, a: Buffer, b: Buffer): Promise<number> {
  return page.evaluate(async ([x, y]) => {
    const load = async (b64: string) => {
      const img = new Image();
      img.src = `data:image/png;base64,${b64}`;
      await img.decode();
      const c = document.createElement("canvas");
      c.width = img.naturalWidth; c.height = img.naturalHeight;
      const ctx = c.getContext("2d")!;
      ctx.drawImage(img, 0, 0);
      return ctx.getImageData(0, 0, c.width, c.height);
    };
    const [p, q] = [await load(x), await load(y)];
    if (p.width !== q.width || p.height !== q.height) return -1;
    let n = 0;
    for (let i = 0; i < p.data.length; i += 4) {
      if (Math.abs(p.data[i] - q.data[i]) > 24 || Math.abs(p.data[i + 1] - q.data[i + 1]) > 24 || Math.abs(p.data[i + 2] - q.data[i + 2]) > 24) n++;
    }
    return n;
  }, [a.toString("base64"), b.toString("base64")]);
}

test.describe("country and world maps", () => {
  test("a country map says what it is loading, then nothing, and its box never changes size", async ({ app, page }) => {
    await recordIndicator(page);
    await app.open("?sys=us");
    const indicator = page.locator(".country-map .map-load");
    await expect(indicator).toHaveAttribute("data-map-load", "ready");
    await expect(indicator.getByRole("status")).toHaveText("");
    const seen = await recorded(page);
    // The first thing the box said was that the geometry was loading; the last is nothing.
    expect(seen[0]).toMatchObject({ text: "Loading map geometry…", phase: "geometry" });
    expect(seen[seen.length - 1]).toMatchObject({ text: "", phase: "ready" });
    for (const s of seen) expect(["Loading map geometry…", "Loading data…", ""]).toContain(s.text);
    // No layout shift: the map box is the same size in every state.
    expect(new Set(seen.map((s) => `${s.w}x${s.h}`)).size).toBe(1);
    expect(seen[0].h).toBeGreaterThan(200);
    // Once drawn it takes no room and blocks nothing.
    expect(await indicator.evaluate((el) => el.getBoundingClientRect().width)).toBeLessThanOrEqual(2);
    expect(app.errors).toEqual([]);
  });

  test("the Gulf overview's map says what it is loading, then nothing", async ({ app, page }) => {
    await recordIndicator(page);
    await app.open("?group=gulf");
    const indicator = page.locator(".map-load");
    await expect(indicator).toHaveCount(1);
    await expect(indicator).toHaveAttribute("data-map-load", "ready");
    await expect(indicator.getByRole("status")).toHaveText("");
    const seen = await recorded(page);
    expect(seen[0]).toMatchObject({ text: "Loading map geometry…", phase: "geometry" });
    expect(seen[seen.length - 1]).toMatchObject({ text: "", phase: "ready" });
    expect(new Set(seen.map((s) => `${s.w}x${s.h}`)).size).toBe(1);
    expect(app.errors).toEqual([]);
  });

  test("the world map says 'Loading map geometry…' while its file is held, and stops when it is drawn", async ({ app, page }) => {
    const world = await hold(page, "**/data/global/world.geojson");
    await page.goto("/");
    const section = page.getByRole("region", { name: "World energy context" });
    const waiting = section.locator(".map-load-placeholder");
    await expect(waiting.getByRole("status")).toHaveText("Loading map geometry…");
    expect(world.requests()).toBe(1);
    const before = await section.locator(".global-map-wrap").boundingBox();
    // The rest of the page does not wait for the map.
    await expect(page.getByRole("article").first()).toBeVisible();
    world.release();
    await app.mapIdle();
    await expect(section.locator(".map-load")).toHaveAttribute("data-map-load", "ready");
    await expect(section.locator(".map-load").getByRole("status")).toHaveText("");
    await expect(waiting).toHaveCount(0);
    const after = await section.locator(".global-map-wrap").boundingBox();
    expect(Math.abs(after!.height - before!.height)).toBeLessThanOrEqual(2);
    expect(app.errors).toEqual([]);
  });

  test("a map that cannot be drawn says so, offers a retry, and leaves the list usable", async ({ app, page }) => {
    // No WebGL: every map context is refused until the test allows it again.
    await page.addInitScript(() => {
      const w = window as unknown as { __noWebGL: boolean };
      w.__noWebGL = true;
      const real = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, kind: string, ...rest: unknown[]) {
        if (w.__noWebGL && /webgl/i.test(kind)) return null;
        return (real as (...a: unknown[]) => unknown).call(this, kind, ...rest);
      } as typeof HTMLCanvasElement.prototype.getContext;
    });
    app.allowConsoleError(/webgl/i);
    await page.goto("/?sys=us");
    const indicator = page.locator(".country-map .map-load");
    await expect(indicator).toHaveAttribute("data-map-load", "failed");
    await expect(indicator.getByRole("status")).toHaveText(
      "The map could not be drawn. The list of reported events beside it does not need the map.");
    // The alternative is really there: the records, their filters and the region select.
    await expect(page.locator(".event-card").first()).toBeVisible();
    await expect(page.locator(".rf-count")).toContainText("published records");
    await page.getByLabel(/Choose a state/i).selectOption({ label: "Texas" });
    await expect(page.locator(".events-panel h2").first()).toHaveText("Texas");

    await page.evaluate(() => { (window as unknown as { __noWebGL: boolean }).__noWebGL = false; });
    await indicator.getByRole("button", { name: "Try again" }).click();
    await app.mapIdle();
    await expect(indicator).toHaveAttribute("data-map-load", "ready");
    await expect(indicator.getByRole("button")).toHaveCount(0);
    const px = await app.mapPixels();
    expect(px.distinct).toBeGreaterThan(3);
  });
});

test.describe("the theatre map and its line network", () => {
  test("regions, choropleth and controls draw while the line file is still held", async ({ app, page }) => {
    await recordIndicator(page);
    const lines = await hold(page, "**/data/assets_lines.geojson");
    await page.goto("/?sys=ru");
    // The map reaches MapLibre's idle state without the 2.4 MB file.
    await app.mapIdle();
    expect(lines.requests()).toBe(1);
    await expect(page.locator(".ribbon")).toContainText("ESDI");
    await expect(page.locator(".camera-controls button").first()).toBeVisible();
    const px = await app.mapPixels();
    expect(px.distinct, "the choropleth is not drawn").toBeGreaterThan(20);
    // The line layer is off by default, so nothing is said about a file the reader did not ask for.
    const indicator = page.locator(".mapwrap .map-load");
    await expect(indicator).toHaveAttribute("data-map-load", "ready");
    await expect(indicator.getByRole("status")).toHaveText("");
    const seen = await recorded(page);
    expect(seen[0]).toMatchObject({ text: "Loading map geometry…", phase: "geometry" });
    expect(new Set(seen.map((s) => `${s.w}x${s.h}`)).size).toBe(1);
    lines.release();
    expect(app.errors).toEqual([]);
  });

  test("with the line layer on, the map says 'Loading network lines…' until the file lands, then draws them", async ({ app, page }) => {
    const lines = await hold(page, "**/data/assets_lines.geojson");
    await page.goto("/?sys=ru&ly=lines");
    await app.mapIdle();
    const indicator = page.locator(".mapwrap .map-load");
    await expect(indicator).toHaveAttribute("data-map-load", "late");
    await expect(indicator.getByRole("status")).toHaveText("Loading network lines…");
    // The map under the message is drawn and usable while it waits.
    await expect(page.locator(".ribbon")).toContainText("ESDI");
    const without = await page.locator("[data-map-state] canvas").first().screenshot();

    lines.release();
    await expect(indicator).toHaveAttribute("data-map-load", "ready");
    await expect(indicator.getByRole("status")).toHaveText("");
    await app.mapIdle();
    const withLines = await page.locator("[data-map-state] canvas").first().screenshot();
    expect(await pixelsDiffering(page, without, withLines), "the lines were not drawn when the file arrived").toBeGreaterThan(400);
    expect(lines.requests()).toBe(1);
    expect(app.errors).toEqual([]);
  });

  test("a PNG made with the line layer on waits for the line file and carries the lines", async ({ app, page }) => {
    const lines = await hold(page, "**/data/assets_lines.geojson");
    await page.goto("/?sys=ru&ly=lines");
    await app.mapIdle();
    await app.button(/briefing & export/i).click();
    let arrived = false;
    const first = page.waitForEvent("download").then((d) => { arrived = true; return d; });
    await app.button(/download png/i).click();
    // Held: no file may be written while the lines the reader asked for are missing.
    await expect(page.locator(".mapwrap .map-load")).toHaveAttribute("data-map-load", "late");
    await page.waitForTimeout(1500);
    expect(arrived, "an image was written before its line layer had loaded").toBe(false);
    lines.release();
    const early = readBytes((await (await first).path())!);
    expect(early.subarray(1, 4).toString("ascii")).toBe("PNG");

    // The same view exported again with everything loaded is the reference.
    await expect(page.locator(".mapwrap .map-load")).toHaveAttribute("data-map-load", "ready");
    const [second] = await Promise.all([page.waitForEvent("download"), app.button(/download png/i).click()]);
    const settled = readBytes((await second.path())!);

    // And the control: the same view with the line layer off.
    await page.goto("/?sys=ru");
    await app.mapIdle();
    await app.button(/briefing & export/i).click();
    const [third] = await Promise.all([page.waitForEvent("download"), app.button(/download png/i).click()]);
    const noLines = readBytes((await third.path())!);

    // The control first: on a settled map the line layer changes the image visibly.
    const control = await pixelsDiffering(page, settled, noLines);
    expect(control, "the line layer makes no visible difference to the image, so this proves nothing").toBeGreaterThan(400);
    // Then the claim: the image made while the file was held matches the settled one, lines and all.
    // (Checked by breaking it: without the line data in the copied style it matches the no-lines image.)
    const sameView = await pixelsDiffering(page, early, settled);
    expect(sameView, "the two images of the same view are different sizes").toBeGreaterThanOrEqual(0);
    expect(sameView, `the image made while the line file was held differs from the settled one by ${sameView} px (the line layer itself is ${control} px): its lines are missing`)
      .toBeLessThan(control / 4);
    expect(app.errors).toEqual([]);
  });

  test("a line file that fails costs the lines, says so with a retry, and never the page", async ({ app, page }) => {
    app.allowConsoleError(/Failed to load resource|assets_lines/);
    let fail = true;
    await page.route("**/data/assets_lines.geojson", (route) => (fail ? route.abort() : route.continue()));
    await page.goto("/?sys=ru&ly=lines");
    await app.mapIdle();
    await expect(page.locator(".ribbon")).toContainText("ESDI");
    const indicator = page.locator(".mapwrap .map-load");
    await expect(indicator).toHaveAttribute("data-map-load", "late_failed");
    await expect(indicator.getByRole("status")).toHaveText("Network lines could not be loaded. The rest of the map is complete.");
    fail = false;
    await indicator.getByRole("button", { name: "Try again" }).click();
    await expect(indicator).toHaveAttribute("data-map-load", "ready");
    await expect(indicator.getByRole("button")).toHaveCount(0);
  });
});
