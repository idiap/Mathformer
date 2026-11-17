# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP adapters for the shared native normalization steps. No action execution."""

import json
import io
import importlib.util
import sys
from contextlib import redirect_stdout
from functools import lru_cache
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location("normalization_native", ROOT / SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    options: dict


class Inventoried(TypedDict):
    descriptors: list[str]


class Rendered(TypedDict):
    rendered: dict


class Checked(TypedDict):
    result: dict


class JsonChecked(TypedDict):
    result: dict
    result_json: str


class JsonFinished(TypedDict):
    exit_code: int
    stdout: str


class Finished(TypedDict):
    exit_code: int


def output_path(output_directory):
    path = (ROOT / output_directory).resolve() if output_directory else source().OUTPUT
    if not any(
        path.is_relative_to(base.resolve())
        for base in (source().OUTPUT, ROOT / "artifacts/workflow_hub")
    ):
        raise ValueError("normalization output is outside declared write roots")
    return path


def files_from(rendered, output):
    files = {Path(key): rendered["files"][key] for key in rendered["file_order"]}
    if set(rendered["file_order"]) != set(rendered["files"]) or len(files) != len(
        rendered["file_order"]
    ):
        raise ValueError("rendered file order must list every path exactly once")
    for path in files:
        if path.is_absolute() or not (output / path).resolve().is_relative_to(output):
            raise ValueError("rendered path escapes output directory")
    return files


def register_normalize_workflows_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_normalize_parse(argv: list[str]) -> Parsed:
        # argparse's SystemExit must not terminate the MCP server.
        try:
            with redirect_stdout(sys.stderr):
                options = source().parse_options(argv)
        except SystemExit as error:
            if error.code != 0:
                raise ValueError(f"argparse exited {error.code}") from error
            return {"options": {"write": False, "json": False, "halted": True}}
        return {"options": {**options, "halted": False}}

    @mcp.tool()
    def mathformer_normalize_inventory() -> Inventoried:
        return {
            "descriptors": [
                json.dumps(d, ensure_ascii=False) for d in source().inventory()
            ]
        }

    @mcp.tool()
    def mathformer_normalize_render(descriptors: list[str]) -> Rendered:
        files, catalog = source().render_descriptors(
            [json.loads(d) for d in descriptors]
        )
        return {
            "rendered": {
                "files": {str(p): text for p, text in files.items()},
                "file_order": [str(p) for p in files],
                "catalog": catalog,
            }
        }

    @mcp.tool()
    def mathformer_normalize_write(rendered: dict, output_directory: str) -> dict:
        write_policy()
        output = output_path(output_directory)
        source().write_files(files_from(rendered, output), output)
        return {}

    @mcp.tool()
    def mathformer_normalize_check(rendered: dict, output_directory: str) -> Checked:
        output = output_path(output_directory)
        return {
            "result": source().check_rendered(
                files_from(rendered, output), rendered["catalog"], output
            )
        }

    @mcp.tool()
    def mathformer_normalize_finish(result: dict | None, options: dict) -> Finished:
        # Preserve native text/JSON output on stderr; stdout is MCP framing.
        with redirect_stdout(sys.stderr):
            code = source().finish(result, options)
        return {"exit_code": code}

    @mcp.tool()
    def mathformer_normalized_finish(result_json: str) -> JsonFinished:
        """Complete the registered --check --json path using native formatting."""
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = source().finish(
                json.loads(result_json), {"json": True, "write": False}
            )
        stdout = stream.getvalue()
        # Native console observability survives without corrupting MCP framing.
        print(stdout, end="", file=sys.stderr)
        return {"exit_code": code, "stdout": stdout}

    @mcp.tool()
    def mathformer_normalized_check(
        rendered: dict, output_directory: str
    ) -> JsonChecked:
        """Read-only check retaining native JSON insertion order for completion."""
        output = output_path(output_directory)
        files = files_from(rendered, output)
        # Serialized catalog is the native ordered transport. JSON object key
        # order in the separately typed catalog can change in the PRISM codec.
        catalog = json.loads(files[Path("catalog.json")])
        if catalog != rendered["catalog"]:
            raise ValueError("serialized catalog differs from rendered catalog")
        result = source().check_rendered(files, catalog, output)
        return {"result": result, "result_json": json.dumps(result)}
