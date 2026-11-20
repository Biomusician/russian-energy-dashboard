/** How precisely a regional group's records are placed, in words (iteration 22 closure).
 *
 *  Three different things, never blurred into one "first-level region at most":
 *  - an attack or sabotage record is placed at country level, and in the global impact layer
 *    always, whatever the country;
 *  - a system whose `attack_records_placed` is "admin1" (served: the earlier rule, kept under the
 *    project's current decision) places attack records by first-level region on its own page;
 *  - a record that is not an attack is placed by first-level region at most, where it is eligible
 *    for one at all.
 *
 *  Which systems are which is read from the served field; no country is named here. Pure.
 */

export type AttackPlacement = "country" | "admin1";

const OTHERS = "Other eligible records: first-level region at most.";

/** The line on a system's card. */
export function attackPlacementText(placed: AttackPlacement): string {
  return placed === "country"
    ? `Attacks and sabotage are recorded for the country as a whole, with no region or facility. ${OTHERS}`
    : "Attacks are recorded by first-level region, with the facility named, on this country's own page: the earlier rule under which "
      + `this system was added, kept under the project's current decision. In the impact records on this page they are country level. ${OTHERS}`;
}

function listNames(names: readonly string[]): string {
  if (names.length <= 1) return names[0] ?? "";
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

/** The paragraph in "How to read this page". `systems` in the served (alphabetical) order. */
export function precisionRulesText(systems: readonly { name: string; attack_records_placed?: AttackPlacement }[]): { lead: string; body: string } {
  const earlier = systems.filter((s) => s.attack_records_placed === "admin1").map((s) => s.name);
  const body = [
    "An attack or sabotage record is placed for the country as a whole, with no region, facility or operator, because in a small or concentrated system a region and a kind of facility together can name one site.",
    "In the impact records on this page that holds for every country, always.",
    earlier.length > 0
      ? `${listNames(earlier)} ${earlier.length === 1 ? "places its" : "place their"} own attack records by first-level region, with the facility named, on ${earlier.length === 1 ? "its own country page" : "their own country pages"}: the earlier rule, kept under the project's current decision.`
      : null,
    "Records that are not attacks are placed by first-level region at most, where they are eligible for a region at all.",
    "Each card below says which rule applies.",
  ].filter(Boolean).join(" ");
  return { lead: earlier.length > 0 ? "Countries are recorded under two rules." : "How precisely records are placed.", body };
}
