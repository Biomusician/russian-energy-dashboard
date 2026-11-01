import { test, expect } from "./fixtures";

/**
 * The three histories, in a real browser (iteration 16).
 *
 * CURRENT RECONSTRUCTION IS NOT AS-PUBLISHED HISTORY. A reconstruction is today's code and corpus
 * at a past date; as-published is what the deployed dashboard actually served. Each test names
 * the concept it validates.
 *
 * The October 9/10 values are fixed on purpose: they are archived publications, read from
 * deployed commits, and must never change. If one does, the history was rewritten.
 */

const OCT10_BACKFILL = [
  "gazprom-neftekhim-salavat:2026-10-08", "novoshakhtinsk-refinery:2026-09-25",
  "nps-samara-prosvet:2026-04-21", "nps-samara-prosvet:2026-10-02", "nps-samara-prosvet:2026-10-07",
  "omsk-refinery:2026-10-08", "perm-refinery:2026-09-25",
];

async function openCompare(app: import("./fixtures").App, concept: "Current reconstruction" | "As published") {
  await app.open();
  await app.button(/compare dates/i).click();
  await app.page.getByRole("group", { name: "Which history" }).getByRole("button", { name: concept }).click();
}

async function setDates(page: import("@playwright/test").Page, a: string, b: string) {
  const inputs = page.locator(".cmp-dates input[type=date]");
  await inputs.nth(0).fill(a);
  await inputs.nth(1).fill(b);
}

test.describe("as published (concept: as_published)", () => {
  test("October 9 and 10 show what was served, and the seven backfilled events as learned", async ({ app, page }) => {
    await openCompare(app, "As published");
    await setDates(page, "2026-10-09", "2026-10-10");
    const cells = page.locator(".published-cell");
    await expect(cells.nth(0)).toContainText("as published on");
    await expect(cells.nth(0)).toContainText("9.08");
    await expect(cells.nth(0)).toContainText("176 events");
    await expect(cells.nth(1)).toContainText("14.40");
    await expect(cells.nth(1)).toContainText("184 events");
    // Event date is not knowledge date: events dated weeks or months before October 9 were
    // first served on October 10.
    const learned = page.locator(".published-learned li");
    for (const id of OCT10_BACKFILL) await expect(learned.filter({ hasText: id })).toHaveCount(1);
    await expect(page.locator(".published-builds")).not.toContainText(/reconstruct/i);
  });

  test("before the first deployed build it is unavailable, not reconstructed", async ({ app, page }) => {
    await openCompare(app, "As published");
    await setDates(page, "2026-08-28", "2026-10-10");
    const a = page.locator(".published-cell").nth(0);
    await expect(a).toHaveClass(/unavailable/);
    await expect(a).toContainText("Unavailable on");
    await expect(a).not.toContainText(/\d+\.\d\d/);
  });

  test("the map does not pretend to be a past build", async ({ app, page }) => {
    await openCompare(app, "As published");
    await expect(page.locator(".comparison")).toContainText("The map shows the current build");
  });
});

test.describe("current reconstruction (concept: current_evidence_reconstruction)", () => {
  test("the default comparison is labelled a reconstruction and is never called as published", async ({ app, page }) => {
    await app.open();
    await app.button(/compare dates/i).click();
    const group = page.getByRole("group", { name: "Which history" });
    await expect(group.getByRole("button", { name: "Current reconstruction" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.locator(".comparison")).not.toContainText(/as published on/i);
  });

  test("the committed payload says it is the current build", async ({ app, page }) => {
    await app.open();
    const snap = await page.evaluate(async () => (await fetch("/data/snapshot.json")).json());
    expect(snap.history_concept.mode).toBe("current_build");
    expect(snap.history_concept.label).toBe("Current build");
  });
});

test.describe("export labels (both concepts)", () => {
  test("a briefing of an as-published comparison says AS PUBLISHED, on screen and in the file", async ({ app, page }) => {
    await openCompare(app, "As published");
    await setDates(page, "2026-10-09", "2026-10-10");
    await app.button(/briefing & export/i).click();
    await expect(page.locator(".brief-history-heading")).toHaveText("AS PUBLISHED ON 2026-10-09 AND 2026-10-10");
    // The caveat travels with the image: never "Reconstructed" for published figures, and it says
    // the map is today's build (history red team, iteration 16).
    const caveats = page.locator(".brief-caveat");
    await expect(caveats.filter({ hasText: "The map is today's build" })).toHaveCount(1);
    await expect(caveats.filter({ hasText: /Reconstructed/ })).toHaveCount(0);
    const [download] = await Promise.all([page.waitForEvent("download"), app.button(/download png/i).click()]);
    expect(download.suggestedFilename()).toMatch(/_as-published_2026-10-09_to_2026-10-10\.png$/);
  });

  test("a briefing of a reconstruction says CURRENT-EVIDENCE RECONSTRUCTION", async ({ app, page }) => {
    await openCompare(app, "Current reconstruction");
    await app.button(/briefing & export/i).click();
    await expect(page.locator(".brief-history-heading")).toContainText("CURRENT-EVIDENCE RECONSTRUCTION FOR");
    await expect(page.locator(".brief-history-heading")).not.toContainText("AS PUBLISHED");
  });

  test("a scrubbed past date says it is a reconstruction, beside the number", async ({ app, page }) => {
    // A shared d= link lands on a past date: the label must travel with the value.
    await app.open("?sys=ru&d=2026-10-10");
    await expect(page.locator(".esdi-meta .reconstruction-tag")).toContainText("CURRENT-EVIDENCE RECONSTRUCTION FOR 2026-10-10");
    await app.open("?sys=ru");
    await expect(page.locator(".esdi-meta .reconstruction-tag")).toHaveCount(0);
  });
});
