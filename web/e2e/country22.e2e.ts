import { test, expect, pixelStats, readBytes } from "./fixtures";
import { eventAnchor } from "../src/global/evidence";
import { TAB_LABEL, TAB_ORDER } from "../src/global/countryTabs";
import { OVERVIEW_TITLE, NO_RECORD_IS_NOT_NO_DISRUPTION } from "../src/global/countryOverview";
import { IMPACT_COLUMNS } from "../src/global/recordCsv";
import type { CountryEvent } from "../src/global/manifest";

/**
 * Country pages, iteration 22, as a reader meets them: the overview on the first screen of a
 * country with no published record, the two new tabs, a tab in the address, the tab row on a
 * phone, the keyboard path, evidence confidence on an event card, and the exports read back.
 *
 * Every expected value is read from the payload the page loaded. Run against a build that serves
 * the impact artifacts (`python -m pipeline.global_impacts --fixture` while developing).
 */

type Page = import("@playwright/test").Page;
const json = (page: Page, path: string) => page.evaluate((p) => fetch(`/data/${p}`).then((r) => r.json()), path);
const sideways = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
const tabButton = (page: Page, tab: string) => page.locator(`.country-side .tabs button[data-tab="${tab}"]`);
const overviewLink = (page: Page, tab: string) => page.locator(`.country-overview a[data-tab="${tab}"]`);

interface Impact { impact_id: string; system_id: string | null; record_kind: string; countries?: { system_id: string | null }[] | null }
async function impactsOf(page: Page, id: string): Promise<{ records: Impact[]; attempts: Impact[] }> {
  const p = await json(page, "global/impacts.json");
  const mine = (r: Impact) => r.system_id === id || (r.countries ?? []).some((c) => c.system_id === id);
  return { records: (p.records as Impact[]).filter(mine), attempts: (p.attempts as Impact[]).filter(mine) };
}

/** A country with no published record that is in the regional group: the page the task is about. */
async function emptyGulfSystem(page: Page): Promise<{ id: string; name: string }> {
  const m = await json(page, "global/manifest.json");
  const group = Object.values(m.groups as Record<string, { slug: string | null; members: string[] }>).find((g) => g.slug === "gulf");
  expect(group, "the manifest has no regional group").toBeTruthy();
  const ir = (m.systems as { id: string; name: string; record_reviewed?: string | null }[]).find((s) => s.id === "ir");
  expect(ir && group!.members.includes("ir")).toBeTruthy();
  return { id: ir!.id, name: ir!.name };
}

