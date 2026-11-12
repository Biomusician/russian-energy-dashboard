"""Check every citation URL of the country systems, slowly (iteration 18; all twelve since 20).

    .venv\\Scripts\\python.exe scripts\\check_source_links.py

An ANALYST step, never part of the daily build: a media link that fails today says nothing about
the record, so a failed link is recorded and never stops publication.

Writes two files:
  data/candidates/review20/link_check.json   per URL, local: state, checked_at, final address,
                                             whether it redirected, the page's own <title>, hash
  data/curated/systems/source_link_health.json   counts per country, and page-stated publication
                                                 dates keyed by URL (only for pages that state one)

States: reachable, redirected (reached at a different address), blocked (401, 402, 403, 429 or a
bot challenge; never retried or worked around), dead (404, 410, DNS failure), error (timeout or
5xx). `changed_content` needs a previous run's page hash, so the first run cannot report it.

A publication date is taken only from the page's own metadata (article:published_time,
datePublished and similar). It is never inferred from a URL or from the retrieval date. A date
recorded by an earlier run is kept: a re-check updates a link's health, never its history.

Iteration 20. A host that refuses once (blocked) is not asked again in the same run, and a short
or redirecting link (`?p=123`, a shortener, an amp redirect) is flagged so the citation can be
replaced by the final article address. The page body is hashed and dropped; only its <title> is
kept, locally, so a reviewer can check that the title is safe to publish beside the record.
"""
import hashlib
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / "data" / "candidates" / os.environ.get("EDM_REVIEW_DIR", "review20") / "link_check.json"
PUBLIC = ROOT / "data" / "curated" / "systems" / "source_link_health.json"
# Every country system. The seven Gulf systems added in iteration 19 were first checked in 20.
SYSTEMS = ("ae", "bh", "ca", "cn", "in", "iq", "ir", "kw", "om", "qa", "sa", "us")
CHECKED = os.environ.get("EDM_CHECK_DATE") or __import__("datetime").date.today().isoformat()
SHORT_LINK = re.compile(r"[?&]p=\d+$|^https?://(bit\.ly|t\.co|goo\.gl|ow\.ly|tinyurl\.com|buff\.ly|amzn\.to)/"
                        r"|/amp/?$|[?&](amp|outputType=amp)\b|^https?://amp\.", re.I)
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
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


def ascii_url(url):
    """The address as a request line can carry it: non-ASCII path and query characters
    percent-encoded, the host IDNA-encoded. The recorded citation keeps its original spelling."""
    p = urllib.parse.urlsplit(url)
    host = p.hostname.encode("idna").decode("ascii") if p.hostname else ""
    netloc = host + (f":{p.port}" if p.port else "")
    return urllib.parse.urlunsplit((p.scheme, netloc, urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;=-._~"),
                                    urllib.parse.quote(p.query, safe="=&%:@!$'()*+,;/?-._~"), ""))


def fetch(url):
    req = urllib.request.Request(ascii_url(url), headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context()) as r:
            body = r.read(READ_BYTES)
            final = r.geturl()
            state = "redirected" if _norm(final) != _norm(ascii_url(url)) else "reachable"
            kind = r.headers.get("Content-Type", "")
            text = body.decode("utf-8", "replace") if "html" in kind or not kind else ""
            if re.search(r"just a moment|enable javascript and cookies|attention required", text[:4000], re.I):
                return {"state": "blocked", "http": r.status}
            t = TITLE.search(text) if text else None
            return {"state": state, "http": r.status, "final": final if state == "redirected" else None,
                    "final_url": final, "redirect": state == "redirected",
                    "title": re.sub(r"\s+", " ", t.group(1)).strip()[:240] if t else None,
                    "hash": hashlib.sha256(body).hexdigest()[:16], "page_date": page_date(text) if text else None}
    except urllib.error.HTTPError as e:
        state = "blocked" if e.code in (401, 402, 403, 406, 429, 451) else "dead" if e.code in (404, 410) else "error"
        return {"state": state, "http": e.code}
    except urllib.error.URLError as e:
        return {"state": "dead" if "getaddrinfo" in str(e.reason) else "error", "http": None, "detail": str(e.reason)[:80]}
    except Exception as e:  # a timeout or a malformed response is one failed link, not a failed run
        return {"state": "error", "http": None, "detail": type(e).__name__}


CHALLENGE = re.compile(r"\.within\.website|captcha|/login|/signin|consent\.|/challenge", re.I)
TRACKING = re.compile(r"^(utm_[a-z]+|_guid[a-z_]*|fbclid|gclid|cmpid|ref)$", re.I)


