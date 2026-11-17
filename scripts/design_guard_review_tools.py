# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared native SymPy design-guard reviewer.

Modules stay in this server process until inspection consumes their opaque
handle. Abandoned handles are reclaimed at server shutdown. Imports and native
callbacks execute Python and therefore require the service's mutation policy.
"""

from contextlib import asynccontextmanager
from copy import deepcopy
from functools import lru_cache
import importlib.util
from pathlib import Path
from threading import RLock
from uuid import uuid4
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/physics-sympy/physics-sympy-review-refinement-router/scripts/plan_physics_sympy_review_refinement.py"
_ARTIFACTS = {}
_LOCK = RLock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "_design_guard_review_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Request(TypedDict):
    case_id: str
    path: str
    reasoning_log: str | None


class Artifact(TypedDict):
    handle: str


class Initialized(TypedDict):
    state: dict
    artifact_present: bool


class Updated(TypedDict):
    state: dict


class Loaded(TypedDict):
    state: dict
    artifact: Artifact | None
    module_loaded: bool


class Finished(TypedDict):
    report: dict


def log_path(request):
    return None if request["reasoning_log"] is None else Path(request["reasoning_log"])


@asynccontextmanager
async def design_guard_review_lifespan(server):
    from adversarial_design_guard_tools import adversarial_guard_lifespan

    async with adversarial_guard_lifespan(server) as state:
        try:
            yield state
        finally:
            with _LOCK:
                _ARTIFACTS.clear()


def register_design_guard_review_tools(mcp, import_policy):
    @mcp.tool()
    def mathformer_design_guard_initialize(request: Request) -> Initialized:
        """Capture native evidence before branching on artifact presence."""
        state, present = source().initialize_design_guard_review(
            Path(request["path"]), log_path(request)
        )
        return {"state": state, "artifact_present": present}

    @mcp.tool()
    def mathformer_design_guard_missing_artifact(
        request: Request, state: dict
    ) -> Updated:
        """Append the native missing-artifact finding."""
        return {
            "state": source().missing_design_guard_artifact(
                Path(request["path"]), state
            )
        }

    @mcp.tool()
    def mathformer_design_guard_read_and_import(
        request: Request, state: dict
    ) -> Loaded:
        """Scan commentary and import once; return a process-local module handle."""
        import_policy()
        state, artifact = source().read_design_guard_artifact(
            request["case_id"], Path(request["path"]), state
        )
        result = {
            "state": state,
            "artifact": None,
            "module_loaded": artifact is not None,
        }
        if artifact is not None:
            with _LOCK:
                key = uuid4().hex
                _ARTIFACTS[key] = (artifact, deepcopy(state))
            result["artifact"] = {"handle": key}
        return result

    @mcp.tool()
    def mathformer_design_guard_failed_import(state: dict) -> Updated:
        """Preserve the import failure as report data and skip module callbacks."""
        return {"state": source().failed_design_guard_import(state)}

    @mcp.tool()
    def mathformer_design_guard_inspect_module(
        state: dict, artifact: Artifact | None
    ) -> Updated:
        """Consume the imported module exactly once and run native checks."""
        import_policy()
        if artifact is None:
            raise ValueError("no imported design-guard artifact")
        with _LOCK:
            owned = _ARTIFACTS.pop(artifact["handle"], None)
        if owned is None:
            raise ValueError("unknown or consumed design-guard artifact handle")
        native_artifact, expected = owned
        if state != expected:
            raise ValueError(
                "design-guard state differs from the imported artifact state"
            )
        return {"state": source().inspect_design_guard_module(state, native_artifact)}

    @mcp.tool()
    def mathformer_design_guard_finish_review(
        request: Request, state: dict
    ) -> Finished:
        """Review log evidence and return the native report; never execute repairs."""
        return {
            "report": source().finish_design_guard_review(
                request["case_id"], log_path(request), state
            )
        }
