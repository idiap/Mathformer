# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports sharing the graph layout CLI implementation.

JSON text carries insertion order through the runtime's nominal record codec.
"""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict
import plan_workflow_graph_layout as native


class Context(TypedDict):
    repository_root: str


class Resolved(TypedDict):
    paths: dict


class Read(TypedDict):
    model: str


class Built(TypedDict):
    plan: str


class Completed(TypedDict):
    result: dict


def register_workflow_graph_layout_tools(mcp, write_policy=lambda path: None):
    @mcp.tool()
    def mathformer_graph_layout_resolve(argv: list[str], context: Context) -> Resolved:
        stream = io.StringIO()
        try:
            with redirect_stdout(stream):
                paths = native.resolve_paths(argv, context["repository_root"])
        except SystemExit as error:
            if error.code != 0:
                raise ValueError(
                    f"argparse terminated with status {error.code}"
                ) from error
            text = stream.getvalue()
            print(text, end="", file=sys.stderr)
            return {
                "paths": {
                    "graph": "",
                    "output": "",
                    "json": False,
                    "halted": True,
                    "stdout": text,
                }
            }
        return {"paths": {**paths, "halted": False, "stdout": ""}}

    @mcp.tool()
    def mathformer_graph_layout_halt(paths: dict) -> Completed:
        if not paths["halted"]:
            raise ValueError("help completion requires argparse termination")
        return {
            "result": {
                "ok": True,
                "output": None,
                "views": [],
                "exit_code": 0,
                "stdout": paths["stdout"],
            }
        }

    @mcp.tool()
    def mathformer_graph_layout_read(paths: dict) -> Read:
        return {"model": json.dumps(native.read_graph(paths), ensure_ascii=False)}

    @mcp.tool()
    def mathformer_graph_layout_build(model: str) -> Built:
        return {
            "plan": json.dumps(native.build_plan(json.loads(model)), ensure_ascii=False)
        }

    @mcp.tool()
    def mathformer_graph_layout_emit(
        paths: dict, plan: str, context: Context
    ) -> Completed:
        write_policy(Path(paths["output"]))
        value = json.loads(plan)
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.emit_plan(paths, value, context["repository_root"])
        text = stream.getvalue()
        print(text, end="", file=sys.stderr)
        return {
            "result": {
                "ok": True,
                "output": str(
                    Path(paths["output"]).relative_to(context["repository_root"])
                ),
                "views": list(value["views"]),
                "exit_code": code,
                "stdout": text,
            }
        }
