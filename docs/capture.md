<!-- docs/capture.md — owned by vertex-order/kit. Edit here.
     Vendored elsewhere via sync.toml; don't edit the copy there. -->

# Capture cache

Saved web pages and API results, used as evidence for `sources/`.

- Lives outside every repo, not in git: `../_captures/` (override with
  `$CAPTURES_DIR`).
- One cache for all repos. The key is the **URL**; the lookup goes one way,
  URL → file. Never guess a URL from a file.
- Not a Wayback machine: one capture per URL. History is Wayback captures
  (each timestamp is its own URL) and wiki revision (`oldid`) URLs.

## The rule

- **Before any web or API fetch** (WebFetch, curl, MediaWiki API, Wayback,
  a parser's own download), run:
  `python3 -I -X utf8 scripts/capture.py lookup <url>`
  - `HIT <path>`: read that file. Do not fetch.
  - `BLOCKED <date>`: an earlier fetch failed (Cloudflare, 403, 429).
    Do not retry; use the user workflow below.
  - `WAYBACK <path>`: Wayback captures of the URL are cached; read one if it
    answers the question.
  - `MISS`: fetch, then store.
- **Store every fetch**, including failures:
  - `capture.py fetch <url> [--page N]`: lookup, then a polite GET (generic
    user agent, 5 s gap per host), stored. A 403/429/Cloudflare reply is
    recorded as `blocked`, so it is never repeated.
  - `capture.py save <url> --from FILE|- [--via webfetch|mw-api|script]
    [--kind api] [--page N] [--title T]`: store content got another way
    (WebFetch output, API JSON, one page of a paginated sub-script).
- Never fetch a page again only to re-parse it. Parse from the cached file;
  fix the parser, not the cache.
- **On a 403, 429, rate limit or anti-bot page, from any tool: stop.** Do
  not retry or try another tool. Run `capture.py request <url> --note
  "<reason>"`, give the user the clickable URL and ask them to save it into
  `_captures/_user/` (see "When a fetch fails").
- Do not hit a site harder to "finish" an audit. A ban would cost the whole
  project. Few requests, spaced, cached.

## When a fetch fails (user workflow)

1. `capture.py request <url> --note "<reason>"` queues it, records the failure
   as `blocked` (so no one retries, even if the failure came from WebFetch or
   curl) and prints what to tell the user.
2. Give the user the clickable URL and say: save the page into
   `_captures/_user/` (browser default filename is fine; keep any
   search-term or page-number prefix they add).
   - **Always present the URLs to save as a numbered list** (`1.`, `2.`, …),
     never bullets, one URL per item, each a clickable link, so the user can
     answer by number (e.g. "saved 1 and 3"). Add what to prefix when it
     matters (search term, page number) after the URL.
3. The user pastes the saved filename(s) back.
4. Run `capture.py ingest "<filename>"` (no arguments ingests the whole
   user folder). Do this every time a filename from `_user/` is pasted; do not
   wait to be told.
5. The file is moved, indexed and found by `lookup` from then on.

- `ingest` finds the URL in this order: `--url` → the page's own
  `saved from url=` / SingleFile header → a Wayback toolbar URL whose
  timestamp matches the filename → the single queued request → a queued
  request matched by words in the filename. Otherwise it stops and lists
  candidates; re-run with `--url <url>`.
- `canonical` / `og:url` inside a page are only suggestions: they drop
  search terms and page numbers.
- Saving tips for the user: Brave/Chrome "Save as" embeds the URL;
  Firefox does not (give the URL with the filename). The SingleFile
  extension writes one file with the URL and date in a header and no
  `_files` folder (shorter paths, fewer files).

## Layout

`_captures/<host>/<parent-path>/<file>`, plus an `_index.tsv` in every
folder holding files.

- `<host>`: lowercase, no `www.`. Wayback captures go under the archived
  URL's host.
- `<parent-path>`: the URL's folders above the last segment, joined with
  `~`, trailing `/` dropped. `store.xbox.com/en-US/Xbox-One/Games/FINAL-FANTASY-XV/<id>`
  → `store.xbox.com/en-US~Xbox-One~Games~FINAL-FANTASY-XV/`. A page directly
  under the host sits in the host folder. Capped at 60 characters (a hash
  suffix follows when cut).
- No language or region top level: the host or path already carries it
  (`square-enix-games.com/de_DE/`, `ja.wikipedia.org`). English and Japanese
  articles are different pages, not translations.
- File name: `<date>-[live-|api-][<query-tag>-]<title>.<ext>`
  - `<date>`: `YYYYMMDD` for the day saved, or the 14-digit Wayback
    timestamp.
  - `<query-tag>`: from the URL's query (`term=chocobo`, `p002` for page 2).
    A prefix the user typed (`2-`, `final fantasy-`) stays as part of the
    name; it is never parsed.
  - `<title>`: the browser's default name. Names are capped at 150 bytes and
    whole paths at 240 characters (Windows tools and zip fail beyond that).
    Illegal characters become `_`.
- A saved page and its `<name>_files/` folder are one unit; the script moves
  and renames them together and rewrites the references. Never rename one
  by hand.
- Same URL, different content (search, POST, JS pagination): add a
  `#cap:<what>` fragment to the URL, e.g. `https://x.com/list#cap:page=2`.
  The fragment is part of the lookup key; any other fragment is ignored.
  Used where the page's state is not in its address (Wii U software lists:
  `…/wiiu/2#cap:filter=wiiu_disc_all`; Rotten Tomatoes pages).
