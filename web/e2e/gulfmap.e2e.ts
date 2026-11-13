import { test, expect, colourGrid, pixelStats, readBytes } from "./fixtures";

/**
 * The regional overview as a product, and the shared map's controls (iteration 21).
 *
 * The first screen must say what the view is, show the members, the map and the control that
 * colours it; a chosen figure always shows its definition, year, unit, source and accounting
 * convention; small members are found from a list, by keyboard as well as pointer; and the reader's
 * selection never reaches the exported brief, where a highlighted country would read as the one
 * that matters. Every figure asserted is read from the payload the page loaded.
 */

type Page = import("@playwright/test").Page;
type Metric = { label: string; unit: string; year: number; definition: string; source_id: string };
type Sys = { system_id: string; name: string; a3: string };

const gulf = (page: Page) => page.evaluate(() => fetch("/data/global/gulf.json").then((r) => r.json()));
const manifest = (page: Page) => page.evaluate(() => fetch("/data/global/manifest.json").then((r) => r.json()));
const members = (page: Page) => page.locator(".member-list").getByRole("button");

/** Pixels of the selection colour (#2ad4ee) in a PNG: the mark of a chosen member. */
async function cyanPixels(page: Page, png: Buffer): Promise<number> {
  const b64 = png.toString("base64");
  return page.evaluate(async (b64) => {
    const img = new Image();
    img.src = `data:image/png;base64,${b64}`;
    await img.decode();
    const c = document.createElement("canvas");
    c.width = img.naturalWidth; c.height = img.naturalHeight;
    const g = c.getContext("2d")!;
    g.drawImage(img, 0, 0);
    const d = g.getImageData(0, 0, c.width, c.height).data;
    let n = 0;
    for (let i = 0; i < d.length; i += 4) if (Math.abs(d[i] - 42) < 30 && Math.abs(d[i + 1] - 212) < 30 && Math.abs(d[i + 2] - 238) < 30) n++;
    return n;
  }, b64);
}

const gridDiff = (a: number[][], b: number[][]) => a.filter((c, i) => Math.max(...c.map((v, k) => Math.abs(v - b[i][k]))) > 12).length;

async function mapGrid(page: Page) {
  return colourGrid(page, await page.locator("[data-map-state]").screenshot(), 10, 6);
}

