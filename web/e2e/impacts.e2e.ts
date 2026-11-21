import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test, expect } from "./fixtures";

/**
 * The Impact Atlas, in a real browser (iteration 22).
 *
 * Runs against the pipeline's SYNTHETIC fixture corpus as it is served (e2e/fixtures/impacts22,
 * kept equal to `python -m pipeline.global_impacts --fixture` by a pytest), routed in place of the
 * three impact files. So these tests exercise every state the layer can serve (disputed, claimed,
 * AI-assisted, abstracted, attempt, month-precision, social sources) whatever the published corpus
 * happens to hold, and never depend on a real record.
 *
 * What is fixed: the atlas opens from the site bar and the home page never fetches the corpus;
 * presets are ordinary filters in the address; a link, a reload and Back show the same thing; no
 * count stands beside a country; attempts are apart and uncounted; the inspector says which source
 * supports which claim; the CSV is the shown records; a corrupt corpus costs the atlas and nothing
 * else; it works on a phone.
 */

type Page = import("@playwright/test").Page;
type Rec = {
  impact_id: string; record_kind: string; country_a3: string; countries_a3?: string[] | null; country_name: string;
  domain: string; sector: string; technology: string | null; cause_family: string; cyber_mechanism: string | null;
  summary: string; attribution: { status: string }; ai_involvement: { status: string };
  evidence_confidence: { category: string } | null; sources: { publisher: string; supports: string[] }[];
};

const FIX = new URL("./fixtures/impacts22/global/", import.meta.url);
const body = (name: string) => readFileSync(fileURLToPath(new URL(name, FIX)), "utf-8");
const corpus = JSON.parse(body("impacts.json")) as { records: Rec[]; attempts: Rec[]; attempts_label: string; as_of: string };
const records = corpus.records;
const codes = (r: Rec) => (r.country_a3 === "MULTI" ? r.countries_a3 ?? [] : [r.country_a3]);
const countryCount = new Set(records.flatMap(codes)).size;
const FILES = ["impacts.json", "regional_context.json", "evidence_confidence.json"];

async function serveFixture(page: Page) {
  for (const f of FILES) {
    await page.route(`**/data/global/${f}`, (r) => r.fulfill({ status: 200, contentType: "application/json", body: body(f) }));
  }
}

async function openAtlas(page: Page, query = "") {
  await serveFixture(page);
  await page.goto(`/?view=impacts${query}`);
  await expect(page.getByRole("heading", { name: "Impact atlas", level: 1 })).toBeVisible();
  await expect(page.getByTestId("atlas-summary")).toBeVisible();
}

const cards = (page: Page) => page.locator(".atlas-timeline .impact-card");
const countLine = (page: Page) => page.locator(".record-filters .rf-count").first();
const preset = (page: Page, name: string) => page.getByRole("navigation", { name: "Preset views" }).getByRole("link", { name: new RegExp(`^${name}`) });
const filterParams = (page: Page) => [...new URL(page.url()).searchParams.entries()].filter(([k]) => k.startsWith("f.")).map(([k, v]) => `${k}=${v}`).sort();
const isCyber = (r: Rec) => r.cause_family === "cyber";

const PRESETS: { name: string; params: string[]; match: (r: Rec) => boolean }[] = [
  { name: "Cyber", params: ["f.cause=cyber"], match: isCyber },
  { name: "AI involved", params: ["f.ai=ASSESSED,CLAIMED,CONFIRMED,SUSPECTED"], match: (r) => r.ai_involvement.status !== "NONE_REPORTED" },
  { name: "Attributed cyber", params: ["f.attr=ASSESSED,ATTRIBUTED", "f.cause=cyber"], match: (r) => isCyber(r) && ["ASSESSED", "ATTRIBUTED"].includes(r.attribution.status) },
  { name: "Power-grid cyber", params: ["f.cause=cyber", "f.sector=electricity"], match: (r) => isCyber(r) && r.sector === "electricity" },
  { name: "Renewable cyber", params: ["f.cause=cyber", "f.tech=hydro_generation,solar_generation,wind_generation"],
    match: (r) => isCyber(r) && ["hydro_generation", "solar_generation", "wind_generation"].includes(r.technology ?? "") },
  { name: "Civilian-service cyber", params: ["f.cause=cyber", "f.domain=civilian_service"], match: (r) => isCyber(r) && r.domain === "civilian_service" },
  { name: "IT failure", params: ["f.it=yes"], match: (r) => !isCyber(r) && r.cyber_mechanism === "it_outage_affecting_operations" },
];

