# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP bindings for shared comparative-report smoke checks and owned fixtures."""

from contextlib import asynccontextmanager, contextmanager
from copy import deepcopy
from functools import lru_cache
import importlib.util
from pathlib import Path
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "tests/physics_lean/run_formalphysics_comparative_report.py"
_SCOPES = {}
_LOCK = RLock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "_comparative_report_smoke_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    session_id: str


class Created(TypedDict):
    state: dict
    context: Context


class Retained(TypedDict):
    state: dict
    done: bool


class Updated(TypedDict):
    state: dict


class Checked(TypedDict):
    state: dict
    done: bool


class Guarded(TypedDict):
    state: dict
    present: bool


class Finished(TypedDict):
    report: dict


def cleanup(key):
    scope = _SCOPES.pop(key, None)
    if scope is not None:
        scope["temporary"].cleanup()


@asynccontextmanager
async def comparative_report_lifespan(server):
    from codex_judge_self_test_tools import judge_self_test_lifespan

    async with judge_self_test_lifespan(server) as state:
        try:
            yield state
        finally:
            with _LOCK:
                for key in list(_SCOPES):
                    cleanup(key)


@contextmanager
def owned(context, state, stage):
    with _LOCK:
        key = context["session_id"]
        scope = _SCOPES.get(key)
        try:
            if (
                scope is None
                or set(context) != {"session_id"}
                or scope["stage"] != stage
                or state != scope["state"]
            ):
                raise ValueError(
                    "unknown, modified, closed or out-of-order comparative smoke scope"
                )
            yield scope
        except BaseException:
            cleanup(key)
            raise


def advance(scope, function, next_stage):
    function(scope["state"])
    scope["stage"] = next_stage
    return {"state": deepcopy(scope["state"])}


def register_comparative_report_self_test_tools(mcp):
    @mcp.tool()
    def mathformer_comparative_smoke_fixtures() -> Created:
        """Create exactly the native one-case and synthesis fixtures."""
        with _LOCK:
            temporary = source().tempfile.TemporaryDirectory()
            try:
                state = source().create_fixture(Path(temporary.name))
                key = uuid4().hex
                _SCOPES[key] = dict(temporary=temporary, state=state, stage="builder")
                return {"state": deepcopy(state), "context": {"session_id": key}}
            except BaseException:
                temporary.cleanup()
                raise

    @mcp.tool()
    def mathformer_comparative_smoke_builder(state: dict, context: Context) -> Updated:
        """Invoke the native report builder once, with its unchanged argv and environment."""
        with owned(context, state, "builder") as scope:
            return advance(scope, source().invoke_builder, "start_artifacts")

    @mcp.tool()
    def mathformer_comparative_smoke_start_artifacts(
        state: dict, context: Context
    ) -> Updated:
        with owned(context, state, "start_artifacts") as scope:
            return advance(scope, source().start_artifacts, "check_item")

    @mcp.tool()
    def mathformer_comparative_smoke_check_item(
        state: dict, context: Context
    ) -> Checked:
        with owned(context, state, "check_item") as scope:
            state, done = source().check_item(scope["state"])
            if done:
                scope["stage"] = {
                    "artifacts": "after_artifacts",
                    "html": "report_guard",
                    "metrics": "start_critics",
                    "critics": "finish_report",
                }[state["phase"]]
            return {"state": deepcopy(state), "done": done}

    @mcp.tool()
    def mathformer_comparative_smoke_after_artifacts(
        state: dict, context: Context
    ) -> Guarded:
        with owned(context, state, "after_artifacts") as scope:
            state, present = source().after_artifacts(scope["state"])
            scope["stage"] = "check_item" if present else "retain_html"
            return {"state": deepcopy(state), "present": present}

    @mcp.tool()
    def mathformer_comparative_smoke_report_guard(
        state: dict, context: Context
    ) -> Guarded:
        with owned(context, state, "report_guard") as scope:
            state, present = source().report_guard(scope["state"])
            scope["stage"] = "start_report" if present else "retain_report_start"
            return {"state": deepcopy(state), "present": present}

    @mcp.tool()
    def mathformer_comparative_smoke_start_report(
        state: dict, context: Context
    ) -> Updated:
        with owned(context, state, "start_report") as scope:
            return advance(scope, source().start_report, "check_item")

    @mcp.tool()
    def mathformer_comparative_smoke_start_critics(
        state: dict, context: Context
    ) -> Updated:
        with owned(context, state, "start_critics") as scope:
            return advance(scope, source().start_critics, "check_item")

    @mcp.tool()
    def mathformer_comparative_smoke_finish_report(
        state: dict, context: Context
    ) -> Updated:
        with owned(context, state, "finish_report") as scope:
            return advance(scope, source().finish_report, "finish")

    @mcp.tool()
    def mathformer_comparative_smoke_retain(state: dict, context: Context) -> Retained:
        with _LOCK:
            scope = _SCOPES.get(context["session_id"])
            stage = scope["stage"] if scope else ""
            with owned(context, state, stage) as scope:
                skips = dict(
                    retain_html="report_guard",
                    retain_report_start="retain_metrics",
                    retain_metrics="retain_critics_start",
                    retain_critics_start="retain_critics",
                    retain_critics="retain_tail",
                    retain_tail="finish",
                )
                if stage not in skips:
                    raise ValueError("retain requires an absent file guard")
                scope["stage"] = skips[stage]
                return {"state": deepcopy(scope["state"]), "done": True}

    @mcp.tool()
    def mathformer_comparative_smoke_finish(state: dict, context: Context) -> Finished:
        with owned(context, state, "finish") as scope:
            try:
                return {"report": source().finish(scope["state"])}
            finally:
                cleanup(context["session_id"])
