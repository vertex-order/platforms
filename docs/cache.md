<!-- docs/cache.md — owned by vertex-order/kit. Edit here.
     Vendored elsewhere via sync.toml; don't edit the copy there. -->

# Caching

Two unrelated caching problems show up in this build, and the fixes for
each live in different places. This doc covers both.

## `components.js` — the `file://` bundle

`page.dc.html` (and every component) fetches its sibling `*.dc.html` files
live at runtime. That `fetch()` is blocked when a page is opened directly
off disk (`file://`), so `components.js` exists as a pre-bundled fallback:
it inlines every sibling `*.dc.html` as a JS string, and `page.dc.html`
loads it — but only over `file://`:

```html
<script>
  if (location.protocol === 'file:') {
    document.write('<script src="./components.js"><\/script>');
  }
</script>
```

Over `http(s)` — GitHub Pages, `just serve`, and Claude Design's preview —
this tag is skipped and every `*.dc.html` is fetched fresh, so there's
nothing to cache-bust: editing a component shows up immediately. See the
comment at the top of `components.js` itself, and each repo's own
`.claude/CLAUDE.md` ("Regenerating components.js"), for how it's built and
when it actually needs regenerating.

## `data/theme.css` — the dev-only cache-bust

`data/theme.css` is a genuinely separate problem: it's a normal `<link
rel="stylesheet">`, fetched the same way (and cached the same way) whether
you're on `file://`, `http(s)`, or inside Claude Design's preview. Editing
its *content* doesn't change its *URL*, so a browser (or the preview's own
cache) can keep serving the pre-edit response after you save.

`site/theme-dev.js` fixes this by rewriting the `theme.css` `<link>`'s
`href` with a fresh `?v=<timestamp>` on every load — but only when it
should:

- **Fires** when the loaded document's own path ends in `.dc.html` — i.e.
  `site/page.dc.html` or any component opened directly, which covers both
  local dev and Claude Design's preview.
- **No-ops** everywhere else, in particular the built site
  (`build/index.html` — `just build` renames `page.dc.html` to
  `index.html`, so the path never ends in `.dc.html`). Production keeps
  normal HTTP caching on `theme.css`.

Every helmet that links `theme.css` also carries a one-line
`<script src="./theme-dev.js"></script>` right after it — same duplication
as the `theme.css` link itself (see `docs/init-list.md` "Theme colors"):
a component previewed standalone needs its own copy, same as the full page.

### Turning it off

Cache-busting on every load means an extra request each reload, which
you may not want if you're iterating on something other than
`theme.css`. To turn it off for your browser:

```js
localStorage.setItem('vertexNoCacheBust', '1')
```

in devtools. Clear the key (or use a private window) to turn it back on.

This is deliberately **runtime-only, browser-only state** — there is no
file-based way to disable the cache-bust, on purpose, so "cache-bust off"
can never end up in a commit. Don't add one. (This is also why the fix
lives in its own small file rather than as a hand-typed query string on
the `theme.css` link itself — that's what caused the problem in the
first place: final-fantasy's retheme temporarily shipped
`data/theme.css?v=ff4` straight into vendored `page.dc.html`, which
defeats vendoring — that file must stay byte-identical to kit's copy.)

### Why not in `support.js`

`site/support.js` is the vendored Claude Design / DC runtime itself —
"vendored, don't edit" applies to it even inside kit (see
`CONTRIBUTING.md`). `theme-dev.js` is a separate, kit-authored file for
exactly that reason: it's ordinary app-level code kit's maintainers can
edit freely, sitting next to `support.js` rather than inside it.