/** Data files requested from now on. */
function recordData(page: Page): string[] {
  const seen: string[] = [];
  page.on("request", (r) => {
    const u = new URL(r.url());
    if (u.pathname.includes("/data/")) seen.push(u.pathname.replace(/^.*\/data\//, ""));
  });
  return seen;
}

test.describe("first screen of a country with no published record", () => {
  test("?sys=ir says what is published, what else is here and what is withheld, in that order, above the fold", async ({ app, page }) => {
    await app.open("?sys=ir");
    const sys = await json(page, "systems/ir/system.json");
    test.skip(sys.event_summary.recorded_events > 0, "Iran has published records in this build");
    const { name } = await emptyGulfSystem(page);
    const block = page.locator(".country-overview");
    await expect(block.getByRole("heading", { name: OVERVIEW_TITLE })).toBeVisible();
    const boxes = [];
    for (const h of ["Published here", "Also on this page", "Not published, and why"]) {
      const b = await block.getByRole("heading", { name: h, exact: true }).boundingBox();
      expect(b, h).toBeTruthy();
      boxes.push(b!);
    }
    // Reading order: left to right on a wide screen, each part's heading no higher than the one before.
    expect(boxes[0].x).toBeLessThan(boxes[1].x);
    expect(boxes[1].x).toBeLessThan(boxes[2].x);
    const whole = await block.boundingBox();
    expect(whole!.y + whole!.height, "the overview runs below the first screen").toBeLessThanOrEqual(900);
    await expect(block).toContainText(`No energy-disruption record is published for ${name} yet.`);
    await expect(block).toContainText(NO_RECORD_IS_NOT_NO_DISRUPTION);
    await expect(block).toContainText("the inclusion rule is strict");
    await expect(block).toContainText("attack-campaign safeguards apply");
    await expect(block).toContainText("whether, or how many, records are in review");
    for (const tab of ["impacts", "regional", "context", "research"]) {
      await expect(overviewLink(page, tab)).toHaveText(TAB_LABEL[tab as keyof typeof TAB_LABEL]);
      await expect(overviewLink(page, tab)).toHaveAttribute("href", `?sys=ir&tab=${tab}`);
    }
    // The page with no record asks the impact corpus at once, and the line says what it holds.
    const mine = await impactsOf(page, "ir");
    const line = block.locator("li").filter({ has: page.locator('a[data-tab="impacts"]') });
    if (mine.records.length > 0) await expect(line).toContainText(`${mine.records.length} reviewed impact record`);
    else await expect(line).toContainText("no impact record yet");
    await expect(line).toContainText(/separate, non-scored corpus|describes that corpus/);
    // The headline still says no record: the impact corpus did not fill it.
    await expect(page.locator(".country-ribbon")).toContainText("No qualifying records in the current reviewed corpus");
    const body = await page.locator(".global-page").innerText();
    expect(body).not.toMatch(/\d+ (of them )?(are )?(not shown|held|under review|in review)/i);
    expect(app.errors).toEqual([]);
  });

  test("a country with records states its own count, and waits to read the impact corpus", async ({ app, page }) => {
    const seen = recordData(page);
    await app.open("?sys=us");
    await page.waitForLoadState("networkidle");
    const sys = await json(page, "systems/us/system.json");
    const block = page.locator(".country-overview");
    await expect(block).toContainText(`${sys.event_summary.recorded_events} reviewed energy-disruption records are published for the United States.`);
    await expect(block).not.toContainText(NO_RECORD_IS_NOT_NO_DISRUPTION);
    await expect(overviewLink(page, "regional")).toHaveCount(0);
    await expect(tabButton(page, "regional")).toHaveCount(0);
    // Not read yet, and said as such: no count is claimed before the file is in.
    const before = seen.filter((p) => p === "global/impacts.json").length;
    expect(before, "the impact corpus was fetched before its tab was opened").toBe(0);
    await expect(block.locator("li").first()).toContainText("reviewed impact records, in a separate, non-scored corpus");
    await overviewLink(page, "impacts").click();
    await expect(tabButton(page, "impacts")).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator(".country-impacts")).toContainText("separate, non-scored corpus");
    await expect(page.locator(".country-impacts [role=status]").filter({ hasText: "Loading" })).toHaveCount(0);
    expect(seen.filter((p) => p === "global/impacts.json")).toHaveLength(1);
    // The header count is the country's own, before and after.
    await expect(page.locator(".country-ribbon")).toContainText(`${sys.event_summary.recorded_events} qualifying events recorded`);
  });
});

test.describe("the new tabs", () => {
  test("Impact records (not scored) lists this country's impact records, says what the list is and why it differs, and exports it", async ({ app, page }) => {
    await app.open("?sys=ir");
    const mine = await impactsOf(page, "ir");
    await overviewLink(page, "impacts").click();
    await expect(tabButton(page, "impacts")).toHaveAttribute("aria-pressed", "true");
    await expect(page).toHaveURL(/[?&]tab=impacts(&|$)/);
    // The reader is moved to the tab's panel.
    await expect(page.locator("#country-details")).toBeFocused();
    const panel = page.locator(".country-impacts");
    await expect(panel.getByRole("heading", { name: TAB_LABEL.impacts, level: 2 })).toBeVisible();
    await expect(panel.locator(".impacts-what")).toContainText("not part of this country's published energy-disruption record and enter no count or index");
    expect(TAB_LABEL.impacts).toBe("Impact records (not scored)");
    await expect(panel.locator(".impacts-inclusion")).toContainText("so an event can appear here and not there. Impact records never enter a score.");
    await expect(panel.locator(".impact-list").first().locator(".impact-card")).toHaveCount(mine.records.length);
    if (mine.records.length === 0) {
      await expect(panel).toContainText("That describes this corpus, not Iran.");
      await expect(panel).toContainText(/The impact research last ran on|No impact research pass has been logged yet/);
      return;
    }
    await expect(panel).toContainText(`Showing ${mine.records.length} of ${mine.records.length} reviewed impact records for Iran`);
    await expect(panel.locator(".impact-card .conf-chip").first()).toContainText("Evidence confidence:");
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      panel.getByRole("button", { name: /^Download CSV of the/ }).click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/^edm-ir-impacts-\d{4}-\d{2}-\d{2}\.csv$/);
    const csv = readBytes((await download.path())!).toString("utf-8");
    expect(csv.charCodeAt(0)).toBe(0xfeff);
    const lines = csv.slice(1).trim().split("\r\n");
    expect(lines[0]).toBe(IMPACT_COLUMNS.join(","));
    expect(lines.filter((l) => l.startsWith("imp-")).length).toBe(mine.records.length);
    expect(app.errors).toEqual([]);
  });

  test("Gulf & Hormuz context shows the newest statement of each kind, says it is regional, and links to the full timeline", async ({ app, page }) => {
    await app.open("?sys=ir");
    const ctx = await json(page, "global/regional_context.json");
    const latest = (ctx.entries as { is_latest_of_type: boolean }[]).filter((e) => e.is_latest_of_type).length;
    await overviewLink(page, "regional").click();
    await expect(tabButton(page, "regional")).toHaveAttribute("aria-pressed", "true");
    await expect(page).toHaveURL(/[?&]tab=regional(&|$)/);
    const panel = page.locator(".country-regional");
    await expect(panel.locator(".regional-note")).toContainText("says nothing about any facility in Iran");
    await expect(panel.locator(".regional-note")).toContainText("enters no count or index");
    await expect(panel.locator(".ctx-entry")).toHaveCount(latest);
    await expect(panel.locator(".ctx-historical")).toHaveCount(0);
    await expect(panel.locator(".ctx-caveat")).toContainText("No vessels, routes or bypass capacity are collected");
    const link = panel.getByRole("link", { name: /^Full timeline on the / });
    await expect(link).toHaveAttribute("href", "?group=gulf");
    await link.click();
    await expect(page).toHaveURL(/\?group=gulf$/);
    await app.mapIdle();
    expect(app.errors).toEqual([]);
  });

  test("a system outside the regional group has no such tab, and a link to it opens the country's own record", async ({ app, page }) => {
    await app.open("?sys=us&tab=regional");
    await expect(tabButton(page, "regional")).toHaveCount(0);
    await expect(tabButton(page, "events")).toHaveAttribute("aria-pressed", "true");
    await expect(page).toHaveURL(/\?sys=us$/);
    await expect(page.locator(".event-card").first()).toBeVisible();
  });
});

