# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline service using production registration, plus a frozen source oracle."""

from pathlib import Path


def serve(base):
    import mathformer as hub
    from mcp_server import mcp, apply_runtime_config
    from mathlib_route_tools import selected_match, checked_registry

    base = Path(base).resolve()
    apply_runtime_config(allowed_write_roots=[str(base)])

    @mcp.tool()
    def fixture_mathlib_original(
        context: dict, match: dict, registry: dict, repository_root: str
    ) -> dict:
        root = Path(repository_root).resolve()
        assert root.is_relative_to(base) and root != hub.REPO_ROOT
        scope = dict(vars(hub))
        exec(
            Path(__file__).with_name("mathlib_route_original.py.txt").read_text(), scope
        )
        return scope["run_intent_match"](
            selected_match(match),
            checked_registry(registry),
            hub.RunContext(**context),
            repository_root=root,
        )

    mcp.run(transport="stdio")
