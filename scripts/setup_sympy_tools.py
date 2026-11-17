# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Controlled setup:sympy leaf boundary, retaining one native subprocess.

Continuation handles belong to this server session. Client-supplied argv,
results and snapshots never authorize execution or replace the write audit.
"""

from copy import deepcopy
import uuid
from typing_extensions import TypedDict
import mathformer as hub


class Context(TypedDict):
    dry_run: bool
    json_output: bool
    keep_going: bool
    allow_mutating: bool
    write_report: bool


class Boundary(TypedDict):
    execute: bool
    continuation: str


class Prepared(TypedDict):
    boundary: Boundary


class Result(TypedDict):
    result: dict


def register_setup_sympy_tools(mcp, before_write):
    records = {}

    def record(boundary):
        saved = records[boundary["continuation"]]
        if boundary["execute"] != saved["native"]["execute"]:
            raise ValueError("boundary changed")
        return saved

    @mcp.tool()
    def mathformer_setup_sympy_prepare_boundary(
        context: Context, extra_args: list[str]
    ) -> Prepared:
        item = hub.build_registry()["setup:sympy"]
        native = hub.prepare_leaf_boundary(item, hub.RunContext(**context), extra_args)
        token = uuid.uuid4().hex
        records[token] = dict(native=native, item=item)
        return {"boundary": {"execute": native["execute"], "continuation": token}}

    @mcp.tool()
    def mathformer_setup_sympy_return_preflight(boundary: Boundary) -> Result:
        saved = record(boundary)
        if saved["native"]["execute"]:
            raise ValueError("execution boundary requires launch and audit")
        records.pop(boundary["continuation"])
        return {"result": saved["native"]["payload"]}

    @mcp.tool()
    def mathformer_setup_sympy_launch_installer(boundary: Boundary) -> Result:
        saved = record(boundary)
        if not saved["native"]["execute"] or saved.get("launched"):
            raise ValueError("boundary unlaunchable or already launched")
        before_write(hub.REPO_ROOT / ".venv")
        saved["launched"] = True
        saved["result"] = hub.launch_leaf_boundary(
            saved["item"], deepcopy(saved["native"]["payload"])
        )
        return {"result": deepcopy(saved["result"])}

    @mcp.tool()
    def mathformer_setup_sympy_audit_result(boundary: Boundary, result: dict) -> Result:
        saved = record(boundary)
        if "result" not in saved or result != saved["result"]:
            raise ValueError("audit requires the captured native result")
        records.pop(boundary["continuation"])
        return {
            "result": hub.finish_leaf_boundary(
                saved["item"], saved["native"], saved["result"]
            )
        }
