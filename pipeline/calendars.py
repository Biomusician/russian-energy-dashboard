"""Dates and numbers as Gulf sources write them (iteration 19).

Persian and Arabic sources use three calendars and three sets of digits. Every conversion here is
explicit and keeps what the source wrote: a converted date carries `source_date_text`,
`date_calendar` and `conversion_basis` beside the normalised Gregorian date.

THE ONE RULE. A year is never assumed to be Gregorian. `1404` is a Solar Hijri year (2025-26) or a
Hijri one (1983-84); read as Gregorian it is the fifteenth century. `normalize_date` refuses a
Gregorian date whose year is implausible rather than pass it through.

Solar Hijri (Jalali) conversion is exact: the calendar is arithmetic in this era. Hijri conversion
uses the tabular (civil) calendar, which can differ from an observed or Umm al-Qura date by a day,
and says so in `conversion_basis`; a Hijri-dated event should not claim day precision on the
strength of this conversion alone.
"""
import datetime as dt
import re

DIGITS = {**{chr(0x0660 + i): str(i) for i in range(10)},   # Arabic-Indic ٠-٩
          **{chr(0x06F0 + i): str(i) for i in range(10)}}   # Persian and Urdu ۰-۹
DECIMAL_MARKS = {"٫": "."}                              # ٫ Arabic decimal separator
THOUSANDS_MARKS = ("٬", "،")                       # ٬ thousands separator, ، Arabic comma

CALENDARS = ("gregorian", "solar_hijri", "hijri")
# A Gregorian year outside this span in an energy-news source is a misread calendar, not a date.
GREGORIAN_PLAUSIBLE = (1900, 2100)

JALALI_MONTHS = {
    "فروردین": 1, "اردیبهشت": 2, "خرداد": 3, "تیر": 4, "مرداد": 5, "شهریور": 6,
    "مهر": 7, "آبان": 8, "آذر": 9, "دی": 10, "بهمن": 11, "اسفند": 12,
}
HIJRI_MONTHS = {
    "محرم": 1, "صفر": 2, "ربيع الأول": 3, "ربيع الآخر": 4, "ربيع الثاني": 4, "جمادى الأولى": 5,
    "جمادى الآخرة": 6, "جمادى الثانية": 6, "رجب": 7, "شعبان": 8, "رمضان": 9, "شوال": 10,
    "ذو القعدة": 11, "ذو الحجة": 12,
}


def western_digits(text):
    """`text` with Arabic-Indic and Persian digits replaced by 0-9. Nothing else changes."""
    return "".join(DIGITS.get(ch, ch) for ch in text)


def _digit_set(ch):
    if "0" <= ch <= "9":
        return "ascii"
    if "\u0660" <= ch <= "\u0669":
        return "arabic_indic"
    if "\u06F0" <= ch <= "\u06F9":
        return "persian"
    return "other" if ch.isdigit() or ch.isdecimal() else None


def parse_number(text, allow_space_groups=False):
    """A number written in any of the three digit sets, or None if `text` is not exactly one number.

    Fails closed (iteration 20). Accepted: digits; thousands groups of exactly three digits after a
    first group of one to three, separated by "," or "٬" or a space; one decimal part after "." or
    "٫". Refused, because each is a guess:
      - two numbers side by side ("10 20", "2025 2026");
      - the Arabic comma "،", which separates list items as often as thousands ("5، 300");
      - "1,5" and "12,34" (a decimal comma or a typo);
      - "1.500" (one point then exactly three digits: 1.5 in Houston, 1,500 in Berlin);
      - "0,500" and "007" (a leading zero in front of more digits);
      - mixed or repeated decimal marks;
      - a space between groups ("10 200"), unless the caller says the source groups thousands with
        spaces: Arabic and Persian sources rarely do, and two numbers side by side read the same;
      - digits from any other script ("१२३", full-width "１２３"), and digit sets mixed in one
        number ("1٢3"): int() would read them, but no source in scope writes them.
    """
    if text is None:
        return None
    sets = {_digit_set(ch) for ch in str(text)} - {None}
    if "other" in sets or len(sets) > 1:
        return None
    s = western_digits(str(text)).strip()
    if not s or "،" in s:
        return None
    s = s.replace("٫", ".").replace("٬", ",").replace("\u00a0", " ").replace("\u202f", " ")
    if " " in s and not allow_space_groups:
        return None
    m = re.fullmatch(r"([+-]?)(\d{1,3}(?:([, ])\d{3})*|\d+)(?:\.(\d+))?", s)
    if not m:
        return None
    sign, whole, sep, frac = m.group(1), m.group(2), m.group(3), m.group(4)
    if sep and re.search(r"[, ]", whole.replace(sep, "")):
        return None                                   # two different group separators
    digits = whole.replace(",", "").replace(" ", "")
    if len(digits) > 1 and digits[0] == "0":
        return None                                   # "007", "0,500"
    if frac is not None and not sep and len(frac) == 3 and 1 <= len(digits) <= 3:
        return None                                   # "1.500": thousands or decimal?
    if frac is None:
        return int(sign + digits)
    return float(f"{sign}{digits}.{frac}")


