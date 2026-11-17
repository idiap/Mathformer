# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only MCP steps shared with the native immutable receipt renderer."""

from functools import lru_cache
from pathlib import Path
import sys
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    directory = (
        Path(__file__).resolve().parents[1]
        / "skills/control/reasoning-log-schema-guardian/scripts"
    )
    sys.path.insert(0, str(directory))
    import adoption_provenance

    return adoption_provenance


class Validated(TypedDict):
    record: dict


class Rows(TypedDict):
    rows: list[list[str]]


class Rendered(TypedDict):
    html: str


def register_adoption_receipt_render_tools(mcp):
    """Expose native blocks; validation exceptions stop the host sequence."""

    @mcp.tool()
    def mathformer_receipt_validate(directory: str) -> Validated:
        return {"record": source().validate_invocation(directory)}

    @mcp.tool()
    def mathformer_receipt_base_rows(record: dict) -> Rows:
        return {"rows": source().summary_base_rows(record)}

    @mcp.tool()
    def mathformer_receipt_append_metadata(record: dict, rows: list[list[str]]) -> Rows:
        return {"rows": source().summary_append_metadata(record, rows)}

    @mcp.tool()
    def mathformer_receipt_assemble_html(rows: list[list[str]]) -> Rendered:
        return {"html": source().summary_html(rows)}
