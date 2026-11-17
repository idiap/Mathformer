# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP ports for the surface planner's shared native steps.

JSON companions retain insertion order through canonicalizing transports. They
are checked against typed values before use. Stdout is returned verbatim and
mirrored to stderr so source observability never corrupts MCP framing.
"""

import argparse
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import sys
from typing import Any
from typing_extensions import TypedDict

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "skills/mathformerphysicslib/mathformerphysicslib-foundation-surface-designer/scripts/design_foundation_surfaces.py"
)
spec = importlib.util.spec_from_file_location("_foundation_surface", SOURCE)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class Context(TypedDict):
    working_directory: str
    program_name: str
    allow_mutating: bool


class Parsed(TypedDict):
    args: dict


class Packet(TypedDict):
    packet: Any
    packet_json: str


class Surfaces(TypedDict):
    surfaces: list[dict]
    surfaces_json: str


class Modules(TypedDict):
    modules: list[str]


class Planned(TypedDict):
    plan: dict
    plan_json: str


class Emitted(TypedDict):
    json_text: str
    exit_code: int
    stdout: str


class Helped(TypedDict):
    plan: None
    json_text: str
    exit_code: int
    stdout: str


def working_directory(context):
    root = Path(context["working_directory"])
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("working_directory must be an existing absolute directory")
    return root


def packed(name, value):
    return {name: value, name + "_json": json.dumps(value, ensure_ascii=False)}


def restored(value, text):
    ordered = json.loads(text)
    if ordered != value:
        raise ValueError("Serialized evidence does not match its typed payload")
    return ordered


def namespace(args):
    return argparse.Namespace(
        **{
            k: Path(v) if k in ("object_packet", "output") and v is not None else v
            for k, v in args.items()
        }
    )


def register_foundation_surface_tools(mcp, before_write, path_allowed):
    @mcp.tool()
    def mathformer_foundation_surface_parse(
        argv: list[str], context: Context
    ) -> Parsed:
        working_directory(context)
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                args = native.parse_args(argv, prog=context["program_name"])
        except SystemExit as error:
            print(stdout.getvalue() + stderr.getvalue(), end="", file=sys.stderr)
            if error.code != 0:
                raise ValueError(
                    f"argparse exit {error.code}: {stderr.getvalue()}"
                ) from error
            return {
                "args": dict(
                    object_packet=None,
                    output=None,
                    self_test=False,
                    json=False,
                    halted=True,
                    help_text=stdout.getvalue(),
                )
            }
        options = {
            k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
        }
        options.update(halted=False, help_text="")
        return {"args": options}

    @mcp.tool()
    def mathformer_foundation_surface_fixture() -> Packet:
        return packed("packet", native.fixed_packet())

    @mcp.tool()
    def mathformer_foundation_surface_load(args: dict, context: Context) -> Packet:
        path = args["object_packet"]
        return packed(
            "packet",
            native.load_json(
                working_directory(context) / path if path is not None else None
            ),
        )

    @mcp.tool()
    def mathformer_foundation_surface_design(packet: Any, packet_json: str) -> Surfaces:
        return packed("surfaces", native.design_surfaces(restored(packet, packet_json)))

    @mcp.tool()
    def mathformer_foundation_surface_modules(surfaces: list[dict]) -> Modules:
        return {"modules": native.collect_modules(surfaces)}

    @mcp.tool()
    def mathformer_foundation_surface_assemble(
        packet: Any,
        packet_json: str,
        surfaces: list[dict],
        surfaces_json: str,
        modules: list[str],
    ) -> Planned:
        return packed(
            "plan",
            native.assemble_plan(
                restored(packet, packet_json),
                restored(surfaces, surfaces_json),
                modules,
            ),
        )

    @mcp.tool()
    def mathformer_foundation_surface_check_self_test(
        args: dict, plan: dict, plan_json: str
    ) -> Planned:
        return packed(
            "plan", native.check_self_test(namespace(args), restored(plan, plan_json))
        )

    @mcp.tool()
    def mathformer_foundation_surface_emit(
        args: dict, plan: dict, plan_json: str, context: Context
    ) -> Emitted:
        def guard(path):
            before_write()
            if not context["allow_mutating"]:
                raise ValueError("Surface output writes require allow_mutating")
            if not path_allowed(path.resolve()):
                raise ValueError("Surface output is outside service write roots")

        stream = io.StringIO()
        with redirect_stdout(stream):
            text, code = native.emit_plan(
                namespace(args),
                restored(plan, plan_json),
                working_directory=working_directory(context),
                before_write=guard,
            )
        print(stream.getvalue(), end="", file=sys.stderr)
        return dict(json_text=text, exit_code=code, stdout=stream.getvalue())

    @mcp.tool()
    def mathformer_foundation_surface_help(args: dict) -> Helped:
        return dict(plan=None, json_text="", exit_code=0, stdout=args["help_text"])
