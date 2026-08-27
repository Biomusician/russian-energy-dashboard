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
# The brief says "Russia west of the SFD division". We read SFD as the Siberian
# Federal District and take the AOI to be every federal district west of the
# Siberian FD's western boundary, plus Belarus. That is six of Russia's eight
# federal districts; Siberian and Far Eastern are out of scope.
#
# This assumption is documented in docs/METHODOLOGY.md and is changed by editing
# AOI_FEDERAL_DISTRICTS below.
AOI_FEDERAL_DISTRICTS = {
    "Central",
    "Northwestern",
    "Southern",
    "North Caucasian",
    "Volga",
    "Ural",
}

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

BY_REGIONS = {
    "Brest":         ("BY-BR", "Brest Region",   "Belarus"),
    "Gomel":         ("BY-HO", "Gomel Region",   "Belarus"),
    "Grodno":        ("BY-HR", "Grodno Region",  "Belarus"),
    "Minsk":         ("BY-MI", "Minsk Region",   "Belarus"),
    "City of Minsk": ("BY-HM", "Minsk City",     "Belarus"),
    "Mogilev":       ("BY-MA", "Mogilev Region", "Belarus"),
    "Vitebsk":       ("BY-VI", "Vitebsk Region", "Belarus"),
}


def aoi_regions():
    """Return {natural_earth_name: (code, display_name, district, country)} for the AOI."""
    out = {}
    for ne_name, (code, name, district) in RU_REGIONS.items():
        if district in AOI_FEDERAL_DISTRICTS:
            out[ne_name] = (code, name, district, "RU")
    for ne_name, (code, name, district) in BY_REGIONS.items():
        out[ne_name] = (code, name, district, "BY")
    return out


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


# Russian federal subjects deliberately OUTSIDE the AOI. Listed only so that a
# source naming one can be recognised and reported as "out of area" rather than
# landing in the unresolved-region bucket, which is reserved for genuine parse
# failures. Siberian and Far Eastern federal districts.
OUT_OF_AOI_REGIONS = {
    "Omsk Oblast": "Siberian",
    "Novosibirsk Oblast": "Siberian",
    "Tomsk Oblast": "Siberian",
    "Kemerovo Oblast": "Siberian",
    "Irkutsk Oblast": "Siberian",
    "Krasnoyarsk Krai": "Siberian",
    "Altai Krai": "Siberian",
    "Altai Republic": "Siberian",
    "Republic of Khakassia": "Siberian",
    "Tuva Republic": "Siberian",
    "Republic of Buryatia": "Far Eastern",
    "Zabaykalsky Krai": "Far Eastern",
    "Amur Oblast": "Far Eastern",
    "Primorsky Krai": "Far Eastern",
    "Khabarovsk Krai": "Far Eastern",
    "Sakhalin Oblast": "Far Eastern",
    "Magadan Oblast": "Far Eastern",
    "Kamchatka Krai": "Far Eastern",
    "Chukotka Autonomous Okrug": "Far Eastern",
    "Sakha Republic": "Far Eastern",
    "Jewish Autonomous Oblast": "Far Eastern",
}
