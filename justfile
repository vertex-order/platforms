# Build the deployable site into build/ (gitignored, matches CI).
build: strip-metadata bundle-components
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
