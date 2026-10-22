#!/usr/bin/env python3
"""Validate specs/<part>/spec.yaml files against schemas/spec.schema.json.

Structural gate for the spec-driven workflow: catches broken spec structure
before any model or test reads it. Also enforces that the `part` field
matches the specs/<part>/ directory name.

Usage:
    python tools/validate_spec.py                      # validate every spec
    python tools/validate_spec.py specs/foo/spec.yaml  # validate one file

Exit code 0 = all valid, 1 = any failure (suitable for CI).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "spec.schema.json"


def display(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def validate_file(schema: dict, path: Path) -> list[str]:
    """Return a list of human-readable errors (empty list = valid)."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        return [f"  <file>: not readable/parseable: {exc}"]

    errors: list[str] = []
    validator = Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
        errors.append(f"  {loc}: {err.message}")

    if isinstance(data, dict) and data.get("part") != path.parent.name:
        errors.append(
            f"  <root>: part field {data.get('part')!r} does not match "
            f"directory name {path.parent.name!r}"
        )
    return errors


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    args = [Path(a) for a in sys.argv[1:]]
    targets = args or sorted((REPO_ROOT / "specs").glob("*/spec.yaml"))
    if not targets:
        print("error: no spec files found", file=sys.stderr)
        return 1

    failed = False
    for path in targets:
        errors = validate_file(schema, path)
        print(f"[{'FAIL' if errors else 'OK'}] {display(path)}")
        for message in errors:
            print(message)
            failed = True

    if failed:
        print("spec validation FAILED", file=sys.stderr)
        return 1
    print(f"all {len(targets)} spec file(s) valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())