# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP stages sharing the native all-candidate Lean compilation steps.

The descriptor specializes uncapped native discovery to an asserted 0..256
case domain. Admission rejects a mismatch before any compiler invocation.
"""

import importlib.util
from pathlib import Path
from typing_extensions import TypedDict

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "tests/physics_lean/run_mathformerphysicslib_all_candidate_compile.py"
)
spec = importlib.util.spec_from_file_location("_physics_candidate_compile", SOURCE)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class Discovered(TypedDict):
    state: dict
    pending: bool


class Compiled(TypedDict):
    record: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Finished(TypedDict):
    report: dict


def register_physics_candidate_compile_tools(
    mcp, write_policy=lambda: None, path_allowed=lambda path: True
):
    def writable(path):
        write_policy()
        if not path_allowed(path):
            raise ValueError(
                f"Candidate compilation write outside service roots: {path}"
            )

    @mcp.tool()
    def mathformer_physics_candidates_discover(request: dict) -> Discovered:
        state = native.discover_state(Path(request["repository_root"]).resolve())
        if (
            len(state["cases"]) != request["case_count"]
            or not 0 <= request["case_count"] <= 256
        ):
            raise ValueError("case_count must equal discovery and be at most 256")
        return {"state": state, "pending": bool(state["cases"])}

    @mcp.tool()
    def mathformer_physics_candidates_compile(state: dict, request: dict) -> Compiled:
        root = Path(request["repository_root"]).resolve()
        writable(root / ".lake")
        return {
            "record": native.compile_next(
                state, timeout_seconds=request["timeout_seconds"], repository_root=root
            )
        }

    @mcp.tool()
    def mathformer_physics_candidates_advance(state: dict, record: dict) -> Advanced:
        updated = native.advance_state(state, record)
        return {"state": updated, "done": updated["index"] == len(updated["cases"])}

    @mcp.tool()
    def mathformer_physics_candidates_empty(state: dict) -> Advanced:
        """Project the native empty traversal without invoking the compiler."""
        return {"state": native.empty_state(state), "done": True}

    @mcp.tool()
    def mathformer_physics_candidates_finish(state: dict, request: dict) -> Finished:
        root = Path(request["repository_root"]).resolve()
        output = root / request["output"]
        writable(output)
        return {
            "report": native.finish_report(
                state["results"], output, repository_root=root
            )
        }
