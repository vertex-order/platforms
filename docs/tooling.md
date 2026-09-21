<!-- docs/tooling.md (markdown) -->

# Lint/format tooling

Every linter/formatter this repo runs (`ruff`, `prettier`, `stylelint`,
`oxlint`, `@action-validator/cli`, `@taplo/cli`, `ajv-cli`) is a real,
exact-pinned dev dependency -- `pyproject.toml`'s `[dependency-groups].dev`
for `ruff`, `package.json`'s `devDependencies` for the rest. `svgo` is the
one exception, still run ephemerally via `npx` (see "The one ephemeral
tool" below).

## Why real dependencies, not `npx`/`uvx`

These all used to run ephemerally (`npx pkg@version`/`uvx pkg@version`,
never added to a manifest) specifically so a version bump didn't need a
`package.json`/lockfile change. That traded away two things a real
dependency gives you for free:

- **A version pin only Dependabot can see.** `.github/dependabot.yml`
  already watches `package.json`/`package-lock.json` (and now
  `pyproject.toml`/`uv.lock`) with a **7-day cooldown** on every bump --
  the same age-gate `uv.toml`'s `exclude-newer` and `.npmrc`'s
  `min-release-age` exist for, except Dependabot's version gives you a
  reviewable, changelogged PR per bump instead of an ephemeral tool
  silently resolving to a different "latest that's old enough" version
  on a different day. A supply-chain-fresh compromised release still
  can't reach you either way; the difference is whether a bump is a
  commit you can look at or an invisible resolution.
- **One source of truth for the pin**, not three. The ephemeral era
  needed the version pin to agree across the `justfile` recipe,
  `.githooks/pre-commit`, and the matching `.github/workflows/check-*.yml`
  -- now it's just whatever `package-lock.json`/`uv.lock` says, and every
  invocation (`npx <tool>` with no `@version`, `uv run ruff`) resolves to
  that automatically.

The tradeoff moved the other way too: a real dependency needs
`npm install`/`uv sync` to have actually run before the tool exists
locally, so every check below is Node/uv-*optional* the same way
`check-css` already was -- skip gracefully with an install hint if it
hasn't, rather than silently `npx`-fetching a copy just for one run.

## Current dev-dependency tools

| Tool | Covers | Local recipe | CI workflow |
| --- | --- | --- | --- |
| `ruff` (uv, `[dependency-groups].dev`) | `scripts/*.py` lint + format | `just check-ruff` | `check-ruff.yml` |
| `oxlint` (npm) | `scripts/*.js` lint | `just check-oxlint` | `check-oxlint.yml` |
| `prettier` (npm) | `scripts/*.js`, `.github/**/*.yml`, hand-written `*.json`, `*.css` format | `just check-format` | `check-format.yml` |
| `stylelint` (npm) | `site/**/*.css` lint | `just check-css` | `check-css.yml` |
| `@action-validator/cli` + `@action-validator/core` (npm) | `.github/workflows/*.yml` schema validation | `just check-actions` | `check-actions.yml` |
| `@taplo/cli` (npm) | `*.toml` lint + format | `just check-toml` | `check-toml.yml` |
| `ajv-cli` (npm) | `schemas/*.schema.json` meta-validation | `just check-schemas` | `check-schemas.yml` |

`@action-validator/cli` is *not* `actionlint` (the well-known Go tool) --
that npm package (`actionlint`) is wasm-wrapped with no CLI `bin`, so
`npx actionlint` errors outright with "could not determine executable to
run" (confirmed by testing). `@action-validator/cli` is a separate, real
implementation with an actual CLI, validating against the same published
GitHub Actions JSON schemas.

`just format` runs `uv run ruff format` + `npx prettier --write` for a
local auto-fix; not part of `fix`/`build` (those regenerate derived
artifacts -- this rewrites your own source style).

`.prettierignore` excludes `site/data/*.js` and `site/components.js`: the
former is deliberately hand-styled data (single quotes, one entry per
line) prettier would otherwise fight for no benefit, and the latter is a
generated artifact with its own regeneration path
(`scripts/bundle-components.py`), not something to reformat directly.
`stylelint`'s equivalent exclusion (`site/_ds/`, vendored Claude Design
output) lives in `.stylelintrc.cjs` instead, since it predates this file.

