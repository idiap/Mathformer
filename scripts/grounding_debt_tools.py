# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports over the grounding gate's shared native functions."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict


class Context(TypedDict):
    repository_root: str
    allow_mutating: bool


class Reported(TypedDict):
    report: dict


class Checked(TypedDict):
    checks: list[dict]


class Finished(TypedDict):
    exit_code: int
    stdout: str


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "tests/physics_lean/run_formal_science_grounding_debt_gate.py"
    )
    spec = importlib.util.spec_from_file_location("_grounding_debt_gate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def repository(context: Context) -> Path:
    root = Path(context["repository_root"])
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("repository_root must be an existing absolute directory")
    return root.resolve()


def register_grounding_debt_tools(mcp, before_write, path_allowed):
    @mcp.tool()
    def mathformer_grounding_debt_monitor_synthetic(context: Context) -> Reported:
        """Run the fixed synthetic monitor subprocess; propagate process/JSON errors."""
        return {
            "report": source().monitor_synthetic(repository_root=repository(context))
        }

    @mcp.tool()
    def mathformer_grounding_debt_monitor_case(
        case_id: str, context: Context
    ) -> Reported:
        """Run exactly one native case; only 0191 and 0059 are accepted."""
        return {
            "report": source().monitor_named_case(
                case_id, repository_root=repository(context)
            )
        }

    @mcp.tool()
    def mathformer_grounding_debt_construct_checks(
        bad: dict, case_0191: dict, case_0059: dict, context: Context
    ) -> Checked:
        """Retain monitor findings and construct the source's five ordered checks."""
        return {
            "checks": source().construct_checks(
                bad, case_0191, case_0059, repository_root=repository(context)
            )
        }

    @mcp.tool()
    def mathformer_grounding_debt_aggregate(checks: list[dict]) -> Reported:
        """Aggregate checks without retry, repair or short-circuit acceptance."""
        return {"report": source().aggregate(checks)}

    @mcp.tool()
    def mathformer_grounding_debt_write_report(
        report: dict, context: Context
    ) -> Reported:
        """Write only the source-owned report, under the service write policy."""
        root = repository(context)
        before_write()
        if not context["allow_mutating"]:
            raise ValueError("Grounding debt report requires allow_mutating")
        if not path_allowed(source().report_path(root).resolve()):
            raise ValueError("Grounding debt report is outside service write roots")
        return {"report": source().write_report(report, repository_root=root)}

    @mcp.tool()
    def mathformer_grounding_debt_emit_return(
        report: dict, json_output: bool
    ) -> Finished:
        """Preserve native output bytes in the result and on the MCP diagnostic stream."""
        output = io.StringIO()
        with redirect_stdout(output):
            code = source().emit_return(report, json_output)
        print(output.getvalue(), end="", file=sys.stderr)
        return {"exit_code": code, "stdout": output.getvalue()}
