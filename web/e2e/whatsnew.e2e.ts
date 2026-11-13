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
    // No link or markup in the panel carries an event id: a campaign system's ids can name the
    // facility, and the panel links only to the country page (?sys=<id>).
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
    for (const h of hrefs) expect(h).toMatch(/^\?sys=[a-z]{2}$|^#|^https?:/);
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
    await expect(ru).toContainText("Monitored-Area ESDI 6.80 to 6.69.");
    await expect(ru).not.toContainText("New published records");
    const sa = panel.locator('.wn-system[data-system="sa"]');
    await expect(sa).toContainText("dated 1 Mar 2022 to 1 May 2024. All dated before the previous build: the record catching up, not new disruption.");
    await expect(sa.locator(".wn-items li")).toHaveText(["Mar 2022 · National · Oil refinery"]);
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
