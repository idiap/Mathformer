# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP tools sharing the authoritative portable adoption dispatcher."""

from pathlib import Path
from typing_extensions import TypedDict
from catalog_check_tools import source


class Prepared(TypedDict):
    oid: str
    inputs: dict
    metadata: dict
    surface: dict
    operation: dict
    output_dir: str | None


class Preparation(TypedDict):
    prepared: Prepared


class Result(TypedDict):
    result: dict | list


def dispatch(prepared, identities):
    if prepared["oid"] not in identities:
        raise ValueError("prepared operation does not match dispatch branch")
    return {"result": source().execute_invocation(prepared)}


def register_adoption_invoke_tools(mcp):
    @mcp.tool()
    def mathformer_invoke_prepare(
        identity: str, inputs: dict, output_dir: str | None
    ) -> Preparation:
        return {
            "prepared": source().prepare_invocation(
                identity, inputs, Path(output_dir) if output_dir is not None else None
            )
        }

    @mcp.tool()
    def mathformer_invoke_router(prepared: Prepared) -> Result:
        return dispatch(prepared, {"router:resolve"})

    @mcp.tool()
    def mathformer_invoke_hub_action(prepared: Prepared) -> Result:
        return dispatch(prepared, {"control:workflow-contract"})

    @mcp.tool()
    def mathformer_invoke_reasoning_log(prepared: Prepared) -> Result:
        return dispatch(
            prepared, {"control:reasoning-log-summary", "reasoning-log:validate"}
        )

    @mcp.tool()
    def mathformer_invoke_prism_fixture(prepared: Prepared) -> Result:
        return dispatch(
            prepared,
            {"artifact_acceptance_loop:public", "artifact_acceptance_loop:material"},
        )
