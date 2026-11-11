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


def parse_number(text):
    """A number written in any of the three digit sets, or None if `text` is not one number.

    Handles the Arabic decimal mark and thousands separators. A string with two candidate decimal
    points, or with anything left over, is refused: guessing which comma is the decimal is how
    1,500 becomes 1.5.
    """
    if text is None:
        return None
    s = western_digits(str(text)).strip()
    for mark, repl in DECIMAL_MARKS.items():
        s = s.replace(mark, repl)
    for mark in THOUSANDS_MARKS:
        s = s.replace(mark, ",")
    s = s.replace(" ", "").replace(" ", "")
    if not re.fullmatch(r"[+-]?(\d{1,3}(,\d{3})+|\d+)(\.\d+)?", s):
        return None
    value = float(s.replace(",", ""))
    return int(value) if value.is_integer() and "." not in s else value


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


def hijri_to_gregorian(year, month, day):
    """Gregorian date of a Hijri date by the tabular (civil) calendar. May be a day off an
    observed or Umm al-Qura date."""
    if not (1 <= month <= 12 and 1 <= day <= 30):
        raise ValueError(f"Hijri {year}-{month}-{day} does not exist")
    # Tabular Islamic calendar, civil epoch (16 July 622 Julian), 30-year cycle with 11 leap years.
    jdn = (day + (59 * (month - 1) + 1) // 2 + (year - 1) * 354 + (3 + 11 * year) // 30 + 1948439)
    return dt.date.fromordinal(jdn - 1721425)


def normalize_date(text, calendar):
    """The date a source wrote, normalised.

    Returns {"source_date_text", "normalized_date", "date_calendar", "conversion_basis",
    "date_precision"}. `text` is `Y-M-D`, `Y/M/D`, `D monthname Y` (Persian or Arabic month names)
    or `Y-M` / `monthname Y` for month precision, in any digit set. Raises ValueError rather than
    guess: an unknown calendar, an impossible date, or a "Gregorian" year that is plainly not one.
    """
    if calendar not in CALENDARS:
        raise ValueError(f"unknown calendar {calendar!r}")
    raw = text
    s = western_digits(text).strip()
    months = JALALI_MONTHS if calendar == "solar_hijri" else HIJRI_MONTHS if calendar == "hijri" else {}
    year = month = day = None
    for name, n in sorted(months.items(), key=lambda kv: -len(kv[0])):
        if name in s:
            nums = [int(x) for x in re.findall(r"\d+", s.replace(name, " "))]
            month = n
            if len(nums) == 2:
                day, year = (nums[0], nums[1]) if nums[1] > 31 else (nums[1], nums[0])
            elif len(nums) == 1:
                year = nums[0]
            else:
                raise ValueError(f"cannot read a date from {raw!r}")
            break
    if month is None:
        nums = [int(x) for x in re.split(r"[-/.]", s) if x.strip().isdigit()]
        if len(nums) == 3:
            year, month, day = nums if nums[0] > 31 else nums[::-1]
        elif len(nums) == 2:
            year, month = nums if nums[0] > 31 else nums[::-1]
        else:
            raise ValueError(f"cannot read a date from {raw!r}")
    precision = "day" if day is not None else "month"
    if calendar == "gregorian":
        if not GREGORIAN_PLAUSIBLE[0] <= year <= GREGORIAN_PLAUSIBLE[1]:
            raise ValueError(f"{raw!r}: year {year} is not a Gregorian year; state the calendar")
        g = dt.date(year, month, day or 1)
        basis = None
    elif calendar == "solar_hijri":
        g = jalali_to_gregorian(year, month, day or 1)
        basis = "Solar Hijri to Gregorian, arithmetic calendar (exact)"
    else:
        g = hijri_to_gregorian(year, month, day or 1)
        basis = "Hijri to Gregorian, tabular calendar (may differ by one day from the observed date)"
    if precision == "month" and calendar != "gregorian":
        # A non-Gregorian month straddles two Gregorian months: say which month it starts in.
        basis += "; month precision, Gregorian month of the first day"
    return {"source_date_text": raw, "normalized_date": g.isoformat() if precision == "day" else g.isoformat()[:7],
            "date_calendar": calendar, "conversion_basis": basis, "date_precision": precision}
