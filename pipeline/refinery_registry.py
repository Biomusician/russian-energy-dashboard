"""Canonical refinery identity layer (iteration 6, §6).

One stable id + alias set per tracked refinery, so the denominator inventory, the Wikipedia
strike parse, curated incidents, candidate incidents and recovery evidence all resolve to the
SAME canonical asset instead of joining by fragile display-name string equality. Designed to
generalise later into a `canonical_asset_registry` for other classes (§31) without a rewrite.

Resolution is EXACT normalized-alias match only — an unknown or ambiguous name returns None
and is never silently guessed into a mapping (§7).
"""
import csv
import re

from pipeline.config import CURATED

_GENERIC = {"refinery", "npz", "oil", "the", "complex", "petrochemical", "company", "plant"}
_REGISTRY = None
_ALIAS_INDEX = None


def _norm(s):
    s = re.sub(r"[^a-z0-9]+", " ", (s or "").lower())
    return " ".join(t for t in s.split() if t not in _GENERIC).strip()


def load():
    """Return the list of canonical refinery rows (cached)."""
    global _REGISTRY
    if _REGISTRY is None:
        path = CURATED / "refineries_canonical.csv"
        rows = []
        with open(path, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                r["aliases"] = [a for a in r["aliases"].split("|") if a]
                rows.append(r)
        _REGISTRY = rows
    return _REGISTRY


def _index():
    global _ALIAS_INDEX
    if _ALIAS_INDEX is None:
        idx = {}
        for r in load():
            for a in [r["canonical_id"], r["canonical_name"], *r["aliases"]]:
                key = _norm(a)
                if key:
                    idx.setdefault(key, r["canonical_id"])
        _ALIAS_INDEX = idx
    return _ALIAS_INDEX


def resolve(text):
    """canonical_id for a refinery name/id/alias, or None (no fuzzy guessing)."""
    return _index().get(_norm(text))


def by_id():
    return {r["canonical_id"]: r for r in load()}


def denominator_ids():
    """Canonical ids that count toward the fuels-refining denominator (excludes petrochemical
    complexes flagged `exclude`; mini fuels refineries are kept)."""
    return {r["canonical_id"] for r in load() if r["denominator_status"] != "exclude"}
