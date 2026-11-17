# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Registered MCP ports for the native famous corpus regression stages."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    path = Path(__file__).resolve().parents[1] / "tests/kb/run_famous_theorem_corpus.py"
    spec = importlib.util.spec_from_file_location("_famous_corpus_native", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PathsOutput(TypedDict):
    paths: dict


class GeneratedOutput(TypedDict):
    generated: dict


class IndexedOutput(TypedDict):
    indexed: dict


class ProbesOutput(TypedDict):
    probes: dict


class PayloadOutput(TypedDict):
    payload: dict


class EmitOutput(TypedDict):
    exit_code: int
    stdout: str


def register_famous_corpus_tools(mcp, guard=lambda path: None):
    def check(paths):
        root = Path(paths["artifact_root"]).resolve()
        if (
            Path(paths["corpus_path"]).resolve()
            != root / "famous_theorems_axioms_500.jsonl"
            or Path(paths["kb_root"]).resolve() != root / "kb"
        ):
            raise ValueError("Paths do not match native artifact context")
        guard(root)

    @mcp.tool()
    def mathformer_famous_prepare(request: dict) -> PathsOutput:
        root = Path(request.get("artifact_root", "artifacts/kb/famous_corpus_test"))
        guard(root if root.is_absolute() else source().REPO_ROOT / root)
        return {"paths": source().prepare(request)}

    @mcp.tool()
    def mathformer_famous_generate_read(paths: dict) -> GeneratedOutput:
        check(paths)
        return {"generated": source().generate_read(paths)}

    @mcp.tool()
    def mathformer_famous_index(paths: dict) -> IndexedOutput:
        check(paths)
        return {"indexed": source().index(paths)}

    @mcp.tool()
    def mathformer_famous_probe(paths: dict, indexed: dict) -> ProbesOutput:
        check(paths)
        return {"probes": source().probe(paths, indexed)}

    @mcp.tool()
    def mathformer_famous_assess(
        paths: dict, generated: dict, indexed: dict, probes: dict
    ) -> PayloadOutput:
        check(paths)
        return {"payload": source().assess(paths, generated, indexed, probes)}

    @mcp.tool()
    def mathformer_famous_emit(payload: dict, code: int) -> EmitOutput:
        out = io.StringIO()
        with redirect_stdout(out):
            result = source().emit(payload, code)
        print(out.getvalue(), end="", file=sys.stderr)
        return {"exit_code": result, "stdout": out.getvalue()}
