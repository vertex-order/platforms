#!/usr/bin/env node
// scripts/ssr-lib.js — kit-owned. Edit here. Vendored elsewhere via
// sync.toml (published alongside scripts/ssr-render.js, which `require`s
// it — it has to ship wherever ssr-render.js does); don't edit the copy
// there.
//
// Shared JSDOM boot mechanics factored out of scripts/ssr-render.js so
// tests/site/verify-ssr.js can boot a *second*, independent DC runtime
// instance against an already-written build/<entry> file -- the same way
// a real visitor's browser would -- without duplicating (and risking
// drift from) the CDN pin / SRI / fetch-shim / matchMedia-shim details
// ssr-render.js already gets right. See ssr-render.js's header comment
// for the full "why" of each piece; this file only hosts the mechanics.

"use strict";

const fs = require("fs");
const path = require("path");
const { JSDOM, requestInterceptor } = require("jsdom");

const SSR_ORIGIN = "https://ssr-render.internal";

// Exact CDN URLs site/support.js hardcodes (REACT_URL / REACT_DOM_URL) --
// keep in sync if that pin ever moves.
const REACT_CDN_URL = "https://esm.sh/react@19.3.0";
const REACT_DOM_CDN_URL = "https://esm.sh/react-dom@19.3.0/client";
const REACT_SRI =
  "sha384-gq3XRS6InsfZ3Lv6d+6mBuySvNkEX/1Ciw3jSlg9gL82444AmhVcwtYbpJfKbDqf";
const REACT_DOM_SRI =
  "sha384-p4FQDUEGwuQqD58o1+ZGDAQ7+hkNAiUKaJK/6iK2E/9dxO6TafEZMQadHMnx8NY9";

const MIME_BY_EXT = {
  ".js": "application/javascript",
  ".mjs": "application/javascript",
  ".css": "text/css",
  ".svg": "image/svg+xml",
  ".html": "text/html",
};

function fileResponse(absPath) {
  const body = fs.readFileSync(absPath);
  const type =
    MIME_BY_EXT[path.extname(absPath).toLowerCase()] ||
    "application/octet-stream";
  return new Response(body, { headers: { "Content-Type": type } });
}

// Resolves a same-origin resource (support.js, data/*.js, dynamically
// injected series-*.js, every *.dc.html a dc-import fetches) straight off
// build/ on disk -- no network dependency. Returns null for anything else
// (e.g. the bootstrap-icons CDN stylesheet), which callers fall back to
// the real network for, harmlessly.
//
// React/ReactDOM used to be interceptable here too (classic <script src>
// loads jsdom's resource loader governs), back when they were UMD. Now
// support.js loads them via dynamic import(), which jsdom's page scripts
// can't do at all -- see installReact below for how this sidesteps that
// instead of trying to intercept it.
function resolveLocal(url, buildDir) {
  if (url.startsWith(SSR_ORIGIN + "/")) {
    const pathname = new URL(url).pathname;
    return fileResponse(path.join(buildDir, decodeURIComponent(pathname)));
  }
  return null;
}

// support.js's loadReactUmd() loads React/ReactDOM via dynamic import() of
// an ESM CDN URL -- fine in a real browser, but jsdom's page-script
// execution has no importModuleDynamically callback wired at all (unlike
// a plain Node script), so any import() called from inside a <script src>
// jsdom runs throws ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING, no matter what
// URL or specifier it's given. Rather than fight that, this uses a real,
// unsandboxed Node require() -- running here, in ssr-lib.js's own process,
// not inside jsdom's realm -- to load the exact npm-installed versions and
// hand the finished modules straight to window.React/window.ReactDOM
// before any page script runs. loadReactUmd() already early-returns when
// both are present, so its own CDN-loading path (and the modulepreload
// link it would otherwise create) never runs during SSR at all -- a real
// visitor's browser, which has no such restriction, still goes through it
// completely normally.
function installReact(window) {
  // react-dom's client renderer (unlike plain react) reads bare `window`/
  // `document` at call time -- e.g. resolveUpdatePriority(), invoked from
  // deep inside a require()'d file, not something a per-file realm wrapper
  // would reach. Aliasing them onto Node's real global makes every plain
  // require() in the chain (react-dom/client and whatever it requires in
  // turn) resolve the same bare identifiers a real browser would provide,
  // no matter how deeply nested.
  global.window = window;
  global.document = window.document;
  window.React = require("react");
  window.ReactDOM = require("react-dom/client");
}

// Governs <script src>/<link>/<iframe> element loads -- NOT plain fetch()
// calls, which dc-import/x-import use directly (see installFetchShim), NOR
// dynamic import() (see installReactModuleOverride above).
function makeInterceptor(buildDir) {
  return requestInterceptor(
    (request) => resolveLocal(request.url, buildDir) || undefined,
  );
}

