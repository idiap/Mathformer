# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native consumer suite steps, with server-owned temporary fixture scopes."""

from contextlib import asynccontextmanager
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "_consumer_suite", ROOT / "tests/reasoning_logs/run_consumer_contract_suite.py"
)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)
_SCOPES = {}
_LOCK = RLock()


class Initialized(TypedDict):
    state: dict


class Evaluated(TypedDict):
    check: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Completed(TypedDict):
    report: dict


def cleanup(root):
    scope = _SCOPES.pop(root, None)
    if scope is not None:
        scope.cleanup()


@asynccontextmanager
async def consumer_lifespan(server):
    """Also release unfinished scopes if the host stops on a budget or disconnects."""
    try:
        yield {}
    finally:
        with _LOCK:
            for root in list(_SCOPES):
                cleanup(root)


def owned(state):
    if state["root"] not in _SCOPES:
        raise ValueError("unknown or closed consumer fixture scope")
    if state["cases"] != native.initialize_suite(Path(state["root"]))["cases"]:
        raise ValueError("consumer cases must retain their fixed order")
    if state["cursor"] != len(state["checks"]) or not 0 <= state["cursor"] <= 4:
        raise ValueError("invalid consumer cursor/history")


def register_reasoning_consumer_tools(mcp):
    @mcp.tool()
    def mathformer_reasoning_consumer_initialize() -> Initialized:
        with _LOCK:
            scope = TemporaryDirectory(prefix="reasoning-consumer-")
            _SCOPES[scope.name] = scope
            return {"state": native.initialize_suite(Path(scope.name))}

    @mcp.tool()
    def mathformer_reasoning_consumer_evaluate_fixture(state: dict) -> Evaluated:
        with _LOCK:
            owned(state)
            try:
                return {"check": native.evaluate_fixture(state)}
            except BaseException:
                cleanup(state["root"])
                raise

    @mcp.tool()
    def mathformer_reasoning_consumer_append_and_advance(
        state: dict, check: dict
    ) -> Advanced:
        with _LOCK:
            owned(state)
            try:
                if state["cursor"] >= 4:
                    raise ValueError("consumer iterator already exhausted")
                state = native.append_and_advance(state, check)
                return {"state": state, "done": state["cursor"] == len(state["cases"])}
            except BaseException:
                cleanup(state["root"])
                raise

    @mcp.tool()
    def mathformer_reasoning_consumer_cleanup_and_aggregate(state: dict) -> Completed:
        with _LOCK:
            owned(state)
            try:
                if state["cursor"] != 4:
                    raise ValueError("consumer iterator not exhausted")
            finally:
                cleanup(state["root"])
            return {"report": native.aggregate_suite(state)}
