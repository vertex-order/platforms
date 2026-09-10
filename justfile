# Build the deployable site into build/ (gitignored, matches CI).
build: strip-metadata normalize-svg bundle-components
    rm -rf build
    mkdir build
    cp -r site/. build/
    mv build/Platforms.dc.html build/index.html

# Regenerate site/components.js — inlines sibling *.dc.html so <dc-import>
# resolves without a fetch() (needed for opening the entry page over file://).
bundle-components:
    python3 scripts/bundle-components.py

# Build then serve build/ locally, like the real deploy.
serve: build
    cd build && python -m http.server 8000

clean:
    rm -rf build

# One-time per clone: wire up repo git hooks (pre-commit strips C2PA metadata from
# images and regenerates site/components.js when a sibling component changes).
install-hooks:
    git config core.hooksPath .githooks

# Strip embedded C2PA provenance metadata from all site images (run after a fresh export).
strip-metadata:
    python3 scripts/strip-c2pa.py site/images

# Normalize SVG empty elements to self-closing form (the icons and Claude
# Design's exporter are inconsistent), for a stable check-in.
normalize-svg:
    python3 scripts/normalize-svg.py site/images

# One-time SVG trimming — NOT part of `build`, run by hand. svgo strips
# editor cruft, unused defs, inline styles, and excess precision (see
# svgo.config.mjs). Every changed icon needs a visual re-check in
# Platforms.dc.html (zoomed + page-size rows) before committing.
# Needs Node: `winget install OpenJS.NodeJS.LTS` (or `scoop install nodejs-lts`).
# svgo is npm-only — no winget/scoop package — so npx fetches and caches it.
trim-svg:
    npx --yes svgo@3 --config svgo.config.mjs --recursive --folder site/images/platforms
    python3 scripts/normalize-svg.py site/images/platforms
