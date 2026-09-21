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
check: check-py check-ruff check-js check-oxlint check-format check-css check-toml check-actions check-schemas check-dedup-drift check-data sync-check

# CI check: fail if cross-listed duplicate game entries in site/data/ have drifted.
check-dedup-drift:
    python3 scripts/check-dedup-drift.py

# CI check: fail if any site/data/*.js doesn't match the schema it declares
# with its own `// schema: <name>.schema.json` comment -- see
# scripts/validate-data.py. Pure Python, no external deps -- unlike
# check-css/check-js, always runs, even without Node.
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

# CI check: fail if any scripts/*.js or site/data/*.js has a syntax error.
# Syntax-only (node --check parses without executing) -- site/data/*.js
# isn't valid JSON (single-quoted strings, unquoted keys, comments), but
# it IS valid JS, so node --check reads it fine even though a JSON parser
# can't; this is a cheap syntax gate ahead of scripts/js_literal.py's own
# parser, which does the real value-extraction work for
# validate-data.py/check-dedup-drift.py. Node-optional locally, same shape
# as check-css -- see .github/workflows/check-syntax.yml.
check-js:
    if command -v node >/dev/null 2>&1; then \
        for f in scripts/*.js site/data/*.js; do node --check "$f" || exit 1; done; \
    else \
        echo "just check-js: node not on PATH — skipped syntax check. Install Node (https://nodejs.org, or see .node-version) to get it locally; CI always runs it."; \
    fi

# CI check: lint + format-check scripts/*.py with ruff, run via `uvx` --
# not a project dependency (no requirements.txt/pyproject.toml added just
# for this; see docs/tooling.md). UV_CONFIG_FILE points uvx at uv.toml's
# exclude-newer -- uvx never discovers a project uv.toml on its own, so
# this must be set explicitly every time. uvx-optional locally, same shape
# as check-css: a contributor without uv just skips it. CI always has uv,
# so it always runs there -- see .github/workflows/check-ruff.yml.
#
# Only checks scripts/*.py this repo actually owns (scripts/sync.py
# --unvendored) -- a file matching some [subscribe.*] spec is a vendored
# byte-for-byte copy the owning repo's own CI already checked, so
# re-running it here would only ever pass. In kit itself, --unvendored is
# a no-op (nothing there is vendored from kit), so this still runs for
# real. Empty result -> skip entirely, no npx/uvx cost paid.
check-ruff:
    files=$(python3 scripts/sync.py --unvendored scripts/*.py); \
    if [ -z "$files" ]; then \
        echo "just check-ruff: scripts/*.py is all vendored here, already checked upstream — skipping."; \
    elif command -v uvx >/dev/null 2>&1; then \
        export UV_CONFIG_FILE=uv.toml; uvx ruff@0.16 check $files && uvx ruff@0.16 format --check $files; \
    else \
        echo "just check-ruff: uvx not on PATH — skipped ruff lint/format check. Install uv (https://docs.astral.sh/uv/, e.g. 'curl -LsSf https://astral.sh/uv/install.sh | sh') to get it locally; CI always runs it."; \
    fi

# CI check: format-check scripts/*.js, .github/**/*.yml, hand-written
# *.json, and *.css with prettier, run via `npx` -- not a project
# dependency, same reasoning as check-ruff. See .prettierignore for what's
# excluded and why (mainly site/data/*.js and site/components.js, which
# have their own deliberate/generated shape prettier would otherwise
# fight). npx-optional locally, same shape as check-css. CI always has
# Node, so it always runs there -- see .github/workflows/check-format.yml.
check-format:
    if command -v npx >/dev/null 2>&1; then \
        npx --yes prettier@3 --check "scripts/*.js" ".github/**/*.yml" "**/*.json" "site/**/*.css"; \
    else \
        echo "just check-format: npx not on PATH — skipped prettier format check. Install Node (https://nodejs.org, or see .node-version) to get it locally; CI always runs it."; \
    fi

