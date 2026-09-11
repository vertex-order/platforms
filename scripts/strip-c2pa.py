#!/usr/bin/env python3
# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
"""Strip embedded C2PA content-credential metadata from image assets.

Claude Design exports (and similar tools) embed a C2PA provenance
manifest in PNG/SVG files, bloating them and disclosing AI authorship.
This has no functional purpose on committed site assets, so it's run
both by the pre-commit hook (.githooks/pre-commit) and on demand via
`just strip-metadata`.

No external tools required (no exiftool/svgo): SVG stripping is a
targeted regex on the known <metadata>/xmlns:c2pa shape; PNG stripping
is a chunk allowlist so unrelated ancillary chunks (pHYs, gAMA, sRGB,
iCCP, ...) are preserved rather than nuked wholesale.
"""
import re
import struct
import sys
from pathlib import Path

# PNG chunk type C2PA embeds its JUMBF manifest container in. Only this
# is dropped -- anything else (pHYs, sBIT, a pre-existing tEXt from
# whatever tool originally authored the icon, ...) is left alone, since
# it may be legitimate metadata unrelated to C2PA.
PNG_C2PA_CHUNKS = {"caBX"}


def strip_svg(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    stripped = re.sub(r'\s*xmlns:c2pa="[^"]*"', "", content)
    stripped = re.sub(r"<metadata\b[^>]*>.*?</metadata>", "", stripped, flags=re.S)
    if stripped != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(stripped)
        return True
    return False


def strip_png(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return False

    out = [data[:8]]
    i = 8
    changed = False
    while i < len(data):
        length = struct.unpack(">I", data[i:i + 4])[0]
        ctype = data[i + 4:i + 8].decode("latin1")
        chunk_end = i + 8 + length + 4
        if ctype in PNG_C2PA_CHUNKS:
            changed = True
        else:
            out.append(data[i:chunk_end])
        i = chunk_end

    if changed:
        with open(path, "wb") as f:
            f.write(b"".join(out))
    return changed


def iter_files(paths):
    """Expand directory args into their .png/.svg files (shell-glob-free,
    so this works the same whether `just` runs it under bash or cmd)."""
    for path in paths:
        p = Path(path)
        if p.is_dir():
            yield from sorted(p.rglob("*.png"))
            yield from sorted(p.rglob("*.svg"))
        else:
            yield p


def main(paths):
    changed = []
    for path in iter_files(paths):
        path = str(path)
        lower = path.lower()
        if lower.endswith(".svg") and strip_svg(path):
            changed.append(path)
        elif lower.endswith(".png") and strip_png(path):
            changed.append(path)
    return changed


if __name__ == "__main__":
    changed = main(sys.argv[1:])
    for path in changed:
        print(f"stripped C2PA metadata: {path}")
