# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP steps for the native Mathlib index builder.

No indexing algorithm lives here: parsing, validation, reranking and persistence
are shared with the original entrypoint. Service policy qualifies write paths.
"""

from argparse import Namespace
from pathlib import Path
from typing_extensions import TypedDict

from mathlib_index_validation_tools import source


class BuildArgs(TypedDict):
    mathlib_root: str
    output: str
    reranker_cache: str
    max_files: int | None
    validate_existing: bool


class Exists(TypedDict):
    exists: bool


class Result(TypedDict):
    result: dict


class Index(TypedDict):
    index: dict


class Cache(TypedDict):
    cache: dict


def native_args(args: BuildArgs) -> Namespace:
    return Namespace(
        **{
            **args,
            **{
                key: Path(args[key])
                for key in ("mathlib_root", "output", "reranker_cache")
            },
        }
    )


def register_mathlib_index_build_tools(mcp, write_policy, path_allowed):
    @mcp.tool()
    def mathformer_mathlib_index_build_path_exists(path: str) -> Exists:
        """Check the native path, without changing its meaning or defaults."""
        return {"exists": source().path_exists(Path(path))}

    @mcp.tool()
    def mathformer_mathlib_index_build_missing_root(args: BuildArgs) -> Result:
        return {"result": source().missing_root(native_args(args).mathlib_root)}

    @mcp.tool()
    def mathformer_mathlib_index_build_missing_index(args: BuildArgs) -> Result:
        return {"result": source().missing_index(native_args(args).output)}

    @mcp.tool()
    def mathformer_mathlib_index_build_load_validate(args: BuildArgs) -> Result:
        return {"result": source().load_validate(native_args(args))}

    @mcp.tool()
    def mathformer_mathlib_index_build_parse(args: BuildArgs) -> Index:
        values = native_args(args)
        return {
            "index": source().parse_mathlib(
                values.mathlib_root, max_files=values.max_files
            )
        }

    @mcp.tool()
    def mathformer_mathlib_index_build_rerank(index: dict) -> Cache:
        return {"cache": source().build_optional_reranker_cache(index)}

    @mcp.tool()
    def mathformer_mathlib_index_build_write_return(
        args: BuildArgs, index: dict, cache: dict
    ) -> Result:
        write_policy()
        values = native_args(args)
        if any(
            not path_allowed(path) for path in (values.output, values.reranker_cache)
        ):
            raise ValueError(
                "Mathlib index or reranker cache is outside allowed write roots"
            )
        return {"result": source().write_return(values, index, cache)}
