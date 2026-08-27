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
    text = normalise_templates(text)
    found = []
    seen = set()
    pos = 0
    while pos < len(text):
        best = None
        for kind, rx in _PATTERNS:
            m = rx.search(text, pos)
            if m and (best is None or m.start() < best[1].start()):
                best = (kind, m)
        if best is None:
            break
        kind, m = best
        for value in _expand(kind, m):
            if value and value[0] not in seen:
                seen.add(value[0])
                found.append(value)
        pos = m.end()
    return found


_RANGE_RE = re.compile(rf"^(\d{{1,2}})\s*{DASH}\s*(\d{{1,2}})$")


def _days_in_list(text):
    """Expand "22-23 and 25" to [22, 23, 25]."""
    days = []
    for part in re.split(r"\s*(?:,|and|&)\s*", text.strip()):
        part = part.strip()
        if not part:
            continue
        m = _RANGE_RE.match(part)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            # A descending pair spans a month boundary ("31-2 April"); the source
            # does not say which month the first day belongs to, so take it as
            # written and keep only the endpoint we can place.
            days.extend(range(lo, hi + 1) if lo <= hi else [hi])
        elif part.isdigit():
            days.append(int(part))
    return days


def _expand(kind, m):
    try:
        if kind == "day_list":
            mon, yr = MONTHS[m[2].lower()], int(m[3])
            return [_iso(yr, mon, d) for d in _days_in_list(m[1]) if 1 <= d <= 31]
        if kind == "day_us":
            return [_iso(int(m[3]), MONTHS[m[1].lower()], int(m[2]))]
        if kind == "iso":
            return [_iso(int(m[1]), int(m[2]), int(m[3]))]
        if kind == "month":
            return [_iso(int(m[2]), MONTHS[m[1].lower()])]
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
