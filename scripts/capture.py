#!/usr/bin/env python3
# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
"""URL -> capture cache. Check the cache before any web fetch; store every fetch.

The cache lives OUTSIDE the repos (not in git): `$CAPTURES_DIR`, default
`<repos parent>/_captures`. Layout, naming and workflow: docs/capture.md.

    capture.py lookup <url> [--all]            HIT / WAYBACK / BLOCKED / MISS
    capture.py fetch <url> [--page N] [--retry-blocked]
                                                lookup, then GET politely, store
    capture.py save <url> --from FILE|-        store content fetched another way
    capture.py request <url> [--note TEXT]     queue a URL for the user to save
    capture.py ingest [FILE...] [--url U]      file the user's _user/ saves
    capture.py check [--all]                   orphans, missing files, long paths

Run with `python3 -I -X utf8`. Stdlib only. One direction only: URL -> path.
Files are never mapped back to a URL by guessing; every stored file has an
`_index.tsv` row (file, url, final_url, accessed, kind, via, status, sha1, note).
"""

import argparse
import datetime
import hashlib
import html
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit

COLUMNS = ["file", "url", "final_url", "accessed", "kind", "via", "status", "sha1", "note"]
INDEX = "_index.tsv"
SPECIAL = {"_user", "_trash", "_tools", "_migration"}
MAX_NAME_BYTES = 150
MAX_PATH = 240
FOLDER_CAP = 60
ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
TRACKING = re.compile(r"^(utm_.*|fbclid|gclid|mc_cid|mc_eid|igshid)$", re.I)
WAYBACK = re.compile(r"^https?:/+(?:www\.)?web\.archive\.org/web/(\d+)([a-z]{2}_)?/+(.*)$", re.I | re.S)
USER_AGENT = "Mozilla/5.0 (compatible; capture-cache/1.0)"
THROTTLE_SECONDS = 5


