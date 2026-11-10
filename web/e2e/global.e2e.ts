import { test, expect, colourGrid, pixelStats, readBytes, readStructure, structureProfile } from "./fixtures";

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
    // Totals for the five countries together, once, outside every card (iteration 17).
    const totals = page.getByRole("region", { name: "Country record, all five together" });
    await expect(totals).toContainText(`${m.corpus.records} reported disruptions in ${m.corpus.episodes} episodes`);
    await expect(totals).toContainText(`${m.corpus.research_lanes} source groups`);
    for (const s of m.systems) {
      await expect(page.getByRole("article", { name: s.name })).not.toContainText(String(m.corpus.records));
    }
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

  for (const id of COUNTRIES) {
    test(`${id}: a deep link to its busiest region lists exactly that region's records`, async ({ app, page }) => {
      await app.open(`?sys=${id}`);
      const events = (await countryPayload(page, id, "events.json")).events as
        { region_code: string | null; region_name: string; geography_precision: string; regions_affected: string[] }[];
      const counts = new Map<string, { n: number; name: string }>();
      for (const e of events) {
        if (e.region_code) counts.set(e.region_code, { n: (counts.get(e.region_code)?.n ?? 0) + 1, name: e.region_name });
      }
      const [code, { n, name }] = [...counts.entries()].sort((a, b) => b[1].n - a[1].n)[0];
      // Multi-region records naming this region are listed beside it, never counted in it.
      const shared = events.filter((e) => e.geography_precision !== "admin1" && e.regions_affected.includes(code)).length;
      await app.open(`?sys=${id}&r=${code}`);
      await expect(page.getByRole("heading", { name, level: 2 })).toBeVisible();
      await expect(page.locator(".event-item")).toHaveCount(n + shared);
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
    // Multi-region records naming this region are listed beside it, never counted in it.
    const shared = events.filter((e: { geography_precision: string; regions_affected: string[] }) =>
      e.geography_precision !== "admin1" && e.regions_affected.includes(code)).length;
    await app.open(`?sys=us&r=${code}`);
    await expect(page.getByRole("heading", { name, level: 2 })).toBeVisible();
    await expect(page.locator(".event-item")).toHaveCount(n + shared);
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
    // The count comes from the payload: the iteration-16 sweep found Helene in ten states, and
    // the next sweep may find more. What is fixed is that one hurricane is one group.
    const ep = payload.episodes.find((x: { hazard: string | null }) => x.hazard?.startsWith("Hurricane Helene"));
    const helene = page.locator(".episode-group").filter({ hasText: "Hurricane Helene" });
    await expect(helene).toHaveCount(1);
    await expect(helene.locator(".event-item")).toHaveCount(ep.records);
    await expect(helene).toContainText(`${ep.records} records`);
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
    await app.button("Research coverage").click();
    await expect(page.locator(".research-log tbody tr")).toHaveCount(sys.research_log.passes.length);
    await expect(page.locator(".research-log")).toContainText("targeted search (never complete by design)");
  });

  test("a source past its limit is flagged on the reader's clock, not the build's", async ({ app, page }) => {
    await page.route("**/data/systems/ca/system.json", async (route) => {
      const res = await route.fetch();
      const body = await res.json();
      body.sources[0].last_checked = "2020-01-01";
      await route.fulfill({ response: res, json: body });
    });
    await app.open("?sys=ca");
    await app.button("Sources & data quality").click();
    await expect(page.locator(".source-table .stale-flag")).toHaveCount(1);
  });
});

