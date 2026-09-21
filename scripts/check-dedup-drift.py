#!/usr/bin/env python3
# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
"""Flag drift between duplicate/cross-listed media entries in site/data/, and
duplicate stable entry/pilcrow keys.

## Dedup drift

A release can be legitimately hand-cross-listed in two series (e.g. a
Picture Book tie-in also listed under its parent game's series). Only each
media[] slot's *primary* release (`releases[0]`) is ever cross-listed this
way -- site/page.dc.html dedupes these at render time (`dupGroups`, from
each slot's primary) so checking one checkbox checks both. That relies on
the two hand-typed copies staying in sync -- nothing enforces it. This
script finds every group of primary releases sharing page.dc.html's dedupe
key (title|subtitleKey|titleDate) and fails if their
description/tags/ratings/length/platforms/languages disagree. It
intentionally does not look inside releases[1:] or versions[] (inline-or/
other-version sub-entries) -- only each slot's primary release.

## Entry-key collisions

site/page.dc.html derives a stable pilcrow/checked-state key per media[]
slot (`entrySlug`/`subSlug`/`withDedupeSuffix`) from its primary release's
`title` + titleDate's year (or an explicit `id:`), and for a versions[]
sub-entry (on any release, not just the primary) from its own
`subtitle`/`title` + year, or (for a bare inheriting sub-entry with
neither) its *own release's* `title` + year. That derivation has its own
last-resort dedupe suffix (`-2`, `-3`...) so a collision never breaks
rendering outright, but a suffixed key is a code smell -- it means two
different things now render under near-identical anchors, e.g.
`#entry-VII-remaster-2012` and `...-2012-2`, and links to the second are
one accidental data reorder away from drifting back to the first. This
script mirrors that same derivation in Python and fails on any collision
(slot-level, or within one release's own versions[]), and on any versions[]
sub-entry with no derivable label at all -- authors should either fix the
underlying `subtitle`/`title` or add an explicit `id:` rather than ship the
review depending on the fallback. A release[1:] (inline-or) itself never
needs checking here -- it always renders at a fixed positional anchor
(`-or`/`-or-2`/...), never a derived slug.

## Title/year redundancy

The year shown next to `title` at render time is composed separately by
`composeDateLabel()` from `titleDate`, never baked into `title` itself (see
the list repos' docs/sources.md for the fuller writeup of why). If someone
also types the year into `title` (redundant with what `titleDate` already
carries), the displayed title ends up with a doubled or confusingly
adjacent year, e.g. `Final Fantasy I (1987) (1987)`. This check flags any
primary release whose `title` contains `(<same year as titleDate>)`
anywhere in the string (not just trailing) -- fix by removing that
redundant year from `title`, not from `titleDate`.

site/data/index.js and series-*.js are plain JS object literals (unquoted
keys, single-quoted strings, trailing commas) -- not valid JSON -- so this
shares scripts/js_literal.py's hand-rolled parser for the subset actually
in use (no template literals, no spread/computed keys).

Runs unchanged in kit (checks its own fixture data) and every list repo.

No external deps. Run: python3 scripts/check-dedup-drift.py
"""

import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from js_literal import ParseError
from js_literal import parse_value_after as _parse_value_after

SITE = Path(__file__).resolve().parent.parent / "site"
DATA = SITE / "data"


# ---------------------------------------------------------------------------
# Data loading. Deliberately doesn't depend on the `window.__xxSeriesReg`
# registry name -- that's franchise-specific and differs per list repo.
# ---------------------------------------------------------------------------

_SERIES_ORDER_RE = re.compile(r"\bSERIES_ORDER\s*=\s*")
_ASSIGN_VALUE_RE = re.compile(r"=\s*(?=[{\[])")


def load_series_order():
    text = (DATA / "index.js").read_text(encoding="utf-8")
    order = _parse_value_after(text, _SERIES_ORDER_RE)
    if not isinstance(order, list) or not all(isinstance(s, str) for s in order):
        raise ParseError("site/data/index.js: SERIES_ORDER is not a list of strings")
    return order


def load_series(slug):
    path = DATA / f"series-{slug}.js"
    if not path.exists():
        raise ParseError(f"{path.name}: listed in SERIES_ORDER but file is missing")
    return _parse_value_after(path.read_text(encoding="utf-8"), _ASSIGN_VALUE_RE)


# ---------------------------------------------------------------------------
# Dedupe key -- mirrors site/page.dc.html's raw/pre-transform dupGroups
# construction (~line 772-773) exactly, including its truthiness asymmetry:
# `g.bylineParts ? ... : ...` is a bare-truthy check in JS, so an empty
# bylineParts array still takes that branch; `g.tags && g.tags.length` needs
# a non-empty array, so an empty tags array falls through to ''.
# ---------------------------------------------------------------------------


def title_date_key(d):
    """Mirrors titleDateKey(): full-precision string for a titleDate
    value -- itself if already a string, the year as a string for a plain
    year number, or a {start,end} range's start year."""
    if d is None:
        return ""
    if isinstance(d, dict):
        return str(d["start"])
    return str(d)


