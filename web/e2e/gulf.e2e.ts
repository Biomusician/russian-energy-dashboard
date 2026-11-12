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
                    maturity: string; recovery_status_withheld: boolean; values: Record<string, number | null> };
type Event = { event_id: string; cause: string; region_code: string | null; region_name: string | null;
               facility_name: string | null; geography_precision: string; summary: string; effect: string | null;
               regions_affected: string[]; sources: { url: string; title_original?: string; language?: string }[] };

const json = (page: Page, path: string) => page.evaluate((p) => fetch(p).then((r) => r.json()), path);
const manifest = (page: Page) => json(page, "/data/global/manifest.json");
const gulf = (page: Page) => json(page, "/data/global/gulf.json");
const payload = (page: Page, id: string, file: string) => json(page, `/data/systems/${id}/${file}`);

// Wording a regional picture must never carry, whatever the data says.
const RANKING = /\b(rank(ed|ing)?|league|top \d|most (important|vulnerable|critical|exposed)|worst[- ]hit|hardest[- ]hit)\b/i;
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
    const filter = page.getByLabel("Filter monitored systems by group");
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
    await expect(page.locator(".map-control-row")).toContainText("Iran and Iraq are not members");

    await app.button("Open the Gulf overview").click();
    await expect(page).toHaveURL(/[?&]group=gulf\b/);
    await expect(page.getByRole("heading", { name: "Gulf overview", level: 1 })).toBeVisible();
    await page.goBack();
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
  });

  test("the overview lists all eight alphabetically with national context, its year and its source", async ({ app, page }) => {
    await app.open("?group=gulf");
    const g = await gulf(page);
    const systems = g.systems as GulfSystem[];
    expect(systems).toHaveLength(8);
    await expect(page.getByRole("heading", { name: "Gulf overview", level: 1 })).toBeVisible();
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
      await expect(card.getByText("Recovery status withheld")).toHaveCount(s.recovery_status_withheld ? 1 : 0);
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
    for (const src of g.sources as { name: string }[]) {
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

    const main = await page.locator("main").innerText();
    expect(main).not.toMatch(RANKING);
    expect(main).not.toMatch(ROUTES);
    expect(main).toContain("Gulf, GCC and OPEC are three different things");
  });

  test("regional events are in date order only, and an attack under a country rule names no place", async ({ app, page }) => {
    await app.open("?group=gulf");
    const g = await gulf(page);
    const feed = page.getByRole("region", { name: "Recent reviewed events in this region" });
    await expect(feed).toContainText("Date order only");
    await expect(feed).toContainText("not a deteriorating region");
    const eps = g.recent.episodes as { system_id: string; start: string; members: { region: string; withheld: boolean }[] }[];
    if (eps.length === 0) {
      await expect(feed).toContainText("No qualifying records in the current reviewed corpus for this region");
      return;
    }
    await expect(feed.locator(".feed-item")).toHaveCount(eps.length);
    const starts = eps.map((e) => e.start);
    expect(starts).toEqual([...starts].sort().reverse());
    expect(await feed.innerText()).not.toMatch(ROUTES);
  });

  test("the regional brief downloads as a real image carrying its framing", async ({ app, page }) => {
    await app.open("?group=gulf");
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
    await expect(page.getByRole("heading", { name: "Gulf overview", level: 1 })).toBeVisible();
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

  for (const id of GULF) {
    test(`${id}: what the page shows for an attack matches the system's precision rule`, async ({ app, page }) => {
      await app.open(`?sys=${id}`);
      const sys = await payload(page, id, "system.json");
      const events = (await payload(page, id, "events.json")).events as Event[];
      const policy = sys.geography.precision_policy as { kinetic: string; other: string } | undefined;
      test.skip(!policy || policy.kinetic !== "country", "this system places attacks at first-level regions");
      const attacks = events.filter((e) => e.cause === "attack");
      for (const e of attacks) {
        expect(e.region_code, `${e.event_id} carries a region`).toBeNull();
        expect(e.facility_name, `${e.event_id} carries a facility`).toBeNull();
        expect(e.geography_precision).toBe("country");
        expect(e.event_id).toMatch(new RegExp(`^${id}-\\d{4}(-\\d{2}){0,2}-[a-z_]+-attack-\\d+$`));
      }
      // On the page each such record is titled with the country and nothing narrower.
      const titles = await page.locator(".event-item").filter({ hasText: /attack/i }).locator(".event-title").allInnerTexts();
      for (const t of titles) expect([sys.name, ...events.map((e) => e.facility_name ?? e.region_name ?? sys.name)]).toContain(t);
      const attackTitles = await page.locator(".event-item").evaluateAll((items, causeLabel) =>
        items.filter((li) => li.querySelector(".event-head")?.textContent?.includes(causeLabel as string))
             .map((li) => li.querySelector(".event-title")?.textContent ?? ""), sys.taxonomy.causes.attack?.label ?? "Attack");
      for (const t of attackTitles) expect(t).toBe(sys.name);
      // And the page offers no restart or repair wording for them.
      const text = await page.locator(".event-list, .country-side").first().innerText();
      if (attacks.length === events.length && attacks.length > 0) {
        expect(text).not.toMatch(/\b(restarted|resumed operations|back online|repairs? (completed|under way)|fully restored)\b/i);
      }
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
      await app.button("Sources & data quality").click();
      await expect(page.locator(".country-side")).toContainText(sys.name);
      await app.button("Events").click();
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
    await expect(page.getByRole("heading", { name: "Gulf overview", level: 1 })).toBeVisible();
    await expect(page.getByRole("region", { name: "Monitored systems in this view" }).getByRole("article")).toHaveCount(8);
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
      });
    }
  }
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
