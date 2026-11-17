# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable native reasoning smoke steps and owned temporary scopes."""

from contextlib import asynccontextmanager, contextmanager
from functools import lru_cache
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "skills/control/reasoning-log-schema-guardian/scripts/self_test_reasoning_logs.py"
)
_SCOPES = {}
_LOCK = RLock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "_reasoning_smoke_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Created(TypedDict):
    fixture: dict


class Validated(TypedDict):
    validation: dict


class Rendered(TypedDict):
    rendered: dict


class Audited(TypedDict):
    coverage: dict


class Finished(TypedDict):
    result: dict


def cleanup(key):
    scope = _SCOPES.pop(key, None)
    if scope:
        scope["temporary"].cleanup()


@asynccontextmanager
async def smoke_lifespan(server):
    from reasoning_consumer_tools import consumer_lifespan

    async with consumer_lifespan(server) as state:
        try:
            yield state
        finally:
            with _LOCK:
                for key in list(_SCOPES):
                    cleanup(key)


@contextmanager
def owned(fixture, stage):
    """Paths come only from owned native fixtures; reject stale/reordered calls."""
    with _LOCK:
        key = fixture.get("log_file")
        scope = _SCOPES.get(key)
        try:
            if scope is None or fixture != scope["fixture"] or scope["stage"] != stage:
                raise ValueError(
                    "unknown, modified, closed or out-of-order smoke fixture"
                )
            yield scope
            scope["stage"] += 1
        except BaseException:
            cleanup(key)
            raise


def register_reasoning_smoke_tools(mcp):
    @mcp.tool()
    def mathformer_reasoning_smoke_create_fixture(context: dict) -> Created:
        """Create the native three-event fixture; context selects read-only repository inputs."""
        if set(context) != {"repository_root"}:
            raise ValueError("context requires exactly repository_root")
        repo = Path(context["repository_root"]).resolve(strict=True)
        with _LOCK:
            temporary = TemporaryDirectory(prefix="reasoning-smoke-")
            try:
                fixture = source().create_fixture(Path(temporary.name))
                _SCOPES[fixture["log_file"]] = dict(
                    temporary=temporary, fixture=fixture, repository=repo, stage=0
                )
                return {"fixture": fixture}
            except BaseException:
                temporary.cleanup()
                raise

    @mcp.tool()
    def mathformer_reasoning_smoke_validate_fixture(fixture: dict) -> Validated:
        with owned(fixture, 0) as scope:
            return {
                "validation": source().validate_fixture(fixture, scope["repository"])
            }

    @mcp.tool()
    def mathformer_reasoning_smoke_render_fixture(
        fixture: dict, validation: dict
    ) -> Rendered:
        with owned(fixture, 1):
            return {"rendered": source().render_fixture(fixture, validation)}

    @mcp.tool()
    def mathformer_reasoning_smoke_audit_coverage(fixture: dict) -> Audited:
        with owned(fixture, 2) as scope:
            return {"coverage": source().audit_fixture_coverage(scope["repository"])}

    @mcp.tool()
    def mathformer_reasoning_smoke_finish(
        fixture: dict, validation: dict, rendered: dict, coverage: dict
    ) -> Finished:
        with owned(fixture, 3):
            try:
                return {
                    "result": source().finish_fixture(validation, rendered, coverage)
                }
            finally:
                cleanup(fixture["log_file"])
