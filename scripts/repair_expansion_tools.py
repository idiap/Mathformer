# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP bindings for the native expansion mapper's shared finite stages."""

from contextlib import redirect_stderr, redirect_stdout
from functools import lru_cache
import importlib.util
import io
import json
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/physics-lean/physics-lean-repair-expansion-cartographer/scripts/map_repair_expansion.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "repair_expansion_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Context(TypedDict):
    working_directory: str
    program_name: str


class Loaded(TypedDict):
    packets: dict
    packets_json: str
    options: dict


class Carried(TypedDict):
    state: dict
    state_json: str


class Assessed(TypedDict):
    assessment: dict
    assessment_json: str


class Assigned(TypedDict):
    status: str


class Finished(TypedDict):
    expansion: dict | None
    exit_code: int
    stdout_text: str
    json_text: str


def packed(name, value):
    # PRISM canonicalizes object keys. The paired text keeps native nested key
    # order observable at the CLI emission boundary without changing the payload.
    return {name: value, name + "_json": json.dumps(value, ensure_ascii=False)}


def restored(value, serialized):
    ordered = json.loads(serialized)
    if ordered != value:
        raise ValueError("Serialized evidence does not match its typed payload")
    return ordered


def register_repair_expansion_tools(mcp, write_policy, path_allowed):
    @mcp.tool()
    def mathformer_repair_expansion_load(argv: list[str], context: Context) -> Loaded:
        """Parse once and load native inputs in order, relative to the caller."""
        directory = Path(context["working_directory"])
        if not directory.is_absolute() or not directory.is_dir():
            raise ValueError("working_directory must be an existing absolute directory")
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                args = source().parse_args(argv, prog=context["program_name"])
            except SystemExit as error:
                if error.code != 0:
                    raise ValueError(
                        f"Native argparse exited ({error.code}): {stderr.getvalue()}"
                    ) from error
                packets = {
                    key: {}
                    for key in [
                        "monitor_report",
                        "object_packet",
                        "workbench_plan",
                        "repair_loop",
                        "generative_repair",
                    ]
                }
                packets["repair_plans"] = []
                return {
                    **packed("packets", packets),
                    "options": {"early_exit": True, "stdout_text": stdout.getvalue()},
                }
        for key in [
            "monitor_report",
            "object_packet",
            "workbench_plan",
            "repair_loop",
            "generative_repair",
            "output",
        ]:
            path = getattr(args, key)
            if path is not None and not path.is_absolute():
                setattr(args, key, directory / path)
        args.repair_plan = [
            p if p.is_absolute() else directory / p for p in args.repair_plan
        ]
        return {
            **packed("packets", source().load_packets(args)),
            "options": {
                "early_exit": False,
                "stdout_text": stdout.getvalue(),
                "self_test": args.self_test,
                "output": str(args.output) if args.output is not None else None,
            },
        }

    @mcp.tool()
    def mathformer_repair_expansion_seed(packets: dict, packets_json: str) -> Carried:
        return packed("state", source().seed_map(restored(packets, packets_json)))

    @mcp.tool()
    def mathformer_repair_expansion_expand_categories(
        state: dict, state_json: str
    ) -> Carried:
        return packed("state", source().expand_categories(restored(state, state_json)))

    @mcp.tool()
    def mathformer_repair_expansion_expand_objects(
        state: dict, state_json: str
    ) -> Carried:
        return packed("state", source().expand_objects(restored(state, state_json)))

    @mcp.tool()
    def mathformer_repair_expansion_append_policies(
        state: dict, state_json: str
    ) -> Carried:
        return packed("state", source().append_policies(restored(state, state_json)))

    @mcp.tool()
    def mathformer_repair_expansion_assess(state: dict, state_json: str) -> Assessed:
        return packed("assessment", source().assess_map(restored(state, state_json)))

    @mcp.tool()
    def mathformer_repair_expansion_assign_status(value: str) -> Assigned:
        return {"status": source().assign_status(value)}

    @mcp.tool()
    def mathformer_repair_expansion_finish(
        options: dict,
        state: dict,
        state_json: str,
        assessment: dict,
        assessment_json: str,
        status: str,
    ) -> Finished:
        expansion = source().finish_map(
            restored(state, state_json), restored(assessment, assessment_json), status
        )
        if options["self_test"]:
            source().assert_fixture(expansion)
        path = Path(options["output"]) if options["output"] is not None else None
        if path is not None:
            write_policy()
            if not path_allowed(path):
                raise ValueError(
                    "Requested map path is outside the service write roots"
                )
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = source().emit_expansion(expansion, path)
        return {
            "expansion": expansion,
            "exit_code": code,
            "stdout_text": stdout.getvalue(),
            "json_text": json.dumps(expansion, ensure_ascii=False, indent=2),
        }

    @mcp.tool()
    def mathformer_repair_expansion_help(options: dict) -> Finished:
        """Return argparse's successful early exit without reading evidence."""
        if not options["early_exit"]:
            raise ValueError("No successful argparse early exit was selected")
        return {
            "expansion": None,
            "exit_code": 0,
            "stdout_text": options["stdout_text"],
            "json_text": "",
        }
