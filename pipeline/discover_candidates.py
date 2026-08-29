"""EXPERIMENTAL candidate discovery (iteration 6, §29-30). Opt-in, best-effort, human-gated.

What it does: queries a no-key PUBLIC news-aggregation feed (GDELT DOC 2.0) for possible
reports of strikes on Russian energy infrastructure, and writes each hit to a NEEDS-REVIEW
queue as a bare pointer: headline + article URL + domain + date. Nothing more.

What it deliberately does NOT do — these are scope guarantees, not omissions:
  * It never writes to the scored dataset. The queue lives under data/review/ and the daily
    build (pipeline.run) does not import or read it. A curated incident only ever exists
    because a human read the source and hand-added a sourced row to data/curated/incidents.csv.
  * It never assigns a location, a coordinate, a facility, a capacity, or a score. A candidate
    is a link to a public article for a human to judge — not an aggregated intelligence record.
  * It fails safely. Any network, timeout, or parse error yields an EMPTY result and changes
    nothing; it can never break the build (which never calls it anyway).

Why it is bounded this way: this project models publicly documented STRUCTURE, not operational
activity. An automated feed that inferred locations or scored events would drift toward
operational tracking, which is out of scope and must stay out. Keeping discovery at the level
of "here is a public news link, a human should look" preserves the open-source, human-in-the-
loop discipline the brief requires. If a robust, in-scope automated mechanism cannot be had,
the honest answer (per §30) is exactly this: a triage aid, not an ingestion pipeline.

Run manually:  .venv\\Scripts\\python.exe -m pipeline.discover_candidates
"""

import csv
import datetime as dt
import json
import urllib.parse
import urllib.request
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent.parent / "data" / "review"
QUEUE = REVIEW_DIR / "candidates.csv"

# A tight query: energy-infrastructure terms AND Russia, in English news. Kept narrow so the
# queue stays a triage aid, not a firehose. GDELT DOC 2.0 needs no API key.
_GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
_QUERY = '(refinery OR "oil depot" OR "gas processing" OR substation OR "power plant") ' \
         'AND (drone OR strike OR attack) AND Russia'

_FIELDS = ["discovered_at", "title", "url", "domain", "seendate", "status", "reviewed"]


def discover(days_back=3, max_records=25, timeout=15):
    """Return a list of candidate pointers, or [] on ANY failure. Never raises."""
    try:
        params = {
            "query": _QUERY, "mode": "ArtList", "format": "json",
            "maxrecords": str(int(max_records)), "sort": "DateDesc",
            "timespan": f"{int(days_back)}d",
        }
        url = f"{_GDELT}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "russia-energy-atlas/research"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception as exc:  # network, timeout, JSON, anything — fail safely
        print(f"discover: no candidates ({type(exc).__name__}); queue unchanged")
        return []

    out, seen = [], set()
    for a in (data.get("articles") or []):
        u = a.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        out.append({
            "title": (a.get("title") or "").strip(),
            "url": u,
            "domain": a.get("domain") or "",
            "seendate": a.get("seendate") or "",
            # A candidate is ONLY a pointer. No location, no facility, no score — by design.
            "status": "needs_review",
            "reviewed": "no",
        })
    return out


def write_queue(candidates, discovered_at, path=QUEUE):
    """Merge new candidates into the review queue by URL, preserving any human triage already
    recorded (status/reviewed) on rows a curator has touched."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if path.exists():
        with open(path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                existing[row["url"]] = row
    added = 0
    for c in candidates:
        if c["url"] in existing:
            continue  # keep the curator's version, never clobber a reviewed row
        existing[c["url"]] = {"discovered_at": discovered_at, **c}
        added += 1
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDS)
        w.writeheader()
        for row in existing.values():
            w.writerow({k: row.get(k, "") for k in _FIELDS})
    return added, len(existing)


def main():
    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    cands = discover()
    added, total = write_queue(cands, stamp)
    print(f"discover: {len(cands)} fetched, {added} new -> {QUEUE} ({total} in queue). "
          "These are UNVERIFIED pointers for human review; none are scored or located.")


if __name__ == "__main__":
    main()