def root_dir():
    env = os.environ.get("CAPTURES_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent.parent / "_captures"


def today():
    return datetime.date.today().isoformat()


# ---- URL normalisation -------------------------------------------------


class Norm:
    """A normalised URL. `key` is the lookup identity."""

    def __init__(self, key, host, segs, query, ts=None, inner=None):
        self.key = key
        self.host = host
        self.segs = segs
        self.query = query
        self.ts = ts  # wayback timestamp, else None
        self.inner = inner  # wayback: Norm of the archived URL

    @property
    def place(self):
        """The Norm that decides folder: the archived URL for wayback."""
        return self.inner or self


def norm_url(url):
    url = url.strip()
    m = WAYBACK.match(url)
    if m:
        ts, _, rest = m.groups()
        if not re.match(r"^https?:", rest, re.I):
            rest = "http://" + rest
        rest = re.sub(r"^(https?:)/+", r"\1//", rest, flags=re.I)
        inner = norm_url(rest)
        return Norm(f"wayback:{ts}:{inner.key}", "web.archive.org", [], [], ts, inner)
    u = urlsplit(url)
    host = (u.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if u.port and u.port not in (80, 443):
        host += f":{u.port}"
    path = unquote(u.path)
    path = re.sub(r"/{2,}", "/", path).rstrip("/")
    query = sorted(
        (k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if not TRACKING.match(k)
    )
    key = host + path
    if query:
        key += "?" + urlencode(query)
    if u.fragment.startswith("cap:"):  # explicit disambiguator, see docs/capture.md
        key += "#" + u.fragment
    segs = [s for s in path.split("/") if s]
    return Norm(key, host, segs, query)


def safe(name):
    name = ILLEGAL.sub("_", name).strip(" .")
    return name or "_"


def host_dir(host):
    return safe(host.replace(":", "_"))


def folder_name(segs):
    """Parent path of the last segment, joined with ~, capped."""
    parent = "~".join(safe(s) for s in segs[:-1])
    if len(parent) > FOLDER_CAP:
        parent = parent[: FOLDER_CAP - 7] + "~" + hashlib.sha1(parent.encode()).hexdigest()[:6]
    return parent


def dest_dir(norm, root):
    p = norm.place
    d = root / host_dir(p.host)
    f = folder_name(p.segs)
    return d / f if f else d


def trim_bytes(text, limit):
    while len(text.encode("utf-8")) > limit:
        text = text[:-1]
    return text


def build_name(norm, accessed, kind, ext, title=None, page=None, via=None):
    """<date>-[live-|api-][<query-tag>-]<title>.<ext>"""
    p = norm.place
    title = title or (os.path.splitext(p.segs[-1])[0] if p.segs else "index")
    tag = "-".join(f"{k}={v}" for k, v in p.query)
    if page is not None:
        tag = (tag + "-" if tag else "") + f"p{int(page):03d}"
    if norm.ts:
        prefix = norm.ts + "-"
    else:
        prefix = accessed.replace("-", "") + "-" + {"live": "live-", "api": "api-"}.get(kind, "")
    stem = safe(prefix + (tag + "-" if tag else "") + title)
    stem = trim_bytes(stem, MAX_NAME_BYTES - len(ext) - 8)
    return stem + ext


def unique_path(directory, name):
    path = directory / name
    base, ext = os.path.splitext(name)
    n = 2
    while path.exists():
        path = directory / f"{base}~{n}{ext}"
        n += 1
    return path


# ---- index -------------------------------------------------------------


def clean(v):
    return re.sub(r"[\t\r\n]+", " ", str(v)).strip()


def read_index(directory):
    path = directory / INDEX
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        cells = line.split("\t")
        cells += [""] * (len(COLUMNS) - len(cells))
        rows.append(dict(zip(COLUMNS, cells)))
    return rows


def write_index(directory, rows):
    directory.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(COLUMNS)] + ["\t".join(clean(r.get(c, "")) for c in COLUMNS) for r in rows]
    with with_lock(directory):
        (directory / INDEX).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


class with_lock:
    """Tiny lock file so parallel AI runs don't interleave index writes."""

    def __init__(self, directory):
        self.path = directory / (INDEX + ".lock")

    def __enter__(self):
        for _ in range(100):
            try:
                os.close(os.open(self.path, os.O_CREAT | os.O_EXCL))
                return self
            except FileExistsError:
                time.sleep(0.1)
        self.path.unlink(missing_ok=True)  # stale
        return self.__enter__()

    def __exit__(self, *_):
        self.path.unlink(missing_ok=True)


def append_row(directory, row):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / INDEX
    with with_lock(directory):
        new = not path.exists()
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            if new:
                f.write("\t".join(COLUMNS) + "\n")
            f.write("\t".join(clean(row.get(c, "")) for c in COLUMNS) + "\n")


def walk_dirs(top):
    """Directories under top, skipping browser asset folders and housekeeping."""
    for dp, dns, _ in os.walk(top):
        dns[:] = [d for d in dns if not d.endswith("_files") and d not in SPECIAL]
        yield Path(dp)


def rows_for_host(host, root):
    hd = root / host_dir(host)
    if not hd.is_dir():
        return
    for d in walk_dirs(hd):
        for row in read_index(d):
            yield d, row


# ---- lookup ------------------------------------------------------------


def find(url, root):
    """-> (hits, wayback, blocked) for url."""
    n = norm_url(url)
    host = n.place.host
    hits, wb, blocked = [], [], []
    for d, row in rows_for_host(host, root):
        if not row["url"] or row["url"] == "unknown":
            continue
        rn = norm_url(row["url"])
        fn = norm_url(row["final_url"]) if row["final_url"] else None
        if row["status"] == "ok" or not row["status"]:
            if rn.key == n.key or (fn and fn.key == n.key):
                hits.append((d, row))
            elif not n.ts and rn.ts and rn.inner.key == n.key:
                wb.append((d, row))
            elif n.ts and rn.ts and rn.inner.key == n.inner.key:
                wb.append((d, row))
        elif rn.key == n.key:
            blocked.append((d, row))
    return n, hits, wb, blocked


def cmd_lookup(args):
    root = root_dir()
    n, hits, wb, blocked = find(args.url, root)
    code = 1
    for d, row in hits:
        print(f"HIT {d / row['file']} ({row['kind']} {row['accessed']} via {row['via']})")
        code = 0
    for d, row in blocked:
        print(f"BLOCKED {row['accessed']} {row['note']} — do not refetch; ask the user to save it")
        code = 0 if code == 0 else 3
    if args.all or not hits:
        for d, row in sorted(wb, key=lambda x: x[1]["file"]):
            print(f"WAYBACK {d / row['file']} ({row['url']})")
    if code == 1:
        print(f"MISS -> would save under {dest_dir(n, root)}")
    return code


# ---- storing -----------------------------------------------------------


def sha1_of(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rename_unit(src, new_stem):
    """Rename an .htm/.html (plus its <stem>_files folder) and fix references."""
    src = Path(src)
    old_stem = src.stem
    dst = src.with_name(new_stem + src.suffix)
    if dst == src:
        return src
    assets = src.with_name(old_stem + "_files")
    src.rename(dst)
    if assets.is_dir():
        assets.rename(dst.with_name(new_stem + "_files"))
        data = dst.read_bytes()
        o, nw = old_stem + "_files", new_stem + "_files"
        variants = {
            o: nw,
            quote(o): quote(nw),
            quote(o, safe="/:@!$&'()*+,;="): quote(nw, safe="/:@!$&'()*+,;="),
            html.escape(o): html.escape(nw),
        }
        for a, b in variants.items():
            data = data.replace(a.encode("utf-8"), b.encode("utf-8"))
        dst.write_bytes(data)
    return dst


def move_unit(src, dst_dir, name, copy=False):
    """Move (or copy) a file with its paired _files folder; renames when name differs."""
    src = Path(src)
    dst_dir.mkdir(parents=True, exist_ok=True)
    target = unique_path(dst_dir, name)
    assets = src.with_name(src.stem + "_files")
    if copy:
        shutil.copy2(src, target)
        return target
    shutil.move(str(src), str(target))
    if assets.is_dir() and src.suffix.lower() in (".htm", ".html"):
        want = target.with_name(target.stem + "_files")
        shutil.move(str(assets), str(want))
        if target.stem != src.stem:
            data = target.read_bytes()
            o, nw = src.stem + "_files", target.stem + "_files"
            for a, b in {
                o: nw,
                quote(o): quote(nw),
                quote(o, safe="/:@!$&'()*+,;="): quote(nw, safe="/:@!$&'()*+,;="),
                html.escape(o): html.escape(nw),
            }.items():
                data = data.replace(a.encode("utf-8"), b.encode("utf-8"))
            target.write_bytes(data)
    return target


def too_long(path):
    return len(str(path)) > MAX_PATH


def store(url, source, *, accessed=None, kind=None, via="script", final_url="", status="ok",
          note="", title=None, page=None, ext=None, replace=False, copy=False):
    """File `source` under the cache for `url`. Returns (path|None, message)."""
    root = root_dir()
    n = norm_url(url)
    kind = kind or ("wayback" if n.ts else "live")
    accessed = accessed or today()
    ext = ext or Path(source).suffix or ".html"
    d = dest_dir(n, root)
    digest = sha1_of(source)
    name = build_name(n, accessed, kind, ext, title, page, via)
    _, hits, _, _ = find(url, root)
    for hd, row in hits:
        if row["sha1"] == digest:
            return hd / row["file"], "DUPLICATE (identical content already cached)"
        if not replace:
            return None, (
                f"EXISTS {hd / row['file']} differs ({row['accessed']}); "
                "use --replace to keep the new copy (old goes to _trash/)"
            )
        trash = root / "_trash"
        trash.mkdir(exist_ok=True)
        old = hd / row["file"]
        if old.exists():
            move_unit(old, trash, f"{today()}-{old.name}")
        write_index(hd, [r for r in read_index(hd) if r["file"] != row["file"]])
    target = move_unit(source, d, name, copy=copy)
    if too_long(target):
        print(f"WARNING path over {MAX_PATH} chars: {target}", file=sys.stderr)
    append_row(d, dict(file=target.name, url=url, final_url=final_url, accessed=accessed,
                       kind=kind, via=via, status=status, sha1=digest, note=note))
    return target, f"STORED {target}"


def record_blocked(url, via, note, status="blocked"):
    root = root_dir()
    n = norm_url(url)
    append_row(dest_dir(n, root), dict(file="-", url=url, accessed=today(),
                                        kind="live", via=via, status=status, note=note))


# ---- fetch / save ------------------------------------------------------


def throttle(host):
    root = root_dir()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "_throttle.tsv"
    last = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            h, _, t = line.partition("\t")
            try:
                last[h] = float(t)
            except ValueError:
                pass
    wait = last.get(host, 0) + THROTTLE_SECONDS - time.time()
    if wait > 0:
        time.sleep(wait)
    last[host] = time.time()
    path.write_text("".join(f"{h}\t{t}\n" for h, t in last.items()), encoding="utf-8")


BLOCK_MARKERS = (b"Just a moment...", b"cf-chl", b"Attention Required! | Cloudflare",
                 b"Access Denied", b"are you a robot", b"captcha")


def cmd_fetch(args):
    root = root_dir()
    n, hits, wb, blocked = find(args.url, root)
    if args.page is None and hits:
        print(f"HIT {hits[0][0] / hits[0][1]['file']} — already cached, not fetching")
        return 0
    if blocked and not args.retry_blocked:
        print(f"BLOCKED earlier ({blocked[0][1]['accessed']}): not fetching. "
              "Run `request` so the user saves it, or pass --retry-blocked.")
        return 3
    throttle(n.place.host)
    req = urllib.request.Request(args.url, headers={
        "User-Agent": USER_AGENT, "Accept-Encoding": "identity",
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"})
    final, ctype, code = args.url, "", 0
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body, final, ctype, code = r.read(), r.geturl(), r.headers.get("Content-Type", ""), r.status
    except urllib.error.HTTPError as e:
        body, final, ctype, code = e.read(), e.url or args.url, e.headers.get("Content-Type", ""), e.code
    except (urllib.error.URLError, TimeoutError) as e:
        record_blocked(args.url, "script", f"network error: {e}", "error")
        print(f"ERROR {e} (recorded; not retried automatically)")
        return 2
    if code in (403, 429, 503) or (code != 200 and any(m in body[:20000] for m in BLOCK_MARKERS)):
        record_blocked(args.url, "script", f"http {code}")
        print(f"BLOCKED http {code}. Recorded. Next: `capture.py request {args.url}` and ask the user to save it.")
        return 3
    if code >= 400:
        record_blocked(args.url, "script", f"http {code}", f"http{code}")
        print(f"HTTP {code} recorded; no file stored.")
        return 2
    ext = ".json" if "json" in ctype else ".xml" if "xml" in ctype else ".txt" if "text/plain" in ctype else ".html"
    tmp = root / "_user" / f".fetch-{os.getpid()}{ext}"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(body)
    kind = "api" if ext == ".json" else None
    path, msg = store(args.url, tmp, kind=kind, via="curl", final_url=final if final != args.url else "",
                      page=args.page, ext=ext, replace=args.replace)
    tmp.unlink(missing_ok=True)
    print(msg)
    return 0 if path else 2


def cmd_save(args):
    root = root_dir()
    (root / "_user").mkdir(parents=True, exist_ok=True)
    if args.src == "-":
        tmp = root / "_user" / f".save-{os.getpid()}{args.ext}"
        tmp.write_bytes(sys.stdin.buffer.read())
        src, copy = tmp, False
    else:
        src, copy = Path(args.src), True
    path, msg = store(args.url, src, via=args.via, kind=args.kind, note=args.note, title=args.title,
                      page=args.page, ext=args.ext if args.src == "-" else None,
                      replace=args.replace, copy=copy)
    print(msg)
    return 0 if path else 2


# ---- request / ingest --------------------------------------------------


def pending_path():
    return root_dir() / "_user" / "_pending.tsv"


def read_pending():
    p = pending_path()
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        c = line.split("\t")
        if c and c[0]:
            out.append({"url": c[0], "requested": c[1] if len(c) > 1 else "", "note": c[2] if len(c) > 2 else ""})
    return out


def write_pending(rows):
    p = pending_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(f"{clean(r['url'])}\t{r['requested']}\t{clean(r['note'])}\n" for r in rows),
                 encoding="utf-8", newline="\n")


def cmd_request(args):
    _, hits, _, blocked = find(args.url, root_dir())
    if hits:
        d, row = hits[0]
        print(f"HIT {d / row['file']}: already cached, no need to ask the user to save it.")
        return 0
    if not blocked:  # a fetch failed outside `fetch` (WebFetch, curl): mark it so nobody retries
        record_blocked(args.url, "webfetch", args.note or "fetch failed (blocked or rate limited)")
    rows = read_pending()
    if not any(norm_url(r["url"]).key == norm_url(args.url).key for r in rows):
        rows.append({"url": args.url, "requested": today(), "note": args.note or ""})
        write_pending(rows)
    print(f"Ask the user to open: {args.url}\n"
          f"Save the page into {root_dir() / '_user'} (browser default filename is fine; "
          "SingleFile or Save-as complete both work), then paste the saved filename back.")
    return 0


HINT_BYTES = 400_000
NOISE_HOST = re.compile(r"//(fonts\.|[^/]*(doubleclick|googleads|google-analytics|googletagmanager|gstatic)\.|connect\.facebook|platform\.twitter)", re.I)
ASSET_EXT = re.compile(r"\.(js|css|png|jpe?g|gif|svg|ico|webp|woff2?|ttf|json)(\?|$)", re.I)


def extract_hints(path):
    """URLs a saved page says it came from. -> [(source, url)]; verification only."""
    try:
        text = Path(path).read_bytes()[:HINT_BYTES].decode("utf-8", "replace")
    except OSError:
        return []
    out = []
    m = re.search(r"saved from url=\(\d+\)(\S+)", text)
    if m:
        out.append(("saved-from", m.group(1)))
    m = re.search(r"Page saved with SingleFile\s+url:\s*(\S+)", text)
    if m:
        out.append(("singlefile", m.group(1)))
    ts = re.match(r"(\d{14})-", Path(path).name)
    pat = (re.escape(ts.group(1)) if ts else r"\d{14}") + r"(?:[a-z]{2}_)?"
    counts = {}
    for m in re.finditer(r"web\.archive\.org/web/(" + pat + r")/(https?:/+[^\"'\s<>)]+)", text):
        u = m.group(2)
        if ASSET_EXT.search(u) or NOISE_HOST.search(u) or re.search(r"/(rss|feed)", u):
            continue
        u = f"https://web.archive.org/web/{m.group(1)[:14]}/{u}"
        counts[u] = counts.get(u, 0) + 1
    for u in sorted(counts, key=lambda k: -counts[k])[:3]:
        out.append(("wayback", u))
    for rx, src in ((r"<link[^>]+rel=[\"']canonical[\"'][^>]*href=[\"']([^\"']+)", "canonical"),
                    (r"<link[^>]+href=[\"']([^\"']+)[\"'][^>]*rel=[\"']canonical[\"']", "canonical"),
                    (r"<meta[^>]+property=[\"']og:url[\"'][^>]*content=[\"']([^\"']+)", "og:url"),
                    (r"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]*property=[\"']og:url[\"']", "og:url")):
        m = re.search(rx, text, re.I)
        if m and not any(s == src for s, _ in out):
            out.append((src, html.unescape(m.group(1))))
    return out


def inbox_files(root):
    inbox = root / "_user"
    names = []
    for p in sorted(inbox.iterdir()) if inbox.is_dir() else []:
        if p.name.startswith(".") or p.name == "_pending.tsv" or p.is_dir() and p.name.endswith("_files"):
            continue
        if p.is_file():
            names.append(p)
    return names


def resolve_user_file(root, name):
    p = Path(name)
    if p.is_file():
        return p
    cand = root / "_user" / name
    if cand.is_file():
        return cand
    hits = [q for q in inbox_files(root) if name.lower() in q.name.lower()]
    return hits[0] if len(hits) == 1 else None


def pick_url(file, pending, given):
    """-> (url|None, how, candidates)."""
    if given:
        return given, "given", []
    hints = extract_hints(file)
    for src in ("saved-from", "singlefile", "wayback"):
        for s, u in hints:
            if s == src:
                return u, src, []
    if len(pending) == 1:
        return pending[0]["url"], "pending", []
    cands = [r["url"] for r in pending]
    toks = [t for t in re.split(r"\W+", file.stem.lower()) if len(t) > 2]
    scored = [(sum(t in u.lower() for t in toks), u) for u in cands]
    if scored and max(scored)[0] > 0 and [s for s, _ in scored].count(max(scored)[0]) == 1:
        return max(scored)[1], "pending-match", []
    return None, "unknown", cands + [u for s, u in hints]


def cmd_ingest(args):
    root = root_dir()
    files = [resolve_user_file(root, f) for f in args.files] if args.files else inbox_files(root)
    if args.files and None in files:
        bad = [f for f, p in zip(args.files, files) if p is None]
        print(f"NOT FOUND in {root / '_user'}: {', '.join(bad)}")
        return 2
    pending = read_pending()
    status = 0
    for f in files:
        url, how, cands = pick_url(f, pending, args.url if len(files) == 1 else None)
        if not url:
            print(f"UNSURE {f.name}: no URL. Candidates: {cands or 'none'}. "
                  f"Re-run with --url <url> (or `request` first).")
            status = 2
            continue
        accessed = datetime.date.fromtimestamp(f.stat().st_mtime).isoformat()
        m = re.match(r"(\d{4})(\d{2})(\d{2})-live-", f.name)
        if m:
            accessed = "-".join(m.groups())
        stem_title = re.sub(r"^(\d{14}|\d{8}-live)-", "", f.stem)
        n = norm_url(url)
        kind = "wayback" if n.ts else "api" if f.suffix.lower() == ".json" else "live"
        # keep the user's own prefixes ("2-", "final fantasy-") and title as the title part
        path, msg = store(url, f, accessed=accessed, kind=kind, via="user", note=f"url from {how}",
                          title=stem_title, ext=f.suffix.lower() or ".html", replace=args.replace)
        print(f"{msg}  url={url} (from {how}) accessed={accessed}")
        if path is None:
            status = 2
        else:
            pending = [r for r in pending if norm_url(r["url"]).key != n.key]
            write_pending(pending)
    return status


# ---- check -------------------------------------------------------------


def cmd_check(args):
    root = root_dir()
    problems = []
    for d in walk_dirs(root):
        if d == root or any(p in SPECIAL for p in d.relative_to(root).parts):
            continue
        rows = read_index(d)
        indexed = {r["file"] for r in rows}
        for r in rows:
            if r["file"] not in ("-", "") and not (d / r["file"]).exists():
                problems.append(f"index row without file: {d / r['file']}")
        for p in d.iterdir():
            if p.name in (INDEX, INDEX + ".lock"):
                continue
            if p.is_file() and p.name not in indexed:
                problems.append(f"file not in index: {p}")
            if p.is_dir() and p.name.endswith("_files") and not any(
                    (d / (p.name[:-6] + e)).exists() for e in (".htm", ".html")):
                problems.append(f"asset folder without page: {p}")
            if too_long(p):
                problems.append(f"path over {MAX_PATH}: {p}")
    for line in problems if args.all else problems[:40]:
        print(line)
    print(f"{len(problems)} problem(s)" + ("" if args.all or len(problems) <= 40 else " (use --all)"))
    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("lookup"); p.add_argument("url"); p.add_argument("--all", action="store_true")
    p.set_defaults(fn=cmd_lookup)
    p = sub.add_parser("fetch"); p.add_argument("url"); p.add_argument("--page", type=int)
    p.add_argument("--retry-blocked", action="store_true"); p.add_argument("--replace", action="store_true")
    p.set_defaults(fn=cmd_fetch)
    p = sub.add_parser("save"); p.add_argument("url"); p.add_argument("--from", dest="src", required=True)
    p.add_argument("--via", default="webfetch"); p.add_argument("--kind", choices=["live", "api", "wayback"])
    p.add_argument("--note", default=""); p.add_argument("--title"); p.add_argument("--page", type=int)
    p.add_argument("--ext", default=".html"); p.add_argument("--replace", action="store_true")
    p.set_defaults(fn=cmd_save)
    p = sub.add_parser("request"); p.add_argument("url"); p.add_argument("--note")
    p.set_defaults(fn=cmd_request)
    p = sub.add_parser("ingest"); p.add_argument("files", nargs="*"); p.add_argument("--url")
    p.add_argument("--replace", action="store_true"); p.set_defaults(fn=cmd_ingest)
    p = sub.add_parser("check"); p.add_argument("--all", action="store_true"); p.set_defaults(fn=cmd_check)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
