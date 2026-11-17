# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP ports for the shared single-case semantic packet stages.

The opaque State port refers to native Python locals in this server instance.
It retains the imported module, including callback side effects, until assembly
or failure. Handles are single use and cannot resume in another server. Artifact
roots retain Path semantics (relative to the service working directory); omitted
roots retain the native defaults. Python artifact imports have native effects.
"""

from contextlib import redirect_stdout
import importlib.util
from pathlib import Path
import sys
import uuid
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


def source():
    """Load the authoritative implementation without running its CLI."""
    spec = importlib.util.spec_from_file_location(
        "mathformer_semantic_packet",
        ROOT / "tests/physics_sympy/run_cross_backend_semantic_packet.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class State(TypedDict):
    handle: str
    phase: str


class Inspected(TypedDict):
    state: State


class Collected(TypedDict):
    state: State
    ir_ready: bool


class Assembled(TypedDict):
    packet: dict


class Readiness(TypedDict):
    ready: bool


class PacketStages:
    """Retain native objects without reimport, serialization, replay or retry."""

    def __init__(self):
        self.native = source()
        self.states = {}

    def inspect(self, case_id, artifact_root=None):
        with redirect_stdout(sys.stderr):
            state = self.native.inspect_packet(
                case_id, None if artifact_root is None else Path(artifact_root)
            )
        token = uuid.uuid4().hex
        self.states[token] = ("inspected", state)
        return {"state": {"handle": token, "phase": "inspected"}}

    def advance(self, reference, expected, stage, next_phase=None):
        token = reference["handle"]
        phase, state = self.states.pop(token)  # consume even on native failure
        if phase != reference["phase"] or phase not in expected:
            raise ValueError("semantic packet stage is out of order")
        if stage == self.native.align_packet and not self.native.packet_ir_ready(state):
            raise ValueError("IR branch is unavailable")
        if (
            stage == self.native.assemble_packet
            and phase == "collected"
            and self.native.packet_ir_ready(state)
        ):
            raise ValueError("IR branch must complete before assembly")
        with redirect_stdout(sys.stderr):
            result = stage(state)
        if next_phase is not None:
            # Rotate the token so stale references cannot replay a source step.
            token = uuid.uuid4().hex
            self.states[token] = (next_phase, result)
            return {"handle": token, "phase": next_phase}
        return result

    def collect(self, state):
        reference = self.advance(
            state, {"inspected"}, self.native.collect_packet, "collected"
        )
        return {
            "state": reference,
            "ir_ready": self.native.packet_ir_ready(
                self.states[reference["handle"]][1]
            ),
        }

    def align(self, state):
        return {
            "state": self.advance(
                state, {"collected"}, self.native.align_packet, "aligned"
            )
        }

    def readiness(self, state):
        phase, native_state = self.states[state["handle"]]
        if phase != "collected" or state["phase"] != phase:
            raise ValueError("semantic packet readiness requires collected state")
        return {"ready": self.native.packet_ir_ready(native_state)}

    def assemble(self, state):
        return {
            "packet": self.advance(
                state, {"collected", "aligned"}, self.native.assemble_packet
            )
        }


def register_cross_backend_semantic_packet_tools(mcp):
    stages = PacketStages()

    @mcp.tool()
    def mathformer_semantic_packet_inspect(
        case_id: str, artifact_root: str | None = None
    ) -> Inspected:
        """Import one artifact and inspect backend source availability."""
        return stages.inspect(case_id, artifact_root)

    @mcp.tool()
    def mathformer_semantic_packet_collect(state: State) -> Collected:
        """Collect validations and metadata without repeating the import."""
        return stages.collect(state)

    @mcp.tool()
    def mathformer_semantic_packet_readiness(state: State) -> Readiness:
        """Evaluate the native IR guard while retaining the same collected state."""
        return stages.readiness(state)

    @mcp.tool()
    def mathformer_semantic_packet_align(state: State) -> Inspected:
        """Construct the IR and bind and compare up to three backend packets."""
        return stages.align(state)

    @mcp.tool()
    def mathformer_semantic_packet_assemble(state: State) -> Assembled:
        """Return evidence, including failed evidence, and release native state."""
        return stages.assemble(state)

    return stages


def create_server():
    """Serve these production ports without loading unrelated workflow tools."""
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("Mathformer single-case semantic packet")
    register_cross_backend_semantic_packet_tools(server)
    return server


if __name__ == "__main__":
    create_server().run(transport="stdio")
