// theme-dev.js — dev-only cache-bust for data/theme.css, so an edit to that
// file shows up in Claude Design preview without a manual query-string bump
// (one of those used to get hand-typed straight into vendored page.dc.html
// and accidentally checked in -- see final-fantasy's ?v=ff4 cleanup).
//
// No-op for the built site: `just build` renames page.dc.html to
// index.html, and the bust below only fires when the *currently loaded
// document's own path* ends in .dc.html -- i.e. site/page.dc.html or any
// component opened directly (Claude Design preview, `just serve` pointed at
// site/ itself). build/index.html never matches, so the deployed site keeps
// normal HTTP caching on theme.css.
//
// Escape hatch, for when you're iterating on something other than
// theme.css and don't want the extra reload: run
//   localStorage.setItem('vertexNoCacheBust', '1')
// in the devtools console to turn this off for that browser. Deliberately
// runtime-only browser state with no file-based equivalent, so "cache-bust
// off" can never be checked in by accident -- clear the key (or use a
// private window) to turn it back on.
(function () {
  if (!/\.dc\.html$/i.test(location.pathname)) return;
  try {
    if (localStorage.getItem('vertexNoCacheBust') === '1') return;
  } catch (e) {}
  var link = document.querySelector('link[href*="data/theme.css"]');
  if (!link) return;
  var base = link.getAttribute('href').split('?')[0];
  link.setAttribute('href', base + '?v=' + Date.now());
})();
