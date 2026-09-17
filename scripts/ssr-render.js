#!/usr/bin/env node
// scripts/ssr-render.js — kit-owned. Not vendored (see sync.toml [publish]).
//
// Prerenders a built entry page (default build/index.html) to static markup,
// so the deployed page paints real content immediately instead of the blank
// shell support.js currently fills in only after React + data load. Runs
// after `just build` has assembled build/ — never touches site/.
//
// How: boots the *real* support.js DC runtime inside jsdom (not a
// reimplementation) against build-time defaults (no localStorage entries =>
// the same defaults support.js already falls back to for a first-time
// visitor), waits for it to settle, then serializes the resulting DOM back
// over the entry file. The client boot path is untouched — support.js still
// calls ReactDOM.createRoot(...).render() on load (site/support.js:198-200),
// a full client-side remount, not a hydrate() — so it cleanly overwrites
// this prerendered shell once it reads the visitor's real localStorage
// prefs (theme, order, checked progress). This step only removes the blank
// paint before that happens; it changes no runtime behavior.
//
// Document URL is a fake https:// origin (SSR_ORIGIN below), not file:// —
// file:// is an opaque origin in jsdom (and in real browsers), and
// page.dc.html reads localStorage synchronously during its initial state
// init, which throws on an opaque origin and takes the whole page down via
// the DC runtime's error boundary. https:// also means the entry page's own
// `if (location.protocol === 'file:') document.write(...)` bundling branch
// (which loads components.js — see CLAUDE.md "Regenerating components.js")
// correctly does NOT fire, same as a real deployed page: every *.dc.html
// and data/*.js is "live"-fetched exactly like production, just intercepted
// below and served from the local build/ directory instead of the network.
//
// React/ReactDOM are vendored locally (package.json) at the *exact*
// versions site/support.js hardcodes for its own CDN load (see
// REACT_CDN_URL/REACT_DOM_CDN_URL below), and those two exact URLs are
// intercepted to serve the local copies — so this pass needs no network
// access and can never drift from what a real visitor's browser would run.

'use strict';

const fs = require('fs');
const path = require('path');
const { JSDOM, requestInterceptor } = require('jsdom');

const SETTLE_POLL_MS = 50;
const SETTLE_STABLE_TICKS = 3;
const SETTLE_TIMEOUT_MS = 20000;
const SSR_ORIGIN = 'https://ssr-render.internal';

// Exact CDN URLs site/support.js hardcodes (REACT_URL / REACT_DOM_URL) —
// keep in sync if that pin ever moves.
const REACT_CDN_URL = 'https://unpkg.com/react@18.3.1/umd/react.production.min.js';
const REACT_DOM_CDN_URL = 'https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js';
// Same exact hashes as support.js's REACT_SRI/REACT_DOM_SRI — needed only
// because jsdom sets these via the `.integrity` IDL property (support.js's
// loadScript(), site/support.js:1825-1833), and jsdom 30 doesn't reflect
// that property to the content attribute (verified empirically — .src and
// .crossOrigin reflect, .integrity silently doesn't). Without restoreSri()
// below, the serialized page would silently ship these two <script> tags
// with no integrity check at all.
const REACT_SRI = 'sha384-DGyLxAyjq0f9SPpVevD6IgztCFlnMF6oW/XQGmfe+IsZ8TqEiDrcHkMLKI6fiB/Z';
const REACT_DOM_SRI = 'sha384-gTGxhz21lVGYNMcdJOyq01Edg0jhn/c22nsx0kyqP0TxaV5WVdsSH1fSDUf5YJj1';

const MIME_BY_EXT = {
  '.js': 'application/javascript',
  '.mjs': 'application/javascript',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.html': 'text/html',
};

function fileResponse(absPath) {
  const body = fs.readFileSync(absPath);
  const type = MIME_BY_EXT[path.extname(absPath).toLowerCase()] || 'application/octet-stream';
  return new Response(body, { headers: { 'Content-Type': type } });
}

// Resolves a same-origin resource (support.js, data/*.js, dynamically
// injected series-*.js, every *.dc.html a dc-import fetches) straight off
// build/ on disk, plus the two pinned React/ReactDOM CDN URLs from
// node_modules — no network dependency for this build step. Returns null for
// anything else (e.g. the bootstrap-icons CDN stylesheet), which callers
// fall back to the real network for, harmlessly.
function resolveLocal(url, buildDir) {
  if (url === REACT_CDN_URL) {
    return fileResponse(path.resolve(__dirname, '..', 'node_modules', 'react', 'umd', 'react.production.min.js'));
  }
  if (url === REACT_DOM_CDN_URL) {
    return fileResponse(path.resolve(__dirname, '..', 'node_modules', 'react-dom', 'umd', 'react-dom.production.min.js'));
  }
  if (url.startsWith(SSR_ORIGIN + '/')) {
    const pathname = new URL(url).pathname;
    return fileResponse(path.join(buildDir, decodeURIComponent(pathname)));
  }
  return null;
}