def _jalali_leap(year):
    """Leap years of the arithmetic Solar Hijri calendar (the 33-year rule used for this era)."""
    return year % 33 in (1, 5, 9, 13, 17, 22, 26, 30)


def jalali_to_gregorian(year, month, day):
    """Gregorian date of a Solar Hijri date. Raises ValueError for a date that does not exist."""
    if not 1 <= month <= 12:
        raise ValueError(f"Solar Hijri month {month} does not exist")
    length = 31 if month <= 6 else 30 if month <= 11 else (30 if _jalali_leap(year) else 29)
    if not 1 <= day <= length:
        raise ValueError(f"Solar Hijri {year}-{month:02d} has no day {day}")
    # Days from 1 Farvardin of `year`; 1 Farvardin 1 AP is 22 March 622 (proleptic Gregorian).
    days = sum(366 if _jalali_leap(y) else 365 for y in range(_ANCHOR_YEAR, year)) if year >= _ANCHOR_YEAR else \
        -sum(366 if _jalali_leap(y) else 365 for y in range(year, _ANCHOR_YEAR))
    days += (month - 1) * 31 if month <= 7 else 186 + (month - 7) * 30
    return _ANCHOR_DATE + dt.timedelta(days=days + day - 1)


# 1 Farvardin 1400 was 21 March 2021 (Nowruz, announced by Iran's calendar authority).
_ANCHOR_YEAR, _ANCHOR_DATE = 1400, dt.date(2021, 3, 21)


def _hijri_leap(year):
    """Leap years of the tabular Islamic calendar (11 in each 30-year cycle)."""
    return (14 + 11 * year) % 30 < 11


def hijri_month_length(year, month):
    """Days in a month of the TABULAR calendar: odd months 30, even 29, the twelfth 30 in a leap
    year. An observed calendar can differ; a date the tabular calendar does not have is refused
    rather than shifted."""
    if not 1 <= month <= 12:
        raise ValueError(f"Hijri month {month} does not exist")
    return 30 if month % 2 == 1 or (month == 12 and _hijri_leap(year)) else 29