def title_date_year(d):
    """Mirrors titleDateYear(): title_date_key() sliced to its year."""
    return title_date_key(d)[:4]


def primary_of(slot):
    """A media[] slot's primary release (releases[0]) -- the checkbox row,
    equivalent to the old flat games[] entry for every purpose this script
    cares about (dedupe/entry-key/title-year checks all only ever looked at
    the top-level entry, never extras/alt/alts, and that's unchanged: they
    still only look at releases[0], never releases[1:] or versions[])."""
    return slot["releases"][0]


def dedupe_key(release):
    byline_parts = release.get("bylineParts")
    if byline_parts is not None:
        subtitle_key = "".join((p.get("text") or "") for p in byline_parts)
    else:
        tags = release.get("tags")
        subtitle_key = " · ".join(tags) if tags else ""
    return f"{release.get('title', '')}|{subtitle_key}|{title_date_key(release.get('titleDate'))}"


# ---------------------------------------------------------------------------
# Comparison -- entry-level fields only, never extras/alt/alts. Some fields
# have two spellings depending on media type (page.dc.html:814-815, :976):
# game entries use lengthParts/platformGroups, book/video entries use the
# plain length/platforms strings.
# ---------------------------------------------------------------------------

COMPARED_FIELDS = {
    "description": ("description",),
    "tags": ("tags",),
    "ratings": ("ratings",),
    "length": ("length",),
    "platforms": ("platforms",),
    "languages": ("languages",),
}


def _run_text(part):
    if isinstance(part, dict):
        return part.get("text") or part.get("emText") or ""
    return part if isinstance(part, str) else ""


def normalize_description(desc):
    """A cross-listed entry's description legitimately differs from its
    sibling in exactly one place: the sentence naming which *other* series
    it's also found in ("Entry also found in our X series."). Rather than
    trying to recognize that cross-reference by matching series slugs/titles
    (fragile -- titles and slugs are both used interchangeably, and neither
    is available to a plain per-field comparison), drop any top-level
    paragraph/string mentioning "series" outright before comparing -- it's
    expected to differ by construction, so it's never real drift."""
    if not isinstance(desc, list):
        return desc
    out = []
    for item in desc:
        if isinstance(item, list):
            text = "".join(_run_text(p) for p in item)
            if "series" in text.lower():
                continue
            out.append(item)
        elif isinstance(item, str):
            if "series" in item.lower():
                continue
            out.append(item)
        else:
            out.append(item)
    return out


def field_snapshot(game, raw_keys, label):
    if label == "description":
        return tuple(normalize_description(game.get(k)) for k in raw_keys)
    return tuple(game.get(k) for k in raw_keys)


