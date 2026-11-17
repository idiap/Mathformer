# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared native object workbench, without subprocesses."""

import importlib.util
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from functools import lru_cache
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/mathformerphysicslib/mathformerphysicslib-object-workbench/scripts/build_mathformerphysicslib_object_workbench.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "object_workbench_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    options: dict


class Loaded(TypedDict):
    packet: dict
    native_packet_text: str


class Planned(TypedDict):
    plan: dict
    native_json_text: str


class Emitted(TypedDict):
    json_text: str
    exit_code: int
    stdout_text: str


def register_object_workbench_tools(mcp, write_policy, path_allowed):
    @mcp.tool()
    def mathformer_object_workbench_parse_options(argv: list[str]) -> Parsed:
        """Use native argparse; terminal CLI exits become terminal MCP errors."""
        text = io.StringIO()
        with redirect_stdout(text), redirect_stderr(text):
            try:
                args = source().parse_args(argv)
            except SystemExit as error:
                raise ValueError(
                    f"Native argparse exited ({error.code}): {text.getvalue()}"
                ) from error
        return {
            "options": {
                "object_packet": (
                    str(args.object_packet) if args.object_packet is not None else None
                ),
                "output": str(args.output) if args.output is not None else None,
                "self_test": args.self_test,
                "json": args.json,
            }
        }

    @mcp.tool()
    def mathformer_object_workbench_fixture_packet() -> Loaded:
        packet = source().fixture_packet()
        return {
            "packet": packet,
            "native_packet_text": json.dumps(packet, ensure_ascii=False),
        }

    @mcp.tool()
    def mathformer_object_workbench_load_packet(options: dict) -> Loaded:
        path = options["object_packet"]
        packet = source().load_json(Path(path) if path is not None else None)
        return {
            "packet": packet,
            "native_packet_text": json.dumps(packet, ensure_ascii=False),
        }

    @mcp.tool()
    def mathformer_object_workbench_build_plan(
        packet: dict, native_packet_text: str, repository_root: str | None
    ) -> Planned:
        """Search real local Lean files; null selects the native repository."""
        ordered_packet = json.loads(native_packet_text)
        if ordered_packet != packet:
            raise ValueError("Native serialization does not match the carried packet")
        root = Path(repository_root).resolve() if repository_root is not None else None
        plan = source().build_plan(object_packet=ordered_packet, repository_root=root)
        return {"plan": plan, "native_json_text": source().serialize_plan(plan)}

    @mcp.tool()
    def mathformer_object_workbench_assert_fixture(
        plan: dict, native_json_text: str
    ) -> Planned:
        return {
            "plan": source().assert_fixture(plan),
            "native_json_text": native_json_text,
        }

    @mcp.tool()
    def mathformer_object_workbench_emit_plan(
        options: dict, plan: dict, native_json_text: str
    ) -> Emitted:
        """Keep CLI output as data so printing cannot corrupt MCP stdio."""
        # Lunar canonicalizes object keys at each port. Carry native serialization
        # as a string to restore all nested insertion order before native emission.
        ordered_plan = json.loads(native_json_text)
        if ordered_plan != plan:
            raise ValueError("Native serialization does not match the carried plan")
        path = Path(options["output"]) if options["output"] is not None else None
        if path is not None:
            write_policy()
            if not path_allowed(path):
                raise ValueError(
                    "Requested plan path is outside the service write roots"
                )
        text = io.StringIO()
        with redirect_stdout(text):
            result = source().emit_plan(
                ordered_plan, output_path=path, json_output=options["json"]
            )
        return {**result, "stdout_text": text.getvalue()}
