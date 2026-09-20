# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
#
# One justfile for every Vertex Order repo — kit included. The only thing
# that could differ per repo is the entry-page rename in `build`, and the
# `mv ... || true` makes that a no-op rather than a fork: kit has no entry
# page, platforms and every list have `page.dc.html`.

# Regenerate every checked-in generated/normalized file (no build/ assembly)
# — what CI's fix-build.yml runs against a PR branch, and what `build`
# depends on. Kept as its own recipe so both call one source of truth
# instead of listing the same five recipes in two places.
fix: strip-metadata normalize-svg restore-headers ensure-helmets bundle-components

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
build: fix
    rm -rf build
    mkdir build
    cp -r site/. build/
    mv build/page.dc.html build/index.html 2>/dev/null || true
    if command -v node >/dev/null 2>&1; then \
        if [ -f build/index.html ]; then npm install --no-fund --no-audit --silent && node scripts/ssr-render.js build; fi; \
        if [ -f build/index.html ] && [ -f tests/site/verify-ssr.js ]; then node tests/site/verify-ssr.js build; fi; \
    else \
        echo "just build: node not on PATH — skipped SSR prerender (build/index.html ships blank-then-hydrate). Install Node (https://nodejs.org, or see .node-version) to get it locally."; \
    fi

# Build then serve build/ locally, like the real deploy.
serve: build
    cd build && python -m http.server 8000

# Fast, no-build regression checks for kit-owned design tokens and their
# var() fallback consistency — see docs/testing.md. tests/site/ isn't
# vendored (not in sync.toml [publish]), so this recipe only does anything
# in kit itself; elsewhere it's an inert entry pulled in with the rest of
# this shared justfile.
check-tokens:
    node tests/site/check-token-snapshot.js
    node tests/site/check-var-fallbacks.js

# Kit's full test suite: the fast checks above, plus `build`, which itself
# runs tests/site/verify-ssr.js against the real build output when present.
test: check-tokens build

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

# Every fast validation check in one command -- what a PR needs to pass
# before merge, minus the two that don't fit a single local recipe:
# check-tokens (kit-only -- reads tests/site/, which isn't vendored, so it
# errors elsewhere instead of being inert like everywhere else in this
# file; see `test`) and check-generated (components.js/SVG staleness --
# `just build` already regenerates both, so there's no separate check for
# it to fail locally). CI still runs each of the recipes below as its own
# parallel job (for a clear per-check pass/fail in the PR UI, and so one
# failure doesn't block reporting the others) -- this is for a local
# all-in-one before you push.
check: check-py check-js check-css check-dedup-drift check-data sync-check

# CI check: fail if cross-listed duplicate game entries in site/data/ have drifted.
check-dedup-drift:
    python3 scripts/check-dedup-drift.py

# CI check: fail if any site/data/*.js doesn't match its schemas/*.schema.json
# (only checks a pair when both sides exist -- see scripts/validate-data.py).
# Pure Python, no external deps -- unlike check-css/check-js, always runs,
# even without Node.
check-data:
    python3 scripts/validate-data.py

# CI check: lint every CSS file with stylelint (see .stylelintrc.cjs) --
# mainly to catch CSS that fails to parse at all, e.g. a comment that closes
# earlier than intended (a literal */ inside /* ... */). Scans the whole
# site/ tree (minus vendored site/_ds/), so it also covers each repo's own
# un-vendored site/data/theme.css, not just kit's own CSS.
#
# Node-optional locally, same shape as `build`'s SSR step: a contributor
# without Node (or without having run `npm install`) just skips it, same
# as before this check existed. CI always has Node, so it always runs
# there -- see .github/workflows/check-css.yml.
check-css:
    if command -v node >/dev/null 2>&1; then \
        npm install --no-fund --no-audit --silent && npx stylelint "site/**/*.css"; \
    else \
        echo "just check-css: node not on PATH — skipped stylelint CSS check. Install Node (https://nodejs.org, or see .node-version) to get it locally; CI always runs it."; \
    fi

# CI check: fail if any scripts/*.py has a syntax error. Syntax-only (does
# not import or run the file) -- stdlib py_compile, no external tools.
check-py:
    python3 -m py_compile scripts/*.py

# CI check: fail if any scripts/*.js has a syntax error. Syntax-only (node
# --check parses without executing). Node-optional locally, same shape as
# check-css -- see .github/workflows/check-syntax.yml.
check-js:
    if command -v node >/dev/null 2>&1; then \
        for f in scripts/*.js; do node --check "$f" || exit 1; done; \
    else \
        echo "just check-js: node not on PATH — skipped syntax check. Install Node (https://nodejs.org, or see .node-version) to get it locally; CI always runs it."; \
    fi

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
