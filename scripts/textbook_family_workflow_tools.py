# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for the fixed textbook family invocation of the native test runner.

Only canonical matrix rows execute. Parsed arguments, cursors and publication
remain server-owned; transported values are assertions, never command sources.
"""

from contextlib import redirect_stdout
from copy import deepcopy
import io
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict

from comprehensive_strict_tools import source_runner

INVOCATION = dict(
    module_family=["textbook"],
    json=True,
    profile="workstation",
    fail_on_warning=False,
    changed_files_only=False,
    validate_matrix=False,
    emit_dependency_map_only=False,
    write_jsonl=None,
    write_junit=None,
    selected_row_cap=4,
)


class Entered(TypedDict):
    context: dict


class Prepared(TypedDict):
    state: dict


class Guarded(TypedDict):
    pending: bool
    cursor: dict


class Finalized(TypedDict):
    report: dict


class Published(TypedDict):
    exit_code: int
    publication: dict


def register_textbook_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def allowed():
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise PermissionError(
                "textbook family artifacts outside service write roots"
            )
        return native

    def owned(context, phase, state=None, invocation=None):
        native = allowed()
        scope = scopes.get(context.get("handle"))
        if scope is None or scope["phase"] != phase:
            raise ValueError(
                "unknown, consumed or out-of-order textbook family context"
            )
        if state is not None and state != scope["state"]:
            raise ValueError("modified or replayed textbook family state")
        if invocation is not None and invocation != INVOCATION:
            raise ValueError("invocation must equal registered textbook defaults")
        return native, scope

    @mcp.tool()
    def mathformer_textbook_family_enter(
        invocation: dict, selection_bound: int
    ) -> Entered:
        """Parse the exact hub defaults once and enter the native runner."""
        with lock:
            native = allowed()
            if selection_bound != 4 or type(selection_bound) is not int:
                raise ValueError("selection_bound must be four")
            if (
                invocation != INVOCATION
                or type(invocation.get("selected_row_cap")) is not int
            ):
                raise ValueError("invocation must equal registered textbook defaults")
            args = native.parse_args(["--module-family", "textbook", "--json"])
            if native.enter_checks(args):
                raise ValueError("registered invocation must enter checks")
            handle = uuid4().hex
            scopes[handle] = dict(args=args, phase="prepare")
            return {"context": {"handle": handle}}

    @mcp.tool()
    def mathformer_textbook_family_prepare(invocation: dict, context: dict) -> Prepared:
        """Load and select the canonical matrix, preserving matrix order."""
        with lock:
            native, scope = owned(context, "prepare", invocation=invocation)
            try:
                state = native.prepare_checks(scope["args"])
                if len(state["selected"]) > 4:
                    raise ValueError("textbook selection exceeds contract bound of 4")
                for row in state["selected"]:
                    for path in row.get("write_set") or ():
                        if not path_allowed((native.REPO_ROOT / path).resolve()):
                            raise PermissionError(
                                "textbook check writes outside service write roots"
                            )
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(state=deepcopy(state), phase="guard")
            return {"state": state}

    @mcp.tool()
    def mathformer_textbook_family_cursor_guard(state: dict, context: dict) -> Guarded:
        """Evaluate the native while condition, including zero iterations."""
        with lock:
            native, scope = owned(context, "guard", state)
            pending = native.checks_pending(scope["state"])
            scope["phase"] = "advance" if pending else "finalize"
            return {"pending": pending, "cursor": {"state": state, "pending": pending}}

    @mcp.tool()
    def mathformer_textbook_family_retain_empty(cursor: dict, context: dict) -> Guarded:
        """Carry the zero-check path through the runtime's at-least-once loop."""
        with lock:
            owned(context, "finalize", cursor["state"])
            state = cursor["state"]
            if (
                cursor != {"state": state, "pending": False}
                or state["selected"]
                or state["results"]
                or state["index"]
            ):
                raise ValueError("empty textbook selection required")
            return {"cursor": cursor, "pending": False}

    @mcp.tool()
    def mathformer_textbook_family_advance(
        state: dict, invocation: dict, context: dict
    ) -> Prepared:
        """Execute exactly one source check; failures and skips remain results."""
        with lock:
            native, scope = owned(context, "advance", state, invocation)
            try:
                updated = native.advance_check(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(state=deepcopy(updated), phase="guard")
            return {"state": updated}

    @mcp.tool()
    def mathformer_textbook_family_finalize(
        state: dict, invocation: dict, context: dict
    ) -> Finalized:
        """Validate exhaustion/results, aggregate evidence and write the snapshot."""
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
    def mathformer_textbook_family_publish(
        report: dict, invocation: dict, context: dict
    ) -> Published:
        """Write the native JSON and return its CLI stdout and exit status."""
        with lock:
            native, scope = owned(context, "publish", invocation=invocation)
            if report != scope["report"]:
                raise ValueError("modified textbook family report")
            scopes.pop(context["handle"])
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = native.publish_report(scope["report"], scope["args"])
            return {
                "exit_code": code,
                "publication": {
                    "output_file": str(
                        (native.REPO_ROOT / scope["args"].output_file).resolve()
                    ),
                    "exit_code": code,
                    "stdout": stream.getvalue(),
                },
            }
