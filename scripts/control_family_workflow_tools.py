# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Workstation control-family runner blocks using the native cursor implementation.

Canonical selection assertions and owned state prevent a transported cursor from
becoming an arbitrary command interface. Context retains parse-time defaults.
"""

from contextlib import redirect_stdout
from copy import deepcopy
import sys
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner


class Context(TypedDict):
    run_id: str


class RuntimeContext(TypedDict):
    handle: str


class Prepared(TypedDict):
    state: dict
    context: RuntimeContext


class Updated(TypedDict):
    state: dict


class Guarded(TypedDict):
    pending: bool


class Retained(TypedDict):
    state: dict
    pending: bool


class Reported(TypedDict):
    report: dict


class Published(TypedDict):
    exit_code: int


def register_control_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def owned(context, state=None, phase=None):
        scope = scopes.get(context["handle"])
        if scope is None:
            raise ValueError("unknown or consumed control_family context")
        if (state is not None and state != scope["state"]) or (
            phase and scope["phase"] != phase
        ):
            raise ValueError("modified or out-of-order control_family state")
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise ValueError("control_family artifacts outside service write roots")
        return scope

    @mcp.tool()
    def mathformer_control_family_prepare(domain: dict, context: Context) -> Prepared:
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise ValueError("control_family artifacts outside service write roots")
        with lock:
            native.ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
            args = native.parse_args(
                ["--module-family", "control", "--json", "--run-id", context["run_id"]]
            )
            state = native.prepare_checks(args)
            if len(state["selected"]) > 1024 or domain != {
                "selected_count": len(state["selected"])
            }:
                raise ValueError(
                    "domain must match canonical selection, at most 1024 rows"
                )
            handle = uuid4().hex
            scopes[handle] = {"args": args, "state": deepcopy(state), "phase": "guard"}
            return {"state": state, "context": {"handle": handle}}

    @mcp.tool()
    def mathformer_control_family_cursor_guard(
        state: dict, context: RuntimeContext
    ) -> Guarded:
        with lock:
            scope = owned(context, state, "guard")
            pending = state["index"] < len(state["selected"])
            scope["phase"] = "advance" if pending else "finalize"
            return {"pending": pending}

    @mcp.tool()
    def mathformer_control_family_advance(
        state: dict, context: RuntimeContext
    ) -> Updated:
        with lock:
            scope = owned(context, state, "advance")
            try:
                state = source_runner().advance_check(state, scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(state=deepcopy(state), phase="guard")
            return {"state": state}

    @mcp.tool()
    def mathformer_control_family_retain_empty(
        state: dict, context: RuntimeContext
    ) -> Retained:
        with lock:
            owned(context, state, "finalize")
            if state["selected"] or state["results"] or state["index"] != 0:
                raise ValueError("retain_empty requires empty selection")
            return {"state": state, "pending": False}

    @mcp.tool()
    def mathformer_control_family_finalize(
        state: dict, context: RuntimeContext
    ) -> Reported:
        with lock:
            scope = owned(context, state, "finalize")
            try:
                report = source_runner().finalize_checks(state, scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_control_family_publish(
        report: dict, context: RuntimeContext
    ) -> Published:
        with lock:
            scope = owned(context, phase="publish")
            if report != scope["report"]:
                raise ValueError("modified control_family report")
            scopes.pop(context["handle"])
            native, args = source_runner(), scope["args"]
            # Preserve source JSON output on stderr; stdout belongs to MCP.
            with redirect_stdout(sys.stderr):
                code = native.publish_report(report, args)
            return {"exit_code": code}
