"""Check every citation URL, slowly: the country systems (iteration 18; all twelve since 20) or,
with --impacts, the global impact layer and the Gulf regional context (iteration 22).

    .venv\\Scripts\\python.exe scripts\\check_source_links.py
    .venv\\Scripts\\python.exe scripts\\check_source_links.py --impacts [--local PATH]

An ANALYST step, never part of the daily build: a media link that fails today says nothing about
the record, so a failed link is recorded and never stops publication.

Country systems: writes two files
  data/candidates/review20/link_check.json   per URL, local: state, checked_at, final address,
                                             whether it redirected, the page's own <title>, hash
  data/curated/systems/source_link_health.json   counts per country, and page-stated publication
                                                 dates keyed by URL (only for pages that state one),
                                                 and each cited URL's state (iteration 21)

Impact layer (--impacts): writes three files
  data/candidates/impacts22/link_check.json          per URL, local (or --local PATH)
  data/candidates/impacts22/link_check_summary.json  counts, refusing hosts, dead and deleted
                                                     citations and redirect-safety hits, local
  data/curated/global_impacts/link_health.json       {checked, note, link_states}: each published
                                                     citation's state, read by the impact build.
                                                     Nothing else: no title, hash, final address
                                                     or safety finding leaves the local files.

`--states-only` rewrites the public file's states from the last run's local results, visiting no
page. Run it after a record is withdrawn: the build refuses a state for an unpublished citation.

States: reachable, redirected (reached at a different address), blocked (401, 402, 403, 406, 429,
451, a bot challenge, or a server that refused or dropped the connection; never retried or worked
around), dead (404, 410, or a host DNS says does not exist, asked twice), error (timeout, TLS, 5xx,
or the checker's own failure), deleted (the page loaded and its own title or description says it
was removed or not found; impact layer only), unchecked (the run's request cap was reached).
Blocked is never dead, and a failure of the checker is never dead. The country systems' file
carries five states only: there `deleted` is written as dead and `unchecked` is left out.
`archived_copy` is a citation choice, not a check result: the checker never produces it.

A redirect to a home page or listing (the article is likely gone) is `dead` for the country
systems, as it has been since iteration 20. For the impact layer it stays `redirected`, because
the brief there defines dead strictly; the summary lists those citations for a reviewer.

`changed_content` needs a previous run's page hash, so the first run cannot report it.

A publication date is taken only from the page's own metadata (article:published_time,
datePublished and similar). It is never inferred from a URL or from the retrieval date. A date
recorded by an earlier run is kept: a re-check updates a link's health, never its history.

Iteration 20. A host that refuses once (blocked) is not asked again in the same run, and a short
or redirecting link (`?p=123`, a shortener, an amp redirect) is flagged so the citation can be
replaced by the final article address. The page body is hashed and dropped; only its <title> is
kept, locally, so a reviewer can check that the title is safe to publish beside the record.

Iteration 22, redirect safety. For every country-abstracted impact record, every impact record in
a Gulf littoral system and every regional-context entry, the cited address AND the address it
finally lands on are read with the pipeline's own address checks (region names of the Gulf
systems, facility and operator names held in the curated country records, attack method, status
wording, route wording). A hit is reported generically (id, field, kind of leak), never with the
words that matched; the citation must not be published until a reviewer decides.

Traffic: one GET per URL (the body is needed to see a bot wall or a removal notice, so a HEAD
first would double the requests), at least PER_HOST_DELAY seconds between two requests to one
host, a TIMEOUT, at most MAX_REQUESTS requests per run, a User-Agent that names the project and
nothing personal. No login, no cookie, no archive lookup, no retry after a refusal.
"""
import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / "data" / "candidates" / os.environ.get("EDM_REVIEW_DIR", "review20") / "link_check.json"
PUBLIC = ROOT / "data" / "curated" / "systems" / "source_link_health.json"
IMPACTS_CURATED = ROOT / "data" / "curated" / "global_impacts"
IMPACTS_PUBLIC = IMPACTS_CURATED / "link_health.json"
IMPACTS_LOCAL = ROOT / "data" / "candidates" / "impacts22" / "link_check.json"
# Every country system. The seven Gulf systems added in iteration 19 were first checked in 20.
SYSTEMS = ("ae", "bh", "ca", "cn", "in", "iq", "ir", "kw", "om", "qa", "sa", "us")
CHECKED = os.environ.get("EDM_CHECK_DATE") or __import__("datetime").date.today().isoformat()
SHORT_LINK = re.compile(r"[?&]p=\d+$|^https?://(bit\.ly|t\.co|goo\.gl|ow\.ly|tinyurl\.com|buff\.ly|amzn\.to)/"
                        r"|/amp/?$|[?&](amp|outputType=amp)\b|^https?://amp\.", re.I)
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
PER_HOST_DELAY = 3.0
TIMEOUT = 25
READ_BYTES = 300_000
MAX_REQUESTS = int(os.environ.get("EDM_LINK_MAX_REQUESTS") or 1500)
DNS_RETRY_WAIT = 10
# Names the project and nothing about the person running it: no address, no account, no repo URL.
UA = "Mozilla/5.0 (compatible; EnergyDisruptionMonitor-LinkCheck/2.0; open-source research link check)"

