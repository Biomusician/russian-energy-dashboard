/** How precisely a record is placed, in the ONE set of words every surface uses: the home and Gulf
 *  lists, the country page's cards, filters and headings, Compare and the glossary.
 *
 *  Four placements, because the data makes four distinctions:
 *  - a record about the whole country;
 *  - one record that spans several regions;
 *  - a record placed in one region;
 *  - an attack record kept at the country level by the attack-campaign safeguards.
 *  The first and the last both read "National", on purpose: in a list that sets countries side by
 *  side both are shown for the country as a whole, and the What's new list cannot tell them apart.
 *  The safeguarded one always says so and carries its list entry.
 *
 *  No imports, so evidence.ts (which the Python suite runs in Node) can take the type from here.
 */

export type Placement = "national" | "several_regions" | "one_region" | "national_safeguarded";

export const PLACEMENTS: Placement[] = ["national", "several_regions", "one_region", "national_safeguarded"];

export const PLACEMENT_LABEL: Record<Placement, string> = {
  national: "National",
  several_regions: "Several regions",
  one_region: "One region",
  national_safeguarded: "National, under safeguards",
};

export const PLACEMENT_MEANING: Record<Placement, string> = {
  national: "About the country as a whole; not placed in any one region.",
  several_regions: "One record that spans more than one region. It is listed, never counted against any single region.",
  one_region: "Placed in a single first-level region (a state, province or similar), named beside it.",
  national_safeguarded: "An attack record shown for the country as a whole because of the attack-campaign safeguards. "
    + "Lists that set countries side by side give it a list entry number instead of its own name.",
};

/** The data's own region strings in the lists that set countries side by side. */
const NATIONAL = "National";
const MULTIPLE = "Multiple regions";

/** One list member's place, in reader words: a named region stays its name. */
export function memberPlace(region: string, safeguarded: boolean): string {
  if (safeguarded) return PLACEMENT_LABEL.national_safeguarded;
  if (region === NATIONAL) return PLACEMENT_LABEL.national;
  if (region === MULTIPLE) return PLACEMENT_LABEL.several_regions;
  return region;
}

/** A What's new item's place. Its "National" may be either national placement, so it stays the
 *  shared word; only the build's "Multiple regions" is translated. */
export function itemPlace(region: string): string {
  return region === MULTIPLE ? PLACEMENT_LABEL.several_regions : region;
}

/** "list entry 15" from a row key such as "sa-row-15": the neutral key a list gives a safeguarded
 *  record instead of its own id. Any other shape is shown whole, never dropped. */
export function listEntry(rowKey: string): string {
  const m = /-row-(\d+)$/.exec(rowKey);
  return `list entry ${m ? String(Number(m[1])) : rowKey}`;
}

export const LIST_ENTRY_NOTE = "Published under the attack-campaign safeguards: the list entry number stands in for the record's own name. See the country page.";
