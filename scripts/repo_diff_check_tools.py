# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed transport for the fixed repo:diff-check native leaf boundaries."""

from dataclasses import asdict
from scripts.workflow_write_audit import FileState
from pathlib import Path
from typing_extensions import TypedDict
import mathformer as hub
from quality_smoke_tools import Context, Admission

ACTION = "repo:diff-check"


class Boundary(TypedDict):
    execute: bool
    payload: dict
    snapshot: dict


class Admitted(TypedDict):
    admission: Admission


class Prepared(TypedDict):
    boundary: Boundary


class Result(TypedDict):
    result: dict


class Launched(TypedDict):
    payload: dict


def mount(repository_root):
    return hub.REPO_ROOT if repository_root is None else Path(repository_root).resolve()


def register_repo_diff_check_tools(mcp):
    """Use the same helpers as run_action, with source-owned argv and no timeout."""

    def item():
        return hub.build_registry()[ACTION]

    @mcp.tool()
    def mathformer_repo_diff_check_admit(
        extra_args: list[str], seen: list[str]
    ) -> Admitted:
        return {
            "admission": hub.admit_action(
                ACTION, hub.build_registry(), extra_args, seen
            )
        }

    @mcp.tool()
    def mathformer_repo_diff_check_reject(admission: Admission) -> Result:
        return {"result": hub.reject_action(ACTION, admission)}

    @mcp.tool()
    def mathformer_repo_diff_check_prepare(
        context: Context, extra_args: list[str], repository_root: str | None
    ) -> Prepared:
        boundary = hub.prepare_leaf_boundary(
            item(),
            hub.RunContext(**context),
            extra_args,
            repository_root=mount(repository_root),
        )
        # Nanosecond timestamps travel as decimal strings to preserve integers
        # across JSON/PRISM numeric representations, then regain native types.
        boundary["snapshot"] = {
            path: {**asdict(state), "mtime_ns": str(state.mtime_ns)}
            for path, state in boundary["snapshot"].items()
        }
        return {"boundary": boundary}

    @mcp.tool()
    def mathformer_repo_diff_check_early_return(boundary: Boundary) -> Result:
        return {"result": boundary["payload"]}

    @mcp.tool()
    def mathformer_repo_diff_check_launch(
        boundary: Boundary, repository_root: str | None
    ) -> Launched:
        # Transported payloads cannot supply arbitrary commands to the service.
        if not boundary["execute"] or boundary["payload"][
            "argv"
        ] != hub.resolve_command(item().command):
            raise ValueError("invalid repo:diff-check execution boundary")
        return {
            "payload": hub.launch_leaf_boundary(
                item(), boundary["payload"], repository_root=mount(repository_root)
            )
        }

    @mcp.tool()
    def mathformer_repo_diff_check_finish(
        boundary: Boundary, payload: dict, repository_root: str | None
    ) -> Result:
        boundary = {
            **boundary,
            "snapshot": {
                path: FileState(
                    size=state["size"],
                    mtime_ns=int(state["mtime_ns"]),
                    digest=state["digest"],
                )
                for path, state in boundary["snapshot"].items()
            },
        }
        return {
            "result": hub.finish_leaf_boundary(
                item(), boundary, payload, repository_root=mount(repository_root)
            )
        }