- A `note` of `url inferred` means the URL was derived (from the page's own
  links, its query echo, or the search term in the file name) and checked
  against at most one live fetch, not recorded when the page was saved.
  Treat it as likely, not proven.
- URL normalisation for lookup: `http`/`https` equal, `www.` dropped,
  query parameters sorted, `utm_*`/`fbclid`/`gclid` removed,
  percent-encoding unified, trailing `/` ignored.

### `_index.tsv`

Columns: `file`, `url`, `final_url` (after redirects), `accessed`,
`kind` (`live`/`wayback`/`api`), `via` (`user`/`curl`/`webfetch`/`mw-api`/`script`),
`status` (`ok`/`blocked`/`http404`/`error`), `sha1`, `note`.

- Readable in any editor; moves with the folder; no tool needed to read.
- The date in the file name backs up `accessed`. File times are not trusted.
- Duplicates: identical content (sha1) is dropped; different content is
  refused until `--replace`, which moves the old copy to `_trash/`.

### Other folders

- `_user/`: where the user drops saves; `_pending.tsv` lists queued URLs.
- `_unsorted/<old folder>/`: captures whose URL is not known (`url` =
  `unknown` in the index). They are still readable by path. Resolve one by
  re-saving through `ingest --url`, or by correcting its index row and
  moving it. Empty since the 2026-11 migration.
- `_trash/`: copies replaced by `--replace` and duplicate saves. Safe to
  delete; nothing reads it.
- `_tools/`: parsers for specific sites (Backloggd, Epic, GOG, IGDB, Square
  Enix lists, Xbox). Reuse them; fix a bug in the tool itself. They find
  their inputs through `legacy.py` (the old per-site folders, mapped via
  `_migration/map.tsv`); new captures are found with `capture.py lookup`.
- `_migration/`: the one-time move from `_reference/captures/` (`map.tsv`:
  old path → new path, read by `legacy.py`; `migrate.py`).
- `capture.py check` lists files not in an index, index rows without a file,
  asset folders without a page, and paths over 240 characters.

## Large and paginated pages

- Save each raw page once (`--page N`, or the site's own page numbers), then
  parse from the cached files with a sub-script. Do not re-fetch to parse.
- Parse with the site's script in `_tools/`; one-off throwaway parsers per
  audit are not wanted.
- Verify parser output against the saved page on a few items before writing
  to `sources/`.

## Wayback

- Index (CDX) query, plain text:
  `https://web.archive.org/cdx/search/cdx?url=<url or prefix*>&output=txt&fl=timestamp,statuscode,original&filter=statuscode:200`
  - `*` only at the end of the URL; no `*` is one exact URL.
  - `from=YYYYMMDD&to=YYYYMMDD` narrows. `collapse=timestamp:6` hides later
    captures: leave it off when looking for the last one. `collapse=urlkey`
    lists each URL once.
  - Status 200 is a page; 301/302/404 show none.
- Raw HTML: `https://web.archive.org/web/<timestamp>id_/<url>`; often gzip.
  A bare year as timestamp returns the nearest capture. Read titles and
  descriptions with a script, not by eye.
- Rate limit: about 35 quick requests, then 429, or the index says
  "Temporarily Offline"/504. Wait 4–8 s between requests; run few at a
  time; retry later instead of repeating. Record the failure
  (`capture.py save` / `fetch` note it) so it is not repeated.
- Live checks without Wayback: `https://itunes.apple.com/lookup?id=<id>&country=us`
  (`resultCount` 0 = off the store); a plain GET (404 = gone).
- App Store captures of 2023–2024 show an Apple "Connecting" splash that
  never resolves; the raw HTML (`id_`) still holds the text. Check each
  linked capture renders in a browser.
- "Last working capture": the last status-200 capture before removal whose
  raw HTML still shows the page's content, not just a 200 status. The user
  confirms it renders; if not, step to the next earlier capture.

## Captures versus sources

- Captures are temporary working copies; `sources/` stay self-contained.
- A sources line carries the URL and `accessed` date. Never a cache path;
  the URL is the join key.
- Search-result and API pages usually have no sources line (nothing
  actionable); the index still records them so they are not re-fetched.
- Record in `sources/` only what a capture proved, per `docs/sources.md`.
