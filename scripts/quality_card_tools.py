# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Registered adapters for the native quality-card validator's shared steps."""

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "quality_card_native",
        ROOT / "meta_skills/scripts/validate_skill_quality_cards.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Initialized(TypedDict):
    state: dict
    has_cards: bool


class Advanced(TypedDict):
    state: dict
    done: bool


class Reported(TypedDict):
    result: dict


def context_root(repository_root):
    root = (ROOT / repository_root).resolve() if repository_root else ROOT
    if not root.is_relative_to(ROOT):
        raise ValueError("quality card context must be inside the repository")
    return root


def check_state(state):
    root = context_root(state["repository_root"])
    expected = root / "artifacts/meta_skills/skill_quality_card_validation.json"
    if Path(state["output_path"]).resolve() != expected.resolve():
        raise ValueError("quality card output differs from context")
    cards = (root / "meta_skills/quality_cards").resolve()
    for path in state["paths"]:
        if not Path(path).resolve().is_relative_to(cards):
            raise ValueError("card path escapes context")
    if not 0 <= state["cursor"] <= len(state["paths"]) <= 10000:
        raise ValueError("invalid quality card cursor or bound")
    return expected


def register_quality_card_tools(mcp, write_policy=lambda path: None):
    @mcp.tool()
    def mathformer_quality_cards_initialize(
        discovered_card_count: int, repository_root: str
    ) -> Initialized:
        state = source().initialize(context_root(repository_root))
        if not 0 <= discovered_card_count <= 10000 or discovered_card_count != len(
            state["paths"]
        ):
            raise ValueError(
                "discovered_card_count must equal actual discovery and be at most 10000"
            )
        check_state(state)
        state["has_cards"] = bool(state["paths"])
        return {"state": state, "has_cards": state["has_cards"]}

    @mcp.tool()
    def mathformer_quality_cards_validate_next(state: dict) -> Advanced:
        check_state(state)
        state = source().validate_next(state)
        return {"state": state, "done": state["cursor"] == len(state["paths"])}

    @mcp.tool()
    def mathformer_quality_cards_empty(state: dict) -> Advanced:
        """Carry the native empty collection without attempting a card read."""
        check_state(state)
        if state["paths"]:
            raise ValueError("empty branch requires no discovered cards")
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_quality_cards_write_report(state: dict) -> Reported:
        output = check_state(state)
        if state["cursor"] != len(state["paths"]):
            raise ValueError("cannot report before consuming every card")
        if (
            output.resolve() != source().OUTPUT_PATH.resolve()
            and not output.resolve().is_relative_to(ROOT / "artifacts/workflow_hub")
        ):
            raise ValueError("quality card output is outside declared write roots")
        write_policy(output)
        return {"result": source().write_report(state)}
