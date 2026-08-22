#!/usr/bin/env python3
# Copyright (c) 2026 Carnegie Mellon University
# SPDX-License-Identifier: BSD-3-Clause-Clear
"""Validate airstack-modules-index registry entries against the entry schemas.

The registry follows the rosdistro pattern (RFC #379 §7): one YAML per entry,
``modules/<name>.yaml`` validated against ``schema/module-entry.schema.json`` and
``stacks/<name>.yaml`` against ``schema/stack-entry.schema.json``. This validator
mirrors trunk's ``tools/validate_module.py``: python3 stdlib + PyYAML (deliberately
no ``jsonschema`` dependency), interpreting the schemas with a small generic walker
so schema evolution normally requires no code changes here.

The walker understands the draft-07 subset the schemas keep to — ``type``,
``required``, ``properties``, ``enum``, ``pattern``, ``items``,
``additionalProperties``, ``minLength``, ``minItems`` — plus the custom
``x-airstack-format`` annotations:

- ``semver-range`` — space-separated comparators over full ``X.Y.Z`` semvers
  (``airstack_compat``); branch names and partial versions are invalid.
- ``sha-or-tag`` — a full 40-hex commit SHA or a ``vX.Y.Z`` tag
  (``registered_ref``); branch names are invalid because branch refs rot silently.
- ``safe-relative-path`` — no absolute paths, no ``..`` escapes (``wiring``).

Beyond the schema, two registry-level cross-checks per entry:

- the entry's ``name`` must match its filename stem (``modules/optitrack.yaml``
  must declare ``name: optitrack``), so catalog lookups never diverge;
- duplicate names across entries of the same kind are an error.

CLI::

    validate_entry.py                 # validate every modules/*.yaml + stacks/*.yaml
    validate_entry.py modules/x.yaml  # validate specific entry file(s)

Human-readable errors go to stderr; a JSON verdict
``{"valid": bool, "errors": [{"entry", "path", "message"}]}`` goes to stdout;
exit 0 when valid, 1 otherwise.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# entry kind -> (entries dir, schema file)
KINDS = {
    "modules": REPO_ROOT / "schema" / "module-entry.schema.json",
    "stacks": REPO_ROOT / "schema" / "stack-entry.schema.json",
}

# ── generic walker (mirrors trunk tools/validate_module.py) ────────────────

_JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}

_SEMVER = (
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z][0-9A-Za-z.-]*)?"
    r"(?:\+[0-9A-Za-z][0-9A-Za-z.-]*)?"
)
_COMPARATOR_RE = re.compile(r"^(?:>=|<=|>|<|==|=|\^|~)?" + _SEMVER + r"$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_TAG_RE = re.compile(r"^v" + _SEMVER + r"$")


def _check_semver_range(value):
    """Validate a semver range like ``>=0.19.0 <0.21.0`` (same rule as trunk)."""
    tokens = value.split()
    if not tokens:
        return "empty semver range"
    for token in tokens:
        if not _COMPARATOR_RE.match(token):
            return (
                f"invalid semver range component {token!r} — expected an optional "
                "operator (>=, <=, >, <, ==, =, ^, ~) followed by a full X.Y.Z "
                "semver, e.g. \">=0.19.0 <0.21.0\""
            )
    return None


def _check_sha_or_tag(value):
    """A pinned ref: full 40-hex commit SHA or a vX.Y.Z tag — never a branch."""
    if _SHA_RE.match(value) or _TAG_RE.match(value):
        return None
    return (
        f"invalid registered_ref {value!r} — expected a full 40-hex commit SHA "
        "or a vX.Y.Z tag (branch names rot silently and are not allowed)"
    )


def _check_safe_relative_path(value):
    """A repo-relative path: non-empty, not absolute, no ``..`` escapes."""
    if not value:
        return "path must be non-empty"
    if value.startswith(("/", "\\", "~")) or re.match(r"^[A-Za-z]:[/\\]", value):
        return f"path must be relative, got {value!r}"
    if ".." in Path(value).parts:
        return f"path must not escape the repo via '..', got {value!r}"
    return None


_FORMAT_CHECKS = {
    "semver-range": _check_semver_range,
    "sha-or-tag": _check_sha_or_tag,
    "safe-relative-path": _check_safe_relative_path,
}


def _join(path, key):
    return f"{path}.{key}" if path else str(key)


def _type_ok(value, type_spec):
    types = type_spec if isinstance(type_spec, list) else [type_spec]
    for name in types:
        expected = _JSON_TYPES.get(name)
        if expected is None:
            continue
        # bool is a subclass of int in Python; keep JSON semantics strict.
        if isinstance(value, bool) and name in ("integer", "number"):
            continue
        if isinstance(value, expected):
            return True
    return False


def _type_names(type_spec):
    return type_spec if isinstance(type_spec, list) else [type_spec]


class _Context:
    """Collects errors for one entry during the walk."""

    def __init__(self, entry):
        self.entry = entry
        self.errors = []

    def error(self, path, message):
        self.errors.append(
            {"entry": self.entry, "path": path or "(root)", "message": message}
        )


def _walk(value, schema, path, ctx):
    """Apply one schema node to one instance node, recursing into properties/items."""
    if "type" in schema and not _type_ok(value, schema["type"]):
        ctx.error(
            path,
            f"expected type {' or '.join(_type_names(schema['type']))}, "
            f"got {type(value).__name__}",
        )
        return
    if value is None:
        return  # a nullable field left null — string/object keywords do not apply

    if "enum" in schema and value not in schema["enum"]:
        ctx.error(path, f"{value!r} is not one of {schema['enum']}")
        return

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            ctx.error(path, f"must be at least {schema['minLength']} characters")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            ctx.error(path, f"{value!r} does not match pattern {schema['pattern']!r}")
        fmt = schema.get("x-airstack-format")
        if fmt:
            msg = _FORMAT_CHECKS[fmt](value)
            if msg:
                ctx.error(path, msg)

    elif isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                ctx.error(_join(path, key), "required property is missing")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    ctx.error(_join(path, key), "unknown property (additionalProperties: false)")
        for key, subschema in properties.items():
            if key in value:
                _walk(value[key], subschema, _join(path, key), ctx)

    elif isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            ctx.error(path, f"must have at least {schema['minItems']} item(s)")
        if "items" in schema:
            for i, item in enumerate(value):
                _walk(item, schema["items"], f"{path}[{i}]", ctx)


# ── entry points ───────────────────────────────────────────────────────────

def _load_schema(schema_path):
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def _kind_of(entry_path):
    """'modules' or 'stacks' from the entry's parent directory name."""
    kind = entry_path.parent.name
    return kind if kind in KINDS else None


