"""Parse the free-text date expressions used in the source tables.

The strike-date column is prose, not data. It mixes {{dts}} templates, "4 October
2025", bare "March 2024", day ranges written with an en dash, and phrases like
"At least 16 times between March 2024 and July 2026".

Every parsed date carries a precision. A month-precision date is not silently
promoted to the first of the month and then displayed as if it were exact -- the
precision travels with it so the UI and the index can both tell the difference.
"""

import re

MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        start=1,
    )
}
_MONTH_RE = "|".join(MONTHS)

DASH = r"[‐-―\-]"

# {{dts|2026-07-06|format=dmy}} and friends -> the bare ISO date.
_DTS = re.compile(r"\{\{\s*dts\s*\|\s*(\d{4}-\d{2}-\d{2})[^}]*\}\}", re.I)
_DTS_PARTS = re.compile(r"\{\{\s*dts\s*\|\s*(\d{4})\|(\d{1,2})\|(\d{1,2})[^}]*\}\}", re.I)

# A day-list sharing one trailing month and year: "22-23 and 25 May 2026" means the
# 22nd, 23rd and 25th. Matching only the last date here would silently drop two
# strikes, so the whole leading list is captured and expanded.
_DAY_ITEM = rf"\d{{1,2}}\s*{DASH}\s*\d{{1,2}}|\d{{1,2}}"
_DAY_LIST = rf"(?:{_DAY_ITEM})(?:\s*(?:,|and|&)\s*(?:{_DAY_ITEM}))*"

# Ordered most specific first; the scanner consumes left to right.
_PATTERNS = [
    # 22-23 and 25 May 2026  /  9-10 June 2026  /  4 October 2025
    ("day_list", re.compile(rf"({_DAY_LIST})\s+({_MONTH_RE})\s+(\d{{4}})", re.I)),
    # October 4, 2025
    ("day_us", re.compile(rf"({_MONTH_RE})\s+(\d{{1,2}}),?\s+(\d{{4}})", re.I)),
    # 2026-07-06
    ("iso", re.compile(r"(\d{4})-(\d{2})-(\d{2})")),
    # March 2024
    ("month", re.compile(rf"({_MONTH_RE})\s+(\d{{4}})", re.I)),
]

# Phrases meaning "repeatedly, and we are not enumerating them".
_UNENUMERATED = re.compile(
    r"at least\s+(\d+)\s+times|multiple\s+(?:times|dates)|repeatedly|numerous", re.I
)


def normalise_templates(text):
    text = _DTS_PARTS.sub(lambda m: f"{int(m[1]):04d}-{int(m[2]):02d}-{int(m[3]):02d}", text)
    text = _DTS.sub(lambda m: m.group(1), text)
    return text


def _iso(year, month, day=None):
    if day is None:
        return f"{year:04d}-{month:02d}", "month"
    return f"{year:04d}-{month:02d}-{day:02d}", "day"


def parse_dates(text):
    """Extract every date mentioned, left to right, without duplicates.

    Returns a list of (iso_string, precision) where precision is "day" or "month".
    """
    return [(iso, prec) for iso, prec, _grp in parse_dates_grouped(text)]


def parse_dates_grouped(text):
    """Like parse_dates, but each date carries an EPISODE group index.

    Dates from one contiguous day-range ("9-10 June") share a group -- they are one
    strike spanning two days. Discrete listed dates ("5 April, 20 May", or "22, 25 May")
    are separate groups -- distinct strikes. This is what lets the pipeline tell one
    multi-day incident from two independent strikes on successive days.

    Returns [(iso_string, precision, group_index)] with group_index increasing left to
    right; every date in a hyphen-range shares its group's index.
    """
    text = normalise_templates(text)
    found = []
    seen = set()
    pos = 0
    group = 0
    while pos < len(text):
        best = None
        for kind, rx in _PATTERNS:
            m = rx.search(text, pos)
            if m and (best is None or m.start() < best[1].start()):
                best = (kind, m)
        if best is None:
            break
        kind, m = best
        for iso, prec, sub in _expand_grouped(kind, m):
            if iso and iso not in seen:
                seen.add(iso)
                found.append((iso, prec, group + sub))
        # Advance the group counter past every sub-group this token produced.
        group += 1 + max((sub for *_x, sub in _expand_grouped(kind, m)), default=0)
        pos = m.end()
    return found


_RANGE_RE = re.compile(rf"^(\d{{1,2}})\s*{DASH}\s*(\d{{1,2}})$")


def _days_in_list_grouped(text):
    """Expand "22-23 and 25" to [(22,0),(23,0),(25,1)] -- range shares a subgroup,
    discrete days get their own."""
    out = []
    sub = 0
    for part in re.split(r"\s*(?:,|and|&)\s*", text.strip()):
        part = part.strip()
        if not part:
            continue
        m = _RANGE_RE.match(part)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            days = range(lo, hi + 1) if lo <= hi else [hi]
            for d in days:
                out.append((d, sub))
            sub += 1
        elif part.isdigit():
            out.append((int(part), sub))
            sub += 1
    return out


def _expand_grouped(kind, m):
    """Return [(iso, precision, subgroup)] for one matched token."""
    try:
        if kind == "day_list":
            mon, yr = MONTHS[m[2].lower()], int(m[3])
            return [(*_iso(yr, mon, d), sub) for d, sub in _days_in_list_grouped(m[1]) if 1 <= d <= 31]
        if kind == "day_us":
            return [(*_iso(int(m[3]), MONTHS[m[1].lower()], int(m[2])), 0)]
        if kind == "iso":
            return [(*_iso(int(m[1]), int(m[2]), int(m[3])), 0)]
        if kind == "month":
            return [(*_iso(int(m[2]), MONTHS[m[1].lower()]), 0)]
    except (ValueError, KeyError):
        return []
    return []


def unenumerated_count(text):
    """If the cell says "at least N times", return N; if it just says "multiple",
    return 0; otherwise None.

    The caller must not invent dates to fill this in. It is recorded as a known
    undercount so the UI can say the true event count is higher than the one shown.
    """
    m = _UNENUMERATED.search(text)
    if not m:
        return None
    return int(m.group(1)) if m.group(1) else 0


def sort_key(iso):
    """Sort month-precision dates alongside day-precision ones."""
    return iso if len(iso) == 10 else iso + "-00"
