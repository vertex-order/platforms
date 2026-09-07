<!-- README.md (markdown) -->

# platforms

A visual reference for working out how platform icons should render in the
[Vertex Order](https://vertex-order.github.io) game listings — sizes,
weights, and the light/dark colour treatment — without editing the real
site.

[`site/data/platform-legend.js`](site/data/platform-legend.js) is the single
source of truth: one entry per platform, each a Bootstrap Icon, an image, or
a short text label, plus per-icon size / style overrides. The legend values
are the **zoomed** (~2×) sizes.
[`site/Platforms.dc.html`](site/Platforms.dc.html) renders that list two ways:

- **Zoomed icons** — ~2× page size, on ruled guide lines, for eyeballing
  optical size and weight while tuning.
- **Page size icons** — each entry through
  [`site/PlatformIcon.dc.html`](site/PlatformIcon.dc.html) (the component the
  real site uses) at listing-row size: Bootstrap glyphs at a fixed 16px,
  images at half their legend height.

Plain HTML / CSS / JS, no build step, no Node. Open
[`site/Platforms.dc.html`](site/Platforms.dc.html) straight off disk, or run
`just serve`. Every push to `main` deploys to GitHub Pages.

Third-party icon attribution: [NOTICE.md](NOTICE.md). Contributor guide:
[CONTRIBUTING.md](CONTRIBUTING.md). Notes for AI coding tools:
[AGENTS.md](AGENTS.md) and [`.claude/CLAUDE.md`](.claude/CLAUDE.md).