test.describe("a tab in the address", () => {
  test("a deep link opens its tab, survives a reload, and the default tab is never written", async ({ app, page }) => {
    await app.open("?sys=ir&tab=impacts");
    await expect(tabButton(page, "impacts")).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator(".country-impacts")).toBeVisible();
    await page.reload();
    await app.mapIdle();
    await expect(tabButton(page, "impacts")).toHaveAttribute("aria-pressed", "true");
    await expect(page).toHaveURL(/\?sys=ir&tab=impacts$/);
    await tabButton(page, "research").click();
    await expect(page).toHaveURL(/\?sys=ir&tab=research$/);
    await expect(page.getByRole("heading", { name: "Research coverage", level: 2 })).toBeVisible();
    await tabButton(page, "events").click();
    await expect(page).toHaveURL(/\?sys=ir$/);
    // Every tab of this system opens from its own address.
    for (const t of TAB_ORDER) {
      await app.open(`?sys=ir&tab=${t}`);
      await expect(tabButton(page, t), t).toHaveAttribute("aria-pressed", "true");
      await expect(page.locator(".country-side [role=alert]")).toHaveCount(0);
    }
    expect(app.errors).toEqual([]);
  });

  test("the tab and the event filters share the address without disturbing each other", async ({ app, page }) => {
    await app.open("?sys=us&f.date=2022&tab=sources");
    await expect(tabButton(page, "sources")).toHaveAttribute("aria-pressed", "true");
    await expect(page).toHaveURL(/\?sys=us&f\.date=2022&tab=sources$/);
    await tabButton(page, "events").click();
    await expect(page).toHaveURL(/\?sys=us&f\.date=2022$/);
    await expect(page.locator(".record-filters")).toContainText("Filters on: Date");
    // Choosing a region is a question about the country's own record: it opens that tab.
    await tabButton(page, "method").click();
    await page.getByRole("combobox", { name: /^Choose a / }).selectOption({ index: 1 });
    await expect(tabButton(page, "events")).toHaveAttribute("aria-pressed", "true");
    await expect(page).toHaveURL(/\?sys=us&r=[^&]+&f\.date=2022$/);
  });
});

