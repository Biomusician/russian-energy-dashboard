"""Extract facilities and strike incidents from the English Wikipedia strike tables.

Source: "Deep strike campaign", section "List of oil industry facilities in Russia
hit by Ukrainian strikes". Text is CC BY-SA 4.0; attribution is carried in
docs/SOURCES.md and in the app.

Two deliberate omissions:

  * The source table has a "Distance (km)" column giving the range from
    Ukrainian-controlled territory to each facility. It is not read. It describes
    reach rather than damage, contributes nothing to a degradation assessment, and
    is the one field in the table with obvious operational-planning value.

  * Where the source says a facility was hit "at least 16 times" without listing the
    dates, those strikes are NOT invented as individual events. The count is
    recorded as `unenumerated_events` so the UI can state that the true event count
    exceeds the number plotted.

Attribution is reported, never asserted. Every incident from this source carries
attribution_confidence="probable" because the source table's framing is media
reporting of Ukrainian responsibility, not independent confirmation.
"""

import re

from pipeline import wikitext as W
from pipeline.dates import parse_dates, parse_dates_grouped, unenumerated_count
from pipeline.regionmatch import resolve
from pipeline.util import fetch_json, log

API = "https://en.wikipedia.org/w/api.php"
PAGE = "Deep_strike_campaign"
SECTION_HEADING = "== List of oil industry facilities"
PAGE_URL = "https://en.wikipedia.org/wiki/Deep_strike_campaign"

_NAMED_REF = re.compile(r'<ref\s+name\s*=\s*["\']?([^"\'>/]+)["\']?\s*>(.*?)</ref>', re.S | re.I)
_REF_NAME_ONLY = re.compile(r'<ref\s+name\s*=\s*["\']?([^"\'>/]+)["\']?\s*/?>', re.I)
_URL = re.compile(r"\|\s*url\s*=\s*(\S+?)\s*(?:\||\}\}|$)", re.I | re.S)
_TITLE = re.compile(r"\|\s*title\s*=\s*([^|}]+)", re.I | re.S)
_WORK = re.compile(r"\|\s*(?:work|website|publisher|newspaper)\s*=\s*([^|}]+)", re.I | re.S)
_DATE = re.compile(r"\|\s*date\s*=\s*([^|}]+)", re.I | re.S)


def load_wikitext(max_age_hours=12):
    url = (
        f"{API}?action=parse&page={PAGE}&prop=wikitext&format=json&formatversion=2"
    )
    payload = fetch_json(url, "wiki_deep_strike.json", max_age_hours=max_age_hours)
    return payload["parse"]["wikitext"]


def build_named_refs(wt):
    """Map ref name -> ref body, so `<ref name="x"/>` back-references resolve."""
    return {name.strip(): body for name, body in _NAMED_REF.findall(wt)}


def parse_citation(ref_src, named_refs):
    """Pull (url, title, publisher, date) out of one <ref>."""
    body = ref_src
    if "</ref>" not in ref_src.lower():
        m = _REF_NAME_ONLY.search(ref_src)
        if m:
            body = named_refs.get(m.group(1).strip(), "")
    if not body:
        return None
    url = _URL.search(body)
    if not url:
        return None
    return {
        "url": url.group(1).strip(),
        "title": _clean_field(_TITLE.search(body)),
        "publisher": _clean_field(_WORK.search(body)),
        "date": _clean_field(_DATE.search(body)),
    }


def _clean_field(match):
    if not match:
        return None
    return W.clean_cell(match.group(1))[:300] or None


def classify(table_index, facility_name):
    """Which asset class a table row describes."""
    if table_index == 0:
        return "refinery"
    name = facility_name.lower()
    if "pumping" in name or "lpds" in name or "pipeline" in name:
        return "pipeline_oil"
    return "oil_terminal"


def _capacity(text):
    """First number in a capacity cell, in MTPA. Ranges take the low end.

    Cells like "(6,400 m3)" describe storage volume, not annual throughput, and are
    not comparable -- those return None rather than a wrong number.
    """
    if not text:
        return None
    if "m3" in text.lower() or "m<sup>3" in text.lower():
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
    return float(m.group(1)) if m else None


