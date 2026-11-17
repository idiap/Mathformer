# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP boundaries shared with the paper evidence packet CLI.

No validation command listed in a packet is executed. CLI console output goes
onto stderr (MCP stdout is framing) and is also returned as a typed receipt.
"""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "paper_skills/framework-repository-cartographer/scripts/build_paper_evidence_packet.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "paper_evidence_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    args: dict


class Built(TypedDict):
    packets: list[dict]


class Finalized(TypedDict):
    packet: dict


class Written(TypedDict):
    path: str
    artifact: dict


class Emitted(TypedDict):
    result: dict
    exit_code: int
    stdout: str


def register_paper_evidence_packet_tools(mcp, write_guard=lambda path: None):
    @mcp.tool()
    def mathformer_paper_evidence_parse(argv: list[str]) -> Parsed:
        # argparse exits must terminate this invocation, never the MCP server.
        try:
            with redirect_stdout(sys.stderr):
                args = source().parse_options(argv)
        except SystemExit as error:
            raise ValueError(
                f"argparse terminated with exit code {error.code}"
            ) from error
        return {"args": args}

    @mcp.tool()
    def mathformer_paper_evidence_build_all() -> Built:
        return {"packets": source().build_all_packets()}

    @mcp.tool()
    def mathformer_paper_evidence_build_one(args: dict) -> Built:
        return {"packets": source().build_one_packet(args["feature"])}

    @mcp.tool()
    def mathformer_paper_evidence_finalize(
        args: dict, packets: list[dict]
    ) -> Finalized:
        return {"packet": source().finalize_packet(args["feature"], packets)}

    @mcp.tool()
    def mathformer_paper_evidence_write(args: dict, packet: dict) -> Written:
        output = source().resolve_output(args["output"])
        write_guard(output)
        path = source().write_packet(args["output"], packet)
        return {"path": str(path), "artifact": packet}

    @mcp.tool()
    def mathformer_paper_evidence_emit(args: dict, packet: dict, path: str) -> Emitted:
        stream = io.StringIO()
        with redirect_stdout(stream):
            result, code = source().emit_result(args, packet, Path(path))
        stdout = stream.getvalue()
        print(stdout, end="", file=sys.stderr)
        return {"result": result, "exit_code": code, "stdout": stdout}


def main():
    """Serve this tool family without loading unrelated scientific backends."""
    import argparse
    from mcp.server.fastmcp import FastMCP

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readonly", action="store_true")
    parser.add_argument("--write-root", action="append", default=[])
    options = parser.parse_args()
    roots = [Path(path).resolve() for path in options.write_root]

    def guard(path):
        if options.readonly:
            raise PermissionError(
                "Evidence packet writes are disabled by service read-only policy"
            )
        if roots and not any(path.resolve().is_relative_to(root) for root in roots):
            raise PermissionError(
                f"paper evidence output outside configured service roots: {path}"
            )

    mcp = FastMCP("mathformer-paper-evidence-packet")
    register_paper_evidence_packet_tools(mcp, guard)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