test.describe("phones", () => {
  for (const [w, h] of [[390, 844], [430, 932]] as const) {
    test(`?sys=ir at ${w}x${h}: the overview and the start of the map are on the first screen, and nothing scrolls sideways`, async ({ app, page }) => {
      await page.setViewportSize({ width: w, height: h });
      await app.open("?sys=ir");
      await page.waitForLoadState("networkidle");
      expect(await sideways(page), "horizontal scroll").toBeLessThanOrEqual(1);
      const block = await page.locator(".country-overview").boundingBox();
      expect(block!.y + block!.height, "the overview runs below the first screen").toBeLessThanOrEqual(h);
      for (const part of ["Published here", "Also on this page", "Not published, and why"]) {
        const b = await page.locator(".country-overview").getByRole("heading", { name: part, exact: true }).boundingBox();
        expect(b!.y + b!.height, `${part} is below the first screen`).toBeLessThanOrEqual(h);
      }
      const title = await page.getByRole("heading", { level: 1 }).boundingBox();
      const map = await page.locator("[data-map-state]").boundingBox();
      expect(title!.y).toBeLessThan(block!.y);
      expect(block!.y, "the overview comes before the map").toBeLessThan(map!.y);
      expect(map!.y, "the map starts below the first screen").toBeLessThan(h - 150);
    });

    test(`the tab row at ${w}x${h} is one row that scrolls, and every tab can be reached and opened`, async ({ app, page }) => {
      await page.setViewportSize({ width: w, height: h });
      await app.open("?sys=ir");
      const row = page.locator(".country-side .tabs");
      const tabs = row.locator("button");
      await expect(tabs).toHaveCount(TAB_ORDER.length);
      const m = await row.evaluate((el) => ({ h: el.getBoundingClientRect().height, scroll: el.scrollWidth, client: el.clientWidth,
        tops: [...el.querySelectorAll("button")].map((b) => Math.round(b.getBoundingClientRect().top)) }));
      expect(new Set(m.tops).size, "the tabs wrap onto more than one row").toBe(1);
      expect(m.h).toBeLessThan(70);
      expect(m.scroll, "the row does not scroll, so some tabs are cut off").toBeGreaterThan(m.client);
      for (const t of TAB_ORDER) {
        await tabButton(page, t).click();
        await expect(tabButton(page, t)).toHaveAttribute("aria-pressed", "true");
        const visible = await tabButton(page, t).evaluate((b) => {
          const r = b.getBoundingClientRect(); const p = b.parentElement!.getBoundingClientRect();
          return r.left >= p.left - 1 && r.right <= p.right + 1 && r.height >= 43.5;
        });
        expect(visible, `${t}: the open tab is outside the row's view or too small to tap`).toBe(true);
        expect(await sideways(page), `${t}: the page scrolls sideways`).toBeLessThanOrEqual(1);
      }
      // A deep link to the last tab opens with that tab in view.
      const last = TAB_ORDER[TAB_ORDER.length - 1];
      await app.open(`?sys=ir&tab=${last}`);
      const inView = await tabButton(page, last).evaluate((b) => {
        const r = b.getBoundingClientRect(); const p = b.parentElement!.getBoundingClientRect();
        return r.left >= p.left - 1 && r.right <= p.right + 1;
      });
      expect(inView, "the linked tab opens out of sight").toBe(true);
    });

    test(`an overview link at ${w}x${h} opens its tab and brings it onto the screen`, async ({ app, page }) => {
      await page.setViewportSize({ width: w, height: h });
      await app.open("?sys=ir");
      await overviewLink(page, "impacts").click();
      await expect(tabButton(page, "impacts")).toHaveAttribute("aria-pressed", "true");
      const top = await page.locator("#country-details").evaluate((el) => el.getBoundingClientRect().top);
      expect(top).toBeGreaterThanOrEqual(-1);
      expect(top).toBeLessThan(h / 2);
      await expect(page.locator(".country-impacts .impacts-what")).toBeVisible();
      expect(await sideways(page)).toBeLessThanOrEqual(1);
    });
  }
});

