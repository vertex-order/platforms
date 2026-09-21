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
// over the entry file.
//
// The client boot path (support.js's boot(), site/support.js:152-199) finds
// the entry file's <x-dc> element and *destructively* replaces it with a
// freshly created <div id="dc-root"> it then mounts React into
// (dc.replaceWith(hostEl), site/support.js:168) — so running that same
// boot() here, in-process, to produce the snapshot, consumes the one
// <x-dc> the file had. Naively serializing the post-boot DOM ships a file
// with no <x-dc> left in it at all: a real visitor's browser runs boot()
// again, parseDcDocument() finds no <x-dc> (site/support.js:27-28),
// returns null, and boot() silently no-ops — no React root ever mounts,
// no event handler ever attaches, forever. The page LOOKS complete (it's a
// real settled render) and throws nothing, so this shipped fully inert on
// every deploy since this script was added.
//
// The fix: keep a copy of the *original*, untouched <x-dc>...</x-dc> block
// (captured from `html` below, before jsdom ever parses/mutates it) and
// splice it back into the serialized output as a sibling placed right
// before the snapshot div — renamed from id="dc-root" to id="dc-root-ssr"
// so the client's real, fresh div doesn't collide with it. A visitor's
// browser now paints the id="dc-root-ssr" snapshot immediately (no blank
// flash — the original goal), then boot() finds the *real* <x-dc>, mounts
// a live React tree in a new div it creates itself, and a small inline
// script (appended below, output-only — never touches site/) removes the
// now-superseded snapshot once that live #dc-root shows up.
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

"use strict";

const fs = require("fs");
const path = require("path");
const {
  SSR_ORIGIN,
  bootDom,
  restoreSri,
  waitForStableElement,
} = require("./ssr-lib");

async function main() {
  const buildDir = process.argv[2];
  if (!buildDir) {
    console.error("usage: node scripts/ssr-render.js <build-dir> [entry-file]");
    process.exit(1);
  }
  const entryFile = process.argv[3] || "index.html";
  const entryPath = path.join(buildDir, entryFile);
  const html = fs.readFileSync(entryPath, "utf8");

  // Captured from the untouched source string, before jsdom (and boot())
  // ever sees it — see the <x-dc> consumption note above. Same open/close
  // matching support.js's own parseDcText() uses (site/support.js:41-43).
  const xDcOpenMatch = /<x-dc(?:\s[^>]*)?>/.exec(html);
  const xDcCloseIdx = html.lastIndexOf("</x-dc>");
  if (!xDcOpenMatch || xDcCloseIdx === -1) {
    throw new Error(
      entryPath +
        ": no <x-dc>...</x-dc> found — can't preserve it for re-mount",
    );
  }
  const originalXDcBlock = html.slice(
    xDcOpenMatch.index,
    xDcCloseIdx + "</x-dc>".length,
  );

  const dom = bootDom(html, {
    url: SSR_ORIGIN + "/" + entryFile,
    buildDir: path.resolve(buildDir),
  });
  const { window } = dom;
  window.addEventListener("error", (e) => {
    console.error("[ssr-render]", e.error || e.message);
  });

  // Not wrapped in try/finally: every error here already propagates to
  // main().catch() below and exits the process either way, so a `finally`
  // bought no real cleanup guarantee -- it only risked the classic
  // unsafe-finally bug, where the SNAPSHOT_MARKER throw a few lines down
  // would silently overwrite whatever real error waitForStableElement
  // threw (oxlint: no-unsafe-finally).
  await waitForStableElement(window, "dc-root");
  restoreSri(window.document);
  let out = "<!DOCTYPE html>\n" + window.document.documentElement.outerHTML;

  // Re-insert the original <x-dc> (see the top-of-file note) as a sibling
  // right before the settled snapshot, and rename the snapshot's id out
  // of #dc-root's way. There's exactly one id="dc-root" opening tag —
  // boot() creates it fresh each time it runs (site/support.js:167-168).
  const SNAPSHOT_MARKER = '<div id="dc-root">';
  if (!out.includes(SNAPSHOT_MARKER)) {
    throw new Error(
      entryPath +
        ': expected exactly one <div id="dc-root"> in the settled render',
    );
  }
  out = out.replace(
    SNAPSHOT_MARKER,
    originalXDcBlock + '\n<div id="dc-root-ssr">',
  );
  // Removes the now-superseded snapshot once the client's real boot() has
  // mounted its own live #dc-root over the <x-dc> above. Output-only —
  // never written to site/, so it has no effect on the dev/preview flow
  // (that HTML never runs through this script).
  const CLEANUP_SCRIPT =
    '<script>(function(){var s=document.getElementById("dc-root-ssr");if(!s)return;new MutationObserver(function(_,o){if(document.getElementById("dc-root")){s.remove();o.disconnect();}}).observe(document.body,{childList:true,subtree:true});})();</script>';
  out = out.replace("</body>", CLEANUP_SCRIPT + "</body>");

  // Elements the runtime builds by string-concatenating an absolute base
  // (e.g. data/index.js's dynamically-injected <script src> for each
  // series file, resolved against SSR_ORIGIN) bake that absolute URL into
  // the attribute value itself, not just the live resolution — strip it
  // back to relative so nothing in the shipped page ever points at this
  // build-only fake origin. Harmless either way once loaded (the client's
  // own boot re-runs and re-injects these fresh against the real origin),
  // but a leaked ssr-render.internal URL would otherwise sit in the page
  // as a guaranteed-failing request.
  out = out
    .split(SSR_ORIGIN + "/")
    .join("./")
    .split(SSR_ORIGIN)
    .join(".");
  fs.writeFileSync(entryPath, out);
  window.close();
  console.log("[ssr-render] wrote static render: " + entryPath);
}

main().catch((err) => {
  console.error("[ssr-render] failed:", err);
  process.exit(1);
});