// jsdom drops the integrity attribute when it's set via the IDL property
// -- restore it by exact src/href match so a serialized page keeps real
// SRI protection on the CDN scripts/preloads. React/ReactDOM now load via
// <link rel=modulepreload>, not <script src> -- both selectors stay so
// this still covers Babel's classic <script src> too.
function restoreSri(document) {
  const bySrc = {
    [REACT_CDN_URL]: REACT_SRI,
    [REACT_DOM_CDN_URL]: REACT_DOM_SRI,
  };
  document.querySelectorAll("script[src], link[href]").forEach((el) => {
    const attr = el.tagName === "LINK" ? "href" : "src";
    const sri = bySrc[el.getAttribute(attr)];
    if (sri && !el.getAttribute("integrity")) el.setAttribute("integrity", sri);
  });
}

// dc-import/x-import call fetch() directly rather than going through an
// element jsdom's resource loader governs -- jsdom doesn't give
// window.fetch a body of its own, so without this every component/data
// fetch throws "fetch is not defined".
function installFetchShim(window, buildDir) {
  const buildDirAbs = path.resolve(buildDir);
  window.fetch = function (input, init) {
    // dc-import passes bare relative paths ("./FAQ.dc.html") -- resolve
    // against the document like a real fetch() would before matching or
    // falling through to Node's fetch, which requires an absolute URL.
    const raw = String(input && input.url ? input.url : input);
    const url = new URL(raw, window.location.href).href;
    const local = resolveLocal(url, buildDirAbs);
    if (local) return Promise.resolve(local);
    return fetch(url, init);
  };
}

// jsdom doesn't implement matchMedia; page.dc.html's own script calls it
// for theme detection. No real OS preference exists in this environment,
// so this reports "no light preference" -- the same "dark" fallback the
// client itself uses before it ever reads a real one.
function installMatchMediaShim(window) {
  window.matchMedia = function () {
    return {
      matches: false,
      media: "",
      addEventListener() {},
      removeEventListener() {},
      addListener() {},
      removeListener() {},
    };
  };
}

// Boots a fresh, independent DC runtime instance against `html`, exactly
// the mechanics scripts/ssr-render.js and tests/site/verify-ssr.js both
// need: same local-file interception, same fetch/matchMedia shims, same
// fake https:// origin (real browsers, and jsdom, treat file:// as an
// opaque origin, which breaks page.dc.html's synchronous localStorage
// read during initial state init -- see ssr-render.js's header comment).
function bootDom(html, { url, buildDir }) {
  const dom = new JSDOM(html, {
    url,
    runScripts: "dangerously",
    pretendToBeVisual: true,
    resources: { interceptors: [makeInterceptor(buildDir)] },
    beforeParse(window) {
      installFetchShim(window, buildDir);
      installMatchMediaShim(window);
      installReact(window);
    },
  });
  return dom;
}

// Polls `document.getElementById(id)` until its innerHTML is present and
// unchanged for `stableTicks` consecutive polls, or rejects on timeout.
// Generalizes ssr-render.js's original settle-wait so verify-ssr.js can
// wait on a *different* id (the live #dc-root, not the SSR snapshot's
// #dc-root-ssr) with the same stability logic.
function waitForStableElement(window, id, opts = {}) {
  const pollMs = opts.pollMs || 50;
  const stableTicks = opts.stableTicks || 3;
  const timeoutMs = opts.timeoutMs || 20000;
  return new Promise((resolve, reject) => {
    const start = Date.now();
    let last = null;
    let ticks = 0;
    const tick = () => {
      const el = window.document.getElementById(id);
      const snapshot = el ? el.innerHTML : null;
      if (snapshot && snapshot === last) ticks++;
      else {
        ticks = 0;
        last = snapshot;
      }
      if (snapshot && ticks >= stableTicks) return resolve(el);
      if (Date.now() - start > timeoutMs) {
        if (!snapshot)
          return reject(
            new Error("#" + id + " never rendered within " + timeoutMs + "ms"),
          );
        console.warn(
          "[ssr-lib] settle timeout waiting on #" +
            id +
            " -- resolving best-effort",
        );
        return resolve(el);
      }
      setTimeout(tick, pollMs);
    };
    setTimeout(tick, pollMs);
  });
}

module.exports = {
  SSR_ORIGIN,
  REACT_CDN_URL,
  REACT_DOM_CDN_URL,
  REACT_SRI,
  REACT_DOM_SRI,
  MIME_BY_EXT,
  fileResponse,
  resolveLocal,
  makeInterceptor,
  restoreSri,
  installFetchShim,
  installMatchMediaShim,
  installReact,
  bootDom,
  waitForStableElement,
};
