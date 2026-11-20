import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test, expect } from "./fixtures";

/**
 * Iteration-22 release closure, in a real browser.
 *
 * The impact files are the pipeline's synthetic fixture (e2e/fixtures/impacts22), changed here in
 * the test, never on disk, to carry the shapes this release adds: a self-claim on an attribution, a
 * record not yet served (first_published null), and two statements of one kind sharing the newest
 * date. Every record and statement is invented.
 */

type Page = import("@playwright/test").Page;
type Json = Record<string, unknown>;
type Rec = Json & { impact_id: string; attribution: Json & { status: string; competing: unknown[] }; first_published: string | null };
type Entry = Json & { id: string; context_type: string; as_of: string; date: string; is_latest_of_type: boolean };

const fixture = (name: string) => JSON.parse(readFileSync(fileURLToPath(new URL(`./fixtures/impacts22/global/${name}`, import.meta.url)), "utf-8"));
const CLAIM = "SYNTHETIC Group Z said on its own channel that it carried out the incident.";
const SELF_CLAIM = { actor: "SYNTHETIC Group Z", actor_type: "hacktivist", statement: CLAIM, source_refs: [] };

async function serve(page: Page, change: { impacts?: (p: Json & { records: Rec[] }) => void; context?: (c: Json & { entries: Entry[] }) => void } = {}) {
  const impacts = fixture("impacts.json");
  const context = fixture("regional_context.json");
  change.impacts?.(impacts);
  change.context?.(context);
  await page.route("**/data/global/impacts.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(impacts) }));
  await page.route("**/data/global/regional_context.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(context) }));
  await page.route("**/data/global/evidence_confidence.json", (r) => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fixture("evidence_confidence.json")) }));
  return { impacts, context };
}

async function openAtlas(page: Page, query = "") {
  await page.goto(`/?view=impacts${query}`);
  await expect(page.getByRole("heading", { name: "Impact atlas", level: 1 })).toBeVisible();
  await expect(page.getByTestId("atlas-summary")).toBeVisible();
}

test.describe("closure: self-claims", () => {
  test("a self-claim is its own line, never in the competing list and never the attribution; the inspector cites it apart", async ({ page }) => {
    await serve(page, { impacts: (p) => { for (const r of p.records) if (r.attribution.status === "DISPUTED" || r.attribution.status === "ASSESSED") r.attribution.self_claims = [SELF_CLAIM]; } });
    await openAtlas(page);
    const disputed = page.locator(".atlas-timeline .impact-card").filter({ has: page.locator(".attr-disputed") }).first();
    await expect(disputed.locator(".attr-self-claim")).toHaveText(`Self-claim (unverified): ${CLAIM}`);
    await expect(disputed.locator(".attr-competing")).not.toContainText("Group Z");
    await expect(disputed.locator(".attr-competing li")).toHaveCount(2);
    const assessed = page.locator(".atlas-timeline .impact-card").filter({ has: page.locator(".attr-assessed") }).first();
    await expect(assessed.locator(".attr-line")).toContainText("Self-claim (unverified)");
    // The attribution itself still names the assessed actor, not the claimant.
    expect((await assessed.locator(".attr-line").innerText()).split("\n")[0]).not.toContain("Group Z");
    await assessed.getByRole("button", { name: /^Sources \(/ }).click();
    const insp = assessed.getByRole("region", { name: "Evidence inspector" });
    await expect(insp.getByRole("heading", { name: "Self-claims of responsibility (unverified)" })).toBeVisible();
    await expect(insp).toContainText("A self-claim is not corroboration");
  });
});

test.describe("closure: a record not yet served", () => {
  test("first_published null is never shown as a date anywhere in the atlas", async ({ page }) => {
    await serve(page, { impacts: (p) => { for (const r of [...p.records, ...(p.attempts as Rec[])]) r.first_published = null; } });
    await openAtlas(page);
    await expect(page.locator(".atlas-timeline .impact-card").first()).toBeVisible();
    const body = await page.locator("main, body").first().innerText();
    expect(body).not.toMatch(/\bnull\b|Invalid Date|1970|NaN/);
    await expect(page.locator(".impact-historical")).toHaveCount(0);
  });
});

test.describe("closure: tied newest statements", () => {
  test("two statements of one kind on the newest date are both 'as of' it, in the plural, on the Gulf page", async ({ app, page }) => {
    const { context } = await serve(page, { context: (c) => {
      const newest = c.entries.find((e) => e.context_type === "shipping_status" && e.is_latest_of_type)!;
      c.entries.push({ ...newest, id: "ctx-synthetic-tied-shipping", claim: "SYNTHETIC second shipping statement of the same date.", date: newest.date });
      c.latest_by_type = Object.fromEntries([...new Set(c.entries.map((e) => e.context_type))].map((t) => {
        const of = c.entries.filter((e) => e.context_type === t);
        const max = of.map((e) => e.as_of).sort().at(-1);
        return [t, of.filter((e) => e.as_of === max).map((e) => e.id)];
      }));
    } });
    await app.open("?group=gulf&section=context");
    const sec = page.locator("#sec-context");
    await expect(sec.locator(".ctx-entry")).toHaveCount((context.entries as Entry[]).length);
    await expect(sec.locator(".ctx-asof").filter({ hasText: /one of the 2 most recent shipping, in aggregate statements on record/i })).toHaveCount(2);
    await expect(sec.locator(".ctx-asof").filter({ hasText: /the most recent shipping, in aggregate statement on record/i })).toHaveCount(0);
  });
});

test.describe("closure: Gulf placement rules", () => {
  test("the page says attacks are country level in the impact layer, the admin1 system's own-page rule, and region at most otherwise", async ({ app, page }) => {
    await app.open("?group=gulf");
    const g = await (await page.request.get("/data/global/gulf.json")).json() as { systems: { name: string; attack_records_placed?: string }[] };
    const rules = page.locator(".precision-rules");
    await expect(rules).toContainText("In the impact records on this page that holds for every country, always.");
    await expect(rules).toContainText("Records that are not attacks are placed by first-level region at most");
    for (const s of g.systems.filter((x) => x.attack_records_placed === "admin1")) await expect(rules).toContainText(s.name);
    const cards = page.getByRole("region", { name: "Monitored systems in this view" });
    for (const s of g.systems) {
      const line = cards.getByRole("article", { name: s.name, exact: true }).locator(".attack-placement");
      await expect(line).toContainText("Other eligible records: first-level region at most.");
      await expect(line).toContainText(s.attack_records_placed === "admin1" ? "In the impact records on this page they are country level" : "Attacks and sabotage are recorded for the country as a whole");
    }
  });
});
