#!/usr/bin/env python3
# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
"""Cross-repo file sync for the Vertex Order repos.

Reads `sync.toml`. Each `[subscribe.<name>]` table names another repo, a git
ref, and a list of paths this repo vendors from it. This script fetches those
paths at that ref and writes them into the working tree. They are **vendored
copies** — never hand-edit them here; edit them in the owning repo. CI
(`.github/workflows/check-vendored.yml`) runs `sync.py --check` and fails the
PR if any vendored file has drifted from its source.

`[publish]` in sync.toml is documentation only (what this repo owns and other
repos pull) — this script does not read it beyond refusing to clobber a
published path.

Usage:
  python3 scripts/sync.py               # pull every subscription into the tree
  python3 scripts/sync.py --check       # CI: exit 1 if anything drifted, no writes
  python3 scripts/sync.py --update NAME  # repin [subscribe.NAME].ref to that
                                         # ref's current HEAD sha, then pull NAME

Source resolution per subscription, in order:
  1. sibling checkout ../<repo-with-slash-as-dash> if it is a git repo  (git archive)
  2. git clone the repo over https, checkout <ref>

Needs git and Python 3.11+ (tomllib). Not runnable in a design tool (no shell)
— there the vendored files are simply the last-synced committed copies.
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOML = ROOT / "sync.toml"


def run(cmd, **kw):
    return subprocess.run(
        cmd, check=True, capture_output=True,
        encoding="utf-8", errors="replace", **kw,
    )


def load():
    if not TOML.exists():
        sys.exit(f"{TOML.name} not found")
    with open(TOML, "rb") as f:
        return tomllib.load(f)


def published(cfg):
    return set((cfg.get("publish") or {}).get("paths", []))


def sibling_dir(repo: str) -> Path:
    return ROOT.parent / repo.replace("/", "-")


def checkout(repo: str, ref: str, fetch: bool = True) -> tuple[Path, str]:
    """Return (tree_dir, resolved_sha). tree_dir is a temp dir; caller removes it.

    fetch=False tries the sibling's already-known refs first — fast, no
    network — and only fetches if that doesn't resolve. Used by the
    pre-commit guard so a routine commit doesn't always hit the network;
    everything else defaults to fetch=True for freshness."""
    tmp = Path(tempfile.mkdtemp(prefix="vo-sync-"))
    sib = sibling_dir(repo)
    if (sib / ".git").exists():
        attempts = [True] if fetch else [False, True]
        for do_fetch in attempts:
            if do_fetch:
                try:
                    run(["git", "-C", str(sib), "fetch", "--quiet", "origin", ref])
                except subprocess.CalledProcessError:
                    pass
            try:
                sha = run(["git", "-C", str(sib), "rev-parse", ref]).stdout.strip()
                tar = subprocess.run(
                    ["git", "-C", str(sib), "archive", "--format=tar", ref],
                    check=True, capture_output=True,
                ).stdout
                (tmp / "t.tar").write_bytes(tar)
                (tmp / "tree").mkdir(exist_ok=True)
                shutil.unpack_archive(str(tmp / "t.tar"), str(tmp / "tree"), "tar")
                (tmp / "t.tar").unlink()
                return tmp / "tree", sha
            except subprocess.CalledProcessError:
                continue
    url = f"https://github.com/{repo}.git"
    dest = tmp / "tree"
    run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout", url, str(dest)])
    run(["git", "-C", str(dest), "fetch", "--quiet", "origin", ref])
    run(["git", "-C", str(dest), "-c", "advice.detachedHead=false", "checkout", "--quiet", ref])
    sha = run(["git", "-C", str(dest), "rev-parse", "HEAD"]).stdout.strip()
    shutil.rmtree(dest / ".git", ignore_errors=True)
    return dest, sha


def files_for(base: Path, rel: str):
    """Yield (relpath, abspath) pairs for a path spec (trailing / = directory)."""
    src = base / rel.rstrip("/")
    if rel.endswith("/"):
        if not src.is_dir():
            sys.exit(f"source has no directory {rel!r}")
        for p in sorted(src.rglob("*")):
            if p.is_file():
                yield p.relative_to(base), p
    else:
        if not src.is_file():
            sys.exit(f"source has no file {rel!r}")
        yield Path(rel), src


def sync_one(name, sub, *, check, drift):
    repo, ref = sub["repo"], str(sub.get("ref", "main"))
    tree, sha = checkout(repo, ref)
    try:
        seen = set()
        for spec in sub["paths"]:
            for rel, srcfile in files_for(tree, spec):
                seen.add(rel)
                dst = ROOT / rel
                same = dst.is_file() and filecmp.cmp(srcfile, dst, shallow=False)
                if same:
                    continue
                drift.append(f"{rel}  ({name} @ {ref})")
                if not check:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(srcfile, dst)
            # local extras in a subscribed directory: warn, never delete
            if spec.endswith("/"):
                localdir = ROOT / spec.rstrip("/")
                if localdir.is_dir():
                    for p in sorted(localdir.rglob("*")):
                        if p.is_file() and p.relative_to(ROOT) not in seen:
                            print(f"  ! local extra not in {name}: {p.relative_to(ROOT)}")
    finally:
        shutil.rmtree(tree.parent, ignore_errors=True)
    return sha


def repin(name, sha):
    lines = TOML.read_text(encoding="utf-8").splitlines(keepends=True)
    header = f"[subscribe.{name}]"
    inblock = False
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("["):
            inblock = s == header
        if inblock and s.startswith("ref "):
            indent = ln[: len(ln) - len(ln.lstrip())]
            lines[i] = f'{indent}ref = "{sha}"\n'
            TOML.write_text("".join(lines), encoding="utf-8", newline="\n")
            print(f"sync.toml: [subscribe.{name}].ref = {sha}")
            return
    sys.exit(f"no [subscribe.{name}] ref line to update")


def spec_matches(relposix: str, spec: str) -> bool:
    return relposix == spec.rstrip("/") if not spec.endswith("/") else (
        relposix == spec.rstrip("/") or relposix.startswith(spec)
    )


def staged_files():
    out = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], cwd=ROOT).stdout
    return [line for line in out.splitlines() if line]


def check_staged(subs) -> int:
    """Pre-commit guard: block a commit that hand-edits a vendored path so it
    no longer matches its source. A legitimate sync (just sync, then commit)
    always matches the source, so it always passes."""
    staged = staged_files()
    if not staged:
        return 0
    hits = []
    for name, sub in subs.items():
        for spec in sub.get("paths", []):
            for f in staged:
                if spec_matches(f, spec):
                    hits.append((name, sub, f))
    if not hits:
        return 0

    trees = {}
    bad = []
    for name, sub, relposix in hits:
        key = (sub["repo"], str(sub.get("ref", "main")))
        if key not in trees:
            trees[key] = checkout(*key, fetch=False)
        tree, _sha = trees[key]
        srcfile = tree / relposix
        staged_bytes = subprocess.run(
            ["git", "show", f":{relposix}"], cwd=ROOT, check=True, capture_output=True,
        ).stdout
        if not srcfile.is_file() or staged_bytes != srcfile.read_bytes():
            bad.append(f"{relposix}  (vendored from {name})")
    for tree, _ in trees.values():
        shutil.rmtree(tree.parent, ignore_errors=True)

    if not bad:
        return 0
    print(f"{len(bad)} staged file(s) are vendored and don't match their source:")
    for b in bad:
        print(f"  {b}")
    print("\nEdit these in the owning repo instead, then `just sync-update` here.")
    print("If this really is a sync commit, run `just sync` again and re-stage.")
    return 1


def main():
    ap = argparse.ArgumentParser(description="cross-repo vendored-file sync")
    ap.add_argument("--check", action="store_true", help="report drift, exit 1, no writes")
    ap.add_argument("--check-staged", action="store_true",
                     help="pre-commit guard: block hand-edited vendored files in the index")
    ap.add_argument("--update", metavar="NAME", help="repin a subscription then pull it")
    args = ap.parse_args()

    cfg = load()
    subs = cfg.get("subscribe") or {}
    if not subs:
        if not args.check_staged:
            print("no [subscribe.*] in sync.toml — nothing to do")
        return 0

    if args.check_staged:
        return check_staged(subs)

    pub = published(cfg)
    for name, sub in subs.items():
        clash = pub.intersection(sub.get("paths", []))
        if clash:
            sys.exit(f"[subscribe.{name}] also lists published path(s): {sorted(clash)}")

    if args.update:
        if args.update not in subs:
            sys.exit(f"no [subscribe.{args.update}]")
        _, sha = checkout(subs[args.update]["repo"], str(subs[args.update].get("ref", "main")))
        repin(args.update, sha)
        cfg = load()
        subs = cfg["subscribe"]
        subs = {args.update: subs[args.update]}

    drift = []
    for name, sub in subs.items():
        sync_one(name, sub, check=args.check, drift=drift)

    if not drift:
        print("vendored files in sync" if args.check else "nothing to update")
        return 0
    verb = "drifted" if args.check else "updated"
    print(f"\n{len(drift)} vendored file(s) {verb}:")
    for d in drift:
        print(f"  {d}")
    if args.check:
        print("\nrun `just sync` and commit the result.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
