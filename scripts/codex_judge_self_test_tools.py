# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned MCP scopes over the native Codex judge preparation self-test.

Only the fixed self-test is exposed: callers cannot request execution, substitute
paths, or change parser defaults. Interrupted scopes close at server shutdown.
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
SOURCE = "skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/run_codex_exec_judges.py"
_SCOPES = {}
_LOCK = RLock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "_codex_judge_self_test_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    session_id: str


class Fixture(TypedDict):
    args: dict
    context: Context


class Selected(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Persisted(TypedDict):
    manifest: dict


class Finished(TypedDict):
    report: dict


def cleanup(key):
    scope = _SCOPES.pop(key, None)
    if scope is not None:
        scope["temporary"].cleanup()


@asynccontextmanager
async def judge_self_test_lifespan(server):
    from reasoning_smoke_tools import smoke_lifespan

    async with smoke_lifespan(server) as state:
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
                    "unknown, modified, closed or out-of-order judge self-test scope"
                )
            yield scope
            scope["stage"] += 1
        except BaseException:
            cleanup(key)
            raise


def register_codex_judge_self_test_tools(mcp):
    @mcp.tool()
    def mathformer_codex_judge_self_test_fixture_args() -> Fixture:
        """Create the native temporary fixture with fresh parse_args defaults."""
        with _LOCK:
            native = source()
            temporary = native.tempfile.TemporaryDirectory()
            try:
                args = native.self_test_args(Path(temporary.name))
                projected = {
                    k: str(v) if isinstance(v, Path) else v
                    for k, v in vars(args).items()
                }
                projected["tmp"] = temporary.name
                key = uuid4().hex
                _SCOPES[key] = dict(
                    temporary=temporary, native_args=args, args=projected, stage=0
                )
                return {"args": deepcopy(projected), "context": {"session_id": key}}
            except BaseException:
                temporary.cleanup()
                raise

    @mcp.tool()
    def mathformer_codex_judge_self_test_select_pack(
        args: dict, context: Context
    ) -> Selected:
        with owned(context, 0, args=args) as scope:
            state = source().initialize_run(scope["native_args"])
            scope["state"] = state
            return {"state": deepcopy(state)}

    @mcp.tool()
    def mathformer_codex_judge_self_test_prepare_append(
        state: dict, context: Context
    ) -> Advanced:
        with owned(context, 1, state=state) as scope:
            done = source().append_run_row(scope["native_args"], scope["state"])
            return {"state": deepcopy(scope["state"]), "done": done}

    @mcp.tool()
    def mathformer_codex_judge_self_test_persist(
        state: dict, context: Context
    ) -> Persisted:
        with owned(context, 2, state=state) as scope:
            manifest = source().persist_run(scope["native_args"], scope["state"])
            scope["manifest"] = manifest
            return {"manifest": deepcopy(manifest)}

    @mcp.tool()
    def mathformer_codex_judge_self_test_check_cleanup(
        args: dict, manifest: dict, context: Context
    ) -> Finished:
        with owned(context, 3, args=args, manifest=manifest):
            try:
                return {"report": source().check_self_test(manifest)}
            finally:
                cleanup(context["session_id"])
