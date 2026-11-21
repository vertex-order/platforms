#!/usr/bin/env python3
# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
"""Validate site/data/*.js against schemas/*.schema.json.

Each site/data/*.js file declares its own schema with a
`// schema: <name>.schema.json` comment (optionally `#/<json-pointer>` for
one def inside a file that holds several, e.g. catalogs.js's three
globals) placed anywhere before the assignment it covers -- the next
top-level `<lhs> = <literal>` after that comment is what gets checked
against it. A file can carry more than one declaration (again: catalogs.js,
one per global). A file with no declaration at all is simply not checked --
this is how an org-only file like games.js, with its own local
schemas/franchise-list.schema.json, gets picked up automatically, same as
every file kit itself owns: there is no hardcoded file/schema mapping here
to keep in sync, just the directive scan.

The literal is extracted with scripts/js_literal.py (a real JSON parser
can't read these files -- unquoted keys, single-quoted strings, trailing
commas, comments).

Also fails on non-Latin text with no `lang` (`--warn-lang` downgrades it to a
warning, for a repo adopting the check): see check_lang_coverage.

Implements exactly the JSON Schema (2020-12) keywords schemas/*.schema.json
actually use: type, enum, const, properties, additionalProperties (bool or
schema), required, items, minItems, uniqueItems, minLength, minProperties,
pattern, minimum, maximum, oneOf, anyOf, allOf, dependentRequired, $ref
(same-file and cross-file), $defs. Not a general-purpose validator --
anything else in a future schema fails loudly (KeyError/NotImplementedError)
rather than silently no-op-ing.

No external deps (stdlib json/re only, plus scripts/js_literal.py). Run:
python3 scripts/validate-data.py
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from js_literal import ParseError, parse_value, parse_value_after

_PLATFORM_ICONS_RE = re.compile(r"window\.PLATFORM_ICONS\s*=\s*")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data"
SCHEMAS = ROOT / "schemas"

_DIRECTIVE_RE = re.compile(r"//\s*schema:\s*(\S+\.schema\.json(?:#\S*)?)")
_NEXT_ASSIGN_RE = re.compile(r"=\s*(?=[{\[])")


def find_declarations(text):
    """Yield (schema_ref, instance) for every `// schema: <ref>` directive in
    text, each paired with the JS-literal value of the assignment that
    follows it (the next `<lhs> = <literal>` found anywhere after the
    directive -- typically right below it, possibly past more header
    comment lines)."""
    for m in _DIRECTIVE_RE.finditer(text):
        schema_ref = m.group(1)
        am = _NEXT_ASSIGN_RE.search(text, m.end())
        if not am:
            raise ParseError(
                f"'// schema: {schema_ref}' directive has no following assignment"
            )
        instance, _ = parse_value(text, am.end())
        yield schema_ref, instance


# ---------------------------------------------------------------------------
# Minimal JSON Schema (2020-12) validator -- exactly the keyword subset
# schemas/*.schema.json use. See module docstring.
# ---------------------------------------------------------------------------


class SchemaStore:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self._cache = {}

    def load(self, rel_name):
        if rel_name not in self._cache:
            with open(self.base_dir / rel_name, encoding="utf-8") as f:
                self._cache[rel_name] = json.load(f)
        return self._cache[rel_name]


def _resolve_pointer(doc, pointer):
    node = doc
    if pointer in ("", "/"):
        return node
    for seg in pointer.lstrip("/").split("/"):
        seg = seg.replace("~1", "/").replace("~0", "~")
        node = node[seg]
    return node


def _resolve_ref(ref, current_file, store):
    """Returns (target_schema, target_root_doc, target_file) -- ref may be
    'file.schema.json', 'file.schema.json#/$defs/X', or (only reachable via
    an in-schema $ref, never a directive) a bare '#/$defs/X' resolved
    against current_file."""
    if "#" in ref:
        file_part, pointer = ref.split("#", 1)
    else:
        file_part, pointer = ref, ""
    target_file = file_part or current_file
    root_doc = store.load(target_file)
    return _resolve_pointer(root_doc, pointer), root_doc, target_file


_TYPE_MAP = {
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _type_matches(instance, type_name):
    if type_name == "integer":
        if isinstance(instance, bool):
            return False
        if isinstance(instance, int):
            return True
        return isinstance(instance, float) and instance.is_integer()
    if type_name == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if type_name == "array":
        return isinstance(instance, list)
    if type_name == "object":
        return isinstance(instance, dict)
    py_type = _TYPE_MAP.get(type_name)
    if py_type is None:
        raise NotImplementedError(f"unsupported type keyword value: {type_name!r}")
    if py_type is bool:
        return isinstance(instance, bool)
    return isinstance(instance, py_type) and not isinstance(instance, bool)


def _path_str(path):
    return "$" + "".join(f"[{p!r}]" if isinstance(p, str) else f"[{p}]" for p in path)


def validate(instance, schema, current_file, store, path, errors):
    if isinstance(schema, bool):
        if schema is False:
            errors.append(f"{_path_str(path)}: not allowed here")
        return

    if "$ref" in schema:
        target, _root_doc, target_file = _resolve_ref(
            schema["$ref"], current_file, store
        )
        validate(instance, target, target_file, store, path, errors)
        return

    if "type" in schema:
        types = schema["type"]
        types = types if isinstance(types, list) else [types]
        if not any(_type_matches(instance, t) for t in types):
            errors.append(
                f"{_path_str(path)}: expected type {types!r}, got {type(instance).__name__}: {instance!r}"
            )
            return

    if "const" in schema:
        expected = schema["const"]
        ok = (
            (instance is expected)
            if isinstance(expected, bool)
            else (not isinstance(instance, bool) and instance == expected)
        )
        if not ok:
            errors.append(
                f"{_path_str(path)}: expected const {expected!r}, got {instance!r}"
            )

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{_path_str(path)}: {instance!r} not one of {schema['enum']!r}")

    if isinstance(instance, str):
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(
                f"{_path_str(path)}: {instance!r} doesn't match pattern {schema['pattern']!r}"
            )
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(
                f"{_path_str(path)}: {instance!r} shorter than minLength {schema['minLength']}"
            )

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(
                f"{_path_str(path)}: {instance!r} below minimum {schema['minimum']}"
            )
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(
                f"{_path_str(path)}: {instance!r} above maximum {schema['maximum']}"
            )

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(
                f"{_path_str(path)}: has {len(instance)} item(s), needs at least {schema['minItems']}"
            )
        if schema.get("uniqueItems") and len(instance) != len(
            {json.dumps(x, sort_keys=True) for x in instance}
        ):
            errors.append(f"{_path_str(path)}: items are not unique")
        if "items" in schema:
            for i, item in enumerate(instance):
                validate(item, schema["items"], current_file, store, path + [i], errors)

    if isinstance(instance, dict):
        props = schema.get("properties", {})
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            errors.append(
                f"{_path_str(path)}: has {len(instance)} propertie(s), needs at least {schema['minProperties']}"
            )
        if "required" in schema:
            for key in schema["required"]:
                if key not in instance:
                    errors.append(
                        f"{_path_str(path)}: missing required property {key!r}"
                    )
        if "dependentRequired" in schema:
            for key, needs in schema["dependentRequired"].items():
                if key in instance:
                    for need in needs:
                        if need not in instance:
                            errors.append(
                                f"{_path_str(path)}: {key!r} present but {need!r} is missing"
                            )
        ap = schema.get("additionalProperties", True)
        for key, val in instance.items():
            if key in props:
                validate(val, props[key], current_file, store, path + [key], errors)
            elif ap is False:
                errors.append(
                    f"{_path_str(path)}: additional property {key!r} not allowed"
                )
            elif ap is not True:
                validate(val, ap, current_file, store, path + [key], errors)

    for combinator in ("oneOf", "anyOf", "allOf"):
        if combinator not in schema:
            continue
        branches = schema[combinator]
        matches = 0
        branch_errors = []
        for branch in branches:
            sub_errors = []
            validate(instance, branch, current_file, store, path, sub_errors)
            branch_errors.append(sub_errors)
            if not sub_errors:
                matches += 1
        if combinator == "allOf":
            for sub_errors in branch_errors:
                errors.extend(sub_errors)
        elif combinator == "anyOf" and matches == 0:
            errors.append(
                f"{_path_str(path)}: matched none of {len(branches)} anyOf branch(es)"
            )
        elif combinator == "oneOf" and matches != 1:
            errors.append(
                f"{_path_str(path)}: matched {matches} of {len(branches)} oneOf branch(es) (want exactly 1)"
            )


def check(label, instance, schema_ref, store, findings):
    try:
        schema, _root_doc, target_file = _resolve_ref(schema_ref, "", store)
    except (FileNotFoundError, KeyError) as e:
        findings.append((label, [f"'// schema: {schema_ref}' doesn't resolve: {e}"]))
        return
    errors = []
    validate(instance, schema, target_file, store, [], errors)
    if errors:
        findings.append((label, errors))


def load_name_override_keys():
    """Keys platform-icons.js flags `nameOverride: true` for -- the only
    keys a group entry's platforms[].name is allowed to use (PlatformItem's
    `name` is a full-label override; every other key must compose via
    `paren` instead, per platform-icons.schema.json's own field
    description). Cross-file, so not expressible as a plain JSON Schema
    keyword: depends on platform-icons.js's own content, not just the
    group schema. Returns None if platform-icons.js isn't present (e.g. a
    repo checked before init-list.py seeds it) -- the caller skips the
    check rather than failing every group file for a missing dependency.
    """
    path = DATA / "platform-icons.js"
    if not path.exists():
        return None
    # platform-icons.js carries no `// schema:` directive of its own (it's
    # vendored from vertex-order/platforms, checked there, not re-declared
    # per consuming repo), so this reads window.PLATFORM_ICONS directly
    # instead of going through find_declarations.
    try:
        instance = parse_value_after(
            path.read_text(encoding="utf-8"), _PLATFORM_ICONS_RE
        )
    except ParseError:
        return None
    return {p["key"] for p in instance if p.get("nameOverride")}


def check_name_overrides(label, instance, allowed_keys, findings):
    """A platforms[] item's `name` (full label override) is only legitimate
    on a key platform-icons.js flags nameOverride:true for -- everywhere
    else, the same result should come from `paren` (composed onto the
    catalog's own base label) or the boolean flags (terminated/jpTag/
    nonJpTag/noResults, which already auto-append their own tooltip text).
    Walks every release and its versions[] (versions don't recurse
    further, per MediaDetails/VersionDetails)."""
    errors = []

    def walk_platforms(node, where):
        for pl in node.get("platforms") or []:
            key = pl.get("key")
            if "name" in pl and key not in allowed_keys:
                errors.append(
                    f"{where}.platforms[]: `name` used on key {key!r}, not flagged "
                    f"nameOverride:true in platform-icons.js -- use `paren` (or the "
                    f"terminated/jpTag/nonJpTag/noResults auto-text) instead"
                )

    def walk_version(node, where):
        walk_platforms(node, where)
        for i, ver in enumerate(node.get("versions") or []):
            walk_version(ver, f"{where}.versions[{i}]")

    for si, slot in enumerate(instance.get("media") or []):
        for ri, rel in enumerate(slot.get("releases") or []):
            walk_version(rel, f"$.media[{si}].releases[{ri}]")

    if errors:
        findings.append((label, errors))


def check_contents_orders(label, instance, findings):
    """A release's `contents[]` sort keys are all-or-nothing, like a group's
    section orders: if any part sets `narrativeOrder` (or `chronoOrder`),
    every part in that list must."""
    errors = []

    def walk(node, where):
        if isinstance(node, dict):
            parts = node.get("contents")
            if isinstance(parts, list):
                for field in ("narrativeOrder", "chronoOrder"):
                    have = [
                        i
                        for i, p in enumerate(parts)
                        if isinstance(p, dict) and field in p
                    ]
                    if have and len(have) != len(parts):
                        missing = [i for i in range(len(parts)) if i not in have]
                        errors.append(
                            f"{where}.contents[]: `{field}` is set on some parts but not "
                            f"on part(s) {missing} -- set it on every part or none"
                        )
            for k, v in node.items():
                walk(v, f"{where}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{where}[{i}]")

    walk(instance, "$")
    if errors:
        findings.append((label, errors))


def check_more_platforms(label, instance, findings):
    """`more: true` on a platforms[] item hides the row behind a "+N" chip, and
    only a `contents[]` part has the chip. It fails anywhere else, and on a
    part whose rows are all `more` (nothing would show in the compact line)."""
    errors = []

    def walk(node, where, in_part):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "platforms" and isinstance(v, list):
                    rows = [pl for pl in v if isinstance(pl, dict)]
                    if in_part:
                        if rows and all(pl.get("more") for pl in rows):
                            errors.append(
                                f"{where}.platforms: every row is `more`; leave the "
                                f"original platform(s) without it"
                            )
                    else:
                        for i, pl in enumerate(v):
                            if isinstance(pl, dict) and pl.get("more"):
                                errors.append(
                                    f"{where}.platforms[{i}] (key {pl.get('key')!r}): "
                                    f"`more` is only for a `contents[]` part's platforms"
                                )
                if k == "contents" and isinstance(v, list):
                    for i, part in enumerate(v):
                        walk(part, f"{where}.contents[{i}]", True)
                else:
                    walk(v, f"{where}.{k}", False)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{where}[{i}]", in_part)

    walk(instance, "$", False)
    if errors:
        findings.append((label, errors))


def check_platform_link_modes(label, instance, findings):
    """A platforms[] item links out in at most one way: a stated `url`, a
    computed `search`, or `opensContents` (toggles the release's contents[]
    list instead of linking). Setting two is ambiguous, so it fails, and
    `opensContents` fails on a release with no contents[] to open."""
    errors = []
    modes = ("url", "search", "opensContents")

    def walk(node, where):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "platforms" and isinstance(v, list):
                    for i, pl in enumerate(v):
                        if not isinstance(pl, dict):
                            continue
                        used = [m for m in modes if pl.get(m) not in (None, False, "")]
                        if pl.get("opensContents") and not node.get("contents"):
                            errors.append(
                                f"{where}.platforms[{i}] (key {pl.get('key')!r}): "
                                f"`opensContents` needs a `contents[]` list on the same "
                                f"release (a primary or alt, not a version)"
                            )
                        if len(used) > 1:
                            errors.append(
                                f"{where}.platforms[{i}] (key {pl.get('key')!r}): "
                                f"{' and '.join('`' + m + '`' for m in used)} are "
                                f"mutually exclusive -- use only one"
                            )
                walk(v, f"{where}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{where}[{i}]")

    walk(instance, "$")
    if errors:
        findings.append((label, errors))


# Section orders: the three sort orders a group's `sections[]` can exist in,
# with the section field a slot sets and the sort-key field a section carries.
SECTION_ORDERS = {
    "narrative": ("narrativeSection", "narrativeOrder"),
    "chrono": ("chronoSection", "chronoOrder"),
    "release": ("releaseSection", "releaseOrder"),
}


def check_sections(label, instance, findings):
    """A group's `sections[]` and its slots' `<order>Section` fields are
    cross-field rules JSON Schema can't express:

    - section ids are unique within the group;
    - a section's `orders` is exactly the set of orders it carries a
      `<order>Order` value for (no missing value, no stray one);
    - per order, all-or-nothing: if any section lists the order, every
      media[] slot sets that order's section field, to the id of a section
      that lists the order, and every such section is used by at least one
      slot; if no section lists the order, no slot sets the field.
    Structural problems (wrong types, unknown keys) are the schema pass's
    job -- this skips anything malformed rather than double-reporting."""
    errors = []
    sections = instance.get("sections")
    sections = sections if isinstance(sections, list) else []
    slots = instance.get("media")
    slots = slots if isinstance(slots, list) else []

    seen = set()
    for i, sec in enumerate(sections):
        if not isinstance(sec, dict):
            continue
        sid = sec.get("id")
        where = f"$.sections[{i}]" + (f" ({sid!r})" if isinstance(sid, str) else "")
        if isinstance(sid, str):
            if sid in seen:
                errors.append(f"{where}: duplicate section id")
            seen.add(sid)
        orders = sec.get("orders")
        orders = (
            [o for o in orders if o in SECTION_ORDERS]
            if isinstance(orders, list)
            else []
        )
        for order, (_, key_field) in SECTION_ORDERS.items():
            has_value = key_field in sec
            if order in orders and not has_value:
                errors.append(
                    f"{where}: lists {order!r} in `orders` but has no `{key_field}`"
                )
            elif order not in orders and has_value:
                errors.append(
                    f"{where}: has `{key_field}` but does not list {order!r} in `orders`"
                )

    for order, (slot_field, _) in SECTION_ORDERS.items():
        listing = {
            sec["id"]
            for sec in sections
            if isinstance(sec, dict)
            and isinstance(sec.get("id"), str)
            and isinstance(sec.get("orders"), list)
            and order in sec["orders"]
        }
        used = set()
        for i, slot in enumerate(slots):
            if not isinstance(slot, dict):
                continue
            where = f"$.media[{i}]" + (
                f" ({slot['title']!r})" if isinstance(slot.get("title"), str) else ""
            )
            value = slot.get(slot_field)
            if listing:
                if value is None:
                    errors.append(
                        f"{where}: no `{slot_field}` -- the {order} order has sections, "
                        f"so every entry needs one of {sorted(listing)}"
                    )
                elif value in listing:
                    used.add(value)
                elif value in seen:
                    errors.append(
                        f"{where}: `{slot_field}` {value!r} is a section that does not "
                        f"list {order!r} in `orders` (listing it: {sorted(listing)})"
                    )
                else:
                    errors.append(
                        f"{where}: `{slot_field}` {value!r} is not a section id of this "
                        f"group (listing {order!r}: {sorted(listing)})"
                    )
            elif value is not None:
                errors.append(
                    f"{where}: `{slot_field}` set, but no section lists {order!r} in "
                    f"`orders` -- the {order} order is flat"
                )
        for sid in sorted(listing - used):
            errors.append(
                f"section {sid!r} lists {order!r} but no entry sets "
                f"`{slot_field}: {sid!r}`"
            )

    if errors:
        findings.append((label, errors))


MARKERS = ("Mainline", "Essential", "Optional")


def _tag_text(tag):
    return tag if isinstance(tag, str) else tag.get("abbrTerm", "")


def check_markers(label, instance, findings, usage):
    """Tags that rank an entry: `Mainline` (the group's core numbered
    title), `Essential` and `Optional`. Per entry (its primary): at most
    one of the three, and it is the first tag. Across the whole list
    (`usage`, filled here and judged at the end): only one of Essential
    and Optional, because the entries without the marker are read as the
    opposite."""
    errors = []
    for i, slot in enumerate(instance.get("media") or []):
        if not isinstance(slot, dict):
            continue
        primary = slot.get("primary")
        if not isinstance(primary, dict):
            continue
        tags = [_tag_text(t) for t in (primary.get("tags") or [])]
        found = [t for t in tags if t in MARKERS]
        where = f"$.media[{i}]" + (
            f" ({slot['title']!r})" if isinstance(slot.get("title"), str) else ""
        )
        if len(found) > 1:
            errors.append(
                f"{where}: more than one of Mainline / Essential / Optional ({', '.join(found)}) -- Mainline already implies Essential; use one"
            )
        elif found and tags[0] != found[0]:
            errors.append(f"{where}: `{found[0]}` must be the first tag")
        for t in found:
            if t in ("Essential", "Optional"):
                usage[t].append(f"{label}: {slot.get('title')}")
    if errors:
        findings.append((label, errors))


def check_marker_usage(usage, findings):
    essential, optional = usage["Essential"], usage["Optional"]
    if not (essential and optional):
        return
    fewer, name = (
        (essential, "Essential")
        if len(essential) <= len(optional)
        else (optional, "Optional")
    )
    message = (
        f"this list uses both Essential ({len(essential)}) and Optional "
        f"({len(optional)}); use only one -- the entries without the marker "
        f"read as the opposite. The smaller side is {name} (e.g. {fewer[0]})"
    )
    findings.append(("tags", [message]))


def _walk_tags(node, where="$"):
    """Yield (path, tag text) for every `tags` list in a group literal --
    primary, alts[] and versions[] alike."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "tags" and isinstance(value, list):
                for tag in value:
                    yield f"{where}.tags", _tag_text(tag)
            else:
                yield from _walk_tags(value, f"{where}.{key}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _walk_tags(item, f"{where}[{i}]")


def check_tag_style(label, instance, findings, spellings):
    """Tag text starts with an uppercase letter or a digit (DLC, MMORPG
    and 2D pass; "rpg" doesn't). Spellings of each tag are also collected
    across the whole list (`spellings`, judged at the end): two tags that
    differ only in case must be written one way."""
    errors = []
    seen = set()
    for path, text in _walk_tags(instance):
        if not text:
            continue
        spellings.setdefault(text.casefold(), {}).setdefault(text, []).append(label)
        if not (text[0].isupper() or text[0].isdigit()) and (path, text) not in seen:
            seen.add((path, text))
            errors.append(
                f"{path}: tag {text!r} must start with an uppercase letter or a digit"
            )
    if errors:
        findings.append((label, errors))


def check_tag_spellings(spellings, findings):
    errors = []
    for variants in spellings.values():
        if len(variants) > 1:
            counts = ", ".join(
                f"{text!r} x{len(files)}"
                for text, files in sorted(variants.items(), key=lambda kv: -len(kv[1]))
            )
            errors.append(
                f"tag spelled more than one way (differs only in case): {counts}"
            )
    if errors:
        findings.append(("tags", errors))


# ---------------------------------------------------------------------------
# Language coverage: text in a non-Latin script must carry a `lang`.
#
# Script, not "non-ASCII": accented Latin (é, ñ, ō -- loan words, romaji with
# macrons) is still Latin and is never flagged. French or romaji in plain
# Latin can't be told from English, so those rely on explicit tagging and are
# not checked. An error by default; `--warn-lang` makes them warnings, and
# `--lang` lists the warnings (docs/data.md, "Language of text and links").
# ---------------------------------------------------------------------------

_SCRIPT_PREFIXES = (
    ("CJK UNIFIED", "han"),
    ("CJK COMPATIBILITY IDEOGRAPH", "han"),
    ("HIRAGANA", "kana"),
    ("KATAKANA", "kana"),
    ("HANGUL", "hangul"),
    ("CYRILLIC", "cyrillic"),
    ("GREEK", "greek"),
    ("ARABIC", "arabic"),
    ("HEBREW", "hebrew"),
    ("THAI", "thai"),
    ("DEVANAGARI", "devanagari"),
)

# Languages each script can be written in (the primary subtag of the `lang`).
_SCRIPT_LANGS = {
    "kana": {"ja"},
    "hangul": {"ko"},
    "han": {"ja", "zh", "yue", "ko"},
    "cyrillic": {"ru", "uk", "bg", "sr", "mk", "be", "kk", "mn", "ky", "tg"},
    "greek": {"el", "grc"},
    "arabic": {"ar", "fa", "ur", "ps", "ku"},
    "hebrew": {"he", "yi"},
    "thai": {"th"},
    "devanagari": {"hi", "mr", "ne", "sa"},
}
_NON_LATIN_LANGS = set().union(*_SCRIPT_LANGS.values())

# Fields whose text is a span's displayed text (the span's `tip` and
# `abbrDef` tooltips ride on the same `lang`).
_SPAN_TEXT_KEYS = (
    "text",
    "emText",
    "emLinkText",
    "abbrTerm",
    "tipText",
    "hintText",
    "tip",
    "abbrDef",
)


# Punctuation that English titles borrow (Final Fantasy I・II・III): not text.
_NEUTRAL = {"・", "･"}


# A lone Greek letter in an English title is a symbol (Kingdom Hearts χ), not text.
_LONE_GREEK = re.compile("(?<![Ͱ-Ͽ])[Ͱ-Ͽ](?![Ͱ-Ͽ])")


def _scripts_in(text):
    text = _LONE_GREEK.sub("", text)
    found = set()
    for ch in text:
        if ord(ch) < 0x250 or ch in _NEUTRAL:
            continue
        name = unicodedata.name(ch, "")
        for prefix, script in _SCRIPT_PREFIXES:
            if name.startswith(prefix):
                found.add(script)
                break
    return found


def _lang_problem(text, lang):
    """None when `lang` fits `text`; else a short reason. `lang` None means
    the field has no language set."""
    scripts = _scripts_in(text)
    if lang is None:
        return "non-Latin text with no lang" if scripts else None
    primary = lang.split("-")[0].lower()
    latn = any(part.lower() == "latn" for part in lang.split("-")[1:])
    if latn:
        return (
            f"lang {lang!r} says romanized but the text has {'/'.join(sorted(scripts))} characters"
            if scripts
            else None
        )
    if not scripts:
        if primary in _NON_LATIN_LANGS:
            return (
                f"Latin-only text under lang {lang!r}: romanization is {primary}-Latn"
            )
        return None
    if "kana" in scripts:
        want = _SCRIPT_LANGS["kana"]
    elif "hangul" in scripts:
        want = _SCRIPT_LANGS["hangul"]
    elif len(scripts) == 1:
        want = _SCRIPT_LANGS[next(iter(scripts))]
    else:
        return None
    if primary not in want:
        return f"lang {lang!r} does not fit the {'/'.join(sorted(scripts))} text (expected {'/'.join(sorted(want))})"
    return None


def check_lang_coverage(instance):
    """Return [(path, text, reason)] for a group literal."""
    out = []

    def pair(path, text, lang):
        if isinstance(text, str) and text:
            problem = _lang_problem(text, lang if isinstance(lang, str) else None)
            if problem:
                out.append((path, text, problem))

    def untaggable(path, text):
        # A bare string with no way to carry a `lang`.
        if isinstance(text, str) and _scripts_in(text):
            out.append(
                (
                    path,
                    text,
                    "non-Latin text in a plain string: use the object form with lang",
                )
            )

    def span(path, s):
        if isinstance(s, str):
            untaggable(path, s)
        elif isinstance(s, list):
            for i, item in enumerate(s):
                span(f"{path}[{i}]", item)
        elif isinstance(s, dict):
            lang = s.get("lang")
            for key in _SPAN_TEXT_KEYS:
                pair(f"{path}.{key}", s.get(key), lang)

    def by(path, b):
        if isinstance(b, str):
            untaggable(path, b)
        elif isinstance(b, list):
            for i, item in enumerate(b):
                by(f"{path}[{i}]", item)
        elif isinstance(b, dict):
            if "name" in b:
                pair(f"{path}.name", b.get("name"), b.get("lang"))
            if "names" in b:
                by(f"{path}.names", b["names"])

    def length(path, v):
        if isinstance(v, str):
            untaggable(path, v)
        elif isinstance(v, list):
            for i, part in enumerate(v):
                if isinstance(part, dict):
                    for key in ("label", "value", "tip"):
                        pair(f"{path}[{i}].{key}", part.get(key), part.get("lang"))

    def items(path, rows, keys):
        for i, row in enumerate(rows if isinstance(rows, list) else []):
            if isinstance(row, dict):
                for key in keys:
                    pair(f"{path}[{i}].{key}", row.get(key), row.get("lang"))

    def walk(path, node):
        if isinstance(node, list):
            for i, item in enumerate(node):
                walk(f"{path}[{i}]", item)
            return
        if not isinstance(node, dict):
            return
        is_group_or_section = "num" in node or "orders" in node
        if isinstance(node.get("title"), str) and not is_group_or_section:
            pair(f"{path}.title", node["title"], node.get("titleLang"))
        if isinstance(node.get("subtitle"), str):
            pair(f"{path}.subtitle", node["subtitle"], node.get("subtitleLang"))
        for key in ("mediaDesc", "versionDesc", "note"):
            if key in node:
                span(f"{path}.{key}", node[key])
        if "by" in node:
            by(f"{path}.by", node["by"])
        if "length" in node:
            length(f"{path}.length", node["length"])
        if "ratings" in node:
            items(
                f"{path}.ratings",
                node["ratings"],
                ("score", "label", "abbrTerm", "abbrDef"),
            )
        if "platforms" in node:
            items(
                f"{path}.platforms",
                node["platforms"],
                ("name", "paren", "prefix", "suffix", "text"),
            )
        if "languages" in node:
            items(f"{path}.languages", node["languages"], ("tip",))
        for key, value in node.items():
            if key in (
                "tags",
                "by",
                "mediaDesc",
                "versionDesc",
                "note",
                "length",
                "ratings",
                "platforms",
                "languages",
                "searchTitle",
            ):
                continue
            if isinstance(value, (dict, list)):
                walk(f"{path}.{key}", value)

    walk("$", instance)
    return out


def main():
    if not DATA.is_dir():
        print("validate-data: no site/data/ -- nothing to check")
        return 0

    store = SchemaStore(SCHEMAS)
    findings = []
    checked = 0
    allowed_name_override_keys = load_name_override_keys()

    lang_warnings = []
    marker_usage = {"Essential": [], "Optional": []}
    tag_spellings = {}
    for path in sorted(DATA.glob("*.js")):
        text = path.read_text(encoding="utf-8")
        try:
            decls = list(find_declarations(text))
        except ParseError as e:
            findings.append((path.name, [f"parse error: {e}"]))
            continue
        for schema_ref, instance in decls:
            check(path.name, instance, schema_ref, store, findings)
            checked += 1
            if schema_ref.startswith("group.schema.json"):
                check_sections(path.name, instance, findings)
                check_contents_orders(path.name, instance, findings)
                check_platform_link_modes(path.name, instance, findings)
                check_more_platforms(path.name, instance, findings)
                check_markers(path.name, instance, findings, marker_usage)
                check_tag_style(path.name, instance, findings, tag_spellings)
                for where, text, reason in check_lang_coverage(instance):
                    lang_warnings.append((path.name, where, text, reason))
                if allowed_name_override_keys is not None:
                    check_name_overrides(
                        path.name, instance, allowed_name_override_keys, findings
                    )

    check_marker_usage(marker_usage, findings)
    check_tag_spellings(tag_spellings, findings)

    if lang_warnings and "--warn-lang" not in sys.argv:
        by_file = {}
        for name, where, text, reason in lang_warnings:
            by_file.setdefault(name, []).append(f"{where}: {reason}: {text[:60]!r}")
        for name, errs in by_file.items():
            findings.append((name, errs))

    if findings:
        total = sum(len(errs) for _, errs in findings)
        print(f"validate-data: {total} error(s) across {len(findings)} file(s):")
        for label, errs in findings:
            print(f"  {label}:")
            for e in errs:
                print(f"    {e}")
        return 1

    print(
        f"validate-data: checked {checked} declared schema(s) across site/data/*.js, no errors"
    )
    if lang_warnings:
        files = {name for name, *_ in lang_warnings}
        print(
            f"validate-data: lang: {len(lang_warnings)} warning(s) in {len(files)} file(s) "
            "(non-Latin text without a matching lang, --warn-lang; --lang lists them)"
        )
        if "--lang" in sys.argv:
            for name, where, text, reason in lang_warnings:
                print(f"  {name} {where}: {reason}: {text[:70]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
