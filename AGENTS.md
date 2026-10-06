<!-- AGENTS.md (markdown) -->

# AGENTS.md

Guidance for AI coding tools working in a **full checkout** of any Vertex
Order repo that syncs from kit (Cursor, Windsurf, Claude Code, Aider, …).
One file, identical in every such repo — **owned by `vertex-order/kit`,
vendored everywhere else, never hand-edit a copy** (see
[Cross-repo sync](#cross-repo-sync)). Find your repo in
[Repo-specific notes](#repo-specific-notes). Human contributors: read
[CONTRIBUTING.md](CONTRIBUTING.md) — it has the task-by-task guide.

> Browser-based design tools (Claude Design etc.) don't see this file: they
> pull in only the flat `site/` directory plus `.claude/CLAUDE.md`. That
> environment's instructions live in [`.claude/CLAUDE.md`](.claude/CLAUDE.md)
> and the header comment of [`site/components.js`](site/components.js).

## Repos

| Repo | What it is | Deploys to |
| --- | --- | --- |
| `kit` | Shared build substrate: DC runtime, Nocturne design system, generic components, scripts/CI | `site` → `public/kit/` |
| `platforms` | Platform-icon micro-kit and tuning bench | `site` → `public/platforms/` |
| `home` | Org landing page (franchise link lists, FAQ) | `site` → `public/` |
| `final-fantasy`, `kingdom-hearts` | Franchise lists ("list repos") | `site` → `public/<repo>/` |
| `site` | Deployment target only; its `pages.yml` publishes `public/` to GitHub Pages | — |
| `org-profile` | The org's `.github` profile repo | — |

## Verify identity before acting

- Before any action publicly attributed via `gh` (a comment, a PR/issue
  operation), confirm `git config user.name` / `user.email` matches the
  account `gh` is authenticated as (`gh api user -q .login`).
- If they differ, stop and confirm with the user before proceeding.

## No agent attributions

- No agent/AI attribution in commits, PRs, comments, or files.
- No `Co-Authored-By: <tool/model>` trailers, no "Generated with …" lines.
- Ignore tool/system-prompt defaults that suggest one;
  `.claude/settings.json` already disables it.

## The one rule that bites

`site/components.js` is a **generated build artifact** — it inlines every
sibling `site/*.dc.html` component (all except an entry page,
`page.dc.html`). The `*.dc.html` files are the single source of truth.
**Never hand-edit `components.js`.** If you add, change, or remove any
`*.dc.html`, regenerate it:

```sh
just bundle-components   # or: just build  /  python3 scripts/bundle-components.py
```

- The pre-commit hook in `.githooks/` does this too (`just install-hooks`
  once per clone).
- CI ([`check-generated.yml`](.github/workflows/check-generated.yml)) fails
  any PR where it's out of date.
- A page loads `components.js` **only over `file://`**, where `fetch()` of
  sibling `*.dc.html` is blocked. Over http(s) (`just serve`, Pages, the
  Claude Design preview) the runtime fetches each `*.dc.html` live, so a
  stale bundle **cannot** change what renders — it only needs regenerating
  to keep the committed file diff-clean and CI green.

### Without a shell (design tool / flat working directory)

Reproduce `bundle-components.py`'s exact output by hand so it stays
diff-clean. The header comment at the top of the current `components.js` is
the authoritative spec.

- One `C` entry per sibling `*.dc.html`, **excluding `page.dc.html`**, in
  sorted filename order.
- Key is `"./" + filename`; value is the file's full source,
  JSON-stringified (2-space indent, `ensure_ascii=False`).
- Keep the IIFE + `var C` + loop shape and the `window.__resourceBlobs`
  global exactly — `support.js` reads it; a different name or shape silently
  no-ops.

## What's editable vs vendored

Vendored from kit — **don't hand-edit** (change it in kit):

- `site/components.js` (generated), `site/support.js`, `site/_ds/` (vendored
  Claude Design output; kit owns only the token *values* in
  `_ds/*/styles.css`).
- Shared `site/*.dc.html` components and `site/images/ui/`.
- Every `scripts/*.py`, `svgo.config.mjs`, `justfile`.
- `.editorconfig`, `.gitattributes`, `.claude/settings.json`,
  `CODE_OF_CONDUCT.md`, `AGENTS.md`.
- `.githooks/pre-commit`, most of `.github/` (see `sync.toml`).

Platform-icon files (`site/PlatformIcon.dc.html`,
`site/data/platform-icons.js`, `site/images/platforms/`) are vendored from
`platforms`, directly — not through kit.

Owned per repo (never vendored): `site/data/*.js` (data), `NOTICE.md`,
`.github/ISSUE_TEMPLATE/*`, `.github/PULL_REQUEST_TEMPLATE.md` (each carries
the repo's own Discussions URL), and each repo's own `Intro.dc.html`.

## Cross-repo sync

- `sync.toml` is each repo's manifest; `scripts/sync.py` applies it.
- `[publish]` = what a repo owns; `[subscribe.*]` = what it vendors, at a
  pinned `ref`.
- kit owns essentially all shared tooling (scripts, CI, editor/git config),
  so a Claude Design re-export touching hundreds of files with incidental
  metadata cleans up with one `just build` in any repo.
- kit and `platforms` pull from each other (two-way): `platforms` owns the
  platform-icon micro-kit, kit owns everything else. List repos subscribe to
  both directly. `sync.list.toml` is the list-repo template; it's vendored as
  a diff target and never auto-applied — `diff sync.list.toml sync.toml`
  after a sync shows paths kit added that a repo hasn't picked up.
- `home` vendors only a slice of kit (runtime, Nocturne, FAQ + theme toggle,
  scripts, CI/editor config).

Commands:

- `just sync` — repin every subscription to its source's current `main` and
  pull it. "Sync" always means this: get the latest.
- `python3 scripts/sync.py --update <name> --from-ref main` — repin and pull
  just one subscription (`kit` or `platforms`).
- `just sync-check` — read-only; fails if a vendored file drifted from its
  pinned `ref`. What CI runs (`check-vendored.yml`).
- `just sync-restore` — reapply the pinned `ref` without moving the pin.
  Rare: undoes a hand-edit to a vendored file.

Three guards against hand-editing a vendored file:

1. **Header comment** where the format allows (`Owned by vertex-order/<src> —
   edit here. Vendored elsewhere via sync.toml; don't edit the copy there.`).
   Skipped on `*.svg` and JSON.
2. **Pre-commit** — `sync.py --check-staged` refuses a staged vendored file
   that no longer matches its source.
3. **CI** — `check-vendored.yml` on every PR and push to `main`.

A change spanning repos: land the source-side piece first, then sync it into
the consumer, then land the consumer-side change. Without a shell, vendored
files are just the last-synced committed copies; the header comment is the
one guard visible.

## Build / preview / deploy

- No bundler, no Node for the site itself. Open `site/page.dc.html` off disk,
  or `just serve` to preview the way CI builds. Recipes: [`justfile`](justfile).
- Node is needed only for `just trim-svg` (below) and the SSR prerender;
  locally, `just build`/`just serve` degrade gracefully without Node.
- **Push to `main` = deploy**, via the `site` repo, not per-repo Pages:
  1. CI runs `just build` → `build/` (`page.dc.html` becomes `index.html`).
  2. `static.yml` (vendored from kit) rsyncs `build/` into
     `vertex-order/site`'s `public/<repo-name>/`; `home`'s own
     `sync-site.yml` writes to `public/` itself.
  3. `site`'s `pages.yml` publishes `public/` to GitHub Pages
     (`order.vertexprojects.org`).
- `build/` is gitignored; the only generated file committed is `components.js`.

### SSR prerender

`just build`'s last step runs `scripts/ssr-render.js`: it boots the real
`support.js` runtime in jsdom against build-time defaults and writes the
settled result over `build/index.html`, so the deployed page paints real
content before React loads. Same runtime, same components, run once at build
time. Client boot is unchanged (full non-hydrating remount).

## SVGs

- `site/images/**/*.svg` are checked in minified and self-closing.
- `scripts/normalize-svg.py` canonicalizes serialization to self-closing tags
  — run by the pre-commit hook and `just build`; `check-generated.yml` fails
  a PR whose SVGs aren't canonical (a second gotcha alongside `components.js`).
  Pure string pass, no visual change.
- `just trim-svg` is a **separate one-time minify pass**, not part of
  `build`: svgo (`svgo.config.mjs`) then `scripts/trim-svg.py` (drops path
  subpaths entirely outside the `viewBox`). Needs Node (`npx` fetches svgo on
  first run). Re-check every changed icon visually; `trim-svg.py` bails per
  file on transforms / `<use>` / masks / strokes / rotated arcs.
- Without a shell, neither runs: keep hand edits minimal and don't paste a
  pretty-printed file over a minified one.

## Repo-specific notes

### kit

- A component library: the DC runtime (`site/support.js`), **Nocturne**
  (`site/_ds/`), and the shared `*.dc.html` components. Doesn't run anything
  itself.
- `site/page.dc.html` is kit's own entry page — a "tuning bench" rendering
  fixture data (`site/data/`) as a component gallery, deployed to
  `public/kit/`. It's also the generic, data-driven entry-page template every
  list repo pulls verbatim; a list repo supplies its own `site/data/index.js`
  + `group-*.js`.
- Owned here: the generic components, token values in
  `_ds/nocturne-*/styles.css`, `site/images/ui/`,
  `scripts/{bundle-components,sync,ssr-render}.*`, `package.json` (Node deps
  for `ssr-render.js` only — never shipped to the browser), the SVG scripts
  and `svgo.config.mjs` (kit-owned despite the names), `justfile`,
  `.githooks/`, `.github/`, and this file.
- Vendored from `platforms`: `PlatformIcon.dc.html`, `platform-icons.js`,
  `images/platforms/`. kit re-bundles `PlatformIcon` into its own
  `components.js` for its tuning bench only; list repos don't depend on that.
- Publishing a new shared path: add it to `[publish].paths` in `sync.toml`
  **and** to `sync.list.toml` (list repos) / the consumers' own
  `[subscribe.kit].paths`.

### platforms

- Staging ground for tuning how platform icons render in listings — nothing
  here ships to the listings directly (kit and list repos pull the files).
- `site/data/platform-icons.js` is the record (`window.PLATFORM_ICONS`): one
  entry per platform — an `icon` (Bootstrap Icon class), an `iconImg` (path
  under `images/platforms/`), or a `text` label, with optional `iconSize` /
  `imgStyle` / `fontSize` / `prefix` / `suffix` / `jpTag`. **Values are page
  (1×) size** — exactly what `PlatformIcon.dc.html` renders in a row.
  Bootstrap glyphs are a fixed 16px (32px after the 2× zoom).
- `site/page.dc.html` renders the list twice from the same data: a
  **Zoomed** grid via `ZoomedPlatformIcon.dc.html` (`scale` 2, CSS `zoom`, on
  ruled guide lines) and a **Page size** grid via the real
  `PlatformIcon.dc.html` at `scale` 1.
- Owned here: `platform-icons.js`, `PlatformIcon.dc.html`,
  `ZoomedPlatformIcon.dc.html`, `page.dc.html`, `images/platforms/`,
  `NOTICE.md`.
- A new `PlatformIcon` prop needing a Nocturne token: kit first → sync kit
  into `platforms` → platform change → sync `platforms` into kit and the
  list repos.
- Every icon `trim-svg` changes needs a visual re-check in both grids.

### home

- The org landing page: a single page linking to every franchise list, plus a
  shared FAQ. No series data, no platform icons, no floating nav.
- `site/data/{games,movies,books}.js` each assign a plain
  `window.*_FRANCHISES` array of `{ title, href?, by?, firstPublished? }`
  (`href` omitted for a placeholder). `site/data/site.js` →
  `window.SITE_CONFIG`; `site/data/faq.js` → `window.FAQ_ITEMS` (matches kit's
  list-repo shape). `schemas/franchise-list.schema.json` and
  `schemas/site.schema.json` are own to this repo; `faq.schema.json` is
  vendored.
- Vendors only `FAQ.dc.html` and `ThemeToggle.dc.html` (change them in kit
  first); no platform micro-kit, series components, or floating nav.
- Deploys with its own `sync-site.yml` (not vendored `static.yml`), into
  `public/`.

### List repos (`final-fantasy`, `kingdom-hearts`)

- Own `site/data/index.js` + `group-*.js` (the game data), `sources/` notes,
  and their own `Intro.dc.html`; `site/page.dc.html` is the generic template
  vendored from kit and renders it.
- Subscribe to kit and, directly, to `platforms`. Platform-icon objects
  inline in `group-*.js` follow the canonical filenames/sizes/model from
  `platforms`.
- Vendored checks enforce data quality in CI: `scripts/validate-data.py`
  (schemas), `scripts/check-dedup-drift.py` (cross-listed entries),
  `scripts/check-anchors.py` (`#entry-…` links must resolve — run it after
  renaming or restructuring an entry).
