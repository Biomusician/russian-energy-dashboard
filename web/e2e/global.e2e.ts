import { test, expect, pixelStats, readBytes } from "./fixtures";

/**
 * The global home and the five country systems, in a real browser (iteration 14).
 *
 * Values are read from the payload the page itself loaded, never typed in here: the corpora are
 * curated and will grow. What is fixed is the behaviour — and the refusals: no score for a
 * country, no zero where a score would be, no counts on the home page, no ranking.
 */

const COUNTRIES = ["ca", "cn", "in", "sa", "us"] as const;

async function manifest(page: import("@playwright/test").Page) {
  return page.evaluate(async () => (await fetch("/data/global/manifest.json")).json());
}

async function countryPayload(page: import("@playwright/test").Page, id: string, file: string) {
  return page.evaluate(async ([i, f]) => (await fetch(`/data/systems/${i}/${f}`)).json(), [id, file]);
}

test.describe("global home", () => {
  test("a bare URL opens the overview with every system in fixed order and no counts", async ({ app, page }) => {
    await app.open("");
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
    const m = await manifest(page);
    const cards = page.getByRole("article");
    await expect(cards).toHaveCount(m.systems.length);
    const names = await cards.locator("h2").allInnerTexts();
    expect(names).toEqual(m.systems.map((s: { name: string }) => s.name));
    expect(names).toEqual([...names].sort());
    // The comparability statement is on the page, not in a tooltip.
    await expect(page.getByRole("note")).toContainText("not shown to be safer");
    // No event counts anywhere on the home page: a number per card reads as a league table.
    await expect(page.locator("main")).not.toContainText(/qualifying events/i);
    // Only the theatre has a headline; every country says it has none.
    await expect(page.getByRole("article", { name: "Russia, Belarus & Crimea" })).toContainText("Monitored-Area ESDI");
    for (const s of m.systems.filter((x: { kind: string }) => x.kind === "country")) {
      await expect(page.getByRole("article", { name: s.name })).toContainText("No index");
    }
    const px = await app.mapPixels();
    expect(px.distinct).toBeGreaterThan(8);
  });

  test("opening a system from the home page pushes history, and Back returns", async ({ app, page }) => {
    await app.open("");
    await app.button("Open Canada").click();
    await expect(page).toHaveURL(/[?&]sys=ca\b/);
    await expect(page.getByRole("heading", { name: "Canada", level: 1 })).toBeVisible();
    await app.mapIdle();
    await page.goBack();
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
  });

  test("an unknown or hostile system id is refused, not trusted", async ({ app, page }) => {
    for (const q of ["?sys=zz", "?sys=constructor", "?sys=__proto__"]) {
      await page.goto(`/${q}`);
      await expect(page.getByRole("alert")).toContainText("not a monitored country system");
    }
    expect(app.errors).toEqual([]);
  });
});

