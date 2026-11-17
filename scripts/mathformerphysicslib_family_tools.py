# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned MCP bindings for the registered physics-library runner invocation."""

from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from threading import RLock
from uuid import uuid4
import sys
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner

ARGV = ["--module-family", "mathformerphysicslib", "--json"]


class Parsed(TypedDict):
    args: dict
    context: dict


class Entered(TypedDict):
    snapshot_only: bool


class Stateful(TypedDict):
    state: dict


class Guarded(TypedDict):
    remaining: bool


class Reported(TypedDict):
    report: dict


class Published(TypedDict):
    exit_code: int


def register_mathformerphysicslib_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def allowed():
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise PermissionError(
                "physics-library artifacts outside service write roots"
            )
        return native

    def owned(context, args=None, state=None, phases=()):
        native = allowed()
        scope = scopes.get(context.get("handle"))
        if (
            scope is None
            or (phases and scope["phase"] not in phases)
            or (args is not None and args != scope["serialized"])
            or (state is not None and state != scope.get("state"))
        ):
            raise ValueError(
                "unknown, modified, consumed or out-of-order physics-library context"
            )
        return native, scope

    @mcp.tool()
    def mathformer_physicslib_parse(invocation: dict) -> Parsed:
        with lock:
            native = allowed()
            if (
                set(invocation) != {"argv", "selected_row_count"}
                or invocation["argv"] != ARGV
                or type(invocation["selected_row_count"]) is not int
                or not 0 <= invocation["selected_row_count"] <= 15
            ):
                raise ValueError(
                    "fixed physics-library argv and selected row count 0..15 required"
                )
            args = native.parse_args(invocation["argv"])
            serialized = {
                k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
            }
            handle = uuid4().hex
            scopes[handle] = dict(
                args=args,
                serialized=deepcopy(serialized),
                phase="enter",
                count=invocation["selected_row_count"],
            )
            return {"args": serialized, "context": {"handle": handle}}

    @mcp.tool()
    def mathformer_physicslib_enter(args: dict, context: dict) -> Entered:
        with lock:
            native, scope = owned(context, args, phases=("enter",))
            snapshot = native.enter_checks(scope["args"])
            scope["phase"] = "snapshot" if snapshot else "prepare"
            return {"snapshot_only": snapshot}

    @mcp.tool()
    def mathformer_physicslib_snapshot_frame(context: dict) -> Stateful:
        with lock:
            _, scope = owned(context, phases=("snapshot",))
            state = dict(matrix=[], selected=[], families=[], index=0, results=[])
            scope["state"] = deepcopy(state)
            return {"state": state}

    @mcp.tool()
    def mathformer_physicslib_prepare(args: dict, context: dict) -> Stateful:
        with lock:
            native, scope = owned(context, args, phases=("prepare",))
            try:
                state = native.prepare_checks(scope["args"])
                if len(state["selected"]) != scope["count"]:
                    raise ValueError(
                        "selected row count differs from invocation precondition"
                    )
            except BaseException:
                scopes.pop(context["handle"])
                raise
            scope.update(state=deepcopy(state), phase="guard")
            return {"state": state}

    @mcp.tool()
    def mathformer_physicslib_cursor_guard(state: dict, context: dict) -> Guarded:
        with lock:
            _, scope = owned(
                context,
                state=state,
                phases=("snapshot", "guard", "advance", "finalize"),
            )
            remaining = state["index"] < len(state["selected"])
            if scope["phase"] != "snapshot":
                scope["phase"] = "advance" if remaining else "finalize"
            return {"remaining": remaining}

    @mcp.tool()
    def mathformer_physicslib_retain(state: dict, context: dict) -> Stateful:
        with lock:
            owned(context, state=state, phases=("snapshot", "finalize"))
            if state["selected"] or state["index"] or state["results"]:
                raise ValueError("inactive empty cursor required")
            return {"state": state}

    @mcp.tool()
    def mathformer_physicslib_advance(
        state: dict, args: dict, context: dict
    ) -> Stateful:
        with lock:
            native, scope = owned(context, args, state, ("advance",))
            try:
                state = native.advance_check(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"])
                raise
            scope.update(state=deepcopy(state), phase="guard")
            return {"state": state}

    def report_step(args, context, state, snapshot):
        native, scope = owned(
            context, args, state, ("snapshot",) if snapshot else ("finalize",)
        )
        try:
            report = (
                native.snapshot_report(scope["args"])
                if snapshot
                else native.finalize_checks(scope["state"], scope["args"])
            )
        except BaseException:
            scopes.pop(context["handle"])
            raise
        scope.update(report=deepcopy(report), phase="publish")
        return {"report": report}

    @mcp.tool()
    def mathformer_physicslib_snapshot(args: dict, context: dict) -> Reported:
        with lock:
            return report_step(args, context, None, True)

    @mcp.tool()
    def mathformer_physicslib_finalize(
        state: dict, args: dict, context: dict
    ) -> Reported:
        with lock:
            return report_step(args, context, state, False)

    @mcp.tool()
    def mathformer_physicslib_publish(
        report: dict, args: dict, context: dict
    ) -> Published:
        with lock:
            native, scope = owned(context, args, phases=("publish",))
            if report != scope["report"]:
                raise ValueError("modified physics-library report")
            scopes.pop(context["handle"])
            with redirect_stdout(sys.stderr):
                code = native.publish_report(scope["report"], scope["args"])
            return {"exit_code": code}
