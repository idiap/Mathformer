# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP bindings for the selected native equational-trace suite."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "sympy_controlled_suite_native", ROOT / "tests/sympy/run_controlled_suite.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Initialized(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class CaseOutput(TypedDict):
    report: dict


class Finished(TypedDict):
    result: dict


class CompletionOutput(TypedDict):
    completion: dict


def register_sympy_equational_trace_tools(mcp, before_write, path_allowed):
    """Bind the loop contract to the same helpers used by native main().

    The hub interface below specializes the default paths and JSON mode. This
    interface also carries the CLI artifact-root and output-mode arguments.
    Both the equational-trace loop and the executable-symbolic-derivation
    profile's associated materialization use these tools. Neither interface
    treats the profile's epistemic dependency graph as a unique schedule.
    """

    def paths(state):
        workspace = Path(state["working_directory"]).resolve()
        root, index = Path(state["root"]), Path(state["api_index"])
        if not workspace.is_dir():
            raise ValueError("Suite working directory must exist")
        if not root.is_absolute() or not index.is_absolute():
            raise ValueError("Suite paths must be absolute")
        if index != workspace / "artifacts/sympy_api/index.json":
            raise ValueError("API index differs from the native default")
        if state["python"] != str(source().PYTHON):
            raise ValueError("Python differs from the native executable")
        # The indexer also writes sibling JSONL and per-module index files.
        if not path_allowed(root.resolve()) or not path_allowed(index.parent.resolve()):
            raise ValueError("Suite outputs are outside allowed write roots")
        return workspace

    def invoke(name, state, *args):
        before_write()
        workspace = paths(state)
        native = source()
        token = native.WORKING_DIRECTORY.set(workspace)
        stream = io.StringIO()
        try:
            with redirect_stdout(stream):
                result = getattr(native, name)(state, *args)
            if name in ("finish", "preflight_failure"):
                result["stdout"] = stream.getvalue()
            return result
        finally:
            native.WORKING_DIRECTORY.reset(token)

    @mcp.tool()
    def mathformer_sympy_equational_trace_initialize(
        context: dict, artifact_root: str, json_output: bool
    ) -> Initialized:
        """Resolve CLI inputs and create the native suite's initial state."""
        before_write()
        if context.get("allow_mutating") is not True:
            raise ValueError("Suite requires allow_mutating")
        workspace = Path(context["working_directory"]).resolve()
        root = Path(artifact_root)
        root = (root if root.is_absolute() else workspace / root).resolve()
        index = workspace / "artifacts/sympy_api/index.json"
        seed = {
            "working_directory": str(workspace),
            "root": str(root),
            "api_index": str(index),
            "python": str(source().PYTHON),
        }
        paths(seed)
        return {
            "state": {
                **source().initialize(root, index, json_output),
                "working_directory": str(workspace),
            }
        }

    @mcp.tool()
    def mathformer_sympy_equational_trace_preflight_step(state: dict) -> Advanced:
        """Run the next preflight command and accumulate its native outcome."""
        return invoke("preflight_step", state)

    @mcp.tool()
    def mathformer_sympy_equational_trace_preflight_failure(
        state: dict,
    ) -> CompletionOutput:
        """Write the native early failure report and retain console output."""
        return {"completion": invoke("preflight_failure", state)}

    @mcp.tool()
    def mathformer_sympy_equational_trace_prepare_cases(state: dict) -> Initialized:
        """Reset the cursor after successful preflight."""
        return {"state": invoke("prepare_cases", state)}

    @mcp.tool()
    def mathformer_sympy_equational_trace_suite_case(state: dict) -> CaseOutput:
        """Execute the current case with native ordering and fail-fast stages."""
        return {"report": invoke("suite_case", state)}

    @mcp.tool()
    def mathformer_sympy_equational_trace_collect_case(
        state: dict, report: dict
    ) -> Advanced:
        """Retain a successful or failed case and advance through all five sources."""
        return invoke("collect_case", state, report)

    @mcp.tool()
    def mathformer_sympy_equational_trace_skip_cases(state: dict) -> Advanced:
        """Carry failed preflight through the guarded loop without case commands."""
        return invoke("skip_cases", state)

    @mcp.tool()
    def mathformer_sympy_equational_trace_finish(state: dict) -> CompletionOutput:
        """Write the native HTML index, suite report, exit status and console output."""
        return {"completion": invoke("finish", state)}


def register_sympy_controlled_suite_tools(mcp, before_write, path_allowed):
    register_sympy_equational_trace_tools(mcp, before_write, path_allowed)

    def invoke(name, state, *args):
        before_write()
        workspace = Path(state["working_directory"]).resolve()
        if not path_allowed(workspace / "artifacts"):
            raise ValueError(
                "Suite workspace artifacts are outside allowed write roots"
            )
        if (
            Path(state["root"]) != workspace / "artifacts/sympy/controlled_suite"
            or Path(state["api_index"]) != workspace / "artifacts/sympy_api/index.json"
        ):
            raise ValueError("Suite paths must match the fixed native invocation")
        native = source()
        token = native.WORKING_DIRECTORY.set(workspace)
        stream = io.StringIO()
        try:
            with redirect_stdout(stream):
                result = getattr(native, name)(state, *args)
            if name in ("finish", "preflight_failure"):
                result["stdout"] = stream.getvalue()
            return result
        finally:
            native.WORKING_DIRECTORY.reset(token)

    @mcp.tool()
    def mathformer_sympy_controlled_suite_initialize(context: dict) -> Initialized:
        before_write()
        if not context.get("allow_mutating", False):
            raise ValueError("Suite requires allow_mutating")
        workspace = Path(context["working_directory"]).resolve()
        if not path_allowed(workspace / "artifacts"):
            raise ValueError(
                "Suite workspace artifacts are outside allowed write roots"
            )
        state = source().initialize(
            workspace / "artifacts/sympy/controlled_suite",
            workspace / "artifacts/sympy_api/index.json",
        )
        return {"state": {**state, "working_directory": str(workspace)}}

    @mcp.tool()
    def mathformer_sympy_controlled_suite_preflight_step(state: dict) -> Advanced:
        return invoke("preflight_step", state)

    @mcp.tool()
    def mathformer_sympy_controlled_suite_preflight_failure(state: dict) -> Finished:
        return {"result": invoke("preflight_failure", state)}

    @mcp.tool()
    def mathformer_sympy_controlled_suite_prepare_cases(state: dict) -> Initialized:
        return {"state": invoke("prepare_cases", state)}

    @mcp.tool()
    def mathformer_sympy_controlled_suite_run_case(state: dict) -> CaseOutput:
        return {"report": invoke("suite_case", state)}

    @mcp.tool()
    def mathformer_sympy_controlled_suite_collect_case(
        state: dict, report: dict
    ) -> Advanced:
        return invoke("collect_case", state, report)

    @mcp.tool()
    def mathformer_sympy_controlled_suite_skip_cases(state: dict) -> Advanced:
        return source().skip_cases(state)

    @mcp.tool()
    def mathformer_sympy_controlled_suite_finish(state: dict) -> Finished:
        return {"result": invoke("finish", state)}


def create_server():
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("Mathformer controlled SymPy suite")
    register_sympy_controlled_suite_tools(
        server, lambda: None, lambda path: path.resolve().is_relative_to(ROOT)
    )
    return server


if __name__ == "__main__":
    create_server().run(transport="stdio")
