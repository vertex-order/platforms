#!/usr/bin/env python3
# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
r"""Minimal parser for the JS-object-literal subset used by site/data/*.js.

Those files are plain `<script>` assignments (`window.X = {...};`), not
JSON — unquoted keys, single- or double-quoted strings, trailing commas,
and `//` line comments are all in real use, so a real JSON parser can't
read them. This is the same hand-rolled parser scripts/check-dedup-drift.py
used to carry inline (extracted here so scripts/validate-data.py can share
it without duplicating ~130 lines).

Handles: {}/[], bare or quoted object keys, single- or double-quoted
strings (\\ \" \' \n \t \r \uXXXX escapes; raw unicode passes through
untouched), int/float numbers, true/false/null, trailing commas, `//` line
comments between tokens, a bare `...identifier(.identifier)*` spread
element inside an array (dropped from the parsed result -- real usage is
exactly `...window.FAQ_ITEMS_COMMON` inside a consuming repo's
site/data/faq.js; anything spread in is a shared constant validated on its
own when the file that actually defines it is checked), and a bare member
expression as a value, optionally `&&`-guarded (e.g.
`window.SITE_CONFIG.discussionsUrl` or `window.SITE_CONFIG &&
window.SITE_CONFIG.discussionsUrl` -- real usage: a dynamic discussionsUrl
reference in a faq.js/common-faq.js answer). Not evaluated -- resolves to
a placeholder string equal to its own source text, which is enough for
schema validation since every real use is in a plain string-typed field.

Does not handle: template literals, computed/spread keys inside an object,
function values -- none of those appear in current site/data/*.js.

No external deps.
"""

import re

__all__ = ["ParseError", "parse_value", "parse_value_after"]


class ParseError(Exception):
    pass


_WS_RE = re.compile(r"\s+")
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")
_IDENT_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_NUMBER_RE = re.compile(r"-?\d+(\.\d+)?([eE][+-]?\d+)?")
_SPREAD_RE = re.compile(
    r"\.\.\.[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)*"
)
_DOTTED_RE = r"[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)*"
_MEMBER_EXPR_RE = re.compile(rf"{_DOTTED_RE}(?:\s*&&\s*{_DOTTED_RE})?")
_ESCAPES = {
    '"': '"',
    "'": "'",
    "\\": "\\",
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "b": "\b",
    "f": "\f",
}


def _skip_trivia(s, i):
    n = len(s)
    while i < n:
        m = _WS_RE.match(s, i)
        if m:
            i = m.end()
            continue
        m = _LINE_COMMENT_RE.match(s, i)
        if m:
            i = m.end()
            continue
        break
    return i


def _parse_string(s, i):
    quote = s[i]
    i += 1
    out = []
    n = len(s)
    while True:
        if i >= n:
            raise ParseError("unterminated string")
        c = s[i]
        if c == quote:
            return "".join(out), i + 1
        if c == "\\":
            i += 1
            if i >= n:
                raise ParseError("unterminated escape")
            e = s[i]
            if e == "u":
                out.append(chr(int(s[i + 1 : i + 5], 16)))
                i += 5
                continue
            out.append(_ESCAPES.get(e, e))
            i += 1
            continue
        out.append(c)
        i += 1


def _parse_object(s, i):
    i = _skip_trivia(s, i + 1)
    obj = {}
    if s[i] == "}":
        return obj, i + 1
    while True:
        i = _skip_trivia(s, i)
        if s[i] in ('"', "'"):
            key, i = _parse_string(s, i)
        else:
            m = _IDENT_RE.match(s, i)
            if not m:
                raise ParseError(
                    f"expected object key at offset {i}: {s[i : i + 40]!r}"
                )
            key, i = m.group(0), m.end()
        i = _skip_trivia(s, i)
        if s[i] != ":":
            raise ParseError(f"expected ':' at offset {i}: {s[i : i + 40]!r}")
        i = _skip_trivia(s, i + 1)
        obj[key], i = _parse_value(s, i)
        i = _skip_trivia(s, i)
        if s[i] == ",":
            i = _skip_trivia(s, i + 1)
            if s[i] == "}":
                return obj, i + 1
            continue
        if s[i] == "}":
            return obj, i + 1
        raise ParseError(f"expected ',' or '}}' at offset {i}: {s[i : i + 40]!r}")


def _parse_array(s, i):
    i = _skip_trivia(s, i + 1)
    arr = []
    if s[i] == "]":
        return arr, i + 1
    while True:
        i = _skip_trivia(s, i)
        m = _SPREAD_RE.match(s, i)
        if m:
            i = m.end()
        else:
            value, i = _parse_value(s, i)
            arr.append(value)
        i = _skip_trivia(s, i)
        if s[i] == ",":
            i = _skip_trivia(s, i + 1)
            if s[i] == "]":
                return arr, i + 1
            continue
        if s[i] == "]":
            return arr, i + 1
        raise ParseError(f"expected ',' or ']' at offset {i}: {s[i : i + 40]!r}")


def _parse_value(s, i):
    i = _skip_trivia(s, i)
    c = s[i]
    if c == "{":
        return _parse_object(s, i)
    if c == "[":
        return _parse_array(s, i)
    if c in ('"', "'"):
        return _parse_string(s, i)
    if s.startswith("true", i):
        return True, i + 4
    if s.startswith("false", i):
        return False, i + 5
    if s.startswith("null", i):
        return None, i + 4
    m = _NUMBER_RE.match(s, i)
    if m:
        text = m.group(0)
        num = float(text) if ("." in text or "e" in text or "E" in text) else int(text)
        return num, m.end()
    m = _MEMBER_EXPR_RE.match(s, i)
    if m:
        # A bare member-expression value, e.g. `window.SITE_CONFIG.discussionsUrl`
        # or `window.SITE_CONFIG && window.SITE_CONFIG.discussionsUrl` (real usage:
        # a dynamic discussionsUrl reference in a faq.js/common-faq.js answer).
        # Not evaluated -- resolves to a placeholder string equal to its own
        # source text, which is enough for schema validation (every real use is
        # in a plain string-typed field).
        return m.group(0), m.end()
    raise ParseError(f"unexpected token at offset {i}: {s[i : i + 40]!r}")


def parse_value(s, i=0):
    """Parse one JS-literal value starting at offset i. Returns (value, end_offset)."""
    return _parse_value(s, i)


def parse_value_after(text, anchor_re):
    """Find anchor_re in text, then parse the JS literal starting right after it."""
    m = anchor_re.search(text)
    if not m:
        raise ParseError(f"pattern {anchor_re.pattern!r} not found")
    value, _ = _parse_value(text, m.end())
    return value