test.describe("Impact atlas", () => {
  test("the home page never requests the impact corpus; the site bar opens the atlas, which then does", async ({ app, page }) => {
    const asked: string[] = [];
    page.on("request", (r) => { if (FILES.some((f) => r.url().endsWith(`/data/global/${f}`))) asked.push(r.url()); });
    await serveFixture(page);
    await app.open("");
    await expect(page.getByRole("link", { name: "Impact atlas →" })).toBeVisible();
    expect(asked, "home must load none of the impact files").toEqual([]);

    await page.locator(".global-nav").getByRole("link", { name: "Impact atlas", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Impact atlas", level: 1 })).toBeVisible();
    await expect(page).toHaveURL(/\?view=impacts$/);
    await expect(page.getByTestId("atlas-summary")).toBeVisible();
    expect(asked.filter((u) => u.endsWith("impacts.json"))).toHaveLength(1);
    await expect(page).toHaveTitle(/impact atlas/);
    // Back returns to the overview.
    await page.goBack();
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
  });

  test("the header says what the corpus is, with one count for the corpus and none per country", async ({ app, page }) => {
    await openAtlas(page);
    await expect(page.locator(".atlas-badge")).toHaveText("Expanding corpus, not a census");
    const summary = await page.getByTestId("atlas-summary").innerText();
    expect(summary).toContain(`${records.length} published records in this corpus`);
    expect(summary).toContain(`${countryCount} countries`);
    expect(summary).toMatch(/records from .+ to .+ · research last run /);
    await expect(page.locator(".atlas-bias").first()).toContainText("not rates");
    await expect(countLine(page)).toContainText(`Showing ${records.length} of ${records.length} published records`);
    await expect(cards(page)).toHaveCount(records.length);
    // The country list is names only: no digit beside any country, in the list or in the filter menu.
    const names = await page.locator(".atlas-country-list button").allInnerTexts();
    expect(names.length).toBe(countryCount);
    for (const n of names) expect(n, n).not.toMatch(/\d/);
    expect(names.map((n) => n.split(":")[0].trim())).toEqual([...names.map((n) => n.split(":")[0].trim())].sort((a, b) => a.localeCompare(b)));
    await page.locator(".record-filters").getByRole("button", { name: /^Country/ }).click();
    const panel = page.getByRole("group", { name: "Country filter" });
    await expect(panel.locator("label").first()).toBeVisible();
    await expect(panel.locator(".rf-n")).toHaveCount(0);
    // A category filter keeps its in-list counts.
    await page.keyboard.press("Escape");
    await page.locator(".record-filters").getByRole("button", { name: /^Cause family/ }).click();
    await expect(page.getByRole("group", { name: "Cause family filter" }).locator(".rf-n").first()).toBeVisible();
    await expect(page.locator(".atlas-page")).not.toContainText(/most (attacked|affected|targeted)|ranking of|ranked (first|second|\d)|top \d/i);
  });

  test("the timeline is newest first, grouped by year and month", async ({ app, page }) => {
    await openAtlas(page);
    const years = await page.locator(".atlas-year-head").allInnerTexts();
    expect(years).toEqual([...years].sort().reverse());
    expect(new Set(years).size).toBe(years.length);
    const first = await cards(page).first().innerText();
    expect(first).toContain(records[0].summary);
    const last = await cards(page).last().innerText();
    expect(last).toContain(records[records.length - 1].summary);
  });

  for (const p of PRESETS) {
    test(`preset "${p.name}" is ordinary filters in the address and shows exactly the matching records`, async ({ app, page }) => {
      await openAtlas(page);
      const want = records.filter(p.match);
      await preset(page, p.name).click();
      expect(filterParams(page)).toEqual(p.params);
      await expect(preset(page, p.name)).toHaveAttribute("aria-current", "true");
      await expect(countLine(page)).toContainText(`Showing ${want.length} of ${records.length} published records`);
      if (want.length < records.length) await expect(countLine(page)).toContainText(`The filters hide ${records.length - want.length}`);
      await expect(cards(page)).toHaveCount(want.length);
      const text = want.length > 0 ? await page.locator(".atlas-timeline").innerText() : "";
      for (const r of want) expect(text).toContain(r.summary);
      if (want.length === 0) await expect(page.locator(".atlas-empty")).toContainText("not a census");
      // Activating the chosen preset clears it.
      await preset(page, p.name).click();
      expect(filterParams(page)).toEqual([]);
      await expect(cards(page)).toHaveCount(records.length);
    });
  }

  test("no cyber preset includes an IT failure, and the default hides nothing", async ({ app, page }) => {
    await openAtlas(page);
    await expect(countLine(page)).not.toContainText("The filters hide");
    await preset(page, "Cyber").click();
    await expect(page.locator(".atlas-timeline")).not.toContainText("IT failure:");
    const mechanisms = await page.locator(".atlas-timeline .impact-card").evaluateAll((els) => els.map((e) => (e as HTMLElement).innerText));
    for (const m of mechanisms) expect(m).toContain("Cause: cyber");
  });

  test("a filtered link survives a reload, and Back steps through preset and country choices", async ({ app, page }) => {
    await openAtlas(page, "&f.cause=cyber&f.conf=HIGH");
    const want = records.filter((r) => isCyber(r) && r.evidence_confidence?.category === "HIGH");
    await expect(cards(page)).toHaveCount(want.length);
    await expect(countLine(page)).toContainText("Cause family: Cyber");
    await expect(countLine(page)).toContainText("Evidence confidence: High");
    await page.reload();
    await expect(cards(page)).toHaveCount(want.length);
    expect(filterParams(page)).toEqual(["f.cause=cyber", "f.conf=HIGH"]);

    await preset(page, "AI involved").click();
    const ai = records.filter((r) => r.ai_involvement.status !== "NONE_REPORTED");
    await expect(cards(page)).toHaveCount(ai.length);
    const country = ai[0].country_name;
    await page.locator(".atlas-country-list").getByRole("button", { name: new RegExp(`^${country}`) }).click();
    await expect(page).toHaveURL(/f\.country=/);
    await expect(cards(page)).toHaveCount(ai.filter((r) => r.country_name === country).length);
    await page.goBack();
    await expect(cards(page)).toHaveCount(ai.length);
    await page.goBack();
    await expect(cards(page)).toHaveCount(want.length);
    expect(filterParams(page)).toEqual(["f.cause=cyber", "f.conf=HIGH"]);
  });

  test("a link naming a filter value this corpus does not have says so instead of obeying or dropping it silently", async ({ app, page }) => {
    await openAtlas(page, "&f.cause=cyber,meteor&f.nosuch=1");
    await expect(page.locator(".rf-note")).toHaveCount(2);
    await expect(page.locator(".rf-note").first()).toContainText("meteor");
    await expect(cards(page)).toHaveCount(records.filter(isCyber).length);
  });

  test("attempts are in their own collapsed section, labelled, and in no count", async ({ app, page }) => {
    await openAtlas(page);
    const attempt = corpus.attempts[0];
    await expect(page.locator(".atlas-timeline")).not.toContainText(attempt.summary);
    const section = page.locator("details.atlas-attempts");
    await expect(section).not.toHaveAttribute("open", "");
    await expect(section.locator("summary")).toContainText(corpus.attempts_label);
    await section.locator("summary").click();
    await expect(section.locator(".impact-card")).toHaveCount(corpus.attempts.length);
    await expect(section).toContainText(attempt.summary);
    // Opening it changed no count.
    expect(await page.getByTestId("atlas-summary").innerText()).toContain(`${records.length} published records`);
    await expect(cards(page)).toHaveCount(records.length);
  });

  test("a card shows attribution and AI lines only where they apply, and the confidence reasons on request", async ({ app, page }) => {
    await openAtlas(page);
    const unknown = cards(page).filter({ hasText: "Attribution: unknown (not established)" }).first();
    await expect(unknown).toBeVisible();
    await expect(unknown.locator(".attr-line")).toHaveText(/^Attribution: unknown \(not established\)/);
    await expect(unknown.locator(".attr-line")).not.toContainText(/confidence/i);
    const natural = records.find((r) => r.attribution.status === "NOT_APPLICABLE" && r.ai_involvement.status === "NONE_REPORTED")!;
    const plain = cards(page).filter({ hasText: natural.summary });
    await expect(plain).not.toContainText("Attribution:");
    await expect(plain).not.toContainText("AI involvement");
    await expect(cards(page).filter({ hasText: "AI-assisted (not AI-caused)" })).toHaveCount(1);
    await expect(cards(page).filter({ hasText: "AI as operational cause" })).toHaveCount(1);
    const abstracted = cards(page).filter({ hasText: "Published under safeguards: place withheld" });
    await expect(abstracted).toHaveCount(records.filter((r) => ["kinetic", "sabotage"].includes(r.cause_family)).length);

    const card = cards(page).first();
    await card.getByRole("button", { name: /^Why\?/ }).click();
    const why = card.locator(".conf-panel");
    // No total of the points (iteration 23, ECI-15); the category and its components stay.
    await expect(why).toContainText("they are not a probability");
    await expect(why).not.toContainText("ordinal score");
    await expect(why).toContainText("It is not a probability, not a measure of severity");
    await expect(why.locator("table tbody tr")).toHaveCount(5);
    await page.keyboard.press("Escape");
    await expect(why).toHaveCount(0);
  });

  test("the evidence inspector lists which source supports which claim", async ({ app, page }) => {
    await openAtlas(page);
    const r = records.find((x) => x.attribution.status === "ATTRIBUTED")!;
    const card = cards(page).filter({ hasText: r.summary });
    const toggle = card.getByRole("button", { name: new RegExp(`^Sources \\(${r.sources.length}\\)`) });
    await toggle.click();
    const inspector = card.getByRole("region", { name: "Evidence inspector" });
    await expect(inspector.getByRole("heading", { name: "What each claim rests on" })).toBeVisible();
    const chain = await inspector.locator(".imp-chain li").allInnerTexts();
    expect(chain.map((c) => c.split(":")[0])).toEqual(["That it happened", "The effect", "Attribution"]);
    for (const s of r.sources.filter((x) => x.supports.includes("attribution"))) expect(chain[2]).toContain(s.publisher);
    for (const s of r.sources.filter((x) => !x.supports.includes("attribution"))) expect(chain[2]).not.toContain(s.publisher);
    await expect(inspector.locator(".imp-source")).toHaveCount(r.sources.length);
    await expect(inspector.locator(".imp-supports").first()).toContainText("Supports:");
    await expect(inspector.getByRole("heading", { name: "What the evidence does not establish" })).toBeVisible();
    // Escape closes it and focus returns to the button that opened it.
    await inspector.getByRole("button", { name: "Close" }).focus();
    await page.keyboard.press("Escape");
    await expect(inspector).toHaveCount(0);
    await expect(toggle).toBeFocused();
  });

  test("Download CSV is the shown records, read back; About this file states the filters", async ({ app, page }) => {
    await openAtlas(page, "&f.cause=cyber");
    const want = records.filter(isCyber);
    const [csv] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Download CSV" }).click()]);
    expect(csv.suggestedFilename()).toBe(`edm-impacts-records-${corpus.as_of}.csv`);
    const text = readFileSync(await csv.path(), "utf-8");
    expect(text.charCodeAt(0)).toBe(0xfeff);
    const lines = text.slice(1).split("\r\n").filter(Boolean);
    const header = lines[0].split(",");
    expect(header.slice(0, 3)).toEqual(["impact_id", "record_kind", "date"]);
    for (const banned of ["lat", "lon", "latitude", "longitude", "coordinates", "review_notes"]) expect(header).not.toContain(banned);
    const ids = lines.slice(1).map((l) => l.split(",")[0]);
    expect(ids).toEqual(want.map((r) => r.impact_id));
    expect(text).not.toContain(corpus.attempts[0].impact_id);

    const [readme] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "About this file" }).click()]);
    const about = readFileSync(await readme.path(), "utf-8");
    expect(about).toContain(`Records in this file: ${want.length} of ${records.length}`);
    expect(about).toContain("Cause family: Cyber");
    expect(about).toContain("not a census");
  });

  test("the presence map marks countries in one colour and its list sets the country filter", async ({ app, page }) => {
    await openAtlas(page);
    await expect(page.locator('.atlas-map [data-map-state="idle"]')).toHaveCount(1, { timeout: 45_000 });
    await expect(page.locator(".atlas-map-key")).toContainText("At least one published record in this view");
    await expect(page.locator(".atlas-map-key .atlas-key-swatch")).toHaveCount(2);
    const first = page.locator(".atlas-country-list button").first();
    const name = (await first.innerText()).split(":")[0].trim();
    await first.click();
    await expect(page).toHaveURL(/f\.country=[A-Z]{3}$/);
    await expect(countLine(page)).toContainText(`Country: ${name}`);
    await expect(page.locator(".atlas-country-list button[aria-pressed='true']")).toHaveCount(1);
    await expect(page.locator(".atlas-bias").nth(1)).toBeVisible();
  });

  test("keyboard: a preset, a filter menu, a Why? and an inspector are all reachable and operable", async ({ app, page }) => {
    await openAtlas(page);
    await preset(page, "Cyber").focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/f\.cause=cyber/);
    const sector = page.locator(".record-filters").getByRole("button", { name: /^Sector/ });
    await sector.focus();
    await page.keyboard.press("Enter");
    const panel = page.getByRole("group", { name: "Sector filter" });
    await expect(panel).toBeVisible();
    await page.keyboard.press("Tab");
    await expect(panel.locator("input").first()).toBeFocused();
    await page.keyboard.press("Space");
    await expect(page).toHaveURL(/f\.sector=/);
    await page.keyboard.press("Escape");
    await expect(panel).toHaveCount(0);
    await expect(sector).toBeFocused();
    const card = cards(page).first();
    const why = card.locator("button.conf-why");
    await why.focus();
    await page.keyboard.press("Enter");
    await expect(card.locator(".conf-panel")).toBeVisible();
    await expect(why).toHaveAttribute("aria-expanded", "true");
    const src = card.getByRole("button", { name: /^Sources \(/ });
    await src.focus();
    await page.keyboard.press("Enter");
    await expect(card.getByRole("region", { name: "Evidence inspector" })).toBeVisible();
  });

  test("a corrupt corpus costs the atlas only: the site bar stays, and the rest of the site works", async ({ app, page }) => {
    await page.route("**/data/global/evidence_confidence.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: body("evidence_confidence.json") }));
    await page.route("**/data/global/impacts.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: '{"records": [tru' }));
    await page.goto("/?view=impacts");
    const alert = page.getByRole("alert");
    await expect(alert).toContainText("The impact corpus could not be loaded");
    await expect(page.locator(".global-nav")).toBeVisible();
    await expect(page.locator(".global-nav").getByRole("link", { name: "Impact atlas", exact: true })).toBeVisible();
    await expect(page.locator(".sys-switch select")).toBeVisible();
    await expect(cards(page)).toHaveCount(0);
    // A malformed shape is refused the same way, and "Try again" recovers once the file is good.
    await page.unroute("**/data/global/impacts.json");
    await page.route("**/data/global/impacts.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: '{"records": "x"}' }));
    await alert.getByRole("button", { name: "Try again" }).click();
    await expect(alert).toContainText("could not be loaded");
    await page.unroute("**/data/global/impacts.json");
    await serveFixture(page);
    await alert.getByRole("button", { name: "Try again" }).click();
    await expect(cards(page)).toHaveCount(records.length);
    // The rest of the site was never affected.
    await page.locator(".global-nav .product-home").click();
    await expect(page.getByRole("heading", { name: "Energy Disruption Monitor", level: 1 })).toBeVisible();
  });

  test("a not-assessed record says so with its reason and has its own filter bucket; a provisional method says it is", async ({ app, page }) => {
    const reason = "Cited through a discovery aid only; a primary source is not yet attached.";
    const doc = JSON.parse(body("impacts.json"));
    doc.records[0].evidence_confidence = { category: null, label: null, score: null, disputed: false, reason };
    doc.records[1].evidence_confidence.components.origins.basis = "publishers";
    const method = { ...JSON.parse(body("evidence_confidence.json")), status: "provisional: thresholds not calibrated" };
    await page.route("**/data/global/impacts.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(doc) }));
    await page.route("**/data/global/evidence_confidence.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(method) }));
    await page.goto("/?view=impacts");
    await expect(cards(page)).toHaveCount(records.length);
    const first = cards(page).first();
    await expect(first.locator(".conf")).toHaveText(`Evidence confidence: Not assessed ${reason}`);
    await expect(first.locator(".conf")).not.toContainText(/Preliminary|Why\?/);
    // Its own bucket: choosing it shows that record and no other; Preliminary does not include it.
    await page.goto("/?view=impacts&f.conf=NOT_ASSESSED");
    await expect(cards(page)).toHaveCount(1);
    await expect(countLine(page)).toContainText("Evidence confidence: Not assessed");
    await page.goto("/?view=impacts&f.conf=PRELIMINARY");
    await expect(cards(page)).toHaveCount(records.filter((r, i) => i > 0 && r.evidence_confidence?.category === "PRELIMINARY").length);
    // The explainer: points only, the provisional status, and publishers worded as publishers.
    await page.goto("/?view=impacts");
    const second = cards(page).nth(1);
    await second.locator("button.conf-why").click();
    const why = second.locator(".conf-panel");
    await expect(why).toContainText("Method status: provisional: thresholds not calibrated.");
    await expect(why).toContainText(/distinct publishers? cited; whether they relay one statement was not reviewed/);
    await expect(why).toContainText("they are not a probability");
    // The status is beside the category itself, before any click (iteration 23, F5), with the line
    // that the category does not cover the cause (ECI-08).
    await expect(second.locator(".conf-provisional")).toHaveText(/^provisional method/);
    await expect(second.locator(".conf-scope")).toContainText("It does not cover the cause");
    await expect(why).not.toContainText(/\/\s*100|of 100|\d\s*%/);
  });

  test("an empty corpus says so, with the served reason, and offers no filter, preset or download", async ({ app, page }) => {
    const empty = { ...JSON.parse(body("impacts.json")), records: [], attempts: [], countries: [],
      empty_reason: "No reviewed record has been published yet. That is the state of the review, not a finding that nothing happened." };
    await page.route("**/data/global/impacts.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(empty) }));
    await page.route("**/data/global/evidence_confidence.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: body("evidence_confidence.json") }));
    await page.goto("/?view=impacts");
    await expect(page.getByRole("heading", { name: "No reviewed record is published yet" })).toBeVisible();
    await expect(page.locator(".atlas-main")).toContainText("not a finding that nothing happened");
    expect(await page.getByTestId("atlas-summary").innerText()).toContain("0 published records in this corpus · 0 countries");
    await expect(page.getByTestId("atlas-summary")).toContainText("research last run");
    await expect(page.locator(".atlas-presets")).toHaveCount(0);
    await expect(page.locator(".record-filters")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Download CSV" })).toHaveCount(0);
    await expect(page.locator("details.atlas-attempts")).toHaveCount(0);
    await expect(page.locator(".atlas-badge")).toBeVisible();
  });

  test("search finds the atlas and its cyber view without loading any record", async ({ app, page }) => {
    const asked: string[] = [];
    page.on("request", (r) => { if (r.url().endsWith("/data/global/impacts.json")) asked.push(r.url()); });
    await serveFixture(page);
    await app.open("");
    const box = page.locator(".gsearch input").first();
    await box.fill("cyber");
    await expect(page.getByRole("option", { name: /Cyber disruptions/ })).toBeVisible();
    expect(asked).toEqual([]);
    await page.getByRole("option", { name: /Cyber disruptions/ }).click();
    await expect(page).toHaveURL(/view=impacts&f\.cause=cyber/);
    await expect(preset(page, "Cyber")).toHaveAttribute("aria-current", "true");
    await expect(cards(page)).toHaveCount(records.filter(isCyber).length);
  });

  test("the glossary explains the impact terms, with the served definition as the detail", async ({ app, page }) => {
    await openAtlas(page);
    await page.locator(".global-nav").getByRole("button", { name: "Glossary" }).click();
    const dialog = page.locator("dialog.glossary-dialog");
    for (const term of ["AI involvement", "Attribution", "Attribution confidence", "Evidence confidence", "Impact atlas", "Cyber disruption",
      "Civilian-service impact", "Reported effect", "Claimed", "Assessed", "Attributed", "Disputed"]) {
      await expect(dialog.getByRole("heading", { name: term, exact: true })).toHaveCount(1);
    }
    const entry = dialog.locator("#gl-evidence-confidence");
    await entry.locator("summary").click();
    await expect(entry.locator("details p")).toContainText("It is not a probability, not a measure of severity");
  });
});

for (const size of [{ width: 390, height: 844 }, { width: 430, height: 932 }]) {
  test.describe(`Impact atlas on a phone, ${size.width}x${size.height}`, () => {
    test.use({ viewport: size, hasTouch: true, isMobile: true });

    test("fits the screen, opens from the Menu, and filters through the sheet", async ({ app, page }) => {
      await serveFixture(page);
      await app.open("");
      await page.locator(".global-nav").getByRole("button", { name: "Menu" }).click();
      await page.locator(".global-nav .nav-menu").getByRole("link", { name: "Impact atlas", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Impact atlas", level: 1 })).toBeVisible();
      await expect(cards(page)).toHaveCount(records.length);

      const overflow = () => page.evaluate(() => {
        const wide: string[] = [];
        const vw = document.documentElement.clientWidth;
        for (const el of Array.from(document.querySelectorAll<HTMLElement>(".atlas-page *"))) {
          const b = el.getBoundingClientRect();
          if (b.width > 0 && (b.right > vw + 1 || b.left < -1) && !el.closest(".maplibregl-map, .sr-only")) wide.push(`${el.tagName}.${el.className}`);
        }
        const page = document.querySelector<HTMLElement>(".atlas-page")!;
        return { wide: wide.slice(0, 5), scroll: page.scrollWidth - page.clientWidth, doc: document.documentElement.scrollWidth - vw };
      });
      expect(await overflow()).toEqual({ wide: [], scroll: 0, doc: 0 });

      // The filter sheet: one button, a dialog, Done returns.
      const open = page.locator(".record-filters").getByRole("button", { name: /^Filters \(0\)/ });
      await open.click();
      const sheet = page.getByRole("dialog", { name: /Filter the published records/ });
      await expect(sheet).toBeVisible();
      await sheet.locator("fieldset", { hasText: "Cause family" }).getByLabel(/^Cyber/).check();
      const want = records.filter(isCyber);
      await expect(sheet).toContainText(`Showing ${want.length} of ${records.length}`);
      await sheet.getByRole("button", { name: new RegExp(`^Show ${want.length} record`) }).click();
      await expect(sheet).toHaveCount(0);
      await expect(page.locator(".record-filters").getByRole("button", { name: /^Filters \(1\)/ })).toBeVisible();
      await expect(cards(page)).toHaveCount(want.length);
      expect(await overflow()).toEqual({ wide: [], scroll: 0, doc: 0 });

      // A card's inspector and confidence table also fit.
      const card = cards(page).first();
      await card.getByRole("button", { name: /^Why\?/ }).click();
      await card.getByRole("button", { name: /^Sources \(/ }).click();
      await expect(card.getByRole("region", { name: "Evidence inspector" })).toBeVisible();
      expect(await overflow()).toEqual({ wide: [], scroll: 0, doc: 0 });
      // The map is not loaded on a phone until asked for.
      await expect(page.locator(".atlas-map")).toHaveCount(0);
      await expect(page.getByRole("button", { name: "Show map" })).toBeVisible();
    });
  });
}
