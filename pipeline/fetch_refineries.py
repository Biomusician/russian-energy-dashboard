"""Parse Russia's refinery inventory to get a real denominator for refining exposure.

Without this, refining exposure would be measured against the set of refineries known
to have been struck -- which is 100% by construction and says nothing. The national
inventory gives an honest denominator: what share of Russia's refining base sits at
disrupted facilities.

Source: English Wikipedia "List of oil refineries", sections "Russia in Europe" and
"Russia in Asia". Both are included: the index frame is national because Russian fuel
markets are national, and the Europe/Asia split in that article does not line up with
our federal-district AOI anyway (Antipinsky, in the Ural FD and inside our AOI, is
filed under Asia).

Capacities are published in barrels per day and converted to MTPA so they are
comparable with the strike table's figures. The conversion assumes 0.136 tonnes per
barrel of crude, i.e. 1 bbl/d = 49.6 tonnes/year. Cross-check: Omsk at 22.0 MTPA in
the strike table converts to ~443,000 bbl/d, against a published figure in the same
range.
"""

import re

from pipeline import wikitext as W
from pipeline.util import fetch_json, log

API = "https://en.wikipedia.org/w/api.php"
PAGE = "List_of_oil_refineries"
PAGE_URL = "https://en.wikipedia.org/wiki/List_of_oil_refineries"

TONNES_PER_BARREL = 0.136
BBL_PER_DAY_TO_MTPA = TONNES_PER_BARREL * 365 / 1e6

SECTIONS = ("Russia in Europe", "Russia in Asia")

_BULLET = re.compile(r"^\*\s*(?!\*)(.+)$", re.M)
_CVT_BBL = re.compile(r"\{\{\s*cvt\s*\|\s*([\d,\.]+)\s*\|\s*oilbbl/d", re.I)
_CVT_TPA = re.compile(r"\{\{\s*cvt\s*\|\s*([\d,\.]+)\s*\|\s*(?:MTPA|Mt/a|t/a)", re.I)


def load_wikitext(max_age_hours=24 * 7):
    url = f"{API}?action=parse&page={PAGE}&prop=wikitext&format=json&formatversion=2"
    return fetch_json(url, "wiki_refineries.json", max_age_hours=max_age_hours)["parse"]["wikitext"]


def _section(wt, heading):
    start = wt.find(f"==={heading}===")
    if start < 0:
        start = wt.find(heading)
        if start < 0:
            return ""
    end = wt.find("\n==", start + len(heading) + 4)
    return wt[start : end if end > 0 else len(wt)]


def build():
    wt = load_wikitext()
    out = []
    for heading in SECTIONS:
        sec = _section(wt, heading)
        if not sec:
            log(f"  WARN refinery section {heading!r} not found")
            continue
        for line in _BULLET.findall(sec):
            entry = _parse_line(line, heading)
            if entry:
                out.append(entry)

    # De-duplicate: a refinery listed in both sections would otherwise double-count
    # into the denominator and deflate every refining exposure number.
    seen = {}
    for e in out:
        seen.setdefault(e["name"].lower(), e)
    refineries = list(seen.values())

    total = sum(r["capacity_mtpa"] for r in refineries if r["capacity_mtpa"])
    log(
        f"refineries: {len(refineries)} in national inventory, "
        f"{sum(1 for r in refineries if r['capacity_mtpa'])} with capacity, "
        f"{total:,.1f} MTPA total"
    )
    return refineries, total


def _parse_line(line, section):
    bbl = _CVT_BBL.search(line)
    tpa = _CVT_TPA.search(line)
    if not bbl and not tpa:
        return None

    # Name is everything before the first top-level comma. Entries trail off into
    # "…, Samara Oblast" or "…, design capacity 6.25 million tonnes", none of which
    # belongs in a facility name. The comma split must respect parentheses so an
    # operator list like "(Tatneft, TANEKO)" survives intact.
    head = W.clean_cell(line.split("{{cvt")[0])
    head = _before_top_level_comma(head)
    operator = None
    m = re.search(r"\(([^)]*)\)\s*$", head)
    if m:
        operator = m.group(1).strip() or None
        head = head[: m.start()].strip()
    name = head.strip().rstrip(",")
    if not name or len(name) > 120:
        return None

    if bbl:
        capacity = float(bbl.group(1).replace(",", "")) * BBL_PER_DAY_TO_MTPA
    else:
        capacity = float(tpa.group(1).replace(",", ""))

    return {
        "name": name,
        "operator": operator,
        "capacity_mtpa": round(capacity, 3),
        "listed_under": section,
        "source_page": PAGE_URL,
    }


def _before_top_level_comma(text):
    depth = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            return text[:i].strip()
    return text.strip()


if __name__ == "__main__":
    refineries, total = build()
    for r in refineries[:10]:
        print(f"  {r['name'][:44]:46} {r['capacity_mtpa']:8.2f} MTPA  {r['operator']}")
    print(f"  TOTAL {total:,.1f} MTPA")
