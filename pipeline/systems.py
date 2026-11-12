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

# `aliases` are names a reader may type, including the country's own-script name. They feed search
# only: a stable id never depends on a spelling or a transliteration.
SYSTEMS = (
    {"id": "bh", "name": "Bahrain", "kind": "country", "admin0_a3": ("BHR",),
     "aliases": ("البحرين", "Kingdom of Bahrain")},
    {"id": "ca", "name": "Canada", "kind": "country", "admin0_a3": ("CAN",)},
    {"id": "cn", "name": "China", "kind": "country", "admin0_a3": ("CHN", "HKG", "MAC")},
    {"id": "in", "name": "India", "kind": "country", "admin0_a3": ("IND",)},
    {"id": "ir", "name": "Iran", "kind": "country", "admin0_a3": ("IRN",),
     "aliases": ("ایران", "Islamic Republic of Iran", "Persia")},
    {"id": "iq", "name": "Iraq", "kind": "country", "admin0_a3": ("IRQ",),
     "aliases": ("العراق", "عێراق", "Republic of Iraq")},
    {"id": "kw", "name": "Kuwait", "kind": "country", "admin0_a3": ("KWT",),
     "aliases": ("الكويت", "State of Kuwait")},
    {"id": "om", "name": "Oman", "kind": "country", "admin0_a3": ("OMN",),
     "aliases": ("عُمان", "عمان", "Sultanate of Oman")},
    {"id": "qa", "name": "Qatar", "kind": "country", "admin0_a3": ("QAT",),
     "aliases": ("قطر", "State of Qatar")},
    {"id": "ru", "name": "Russia, Belarus & Crimea", "kind": "theatre",
     "admin0_a3": ("RUS", "BLR"),
     # The theatre's original, unchanged home. Never moved: see the module docstring.
     "root": ""},
    {"id": "sa", "name": "Saudi Arabia", "kind": "country", "admin0_a3": ("SAU",),
     "aliases": ("السعودية", "المملكة العربية السعودية", "KSA")},
    {"id": "ae", "name": "United Arab Emirates", "kind": "country", "admin0_a3": ("ARE",),
     "aliases": ("الإمارات", "الإمارات العربية المتحدة", "UAE", "Emirates")},
    {"id": "us", "name": "United States", "kind": "country", "admin0_a3": ("USA",),
     "aliases": ("USA", "US", "United States of America")},
)

# GROUPS (iteration 19). Four different things that are easy to conflate, kept as separate facts:
# a geographic group (the Gulf littoral), and two memberships (GCC, OPEC). Iran and Iraq border the
# Gulf and belong to OPEC but not to the GCC; Bahrain, Qatar and Oman are GCC members outside OPEC.
# Groups are navigation and context. They never enter a score, and no group has an index.
GROUPS = {
    "gulf_littoral": {
        "label": "Gulf littoral",
        # A group with a `slug` has a regional overview at ?group=<slug>, fed by `context`.
        "slug": "gulf",
        "context": "global/gulf.json",
        "kind": "geographic",
        "members": ("bh", "ir", "iq", "kw", "om", "qa", "sa", "ae"),
        "note": "The eight states on the Gulf. A geographic group, not an organisation: it is not "
                "the GCC and not OPEC.",
    },
    "gcc": {
        "label": "GCC",
        "kind": "membership",
        "members": ("bh", "kw", "om", "qa", "sa", "ae"),
        "as_of": "2026-11-11",
        "basis": "The six founding members of 1981. No change of membership is reported.",
        "note": "Members of the Gulf Cooperation Council. Iran and Iraq are not members.",
    },
    "opec": {
        "label": "OPEC",
        "kind": "membership",
        # The UAE announced its withdrawal on 2026-04-28, effective 2026-05-01 (WAM). The brief for
        # iteration 19 listed it as a member; the membership published is today's.
        "members": ("ir", "iq", "kw", "sa"),
        "as_of": "2026-11-11",
        "former_members": {"ae": "The United Arab Emirates was an OPEC member until 2026-04-30; the annual "
                                 "figures shown here are for a year in which it was a member."},
        "note": "Monitored systems that are OPEC members today. The United Arab Emirates left on "
                "2026-05-01, as its government announced on 2026-04-28; OPEC's own member page "
                "refused access when this was checked, so the list rests on that announcement as "
                "reported. Membership is context only; an OPEC production decision is policy, never "
                "a disruption record.",
        "basis": "UAE government announcement of 2026-04-28 (state news agency, widely reported); "
                 "opec.org returned HTTP 402 on 2026-11-11 and was not read.",
    },
}


def groups_of(system_id):
    return tuple(g for g, d in GROUPS.items() if system_id in d["members"])

# The one system whose build is `pipeline.run`'s main body and whose headline is the ESDI.
THEATRE = "ru"

# Systems built from curated per-system sources by `pipeline.build_systems`.
COUNTRY_SYSTEMS = tuple(s["id"] for s in SYSTEMS if s["kind"] == "country")

# Why the Gulf systems (iteration 19): a regional expansion decided by the owner, not by the
# five-largest rule below. Stated so nobody reads the Gulf systems as "the next largest".
GULF_SELECTION = {
    "rule": "Seven Gulf states were added in iteration 19 as a geographic expansion alongside "
            "Saudi Arabia: Bahrain, Iran, Iraq, Kuwait, Oman, Qatar and the United Arab Emirates. "
            "They were not chosen by production size, and no order among them is displayed.",
}

# Why these five: EIA International Energy Statistics, total primary energy production, 2024,
# ranked over all countries (quadrillion Btu). India and Canada swap places between sources and
# years, so neither is given a fixed rank anywhere a reader can see it.
SELECTION = {
    "rule": "The first five country systems are the five largest total primary energy producers "
            "in the world, excluding Russia: Canada, China, India, Saudi Arabia and the United States.",
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
