# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned callable cursors over the native meta_skills matrix invocation.

The source parses defaults and loads commands. Transported states and reports
are assertions against server-owned values, never alternate command sources.
"""

from contextlib import redirect_stdout
from copy import deepcopy
import io
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict

from comprehensive_strict_tools import source_runner

INVOCATION = dict(
    module_family=["meta_skills"],
    profile="workstation",
    json=True,
    emit_dependency_map_only=False,
    changed_files_only=False,
    validate_matrix=False,
    fail_on_warning=False,
    write_jsonl=None,
    write_junit=None,
    selected_row_cap=3,
)


class Prepared(TypedDict):
    state: dict
    context: dict


class Advanced(TypedDict):
    state: dict


class Guarded(TypedDict):
    pending: bool
    cursor: dict


class Finalized(TypedDict):
    report: dict


class Published(TypedDict):
    exit_code: int
    publication: dict


def register_meta_skills_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def allowed():
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise PermissionError("meta_skills artifacts outside service write roots")
        return native

    def invocation_valid(invocation):
        if (
            invocation != INVOCATION
            or type(invocation.get("selected_row_cap")) is not int
        ):
            raise ValueError("invocation must equal registered meta_skills defaults")

    def owned(context, phase, state=None, invocation=None):
        native = allowed()
        scope = scopes.get(context.get("handle"))
        if scope is None or scope["phase"] != phase:
            raise ValueError("unknown, consumed or out-of-order meta_skills context")
        if state is not None and state != scope["state"]:
            raise ValueError("modified or replayed meta_skills state")
        if invocation is not None:
            invocation_valid(invocation)
        return native, scope

    @mcp.tool()
    def mathformer_meta_skills_family_prepare(invocation: dict) -> Prepared:
        """Parse exact hub defaults, enter the runner, and load its ordered rows."""
        with lock:
            native = allowed()
            invocation_valid(invocation)
            args = native.parse_args(["--module-family", "meta_skills", "--json"])
            if native.enter_checks(args):
                raise ValueError("registered invocation must enter checks")
            state = native.prepare_checks(args)
            if len(state["selected"]) > 3:
                raise ValueError("meta_skills selection exceeds contract bound of 3")
            for row in state["selected"]:
                for path in row.get("write_set") or ():
                    if not path_allowed((native.REPO_ROOT / path).resolve()):
                        raise PermissionError(
                            "meta_skills check writes outside service write roots"
                        )
            handle = uuid4().hex
            scopes[handle] = dict(args=args, state=deepcopy(state), phase="pending")
            return {"state": state, "context": {"handle": handle}}

    @mcp.tool()
    def mathformer_meta_skills_family_pending(state: dict, context: dict) -> Guarded:
        """Evaluate the native while condition, including zero iterations."""
        with lock:
            native, scope = owned(context, "pending", state)
            pending = native.checks_pending(scope["state"])
            scope["phase"] = "advance" if pending else "finalize"
            return {"pending": pending, "cursor": {"state": state, "pending": pending}}

    @mcp.tool()
    def mathformer_meta_skills_family_retain_empty(
        cursor: dict, context: dict
    ) -> Guarded:
        """Carry zero checks through PRISM's at-least-once loop without a check."""
        with lock:
            owned(context, "finalize", cursor["state"])
            state = cursor["state"]
            if (
                cursor != {"state": state, "pending": False}
                or state["selected"]
                or state["results"]
                or state["index"]
            ):
                raise ValueError("empty meta_skills selection required")
            return {"cursor": cursor, "pending": False}

    @mcp.tool()
    def mathformer_meta_skills_family_advance(
        state: dict, invocation: dict, context: dict
    ) -> Advanced:
        """Run one native check; failed and skipped results continue traversal."""
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
    def mathformer_meta_skills_family_finalize(
        state: dict, invocation: dict, context: dict
    ) -> Finalized:
        """Validate consumed results, aggregate evidence and write the snapshot."""
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
    def mathformer_meta_skills_family_publish(
        report: dict, invocation: dict, context: dict
    ) -> Published:
        """Publish native JSON and return CLI stdout without corrupting JSON-RPC."""
        with lock:
            native, scope = owned(context, "publish", invocation=invocation)
            if report != scope["report"]:
                raise ValueError("modified meta_skills report")
            scopes.pop(context["handle"])
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = native.publish_report(scope["report"], scope["args"])
            return {
                "exit_code": code,
                "publication": {
                    "report_path": str(scope["args"].output_file),
                    "stdout": stream.getvalue(),
                },
            }
