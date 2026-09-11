#!/usr/bin/env python3
# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
"""Second SVG trim pass: drop path subpaths that lie entirely outside the
viewBox.

Several icons are crops of larger artwork -- nintendo-switch.svg still
carries a full "NINTENDO SWITCH" wordmark ~70 units below its viewBox.
svgo (`just trim-svg` step 1) never tests geometry against the viewBox, so
that dead ink ships. This removes only subpaths whose bounding box -- taken
over every on-path point, every Bezier control point (convex-hull bound),
and exact arc extrema -- falls completely outside the viewBox. A subpath
that touches or crosses an edge is kept byte-for-byte.

Why this is pixel-safe: when an SVG renders as a replaced element (<img>)
or inline, the viewport clips to the viewBox, so offscreen ink is already
invisible. For fill, every subpath is implicitly closed, so a straight
fill-rule test ray from any on-canvas point crosses a fully-offscreen
closed loop an even number of times -- nonzero winding and even-odd parity
of on-canvas points are both unchanged. (Strokes and markers break that
argument, hence the bail list below.)

Bails on a whole file -- leaving it untouched -- when safety isn't provable:
  - any `transform=` anywhere
  - <use>/<clipPath>/<mask>/<pattern>/<marker>/<symbol>, or marker-* attrs
  - any real stroke (`stroke=` / `stroke:` other than none)
  - <svg> has no viewBox
  - an arc with a non-zero x-axis-rotation
  - a `d` attribute this parser can't fully consume

Run order: svgo -> this -> normalize-svg.py (all three are `just trim-svg`).
Conservative by construction; still, eyeball the diff.
"""
import math
import re
import sys
from pathlib import Path

NUMBER = re.compile(r"[+-]?(?:\d*\.\d+|\d+\.?)(?:[eE][+-]?\d+)?")
VIEWBOX = re.compile(r'viewBox\s*=\s*"([^"]+)"')
PATH_D = re.compile(r'(<path\b[^>]*?\bd\s*=\s*")([^"]*)(")')
BAIL = re.compile(
    r"transform\s*=|<use\b|<clipPath\b|<mask\b|<pattern\b|<marker\b|<symbol\b"
    r"|marker-(?:start|mid|end)\s*=|stroke\s*:\s*(?!none\b)[^;\"'\s]"
    r'|stroke\s*=\s*"(?!none")',
    re.IGNORECASE,
)


class ParseError(Exception):
    pass


def tokenize(d):
    """Yield 'cmd' letters and float numbers in document order."""
    i, n = 0, len(d)
    while i < n:
        c = d[i]
        if c in " ,\t\r\n":
            i += 1
            continue
        if c.isalpha():
            yield c
            i += 1
            continue
        m = NUMBER.match(d, i)
        if not m or m.end() == i:
            raise ParseError(f"stray {c!r} at {i}")
        yield float(m.group())
        i = m.end()


def arc_bbox(x0, y0, rx, ry, phi_deg, fa, fs, x, y):
    """Exact bbox of an SVG elliptical arc. Only phi==0 is supported;
    callers bail otherwise."""
    if phi_deg % 360 != 0:
        raise ParseError("arc x-axis-rotation != 0")
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0 or (x0, y0) == (x, y):
        return (min(x0, x), min(y0, y), max(x0, x), max(y0, y))
    # endpoint -> center (F.6.5, phi == 0)
    dx2, dy2 = (x0 - x) / 2.0, (y0 - y) / 2.0
    lam = dx2 * dx2 / (rx * rx) + dy2 * dy2 / (ry * ry)
    if lam > 1:
        s = math.sqrt(lam)
        rx, ry = rx * s, ry * s
    num = rx * rx * ry * ry - rx * rx * dy2 * dy2 - ry * ry * dx2 * dx2
    den = rx * rx * dy2 * dy2 + ry * ry * dx2 * dx2
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if fa == fs:
        co = -co
    cxp, cyp = co * rx * dy2 / ry, -co * ry * dx2 / rx
    cx, cy = cxp + (x0 + x) / 2.0, cyp + (y0 + y) / 2.0

    def ang(ux, uy, vx, vy):
        d = math.hypot(ux, uy) * math.hypot(vx, vy)
        c = max(-1.0, min(1.0, (ux * vx + uy * vy) / d))
        a = math.acos(c)
        return -a if ux * vy - uy * vx < 0 else a

    t1 = ang(1, 0, (dx2 - cxp) / rx, (dy2 - cyp) / ry)
    dt = ang((dx2 - cxp) / rx, (dy2 - cyp) / ry,
             (-dx2 - cxp) / rx, (-dy2 - cyp) / ry)
    if not fs and dt > 0:
        dt -= 2 * math.pi
    elif fs and dt < 0:
        dt += 2 * math.pi
    lo, hi = sorted((t1, t1 + dt))
    xs, ys = [x0, x], [y0, y]
    k = math.ceil(lo / (math.pi / 2)) * (math.pi / 2)
    while k <= hi:
        xs.append(cx + rx * math.cos(k))
        ys.append(cy + ry * math.sin(k))
        k += math.pi / 2
    return (min(xs), min(ys), max(xs), max(ys))