test.describe("Gulf overview: first screen", () => {
  for (const [w, h] of [[1600, 900], [390, 844]] as const) {
    test(`at ${w}x${h} the first screen holds the purpose, the members, the map and the metric control`, async ({ app, page }) => {
      await page.setViewportSize({ width: w, height: h });
      await app.open("?group=gulf");
      const g = await gulf(page);
      const inView = async (sel: ReturnType<Page["locator"]>, what: string) => {
        const b = await sel.boundingBox();
        expect(b, `${what} is not rendered`).not.toBeNull();
        expect(b!.y, `${what} starts above the page`).toBeGreaterThanOrEqual(0);
        expect(b!.y + Math.min(b!.height, 44), `${what} is below the first screen`).toBeLessThanOrEqual(h);
      };
      await inView(page.locator(".group-purpose"), "the purpose line");
      await expect(page.locator(".group-purpose")).toContainText(g.label);
      await inView(page.locator(".group-caveat-line"), "the caveat line");
      await expect(page.locator(".group-caveat-line")).toContainText("not comparable between countries");
      await expect(page.locator(".group-caveat-line")).toContainText("National context only");
      await inView(page.getByLabel("Regional map metric"), "the metric control");
      await inView(members(page).first(), "the member list");
      await expect(members(page)).toHaveCount((g.systems as Sys[]).length);
      const map = await page.locator("[data-map-state]").boundingBox();
      expect(map!.y, "the map starts too low").toBeLessThan(h - 200);
      expect(map!.height).toBeGreaterThan(200);
      // The long statements are below the map, one link away.
      const notes = await page.locator("#group-notes").boundingBox();
      expect(notes!.y).toBeGreaterThan(map!.y);
      await page.locator(".group-caveat-line a").click();
      await expect(page).toHaveURL(/#group-notes$/);
      await expect(page.getByRole("note")).toBeInViewport();
    });
  }

  test("the default map is geography only, says so on the map, and members stand apart from other countries", async ({ app, page }) => {
    await app.open("?group=gulf");
    await expect(page.getByLabel("Regional map metric")).toHaveValue("none");
    await expect(page.locator(".map-state-note")).toHaveText("Geography only — choose a national figure to colour the map");
    await expect(page.getByRole("region", { name: "About this figure" })).toHaveCount(0);
    const legend = page.getByLabel("Map legend");
    await expect(legend).toContainText("member, in this view");
    await expect(legend).toContainText("other countries: geography only");
    // Members and other countries are visibly different: the map has more than one land colour.
    const px = await app.mapPixels();
    expect(px.distinct).toBeGreaterThan(8);
    await page.getByLabel("Regional map metric").selectOption({ index: 1 });
    await expect(page.locator(".map-state-note")).toHaveCount(0);
  });
});

test.describe("Gulf overview: a chosen figure explains itself", () => {
  test("every metric shows its definition, year, unit, source and the accounting convention beside the control", async ({ app, page }) => {
    await app.open("?group=gulf");
    const g = await gulf(page);
    const entries = Object.entries(g.metrics) as [string, Metric][];
    expect(entries.length).toBeGreaterThan(0);
    expect(g.accounting_convention, "the payload carries no accounting convention").toBeTruthy();
    const facts = page.getByRole("region", { name: "About this figure" });
    for (const [id, x] of entries) {
      await page.getByLabel("Regional map metric").selectOption(id);
      await expect(facts).toContainText(x.label);
      await expect(facts.locator(".metric-definition")).toHaveText(x.definition);
      await expect(facts).toContainText(String(x.year));
      await expect(facts).toContainText(x.unit);
      await expect(facts).toContainText(g.sources[x.source_id].name);
      await expect(facts.locator(".metric-accounting")).toContainText(g.accounting_convention);
      await expect(facts).toBeInViewport();
    }
  });
});

test.describe("Gulf overview: members", () => {
  test("the member list is alphabetical, and keyboard focus and Enter highlight, select and zoom", async ({ app, page }) => {
    await app.open("?group=gulf");
    const g = await gulf(page);
    const names = await members(page).allInnerTexts();
    expect(names.length).toBeGreaterThan(0);
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b, "en")));
    expect([...names].sort()).toEqual((g.systems as Sys[]).map((s) => s.name).sort());

    const before = await mapGrid(page);
    const beforeCyan = await cyanPixels(page, await page.locator("[data-map-state]").screenshot());
    // Keyboard only: focus the first member, Tab to the second, Enter.
    await members(page).first().focus();
    await expect(members(page).first()).toHaveClass(/is-pointed/);
    await page.keyboard.press("Tab");
    const target = members(page).nth(1);
    await expect(target).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(target).toHaveAttribute("aria-pressed", "true");
    const name = names[1];
    await expect(page.getByRole("status", { name: "Selected member" })).toContainText(name);
    await app.mapIdle();
    const after = await mapGrid(page);
    expect(gridDiff(before, after), "choosing a member did not move the map to it").toBeGreaterThan(6);
    const cyan = await cyanPixels(page, await page.locator("[data-map-state]").screenshot());
    expect(cyan, "the chosen member is not marked on the map").toBeGreaterThan(beforeCyan + 50);

    // Escape clears the choice; Reset view frames the region again.
    await target.focus();
    await page.keyboard.press("Escape");
    await expect(target).toHaveAttribute("aria-pressed", "false");
    await expect(page.getByRole("status", { name: "Selected member" })).toHaveCount(0);
    await page.getByRole("button", { name: "Reset view" }).focus();
    await page.keyboard.press("Enter");
    await app.mapIdle();
    expect(gridDiff(before, await mapGrid(page)), "Reset view did not return to the region").toBeLessThanOrEqual(3);
  });

  test("the smallest members are reachable: each zooms to its own manifest box", async ({ app, page }) => {
    await app.open("?group=gulf");
    const g = await gulf(page);
    const m = await manifest(page);
    const box = (id: string) => m.systems.find((s: { id: string }) => s.id === id).bounds as number[];
    const area = (b: number[]) => (b[2] - b[0]) * (b[3] - b[1]);
    const smallest = [...(g.systems as Sys[])].sort((a, b) => area(box(a.system_id)) - area(box(b.system_id)))[0];
    const before = await mapGrid(page);
    await page.locator(".member-list").getByRole("button", { name: smallest.name }).click();
    await app.mapIdle();
    expect(gridDiff(before, await mapGrid(page))).toBeGreaterThan(6);
    const open = page.getByRole("status", { name: "Selected member" }).getByRole("button", { name: `Open ${smallest.name}` });
    await expect(open).toBeVisible();
    await open.click();
    await expect(page.getByRole("heading", { name: smallest.name, level: 1 })).toBeVisible();
  });

  test("a tap on the map chooses a member and says what it is: nothing is hover-only", async ({ app, page }) => {
    await app.open("?group=gulf");
    await page.getByLabel("Regional map metric").selectOption({ index: 1 });
    await app.mapIdle();
    const mapEl = page.locator("[data-map-state]");
    const png = await mapEl.screenshot();
    // Find a pixel of member colour nearest the map centre and tap there.
    const pt = await page.evaluate(async (b64) => {
      const img = new Image();
      img.src = `data:image/png;base64,${b64}`;
      await img.decode();
      const c = document.createElement("canvas");
      c.width = img.naturalWidth; c.height = img.naturalHeight;
      const g = c.getContext("2d")!;
      g.drawImage(img, 0, 0);
      const d = g.getImageData(0, 0, c.width, c.height).data;
      let best: [number, number] | null = null; let bd = Infinity;
      for (let y = 60; y < c.height - 40; y += 4) for (let x = 0; x < c.width; x += 4) {
        const i = (y * c.width + x) * 4;
        // Ramp colours are green-blue and bright; other countries and sea are near-black.
        if (d[i + 1] > 100 && d[i + 1] > d[i] + 30) {
          const dist = Math.hypot(x - c.width / 2, y - c.height / 2);
          if (dist < bd) { bd = dist; best = [x, y]; }
        }
      }
      return best;
    }, png.toString("base64"));
    expect(pt, "no member pixel found on the map").not.toBeNull();
    await mapEl.click({ position: { x: pt![0], y: pt![1] } });
    const detail = page.getByRole("status", { name: "Selected member" });
    await expect(detail).toBeVisible();
    await expect(detail).toContainText("national total");
    await expect(page.locator(".member-btn[aria-pressed=true]")).toHaveCount(1);
  });
});

