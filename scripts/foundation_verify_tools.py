# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports over the native foundation verifier and its Lake boundary.

An explicit repository mount supplies the native working directory. Production
always uses the real compiler; only test code substitutes subprocess.run.
"""

from contextlib import redirect_stdout
import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "skills/mathformerphysicslib/mathformerphysicslib-foundation-verifier/scripts/verify_foundation_modules.py"
)
spec = importlib.util.spec_from_file_location("foundation_verify_source", SOURCE)
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


class Context(TypedDict):
    repository_root: str
    allow_mutating: bool


class Parsed(TypedDict):
    args: dict


class Initialized(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Collected(TypedDict):
    structure: dict


class Compiled(TypedDict):
    index: dict


class Finished(TypedDict):
    report: dict


class SelfTested(TypedDict):
    state: dict


class Emitted(TypedDict):
    emission: dict


def register_foundation_verify_tools(mcp, write_policy, path_allowed):
    def mount(context):
        root = Path(context["repository_root"]).resolve(strict=True)
        if not root.is_dir() or not path_allowed(root):
            raise ValueError("Repository mount is outside service roots")
        return root

    def checked_path(root, path):
        path = Path(path)
        resolved = (path if path.is_absolute() else root / path).resolve()
        if not resolved.is_relative_to(root) or not path_allowed(resolved):
            raise ValueError("Foundation path escapes the authorized repository mount")
        return resolved

    def authorize(context):
        if not context["allow_mutating"]:
            raise ValueError("Foundation compilation/output requires allow_mutating")
        write_policy()

    @mcp.tool()
    def mathformer_foundation_verify_parse(argv: list[str]) -> Parsed:
        """Parse native CLI flags with bounded contract admission."""
        if len(argv) > 256:
            raise ValueError("Contract admits at most 256 argv tokens")
        try:
            with redirect_stdout(sys.stderr):
                return {"args": source.parse_options(argv)}
        except SystemExit as error:
            raise ValueError(
                f"Native argparse exited with code {error.code}"
            ) from error

    @mcp.tool()
    def mathformer_foundation_verify_self_test(context: Context) -> SelfTested:
        root = mount(context)
        checked_path(
            root,
            "artifacts/mathformerphysicslib/foundations/verification_self_test.lean",
        )
        authorize(context)
        report = source.self_test(root)
        return {
            "state": {
                "scan": source.initialize_scan([]),
                "done": True,
                "self_test_report": report,
            }
        }

    @mcp.tool()
    def mathformer_foundation_verify_initialize(
        args: dict, context: Context
    ) -> Initialized:
        root = mount(context)
        result = source.select_modules(args, root)
        if len(result["state"]["paths"]) > 256:
            raise ValueError("Contract admits at most 256 selected modules")
        for path in result["state"]["paths"]:
            checked_path(root, path)
        return {
            "state": {
                "scan": result["state"],
                "done": not result["has_modules"],
                "self_test_report": None,
            }
        }

    @mcp.tool()
    def mathformer_foundation_verify_scan_next(
        state: dict, context: Context
    ) -> Advanced:
        root = mount(context)
        if state["done"] or state["self_test_report"] is not None:
            raise ValueError("Cannot scan a finished or self-test selection")
        if len(state["scan"]["paths"]) > 256:
            raise ValueError("Contract admits at most 256 selected modules")
        for path in state["scan"]["paths"]:
            checked_path(root, path)
        result = source.scan_next(state["scan"], root)
        return {
            "state": {
                "scan": result["state"],
                "done": result["done"],
                "self_test_report": None,
            },
            "done": result["done"],
        }

    @mcp.tool()
    def mathformer_foundation_verify_retain_empty(state: dict) -> Advanced:
        """Guard the root loop for empty input and the already-completed self-test."""
        if not state["done"] or state["scan"] != source.initialize_scan([]):
            raise ValueError("Only a completed empty selection may bypass scanning")
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_foundation_verify_self_test_report(state: dict) -> Finished:
        if not state["done"] or state["self_test_report"] is None:
            raise ValueError("Self-test report is unavailable")
        return {"report": state["self_test_report"]}

    @mcp.tool()
    def mathformer_foundation_verify_collect(state: dict) -> Collected:
        if state["self_test_report"] is not None:
            raise ValueError("Self-test has already collected its native report")
        return {"structure": source.collect_structure(state["scan"])}

    @mcp.tool()
    def mathformer_foundation_verify_compile_index(context: Context) -> Compiled:
        root = mount(context)
        checked_path(root, ".lake")
        authorize(context)
        return {"index": source.check_foundation_index_compile(root)}

    @mcp.tool()
    def mathformer_foundation_verify_skip_compile() -> Compiled:
        return {"index": source.skip_compile()}

    @mcp.tool()
    def mathformer_foundation_verify_finalize(structure: dict, index: dict) -> Finished:
        return {"report": source.finalize_report(structure, index)}

    @mcp.tool()
    def mathformer_foundation_verify_emit(
        args: dict, report: dict, context: Context
    ) -> Emitted:
        root = mount(context)
        if args["output"]:
            checked_path(root, args["output"])
            authorize(context)
        # Keep native prints observable while reserving stdout for MCP framing.
        with redirect_stdout(sys.stderr):
            return {"emission": source.emit_report(args, report, root)}
