<!-- docs/tooling.md (markdown) -->

# Ephemeral tools (`npx`/`uvx`)

A few checks in this repo run a real linter/formatter (ruff for Python,
prettier for JS/YAML/JSON/CSS) without adding it as a project dependency
anywhere -- no `requirements.txt`, no `pyproject.toml`, and (for prettier)
no entry in `package.json` either, unlike `jsdom`/`react`/`react-dom`,
which *are* real `package.json` devDependencies because `scripts/ssr-render.js`
(`just build`'s SSR step) actually `require()`s them at build time -- not
just runnable once, needed present as installed packages.

`stylelint` is a real devDependency too, but not for that reason -- tested
and confirmed it can't cleanly go ephemeral like the others. Its config
(`.stylelintrc.cjs`) uses `extends: "stylelint-config-recommended"`, and
stylelint resolves that via Node's module resolution starting from the
config file's own location, not from wherever `npx` happened to fetch
stylelint to. An `npx -p stylelint -p stylelint-config-recommended stylelint`
invocation installs both packages fine but still fails to resolve the
`extends` -- they land in npx's isolated temp cache dir, which isn't in
this repo's module resolution path. `--config-basedir` can point at that
temp dir explicitly and it does work, but the path is a randomized
npm-cache hash, not something scriptable across machines or CI runs. The
only way around it would be dropping `extends` and inlining
`stylelint-config-recommended`'s ruleset directly into `.stylelintrc.cjs`
-- which trades the dependency for silently drifting out of sync with
that package's own future updates. Not done.

`npx <pkg>@<version>` (Node) and `uvx <pkg>@<version>` (Python, via
[uv](https://docs.astral.sh/uv/)) fetch, cache, and run a tool for one
invocation and discard it -- the `npx svgo@3` in `just trim-svg` is the
existing example this pattern generalizes from. The version is pinned in
the command itself, not in a lockfile; a pin appears in three places that
must agree for a given tool -- the `justfile` recipe, `.githooks/pre-commit`,
and the matching `.github/workflows/check-*.yml` -- since there's no single
manifest file tracking it. Bumping a pin means editing all three.

## The optional-locally, mandatory-in-CI rule

Every check built this way follows the same shape as `check-css`
(stylelint, a real dependency, but same idea): guard on
`command -v npx`/`command -v uvx` locally (in the `justfile` recipe and in
`.githooks/pre-commit`), and skip with an explanatory message if the tool
isn't installed -- a contributor without Node or `uv` on `PATH` never gets
a commit blocked over it. CI never has that guard: every
`.github/workflows/check-*.yml` job installs Node (`actions/setup-node`)
or `uv` (`astral-sh/setup-uv`) unconditionally and always runs the check,
so it's still a hard gate before merge regardless of what any individual
contributor has installed locally.

`uv` isn't preinstalled the way `npx` ships with Node -- install it once
with `curl -LsSf https://astral.sh/uv/install.sh | sh` (or see
https://docs.astral.sh/uv/getting-started/installation/), a single static
binary, no dependencies of its own.

## `uv.toml` and the supply-chain age guard

`uv.toml` (repo root) sets `exclude-newer = "7 days"` -- a supply-chain
guard: uv refuses to resolve to any package version uploaded more
recently than that, so a just-published/compromised release can't get
pulled in the moment it lands. It only constrains which version an
existing pin (e.g. `ruff@0.16`) resolves to within its own range -- it
doesn't replace the pin.

**This does not apply automatically.** Confirmed by testing, not
assumed: `uv tool run` (`uvx`) never discovers a project-level `uv.toml`
by walking up from the current directory the way `uv sync`/`uv add` do --
it only reads a user-global config (`~/.config/uv/uv.toml` on Linux/macOS,
`%APPDATA%\uv\uv.toml` on Windows), which is per-machine and not something
CI or another contributor has. Every `uvx` invocation in this repo must
therefore set `UV_CONFIG_FILE=uv.toml` (or pass `--config-file uv.toml`)
explicitly to pick it up -- already done in `just check-ruff`/`just
format`, `.githooks/pre-commit`, and `check-ruff.yml`'s job-level `env:`.
Adding a new `uvx`-based check later means remembering this the same way
it means remembering the version pin.

## Current ephemeral tools

| Tool | Covers | Local recipe | CI workflow |
| --- | --- | --- | --- |
| `ruff` (via `uvx`) | `scripts/*.py` lint + format | `just check-ruff` | `check-ruff.yml` |
| `oxlint` (via `npx`) | `scripts/*.js` lint | `just check-oxlint` | `check-oxlint.yml` |
| `prettier` (via `npx`) | `scripts/*.js`, `.github/**/*.yml`, hand-written `*.json`, `*.css` format | `just check-format` | `check-format.yml` |
| `@action-validator/cli` (via `npx`) | `.github/workflows/*.yml` schema validation | `just check-actions` | `check-actions.yml` |
| `@taplo/cli` (via `npx`) | `*.toml` lint + format | `just check-toml` | `check-toml.yml` |
| `ajv-cli` (via `npx`) | `schemas/*.schema.json` meta-validation | `just check-schemas` | `check-schemas.yml` |
| `svgo` (via `npx`) | one-time SVG trimming, not a CI gate | `just trim-svg` | -- |

`@action-validator/cli` is *not* `actionlint` (the well-known Go tool) --
that npm package (`actionlint`) is wasm-wrapped with no CLI `bin`, so
`npx actionlint` errors outright with "could not determine executable to
run" (confirmed by testing). `@action-validator/cli` is a separate, real
implementation with an actual CLI, validating against the same published
GitHub Actions JSON schemas.

`just format` runs `ruff format` + `prettier --write` for a local
auto-fix; same tool-optional guards, not part of `fix`/`build` (those
regenerate derived artifacts -- this rewrites your own source style).

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
step, so `setup-uv`/`setup-node` and the actual `npx`/`uvx` download don't
run either -- checkout still does, since reading `sync.toml` needs it).

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