def hijri_to_gregorian(year, month, day):
    """Gregorian date of a Hijri date by the tabular (civil) calendar. May be a day off an
    observed or Umm al-Qura date."""
    if not 1 <= day <= hijri_month_length(year, month):
        raise ValueError(f"Hijri {year}-{month}-{day} does not exist in the tabular calendar; give the Gregorian date")
    # Tabular Islamic calendar, civil epoch (16 July 622 Julian), 30-year cycle with 11 leap years.
    jdn = (day + (59 * (month - 1) + 1) // 2 + (year - 1) * 354 + (3 + 11 * year) // 30 + 1948439)
    return dt.date.fromordinal(jdn - 1721425)


# The years each calendar can plausibly write for a date in this project's span (1900-2100).
YEAR_SPAN = {"gregorian": GREGORIAN_PLAUSIBLE, "solar_hijri": (1278, 1480), "hijri": (1317, 1529)}
WEEKDAYS = ("شنبه", "یکشنبه", "يکشنبه", "یک‌شنبه", "دوشنبه", "سه‌شنبه", "سه شنبه", "چهارشنبه", "پنجشنبه",
            "پنج‌شنبه", "جمعه", "السبت", "الأحد", "الاحد", "الإثنين", "الاثنين", "الثلاثاء", "الأربعاء",
            "الاربعاء", "الخميس", "الجمعة", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday")
# Python weekday numbers (Monday 0) for the names above. A weekday a source writes is checked
# against the date it converts to (iteration 20, geography red team): a mismatch is a misread.
WEEKDAY_NUMBER = {"دوشنبه": 0, "سه‌شنبه": 1, "سه شنبه": 1, "چهارشنبه": 2, "پنجشنبه": 3, "پنج‌شنبه": 3,
                  "جمعه": 4, "شنبه": 5, "یکشنبه": 6, "يکشنبه": 6, "یک‌شنبه": 6,
                  "الإثنين": 0, "الاثنين": 0, "الثلاثاء": 1, "الأربعاء": 2, "الاربعاء": 2, "الخميس": 3,
                  "الجمعة": 4, "السبت": 5, "الأحد": 6, "الاحد": 6,
                  "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
# Calendar suffixes a source may write after the year, per calendar. Anything else left over is
# refused: a parser that skips what it does not understand loses the year or the day silently.
SUFFIXES = {"gregorian": ("م", "میلادی", "ميلادي", "CE", "AD"),
            "solar_hijri": ("ه.ش", "هـ.ش", "ه‍.ش", "ش", "هجری شمسی", "SH", "AP"),
            "hijri": ("هـ", "ه", "ه‍", "هجري", "هجرية", "AH")}
MONTH_NAMES = {"solar_hijri": JALALI_MONTHS, "hijri": HIJRI_MONTHS}


def _strip(s, calendar):
    """(`s` without a leading weekday and a trailing calendar suffix, the weekday number or None).
    Both are optional and explicit; a weekday must be followed by a separator."""
    s = re.sub(r"\s+", " ", s).strip().strip("،,")
    weekday = None
    for w in sorted(WEEKDAYS, key=len, reverse=True):
        if s.startswith(w):
            rest = s[len(w):]
            if rest and rest[0] not in " ،,":
                raise ValueError(f"{s!r}: a weekday must be separated from the date")
            s, weekday = rest.lstrip(" ،,"), WEEKDAY_NUMBER[w]
            break
    for suf in sorted(SUFFIXES[calendar], key=len, reverse=True):
        if s.endswith(suf) and (len(s) == len(suf) or not s[-len(suf) - 1].isalpha()):
            s = s[:-len(suf)].rstrip(" .")
            break
    return s.strip(), weekday


def _check_year(year, calendar, raw):
    lo, hi = YEAR_SPAN[calendar]
    if not lo <= year <= hi:
        what = "a Gregorian year; state the calendar" if calendar == "gregorian" else f"a {calendar} year in this span"
        raise ValueError(f"{raw!r}: year {year} is not {what}")


def _month_range(calendar, year, month):
    """First and last Gregorian day of a month written in `calendar`."""
    if calendar == "gregorian":
        first = dt.date(year, month, 1)
        last = (dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1))
        return first, last
    if calendar == "solar_hijri":
        length = 31 if month <= 6 else 30 if month <= 11 else (30 if _jalali_leap(year) else 29)
        return jalali_to_gregorian(year, month, 1), jalali_to_gregorian(year, month, length)
    return hijri_to_gregorian(year, month, 1), hijri_to_gregorian(year, month, hijri_month_length(year, month))


def normalize_date(text, calendar):
    """The date a source wrote, normalised, or ValueError. Fails closed (iteration 20).

    Returns {"source_date_text", "normalized_date", "date_calendar", "conversion_basis",
    "date_precision", "gregorian_range"}. Every character of `text` is accounted for. Accepted:

      - `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY.MM.DD`; `YYYY-MM` (month precision);
      - `D/M/YYYY` only where the day is over 12, so it cannot be read as `M/D/YYYY`;
      - `D monthname YYYY` and `monthname YYYY` with Persian or Arabic month names;
      - a Gregorian ISO timestamp (`2025-03-14T10:00:00Z`), read as its date;
      - an optional leading weekday and trailing calendar suffix (`هـ`, `ش`, `م`, ...).

    Refused: a two-digit year; day or month 0; `05/06/2025` (day and month cannot be told apart);
    a year outside the calendar's plausible span, which catches a Gregorian date given the wrong
    calendar label; a converted result outside 1900-2100; a day the calendar does not have;
    anything left over.

    MONTH PRECISION. A Solar Hijri or Hijri month runs across two Gregorian months, so it has no
    Gregorian month. For those `normalized_date` is None and `gregorian_range` gives the first and
    last Gregorian day: "Mordad 1404" is 23 July to 22 August 2025, never "July 2025". A Gregorian
    month keeps `YYYY-MM`.
    """
    if calendar not in CALENDARS:
        raise ValueError(f"unknown calendar {calendar!r}")
    raw = text
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"cannot read a date from {raw!r}")
    s = western_digits(text).strip()
    if calendar == "gregorian":
        ts = re.fullmatch(r"(\d{4}-\d{2}-\d{2})T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?", s)
        if ts:
            try:
                dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError(f"{raw!r}: not a real time") from None
            s = ts.group(1)
    s, weekday = _strip(s, calendar)
    year = month = day = None
    names = MONTH_NAMES.get(calendar, {})
    named = None
    for name in sorted(names, key=len, reverse=True):
        m = re.fullmatch(rf"(?:(\d{{1,2}}) )?{re.escape(name)} (\d{{4}})", s)
        if m:
            named, month = name, names[name]
            day = int(m.group(1)) if m.group(1) else None
            year = int(m.group(2))
            break
    if named is None:
        m = re.fullmatch(r"(\d{4})([-/.])(\d{1,2})(?:\2(\d{1,2}))?", s)
        if m:
            year, month = int(m.group(1)), int(m.group(3))
            day = int(m.group(4)) if m.group(4) else None
        else:
            m = re.fullmatch(r"(\d{1,2})([-/.])(\d{1,2})\2(\d{4})", s)
            if not m:
                raise ValueError(f"cannot read a date from {raw!r}")
            a, b, year = int(m.group(1)), int(m.group(3)), int(m.group(4))
            if a <= 12 and b <= 12 and a != b:
                raise ValueError(f"{raw!r}: day and month cannot be told apart")
            if a > 12:
                day, month = a, b
            elif b > 12:
                raise ValueError(f"{raw!r}: reads as month-first; give the date year-first")
            else:
                day, month = a, b
    if month == 0 or day == 0:
        raise ValueError(f"{raw!r}: there is no day or month 0")
    if not 1 <= month <= 12:
        raise ValueError(f"{raw!r}: month {month} does not exist")
    _check_year(year, calendar, raw)
    precision = "day" if day is not None else "month"
    if calendar == "gregorian":
        g = dt.date(year, month, day) if day else None
        basis = None
    elif calendar == "solar_hijri":
        g = jalali_to_gregorian(year, month, day) if day else None
        basis = "Solar Hijri to Gregorian, arithmetic calendar (exact)"
    else:
        g = hijri_to_gregorian(year, month, day) if day else None
        basis = "Hijri to Gregorian, tabular calendar (may differ by one day from the observed date)"
    if weekday is not None and g is None:
        raise ValueError(f"{raw!r}: a weekday with no day")
    if weekday is not None and calendar != "hijri" and g.weekday() != weekday:
        raise ValueError(f"{raw!r}: the weekday does not match {g.isoformat()}")
    if calendar == "hijri" and g is not None:
        # The tabular date can differ from the observed one by a day either way. A weekday the
        # source states settles which; without one the range says so.
        near = [g + dt.timedelta(days=k) for k in (-1, 0, 1)]
        if weekday is not None:
            match = [d for d in near if d.weekday() == weekday]
            if not match:
                raise ValueError(f"{raw!r}: the weekday matches no day within one of {g.isoformat()}")
            g = match[0]
            basis = "Hijri to Gregorian, tabular calendar, day settled by the weekday the source states"
            first = last = g
        else:
            first, last = near[0], near[2]
    else:
        first, last = (g, g) if g else _month_range(calendar, year, month)
    for d in (first, last):
        if not GREGORIAN_PLAUSIBLE[0] <= d.year <= GREGORIAN_PLAUSIBLE[1]:
            raise ValueError(f"{raw!r}: converts to {d.isoformat()}, outside {GREGORIAN_PLAUSIBLE}")
    if precision == "day":
        normalized = g.isoformat()
    elif calendar == "gregorian":
        normalized = f"{year:04d}-{month:02d}"
    else:
        normalized = None
        basis += "; month precision: the source month spans two Gregorian months, so only its Gregorian range is given"
    return {"source_date_text": raw, "normalized_date": normalized, "date_calendar": calendar,
            "conversion_basis": basis, "date_precision": precision,
            "gregorian_range": [first.isoformat(), last.isoformat()]}
