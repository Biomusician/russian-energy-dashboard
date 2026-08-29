"""Resolve free-text region names from sources to canonical region codes.

Sources name regions loosely: "Tatarstan" for the Republic of Tatarstan, "Port of
Novorossiysk, Krasnodar Krai" for Krasnodar Krai, "Moscow" for the federal city as
distinct from "Moscow Oblast" around it.

Resolution returns one of five outcomes, and the differences matter:
  ("in_aoi", code)           -- a Russia/Belarus region we cover and score
  ("context", "UA-CR")       -- Crimea: a separately-identified occupied unit, tracked and
                                (since iteration 4) included in the Monitored-Area index
  ("excluded_occupied", name)-- other occupied Ukrainian territory, fully excluded
  ("out_of_aoi", name)       -- a real Russian region east of the enabled AOI boundary
  ("unresolved", text)       -- could not identify it; a parse failure to be reported
Collapsing any of these would hide either a scope decision or genuine parser breakage.
"""

import re

from pipeline.config import (
    ALL_RU_REGIONS, BY_REGIONS, OCCUPIED_EXCLUDED, SPECIAL_UNITS,
    aoi_regions, context_units, out_of_aoi_regions,
)

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


# Crimea and Sevastopol names/aliases → the single context unit.
_CRIMEA_ALIASES = {
    "crimea", "republic of crimea", "autonomous republic of crimea",
    "sevastopol", "simferopol", "kerch", "feodosia", "feodosiya",
    "crimean peninsula", "saky", "dzhankoi",
}


def _build():
    canonical = {}
    for src in (ALL_RU_REGIONS, BY_REGIONS):
        for _ne, (code, display, _district) in src.items():
            canonical[_norm(display)] = code
    aoi_codes = {v[0] for v in aoi_regions().values()}
    out_names = {_norm(n): n for n in out_of_aoi_regions()}
    occupied = {_norm(n): n for n in OCCUPIED_EXCLUDED}
    crimea_code = next(iter(SPECIAL_UNITS))  # "UA-CR"
    context_codes = set(context_units())
    return canonical, aoi_codes, out_names, occupied, crimea_code, context_codes


_CANONICAL, _AOI_CODES, _OUT_NAMES, _OCCUPIED, _CRIMEA_CODE, _CONTEXT_CODES = _build()


def resolve(text):
    """Resolve a free-text region name. See module docstring for the return shape."""
    if not text:
        return ("unresolved", text)
    n = _norm(text)
    if not n:
        return ("unresolved", text)

    # 0. Crimea first — it must never be mistaken for a RUSSIAN region: it resolves to its own
    #    "context" class with occupied styling. (Whether it enters the monitored-area aggregate
    #    is a separate downstream decision via esdi_included, currently True — it DOES contribute.
    #    That is not decided here.) Other occupied Ukrainian territory stays fully excluded.
    if n in _CRIMEA_ALIASES or any(re.search(rf"\b{re.escape(a)}\b", n) for a in _CRIMEA_ALIASES):
        return ("context", _CRIMEA_CODE)
    if n in _OCCUPIED:
        return ("excluded_occupied", _OCCUPIED[n])

    # 1. Exact canonical name, then exact alias.
    if n in _CANONICAL:
        return _classify(_CANONICAL[n], text)
    if n in ALIASES:
        return _classify(ALIASES[n], text)
    if n in _OUT_NAMES:
        return ("out_of_aoi", _OUT_NAMES[n])
    if n in _OCCUPIED:
        return ("excluded_occupied", _OCCUPIED[n])

    # 2. Containment, longest key first. "Moscow Oblast" must beat "Moscow", and
    #    "Port of Novorossiysk, Krasnodar Krai" must find "Krasnodar Krai".
    best = None
    for table, kind in (
        (_CANONICAL, "code"), (ALIASES, "code"),
        (_OUT_NAMES, "out"), (_OCCUPIED, "occupied"),
    ):
        for key, value in table.items():
            if len(key) < 4:
                continue
            if re.search(rf"\b{re.escape(key)}\b", n):
                if best is None or len(key) > len(best[0]):
                    best = (key, value, kind)
    if best:
        if best[2] == "code":
            return _classify(best[1], text)
        if best[2] == "occupied":
            return ("excluded_occupied", best[1])
        return ("out_of_aoi", best[1])

    return ("unresolved", text)


def _classify(code, original):
    if code in _AOI_CODES:
        return ("in_aoi", code)
    # A code we know but that sits outside the configured AOI -- e.g. if someone
    # narrows AOI_FEDERAL_DISTRICTS.
    return ("out_of_aoi", original)
