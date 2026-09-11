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
[`site/page.dc.html`](site/page.dc.html) renders the list twice
from the same data — a **Zoomed** grid via `ZoomedPlatformIcon.dc.html`
(which passes `scale` 2 to `PlatformIcon`, so it renders itself at 2× via
CSS `zoom`, on ruled guide lines) and a **Page size** grid straight through
the real `PlatformIcon.dc.html` at `scale` 1. Bootstrap glyphs are a fixed
16px in `PlatformIcon` (32px after the 2× zoom).

The entry page here is **`page.dc.html`**, same as every other Vertex Order
repo — `bundle-components.py` (vendored from kit) detects it by content (any
`*.dc.html` that references `components.js`), not by name, so nothing here
is repo-specific.

## The one rule that bites

`site/components.js` is a **generated build artifact** — it inlines every
sibling `site/*.dc.html` component (all except the entry page,
`page.dc.html`). If you add, change, or remove any `*.dc.html`,
regenerate it:

```sh
just bundle-components   # or: just build  /  python3 scripts/bundle-components.py
```

The pre-commit hook in `.githooks/` also does this (run `just install-hooks`
once per clone), and CI
([`check-generated.yml`](.github/workflows/check-generated.yml)) fails any PR
where it's out of date. Never hand-edit `components.js`.

`page.dc.html` loads `components.js` **only over `file://`** — it's the
fallback for opening the page straight off disk, where `fetch()` of sibling
`*.dc.html` is blocked. Over http(s) (`just serve`, Pages, any preview) the
runtime fetches each `*.dc.html` live, so a stale bundle never changes what
renders there — it only needs regenerating to keep the committed file
diff-clean and CI green.

## What's editable vs vendored

| Editable (owned here) | Vendored from kit — don't hand-edit |
| --- | --- |
| `site/data/platform-icons.js` (the platform record) | `site/components.js` (generated — `just bundle-components`) |
| `site/PlatformIcon.dc.html`, `ZoomedPlatformIcon.dc.html`, `page.dc.html` | `site/support.js`, `site/_ds/`, `site/images/ui/` |
| `site/images/platforms/`, `NOTICE.md` | `site/BackToTop.dc.html`, `site/HelpWanted.dc.html` |
| | every `scripts/*.py`, `svgo.config.mjs`, `justfile` |
| | `.editorconfig`, `.gitattributes`, `.claude/settings.json`, `CODE_OF_CONDUCT.md` |
| | `.githooks/pre-commit`, most of `.github/` (see `sync.toml`) |

## Cross-repo sync

This repo and [`vertex-order/kit`](https://github.com/vertex-order/kit) each
**own** some files and **vendor** others from the other — a deliberate
two-way pull, but a lopsided one: kit owns essentially all shared tooling
(scripts, CI, editor/git config) so any repo that pulls kit gets the whole
toolkit in one go — a Claude Design re-export that touches hundreds of files
with incidental metadata changes cleans up with a single `just build`
regardless of which repo it landed in. [`sync.toml`](sync.toml) is the
manifest:

- `[publish]` — the platform-icon micro-kit only: `PlatformIcon.dc.html`,
  `platform-icons.js`, `images/platforms/`. kit pulls it; the list repos
  get it transitively via kit.
- `[subscribe.kit]` — everything else: the DC runtime, Nocturne (`_ds/`),
  the generic components, every script (`bundle-components.py`, `sync.py`,
  and the SVG tooling — `normalize-svg.py`, `strip-c2pa.py`, `trim-svg.py`,
  `svgo.config.mjs`), `justfile`, and the CI/editor config with no
  legitimate reason to differ per repo.

Not vendored, even though this repo needs its own: `.github/ISSUE_TEMPLATE/*`
and `.github/PULL_REQUEST_TEMPLATE.md` — each necessarily carries this
repo's own Discussions URL (and PR-checklist lines specific to the icon
grids), so a byte-identical vendor is impossible by construction. Seeded
from kit's copies once, then maintained locally.

`just sync` pulls the subscribed files at the pinned `ref`. `just sync-check`
(and `.github/workflows/check-vendored.yml` on every PR) fails if a vendored
file has drifted. `just sync-update kit` repins to kit's current HEAD.

**Never edit a vendored file here** — change it in kit, then `just sync-update kit`.
Three guards back that up:

1. **A header comment**, where the file format allows one — `Owned by
   vertex-order/kit — edit here. Vendored elsewhere via sync.toml; don't edit
   the copy there.` (Not on `*.svg` or JSON — no room without breaking the
   icon-minification policy or the format.)
2. **Pre-commit guard** — `sync.py --check-staged` (wired into
   `.githooks/pre-commit`) refuses to commit a staged vendored file that no
   longer matches its source. A real sync commit always matches, so it always
   passes; a hand edit doesn't.
3. **CI** — `check-vendored.yml` runs the same check on every PR and on push
   to `main`, catching anything committed without the hook (`--no-verify`,
   web UI, a design-tool sync).

**A change spanning both repos** (e.g. a new `PlatformIcon` prop that needs a
Nocturne token): land the kit-side piece first → `just sync-update kit` here →
land the `PlatformIcon` change here → in kit, `just sync-update platforms`.

Design tool (no shell): `sync.py` can't run; the vendored files are just the
last-synced committed copies — same story as `components.js`. The header
comment is the one guard still visible there.

## Build / preview / deploy

- No bundler, no Node for the site. Open `site/page.dc.html` off disk,
  or `just serve` to preview the way CI deploys.
- Push to `main` = deploy (GitHub Actions runs `just build`, publishes
  `build/` to Pages; `build/page.dc.html` is renamed to `index.html`).
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
