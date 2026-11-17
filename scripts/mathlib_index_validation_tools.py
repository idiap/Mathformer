# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only MCP bindings for native Mathlib index stamp validation."""

from functools import lru_cache
import importlib.util
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py"


@lru_cache(maxsize=1)
def source():
    path = ROOT / SOURCE
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(
        "mathlib_index_validation_native", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def root_path(value):
    return Path(value) if value else source().DEFAULT_MATHLIB_ROOT


def index_path(value):
    return Path(value) if value else source().DEFAULT_INDEX


class Exists(TypedDict):
    exists: bool


class Result(TypedDict):
    result: dict


class Index(TypedDict):
    index: str


def register_mathlib_index_validation_tools(mcp):
    @mcp.tool()
    def mathformer_mathlib_index_root_exists(mathlib_root: str) -> Exists:
        return {"exists": source().path_exists(root_path(mathlib_root))}

    @mcp.tool()
    def mathformer_mathlib_index_missing_root(mathlib_root: str) -> Result:
        return {"result": source().missing_root(root_path(mathlib_root))}

    @mcp.tool()
    def mathformer_mathlib_index_index_exists(output: str) -> Exists:
        return {"exists": source().path_exists(index_path(output))}

    @mcp.tool()
    def mathformer_mathlib_index_missing_index(output: str) -> Result:
        return {"result": source().missing_index(index_path(output))}

    @mcp.tool()
    def mathformer_mathlib_index_load_index(output: str) -> Index:
        # JSON transport preserves arbitrary loaded shapes, including malformed
        # ones: native stamp access, rather than the adapter, rejects them.
        return {"index": json.dumps(source().load_index(index_path(output)))}

    @mcp.tool()
    def mathformer_mathlib_index_compare_and_return(
        index: str, mathlib_root: str, output: str
    ) -> Result:
        return {
            "result": source().compare_and_return(
                json.loads(index), root_path(mathlib_root), index_path(output)
            )
        }
