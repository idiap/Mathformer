# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only MCP boundaries for the native portable adoption catalog check."""

import importlib.util
import sys
from contextlib import redirect_stdout
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/control/workflow-contract-validator/scripts/portable_adoption.py"
CAUGHT = (ValueError, KeyError, TypeError, FileNotFoundError)


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location("catalog_check_native", ROOT / SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Completion(TypedDict):
    returncode: int
    json: dict


class Loaded(TypedDict):
    ok: bool
    data: dict | None
    completion: Completion


class Rendered(TypedDict):
    ok: bool
    text: str
    completion: Completion


class Compared(TypedDict):
    ok: bool
    stale: bool
    completion: Completion


class Finished(TypedDict):
    completion: Completion


def repository_path(value, default):
    path = (ROOT / value).resolve() if value else default
    if not path.is_relative_to(ROOT):
        raise ValueError("catalog context path escapes repository")
    return path


def pending():
    return {"returncode": 0, "json": {"ok": True}}


def complete(result, code=0):
    # MCP owns stdout framing; preserve native JSON observability on stderr.
    with redirect_stdout(sys.stderr):
        return source().emit_completion(result, code)


def failed(error):
    return complete(source().error_result(error), 2)


def register_catalog_check_tools(mcp):
    @mcp.tool()
    def mathformer_catalog_load(metadata_path: str = "") -> Loaded:
        try:
            data, _ = source().load_contract(
                repository_path(metadata_path, source().METADATA)
            )
            return {"ok": True, "data": data, "completion": pending()}
        except CAUGHT as error:
            return {"ok": False, "data": None, "completion": failed(error)}

    @mcp.tool()
    def mathformer_catalog_render(data: dict | None) -> Rendered:
        try:
            return {
                "ok": True,
                "text": source().catalog_text(data),
                "completion": pending(),
            }
        except CAUGHT as error:
            return {"ok": False, "text": "", "completion": failed(error)}

    @mcp.tool()
    def mathformer_catalog_compare(text: str, catalog_path: str = "") -> Compared:
        try:
            stale = source().catalog_is_stale(
                text, repository_path(catalog_path, source().CATALOG)
            )
            return {"ok": True, "stale": stale, "completion": pending()}
        except CAUGHT as error:
            return {"ok": False, "stale": False, "completion": failed(error)}

    @mcp.tool()
    def mathformer_catalog_failed(completion: Completion) -> Finished:
        """Forward the already emitted native error without running dependent steps."""
        return {"completion": completion}

    @mcp.tool()
    def mathformer_catalog_stale() -> Finished:
        try:
            source().stale_catalog_error()
        except CAUGHT as error:
            return {"completion": failed(error)}

    @mcp.tool()
    def mathformer_catalog_matched(catalog_path: str = "") -> Finished:
        try:
            result = source().catalog_result(
                True, repository_path(catalog_path, source().CATALOG)
            )
            return {"completion": complete(result)}
        except CAUGHT as error:
            return {"completion": failed(error)}
