# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP projections of the native one-shot repository status controller."""

from dataclasses import asdict, replace
from pathlib import Path
from typing_extensions import TypedDict
import mathformer as hub
from adoption_check_tools import Context, Admission, Finished
from scripts.workflow_write_audit import FileState

ACTION = "repo:status"


class Boundary(TypedDict):
    execute: bool
    payload: dict
    snapshot: dict


class Admitted(TypedDict):
    admission: Admission
    accepted: bool


class Prepared(TypedDict):
    boundary: Boundary
    execute: bool


def item(timeout_seconds):
    if timeout_seconds is not None and timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive or null")
    return replace(hub.build_registry()[ACTION], timeout_seconds=timeout_seconds)


def mount(repository_root):
    return hub.REPO_ROOT if repository_root is None else Path(repository_root)


def register_repo_status_tools(mcp):
    @mcp.tool()
    def mathformer_repo_status_admit(
        seen: list[str], extra_args: list[str]
    ) -> Admitted:
        admission = hub.admit_action(ACTION, hub.build_registry(), extra_args, seen)
        return {"admission": admission, "accepted": admission["accepted"]}

    @mcp.tool()
    def mathformer_repo_status_reject(admission: Admission) -> Finished:
        return {"result": hub.reject_action(ACTION, admission)}

    @mcp.tool()
    def mathformer_repo_status_prepare(
        context: Context,
        extra_args: list[str],
        repository_root: str | None,
        timeout_seconds: float | None,
    ) -> Prepared:
        boundary = hub.prepare_leaf_boundary(
            item(timeout_seconds),
            hub.RunContext(**context),
            extra_args,
            repository_root=mount(repository_root),
        )
        boundary["snapshot"] = {k: asdict(v) for k, v in boundary["snapshot"].items()}
        return {"boundary": boundary, "execute": boundary["execute"]}

    @mcp.tool()
    def mathformer_repo_status_return_prepared(boundary: Boundary) -> Finished:
        return {"result": boundary["payload"]}

    @mcp.tool()
    def mathformer_repo_status_launch(
        boundary: Boundary, repository_root: str | None, timeout_seconds: float | None
    ) -> Finished:
        action = item(timeout_seconds)
        # Transported payloads cannot supply executable argv or bypass preflight.
        if not boundary["execute"] or boundary["payload"][
            "argv"
        ] != hub.resolve_command(action.command):
            raise ValueError("invalid native execution boundary")
        return {
            "result": hub.launch_leaf_boundary(
                action,
                dict(boundary["payload"]),
                repository_root=mount(repository_root),
            )
        }

    @mcp.tool()
    def mathformer_repo_status_audit(
        boundary: Boundary, result: dict, repository_root: str | None
    ) -> Finished:
        native = {
            **boundary,
            "snapshot": {k: FileState(**v) for k, v in boundary["snapshot"].items()},
        }
        return {
            "result": hub.finish_leaf_boundary(
                hub.build_registry()[ACTION],
                native,
                result,
                repository_root=mount(repository_root),
            )
        }
