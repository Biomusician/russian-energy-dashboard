import { test, expect, pixelStats, readBytes } from "./fixtures";

/**
 * The Gulf regional view and its eight country systems, in a real browser (iteration 19).
 *
 * THE GULF IS A REGIONAL ENERGY PICTURE, NOT A TARGET SET. Every value asserted here is read from
 * the payload the page itself loaded. What is fixed is the behaviour and the refusals: a group is
 * a list of countries with national context, never a ranking; a country with no reviewed record
 * says so in words and never shows a zero; an attack recorded under a country-level rule carries
 * no place below the country; and one broken file never takes a neighbour down with it.
 *
 * The ids below only generate one test per system. The first test fails if they drift from the
 * manifest, which is what the application itself reads.
 */

const GULF = ["ae", "bh", "iq", "ir", "kw", "om", "qa", "sa"] as const;
const NEW = GULF.filter((id) => id !== "sa");
const MOBILE = [[1024, 768], [430, 932], [390, 844]] as const;

type Page = import("@playwright/test").Page;
type GulfSystem = { system_id: string; name: string; a3: string; gcc_member: boolean; opec_member: boolean;
                    maturity: string; recovery_status_withheld: boolean; values: Record<string, number | null>;
                    attack_records_placed: "country" | "admin1" };
type Event = { event_id: string; cause: string; region_code: string | null; region_name: string | null;
               facility_name: string | null; geography_precision: string; summary: string; effect: string | null;
               regions_affected: string[]; sources: { url: string; title_original?: string; language?: string }[] };

const json = (page: Page, path: string) => page.evaluate((p) => fetch(p).then((r) => r.json()), path);
const manifest = (page: Page) => json(page, "/data/global/manifest.json");
const gulf = (page: Page) => json(page, "/data/global/gulf.json");
const payload = (page: Page, id: string, file: string) => json(page, `/data/systems/${id}/${file}`);

