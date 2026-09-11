// Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
// don't edit the copy there.
//
// One-time SVG trimming config — used by `just trim-svg`, NOT part of `build`.
//
// svgo strips what our two build-time passes (strip-c2pa.py, normalize-svg.py)
// deliberately leave alone: editor cruft (Inkscape <namedview>/<perspective>,
// XML prolog, comments, <metadata>), unused <defs> (dead gradients/clipPaths),
// inline style="" props, and excess coordinate precision.
//
// Everything here CAN change rendering. After running, eyeball every changed
// icon wherever it renders — at every size it renders at — and diff the SVGs
// before committing. Retest priority:
//   1. removeDimensions — icons lose width/height, now scale to their box.
//   2. convertStyleToAttrs — style="fill:#fff" becomes fill="#fff"; watch for
//      dropped shorthand.
//   3. floatPrecision — rounded path coords; check small/thin glyphs.
//
// svgo emits self-closing tags already, but `just trim-svg` re-runs
// normalize-svg.py afterward so the check-in form is guaranteed.
//
// What svgo does NOT do: prune path subpaths that sit fully outside the
// viewBox (e.g. a wordmark left behind by a crop). That needs the
// geometry-aware pass in scripts/trim-svg.py.

export default {
  multipass: true,
  js2svg: {
    pretty: false, // keep the one-line form the icons check in as
    eol: 'lf',
  },
  plugins: [
    {
      name: 'preset-default',
      params: {
        overrides: {
          // viewBox IS the crop — dropping it breaks aspect/scaling.
          removeViewBox: false,
          // No icon has a11y text today; if one gains <title>/<desc>, keep it.
          removeTitle: false,
          removeDesc: false,
          // 2 decimals is <0.5% of the smallest icon's viewBox.
          cleanupNumericValues: { floatPrecision: 2 },
          convertPathData: { floatPrecision: 2 },
          convertTransform: { floatPrecision: 3 },
        },
      },
    },
    // Not in preset-default:
    'removeDimensions', // strip width/height, keep viewBox → scales to box
    'convertStyleToAttrs', // style="fill:#fff" → fill="#fff"
  ],
};