test.describe("Shared map controls", () => {
  for (const q of ["?group=gulf", "", "?sys=qa"]) {
    test(`${q || "home"}: zoom and reset are 44px controls that move the map and bring it back; credits are visible`, async ({ app, page }) => {
      await page.setViewportSize({ width: 390, height: 844 });
      await app.open(q);
      for (const name of ["Zoom in", "Zoom out", "Reset view"]) {
        const b = await page.getByRole("button", { name, exact: true }).first().boundingBox();
        expect(b!.width, `${name} target`).toBeGreaterThanOrEqual(44);
        expect(b!.height, `${name} target`).toBeGreaterThanOrEqual(44);
      }
      const before = await mapGrid(page);
      await page.getByRole("button", { name: "Zoom in", exact: true }).first().click();
      await app.mapIdle();
      expect(gridDiff(before, await mapGrid(page))).toBeGreaterThan(4);
      await page.getByRole("button", { name: "Reset view", exact: true }).first().click();
      await app.mapIdle();
      expect(gridDiff(before, await mapGrid(page))).toBeLessThanOrEqual(3);
      // Credits are text under the map, not a collapsed icon over it.
      const credits = page.locator(".map-credits").first();
      await expect(credits).toBeVisible();
      await expect(credits).toContainText("Natural Earth");
      const cb = await credits.boundingBox();
      const mb = await page.locator("[data-map-state]").boundingBox();
      expect(cb!.y).toBeGreaterThanOrEqual(mb!.y + mb!.height - 1);
    });
  }

  test("the regional map links to the same data as a table", async ({ app, page }) => {
    await app.open("?group=gulf");
    await page.getByRole("link", { name: "Same data as a table" }).click();
    await expect(page.locator("#group-table")).toBeFocused();
    await expect(page.locator(".group-table")).toBeInViewport();
  });

  test("a country map with nothing shaded says so on the map", async ({ app, page }) => {
    let checked = 0;
    for (const id of ["bh", "qa", "us"]) {
      await app.open(`?sys=${id}`);
      const regions = await page.evaluate((p) => fetch(p).then((r) => r.json()), `/data/systems/${id}/regions.geojson`).catch(() => null);
      const shaded = regions ? (regions.features as { properties: { recorded_events?: number | null } }[]).some((f) => (f.properties.recorded_events ?? 0) > 0) : null;
      if (shaded === null) continue;
      await expect(page.locator(".map-empty-note")).toHaveCount(shaded ? 0 : 1);
      if (!shaded) await expect(page.locator(".map-empty-note")).toContainText("nothing is shaded");
      checked += 1;
    }
    expect(checked, "no country's regions were read: this test proved nothing").toBeGreaterThan(0);
  });
});

