# Data integrity — lessons and known gaps

Failures that produced no error message, and gaps we have decided to carry rather than paper
over. Both kinds belong here because both are invisible from inside the data.

---

## Lesson: `DictReader` overflow files silently under the key `None`

**Found:** iteration 11, P5, in `data/curated/sources.csv`.

A curated CSV was written with unquoted commas inside a free-text field:

```
...,Has no retirement field at all, so a closed plant stays in the base|See docs/...
```

`csv.DictReader` does not treat that as an error. It maps the declared headers to the first *n*
fields and files **everything after them in a list under the key `None`**. The row still parses.
Every field still has a value. Nothing raises, nothing warns, and the emitted JSON looks entirely
normal — it is just missing content.

Four of fourteen rows lost their final limitation this way. The WRI record lost its pointer to
`GENERATION_DENOMINATOR_AUDIT.md`; the ENTSOG record lost both the Turkey caveat and the note
about never reading `tpMapX/tpMapY` as geography. Those are exactly the kind of statement this
project exists to preserve, and they vanished without a trace.

**Why it matters beyond one file.** The dashboard's core promise is that absence is reported
rather than assumed. A parser that silently discards content violates that promise at the
cheapest possible layer, and no downstream test would notice: the sector still renders, the
source card still appears, the limitation list is merely shorter than it should be.

**The guard.** `test_every_curated_csv_parses_without_column_overflow` walks **every** file in
`data/curated/` and asserts that no row carries the `None` key and no row has fewer fields than
headers. It is deliberately generic — it globs the directory rather than naming files — so any
curated CSV added later inherits the check with no action required.

**The rule.** Write curated CSVs through `csv.writer`, never by joining strings. If you must hand-
edit one, quote any field containing a comma.

---

## Known gap: the refinery registry has no registry-level vintage

**Status:** accepted, deferred. Recorded here so it is a decision rather than an oversight.

`data/curated/refineries_canonical.csv` is the denominator for both refining and (as a borrowed
proxy) oil logistics. The Data Quality view reports its vintage as:

> maintained per-incident; see refinery_reconciliation

That is honest — the registry genuinely is maintained incrementally as incidents arrive — but it
is weaker than every other denominator in the view, each of which carries a real date. It does not
block anything, and inventing a date to fill the field would be worse than admitting there is
none.

**When this is fixed, three dates must be kept apart.** They are not the same date and collapsing
them would reintroduce exactly the conflation the source model was built to prevent:

| Field | Means |
|---|---|
| facility capacity source vintage | when the *capacity figure* for a given refinery was published by its source |
| registry maintenance date | when this project last revised the registry file |
| denominator reconciliation date | when the registry was last reconciled against the external benchmark (`refinery_reconciliation`) |

A single refinery can have a 2021 capacity figure, a 2026 registry edit, and a reconciliation from
a third date. Per-facility vintage is the substantive one; the other two describe our process, not
the world.

---

## Known gap: `natural_earth` release identifier not recorded

**Status:** open, flagged in the Data Quality view.

Natural Earth issues numbered releases, and boundary geometry shifts between them. Region shapes
and centroids depend on which release the local files came from, and that was never recorded. The
quality view reports this as a `release_expected_but_absent` gap that materially matters — as
distinct from the undated wikis, which have no releases to miss.

---

## Known gap: GEM records carry no citable release

**Status:** accepted and documented at the importer.

The GEM records come from the public map-data branch, generated from a live backend sheet with no
release identifier at all. `pipeline/import_gem.py` refuses `--release` on such a file precisely so
these records can never be laundered into a dated citation. The quality view reports the gap; the
importer prevents it becoming a false claim.
