import { test, expect } from "./fixtures";
import { countLine, eventAnchor, originSummary } from "../src/global/evidence";
import { EMPTY_CORPUS_LEAD, RESEARCH_PREVIEW_DEFINITION } from "../src/global/countryCopy";
import type { CountryEvent } from "../src/global/manifest";

/**
 * Country pages as a reader meets them (iteration 21): the event card, the Evidence Inspector,
 * a page with no published record, "Why no score", the research-preview disclosure and record
 * anchors. Every value is read from the payload the page loaded; the origin count is computed
 * with the same module the page uses, which tests/test_iteration21_country.py pins to the
 * pipeline's own rule.
 */

type Page = import("@playwright/test").Page;
const payload = (page: Page, id: string, file: string) =>
  page.evaluate(([i, f]) => fetch(`/data/systems/${i}/${f}`).then((r) => r.json()), [id, file]);
const countryIds = async (page: Page): Promise<string[]> =>
  (await page.evaluate(() => fetch("/data/global/manifest.json").then((r) => r.json()))).systems
    .filter((s: { kind: string }) => s.kind === "country").map((s: { id: string }) => s.id);
const sideways = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);

test.describe("event cards", () => {
  test("every US card states date, type, cause, placement and its origin count by the pipeline rule", async ({ app, page }) => {
    await app.open("?sys=us");
    const events = (await payload(page, "us", "events.json")).events as CountryEvent[];
    const sys = await payload(page, "us", "system.json");
    const cards = page.locator(".event-card");
    await expect(cards).toHaveCount(events.length);
    const shown = await cards.evaluateAll((els) => els.map((el) => ({
      id: el.id, count: el.querySelector(".origin-count")?.textContent ?? "",
      date: el.querySelector(".event-date")?.textContent ?? "", tags: el.querySelectorAll(".event-tag").length,
      placement: el.querySelector(".placement-level")?.textContent ?? "", rows: el.querySelectorAll(".source-row").length,
      discovery: !!el.querySelector(".discovery-only"),
    })));
    const byAnchor = new Map(events.map((e) => [eventAnchor(e, "us"), e]));
    let checked = 0;
    for (const c of shown) {
      const e = byAnchor.get(c.id);
      expect(e, `card ${c.id} matches no served record`).toBeTruthy();
      const o = originSummary(e!);
      expect(c.count).toBe(countLine(o));
      expect(c.date).not.toBe("");
      expect(c.tags).toBe(2);
      expect(c.placement).not.toBe("");
      expect(c.rows, "one line per citation").toBe(e!.sources.length);
      expect(c.discovery).toBe(o.discoveryOnly);
      checked += 1;
    }
    expect(checked).toBe(events.length);
    // The page's own totals agree with the published source health.
    expect(shown.filter((c) => c.discovery).length).toBe(sys.source_health.discovery_only_events);
    const single = shown.filter((c) => / · 1 originating statement$/.test(c.count)).length;
    expect(single).toBe(sys.source_health.single_origin_events);
    expect(app.errors).toEqual([]);
  });

  test("a card keeps the original headline apart from its gloss, in its own script", async ({ app, page }) => {
    let checked = 0;
    for (const id of ["iq", "kw"]) {
      await app.open(`?sys=${id}`);
      const row = page.locator(".source-row").filter({ has: page.locator(".source-title") }).first();
      if (await row.count() === 0) continue;
      await expect(row.locator(".source-title bdi")).toHaveAttribute("dir", "rtl");
      await expect(row.locator(".source-title")).not.toContainText("Gloss");
      await expect(row.locator(".source-gloss")).toContainText("Gloss:");
      checked += 1;
    }
    expect(checked, "no titled source was rendered").toBeGreaterThan(0);
  });
});