// Wording a regional picture must never carry, whatever the data says.
// The page's own refusals ("never a ranking") are allowed; a positive ranking statement is not.
const RANKING = /\b(ranked (first|second|third|\d)|top \d|#\d|most (important|vulnerable|critical|exposed)|worst[- ]hit|hardest[- ]hit|league table of)\b/i;
const ROUTES = /hormuz|tanker|choke ?point|shipping lane|bypass/i;

async function sideways(page: Page) {
  return page.evaluate(() =>
    Math.max(document.documentElement.scrollWidth - window.innerWidth,
             ...[...document.querySelectorAll(".global-page")].map((e) => e.scrollWidth - e.clientWidth)));
}

test.describe("Gulf group", () => {
  test("the manifest's Gulf group is exactly the eight systems, and the GCC is not the Gulf", async ({ app, page }) => {
    await app.open("");
    const m = await manifest(page);
    expect([...m.groups.gulf_littoral.members].sort()).toEqual([...GULF].sort());
    expect(m.groups.gcc.members).not.toContain("ir");
    expect(m.groups.gcc.members).not.toContain("iq");
    expect(m.groups.gcc.members).toHaveLength(6);
  });

  test("the home page filters by group and opens the Gulf overview, and Back returns", async ({ app, page }) => {
    await app.open("");
    const m = await manifest(page);
    const name = (id: string) => m.systems.find((s: { id: string }) => s.id === id).name;
    const filter = page.getByLabel("Filter the system cards by group");
    const cards = page.getByRole("region", { name: "Monitored systems" }).getByRole("article");
    await expect(cards).toHaveCount(m.systems.length);

    await filter.selectOption("gulf_littoral");
    await expect(cards).toHaveCount(8);
    const shown = await cards.locator("h2").allInnerTexts();
    expect(shown).toEqual([...shown].sort());
    expect(shown).toEqual(m.groups.gulf_littoral.members.map(name));

    await filter.selectOption("gcc");
    await expect(cards).toHaveCount(6);
    await expect(page.getByRole("article", { name: "Iran" })).toHaveCount(0);
    await expect(page.getByRole("article", { name: "Iraq" })).toHaveCount(0);
    await expect(page.locator(".map-control-row").filter({ has: filter })).toContainText("Iran and Iraq are not members");

    await app.button("Open the Gulf littoral overview").click();
    await expect(page).toHaveURL(/[?&]group=gulf\b/);
    await expect(page.getByRole("heading", { name: "Gulf littoral overview", level: 1 })).toBeVisible();
    await page.goBack();
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
  });

  test("the overview lists all eight alphabetically with national context, its year and its source", async ({ app, page }) => {
    await app.open("?group=gulf");
    const g = await gulf(page);
    const systems = g.systems as GulfSystem[];
    expect(systems).toHaveLength(8);
    await expect(page.getByRole("heading", { name: "Gulf littoral overview", level: 1 })).toBeVisible();
    await expect(page.getByRole("note")).toContainText("not shown to be safer");

    const cards = page.getByRole("region", { name: "Monitored systems in this view" }).getByRole("article");
    await expect(cards).toHaveCount(8);
    const names = await cards.locator("h2").allInnerTexts();
    expect(names).toEqual(systems.map((s) => s.name));
    expect(names).toEqual([...names].sort());
    for (const s of systems) {
      const card = page.getByRole("article", { name: s.name });
      await expect(card).toContainText("No index");
      await expect(card).toContainText(s.gcc_member ? "GCC member" : "Not a GCC member");
      await expect(card).toContainText(s.opec_member ? "OPEC member" : "Not an OPEC member");
      // The campaign badge wherever the build withholds recovery status, and only there.
      await expect(card.getByText("Later status of attacked facilities is not published")).toHaveCount(s.recovery_status_withheld ? 1 : 0);
      // Why two neighbours' attack records look different is said on the card, not left to guess.
      await expect(card).toContainText(s.attack_records_placed === "country"
        ? "Attacks are recorded for the country as a whole" : "Attacks are recorded by first-level region");
      // A card carries no event count: eight numbers side by side are a league table.
      await expect(card).not.toContainText(/\d+\s+(qualifying|reported|recorded)/i);
    }

    // The table: one row per country in the same order, a year in every metric header.
    const rows = page.locator(".group-table tbody tr");
    const firstCells = await rows.locator("td:first-child").allInnerTexts();
    expect(firstCells.slice(0, 8)).toEqual(systems.map((s) => s.name));
    for (const [, x] of Object.entries(g.metrics) as [string, { label: string; unit: string; year: number }][]) {
      await expect(page.locator(".group-table thead")).toContainText(`${x.label} (${x.unit}, ${x.year})`);
    }
    // A missing national value is words, never a zero.
    for (const s of systems) {
      const row = rows.filter({ has: page.getByRole("button", { name: s.name, exact: true }) });
      for (const v of Object.values(s.values)) if (v == null) await expect(row).toContainText("no data");
    }
    for (const src of Object.values(g.sources) as { name: string }[]) {
      await expect(page.getByRole("region", { name: "Regional energy context" })).toContainText(src.name);
    }
  });

  test("the map is drawn, every metric redraws with its unit and year, and nothing but countries is on it", async ({ app, page }) => {
    await app.open("?group=gulf");
    const g = await gulf(page);
    const px = await app.mapPixels();
    expect(px.distinct, "the Gulf map is blank").toBeGreaterThan(8);
    const legend = page.getByLabel("Map legend");
    for (const [id, x] of Object.entries(g.metrics) as [string, { label: string; unit: string; year: number }][]) {
      await page.getByLabel("Regional map metric").selectOption(id);
      await app.mapIdle();
      await expect(legend).toContainText(`${x.label} — ${x.year}`);
      await expect(legend).toContainText(x.unit);
    }
    await expect(legend).toContainText("a larger figure is not a more important country");
    // No facility, route or incident layer: no markers, and the attribution says what is drawn.
    await expect(page.locator(".maplibregl-marker")).toHaveCount(0);
    await expect(page.locator(".global-map-wrap")).toContainText("no facilities, routes or incident points");
  });

  test("the GCC and OPEC filters are memberships, and the regional total never becomes a ranking", async ({ app, page }) => {
    await app.open("?group=gulf");
    const g = await gulf(page);
    const systems = g.systems as GulfSystem[];
    const cards = page.getByRole("region", { name: "Monitored systems in this view" }).getByRole("article");
    await page.getByLabel("Membership filter").selectOption("gcc");
    await expect(cards).toHaveCount(systems.filter((s) => s.gcc_member).length);
    await expect(page.getByRole("article", { name: "Iran" })).toHaveCount(0);
    await expect(page.getByRole("article", { name: "Iraq" })).toHaveCount(0);
    await page.getByLabel("Membership filter").selectOption("opec");
    await expect(cards).toHaveCount(systems.filter((s) => s.opec_member).length);
    await page.getByLabel("Membership filter").selectOption("all");
    await expect(cards).toHaveCount(8);

    // The view's one statement of what it leaves out names those things; nothing else may.
    // The definitions sit in a disclosure (iteration 20, §62): opened, they are all there.
    await page.locator(".group-howto summary").click();
    const main = (await page.locator("main").innerText()).replace(g.not_built, "");
    expect(main).not.toMatch(RANKING);
    expect(main).not.toMatch(ROUTES);
    expect(main).toContain("Gulf littoral, GCC and OPEC are three different things");
    await expect(page.locator(".group-kinds li")).toHaveCount(3);
  });

  test("regional events are in date order only, and an attack under a country rule names no place", async ({ app, page }) => {
    await app.open("?group=gulf");
    const g = await gulf(page);
    const feed = page.getByRole("region", { name: "Recent reviewed events in this region" });
    await expect(feed).toContainText("Date order only");
    await expect(feed).toContainText("not a deteriorating region");
    const eps = g.recent.episodes as { system_id: string; last_date: string; members: { region: string; withheld: boolean }[] }[];
    if (eps.length === 0) {
      await expect(feed).toContainText("No qualifying records in the current reviewed corpus for this region");
      return;
    }
    await expect(feed.locator(".feed-item")).toHaveCount(eps.length);
    const dates = eps.map((e) => e.last_date);
    expect(dates).toEqual([...dates].sort().reverse());
    expect(g.recent.scope).not.toMatch(/five/);
    expect(await feed.innerText()).not.toMatch(ROUTES);
  });

  test("the map opens uncoloured, and a brief needs a chosen figure", async ({ app, page }) => {
    // Iteration 20 (§38): the default map is geography only, so it cannot be read as a ranking.
    await app.open("?group=gulf");
    await expect(page.getByLabel("Regional map metric")).toHaveValue("none");
    await expect(page.locator(".map-legend-mini")).toContainText("Geography only");
    await expect(page.locator(".map-legend-mini")).not.toContainText("larger, within this group");
    await app.button("Download brief (PNG)").click();
    await expect(page.getByText(/Choose a metric under "Colour the map by" first/)).toBeVisible();
  });

  test("the regional brief downloads as a real image carrying its framing", async ({ app, page }) => {
    await app.open("?group=gulf");
    await page.getByLabel("Regional map metric").selectOption({ index: 1 });
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      app.button("Download brief (PNG)").click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/^gulf-energy-context-[a-z_]+-\d{4}\.png$/);
    const png = readBytes((await download.path())!);
    expect(png.subarray(1, 4).toString("ascii")).toBe("PNG");
    const whole = await pixelStats(page, png);
    expect([whole.width, whole.height]).toEqual([1600, 900]);
    expect(whole.distinct).toBeGreaterThan(20);
    const band = await pixelStats(page, png, [320, 270, 960, 360]);
    expect(band.distinct, "the map area of the brief is blank").toBeGreaterThan(4);
  });

  test("an unknown group is refused, and the picker reaches the overview from a country", async ({ app, page }) => {
    await page.goto("/?group=constructor");
    await expect(page.getByRole("alert")).toContainText("no regional view called");
    await app.open("?sys=qa");
    await page.getByRole("combobox", { name: "Monitored system" }).selectOption("group:gulf");
    await expect(page.getByRole("heading", { name: "Gulf littoral overview", level: 1 })).toBeVisible();
    await expect(page).toHaveURL(/[?&]group=gulf\b/);
    expect(app.errors).toEqual([]);
  });

  test("the overview is usable from the keyboard alone", async ({ app, page }) => {
    await app.open("?group=gulf");
    const g = await gulf(page);
    const first = (g.systems as GulfSystem[])[0];
    const link = page.locator(".group-table").getByRole("button", { name: first.name, exact: true });
    await link.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: first.name, level: 1 })).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`[?&]sys=${first.system_id}\\b`));
  });
});

