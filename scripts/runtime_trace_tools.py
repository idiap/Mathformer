# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP boundaries sharing the observational recorder's native steps."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "meta_skills/scripts/record_skill_application.py"
    )
    spec = importlib.util.spec_from_file_location("_runtime_trace_native", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    args: dict


class Constructed(TypedDict):
    rows: list[dict]


class Written(TypedDict):
    payload: dict


class Finished(TypedDict):
    completion: dict


def register_runtime_trace_tools(
    mcp, before_write=lambda: None, path_allowed=lambda path: True
):
    @mcp.tool()
    def mathformer_runtime_trace_parse(argv: list[str]) -> Parsed:
        try:
            with redirect_stdout(io.StringIO()):
                return {"args": source().parse_check(argv)}
        except SystemExit as error:
            # argparse's CLI termination must fail this call, not kill the MCP server.
            raise ValueError(f"recorder argument termination: {error}") from error

    @mcp.tool()
    def mathformer_runtime_trace_events() -> Constructed:
        return {"rows": source().coherence_events()}

    @mcp.tool()
    def mathformer_runtime_trace_write(args: dict, rows: list[dict]) -> Written:
        before_write()
        for name in ("output_jsonl", "output_md"):
            path = Path(args[name])
            if not path.is_absolute():
                path = source().REPO_ROOT / path
            if not path_allowed(path):
                raise PermissionError(f"write path is outside configured roots: {path}")
        return {"payload": source().write_payload(args, rows)}

    @mcp.tool()
    def mathformer_runtime_trace_finish(args: dict, payload: dict) -> Finished:
        stream = io.StringIO()
        code = source().emit_success(args, payload, stdout=stream)
        return {"completion": {"exit_code": code, "stdout": stream.getvalue()}}
