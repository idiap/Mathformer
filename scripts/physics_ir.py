#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

"""Build a backend-neutral physics IR from one JSON source record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libraries.MathformerPhysicsLib.physics_ir import (
    PhysicsDerivationIR,
    Quantity,
    Assumption,
    Obligation,
    ProjectionBridge,
    from_case_spec,
    validate_ir,
)


def parse_arguments(argv=None, *, prog=None):
    parser = argparse.ArgumentParser(description=__doc__, prog=prog)
    parser.add_argument("--source-record", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def resolve_path(path, working_directory=None):
    path = Path(path)
    return Path(working_directory) / path if working_directory is not None else path


def load_request(argv=None, *, working_directory=None, prog=None):
    args = parse_arguments(argv, prog=prog)
    record = json.loads(
        resolve_path(args.source_record, working_directory).read_text(encoding="utf-8")
    )
    return {
        "record": record,
        "case_id": str(record.get("case_id") or args.source_record.stem),
        "steps": record.get("steps") or record.get("obligations") or (),
        "projection_bridges": record.get("projection_bridges") or (),
        "output": str(args.output) if args.output else None,
        "write_output": bool(args.output),
        "json_output": args.json,
        "halted": False,
        "stdout": "",
    }


def convert_request(request):
    return from_case_spec(
        request["case_id"],
        request["record"],
        steps=request["steps"],
        projection_bridges=request["projection_bridges"],
    )


def ir_from_dict(value):
    """Restore the dataclass at the JSON transport boundary, without conversion."""
    return PhysicsDerivationIR(
        **{
            key: item
            for key, item in value.items()
            if key
            not in {"quantities", "assumptions", "obligations", "projection_bridges"}
        },
        quantities=tuple(Quantity(**item) for item in value["quantities"]),
        assumptions=tuple(Assumption(**item) for item in value["assumptions"]),
        obligations=tuple(Obligation(**item) for item in value["obligations"]),
        projection_bridges=tuple(
            ProjectionBridge(**item) for item in value["projection_bridges"]
        ),
    )


def package_report(ir, errors):
    artifact_status = "candidate" if not errors and ir.obligations else "blocked"
    payload = {
        "schema_version": 1,
        "style": "physics_ir_build_report",
        "ok": not errors,
        "artifact_status": artifact_status,
        "blockers": errors or ([] if ir.obligations else ["no_derivation_obligations"]),
        "physics_ir": ir.to_dict(),
        "physics_ir_digest": ir.ir_digest,
    }
    return payload


def write_report(request, payload, *, working_directory=None):
    output = resolve_path(request["output"], working_directory)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def emit_report(request, payload):
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if request["json_output"] or not request["output"]
        else payload["artifact_status"]
    )
    return 0 if payload["ok"] else 3


def main() -> int:
    request = load_request()
    ir = convert_request(request)
    errors = validate_ir(ir)
    payload = package_report(ir, errors)
    if request["write_output"]:
        write_report(request, payload)
    return emit_report(request, payload)


if __name__ == "__main__":
    raise SystemExit(main())
