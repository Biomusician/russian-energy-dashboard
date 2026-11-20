import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test, expect } from "./fixtures";

/**
 * Iteration-22 release closure: the first-time-user (C) and mobile/accessibility (A) review
 * findings, in a real browser. The atlas reads the pipeline's synthetic fixture
 * (e2e/fixtures/impacts22); the other pages read the build as served.
 */

type Page = import("@playwright/test").Page;
type Json = Record<string, unknown>;
type Rec = Json & { record_kind: string; ai_involvement: { status: string } };

const fixture = (name: string) => JSON.parse(readFileSync(fileURLToPath(new URL(`./fixtures/impacts22/global/${name}`, import.meta.url)), "utf-8"));

async function serve(page: Page) {
  const impacts = fixture("impacts.json") as Json & { records: Rec[]; countries: { name: string; system_id: string | null }[] };
  for (const f of ["impacts.json", "regional_context.json", "evidence_confidence.json"]) {
    await page.route(`**/data/global/${f}`, (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fixture(f)) }));
  }
  return impacts;
}

async function openAtlas(page: Page, query = "") {
  await page.goto(`/?view=impacts${query}`);
  await expect(page.getByRole("heading", { name: "Impact atlas", level: 1 })).toBeVisible();
  await expect(page.getByTestId("atlas-summary")).toBeVisible();
}

test.describe("review: home and country pages", () => {
  test("C1: a country card with no qualifying record links its impact records tab, with no count", async ({ app, page }) => {
    await app.open("");
    const m = await page.evaluate(async () => (await fetch("/data/global/manifest.json")).json()) as
      { systems: { id: string; name: string; kind: string; record_reviewed?: string | null }[] };
    const countries = m.systems.filter((s) => s.kind === "country");
    for (const s of countries) {
      const card = page.getByRole("article", { name: s.name, exact: true });
      await expect(card.locator(".home-impact-note")).toHaveCount(s.record_reviewed === null ? 1 : 0);
    }
    const zero = countries.filter((s) => s.record_reviewed === null);
    test.skip(zero.length === 0, "every country system has a qualifying record in this build");
    const card = page.getByRole("article", { name: zero[0].name, exact: true });
    const link = card.getByRole("link", { name: new RegExp(`^impact records tab for ${zero[0].name}`) });
    await expect(link).toHaveAttribute("href", `?sys=${zero[0].id}&tab=impacts`);
    await expect(card.locator(".home-impact-note")).not.toContainText(/\d/);
    await link.click();
    await expect(page).toHaveURL(new RegExp(`[?&]sys=${zero[0].id}&tab=impacts`));
    await expect(page.locator(".country-impacts h2")).toHaveText("Impact records (not scored)");
  });

  test("A14 + C9: a deep link to a tab brings it into view on a phone; a zero-record badge implies no events", async ({ app, page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await app.open("?sys=ir&tab=impacts");
    await expect(page.locator("#country-details")).toBeInViewport();
    const sys = await page.evaluate(async () => (await fetch("/data/systems/ir/system.json")).json()) as { event_summary: { recorded_events: number } };
    if (sys.event_summary.recorded_events === 0) {
      await expect(page.locator(".country-main")).not.toContainText("Reported events, no index");
    }
  });

  test("A13: 'How this works' opens a dialog named for that section", async ({ app, page }) => {
    await app.open("");
    await page.getByRole("button", { name: "How this works, in six steps" }).click();
    await expect(page.getByRole("dialog", { name: "How this works Glossary" })).toBeVisible();
  });
});

test.describe("review: the atlas", () => {
  test("C3, C6, A5: monitored tags in words, preset counts, an empty-preset note, a Saved status for each download", async ({ page }) => {
    const impacts = await serve(page);
    await openAtlas(page);
    const list = page.locator(".atlas-country-list");
    for (const c of impacts.countries.filter((x) => x.system_id)) {
      await expect(list.getByRole("button", { name: new RegExp(`^${c.name} \\(monitored system\\)`) })).toHaveCount(1);
    }
    const ai = page.getByRole("navigation", { name: "Preset views" }).getByRole("link", { name: /^AI involved/ });
    const aiRecords = impacts.records.filter((r) => r.record_kind === "disruption" && r.ai_involvement.status !== "NONE_REPORTED").length;
    await expect(ai.locator(".atlas-preset-n")).toHaveText(`${aiRecords} published records`);
    await ai.click();
    await expect(page.locator(".atlas-preset-empty")).toHaveCount(aiRecords === 0 ? 1 : 0);

    await openAtlas(page);
    await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: /^About this file/ }).click()]);
    await expect(page.getByRole("status").filter({ hasText: /^Saved .+\.txt\.?$|^Saved .*readme/i })).toHaveCount(1);
    await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: /^Download CSV/ }).click()]);
    await expect(page.getByRole("status").filter({ hasText: /^Saved .+\.csv: \d+ of \d+ published records\.$/ })).toHaveCount(1);
  });

  test("C7: an unknown-cause record has no attribution question; nothing says 'malicious or possibly malicious' over it", async ({ page }) => {
    const impacts = await serve(page);
    await openAtlas(page);
    const unknownCause = impacts.records.filter((r) => r.record_kind === "disruption" && r.cause_family === "unknown"
      && (r.attribution as { status: string }).status === "UNKNOWN");
    await expect(page.locator(".attr-no-question")).toHaveCount(unknownCause.length);
    for (const el of await page.locator(".attr-no-question").all()) await expect(el).not.toContainText(/possibly malicious/i);
  });

  test("A2: clearing the filters by keyboard leaves focus on the first filter menu, not on the page body", async ({ page }) => {
    await serve(page);
    await openAtlas(page, "&f.cause=cyber");
    const clear = page.locator(".record-filters").getByRole("button", { name: "Clear filters" });
    await clear.focus();
    await page.keyboard.press("Enter");
    await expect(clear).toBeDisabled();
    await expect(page.locator(".record-filters .rf-row button").first()).toBeFocused();
    expect(await page.evaluate(() => document.activeElement === document.body)).toBe(false);
    await expect(page.locator(".record-filters .rf-count")).toContainText("Showing");
  });
});

