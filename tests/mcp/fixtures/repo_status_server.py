# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Production registrations plus a frozen-source oracle in the same environment."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from mcp.server.fastmcp import FastMCP
import mathformer as hub
from adoption_check_tools import Context, Finished
from repo_status_tools import register_repo_status_tools

mcp = FastMCP("isolated-status")
register_repo_status_tools(mcp)
namespace = dict(vars(hub))
exec(
    compile(
        Path(__file__).with_name("repo_status_original.py.txt").read_text(),
        "frozen-original",
        "exec",
    ),
    namespace,
)


@mcp.tool()
def fixture_original_status(
    context: Context, extra_args: list[str], seen: list[str], repository_root: str
) -> Finished:
    return {
        "result": namespace["run_action"](
            "repo:status",
            hub.build_registry(),
            hub.RunContext(**context),
            extra_args=extra_args,
            seen=set(seen),
            repository_root=Path(repository_root),
        )
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