def build():
    wt = load_wikitext()
    named_refs = build_named_refs(wt)

    start = wt.find(SECTION_HEADING)
    if start < 0:
        raise RuntimeError(
            f"section {SECTION_HEADING!r} not found in {PAGE} -- the article has been "
            "restructured and this parser needs revisiting"
        )
    end = wt.find("\n== ", start + 5)
    section = wt[start : end if end > 0 else len(wt)]

    tables = W.find_tables(section)
    if len(tables) < 2:
        raise RuntimeError(f"expected 2 tables in {PAGE} section, found {len(tables)}")

    facilities = []
    incidents = []
    warnings = []

    for ti, table_src in enumerate(tables[:2]):
        headers, rows, spans = W.parse_table(table_src)
        cols = {W.clean_cell(h).lower(): i for i, h in enumerate(headers)}
        i_region = cols.get("region", 1)
        i_operator = cols.get("operator", 2)
        i_cap = cols.get("capacity by mtpa", cols.get("mtpa", 3))
        i_date = len(headers) - 1  # "Date of strike(s)" is always last

        for row in rows:
            ragged = len(row) != len(headers)
            # raw() keeps the ref/template placeholders, which is what citation
            # extraction needs; txt() is the human-readable value.
            raw = lambda i: row[i] if 0 <= i < len(row) else ""
            txt = lambda i: W.clean_cell(W.restore(raw(i), spans))

            name = txt(0)
            if not name:
                continue

            if ragged:
                # Do not guess at column positions in a malformed row. Facility is
                # reliably first; find the date column by content and take nothing
                # else that could be silently wrong.
                date_i = max(range(len(row)), key=lambda i: len(parse_dates(txt(i))))
                date_src = raw(date_i)
                region_src = txt(1)
                operator = txt(2) or None
                capacity = None
                warnings.append(
                    f"{name}: source row has {len(row)} cells, expected "
                    f"{len(headers)}; capacity not read"
                )
            else:
                date_src = raw(i_date)
                region_src = txt(i_region)
                operator = txt(i_operator) or None
                capacity = _capacity(txt(i_cap))

            kind, region = resolve(region_src)
            if kind == "unresolved":
                warnings.append(f"{name}: could not resolve region {region_src!r}")

            # in_aoi regions and the Crimea context unit both get a region_code so their
            # events are tracked. Crimea is flagged so the index excludes it from the
            # Russia+Belarus composite. Everything else stays region-less.
            tracked = kind in ("in_aoi", "context")
            region_code = region if tracked else None

            asset_class = classify(ti, name)
            asset_id = _slug(name)

            facilities.append(
                {
                    "asset_id": asset_id,
                    "name": name,
                    "asset_class": asset_class,
                    "region_code": region_code,
                    "region_text": region_src or None,
                    "in_aoi": kind == "in_aoi",
                    "context": kind == "context",
                    "out_of_aoi": kind == "out_of_aoi",
                    "operator": operator,
                    "capacity_mtpa": capacity,
                    "source_page": PAGE_URL,
                }
            )

            unenumerated = unenumerated_count(W.clean_cell(date_src))
            row_incidents = _incidents_for(
                asset_id, name, asset_class, region_code,
                date_src, spans, named_refs,
            )
            if unenumerated is not None:
                for inc in row_incidents:
                    inc["part_of_unenumerated_series"] = True
                    # The MAGNITUDE, not just the fact. "At least 16 times" with three
                    # extractable dates is a known undercount of thirteen; a bare "series
                    # undercounted" tag tells a reader something is missing without telling
                    # them how much, which is the difference between a stated limitation and
                    # a shrug. The number was computed here and then read by nobody.
                    inc["unenumerated_series_total"] = unenumerated
                    inc["series_events_extracted"] = len(row_incidents)
                facilities[-1]["unenumerated_events"] = unenumerated
            incidents.extend(row_incidents)

    log(f"wikipedia: {len(facilities)} facilities, {len(incidents)} incidents")
    for w in warnings:
        log(f"  WARN {w}")
    return facilities, incidents, warnings


def _incidents_for(asset_id, name, asset_class, region, date_src, spans, named_refs):
    """One incident per EPISODE, with citations attributed by proximity.

    An episode is one disruption event: a single date, or a contiguous day-range
    ("9-10 June") that the source describes as one strike. Discrete listed dates are
    separate episodes. This is the iteration-3 fix for multi-day strikes previously
    exploding into several independent incident rows.

    The date cell is prose of the form "date<ref>, date<ref>, date<ref>". Splitting on
    top-level commas keeps each date with the citation that follows it; episode grouping
    within a fragment then merges a hyphen-range into one incident.
    """
    out = []
    seen_episode_first = set()
    for fragment in _split_fragments(date_src):
        restored = W.restore(fragment, spans)
        citations = [
            c
            for c in (parse_citation(r, named_refs) for r in W.refs_in(fragment, spans))
            if c
        ]
        # group -> ordered list of (iso, precision)
        episodes = {}
        for iso, precision, grp in parse_dates_grouped(W.clean_cell(restored, keep_templates=("dts",))):
            episodes.setdefault(grp, []).append((iso, precision))
        for _grp, dates in episodes.items():
            first_iso, precision = dates[0]
            last_iso = dates[-1][0]
            if first_iso in seen_episode_first:
                continue
            seen_episode_first.add(first_iso)
            incident_id = f"{asset_id}:{first_iso}"
            out.append(
                {
                    "incident_id": incident_id,
                    "episode_id": incident_id,
                    "asset_id": asset_id,
                    "asset_name": name,
                    "asset_class": asset_class,
                    "region_code": region,
                    "date": first_iso,
                    "date_start": first_iso,
                    "date_end": last_iso if last_iso != first_iso else None,
                    "date_precision": precision,
                    "cause": "kinetic_strike",
                    "attribution": "reported_ukrainian_strike",
                    # Reported, not independently confirmed. See module docstring.
                    "attribution_confidence": "probable",
                    "confidence": _confidence(citations),
                    "sources": citations,
                    "source_page": PAGE_URL,
                }
            )
    return out


def _split_fragments(text):
    """Split a date cell on commas that are not inside a placeholder or bracket."""
    parts = []
    buf = []
    depth = 0
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p for p in parts if p.strip()]


def _confidence(citations):
    """Occurrence confidence, from how many independent outlets are cited.

    This scores whether the event happened, not who did it; attribution confidence
    is a separate field and is never raised above "probable" from this source.
    """
    hosts = {_host(c["url"]) for c in citations if c.get("url")}
    if len(hosts) >= 2:
        return "confirmed"
    if len(hosts) == 1:
        return "probable"
    return "possible"


def _host(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().removeprefix("www.") if m else None


def _slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:60] or "unnamed"


if __name__ == "__main__":
    f, i, w = build()
    print(f"facilities={len(f)} incidents={len(i)} warnings={len(w)}")
