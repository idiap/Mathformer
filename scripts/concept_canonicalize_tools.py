# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Staged ports for the fixed concept-canonicalize hub action.

The fixture, canonicalizer, emission and write auditing are native functions.
Only the subprocess transport is replaced by typed in-process calls. Exceptions
remain terminal operation failures; no subprocess failure envelope is invented.
"""

from contextlib import redirect_stdout
from dataclasses import asdict
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
from typing_extensions import TypedDict
import mathformer as hub
from coherence_suite_tools import Context
from scripts.workflow_write_audit import FileState

ACTION = "mathformerphysicslib:concept-canonicalize"
SOURCE = "skills/mathformerphysicslib/mathformerphysicslib-concept-canonicalizer/scripts/canonicalize_physics_concepts.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "concept_canonicalize_native", hub.REPO_ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Prepared(TypedDict):
    boundary: dict


class Report(TypedDict):
    report: dict


class Graph(TypedDict):
    graph: dict


class Finished(TypedDict):
    result: dict


def require_execute(boundary):
    item = hub.build_registry()[ACTION]
    payload = boundary["payload"]
    if (
        boundary.get("execute") is not True
        or payload.get("argv") != hub.resolve_command(item.command)
        or payload.get("action") != hub.action_to_dict(item)
        or payload.get("preflight_errors") != []
        or payload.get("dry_run") is not False
    ):
        raise ValueError("Expected admitted fixed concept-canonicalize boundary")
    return item


def register_concept_canonicalize_tools(mcp):
    @mcp.tool()
    def mathformer_concept_canonicalize_prepare(
        context: Context, extra_args: list[str], repository_root: str
    ) -> Prepared:
        item = hub.build_registry()[ACTION]
        boundary = hub.prepare_leaf_boundary(
            item,
            hub.RunContext(**context),
            extra_args,
            repository_root=Path(repository_root),
        )
        boundary["snapshot"] = {k: asdict(v) for k, v in boundary["snapshot"].items()}
        return {"boundary": boundary}

    @mcp.tool()
    def mathformer_concept_canonicalize_self_test(
        boundary: dict, repository_root: str
    ) -> Report:
        require_execute(boundary)
        return {"report": source().self_test_payload(Path(repository_root))}

    @mcp.tool()
    def mathformer_concept_canonicalize_canonicalize(report: dict) -> Graph:
        return {"graph": source().canonicalize(report)}

    @mcp.tool()
    def mathformer_concept_canonicalize_finish(
        boundary: dict, graph: dict, repository_root: str
    ) -> Finished:
        item = require_execute(boundary)
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = source().emit_payload(graph)
        payload = {
            **boundary["payload"],
            "status": "completed",
            "returncode": code,
            "stdout": stream.getvalue(),
            "stderr": "",
            "ok": code == 0,
        }
        restored = {
            **boundary,
            "snapshot": {k: FileState(**v) for k, v in boundary["snapshot"].items()},
        }
        return {
            "result": hub.finish_leaf_boundary(
                item, restored, payload, repository_root=Path(repository_root)
            )
        }

    @mcp.tool()
    def mathformer_concept_canonicalize_stopped(boundary: dict) -> Finished:
        if boundary["execute"]:
            raise ValueError("Expected stopped boundary")
        return {"result": boundary["payload"]}
