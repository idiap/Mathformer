# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned MCP scope over the native synthetic judge synthesis report check.

The context pins paths, results, state and ordering. Native errors close the
scope immediately; interrupted graphs are reclaimed by the server lifespan.
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
SOURCE = "tests/physics_lean/run_formalphysics_judge_synthesis_report.py"
_SCOPES = {}
_LOCK = RLock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "_judge_synthesis_report_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    session_id: str


class Prepared(TypedDict):
    workspace: dict
    context: Context


class Built(TypedDict):
    result: dict


class Updated(TypedDict):
    state: dict


class Checked(TypedDict):
    state: dict
    done: bool


class Guarded(TypedDict):
    state: dict
    present: bool


class Finished(TypedDict):
    result: dict
    exit_code: int


def cleanup(key):
    scope = _SCOPES.pop(key, None)
    if scope is not None:
        scope["temporary"].cleanup()


@asynccontextmanager
async def synthesis_report_lifespan(server):
    from comparative_report_self_test_tools import comparative_report_lifespan

    async with comparative_report_lifespan(server) as state:
        try:
            yield state
        finally:
            with _LOCK:
                for key in list(_SCOPES):
                    cleanup(key)


@contextmanager
def owned(context, stage, **values):
    with _LOCK:
        key = context["session_id"]
        scope = _SCOPES.get(key)
        try:
            if (
                scope is None
                or set(context) != {"session_id"}
                or scope["stage"] != stage
                or any(value != scope[name] for name, value in values.items())
            ):
                raise ValueError(
                    "unknown, modified, closed or out-of-order synthesis scope"
                )
            yield scope
        except BaseException:
            cleanup(key)
            raise


def register_judge_synthesis_report_tools(mcp, readonly=lambda: False):
    @mcp.tool()
    def mathformer_synthesis_smoke_prepare_fixture() -> Prepared:
        """Write the fixed native fixture in an owned TemporaryDirectory."""
        if readonly():
            raise PermissionError(
                "synthetic report writes are disabled by service read-only policy"
            )
        with _LOCK:
            temporary = source().tempfile.TemporaryDirectory()
            try:
                workspace = source().prepare_fixture(Path(temporary.name))
                key = uuid4().hex
                _SCOPES[key] = dict(
                    temporary=temporary, workspace=workspace, stage="builder"
                )
                return {
                    "workspace": deepcopy(workspace),
                    "context": {"session_id": key},
                }
            except BaseException:
                temporary.cleanup()
                raise

    @mcp.tool()
    def mathformer_synthesis_smoke_invoke_builder(
        workspace: dict, context: Context
    ) -> Built:
        """Invoke the native builder CLI exactly once with the native arguments."""
        with owned(context, "builder", workspace=workspace) as scope:
            scope["result"] = source().invoke_builder(scope["workspace"])
            scope["stage"] = "start"
            return {"result": deepcopy(scope["result"])}

    @mcp.tool()
    def mathformer_synthesis_smoke_start_checks(
        workspace: dict, result: dict, context: Context
    ) -> Updated:
        with owned(context, "start", workspace=workspace, result=result) as scope:
            scope["state"] = source().start_checks(scope["workspace"], scope["result"])
            scope["stage"] = "artifact"
            return {"state": deepcopy(scope["state"])}

    @mcp.tool()
    def mathformer_synthesis_smoke_check_artifact(
        state: dict, context: Context
    ) -> Checked:
        with owned(context, "artifact", state=state) as scope:
            _, done = source().check_artifact(scope["state"])
            if done:
                scope["stage"] = "json_guard"
            return {"state": deepcopy(scope["state"]), "done": done}

    @mcp.tool()
    def mathformer_synthesis_smoke_prepare_inspection(
        state: dict, format: str, context: Context
    ) -> Guarded:
        with owned(context, format + "_guard", state=state) as scope:
            if format not in ("json", "html"):
                raise ValueError("unsupported inspection format")
            _, present = source().prepare_inspection(scope["state"], format)
            scope["stage"] = format if present else "skip_" + format
            return {"state": deepcopy(scope["state"]), "present": present}

    @mcp.tool()
    def mathformer_synthesis_smoke_check_json(state: dict, context: Context) -> Updated:
        with owned(context, "json", state=state) as scope:
            source().check_json(scope["state"])
            scope["stage"] = "html_guard"
            return {"state": deepcopy(scope["state"])}

    @mcp.tool()
    def mathformer_synthesis_smoke_carry_state(
        state: dict, context: Context
    ) -> Checked:
        with _LOCK:
            scope = _SCOPES.get(context["session_id"])
            stage = scope["stage"] if scope else ""
            with owned(context, stage, state=state) as scope:
                if stage not in ("skip_json", "skip_html"):
                    raise ValueError("carry requires an absent artifact guard")
                source().carry_state(scope["state"])
                scope["stage"] = "html_guard" if stage == "skip_json" else "finish"
                return {"state": deepcopy(scope["state"]), "done": True}

    @mcp.tool()
    def mathformer_synthesis_smoke_check_marker(
        state: dict, context: Context
    ) -> Checked:
        with owned(context, "html", state=state) as scope:
            _, done = source().check_marker(scope["state"])
            if done:
                scope["stage"] = "finish"
            return {"state": deepcopy(scope["state"]), "done": done}

    @mcp.tool()
    def mathformer_synthesis_smoke_finish(state: dict, context: Context) -> Finished:
        with owned(context, "finish", state=state) as scope:
            # The native report becomes observable only after temporary cleanup.
            cleanup(context["session_id"])
            result = source().finish(scope["state"])
            return {"result": result, "exit_code": 0 if result["ok"] else 3}