def slugify_title(s):
    """Mirrors site/page.dc.html's slugifyTitle() exactly."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("'", "").replace("’", "")
    s = re.sub(r"[^A-Za-z0-9]+", "-", s)
    s = s.strip("-")
    return s.lower()


def entry_slug(release):
    """Mirrors entrySlug(): explicit id: wins, else title + release year
    (from titleDate)."""
    if release.get("id"):
        return release["id"]
    year = title_date_year(release.get("titleDate"))
    base = slugify_title(release.get("title") or "")
    return base + ("-" + year if year else "")


def sub_slug(node, parent):
    """Mirrors subSlug(): own subtitle + year if it has one, else own title
    + year if it has one (a cross-reference to a different entry), else the
    *parent* release's title + year (a bare inheriting sub-entry with no
    edition tag), else the legacy bare `label` field."""
    if node.get("id"):
        return node["id"]
    if node.get("subtitle"):
        yr = title_date_year(node.get("subtitleDate"))
        return slugify_title(node["subtitle"]) + (f"-{yr}" if yr else "")
    has_own = node.get("title") is not None
    title = node.get("title") if has_own else (parent.get("title") if parent else None)
    title_date = (
        node.get("titleDate")
        if has_own
        else (parent.get("titleDate") if parent else None)
    )
    if title:
        yr = title_date_year(title_date)
        return slugify_title(title) + (f"-{yr}" if yr else "")
    return slugify_title(node.get("label") or "")


def with_dedupe_suffix(base_keys):
    """Mirrors withDedupeSuffix(): -2, -3... on repeats, in order."""
    seen = {}
    out = []
    for k in base_keys:
        n = seen.get(k, 0) + 1
        seen[k] = n
        out.append(k if n == 1 else f"{k}-{n}")
    return out


def check_entry_keys(order):
    """Fail on any derived pilcrow/status key collision (slot-level, from
    each media[] slot's primary release; or within one release's own
    versions[]), and on any versions[] sub-entry with no derivable label at
    all. A release[1:] (inline-or) itself always uses a fixed positional
    anchor ('-or'/'-or-2'/...), never a derived slug, so it can't collide
    the way a versions[] entry can -- only each release's own versions[]
    needs checking, for every release in the slot, not just the primary."""
    findings = []
    for slug in order:
        series = load_series(slug)
        media = series.get("media", [])
        primaries = [primary_of(m) for m in media]
        entry_keys = with_dedupe_suffix([entry_slug(p) for p in primaries])
        seen_entries = {}
        for i, key in enumerate(entry_keys):
            seen_entries.setdefault(key, []).append(i)
        for key, idxs in seen_entries.items():
            if len(idxs) > 1:
                findings.append(
                    f"series-{slug}.js: duplicate entry key '{slug}-{key}' at media{idxs} "
                    "-- add an explicit id: to one of them"
                )

        for i, slot in enumerate(media):
            releases = slot.get("releases", [])
            for ri, release in enumerate(releases):
                versions = release.get("versions")
                if not versions:
                    continue
                where = f"media[{i}].releases[{ri}]"
                base = [sub_slug(n, release) for n in versions]
                sub_keys = with_dedupe_suffix(base)
                seen_sub = {}
                for j, key in enumerate(sub_keys):
                    if not base[j]:
                        findings.append(
                            f"series-{slug}.js {where}.versions[{j}]: no derivable label for "
                            "its pilcrow key -- add a subtitle/title (or a parent title to "
                            "inherit) or an explicit id:"
                        )
                    seen_sub.setdefault(key, []).append(j)
                for key, idxs in seen_sub.items():
                    if len(idxs) > 1:
                        findings.append(
                            f"series-{slug}.js {where}.versions: duplicate derived key '{key}' "
                            f"at indices {idxs} -- add an explicit id: to one of them"
                        )
    return findings


def check_title_year_redundancy(entries):
    """Flag any entry whose title contains "(<year>)" matching its own
    title_date year -- see the module docstring's "Title/year redundancy"
    section. Checks for the year anywhere in title, not just trailing,
    since a legitimate edition suffix (e.g. "Remake (2018)") can sit after
    a redundant leading "(<title_date year>)"."""
    findings = []
    for slug, idx, game in entries:
        title = game.get("title")
        year = title_date_year(game.get("titleDate"))
        if title and year and f"({year})" in title:
            findings.append(
                f"series-{slug}.js media[{idx}]: title {title!r} redundantly "
                f"repeats its own titleDate year ({year}) -- remove it from "
                "title, composeDateLabel() already composes it for display"
            )
    return findings


def main():
    try:
        order = load_series_order()
    except FileNotFoundError:
        print("check-dedup-drift: no site/data/index.js, nothing to check")
        return 0
    except (ParseError, IndexError, ValueError) as e:
        print(
            f"check-dedup-drift: failed to parse site/data/index.js: {e}",
            file=sys.stderr,
        )
        return 1

    entries = []  # (slug, index, primary_release)
    try:
        for slug in order:
            series = load_series(slug)
            for idx, slot in enumerate(series.get("media", [])):
                entries.append((slug, idx, primary_of(slot)))
    except (ParseError, IndexError, ValueError) as e:
        print(f"check-dedup-drift: {e}", file=sys.stderr)
        return 1

    groups = {}
    for slug, idx, game in entries:
        groups.setdefault(dedupe_key(game), []).append((slug, idx, game))
    dup_groups = {k: v for k, v in groups.items() if len(v) > 1}

    findings = []
    for members in dup_groups.values():
        for label, raw_keys in COMPARED_FIELDS.items():
            snapshots = [field_snapshot(g, raw_keys, label) for _, _, g in members]
            if any(snap != snapshots[0] for snap in snapshots[1:]):
                where = ", ".join(
                    f"series-{slug}.js media[{idx}]" for slug, idx, _ in members
                )
                entry_title = members[0][2].get("title", "?")
                findings.append(f"  {entry_title!r} ({where}): {label} differs")

    try:
        key_findings = check_entry_keys(order)
    except (ParseError, IndexError, ValueError) as e:
        print(f"check-dedup-drift: {e}", file=sys.stderr)
        return 1

    year_findings = check_title_year_redundancy(entries)

    if findings or key_findings or year_findings:
        if findings:
            print(
                f"check-dedup-drift: {len(findings)} drift finding(s) across {len(dup_groups)} duplicate group(s):"
            )
            for finding in findings:
                print(finding)
            print(
                "Fix: reconcile the duplicate entries so description/tags/rating/length/platforms/languages match."
            )
        if key_findings:
            print(f"check-dedup-drift: {len(key_findings)} entry-key finding(s):")
            for finding in key_findings:
                print(f"  {finding}")
        if year_findings:
            print(
                f"check-dedup-drift: {len(year_findings)} title/year redundancy finding(s):"
            )
            for finding in year_findings:
                print(f"  {finding}")
        return 1

    print(
        f"check-dedup-drift: checked {len(dup_groups)} duplicate group(s) across {len(entries)} entries, "
        f"{len(order)} series' entry keys, and title/year redundancy, no drift"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
