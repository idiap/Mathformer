# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned MCP bindings for the fixed native SymPy adversarial suite.

Only fixture paths created by this session are reviewed. Failed calls close the
native temporary context; abandoned graphs are reclaimed on server shutdown.
"""

from contextlib import asynccontextmanager, contextmanager
from copy import deepcopy
from functools import lru_cache
import importlib.util
from pathlib import Path
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "tests/physics_sympy/run_adversarial_design_guard_suite.py"
_SCOPES = {}
_LOCK = RLock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "_adversarial_guard_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Session(TypedDict):
    session_id: str


class Initialized(TypedDict):
    session: Session
    state: dict


class Materialized(TypedDict):
    fixture: dict


class Reviewed(TypedDict):
    report: dict


class Appended(TypedDict):
    state: dict
    done: bool


class Finished(TypedDict):
    report: dict


def cleanup(key):
    scope = _SCOPES.pop(key, None)
    if scope is not None:
        scope["temporary"].cleanup()


@asynccontextmanager
async def adversarial_guard_lifespan(server):
    from judge_synthesis_report_tools import synthesis_report_lifespan

    async with synthesis_report_lifespan(server) as state:
        try:
            yield state
        finally:
            with _LOCK:
                for key in list(_SCOPES):
                    cleanup(key)


@contextmanager
def owned(session, stage, **values):
    with _LOCK:
        key = session.get("session_id")
        scope = _SCOPES.get(key)
        try:
            if (
                set(session) != {"session_id"}
                or scope is None
                or scope["stage"] != stage
                or any(scope[name] != value for name, value in values.items())
            ):
                raise ValueError(
                    "unknown, closed, modified or out-of-order adversarial suite session"
                )
            yield scope
        except BaseException:
            cleanup(key)
            raise


def register_adversarial_guard_tools(mcp):
    @mcp.tool()
    def mathformer_adversarial_guard_initialize() -> Initialized:
        """Load the native router, then create an owned temporary fixture directory."""
        with _LOCK:
            router, temporary, state = source().initialize_suite()
            try:
                key = uuid4().hex
                _SCOPES[key] = dict(
                    router=router, temporary=temporary, state=state, stage="materialize"
                )
                return {"session": {"session_id": key}, "state": deepcopy(state)}
            except BaseException:
                temporary.cleanup()
                raise

    @mcp.tool()
    def mathformer_adversarial_guard_materialize(
        session: Session, state: dict
    ) -> Materialized:
        """Materialize the next fixed fixture, in source insertion order."""
        with owned(session, "materialize", state=state) as scope:
            fixture = source().materialize_fixture(
                Path(scope["temporary"].name), scope["state"]
            )
            scope.update(fixture=fixture, stage="review")
            return {"fixture": deepcopy(fixture)}

    @mcp.tool()
    def mathformer_adversarial_guard_review(
        session: Session, fixture: dict
    ) -> Reviewed:
        """Call the actual reviewer with formalphysics_0000, native Path and None log."""
        with owned(session, "review", fixture=fixture) as scope:
            report = source().review_fixture(scope["router"], scope["fixture"])
            scope.update(report=report, stage="append")
            return {"report": deepcopy(report)}

    @mcp.tool()
    def mathformer_adversarial_guard_append_and_guard(
        session: Session, state: dict, fixture: dict, report: dict
    ) -> Appended:
        """Carry all observations; a reviewer fail is data, never fail-fast."""
        with owned(
            session, "append", state=state, fixture=fixture, report=report
        ) as scope:
            updated, done = source().append_fixture_result(
                scope["state"], scope["fixture"], scope["report"]
            )
            scope.update(state=updated, stage="finish" if done else "materialize")
            return {"state": deepcopy(updated), "done": done}

    @mcp.tool()
    def mathformer_adversarial_guard_finish(session: Session, state: dict) -> Finished:
        """Close the native context before aggregating all eight expectations."""
        with owned(session, "finish", state=state):
            cleanup(session["session_id"])
            return {"report": source().finish_suite(state)}