def classify_redirect(url, final):
    """canonical (an article), general_page (a home page or listing: the article is gone) or
    challenge (a bot check: a refusal). An article address ends in a slug of three or more words
    or carries an id of four or more digits."""
    if CHALLENGE.search(final):
        return "challenge"
    last = [seg for seg in urllib.parse.unquote(urllib.parse.urlsplit(final).path).split("/") if seg][-1:] or [""]
    slug = re.sub(r"\.(html?|php|aspx?)$", "", last[0])
    # An id anywhere in the path counts ("/edgar/data/1534504/000153450426000029/a991....htm").
    if len([w for w in re.split(r"[-_]+", slug) if w]) >= 3 or re.search(r"\d{4,}", urllib.parse.urlsplit(final).path):
        return "canonical"
    return "general_page"


def clean_final(final):
    """The adopted address without a default port or tracking parameters."""
    p = urllib.parse.urlsplit(final)
    netloc = re.sub(r":(443|80)$", "", p.netloc)
    query = urllib.parse.urlencode([(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
                                    if not TRACKING.match(k)])
    return urllib.parse.urlunsplit((p.scheme, netloc, p.path, query, ""))


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
    # --retry-errors: keep every earlier answer except a failure to load, which is asked once more.
    retry_only = "--retry-errors" in sys.argv
    last_hit, results, refused = {}, {}, set()
    LOCAL.parent.mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(sorted(urls, key=lambda u: urllib.parse.urlsplit(u).netloc)):
        host = urllib.parse.urlsplit(url).netloc
        if retry_only and url in previous and previous[url].get("state") != "error":
            results[url] = previous[url]
            continue
        if host in refused:
            # One refusal is the site's answer for this run; asking again is working around it.
            results[url] = {"state": "blocked", "http": None, "detail": "host refused earlier in this run; not retried"}
        else:
            wait = PER_HOST_DELAY - (time.monotonic() - last_hit.get(host, -99))
            if wait > 0:
                time.sleep(wait)
            results[url] = fetch(url)
            last_hit[host] = time.monotonic()
            if results[url]["state"] == "blocked":
                refused.add(host)
        results[url]["checked_at"] = CHECKED
        results[url]["short_link"] = bool(SHORT_LINK.search(url))
        old = previous.get(url, {})
        if old.get("hash") and results[url].get("hash") and old["hash"] != results[url]["hash"]:
            results[url]["changed_content"] = True
        if (i + 1) % 25 == 0:
            LOCAL.write_text(json.dumps(results, ensure_ascii=False, indent=0), encoding="utf-8")
            print(i + 1, "of", len(urls), flush=True)
    # A short link the import already replaced is no longer cited; its answer is carried forward
    # while the address it lands on is still cited, so the import keeps the canonical address.
    for u, r in previous.items():
        if u not in results and r.get("redirect_kind") == "canonical" and clean_final(r.get("final_url") or "") in urls:
            results[u] = r
    for url, r in results.items():
        if r.get("redirect") and r.get("final_url"):
            kind = classify_redirect(url, r["final_url"])
            r["redirect_kind"] = kind
            if kind == "challenge":
                r["state"], r["detail"] = "blocked", "redirected to a bot challenge"
            elif kind == "general_page":
                r["state"], r["detail"] = "dead", "redirected to a home page or listing: the article is gone"
    LOCAL.write_bytes(json.dumps(results, ensure_ascii=False, indent=0).encode("utf-8"))
    counts = {}
    old_public = json.loads(PUBLIC.read_text(encoding="utf-8")) if PUBLIC.exists() else {}
    dates = dict(old_public.get("page_stated_dates") or {})
    for u, r in results.items():
        if r.get("page_date") and u not in dates:
            dates[u] = r["page_date"]
    for url, sids in urls.items():
        if url not in results:
            continue
        for sid in sids:
            c = counts.setdefault(sid, {k: 0 for k in ("reachable", "redirected", "blocked", "dead", "error")})
            c[results[url]["state"]] += 1
    PUBLIC.write_bytes((json.dumps({
        "checked": CHECKED,
        "note": ("One automated visit to each cited page. Blocked means the site refused an automated visitor, not that "
                 "the page is gone. Redirects to a home page or listing count as gone; redirects to a bot check count as blocked."),
        "by_system": dict(sorted(counts.items())),
        "page_stated_dates": dict(sorted((u, d) for u, d in dates.items() if u in urls)),
        # Where a redirecting citation lands. The import cites this address instead, and judges an
        # attack record's citation by it (iteration 20).
        "final_addresses": dict(sorted((u, clean_final(r["final_url"])) for u, r in results.items()
                                       if r.get("redirect_kind") == "canonical"
                                       and (u in urls or clean_final(r["final_url"]) in urls))),
    }, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print("done", {k: sum(c[k] for c in counts.values()) for k in ("reachable", "redirected", "blocked", "dead", "error")}, file=sys.stderr)


if __name__ == "__main__":
    main()
