# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only MCP boundaries sharing the native reasoning catalogue implementation."""

import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "skills/control/reasoning-flow-language/scripts/render_all_reasoning_flows.py"
)


class Context(TypedDict):
    repository_root: str


class Constructed(TypedDict):
    construction: dict


class Compared(TypedDict):
    outcome: dict


class Emitted(TypedDict):
    result: dict


def source(context: Context):
    """Isolate native path constants per invocation, without global cross-call state."""
    root = Path(context["repository_root"]).resolve()
    root.relative_to(ROOT)
    spec = importlib.util.spec_from_file_location("_reasoning_catalog_native", SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.REPO_ROOT = root
    module.REASONING_TYPES_FILE = root / "skills/REASONING_TYPES.yaml"
    module.SKILL_HOOKS_FILE = root / "skills/SKILL_HOOKS.yaml"
    module.ACTION_REGISTRY_FILE = root / "scripts/mathformer.py"
    module.ERFL_REGISTRY_FILE = (
        root / "skills/control/reasoning-flow-language/references/erfl-0.3.json"
    )
    module.DEFAULT_FLOWS_DIR = root / "examples/reasoning_flows"
    module.DEFAULT_OUTPUT_FILE = root / "docs/architecture/ALL_REASONING_FLOWS.md"
    module.DEFAULT_MATERIALIZATIONS_FILE = (
        root / "docs/architecture/REASONING_FLOW_MATERIALIZATIONS.md"
    )
    return module


def register_reasoning_catalog_tools(mcp):
    @mcp.tool()
    def mathformer_reasoning_catalog_construct(context: Context) -> Constructed:
        native = source(context)
        return {"construction": native.construct_catalog(native.DEFAULT_FLOWS_DIR)}

    @mcp.tool()
    def mathformer_reasoning_catalog_compare(
        context: Context, construction: dict
    ) -> Compared:
        native = source(context)
        if not construction["ok"]:
            raise ValueError("Comparison requires successful construction")
        return {
            "outcome": native.compare_catalog(
                construction,
                native.DEFAULT_OUTPUT_FILE,
                native.DEFAULT_MATERIALIZATIONS_FILE,
            )
        }

    @mcp.tool()
    def mathformer_reasoning_catalog_construction_failure(
        context: Context, construction: dict
    ) -> Compared:
        native = source(context)
        if construction["ok"]:
            raise ValueError("Failure conversion requires failed construction")
        return {
            "outcome": native.catalog_failure(
                construction["error"],
                native.DEFAULT_OUTPUT_FILE,
                native.DEFAULT_MATERIALIZATIONS_FILE,
            )
        }

    @mcp.tool()
    def mathformer_reasoning_catalog_emit(outcome: dict) -> Emitted:
        # stdout belongs to the stdio MCP transport. Route source emission to the
        # server's diagnostic stream, preserving its exact text and result payload.
        from contextlib import redirect_stdout

        with redirect_stdout(sys.stderr):
            result = source({"repository_root": str(ROOT)}).emit_catalog(outcome)
        return {"result": result}