// Governs <script src>/<link>/<iframe> element loads (the CDN React/ReactDOM
// tags, dynamically-injected series-*.js) — NOT plain fetch() calls, which
// dc-import/x-import use directly and which jsdom doesn't route through
// this at all (see window.fetch below).
function makeInterceptor(buildDir) {
  return requestInterceptor((request) => resolveLocal(request.url, buildDir) || undefined);
}

// jsdom drops the integrity attribute when it's set via the IDL property
// (see the REACT_SRI comment above) — restore it by exact src match so the
// shipped page keeps real SRI protection on the CDN scripts.
function restoreSri(document) {
  const bySrc = { [REACT_CDN_URL]: REACT_SRI, [REACT_DOM_CDN_URL]: REACT_DOM_SRI };
  document.querySelectorAll('script[src]').forEach((el) => {
    const sri = bySrc[el.getAttribute('src')];
    if (sri && !el.getAttribute('integrity')) el.setAttribute('integrity', sri);
  });
}

function waitForSettle(window) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    let last = null;
    let stableTicks = 0;
    const tick = () => {
      const el = window.document.getElementById('dc-root');
      const snapshot = el ? el.innerHTML : null;
      if (snapshot && snapshot === last) stableTicks++;
      else { stableTicks = 0; last = snapshot; }
      if (snapshot && stableTicks >= SETTLE_STABLE_TICKS) return resolve();
      if (Date.now() - start > SETTLE_TIMEOUT_MS) {
        if (!snapshot) return reject(new Error('#dc-root never rendered within ' + SETTLE_TIMEOUT_MS + 'ms'));
        console.warn('[ssr-render] settle timeout — writing best-effort render');
        return resolve();
      }
      setTimeout(tick, SETTLE_POLL_MS);
    };
    setTimeout(tick, SETTLE_POLL_MS);
  });
}

async function main() {
  const buildDir = process.argv[2];
  if (!buildDir) {
    console.error('usage: node scripts/ssr-render.js <build-dir> [entry-file]');
    process.exit(1);
  }
  const entryFile = process.argv[3] || 'index.html';
  const entryPath = path.join(buildDir, entryFile);
  const html = fs.readFileSync(entryPath, 'utf8');

  const dom = new JSDOM(html, {
    url: SSR_ORIGIN + '/' + entryFile,
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    resources: { interceptors: [makeInterceptor(path.resolve(buildDir))] },
    beforeParse(window) {
      // dc-import/x-import call fetch() directly (site/support.js:1208,1652)
      // rather than going through an element jsdom's resource loader governs
      // — jsdom doesn't give window.fetch a body of its own, so without this
      // every component/data fetch throws "fetch is not defined".
      const buildDirAbs = path.resolve(buildDir);
      window.fetch = function (input, init) {
        // dc-import passes bare relative paths ("./FAQ.dc.html") — resolve
        // against the document like a real fetch() would before matching or
        // falling through to Node's fetch, which requires an absolute URL.
        const raw = String(input && input.url ? input.url : input);
        const url = new URL(raw, window.location.href).href;
        const local = resolveLocal(url, buildDirAbs);
        if (local) return Promise.resolve(local);
        return fetch(url, init);
      };
      // jsdom doesn't implement matchMedia; page.dc.html's own script calls
      // it for theme detection at build time. No real OS preference exists
      // here, so this reports "no light preference" — the same "dark"
      // fallback the client itself uses before it ever reads a real one.
      window.matchMedia = function () {
        return {
          matches: false,
          media: '',
          addEventListener() {},
          removeEventListener() {},
          addListener() {},
          removeListener() {},
        };
      };
    },
  });
  const { window } = dom;
  window.addEventListener('error', (e) => {
    console.error('[ssr-render]', e.error || e.message);
  });

  try {
    await waitForSettle(window);
  } finally {
    restoreSri(window.document);
    let out = '<!DOCTYPE html>\n' + window.document.documentElement.outerHTML;
    // Elements the runtime builds by string-concatenating an absolute base
    // (e.g. data/index.js's dynamically-injected <script src> for each
    // series file, resolved against SSR_ORIGIN) bake that absolute URL into
    // the attribute value itself, not just the live resolution — strip it
    // back to relative so nothing in the shipped page ever points at this
    // build-only fake origin. Harmless either way once loaded (the client's
    // own boot re-runs and re-injects these fresh against the real origin),
    // but a leaked ssr-render.internal URL would otherwise sit in the page
    // as a guaranteed-failing request.
    out = out.split(SSR_ORIGIN + '/').join('./').split(SSR_ORIGIN).join('.');
    fs.writeFileSync(entryPath, out);
    window.close();
  }
  console.log('[ssr-render] wrote static render: ' + entryPath);
}

main().catch((err) => {
  console.error('[ssr-render] failed:', err);
  process.exit(1);
});