# The five states the country systems' file may carry (build_systems.LINK_STATES).
SYSTEM_STATES = ("reachable", "redirected", "blocked", "dead", "error")
BLOCKED_HTTP = (401, 402, 403, 406, 429, 451)
DEAD_HTTP = (404, 410)
# getaddrinfo's "no such host" and "name has no address" (POSIX and Windows numbering). A temporary
# failure (EAI_AGAIN, 11002) is the network's problem, not the host's: it is an error.
DNS_NOT_FOUND = {getattr(socket, "EAI_NONAME", -2), getattr(socket, "EAI_NODATA", -5), -2, -5, 11001, 11004}
BOT_WALL = re.compile(r"just a moment|enable javascript and cookies|attention required|checking your browser"
                      r"|verify you are (a )?human", re.I)
# What a page says about itself when its content is gone. Read only in its <title> and its meta
# title and description: an article body that quotes "the post was deleted" is not a removal.
REMOVAL = re.compile(
    r"\b(page|article|post|story|content|video|tweet|message|item|account)\s+(has been|was|is|had been)\s+"
    r"(removed|deleted|taken down|unpublished|withdrawn)\b"
    # Not "no longer exists": a headline says that of a destroyed dam or plant.
    r"|\b(this|the) (page|post|content|article|video|story)\s+(is no longer available|isn'?t available|is not available"
    r"|does not exist|doesn'?t exist)"
    r"|\bpage not found\b|\berror 404\b|^\s*404\b|\b404\s*[-|:–—]|^\s*not found\b", re.I)
META_TEXT = re.compile(r"""<meta\b[^>]*?(?:name|property)\s*=\s*["'](?:description|og:title|og:description|twitter:title)["'][^>]*>""",
                       re.I)
META_CONTENT = re.compile(r"""content\s*=\s*["']([^"']*)""", re.I)

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


def removal_notice(html, title):
    """Whether the page's own title or meta title/description says its content is gone."""
    texts = [title or ""] + [m.group(1) for tag in META_TEXT.findall(html[:READ_BYTES])
                             for m in [META_CONTENT.search(tag)] if m]
    return any(REMOVAL.search(t) for t in texts)


def ascii_url(url):
    """The address as a request line can carry it: non-ASCII path and query characters
    percent-encoded, the host IDNA-encoded. The recorded citation keeps its original spelling."""
    p = urllib.parse.urlsplit(url)
    host = p.hostname.encode("idna").decode("ascii") if p.hostname else ""
    netloc = host + (f":{p.port}" if p.port else "")
    return urllib.parse.urlunsplit((p.scheme, netloc, urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;=-._~"),
                                    urllib.parse.quote(p.query, safe="=&%:@!$'()*+,;/?-._~"), ""))


