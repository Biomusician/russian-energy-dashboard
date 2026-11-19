import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test, expect, pixelStats, readBytes } from "./fixtures";

/**
 * The Gulf overview's evidence sections, in a real browser (iteration 22).
 *
 * ONE PAGE, MORE EVIDENCE. The sections are headings on one scrolling page, each with an address.
 * What is fixed here is behaviour and refusal: records are one list in date order and no country
 * has a count; an attack record is its country and nothing finer; the regional context is dated
 * statements with their sources and no status; only that one section may speak of the strait, and
 * no section names a ship, a path, bypass capacity or what depends on what; and a broken file
 * leaves the rest of the page working.
 *
 * DATA. The impact layer is served from the synthetic fixture (e2e/fixtures/impacts22), with its
 * records moved onto the group's members so the page has something to show: which members exist
 * is read from the page's own manifest and regional file, never typed here. Every record in it is
 * invented.
 */

type Page = import("@playwright/test").Page;
type Member = { system_id: string; name: string; a3: string };
type Rec = Record<string, unknown> & {
  impact_id: string; date: string; country_a3: string; country_name: string; system_id: string | null;
  cause_family: string; cyber_mechanism: string | null; publication_policy: string;
  civilian_service_impact: { service: string }[]; record_kind: string;
};
type Payload = { records: Rec[]; attempts: Rec[]; empty_reason: string | null; vocabularies: Record<string, { id: string; label: string }[]> } & Record<string, unknown>;
type Entry = { id: string; date: string; as_of: string; context_type: string; is_latest_of_type: boolean; sources: { publisher: string }[] };
type Context = { entries: Entry[]; context_types: { id: string; label: string }[] } & Record<string, unknown>;

const fixture = (name: string) => JSON.parse(readFileSync(fileURLToPath(new URL(`./fixtures/impacts22/global/${name}`, import.meta.url)), "utf-8"));
const IT_OUTAGE = "it_outage_affecting_operations";

// Wording no section but the regional context may carry, and wording no section at all may carry
// outside the two fixed statements of what is not collected.
const STRAIT = /hormuz|strait|tanker|choke ?point|shipping|bypass/i;
const NEVER = /tanker|vessel|\bships?\b|bypass|choke ?point|\broutes?\b|\bdepend\w*/i;
const STATUS = /\b(is|are|remains?|now|currently|status:)\s+(open|closed|shut|blocked)\b/i;
const CONTEXT_LABEL = "Gulf & Hormuz context";

const json = (page: Page, path: string) => page.evaluate((p) => fetch(p).then((r) => r.json()), path);

/** The fixture's records placed on the group's members, in turn, alphabetically. A record placed
 *  on a member loses any region, as the build's campaign rule would have it. One technical record
 *  becomes an IT failure, so that label has a record to show. */
function onMembers(payload: Payload, members: Member[]): Payload {
  let i = 0;
  let itFailure = false;
  const place = (r: Rec): Rec => {
    if (r.country_a3 === "MULTI") return r;
    const m = members[i++ % members.length];
    const out: Rec = { ...r, country_a3: m.a3, country_name: m.name, system_id: m.system_id, admin1: null, geographic_precision: "country" };
    delete out.theatre;
    if (!itFailure && r.cause_family === "industrial_technical" && r.cyber_mechanism == null) {
      itFailure = true;
      out.cyber_mechanism = IT_OUTAGE;
    }
    return out;
  };
  return { ...payload, records: payload.records.map(place), attempts: payload.attempts.map(place) };
}

async function members(page: Page): Promise<Member[]> {
  const g = await (await page.request.get("/data/global/gulf.json")).json();
  return (g.systems as Member[]).map((s) => ({ system_id: s.system_id, name: s.name, a3: s.a3 }));
}