def split_subpaths(d):
    """Return a list of subpaths, each a dict with the char span in `d`,
    the absolute start point, the absolute end point, and the bbox
    (minx, miny, maxx, maxy) taken over a convex-hull bound of every
    segment."""
    # locate command spans first (so we can slice `d` verbatim later)
    cmd_pos = [m.start() for m in re.finditer(r"[A-Za-z]", d)]
    if not cmd_pos:
        return []
    subs = []
    toks = list(tokenize(d))
    px = py = 0.0            # current point
    sx = sy = 0.0            # current subpath start
    cpx = cpy = None         # last cubic/quad control (for S/T)
    last_cmd = None
    cur = None               # subpath being built

    def bump(x, y):
        cur["bb"][0] = min(cur["bb"][0], x)
        cur["bb"][1] = min(cur["bb"][1], y)
        cur["bb"][2] = max(cur["bb"][2], x)
        cur["bb"][3] = max(cur["bb"][3], y)

    ti = 0
    ci = 0  # index into cmd_pos

    def read(k):
        nonlocal ti
        vals = toks[ti:ti + k]
        if len(vals) != k or any(isinstance(v, str) for v in vals):
            raise ParseError("short parameter list")
        ti += k
        return vals

    while ti < len(toks):
        t = toks[ti]
        if isinstance(t, str):
            cmd = t
            ti += 1
            ci += 1
        else:
            # implicit repeat of previous command (M->L, m->l)
            if last_cmd is None:
                raise ParseError("number before any command")
            cmd = last_cmd
            if cmd == "M":
                cmd = "L"
            elif cmd == "m":
                cmd = "l"
        cl = cmd.lower()
        rel = cmd.islower()

        if cl == "z":
            if cur:
                bump(sx, sy)
            px, py = sx, sy
            last_cmd = cmd
            continue

        if cl == "m":
            x, y = read(2)
            if rel and cur is not None:
                x, y = px + x, py + y
            elif rel and cur is None:
                # first moveto: lowercase still absolute (pen at 0,0)
                pass
            # close previous subpath span
            start_char = cmd_pos[ci - 1]
            if cur is not None:
                cur["span"][1] = start_char
                cur["end"] = (px, py)
                subs.append(cur)
            cur = {"span": [start_char, len(d)], "start": (x, y),
                   "end": None, "bb": [x, y, x, y],
                   "first_pair_cmd_index": ci - 1}
            px, py = x, y
            sx, sy = x, y
            last_cmd = cmd
            continue

        if cur is None:
            raise ParseError("drawing command before moveto")

        if cl == "l":
            x, y = read(2)
            if rel:
                x, y = px + x, py + y
            bump(x, y)
            px, py = x, y
            cpx = cpy = None
        elif cl == "h":
            (x,) = read(1)
            x = px + x if rel else x
            bump(x, py)
            px = x
            cpx = cpy = None
        elif cl == "v":
            (y,) = read(1)
            y = py + y if rel else y
            bump(px, y)
            py = y
            cpx = cpy = None
        elif cl == "c":
            x1, y1, x2, y2, x, y = read(6)
            if rel:
                x1, y1, x2, y2, x, y = (px + x1, py + y1, px + x2, py + y2,
                                        px + x, py + y)
            for a, b in ((x1, y1), (x2, y2), (x, y)):
                bump(a, b)
            cpx, cpy = x2, y2
            px, py = x, y
        elif cl == "s":
            x2, y2, x, y = read(4)
            if rel:
                x2, y2, x, y = px + x2, py + y2, px + x, py + y
            x1, y1 = (2 * px - cpx, 2 * py - cpy) if cpx is not None else (px, py)
            for a, b in ((x1, y1), (x2, y2), (x, y)):
                bump(a, b)
            cpx, cpy = x2, y2
            px, py = x, y
        elif cl == "q":
            x1, y1, x, y = read(4)
            if rel:
                x1, y1, x, y = px + x1, py + y1, px + x, py + y
            for a, b in ((x1, y1), (x, y)):
                bump(a, b)
            cpx, cpy = x1, y1
            px, py = x, y
        elif cl == "t":
            x, y = read(2)
            if rel:
                x, y = px + x, py + y
            x1, y1 = (2 * px - cpx, 2 * py - cpy) if cpx is not None else (px, py)
            bump(x1, y1)
            bump(x, y)
            cpx, cpy = x1, y1
            px, py = x, y
        elif cl == "a":
            rx, ry, rot = read(3)
            fa, fs = read(2)
            x, y = read(2)
            if rel:
                x, y = px + x, py + y
            bb = arc_bbox(px, py, rx, ry, rot, int(fa), int(fs), x, y)
            bump(bb[0], bb[1])
            bump(bb[2], bb[3])
            px, py = x, y
            cpx = cpy = None
        else:
            raise ParseError(f"unknown command {cmd!r}")
        last_cmd = cmd

    if cur is not None:
        cur["end"] = (px, py)
        subs.append(cur)
    return subs


