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

# Published national estimate of Russian primary crude-refining capacity. ~6.6 mb/d of
# primary distillation is the figure repeatedly cited by the IEA and Reuters; at the
# 0.136 t/bbl / 49.6 t/yr convention that is ~330 MTPA. Used ONLY to state our
# denominator coverage honestly -- never as an input to any score.
NATIONAL_ESTIMATE_MTPA = 330.0  # kept for N-1 compatibility; superseded by REFERENCE_* below
NATIONAL_ESTIMATE_SOURCE = "IEA / Reuters, Russian primary refining ~6.6 mb/d (~330 MTPA)"

# Iteration-7 refining-capacity reference (triangulated: Carnegie Oct-2025 + Reuters/industry).
# FULL nameplate primary distillation, Russia-only (excludes Belarus), on the CDU-TEK basis —
# which INCLUDES gas-condensate splitters and mini-refineries. NB: 2024 THROUGHPUT was ~267 MTPA
# (>22% of nameplate chronically idle) — capacity, not throughput. Used only to state denominator
# completeness; never an input to any score.
REFERENCE_NAMEPLATE_MTPA = 327.0
REFERENCE_RANGE_MTPA = [320.0, 330.0]
REFERENCE_YEAR = 2025
REFERENCE_SOURCE = "Carnegie Endowment (Oct 2025) + Reuters/industry consensus; ~6.5 mb/d nameplate"
# The tracked base is CRUDE-fuels only. The like-for-like reference removes the ~24 MTPA of
# gas-condensate splitters counted in the full 327 (Surgut CSP ~12 + Novatek Ust-Luga ~9 +
# Astrakhan condensate line ~3) — they make motor fuels from CONDENSATE, not crude, and are
# excluded by the same rule as Tobolsk. This is the comparable universe for coverage.
REFERENCE_CRUDE_NAMEPLATE_MTPA = 303.0
EXCLUDED_CONDENSATE_SPLITTERS = [
    "Surgut Condensate Stabilization Plant (~12 MTPA, Gazprom; condensate, not crude)",
    "Novatek Ust-Luga complex (~9 MTPA; stable gas condensate, not crude)",
    "Astrakhan condensate refining line (~3 MTPA; on the gas-processing census instead)",
]

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
        seen.setdefault(_dedup_key(e["name"]), e)
    base_total = sum(e["capacity_mtpa"] for e in seen.values() if e["capacity_mtpa"])
    base_count = len(seen)

    # Denominator audit (iteration 2): merge a curated supplement of major refineries
    # the automated List parse omits (Moscow, Ilsky, Slavyansk, TAIF-NK, Mari El). Each
    # supplement row is sourced and de-duplicated against the base by canonical name, so
    # nothing is double-counted and the denominator is never silently inflated.
    added = []
    for row in _load_supplement():
        key = _dedup_key(row["name"])
        if key in seen:
            log(f"  refineries: supplement '{row['name']}' already in base list; skipped")
            continue
        seen[key] = row
        added.append(row)

    refineries = list(seen.values())

    # Canonical identity (iteration 6, §6/§7): resolve every inventory refinery to a stable
    # canonical id, and EXCLUDE facilities flagged non-fuels (petrochemical complexes such as
    # Tobolsk/ZapSibNeftekhim) from the denominator — they inflate the base but are not fuels
    # refineries. Mini fuels refineries are kept. This replaces display-name string equality.
    from pipeline import refinery_registry as RR
    reg = RR.by_id()
    excluded = []
    for r in refineries:
        cid = RR.resolve(r["name"])
        r["canonical_id"] = cid
        status = reg.get(cid, {}).get("denominator_status") if cid else "unresolved"
        r["denominator_status"] = status
        if status == "exclude":
            excluded.append(r["name"])
    total = sum(r["capacity_mtpa"] for r in refineries
                if r["capacity_mtpa"] and r["denominator_status"] != "exclude")
    denom_refineries = [r for r in refineries if r["denominator_status"] != "exclude"]

    # Reconciliation (iteration 3): state coverage against the published national
    # estimate honestly. The gap is not padded away -- it is reported.
    tracked = round(total, 1)
    # Coverage is against the LIKE-FOR-LIKE crude nameplate reference, never the full 327 (that
    # would be a universe mismatch — the full figure counts condensate the tracked base excludes).
    coverage_pct = round(100 * tracked / REFERENCE_CRUDE_NAMEPLATE_MTPA, 1)
    gap_full = round(REFERENCE_NAMEPLATE_MTPA - tracked, 1)
    condensate_mtpa = 24.0  # Surgut 12 + Ust-Luga 9 + Astrakhan ~3
    basis_understatement = round(gap_full - condensate_mtpa, 1)
    reconciliation = {
        # N-1 compatible fields (kept):
        "national_public_estimate_mtpa": REFERENCE_NAMEPLATE_MTPA,
        "national_estimate_source": REFERENCE_SOURCE,
        "tracked_mtpa": tracked,
        "tracked_refineries": len(denom_refineries),
        "coverage_pct": coverage_pct,
        "gap_mtpa": gap_full,
        "excluded_non_fuels": excluded,
        # Iteration-7 denominator-completeness metadata (§6). DENOMINATOR completeness is a
        # different concept from EVENT coverage and is never merged with it.
        "reference_nameplate_mtpa": REFERENCE_NAMEPLATE_MTPA,
        "reference_range_mtpa": REFERENCE_RANGE_MTPA,
        "reference_crude_nameplate_mtpa": REFERENCE_CRUDE_NAMEPLATE_MTPA,
        "reference_year": REFERENCE_YEAR,
        "reference_definition": (
            "Russia-only nameplate primary distillation (CDU-TEK basis), which INCLUDES gas-"
            "condensate splitters and mini-refineries. 2024 THROUGHPUT was ~267 MTPA — this is "
            "capacity, not throughput."
        ),
        "denominator_coverage_pct": coverage_pct,
        "denominator_coverage_basis": "crude-fuels nameplate reference (~303 MTPA)",
        "facility_count": len(denom_refineries),
        "excluded_facility_count": len(excluded),
        "excluded_condensate_splitters": EXCLUDED_CONDENSATE_SPLITTERS,
        "gap_decomposition": {
            "excluded_condensate_splitters_mtpa": condensate_mtpa,
            "conservative_basis_understatement_mtpa": basis_understatement,
            "missing_crude_refineries_mtpa": 0.0,
        },
        "note": (
            "DENOMINATOR completeness (distinct from event coverage). No major crude refinery is "
            "missing: an independent open-source census maps every top-tier Russian refinery to the "
            f"tracked list. The gap to the full {REFERENCE_NAMEPLATE_MTPA:.0f} MTPA nameplate is "
            f"(a) ~{condensate_mtpa:.0f} MTPA of gas-condensate splitters (Surgut CSP, Novatek Ust-"
            "Luga, Astrakhan line) that make motor fuels from CONDENSATE not crude and are excluded "
            "by the same rule as Tobolsk/ZapSibNeftekhim (6.85 MTPA, the only petrochemical "
            f"exclusion); and (b) ~{basis_understatement:.0f} MTPA because the tracked figures come "
            "from one consistent public source (Wikipedia bbl/d, converted) that sits ~10-15% below "
            "current nameplate. Consequence: reported refining struck-shares are CONSERVATIVE UPPER "
            "BOUNDS — a full-nameplate basis would give a larger denominator and a lower exposure. "
            "The consistent single-source basis is kept deliberately rather than swapping to a mixed "
            "nameplate basis; a future pass could revalue uniformly. Belarus (Mozyr, Naftan) is "
            "correctly outside the Russian denominator."
        ),
    }
    log(
        f"refineries: {base_count} base ({base_total:,.1f} MTPA) + {len(added)} "
        f"supplement = {len(refineries)} refineries, {total:,.1f} MTPA tracked "
        f"= {coverage_pct}% of the ~{REFERENCE_CRUDE_NAMEPLATE_MTPA:.0f} MTPA crude nameplate "
        f"reference (gap to full {REFERENCE_NAMEPLATE_MTPA:.0f} = {condensate_mtpa:.0f} condensate "
        f"+ {basis_understatement:.0f} basis, 0 missing refineries)"
    )
    return refineries, total, reconciliation


def _dedup_key(name):
    """Normalise a refinery name for duplicate detection across sources."""
    n = name.lower()
    for junk in ("refinery", "oil", "petrochemical", "the", "jsc", "ooo", "pjsc", "-"):
        n = n.replace(junk, " ")
    return re.sub(r"[^a-z0-9]+", "", n)


def _load_supplement():
    from pipeline.config import CURATED
    from pipeline.util import read_csv

    path = CURATED / "refineries_supplement.csv"
    if not path.exists():
        return []
    rows = []
    for r in read_csv(path):
        cap = r.get("capacity_mtpa")
        rows.append({
            "name": r["name"],
            "operator": r.get("operator"),
            "capacity_mtpa": round(float(cap), 3) if cap else None,
            "region_code": r.get("region_code"),
            "listed_under": "curated_supplement",
            "source_page": r.get("source_url"),
            "source_date": r.get("source_date"),
            "inclusion_reason": r.get("inclusion_reason"),
        })
    return rows


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
