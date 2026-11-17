# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP boundaries for the native premise-KB regression steps."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "kb_skill_scripts_native", ROOT / "tests/kb/run_premise_kb_skill_scripts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_paths(paths):
    root = Path(paths["artifact_root"]).resolve()
    if not any(
        root.is_relative_to(base.resolve()) and root != base.resolve()
        for base in (ROOT / "artifacts/kb", ROOT / "artifacts/workflow_hub")
    ):
        raise ValueError("artifact root is outside declared write roots")
    for key, suffix in (("seed_jsonl", "generated_seeds.jsonl"), ("kb_root", "kb")):
        if key in paths and Path(paths[key]).resolve() != root / suffix:
            raise ValueError("paths differ from native artifact layout")


class Prepared(TypedDict):
    paths: dict


class Generated(TypedDict):
    generated: dict


class Indexed(TypedDict):
    indexed: dict


class Finished(TypedDict):
    result: dict
    exit_code: int
    stdout: str


def register_kb_skill_scripts_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_kb_skill_scripts_prepare(request: dict) -> Prepared:
        write_policy()
        check_paths({"artifact_root": str(ROOT / request["artifact_root"])})
        return {"paths": source().prepare(request)}

    @mcp.tool()
    def mathformer_kb_skill_scripts_generate(paths: dict) -> Generated:
        write_policy()
        check_paths(paths)
        return {"generated": source().generate(paths)}

    @mcp.tool()
    def mathformer_kb_skill_scripts_index(paths: dict, context: dict) -> Indexed:
        write_policy()
        check_paths(paths)
        return {"indexed": source().index(paths, context)}

    @mcp.tool()
    def mathformer_kb_skill_scripts_finish(
        request: dict, paths: dict, generated: dict, indexed: dict
    ) -> Finished:
        check_paths(paths)
        stream = io.StringIO()
        with redirect_stdout(stream):
            result = source().finish(request, paths, generated, indexed)
        stdout = stream.getvalue()
        print(stdout, end="", file=sys.stderr)
        return {**result, "stdout": stdout}
