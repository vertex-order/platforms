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
ships to the listings directly. [`site/data/platform-legend.js`](site/data/platform-legend.js)
holds the legend (`window.PLATFORM_LEGEND`): one entry per platform, each an
`icon` (Bootstrap Icon class), an `iconImg` (path under `images/platforms/`),
or a `text` label, with optional `iconSize` / `imgStyle` / `fontSize` /
`prefix` / `suffix` / `jpTag`. **Those values are the zoomed (~2×) sizes.**
[`site/Platforms.dc.html`](site/Platforms.dc.html) renders the list twice —
a **Zoomed** grid straight from the legend (via
`ZoomedPlatformIcon.dc.html`, on ruled guide lines) and a **Page size** grid
through the real `PlatformIcon.dc.html`, fed the legend with `iconSize` and
every `Npx` in `imgStyle` halved (`toPageSize()` in that file). Bootstrap
glyphs are fixed by the components: 32px zoomed, 16px page size.

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
| `site/data/platform-legend.js` (the legend) | `site/components.js` (generated) |
| `site/*.dc.html` (page + render components) | `site/support.js` |
| `NOTICE.md` (third-party icon attribution — keep in step with the legend) | |
| `site/_ds/*/styles.css` (design tokens) | `site/_ds/*/_ds_bundle.js`, `_ds_manifest.json` |
| `site/images/platforms/` | `site/_ds/*/_adherence.oxlintrc.json` |

## Build / preview / deploy

- No bundler, no Node. Open `site/Platforms.dc.html` off disk, or
  `just serve` to preview the way CI deploys.
- Push to `main` = deploy (GitHub Actions runs `just build`, publishes
  `build/` to Pages; `build/Platforms.dc.html` is renamed to `index.html`).
- Recipes: see [`justfile`](justfile).