test.describe("keyboard", () => {
  test("from the overview to a tab, into a record's confidence and its sources, and back, without a mouse", async ({ app, page }) => {
    await app.open("?sys=ir");
    const mine = await impactsOf(page, "ir");
    await overviewLink(page, "impacts").focus();
    await page.keyboard.press("Enter");
    await expect(tabButton(page, "impacts")).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator("#country-details")).toBeFocused();
    // The next stop is the tab row, in order.
    await page.keyboard.press("Tab");
    await expect(tabButton(page, TAB_ORDER[0])).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(tabButton(page, "impacts")).toBeFocused();
    test.skip(mine.records.length === 0, "no impact record for Iran in this build");
    const card = page.locator(".country-impacts .impact-card").first();
    const why = card.locator(".conf-why");
    await why.focus();
    await page.keyboard.press("Enter");
    await expect(why).toHaveAttribute("aria-expanded", "true");
    await expect(card.locator(".conf-panel")).toContainText("not a probability");
    await page.keyboard.press("Escape");
    await expect(why).toHaveAttribute("aria-expanded", "false");
    await expect(why).toBeFocused();
    const sources = card.locator(".ev-inspector-toggle");
    await sources.focus();
    await page.keyboard.press("Space");
    await expect(sources).toHaveAttribute("aria-expanded", "true");
    await page.keyboard.press("Escape");
    await expect(sources).toHaveAttribute("aria-expanded", "false");
    await expect(sources).toBeFocused();
    // A tab button opens with the keyboard too.
    await tabButton(page, "regional").focus();
    await page.keyboard.press("Enter");
    await expect(page.locator(".country-regional")).toBeVisible();
    expect(app.errors).toEqual([]);
  });
});