Considered and skipped: Biome and oxlint+oxfmt as a prettier/eslint
replacement. Tested directly -- Biome silently ignores `.yml` entirely (no
YAML support at all: pointed at a `.yml` file, it reports "0 files
processed", no error, nothing checked), so it can't replace `prettier`
here without still needing `prettier` (or something else) for workflow
YAML anyway -- more moving parts, not fewer, for this repo's small JS/CSS
surface. `svglint` (a real, separate SVG *linter* -- distinct from `svgo`,
which optimizes/rewrites and has no check-only mode) and `html-validate`
(parses `*.dc.html`'s custom tags/`{{ }}` bindings fine, but its default
ruleset actively conflicts with real conventions here -- flags every
`onClick` as wrong case, flags intentional inline `style=`, doesn't know
`<helmet>` -- and would need real per-project config before it's usable)
were also tested and skipped for now, cost/benefit not clearly worth it
yet.

## The Python side: `pyproject.toml` + `uv.lock`, not `uv.toml`

This repo has exactly one Python dev dependency (`ruff`), declared the
way `uv` actually expects a *dependency* to be declared: a minimal
`pyproject.toml` (`[project]` is a required-but-unused placeholder here --
this isn't a distributable package, just a home for
`[dependency-groups].dev`) plus the `uv.lock` it generates. `.venv/` is
gitignored, same as `node_modules/`.

`uv run ruff ...` (a *project* command) is what every check uses now, not
`uvx ruff@<version> ...` (an *ephemeral* tool-run command) -- `uv run`
auto-syncs `.venv/` from `uv.lock` first, so it always uses the exact
locked version, and -- confirmed by testing, not assumed -- it discovers
`uv.toml`'s `exclude-newer` automatically by walking up from the project
root the same way `uv sync`/`uv add` do. That's a real, useful difference
from `uv tool run` (`uvx`), which never discovers a project `uv.toml` on
its own (see the next section) -- once something is a project dependency
instead of an ephemeral tool run, the awkward `UV_CONFIG_FILE=uv.toml`
workaround this repo used to need goes away entirely.

## `uv.toml`'s `exclude-newer`: still here, now a backstop

`uv.toml` (repo root) still sets `exclude-newer = "7 days"`. For `ruff`
specifically, Dependabot's own cooldown (above) is now the primary
guard -- it won't even *propose* a bump for a version younger than that.
`uv.toml`'s setting stays as a blanket backstop for any other `uv`
resolution this repo ever does (a future `uv add`, an ad-hoc `uv run
--with X`, `uv lock` re-resolving) that wouldn't otherwise be covered by
a manifest-based cooldown.

**This does not apply automatically to `uvx`.** Confirmed by testing, not
assumed: `uv tool run` (`uvx`) never discovers a project-level `uv.toml`
by walking up from the current directory the way `uv sync`/`uv add`/
`uv run` do -- it only reads a user-global config (`~/.config/uv/uv.toml`
on Linux/macOS, `%APPDATA%\uv\uv.toml` on Windows), which is per-machine
and not something CI or another contributor has. If this repo ever
reaches for a truly one-off `uvx`-run tool again (the way `svgo` still
runs via bare `npx`), remember it needs `UV_CONFIG_FILE=uv.toml` set
explicitly every time to pick this up -- `uv run` doesn't have that
problem, which is one more reason project dependencies are the better
default now.

## Skipping vendored content: `scripts/sync.py --unvendored`

Every check above whose target can be entirely vendored (`scripts/*.py`,
`scripts/*.js`, `.github/workflows/*.yml`, `*.toml`, `schemas/*.schema.json`)
filters its file list through `scripts/sync.py --unvendored <paths...>`
first, which prints back only the paths that do *not* match some
`[subscribe.*]` spec in this repo's own `sync.toml`. A file that *is*
vendored is a byte-for-byte copy of something the owning repo's own CI
already checked (guaranteed by `check-vendored.yml`) -- re-running the
same tool against the same bytes here would only ever pass, and CI
minutes are the scarcer resource than local dev time. When the filtered
list comes back empty, the recipe/workflow skips the expensive part
entirely (in CI: everything after an early "is anything left to check"
step, so `setup-uv`/`setup-node`/`npm install`/`uv sync` and the actual
tool run don't run either -- checkout still does, since reading
`sync.toml` needs it).

This is a per-*file* check, not a per-*repo* one (a cruder "is this repo
kit" flag was tried first and replaced) -- `spec_matches()` (already used
by the pre-commit vendored-file guard) handles a directory-style spec
(`"schemas/"` vendors every file under it) as a prefix match, so a
partial subscription like org's `schemas/` -- two files vendored from
kit, two of its own alongside them -- correctly narrows to just the two
real ones instead of skipping (or wrongly running against) the whole
directory. `check-schemas` is the one exception that still compiles the
*full* glob once it decides to run at all: a local schema's `$ref` can
point at a vendored one, so dropping the vendored files from the actual
`ajv-cli` invocation (as opposed to just the skip-or-not decision) would
break resolution rather than skip redundant checking.

`--unvendored` is a plain filter with no other side effects -- safe to
call as many times as a recipe needs (the gate check and the real
invocation each recompute it rather than pass a value between steps,
since the computation itself is fast and local, no network).

## The one ephemeral tool: `svgo`

`svgo` (`just trim-svg`) is the one tool still run via bare `npx svgo@3`
-- deliberately, not an oversight. It's a one-time, run-by-hand SVG
trimming pass, not a CI gate: there's no `check-svgo.yml`, no repeated
"does this still pass" question a stale pin could silently get wrong, and
no real benefit to a manifest entry Dependabot would open a PR against
for a tool nothing else depends on being a specific version. If that ever
changes (e.g. `svgo` becomes a real CI check), move it into this table
the same way the others got moved.