# CI check: lint scripts/*.js with oxlint, run via `npx` -- not a project
# dependency, same reasoning as check-format. Catches real mistakes
# prettier's pure formatting can't (e.g. an unsafe `finally` block).
# npx-optional locally, same shape as check-css. CI always has Node, so it
# always runs there -- see .github/workflows/check-oxlint.yml.
#
# Only lints scripts/*.js this repo actually owns -- see check-ruff's
# comment, same scripts/sync.py --unvendored mechanism.
check-oxlint:
    files=$(python3 scripts/sync.py --unvendored scripts/*.js); \
    if [ -z "$files" ]; then \
        echo "just check-oxlint: scripts/*.js is all vendored here, already checked upstream — skipping."; \
    elif command -v npx >/dev/null 2>&1; then \
        npx --yes oxlint@1.82.0 $files; \
    else \
        echo "just check-oxlint: npx not on PATH — skipped oxlint. Install Node (https://nodejs.org, or see .node-version) to get it locally; CI always runs it."; \
    fi

# CI check: validate GitHub Actions workflow YAML against the real
# published schemas, run via `npx` -- not a project dependency. Not
# `actionlint` itself (the well-known Go tool) -- that npm package is
# wasm-wrapped with no CLI bin, so `npx actionlint` errors outright;
# @action-validator/cli is a separate, real implementation that does have
# one. Scoped to .github/workflows/*.yml only -- dependabot.yml and
# ISSUE_TEMPLATE/*.yml aren't workflow-shaped and this tool has no other
# mode, so it just fails them if pointed there. npx-optional locally, same
# shape as check-css. CI always has Node, so it always runs there -- see
# .github/workflows/check-actions.yml.
#
# Only validates .github/workflows/*.yml this repo actually owns -- see
# check-ruff's comment, same scripts/sync.py --unvendored mechanism.
check-actions:
    files=$(python3 scripts/sync.py --unvendored .github/workflows/*.yml); \
    if [ -z "$files" ]; then \
        echo "just check-actions: .github/workflows/*.yml is all vendored here, already checked upstream — skipping."; \
    elif command -v npx >/dev/null 2>&1; then \
        for f in $files; do \
            npx --yes -p @action-validator/core@0.6.0 -p @action-validator/cli@0.6.0 action-validator "$f" || exit 1; \
        done; \
    else \
        echo "just check-actions: npx not on PATH — skipped workflow validation. Install Node (https://nodejs.org, or see .node-version) to get it locally; CI always runs it."; \
    fi

# CI check: lint + format-check every *.toml with taplo, run via `npx` --
# not a project dependency. Piped through stdin (`taplo lint -`), not
# passed as a file argument or glob -- npx's fetched taplo silently finds
# 0 files when given a path directly on this setup (untracked upstream
# quirk, not worth chasing further since stdin works reliably). One
# process per file rather than one combined invocation for the same
# reason. npx-optional locally, same shape as check-css. CI always has
# Node, so it always runs there -- see .github/workflows/check-toml.yml.
#
# Only lints/format-checks *.toml this repo actually owns -- see
# check-ruff's comment, same scripts/sync.py --unvendored mechanism.
# sync.toml itself never matches (every repo's own [subscribe.kit] shape
# genuinely differs); sync.list.toml/uv.toml, where present, do.
check-toml:
    files=$(python3 scripts/sync.py --unvendored *.toml); \
    if [ -z "$files" ]; then \
        echo "just check-toml: *.toml is all vendored here, already checked upstream — skipping."; \
    elif command -v npx >/dev/null 2>&1; then \
        for f in $files; do \
            cat "$f" | npx --yes @taplo/cli@0.7.0 lint - || exit 1; \
            cat "$f" | npx --yes @taplo/cli@0.7.0 fmt --check - || exit 1; \
        done; \
    else \
        echo "just check-toml: npx not on PATH — skipped taplo lint/format check. Install Node (https://nodejs.org, or see .node-version) to get it locally; CI always runs it."; \
    fi

# CI check: validate every schemas/*.schema.json is well-formed JSON
# Schema (2020-12), run via `npx` -- not a project dependency. An
# independent cross-check scripts/validate-data.py's own hand-rolled
# validator can't give itself (it has no concept of "this schema file
# itself is malformed" -- e.g. a typo'd "propertie" instead of
# "properties" silently no-ops there but is a real error here).
# --strict=false only silences ajv's advisory nag about this repo's two
# union-type fields (title_italic/subtitle_italic accepting string|bool),
# not a real error. npx-optional locally, same shape as check-css. CI
# always has Node, so it always runs there -- see
# .github/workflows/check-schemas.yml.
#
# Skipped entirely if schemas/*.schema.json is all vendored (scripts/sync.py
# --unvendored, same mechanism as check-ruff) -- e.g. a full list repo,
# where the whole schemas/ dir is one [subscribe.kit] entry. Where it isn't
# (e.g. org: two local schemas alongside two vendored ones) this still
# compiles the *full* glob, not just the unvendored files -- a local
# schema's $ref can point at a vendored one (common.schema.json), so
# dropping the vendored files here would break resolution rather than
# just skip redundant checking of them.
check-schemas:
    files=$(python3 scripts/sync.py --unvendored schemas/*.schema.json 2>/dev/null); \
    if [ -z "$files" ]; then \
        echo "just check-schemas: schemas/*.schema.json is all vendored here, already checked upstream — skipping."; \
    elif command -v npx >/dev/null 2>&1; then \
        npx --yes ajv-cli@5.0.0 compile -s "schemas/*.schema.json" --spec=draft2020 --strict=false; \
    else \
        echo "just check-schemas: npx not on PATH — skipped ajv schema check. Install Node (https://nodejs.org, or see .node-version) to get it locally; CI always runs it."; \
    fi

# Auto-fix formatting: ruff format (scripts/*.py) + prettier --write
# (scripts/*.js, .github/**/*.yml, *.json, *.css). Not part of `fix`/
# `build` -- those regenerate derived artifacts; this rewrites your own
# source style, so it's run by hand. Same tool-optional guards as
# check-ruff/check-format.
format:
    if command -v uvx >/dev/null 2>&1; then \
        UV_CONFIG_FILE=uv.toml uvx ruff@0.16 format scripts/; \
    else \
        echo "just format: uvx not on PATH — skipped ruff format."; \
    fi
    if command -v npx >/dev/null 2>&1; then \
        npx --yes prettier@3 --write "scripts/*.js" ".github/**/*.yml" "**/*.json" "site/**/*.css"; \
    else \
        echo "just format: npx not on PATH — skipped prettier --write."; \
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
