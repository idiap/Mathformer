# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports over the shared native source runner, with owned invocation state."""

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict

from comprehensive_strict_tools import source_runner

DEFAULTS = dict(
    module_family=["source"],
    profile="workstation",
    changed_files_only=False,
    validate_matrix=False,
    emit_dependency_map_only=False,
    fail_on_warning=False,
    output_file="artifacts/test_program/deterministic_tests.json",
    write_jsonl=None,
    write_junit=None,
    json=True,
)


class Entered(TypedDict):
    snapshot_only: bool
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


def register_source_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    """Register native blocks; transported commands/reports are assertions only."""
    scopes = {}
    lock = RLock()

    def allowed():
        authorize()
        native = source_runner()
        if not path_allowed(native.ARTIFACT_ROOT):
            raise PermissionError("source artifacts outside service write roots")
        return native

    def parse(native, args):
        # The public tools also support the source's early snapshot branch. The
        # published hub specialization restricts this flag to false.
        expected = {
            **DEFAULTS,
            "run_id": args.get("run_id"),
            "emit_dependency_map_only": args.get("emit_dependency_map_only"),
        }
        if (
            args != expected
            or not isinstance(args.get("run_id"), str)
            or type(args.get("emit_dependency_map_only")) is not bool
        ):
            raise ValueError(
                "args must equal registered source defaults with run_id and snapshot flag"
            )
        argv = ["--module-family", "source", "--json", "--run-id", args["run_id"]]
        if args["emit_dependency_map_only"]:
            argv.append("--emit-dependency-map-only")
        return native.parse_args(argv)

    def owned(context, phase, state=None, args=None):
        native = allowed()
        scope = scopes.get(context.get("handle"))
        if scope is None or scope["phase"] != phase:
            raise ValueError("unknown, consumed or out-of-order source context")
        if state is not None and state != scope.get("state"):
            raise ValueError("modified or replayed source state")
        if args is not None and args != scope["input_args"]:
            raise ValueError("modified source invocation")
        return native, scope

    @mcp.tool()
    def mathformer_source_family_enter(args: dict) -> Entered:
        """Parse once, create the native artifact root and evaluate early return."""
        with lock:
            native = allowed()
            parsed = parse(native, args)
            snapshot_only = native.enter_checks(parsed)
            handle = uuid4().hex
            scopes[handle] = dict(
                args=parsed,
                input_args=deepcopy(args),
                phase="snapshot" if snapshot_only else "prepare",
            )
            return {"snapshot_only": snapshot_only, "context": {"handle": handle}}

    @mcp.tool()
    def mathformer_source_family_snapshot(args: dict, context: dict) -> Finalized:
        """Write the native dependency snapshot and early-return report."""
        with lock:
            native, scope = owned(context, "snapshot", args=args)
            try:
                report = native.snapshot_report(scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_source_family_prepare(
        args: dict, matrix: dict, context: dict
    ) -> Prepared:
        """Assert the canonical file snapshot and load its selected rows in order."""
        with lock:
            native, scope = owned(context, "prepare", args=args)
            if matrix != json.loads(native.MATRIX_FILE.read_text(encoding="utf-8")):
                raise ValueError(
                    "matrix must equal canonical tests/test_matrix.json snapshot"
                )
            state = native.prepare_checks(scope["args"])
            if len(state["selected"]) > 4:
                raise ValueError("source selection exceeds contract bound of 4")
            for row in state["selected"]:
                for path in row.get("write_set") or ():
                    if not path_allowed((native.REPO_ROOT / path).resolve()):
                        raise PermissionError(
                            "source check writes outside service write roots"
                        )
            scope.update(state=deepcopy(state), phase="pending")
            return {"state": state}

    @mcp.tool()
    def mathformer_source_family_pending(state: dict, context: dict) -> Guarded:
        """Evaluate the shared native while guard, including zero iterations."""
        with lock:
            native, scope = owned(context, "pending", state)
            pending = native.checks_pending(scope["state"])
            scope["phase"] = "advance" if pending else "finalize"
            return {"pending": pending, "cursor": {"state": state, "pending": pending}}

    @mcp.tool()
    def mathformer_source_family_advance(
        state: dict, args: dict, context: dict
    ) -> Prepared:
        """Execute one source check, accumulate its result and increment once."""
        with lock:
            native, scope = owned(context, "advance", state, args)
            try:
                updated = native.advance_check(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(state=deepcopy(updated), phase="pending")
            return {"state": updated}

    @mcp.tool()
    def mathformer_source_family_retain_empty(cursor: dict, context: dict) -> Guarded:
        """Carry an empty selection through the runtime's at-least-once loop."""
        with lock:
            owned(context, "finalize", cursor["state"])
            state = cursor["state"]
            if (
                cursor != {"state": state, "pending": False}
                or state["selected"]
                or state["results"]
                or state["index"]
            ):
                raise ValueError("empty source selection required")
            return {"cursor": cursor, "pending": False}

    @mcp.tool()
    def mathformer_source_family_finalize(
        state: dict, args: dict, context: dict
    ) -> Finalized:
        """Require traversal completion, aggregate evidence and write the snapshot."""
        with lock:
            native, scope = owned(context, "finalize", state, args)
            try:
                report = native.finalize_checks(scope["state"], scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_source_family_publish(
        report: dict, args: dict, context: dict
    ) -> Published:
        """Publish native JSON and expose its stdout without corrupting JSON-RPC."""
        with lock:
            native, scope = owned(context, "publish", args=args)
            if report != scope["report"]:
                raise ValueError("modified source report")
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
