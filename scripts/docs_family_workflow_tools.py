# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Docs-family MCP steps over the authoritative comprehensive runner.

The server owns parsed defaults and cursor histories. Transported state is an
assertion of that history, never a caller-supplied command source.
"""

from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
import sys
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner


class Prepared(TypedDict):
    args: dict
    state: dict
    context: dict


class Updated(TypedDict):
    state: dict


class Retained(TypedDict):
    state: dict
    done: bool


class Guarded(TypedDict):
    done: bool


class Finalized(TypedDict):
    report: dict


class Published(TypedDict):
    publication: dict


def register_docs_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def owned(context, state=None, args=None, phase=None):
        authorize()
        if not path_allowed(source_runner().ARTIFACT_ROOT):
            raise ValueError("docs artifacts outside service write roots")
        scope = scopes.get(context["handle"])
        if scope is None or scope["phase"] != phase:
            raise ValueError("unknown, consumed or out-of-order docs context")
        if state is not None and state != scope["state"]:
            raise ValueError("modified or replayed docs cursor")
        if args is not None and args != scope["args_value"]:
            raise ValueError("modified docs arguments")
        return scope

    @mcp.tool()
    def mathformer_docs_family_prepare(domain: dict) -> Prepared:
        """Parse the fixed hub invocation and prepare its canonical docs selection."""
        with lock:
            authorize()
            native = source_runner()
            if not path_allowed(native.ARTIFACT_ROOT):
                raise ValueError("docs artifacts outside service write roots")
            if domain != {"max_selected_rows": 4096}:
                raise ValueError("docs domain must declare max_selected_rows=4096")
            args = native.parse_args(["--module-family", "docs", "--json"])
            native.ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
            state = native.prepare_checks(args)
            if len(state["selected"]) > 4096:
                raise ValueError("docs selection exceeds contract bound of 4096")
            args_value = {
                key: str(value) if isinstance(value, Path) else value
                for key, value in vars(args).items()
            }
            handle = uuid4().hex
            scopes[handle] = dict(
                args=args,
                args_value=deepcopy(args_value),
                state=deepcopy(state),
                phase="guard",
            )
            return {"args": args_value, "state": state, "context": {"handle": handle}}

    @mcp.tool()
    def mathformer_docs_family_cursor_done(state: dict, context: dict) -> Guarded:
        """Evaluate the native loop predicate on the owned cursor."""
        with lock:
            scope = owned(context, state=state, phase="guard")
            done = state["index"] >= len(state["selected"])
            scope["phase"] = "finalize" if done else "advance"
            return {"done": done}

    @mcp.tool()
    def mathformer_docs_family_advance(
        state: dict, args: dict, context: dict
    ) -> Updated:
        """Execute exactly one native check, retaining failed and skipped rows."""
        with lock:
            scope = owned(context, state, args, "advance")
            try:
                state = source_runner().advance_check(state, scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(state=deepcopy(state), phase="guard")
            return {"state": state}

    @mcp.tool()
    def mathformer_docs_family_retain_empty(state: dict, context: dict) -> Retained:
        """Retain the guarded zero-row state without advancing a native check."""
        with lock:
            owned(context, state=state, phase="finalize")
            if state["selected"] or state["results"] or state["index"] != 0:
                raise ValueError("empty docs selection required")
            return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_docs_family_finalize(
        state: dict, args: dict, context: dict
    ) -> Finalized:
        """Apply native validation and write the native dependency snapshot."""
        with lock:
            scope = owned(context, state, args, "finalize")
            try:
                report = source_runner().finalize_checks(state, scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_docs_family_publish(
        report: dict, args: dict, context: dict
    ) -> Published:
        """Publish in native order; route CLI output to the MCP stderr channel."""
        with lock:
            scope = owned(context, args=args, phase="publish")
            if report != scope["report"]:
                raise ValueError("modified docs report")
            scopes.pop(context["handle"])
            native = source_runner()
            with redirect_stdout(sys.stderr):
                code = native.publish_report(report, scope["args"])
            return {
                "publication": {
                    "exit_code": code,
                    "output_file": str(scope["args"].output_file),
                }
            }
