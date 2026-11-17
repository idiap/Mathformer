# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned MCP ports over the native mathlib run() traversal.

Matrix, state and cursor payloads are assertions against server-owned values,
never command sources. Cursor envelopes let a root-level bounded PRISM loop
carry an empty selection or an already-completed snapshot without running a
check. All scientific work, reports and while guards remain native functions.
"""

from copy import deepcopy
import json
from threading import RLock
from uuid import uuid4
from typing import Optional
from typing_extensions import TypedDict
from comprehensive_strict_tools import source_runner


class Entered(TypedDict):
    snapshot_only: bool
    context: dict


class Prepared(TypedDict):
    state: dict


class Guarded(TypedDict):
    pending: bool
    cursor: dict


class Retained(TypedDict):
    cursor: dict


class Snapshotted(TypedDict):
    report: dict
    cursor: dict


class Reported(TypedDict):
    report: dict


def parse_mathlib_args(native, args):
    """Use native parsing with the candidate's explicit, restricted CLI inputs."""
    required = {
        "run_id",
        "module_family",
        "changed_files_only",
        "emit_dependency_map_only",
        "profile",
        "fail_on_warning",
        "validate_matrix",
    }
    if (
        set(args) != required
        or not isinstance(args["run_id"], str)
        or args["module_family"] != ["mathlib"]
        or args["changed_files_only"] is not False
        or args["profile"] not in ("workstation", "strict")
        or any(
            type(args[key]) is not bool
            for key in (
                "emit_dependency_map_only",
                "fail_on_warning",
                "validate_matrix",
            )
        )
    ):
        raise ValueError("arguments must match the mathlib run contract")
    argv = [
        "--module-family",
        "mathlib",
        "--json",
        "--run-id",
        args["run_id"],
        "--profile",
        args["profile"],
    ]
    for key in ("emit_dependency_map_only", "fail_on_warning", "validate_matrix"):
        if args[key]:
            argv.append("--" + key.replace("_", "-"))
    return native.parse_args(argv)


def register_mathlib_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def allowed():
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise PermissionError("mathlib artifacts outside service write roots")
        return native

    def owned(context, phase, *, state=None, cursor=None, args=None):
        native = allowed()
        scope = scopes.get(context.get("handle"))
        if scope is None or scope["phase"] not in phase:
            raise ValueError("unknown, consumed or out-of-order mathlib context")
        if (
            (state is not None and state != scope.get("state"))
            or (cursor is not None and cursor != scope.get("cursor"))
            or (args is not None and args != scope["input_args"])
        ):
            raise ValueError("modified or replayed mathlib state or arguments")
        return native, scope

    @mcp.tool()
    def mathformer_mathlib_family_enter(args: dict) -> Entered:
        """Create the native artifact root and evaluate the early-return guard."""
        with lock:
            native = allowed()
            parsed = parse_mathlib_args(native, args)
            snapshot_only = native.enter_checks(parsed)
            handle = uuid4().hex
            scopes[handle] = dict(
                args=parsed,
                input_args=deepcopy(args),
                phase="snapshot" if snapshot_only else "prepare",
            )
            return {"snapshot_only": snapshot_only, "context": {"handle": handle}}

    @mcp.tool()
    def mathformer_mathlib_family_snapshot(args: dict, context: dict) -> Snapshotted:
        """Write the native early snapshot without loading a matrix."""
        with lock:
            native, scope = owned(context, ("snapshot",), args=args)
            try:
                report = native.snapshot_report(scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            cursor = {"pending": False}
            scope.update(
                report=deepcopy(report), cursor=cursor, phase="snapshot_result"
            )
            return {"report": report, "cursor": deepcopy(cursor)}

    @mcp.tool()
    def mathformer_mathlib_family_prepare(
        args: dict, context: dict, matrix: Optional[dict] = None
    ) -> Prepared:
        """Assert the canonical matrix and select rows once in native order."""
        with lock:
            native, scope = owned(context, ("prepare",), args=args)
            if matrix is None or matrix != json.loads(
                native.MATRIX_FILE.read_text(encoding="utf-8")
            ):
                raise ValueError("matrix must equal canonical tests/test_matrix.json")
            state = native.prepare_checks(scope["args"])
            if len(state["selected"]) > 9:
                raise ValueError("selected mathlib rows exceed contract bound of 9")
            for row in state["selected"]:
                for path in row.get("write_set") or ():
                    if not path_allowed((native.REPO_ROOT / path).resolve()):
                        raise PermissionError(
                            "mathlib check writes outside service write roots"
                        )
            scope.update(state=deepcopy(state), phase="pending")
            return {"state": state}

    @mcp.tool()
    def mathformer_mathlib_family_pending(state: dict, context: dict) -> Guarded:
        """Evaluate the shared native while guard, including zero checks."""
        with lock:
            native, scope = owned(context, ("pending",), state=state)
            pending = native.checks_pending(scope["state"])
            cursor = {"state": deepcopy(state), "pending": pending}
            scope.update(
                cursor=deepcopy(cursor), phase="advance" if pending else "finalize"
            )
            return {"pending": pending, "cursor": cursor}

    @mcp.tool()
    def mathformer_mathlib_family_advance(
        cursor: dict, args: dict, context: dict
    ) -> Prepared:
        """Run exactly one source check; failed results continue the traversal."""
        with lock:
            native, scope = owned(context, ("advance",), cursor=cursor, args=args)
            try:
                updated = native.advance_check(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(state=deepcopy(updated), phase="pending")
            return {"state": updated}

    @mcp.tool()
    def mathformer_mathlib_family_retain(cursor: dict, context: dict) -> Retained:
        """Carry an empty traversal or early report through the typed loop."""
        with lock:
            _, scope = owned(context, ("finalize", "snapshot_result"), cursor=cursor)
            if cursor["pending"] or (
                scope["phase"] == "finalize"
                and (scope["state"]["index"] or scope["state"]["selected"])
            ):
                raise ValueError("only empty traversal or snapshot may be retained")
            return {"cursor": deepcopy(cursor)}

    @mcp.tool()
    def mathformer_mathlib_family_snapshot_result(
        cursor: dict, args: dict, context: dict
    ) -> Reported:
        """Return the already-produced early report; perform no further source work."""
        with lock:
            _, scope = owned(context, ("snapshot_result",), cursor=cursor, args=args)
            scopes.pop(context["handle"])
            return {"report": scope["report"]}

    @mcp.tool()
    def mathformer_mathlib_family_finalize(
        cursor: dict, args: dict, context: dict
    ) -> Reported:
        """Require full consumption, validate evidence and write the native snapshot."""
        with lock:
            native, scope = owned(context, ("finalize",), cursor=cursor, args=args)
            scopes.pop(context["handle"])
            return {"report": native.finalize_checks(scope["state"], scope["args"])}
