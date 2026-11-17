#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.
#
# Intent:
#   Tell coding agents what context to load, what invariants to preserve, and how to validate their work.
#
# Function:
#   Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Normalize Mathformer phase-gate decisions from structured checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence

TRUE_VALUES = {"1", "true", "yes", "y", "pass", "passed", "ok"}
FALSE_VALUES = {"0", "false", "no", "n", "fail", "failed", "error"}
VALID_SEVERITIES = {"info", "low", "medium", "high", "critical"}


def parse_bool(value: Any) -> bool:
    """Document the responsibility of ``parse_bool``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    raise ValueError(f"Expected boolean value, got: {value!r}")


def normalize_severity(value: Any) -> str:
    """Document the responsibility of ``normalize_severity``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_severity`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = str(value or "medium").strip().lower()
    if text not in VALID_SEVERITIES:
        raise ValueError(f"Invalid severity: {value!r}")
    return text


def normalize_waiver(raw: Any) -> Dict[str, Any]:
    """Document the responsibility of ``normalize_waiver``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_waiver`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if isinstance(raw, dict):
        check_id = str(raw.get("id") or raw.get("check_id") or "").strip()
        if not check_id:
            raise ValueError("Waiver object is missing id/check_id.")
        return {
            "id": check_id,
            "reason": str(raw.get("reason", "")).strip(),
            "owner": str(raw.get("owner", "")).strip(),
            "expiry": str(raw.get("expiry", "")).strip(),
            "residual_risk": str(raw.get("residual_risk", "")).strip(),
        }

    token = str(raw).strip()
    if not token:
        raise ValueError("Waiver token is empty.")
    parts = token.split(":", 4)
    return {
        "id": parts[0].strip(),
        "owner": parts[1].strip() if len(parts) > 1 else "",
        "expiry": parts[2].strip() if len(parts) > 2 else "",
        "reason": parts[3].strip() if len(parts) > 3 else "",
        "residual_risk": parts[4].strip() if len(parts) > 4 else "",
    }


def normalize_check(
    raw: Dict[str, Any],
    *,
    waiver_lookup: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Document the responsibility of ``normalize_check``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    check_id = str(raw.get("id") or raw.get("check_id") or "").strip()
    if not check_id:
        raise ValueError("Gate check is missing id.")
    passed = parse_bool(raw.get("passed", raw.get("ok", False)))
    severity = normalize_severity(raw.get("severity", "medium"))
    blocking = parse_bool(raw.get("blocking", severity in {"high", "critical"}))
    message = str(raw.get("message", "")).strip()
    waiver = waiver_lookup.get(check_id)
    result = {
        "id": check_id,
        "passed": passed,
        "severity": severity,
        "blocking": blocking,
        "message": message,
        "waived": waiver is not None,
    }
    if waiver is not None:
        result["waiver"] = waiver
    return result


def decide_gate(
    *,
    gate_id: str,
    hook_id: Optional[str],
    checks: Sequence[Dict[str, Any]],
    waivers: Sequence[Any] = (),
) -> Dict[str, Any]:
    """Document the responsibility of ``decide_gate``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``decide_gate`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    waiver_records = [normalize_waiver(item) for item in waivers]
    waiver_lookup = {item["id"]: item for item in waiver_records}
    normalized = [normalize_check(item, waiver_lookup=waiver_lookup) for item in checks]
    failed = [item for item in normalized if not item["passed"]]
    blocking_failures = [
        item for item in failed if item["blocking"] and not item["waived"]
    ]
    waived_failures = [item for item in failed if item["blocking"] and item["waived"]]
    warnings = [item for item in failed if not item["blocking"] and not item["waived"]]

    if not normalized:
        status = "skip"
    elif blocking_failures:
        status = "fail"
    elif waived_failures and not warnings:
        status = "waived"
    elif warnings or waived_failures:
        status = "warn"
    else:
        status = "pass"

    return {
        "gate_id": gate_id,
        "hook_id": hook_id,
        "status": status,
        "ok": status in {"pass", "warn", "waived", "skip"},
        "checks": normalized,
        "blocking_failures": blocking_failures,
        "warnings": warnings,
        "waivers": waiver_records,
    }


def parse_check_token(token: str) -> Dict[str, Any]:
    """Parse id=passed[:severity][:blocking][:message]."""
    if "=" not in token:
        raise ValueError(f"Check must use id=value format: {token!r}")
    check_id, rest = token.split("=", 1)
    parts = rest.split(":", 3)
    check: Dict[str, Any] = {
        "id": check_id.strip(),
        "passed": parts[0].strip(),
    }
    if len(parts) > 1 and parts[1].strip():
        check["severity"] = parts[1].strip()
    if len(parts) > 2 and parts[2].strip():
        check["blocking"] = parts[2].strip()
    if len(parts) > 3:
        check["message"] = parts[3]
    return check


def load_input_file(path: Path) -> Dict[str, Any]:
    """Document the responsibility of ``load_input_file``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Gate input JSON must be an object.")
    return parsed


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Document the responsibility of ``parse_args``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate-id", required=False)
    parser.add_argument("--hook-id")
    parser.add_argument("--input-file", type=Path)
    parser.add_argument("--check", action="append", default=[])
    parser.add_argument("--waiver", action="append", default=[])
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def render_text(decision: Dict[str, Any]) -> str:
    """Document the responsibility of ``render_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = [
        f"gate_id: {decision['gate_id']}",
        f"status: {decision['status']}",
        f"ok: {decision['ok']}",
        f"checks: {len(decision['checks'])}",
        f"blocking_failures: {len(decision['blocking_failures'])}",
        f"warnings: {len(decision['warnings'])}",
    ]
    for item in decision["blocking_failures"]:
        lines.append(f"- fail {item['id']}: {item['message']}")
    for item in decision["warnings"]:
        lines.append(f"- warn {item['id']}: {item['message']}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    args = parse_args(argv)
    input_data: Dict[str, Any] = {}
    if args.input_file is not None:
        input_data = load_input_file(args.input_file)

    checks: List[Dict[str, Any]] = []
    raw_checks = input_data.get("checks", [])
    if raw_checks:
        if not isinstance(raw_checks, list):
            raise ValueError("input-file checks must be a list.")
        checks.extend(raw_checks)
    checks.extend(parse_check_token(token) for token in args.check)

    waivers = list(input_data.get("waivers", [])) + list(args.waiver)
    decision = decide_gate(
        gate_id=args.gate_id or input_data.get("gate_id") or "unnamed-gate",
        hook_id=args.hook_id or input_data.get("hook_id"),
        checks=checks,
        waivers=waivers,
    )
    decision["mode"] = (
        "audit-only"
        if args.audit_only
        else "fail-fast" if args.fail_fast else "advisory"
    )
    if args.json:
        print(json.dumps(decision, ensure_ascii=False, indent=2))
    else:
        print(render_text(decision))
    return (
        3
        if args.fail_fast and not args.audit_only and decision["status"] == "fail"
        else 0
    )


if __name__ == "__main__":
    sys.exit(main())
