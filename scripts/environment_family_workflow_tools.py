# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Environment traversal ports sharing the native comprehensive runner.

Opaque contexts retain parsed arguments and cursor history. State ports assert
that history rather than accepting arbitrary commands from a remote client.
"""

from copy import deepcopy
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner


class ContextOutput(TypedDict):
    context: dict


class StateOutput(TypedDict):
    state: dict


class GuardOutput(TypedDict):
    done: bool


class ReportOutput(TypedDict):
    report: dict


def register_environment_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def owned(context, phase, args=None, state=None):
        authorize()
        if not path_allowed(source_runner().ARTIFACT_ROOT):
            raise ValueError("environment artifacts outside service write roots")
        scope = scopes.get(context["handle"])
        if scope is None or scope["phase"] != phase:
            raise ValueError("unknown, consumed or out-of-order environment context")
        if args is not None and args != scope["args_value"]:
            raise ValueError("modified environment arguments")
        if state is not None and state != scope["state"]:
            raise ValueError("modified or replayed environment cursor")
        return scope

    @mcp.tool()
    def mathformer_environment_ensure_artifacts(args: dict) -> ContextOutput:
        with lock:
            authorize()
            native = source_runner()
            if not path_allowed(native.ARTIFACT_ROOT):
                raise ValueError("environment artifacts outside service write roots")
            required = {
                "module_family",
                "profile",
                "changed_files_only",
                "validate_matrix",
                "fail_on_warning",
                "emit_dependency_map_only",
                "run_id",
            }
            if (
                set(args) != required
                or args["module_family"] != ["environment"]
                or args["profile"] not in ("workstation", "strict")
                or args["changed_files_only"] is not False
                or not isinstance(args["run_id"], str)
                or any(
                    type(args[k]) is not bool
                    for k in (
                        "validate_matrix",
                        "fail_on_warning",
                        "emit_dependency_map_only",
                    )
                )
            ):
                raise ValueError("invalid environment traversal arguments")
            argv = [
                "--module-family",
                "environment",
                "--json",
                "--run-id",
                args["run_id"],
                "--profile",
                args["profile"],
            ]
            for key in (
                "validate_matrix",
                "fail_on_warning",
                "emit_dependency_map_only",
            ):
                if args[key]:
                    argv.append("--" + key.replace("_", "-"))
            parsed = native.parse_args(argv)
            native.ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
            handle = uuid4().hex
            scopes[handle] = {
                "args": parsed,
                "args_value": deepcopy(args),
                "phase": "snapshot" if args["emit_dependency_map_only"] else "prepare",
            }
            return {"context": {"handle": handle}}

    @mcp.tool()
    def mathformer_environment_empty_snapshot(context: dict) -> StateOutput:
        """Supply a consumed plumbing cursor without loading the matrix."""
        with lock:
            owned(context, "snapshot")
            return {
                "state": {
                    "matrix": [],
                    "selected": [],
                    "families": ["environment"],
                    "index": 0,
                    "results": [],
                    "done": True,
                }
            }

    @mcp.tool()
    def mathformer_environment_retain_consumed(
        state: dict, context: dict
    ) -> StateOutput:
        """Pass through a consumed cursor, without a native check or snapshot."""
        with lock:
            if scopes.get(context["handle"], {}).get("phase") == "snapshot":
                owned(context, "snapshot")
                if state != {
                    "matrix": [],
                    "selected": [],
                    "families": ["environment"],
                    "index": 0,
                    "results": [],
                    "done": True,
                }:
                    raise ValueError("modified snapshot plumbing cursor")
            else:
                owned(context, "finalize", state=state)
            if not state["done"] or state["index"] != len(state["selected"]):
                raise ValueError("consumed cursor required")
            return {"state": state}

    @mcp.tool()
    def mathformer_environment_snapshot_report(
        args: dict, context: dict
    ) -> ReportOutput:
        with lock:
            scope = owned(context, "snapshot", args=args)
            scopes.pop(context["handle"])
            return {"report": source_runner().snapshot_report(scope["args"])}

    @mcp.tool()
    def mathformer_environment_prepare_checks(args: dict, context: dict) -> StateOutput:
        with lock:
            scope = owned(context, "prepare", args=args)
            state = source_runner().prepare_checks(scope["args"])
            if len(state["selected"]) > 2:
                scopes.pop(context["handle"])
                raise ValueError("environment selection exceeds contract bound of 2")
            state = {**state, "done": state["index"] >= len(state["selected"])}
            scope.update(
                state=deepcopy(state), phase="finalize" if state["done"] else "advance"
            )
            return {"state": state}

    @mcp.tool()
    def mathformer_environment_cursor_guard(state: dict, context: dict) -> GuardOutput:
        with lock:
            scope = owned(context, "guard", state=state)
            done = state["index"] >= len(state["selected"])
            scope["phase"] = "finalize" if done else "advance"
            return {"done": done}

    @mcp.tool()
    def mathformer_environment_advance_check(
        state: dict, args: dict, context: dict
    ) -> StateOutput:
        with lock:
            scope = owned(context, "advance", args=args, state=state)
            try:
                state = source_runner().advance_check(state, scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            state = {**state, "done": state["index"] >= len(state["selected"])}
            scope.update(state=deepcopy(state), phase="guard")
            return {"state": state}

    @mcp.tool()
    def mathformer_environment_finalize_checks(
        state: dict, args: dict, context: dict
    ) -> ReportOutput:
        with lock:
            scope = owned(context, "finalize", args=args, state=state)
            scopes.pop(context["handle"])
            return {"report": source_runner().finalize_checks(state, scope["args"])}