test.describe("Gulf country systems", () => {
  for (const id of GULF) {
    test(`${id}: opens with no index, a drawn map, an honest record line and every tab`, async ({ app, page }) => {
      await app.open(`?sys=${id}`);
      const sys = await payload(page, id, "system.json");
      const events = (await payload(page, id, "events.json")).events as Event[];
      await expect(page.getByRole("heading", { name: sys.name, level: 1 })).toBeVisible();

      const ribbon = page.getByRole("region", { name: "Headline" });
      await expect(ribbon.getByLabel("No index")).toHaveText("No index");
      await expect(ribbon).not.toContainText(/\d+\.\d/);
      if (events.length === 0) {
        // Never "0 disruptions": an empty reviewed corpus is a statement about the dataset.
        await expect(ribbon).toContainText("No qualifying records in the current reviewed corpus");
        await expect(ribbon).toContainText("it does not mean nothing happened");
        await expect(ribbon).not.toContainText(/\b0 (qualifying|events|disruptions)/i);
      } else {
        await expect(ribbon).toContainText(`${events.length} qualifying events recorded`);
      }

      // A country whose candidates were all held must not read like one nobody looked at.
      const passes = (sys.research_log.passes as { kind: string; outcome?: Record<string, number> }[]).filter((p) => p.kind === "systematic");
      const outcome = passes[passes.length - 1]?.outcome;
      if (outcome?.candidates) {
        await expect(ribbon).toContainText(`looked at ${outcome.candidates} candidate records`);
        if (outcome.held > 0) await expect(ribbon).toContainText(`${outcome.held} of them are not shown`);
      }

      // Tiny states need usable bounds: the map shows the country, not empty sea.
      const px = await app.mapPixels();
      expect(px.distinct, "the country map is blank").toBeGreaterThan(8);
      await expect(page.locator(".event-item")).toHaveCount(events.length);

      if (sys.campaign_state && sys.campaign_state.state !== "NO_ACTIVE_CAMPAIGN") {
        const notices = page.getByRole("region", { name: "How to read this country" });
        await expect(notices).toContainText("Whether a facility has been repaired, restarted or is operating is not published");
      }
      if (sys.maturity === "research_preview") {
        await expect(page.getByRole("region", { name: "How to read this country" })).toContainText("Research preview");
      }

      await app.button("Sectors").click();
      await expect(page.locator(".sector-table tbody tr")).toHaveCount(sys.sectors.length);
      await app.button("Energy context").click();
      await expect(page.getByRole("heading", { name: "Energy-system context" })).toBeVisible();
      await app.button("Research coverage").click();
      await expect(page.getByRole("heading", { name: "Research coverage" })).toBeVisible();
      await app.button("Sources & data quality").click();
      await expect(page.getByRole("heading", { name: /sources & data quality/i })).toBeVisible();
      await app.button("Why no score").click();
      await expect(page.locator(".country-side")).toContainText(sys.no_index_reason.slice(0, 40));
      expect(app.errors).toEqual([]);
    });
  }

  test("non-English sources keep their own script and direction", async ({ app, page }) => {
    let checked = 0;
    for (const id of GULF) {
      await app.open(`?sys=${id}`);
      const events = (await payload(page, id, "events.json")).events as Event[];
      const withTitle = events.flatMap((e) => e.sources).filter((s) => s.title_original && ["ar", "fa", "ku"].includes(s.language ?? ""));
      if (withTitle.length === 0) continue;
      const bdi = page.locator(".source-title bdi").first();
      await expect(bdi).toHaveAttribute("dir", "rtl");
      await expect(bdi).toHaveAttribute("lang", /^(ar|fa|ku)$/);
      checked += 1;
    }
    test.info().annotations.push({ type: "systems with original-language titles", description: String(checked) });
  });

  test("switching rapidly through all eight leaves each page showing only its own country", async ({ app, page }) => {
    await app.open("?sys=ae");
    const m = await manifest(page);
    const picker = page.getByRole("combobox", { name: "Monitored system" });
    // Forward and back again, without waiting for the map between hops: a slow response for the
    // country just left must never paint over the one just opened.
    const order = [...GULF, ...[...GULF].reverse()];
    for (const id of order) await picker.selectOption(id);
    const last = order[order.length - 1];
    const name = m.systems.find((s: { id: string }) => s.id === last).name;
    await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
    await app.mapIdle();

    for (const id of ["ir", "bh", "iq", "qa", "sa", "om", "kw", "ae"]) {
      await picker.selectOption(id);
      const sys = await payload(page, id, "system.json");
      const events = (await payload(page, id, "events.json")).events as Event[];
      await expect(page.getByRole("heading", { name: sys.name, level: 1 })).toBeVisible();
      await app.mapIdle();
      await expect(page).toHaveURL(new RegExp(`[?&]sys=${id}\\b`));
      await expect(page.locator(".event-item")).toHaveCount(events.length);
      await expect(page).toHaveTitle(new RegExp(sys.name));
      // Bounds: the drawn map belongs to this country, i.e. it is not blank after the switch.
      const px = await app.mapPixels();
      expect(px.distinct, `${id}: blank map after switching`).toBeGreaterThan(8);
      // Source health belongs to this country: its citations are counted across its own events.
      await app.button("Sources & data quality").click();
      await expect(page.getByRole("heading", { name: /sources & data quality/i })).toBeVisible();
      if (events.length > 0) {
        await expect(page.locator(".country-side")).toContainText(new RegExp(`across ${events.length} events?\\b`));
      }
      await app.button("Reported events").click();
    }
    expect(app.errors).toEqual([]);
  });
});

