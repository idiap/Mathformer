# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed staged ports for the fixed hub SymPy action.

Case exceptions are observed as process termination, never repaired. Captured
streams travel with state so the final hub audit runs even after child failure.
The scientific helper and its sequential tools remain opaque native calls.
"""

from contextlib import redirect_stdout, redirect_stderr
from dataclasses import asdict
from scripts.workflow_write_audit import FileState
import io
import json
import sys
import traceback
from typing_extensions import TypedDict
import mathformer as hub
import generate_formalphysics_extra_sympy as native


class Context(TypedDict):
    dry_run: bool
    json_output: bool
    keep_going: bool
    allow_mutating: bool
    write_report: bool


class Options(TypedDict):
    json: bool
    promote_lib: bool


class Boundary(TypedDict):
    payload: dict
    snapshot: dict


class State(TypedDict):
    index: int
    summaries: list[dict]
    summaries_json: list[str]
    termination: dict | None
    stdout: str
    stderr: str


class Attempt(TypedDict):
    returned: bool
    summary: dict | None
    summary_json: str | None
    termination: dict | None
    stdout: str
    stderr: str


class Process(TypedDict):
    returncode: int
    stdout: str
    stderr: str


class Prepared(TypedDict):
    boundary: Boundary
    execute: bool


class Initialized(TypedDict):
    state: State


class Visited(TypedDict):
    attempt: Attempt


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    process: Process


class Result(TypedDict):
    result: dict


def action():
    return hub.build_registry()["formalphysics:extra-sympy"]


def check_options(options):
    if options != {"json": True, "promote_lib": False}:
        raise ValueError("hub route requires json=true and promote_lib=false")


def register_extra_sympy_tools(mcp, before_write=lambda: None):
    @mcp.tool()
    def mathformer_extra_sympy_prepare(context: Context) -> Prepared:
        boundary = hub.prepare_leaf_boundary(action(), hub.RunContext(**context), ())
        return {
            "boundary": {
                "payload": boundary["payload"],
                "snapshot": {
                    key: asdict(value) for key, value in boundary["snapshot"].items()
                },
            },
            "execute": boundary["execute"],
        }

    @mcp.tool()
    def mathformer_extra_sympy_initialize() -> Initialized:
        return {"state": native.initialize()}

    @mcp.tool()
    def mathformer_extra_sympy_skip(state: State) -> Advanced:
        """Finish a non-executing control turn without touching native state."""
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_extra_sympy_visit(
        state: State, options: Options, context: Context
    ) -> Visited:
        check_options(options)
        before_write()
        runtime = hub.RunContext(**context)
        errors = hub.preflight(action(), runtime, ())
        if errors or runtime.dry_run:
            raise ValueError(f"case execution not authorized: {errors}")
        if state["termination"] is not None or not 0 <= state["index"] < len(
            native.CASES
        ):
            raise ValueError("case traversal already terminated")
        out, err = io.StringIO(), io.StringIO()
        summary, termination = None, None
        with redirect_stdout(out), redirect_stderr(err):
            try:
                summary = native.write_current_case(state, options["promote_lib"])
            except (Exception, SystemExit) as error:
                # Match the child-process exit boundary without killing the MCP server.
                if isinstance(error, SystemExit):
                    code = (
                        error.code
                        if isinstance(error.code, int)
                        else (0 if error.code is None else 1)
                    )
                    if error.code is not None and not isinstance(error.code, int):
                        print(error.code, file=sys.stderr)
                else:
                    code = 1
                    traceback.print_exc()
                termination = {"returncode": code}
        return {
            "attempt": {
                "returned": termination is None,
                "summary": summary,
                "termination": termination,
                "summary_json": (
                    native.json_safe(summary) if termination is None else None
                ),
                "stdout": out.getvalue(),
                "stderr": err.getvalue(),
            }
        }

    @mcp.tool()
    def mathformer_extra_sympy_advance(state: State, attempt: Attempt) -> Advanced:
        if attempt["returned"]:
            updated, done = native.advance(state, attempt["summary"])
            updated["summaries_json"] = [
                *state["summaries_json"],
                attempt["summary_json"],
            ]
        else:
            updated, done = {**state, "termination": attempt["termination"]}, True
        updated = {
            **updated,
            "stdout": state["stdout"] + attempt["stdout"],
            "stderr": state["stderr"] + attempt["stderr"],
        }
        return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_extra_sympy_finish(state: State, options: Options) -> Finished:
        check_options(options)
        out = io.StringIO()
        if state["termination"] is not None:
            code = state["termination"]["returncode"]
        else:
            with redirect_stdout(out):
                # Lunar canonicalizes object keys between calls. Preserve the native
                # summary insertion order separately for byte-identical CLI stdout.
                code = native.finish(
                    [json.loads(text) for text in state["summaries_json"]], options
                )
        return {
            "process": {
                "returncode": code,
                "stdout": state["stdout"] + out.getvalue(),
                "stderr": state["stderr"],
            }
        }

    @mcp.tool()
    def mathformer_extra_sympy_audit(boundary: Boundary, process: Process) -> Result:
        payload = {
            **boundary["payload"],
            **process,
            "status": "completed",
            "ok": process["returncode"] == 0,
        }
        native_boundary = {
            **boundary,
            "snapshot": {
                key: FileState(**value) for key, value in boundary["snapshot"].items()
            },
        }
        return {"result": hub.finish_leaf_boundary(action(), native_boundary, payload)}

    @mcp.tool()
    def mathformer_extra_sympy_return_boundary(boundary: Boundary) -> Result:
        return {"result": boundary["payload"]}
