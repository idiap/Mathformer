# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP bindings for the shared finite SymPy thoroughness gate.

Opaque process-local handles preserve the imported module and raw validator
objects. JSON state snapshots are checked against the owned scope; they are not
checkpoints. Completion, failure and server shutdown release owned modules.
"""

from contextlib import asynccontextmanager, redirect_stdout
from functools import lru_cache
import importlib.util
import json
from pathlib import Path
import sys
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "tests/physics_sympy/run_grounded_sample_thoroughness.py"
_SCOPES = {}
_REPORTS = {}
_LOCK = RLock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "_sympy_grounded_sample_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Initialized(TypedDict):
    state: dict
    imported: bool


class Updated(TypedDict):
    state: dict


class ImportGuard(TypedDict):
    failed: bool


class BuildReported(TypedDict):
    report: dict


class EmissionContext(TypedDict):
    handle: str


class Reported(TypedDict):
    report: dict
    emission: EmissionContext


class Emitted(TypedDict):
    exit_code: int


def snapshot(state, handle):
    value = dict(state)
    value["module"] = handle
    # Retain raw objects in the scope; transport follows the native JSON emitter.
    return json.loads(json.dumps(value, default=str))


@asynccontextmanager
async def sympy_grounded_sample_lifespan(server):
    from formal_answer_policy_tools import formal_answer_policy_lifespan

    async with formal_answer_policy_lifespan(server) as state:
        try:
            yield state
        finally:
            with _LOCK:
                _SCOPES.clear()
                _REPORTS.clear()


def register_sympy_grounded_sample_tools(mcp, import_policy, path_allowed):
    def authorize(path):
        import_policy()
        if not path_allowed(path):
            raise ValueError(
                "SymPy grounded sample output is outside service write roots"
            )

    def advance(state, stage, function, next_stage=None, *, retain_report=True):
        with _LOCK:
            key = state["module"]
            scope = _SCOPES.pop(key, None)
            if scope is None:
                raise ValueError("unknown or consumed SymPy grounded sample handle")
            native, expected, expected_stage = scope
            if state != expected or stage != expected_stage:
                raise ValueError("modified or out-of-order SymPy grounded sample state")
            # Native stdout belongs on stderr while MCP owns the protocol stream.
            with redirect_stdout(sys.stderr):
                result = function(native)
            if next_stage:
                public = snapshot(result, key)
                _SCOPES[key] = (result, public, next_stage)
                return {"state": public}
            public_report = json.loads(json.dumps(result, default=str))
            if not retain_report:
                return {"report": public_report}
            emission = uuid4().hex
            _REPORTS[emission] = (result, public_report)
            return {"report": public_report, "emission": {"handle": emission}}

    @mcp.tool()
    def mathformer_sympy_grounded_initialize_gate(
        case_id: str, path: str, reasoning_log: str | None
    ) -> Updated:
        """Initialize build_report's exact arguments, retaining its native objects."""
        import_policy()
        with _LOCK, redirect_stdout(sys.stderr):
            state = source().initialize_gate(
                case_id,
                Path(path),
                None if reasoning_log is None else Path(reasoning_log),
            )
            key = uuid4().hex
            public = snapshot(state, key)
            _SCOPES[key] = (state, public, "import_guard")
        return {"state": public}

    @mcp.tool()
    def mathformer_sympy_grounded_import_failed(state: dict) -> ImportGuard:
        """Evaluate the native import branch once without reimporting the artifact."""
        with _LOCK:
            key = state["module"]
            scope = _SCOPES.pop(key, None)
            if scope is None:
                raise ValueError("unknown or consumed SymPy grounded sample handle")
            native, expected, stage = scope
            if state != expected or stage != "import_guard":
                raise ValueError("modified or out-of-order SymPy grounded sample state")
            failed = native["module"] is None
            _SCOPES[key] = (native, expected, "blocked" if failed else "inspect")
        return {"failed": failed}

    @mcp.tool()
    def mathformer_sympy_grounded_import_blocked(state: dict) -> BuildReported:
        """Return build_report's early blocked result and release the native state."""
        return advance(
            state, "blocked", source().blocked_gate_report, retain_report=False
        )

    @mcp.tool()
    def mathformer_sympy_grounded_finish_report(state: dict) -> BuildReported:
        """Return build_report's classification without adding CLI emission effects."""
        return advance(state, "classify", source().classify_gate, retain_report=False)

    @mcp.tool()
    def mathformer_sympy_grounded_import_state(request: dict) -> Initialized:
        """Normalize CLI defaults and import exactly once into an owned scope."""
        import_policy()  # Artifact import executes arbitrary Python callbacks.
        native = source()
        path = (
            Path(request["sympy_file"])
            if request.get("sympy_file") is not None
            else None
        )
        log = (
            Path(request["reasoning_log"])
            if request.get("reasoning_log") is not None
            else None
        )
        case = native.normalize_case(request.get("case", "formalphysics_0000"), path)
        with _LOCK, redirect_stdout(sys.stderr):
            state = native.initialize_gate(case, native.case_path(case, path), log)
            imported = state["module"] is not None
            key = uuid4().hex
            public = snapshot(state, key)
            _SCOPES[key] = (state, public, "inspect" if imported else "blocked")
        return {"state": public, "imported": imported}

    @mcp.tool()
    def mathformer_sympy_grounded_blocked_report(state: dict) -> Reported:
        return advance(state, "blocked", source().blocked_gate_report)

    @mcp.tool()
    def mathformer_sympy_grounded_inspect_validate(state: dict) -> Updated:
        import_policy()
        return advance(state, "inspect", source().inspect_gate, "design")

    @mcp.tool()
    def mathformer_sympy_grounded_design_and_review(state: dict) -> Updated:
        import_policy()

        def review(native):
            if native["reasoning_log"] is not None:
                authorize(native["reasoning_log"])
            return source().design_and_review_gate(native)

        return advance(state, "design", review, "classify")

    @mcp.tool()
    def mathformer_sympy_grounded_classify_report(state: dict) -> Reported:
        return advance(state, "classify", source().classify_gate)

    @mcp.tool()
    def mathformer_sympy_grounded_emit(
        request: dict, report: dict, emission: EmissionContext
    ) -> Emitted:
        with _LOCK:
            owned = _REPORTS.pop(emission["handle"], None)
        if owned is None or owned[1] != report:
            raise ValueError("unknown, consumed or modified SymPy grounded report")
        native_report = owned[0]
        output = Path(request["output"]) if request.get("output") is not None else None
        log = (
            Path(request["reasoning_log"])
            if request.get("reasoning_log") is not None
            else None
        )
        # Authorize each native write at its boundary, preserving output-before-log.
        if output is not None:
            authorize(output)
        native = source()
        with _LOCK, redirect_stdout(sys.stderr):
            # The native emitter accepts an authorization callback for its log
            # boundary; the CLI uses its default no-op.
            code = native.emit_gate_report(
                native_report, output, log, authorize_log=authorize
            )
        return {"exit_code": code}