test.describe("Gulf error containment", () => {
  test("a corrupt Iran payload is contained: the overview and the other countries still work", async ({ app, page }) => {
    app.allowConsoleError(/status of 500|Unexpected token|JSON/);
    await page.route("**/data/systems/ir/system.json", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{ not json" }));
    await page.goto("/?sys=ir");
    await expect(page.getByRole("alert")).toContainText("could not be loaded");
    await expect(page.getByRole("alert")).toContainText("Other systems are unaffected");
    const picker = page.getByRole("combobox", { name: "Monitored system" });
    await picker.selectOption("iq");
    await expect(page.getByRole("heading", { name: "Iraq", level: 1 })).toBeVisible();
    await app.mapIdle();
    await picker.selectOption("group:gulf");
    await expect(page.getByRole("heading", { name: "Gulf littoral overview", level: 1 })).toBeVisible();
    await expect(page.getByRole("region", { name: "Monitored systems in this view" }).getByRole("article")).toHaveCount(8);
  });

  test("a corrupt source-health block is contained: that country is refused and the others still work", async ({ app, page }) => {
    // Iteration 20 (§122). Before the load-time check this crashed the page during render.
    app.allowConsoleError(/malformed payload|source_health/);
    await page.route("**/data/systems/iq/system.json", async (route) => {
      const response = await route.fetch();
      const d = await response.json();
      d.source_health = "corrupt";
      await route.fulfill({ response, json: d });
    });
    await page.goto("/?sys=iq");
    await expect(page.getByRole("alert")).toContainText("could not be loaded");
    const picker = page.getByRole("combobox", { name: "Monitored system" });
    await picker.selectOption("kw");
    await expect(page.getByRole("heading", { name: "Kuwait", level: 1 })).toBeVisible();
    await app.mapIdle();
    await picker.selectOption("group:gulf");
    await expect(page.getByRole("heading", { name: "Gulf littoral overview", level: 1 })).toBeVisible();
  });

  test("a corrupt Gulf context is contained: the view says so and every country still opens", async ({ app, page }) => {
    app.allowConsoleError(/status of 500|Unexpected token|JSON/);
    await page.route("**/data/global/gulf.json", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "<html>" }));
    await page.goto("/?group=gulf");
    await expect(page.getByRole("alert")).toContainText("The regional context could not be loaded");
    await expect(page.getByRole("alert")).toContainText("Each country's own page still works");
    // No figure is invented for the missing file.
    await expect(page.locator(".group-table")).toHaveCount(0);
    const picker = page.getByRole("combobox", { name: "Monitored system" });
    for (const [id, name] of [["om", "Oman"], ["ir", "Iran"]]) {
      await picker.selectOption(id);
      await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
      await app.mapIdle();
    }
    await picker.selectOption("");
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
    await app.mapIdle();
  });

  test("a missing events file for one Gulf country leaves its neighbours' records intact", async ({ app, page }) => {
    app.allowConsoleError(/status of 404|404/);
    await page.route("**/data/systems/kw/events.json", (route) => route.fulfill({ status: 404, body: "" }));
    await page.goto("/?sys=kw");
    await expect(page.getByRole("alert").first()).toBeVisible();
    await page.getByRole("combobox", { name: "Monitored system" }).selectOption("sa");
    await expect(page.getByRole("heading", { name: "Saudi Arabia", level: 1 })).toBeVisible();
    const events = (await payload(page, "sa", "events.json")).events as Event[];
    await expect(page.locator(".event-item")).toHaveCount(events.length);
  });
});

