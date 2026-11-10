"""Check every citation URL of the country systems, slowly (iteration 18).

    .venv\\Scripts\\python.exe scripts\\check_source_links.py

An ANALYST step, never part of the daily build: a media link that fails today says nothing about
the record, so a failed link is recorded and never stops publication.

Writes two files:
  data/candidates/review18/link_check.json   per URL, local: state, final address, page hash
  data/curated/systems/source_link_health.json   counts per country, and page-stated publication
                                                 dates keyed by URL (only for pages that state one)

States: reachable, redirected (reached at a different address), blocked (401, 402, 403, 429 or a
bot challenge; never retried or worked around), dead (404, 410, DNS failure), error (timeout or
5xx). `changed_content` needs a previous run's page hash, so the first run cannot report it.

A publication date is taken only from the page's own metadata (article:published_time,
datePublished and similar). It is never inferred from a URL or from the retrieval date.
"""
import hashlib
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / "data" / "candidates" / "review18" / "link_check.json"
PUBLIC = ROOT / "data" / "curated" / "systems" / "source_link_health.json"
SYSTEMS = ("us", "ca", "cn", "in", "sa")
CHECKED = "2026-11-10"
PER_HOST_DELAY = 3.0
TIMEOUT = 25
READ_BYTES = 300_000
UA = "Mozilla/5.0 (compatible; research link check)"

META_DATE = re.compile(
    r"""(?:property|name|itemprop)\s*=\s*["'](?:article:published_time|og:article:published_time|datePublished|publish[-_]?date|pubdate|date|dc\.date|dcterms\.created|sailthru\.date)["'][^>]*?content\s*=\s*["'](\d{4}-\d{2}-\d{2})"""
    r"""|content\s*=\s*["'](\d{4}-\d{2}-\d{2})[^"']*["'][^>]*?(?:property|name|itemprop)\s*=\s*["'](?:article:published_time|datePublished|publish[-_]?date|pubdate)["']"""
    r"""|["']datePublished["']\s*:\s*["'](\d{4}-\d{2}-\d{2})""", re.I)


def page_date(html):
    m = META_DATE.search(html)
    if not m:
        return None
    d = next(x for x in m.groups() if x)
    return d if "2021-01-01" <= d <= CHECKED else None


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context()) as r:
            body = r.read(READ_BYTES)
            final = r.geturl()
            state = "redirected" if _norm(final) != _norm(url) else "reachable"
            kind = r.headers.get("Content-Type", "")
            text = body.decode("utf-8", "replace") if "html" in kind or not kind else ""
            if re.search(r"just a moment|enable javascript and cookies|attention required", text[:4000], re.I):
                return {"state": "blocked", "http": r.status}
            return {"state": state, "http": r.status, "final": final if state == "redirected" else None,
                    "hash": hashlib.sha256(body).hexdigest()[:16], "page_date": page_date(text) if text else None}
    except urllib.error.HTTPError as e:
        state = "blocked" if e.code in (401, 402, 403, 406, 429, 451) else "dead" if e.code in (404, 410) else "error"
        return {"state": state, "http": e.code}
    except urllib.error.URLError as e:
        return {"state": "dead" if "getaddrinfo" in str(e.reason) else "error", "http": None, "detail": str(e.reason)[:80]}
    except Exception as e:  # a timeout or a malformed response is one failed link, not a failed run
        return {"state": "error", "http": None, "detail": type(e).__name__}


def _norm(u):
    p = urllib.parse.urlsplit(u)
    return (p.netloc.lower().removeprefix("www."), p.path.rstrip("/"))


def main():
    urls = {}
    for sid in SYSTEMS:
        events = json.loads((ROOT / "data" / "curated" / "systems" / sid / "events.json").read_text(encoding="utf-8"))["events"]
        for e in events:
            for s in e["sources"]:
                urls.setdefault(s["url"], set()).add(sid)
            if e["recovery"].get("url"):
                urls.setdefault(e["recovery"]["url"], set()).add(sid)
    previous = json.loads(LOCAL.read_text(encoding="utf-8")) if LOCAL.exists() else {}
    last_hit, results = {}, {}
    for i, url in enumerate(sorted(urls, key=lambda u: urllib.parse.urlsplit(u).netloc)):
        host = urllib.parse.urlsplit(url).netloc
        wait = PER_HOST_DELAY - (time.monotonic() - last_hit.get(host, -99))
        if wait > 0:
            time.sleep(wait)
        results[url] = fetch(url)
        last_hit[host] = time.monotonic()
        old = previous.get(url, {})
        if old.get("hash") and results[url].get("hash") and old["hash"] != results[url]["hash"]:
            results[url]["changed_content"] = True
        if (i + 1) % 25 == 0:
            LOCAL.write_text(json.dumps(results, ensure_ascii=False, indent=0), encoding="utf-8")
            print(i + 1, "of", len(urls), flush=True)
    LOCAL.write_text(json.dumps(results, ensure_ascii=False, indent=0), encoding="utf-8")
    counts = {}
    for url, sids in urls.items():
        for sid in sids:
            c = counts.setdefault(sid, {k: 0 for k in ("reachable", "redirected", "blocked", "dead", "error")})
            c[results[url]["state"]] += 1
    PUBLIC.write_text(json.dumps({
        "checked": CHECKED,
        "note": ("One automated visit to each cited page. Blocked means the site refused an automated visitor, not that "
                 "the page is gone. Changed content needs an earlier visit to compare with, so this first run cannot report it."),
        "by_system": dict(sorted(counts.items())),
        "page_stated_dates": {u: r["page_date"] for u, r in sorted(results.items()) if r.get("page_date")},
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("done", {k: sum(c[k] for c in counts.values()) for k in ("reachable", "redirected", "blocked", "dead", "error")}, file=sys.stderr)


if __name__ == "__main__":
    main()
