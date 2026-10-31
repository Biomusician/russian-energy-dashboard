"""Wikipedia wikitext pinned to a revision (iteration 15).

WHY. Three inputs to the theatre build are live Wikipedia articles: the strike table, the
refinery list and the fuel-crisis coverage benchmark. Until iteration 15 every build read the
CURRENT revision, so `--as-of 2026-08-28` did not rebuild the record as it stood on 2026-08-28.
It rebuilt today's article and filtered it by date. Editors revise old rows, add citations and
correct dates, and the frozen regression drifted from 18.50 to 16.8 with no code change
(ITERATION_14_REVIEW §9). A historical build that changes when someone edits Wikipedia is not
a historical build.

WHAT IT DOES.
- A current-date build reads the latest revision, exactly as before, and now records which
  revision that was (id and timestamp) so any published build can be re-fetched by `oldid`.
- A build whose `as_of` is in the past reads the last revision saved on or before the end of
  that day (UTC). Revisions never change, so that fetch is cached indefinitely: the second
  historical build of the same date is byte-for-byte the same input.

WHAT IT DOES NOT DO. It does not make the whole build immutable. OSM geometry, the curated CSVs
and the code are read as they are now; the curated files are versioned by git, and the change
ledger already reports which input group moved. This removes the one input that changed under
a fixed commit.
"""

import datetime as dt
import urllib.parse

from pipeline.util import fetch_json

API = "https://en.wikipedia.org/w/api.php"
# A pinned revision is immutable, so its cache never needs refreshing.
FOREVER_HOURS = 24 * 365 * 100


def is_historical(as_of, today=None):
    """True when `as_of` is strictly before today: only then is there a past revision to pin."""
    return bool(as_of) and as_of < (today or dt.date.today().isoformat())


def latest_url(page):
    return f"{API}?action=parse&page={page}&prop=wikitext%7Crevid&format=json&formatversion=2"


def as_of_url(page, as_of):
    """The last revision saved on or before the end of `as_of` (UTC)."""
    title = urllib.parse.unquote(page).replace("_", " ")
    params = {
        "action": "query", "prop": "revisions", "titles": title, "rvlimit": "1",
        "rvdir": "older", "rvstart": f"{as_of}T23:59:59Z",
        "rvprop": "ids|timestamp|content", "rvslots": "main",
        "format": "json", "formatversion": "2",
    }
    return f"{API}?{urllib.parse.urlencode(params)}"


def parse_latest(payload):
    p = payload["parse"]
    return p["wikitext"], {"revid": p.get("revid"), "timestamp": None}


def parse_as_of(payload):
    pages = payload.get("query", {}).get("pages", [])
    revs = pages[0].get("revisions") if pages else None
    if not revs:
        raise RuntimeError("no revision of the article existed on that date")
    r = revs[0]
    return r["slots"]["main"]["content"], {"revid": r["revid"], "timestamp": r["timestamp"]}


def load(page, cache_name, as_of=None, max_age_hours=12):
    """(wikitext, revision) for `page`, pinned to `as_of` when that date is in the past.

    `revision` is {"page", "revid", "timestamp", "pinned_to", "url"}. `pinned_to` is the as-of
    date for a historical build and None for a current one. `url` opens the exact revision.
    """
    if is_historical(as_of):
        stem = cache_name.rsplit(".", 1)[0]
        payload = fetch_json(as_of_url(page, as_of), f"wikirev/{stem}@{as_of}.json",
                             max_age_hours=FOREVER_HOURS)
        text, rev = parse_as_of(payload)
        pinned = as_of
    else:
        payload = fetch_json(latest_url(page), cache_name, max_age_hours=max_age_hours)
        text, rev = parse_latest(payload)
        pinned = None
    revid = rev["revid"]
    return text, {
        "page": urllib.parse.unquote(page).replace("_", " "),
        "revid": revid,
        "timestamp": rev["timestamp"],
        "pinned_to": pinned,
        "url": f"https://en.wikipedia.org/w/index.php?oldid={revid}" if revid else None,
    }
