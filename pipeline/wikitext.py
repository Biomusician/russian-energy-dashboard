"""Minimal wikitext cleaning and table parsing.

Only as much MediaWiki syntax as the source tables actually use. A general wikitext
parser is a large dependency for a job this narrow, and the failure mode we care
about -- silently mangling a row -- is easier to catch in fifty lines we can read
than in someone else's parser.
"""

import re

_REF_PAIR = re.compile(r"<ref[^>/]*>.*?</ref>", re.S | re.I)
_REF_SELF = re.compile(r"<ref[^>]*/>", re.I)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_TAGS = re.compile(r"</?(?:small|sup|sub|span|div|b|i|nowrap)[^>]*>", re.I)
_BR = re.compile(r"<br\s*/?>", re.I)


def strip_braces(text, keep=()):
    """Remove {{template}} calls, honouring nesting.

    Templates named in `keep` are returned as `\x00name|arg|arg\x00` so a caller can
    pull structured values (dates, mainly) back out after the rest is stripped.
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("{{", i):
            depth = 1
            j = i + 2
            while j < n and depth:
                if text.startswith("{{", j):
                    depth += 1
                    j += 2
                elif text.startswith("}}", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            inner = text[i + 2 : j - 2]
            name = inner.split("|", 1)[0].strip().lower()
            if name in keep:
                out.append("\x00" + inner + "\x00")
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def strip_links(text):
    """[[Target|Label]] -> Label, [[Target]] -> Target, [url Label] -> Label."""
    text = re.sub(r"\[\[(?:[^\[\]|]*\|)?([^\[\]|]*)\]\]", r"\1", text)
    text = re.sub(r"\[(?:https?|//)\S+\s+([^\]]*)\]", r"\1", text)
    text = re.sub(r"\[(?:https?|//)\S+\]", "", text)
    return text


def clean_cell(text, keep_templates=()):
    text = _COMMENT.sub("", text)
    text = _REF_PAIR.sub("", text)
    text = _REF_SELF.sub("", text)
    text = _BR.sub(" ", text)
    text = strip_braces(text, keep=keep_templates)
    text = strip_links(text)
    text = _TAGS.sub("", text)
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


_PLACEHOLDER = "\x01{}\x01"
_PLACEHOLDER_RE = re.compile(r"\x01(\d+)\x01")


def protect(text):
    """Replace <ref>...</ref> blocks and {{templates}} with opaque placeholders.

    Cell splitting keys on newlines and pipes, and both appear freely inside a
    multi-line {{cite web|title=...|url=...}} inside a <ref>. Splitting first turns
    one citation into a dozen phantom cells and shifts the whole row. So these spans
    are lifted out before any structural parsing and put back afterwards -- which
    also keeps the citation source intact for provenance extraction.
    """
    spans = []

    def take(match):
        spans.append(match.group(0))
        return _PLACEHOLDER.format(len(spans) - 1)

    text = _COMMENT.sub("", text)
    text = _REF_PAIR.sub(take, text)
    text = _REF_SELF.sub(take, text)
    text = _protect_braces(text, spans)
    return text, spans


def _protect_braces(text, spans):
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("{{", i):
            depth = 1
            j = i + 2
            while j < n and depth:
                if text.startswith("{{", j):
                    depth += 1
                    j += 2
                elif text.startswith("}}", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            spans.append(text[i:j])
            out.append(_PLACEHOLDER.format(len(spans) - 1))
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def restore(text, spans):
    return _PLACEHOLDER_RE.sub(lambda m: spans[int(m.group(1))], text)


def refs_in(text, spans):
    """Return the source of every <ref> appearing in a cell, including nested ones.

    WHY IT RECURSES. `protect()` lifts out refs first and brace templates second, so a citation
    written inside an explanatory footnote -- `6 April 2026,{{efn|...<ref name="MT CPC">...}}` --
    ends up as a ref placeholder INSIDE a template placeholder. A non-recursive scan sees only
    the template and reports the date as uncited, which is how the CPC marine terminal strike
    came to carry no provenance while the source page cites it in a footnote.

    Order is preserved and each ref is yielded once, because citation order within a cell is
    the only thing distinguishing a definition from a later reuse of the same name.
    """
    out = []
    seen = set()

    def walk(fragment):
        for m in _PLACEHOLDER_RE.finditer(fragment):
            idx = int(m.group(1))
            span = spans[idx]
            if span.lower().startswith("<ref"):
                if idx not in seen:
                    seen.add(idx)
                    out.append(span)
            elif _PLACEHOLDER_RE.search(span):
                # A brace template that itself holds protected refs: {{efn|…<ref/>…}}.
                walk(span)

    walk(text)
    return out


def leading_refs(text, spans):
    """Split `text` into (its leading citation placeholders, the rest).

    Needed because the source puts a date's citation AFTER the comma that follows the date:
    `5 April 2026,<ref/> 20 May 2026,<ref/>`. Splitting the cell on commas therefore puts each
    date's refs at the START of the NEXT fragment, and they have to be handed back.

    A citation here is a `<ref>` OR a footnote template that contains one. The CPC marine
    terminal strike is cited as `6 April 2026,{{efn|…<ref name="MT CPC">…}}` -- same convention,
    wrapped in an explanatory footnote -- and treating only bare refs as citations left that
    date uncited while handing its footnote to the following date.
    """
    i = 0
    n = len(text)
    refs = []
    while i < n:
        if text[i].isspace():
            i += 1
            continue
        m = _PLACEHOLDER_RE.match(text, i)
        if not m:
            break
        span = spans[int(m.group(1))]
        is_ref = span.lower().startswith("<ref")
        # A template is a citation token only if it actually holds a protected ref; a
        # {{dts}} date template must stay exactly where the source put it.
        holds_ref = (not is_ref) and bool(_PLACEHOLDER_RE.search(span)) and any(
            spans[int(x)].lower().startswith("<ref") for x in _PLACEHOLDER_RE.findall(span))
        if not (is_ref or holds_ref):
            break
        refs.append(m.group(0))
        i = m.end()
    return refs, text[i:]


def find_tables(wikitext):
    """Return the raw source of each top-level {| ... |} table, nesting-aware."""
    tables = []
    i = 0
    n = len(wikitext)
    while i < n:
        if wikitext.startswith("{|", i):
            depth = 1
            j = i + 2
            while j < n and depth:
                if wikitext.startswith("{|", j):
                    depth += 1
                    j += 2
                elif wikitext.startswith("|}", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            tables.append(wikitext[i:j])
            i = j
        else:
            i += 1
    return tables


def parse_table(table_src):
    """Parse a wikitable into (headers, rows-of-raw-cells).

    Handles both the `| a | b` inline form and the `| a` newline form, the `||` cell
    separator, and rowspan. Rowspan matters here: the source tables group several
    facilities at one port under a single Region cell, and without expanding it every
    continuation row shifts one column left and silently mis-assigns its region.

    Returns (headers, rows, spans). Cell text still contains placeholders for refs
    and templates; pass `spans` to restore() or refs_in() to get them back.
    """
    body = table_src
    if body.startswith("{|"):
        body = body[body.find("\n") + 1 :]
    if body.rstrip().endswith("|}"):
        body = body.rstrip()[:-2]

    body, spans = protect(body)

    # Row separator is a line beginning with |-
    chunks = re.split(r"\n\|-+[^\n]*\n?", body)

    headers = []
    raw_rows = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        cells = _split_cells(chunk)
        if not cells:
            continue
        if chunk.lstrip().startswith("!"):
            headers = [_strip_cell_marker(c, "!")[1] for c in cells]
        else:
            raw_rows.append([_strip_cell_marker(c, "|") for c in cells])

    return headers, _expand_rowspans(raw_rows, len(headers)), spans


def _expand_rowspans(raw_rows, ncols):
    """Re-place cells carried down by rowspan into their original column index."""
    pending = {}  # column index -> [remaining_rows, text]
    out = []
    for cells in raw_rows:
        row = [None] * max(ncols, len(cells) + len(pending))
        for col, entry in list(pending.items()):
            if col < len(row):
                row[col] = entry[1]
            entry[0] -= 1
            if entry[0] <= 0:
                del pending[col]

        col = 0
        for span, text in cells:
            while col < len(row) and row[col] is not None:
                col += 1
            if col >= len(row):
                row.append(text)
            else:
                row[col] = text
            if span > 1:
                pending[col] = [span - 1, text]
            col += 1

        out.append([c for c in row if c is not None])
    return out


def _split_cells(chunk):
    """Split a row chunk into cell sources."""
    cells = []
    for line in chunk.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("!"):
            parts = re.split(r"!!", stripped[1:])
            cells.extend("!" + p for p in parts)
        elif stripped.startswith("|"):
            parts = re.split(r"\|\|", stripped[1:])
            cells.extend("|" + p for p in parts)
        elif cells:
            # Continuation of the previous cell (a template spanning lines).
            cells[-1] += "\n" + line
    return cells


# A cell may carry HTML attributes before a single pipe: `width="10%" | Region`,
# `rowspan=3| Port of Novorossiysk`. Values appear both quoted and bare in the
# source, so both forms have to be accepted.
_ATTR = r'[a-zA-Z-]+\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s|]+)'
_ATTR_BLOCK = re.compile(rf"\s*{_ATTR}(?:\s+{_ATTR})*\s*\|(?!\|)")
_ROWSPAN = re.compile(r"""rowspan\s*=\s*["']?(\d+)""", re.I)


def _strip_cell_marker(cell, marker):
    """Return (rowspan, text) for one cell."""
    cell = cell.lstrip(marker)
    span = 1
    m = _ATTR_BLOCK.match(cell)
    if m:
        attrs = cell[: m.end()]
        rs = _ROWSPAN.search(attrs)
        if rs:
            span = int(rs.group(1))
        cell = cell[m.end() :]
    return span, cell.strip()
