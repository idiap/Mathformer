# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the native skill projection builder; no provider dependency."""

from pathlib import Path
import sys
from typing_extensions import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "meta_skills/scripts"))
import build_skill_projections as native


class State(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Written(TypedDict):
    written: dict


class Report(TypedDict):
    report: dict


def register_skill_projection_tools(
    mcp, before_write=lambda: None, path_allowed=lambda path: True
):
    @mcp.tool()
    def mathformer_skill_projections_initialize(
        source: dict, destinations: dict, repository_root: str
    ) -> State:
        root = Path(repository_root).resolve()
        state = native.initialize_build(
            root
            / destinations.get(
                "output_path", "meta_skills/taxonomy/skill_projection_cards.json"
            ),
            root
            / destinations.get(
                "report_path", "artifacts/meta_skills/skill_projection_report.json"
            ),
            root,
        )
        paths = [Path(p).relative_to(root).as_posix() for p in state["registries"]]
        if paths != source["registry_paths"] or len(paths) > 10000:
            raise ValueError("registry manifest mismatch or domain exceeded")
        ids = source["projected_skill_ids"]
        if len(ids) > 10000 or len(set(ids)) != len(ids):
            raise ValueError("projected skill manifest domain exceeded")
        state["projected_skill_ids"] = ids
        return {"state": state}

    @mcp.tool()
    def mathformer_skill_projections_registry_iteration(state: dict) -> Advanced:
        return native.registry_iteration(state)

    @mcp.tool()
    def mathformer_skill_projections_prepare_card_pass(state: dict) -> State:
        if set(state["cards"]) != set(state["projected_skill_ids"]):
            raise ValueError("projected skill manifest mismatch")
        return {"state": native.prepare_card_pass(state)}

    @mcp.tool()
    def mathformer_skill_projections_card_iteration(state: dict) -> Advanced:
        return native.card_iteration(state)

    def authorize(state, key):
        before_write()
        if not path_allowed(Path(state["destinations"][key]).resolve()):
            raise ValueError("destination outside allowed write roots")

    @mcp.tool()
    def mathformer_skill_projections_write_cards(state: dict) -> Written:
        authorize(state, "output_path")
        return {"written": native.write_cards(state)}

    @mcp.tool()
    def mathformer_skill_projections_write_report(written: dict) -> Report:
        authorize(written["state"], "report_path")
        return {"report": native.write_report(written)}