test.describe("country systems", () => {
  for (const id of COUNTRIES) {
    test(`${id}: opens with no index, a drawn map, every sector stated, and its events`, async ({ app, page }) => {
      await app.open(`?sys=${id}`);
      const sys = await countryPayload(page, id, "system.json");
      const events = (await countryPayload(page, id, "events.json")).events;
      await expect(page.getByRole("heading", { name: sys.name, level: 1 })).toBeVisible();

      // The headline position says "No index" and never shows a number pretending to be one.
      const ribbon = page.getByRole("region", { name: "Headline" });
      // The reason text names the ESDI to explain its absence; what must never appear is a
      // number in the headline slot, or any decimal figure dressed as a score.
      await expect(ribbon.getByLabel("No index")).toHaveText("No index");
      await expect(ribbon).not.toContainText(/\d+\.\d/);
      await expect(ribbon).toContainText(`${events.length} qualifying events recorded`);

      const px = await app.mapPixels();
      expect(px.distinct, "the country map is blank").toBeGreaterThan(8);

      // Every event is listed (country-level ones in their own group).
      await expect(page.locator(".event-item")).toHaveCount(events.length);

      await app.button("Sectors").click();
      await expect(page.locator(".sector-table tbody tr")).toHaveCount(6);
      await app.button("Energy context").click();
      await expect(page.getByRole("heading", { name: "Energy-system context" })).toBeVisible();
      await app.button("Sources & data quality").click();
      await expect(page.getByRole("heading", { name: /sources & data quality/i })).toBeVisible();
      await app.button("Why no score").click();
      await expect(page.locator(".country-side")).toContainText(sys.no_index_reason.slice(0, 40));
    });
  }

  test("a region deep link lists only that region's events", async ({ app, page }) => {
    await app.open("?sys=us");
    const events = (await countryPayload(page, "us", "events.json")).events;
    const counts: Record<string, { n: number; name: string }> = {};
    for (const e of events) {
      if (e.region_code) counts[e.region_code] = { n: (counts[e.region_code]?.n ?? 0) + 1, name: e.region_name };
    }
    const [code, { n, name }] = Object.entries(counts).sort((a, b) => b[1].n - a[1].n)[0];
    await app.open(`?sys=us&r=${code}`);
    await expect(page.getByRole("heading", { name, level: 2 })).toBeVisible();
    await expect(page.locator(".event-item")).toHaveCount(n);
    await app.button("Show all").click();
    await expect(page.locator(".event-item")).toHaveCount(events.length);
    await expect(page).not.toHaveURL(/[?&]r=/);
  });

  test("the system picker moves between all six systems and Back walks the trail", async ({ app, page }) => {
    await app.open("?sys=ca");
    const picker = page.getByRole("combobox", { name: "Monitored system" });
    for (const [id, name] of [["cn", "China"], ["in", "India"], ["sa", "Saudi Arabia"], ["us", "United States"]]) {
      await picker.selectOption(id);
      await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
      await app.mapIdle();
    }
    await picker.selectOption("ru");
    await app.mapIdle();
    await expect(page.getByRole("button", { name: /explain the monitored-area esdi/i })).toBeVisible();
    await expect(page).toHaveURL(/[?&]sys=ru\b/);
    await page.goBack();
    await expect(page.getByRole("heading", { name: "United States", level: 1 })).toBeVisible();
    await page.goBack();
    await expect(page.getByRole("heading", { name: "Saudi Arabia", level: 1 })).toBeVisible();
  });

  test("a slow response for the country just left never paints over the one just opened", async ({ app, page }) => {
    await page.route("**/data/systems/cn/system.json", async (route) => {
      await new Promise((r) => setTimeout(r, 3000));
      await route.continue().catch(() => { /* aborted by the switch: that is the point */ });
    });
    await page.goto("/?sys=cn");
    await page.getByRole("combobox", { name: "Monitored system" }).selectOption("ca");
    await expect(page.getByRole("heading", { name: "Canada", level: 1 })).toBeVisible();
    await page.waitForTimeout(3500);
    await expect(page.getByRole("heading", { name: "Canada", level: 1 })).toBeVisible();
    await expect(page.getByRole("heading", { name: "China", level: 1 })).toHaveCount(0);
    await expect(page).toHaveURL(/[?&]sys=ca\b/);
    expect(app.errors).toEqual([]);
  });

  test("one system's broken payload is contained to that system", async ({ app, page }) => {
    app.allowConsoleError(/status of 500/);
    await page.route("**/data/systems/cn/system.json", (route) => route.fulfill({ status: 500, body: "" }));
    await page.goto("/?sys=cn");
    await expect(page.getByRole("alert")).toContainText("could not be loaded");
    await expect(page.getByRole("alert")).toContainText("Other systems are unaffected");
    await page.getByRole("combobox", { name: "Monitored system" }).selectOption("ca");
    await expect(page.getByRole("heading", { name: "Canada", level: 1 })).toBeVisible();
    await app.mapIdle();
    await page.getByRole("combobox", { name: "Monitored system" }).selectOption("");
    await expect(page.getByRole("article")).toHaveCount(6);
  });
});

test.describe("episodes and source freshness (iteration 15)", () => {
  test("one hurricane is one episode: grouped, counted once, every record still listed", async ({ app, page }) => {
    await app.open("?sys=us");
    const payload = await countryPayload(page, "us", "events.json");
    const sys = await countryPayload(page, "us", "system.json");
    const ribbon = page.getByRole("region", { name: "Headline" });
    await expect(ribbon).toContainText(`in ${sys.event_summary.episodes} episodes`);
    const multi = payload.episodes.filter((ep: { records: number }) => ep.records > 1);
    await expect(page.locator(".episode-group")).toHaveCount(multi.length);
    const helene = page.locator(".episode-group").filter({ hasText: "Hurricane Helene" });
    await expect(helene.locator(".event-item")).toHaveCount(4);
    await expect(helene).toContainText("4 records");
    // Grouping never hides a record.
    await expect(page.locator(".event-item")).toHaveCount(payload.events.length);
  });

  test("a region view keeps records separate and says which episode each belongs to", async ({ app, page }) => {
    await app.open("?sys=us&r=US-NC");
    await expect(page.locator(".event-item").filter({ hasText: "North Carolina" }).first())
      .toContainText("Part of an episode: Hurricane Helene");
  });

  test("every source shows when it was checked, and the search log says where it stopped", async ({ app, page }) => {
    await app.open("?sys=cn");
    await app.button("Sources & data quality").click();
    const sys = await countryPayload(page, "cn", "system.json");
    await expect(page.locator(".source-table tbody tr")).toHaveCount(sys.sources.length);
    await expect(page.locator(".source-table")).toContainText("Publishes:");
    await expect(page.locator(".research-log tbody tr")).toHaveCount(sys.research_log.passes.length);
    await expect(page.locator(".research-log")).toContainText("partial");
  });

  test("a source past its limit is flagged on the reader's clock, not the build's", async ({ app, page }) => {
    await page.route("**/data/systems/ca/system.json", async (route) => {
      const res = await route.fetch();
      const body = await res.json();
      body.sources[0].checked = "2020-01-01";
      await route.fulfill({ response: res, json: body });
    });
    await app.open("?sys=ca");
    await app.button("Sources & data quality").click();
    await expect(page.locator(".source-table .stale-flag")).toHaveCount(1);
  });
});

