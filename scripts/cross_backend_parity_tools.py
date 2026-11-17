# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP adapters for the shared native cross-backend parity stages.

Builder handles retain the module loaded during preparation for this service
lifetime. Explicit filesystem context supports independent artifact collections;
SymPy artifacts are executable Python, just as at the native entrypoint.
"""

from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import uuid
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


def source():
    spec = importlib.util.spec_from_file_location(
        "mathformer_parity_gate",
        ROOT / "tests/physics_sympy/run_cross_backend_parity_gate.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Prepared(TypedDict):
    plan: dict
    cases: list[dict]
    has_cases: bool


class Selected(TypedDict):
    case_id: str


class PacketOutput(TypedDict):
    packet: dict


class Appended(TypedDict):
    cases: list[dict]
    done: bool


class ReportOutput(TypedDict):
    report: dict
    exit_code: int
    stdout: str


def register_cross_backend_parity_tools(mcp):
    native = source()
    builders = {}

    @mcp.tool()
    def mathformer_parity_prepare(request: dict) -> Prepared:
        plan, builder = native.prepare_gate(
            Path(request["manifest_path"])
            if request.get("manifest_path")
            else native.MANIFEST
        )
        if (
            request["case_cap"] != 10000
            or len(plan["aligned_cases"]) > request["case_cap"]
        ):
            raise ValueError("manifest exceeds contract admission bound of 10000 cases")
        token = uuid.uuid4().hex
        builders[token] = builder
        plan["builder_handle"] = token
        plan["artifact_root"] = request.get("artifact_root")
        return {
            "plan": plan,
            "cases": native.initial_cases(),
            "has_cases": bool(plan["aligned_cases"]),
        }

    @mcp.tool()
    def mathformer_parity_select_case(plan: dict, cases: list[dict]) -> Selected:
        return {"case_id": plan["aligned_cases"][len(cases)]}

    @mcp.tool()
    def mathformer_parity_build_packet(plan: dict, case_id: str) -> PacketOutput:
        builder = builders[plan["builder_handle"]]
        root = plan["artifact_root"]
        packet = (
            builder.build_packet(case_id)
            if root is None
            else builder.build_packet(case_id, artifact_root=Path(root))
        )
        return {"packet": packet}

    @mcp.tool()
    def mathformer_parity_append_case(
        plan: dict, cases: list[dict], case_id: str, packet: dict
    ) -> Appended:
        native.append_case(plan, cases, case_id, packet)
        return {"cases": cases, "done": len(cases) == len(plan["aligned_cases"])}

    @mcp.tool()
    def mathformer_parity_empty() -> Appended:
        return {"cases": native.initial_cases(), "done": True}

    @mcp.tool()
    def mathformer_parity_report(
        request: dict, plan: dict, cases: list[dict]
    ) -> ReportOutput:
        payload = native.build_report(plan, cases)
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.emit_report(payload, request["json_output"])
        builders.pop(plan["builder_handle"], None)
        return {"report": payload, "exit_code": code, "stdout": stream.getvalue()}


def create_server():
    """Expose the parity tools independently of unrelated backend dependencies."""
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("Mathformer cross-backend parity")
    register_cross_backend_parity_tools(server)
    return server
