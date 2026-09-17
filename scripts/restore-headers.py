#!/usr/bin/env python3
# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
"""Restore the "owned by vertex-order/X" header comment on site/ files that
carry one, when a design-tool round-trip has stripped it.

Claude Design overwrites site/ wholesale on export and doesn't preserve a
leading ownership comment on every file type it touches -- so a round-trip
silently drops the header on `*.dc.html` components, `_ds/` CSS and
markdown, and support.js. When a file's header is fully missing, this
inserts one naming the owner sync.toml implies (this repo's own
[publish].owner for a path under [publish].paths, or a [subscribe.<name>].repo
for a path under that subscription) -- but sync.toml only tells you where
*this* repo fetches a path from, not who first authored it: if some future
path were ever subscribed transitively (repo A pulls it from repo B, which
itself only pulled it from repo C), this script would infer owner "B" for a
file actually owned by "C". So a header that's already present and well-formed, for *any*
vertex-order/* owner, is left completely alone (only its wrapping is
normalized) -- sync.toml's inferred owner is strictly a fallback for
filling in a blank, never a value that overwrites one already there. This
keeps `just build` output safe to diff -- header noise self-clears the same
way normalize-svg.py already clears SVG serialization noise.

Runs from `just build` and the pre-commit hook (staged files only there),
alongside normalize-svg.py and ensure-helmets.py.

Usage:
  python3 scripts/restore-headers.py             # whole site/ tree
  python3 scripts/restore-headers.py PATH [PATH...]  # only these files
"""
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
SYNC_TOML = ROOT / "sync.toml"

SUPPORT_JS_HEADER = (
    "// Owned by vertex-order/kit — vendored elsewhere via sync.toml; don't edit\n"
    "// the copy there. GENERATED from dc-runtime/src/*.ts — do not edit here\n"
    "// either. Rebuild with `cd dc-runtime && bun run build`.\n"
)


def load_ownership():
    """Map each sync.toml path (as written there) to its owning repo."""
    if not SYNC_TOML.exists():
        return {}
    with open(SYNC_TOML, "rb") as f:
        cfg = tomllib.load(f)
    owned = {}
    publish = cfg.get("publish")
    if publish:
        for p in publish.get("paths", []):
            owned[p] = publish["owner"]
    for sub in cfg.get("subscribe", {}).values():
        for p in sub.get("paths", []):
            owned.setdefault(p, sub["repo"])
    return owned


def owner_for(rel, owned):
    """rel is a Path relative to ROOT, e.g. site/FAQ.dc.html."""
    rel_s = rel.as_posix()
    if rel_s in owned:
        return owned[rel_s]
    best = None
    for p, owner in owned.items():
        if p.endswith("/") and rel_s.startswith(p):
            if best is None or len(p) > len(best[0]):
                best = (p, owner)
    return best[1] if best else None


def ensure_dc_html_header(path, owner):
    text = path.read_text(encoding="utf-8")
    existing = re.match(
        r"^<!--\s*" + re.escape(path.name) + r"\s*—\s*owned by (vertex-order/[\w.-]+)\."
        r"\s*Edit here\.\s*\n\s*Vendored elsewhere via sync\.toml;"
        r" don't edit the copy there\. -->\n",
        text,
        flags=re.DOTALL,
    )
    header = (
        f"<!-- {path.name} — owned by {existing.group(1) if existing else owner}. Edit here.\n"
        "     Vendored elsewhere via sync.toml; don't edit the copy there. -->\n"
    )
    rest = text[existing.end():] if existing else text
    if existing and text == header + rest:
        return False
    path.write_text(header + rest, encoding="utf-8", newline="\n")
    return True


def ensure_css_header(path, owner):
    text = path.read_text(encoding="utf-8")
    existing = re.match(
        r"^/\*\s*Owned by (vertex-order/[\w.-]+) — edit here\. Vendored elsewhere via"
        r" sync\.toml; don't edit the copy there\. \*/\n",
        text,
    )
    header = (
        f"/* Owned by {existing.group(1) if existing else owner} — edit here. "
        "Vendored elsewhere via sync.toml; don't edit the copy there. */\n"
    )
    rest = text[existing.end():] if existing else text
    if existing and text == header + rest:
        return False
    path.write_text(header + rest, encoding="utf-8", newline="\n")
    return True


def ensure_md_header(path, owner):
    text = path.read_text(encoding="utf-8")
    if re.search(r"^> Owned by vertex-order/[\w.-]+ — edit here\. Vendored elsewhere via sync\.toml;\n"
                 r"> don't edit the copy there\.\n", text, flags=re.MULTILINE):
        return False
    block = (
        f"> Owned by {owner} — edit here. Vendored elsewhere via sync.toml;\n"
        "> don't edit the copy there.\n"
    )
    lines = text.splitlines(keepends=True)
    insert_at = 1
    if insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1
    else:
        lines.insert(insert_at, "\n")
        insert_at += 1
    new_lines = lines[:insert_at] + [block, "\n"] + lines[insert_at:]
    path.write_text("".join(new_lines), encoding="utf-8", newline="\n")
    return True


def ensure_support_js_header(path):
    text = path.read_text(encoding="utf-8")
    if text.startswith(SUPPORT_JS_HEADER):
        return False
    m = re.match(r"(?:^//[^\n]*\n)+", text)
    if m:
        text = text[m.end():]
    path.write_text(SUPPORT_JS_HEADER + text, encoding="utf-8", newline="\n")
    return True


def iter_targets(paths):
    if paths:
        for p in paths:
            path = Path(p)
            if path.is_file():
                yield path.resolve()
    else:
        yield from (p for p in sorted(SITE.rglob("*")) if p.is_file())


def main(paths):
    owned = load_ownership()
    changed = []
    for path in iter_targets(paths):
        rel = path.relative_to(ROOT)
        owner = owner_for(rel, owned)
        if owner is None:
            continue
        if path.name == "support.js":
            did = ensure_support_js_header(path)
        elif path.suffix == ".css":
            did = ensure_css_header(path, owner)
        elif path.suffix == ".md":
            did = ensure_md_header(path, owner)
        elif path.name.endswith(".dc.html"):
            did = ensure_dc_html_header(path, owner)
        else:
            did = False
        if did:
            changed.append(str(rel))
    return changed


if __name__ == "__main__":
    for rel in main(sys.argv[1:]):
        print(f"restored ownership header: {rel}")
