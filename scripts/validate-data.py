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
from js_literal import ParseError, parse_value

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


def main():
    if not DATA.is_dir():
        print("validate-data: no site/data/ -- nothing to check")
        return 0

    store = SchemaStore(SCHEMAS)
    findings = []
    checked = 0

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