def transport_failure(reason):
    """A request that got no HTTP answer. Never dead on its own: a host DNS says does not exist is
    marked `dns_not_found` and becomes dead only when a second lookup agrees (fetch_checked)."""
    if isinstance(reason, socket.gaierror):
        if reason.errno in DNS_NOT_FOUND:
            return {"state": "error", "http": None, "detail": "DNS: no such host", "dns_not_found": True}
        return {"state": "error", "http": None, "detail": "DNS lookup failed"}
    # A refused or dropped connection is the server declining an automated visitor; it says
    # nothing about whether the page exists. RemoteDisconnected is a ConnectionResetError.
    if isinstance(reason, (ConnectionRefusedError, ConnectionResetError, http.client.RemoteDisconnected)):
        return {"state": "blocked", "http": None, "detail": "the server refused or dropped the connection"}
    if isinstance(reason, (ssl.SSLError, ssl.CertificateError)):
        return {"state": "error", "http": None, "detail": "TLS"}
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return {"state": "error", "http": None, "detail": "timeout"}
    return {"state": "error", "http": None, "detail": (type(reason).__name__ if not isinstance(reason, str) else reason)[:80]}


def _challenged(err):
    """A 5xx that is a bot challenge (Cloudflare and similar answer 503 with a challenge page)."""
    if (err.headers or {}).get("cf-mitigated", "").lower() == "challenge":
        return True
    try:
        head = err.read(4000).decode("utf-8", "replace")
    except Exception:
        return False
    return bool(BOT_WALL.search(head))


def fetch(url):
    req = urllib.request.Request(ascii_url(url), headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context()) as r:
            body = r.read(READ_BYTES)
            final = r.geturl()
            state = "redirected" if _norm(final) != _norm(ascii_url(url)) else "reachable"
            kind = r.headers.get("Content-Type", "")
            text = body.decode("utf-8", "replace") if "html" in kind or not kind else ""
            if BOT_WALL.search(text[:4000]):
                return {"state": "blocked", "http": r.status, "final_url": final, "detail": "bot challenge"}
            t = TITLE.search(text) if text else None
            title = re.sub(r"\s+", " ", t.group(1)).strip()[:240] if t else None
            out = {"state": state, "http": r.status, "final": final if state == "redirected" else None,
                   "final_url": final, "redirect": state == "redirected", "title": title,
                   "hash": hashlib.sha256(body).hexdigest()[:16], "page_date": page_date(text) if text else None}
            if text and removal_notice(text, title):
                out["state"], out["detail"] = "deleted", "the page says its content was removed or not found"
            return out
    except urllib.error.HTTPError as e:
        if e.code in BLOCKED_HTTP:
            state = "blocked"
        elif e.code in DEAD_HTTP:
            state = "dead"
        else:
            state = "blocked" if _challenged(e) else "error"
        return {"state": state, "http": e.code, "final_url": e.geturl()}
    except urllib.error.URLError as e:
        return transport_failure(e.reason)
    except Exception as e:  # a timeout or a malformed response is one failed link, not a failed run
        return transport_failure(e)


def fetch_checked(url, fetch_one=fetch, sleep=time.sleep):
    """One request, and for a host DNS says does not exist one more lookup after a pause: a
    resolver's bad moment must not mark a live citation dead."""
    r = fetch_one(url)
    if r.get("dns_not_found"):
        sleep(DNS_RETRY_WAIT)
        r = fetch_one(url)
        if r.get("dns_not_found"):
            r = {**r, "state": "dead", "detail": "DNS: no such host, asked twice"}
    r.pop("dns_not_found", None)
    return r


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


def cited_urls():
    urls = {}
    for sid in SYSTEMS:
        events = json.loads((ROOT / "data" / "curated" / "systems" / sid / "events.json").read_text(encoding="utf-8"))["events"]
        for e in events:
            for s in e["sources"]:
                urls.setdefault(s["url"], set()).add(sid)
            if e["recovery"].get("url"):
                urls.setdefault(e["recovery"]["url"], set()).add(sid)
    return urls


