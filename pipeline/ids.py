"""Stable identifiers, shared by every monitored system.

WHY THIS EXISTS. Until iteration 14 a facility id was its name slugged and cut at 60 characters.
Truncation is not identity: two names sharing a 60-character prefix became one facility, silently,
and `ust-luga-multimodal-complex-ust-luga-oil-jsc-terminal-nevska` already sat exactly on that
edge. Six systems importing their own facility names make a silent merge a matter of time.

THE RULE.
- A slug that fits is the slug, unchanged — so every id already published stays where it is.
- A slug that does not fit keeps a readable prefix and gains a short hash of the WHOLE slug, so
  two long names that share a prefix stay distinct.
- One id already published under the old truncating rule is grandfathered at its old value:
  incident ids, recovery records and saved links are keyed on it, and identity must not move
  because the rule that produced it was improved.
- Within one system an id is local; across systems the key is `<system>:<local id>`. No id is ever
  assumed unique across countries.
"""

import hashlib
import re

MAX_SLUG = 60
_HASH_LEN = 8

# full untruncated slug -> the id it was published under before iteration 14.
GRANDFATHERED = {
    "ust-luga-multimodal-complex-ust-luga-oil-jsc-terminal-nevskaya-opc-terminal-novatek-terminal":
        "ust-luga-multimodal-complex-ust-luga-oil-jsc-terminal-nevska",
}


def full_slug(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def slug(name):
    s = full_slug(name)
    if not s:
        return "unnamed"
    if s in GRANDFATHERED:
        return GRANDFATHERED[s]
    if len(s) <= MAX_SLUG:
        return s
    digest = hashlib.sha1(s.encode("utf-8")).hexdigest()[:_HASH_LEN]
    return s[:MAX_SLUG - _HASH_LEN - 1].rstrip("-") + "-" + digest


def global_key(system_id, local_id):
    """The cross-system identity of a record. Local ids repeat across countries by design."""
    if not system_id or ":" in system_id:
        raise ValueError(f"bad system id {system_id!r}")
    return f"{system_id}:{local_id}"


def collisions(pairs):
    """{id: sorted names} for every id that more than one DISTINCT name produced.

    `pairs` is an iterable of (id, name). The same name appearing twice is the same facility
    and is not a collision; two different names on one id is a merge nobody decided on.
    """
    by_id = {}
    for i, name in pairs:
        by_id.setdefault(i, set()).add(" ".join((name or "").split()))
    return {i: sorted(ns) for i, ns in by_id.items() if len(ns) > 1}
