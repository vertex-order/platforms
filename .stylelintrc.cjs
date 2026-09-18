// Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
// don't edit the copy there.
//
// stylelint config for `just check-css` / `.githooks/pre-commit` /
// `.github/workflows/check-css.yml`. Catches CSS that fails to parse at
// all -- the class of bug where a comment closes earlier than intended
// (a literal */ inside /* ... */) and corrupts everything up to the real
// terminator, which browsers then silently drop with no console error
// (see site/data/theme.css's fix for the shipped instance). That failure
// is a hard `CssSyntaxError` from stylelint's parser regardless of which
// rules are enabled, so `stylelint-config-recommended` (correctness rules
// only, no stylistic/formatting opinions) is here mainly to give the tool
// a non-empty ruleset to run -- it also catches other real mistakes
// (duplicate properties, invalid units, empty blocks, ...) for free.
//
// site/_ds/ (Nocturne) is vendored Claude Design output kit never
// hand-edits, so its violations aren't actionable -- excluded rather than
// fixed. Everything else is linted, including each repo's own un-vendored
// site/data/theme.css: that file is exactly what shipped this bug, and
// exactly what the rest of kit's test suite doesn't reach (see
// docs/testing.md "Scope") -- this check runs from published, vendored
// tooling instead, so it lands in every repo without theme.css itself
// needing to be vendored.
module.exports = {
  extends: "stylelint-config-recommended",
  ignoreFiles: ["**/site/_ds/**"],
};