/** Serve the impact layer from the fixture. Returns what the page will receive. */
async function serveLayer(page: Page, change: { impacts?: (p: Payload) => Payload; context?: (c: Context) => Context } = {}) {
  // The members come from the build's own regional file.
  const who = await members(page);
  const impacts = (change.impacts ?? ((p) => p))(onMembers(fixture("impacts.json") as Payload, who));
  const context = (change.context ?? ((c) => c))(fixture("regional_context.json") as Context);
  await page.route("**/data/global/impacts.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(impacts) }));
  await page.route("**/data/global/regional_context.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(context) }));
  await page.route("**/data/global/evidence_confidence.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fixture("evidence_confidence.json")) }));
  const ids = new Set(who.map((m) => m.system_id));
  const records = impacts.records.filter((r) => r.record_kind === "disruption" && r.system_id != null && ids.has(r.system_id));
  return { who, impacts, context, records };
}

async function sideways(page: Page) {
  return page.evaluate(() =>
    Math.max(document.documentElement.scrollWidth - window.innerWidth,
             ...[...document.querySelectorAll(".global-page")].map((e) => e.scrollWidth - e.clientWidth)));
}

const SECTIONS = [
  ["overview", "Overview", null],
  ["energy", "Energy context", "Regional energy context"],
  ["systems", "Monitored systems", "Monitored systems in this view"],
  ["impacts", "Reported impacts", "Reported impacts"],
  ["services", "Cyber & civilian services", "Cyber & civilian services"],
  ["context", CONTEXT_LABEL, CONTEXT_LABEL],
  ["coverage", "Research coverage", "Research coverage"],
] as const;

const nav = (page: Page) => page.getByRole("navigation", { name: "Sections of this page" });
const section = (page: Page, id: string) => page.locator(`#sec-${id}`);

test.describe("Gulf overview: sections", () => {
  test("every section is one click away, has an address, and takes focus to its heading", async ({ app, page }) => {
    await serveLayer(page);
    await app.open("?group=gulf");
    await expect(nav(page).getByRole("link")).toHaveText(SECTIONS.map((s) => s[1]));
    for (const [id, label, heading] of SECTIONS.slice(1)) {
      await nav(page).getByRole("link", { name: label, exact: true }).click();
      await expect(page).toHaveURL(new RegExp(`[?&]group=gulf&section=${id}$`));
      const h = section(page, id).locator("h2").first();
      await expect(h).toHaveText(heading!);
      await expect(h).toBeFocused();
      await expect(section(page, id)).toBeInViewport();
      await expect(nav(page).getByRole("link", { name: label, exact: true })).toHaveAttribute("aria-current", "location");
      await expect(nav(page).locator('[aria-current="location"]')).toHaveCount(1);
    }
    // The overview is the page's top and its address is the page's own.
    await nav(page).getByRole("link", { name: "Overview", exact: true }).click();
    await expect(page).toHaveURL(/[?&]group=gulf$/);
    await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
    await expect(page.locator(".group-purpose")).toBeInViewport();
    // Nothing is behind a tab: every section is on the page at once.
    for (const [id] of SECTIONS) await expect(section(page, id)).toHaveCount(1);
  });

  for (const [id, , heading] of SECTIONS.slice(1)) {
    test(`a link to section=${id} opens the page there`, async ({ app, page }) => {
      await serveLayer(page);
      await app.open(`?group=gulf&section=${id}`);
      const h = section(page, id).locator("h2").first();
      await expect(h).toHaveText(heading!);
      await expect(h).toBeFocused();
      await expect(section(page, id)).toBeInViewport();
      await expect(page).toHaveURL(new RegExp(`section=${id}$`));
    });
  }

  test("an unknown section name opens the page at its top, not at a guess", async ({ app, page }) => {
    await serveLayer(page);
    await app.open("?group=gulf&section=tankers");
    await expect(page.locator(".group-purpose")).toBeInViewport();
    expect(await page.locator(".group-page").evaluate((e) => e.scrollTop)).toBe(0);
  });

  test("scrolling by hand moves the navigation's mark to the section in view", async ({ app, page }) => {
    await serveLayer(page);
    await app.open("?group=gulf");
    await expect(nav(page).locator('[aria-current="location"]')).toHaveText("Overview");
    await section(page, "coverage").locator("h2").first().scrollIntoViewIfNeeded();
    await page.mouse.move(600, 500);
    await page.mouse.wheel(0, 200000);
    await expect(nav(page).locator('[aria-current="location"]')).toHaveText("Research coverage");
  });

  test("What this page can tell you: eight questions, each linked to the section that answers it", async ({ app, page }) => {
    await serveLayer(page);
    await app.open("?group=gulf");
    const tell = page.locator(".group-tell");
    await expect(tell.getByRole("heading", { name: "What this page can tell you" })).toBeVisible();
    await expect(tell.locator("dt")).toHaveCount(8);
    await expect(tell.locator("dt")).toContainText(["Which energy systems are represented?", "Which countries are monitored?",
      "What disruption evidence is published?", "What regional context does credible reporting document?",
      "Which civilian services have documented effects?", "What is cyber, what is kinetic", "How certain are the claims?", "What is withheld?"]);
    // Every line links somewhere on this page.
    for (const href of await tell.locator("dd a").evaluateAll((as) => as.map((a) => a.getAttribute("href")))) {
      expect(href).toMatch(/^\?group=gulf(&section=(energy|systems|impacts|services|context|coverage))?$/);
    }
    await tell.locator("div", { hasText: "What is withheld?" }).getByRole("link").click();
    await expect(page).toHaveURL(/section=coverage$/);
    await expect(section(page, "coverage").locator("h2").first()).toBeFocused();
    await expect(section(page, "coverage").locator(".withheld-list li").first()).toContainText("place, the facility, the operator, the method");
    // No ranking and no count in the block.
    expect(await tell.innerText()).not.toMatch(/\bmost (affected|attacked|important)\b|\branked?\b/i);
  });

  test("the keyboard reaches a section and continues inside it", async ({ app, page }) => {
    await serveLayer(page);
    await app.open("?group=gulf");
    const link = nav(page).getByRole("link", { name: "Cyber & civilian services", exact: true });
    await link.focus();
    await page.keyboard.press("Enter");
    await expect(section(page, "services").locator("h2").first()).toBeFocused();
    await page.keyboard.press("Tab");
    // The next stop is inside the section the reader jumped to, not back at the top of the page.
    expect(await page.evaluate(() => !!document.activeElement?.closest("#sec-services"))).toBe(true);
    // And the navigation itself is reachable in order with Tab.
    await nav(page).getByRole("link").first().focus();
    for (const [, label] of SECTIONS.slice(1)) {
      await page.keyboard.press("Tab");
      await expect(nav(page).getByRole("link", { name: label, exact: true })).toBeFocused();
    }
  });
});

test.describe("Gulf overview: reported impacts", () => {
  test("the members' records, one list in date order, from a separate corpus, with no count per country", async ({ app, page }) => {
    const { who, records } = await serveLayer(page);
    await app.open("?group=gulf&section=impacts");
    const region = page.getByRole("region", { name: "Reviewed impact records for this region" });
    await expect(region).toContainText("Reviewed records from a separate corpus that is not scored");
    await expect(region).toContainText("nothing here is counted, grouped or ordered by country");
    const cards = region.getByRole("list", { name: "Impact records, newest first" }).locator(".impact-card");
    expect(records.length).toBeGreaterThan(5);
    await expect(cards).toHaveCount(records.length);
    // Served order is event date, newest first; the page keeps it.
    const dates = records.map((r) => r.date);
    expect(dates).toEqual([...dates].sort().reverse());
    const first = await cards.first().locator(".impact-place").innerText();
    expect(first).toBe(records[0].country_name);

    // The filters: date, cause, sector, confidence. There is no country filter, whose option
    // counts would be a tally per country.
    const filters = region.getByRole("region", { name: "Filter the published impact records" });
    const toggles = await filters.locator(".rf-toggle").allInnerTexts();
    expect(toggles.map((t) => t.replace(/:.*$/s, "").trim())).toEqual(["Date", "Cause", "Service or sector", "Evidence confidence"]);
    await expect(filters).toContainText(`Showing ${records.length} of ${records.length} published impact records`);

    // No member's name stands beside a number of records anywhere in the section.
    const text = await section(page, "impacts").innerText();
    for (const m of who) {
      expect(text, m.name).not.toMatch(new RegExp(`${m.name}[^\\n.]{0,24}\\b\\d+ (records?|incidents?|attacks?|events?)\\b`, "i"));
      expect(text, m.name).not.toMatch(new RegExp(`\\b\\d+ (records?|incidents?|attacks?|events?) (in|for|on|against) ${m.name}`, "i"));
    }
    expect(text).not.toMatch(/\bmost (affected|attacked|targeted)\b|\bhardest[- ]hit\b|\branked\b/i);
    expect(text.replace(CONTEXT_LABEL, "")).not.toMatch(STRAIT);
  });

  test("an attack record is its country and nothing finer, and says the place is withheld", async ({ app, page }) => {
    const { records } = await serveLayer(page);
    const attack = records.find((r) => r.publication_policy === "country_abstracted")!;
    expect(attack, "the fixture has no abstracted record").toBeTruthy();
    await app.open("?group=gulf&section=impacts");
    const card = page.getByRole("region", { name: "Reviewed impact records for this region" }).locator(".impact-card")
      .filter({ hasText: "place withheld" });
    await expect(card).toHaveCount(records.filter((r) => r.publication_policy === "country_abstracted").length);
    await expect(card.first().locator(".impact-place")).toHaveText(attack.country_name);
    // Its evidence inspector shows no headline: a headline is where a publisher names the place.
    await card.first().getByRole("button", { name: /^Sources/ }).click();
    await expect(card.first().locator(".source-title")).toHaveCount(0);
  });

  test("a cause filter narrows the list, says how many it hides, and survives in the address", async ({ app, page }) => {
    const { records } = await serveLayer(page);
    const cyber = records.filter((r) => r.cause_family === "cyber").length;
    expect(cyber).toBeGreaterThan(0);
    expect(cyber).toBeLessThan(records.length);
    await app.open("?group=gulf&section=impacts");
    const region = page.getByRole("region", { name: "Reviewed impact records for this region" });
    await region.getByRole("button", { name: /^Cause/ }).click();
    await region.getByRole("group", { name: "Cause filter" }).getByLabel(/^Cyber/).check();
    await expect(region).toContainText(`Showing ${cyber} of ${records.length} published impact records`);
    await expect(region).toContainText(`The filters hide ${records.length - cyber}`);
    await expect(page).toHaveURL(/f\.cause=cyber/);
    await expect(page).toHaveURL(/group=gulf/);
    await expect(region.getByRole("list", { name: "Impact records, newest first" }).locator(".impact-card")).toHaveCount(cyber);
    // An IT failure is its own choice and is never under Cyber.
    await expect(region.getByRole("group", { name: "Cause filter" })).toContainText("IT failure (not an attack)");
    await page.reload();
    await app.mapIdle();
    await expect(region).toContainText(`Showing ${cyber} of ${records.length} published impact records`);
  });

  test("the membership filter narrows the impact records as it narrows the cards", async ({ app, page }) => {
    const { records } = await serveLayer(page);
    await app.open("?group=gulf");
    const g = await json(page, "/data/global/gulf.json");
    const gcc = new Set((g.systems as { system_id: string; gcc_member: boolean }[]).filter((s) => s.gcc_member).map((s) => s.system_id));
    const want = records.filter((r) => gcc.has(r.system_id!)).length;
    await page.getByLabel("Membership filter").selectOption("gcc");
    await expect(page.getByRole("region", { name: "Reviewed impact records for this region" })
      .getByRole("list", { name: "Impact records, newest first" }).locator(".impact-card")).toHaveCount(want);
  });

  test("attempts are listed apart under their own label and never counted", async ({ app, page }) => {
    const { impacts, records } = await serveLayer(page);
    expect(impacts.attempts.length).toBeGreaterThan(0);
    await app.open("?group=gulf&section=impacts");
    const region = page.getByRole("region", { name: "Reviewed impact records for this region" });
    await expect(region.locator(".impact-attempts h3")).toHaveText(String(impacts.attempts_label));
    await expect(region.locator(".impact-attempts .impact-card")).toHaveCount(impacts.attempts.length);
    await expect(region).toContainText(`of ${records.length} published impact records`);
  });

  test("an empty corpus says why in words and never shows a zero", async ({ app, page }) => {
    await serveLayer(page, { impacts: (p) => ({ ...p, records: [], attempts: [], empty_reason: "No reviewed record has been published yet. That is the state of the review." }) });
    await app.open("?group=gulf&section=impacts");
    const region = page.getByRole("region", { name: "Reviewed impact records for this region" });
    await expect(region).toContainText("No reviewed record has been published yet");
    await expect(region.locator(".impact-card")).toHaveCount(0);
    expect(await region.innerText()).not.toMatch(/\b0 (published|records|impact)/i);
    await expect(section(page, "services")).toContainText("That is not a finding that no service was affected");
    await expect(section(page, "services")).toContainText("No cyber record for these countries in the current reviewed corpus");
    await expect(page.locator(".group-tell")).toContainText("which describes the corpus and not the region");
    // The country systems' own event feed is still there.
    await expect(page.getByRole("region", { name: "Recent reviewed events in this region" })).toBeVisible();
  });
});

test.describe("Gulf overview: cyber and civilian services", () => {
  test("effects are grouped by service in the vocabulary's order, in the source's own unit", async ({ app, page }) => {
    const { impacts, records } = await serveLayer(page);
    await app.open("?group=gulf&section=services");
    const sec = section(page, "services");
    const present = new Set(records.flatMap((r) => r.civilian_service_impact.map((s) => s.service)));
    const want = impacts.vocabularies.sectors.filter((s) => present.has(s.id)).map((s) => s.label);
    expect(want.length).toBeGreaterThan(2);
    await expect(sec.locator(".service-group h4")).toHaveText(want);
    const rows = records.reduce((n, r) => n + r.civilian_service_impact.length, 0);
    await expect(sec.locator(".service-rows li")).toHaveCount(rows);
    await expect(sec).toContainText("nothing is converted or added up");
    await expect(sec.locator(".service-group").filter({ hasText: "not converted" }).first()).toContainText(/the source counts [a-z ]+; not converted/);
    // Each service's lines are in date order: the first line of a group is its newest record.
    for (const g of await sec.locator(".service-group").all()) {
      const label = await g.locator("h4").innerText();
      const id = impacts.vocabularies.sectors.find((s) => s.label === label)!.id;
      const of = records.filter((r) => r.civilian_service_impact.some((s) => s.service === id));
      await expect(g.locator(".service-rows li").first().locator(".service-place")).toHaveText(of[0].country_name);
    }
    // No table of totals per service and no summary by actor.
    await expect(sec.locator("table")).toHaveCount(0);
    for (const h of await sec.locator(".service-group h4").allInnerTexts()) expect(h, "a service heading carries a figure").not.toMatch(/\d/);
  });

  test("cyber records and IT failures are two lists, and an IT failure is never in the cyber one", async ({ app, page }) => {
    const { records, impacts } = await serveLayer(page);
    const cyber = records.filter((r) => r.cause_family === "cyber");
    const it = records.filter((r) => r.cause_family !== "cyber" && r.cyber_mechanism === IT_OUTAGE);
    expect(cyber.length).toBeGreaterThan(0);
    expect(it.length).toBe(1);
    await app.open("?group=gulf&section=services");
    const sec = section(page, "services");
    const rows = sec.getByRole("list", { name: "Cyber records, newest first" }).locator(".digital-row");
    await expect(rows).toHaveCount(cyber.length);
    const failures = sec.getByRole("list", { name: "IT failures, newest first" }).locator(".digital-row");
    await expect(failures).toHaveCount(1);
    await expect(failures.first()).toContainText("IT failure:");
    await expect(sec.getByRole("list", { name: "Cyber records, newest first" })).not.toContainText("IT failure:");
    await expect(sec.locator(".cause-kinds")).toContainText("Not an attack, and never listed as cyber");
    // Every cause the taxonomy has is explained in the taxonomy's own words.
    for (const c of impacts.vocabularies.cause_families) await expect(sec.locator(".cause-kinds")).toContainText(c.label);
    // Attribution is shown as who attributes, row by row; there is no actor table.
    await expect(sec).toContainText("There is no summary by actor");
    await expect(rows.first().locator(".attr-line")).toHaveCount((cyber[0].attribution as { status: string }).status === "NOT_APPLICABLE" ? 0 : 1);
    await expect(rows.first()).toContainText(/Evidence confidence: \w/);
    // The full card, with its evidence inspector, is on the page once: these are not second copies.
    await expect(sec.locator(".impact-card")).toHaveCount(0);
    expect((await sec.innerText()).replace(CONTEXT_LABEL, "")).not.toMatch(STRAIT);
  });

  test("a compact record links to its full card, clearing a filter that hides it and saying so", async ({ app, page }) => {
    const { records, impacts } = await serveLayer(page);
    const cyber = records.filter((r) => r.cause_family === "cyber");
    await app.open("?group=gulf&section=impacts");
    const region = page.getByRole("region", { name: "Reviewed impact records for this region" });
    // Hide every cyber record with a filter on another cause, then follow a cyber record's link.
    const other = records.find((r) => r.cause_family === "natural_hazard" || r.cause_family === "supply_shortfall")!;
    expect(other, "the fixture has no record of another cause").toBeTruthy();
    const label = impacts.vocabularies.cause_families.find((c) => c.id === other.cause_family)!.label;
    await region.getByRole("button", { name: /^Cause/ }).click();
    await region.getByRole("group", { name: "Cause filter" }).getByLabel(new RegExp(`^${label}`)).check();
    await expect(page).toHaveURL(/f\.cause=/);
    await expect(region.locator(`#impact-${cyber[0].impact_id}`)).toHaveCount(0);
    await section(page, "services").getByRole("list", { name: "Cyber records, newest first" }).getByRole("link", { name: /^Full record and sources/ }).first().click();
    const card = region.locator(`#impact-${cyber[0].impact_id}`);
    await expect(card).toBeInViewport();
    await expect(card).toBeFocused();
    await expect(region).toContainText("A filter was cleared to show the record you opened.");
    await expect(region).toContainText(`Showing ${records.length} of ${records.length} published impact records`);
    await expect(page).toHaveURL(new RegExp(`#impact-${cyber[0].impact_id}$`));
    await expect(page).not.toHaveURL(/f\.cause=/);
  });

  test("a record the build did not assess says Not assessed, has its own filter choice, and is never Preliminary", async ({ app, page }) => {
    let changed = "";
    const { records } = await serveLayer(page, { impacts: (p) => {
      const target = p.records.find((r) => r.system_id != null && r.country_a3 !== "MULTI")!;
      changed = target.impact_id;
      target.evidence_confidence = { category: null, label: null, score: null, reason: "No primary source is attached yet." };
      return p;
    } });
    await app.open("?group=gulf&section=impacts");
    const region = page.getByRole("region", { name: "Reviewed impact records for this region" });
    const card = region.locator(`#impact-${changed}`);
    await expect(card).toContainText("Not assessed");
    await expect(card).toContainText("No primary source is attached yet");
    await expect(card.locator(".conf")).not.toContainText(/Preliminary|\/ ?100|%/);
    await region.getByRole("button", { name: /^Evidence confidence/ }).click();
    const group = region.getByRole("group", { name: "Evidence confidence filter" });
    const options = await group.locator(".rf-option-label").allInnerTexts();
    expect(options[options.length - 1]).toBe("Not assessed");
    await group.getByLabel(/^Not assessed/).check();
    await expect(region).toContainText(`Showing 1 of ${records.length} published impact records`);
    await expect(region.getByRole("list", { name: "Impact records, newest first" }).locator("li[id^=impact-]")).toHaveCount(1);
    await expect(card).toBeVisible();
  });
});

test.describe("Gulf overview: regional context", () => {
  test("dated statements with their sources, the newest of a kind as of its date, older ones historical, no status", async ({ app, page }) => {
    const { context } = await serveLayer(page);
    await app.open("?group=gulf&section=context");
    const sec = section(page, "context");
    const entries = sec.locator(".ctx-entry");
    await expect(entries).toHaveCount(context.entries.length);
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const shown = (iso: string) => `${Number(iso.slice(8, 10))} ${months[Number(iso.slice(5, 7)) - 1]} ${iso.slice(0, 4)}`;
    const sorted = [...context.entries].sort((a, b) => (a.date < b.date ? 1 : -1));
    for (const [i, e] of sorted.entries()) {
      const row = entries.nth(i);
      await expect(row.locator(".ctx-date")).toHaveText(shown(e.date));
      await expect(row.locator(".ctx-head")).toContainText(e.sources[0].publisher);
      await expect(row.locator(".ctx-sources a").first()).toHaveAttribute("href", /^https?:\/\//);
      await expect(row.locator(".ctx-asof")).toContainText(e.is_latest_of_type ? `As of ${shown(e.as_of)}` : `Historical statement, as of ${shown(e.as_of)}`);
    }
    expect(context.entries.some((e) => !e.is_latest_of_type), "the fixture has no older statement").toBe(true);
    await expect(sec.locator(".ctx-count")).toContainText(`Showing ${context.entries.length} of ${context.entries.length} dated statements`);
    await expect(sec.locator(".ctx-count")).toContainText("No single status is given");
    // No open/closed status anywhere in the section, and no status element.
    expect(await sec.innerText()).not.toMatch(STATUS);
    await expect(sec.locator("[class*=status-flag], [data-status]")).toHaveCount(0);
  });

  test("Why there is no tanker map: the fixed block, above the timeline, and the only place that word appears", async ({ app, page }) => {
    await serveLayer(page);
    await app.open("?group=gulf&section=context");
    const sec = section(page, "context");
    const block = sec.getByRole("note", { name: "Why there is no tanker map" });
    await expect(block.getByRole("heading", { level: 3 })).toHaveText("Why there is no tanker map");
    await expect(block).toContainText("aggregate, dated, sourced statements only");
    await expect(block).toContainText("does not collect vessel positions, routes, bypass capacity or which facility depends on the strait");
    await expect(block).toContainText("those serve operations, not understanding");
    await expect(block).toContainText("enters no index and no country's record");
    await expect(block).toContainText("A price movement is not an infrastructure loss");
    const top = async (sel: string) => (await sec.locator(sel).first().boundingBox())!.y;
    expect(await top(".no-tanker-map")).toBeLessThan(await top(".ctx-timeline"));

    // "tanker" is on the page once, in that block's heading.
    await page.locator(".group-howto summary").click();
    const g = await json(page, "/data/global/gulf.json");
    const whole = (await page.locator("main").innerText()).replace(g.not_built, "");
    expect(whole.match(/tanker/gi) ?? []).toHaveLength(1);
    expect((await block.innerText()).match(/tanker/gi) ?? []).toHaveLength(1);
  });

  test("only the context section speaks of the strait, and nothing in it names a ship, a path or a dependence", async ({ app, page }) => {
    await serveLayer(page);
    await app.open("?group=gulf");
    await page.locator(".group-howto summary").click();
    const g = await json(page, "/data/global/gulf.json");
    // Everything outside the context section. The section's own name, where it is a link to it, is
    // the one string allowed out; the served not_built sentence is the view's statement of what it leaves out.
    const outside = await page.locator("main").evaluate((main) => {
      const copy = main.cloneNode(true) as HTMLElement;
      copy.querySelector("#sec-context")?.remove();
      return copy.textContent ?? "";
    });
    const rest = outside.replace(g.not_built, "").split(CONTEXT_LABEL).join("");
    expect(rest).not.toMatch(STRAIT);
    expect(rest).not.toMatch(/\bvessels?\b|\bships?\b/i);

    // Inside the context section: the two fixed statements of what is not collected are the only
    // place the forbidden words appear. The statements themselves never carry them.
    const inside = await section(page, "context").evaluate((sec) => {
      const copy = sec.cloneNode(true) as HTMLElement;
      copy.querySelectorAll(".no-tanker-map, .ctx-caveat").forEach((e) => e.remove());
      return copy.textContent ?? "";
    });
    expect(inside).toMatch(/Strait of Hormuz/);
    expect(inside).not.toMatch(NEVER);
    for (const t of await section(page, "context").locator(".ctx-entry").allInnerTexts()) expect(t).not.toMatch(NEVER);
  });

  test("the statements can be narrowed by kind, and the count says what is shown", async ({ app, page }) => {
    const { context } = await serveLayer(page);
    await app.open("?group=gulf&section=context");
    const sec = section(page, "context");
    const kinds = context.context_types.filter((t) => context.entries.some((e) => e.context_type === t.id));
    const filter = sec.getByRole("group", { name: "Show statements about" });
    await expect(filter.getByRole("checkbox")).toHaveCount(kinds.length);
    const pick = kinds.find((k) => context.entries.filter((e) => e.context_type === k.id).length > 1)!;
    const n = context.entries.filter((e) => e.context_type === pick.id).length;
    await filter.getByLabel(pick.label).check();
    await expect(sec.locator(".ctx-entry")).toHaveCount(n);
    await expect(sec.locator(".ctx-count")).toContainText(`Showing ${n} of ${context.entries.length} dated statements`);
    // Narrowing never promotes an older statement: one is still the latest, the other historical.
    await expect(sec.locator(".ctx-entry.ctx-latest")).toHaveCount(1);
    await expect(sec.locator(".ctx-entry.ctx-historical")).toHaveCount(n - 1);
    await filter.getByRole("button", { name: "Show every kind" }).click();
    await expect(sec.locator(".ctx-entry")).toHaveCount(context.entries.length);
  });
});

test.describe("Gulf overview: research coverage", () => {
  test("the impact layer's source families and limits, what is withheld, and each country's coverage link", async ({ app, page }) => {
    const { who, impacts } = await serveLayer(page);
    await app.open("?group=gulf&section=coverage");
    const sec = section(page, "coverage");
    const research = impacts.research as { source_families: { family: string }[]; limitations: string[] };
    for (const f of research.source_families) await expect(sec.getByRole("list", { name: "Source families searched for impact records" })).toContainText(f.family);
    for (const l of research.limitations) await expect(sec.getByRole("list", { name: "Known limits of the impact research" })).toContainText(l);
    await expect(sec).toContainText("not a census");
    await expect(sec.locator(".withheld-list li")).toHaveCount(5);
    const links = sec.locator(".coverage-links li a");
    await expect(links).toHaveText(who.map((m) => m.name));
    expect(who.map((m) => m.name)).toEqual([...who.map((m) => m.name)].sort());
    expect((await sec.innerText()).replace(CONTEXT_LABEL, "")).not.toMatch(STRAIT);
    await links.first().click();
    await expect(page).toHaveURL(new RegExp(`[?&]sys=${who[0].system_id}\\b`));
  });
});

test.describe("Gulf overview: impact brief", () => {
  test("the impact brief downloads as a real image with content and its caveat band", async ({ app, page }) => {
    await serveLayer(page);
    await app.open("?group=gulf&section=impacts");
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      app.button("Download impact brief (PNG)").click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/^gulf-impact-brief-\d{4}-\d{2}-\d{2}\.png$/);
    const png = readBytes((await download.path())!);
    expect(png.subarray(1, 4).toString("ascii")).toBe("PNG");
    const whole = await pixelStats(page, png);
    expect(whole.width).toBe(1600);
    expect(whole.height).toBeGreaterThanOrEqual(900);
    expect(whole.distinct).toBeGreaterThan(12);
    expect(whole.spread).toBeGreaterThan(120);
    // The title band, both columns of text and the caveat band at the foot each carry ink.
    const H = whole.height;
    for (const [what, box] of [["title band", [0, 0, 1600, 96]], ["left column", [24, 110, 760, 400]], ["right column", [812, 110, 760, 400]],
                               ["caveat band", [0, H - 100, 1600, 100]]] as const) {
      const part = await pixelStats(page, png, [...box] as [number, number, number, number]);
      expect(part.spread, `${what} is blank`).toBeGreaterThan(100);
      expect(part.distinct, `${what} is blank`).toBeGreaterThan(3);
    }
    await expect(page.getByRole("status").filter({ hasText: "Impact brief saved" })).toContainText("carries its own caveats");
  });

  test("the brief's words, as the page hands them to the image, carry every caveat and no country count", async ({ app, page }) => {
    // The image cannot be read back as text, so the canvas is watched while the brief is drawn.
    const { who } = await serveLayer(page);
    await app.open("?group=gulf&section=impacts");
    await page.evaluate(() => {
      const w = window as unknown as { __drawn: string[] };
      w.__drawn = [];
      const fill = CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText = function (this: CanvasRenderingContext2D, t: string, x: number, y: number, m?: number) {
        w.__drawn.push(String(t));
        return m === undefined ? fill.call(this, t, x, y) : fill.call(this, t, x, y, m);
      };
    });
    await Promise.all([page.waitForEvent("download"), app.button("Download impact brief (PNG)").click()]);
    const drawn = await page.evaluate(() => (window as unknown as { __drawn: string[] }).__drawn);
    const text = drawn.join(" ");
    expect(drawn).toContain("Aggregate regional context only: no facilities, no routes, no vessels.");
    expect(text).toMatch(/not comparable across countries/);
    expect(text).toMatch(/later status of attacked facilities is not published/i);
    expect(text).toMatch(/not a probability/);
    expect(text).toMatch(/As of \d{1,2} [A-Z][a-z]{2} \d{4} · /);
    expect(text).toMatch(/Source: /);
    expect(text).toMatch(/published records for the \d+ countries together/);
    expect(text).not.toMatch(STATUS);
    // A member is named only on its national energy line: "<name>: <figure> <unit>".
    for (const line of drawn) {
      for (const m of who) {
        if (line.includes(m.name)) expect(line, line).toMatch(new RegExp(`^${m.name}: (no data|[\\d.,]+ \\S)`));
      }
    }
    expect(text).not.toMatch(/\b\d+ (records?|incidents?|attacks?) (in|for) [A-Z]/);
  });
});

test.describe("Gulf overview: phones", () => {
  for (const [w, h] of [[390, 844], [430, 932]] as const) {
    test(`${w}x${h}: every section fits the width, the navigation swipes inside itself, and the block opens from a button`, async ({ app, page }) => {
      await page.setViewportSize({ width: w, height: h });
      await serveLayer(page);
      await app.open("?group=gulf");
      expect(await sideways(page), "sideways scroll at the top").toBeLessThanOrEqual(1);
      // The map is still in the first screen (iteration 21's rule).
      const map = await page.locator("[data-map-state]").boundingBox();
      expect(map!.y, "the map starts too low").toBeLessThan(h - 200);
      // With room to spare, whatever font a machine substitutes: iteration 21 left about 130 px.
      expect(map!.y, "the sections' navigation pushed the map down the first screen").toBeLessThan(h - 240);
      // The block waits behind one phrase in the caveat line, which costs the first screen no row.
      const toggle = page.locator(".group-caveat-line").getByRole("button", { name: /What this page can tell you/ });
      await expect(toggle).toHaveAttribute("aria-expanded", "false");
      expect((await toggle.boundingBox())!.height, "an inline disclosure reaches the 24 px AA size").toBeGreaterThanOrEqual(23.5);
      await expect(page.locator(".group-tell dt")).toHaveCount(0);
      await toggle.click();
      await expect(toggle).toHaveAttribute("aria-expanded", "true");
      await expect(page.locator(".group-tell dt")).toHaveCount(8);
      expect(await sideways(page), "sideways scroll with the block open").toBeLessThanOrEqual(1);
      await page.keyboard.press("Escape");
      await expect(toggle).toHaveAttribute("aria-expanded", "false");
      await expect(page.locator(".group-tell dt")).toHaveCount(0);

      for (const [id, label] of SECTIONS.slice(1)) {
        const link = nav(page).getByRole("link", { name: label, exact: true });
        await link.scrollIntoViewIfNeeded();
        const box = (await link.boundingBox())!;
        expect(box.height, `${label} is a small target`).toBeGreaterThanOrEqual(44);
        await link.click();
        await expect(section(page, id)).toBeInViewport();
        expect(await sideways(page), `sideways scroll at ${id}`).toBeLessThanOrEqual(1);
        // Nothing in the section is wider than the screen.
        const wide = await section(page, id).evaluate((sec, vw) =>
          [...sec.querySelectorAll<HTMLElement>("*")].filter((e) => {
            const r = e.getBoundingClientRect();
            return r.width > 0 && (r.right > vw + 1 || r.left < -1) && !e.closest(".table-scroll, .member-list ul, .maplibregl-map, .rf-sheet");
          }).map((e) => `${e.tagName.toLowerCase()}.${String(e.className).split(" ")[0]}`).slice(0, 5), w);
        expect(wide, `${id}: wider than the screen`).toEqual([]);
        await page.locator(".group-page").evaluate((e) => e.scrollTo(0, 0));
      }
    });
  }

  test("390x844: the filters open as a sheet and a card's evidence opens", async ({ app, page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const { records } = await serveLayer(page);
    await app.open("?group=gulf&section=impacts");
    const region = page.getByRole("region", { name: "Reviewed impact records for this region" });
    await region.getByRole("button", { name: /^Filters/ }).click();
    const sheet = page.getByRole("dialog", { name: "Filter the published impact records" });
    await expect(sheet).toBeVisible();
    await sheet.getByLabel(/^Cyber/).check();
    await sheet.getByRole("button", { name: /^Show \d+ records?$/ }).click();
    await expect(sheet).toBeHidden();
    await expect(region).toContainText(`of ${records.length} published impact records`);
    const card = region.locator(".impact-card").first();
    await card.getByRole("button", { name: /^Sources/ }).click();
    await expect(card.getByRole("button", { name: "Close evidence inspector" })).toBeVisible();
    expect(await sideways(page)).toBeLessThanOrEqual(1);
  });
});

test.describe("Gulf overview: a broken impact file", () => {
  test("a corrupted regional_context.json: that section says so, and the rest of the page works", async ({ app, page }) => {
    app.allowConsoleError(/regional_context|JSON|Unexpected|SyntaxError/i);
    const { records } = await serveLayer(page);
    await page.unroute("**/data/global/regional_context.json");
    await page.route("**/data/global/regional_context.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: '{"entries": [tru' }));
    await app.open("?group=gulf&section=context");
    const sec = section(page, "context");
    await expect(sec.getByRole("alert")).toContainText("The regional context statements could not be loaded");
    await expect(sec.locator(".ctx-entry")).toHaveCount(0);
    // The fixed block is there whether or not the file loads.
    await expect(sec.getByRole("note", { name: "Why there is no tanker map" })).toBeVisible();
    // Everything else on the page is whole: the map, the table, the cards, the impact records, the feed.
    await expect(page.locator(".group-table")).toBeVisible();
    await expect(page.getByRole("region", { name: "Monitored systems in this view" }).getByRole("article")).toHaveCount(8);
    await expect(page.getByRole("region", { name: "Reviewed impact records for this region" }).getByRole("list", { name: "Impact records, newest first" }).locator(".impact-card")).toHaveCount(records.length);
    await expect(page.getByRole("region", { name: "Recent reviewed events in this region" })).toBeVisible();
    await expect(page.locator(".group-tell")).toContainText("Could not be loaded just now");
    // The brief still downloads, and says in words that the statements could not be loaded.
    const [download] = await Promise.all([page.waitForEvent("download"), app.button("Download impact brief (PNG)").click()]);
    expect(readBytes((await download.path())!).subarray(1, 4).toString("ascii")).toBe("PNG");
  });

  test("a wrong-shaped regional context is refused whole, not half-shown", async ({ app, page }) => {
    app.allowConsoleError(/malformed|regional_context/i);
    await serveLayer(page, { context: (c) => ({ ...c, entries: [{ id: "x" }] as unknown as Entry[] }) });
    await app.open("?group=gulf&section=context");
    await expect(section(page, "context").getByRole("alert")).toContainText("could not be loaded");
    await expect(section(page, "context").locator(".ctx-entry")).toHaveCount(0);
    await expect(page.locator(".group-table")).toBeVisible();
  });

  test("a missing impacts.json: both record sections say it failed, never that there are none", async ({ app, page }) => {
    app.allowConsoleError(/status of 404|404|impacts/i);
    const { context } = await serveLayer(page);
    await page.unroute("**/data/global/impacts.json");
    await page.route("**/data/global/impacts.json", (r) => r.fulfill({ status: 404, body: "" }));
    await app.open("?group=gulf&section=impacts");
    const region = page.getByRole("region", { name: "Reviewed impact records for this region" });
    await expect(region.getByRole("alert")).toContainText("That is a failed download, not a finding");
    expect(await region.innerText()).not.toMatch(/No impact record/);
    await expect(section(page, "services").getByRole("alert")).toContainText("could not be loaded");
    // The context timeline, a different file, is unaffected.
    await expect(section(page, "context").locator(".ctx-entry")).toHaveCount(context.entries.length);
    await expect(page.getByRole("region", { name: "Recent reviewed events in this region" })).toBeVisible();
  });
});