test.describe("review: the atlas on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });

  test("A4 + A6: the country list is closed; one caveat above the records; the sheet's count stays in sight", async ({ page }) => {
    await serve(page);
    await openAtlas(page);
    const disclosure = page.locator(".atlas-country-disclosure");
    await expect(disclosure).toHaveCount(1);
    await expect(disclosure).not.toHaveAttribute("open", "");
    await expect(page.locator(".atlas-caveats")).toBeHidden();
    await expect(page.locator(".atlas-bias-short")).toBeHidden();
    await expect(page.locator(".atlas-intro .atlas-bias")).toBeVisible();
    await page.locator(".record-filters").getByRole("button", { name: /^Filters \(/ }).click();
    const sheet = page.getByRole("dialog", { name: /Filter the published records/ });
    const foot = sheet.locator(".rf-sheet-foot");
    await expect(foot).toBeInViewport();
    await sheet.evaluate((el) => { el.scrollTop = Math.floor(el.scrollHeight / 2); });
    await expect(foot).toBeInViewport();
    expect(await foot.evaluate((el) => getComputedStyle(el).position)).toBe("sticky");
  });

  test("A1: the Why? button and the inline disclosure links reach 24 px", async ({ page }) => {
    await serve(page);
    await openAtlas(page);
    const b = (await page.locator(".conf-why").first().boundingBox())!;
    expect(b.height).toBeGreaterThanOrEqual(23.5);
    expect(b.width).toBeGreaterThanOrEqual(23.5);
    await page.goto("/");
    await expect(page.locator(".disclosure-button.linklike").first()).toBeVisible();
    for (const h of await page.locator(".disclosure-button.linklike").evaluateAll((els) => els.map((e) => e.getBoundingClientRect().height))) {
      expect(h).toBeGreaterThanOrEqual(23.5);
    }
  });
});

test.describe("review: Gulf and theatre", () => {
  test("A9: a missing impacts.json is one alert; the services section says it as a status", async ({ app, page }) => {
    app.allowConsoleError(/status of 404|404|impacts/i);
    await page.route("**/data/global/impacts.json", (r) => r.fulfill({ status: 404, body: "" }));
    await app.open("?group=gulf");
    await expect(page.locator("#sec-services").getByRole("status").filter({ hasText: "could not be loaded" })).toHaveCount(1);
    await expect(page.getByRole("alert").filter({ hasText: "impact" })).toHaveCount(1);
  });

  test("A12: the Gulf table's country buttons say they open the page; the member list says it shows the map", async ({ app, page }) => {
    await app.open("?group=gulf");
    const g = await (await page.request.get("/data/global/gulf.json")).json() as { systems: { name: string }[] };
    const first = g.systems[0].name;
    await expect(page.locator(".group-table tbody button.linklike").first()).toHaveAccessibleName(`${first}: open its page`);
    await expect(page.getByRole("button", { name: `${first}, show on the map`, exact: true })).toHaveCount(1);
  });

  test("A3: the theatre's scope note can be reached with the keyboard and is named", async ({ app, page }) => {
    await app.open("?sys=ru");
    const note = page.locator(".map-scope-note");
    await expect(note).toHaveAttribute("tabindex", "0");
    await note.focus();
    await expect(note).toBeFocused();
    await expect(note).toHaveAccessibleName(/scope note/);
  });
});