test.describe("Gulf exports", () => {
  for (const id of ["ir", "iq", "qa", "ae", "om", "sa"]) {
    test(`${id}: the country PNG is a real image with a drawn map`, async ({ app, page }) => {
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

  for (const q of ["?group=gulf", ...NEW.map((c) => `?sys=${c}`)]) {
    test(`print/PDF renders for ${q}`, async ({ app, page }) => {
      await app.open(q);
      await page.emulateMedia({ media: "print" });
      const pdf = await page.pdf({ format: "A4", printBackground: true });
      expect(pdf.subarray(0, 4).toString("ascii")).toBe("%PDF");
      expect(pdf.length).toBeGreaterThan(15_000);
    });
  }
});

test.describe("Gulf responsive", () => {
  for (const [w, h] of MOBILE) {
    for (const q of ["?group=gulf", ...NEW.map((c) => `?sys=${c}`)]) {
      test(`${q} at ${w}x${h} does not scroll sideways and keeps its map and picker`, async ({ app, page }) => {
        await page.setViewportSize({ width: w, height: h });
        await app.open(q);
        expect(await sideways(page), "horizontal scroll").toBeLessThanOrEqual(1);
        const box = await page.locator("[data-map-state]").boundingBox();
        expect(box!.width).toBeGreaterThan(w * 0.5);
        expect(box!.height).toBeGreaterThan(200);
        await expect(page.getByRole("combobox", { name: "Monitored system" })).toBeVisible();
        if (w <= 600) {
          // Iteration 20 (§78): on a phone the map starts in the first screen, a compact caveat line
          // above it leads to the full statements, and the comparability statement is still on the page.
          const top = await page.locator("[data-map-state]").evaluate((el) => el.getBoundingClientRect().top + window.scrollY);
          expect(top, "the map starts below the first screen").toBeLessThan(h - 150);
          await expect(page.locator(".phone-only").first()).toBeVisible();
          await expect(page.locator(".comparability")).toHaveCount(1);
        } else {
          await expect(page.locator(".phone-only").first()).toBeHidden();
        }
      });
    }
  }
});

test.describe("Iteration 20 page rules", () => {
  test("a research preview is defined once, in words a reader can act on", async ({ app, page }) => {
    await app.open("?sys=bh");
    const notices = page.getByRole("region", { name: "How to read this country" });
    await expect(notices).toContainText("the absence of a record is not evidence that no disruption occurred");
  });

  test("a page with no record says what that means and never prints a zero", async ({ app, page }) => {
    await app.open("?sys=bh");
    const ribbon = page.getByRole("region", { name: "Headline" });
    await expect(ribbon).toContainText("No qualifying records in the current reviewed corpus.");
    await expect(ribbon).toContainText("it does not mean nothing happened");
    await expect(ribbon).not.toContainText(/\b0 (disruptions|events|records)\b/);
  });

  test("Saudi Arabia's older convention is stated plainly, and only where it applies", async ({ app, page }) => {
    await app.open("?sys=sa");
    // Iteration 21: said in plain terms, with no internal process language.
    await expect(page.locator(".legacy-convention")).toContainText("older records keep an earlier convention");
    await expect(page.locator(".legacy-convention")).toContainText("record an attack for the country as a whole");
    await expect(page.locator(".legacy-convention")).not.toContainText(/decision|owner|iteration|onboard/i);
    for (const id of ["kw", "bh", "us"]) {
      await app.open(`?sys=${id}`);
      await expect(page.locator(".legacy-convention")).toHaveCount(0);
    }
  });

  test("a campaign page says candidates remain under review, never how many", async ({ app, page }) => {
    await app.open("?sys=iq");
    const sys = await payload(page, "iq", "system.json");
    for (const p of sys.research_log.passes as { outcome: Record<string, number>; under_review?: boolean }[]) {
      expect(Object.keys(p.outcome).filter((k) => k !== "records")).toEqual([]);
      expect(typeof p.under_review).toBe("boolean");
    }
  });
});

test.describe("Gulf payloads load lazily", () => {
  test("the home page fetches no country payload and no Gulf context", async ({ app, page }) => {
    const seen: string[] = [];
    page.on("request", (r) => { if (r.url().includes("/data/")) seen.push(new URL(r.url()).pathname); });
    await app.open("");
    expect(seen.filter((p) => p.startsWith("/data/systems/"))).toEqual([]);
    expect(seen).not.toContain("/data/global/gulf.json");
  });

  test("the Gulf overview fetches its context and no country's events", async ({ app, page }) => {
    const seen: string[] = [];
    page.on("request", (r) => { if (r.url().includes("/data/")) seen.push(new URL(r.url()).pathname); });
    await app.open("?group=gulf");
    expect(seen).toContain("/data/global/gulf.json");
    expect(seen.filter((p) => p.startsWith("/data/systems/"))).toEqual([]);
  });

  test("a country page fetches its own directory and nobody else's", async ({ app, page }) => {
    const seen: string[] = [];
    page.on("request", (r) => { if (r.url().includes("/data/systems/")) seen.push(new URL(r.url()).pathname); });
    await app.open("?sys=qa");
    expect(seen.length).toBeGreaterThan(0);
    expect(seen.every((p) => p.startsWith("/data/systems/qa/"))).toBe(true);
  });
});

const KINETIC = ["kinetic_strike", "sabotage"];
const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
type Drawn = { text: string; right: number; width: number };

test.describe("Gulf red team", () => {
  test("attack records under a country rule are found by their real cause and render with no place, headline or status", async ({ app, page }) => {
    // Iteration 20's strict reading held every published country-level attack record. While none is
    // served, Kuwait's payload gains one in the browser only (a rendering fixture, not a record), so
    // the rendering rule is still exercised; a served record replaces the fixture automatically.
    await page.route("**/data/systems/kw/events.json", async (route) => {
      const response = await route.fetch();
      const d = await response.json();
      if (!d.events.some((e: Event) => KINETIC.includes(e.cause))) {
        const base = d.events[0];
        d.events.push({ ...base, event_id: "kw-2026-03-01-refinery-attack-zz", cause: "kinetic_strike",
                        asset_class: "refinery", geography_precision: "country", region_code: null, region_name: null,
                        regions_affected: [], facility_name: null, facility_name_local: null, operator: null,
                        episode_id: "kw-2026-03-01-refinery-attack-zz",
                        summary: "An attack on energy infrastructure was reported (rendering fixture).",
                        sources: base.sources.map((s: Record<string, unknown>) => ({ ...s, title_original: undefined, title_en: undefined })) });
        d.episodes.push({ ...d.episodes[0], episode_id: "kw-2026-03-01-refinery-attack-zz", event_ids: ["kw-2026-03-01-refinery-attack-zz"],
                          records: 1, name: "Kuwait", first_date: base.date, last_date: base.date });
      }
      await route.fulfill({ response, json: d });
    });
    // A served taxonomy labels only the causes its records use; the fixture's label is borrowed
    // from Saudi Arabia's served taxonomy, so it is still never typed here.
    await page.route("**/data/systems/kw/system.json", async (route) => {
      const response = await route.fetch();
      const d = await response.json();
      const sa = await (await route.fetch({ url: route.request().url().replace("/kw/", "/sa/") })).json();
      for (const c of KINETIC) if (!d.taxonomy.causes[c] && sa.taxonomy.causes[c]) d.taxonomy.causes[c] = sa.taxonomy.causes[c];
      await route.fulfill({ response, json: d });
    });
    let checked = 0;
    for (const id of GULF) {
      await app.open(`?sys=${id}`);
      const sys = await payload(page, id, "system.json");
      if (sys.geography.precision_policy?.kinetic !== "country") continue;
      const events = (await payload(page, id, "events.json")).events as (Event & { publication: unknown })[];
      const attacks = events.filter((e) => KINETIC.includes(e.cause));
      if (attacks.length === 0) continue;
      for (const e of attacks) {
        expect(e.region_code, `${e.event_id} carries a region`).toBeNull();
        expect(e.region_name, `${e.event_id} carries a region name`).toBeNull();
        expect(e.facility_name, `${e.event_id} carries a facility`).toBeNull();
        expect(e.regions_affected).toEqual([]);
        expect(e.geography_precision).toBe("country");
        expect(e.event_id).toMatch(new RegExp(`^${id}-\\d{4}-\\d{2}(-\\d{2})?-[a-z-]+-attack-[0-9a-z]{1,6}$`));
        expect(e.sources.filter((s) => s.title_original)).toEqual([]);
      }
      // The cause label comes from the payload's own taxonomy, never typed here.
      const labels = KINETIC.map((c) => sys.taxonomy.causes[c]).filter(Boolean) as string[];
      expect(labels.length, `${id}: the taxonomy labels no attack cause`).toBeGreaterThan(0);
      const items = page.locator(".event-item").filter({
        has: page.locator(".event-head", { hasText: new RegExp(labels.map(escapeRe).join("|")) }),
      });
      await expect(items).toHaveCount(attacks.length);
      await expect(items.locator(".withheld-note")).toHaveCount(attacks.filter((e) => e.publication).length);
      for (let i = 0; i < attacks.length; i++) {
        const item = items.nth(i);
        await expect(item.locator(".event-title")).toHaveText(sys.name);
        await expect(item.locator(".source-title")).toHaveCount(0);
        await expect(item).not.toContainText("Regions affected");
        expect(await item.innerText()).not.toMatch(
          /\b(restarted|resumed|back online|repairs? (completed|under way)|fully restored|drones?|missiles?|rockets?)\b/i);
        checked += 1;
      }
    }
    expect(checked, "no attack record was rendered and checked: this test proved nothing").toBeGreaterThan(0);
  });

  test("a missing national value is words, the total is refused with its reason, and no share is printed", async ({ app, page }) => {
    // No Gulf value is null today, so this path never runs on real data. One value is removed in
    // the browser only; the file on disk is untouched.
    await page.route("**/data/global/gulf.json", async (route) => {
      const response = await route.fetch();
      const g = await response.json();
      const metric = Object.keys(g.metrics)[0];
      g.systems[0].values[metric] = null;
      g.region[metric] = { value: null, world_share: null, reason: `1 of ${g.systems.length} members have no value` };
      await route.fulfill({ response, json: g });
    });
    await app.open("?group=gulf");
    const g = await gulf(page);
    const first = (g.systems as GulfSystem[])[0];
    const context = page.getByRole("region", { name: "Regional energy context" });
    const row = page.locator(".group-table tbody tr").filter({ has: page.getByRole("button", { name: first.name, exact: true }) });
    await expect(row.locator("td").nth(3)).toHaveText("no data");
    await expect(page.locator(".group-table tfoot td").nth(1)).toHaveText(`not summed: 1 of ${g.systems.length} members have no value`);
    await expect(page.locator(".group-table tfoot td").nth(1)).not.toContainText("% of world");
    await expect(context).not.toContainText("A descriptive annual figure");
    await expect(row.locator("td").nth(3)).not.toHaveText(/^0\b/);
  });

  test("the regional brief draws the payload's own figures, order and refusals into the image", async ({ app, page }) => {
    // A PNG cannot be read back as text, so every string drawn into a 2D canvas is recorded.
    await page.addInitScript(() => {
      const drawn: { text: string; right: number; width: number }[] = [];
      (window as unknown as { __drawn: typeof drawn }).__drawn = drawn;
      const original = CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText = function (this: CanvasRenderingContext2D, text: string, x: number, y: number, maxWidth?: number) {
        drawn.push({ text: String(text), right: x + this.measureText(String(text)).width, width: this.canvas.width });
        return maxWidth === undefined ? original.call(this, text, x, y) : original.call(this, text, x, y, maxWidth);
      };
    });
    await app.open("?group=gulf");
    const g = await gulf(page);
    const systems = g.systems as GulfSystem[];
    for (const [id, m] of Object.entries(g.metrics) as [string, { label: string; unit: string; year: number; source_id: string }][]) {
      await page.getByLabel("Regional map metric").selectOption(id);
      await app.mapIdle();
      await page.evaluate(() => { (window as unknown as { __drawn: unknown[] }).__drawn.length = 0; });
      const [download] = await Promise.all([page.waitForEvent("download"), app.button("Download brief (PNG)").click()]);
      expect(download.suggestedFilename()).toBe(`gulf-energy-context-${id}-${m.year}.png`);
      const drawn = (await page.evaluate(() => (window as unknown as { __drawn: Drawn[] }).__drawn.slice())).filter((d) => d.width === 1600);
      const texts = drawn.map((d) => d.text);
      expect(texts[0]).toBe(`${g.label} energy context: ${m.label}, ${m.year}`);
      expect(texts[1]).toContain(m.unit);
      expect(texts[1]).toContain("National annual totals");
      expect(texts[1]).toContain(g.sources[m.source_id].name);
      const rows = texts.slice(2, 2 + systems.length);
      expect(rows.map((t) => t.split(": ")[0])).toEqual(systems.map((s) => s.name));
      systems.forEach((s, i) => {
        if (s.values[id] == null) expect(rows[i]).toContain("no data"); else expect(rows[i]).toMatch(/: [\d.,]+ /);
        expect(rows[i].includes("· GCC")).toBe(s.gcc_member);
        expect(rows[i].includes("· OPEC")).toBe(s.opec_member);
        expect(rows[i].includes("research preview")).toBe(s.maturity === "research_preview");
      });
      const foot = texts.slice(2 + systems.length).join(" ");
      const r = g.region[id];
      if (r.value == null) expect(foot).toContain(`Not summed: ${r.reason}`);
      else if (r.world_share != null) expect(foot).toContain(`${Math.round(r.world_share * 1000) / 10}% of the world total`);
      expect(foot).toContain("No index is published for any of them");
      expect(foot).toContain("no facilities, no routes or shipping, no current status of any facility");
      expect(texts.join(" ")).not.toMatch(/\b(attacks?|strikes?|incidents?|records)\b/i);
      // Nothing runs off the right edge of the image.
      for (const d of drawn) expect(d.right, `"${d.text}" runs off the image`).toBeLessThanOrEqual(1600);
    }
  });

  test("every served original-language headline is on the page in its own script, and at least one exists", async ({ app, page }) => {
    let checked = 0;
    for (const id of GULF) {
      await app.open(`?sys=${id}`);
      const events = (await payload(page, id, "events.json")).events as Event[];
      const titled = events.flatMap((e) => e.sources).filter((s) => s.title_original);
      const shown = page.locator(".source-title bdi");
      await expect(shown).toHaveCount(titled.length);
      const onPage = await shown.evaluateAll((els) => els.map((el) => ({ text: el.textContent, lang: el.getAttribute("lang"), dir: el.getAttribute("dir") })));
      expect(onPage.map((x) => x.text).sort()).toEqual(titled.map((s) => s.title_original).sort());
      for (const x of onPage) {
        expect(x.lang).toMatch(/^(ar|fa|ku)$/);
        expect(x.dir).toBe("rtl");
      }
      checked += titled.length;
    }
    expect(checked, "no original-language headline is served: this test proved nothing").toBeGreaterThan(0);
  });

  test("a converted date shows what the source wrote, its calendar and the basis", async ({ app, page }) => {
    // No served record carries a converted date yet. The fields are added in the browser only:
    // a rendering fixture, not a fact about the record.
    await page.route("**/data/systems/kw/events.json", async (route) => {
      const response = await route.fetch();
      const d = await response.json();
      for (const e of d.events) {
        Object.assign(e, { date_calendar: "solar_hijri", source_date_text: "۲۵ خرداد ۱۴۰۴",
                           conversion_basis: "Solar Hijri to Gregorian, arithmetic calendar (exact)" });
      }
      await route.fulfill({ response, json: d });
    });
    await app.open("?sys=kw");
    const item = page.locator(".event-item").first();
    await expect(item).toContainText("Date in the source:");
    await expect(item.locator('bdi[lang="fa"]')).toHaveText("۲۵ خرداد ۱۴۰۴");
    await expect(item).toContainText("Solar Hijri calendar");
    await expect(item).toContainText("arithmetic calendar (exact)");
  });
});
