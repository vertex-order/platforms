# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
#
# One justfile for every Vertex Order repo — kit included. The only thing
# that could differ per repo is the entry-page rename in `build`, and the
# `mv ... || true` makes that a no-op rather than a fork: kit has no entry
# page, platforms and every list have `page.dc.html`.

# Assemble the deployable site into build/ (gitignored, matches CI).
#
# The last step prerenders the entry page's initial content so it paints
# real markup before support.js boots, instead of today's blank shell — see
# scripts/ssr-render.js's header comment for how. It needs Node; CI (which
# does the real deploy, static.yml) always has it, so this always runs
# there. Locally, a contributor without Node still gets a working `just
# build`/`just serve` — just without the prerender, same blank-then-hydrate
# behavior as before this feature. A Node-present failure here is a real
# bug and fails the build, same as any other step.
build: strip-metadata normalize-svg restore-headers ensure-helmets bundle-components
    rm -rf build
    mkdir build
    cp -r site/. build/
    mv build/page.dc.html build/index.html 2>/dev/null || true
    if command -v node >/dev/null 2>&1; then \
        if [ -f build/index.html ]; then npm install --no-fund --no-audit --silent && node scripts/ssr-render.js build; fi; \
    else \
        echo "just build: node not on PATH — skipping SSR prerender (build/index.html ships blank-then-hydrate)"; \
    fi

# Build then serve build/ locally, like the real deploy.
serve: build
    cd build && python -m http.server 8000

# Regenerate site/components.js — inlines every *.dc.html so <dc-import>
# resolves without a fetch() (needed for opening a page over file://).
bundle-components:
    python3 scripts/bundle-components.py

# Get the latest: repin every sync.toml [subscribe.*] to its source's
# current main, then pull it. "Sync" always means this.
sync:
    python3 scripts/sync.py --update-all --from-ref main

# CI check: fail if any vendored file drifted from its currently pinned ref.
sync-check:
    python3 scripts/sync.py --check

# Reapply the currently pinned ref's content without moving the pin. Rare:
# undoes a hand-edit to a vendored file.
sync-restore:
    python3 scripts/sync.py

# CI check: fail if cross-listed duplicate game entries in site/data/ have drifted.
check-dedup-drift:
    python3 scripts/check-dedup-drift.py

clean:
    rm -rf build

# One-time per clone: wire up repo git hooks (pre-commit restores ownership
# headers and design-system helmets, strips C2PA metadata from images, and
# regenerates site/components.js when a component changes).
install-hooks:
    git config core.hooksPath .githooks

# Strip embedded C2PA provenance metadata from all site images (run after a fresh export).
strip-metadata:
    python3 scripts/strip-c2pa.py site/images

# Normalize SVG empty elements to self-closing form (the icons and Claude
# Design's exporter are inconsistent), for a stable check-in.
normalize-svg:
    python3 scripts/normalize-svg.py site/images

# Restore the "owned by vertex-order/X" header comment on any site/ file a
# Claude Design export stripped it from (sync.toml says who owns what).
restore-headers:
    python3 scripts/restore-headers.py

# Add the Nocturne design-system <helmet> to any component missing one, so
# every component previews standalone and a design-tool export's own
# addition of it is never a surprise diff.
ensure-helmets:
    python3 scripts/ensure-helmets.py

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
