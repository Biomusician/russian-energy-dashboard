import { test, expect, readBytes } from "./fixtures";
import { eventAnchor } from "../src/global/evidence";
import { COUNTRY_EVENT_COLUMNS } from "../src/global/recordCsv";
import type { CountryEvent, CountrySystem } from "../src/global/manifest";

/**
 * Record filters and the CSV export on a country page, as a reader meets them (iteration 22).
 * Every expectation is read from the payload the page loaded. The filter model and the export are
 * unit-tested in src/global/recordFilters.test.ts and recordCsv.test.ts; this is the shipped page:
 * the address, a reload, Back, a real downloaded file's bytes, and the phone sheet.
 */

type Page = import("@playwright/test").Page;
const payload = (page: Page, id: string, file: string) =>
  page.evaluate(([i, f]) => fetch(`/data/systems/${i}/${f}`).then((r) => r.json()), [id, file]);
const sideways = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
const BOM = "﻿";

/** A minimal RFC 4180 reader: the file is read the way a spreadsheet reads it. */
function parseCsv(text: string): string[][] {
  const s = text.startsWith(BOM) ? text.slice(1) : text;
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (quoted) {
      if (ch === '"' && s[i + 1] === '"') { cell += '"'; i++; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\r" && s[i + 1] === "\n") { row.push(cell); rows.push(row); row = []; cell = ""; i++; }
    else cell += ch;
  }
  if (cell !== "" || row.length > 0) { row.push(cell); rows.push(row); }
  return rows;
}

async function chooseCause(page: Page, label: string) {
  const bar = page.locator(".record-filters");
  await bar.getByRole("button", { name: /^Cause/ }).click();
  await bar.getByRole("group", { name: "Cause filter" }).getByLabel(label).check();
}

test.describe("country page filters", () => {
  test("a filter narrows the list, says what it hides, and lives in the address through reload and Back", async ({ app, page }) => {
    await app.open("?sys=us");
    const events = (await payload(page, "us", "events.json")).events as CountryEvent[];
    const sys = (await payload(page, "us", "system.json")) as CountrySystem;
    const technical = events.filter((e) => e.cause === "technical");
    expect(technical.length).toBeGreaterThan(0);
    expect(technical.length).toBeLessThan(events.length);
    const count = page.locator(".rf-count");
    await expect(count).toHaveText(`Showing ${events.length} of ${events.length} published records.`);
    await expect(page.getByRole("button", { name: "Clear filters" })).toBeDisabled();

    await chooseCause(page, new RegExp(`^${sys.taxonomy.causes.technical}`));
    await expect(count).toContainText(`Showing ${technical.length} of ${events.length} published records.`);
    await expect(count).toContainText(`The filters hide ${events.length - technical.length}.`);
    await expect(count).toContainText(`Filters on: Cause: ${sys.taxonomy.causes.technical}.`);
    await expect(page.locator(".event-card")).toHaveCount(technical.length);
    const ids = await page.locator(".event-card").evaluateAll((els) => els.map((e) => e.id));
    expect(new Set(ids)).toEqual(new Set(technical.map((e) => eventAnchor(e, "us"))));
    expect(new URL(page.url()).search).toBe("?sys=us&f.cause=technical");

    // Reload: the address is the state.
    await page.reload();
    await app.mapIdle();
    await expect(count).toContainText(`Showing ${technical.length} of ${events.length} published records.`);
    await expect(page.locator(".event-card")).toHaveCount(technical.length);
    await expect(page.locator(".record-filters").getByRole("button", { name: /^Cause/ })).toContainText(sys.taxonomy.causes.technical);

    // Leave the page and come Back: the filtered list, not the full one.
    await page.locator(".global-nav .product-home").click();
    await expect(page.locator(".event-card")).toHaveCount(0);
    await page.goBack();
    await expect(page.locator(".rf-count")).toContainText(`Showing ${technical.length} of ${events.length} published records.`);
    await expect(page.locator(".event-card")).toHaveCount(technical.length);
    expect(new URL(page.url()).search).toBe("?sys=us&f.cause=technical");

    // The region select keeps working beside the filters, and both are in the address.
    await page.getByLabel(/Choose a state/i).selectOption({ label: "Texas" });
    await expect(page.locator(".events-panel h2").first()).toHaveText("Texas");
    const p = new URL(page.url()).searchParams;
    expect(p.get("sys")).toBe("us");
    expect(p.get("r")).toBe("US-TX");
    expect(p.get("f.cause")).toBe("technical");
    const texas = events.filter((e) => e.region_code === "US-TX" || (e.geography_precision !== "admin1" && e.regions_affected.includes("US-TX")));
    await expect(page.locator(".rf-count")).toContainText(
      `Showing ${texas.filter((e) => e.cause === "technical").length} of ${texas.length} published records for Texas.`);
    await page.getByRole("button", { name: "Show all" }).click();

    await page.getByRole("button", { name: "Clear filters" }).click();
    await expect(page.locator(".rf-count")).toHaveText(`Showing ${events.length} of ${events.length} published records.`);
    await expect(page.locator(".event-card")).toHaveCount(events.length);
    expect(new URL(page.url()).search).toBe("?sys=us");
    expect(app.errors).toEqual([]);
  });

  test("a date preset and a second filter combine, and the option counts are this list's own", async ({ app, page }) => {
    await app.open("?sys=us&f.date=2023-01-01..2023-12-31");
    const events = (await payload(page, "us", "events.json")).events as CountryEvent[];
    const in2023 = events.filter((e) => e.date <= "2023-12-31" && (e.date_end || e.date) >= "2023-01-01");
    expect(in2023.length).toBeGreaterThan(0);
    await expect(page.locator(".rf-count")).toContainText(`Showing ${in2023.length} of ${events.length} published records.`);
    await expect(page.locator(".rf-count")).toContainText("Date: 2023-01-01 to 2023-12-31");
    // The number beside a cause is how many of the records the date filter admits carry it.
    const bar = page.locator(".record-filters");
    await bar.getByRole("button", { name: /^Cause/ }).click();
    const rows = await bar.locator(".rf-panel .rf-options li").evaluateAll((els) => els.map((li) => ({
      label: li.querySelector(".rf-option-label")?.textContent ?? "", n: Number(li.querySelector(".rf-n")?.firstChild?.textContent ?? "-1"),
    })));
    const sys = (await payload(page, "us", "system.json")) as CountrySystem;
    for (const r of rows) {
      const key = Object.keys(sys.taxonomy.causes).find((k) => sys.taxonomy.causes[k] === r.label)!;
      expect(r.n, r.label).toBe(in2023.filter((e) => e.cause === key).length);
    }
    expect(rows.reduce((a, r) => a + r.n, 0)).toBe(in2023.length);
    await page.keyboard.press("Escape");
    await expect(bar.locator(".rf-panel")).toHaveCount(0);
    expect(app.errors).toEqual([]);
  });

  test("a menu opens and closes from the keyboard, and Escape returns focus to its button", async ({ app, page }) => {
    await app.open("?sys=us");
    const toggle = page.locator(".record-filters").getByRole("button", { name: /^Date/ });
    await toggle.focus();
    await page.keyboard.press("Enter");
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await page.keyboard.press("Tab");
    await expect(page.getByRole("radio", { name: "Any date" })).toBeFocused();
    await page.keyboard.press("ArrowDown");
    await expect(page.getByRole("radio", { name: "Last 30 days" })).toBeChecked();
    expect(new URL(page.url()).searchParams.get("f.date")).toBe("30d");
    await page.keyboard.press("Escape");
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(toggle).toBeFocused();
    await expect(toggle).toContainText("Last 30 days");
    expect(app.errors).toEqual([]);
  });

  test("a link to a record the filter hides clears that filter and says so", async ({ app, page }) => {
    await app.open("?sys=us");
    const events = (await payload(page, "us", "events.json")).events as CountryEvent[];
    const hidden = events.find((e) => e.cause !== "technical")!;
    const anchor = eventAnchor(hidden, "us")!;
    await page.goto(`/?sys=us&f.cause=technical&f.date=2022#${anchor}`);
    await app.mapIdle();
    const card = page.locator(`#${anchor}`);
    await expect(card).toBeVisible();
    await expect(card).toHaveClass(/targeted/);
    await expect(page.locator(".rf-note")).toContainText("The linked record was hidden by the Cause filter, so that filter was cleared to show it.");
    // Only the filter that hid it: the date filter, which admits it, stays on and in the address.
    const p = new URL(page.url());
    expect(p.searchParams.get("f.cause")).toBeNull();
    expect(p.searchParams.get("f.date")).toBe("2022");
    expect(p.hash).toBe(`#${anchor}`);
    expect(app.errors).toEqual([]);
  });

  test("a link naming a filter or a value this page does not have is told, not obeyed silently", async ({ app, page }) => {
    await app.open("?sys=us&f.cause=technical,sabotage&f.sector=telecom");
    const events = (await payload(page, "us", "events.json")).events as CountryEvent[];
    const notes = page.locator(".rf-note");
    await expect(notes).toHaveCount(2);
    await expect(notes.filter({ hasText: "sabotage" })).toContainText("Cause filter names a value this list does not have");
    await expect(notes.filter({ hasText: "sector" })).toContainText("a filter this page does not have");
    await expect(page.locator(".rf-count")).toContainText(`Showing ${events.filter((e) => e.cause === "technical").length} of ${events.length}`);
    expect(app.errors).toEqual([]);
  });

  test("the old event links keep working: a region link and a record anchor with no filter", async ({ app, page }) => {
    await app.open("?sys=us&r=US-TX");
    await expect(page.locator(".events-panel h2").first()).toHaveText("Texas");
    const events = (await payload(page, "us", "events.json")).events as CountryEvent[];
    const anchor = eventAnchor(events[3], "us")!;
    await page.goto(`/?sys=us#${anchor}`);
    await app.mapIdle();
    await expect(page.locator(`#${anchor}`)).toHaveClass(/targeted/);
    await expect(page.locator(".rf-note")).toHaveCount(0);
    expect(app.errors).toEqual([]);
  });
});

test.describe("CSV export", () => {
  test("the downloaded file is the filtered list: BOM, header, one row per shown record", async ({ app, page }) => {
    await app.open("?sys=us&f.cause=technical");
    const events = (await payload(page, "us", "events.json")).events as CountryEvent[];
    const sys = (await payload(page, "us", "system.json")) as CountrySystem;
    const technical = events.filter((e) => e.cause === "technical");
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: /^Download CSV/ }).click(),
    ]);
    expect(download.suggestedFilename()).toBe(`edm-us-events-${sys.as_of}.csv`);
    const bytes = readBytes((await download.path())!);
    expect([...bytes.subarray(0, 3)]).toEqual([0xef, 0xbb, 0xbf]);
    const text = bytes.toString("utf-8");
    expect(text.endsWith("\r\n")).toBe(true);
    const [head, ...rows] = parseCsv(text);
    expect(head).toEqual([...COUNTRY_EVENT_COLUMNS]);
    expect(rows).toHaveLength(technical.length);
    const col = (name: string) => head.indexOf(name);
    expect(new Set(rows.map((r) => r[col("record_id")]))).toEqual(new Set(technical.map((e) => e.event_id)));
    for (const r of rows) {
      expect(r).toHaveLength(head.length);
      expect(r[col("cause")]).toBe("technical");
      expect(r[col("system_id")]).toBe("us");
    }
    // Nothing the page does not publish: no coordinate-like column, no review process text.
    expect(text).not.toMatch(/latitude|longitude|"lat"|"lon"/i);
    expect(text).not.toContain(events[0].review.process.slice(0, 40));
    await expect(page.getByText(`Saved edm-us-events-${sys.as_of}.csv: ${technical.length} of ${events.length} published records.`)).toBeVisible();

    const [readme] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: /^About this file/ }).click(),
    ]);
    expect(readme.suggestedFilename()).toBe(`edm-us-events-${sys.as_of}-README.txt`);
    const about = readBytes((await readme.path())!).toString("utf-8");
    for (const want of [`Records in this file: ${technical.length} of ${events.length}`, `Cause: ${sys.taxonomy.causes.technical}`,
      "not a census", "not comparable across countries", `Site build date: ${sys.as_of}`, "us (United States)"]) {
      expect(about).toContain(want);
    }
    expect(app.errors).toEqual([]);
  });

  test("records under attack-campaign safeguards export no place, facility, operator or status", async ({ app, page }) => {
    await app.open("?sys=sa");
    const events = (await payload(page, "sa", "events.json")).events as CountryEvent[];
    const covered = events.filter((e) => e.publication);
    expect(covered.length).toBeGreaterThan(0);
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: /^Download CSV/ }).click(),
    ]);
    const text = readBytes((await download.path())!).toString("utf-8");
    const [head, ...rows] = parseCsv(text);
    expect(rows).toHaveLength(events.length);
    for (const e of covered) {
      for (const name of [e.facility_name, e.facility_name_local, e.operator, e.region_name, e.region_code]) {
        if (name) expect(text, `the file names ${name}`).not.toContain(name);
      }
    }
    const col = (name: string) => head.indexOf(name);
    for (const r of rows) {
      for (const c of ["region_code", "region_name", "facility", "operator", "source_headlines", "recovery_research_status", "recovery_kind", "recovery_date"]) {
        expect(r[col(c)], c).toBe("");
      }
      expect(r[col("publication_note")]).toContain("attack-campaign safeguards");
      // A month-precision record keeps its month: no day is invented for the file.
      expect(r[col("date")]).toMatch(/^\d{4}-\d{2}(-\d{2})?$/);
    }
    expect(app.errors).toEqual([]);
  });
});

