# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""ATP-default MCP ports over the authoritative comprehensive runner steps."""

from contextlib import redirect_stdout
from copy import deepcopy
import json
from pathlib import Path
import sys
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
    more: bool


class Retained(TypedDict):
    state: dict
    more: bool


class Finalized(TypedDict):
    report: dict


class Published(TypedDict):
    exit_code: int


def register_atp_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    scopes = {}
    lock = RLock()

    def owned(context, args=None, state=None, phase=None):
        authorize()
        if not path_allowed(source_runner().ARTIFACT_ROOT):
            raise ValueError("ATP artifacts outside service write roots")
        scope = scopes.get(context["handle"])
        if scope is None or scope["phase"] != phase:
            raise ValueError("unknown, consumed or out-of-order ATP context")
        if args is not None and args != scope["input_args"]:
            raise ValueError("modified ATP arguments")
        if state is not None and state != scope["state"]:
            raise ValueError("modified or replayed ATP cursor")
        return scope

    @mcp.tool()
    def mathformer_atp_family_prepare(manifest: dict, args: dict) -> Prepared:
        with lock:
            authorize()
            native = source_runner()
            if not path_allowed(native.ARTIFACT_ROOT):
                raise ValueError("ATP artifacts outside service write roots")
            defaults = native.parse_args(
                ["--module-family", "atp", "--json", "--run-id", args["run_id"]]
            )
            expected = {
                k: str(v) if isinstance(v, Path) else v
                for k, v in vars(defaults).items()
            }
            if args != expected:
                raise ValueError("arguments must equal registered ATP defaults")
            native.ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
            if manifest != json.loads(native.MATRIX_FILE.read_text(encoding="utf-8")):
                raise ValueError("manifest must equal canonical tests/test_matrix.json")
            state = native.prepare_checks(defaults)
            if len(state["matrix"]) > 1024:
                raise ValueError("matrix exceeds contract bound of 1024")
            handle = uuid4().hex
            scopes[handle] = dict(
                args=defaults,
                input_args=deepcopy(args),
                state=deepcopy(state),
                phase="guard",
            )
            return {"state": state, "context": {"handle": handle}}

    @mcp.tool()
    def mathformer_atp_family_guard(state: dict, context: dict) -> Guarded:
        with lock:
            scope = owned(context, state=state, phase="guard")
            more = state["index"] < len(state["selected"])
            scope["phase"] = "advance" if more else "finalize"
            return {"more": more}

    @mcp.tool()
    def mathformer_atp_family_advance(
        state: dict, args: dict, context: dict
    ) -> Updated:
        with lock:
            scope = owned(context, args, state, "advance")
            try:
                state = source_runner().advance_check(state, scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(state=deepcopy(state), phase="guard")
            return {"state": state}

    @mcp.tool()
    def mathformer_atp_family_retain_empty(state: dict, context: dict) -> Retained:
        with lock:
            owned(context, state=state, phase="finalize")
            if state["selected"] or state["results"] or state["index"] != 0:
                raise ValueError("empty selection required")
            return {"state": state, "more": False}

    @mcp.tool()
    def mathformer_atp_family_finalize(
        state: dict, args: dict, context: dict
    ) -> Finalized:
        with lock:
            scope = owned(context, args, state, "finalize")
            try:
                report = source_runner().finalize_checks(state, scope["args"])
            except BaseException:
                scopes.pop(context["handle"], None)
                raise
            scope.update(report=deepcopy(report), phase="publish")
            return {"report": report}

    @mcp.tool()
    def mathformer_atp_family_publish(
        report: dict, args: dict, context: dict
    ) -> Published:
        with lock:
            scope = owned(context, args=args, phase="publish")
            if report != scope["report"]:
                raise ValueError("modified ATP report")
            scopes.pop(context["handle"])
            with redirect_stdout(sys.stderr):
                code = source_runner().publish_report(report, scope["args"])
            return {"exit_code": code}