def fmt(v):
    v = round(v, 3)
    if v == 0:
        return "0"
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    if s.startswith("0."):
        s = s[1:]
    elif s.startswith("-0."):
        s = "-" + s[3:]
    return s


def outside(bb, vb):
    minx, miny, maxx, maxy = bb
    vx, vy, vw, vh = vb
    return maxx < vx or minx > vx + vw or maxy < vy or miny > vy + vh


def rewrite_d(d, vb):
    subs = split_subpaths(d)
    if not subs:
        return d, 0
    keep = [s for s in subs if not outside(s["bb"], vb)]
    dropped = len(subs) - len(keep)
    if dropped == 0:
        return d, 0
    if not keep:
        raise ParseError("every subpath is outside the viewBox")

    # walk the original subpath order; emit kept spans, rebasing the leading
    # coordinate pair of a kept subpath whenever a preceding subpath was cut
    out = []
    prev_end = (0.0, 0.0)
    prev_kept_touches = True  # first kept subpath: pen is 0,0 (absolute rules)
    gap_since_kept = False
    for s in subs:
        if outside(s["bb"], vb):
            gap_since_kept = True
            continue
        span = d[s["span"][0]:s["span"][1]]
        if gap_since_kept:
            # the leading moveto now sits after a different (or no) subpath
            mcmd = span[0]
            body = span[1:]
            mnum = NUMBER.search(body)
            m2 = NUMBER.search(body, mnum.end())
            tx, ty = s["start"]
            if mcmd == "m" and not out:
                nx, ny = tx, ty                 # first cmd: 'm' is absolute
            elif mcmd == "M":
                nx, ny = tx, ty
            else:
                nx, ny = tx - prev_end[0], ty - prev_end[1]
            sep = "" if fmt(ny).startswith("-") else " "
            new_pair = f"{fmt(nx)}{sep}{fmt(ny)}"
            span = mcmd + body[:mnum.start()] + new_pair + body[m2.end():]
            gap_since_kept = False
        out.append(span)
        prev_end = s["end"]
    return "".join(out), dropped


def trim_svg(path):
    text = Path(path).read_text(encoding="utf-8")
    if BAIL.search(text):
        return None
    m = VIEWBOX.search(text)
    if not m:
        return None
    try:
        vb = [float(x) for x in re.split(r"[ ,]+", m.group(1).strip())]
        if len(vb) != 4:
            return None
    except ValueError:
        return None

    total_dropped = 0

    def repl(mo):
        nonlocal total_dropped
        head, d, tail = mo.groups()
        try:
            new_d, dropped = rewrite_d(d, vb)
        except ParseError:
            return mo.group(0)
        total_dropped += dropped
        return head + new_d + tail

    new_text = PATH_D.sub(repl, text)
    if new_text != text:
        before = len(text.encode("utf-8"))
        Path(path).write_text(new_text, encoding="utf-8", newline="")
        return (total_dropped, before - len(new_text.encode("utf-8")))
    return None


def iter_svgs(paths):
    for p in paths:
        p = Path(p)
        if p.is_dir():
            yield from sorted(p.rglob("*.svg"))
        elif p.suffix.lower() == ".svg":
            yield p


def main(argv):
    targets = argv or ["site/images"]
    changed = 0
    for svg in iter_svgs(targets):
        res = trim_svg(str(svg))
        if res:
            dropped, saved = res
            changed += 1
            print(f"trimmed {svg}: -{dropped} offscreen subpath(s), -{saved} bytes")
    if not changed:
        print("no offscreen subpaths found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
