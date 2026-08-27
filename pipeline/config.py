"""Paths, area-of-interest definition, and shared constants.

Everything in this module is deliberately data, not logic. If the area of interest
changes, or a region is reassigned between federal districts, this is the only file
that needs to move.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
CURATED = DATA / "curated"
PROCESSED = DATA / "processed"
METHODOLOGY_DIR = ROOT / "methodology"
WEB_DATA = ROOT / "web" / "public" / "data"

# Analysis window. The dashboard's time axis runs from here to the build date.
WINDOW_START = "2022-01-01"

# ---------------------------------------------------------------------------
# Area of interest
# ---------------------------------------------------------------------------
# The AOI is now explicitly locked as: Belarus, the six western Russian federal
# districts, and the Siberian Federal District. This supersedes the earlier,
# ambiguous "west of the division" phrasing from the original brief (see
# docs/METHODOLOGY.md for how that phrase was interpreted and then retired).
#
# The Far Eastern Federal District is deliberately DEFINED but NOT ENABLED: its
# regions and geometry are carried in FE_REGIONS so it can be turned on by adding
# "Far Eastern" to AOI_FEDERAL_DISTRICTS below, with no other code change. It is left
# off because open-source disruption reporting for the Far East is currently thin and
# the analytic value does not yet justify the added surface.
#
# Every geographic membership decision is a single edit to this set.
AOI_FEDERAL_DISTRICTS = {
    "Central",
    "Northwestern",
    "Southern",
    "North Caucasian",
    "Volga",
    "Ural",
    "Siberian",
}

# All federal districts we carry geometry for, whether enabled or not. Enabling the
# Far Eastern FD is adding its name to AOI_FEDERAL_DISTRICTS above.
DEFINED_FEDERAL_DISTRICTS = AOI_FEDERAL_DISTRICTS | {"Far Eastern"}

# Natural Earth's own `region` property is stale: it predates the 2010 creation of
# the North Caucasian Federal District and files the entire Southern FD under
# "Volga". It is therefore unusable and we carry our own mapping.
#
# The key is Natural Earth's `name` property for adm0_a3 in (RUS, BLR) -- that is the
# join key, because NE's iso_3166_2 codes for the two Moscow entities are swapped
# relative to the official standard. `code` below is our canonical identifier and is
# what everything downstream uses.
#
# Occupied Ukrainian territory (Crimea, Sevastopol, and the four oblasts Russia
# claims to have annexed in 2022) is excluded: these are internationally recognized
# as Ukraine and are not Russian federal subjects.
RU_REGIONS = {
    # Central Federal District
    "Belgorod":               ("RU-BEL", "Belgorod Oblast",            "Central"),
    "Bryansk":                ("RU-BRY", "Bryansk Oblast",             "Central"),
    "Vladimir":               ("RU-VLA", "Vladimir Oblast",            "Central"),
    "Voronezh":               ("RU-VOR", "Voronezh Oblast",            "Central"),
    "Ivanovo":                ("RU-IVA", "Ivanovo Oblast",             "Central"),
    "Kaluga":                 ("RU-KLU", "Kaluga Oblast",              "Central"),
    "Kostroma":               ("RU-KOS", "Kostroma Oblast",            "Central"),
    "Kursk":                  ("RU-KRS", "Kursk Oblast",               "Central"),
    "Lipetsk":                ("RU-LIP", "Lipetsk Oblast",             "Central"),
    "Moskva":                 ("RU-MOW", "Moscow",                     "Central"),
    "Moskovskaya":            ("RU-MOS", "Moscow Oblast",              "Central"),
    "Orel":                   ("RU-ORL", "Oryol Oblast",               "Central"),
    "Ryazan'":                ("RU-RYA", "Ryazan Oblast",              "Central"),
    "Smolensk":               ("RU-SMO", "Smolensk Oblast",            "Central"),
    "Tambov":                 ("RU-TAM", "Tambov Oblast",              "Central"),
    "Tver'":                  ("RU-TVE", "Tver Oblast",                "Central"),
    "Tula":                   ("RU-TUL", "Tula Oblast",                "Central"),
    "Yaroslavl'":             ("RU-YAR", "Yaroslavl Oblast",           "Central"),
    # Northwestern Federal District
    "Karelia":                ("RU-KR",  "Republic of Karelia",        "Northwestern"),
    "Komi":                   ("RU-KO",  "Komi Republic",              "Northwestern"),
    "Arkhangel'sk":           ("RU-ARK", "Arkhangelsk Oblast",         "Northwestern"),
    "Nenets":                 ("RU-NEN", "Nenets Autonomous Okrug",    "Northwestern"),
    "Vologda":                ("RU-VLG", "Vologda Oblast",             "Northwestern"),
    "Kaliningrad":            ("RU-KGD", "Kaliningrad Oblast",         "Northwestern"),
    "Leningrad":              ("RU-LEN", "Leningrad Oblast",           "Northwestern"),
    "Murmansk":               ("RU-MUR", "Murmansk Oblast",            "Northwestern"),
    "Novgorod":               ("RU-NGR", "Novgorod Oblast",            "Northwestern"),
    "Pskov":                  ("RU-PSK", "Pskov Oblast",               "Northwestern"),
    "City of St. Petersburg": ("RU-SPE", "Saint Petersburg",           "Northwestern"),
    # Southern Federal District
    "Adygey":                 ("RU-AD",  "Republic of Adygea",         "Southern"),
    "Kalmyk":                 ("RU-KL",  "Republic of Kalmykia",       "Southern"),
    "Krasnodar":              ("RU-KDA", "Krasnodar Krai",             "Southern"),
    "Astrakhan'":             ("RU-AST", "Astrakhan Oblast",           "Southern"),
    "Volgograd":              ("RU-VGG", "Volgograd Oblast",           "Southern"),
    "Rostov":                 ("RU-ROS", "Rostov Oblast",              "Southern"),
    # North Caucasian Federal District
    "Dagestan":               ("RU-DA",  "Republic of Dagestan",       "North Caucasian"),
    "Ingush":                 ("RU-IN",  "Republic of Ingushetia",     "North Caucasian"),
    "Kabardin-Balkar":        ("RU-KB",  "Kabardino-Balkar Republic",  "North Caucasian"),
    "Karachay-Cherkess":      ("RU-KC",  "Karachay-Cherkess Republic", "North Caucasian"),
    "North Ossetia":          ("RU-SE",  "North Ossetia-Alania",       "North Caucasian"),
    "Chechnya":               ("RU-CE",  "Chechen Republic",           "North Caucasian"),
    "Stavropol'":             ("RU-STA", "Stavropol Krai",             "North Caucasian"),
    # Volga Federal District
    "Bashkortostan":          ("RU-BA",  "Republic of Bashkortostan",  "Volga"),
    "Mariy-El":               ("RU-ME",  "Mari El Republic",           "Volga"),
    "Mordovia":               ("RU-MO",  "Republic of Mordovia",       "Volga"),
    "Tatarstan":              ("RU-TA",  "Republic of Tatarstan",      "Volga"),
    "Udmurt":                 ("RU-UD",  "Udmurt Republic",            "Volga"),
    "Chuvash":                ("RU-CU",  "Chuvash Republic",           "Volga"),
    "Perm'":                  ("RU-PER", "Perm Krai",                  "Volga"),
    "Kirov":                  ("RU-KIR", "Kirov Oblast",               "Volga"),
    "Nizhegorod":             ("RU-NIZ", "Nizhny Novgorod Oblast",     "Volga"),
    "Orenburg":               ("RU-ORE", "Orenburg Oblast",            "Volga"),
    "Penza":                  ("RU-PNZ", "Penza Oblast",               "Volga"),
    "Samara":                 ("RU-SAM", "Samara Oblast",              "Volga"),
    "Saratov":                ("RU-SAR", "Saratov Oblast",             "Volga"),
    "Ul'yanovsk":             ("RU-ULY", "Ulyanovsk Oblast",           "Volga"),
    # Ural Federal District
    "Kurgan":                 ("RU-KGN", "Kurgan Oblast",              "Ural"),
    "Sverdlovsk":             ("RU-SVE", "Sverdlovsk Oblast",          "Ural"),
    "Tyumen'":                ("RU-TYU", "Tyumen Oblast",              "Ural"),
    "Chelyabinsk":            ("RU-CHE", "Chelyabinsk Oblast",         "Ural"),
    "Khanty-Mansiy":          ("RU-KHM", "Khanty-Mansi AO - Yugra",    "Ural"),
    "Yamal-Nenets":           ("RU-YAN", "Yamalo-Nenets AO",           "Ural"),
}

# Siberian Federal District — added in iteration 1. Ten federal subjects.
#
# Note on Buryatia and Zabaykalsky Krai: Natural Earth's `region` field still files
# both under "Siberian", but they were transferred to the Far Eastern Federal District
# in November 2018. We follow the current administrative reality and place them in
# FE_REGIONS, so they are Far Eastern and (for now) out of the enabled AOI.
SI_REGIONS = {
    "Altay":       ("RU-ALT", "Altai Krai",              "Siberian"),
    "Gorno-Altay": ("RU-AL",  "Altai Republic",          "Siberian"),
    "Irkutsk":     ("RU-IRK", "Irkutsk Oblast",          "Siberian"),
    "Kemerovo":    ("RU-KEM", "Kemerovo Oblast (Kuzbass)", "Siberian"),
    "Khakass":     ("RU-KK",  "Republic of Khakassia",   "Siberian"),
    "Krasnoyarsk": ("RU-KYA", "Krasnoyarsk Krai",        "Siberian"),
    "Novosibirsk": ("RU-NVS", "Novosibirsk Oblast",      "Siberian"),
    "Omsk":        ("RU-OMS", "Omsk Oblast",             "Siberian"),
    "Tomsk":       ("RU-TOM", "Tomsk Oblast",            "Siberian"),
    "Tuva":        ("RU-TY",  "Tuva Republic",           "Siberian"),
}

# Far Eastern Federal District — DEFINED but not enabled. Present so the AOI can be
# extended east by a one-line change to AOI_FEDERAL_DISTRICTS, with no refactor. Eleven
# federal subjects (including Buryatia and Zabaykalsky Krai, transferred here in 2018).
FE_REGIONS = {
    "Amur":                     ("RU-AMU", "Amur Oblast",                 "Far Eastern"),
    "Buryat":                   ("RU-BU",  "Republic of Buryatia",        "Far Eastern"),
    "Chita":                    ("RU-ZAB", "Zabaykalsky Krai",            "Far Eastern"),
    "Chukchi Autonomous Okrug": ("RU-CHU", "Chukotka Autonomous Okrug",   "Far Eastern"),
    "Kamchatka":                ("RU-KAM", "Kamchatka Krai",              "Far Eastern"),
    "Khabarovsk":               ("RU-KHA", "Khabarovsk Krai",             "Far Eastern"),
    "Maga Buryatdan":           ("RU-MAG", "Magadan Oblast",              "Far Eastern"),
    "Primor'ye":                ("RU-PRI", "Primorsky Krai",              "Far Eastern"),
    "Sakha (Yakutia)":          ("RU-SA",  "Sakha Republic (Yakutia)",    "Far Eastern"),
    "Sakhalin":                 ("RU-SAK", "Sakhalin Oblast",             "Far Eastern"),
    "Yevrey":                   ("RU-YEV", "Jewish Autonomous Oblast",    "Far Eastern"),
}

BY_REGIONS = {
    "Brest":         ("BY-BR", "Brest Region",   "Belarus"),
    "Gomel":         ("BY-HO", "Gomel Region",   "Belarus"),
    "Grodno":        ("BY-HR", "Grodno Region",  "Belarus"),
    "Minsk":         ("BY-MI", "Minsk Region",   "Belarus"),
    "City of Minsk": ("BY-HM", "Minsk City",     "Belarus"),
    "Mogilev":       ("BY-MA", "Mogilev Region", "Belarus"),
    "Vitebsk":       ("BY-VI", "Vitebsk Region", "Belarus"),
}

# Every Russian federal subject we model, in one place.
ALL_RU_REGIONS = {**RU_REGIONS, **SI_REGIONS, **FE_REGIONS}

# ---------------------------------------------------------------------------
# Special analytic units — Crimea (iteration 2)
# ---------------------------------------------------------------------------
# Crimea is a deliberate, narrow exception to the blanket occupied-territory exclusion.
# It is tracked as a SEPARATELY IDENTIFIED context unit, NOT as a Russian federal
# subject: publicly reported disruption there is relevant to the picture, but Crimea is
# internationally recognised as Ukraine and is excluded from the Russia+Belarus ESDI
# denominator and composite.
#
# The exception is only to the *geographic* exclusion. Every analytic/safety limit
# (no coordinates, no range-to-target, no facility-level asset deck, no targeting)
# applies to Crimea exactly as elsewhere. See docs/METHODOLOGY.md.
#
# Geometry is the union of Natural Earth's two Crimean features, which NE files under
# adm0_a3=RUS but honestly tags with the Ukrainian ISO codes UA-43 / UA-40.
SPECIAL_UNITS = {
    "UA-CR": {
        "code": "UA-CR",
        "name": "Crimea",
        "district": "Crimea",
        "country": "UA",
        "natural_earth_names": ["Crimea", "Sevastopol"],
        "sovereignty": "Internationally recognised as Ukraine",
        "de_facto_control": "Russian-occupied since 2014",
        "analytic_scope": "context",
        "esdi_included": False,
        "note": (
            "Represented separately because it is relevant to the disruption picture. "
            "Not a Russian federal subject; excluded from the Russia+Belarus composite. "
            "The map does not adjudicate sovereignty through colour or polygon "
            "membership."
        ),
    },
}

# Other occupied Ukrainian territory that remains fully excluded. Listed so a source
# naming one is recognised and reported as "excluded (occupied Ukraine)" rather than as
# an unresolved parse failure. Natural Earth already files these under adm0_a3=UKR, so
# they never enter the region layer; this is only for source-name resolution.
OCCUPIED_EXCLUDED = {
    "Donetsk", "Donetsk Oblast", "Donetsk People's Republic",
    "Luhansk", "Lugansk", "Luhansk Oblast", "Luhansk People's Republic",
    "Zaporizhzhia", "Zaporizhzhia Oblast", "Zaporozhye", "Zaporizhia",
    "Kherson", "Kherson Oblast",
}


def aoi_regions():
    """Return {natural_earth_name: (code, display_name, district, country)} for the AOI.

    A region is in the AOI iff its federal district is currently enabled in
    AOI_FEDERAL_DISTRICTS. Belarus is always in.
    """
    out = {}
    for ne_name, (code, name, district) in ALL_RU_REGIONS.items():
        if district in AOI_FEDERAL_DISTRICTS:
            out[ne_name] = (code, name, district, "RU")
    for ne_name, (code, name, district) in BY_REGIONS.items():
        out[ne_name] = (code, name, district, "BY")
    return out


def context_units():
    """Special context units (Crimea) — tracked, but excluded from the ESDI composite."""
    return dict(SPECIAL_UNITS)


def out_of_aoi_regions():
    """{display_name: district} for every modelled Russian region NOT in the enabled AOI.

    Derived, not hand-maintained: a region is out-of-AOI exactly when its district is
    defined but not enabled. This lets region resolution recognise, e.g., a Far Eastern
    facility and report it as "out of area" rather than as an unresolved parse failure —
    a distinction the pipeline depends on to surface genuine breakage.
    """
    return {
        name: district
        for (_code, name, district) in ALL_RU_REGIONS.values()
        if district not in AOI_FEDERAL_DISTRICTS
    }


# ---------------------------------------------------------------------------
# Asset taxonomy
# ---------------------------------------------------------------------------
# The infrastructure classes the brief asks for. Taxonomy is data: the frontend
# reads these keys from the emitted JSON and never hardcodes them.
ASSET_CLASSES = {
    "power_plant_thermal":  "Thermal power plant",
    "power_plant_nuclear":  "Nuclear power plant",
    "power_plant_hydro":    "Hydroelectric dam",
    "power_plant_other":    "Other generation",
    "refinery":             "Oil refinery",
    "oil_terminal":         "Oil terminal / storage",
    "gas_processing":       "Gas processing",
    "lng_terminal":         "LNG terminal",
    "pipeline_oil":         "Oil pipeline",
    "pipeline_gas":         "Gas pipeline",
    "substation":           "Major substation",
    "transmission_line":    "Transmission line",
    "coal":                 "Coal infrastructure",
    "interconnector":       "Major interconnector",
}

# Which sub-index each asset class rolls up into. Classes absent from this map do
# not contribute to any sub-index (they are shown on the map but not scored).
SECTOR_OF_CLASS = {
    "power_plant_thermal": "electric_power",
    "power_plant_nuclear": "electric_power",
    "power_plant_hydro":   "electric_power",
    "power_plant_other":   "electric_power",
    "substation":          "electric_power",
    "transmission_line":   "electric_power",
    "interconnector":      "electric_power",
    "refinery":            "refining",
    "oil_terminal":        "oil_logistics",
    "pipeline_oil":        "oil_logistics",
    "gas_processing":      "gas",
    "lng_terminal":        "gas",
    "pipeline_gas":        "gas",
    "coal":                "coal",
}

SECTORS = {
    "refining":       "Refining",
    "electric_power": "Electric power",
    "oil_logistics":  "Oil logistics & export",
    "gas":            "Gas",
    "coal":           "Coal",
}

DISRUPTION_CAUSES = {
    "kinetic_strike":  "Kinetic strike",
    "sabotage":        "Sabotage",
    "cyber":           "Cyber",
    "technical":       "Technical accident",
    "sanctions":       "Sanctions / supply chain",
    "maintenance":     "Scheduled maintenance",
    "unknown":         "Unknown",
}

# Ordered strongest to weakest. The index down-weights weaker evidence rather than
# discarding it; see methodology/scoring.json.
CONFIDENCE_LEVELS = ["confirmed", "probable", "possible", "unverified"]

STATUS_VALUES = ["active", "degraded", "repaired", "unknown"]

# ---------------------------------------------------------------------------
# Analytic concept separation (iteration 1)
# ---------------------------------------------------------------------------
# Four distinct concepts the data model and UI must never blur together. A reported
# strike is not quantified degradation; a reported restart is not full reconstitution;
# unknown stays unknown.
ANALYTIC_CONCEPTS = {
    "exposure":    "Disruption exposure",
    "degradation": "Assessed degradation",
    "recovery":    "Recovery / restoration",
    "confidence":  "Data confidence / coverage",
}

# How a value was arrived at. Kept structurally so the UI can render observed and
# estimated facts in visibly different language and never present one as the other.
EVIDENCE_KINDS = ["observed", "estimated", "modelled", "unknown", "not_applicable"]
