# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned MCP bindings for the fixed native Lean matrix traversal."""

from contextlib import redirect_stdout
from copy import deepcopy
from threading import RLock
from uuid import uuid4
import sys
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner

FIXED = dict(
    module_family=["lean"],
    profile="workstation",
    emit_dependency_map_only=False,
    fail_on_warning=False,
    changed_files_only=False,
    validate_matrix=False,
    json=True,
)


class Entered(TypedDict):
    context: dict
    snapshot_only: bool


class Advanced(TypedDict):
    state: dict
    done: bool


class Reported(TypedDict):
    report: dict


class Published(TypedDict):
    exit_code: int


def register_lean_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def allowed():
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise PermissionError("Lean artifacts outside service write roots")
        return native

    def owned(context, args, phase, state=None):
        allowed()
        scope = scopes.get(context.get("handle"))
        if (
            scope is None
            or scope["phase"] != phase
            or args != FIXED
            or (state is not None and state != scope.get("state"))
        ):
            raise ValueError("unknown, modified, consumed or out-of-order Lean context")
        return scope

    @mcp.tool()
    def mathformer_lean_family_enter(args: dict) -> Entered:
        with lock:
            native = allowed()
            if args != FIXED:
                raise ValueError("args must assert the fixed hub Lean invocation")
            parsed = native.parse_args(["--module-family", "lean", "--json"])
            snapshot = native.enter_checks(parsed)
            handle = uuid4().hex
            scopes[handle] = dict(
                args=parsed, phase="snapshot" if snapshot else "prepare"
            )
            return {"context": {"handle": handle}, "snapshot_only": snapshot}

    @mcp.tool()
    def mathformer_lean_family_snapshot(args: dict, context: dict) -> Reported:
        with lock:
            scope = owned(context, args, "snapshot")
            report = source_runner().snapshot_report(scope["args"])
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_lean_family_prepare(
        args: dict, domain: dict, context: dict
    ) -> Advanced:
        with lock:
            scope = owned(context, args, "prepare")
            if (
                domain != {"max_selected_rows": 4096}
                or type(domain["max_selected_rows"]) is not int
            ):
                raise ValueError("domain must declare 4096 selected rows")
            state = source_runner().prepare_checks(scope["args"])
            if len(state["selected"]) > 4096:
                scopes.pop(context["handle"])
                raise ValueError("Lean selection exceeds contract bound of 4096")
            done = state["index"] >= len(state["selected"])
            scope.update(state=deepcopy(state), phase="finalize" if done else "advance")
            return {"state": state, "done": done}

    @mcp.tool()
    def mathformer_lean_family_retain_empty(
        state: dict, args: dict, context: dict
    ) -> Advanced:
        with lock:
            owned(context, args, "finalize", state)
            if state["selected"] or state["results"] or state["index"] != 0:
                raise ValueError("empty Lean selection required")
            return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_lean_family_advance(
        state: dict, args: dict, context: dict
    ) -> Advanced:
        with lock:
            scope = owned(context, args, "advance", state)
            try:
                state = source_runner().advance_check(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"])
                raise
            done = state["index"] >= len(state["selected"])
            scope.update(state=deepcopy(state), phase="finalize" if done else "advance")
            return {"state": state, "done": done}

    @mcp.tool()
    def mathformer_lean_family_finalize(
        state: dict, args: dict, context: dict
    ) -> Reported:
        with lock:
            scope = owned(context, args, "finalize", state)
            try:
                report = source_runner().finalize_checks(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"])
                raise
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_lean_family_publish(
        report: dict, args: dict, context: dict
    ) -> Published:
        with lock:
            scope = owned(context, args, "publish")
            if report != scope["report"]:
                raise ValueError("modified Lean report")
            scopes.pop(context["handle"])
            with redirect_stdout(sys.stderr):
                code = source_runner().publish_report(scope["report"], scope["args"])
            return {"exit_code": code}