test.describe("evidence inspector", () => {
  test("opens and closes from the keyboard and answers its five questions in plain words", async ({ app, page }) => {
    await app.open("?sys=ca");
    const card = page.locator(".event-card").first();
    const toggle = card.locator(".ev-inspector-toggle");
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(card.locator(".ev-inspector")).toHaveCount(0);
    await toggle.focus();
    await page.keyboard.press("Enter");
    const panel = card.getByRole("region", { name: "Evidence inspector" });
    await expect(panel).toBeVisible();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    for (const h of ["Why this record is included", "Where the report came from",
      "How many independent originating statements support it", "What this report does not establish", "Review"]) {
      await expect(panel.getByRole("heading", { name: h, exact: true })).toBeVisible();
    }
    // Plain words by default: no clause number until the reader asks for the technical detail.
    await expect(panel.locator(".ev-inspector-basis")).not.toContainText(/clause|§/i);
    const technical = panel.locator(".ev-inspector-technical");
    await expect(technical).not.toHaveAttribute("open", "");
    // Tab into the panel, open the technical detail with the keyboard, then Escape back out.
    await page.keyboard.press("Tab");
    await expect(technical.locator("summary")).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(technical).toContainText("clause");
    await page.keyboard.press("Escape");
    await expect(card.locator(".ev-inspector")).toHaveCount(0);
    await expect(toggle).toBeFocused();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await page.keyboard.press("Space");
    await expect(panel).toBeVisible();
    expect(app.errors).toEqual([]);
  });

  test("each citation states its link check where one was recorded", async ({ app, page }) => {
    await app.open("?sys=in");
    const events = (await payload(page, "in", "events.json")).events as CountryEvent[];
    const e = events.find((x) => x.sources.some((s) => s.link_check));
    expect(e, "no served citation carries a link state").toBeTruthy();
    const card = page.locator(`#${eventAnchor(e!, "in")}`);
    await card.locator(".ev-inspector-toggle").click();
    await expect(card.locator(".link-state")).toHaveCount(e!.sources.length);
    await expect(card.locator(`.link-${e!.sources.find((s) => s.link_check)!.link_check}`).first()).toBeVisible();
  });

  test("a campaign-covered record's inspector shows no headline, no figure and no later status", async ({ app, page }) => {
    await app.open("?sys=sa");
    const events = (await payload(page, "sa", "events.json")).events as CountryEvent[];
    const covered = events.filter((e) => e.publication);
    expect(covered.length).toBeGreaterThan(0);
    const cards = page.locator(".event-card").filter({ has: page.locator(".withheld-note") });
    await expect(cards).toHaveCount(covered.length);
    for (let i = 0; i < covered.length; i++) {
      const card = cards.nth(i);
      await card.locator(".ev-inspector-toggle").click();
      const panel = card.locator(".ev-inspector");
      await expect(panel).toBeVisible();
      await expect(card.locator(".source-title, .source-gloss")).toHaveCount(0);
      await expect(panel).toContainText("not published");
      const text = await panel.innerText();
      for (const x of covered) {
        if (x.capacity_affected?.value != null) expect(text).not.toContain(x.capacity_affected.value.toLocaleString("en-GB"));
      }
      expect(text).not.toMatch(/restart|resum|reopen|back online|operating at|running at|recover|restor|came back/i);
    }
  });
});

test.describe("a country with no published record", () => {
  test("leads with what the empty corpus means, says what was searched, and never prints a zero", async ({ app, page }) => {
    await app.open("");
    let checked = 0;
    for (const id of await countryIds(page)) {
      await app.open(`?sys=${id}`);
      const events = (await payload(page, id, "events.json")).events;
      if (events.length > 0) continue;
      const panel = page.locator(".empty-corpus");
      await expect(panel.locator(".empty-lead")).toHaveText(EMPTY_CORPUS_LEAD);
      for (const h of ["What was searched", "National context", "Sources", "Publication safeguards", "What remains incomplete"]) {
        await expect(panel.getByRole("heading", { name: h, exact: true })).toBeVisible();
      }
      await expect(panel).toContainText("reports disruptions");
      const body = await page.locator(".global-page").innerText();
      expect(body).not.toMatch(/\b0 (disruptions|events|records|qualifying|citations|of 0)\b|no disruptions/i);
      // No held count of any kind on a page with no record.
      expect(body).not.toMatch(/\d+ (of them )?(are )?(not shown|held|under review)/i);
      // A region filter that could filter nothing is replaced by its reason.
      await expect(page.getByRole("combobox", { name: /^Choose a / })).toHaveCount(0);
      await expect(page.locator(".region-select-reason")).toBeVisible();
      await panel.getByRole("button", { name: "Open the Research coverage tab" }).click();
      await expect(page.getByRole("heading", { name: "Research coverage" })).toBeVisible();
      await expect(page.locator(".recovery-coverage")).toHaveCount(0);
      checked += 1;
    }
    expect(checked, "no zero-record system was checked").toBeGreaterThan(0);
    expect(app.errors).toEqual([]);
  });
});

