# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#
#
"""Validate stored domain-package versions against the runnable PRISM contract.

The command accepts package-version directories (directories containing a
``manifest.json``) or a storage directory containing such versions. It never
executes package code and never changes imported files.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
BACKEND_CANDIDATES = (
    ROOT / "app" / "backend",
    ROOT.parent / "lunar-platform" / "app" / "backend",
)
LUNAR_BACKEND = next(
    (
        candidate
        for candidate in BACKEND_CANDIDATES
        if (candidate / "domain_packages").is_dir()
    ),
    None,
)
if LUNAR_BACKEND is None:
    raise RuntimeError(
        "Lunar backend not found; expected app/backend in this checkout or "
        "a sibling lunar-platform checkout"
    )
sys.path.insert(0, str(LUNAR_BACKEND))

contract = importlib.import_module("domain_packages.format.contract")
PackageValidationError = contract.PackageValidationError
validate_manifest = contract.validate_manifest
validate_payloads = contract.validate_payloads
derive = importlib.import_module("domain_packages.format.source_workflows").derive


def package_roots(paths: Iterable[Path]) -> list[Path]:
    """Find package-version roots without descending into packaged repositories."""
    found: set[Path] = set()
    for supplied in paths:
        path = supplied.resolve()
        if (path / "manifest.json").is_file():
            found.add(path)
            continue
        for manifest in path.glob("*/*/*/manifest.json"):
            found.add(manifest.parent)
    return sorted(found)


def validate_package(root: Path) -> list[str]:
    """Return all runnable-contract errors that can be established offline."""
    errors: list[str] = []
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return [f"cannot read package: {exc}"]
    try:
        validate_manifest(manifest)
    except PackageValidationError as exc:
        errors.append(str(exc))
    payloads = {}
    missing_payloads = []
    for row in manifest.get("files", []):
        path = root / row["path"]
        if path.is_file():
            payloads[row["path"]] = path.read_bytes()
        else:
            missing_payloads.append(row["path"])
    documents = {"repository": []}
    if not missing_payloads:
        try:
            documents = validate_payloads(manifest, payloads)
        except PackageValidationError as exc:
            errors.append(str(exc))

    # Derivation is also inspected directly so the command can report semantic
    # execution problems alongside a general package-contract error.
    try:
        bundle, registrations = derive(
            manifest, payloads, documents.get("repository", [])
        )
    except (PackageValidationError, KeyError, OSError) as exc:
        if str(exc) not in errors:
            errors.append(str(exc))
        return errors

    projects = cast(list[dict[str, Any]], bundle["projects"])
    views = {
        workflow["id"]: workflow
        for project in projects
        for workflow in project["workflows"]
    }
    mathformer_contracts = None
    contract_path = "repository/runtime/workflow-inputs.json"
    if contract_path in payloads:
        try:
            mathformer_contracts = json.loads(payloads[contract_path])
        except (TypeError, json.JSONDecodeError) as exc:
            errors.append(f"invalid Mathformer workflow contracts: {exc}")
    mapped: dict[str, list[dict]] = {}
    for registration in registrations:
        modes = registration.get("modes")
        if modes is not None:
            errors.append(
                f"{registration['id']}: execution modes are not allowed ({modes!r})"
            )
        metadata = registration.get("metadata", {})
        for legacy_key in ("mode_input_schemas", "planner_mode_bindings"):
            if legacy_key in metadata:
                errors.append(
                    f"{registration['id']}: metadata.{legacy_key} is not allowed"
                )
        viewer_id = metadata.get("viewer_workflow_id", registration["id"])
        mapped.setdefault(viewer_id, []).append(registration)

    for view_id in views:
        bound = mapped.get(view_id, [])
        if not bound:
            errors.append(
                f"{view_id}: reasoning workflow has no execution registration"
            )
            continue
        for registration in bound:
            entry = Path(registration["entry_file"])
            material_main = root / entry.parent / "material_main.prism"
            if material_main.is_file() and entry.name != "material_main.prism":
                errors.append(
                    f"{registration['id']}: executes {entry.as_posix()} instead of "
                    f"the packaged material implementation "
                    f"{(entry.parent / 'material_main.prism').as_posix()}"
                )
            if (
                mathformer_contracts is not None
                and registration.get("prepare_hook") == "mathformer-workflow-prepare"
            ):
                if registration.get("execute_hook") != "mathformer-workflow-execute":
                    errors.append(
                        f"{registration['id']}: Mathformer reasoning must use the "
                        "identity-normalizing execution hook"
                    )
                contract = mathformer_contracts.get(registration["id"], {})
                expected = view_id.rpartition(":")[2]
                if contract.get("reasoning_workflow") != expected:
                    errors.append(
                        f"{registration['id']}: runtime reasoning identity "
                        f"{contract.get('reasoning_workflow')!r} does not match "
                        f"the host-derived contract {expected!r}"
                    )

    return list(dict.fromkeys(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[ROOT / "storage"],
        help="package-version root or storage root (default: ./storage)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)
    roots = package_roots(args.paths)
    results = {str(root): validate_package(root) for root in roots}
    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        for root, errors in results.items():
            print(root + (": valid" if not errors else ":"))
            for error in errors:
                print(f"  - {error}")
        print(
            f"Validated {len(results)} imported package(s); "
            f"{sum(bool(errors) for errors in results.values())} invalid."
        )
    return int(any(results.values()) or not results)


if __name__ == "__main__":
    raise SystemExit(main())
