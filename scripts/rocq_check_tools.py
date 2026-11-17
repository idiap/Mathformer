# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native Rocq passes and hub boundaries exposed as typed MCP operations."""

from dataclasses import asdict
from functools import lru_cache
import importlib.util
import json
from pathlib import Path
from typing_extensions import TypedDict
import mathformer as hub
from adoption_check_tools import Context
from scripts.workflow_write_audit import FileState

ACTION = "rocq:check-generated"
ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    path = ROOT / "skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py"
    spec = importlib.util.spec_from_file_location("_rocq_check_native", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Prepared(TypedDict):
    boundary: dict


class Finished(TypedDict):
    result: dict


class Collected(TypedDict):
    files: list[str]


class StructuralResults(TypedDict):
    result: list[dict]


class ExternalResults(TypedDict):
    result: list[dict]


class Aggregated(TypedDict):
    report: dict


def register_rocq_check_tools(mcp):
    @mcp.tool()
    def mathformer_rocq_check_prepare(
        context: Context, repository_root: str, extra_args: list[str]
    ) -> Prepared:
        """Apply native admission/preflight, dry-run and before-snapshot."""
        b = hub.prepare_leaf_boundary(
            hub.build_registry()[ACTION],
            hub.RunContext(**context),
            extra_args,
            repository_root=Path(repository_root),
        )
        b["snapshot"] = {k: asdict(v) for k, v in b["snapshot"].items()}
        return {"boundary": b}

    @mcp.tool()
    def mathformer_rocq_check_early_return(boundary: dict) -> Finished:
        return {"result": boundary["payload"]}

    @mcp.tool()
    def mathformer_rocq_check_collect(repository_root: str) -> Collected:
        """Retain the registered MathformerRocq target without path translation."""
        return {
            "files": [
                str(p)
                for p in source().collect_files(
                    Path(repository_root) / "MathformerRocq"
                )
            ]
        }

    @mcp.tool()
    def mathformer_rocq_check_structural(files: list[str]) -> StructuralResults:
        return {"result": source().structural_pass([Path(f) for f in files])}

    @mcp.tool()
    def mathformer_rocq_check_external(files: list[str]) -> ExternalResults:
        return {
            "result": source().external_pass(
                [Path(f) for f in files], compiler_bin=None, timeout_sec=120
            )
        }

    @mcp.tool()
    def mathformer_rocq_check_aggregate(
        files: list[str], validations: list[dict], external: list[dict]
    ) -> Aggregated:
        return {
            "report": source().aggregate_validation(
                path=Path("MathformerRocq"),
                files=files,
                validations=validations,
                external=external,
                require_compiler=False,
            )
        }

    @mcp.tool()
    def mathformer_rocq_check_complete(
        boundary: dict, report: dict, repository_root: str
    ) -> Finished:
        """Preserve CLI JSON, exit status and the hub's native write audit."""
        payload = hub.complete_leaf_boundary(
            dict(boundary["payload"]),
            0 if report.get("ok") else 1,
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            "",
        )
        b = {
            **boundary,
            "snapshot": {k: FileState(**v) for k, v in boundary["snapshot"].items()},
        }
        return {
            "result": hub.finish_leaf_boundary(
                hub.build_registry()[ACTION],
                b,
                payload,
                repository_root=Path(repository_root),
            )
        }
