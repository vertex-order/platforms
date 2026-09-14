#!/usr/bin/env python3
# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
"""Ensure every Design Component carries its own <helmet> link to the
Nocturne design system, so it renders correctly previewed alone.

The DC runtime already dedupes identical <link>/<script> helmet tags by
href/src when several components compose onto one page (see support.js's
createHelmetManager), so every component declaring its own helmet costs
nothing once assembled -- it stops mattering whether the entry page's own
helmet happened to cover it too. Claude Design adds this block to a
component the moment you touch it there anyway; this just makes that the
checked-in state instead of a surprise diff on the next round-trip.

Runs from `just build` and the pre-commit hook (staged files only there),
alongside normalize-svg.py and restore-headers.py.

Usage:
  python3 scripts/ensure-helmets.py             # whole site/ tree
  python3 scripts/ensure-helmets.py PATH [PATH...]  # only these files
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"


def find_ds_dir():
    dirs = sorted(p for p in SITE.glob("_ds/*") if p.is_dir())
    if len(dirs) != 1:
        sys.exit(f"expected exactly one site/_ds/* design system, found {len(dirs)}")
    return dirs[0].name


def helmet_block(ds_dir):
    return (
        "<helmet>\n"
        f'<link rel="stylesheet" href="_ds/{ds_dir}/styles.css">\n'
        f'<script src="_ds/{ds_dir}/_ds_bundle.js"></script>\n'
        "</helmet>\n"
    )


def is_entry_page(path):
    return "components.js" in path.read_text(encoding="utf-8")


def ensure_helmet(path, block):
    text = path.read_text(encoding="utf-8")
    if is_entry_page(path) or "<helmet>" in text:
        return False
    new_text, n = re.subn(r"(<x-dc>\n)", r"\1" + block.replace("\\", "\\\\"), text, count=1)
    if n == 0:
        return False
    path.write_text(new_text, encoding="utf-8", newline="\n")
    return True


def iter_targets(paths):
    if paths:
        for p in paths:
            path = Path(p)
            if path.is_file() and path.name.endswith(".dc.html"):
                yield path.resolve()
    else:
        yield from sorted(SITE.glob("*.dc.html"))


def main(paths):
    block = helmet_block(find_ds_dir())
    changed = []
    for path in iter_targets(paths):
        if ensure_helmet(path, block):
            changed.append(path.relative_to(ROOT).as_posix())
    return changed


if __name__ == "__main__":
    for rel in main(sys.argv[1:]):
        print(f"added helmet: {rel}")