test.describe("evidence confidence on a published country event", () => {
  const CONF = {
    category: "HIGH", label: "High", score: 84, disputed: false,
    components: {
      directness: { tier: "direct", points: 40 }, origins: { count: 2, points: 16, basis: "publishers" }, effect: { specificity: "described", points: 8 },
      opened: { points: 10 }, contemporaneous: { points: 10 },
    },
    reasons: ["Direct authoritative statement", "2 publishers cited; their origins are not yet reviewed"],
  };

  test("a record that carries it shows the chip and the inspector's breakdown; one that does not shows neither", async ({ app, page }) => {
    // The served payload decides nothing here: the first record is given a value and the second
    // has it removed, so the test holds on a build made before or after the field existed.
    // A third is served as not assessed (category null, with a reason).
    const REASON = "Cited through a discovery aid only; a primary source is not yet attached.";
    let ids: [string, string, string] | null = null;
    await page.route("**/data/systems/ca/events.json", async (route) => {
      const res = await route.fetch();
      const body = await res.json();
      const evs = body.events as (CountryEvent & { evidence_confidence?: unknown })[];
      const open = evs.filter((e) => !e.publication);
      open[0].evidence_confidence = CONF;
      delete open[1].evidence_confidence;
      open[2].evidence_confidence = { category: null, reason: REASON };
      ids = [eventAnchor(open[0], "ca")!, eventAnchor(open[1], "ca")!, eventAnchor(open[2], "ca")!];
      await route.fulfill({ response: res, json: body });
    });
    await app.open("?sys=ca");
    expect(ids).toBeTruthy();
    const withIt = page.locator(`#${ids![0]}`);
    const without = page.locator(`#${ids![1]}`);
    const notAssessed = page.locator(`#${ids![2]}`);
    await expect(withIt.locator(".conf-chip")).toHaveText("Evidence confidence: High");
    await expect(without.locator(".conf-chip")).toHaveCount(0);
    await expect(without).not.toContainText("Evidence confidence");

    // Not assessed is said in those words, with its reason, and never as a category.
    await expect(notAssessed.locator(".conf-chip")).toHaveText("Evidence confidence: Not assessed");
    await expect(notAssessed.locator(".conf")).toContainText(REASON);
    await expect(notAssessed.locator(".conf")).not.toContainText(/Preliminary|Limited|Moderate|High|Disputed/);
    await notAssessed.locator(".ev-inspector-toggle").click();
    await expect(notAssessed.locator(".ev-inspector")).toContainText("Not assessed is not a low category");
    await notAssessed.locator(".ev-inspector-close").click();
    // Its own choice in the filter, and its own line in the country's summary.
    await page.goto("/?sys=ca&f.conf=NOT_ASSESSED");
    await app.mapIdle();
    await expect(page.locator(".record-filters")).toContainText("Filters on: Evidence confidence: Not assessed");
    await expect(page.locator(".event-card .conf-chip")).toHaveText(["Evidence confidence: Not assessed"]);
    await tabButton(page, "sources").click();
    const summary = page.locator(".confidence-summary");
    await expect(summary).toContainText("Not assessed: 1");
    await expect(summary).toContainText("not comparable across countries");
    await tabButton(page, "events").click();
    await page.getByRole("button", { name: "Clear filters" }).click();
    await expect(withIt).toBeVisible();

    // The chip's own disclosure, from the keyboard.
    const why = withIt.locator(".conf-why");
    await why.focus();
    await page.keyboard.press("Enter");
    for (const r of CONF.reasons) await expect(withIt.locator(".conf-panel")).toContainText(r);
    await page.keyboard.press("Escape");
    await expect(withIt.locator(".conf-panel")).toHaveCount(0);

    // The Evidence Inspector: the five components and the sentence about what confidence is not.
    await withIt.locator(".ev-inspector-toggle").click();
    const panel = withIt.locator(".ev-inspector");
    await expect(panel.getByRole("heading", { name: "How strong the evidence is", exact: true })).toBeVisible();
    const method = await json(page, "global/evidence_confidence.json");
    for (const c of method.components as { label: string }[]) await expect(panel).toContainText(c.label);
    await expect(panel).toContainText(method.statement as string);
    for (const r of CONF.reasons) await expect(panel).toContainText(r);
    await without.locator(".ev-inspector-toggle").click();
    await expect(without.locator(".ev-inspector")).toBeVisible();
    await expect(without.locator(".ev-inspector")).not.toContainText("How strong the evidence is");
    expect(app.errors).toEqual([]);
  });
});

