# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Shared, contradiction-resistant release status for physics workflows."""

from __future__ import annotations

from typing import Any, Iterable, Mapping


ARTIFACT_STATUSES = {
    "not_evaluated",
    "experimental",
    "draft",
    "candidate",
    "promoted",
    "blocked",
    "archived",
}
LIBRARY_STATUSES = {"not_evaluated", "accepted", "warn", "blocked"}
BLOCKING_TERMINAL_STATES = {
    "recurse",
    "needs_expansion",
    "repair_required",
    "complete_with_blockers",
    "blocked",
    "stale",
    "compile_failed",
}


def build_release_status(
    *,
    workflow_executed: bool,
    checks_passed: bool,
    artifact_status: str,
    library_status: str,
    blockers: Iterable[str] = (),
    terminal_states: Iterable[str] = (),
) -> dict[str, Any]:
    """Build the authoritative status fields and derive ``release_ok``."""

    blocker_list = sorted({str(item) for item in blockers if str(item)})
    state_list = sorted({str(item) for item in terminal_states if str(item)})
    if artifact_status not in ARTIFACT_STATUSES:
        raise ValueError(f"unknown artifact_status: {artifact_status}")
    if library_status not in LIBRARY_STATUSES:
        raise ValueError(f"unknown library_status: {library_status}")
    terminal_blockers = sorted(set(state_list) & BLOCKING_TERMINAL_STATES)
    all_blockers = sorted(set(blocker_list) | {f"terminal_state:{state}" for state in terminal_blockers})
    release_ok = (
        workflow_executed
        and checks_passed
        and artifact_status == "promoted"
        and library_status == "accepted"
        and not all_blockers
    )
    return {
        "status_schema_version": 1,
        "workflow_executed": bool(workflow_executed),
        "checks_passed": bool(checks_passed),
        "artifact_status": artifact_status,
        "library_status": library_status,
        "release_ok": release_ok,
        "blockers": all_blockers,
        "terminal_states": state_list,
    }


def validate_release_status(payload: Mapping[str, Any]) -> list[str]:
    """Return explicit errors for missing or contradictory status fields."""

    required = {
        "workflow_executed",
        "checks_passed",
        "artifact_status",
        "library_status",
        "release_ok",
        "blockers",
        "terminal_states",
    }
    errors = [f"missing status field: {field}" for field in sorted(required - set(payload))]
    if errors:
        return errors
    try:
        derived = build_release_status(
            workflow_executed=bool(payload["workflow_executed"]),
            checks_passed=bool(payload["checks_passed"]),
            artifact_status=str(payload["artifact_status"]),
            library_status=str(payload["library_status"]),
            blockers=payload.get("blockers") or (),
            terminal_states=payload.get("terminal_states") or (),
        )
    except (TypeError, ValueError) as exc:
        return [str(exc)]
    if bool(payload["release_ok"]) != derived["release_ok"]:
        errors.append(
            f"release_ok={payload['release_ok']!r} contradicts derived value {derived['release_ok']!r}"
        )
    if payload.get("artifact_status") == "promoted" and not payload.get("checks_passed"):
        errors.append("promoted artifact requires checks_passed")
    return errors
