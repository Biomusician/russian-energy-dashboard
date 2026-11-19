import { test, expect } from "./fixtures";

/**
 * "What's new in the data" on the global home (iteration 21), in a real browser.
 *
 * Every expectation is read from the file the page itself loaded: what changed depends on the day
 * the build ran. What is fixed is the behaviour — categories named by cause, systems in alphabetical
 * order, no counts, campaign systems abstracted, and an age worked out on the reader's clock.
 */

const GULF = new Set(["ae", "bh", "iq", "ir", "kw", "om", "qa", "sa"]);

async function served(page: import("@playwright/test").Page) {
  return page.evaluate(async () => (await fetch("/data/global/whats_new.json")).json());
}

test.describe("what's new in the data", () => {
  test("lists what the served file says, by cause, alphabetically, with no counts", async ({ app, page }) => {
    await app.open("");
    const d = await served(page);
    const panel = page.getByRole("region", { name: "What's new in the data" });
    await expect(panel).toBeVisible();
    test.skip(!d.available, "this build has no comparison");
    await expect(panel.locator(".wn-basis")).toContainText("Changes since the published build of");
    const names = await panel.locator(".wn-system[data-system] .wn-name").allInnerTexts();
    expect(names).toEqual(d.systems.map((s: { name: string }) => s.name));
    expect(names.map((n) => n.trim())).toEqual([...names].map((n) => n.trim()).sort((a, b) => a.localeCompare(b)));
    const labels = new Map(d.categories.map((c: { id: string; label: string }) => [c.id, c.label]));
    let rows = 0;
    for (const s of d.systems) {
      const block = panel.locator(`.wn-system[data-system="${s.system_id}"]`);
      for (const c of s.changes) {
        rows += 1;
        await expect(block.locator(`.wn-change[data-category="${c.category}"] .wn-cat`).first()).toHaveText(labels.get(c.category) as string);
      }
      if (GULF.has(s.system_id)) {
        // A campaign system's withdrawn or held records are one sentence: no rows beneath them.
        await expect(block.locator('.wn-change[data-category="records_withdrawn"] .wn-items')).toHaveCount(0);
        await expect(block.locator('.wn-change[data-category="recovery_evidence"]')).toHaveCount(0);
      }
    }
    expect(rows + d.global.length).toBeGreaterThan(0);
    // No event id on the page: ids can name a facility.
    const text = await panel.innerText();
    for (const s of d.systems) for (const c of s.changes) for (const it of c.items ?? []) expect(text).not.toContain(it.key);
    expect(text).not.toMatch(/\b\d+ (records|events|withdrawn|held)\b/i);
    for (const u of d.unchanged) await expect(panel.locator(".wn-unchanged")).toContainText(u.name);
    // No link or markup in the panel carries a campaign system's event id: there an id can name the
    // facility. Elsewhere (iteration 22) a row links to its record, a coverage or method change to
    // the country's tab, and a rule change to this page's own account of how it works.
    for (const s of d.systems) await panel.locator(`.wn-system[data-system="${s.system_id}"] summary`).click();
    const html = await panel.innerHTML();
    const hrefs = await panel.locator("a").evaluateAll((as) => as.map((a) => (a as HTMLAnchorElement).getAttribute("href") ?? ""));
    let idsChecked = 0;
    for (const sid of GULF) {
      const ev = await page.evaluate(async (i) => (await fetch(`/data/systems/${i}/events.json`)).json(), sid);
      for (const e of ev.events) {
        idsChecked += 1;
        expect(html).not.toContain(e.event_id);
        for (const h of hrefs) expect(h).not.toContain(e.event_id);
      }
    }
    expect(idsChecked).toBeGreaterThan(0);
    for (const h of hrefs) expect(h).toMatch(/^\?sys=[a-z]{2}(#(ev-[A-Za-z0-9_-]+|tab-(research|method)))?$|^#|^https?:/);
    for (const sid of GULF) {
      await expect(panel.locator(`.wn-system[data-system="${sid}"] a.wn-record`)).toHaveCount(0);
    }
    // Each system is one closed line naming its kinds of change; opening it leads to the country.
    const first = d.systems[0];
    const block = panel.locator(`.wn-system[data-system="${first.system_id}"]`);
    await expect(block.locator(".wn-kinds")).toHaveText(
      first.unavailable ? "could not be compared" : first.changes.map((c: { category: string }) => labels.get(c.category)).join(" · "));
    // Already opened above.
    await block.getByRole("button", { name: `Go to the ${first.name} page` }).click();
    await expect(page).toHaveURL(new RegExp(`[?&]sys=${first.system_id}\\b`));
  });

  test("the build's age is worked out on the reader's clock", async ({ app, page }) => {
    await page.clock.setFixedTime(new Date("2030-01-15T12:00:00Z"));
    await app.open("");
    const d = await served(page);
    test.skip(!d.available, "this build has no comparison");
    const days = Math.round((Date.UTC(2030, 0, 15) - Date.parse(`${d.comparison.current_as_of}T00:00:00Z`)) / 86400000);
    await expect(page.locator(".whats-new .wn-basis")).toContainText(`built ${days} days ago, by your device's clock`);
  });

  test("a backfill reads as the record catching up, and a decay-only day as decay", async ({ app, page }) => {
    await page.route("**/data/global/whats_new.json", async (route) => {
      const res = await route.fetch();
      const body = await res.json();
      body.available = true;
      body.comparison = { previous_as_of: "2026-11-11", current_as_of: "2026-11-12", mode: "production", basis: "b" };
      body.global = [];
      body.unchanged = [];
      body.systems = [
        { system_id: "ru", name: "Russia, Belarus & Crimea", kind: "theatre",
          index: { label: "Monitored-Area ESDI", before: 6.8, after: 6.69, separable: true },
          changes: [{ category: "decay_only", notes: ["No input changed; only the evaluation date moved, so modelled impairment aged."] }] },
        { system_id: "sa", name: "Saudi Arabia", kind: "country", changes: [
          { category: "records_added", notes: [], event_dates: ["2022-03-01", "2024-05-01"], all_predate_previous_build: true,
            items: [{ key: "sa-change-01", date: "2022-03", date_precision: "month", region: "National", class: "Oil refinery" }], more: false },
          { category: "records_withdrawn", aggregated: true, notes: ["One or more records shown before are not shown now."] }] },
      ];
      await route.fulfill({ response: res, json: body });
    });
    await app.open("");
    const panel = page.getByRole("region", { name: "What's new in the data" });
    const ru = panel.locator('.wn-system[data-system="ru"]');
    await ru.locator("summary").click();
    await panel.locator('.wn-system[data-system="sa"] summary').click();
    await expect(ru.locator(".wn-cat")).toHaveText(["Index moved by time decay only"]);
    // Levels at the headline's one decimal, the movement at two (methodology red team, iteration 21).
    await expect(ru).toContainText("Monitored-Area ESDI 6.8 to 6.7 (−0.11).");
    await expect(ru).not.toContainText("New published records");
    const sa = panel.locator('.wn-system[data-system="sa"]');
    await expect(sa).toContainText("dated 1 Mar 2022 to 1 May 2024. All dated before the previous build: the record catching up, not new disruption.");
    await expect(sa.locator(".wn-items li")).toHaveText(["Mar 2022 · National · Oil refinery"]);
  });

  test("a record outside the campaign rule opens on its country page, and a coverage change on its tab", async ({ app, page }) => {
    let recordId = "";
    await page.route("**/data/global/whats_new.json", async (route) => {
      const res = await route.fetch();
      const body = await res.json();
      // A real published record of a system outside the campaign rule, so the link has somewhere to land.
      const origin = new URL(route.request().url()).origin;
      const us = await (await page.request.get(`${origin}/data/systems/us/events.json`)).json();
      const e = us.events[0];
      recordId = e.event_id;
      body.available = true;
      body.comparison = { previous_as_of: "2026-11-11", current_as_of: "2026-11-12", mode: "production", basis: "b" };
      body.global = [{ category: "methodology", notes: ["The inclusion threshold for country records was revised."], link: { anchor: "why-head" } }];
      body.unchanged = [];
      body.impact_layer = [
        { category: "impact_record_added", notes: [], more: false, all_backfill: false, all_new_events: false, items: [
          { key: "impact-change-01", impact_id: "imp-a", date: "2023-12-12", date_precision: "day", country: "Ukraine", sector: "telecom",
            timing: "backfill", first_published: "2026-11-12" },
          { key: "impact-change-02", impact_id: "imp-b", date: "2026-11-10", date_precision: "day", country: "Ukraine", sector: "water",
            timing: "new_event", first_published: "2026-11-12" }] },
        { category: "attribution_updated", notes: ["The attribution of an existing record was updated. Not a new incident."], more: false, items: [
          { key: "impact-change-03", impact_id: "imp-c", date: "2024-02-01", date_precision: "day", country: "Ukraine", sector: "telecom",
            from: "CLAIMED", to: "ATTRIBUTED" }] }];
      body.systems = [
        { system_id: "sa", name: "Saudi Arabia", kind: "country", changes: [
          { category: "records_added", notes: [], event_dates: ["2022-03-01", "2022-03-01"], all_predate_previous_build: true,
            items: [{ key: "sa-change-01", date: "2022-03", date_precision: "month", region: "National", class: "Oil refinery" }], more: false }] },
        { system_id: "us", name: "United States", kind: "country", changes: [
          { category: "research_coverage", notes: ["The stated research gaps were revised."], link: { system_id: "us", tab: "research" } },
          { category: "data_correction", notes: [], more: false,
            items: [{ key: "us-change-01", date: e.date, date_precision: e.date_precision, region: e.region_name ?? "National",
                      class: "Corrected record", fields: ["sources"], record_id: e.event_id }] }] },
      ];
      await route.fulfill({ response: res, json: body });
    });
    await app.open("");
    const panel = page.getByRole("region", { name: "What's new in the data" });
    await panel.locator('.wn-system[data-system="us"] summary').click();
    await panel.locator('.wn-system[data-system="sa"] summary').click();
    const anchor = `ev-${recordId.replace(/[^A-Za-z0-9_-]/g, "-")}`;

    // The campaign system's row is text; the other system's row is a link to the record's own anchor.
    await expect(panel.locator('.wn-system[data-system="sa"] a.wn-record')).toHaveCount(0);
    await expect(panel.locator('.wn-system[data-system="sa"] .wn-items li')).toHaveText(["Mar 2022 · National · Oil refinery"]);
    const record = panel.locator('.wn-system[data-system="us"] a.wn-record');
    await expect(record).toHaveAttribute("href", `?sys=us#${anchor}`);
    await expect(panel.locator(".wn-global a.wn-link")).toHaveAttribute("href", "#why-head");

    // The impact layer is said once, apart from any country, and tells a backfill from a new event.
    const impact = panel.locator(".wn-impact");
    await expect(impact).toContainText("12 Dec 2023 · Ukraine · telecom — historical record found by research, not a new event");
    await expect(impact).toContainText("10 Nov 2026 · Ukraine · water — new event");
    await expect(impact).toContainText("attribution: Claimed → Attributed (existing record, not a new incident)");
    await expect(impact.locator("a")).toHaveCount(0);

    // Keyboard: the link is reachable and Enter follows it, to the record on its country page.
    await record.focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(new RegExp(`[?&]sys=us\\b.*#${anchor}$`));
    await expect(page.locator(`[id="${anchor}"]`)).toBeVisible();

    // Back, then the coverage change opens the country on its Research coverage tab.
    await page.goBack();
    const back = page.getByRole("region", { name: "What's new in the data" });
    await back.locator('.wn-system[data-system="us"] summary').click();
    await back.getByRole("link", { name: "Open Research coverage" }).click();
    await expect(page).toHaveURL(/[?&]sys=us\b.*#tab-research$/);
    await expect(page.getByRole("button", { name: "Research coverage", exact: true })).toHaveAttribute("aria-pressed", "true");
  });

  test("a malformed file is refused and the rest of the home page keeps working", async ({ app, page }) => {
    await page.route("**/data/global/whats_new.json", (r) => r.fulfill({ status: 200, contentType: "application/json",
      body: JSON.stringify({ available: true, systems: "x" }) }));
    await app.open("");
    await expect(page.getByRole("alert").filter({ hasText: "The list of changes could not be loaded" })).toBeVisible();
    await expect(page.getByRole("article")).not.toHaveCount(0);
  });

  test("a build with no comparison says so rather than showing an empty list", async ({ app, page }) => {
    await page.route("**/data/global/whats_new.json", async (route) => {
      const res = await route.fetch();
      const body = await res.json();
      Object.assign(body, { available: false, unavailable_reason: "no baseline", systems: [], global: [], unchanged: [] });
      await route.fulfill({ response: res, json: body });
    });
    await app.open("");
    await expect(page.locator(".whats-new")).toContainText("That is not the same as nothing having changed.");
  });
});
