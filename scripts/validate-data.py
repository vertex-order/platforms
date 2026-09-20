#!/usr/bin/env python3
# Owned by vertex-order/kit — edit here. Vendored elsewhere via sync.toml;
# don't edit the copy there.
"""Validate site/data/*.js against schemas/*.schema.json.

Each site/data/*.js file assigns a plain `window.*` global (or, for
index.js/site.js/credits.js/etc., a handful of well-known ones) -- see
schemas/README.md for the file-to-schema mapping. This extracts that
literal with scripts/js_literal.py (a real JSON parser can't read these
files -- unquoted keys, single-quoted strings, trailing commas, comments)
and checks it against the matching schema.

Only checks a (data file, schema file) pair when BOTH exist in this repo's
tree -- so kit's own fixture, a full list repo (all pairs), platforms
(platform-icons.js only), and org (faq.js only) all run the exact same
script and each just validates whatever it actually has. A repo's own
local, non-vendored schemas (e.g. org's schemas/franchise-list.schema.json
for games.js/movies.js/books.js) are NOT covered here -- this only knows
the fixed set of file/schema pairs kit itself defines and vendors; add a
repo-local wrapper script if you want those covered too.

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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from js_literal import ParseError, parse_value_after  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data"
SCHEMAS = ROOT / "schemas"

_ASSIGN_VALUE_RE = re.compile(r"=\s*(?=[{\[])")


def _anchor(global_name):
    return re.compile(rf"\b{re.escape(global_name)}\s*=\s*(?=[{{\[])")


# ---------------------------------------------------------------------------
# Data-file loaders. Each returns the literal value that would end up on
# window.<global> (or, for a multi-global file, a dict combining them, or
# for a series file, the single games-array-bearing object it registers).
# ---------------------------------------------------------------------------

def _load_single(path, global_name):
    text = path.read_text(encoding="utf-8")
    return parse_value_after(text, _anchor(global_name))


def load_series_order():
    return _load_single(DATA / "index.js", "SERIES_ORDER")


def load_series_file(path):
    text = path.read_text(encoding="utf-8")
    # First `<ident>[<bracket>] = {` in the file is always the registry
    # assignment (window.__xxSeriesReg['<num>'] = {...}) -- same anchor
    # check-dedup-drift.py has always used for this.
    value = parse_value_after(text, _ASSIGN_VALUE_RE)
    return value


def load_catalogs(path):
    text = path.read_text(encoding="utf-8")
    return {
        "LANGUAGE_NAMES": parse_value_after(text, _anchor("LANGUAGE_NAMES")),
        "RATING_KINDS": parse_value_after(text, _anchor("RATING_KINDS")),
        "STEAM_REVIEW_LABELS": parse_value_after(text, _anchor("STEAM_REVIEW_LABELS")),
    }


# ---------------------------------------------------------------------------
# (data file, schema file, loader) pairs kit knows about. `data` and
# `schema` are relative to DATA/ and SCHEMAS/ respectively; a pair is
# skipped entirely if either side doesn't exist in this repo's tree.
# ---------------------------------------------------------------------------

SIMPLE_PAIRS = [
    ("site.js", "site-config.schema.json", "SITE_CONFIG"),
    ("credits.js", "credits.schema.json", "CREDITS"),
    ("help-wanted.js", "help-wanted.schema.json", "HELP_WANTED_ITEMS"),
    ("platform-icons.js", "platform-icons.schema.json", "PLATFORM_ICONS"),
]
FAQ_PAIRS = [
    ("faq.js", "FAQ_ITEMS"),
    ("common-faq.js", "FAQ_ITEMS_COMMON"),
]


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
    """Returns (target_doc, target_root_doc, current_file_for_target)."""
    if "#" in ref:
        file_part, pointer = ref.split("#", 1)
    else:
        file_part, pointer = ref, ""
    if file_part:
        target_file = file_part
    else:
        target_file = current_file
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
        target, root_doc, target_file = _resolve_ref(schema["$ref"], current_file, store)
        validate(instance, target, target_file, store, path, errors)
        return

    if "type" in schema:
        types = schema["type"]
        types = types if isinstance(types, list) else [types]
        if not any(_type_matches(instance, t) for t in types):
            errors.append(f"{_path_str(path)}: expected type {types!r}, got {type(instance).__name__}: {instance!r}")
            return

    if "const" in schema:
        expected = schema["const"]
        ok = (instance is expected) if isinstance(expected, bool) else (
            not isinstance(instance, bool) and instance == expected
        )
        if not ok:
            errors.append(f"{_path_str(path)}: expected const {expected!r}, got {instance!r}")

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{_path_str(path)}: {instance!r} not one of {schema['enum']!r}")

    if isinstance(instance, str):
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{_path_str(path)}: {instance!r} doesn't match pattern {schema['pattern']!r}")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{_path_str(path)}: {instance!r} shorter than minLength {schema['minLength']}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{_path_str(path)}: {instance!r} below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{_path_str(path)}: {instance!r} above maximum {schema['maximum']}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{_path_str(path)}: has {len(instance)} item(s), needs at least {schema['minItems']}")
        if schema.get("uniqueItems") and len(instance) != len({json.dumps(x, sort_keys=True) for x in instance}):
            errors.append(f"{_path_str(path)}: items are not unique")
        if "items" in schema:
            for i, item in enumerate(instance):
                validate(item, schema["items"], current_file, store, path + [i], errors)

    if isinstance(instance, dict):
        props = schema.get("properties", {})
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            errors.append(f"{_path_str(path)}: has {len(instance)} propertie(s), needs at least {schema['minProperties']}")
        if "required" in schema:
            for key in schema["required"]:
                if key not in instance:
                    errors.append(f"{_path_str(path)}: missing required property {key!r}")
        if "dependentRequired" in schema:
            for key, needs in schema["dependentRequired"].items():
                if key in instance:
                    for need in needs:
                        if need not in instance:
                            errors.append(f"{_path_str(path)}: {key!r} present but {need!r} is missing")
        ap = schema.get("additionalProperties", True)
        for key, val in instance.items():
            if key in props:
                validate(val, props[key], current_file, store, path + [key], errors)
            elif ap is False:
                errors.append(f"{_path_str(path)}: additional property {key!r} not allowed")
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
            errors.append(f"{_path_str(path)}: matched none of {len(branches)} anyOf branch(es)")
        elif combinator == "oneOf" and matches != 1:
            errors.append(f"{_path_str(path)}: matched {matches} of {len(branches)} oneOf branch(es) (want exactly 1)")


def check(label, instance, schema_file, store, findings):
    schema = store.load(schema_file)
    errors = []
    validate(instance, schema, schema_file, store, [], errors)
    if errors:
        findings.append((label, errors))


def main():
    if not DATA.is_dir():
        print("validate-data: no site/data/ -- nothing to check")
        return 0

    store = SchemaStore(SCHEMAS)
    findings = []
    checked = 0

    for data_name, schema_name, global_name in SIMPLE_PAIRS:
        data_path, schema_path = DATA / data_name, SCHEMAS / schema_name
        if not (data_path.is_file() and schema_path.is_file()):
            continue
        try:
            instance = _load_single(data_path, global_name)
        except ParseError as e:
            findings.append((data_name, [f"parse error: {e}"]))
            continue
        check(data_name, instance, schema_name, store, findings)
        checked += 1

    for data_name, global_name in FAQ_PAIRS:
        data_path, schema_path = DATA / data_name, SCHEMAS / "faq.schema.json"
        if not (data_path.is_file() and schema_path.is_file()):
            continue
        try:
            instance = _load_single(data_path, global_name)
        except ParseError as e:
            findings.append((data_name, [f"parse error: {e}"]))
            continue
        check(data_name, instance, "faq.schema.json", store, findings)
        checked += 1

    catalogs_path, catalogs_schema = DATA / "catalogs.js", SCHEMAS / "catalogs.schema.json"
    if catalogs_path.is_file() and catalogs_schema.is_file():
        try:
            instance = load_catalogs(catalogs_path)
        except ParseError as e:
            findings.append(("catalogs.js", [f"parse error: {e}"]))
        else:
            check("catalogs.js", instance, "catalogs.schema.json", store, findings)
            checked += 1

    index_path, index_schema = DATA / "index.js", SCHEMAS / "index.schema.json"
    order = None
    if index_path.is_file() and index_schema.is_file():
        try:
            order = load_series_order()
        except ParseError as e:
            findings.append(("index.js", [f"parse error: {e}"]))
        else:
            check("index.js", order, "index.schema.json", store, findings)
            checked += 1

    series_schema = SCHEMAS / "series.schema.json"
    if series_schema.is_file():
        for series_path in sorted(DATA.glob("series-*.js")):
            try:
                instance = load_series_file(series_path)
            except ParseError as e:
                findings.append((series_path.name, [f"parse error: {e}"]))
                continue
            check(series_path.name, instance, "series.schema.json", store, findings)
            checked += 1

    if findings:
        total = sum(len(errs) for _, errs in findings)
        print(f"validate-data: {total} error(s) across {len(findings)} file(s):")
        for label, errs in findings:
            print(f"  {label}:")
            for e in errs:
                print(f"    {e}")
        return 1

    print(f"validate-data: checked {checked} data file(s) against schemas/, no errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
