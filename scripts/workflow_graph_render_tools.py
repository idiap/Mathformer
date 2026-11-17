# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared native graph renderer; no provider is involved."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict
import render_workflow_graphs as native


class Context(TypedDict):
    repository_root: str


class Prepared(TypedDict):
    directory: str


class Loaded(TypedDict):
    catalogue: str


class Assembled(TypedDict):
    model: str


class Published(TypedDict):
    report: dict
    exit_code: int


def register_workflow_graph_render_tools(mcp, write_policy=lambda path: None):
    @mcp.tool()
    def mathformer_graph_render_prepare_directory(
        options: dict, context: Context
    ) -> Prepared:
        root = Path(context["repository_root"])
        output = Path(options["output_dir"])
        write_policy(output if output.is_absolute() else root / output)
        return {"directory": str(native.prepare_directory(options["output_dir"], root))}

    @mcp.tool()
    def mathformer_graph_render_load_catalogue(context: Context) -> Loaded:
        return {
            "catalogue": json.dumps(
                native.load_catalogue(Path(context["repository_root"])),
                ensure_ascii=False,
            )
        }

    @mcp.tool()
    def mathformer_graph_render_assemble_model(catalogue: str) -> Assembled:
        # Preserve native dict insertion order across canonicalizing runtimes.
        return {
            "model": json.dumps(
                native.assemble_model(json.loads(catalogue)), ensure_ascii=False
            )
        }

    @mcp.tool()
    def mathformer_graph_render_publish(
        directory: str, model: str, options: dict, context: Context
    ) -> Published:
        write_policy(Path(directory))
        report = native.publish_model(
            Path(directory), json.loads(model), Path(context["repository_root"])
        )
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.emit_report(report, options["json"])
        print(stream.getvalue(), end="", file=sys.stderr)
        return {"report": report, "exit_code": code}
