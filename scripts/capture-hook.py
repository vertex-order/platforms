#!/usr/bin/env python3
# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
"""Claude Code PreToolUse hook: stop a web fetch the capture cache already answers.

Wired in .claude/settings.json for WebFetch and Bash. Reads the tool call as
JSON on stdin. For WebFetch it checks `url`; for Bash it checks every http(s)
URL in a curl/wget/Invoke-WebRequest command. On a cache HIT or an earlier
BLOCKED reply it denies the call and says which file to read instead.
Anything else (MISS, no URL, any error) passes through silently.
Commands that already go through scripts/capture.py are never blocked.
See docs/capture.md.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

FETCHERS = re.compile(r"\b(curl|wget|Invoke-WebRequest|iwr|Invoke-RestMethod|irm)\b", re.I)
URL = re.compile(r"https?://[^\s'\"<>`)]+")
LOCAL = re.compile(r"^https?://(localhost|127\.|\[::1\]|0\.0\.0\.0)", re.I)


def urls_of(call):
    name, inp = call.get("tool_name", ""), call.get("tool_input", {}) or {}
    if name == "WebFetch":
        return [inp["url"]] if inp.get("url") else []
    if name == "Bash":
        cmd = inp.get("command", "")
        if "capture.py" in cmd or not FETCHERS.search(cmd):
            return []
        return URL.findall(cmd)
    return []


def main():
    try:
        call = json.load(sys.stdin)
        import capture as C

        root = C.root_dir()
        notes = []
        for url in urls_of(call):
            if LOCAL.match(url):
                continue
            _, hits, _, blocked = C.find(url, root)
            if hits:
                d, row = hits[0]
                notes.append(f"{url} is cached: read {d / row['file']} ({row['kind']} {row['accessed']}).")
            elif blocked:
                notes.append(
                    f"{url} was blocked on {blocked[0][1]['accessed']} ({blocked[0][1]['note']}): "
                    "do not retry; run `capture.py request` and ask the user to save it."
                )
        if notes:
            reason = " ".join(notes) + " Do not fetch it again (docs/capture.md)."
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason}}))
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
