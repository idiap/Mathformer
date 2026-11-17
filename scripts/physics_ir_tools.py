# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""JSON ports for physics_ir.main's shared native steps.

Console output is returned verbatim and mirrored to stderr to preserve MCP
framing. Relative paths use per-call context without changing process cwd.
"""

from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict, NotRequired
import physics_ir as native


class Context(TypedDict):
    working_directory: str
    allow_mutating: bool
    program_name: NotRequired[str]


class Loaded(TypedDict):
    request: dict


class Converted(TypedDict):
    ir: dict


class Validated(TypedDict):
    errors: list[str]


class Packaged(TypedDict):
    report: dict


class Completed(TypedDict):
    completion: dict


class Helped(TypedDict):
    report: None
    completion: dict


def working_directory(context):
    root = Path(context["working_directory"])
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("working_directory must be an existing absolute directory")
    return root


def register_physics_ir_tools(mcp, before_write, path_allowed):
    @mcp.tool()
    def mathformer_physics_ir_load(argv: list[str], context: Context) -> Loaded:
        stdout, stderr = io.StringIO(), io.StringIO()
        root = working_directory(context)
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                request = native.load_request(
                    argv,
                    working_directory=root,
                    prog=context.get("program_name", "physics_ir.py"),
                )
        except SystemExit as error:
            print(stdout.getvalue() + stderr.getvalue(), end="", file=sys.stderr)
            if error.code != 0:
                raise ValueError(
                    f"argparse exit {error.code}: {stderr.getvalue()}"
                ) from error
            request = {
                "record": {},
                "case_id": "",
                "steps": [],
                "projection_bridges": [],
                "output": None,
                "write_output": False,
                "json_output": False,
                "halted": True,
                "stdout": stdout.getvalue(),
            }
        return {"request": request}

    @mcp.tool()
    def mathformer_physics_ir_convert(request: dict) -> Converted:
        return {"ir": native.convert_request(request).to_dict()}

    @mcp.tool()
    def mathformer_physics_ir_validate(ir: dict) -> Validated:
        return {"errors": native.validate_ir(native.ir_from_dict(ir))}

    @mcp.tool()
    def mathformer_physics_ir_package(ir: dict, errors: list[str]) -> Packaged:
        return {"report": native.package_report(native.ir_from_dict(ir), errors)}

    @mcp.tool()
    def mathformer_physics_ir_write(
        request: dict, report: dict, context: Context
    ) -> dict:
        before_write()
        if not context["allow_mutating"]:
            raise ValueError("Physics IR report writes require allow_mutating")
        root = working_directory(context)
        output = native.resolve_path(request["output"], root)
        if not path_allowed(output.resolve()):
            raise ValueError("Physics IR output is outside service write roots")
        native.write_report(request, report, working_directory=root)
        return {}

    @mcp.tool()
    def mathformer_physics_ir_emit(request: dict, report: dict) -> Completed:
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.emit_report(request, report)
        print(stream.getvalue(), end="", file=sys.stderr)
        return {"completion": {"stdout": stream.getvalue(), "exit_code": code}}

    @mcp.tool()
    def mathformer_physics_ir_help(request: dict) -> Helped:
        return {
            "report": None,
            "completion": {"stdout": request["stdout"], "exit_code": 0},
        }
