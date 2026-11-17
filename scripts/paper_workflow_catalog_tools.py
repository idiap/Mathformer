# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP boundaries for the native paper workflow catalogue.

JSON text preserves graph stack insertion order across canonicalizing runtimes.
The registered service supplies its repository-mount and write authorization.
"""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import json
from pathlib import Path
import sys
from threading import Lock
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "paper_skills/framework-repository-cartographer/scripts/collect_workflow_catalog_for_paper.py"
_EMISSION_LOCK = Lock()


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "_paper_workflow_catalog_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    repository_root: str


class Paths(TypedDict):
    graph: str
    output: str
    json: bool


class Parsed(TypedDict):
    paths: Paths


class Loaded(TypedDict):
    model: str


class Collected(TypedDict):
    packet: dict


class Written(TypedDict):
    result: dict


class Emitted(TypedDict):
    exit_code: int


def register_paper_workflow_catalog_tools(mcp, mount_guard, write_policy):
    def root_for(context):
        root = Path(context["repository_root"]).resolve()
        mount_guard(root)
        return root

    @mcp.tool()
    def mathformer_paper_catalog_parse_paths(
        argv: list[str], context: Context
    ) -> Parsed:
        root = root_for(context)
        # argparse help/errors terminate the native CLI. Convert the process exit
        # to a tool failure so an invalid request cannot kill the MCP service.
        with _EMISSION_LOCK, redirect_stdout(sys.stderr):
            try:
                paths = source().parse_paths(argv, root)
            except SystemExit as error:
                raise ValueError(
                    f"Native argparse terminated with exit code {error.code}"
                ) from error
        return {"paths": paths}

    @mcp.tool()
    def mathformer_paper_catalog_load_graph(paths: Paths) -> Loaded:
        return {
            "model": json.dumps(
                source().load_model(Path(paths["graph"])), ensure_ascii=False
            )
        }

    @mcp.tool()
    def mathformer_paper_catalog_catalogue(model: str) -> Collected:
        return {"packet": source().catalogue(json.loads(model))}

    @mcp.tool()
    def mathformer_paper_catalog_write_outputs(
        packet: dict, paths: Paths, context: Context
    ) -> Written:
        root = root_for(context)
        output = Path(paths["output"])
        # Guard each actual destination, including independently symlinked siblings.
        for path in (output, output.with_suffix(".md"), output.with_suffix(".tex")):
            write_policy(path)
        return {"result": source().write_outputs(packet, output, root)}

    def emit(result, json_output):
        # stdout is owned by MCP; source-owned emission remains on diagnostics.
        with _EMISSION_LOCK, redirect_stdout(sys.stderr):
            return {"exit_code": source().emit_result(result, json_output)}

    @mcp.tool()
    def mathformer_paper_catalog_emit_result(
        result: dict, json_output: bool
    ) -> Emitted:
        """Emit the native result using its parsed CLI flag and return its exit code."""
        return emit(result, json_output)

    @mcp.tool()
    def mathformer_paper_catalog_print_json(result: dict) -> Emitted:
        return emit(result, True)

    @mcp.tool()
    def mathformer_paper_catalog_print_text(result: dict) -> Emitted:
        return emit(result, False)
