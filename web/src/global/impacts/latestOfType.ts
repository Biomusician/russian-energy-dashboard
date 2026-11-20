/** Which regional-context statements are the newest of their type (iteration 22 closure).
 *
 *  Several statements of one type can share the newest "as of" date. All of them are the latest;
 *  none is picked over the others, and copy that speaks of "the most recent statement" must say
 *  "statements" when a type has more than one.
 *
 *  The served `latest_by_type` ({type: [ids]}) is used as it is. An older payload without it is
 *  read from the entries, type by type: where the build flagged entries (`is_latest_of_type`), the
 *  flagged ones and any entry of that type tied with them on "as of"; where it flagged none, every
 *  entry on the type's newest "as of". A served flag is never taken away.
 *
 *  Pure: no React, no DOM. The brief, the timeline and the country tab all read it.
 */

export interface LatestEntry {
  id?: string;
  context_type: string;
  as_of: string;
  is_latest_of_type?: boolean | null;
}

function servedMap(v: unknown): Record<string, string[]> | null {
  if (typeof v !== "object" || v === null || Array.isArray(v)) return null;
  const out: Record<string, string[]> = {};
  for (const [k, ids] of Object.entries(v as Record<string, unknown>)) {
    if (!Array.isArray(ids)) return null;
    out[k] = ids.filter((x): x is string => typeof x === "string");
  }
  return out;
}

/** The latest entries, by identity. `latestByType` is the served map, when the payload has one. */
export function latestEntries<T extends LatestEntry>(entries: readonly T[], latestByType?: unknown): Set<T> {
  const served = servedMap(latestByType);
  if (served) {
    return new Set(entries.filter((e) => e.id != null && (served[e.context_type] ?? []).includes(e.id)));
  }
  const out = new Set<T>();
  const types = [...new Set(entries.map((e) => e.context_type))];
  for (const t of types) {
    const ofType = entries.filter((e) => e.context_type === t);
    const flagged = ofType.filter((e) => e.is_latest_of_type === true);
    const days = new Set(flagged.length > 0
      ? flagged.map((e) => e.as_of)
      : [ofType.map((e) => e.as_of).reduce((a, b) => (b > a ? b : a))]);
    for (const e of ofType) if (e.is_latest_of_type === true || days.has(e.as_of)) out.add(e);
  }
  return out;
}

/** How many latest statements each type has, among `entries`. */
export function latestCounts<T extends LatestEntry>(entries: readonly T[], latest: Set<T>): Map<string, number> {
  const n = new Map<string, number>();
  for (const e of entries) if (latest.has(e)) n.set(e.context_type, (n.get(e.context_type) ?? 0) + 1);
  return n;
}

/** True when any type has more than one latest statement: the copy must then be plural. */
export function anyTie(counts: Map<string, number>): boolean {
  return [...counts.values()].some((n) => n > 1);
}
