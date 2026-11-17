# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Source-owned reflection policy steps with temporary ledger scope ownership."""

from contextlib import asynccontextmanager
from functools import lru_cache
import importlib.util
from pathlib import Path
import tempfile
from threading import RLock
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
_SCOPES = {}
_LOCK = RLock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "_formal_answer_policy_native",
        ROOT / "tests/physics_sympy/run_formal_answer_reflection_policy.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ledger(TypedDict):
    directory: str
    path: str


class Capture(TypedDict):
    returncode: int
    report: object
    stderr: str


class State(TypedDict):
    items: list[dict]
    index: int
    findings: list[dict]
    pending: bool


class Prepared(TypedDict):
    ledger: Ledger
    findings: list[dict]


class Captured(TypedDict):
    capture: Capture


class Updated(TypedDict):
    state: State


class Finished(TypedDict):
    report: dict


def cleanup(directory):
    scope = _SCOPES.pop(directory, None)
    if scope is not None:
        scope["temporary"].cleanup()


@asynccontextmanager
async def formal_answer_policy_lifespan(server):
    from design_guard_review_tools import design_guard_review_lifespan

    async with design_guard_review_lifespan(server) as state:
        try:
            yield state
        finally:
            with _LOCK:
                for directory in list(_SCOPES):
                    cleanup(directory)


def owned(ledger, stage):
    scope = _SCOPES.get(ledger["directory"])
    if scope is None or ledger != scope["ledger"] or scope["stage"] != stage:
        raise ValueError("unknown, modified or out-of-order temporary ledger")
    return scope


def register_formal_answer_policy_tools(mcp):
    @mcp.tool()
    def mathformer_formal_answer_policy_prepare() -> Prepared:
        """Open the native temporary scope and write its pre-reflection ledger."""
        with _LOCK:
            temporary = tempfile.TemporaryDirectory()
            try:
                path = source().prepare_ledger(Path(temporary.name))
                ledger = {"directory": temporary.name, "path": str(path)}
                _SCOPES[temporary.name] = dict(
                    temporary=temporary, ledger=ledger, stage="positive"
                )
                return {"ledger": ledger, "findings": []}
            except BaseException:
                temporary.cleanup()
                raise

    @mcp.tool()
    def mathformer_formal_answer_policy_positive(ledger: Ledger) -> Captured:
        """Capture the fixed positive reflector command before the negative call."""
        with _LOCK:
            scope = owned(ledger, "positive")
            try:
                result = source().positive_reflection(Path(ledger["path"]))
                scope["stage"] = "negative"
                return {"capture": result}
            except BaseException:
                cleanup(ledger["directory"])
                raise

    @mcp.tool()
    def mathformer_formal_answer_policy_negative(ledger: Ledger) -> Captured:
        """Capture the missing-ledger command and close the temporary scope."""
        with _LOCK:
            owned(ledger, "negative")
            try:
                return {"capture": source().negative_reflection()}
            finally:
                cleanup(ledger["directory"])

    @mcp.tool()
    def mathformer_formal_answer_policy_initialize(
        ledger: Ledger, findings: list[dict], positive: Capture
    ) -> Updated:
        """Append native positive findings after both commands and scope cleanup."""
        if ledger["directory"] in _SCOPES:
            raise ValueError("reflector commands must finish before validation")
        return {"state": source().initialize_candidates(findings, positive)}

    @mcp.tool()
    def mathformer_formal_answer_policy_inspect_candidate(state: State) -> Updated:
        """Append both native acceptance checks for the current candidate."""
        return {"state": source().inspect_candidate(state)}

    @mcp.tool()
    def mathformer_formal_answer_policy_retain(state: State) -> Updated:
        """Export the unchanged state when the source for-loop has no items."""
        if state["pending"]:
            raise ValueError("cannot retain a pending candidate")
        return {"state": state}

    @mcp.tool()
    def mathformer_formal_answer_policy_finish(
        state: State, positive: Capture, negative: Capture
    ) -> Finished:
        """Reduce negative finding codes and compute the source policy report."""
        return {"report": source().finish_policy(state, positive, negative)}
