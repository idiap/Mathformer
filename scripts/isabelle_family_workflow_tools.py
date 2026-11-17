# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned MCP cursors over the native default Isabelle test invocation.

Arguments and commands are parsed/loaded by the source, never supplied by clients.
Publication captures the native CLI output to keep JSON-RPC stdout intact.
"""

from copy import deepcopy
import contextlib
import io
from pathlib import Path
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner


class Prepared(TypedDict):
    state: dict
    context: dict


class Updated(TypedDict):
    state: dict


class Pending(TypedDict):
    pending: bool


class Retained(TypedDict):
    state: dict
    pending: bool


class Finalized(TypedDict):
    report: dict


class Published(TypedDict):
    publication: dict


def register_isabelle_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def allowed():
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise ValueError("Isabelle artifacts outside service write roots")
        return native

    def owned(context, state, phase):
        allowed()
        scope = scopes.get(context.get("handle"))
        if scope is None or scope["phase"] != phase or state != scope["state"]:
            raise ValueError(
                "unknown, modified, consumed or out-of-order Isabelle cursor"
            )
        return scope

    @mcp.tool()
    def mathformer_isabelle_family_prepare(scope: dict) -> Prepared:
        """Create artifacts and load the fixed native Isabelle selection once."""
        with lock:
            native = allowed()
            if (
                scope != {"max_selected_checks": 5}
                or type(scope["max_selected_checks"]) is not int
            ):
                raise ValueError("scope must declare the five-row Isabelle domain")
            args = native.parse_args(["--module-family", "isabelle", "--json"])
            native.ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
            state = native.prepare_checks(args)
            if len(state["selected"]) > 5:
                raise ValueError("Isabelle selection exceeds contract bound of 5")
            state["args"] = {
                k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
            }
            handle = uuid4().hex
            scopes[handle] = dict(args=args, state=deepcopy(state), phase="pending")
            return {"state": state, "context": {"handle": handle}}

    @mcp.tool()
    def mathformer_isabelle_family_pending(state: dict, context: dict) -> Pending:
        """Evaluate the source loop guard without changing the cursor."""
        with lock:
            scope = owned(context, state, "pending")
            pending = state["index"] < len(state["selected"])
            scope["phase"] = "advance" if pending else "finalize"
            return {"pending": pending}

    @mcp.tool()
    def mathformer_isabelle_family_retain_empty(state: dict, context: dict) -> Retained:
        """Retain the native zero-iteration result after its guard."""
        with lock:
            owned(context, state, "finalize")
            if state["selected"] or state["results"] or state["index"] != 0:
                raise ValueError("empty Isabelle selection required")
            return {"state": state, "pending": False}

    @mcp.tool()
    def mathformer_isabelle_family_advance(state: dict, context: dict) -> Updated:
        """Run one native check, including its timeout and write audit."""
        with lock:
            scope = owned(context, state, "advance")
            try:
                state = source_runner().advance_check(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(state=deepcopy(state), phase="pending")
            return {"state": state}

    @mcp.tool()
    def mathformer_isabelle_family_finalize(state: dict, context: dict) -> Finalized:
        """Validate consumed results and write the native dependency snapshot."""
        with lock:
            scope = owned(context, state, "finalize")
            try:
                report = source_runner().finalize_checks(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_isabelle_family_publish(
        state: dict, report: dict, context: dict
    ) -> Published:
        """Publish the native report and preserve CLI output and exit status."""
        with lock:
            scope = owned(context, state, "publish")
            if report != scope["report"]:
                raise ValueError("modified Isabelle report")
            scopes.pop(context["handle"])
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = source_runner().publish_report(scope["report"], scope["args"])
            return {
                "publication": {
                    "report_path": str(scope["args"].output_file),
                    "exit_code": code,
                    "stdout": stream.getvalue(),
                }
            }
