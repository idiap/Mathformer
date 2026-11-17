# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP ports for the canonical lean:build native boundaries.

FileState and timeout bytes have lossless JSON representations. The controller
continues to own preflight, subprocess arguments, timeout, and write auditing.
"""

import base64
from dataclasses import asdict
from typing_extensions import TypedDict
import mathformer as hub
from scripts.workflow_write_audit import FileState
from adoption_check_tools import Context

ACTION = "lean:build"


class Admission(TypedDict):
    accepted: bool
    status: str
    ancestry: list[str]


class Admitted(TypedDict):
    admission: Admission


class Prepared(TypedDict):
    execute: bool
    payload: dict
    snapshot: dict


class Launched(TypedDict):
    payload: dict


class Finished(TypedDict):
    result: dict


def wire(payload, decode=False):
    """Preserve native TimeoutExpired bytes without replacing or decoding text."""
    result = dict(payload)
    for key in ("stdout", "stderr"):
        value = result.get(key)
        if decode and isinstance(value, dict):
            result[key] = base64.b64decode(value["base64"], validate=True)
        elif isinstance(value, bytes):
            result[key] = {"base64": base64.b64encode(value).decode("ascii")}
    return result


def register_lean_build_tools(mcp, write_policy=lambda path: None):
    @mcp.tool()
    def mathformer_lean_build_admit(
        extra_args: list[str] = [], seen: list[str] = []
    ) -> Admitted:
        return {
            "admission": hub.admit_action(
                ACTION, hub.build_registry(), extra_args, seen
            )
        }

    @mcp.tool()
    def mathformer_lean_build_reject(admission: Admission) -> Finished:
        return {"result": hub.reject_action(ACTION, admission)}

    @mcp.tool()
    def mathformer_lean_build_prepare(
        context: Context, extra_args: list[str] = []
    ) -> Prepared:
        boundary = hub.prepare_leaf_boundary(
            hub.build_registry()[ACTION], hub.RunContext(**context), extra_args
        )
        boundary["snapshot"] = {
            key: asdict(value) for key, value in boundary["snapshot"].items()
        }
        return boundary

    @mcp.tool()
    def mathformer_lean_build_launch(payload: dict) -> Launched:
        item = hub.build_registry()[ACTION]
        # Never accept executable arguments supplied by a transport client.
        if (
            payload.get("argv") != hub.resolve_command(item.command)
            or payload.get("action") != hub.action_to_dict(item)
            or payload.get("preflight_errors") != []
            or payload.get("dry_run") is not False
        ):
            raise ValueError("Expected canonical executable lean:build payload")
        write_policy(hub.REPO_ROOT / ".lake")
        return {"payload": wire(hub.launch_leaf_boundary(item, dict(payload)))}

    @mcp.tool()
    def mathformer_lean_build_audit(snapshot: dict, payload: dict) -> Finished:
        boundary = {
            "snapshot": {key: FileState(**value) for key, value in snapshot.items()}
        }
        return {
            "result": wire(
                hub.finish_leaf_boundary(
                    hub.build_registry()[ACTION], boundary, wire(payload, decode=True)
                )
            )
        }

    @mcp.tool()
    def mathformer_lean_build_return_payload(payload: dict) -> Finished:
        return {"result": payload}
