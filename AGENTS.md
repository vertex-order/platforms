<!-- AGENTS.md (markdown) -->

# AGENTS.md

Guidance for AI coding tools working in a **full checkout** of this repo
(Cursor, Windsurf, Claude Code, Aider, …). Human contributors: read
[CONTRIBUTING.md](CONTRIBUTING.md) — it has the task-by-task guide.

> This file is **not** seen by browser-based design tools (Claude Design
> etc.), which pull in only the flat `site/` directory plus
> `.claude/CLAUDE.md`. Instructions for that environment live in
> [`.claude/CLAUDE.md`](.claude/CLAUDE.md) and the header comment of
> [`site/components.js`](site/components.js).

## What this repo is

A staging ground for tuning how platform icons render in the
[Vertex Order](https://vertex-order.github.io) game listings — nothing here
ships to the listings directly. [`site/data/platform-icons.js`](site/data/platform-icons.js)
holds the record (`window.PLATFORM_ICONS`): one entry per platform, each an
`icon` (Bootstrap Icon class), an `iconImg` (path under `images/platforms/`),
or a `text` label, with optional `iconSize` / `imgStyle` / `fontSize` /
`prefix` / `suffix` / `jpTag`. **Those values are page (1×) size — exactly
what `PlatformIcon.dc.html` renders in a listing row.**
[`site/Platforms.dc.html`](site/Platforms.dc.html) renders the list twice
from the same data — a **Zoomed** grid via `ZoomedPlatformIcon.dc.html`
(which passes `scale` 2 to `PlatformIcon`, so it renders itself at 2× via
CSS `zoom`, on ruled guide lines) and a **Page size** grid straight through
the real `PlatformIcon.dc.html` at `scale` 1. Bootstrap glyphs are a fixed
16px in `PlatformIcon` (32px after the 2× zoom).

The entry page is **`Platforms.dc.html`**, not `page.dc.html` — this repo
diverges from the other Vertex Order repos there (see the note in
[`scripts/bundle-components.py`](scripts/bundle-components.py)).

## The one rule that bites

`site/components.js` is a **generated build artifact** — it inlines every
sibling `site/*.dc.html` component (all except the entry page,
`Platforms.dc.html`). If you add, change, or remove any `*.dc.html`,
regenerate it:

```sh
just bundle-components   # or: just build  /  python3 scripts/bundle-components.py
```

The pre-commit hook in `.githooks/` also does this (run `just install-hooks`
once per clone), and CI
([`check-generated.yml`](.github/workflows/check-generated.yml)) fails any PR
where it's out of date. Never hand-edit `components.js`.

`Platforms.dc.html` loads `components.js` **only over `file://`** — it's the
fallback for opening the page straight off disk, where `fetch()` of sibling
`*.dc.html` is blocked. Over http(s) (`just serve`, Pages, any preview) the
runtime fetches each `*.dc.html` live, so a stale bundle never changes what
renders there — it only needs regenerating to keep the committed file
diff-clean and CI green.

## What's editable vs vendored

| Editable | Vendored / generated — don't hand-edit |
| --- | --- |
| `site/data/platform-icons.js` (the platform record) | `site/components.js` (generated) |
| `site/*.dc.html` (page + render components) | `site/support.js` |
| `NOTICE.md` (third-party icon attribution — keep in step with `platform-icons.js`) | |
| `site/_ds/*/styles.css` (design tokens) | `site/_ds/*/_ds_bundle.js`, `_ds_manifest.json` |
| `site/images/platforms/` | `site/_ds/*/_adherence.oxlintrc.json` |

## Build / preview / deploy

- No bundler, no Node for the site. Open `site/Platforms.dc.html` off disk,
  or `just serve` to preview the way CI deploys.
- Push to `main` = deploy (GitHub Actions runs `just build`, publishes
  `build/` to Pages; `build/Platforms.dc.html` is renamed to `index.html`).
- Recipes: see [`justfile`](justfile).

## Platform icon SVGs

- `scripts/normalize-svg.py` canonicalizes serialization to self-closing
  tags — run by the pre-commit hook and `just build`, and
  `check-generated.yml` fails a PR whose SVGs aren't canonical (a second
  gotcha alongside `components.js`). It's a pure string pass, no visual
  change.
- `just trim-svg` is a **separate one-time minify pass**, not part of
  `build`: svgo (`svgo.config.mjs` — editor cruft, unused defs, precision)
  then `scripts/trim-svg.py` (drops path subpaths that lie entirely
  outside the `viewBox` — e.g. wordmarks left behind by a crop). It's the
  only task that needs Node — `winget install OpenJS.NodeJS.LTS` /
  `brew install node` / distro package, then it calls `npx` (fetches svgo
  on first run, no `npm install`). Every icon it changes needs a visual
  re-check in both grids; `trim-svg.py` is pixel-safe by construction but
  bails, per file, on transforms / `<use>` / masks / strokes / rotated
  arcs.
