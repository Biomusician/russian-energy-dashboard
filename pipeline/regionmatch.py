"""Resolve free-text region names from sources to canonical region codes.

Sources name regions loosely: "Tatarstan" for the Republic of Tatarstan, "Port of
Novorossiysk, Krasnodar Krai" for Krasnodar Krai, "Moscow" for the federal city as
distinct from "Moscow Oblast" around it.

Resolution returns one of three outcomes, and the difference matters:
  ("in_aoi", code)      -- resolved to a region we cover
  ("out_of_aoi", name)  -- a real region east of the AOI boundary
  ("unresolved", text)  -- we could not identify it; a parse failure to be reported
Collapsing the last two would hide genuine parser breakage behind "not our area".
"""

import re

from pipeline.config import ALL_RU_REGIONS, BY_REGIONS, aoi_regions, out_of_aoi_regions

# Forms that appear in sources but are not substrings of the canonical name.
ALIASES = {
    "tatarstan": "RU-TA",
    "bashkortostan": "RU-BA",
    "bashkiria": "RU-BA",
    "chechnya": "RU-CE",
    "adygea": "RU-AD",
    "kalmykia": "RU-KL",
    "dagestan": "RU-DA",
    "ingushetia": "RU-IN",
    "karelia": "RU-KR",
    "komi": "RU-KO",
    "mordovia": "RU-MO",
    "mari el": "RU-ME",
    "udmurtia": "RU-UD",
    "chuvashia": "RU-CU",
    "north ossetia": "RU-SE",
    "alania": "RU-SE",
    "kabardino balkaria": "RU-KB",
    "karachay cherkessia": "RU-KC",
    "yugra": "RU-KHM",
    "khanty mansi": "RU-KHM",
    "khanty mansiysk autonomous okrug": "RU-KHM",
    "yamalo nenets": "RU-YAN",
    "yamal": "RU-YAN",
    "st petersburg": "RU-SPE",
    "saint petersburg": "RU-SPE",
    "petersburg": "RU-SPE",
    "leningrad region": "RU-LEN",
    "moscow city": "RU-MOW",
    "nizhny novgorod": "RU-NIZ",
    "nizhegorodskaya": "RU-NIZ",
    "minsk city": "BY-HM",
    "minsk region": "BY-MI",
    "gomel": "BY-HO",
    "homel": "BY-HO",
    "hrodna": "BY-HR",
    "grodno": "BY-HR",
    "vitebsk": "BY-VI",
    "viciebsk": "BY-VI",
    "mogilev": "BY-MA",
    "mahilyow": "BY-MA",
    "brest": "BY-BR",
    # Siberian Federal District (enabled in iteration 1).
    "omsk": "RU-OMS",
    "novosibirsk": "RU-NVS",
    "tomsk": "RU-TOM",
    "kemerovo": "RU-KEM",
    "kuzbass": "RU-KEM",
    "irkutsk": "RU-IRK",
    "krasnoyarsk": "RU-KYA",
    "altai krai": "RU-ALT",
    "altai republic": "RU-AL",
    "gorno altaysk": "RU-AL",
    "khakassia": "RU-KK",
    "tuva": "RU-TY",
    "tyva": "RU-TY",
}


def _norm(text):
    text = (text or "").lower()
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _build():
    canonical = {}
    for src in (ALL_RU_REGIONS, BY_REGIONS):
        for _ne, (code, display, _district) in src.items():
            canonical[_norm(display)] = code
    aoi_codes = {v[0] for v in aoi_regions().values()}
    out_names = {_norm(n): n for n in out_of_aoi_regions()}
    return canonical, aoi_codes, out_names


_CANONICAL, _AOI_CODES, _OUT_NAMES = _build()


def resolve(text):
    """Resolve a free-text region name. See module docstring for the return shape."""
    if not text:
        return ("unresolved", text)
    n = _norm(text)
    if not n:
        return ("unresolved", text)

    # 1. Exact canonical name, then exact alias.
    if n in _CANONICAL:
        return _classify(_CANONICAL[n], text)
    if n in ALIASES:
        return _classify(ALIASES[n], text)
    if n in _OUT_NAMES:
        return ("out_of_aoi", _OUT_NAMES[n])

    # 2. Containment, longest key first. "Moscow Oblast" must beat "Moscow", and
    #    "Port of Novorossiysk, Krasnodar Krai" must find "Krasnodar Krai".
    best = None
    for table, kind in ((_CANONICAL, "code"), (ALIASES, "code"), (_OUT_NAMES, "out")):
        for key, value in table.items():
            if len(key) < 4:
                continue
            if re.search(rf"\b{re.escape(key)}\b", n):
                if best is None or len(key) > len(best[0]):
                    best = (key, value, kind)
    if best:
        return _classify(best[1], text) if best[2] == "code" else ("out_of_aoi", best[1])

    return ("unresolved", text)


def _classify(code, original):
    if code in _AOI_CODES:
        return ("in_aoi", code)
    # A code we know but that sits outside the configured AOI -- e.g. if someone
    # narrows AOI_FEDERAL_DISTRICTS.
    return ("out_of_aoi", original)
