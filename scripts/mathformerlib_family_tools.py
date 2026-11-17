# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned MCP ports for the native mathformerlib runner, with revision admission."""

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from threading import RLock
from uuid import uuid4
import sys
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner


class Entered(TypedDict):
    snapshot_only: bool
    context: dict


class Stateful(TypedDict):
    state: dict


class Guarded(TypedDict):
    remaining: bool
    cursor: dict


class Reported(TypedDict):
    report: dict


class Published(TypedDict):
    exit_code: int


def native_args(args):
    """Admit the candidate's explicit runner flags, keeping fixed family and paths."""
    booleans = (
        "changed_files_only",
        "emit_dependency_map_only",
        "fail_on_warning",
        "validate_matrix",
        "json",
    )
    keys = set(booleans) | {
        "module_family",
        "profile",
        "run_id",
        "output_file",
        "write_jsonl",
        "write_junit",
    }
    if (
        set(args) != keys
        or args["module_family"] != ["mathformerlib"]
        or args["profile"] not in ("workstation", "strict")
        or args["changed_files_only"] is not False
        or not isinstance(args["run_id"], str)
        or any(type(args[k]) is not bool for k in booleans)
        or args["output_file"] != "artifacts/test_program/deterministic_tests.json"
        or args["write_jsonl"]
        not in (None, "artifacts/test_program/deterministic_tests.jsonl")
        or args["write_junit"]
        not in (None, "artifacts/test_program/deterministic_tests.xml")
    ):
        raise ValueError("unsupported mathformerlib runner arguments")
    return argparse.Namespace(**deepcopy(args))


def register_mathformerlib_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def allowed():
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise PermissionError("mathformerlib artifacts outside service write roots")
        return native

    def owned(context, args=None, state=None, phase=None):
        allowed()
        scope = scopes.get(context.get("handle"))
        if (
            scope is None
            or (args is not None and args != vars(scope["args"]))
            or (state is not None and state != scope.get("state"))
            or (phase is not None and scope["phase"] != phase)
        ):
            raise ValueError(
                "unknown, modified, consumed or out-of-order mathformerlib context"
            )
        return scope

    @mcp.tool()
    def mathformer_mathformerlib_enter(args: dict) -> Entered:
        with lock:
            native = allowed()
            parsed = native_args(args)
            snapshot_only = native.enter_checks(parsed)
            handle = uuid4().hex
            scopes[handle] = {
                "args": parsed,
                "phase": "snapshot" if snapshot_only else "prepare",
            }
            return {"snapshot_only": snapshot_only, "context": {"handle": handle}}

    @mcp.tool()
    def mathformer_mathformerlib_snapshot(args: dict, context: dict) -> Reported:
        with lock:
            scope = owned(context, args, phase="snapshot")
            try:
                report = source_runner().snapshot_report(scope["args"])
            except BaseException:
                scopes.pop(context["handle"])
                raise
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_mathformerlib_prepare(
        args: dict, matrix_revision: str, context: dict
    ) -> Stateful:
        with lock:
            scope = owned(context, args, phase="prepare")
            native = source_runner()
            if (
                matrix_revision
                != "sha256:"
                + hashlib.sha256(native.MATRIX_FILE.read_bytes()).hexdigest()
            ):
                raise ValueError("canonical matrix revision mismatch")
            try:
                state = native.prepare_checks(scope["args"])
            except BaseException:
                scopes.pop(context["handle"])
                raise
            if len(state["selected"]) > 2:
                scopes.pop(context["handle"])
                raise ValueError(
                    "mathformerlib selection exceeds the two-row specialization"
                )
            for row in state["selected"]:
                for path in row.get("write_set") or ():
                    if not path_allowed((native.REPO_ROOT / path).resolve()):
                        scopes.pop(context["handle"])
                        raise PermissionError(
                            "mathformerlib check writes outside service write roots"
                        )
            scope.update(state=deepcopy(state), phase="guard")
            return {"state": state}

    @mcp.tool()
    def mathformer_mathformerlib_snapshot_frame(context: dict) -> Stateful:
        """Transport an inactive cursor; do not load or execute the matrix."""
        with lock:
            scope = owned(context, phase="snapshot")
            state = dict(matrix=[], selected=[], families=[], index=0, results=[])
            scope["state"] = deepcopy(state)
            return {"state": state}

    @mcp.tool()
    def mathformer_mathformerlib_retain(state: dict, context: dict) -> Stateful:
        """Carry only a consumed cursor through the root loop's inactive branch."""
        with lock:
            scope = owned(context, state=state)
            if scope["phase"] not in ("snapshot", "finalize") or state["index"] != len(
                state["selected"]
            ):
                raise ValueError("consumed cursor required")
            return {"state": state}

    @mcp.tool()
    def mathformer_mathformerlib_remaining(state: dict, context: dict) -> Guarded:
        with lock:
            scope = owned(context, state=state)
            if scope["phase"] == "snapshot":
                return {
                    "remaining": False,
                    "cursor": {"state": state, "remaining": False},
                }
            # Guards are pure and may be repeated at a root-loop boundary.
            if scope["phase"] not in ("guard", "advance", "finalize"):
                raise ValueError("out-of-order cursor guard")
            remaining = source_runner().checks_pending(scope["state"])
            scope["phase"] = "advance" if remaining else "finalize"
            return {
                "remaining": remaining,
                "cursor": {"state": state, "remaining": remaining},
            }

    @mcp.tool()
    def mathformer_mathformerlib_retain_cursor(cursor: dict, context: dict) -> Guarded:
        """Carry a zero-check frame through the at-least-once runtime loop."""
        with lock:
            state = cursor["state"]
            scope = owned(context, state=state)
            if (
                scope["phase"] not in ("snapshot", "finalize")
                or cursor != {"state": state, "remaining": False}
                or state["selected"]
                or state["index"]
                or state["results"]
            ):
                raise ValueError("empty or inactive mathformerlib cursor required")
            return {"remaining": False, "cursor": cursor}

    @mcp.tool()
    def mathformer_mathformerlib_advance(
        state: dict, args: dict, context: dict
    ) -> Stateful:
        with lock:
            scope = owned(context, args, state, "advance")
            try:
                state = source_runner().advance_check(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"])
                raise
            scope.update(state=deepcopy(state), phase="guard")
            return {"state": state}

    @mcp.tool()
    def mathformer_mathformerlib_finalize(
        state: dict, args: dict, context: dict
    ) -> Reported:
        with lock:
            scope = owned(context, args, state, "finalize")
            try:
                report = source_runner().finalize_checks(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"])
                raise
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_mathformerlib_publish(
        report: dict, args: dict, context: dict
    ) -> Published:
        with lock:
            scope = owned(context, args, phase="publish")
            if report != scope["report"]:
                raise ValueError("modified mathformerlib report")
            scopes.pop(context["handle"])
            with redirect_stdout(sys.stderr):
                code = source_runner().publish_report(scope["report"], scope["args"])
            return {"exit_code": code}
