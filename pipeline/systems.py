"""The monitored-system registry: ONE declaration of which systems exist.

A "system" is what the dashboard monitors as a unit. The original one is a theatre (Belarus,
monitored Russian regions, and Crimea as an occupied unit), not a country, and it keeps that
shape. Iteration 14 adds the five largest total-energy producers outside Russia as country
systems.

WHY THE RUSSIA THEATRE KEEPS ITS PATHS. `data/processed/` IS the theatre's root. Hundreds of
tests, the iteration-13 staging contract and every published deep link assert on it. Moving it
would buy nothing and risk all of that, so the theatre's `root` is "" and the new systems live
under `systems/<id>/`.

WHAT THIS FILE IS NOT. It holds identity and paths only. What a system's evidence supports
(sector states, reporting environment, context statistics, the reasons it has no score) is
curated per system under `data/curated/systems/<id>/system.json`, and the build validates it
against the rules in `GLOBAL_METHODOLOGY.md` §7. The frontend reads `global/manifest.json`, which
is generated from both; it holds no country constants of its own.

ORDER. `SYSTEMS` is listed alphabetically by display name and the manifest keeps that order. It
is never sorted by any figure: a country list ordered by event count reads as a league table of
danger, which is exactly the comparison the methodology forbids (GLOBAL_METHODOLOGY §6.4 rule 4).
"""

# Country-level readiness. Which state a country is in is derived by the build from its sector
# states; these are the only values it may take.
READINESS = ("INDEX_READY", "EXPERIMENTAL", "CONTEXT_ONLY", "INSUFFICIENT_EVIDENCE")

# Sector-level states (GLOBAL_METHODOLOGY §7.1). Each maps onto one of the project's three
# absences where it is an absence: INSUFFICIENT_EVIDENCE is unknown, NOT_APPLICABLE is not
# applicable, NOT_YET_RESEARCHED is not yet researched.
SECTOR_STATES = ("SCORED", "EXPERIMENTAL", "CONTEXT_ONLY", "INSUFFICIENT_EVIDENCE",
                 "NOT_APPLICABLE", "NOT_YET_RESEARCHED")

# Why counts differ between systems for reasons that have nothing to do with how much disruption
# happened (GLOBAL_METHODOLOGY §5.3.5). Every system carries one.
REPORTING_ENVIRONMENTS = {
    "mandatory_regulatory": "Operators must report qualifying outages to a regulator, and many "
                            "of those reports are public.",
    "mixed_regulatory": "Some outage reporting is mandatory and public; much is not, and press "
                        "and company statements fill the gap.",
    "corporate_disclosure": "Disruption is disclosed mainly through company and ministry "
                            "statements, usually only when material to investors or the state.",
    "media_only": "Operators and authorities do not publish event-level outage reports. Events "
                  "come from media and company statements, so most smaller disruptions will not "
                  "appear.",
    "conflict_restricted": "Disruption is reported under wartime restrictions by the authorities "
                           "concerned, so independent, attacker-side and open-source reporting "
                           "carry most of the record.",
}

SYSTEMS = (
    {"id": "ca", "name": "Canada", "kind": "country", "admin0_a3": ("CAN",)},
    {"id": "cn", "name": "China", "kind": "country", "admin0_a3": ("CHN", "HKG", "MAC")},
    {"id": "in", "name": "India", "kind": "country", "admin0_a3": ("IND",)},
    {"id": "ru", "name": "Russia, Belarus & Crimea", "kind": "theatre",
     "admin0_a3": ("RUS", "BLR"),
     # The theatre's original, unchanged home. Never moved: see the module docstring.
     "root": ""},
    {"id": "sa", "name": "Saudi Arabia", "kind": "country", "admin0_a3": ("SAU",)},
    {"id": "us", "name": "United States", "kind": "country", "admin0_a3": ("USA",)},
)

# The one system whose build is `pipeline.run`'s main body and whose headline is the ESDI.
THEATRE = "ru"

# Systems built from curated per-system sources by `pipeline.build_systems`.
COUNTRY_SYSTEMS = tuple(s["id"] for s in SYSTEMS if s["kind"] == "country")

# Why these five: EIA International Energy Statistics, total primary energy production, 2024,
# ranked over all countries (quadrillion Btu). India and Canada swap places between sources and
# years, so neither is given a fixed rank anywhere a reader can see it.
SELECTION = {
    "rule": "The five largest total primary energy producers in the world, excluding Russia.",
    "source": "U.S. EIA International Energy Statistics, total primary energy production, 2024",
    "source_url": "https://www.eia.gov/international/data/world",
    "unit": "quadrillion Btu",
    "values": {"CHN": 130.8, "USA": 103.5, "RUS": 60.3, "SAU": 26.9, "CAN": 22.6, "IND": 22.3,
               "IDN": 20.2, "IRN": 20.2, "AUS": 17.8},
    "caveat": "Canada and India differ by about 1% and swap order in the Energy Institute "
              "Statistical Review for the same year. The set of five is stable across both "
              "sources; the order within it is not, and the dashboard does not display one.",
}


def system(system_id):
    for s in SYSTEMS:
        if s["id"] == system_id:
            return s
    raise KeyError(system_id)


def root(system_id):
    """Payload directory of a system, relative to data/processed (and web/public/data)."""
    s = system(system_id)
    return s.get("root", f"systems/{system_id}")