def validate_entry(entry_path, schema):
    """Validate one entry file. Returns a list of error dicts."""
    entry_path = Path(entry_path)
    label = str(entry_path)
    ctx = _Context(label)

    try:
        with entry_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        ctx.error("(file)", f"entry not found: {entry_path}")
        return ctx.errors, None
    except yaml.YAMLError as exc:
        ctx.error("(file)", f"invalid YAML: {exc}")
        return ctx.errors, None

    if not isinstance(data, dict):
        ctx.error("(root)", "entry top level must be a mapping")
        return ctx.errors, None

    _walk(data, schema, "", ctx)

    # Registry cross-check: filename stem must match the declared name so the
    # catalog and `airstack module add <name>` can never disagree about identity.
    declared = data.get("name")
    if isinstance(declared, str) and declared != entry_path.stem:
        ctx.error(
            "name",
            f"{declared!r} does not match the entry filename stem "
            f"{entry_path.stem!r} — the file must be named <name>.yaml",
        )

    return ctx.errors, declared


def validate_all(targets=None):
    """Validate the given entry files (default: every modules/*.yaml + stacks/*.yaml).

    Returns the stable JSON verdict shape
    ``{"valid": bool, "errors": [{"entry", "path", "message"}]}``.
    """
    if targets:
        paths = [Path(t) for t in targets]
    else:
        paths = [
            p
            for kind in KINDS
            for p in sorted((REPO_ROOT / kind).glob("*.yaml"))
        ]

    errors = []
    seen = {}  # (kind, name) -> first entry path, for duplicate detection
    schemas = {kind: _load_schema(path) for kind, path in KINDS.items()}

    for path in paths:
        kind = _kind_of(path)
        if kind is None:
            errors.append(
                {
                    "entry": str(path),
                    "path": "(file)",
                    "message": "entry must live under modules/ or stacks/",
                }
            )
            continue
        entry_errors, declared = validate_entry(path, schemas[kind])
        errors.extend(entry_errors)
        if isinstance(declared, str):
            key = (kind, declared)
            if key in seen:
                errors.append(
                    {
                        "entry": str(path),
                        "path": "name",
                        "message": f"duplicate {kind} entry name {declared!r} "
                        f"(also declared by {seen[key]})",
                    }
                )
            else:
                seen[key] = str(path)

    if not paths:
        errors.append(
            {
                "entry": "(registry)",
                "path": "(root)",
                "message": "no entries found under modules/ or stacks/",
            }
        )

    return {"valid": not errors, "errors": errors}, len(paths)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate registry entries (modules/*.yaml, stacks/*.yaml) "
        "against schema/."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="entry files to validate (default: every modules/*.yaml + stacks/*.yaml)",
    )
    args = parser.parse_args(argv)

    verdict, checked = validate_all(args.targets)
    for error in verdict["errors"]:
        print(
            f"error: {error['entry']}: {error['path']}: {error['message']}",
            file=sys.stderr,
        )
    if verdict["valid"]:
        print(f"{checked} registry entr{'y is' if checked == 1 else 'ies are'} valid",
              file=sys.stderr)
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
