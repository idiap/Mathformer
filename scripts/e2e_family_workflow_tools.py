# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""E2E-family MCP steps over the authoritative comprehensive runner.

The server owns parsed defaults and cursor histories. Transported state is an
assertion of that history, never a caller-supplied command source.
"""

from copy import deepcopy
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner


class Prepared(TypedDict):
    state: dict
    context: dict


class Updated(TypedDict):
    state: dict


class Guarded(TypedDict):
    done: bool


class Retained(TypedDict):
    state: dict
    done: bool


class Finalized(TypedDict):
    report: dict


def register_e2e_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def owned(context, state=None, args=None, phase=None):
        authorize()
        if not path_allowed(source_runner().ARTIFACT_ROOT):
            raise ValueError("e2e artifacts outside service write roots")
        scope = scopes.get(context["handle"])
        if scope is None or scope["phase"] != phase:
            raise ValueError("unknown, consumed or out-of-order e2e context")
        if state is not None and state != scope["state"]:
            raise ValueError("modified or replayed e2e cursor")
        if args is not None and args != scope["args_value"]:
            raise ValueError("modified e2e arguments")
        return scope

    @mcp.tool()
    def mathformer_e2e_family_prepare(args: dict) -> Prepared:
        """Parse the fixed hub invocation and prepare its canonical e2e selection."""
        with lock:
            authorize()
            native = source_runner()
            if not path_allowed(native.ARTIFACT_ROOT):
                raise ValueError("e2e artifacts outside service write roots")
            expected = {
                "module_family": ["e2e"],
                "changed_files_only": False,
                "emit_dependency_map_only": False,
                "profile": "workstation",
                "fail_on_warning": False,
                "validate_matrix": False,
                "run_id": args.get("run_id"),
            }
            if args != expected or not isinstance(args.get("run_id"), str):
                raise ValueError("arguments must equal registered e2e defaults")
            input_args = deepcopy(args)
            args = native.parse_args(
                ["--module-family", "e2e", "--json", "--run-id", args["run_id"]]
            )
            native.ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
            state = native.prepare_checks(args)
            if len(state["selected"]) > 4:
                raise ValueError("e2e selection exceeds contract bound of 4")
            handle = uuid4().hex
            scopes[handle] = dict(
                args=args, args_value=input_args, state=deepcopy(state), phase="guard"
            )
            return {"state": state, "context": {"handle": handle}}

    @mcp.tool()
    def mathformer_e2e_family_cursor_done(state: dict, context: dict) -> Guarded:
        """Evaluate the native loop predicate on the owned cursor."""
        with lock:
            scope = owned(context, state=state, phase="guard")
            done = state["index"] >= len(state["selected"])
            scope["phase"] = "finalize" if done else "advance"
            return {"done": done}

    @mcp.tool()
    def mathformer_e2e_family_advance(
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
    def mathformer_e2e_family_retain_empty(state: dict, context: dict) -> Retained:
        """Retain the guarded zero-row state without executing a check."""
        with lock:
            owned(context, state=state, phase="finalize")
            if state["selected"] or state["results"] or state["index"] != 0:
                raise ValueError("empty e2e selection required")
            return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_e2e_family_finalize(
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
            scopes.pop(context["handle"])
            return {"report": report}
