# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the detector's shared native steps and source observability."""

from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "skills/physics-common/physics-math-object-detector/scripts/detect_physics_math_objects.py"
)
spec = importlib.util.spec_from_file_location("_physics_object_detector", SOURCE)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class Context(TypedDict):
    working_directory: str
    allow_mutating: bool
    program_name: str


class Parsed(TypedDict):
    options: dict


class Loaded(TypedDict):
    data: dict
    data_json: str


class Stateful(TypedDict):
    state: dict
    state_json: str


class Packaged(TypedDict):
    packet: dict
    packet_json: str


class Emitted(TypedDict):
    exit_code: int
    stdout: str


class Helped(TypedDict):
    packet: None
    exit_code: int
    stdout: str


def working_directory(context):
    root = Path(context["working_directory"])
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("working_directory must be an existing absolute directory")
    return root


def packed(name, value):
    # Lunar canonicalizes object keys in transit. Keep native insertion order
    # for the CLI's observable JSON bytes, while retaining typed payload ports.
    return {name: value, name + "_json": json.dumps(value, ensure_ascii=False)}


def restored(value, serialized):
    ordered = json.loads(serialized)
    if ordered != value:
        raise ValueError("Serialized evidence does not match its typed payload")
    return ordered


def register_physics_object_detector_tools(mcp, before_write, path_allowed):
    @mcp.tool()
    def mathformer_physics_objects_parse_cli(
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
            options = {
                k: None
                for k in (
                    "source_file",
                    "source_text",
                    "lean_file",
                    "lean_text",
                    "monitor_report",
                    "output",
                )
            }
            options.update(self_test=False, halted=True, help_text=stdout.getvalue())
            return {"options": options}
        options = {
            k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
        }
        options.update(halted=False, help_text="")
        return {"options": options}

    @mcp.tool()
    def mathformer_physics_objects_fixed_fixture() -> Loaded:
        return packed("data", native.fixed_fixture())

    @mcp.tool()
    def mathformer_physics_objects_load_inputs(
        options: dict, context: Context
    ) -> Loaded:
        return packed(
            "data",
            native.load_inputs(options, working_directory=working_directory(context)),
        )

    @mcp.tool()
    def mathformer_physics_objects_initialize_state(
        data: dict, data_json: str
    ) -> Stateful:
        return packed("state", native.initialize_state(**restored(data, data_json)))

    @mcp.tool()
    def mathformer_physics_objects_accumulate_detections(
        state: dict, state_json: str
    ) -> Stateful:
        return packed(
            "state", native.accumulate_detections(restored(state, state_json))
        )

    @mcp.tool()
    def mathformer_physics_objects_finalize_packet(
        state: dict, state_json: str
    ) -> Packaged:
        return packed("packet", native.finalize_packet(restored(state, state_json)))

    @mcp.tool()
    def mathformer_physics_objects_check_and_emit(
        options: dict, packet: dict, packet_json: str, context: Context
    ) -> Emitted:
        def guard(path):
            before_write()
            if not context["allow_mutating"]:
                raise ValueError("Detector output writes require allow_mutating")
            if not path_allowed(path.resolve()):
                raise ValueError("Detector output is outside service write roots")

        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.check_and_emit(
                options,
                restored(packet, packet_json),
                working_directory=working_directory(context),
                before_write=guard,
            )
        print(stream.getvalue(), end="", file=sys.stderr)
        return {"exit_code": code, "stdout": stream.getvalue()}

    @mcp.tool()
    def mathformer_physics_objects_help(options: dict) -> Helped:
        return {"packet": None, "exit_code": 0, "stdout": options["help_text"]}
