<!-- CONTRIBUTING.md (markdown) -->

# Contributing

Everything you need is on this page. No Claude Design account, no Node, no
build tooling — the site is plain HTML/CSS/JS under [`site/`](site/). Clone,
edit, preview in a browser, open a PR.

- [What this repo is](#what-this-repo-is)
- [Quick start](#quick-start)
- [Adjust a platform icon](#adjust-a-platform-icon) ← the common case
- [Add a new platform](#add-a-new-platform)
- [Edit page copy](#edit-page-copy)
- [Restyle](#restyle)
- [Edit a `.dc.html` component](#edit-a-dchtml-component)
- [Cross-repo sync](#cross-repo-sync)
- [Preview locally](#preview-locally)
- [Open a PR](#open-a-pr)
- [Licensing](#licensing)
- [Appendix: repo layout](#appendix-repo-layout)
- [Appendix: deploy internals](#appendix-deploy-internals)

## What this repo is

A staging ground for working out how platform icons should render in the
[Vertex Order](https://vertex-order.github.io) game listings — the pixel
sizes, weights, and the light/dark colour treatment — without touching the
real site.

[`site/data/platform-icons.js`](site/data/platform-icons.js) is the single
source of truth. It assigns `window.PLATFORM_ICONS`, an array with **one
entry per platform**. Each entry is one of:

| Kind | Fields |
| --- | --- |
| Bootstrap Icon | `icon: 'bi bi-steam'` |
| Image | `iconImg: 'images/platforms/ps5.svg'`, `iconSize`, `imgStyle` |
| Text label | `text: 'Wii U'`, `fontSize` |

plus optional `prefix`, `suffix`, `jpTag`, `name` (the hover title).
**The sizes in this file are page (1×) size** — exactly what
`PlatformIcon.dc.html` renders in a listing row, copied straight across.

[`site/Platforms.dc.html`](site/Platforms.dc.html) renders the list twice
from the same data — the only difference is CSS `zoom`:

- **Zoomed icons** — the same entries at 2×, on ruled guide lines, easier to
  judge optical size and weight. Rendered by
  [`site/ZoomedPlatformIcon.dc.html`](site/ZoomedPlatformIcon.dc.html), which
  passes `scale` 2 to `PlatformIcon`.
- **Page size icons** — each entry straight through
  [`site/PlatformIcon.dc.html`](site/PlatformIcon.dc.html), the component the
  real site uses, at listing-row size (`scale` 1). Bootstrap glyphs are a
  fixed 16px there (32px after the 2× zoom), so only images and text carry a
  tunable number.

Workflow: tune an entry in the Zoomed grid, check it in the Page size grid,
copy the number you landed on into the real site's data as-is.

## Quick start

```sh
git clone https://github.com/vertex-order/platforms
cd platforms
# open site/Platforms.dc.html in a browser — done, no build step
```

Optional: install [`just`](https://github.com/casey/just) for the
`just serve` / `just build` shortcuts, and run `just install-hooks` once to
wire up the pre-commit hook (strips image metadata, normalizes SVG
serialization, regenerates `site/components.js`). Neither is required to
contribute.

## Adjust a platform icon

Edit the entry in
[`site/data/platform-icons.js`](site/data/platform-icons.js):

- **Image size** — `iconSize` is the rendered height in px; keep the
  `height: Npx` inside `imgStyle` in step with it. The `imgStyle` filter
  chain is what tints an icon to match the text colour (and the
  `[data-theme="light"]` rules in `Platforms.dc.html` re-tint it for light
  mode — match an existing icon's filter so both themes work).
- **Text label size** — `fontSize` (e.g. `'21.5px'`).
- **Bootstrap glyph size** — not per-entry; change the `font-size` in
  `PlatformIcon.dc.html` (fixed 16px, scaled by `zoom` in the Zoomed grid),
  which affects every glyph.

Reload the page. Data-only edits need no rebuild.

## Add a new platform

1. Drop the image in
   [`site/images/platforms/`](site/images/platforms/), named after what it
   represents (`ps5.svg`, `snes.png`), not where it came from. (Bootstrap
   Icon or text-only entries skip this.) For an SVG, the pre-commit hook
   canonicalizes serialization (self-closing tags) and CI enforces it — no
   setup needed. To also minify — strip editor cruft, cut coordinate
   precision, drop offscreen artwork a crop left behind — run the one-time
   `just trim-svg` pass and eyeball the result in both icon grids. That
   pass is the only thing in the repo that needs Node — install it first:
   `winget install OpenJS.NodeJS.LTS` (Windows) / `brew install node`
   (macOS) / your distro's package; `just trim-svg` then calls `npx`,
   which fetches and caches svgo on first run (no `npm install`).
2. Add an entry to `PLATFORM_ICONS` in `platform-icons.js` — copy a
   neighbouring entry of the same kind as a template.
3. Add the source to the **Credits** list in
   [`site/Platforms.dc.html`](site/Platforms.dc.html), and add a section for
   it in [`NOTICE.md`](NOTICE.md) (the authoritative attribution record —
   alphabetical by platform name).

## Edit page copy

Title, intro, section headings, credits, copyright:
[`site/Platforms.dc.html`](site/Platforms.dc.html). It is readable HTML with
`{{ expression }}` template bindings, evaluated at runtime by `support.js`.
The `.dc.html` naming is just the format Claude Design imports/exports — you
don't need the tool to edit it.

The **Help Wanted** list is data, not copy — edit
[`site/data/help-wanted.js`](site/data/help-wanted.js) (one string per
item); [`site/HelpWanted.dc.html`](site/HelpWanted.dc.html) just renders it.

## Restyle

Colours, fonts, spacing and radii are CSS custom properties at the top of
[`site/_ds/nocturne-dd511f00-0314-498c-83ef-49f001a371b0/styles.css`](site/_ds/nocturne-dd511f00-0314-498c-83ef-49f001a371b0/styles.css).
Change the token values there rather than hardcoding inline. Read that
folder's [`readme.md`](site/_ds/nocturne-dd511f00-0314-498c-83ef-49f001a371b0/readme.md)
first — it documents the system's conventions and a do/don't list.

The light-mode palette and the light-mode image-filter overrides live in the
`<style>` block of `Platforms.dc.html` itself.

The rest of `_ds/` (`_ds_bundle.js`, `_ds_manifest.json`,
`_adherence.oxlintrc.json`) is vendored — don't hand-edit; start a
[discussion](https://github.com/vertex-order/platforms/discussions) if
something there needs to change.

## Edit a `.dc.html` component

**Owned here:** `PlatformIcon.dc.html`, `ZoomedPlatformIcon.dc.html`,
`Platforms.dc.html`. **Vendored from [`vertex-order/kit`](https://github.com/vertex-order/kit)**
(don't edit here — see [Cross-repo sync](#cross-repo-sync)):
`BackToTop.dc.html`, `HelpWanted.dc.html`, plus `support.js` and `_ds/`.

If you change an owned component, regenerate
[`site/components.js`](site/components.js) — a build artifact that inlines
every component so `Platforms.dc.html` also works opened straight off disk
(`file://`):

```sh
just bundle-components   # or: just build
```

The pre-commit hook does this automatically if you ran `just install-hooks`,
and CI ([`check-generated.yml`](.github/workflows/check-generated.yml))
fails your PR if it's stale — so if you forget, run `just bundle-components`
and commit the result.

`Platforms.dc.html` loads `components.js` **only over `file://`**. When you
preview over http (`just serve`, `python -m http.server`, any static
server) the runtime fetches each `*.dc.html` live, so your component edits
show up on reload whether or not you regenerated the bundle. Opened off disk,
a refresh shows the *bundled* copy — regenerate before you reload.

**Never hand-edit `components.js`.** Working without a shell (e.g. inside a
design tool)? See the header comment at the top of `components.js` for the
by-hand procedure, and [`.claude/CLAUDE.md`](.claude/CLAUDE.md).

`PlatformIcon.dc.html` is owned here and pulled by `kit` (and, via kit, by
every list repo) — it is the whole point of the Page size grid. A change to
it ships everywhere, so test it against real data before you PR.

## Cross-repo sync

This repo owns the **platform-icon micro-kit** (`PlatformIcon.dc.html`,
`platform-icons.js`, `images/platforms/`, the SVG scripts, `svgo.config.mjs`)
and vendors the **build substrate** (`support.js`, `_ds/`, `images/ui/`,
`BackToTop.dc.html`, `HelpWanted.dc.html`, `bundle-components.py`, `sync.py`)
from [`vertex-order/kit`](https://github.com/vertex-order/kit).
[`sync.toml`](sync.toml) is the manifest.

- `just sync` — pull the vendored files at the pinned `ref`.
- `just sync-check` — what CI runs
  ([`check-vendored.yml`](.github/workflows/check-vendored.yml)); fails on drift.
- `just sync-update kit` — repin to kit's current HEAD, then pull.

Never hand-edit a vendored file. To change one, change it in `kit`, then
`just sync-update kit` here. A change that spans both repos: land the kit
side first, `sync-update kit`, then land the platforms side.

Three things stop a hand edit from landing: a `Owned by vertex-order/kit —
edit here` header comment on the file itself (where the format allows one),
a pre-commit guard (`sync.py --check-staged`) that refuses to commit a
vendored file that no longer matches its source, and the same check in CI.
None of them stop you from *making* the edit locally — only from committing
or merging it — so still read the header comment before you type.

## Preview locally

Simplest — open [`site/Platforms.dc.html`](site/Platforms.dc.html) directly
in a browser (`file://`). `components.js` plus the classic-script
`platform-icons.js` make that work with no server. Off disk the page depends on `components.js`
being current, so run `just bundle-components` after editing any `*.dc.html`.

To preview the way it deploys — and so component edits load live without a
regen — serve `site/` over http:

```sh
cd site && python -m http.server 8000
# http://localhost:8000/Platforms.dc.html
```

Any static server works (`npx serve`, VS Code Live Server, …). With `just`:
`just serve` runs the exact copy-and-rename step CI uses
(`site/` → `build/`, `Platforms.dc.html` → `index.html`), so you preview the
real deploy output.

## Open a PR

1. Raise it in [Discussions](https://github.com/vertex-order/platforms/discussions)
   first and agree the change there. PRs without a linked Discussion (or
   issue) may be closed unreviewed.
2. Fork, branch off `main`.
3. Make your edit under `site/`.
4. Preview locally. If you touched a `*.dc.html`, run `just bundle-components`
   and commit `site/components.js`.
5. Sign off each commit — `git commit -s` (see [Licensing](#licensing)).
6. PR against `main`, linking the Discussion. **Merging deploys
   automatically** — no manual export step, ever.

## Licensing

Everything in this repo is [MIT](LICENSE) — what you contribute, and what
ships out. It's Claude Design's framework tailored to rendering order lists;
we're glad to have people take it and build their own.

The one exception is the platform icons under `site/images/platforms/` —
third-party marks used under fair use, each recorded in [`NOTICE.md`](NOTICE.md)
with its own source and terms. Don't submit an icon without adding its
`NOTICE.md` section.

Sign off every commit with `git commit -s`. It adds a `Signed-off-by` line
certifying you wrote the change, or otherwise have the right to submit it
under MIT — the
[Developer Certificate of Origin](https://developercertificate.org/).

Questions and proposals go in
[Discussions](https://github.com/vertex-order/platforms/discussions);
issues are for collaborators.

## Appendix: repo layout

Owned here (edit these):

```
site/
├── Platforms.dc.html        entry page: copy, both icon grids, render/logic
├── PlatformIcon.dc.html     page-size icon component — pulled by kit + every list
├── ZoomedPlatformIcon.dc.html   2x wrapper, tuning only (kit doesn't need it)
├── data/
│   ├── platform-icons.js    window.PLATFORM_ICONS — the platform record
│   └── help-wanted.js       window.HELP_WANTED_ITEMS — the Help Wanted list
└── images/platforms/        platform icons referenced by platform-icons.js
scripts/{strip-c2pa,normalize-svg,trim-svg}.py   image metadata / SVG canonicalize / one-time trim
svgo.config.mjs              config for `just trim-svg`
sync.toml                    cross-repo file-sync manifest
justfile, .githooks/pre-commit, .github/  build glue + CI
```

Vendored from [`vertex-order/kit`](https://github.com/vertex-order/kit) via
`just sync` — **don't hand-edit** (see [Cross-repo sync](#cross-repo-sync)):

```
site/support.js, site/_ds/, site/images/ui/,
site/BackToTop.dc.html, site/HelpWanted.dc.html,
scripts/bundle-components.py, scripts/sync.py
```

Generated (`just bundle-components`): `site/components.js`.

```
.github/workflows/
├── static.yml            build + deploy site/ to Pages on push to main
├── check-generated.yml   PR check: components.js / SVG serialization stale
└── check-vendored.yml    PR check: a vendored file drifted from kit
```
```

## Appendix: deploy internals

Every push to `main` runs
[`.github/workflows/static.yml`](.github/workflows/static.yml):

1. Checks out the repo.
2. Installs `just`, runs `just build` — strips image metadata, normalizes
   SVG serialization, regenerates `components.js`, copies `site/` into a
   gitignored `build/`, renames
   `build/Platforms.dc.html` to `build/index.html` (GitHub Pages needs a
   root `index.html`; every other path in the file is already relative).
   Same recipe you can run locally.
3. Uploads `build/` as the Pages artifact and deploys it.

No bundler, no dependencies, no manual "export". Merging a PR to `main` is
the deploy.

**Verify a deploy:** the **Actions** tab, or the environment URL under
**Settings → Pages**.

**First-time setup** (if not already done): **Settings → Pages → Build and
deployment → Source** must be **GitHub Actions**, not "Deploy from a
branch".
