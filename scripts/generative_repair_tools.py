# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real MCP projections of the advisory repair planner's shared native steps."""

from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "skills/physics-lean/physics-lean-generative-repair-orchestrator/scripts/build_physics_lean_generative_repair_plan.py"
)
spec = importlib.util.spec_from_file_location("_generative_repair_native", SOURCE)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class Context(TypedDict):
    working_directory: str
    program_name: str


class Loaded(TypedDict):
    data: dict | None
    data_json: str
    control: dict


class Prepared(TypedDict):
    prepared: dict


class Prompts(TypedDict):
    prompts: list[dict]
    prompts_json: str


class Flags(TypedDict):
    flags: dict


class Assembled(TypedDict):
    plan: dict | None
    plan_json: str


class Emitted(TypedDict):
    exit_code: int
    stdout: str


class Helped(TypedDict):
    plan: dict | None
    exit_code: int
    stdout: str


def restored(value, serialized):
    # JSON payload canonicalization in the host must not change Python repr in
    # prompts or native output key order. Carry and check ordered wire evidence.
    ordered = json.loads(serialized)
    if ordered != value:
        raise ValueError("Ordered evidence does not match typed payload")
    return ordered


def register_generative_repair_tools(mcp, before_write, path_allowed):
    @mcp.tool()
    def mathformer_generative_repair_load(argv: list[str], context: Context) -> Loaded:
        """Use the native parser and file loader; help stops before file reads."""
        root = Path(context["working_directory"])
        if not root.is_absolute() or not root.is_dir():
            raise ValueError("working_directory must be an existing absolute directory")
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                data, control = native.load_inputs(
                    argv, working_directory=root, program_name=context["program_name"]
                )
        except SystemExit as error:
            print(stderr.getvalue(), end="", file=sys.stderr)
            if error.code != 0:
                raise ValueError(
                    f"argparse exit {error.code}: {stderr.getvalue()}"
                ) from error
            return {
                "data": None,
                "data_json": "null",
                "control": {
                    "self_test": False,
                    "output": None,
                    "halted": True,
                    "help_text": stdout.getvalue(),
                },
            }
        control.update(halted=False, help_text="")
        return {
            "data": data,
            "data_json": json.dumps(data, ensure_ascii=False),
            "control": control,
        }

    @mcp.tool()
    def mathformer_generative_repair_prepare(data: dict, data_json: str) -> Prepared:
        return {"prepared": native.prepare_inputs(restored(data, data_json))}

    @mcp.tool()
    def mathformer_generative_repair_prompts(
        data: dict, data_json: str, prepared: dict
    ) -> Prompts:
        prompts = native.prompts_for_inputs(restored(data, data_json), prepared)
        return {
            "prompts": prompts,
            "prompts_json": json.dumps(prompts, ensure_ascii=False),
        }

    @mcp.tool()
    def mathformer_generative_repair_guards(data: dict, data_json: str) -> Flags:
        return {"flags": native.plan_flags(restored(data, data_json))}

    @mcp.tool()
    def mathformer_generative_repair_assemble(
        data: dict,
        data_json: str,
        prepared: dict,
        prompts: list[dict],
        prompts_json: str,
        flags: dict,
        status: str,
    ) -> Assembled:
        plan = native.assemble_plan(
            restored(data, data_json),
            prepared,
            restored(prompts, prompts_json),
            flags,
            status,
        )
        return {"plan": plan, "plan_json": json.dumps(plan, ensure_ascii=False)}

    @mcp.tool()
    def mathformer_generative_repair_emit(
        control: dict, plan: dict, plan_json: str
    ) -> Emitted:
        if control["output"]:
            before_write()
            if not path_allowed(Path(control["output"]).resolve()):
                raise ValueError("Plan output is outside service write roots")
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.emit_plan(control, restored(plan, plan_json))
        print(stream.getvalue(), end="", file=sys.stderr)
        return {"exit_code": code, "stdout": stream.getvalue()}

    @mcp.tool()
    def mathformer_generative_repair_help(control: dict) -> Helped:
        print(control["help_text"], end="", file=sys.stderr)
        return {"plan": None, "exit_code": 0, "stdout": control["help_text"]}
