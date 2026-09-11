#!/usr/bin/env python3
# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
"""Normalize SVG element serialization to one canonical form: self-closing
tags (`<path .../>`, never `<path ...></path>`).

The committed icons are already inconsistent, and Claude Design's exporter
re-serializes each SVG unpredictably (sometimes self-closing, sometimes
not), so every design-tool round-trip risks a spurious diff. This collapses
every empty element to the self-closing form -- which is also what Bootstrap
Icons, the upstream source of these glyphs, ships -- giving a stable
check-in regardless of what the exporter produced.

Runs alongside strip-c2pa.py -- from the pre-commit hook, `just build`, and
on demand via `just normalize-svg`. Pure Python, no svgo/lxml.
"""
import re
import sys
from pathlib import Path

# <tag ...attrs...></tag>  ->  <tag ...attrs.../>
# Only genuinely empty elements collapse: the gap between the open tag's ">"
# and "</tag>" must be whitespace-only (\s* matches newlines too, so a
# close tag on its own line still collapses). Attribute values are skipped
# over so a literal ">" inside a quoted value can't end the open tag early.
EMPTY_ELEMENT = re.compile(
    r"<([a-zA-Z][\w:.-]*)((?:\"[^\"]*\"|'[^']*'|[^>\"'])*?)\s*>\s*</\1\s*>"
)


def normalize_svg(path):
    # newline="" on both ends: never translate line endings (default write
    # mode would rewrite every \n to \r\n on Windows, churning the file).
    with open(path, encoding="utf-8", newline="") as f:
        content = f.read()
    collapsed = content
    while True:
        # Loop so nested empties (<g><rect></rect></g>) fully collapse.
        next_pass = EMPTY_ELEMENT.sub(r"<\1\2/>", collapsed)
        if next_pass == collapsed:
            break
        collapsed = next_pass
    if collapsed != content:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(collapsed)
        return True
    return False


def iter_svgs(paths):
    for path in paths:
        p = Path(path)
        if p.is_dir():
            yield from sorted(p.rglob("*.svg"))
        elif p.suffix.lower() == ".svg":
            yield p


def main(paths):
    return [str(p) for p in iter_svgs(paths) if normalize_svg(str(p))]


if __name__ == "__main__":
    for path in main(sys.argv[1:]):
        print(f"normalized SVG serialization: {path}")
