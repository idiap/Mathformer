# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared native premise KB indexing steps."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "skills/premise-kb/premise-kb-indexer/scripts/index_premise_kb.py"
    )
    spec = importlib.util.spec_from_file_location("_premise_kb_index_native", path)
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    return native


class StateOutput(TypedDict):
    state: dict


class FileOutput(TypedDict):
    state: dict
    done: bool


class ReportOutput(TypedDict):
    result: dict
    exit_code: int
    stdout: str


def register_premise_kb_index_tools(mcp, guard=lambda path: None):
    def check(state):
        root = source().repo_path(Path(state["options"]["kb_root"]))
        if str(root) != state["store"]["root"]:
            raise ValueError("KB store root does not match native options")
        guard(root)

    @mcp.tool()
    def mathformer_kb_index_initialize(extra_args: list[str]) -> StateOutput:
        # argparse's SystemExit must cross MCP as a tool failure, not kill the server.
        with redirect_stdout(sys.stderr):
            try:
                return {"state": source().initialize(extra_args, before_write=guard)}
            except SystemExit as error:
                raise ValueError(
                    f"native argument parser exited: {error.code}"
                ) from error

    @mcp.tool()
    def mathformer_kb_index_ingest_file(state: dict) -> FileOutput:
        check(state)
        return source().ingest_file(state)

    @mcp.tool()
    def mathformer_kb_index_retain(state: dict) -> StateOutput:
        return {"state": source().retain(state)}

    @mcp.tool()
    def mathformer_kb_index_files_empty(state: dict) -> FileOutput:
        if state["files"]:
            raise ValueError("Empty-file transport requires no supplied files")
        return {"state": source().retain(state), "done": True}

    @mcp.tool()
    def mathformer_kb_index_ingest_vampire(state: dict) -> StateOutput:
        check(state)
        return {"state": source().ingest_vampire(state)}

    @mcp.tool()
    def mathformer_kb_index_build_bloom(state: dict) -> StateOutput:
        check(state)
        return {"state": source().build_bloom(state)}

    @mcp.tool()
    def mathformer_kb_index_build_embeddings(state: dict) -> StateOutput:
        check(state)
        return {"state": source().build_embeddings(state)}

    @mcp.tool()
    def mathformer_kb_index_search(state: dict) -> StateOutput:
        check(state)
        return {"state": source().search(state)}

    @mcp.tool()
    def mathformer_kb_index_report(state: dict) -> ReportOutput:
        check(state)
        output = io.StringIO()
        with redirect_stdout(output):
            result = source().report(state)
        stdout = output.getvalue()
        # Keep original evidence available on stderr and as a typed output port.
        sys.stderr.write(stdout)
        return {**result, "stdout": stdout}