test.describe("provenance and coverage (iteration 16)", () => {
  test("research completeness and source freshness are two separate badges", async ({ app, page }) => {
    await app.open("?sys=us");
    const sys = await countryPayload(page, "us", "system.json");
    const status = page.getByLabel("Research status");
    // The US has had a systematic sweep; whether it completed is the payload's claim, read here.
    const label = { complete: "Systematic search complete", partial: "Systematic search under way",
                    never_systematic: "Targeted searches only" }[sys.research_freshness.completeness as string]!;
    await expect(status).toContainText(label);
    await expect(status).toContainText("One does not imply the other");
    await app.button("Sources & data quality").click();
    await expect(page.locator(".research-coverage")).toContainText(label);
    await app.button("Research coverage").click();
    // Every systematic pass lists its lanes, each with its own status (two passes since iteration 17).
    const lanes = sys.research_log.passes.filter((x: { kind: string }) => x.kind === "systematic")
      .reduce((n: number, x: { lanes?: unknown[] }) => n + (x.lanes?.length ?? 0), 0);
    expect(lanes).toBeGreaterThan(0);
    await expect(page.locator(".research-log .lane-list li")).toHaveCount(lanes);
  });

  test("a country never searched systematically says so, whatever its sources' freshness", async ({ app, page }) => {
    await app.open("?sys=cn");
    const sys = await countryPayload(page, "cn", "system.json");
    test.skip(sys.research_freshness.completeness !== "never_systematic", "China has had a systematic pass");
    await expect(page.getByLabel("Research status")).toContainText("Targeted searches only");
  });

  test("stale sources change the freshness badge and leave research completeness alone", async ({ app, page }) => {
    await app.open("?sys=ca");
    const before = await page.getByLabel("Research status").locator(".badge").first().innerText();
    await page.route("**/data/systems/ca/system.json", async (route) => {
      const res = await route.fetch();
      const body = await res.json();
      for (const s of body.sources) s.last_checked = "2020-01-01";
      await route.fulfill({ response: res, json: body });
    });
    await app.open("?sys=ca");
    const status = page.getByLabel("Research status");
    await expect(status).toContainText("overdue for a re-check");
    await expect(status.locator(".badge").first()).toHaveText(before);
  });

  test("an active attack campaign publishes the event, never the facility's status", async ({ app, page }) => {
    await app.open("?sys=sa");
    const events = (await countryPayload(page, "sa", "events.json")).events as
      { event_id: string; publication: { note: string } | null }[];
    const covered = events.filter((e) => e.publication);
    expect(covered.length).toBeGreaterThan(0);
    await expect(page.locator(".withheld-note")).toHaveCount(covered.length);
    const items = page.locator(".event-item").filter({ has: page.locator(".withheld-note") });
    for (let i = 0; i < covered.length; i++) {
      const item = items.nth(i);
      await expect(item).toContainText("Facility status not published while the attack campaign is active");
      // The same wording rule the build enforces, on what the reader actually sees — minus the
      // policy note itself, which names what is withheld.
      const text = await item.evaluate((el) => {
        const c = el.cloneNode(true) as HTMLElement;
        c.querySelector(".withheld-note")?.remove();
        return c.innerText;
      });
      expect(text).not.toMatch(/restart|resum|reopen|back online|operating at|running at|recover|restor/i);
    }
  });

  test("every record says how it was reviewed, and the sources panel totals it", async ({ app, page }) => {
    await app.open("?sys=us");
    const sys = await countryPayload(page, "us", "system.json");
    const events = (await countryPayload(page, "us", "events.json")).events;
    await expect(page.locator(".review-note")).toHaveCount(events.length);
    await expect(page.locator(".review-note .review-dual_reviewed")).toHaveCount(sys.review_summary.dual_reviewed);
    await expect(page.locator(".review-note .review-blind_reviewed")).toHaveCount(sys.review_summary.blind_reviewed ?? 0);
    await app.button("Sources & data quality").click();
    const independent = (sys.review_summary.blind_reviewed ?? 0) + sys.review_summary.dual_reviewed;
    await expect(page.locator(".review-summary")).toContainText(`${independent} of ${events.length} events`);
  });

  test("source health counts the published citations; the browser lists publishers alphabetically", async ({ app, page }) => {
    await app.open("?sys=ca");
    const sys = await countryPayload(page, "ca", "system.json");
    const events = (await countryPayload(page, "ca", "events.json")).events;
    const cites = events.reduce((n: number, e: { sources: unknown[] }) => n + e.sources.length, 0);
    await app.button("Sources & data quality").click();
    await expect(page.locator(".source-health")).toContainText(`${cites} citations from ${sys.source_health.publishers} publishers`);
    await expect(page.locator(".source-health")).toContainText(`${sys.source_health.opened.not_recorded} not recorded`);
    const rows = page.locator(".source-browser-table tbody tr");
    await expect(rows).toHaveCount(sys.source_health.publishers);
    const names = await rows.locator("td:first-child").evaluateAll((tds) => tds.map((td) => td.childNodes[0].textContent ?? ""));
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
    await page.getByRole("combobox", { name: "Filter sources by role" }).selectOption("regulator");
    expect(await rows.count()).toBeLessThan(sys.source_health.publishers);
    await rows.first().getByRole("button").click();
    await expect(rows.first().locator("a").first()).toHaveAttribute("rel", /noopener/);
    expect(app.errors).toEqual([]);
  });

  test("a payload from before source health still renders its sources panel", async ({ app, page }) => {
    await page.route("**/data/systems/in/system.json", async (route) => {
      const res = await route.fetch();
      const body = await res.json();
      delete body.source_health;
      await route.fulfill({ response: res, json: body });
    });
    await app.open("?sys=in");
    await app.button("Sources & data quality").click();
    await expect(page.locator(".source-health")).toHaveCount(0);
    await expect(page.locator(".source-browser-table tbody tr").first()).toBeVisible();
    expect(app.errors).toEqual([]);
  });

  test("a missing Canada payload, a corrupt US payload and an invalid research log are each contained", async ({ app, page }) => {
    app.allowConsoleError(/status of 404|malformed payload|Unexpected token|JSON/);
    await page.route("**/data/systems/ca/system.json", (route) => route.fulfill({ status: 404, body: "" }));
    await page.route("**/data/systems/us/events.json", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "{\"events\": [tru" }));
    await page.route("**/data/systems/in/system.json", async (route) => {
      const res = await route.fetch();
      const body = await res.json();
      body.research_log = { passes: "corrupt" };
      await route.fulfill({ response: res, json: body });
    });
    for (const id of ["ca", "us", "in"]) {
      await page.goto(`/?sys=${id}`);
      await expect(page.getByRole("alert")).toContainText("could not be loaded");
    }
    await page.getByRole("combobox", { name: "Monitored system" }).selectOption("cn");
    await expect(page.getByRole("heading", { name: "China", level: 1 })).toBeVisible();
    await page.getByRole("combobox", { name: "Monitored system" }).selectOption("ru");
    await app.mapIdle();
    await expect(page.locator(".ribbon")).toContainText("ESDI");
  });

  test("a missing as-published history leaves the dashboard and the reconstruction working", async ({ app, page }) => {
    app.allowConsoleError(/status of 404/);
    await page.route("**/data/production_history.json", (route) => route.fulfill({ status: 404, body: "" }));
    await app.open();
    await app.button(/compare dates/i).click();
    await expect(page.getByRole("group", { name: "Which history" })).toBeVisible();
    await expect(page.locator(".comparison")).toBeVisible();
    await page.getByRole("combobox", { name: "Monitored system" }).selectOption("us");
    await expect(page.getByRole("heading", { name: "United States", level: 1 })).toBeVisible();
  });

  test("on a phone a country page's tabs, events and sources are reachable (iteration 17)", async ({ app, page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await app.open("?sys=us");
    // The body used to be squeezed to ~40px under the one-column ribbon, with the map drawn over
    // the tabs: nothing below the legend could be reached.
    const h = await page.locator(".country-body").evaluate((el) => el.getBoundingClientRect().height);
    expect(h).toBeGreaterThan(800);
    const sources = app.button("Sources & data quality");
    await sources.scrollIntoViewIfNeeded();
    await sources.click();
    await expect(page.locator(".source-browser-table tbody tr").first()).toBeVisible();
    const sideways = await page.locator(".global-page").evaluate((el) => el.scrollWidth > window.innerWidth);
    expect(sideways).toBe(false);
  });

  test("the no-index reason is true for every country, including one under attack", async ({ app, page }) => {
    await app.open("?sys=sa");
    await expect(page.locator(".no-index-plain")).not.toContainText(/weather/i);
    await expect(page.locator(".no-index-plain")).toContainText("do not transfer");
  });

  test("a broken events file is contained to its system", async ({ app, page }) => {
    app.allowConsoleError(/status of 500/);
    await page.route("**/data/systems/sa/events.json", (route) => route.fulfill({ status: 500, body: "" }));
    await page.goto("/?sys=sa");
    await expect(page.getByRole("alert")).toContainText("could not be loaded");
    await page.getByRole("combobox", { name: "Monitored system" }).selectOption("us");
    await expect(page.getByRole("heading", { name: "United States", level: 1 })).toBeVisible();
  });

  test("recovery is defined where it is shown", async ({ app, page }) => {
    await app.open("?sys=us");
    await app.button("Sources & data quality").click();
    await expect(page.locator(".recovery-meaning")).toContainText("Nothing is modelled");
  });

  test("records grouped only by an explicit basis: one statement listing incidents is not an episode", async ({ app, page }) => {
    await app.open("?sys=sa");
    const payload = await countryPayload(page, "sa", "events.json");
    const multi = payload.episodes.filter((ep: { records: number }) => ep.records > 1);
    for (const ep of multi) expect(["named_hazard", "explicit_common_event", "coordinated_wave", "explicit_continuation"]).toContain(ep.basis);
    await expect(page.locator(".episode-group")).toHaveCount(multi.length);
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

test.describe("map structure (every platform)", () => {
  // The cross-platform guard (iteration 16). The pixel goldens below are win32-only, so on Linux
  // CI nothing compared the map to anything. A coarse grid of cell means survives font and
  // anti-aliasing differences and still fails a blank map, a wrong extent or a wrong palette.
  for (const q of ["", "?sys=ru", "?sys=us", "?sys=sa"]) {
    const name = q ? q.slice(5) : "home";
    test(`map structure: ${name}`, async ({ app, page }) => {
      await app.open(q);
      const png = await page.locator("[data-map-state]").screenshot();
      const now = await colourGrid(page, png);
      const spread = (g: number[][]) => Math.max(...g.flat()) - Math.min(...g.flat());
      expect(spread(now), "the map is one flat colour").toBeGreaterThan(40);
      const want = structureProfile(`e2e/__structure__/map-${name}.json`, now);
      test.skip(want === null, "structure profile recorded");
      const off = now.filter((c, i) => Math.max(...c.map((v, k) => Math.abs(v - want![i][k]))) > 32);
      expect(off.length, `cells off the recorded structure: ${off.length} of ${now.length}`)
        .toBeLessThanOrEqual(Math.floor(now.length * 0.1));
    });
  }

  test("map structure: the check itself fails a blank map", async ({ app, page }) => {
    // A negative control: a guard never shown to fail is not known to guard anything.
    await app.open("?sys=us");
    await page.addStyleTag({ content: "[data-map-state] canvas { visibility: hidden !important; }" });
    const png = await page.locator("[data-map-state]").screenshot();
    const now = await colourGrid(page, png);
    const want = readStructure("e2e/__structure__/map-us.json");
    test.skip(want === null, "no recorded profile to compare against");
    const off = now.filter((c, i) => Math.max(...c.map((v, k) => Math.abs(v - want![i][k]))) > 32);
    expect(off.length).toBeGreaterThan(Math.floor(now.length * 0.1));
  });
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