test.describe("theatre links", () => {
  test("the theatre's own URL now names it, so its default view survives a reload", async ({ app, page }) => {
    await app.open("?m=ev");
    await expect(page).toHaveURL(/[?&]sys=ru\b/);
    await expect(page).toHaveURL(/[?&]m=ev\b/);
    await page.reload();
    await app.mapIdle();
    await expect(page.getByRole("button", { name: /explain the monitored-area esdi/i })).toBeVisible();
  });

  test("the theatre offers the system picker and can leave for a country", async ({ app, page }) => {
    await app.open();
    await page.getByRole("combobox", { name: "Monitored system" }).selectOption("in");
    await expect(page.getByRole("heading", { name: "India", level: 1 })).toBeVisible();
  });
});

test.describe("country export and print", () => {
  for (const id of COUNTRIES) {
    test(`${id}: the PNG is a real 1600x900 image with a drawn map and its framing`, async ({ app, page }) => {
      await app.open(`?sys=${id}`);
      const [download] = await Promise.all([
        page.waitForEvent("download"),
        app.button("Download PNG").click(),
      ]);
      expect(download.suggestedFilename()).toMatch(new RegExp(`^energy-disruption-${id}-\\d{4}-\\d{2}-\\d{2}\\.png$`));
      const png = readBytes((await download.path())!);
      expect(png.subarray(1, 4).toString("ascii")).toBe("PNG");
      const whole = await pixelStats(page, png);
      expect([whole.width, whole.height]).toEqual([1600, 900]);
      expect(whole.distinct).toBeGreaterThan(20);
      const band = await pixelStats(page, png, [320, 270, 960, 360]);
      expect(band.distinct, "the map area of the export is blank").toBeGreaterThan(4);
    });
  }

  for (const q of ["", "?sys=ru", ...COUNTRIES.map((c) => `?sys=${c}`)]) {
    test(`print/PDF renders for ${q || "the home page"}`, async ({ app, page }) => {
      await app.open(q);
      await page.emulateMedia({ media: "print" });
      const pdf = await page.pdf({ format: "A4", printBackground: true });
      expect(pdf.subarray(0, 4).toString("ascii")).toBe("%PDF");
      expect(pdf.length).toBeGreaterThan(15_000);
    });
  }
});

test.describe("responsive", () => {
  for (const [w, h] of [[1024, 768], [430, 932]] as const) {
    for (const q of ["", "?sys=us", "?sys=cn"]) {
      test(`${q || "home"} at ${w}x${h} does not scroll sideways`, async ({ app, page }) => {
        await page.setViewportSize({ width: w, height: h });
        await app.open(q);
        const overflow = await page.evaluate(() =>
          Math.max(document.documentElement.scrollWidth - window.innerWidth,
                   ...[...document.querySelectorAll(".global-page")].map((e) => e.scrollWidth - e.clientWidth)));
        expect(overflow, "horizontal scroll").toBeLessThanOrEqual(1);
        const box = await page.locator("[data-map-state]").boundingBox();
        expect(box!.width).toBeGreaterThan(w * 0.5);
        expect(box!.height).toBeGreaterThan(200);
        await expect(page.getByRole("combobox", { name: "Monitored system" })).toBeVisible();
      });
    }
  }
});

test.describe("screenshot goldens", () => {
  // Recorded on the development machine's software renderer. Linux CI renders fonts and
  // anti-aliasing differently, so the goldens are compared only where they were made; the
  // pixel-statistics tests above are the cross-platform guard.
  test.skip(process.platform !== "win32", "goldens are recorded on win32");
  for (const q of ["", "?sys=us", "?sys=sa"]) {
    test(`map golden: ${q || "home"}`, async ({ app, page }) => {
      await app.open(q);
      await expect(page.locator("[data-map-state]")).toHaveScreenshot(
        `map-${q ? q.slice(5) : "home"}.png`, { maxDiffPixelRatio: 0.002 });
    });
  }
});