test.describe("filters on a phone", () => {
  for (const width of [390, 430]) {
    test(`at ${width} px one button opens a sheet; Escape closes it and returns focus`, async ({ app, page }) => {
      await page.setViewportSize({ width, height: 844 });
      await app.open("?sys=us");
      const events = (await payload(page, "us", "events.json")).events as CountryEvent[];
      const sys = (await payload(page, "us", "system.json")) as CountrySystem;
      const technical = events.filter((e) => e.cause === "technical");
      const open = page.getByRole("button", { name: /^Filters \(0\)/ });
      await expect(open).toBeVisible();
      await expect(page.locator(".rf-count")).toHaveText(`Showing ${events.length} of ${events.length} published records.`);
      // The row of menus is the wide layout's: on a phone there is one button.
      await expect(page.locator(".rf-toggle")).toHaveCount(0);
      expect(await sideways(page)).toBeLessThanOrEqual(1);

      await open.click();
      const sheet = page.getByRole("dialog", { name: "Filter the published records" });
      await expect(sheet).toBeVisible();
      await expect(sheet).toBeFocused();
      await sheet.getByLabel(new RegExp(`^${sys.taxonomy.causes.technical}`)).check();
      await expect(sheet.getByRole("status")).toContainText(`Showing ${technical.length} of ${events.length} published records.`);
      await expect(sheet.getByRole("status")).toContainText(`The filters hide ${events.length - technical.length}.`);
      // Every control in the sheet is a finger-sized target.
      const small = await sheet.locator(".rf-options label, button").evaluateAll((els) => els
        .map((e) => e.getBoundingClientRect()).filter((r) => r.height > 0 && r.height < 43.5).length);
      expect(small).toBe(0);
      const box = await sheet.boundingBox();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(width + 1);

      await page.keyboard.press("Escape");
      await expect(sheet).toHaveCount(0);
      const reopened = page.getByRole("button", { name: /^Filters \(1\)/ });
      await expect(reopened).toBeFocused();
      await expect(page.locator(".rf-count")).toContainText(`The filters hide ${events.length - technical.length}.`);
      await expect(page.locator(".event-card")).toHaveCount(technical.length);
      expect(new URL(page.url()).searchParams.get("f.cause")).toBe("technical");
      expect(await sideways(page)).toBeLessThanOrEqual(1);

      // The export controls are reachable on a phone too.
      await expect(page.getByRole("button", { name: /^Download CSV/ })).toBeVisible();
      await expect(page.getByRole("button", { name: /^About this file/ })).toBeVisible();
      expect(app.errors).toEqual([]);
    });
  }
});
