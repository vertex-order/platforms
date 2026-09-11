# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
#
# One justfile for every Vertex Order repo — kit included. The only thing
# that could differ per repo is the entry-page rename in `build`, and the
# `mv ... || true` makes that a no-op rather than a fork: kit has no entry
# page, platforms and every list have `page.dc.html`.

# Assemble the deployable site into build/ (gitignored, matches CI).
build: strip-metadata normalize-svg bundle-components
    rm -rf build
    mkdir build
    cp -r site/. build/
    mv build/page.dc.html build/index.html 2>/dev/null || true

# Build then serve build/ locally, like the real deploy.
serve: build
    cd build && python -m http.server 8000

# Regenerate site/components.js — inlines every *.dc.html so <dc-import>
# resolves without a fetch() (needed for opening a page over file://).
bundle-components:
    python3 scripts/bundle-components.py

# Pull vendored files from the repos in sync.toml [subscribe.*].
sync:
    python3 scripts/sync.py

# CI check: fail if any vendored file drifted from its source.
sync-check:
    python3 scripts/sync.py --check

# Repin a subscription's ref to its current HEAD sha, then pull it.
sync-update name:
    python3 scripts/sync.py --update {{name}}

clean:
    rm -rf build

# One-time per clone: wire up repo git hooks (pre-commit strips C2PA metadata
# from images and regenerates site/components.js when a component changes).
install-hooks:
    git config core.hooksPath .githooks

# Strip embedded C2PA provenance metadata from all site images (run after a fresh export).
strip-metadata:
    python3 scripts/strip-c2pa.py site/images

# Normalize SVG empty elements to self-closing form (the icons and Claude
# Design's exporter are inconsistent), for a stable check-in.
normalize-svg:
    python3 scripts/normalize-svg.py site/images

# One-time SVG trimming — NOT part of `build`, run by hand. Two passes:
#   1. svgo — editor cruft, unused defs, inline styles, excess precision
#      (see svgo.config.mjs). Can change rendering; re-check every icon.
#   2. trim-svg.py — drops path subpaths that lie fully outside the viewBox
#      (crops that still carry offscreen artwork). Pixel-safe by
#      construction, bails on anything it can't prove.
# Then normalize-svg.py restores the canonical self-closing form.
# Every changed icon still needs a visual re-check wherever it renders.
# Needs Node — the only task that does: `winget install OpenJS.NodeJS.LTS`
# / `scoop install nodejs-lts` (Windows), `brew install node` (macOS).
# svgo is npm-only — no winget/scoop package — so npx fetches and caches it.
trim-svg:
    npx --yes svgo@3 --config svgo.config.mjs --recursive --folder site/images
    python3 scripts/trim-svg.py site/images
    python3 scripts/normalize-svg.py site/images
