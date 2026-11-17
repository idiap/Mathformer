# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only MCP boundaries for the shared portable metadata validator.

State is explicit JSON, never a process-global cursor. Only the command fields
inspected by the native surface check are transported from the hub registry.
"""

from types import SimpleNamespace
from typing_extensions import TypedDict
from catalog_check_tools import source, repository_path, complete, CAUGHT


class Loaded(TypedDict):
    data: dict


class Cursor(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Finished(TypedDict):
    result: dict


def register_adoption_validate_tools(mcp):
    @mcp.tool()
    def mathformer_validate_load(metadata_path: str = "") -> Loaded:
        source().parse_arguments(["validate"])
        try:
            value = source().read_metadata(
                repository_path(metadata_path, source().METADATA)
            )
            return {"data": {"value": value, "error": None}}
        except CAUGHT as error:
            return {"data": {"value": None, "error": str(error)}}

    @mcp.tool()
    def mathformer_validate_initialize(data: dict) -> Cursor:
        state = {
            "data": {},
            "registry": {},
            "position": 0,
            "identities": [],
            "operations": {},
            "aliases": {},
            "error": data["error"],
        }
        if state["error"] is None:
            try:
                native = source().metadata_initialize(data["value"])
                # This is the candidate representation's finite input domain,
                # not a new limit in validate_metadata or the native CLI.
                if len(native["data"]["surfaces"]) > 4096:
                    raise ValueError("workflow metadata domain exceeds 4096 surfaces")
                native["registry"] = {
                    key: {"command": list(action.command)}
                    for key, action in native["registry"].items()
                }
                native["identities"] = sorted(native["identities"])
                state = {**native, "error": None}
            except CAUGHT as error:
                state["error"] = str(error)
        return {"state": state}

    @mcp.tool()
    def mathformer_validate_check_surface(state: dict) -> Cursor:
        if state["error"] is None:
            native = {
                **state,
                "identities": set(state["identities"]),
                "registry": {
                    key: SimpleNamespace(**action)
                    for key, action in state["registry"].items()
                },
            }
            try:
                source().metadata_check_surface(native)
            except CAUGHT as error:
                state["error"] = str(error)
            finally:
                state["identities"] = sorted(native["identities"])
        return {"state": state}

    @mcp.tool()
    def mathformer_validate_advance_guard(state: dict) -> Advanced:
        done = state["error"] is not None or source().metadata_advance(state)
        return {"state": state, "done": done}

    @mcp.tool()
    def mathformer_validate_finish(state: dict) -> Finished:
        try:
            if state["error"] is not None:
                return {"result": complete({"ok": False, "error": state["error"]}, 2)}
            index = source().metadata_finish(
                {**state, "identities": set(state["identities"])}
            )
            return {
                "result": complete(source().validation_result(state["data"], index))
            }
        except CAUGHT as error:
            return {"result": complete(source().error_result(error), 2)}
