# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the native one-pass reflection observer; no refinement driver."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/autoformalization/autoformalization-reflective-refinement-loop/scripts/observe_autoformalization_process.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "reflection_observer_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LoadedResult(TypedDict):
    loaded: dict


class ObservationResult(TypedDict):
    observation: dict


class OpportunitiesResult(TypedDict):
    opportunities: list[dict]


class PacketResult(TypedDict):
    packet: dict


class FinishedResult(TypedDict):
    exit_code: int


class HelpResult(TypedDict):
    packet: None
    exit_code: int


def register_reflection_observer_tools(
    mcp, write_policy=lambda: None, path_allowed=lambda path: True
):
    def guard(loaded, *keys):
        write_policy()
        for key in keys:
            value = loaded["paths"].get(key)
            if value is not None and not path_allowed(Path(value).resolve()):
                raise PermissionError(
                    f"reflection {key} is outside service write roots"
                )

    @mcp.tool()
    def mathformer_reflection_load(argv: list[str] | None) -> LoadedResult:
        """Parse native options, emit start and load report and optional comparisons."""
        # argparse must never exit the long-lived MCP process. Help retains the
        # native early stop and console output, before any file/event access.
        console = io.StringIO()
        try:
            with redirect_stdout(console):
                loaded = source().prepare_reflection(argv)
        except SystemExit as error:
            print(console.getvalue(), end="", file=sys.stderr)
            if error.code != 0:
                raise ValueError(f"argparse exited {error.code}") from error
            return {
                "loaded": {
                    "halted": True,
                    "report": {},
                    "baseline": None,
                    "monitor": None,
                    "paths": {},
                    "max_opportunities": 8,
                    "write_baseline": False,
                    "json": False,
                }
            }
        guard(loaded, "observer_log")
        return {"loaded": source().load_reflection_inputs(loaded)}

    @mcp.tool()
    def mathformer_reflection_observe(loaded: dict) -> ObservationResult:
        """Validate the real reasoning log strictly and compare baseline evidence."""
        guard(loaded, "observer_log")
        return {"observation": source().observe_reflection(loaded)}

    @mcp.tool()
    def mathformer_reflection_propose(
        loaded: dict, observation: dict
    ) -> OpportunitiesResult:
        """Use native prioritization and Python slice, emitting retained events."""
        guard(loaded, "observer_log")
        return {"opportunities": source().propose_reflection(loaded, observation)}

    @mcp.tool()
    def mathformer_reflection_pack(
        loaded: dict, observation: dict, opportunities: list[dict]
    ) -> PacketResult:
        """Evaluate native monotonicity gates and construct the reflection packet."""
        guard(loaded, "observer_log")
        return {"packet": source().pack_reflection(loaded, observation, opportunities)}

    @mcp.tool()
    def mathformer_reflection_persist(loaded: dict, packet: dict) -> dict:
        """Write the packet even when its gate fails."""
        guard(loaded, "output_file")
        source().persist_reflection(loaded, packet)
        return {}

    def complete(loaded, packet, write_baseline):
        if loaded["write_baseline"] is not write_baseline:
            raise ValueError("finish branch differs from native write-baseline flag")
        guard(
            loaded,
            *(
                ["baseline_file", "observer_log"]
                if write_baseline
                else ["observer_log"]
            ),
        )
        # Preserve native stdout on stderr; stdout carries MCP framing.
        with redirect_stdout(sys.stderr):
            code = source().finish_reflection(loaded, packet)
        return {"exit_code": code}

    @mcp.tool()
    def mathformer_reflection_finish_with_baseline(
        loaded: dict, packet: dict
    ) -> FinishedResult:
        """Write the requested snapshot, then emit completion, print and return."""
        return complete(loaded, packet, True)

    @mcp.tool()
    def mathformer_reflection_finish(loaded: dict, packet: dict) -> FinishedResult:
        """Emit completion, print and return without a baseline write."""
        return complete(loaded, packet, False)

    @mcp.tool()
    def mathformer_reflection_help(loaded: dict) -> HelpResult:
        """Return the successful native parser early stop without artifact access."""
        if not loaded.get("halted"):
            raise ValueError("help completion requires a halted native parser")
        return {"packet": None, "exit_code": 0}
