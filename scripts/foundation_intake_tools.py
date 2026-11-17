# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP bindings to the steps shared with native foundation intake main.

The CLI's cwd, argv=None and program name are explicit remote context. Native
stdout is returned as evidence and mirrored to stderr to protect MCP framing.
"""

from contextlib import redirect_stdout, redirect_stderr
import argparse
import importlib.util
import io
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "skills/physics-common/physics-foundation-object-intake/scripts/intake_physics_foundation_objects.py"
)
spec = importlib.util.spec_from_file_location("_foundation_intake", SOURCE)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class Context(TypedDict):
    working_directory: str
    allow_mutating: bool
    process_argv: list[str]
    program_name: str


class Parsed(TypedDict):
    args: dict
    halted: bool
    help_text: str


class Loaded(TypedDict):
    intake: dict


class Normalized(TypedDict):
    packet: dict
    packet_json: str


class Serialized(TypedDict):
    text: str


class Emitted(TypedDict):
    exit_code: int
    stdout: str


class Helped(TypedDict):
    packet: None
    json_text: str
    exit_code: int
    stdout: str


def working_directory(context):
    root = Path(context["working_directory"])
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("working_directory must be an existing absolute directory")
    return root


def register_foundation_intake_tools(mcp, before_write, path_allowed):
    @mcp.tool()
    def mathformer_foundation_intake_parse(
        argv: list[str] | None, context: Context
    ) -> Parsed:
        working_directory(context)
        stdout, stderr = io.StringIO(), io.StringIO()
        namespace = argparse.Namespace()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                args = native.parse_options(
                    context["process_argv"] if argv is None else argv,
                    prog=context["program_name"],
                    namespace=namespace,
                )
        except SystemExit as error:
            print(stdout.getvalue() + stderr.getvalue(), end="", file=sys.stderr)
            if error.code != 0:
                raise ValueError(
                    f"argparse exit {error.code}: {stderr.getvalue()}"
                ) from error
            # Help terminates before loading/normalizing/writing anything.
            args = native.portable_options(namespace)
            return dict(args=args, halted=True, help_text=stdout.getvalue())
        return dict(args=args, halted=False, help_text="")

    @mcp.tool()
    def mathformer_foundation_intake_self_test_inputs() -> Loaded:
        return {"intake": native.self_test_inputs()}

    @mcp.tool()
    def mathformer_foundation_intake_load_inputs(
        args: dict, context: Context
    ) -> Loaded:
        return {"intake": native.load_inputs(args, working_directory(context))}

    @mcp.tool()
    def mathformer_foundation_intake_normalize(intake: dict) -> Normalized:
        packet = native.build_packet(**intake)
        # Lunar sorts record keys in transit. Carry native insertion order too,
        # so CLI JSON bytes remain identical, including Unicode and indentation.
        return {"packet": packet, "packet_json": json.dumps(packet, ensure_ascii=False)}

    @mcp.tool()
    def mathformer_foundation_intake_serialize(
        args: dict, packet: dict, packet_json: str
    ) -> Serialized:
        ordered = json.loads(packet_json)
        if ordered != packet:
            raise ValueError("Serialized packet does not match its typed payload")
        return {"text": native.serialize_packet(args, ordered)}

    @mcp.tool()
    def mathformer_foundation_intake_emit(
        args: dict, text: str, context: Context
    ) -> Emitted:
        def guard(path):
            before_write()
            if not context["allow_mutating"]:
                raise ValueError("Intake output writes require allow_mutating")
            if not path_allowed(path.resolve()):
                raise ValueError("Intake output is outside service write roots")

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = native.emit_output(
                args, text, working_directory(context), before_write=guard
            )
        print(stdout.getvalue(), end="", file=sys.stderr)
        return {"exit_code": code, "stdout": stdout.getvalue()}

    @mcp.tool()
    def mathformer_foundation_intake_help(help_text: str) -> Helped:
        return dict(packet=None, json_text="", exit_code=0, stdout=help_text)
