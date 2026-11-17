# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Server-owned skills runner cursors, sharing every step with the native CLI."""

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import io
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner


class Entered(TypedDict):
    snapshot_only: bool
    context: dict
    empty_state: dict
    empty_report: dict


class Prepared(TypedDict):
    state: dict


class Guarded(TypedDict):
    pending: bool


class Reported(TypedDict):
    report: dict


class Published(TypedDict):
    exit_code: int
    publication: dict


def register_skills_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def allowed():
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise PermissionError("skills artifacts outside service write roots")
        return native

    def owned(context, phase, args=None, state=None):
        native = allowed()
        scope = scopes.get(context.get("handle"))
        if scope is None or scope["phase"] != phase:
            raise ValueError("unknown, consumed or out-of-order skills context")
        if args is not None and args != scope["input"]:
            raise ValueError("modified skills arguments")
        if state is not None and state != scope["state"]:
            raise ValueError("modified or replayed skills cursor")
        return native, scope

    def invoke(context, scope, native, function, *values):
        try:
            return getattr(native, function)(*values)
        except BaseException:
            scopes.pop(context["handle"], None)
            raise

    @mcp.tool()
    def mathformer_skills_family_enter(args: dict) -> Entered:
        """Enter native run(), retaining CLI arguments and evaluating its early branch."""
        with lock:
            native = allowed()
            defaults = vars(native.parse_args(["--module-family", "skills", "--json"]))
            if set(args) != set(defaults) or args["module_family"] != ["skills"]:
                raise ValueError("skills CLI arguments required")
            if args["profile"] not in ("workstation", "strict"):
                raise ValueError("unknown profile")
            for key in (
                "emit_dependency_map_only",
                "changed_files_only",
                "fail_on_warning",
                "validate_matrix",
                "json",
            ):
                if type(args[key]) is not bool:
                    raise ValueError("boolean CLI flag required")
            for key in ("output_file", "write_jsonl", "write_junit"):
                if args[key] and not path_allowed(
                    (native.REPO_ROOT / args[key]).resolve()
                ):
                    raise PermissionError("skills output outside service write roots")
            parsed = argparse.Namespace(**deepcopy(args))
            snapshot = native.enter_checks(parsed)
            handle = uuid4().hex
            scopes[handle] = dict(
                input=deepcopy(args),
                args=parsed,
                phase="snapshot" if snapshot else "prepare",
            )
            return {
                "snapshot_only": snapshot,
                "context": {"handle": handle},
                "empty_state": {
                    "matrix": [],
                    "selected": [],
                    "families": [],
                    "index": 0,
                    "results": [],
                    "pending": False,
                },
                "empty_report": {
                    "run_id": args["run_id"],
                    "ok": True,
                    "families": [],
                    "summary": {},
                    "results": [],
                    "schema_errors": [],
                    "matrix_errors": [],
                },
            }

    @mcp.tool()
    def mathformer_skills_family_snapshot(args: dict, context: dict) -> Reported:
        with lock:
            native, scope = owned(context, "snapshot", args)
            report = invoke(context, scope, native, "snapshot_report", scope["args"])
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_skills_family_prepare(
        args: dict, selection_bound: int, context: dict
    ) -> Prepared:
        with lock:
            native, scope = owned(context, "prepare", args)
            if type(selection_bound) is not int or selection_bound != 1000:
                raise ValueError("selection bound must be 1000")
            state = invoke(context, scope, native, "prepare_checks", scope["args"])
            if len(state["selected"]) > selection_bound:
                scopes.pop(context["handle"])
                raise ValueError("skills selection exceeds supported contract domain")
            for row in state["selected"]:
                for path in row.get("write_set") or ():
                    if not path_allowed((native.REPO_ROOT / path).resolve()):
                        scopes.pop(context["handle"])
                        raise PermissionError(
                            "skills row writes outside service write roots"
                        )
            state = {**state, "pending": native.checks_pending(state)}
            scope.update(
                state=deepcopy(state),
                phase="advance" if state["pending"] else "finalize",
            )
            return {"state": state}

    @mcp.tool()
    def mathformer_skills_family_retain_empty(state: dict, context: dict) -> Prepared:
        """Carry an empty/snapshot traversal through PRISM's at-least-once loop."""
        with lock:
            allowed()
            scope = scopes.get(context.get("handle"))
            if scope is None or scope["phase"] not in ("finalize", "publish"):
                raise ValueError("empty traversal context required")
            expected = scope.get(
                "state",
                {
                    "matrix": [],
                    "selected": [],
                    "families": [],
                    "index": 0,
                    "results": [],
                    "pending": False,
                },
            )
            if state != expected or state["pending"] or state["selected"]:
                raise ValueError("empty cursor required")
            return {"state": state}

    @mcp.tool()
    def mathformer_skills_family_advance(
        state: dict, args: dict, context: dict
    ) -> Prepared:
        with lock:
            native, scope = owned(context, "advance", args, state)
            state = invoke(
                context,
                scope,
                native,
                "advance_check",
                {k: v for k, v in scope["state"].items() if k != "pending"},
                scope["args"],
            )
            state = {**state, "pending": native.checks_pending(state)}
            scope.update(
                state=deepcopy(state),
                phase="advance" if state["pending"] else "finalize",
            )
            return {"state": state}

    @mcp.tool()
    def mathformer_skills_family_finalize(
        state: dict, args: dict, context: dict
    ) -> Reported:
        with lock:
            native, scope = owned(context, "finalize", args, state)
            report = invoke(
                context,
                scope,
                native,
                "finalize_checks",
                {k: v for k, v in scope["state"].items() if k != "pending"},
                scope["args"],
            )
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_skills_family_publish(
        report: dict, args: dict, context: dict
    ) -> Published:
        with lock:
            native, scope = owned(context, "publish", args)
            if report != scope["report"]:
                raise ValueError("modified skills report")
            scopes.pop(context["handle"])
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = native.publish_report(scope["report"], scope["args"])
            return {
                "exit_code": code,
                "publication": {
                    "stdout": stream.getvalue(),
                    "report_path": str(scope["args"].output_file),
                },
            }

    @mcp.tool()
    def mathformer_skills_family_saved_report(report: dict, context: dict) -> Reported:
        """Forward an already-produced snapshot report without running finalization."""
        with lock:
            native, scope = owned(context, "publish")
            if report != scope["report"]:
                raise ValueError("modified snapshot report")
            return {"report": report}
