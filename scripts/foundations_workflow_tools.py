# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP ports over the native one-pass foundations smoke orchestrator.

The explicit repository mount is the native subprocess cwd. No provider or
compiler is substituted here; verification always invokes the native verifier.
"""

from contextlib import redirect_stdout
import importlib.util
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/physics_lean/run_foundations_workflow.py"
spec = importlib.util.spec_from_file_location("foundations_workflow_source", SOURCE)
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


class Context(TypedDict):
    repository_root: str
    allow_mutating: bool


class Prepared(TypedDict):
    paths: dict
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Intake(TypedDict):
    packet: str
    report: dict


class Surface(TypedDict):
    plan: str
    report: dict


class Report(TypedDict):
    report: dict


class Evaluated(TypedDict):
    result: dict
    rendered_result: str


class Emitted(TypedDict):
    stdout: str
    exit_code: int


FILENAMES = dict(
    intake="intake.json",
    surface_plan="surface_plan.json",
    draft_report="draft_report.json",
    verification_report="verification_report.json",
    workbench="workbench.json",
)


def native_paths(root):
    directory = root / source.ARTIFACT_DIR.relative_to(source.REPO_ROOT)
    return {key: str(directory / value) for key, value in FILENAMES.items()}


def validate_state(state, intake_path=None, complete=False):
    cursor = state["cursor"]
    if type(cursor) is not int or not 0 <= cursor <= len(source.CONCEPTS):
        raise ValueError("Invalid source concept cursor")
    argv = state["argv"]
    packet = (
        intake_path if intake_path is not None else (argv[4] if len(argv) >= 6 else "")
    )
    expected = [
        "skills/physics-common/physics-foundation-object-intake/scripts/intake_physics_foundation_objects.py",
        "--packet-id",
        "priority_1_foundations",
        "--output",
        packet,
        "--json",
    ]
    for concept in source.CONCEPTS[:cursor]:
        expected.extend(["--concept", concept])
    if argv != expected or (complete and cursor != len(source.CONCEPTS)):
        raise ValueError("Concept argv differs from the native traversal")


def register_foundations_workflow_tools(mcp, write_policy, path_allowed):
    def mount(context, paths=None, writing=False):
        root = Path(context["repository_root"]).resolve(strict=True)
        if not root.is_dir() or not path_allowed(root):
            raise ValueError("Repository mount is outside the service roots")
        expected = native_paths(root)
        if paths is not None and paths != expected:
            raise ValueError("Artifact paths differ from native controlled_suite paths")
        for path in expected.values():
            resolved = Path(path).resolve()
            if not resolved.is_relative_to(root) or not path_allowed(resolved):
                raise ValueError("Artifact path escapes the authorized mount")
        if writing:
            if not context["allow_mutating"]:
                raise ValueError("Foundations artifacts/build require allow_mutating")
            write_policy()
        return root

    @mcp.tool()
    def mathformer_foundations_prepare(context: Context) -> Prepared:
        return source.prepare(mount(context, writing=True))

    @mcp.tool()
    def mathformer_foundations_append_concept(state: dict) -> Advanced:
        validate_state(state)
        return source.append_concept(state)

    @mcp.tool()
    def mathformer_foundations_intake(
        state: dict, paths: dict, context: Context
    ) -> Intake:
        root = mount(context, paths, writing=True)
        validate_state(state, paths["intake"], complete=True)
        return source.intake(state, paths, root)

    @mcp.tool()
    def mathformer_foundations_surface(
        packet: str, paths: dict, context: Context
    ) -> Surface:
        root = mount(context, paths, writing=True)
        if packet != paths["intake"]:
            raise ValueError("Packet differs from the native intake handoff")
        return source.surface(packet, paths, root)

    @mcp.tool()
    def mathformer_foundations_draft(
        plan: str, paths: dict, context: Context
    ) -> Report:
        root = mount(context, paths, writing=True)
        if plan != paths["surface_plan"]:
            raise ValueError("Plan differs from the native surface handoff")
        return source.draft(plan, paths, root)

    @mcp.tool()
    def mathformer_foundations_verify(paths: dict, context: Context) -> Report:
        return source.verify(paths, mount(context, paths, writing=True))

    @mcp.tool()
    def mathformer_foundations_workbench(
        packet: str, paths: dict, context: Context
    ) -> Report:
        root = mount(context, paths, writing=True)
        if packet != paths["intake"]:
            raise ValueError("Packet differs from the native intake handoff")
        return source.workbench(packet, paths, root)

    @mcp.tool()
    def mathformer_foundations_evaluate(
        paths: dict,
        intake: dict,
        surface: dict,
        draft: dict,
        verify: dict,
        workbench: dict,
        context: Context,
    ) -> Evaluated:
        return source.evaluate(
            paths, intake, surface, draft, verify, workbench, mount(context, paths)
        )

    @mcp.tool()
    def mathformer_foundations_emit_native(
        result: dict, json_mode: bool, rendered_result: str
    ) -> Emitted:
        """Expose the selected source's emission signature without renaming its ports."""
        # Preserve native output on stderr; stdout belongs to the MCP protocol.
        with redirect_stdout(sys.stderr):
            return source.emit(result, json_mode, rendered_result)

    @mcp.tool()
    def mathformer_foundations_emit(
        result: dict, json: bool, rendered_result: str
    ) -> Emitted:
        """Retain the existing hub action interface over the same native emitter."""
        return mathformer_foundations_emit_native(result, json, rendered_result)
