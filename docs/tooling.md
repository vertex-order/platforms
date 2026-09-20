<!-- docs/tooling.md (markdown) -->

# Ephemeral tools (`npx`/`uvx`)

A few checks in this repo run a real linter/formatter (ruff for Python,
prettier for JS/YAML/JSON/CSS) without adding it as a project dependency
anywhere -- no `requirements.txt`, no `pyproject.toml`, and (for prettier)
no entry in `package.json` either, unlike `stylelint`/`jsdom`/`react`,
which *are* real `package.json` devDependencies because `just build`'s
SSR step and `check-css` need them present as installed packages, not
just runnable once.

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

## Current ephemeral tools

| Tool | Covers | Local recipe | CI workflow |
| --- | --- | --- | --- |
| `ruff` (via `uvx`) | `scripts/*.py` lint + format | `just check-ruff` | `check-ruff.yml` |
| `prettier` (via `npx`) | `scripts/*.js`, `.github/**/*.yml`, hand-written `*.json`, `*.css` | `just check-format` | `check-format.yml` |
| `svgo` (via `npx`) | one-time SVG trimming, not a CI gate | `just trim-svg` | -- |

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

Not covered yet: a YAML *semantic* linter/validator (something like
`actionlint` for the GitHub Actions workflow files specifically, catching
a bad `on:`/`needs:`/expression rather than just a formatting nit) and a
JS linter (`eslint` -- prettier only reformats, it doesn't flag e.g. an
unused variable the way `ruff check` does for Python). Same pattern would
apply if either gets added later.