def check_all(urls, previous, retry_only=False, cap=None, fetch_one=None, sleep=time.sleep, save=None):
    """Visit each URL once, host by host, politely. Returns {url: result}."""
    cap = MAX_REQUESTS if cap is None else cap
    fetch_one = fetch_one or (lambda u: fetch_checked(u, sleep=sleep))
    last_hit, results, refused, asked = {}, {}, set(), 0
    for i, url in enumerate(sorted(urls, key=lambda u: urllib.parse.urlsplit(u).netloc)):
        host = urllib.parse.urlsplit(url).netloc
        if retry_only and url in previous and previous[url].get("state") != "error":
            results[url] = previous[url]
            continue
        if host in refused:
            # One refusal is the site's answer for this run; asking again is working around it.
            results[url] = {"state": "blocked", "http": None, "detail": "host refused earlier in this run; not retried"}
        elif asked >= cap:
            results[url] = {"state": "unchecked", "http": None, "detail": "the run's request cap was reached"}
            continue
        else:
            wait = PER_HOST_DELAY - (time.monotonic() - last_hit.get(host, -99))
            if wait > 0:
                sleep(wait)
            results[url] = fetch_one(url)
            asked += 1
            last_hit[host] = time.monotonic()
            if results[url]["state"] == "blocked":
                refused.add(host)
        results[url]["checked_at"] = CHECKED
        results[url]["short_link"] = bool(SHORT_LINK.search(url))
        old = previous.get(url, {})
        if old.get("hash") and results[url].get("hash") and old["hash"] != results[url]["hash"]:
            results[url]["changed_content"] = True
        if save and (i + 1) % 25 == 0:
            save(results)
            print(i + 1, "of", len(urls), flush=True)
    return results


def classify_redirects(results, gone_is_dead):
    """A redirect to a bot check is a refusal. A redirect to a home page or listing is dead where
    `gone_is_dead` (the country systems' rule since iteration 20), else it stays redirected."""
    for url, r in results.items():
        if r.get("redirect") and r.get("final_url"):
            kind = classify_redirect(url, r["final_url"])
            r["redirect_kind"] = kind
            if kind == "challenge":
                r["state"], r["detail"] = "blocked", "redirected to a bot challenge"
            elif kind == "general_page" and gone_is_dead:
                r["state"], r["detail"] = "dead", "redirected to a home page or listing: the article is gone"


def _write_local(path, results):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(results, ensure_ascii=False, indent=0).encode("utf-8"))


