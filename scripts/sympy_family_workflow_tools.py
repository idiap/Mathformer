# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned MCP ports over the native SymPy matrix traversal.

Only canonical rows can execute. Parse-time defaults and full native cursor
state stay server-owned; transported state and reports are assertions.
"""

from contextlib import redirect_stdout
from copy import deepcopy
import sys
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner


class RuntimeContext(TypedDict):
    handle: str


class Prepared(TypedDict):
    state: dict
    context: RuntimeContext


class Updated(TypedDict):
    state: dict


class Guarded(TypedDict):
    pending: bool
    cursor: dict


class Reported(TypedDict):
    report: dict


class Published(TypedDict):
    exit_code: int


INVOCATION = dict(
    module_family="sympy",
    profile="workstation",
    extra_args=[],
    selected_rows_upper_bound=4096,
)


def register_sympy_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def allowed():
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise PermissionError("SymPy artifacts outside service write roots")
        return native

    def owned(context, phase, state=None, invocation=None):
        native = allowed()
        scope = scopes.get(context.get("handle"))
        if scope is None or scope["phase"] != phase:
            raise ValueError("unknown, consumed or out-of-order SymPy context")
        if state is not None and state != scope["state"]:
            raise ValueError("modified or replayed SymPy state")
        if invocation is not None and invocation != INVOCATION:
            raise ValueError("invocation must equal registered SymPy defaults")
        return native, scope

    @mcp.tool()
    def mathformer_sympy_family_prepare(invocation: dict) -> Prepared:
        """Enter the native runner, load the matrix and select SymPy rows once."""
        if invocation != INVOCATION:
            raise ValueError("invocation must equal registered SymPy defaults")
        with lock:
            native = allowed()
            args = native.parse_args(["--module-family", "sympy", "--json"])
            if native.enter_checks(args):
                raise ValueError(
                    "snapshot branch is outside the SymPy hub specialization"
                )
            state = native.prepare_checks(args)
            if len(state["selected"]) > 4096:
                raise ValueError("SymPy selection exceeds contract bound of 4096")
            for row in state["selected"]:
                for path in row.get("write_set") or ():
                    if not path_allowed((native.REPO_ROOT / path).resolve()):
                        raise PermissionError(
                            "SymPy check writes outside service write roots"
                        )
            handle = uuid4().hex
            scopes[handle] = dict(args=args, state=deepcopy(state), phase="pending")
            return {"state": state, "context": {"handle": handle}}

    @mcp.tool()
    def mathformer_sympy_family_pending(
        state: dict, context: RuntimeContext
    ) -> Guarded:
        """Evaluate the shared native while guard without executing a row."""
        with lock:
            native, scope = owned(context, "pending", state)
            pending = native.checks_pending(scope["state"])
            scope["phase"] = "advance" if pending else "finalize"
            return {"pending": pending, "cursor": {"state": state, "pending": pending}}

    @mcp.tool()
    def mathformer_sympy_family_retain_empty(
        cursor: dict, context: RuntimeContext
    ) -> Guarded:
        """Transport zero native iterations through PRISM's at-least-once loop."""
        with lock:
            owned(context, "finalize", cursor["state"])
            state = cursor["state"]
            if (
                cursor != {"state": state, "pending": False}
                or state["selected"]
                or state["results"]
                or state["index"]
            ):
                raise ValueError("empty SymPy selection required")
            return {"cursor": cursor, "pending": False}

    @mcp.tool()
    def mathformer_sympy_family_advance(
        state: dict, invocation: dict, context: RuntimeContext
    ) -> Updated:
        """Execute exactly one native row, retaining failures as result data."""
        with lock:
            native, scope = owned(context, "advance", state, invocation)
            try:
                updated = native.advance_check(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(state=deepcopy(updated), phase="pending")
            return {"state": updated}

    @mcp.tool()
    def mathformer_sympy_family_finalize(
        state: dict, invocation: dict, context: RuntimeContext
    ) -> Reported:
        """Validate results, build the native ledger and write its snapshot."""
        with lock:
            native, scope = owned(context, "finalize", state, invocation)
            try:
                report = native.finalize_checks(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_sympy_family_publish(
        report: dict, context: RuntimeContext
    ) -> Published:
        """Publish native JSON, retaining its stdout on the MCP stderr stream."""
        with lock:
            native, scope = owned(context, "publish")
            if report != scope["report"]:
                raise ValueError("modified SymPy report")
            if not path_allowed(scope["args"].output_file):
                raise PermissionError("SymPy report outside service write roots")
            scopes.pop(context["handle"])
            with redirect_stdout(sys.stderr):
                code = native.publish_report(scope["report"], scope["args"])
            return {"exit_code": code}
