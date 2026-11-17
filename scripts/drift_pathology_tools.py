# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP bindings for the monitor's shared native stages."""

from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "skills/physics-lean/physics-lean-drift-pathology-monitor/scripts/monitor_physics_lean_drift_pathologies.py"
)
spec = importlib.util.spec_from_file_location("_drift_pathology_monitor", SOURCE)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class Context(TypedDict):
    working_directory: str
    program_name: str
    process_argv: list[str]
    allow_mutating: bool


class Parsed(TypedDict):
    options: dict


class Loaded(TypedDict):
    material: dict
    material_json: str


class Inspected(TypedDict):
    analysis: dict
    analysis_json: str


class Accumulated(TypedDict):
    findings: list[dict]
    findings_json: str


class Reported(TypedDict):
    report: dict
    report_json: str


class Emitted(TypedDict):
    exit_code: int
    stdout: str


class Helped(TypedDict):
    report: None
    exit_code: int
    stdout: str


def directory(context):
    root = Path(context["working_directory"])
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("working_directory must be an existing absolute directory")
    return root


def packed(name, value):
    # Transport canonicalization sorts JSON object keys. Preserve the native
    # insertion order too, since cue arrays and emitted bytes are observable.
    return {name: value, name + "_json": json.dumps(value, ensure_ascii=False)}


def restored(value, serialized):
    ordered = json.loads(serialized)
    if ordered != value:
        raise ValueError("Serialized evidence does not match its typed payload")
    return ordered


def register_drift_pathology_tools(mcp, before_write, path_allowed):
    @mcp.tool()
    def mathformer_drift_parse(argv: list[str] | None, context: Context) -> Parsed:
        directory(context)
        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                args = native.parse_args(
                    context["process_argv"] if argv is None else argv,
                    prog=context["program_name"],
                )
        except SystemExit as error:
            print(stdout.getvalue() + stderr.getvalue(), end="", file=sys.stderr)
            if error.code != 0:
                raise ValueError(
                    f"argparse exit {error.code}: {stderr.getvalue()}"
                ) from error
            options = {
                name: None
                for name in (
                    "source_file",
                    "source_text",
                    "lean_file",
                    "lean_text",
                    "type_packet",
                    "assumption_packet",
                    "unit_report",
                    "physical_semantics_report",
                    "assumption_critic_report",
                    "dimension_critic_report",
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
    def mathformer_drift_load(options: dict, context: Context) -> Loaded:
        return packed(
            "material",
            native.load_inputs(options, working_directory=directory(context)),
        )

    @mcp.tool()
    def mathformer_drift_inspect_pack(material: dict, material_json: str) -> Inspected:
        return packed(
            "analysis", native.inspect_pack(**restored(material, material_json))
        )

    @mcp.tool()
    def mathformer_drift_apply_rules(analysis: dict, analysis_json: str) -> Accumulated:
        return packed("findings", native.apply_rules(restored(analysis, analysis_json)))

    @mcp.tool()
    def mathformer_drift_summarize(
        analysis: dict, analysis_json: str, findings: list[dict], findings_json: str
    ) -> Reported:
        return packed(
            "report",
            native.summarize(
                restored(analysis, analysis_json), restored(findings, findings_json)
            ),
        )

    @mcp.tool()
    def mathformer_drift_self_test() -> Reported:
        return packed("report", native.run_self_test())

    @mcp.tool()
    def mathformer_drift_emit(
        options: dict, report: dict, report_json: str, context: Context
    ) -> Emitted:
        def guard(path):
            before_write()
            if not context["allow_mutating"]:
                raise ValueError("Monitor output writes require allow_mutating")
            if not path_allowed(path.resolve()):
                raise ValueError("Monitor output is outside service write roots")

        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.emit(
                options,
                restored(report, report_json),
                working_directory=directory(context),
                before_write=guard,
            )
        print(stream.getvalue(), end="", file=sys.stderr)
        return {"exit_code": code, "stdout": stream.getvalue()}

    @mcp.tool()
    def mathformer_drift_help(options: dict) -> Helped:
        return {"report": None, "exit_code": 0, "stdout": options["help_text"]}