def _arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def main():
    if "--impacts" in sys.argv:
        return main_impacts(Path(_arg("--local")) if _arg("--local") else IMPACTS_LOCAL)
    urls = cited_urls()
    previous = json.loads(LOCAL.read_text(encoding="utf-8")) if LOCAL.exists() else {}
    # --states-only: add each cited URL's state from the last run's local results to the public
    # file, visiting nothing and leaving every other key as that run wrote it.
    if "--states-only" in sys.argv:
        if not previous or not PUBLIC.exists():
            sys.exit(f"--states-only needs a previous run's results in {LOCAL} and {PUBLIC}")
        public = json.loads(PUBLIC.read_text(encoding="utf-8"))
        public["link_states"] = link_states(previous, urls)
        PUBLIC.write_bytes((json.dumps(public, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        return
    # --retry-errors: keep every earlier answer except a failure to load, which is asked once more.
    results = check_all(urls, previous, retry_only="--retry-errors" in sys.argv,
                        save=lambda res: _write_local(LOCAL, res))
    # A short link the import already replaced is no longer cited; its answer is carried forward
    # while the address it lands on is still cited, so the import keeps the canonical address.
    for u, r in previous.items():
        if u not in results and r.get("redirect_kind") == "canonical" and clean_final(r.get("final_url") or "") in urls:
            results[u] = r
    classify_redirects(results, gone_is_dead=True)
    for r in results.values():
        if r["state"] == "deleted":
            r["state"] = "dead"
    _write_local(LOCAL, results)
    write_public(results, urls)


def link_states(results, urls):
    return dict(sorted((u, results[u]["state"]) for u in urls if u in results and results[u]["state"] in SYSTEM_STATES))


def write_public(results, urls):
    counts = {}
    old_public = json.loads(PUBLIC.read_text(encoding="utf-8")) if PUBLIC.exists() else {}
    dates = dict(old_public.get("page_stated_dates") or {})
    for u, r in results.items():
        if r.get("page_date") and u not in dates:
            dates[u] = r["page_date"]
    for url, sids in urls.items():
        if url not in results or results[url]["state"] not in SYSTEM_STATES:
            continue
        for sid in sids:
            c = counts.setdefault(sid, {k: 0 for k in SYSTEM_STATES})
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
        # Each cited page's state at the last check, so a record can say which of its citations
        # still load (iteration 21). The state only: no title, hash or final address leaves the
        # local file.
        "link_states": link_states(results, urls),
    }, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print("done", {k: sum(c[k] for c in counts.values()) for k in SYSTEM_STATES}, file=sys.stderr)


# --- the impact layer and the regional context (iteration 22) -----------------------------------------

IMPACT_NOTE = ("One automated visit to each cited page. Blocked means the site refused an automated visitor, "
               "not that the page is gone; an error is the check failing, not the page. Dead means not found "
               "(404, 410, or no such host). Deleted means the page itself says its content was removed.")
ABSTRACTED = "country_abstracted"
LEAK_KINDS = {
    "place": "the address names a sub-national place of a Gulf littoral system",
    "facility": "the address names a facility or operator held in the curated country records",
    "facility_type": "the address on a country-abstracted record refers to a kind of facility; check whether it names one",
    "method": "the address states how an attack was carried out",
    "status": "the address carries current-status wording (restart, repair, restored, resumed and similar)",
    "route": "the address carries shipping, route, vessel or dependence wording, or names a Gulf port or terminal",
    "unresolved": "a short or opaque link whose final address could not be read",
}
# The facility words of import_candidates.GENERIC_NAME_WORDS: words that say "a facility" without
# naming one. On an abstracted record a reviewer checks the address beside them.
FACILITY_TYPE_WORDS = ("refinery", "refineries", "plant", "plants", "field", "fields", "terminal", "terminals",
                       "station", "stations", "port", "ports", "facility", "facilities", "depot", "complex",
                       "مصفاة", "محطة", "حقل", "ميناء", "منشأة", "مجمع", "مستودع", "پالایشگاه", "نیروگاه", "میدان",
                       "پتروشیمی", "بندر")


def impact_states():
    """The impact layer's link-state vocabulary, from the taxonomy (taxonomy is data)."""
    tax = json.loads((ROOT / "methodology" / "impact_taxonomy.json").read_text(encoding="utf-8"))
    return tuple(x["id"] for x in tax["link_states"])


def impact_citations(directory=IMPACTS_CURATED):
    """[(corpus, item_id, ref, url, item)] for every citation of the impact records ("impact") and
    the regional context ("context"), in file order."""
    records = json.loads((directory / "events.json").read_text(encoding="utf-8"))["records"]
    entries = json.loads((directory / "regional_context.json").read_text(encoding="utf-8"))["entries"]
    out = [("impact", r.get("impact_id"), s.get("ref"), s["url"], r)
           for r in records for s in r.get("sources") or [] if isinstance(s, dict) and s.get("url")]
    out += [("context", e.get("id"), s.get("ref"), s["url"], e)
            for e in entries for s in e.get("sources") or [] if isinstance(s, dict) and s.get("url")]
    return out


def _countries(item):
    return list(item.get("countries_a3") or []) if item.get("country_a3") == "MULTI" else [item.get("country_a3")]


def address_text(url):
    """What the address checks read: the subdomain labels (not the publisher's registered domain),
    the path and the query, as import_candidates.names_the_place reads an address."""
    rest = (url or "").split("://", 1)[-1]
    host, _, path = rest.partition("/")
    labels = [x for x in host.lower().split(".") if x and x != "www"][:-2]
    return " ".join(labels) + " /" + path


def _modules():
    """The pipeline's address checks and the country import's, imported on first use so the
    country-system run needs neither."""
    for p in (str(ROOT), str(ROOT / "scripts")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from pipeline import build_systems as B
    from pipeline import global_impacts as GI
    import import_candidates as IC
    return B, GI, IC


def safety_lists():
    """The pipeline's own lists, loaded once: the Gulf littoral systems and their a3 codes, each
    one's region phrases and unit words, and facility and operator words from every country
    system's curated records. Nothing here is a new list."""
    B, GI, IC = _modules()
    from pipeline import systems
    gulf = tuple(systems.GROUPS["gulf_littoral"]["members"])
    sid_of = {a3: s["id"] for s in systems.SYSTEMS if s["kind"] == "country" for a3 in s["admin0_a3"]}
    admin1, admin0 = B.load_admin1(), B.load_admin0()
    phrases, unit_words, facility = {}, {}, {}
    for sid in gulf:
        phrases[sid] = GI.system_unit_phrases(sid)
        doc = json.loads((B.SYSTEMS_CURATED / sid / "system.json").read_text(encoding="utf-8"))
        unit_words[sid] = IC.unit_words(B.unit_name_rows(doc, B.units(sid, admin1, admin0)))
    for sid in systems.COUNTRY_SYSTEMS:
        events = json.loads((B.SYSTEMS_CURATED / sid / "events.json").read_text(encoding="utf-8"))["events"]
        facility[sid] = set().union(*[IC.name_tokens({k: e.get(k) for k in ("facility_name", "facility_name_local", "operator")})
                                      for e in events] or [set()])
    return {"gulf": gulf, "gulf_a3": frozenset(a3 for sid in gulf for a3 in systems.system(sid)["admin0_a3"]),
            "sid_of": sid_of, "phrases": phrases, "unit_words": unit_words, "facility": facility,
            "facility_types": frozenset(B.fold(w) for w in FACILITY_TYPE_WORDS)}


def is_sensitive(corpus, item, L):
    """Whose addresses get the redirect-safety scan: every context entry, every abstracted record,
    every record in a Gulf littoral system."""
    if corpus == "context":
        return True
    return item.get("publication_policy") == ABSTRACTED or bool(set(_countries(item)) & L["gulf_a3"])


def leak_kinds(url, corpus, item, L):
    """The kinds of leak in one address, as LEAK_KINDS names them; never the words that matched."""
    B, GI, IC = _modules()
    text = address_text(url)
    words = B.address_words(text)
    path = re.sub(r"^https?://[^/]+", "", url or "")
    abstracted = corpus == "impact" and item.get("publication_policy") == ABSTRACTED
    if corpus == "context":
        gulf_sids = list(L["gulf"])
        own_sids = gulf_sids
    else:
        gulf_sids = [L["sid_of"][a3] for a3 in _countries(item) if a3 in L["gulf_a3"] and a3 in L["sid_of"]]
        own_sids = [L["sid_of"][a3] for a3 in _countries(item) if a3 in L["sid_of"]]
    kinds = []
    if any(GI.names_in(words, L["phrases"][sid]) or IC.names_the_place(url, L["unit_words"][sid]) for sid in gulf_sids):
        kinds.append("place")
    if any(L["facility"].get(sid) and IC.names_the_place(url, L["facility"][sid]) for sid in own_sids):
        kinds.append("facility")
    if abstracted and set(re.findall(r"[^\W\d_]+", words)) & L["facility_types"]:
        kinds.append("facility_type")
    if B.method_in_address(url):
        kinds.append("method")
    if B.status_wording(B.address_words(path)):
        kinds.append("status")
    # The regional context may state shipping status, so only its own ban list applies there. A
    # Gulf record gets both: route wording, and the context list's vessel, dependence and named
    # Gulf port and terminal words.
    route = GI.CONTEXT_CASED.search(path) or GI.CONTEXT_FORBIDDEN.search(B.address_words(path))
    if corpus == "impact":
        route = gulf_sids and (route or GI.route_hit(B.address_words(url)))
    if route:
        kinds.append("route")
    return kinds


def _unresolvable(url):
    IC = _modules()[2]
    return bool(SHORT_LINK.search(url)) or IC.short_link(url) or IC.opaque_unresolved(url)


def safety_hits(citations, results, L):
    """Every sensitive citation whose cited or final address leaks, generically. The final address
    is the one a reader lands on after shorteners, tracking links and publisher redirects."""
    hits = []
    for corpus, iid, ref, url, item in citations:
        if not is_sensitive(corpus, item, L):
            continue
        r = results.get(url) or {}
        final = r.get("final_url")
        found = {}
        for where, address in (("cited address", url), ("final address", final)):
            if address:
                for k in leak_kinds(address, corpus, item, L):
                    found.setdefault(k, []).append(where)
        if not final and _unresolvable(url):
            found.setdefault("unresolved", []).append("cited address")
        for kind, wheres in sorted(found.items()):
            hits.append({"corpus": corpus, "id": iid, "field": f"sources[{ref}].url", "kind": kind,
                         "where": " and ".join(sorted(set(wheres))), "means": LEAK_KINDS[kind]})
    return hits


def impact_summary(citations, results, hits):
    """Counts per class per corpus (citations and unique addresses), refusing hosts, and the
    citations a reviewer must look at. Hosts only, never a path."""
    out = {"checked": CHECKED, "by_corpus": {}, "blocked_hosts_top10": [], "dead": [], "deleted": [],
           "redirected_to_home_or_listing": [], "unchecked": 0, "safety_hits": hits}
    for corpus in ("impact", "context"):
        rows = [c for c in citations if c[0] == corpus]
        per_cite = Counter((results.get(c[3]) or {}).get("state", "unchecked") for c in rows)
        per_url = Counter((results.get(u) or {}).get("state", "unchecked") for u in {c[3] for c in rows})
        out["by_corpus"][corpus] = {"citations": len(rows), "citation_states": dict(sorted(per_cite.items())),
                                    "unique_addresses": len({c[3] for c in rows}), "address_states": dict(sorted(per_url.items()))}
    blocked = Counter(urllib.parse.urlsplit(u).netloc for u in {c[3] for c in citations}
                      if (results.get(u) or {}).get("state") == "blocked")
    out["blocked_hosts_top10"] = blocked.most_common(10)
    for corpus, iid, ref, url, _ in citations:
        r = results.get(url) or {}
        row = {"corpus": corpus, "id": iid, "ref": ref, "host": urllib.parse.urlsplit(url).netloc}
        if r.get("state") == "dead":
            out["dead"].append({**row, "why": r.get("detail") or f"HTTP {r.get('http')}"})
        elif r.get("state") == "deleted":
            out["deleted"].append(row)
        if r.get("redirect_kind") == "general_page" and r.get("state") == "redirected":
            out["redirected_to_home_or_listing"].append(row)
    out["unchecked"] = sum(1 for u in {c[3] for c in citations} if (results.get(u) or {}).get("state", "unchecked") == "unchecked")
    return out


def write_impacts_public(results, citations, path=IMPACTS_PUBLIC):
    """Each PUBLISHED citation's state, nothing else. A state outside the taxonomy, an unchecked
    address and an address no published record cites are left out (the build refuses them)."""
    published = {c[3] for c in citations}
    allowed = set(impact_states()) - {"unchecked", "archived_copy"}
    states = {u: results[u]["state"] for u in published if u in results and results[u].get("state") in allowed}
    path.write_bytes((json.dumps({"checked": CHECKED, "note": IMPACT_NOTE, "link_states": dict(sorted(states.items()))},
                                 ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return states


def main_impacts(local):
    citations = impact_citations()
    urls = {c[3] for c in citations}
    previous = json.loads(local.read_text(encoding="utf-8")) if local.exists() else {}
    summary_path = local.with_name(local.stem + "_summary.json")
    if "--states-only" in sys.argv:
        if not previous:
            sys.exit(f"--states-only needs a previous run's results in {local}")
        write_impacts_public(previous, citations)
        return
    results = check_all(urls, previous, retry_only="--retry-errors" in sys.argv,
                        save=lambda res: _write_local(local, res))
    classify_redirects(results, gone_is_dead=False)
    _write_local(local, results)
    write_impacts_public(results, citations)
    hits = safety_hits(citations, results, safety_lists())
    summary = impact_summary(citations, results, hits)
    summary_path.write_bytes(json.dumps(summary, ensure_ascii=False, indent=1).encode("utf-8"))
    print(json.dumps({k: summary[k] for k in ("by_corpus", "blocked_hosts_top10", "unchecked")}, indent=1))
    print(f"{len(summary['dead'])} dead, {len(summary['deleted'])} deleted, {len(hits)} redirect-safety hits; "
          f"details in {summary_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