test.describe("the image export", () => {
  test("from the impact tab the PNG carries the summary panel; from the record tab it does not", async ({ app, page }) => {
    await app.open("?sys=ir");
    const save = async () => {
      const [download] = await Promise.all([page.waitForEvent("download"), app.button("Download PNG").click()]);
      return { name: download.suggestedFilename(), png: readBytes((await download.path())!) };
    };
    const plain = await save();
    expect(plain.name).toMatch(/^energy-disruption-ir-\d{4}-\d{2}-\d{2}\.png$/);
    await tabButton(page, "impacts").click();
    await expect(page.locator(".country-impacts .impacts-what")).toBeVisible();
    await expect(page.locator(".country-impacts [role=status]").filter({ hasText: "Loading" })).toHaveCount(0);
    const withSummary = await save();
    expect(withSummary.name).toMatch(/^energy-disruption-ir-\d{4}-\d{2}-\d{2}-impacts\.png$/);
    for (const f of [plain, withSummary]) {
      expect(f.png.subarray(1, 4).toString("ascii")).toBe("PNG");
      const whole = await pixelStats(page, f.png);
      expect([whole.width, whole.height]).toEqual([1600, 900]);
      expect(whole.distinct).toBeGreaterThan(20);
    }
    // The summary panel's own area (left, under the title band): light text on a dark band in one
    // image, bare map background in the other.
    const region: [number, number, number, number] = [40, 116, 560, 150];
    const a = await pixelStats(page, plain.png, region);
    const b = await pixelStats(page, withSummary.png, region);
    expect(b.spread, "no text was drawn where the impact summary belongs").toBeGreaterThan(100);
    expect(b.spread).toBeGreaterThan(a.spread + 50);
    // Both still carry the footer band with its caveats (bottom strip is text on a band).
    for (const f of [plain, withSummary]) {
      const foot = await pixelStats(page, f.png, [24, 810, 1000, 80]);
      expect(foot.spread, "the footer caveats are missing").toBeGreaterThan(100);
    }
    // And the country is still drawn, to the right of the panel.
    const map = await pixelStats(page, withSummary.png, [720, 200, 480, 480]);
    expect(map.distinct, "the map area of the impact export is blank").toBeGreaterThan(4);
    expect(app.errors).toEqual([]);
  });
});

// CI's Linux runner draws the page in DejaVu Sans, which is wider than the fonts on a developer's
// machine: the overview wrapped to more lines there and pushed the map below the first screen on
// four Gulf pages. Verdana is as wide, so this reproduces the runner anywhere.
const WIDE_FONT = ":root { --sans: Verdana, 'DejaVu Sans', sans-serif !important; }";

test.describe("phones in a wide fallback font", () => {
  for (const sys of ["ae", "bh", "kw", "om", "ir"]) {
    test(`?sys=${sys} at 390x844 still starts its map on the first screen, overview headings visible`, async ({ app, page }) => {
      const h = 844;
      await page.setViewportSize({ width: 390, height: h });
      await app.open(`?sys=${sys}`);
      await page.addStyleTag({ content: WIDE_FONT });
      await page.waitForLoadState("networkidle");
      expect(await sideways(page), "horizontal scroll").toBeLessThanOrEqual(1);
      for (const part of ["Published here", "Also on this page", "Not published, and why"]) {
        const b = await page.locator(".country-overview").getByRole("heading", { name: part, exact: true }).boundingBox();
        expect(b!.y + b!.height, `${part} is below the first screen`).toBeLessThanOrEqual(h);
      }
      const map = await page.locator("[data-map-state]").boundingBox();
      expect(map!.y, "the map starts below the first screen").toBeLessThan(h - 150);
    });
  }
});