test.describe("why no score, and the research-preview definition", () => {
  test("why no score leads with the plain reason, then says no score is not zero, with the detail folded", async ({ app, page }) => {
    await app.open("?sys=us");
    await app.button("Why no score").click();
    const panel = page.locator(".why-no-score");
    await expect(panel.locator(".no-score-plain")).toContainText("designed for one conflict and one energy system");
    await expect(panel.locator(".no-score-plain")).toContainText("would imply a precision");
    await expect(panel.getByRole("heading", { name: "No score is not a score of zero" })).toBeVisible();
    await expect(panel.locator(".no-score-technical")).not.toHaveAttribute("open", "");
    await expect(panel).not.toContainText(/iteration|owner|D-\d\d|\.md\b|§/);
  });

  test("the research-preview badge explains itself on click, with the one shared definition", async ({ app, page }) => {
    await app.open("");
    const badge = page.getByRole("button", { name: /^Research preview/ }).first();
    await expect(badge).toHaveAttribute("aria-expanded", "false");
    await badge.click();
    await expect(badge).toHaveAttribute("aria-expanded", "true");
    await expect(page.getByRole("note").filter({ hasText: RESEARCH_PREVIEW_DEFINITION })).toBeVisible();
    await app.open("?sys=bh");
    await expect(page.locator(".research-preview-statement")).toContainText(RESEARCH_PREVIEW_DEFINITION);
  });
});

test.describe("record anchors", () => {
  test("a link to one record opens the full list at that record and keeps its anchor", async ({ app, page }) => {
    await app.open("?sys=us");
    const events = (await payload(page, "us", "events.json")).events as CountryEvent[];
    const oldest = [...events].sort((a, b) => (a.date < b.date ? -1 : 1))[0];
    const anchor = eventAnchor(oldest, "us")!;
    await app.open(`?sys=us#${anchor}`);
    const card = page.locator(`#${anchor}`);
    await expect(card).toHaveClass(/targeted/);
    await expect(card).toBeInViewport();
    expect(new URL(page.url()).hash).toBe(`#${anchor}`);
  });

  test("a campaign-covered record whose id names its facility has no anchor at all", async ({ app, page }) => {
    await app.open("?sys=sa");
    const events = (await payload(page, "sa", "events.json")).events as CountryEvent[];
    const covered = events.filter((x) => x.publication);
    expect(covered.length).toBeGreaterThan(0);
    for (const e of covered) expect(eventAnchor(e, "sa")).toBeNull();
    const cards = page.locator(".event-card").filter({ has: page.locator(".withheld-note") });
    await expect(cards).toHaveCount(covered.length);
    for (let i = 0; i < covered.length; i++) expect(await cards.nth(i).getAttribute("id")).toBeNull();
    // A hand-made link carrying the id finds nothing and marks nothing.
    await app.open(`?sys=sa#ev-${covered[0].event_id}`);
    await expect(page.locator(".event-card.targeted")).toHaveCount(0);
  });
});

test.describe("phone width", () => {
  test("a card, its inspector and an empty page fit a phone with nothing off to the side", async ({ app, page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await app.open("?sys=us");
    const card = page.locator(".event-card").first();
    await card.scrollIntoViewIfNeeded();
    await card.locator(".ev-inspector-toggle").click();
    await expect(card.locator(".ev-inspector")).toBeVisible();
    expect(await sideways(page)).toBeLessThanOrEqual(0);
    const box = await card.boundingBox();
    expect(box!.x + box!.width).toBeLessThanOrEqual(390);
    await app.open("?sys=om");
    await expect(page.locator(".empty-lead")).toBeVisible();
    expect(await sideways(page)).toBeLessThanOrEqual(0);
    const badge = page.locator(".phone-caveats").getByRole("button", { name: /^Research preview/ });
    await badge.click();
    await expect(page.locator(".phone-caveats").getByRole("note")).toContainText("not evidence that no disruption occurred");
    expect(await sideways(page)).toBeLessThanOrEqual(0);
  });
});
