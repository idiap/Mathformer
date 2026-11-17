# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP interfaces for shared native receipt validation blocks."""

from typing_extensions import TypedDict
from adoption_receipt_render_tools import source


class ReadChecked(TypedDict):
    receipt: dict
    complete: bool


class Cursor(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Validated(TypedDict):
    provenance: dict


def register_adoption_receipt_validate_tools(mcp):
    @mcp.tool()
    def mathformer_receipt_read_check(directory: str) -> ReadChecked:
        return source().receipt_read_check(directory)

    @mcp.tool()
    def mathformer_receipt_pack_cursor(
        receipt: dict, terminal_step: str, terminal_status: str
    ) -> Cursor:
        return {
            "state": source().receipt_pack_cursor(
                receipt, terminal_step, terminal_status
            )
        }

    @mcp.tool()
    def mathformer_receipt_validate_event(state: dict) -> Advanced:
        return source().receipt_validate_event(state)

    @mcp.tool()
    def mathformer_receipt_finish_joins(state: dict) -> Validated:
        return {"provenance": source().receipt_finish_joins(state)}