test.describe("Gulf brief and the reader's selection", () => {
  test("a selected, zoomed member never reaches the brief, and the brief keeps its caveats", async ({ app, page }) => {
    await page.addInitScript(() => {
      const drawn: string[] = [];
      (window as unknown as { __drawn: string[] }).__drawn = drawn;
      const original = CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText = function (this: CanvasRenderingContext2D, text: string, x: number, y: number, maxWidth?: number) {
        if (this.canvas.width === 1600) drawn.push(String(text));
        return maxWidth === undefined ? original.call(this, text, x, y) : original.call(this, text, x, y, maxWidth);
      };
    });
    await app.open("?group=gulf");
    await page.getByLabel("Regional map metric").selectOption({ index: 1 });
    await app.mapIdle();
    const exportPng = async () => {
      await page.evaluate(() => { (window as unknown as { __drawn: string[] }).__drawn.length = 0; });
      const [d] = await Promise.all([page.waitForEvent("download"), app.button("Download brief (PNG)").click()]);
      const png = readBytes((await d.path())!);
      const texts = await page.evaluate(() => (window as unknown as { __drawn: string[] }).__drawn.slice());
      return { png, texts };
    };
    const plain = await exportPng();
    const first = (await members(page).allInnerTexts())[0];
    await members(page).first().click();
    await app.mapIdle();
    await expect(page.locator(".member-btn[aria-pressed=true]")).toHaveText(first);
    const chosen = await exportPng();

    // Same text, same order: the selection adds and moves nothing.
    expect(chosen.texts).toEqual(plain.texts);
    const all = chosen.texts.join(" ");
    expect(all).toContain("Countries in alphabetical order");
    expect(all).toContain("No index is published for any of them");
    expect(all).toContain("not an order of importance");
    expect(all).toContain("National context only");
    // Same picture: the brief frames the whole group whatever the reader zoomed to, and draws no
    // selection mark.
    const [a, b] = [await colourGrid(page, plain.png, 10, 6), await colourGrid(page, chosen.png, 10, 6)];
    expect(gridDiff(a, b), "the brief follows the reader's zoom or selection").toBe(0);
    expect(await cyanPixels(page, chosen.png), "the selection mark leaked into the brief").toBe(0);
    // The page's membership filter does not change the brief either: its rows list every member.
    await page.getByLabel("Membership filter").selectOption("gcc");
    await app.mapIdle();
    const filtered = await exportPng();
    expect(filtered.texts).toEqual(plain.texts);
    expect(gridDiff(a, await colourGrid(page, filtered.png, 10, 6)), "the brief follows the page's filter").toBe(0);
    // The caveat bands are drawn, not empty.
    const foot = await pixelStats(page, chosen.png, [0, 820, 1600, 80]);
    expect(foot.distinct, "the footer caveats are not drawn").toBeGreaterThan(3);
    const head = await pixelStats(page, chosen.png, [0, 0, 1600, 96]);
    expect(head.distinct, "the title band is not drawn").toBeGreaterThan(3);
  });
});
