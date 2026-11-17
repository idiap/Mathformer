# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP stages shared with the authoritative release gate entrypoint."""

import importlib.util
from pathlib import Path
from typing import Callable
from typing_extensions import NotRequired, TypedDict

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "tests/physics_lean/run_mathformerphysicslib_release_gate.py"
)
spec = importlib.util.spec_from_file_location("_physics_release_gate", SOURCE)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load release gate from {SOURCE}")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


class Check(TypedDict):
    command: list[str]
    returncode: int | None
    ok: bool
    stdout: str
    stderr: str
    diagnostic_sha256: str
    timeout: NotRequired[bool]


class ReleaseStatus(TypedDict):
    status_schema_version: int
    workflow_executed: bool
    checks_passed: bool
    artifact_status: str
    library_status: str
    release_ok: bool
    blockers: list[str]
    terminal_states: list[str]


class Result(TypedDict):
    result: Check


class Imports(TypedDict):
    imports: list[str]


class Release(TypedDict):
    release: ReleaseStatus


class Report(TypedDict):
    report: dict


def register_physics_release_gate_tools(
    mcp, write_policy: Callable[[], None] = lambda: None
):
    """Expose run(output)'s stages without catching native failures or retrying.

    The service supplies its write policy. Filesystem paths retain the native
    process's resolution semantics; only Path/value conversion happens here.
    """

    @mcp.tool()
    def mathformer_physics_release_build() -> Result:
        """Build MathformerPhysicsLib; caught 900s timeout is a failed check."""
        write_policy()
        return {"result": native.build_public_root()}

    @mcp.tool()
    def mathformer_physics_release_coherence() -> Result:
        """Run the native release coherence gate with its 180s timeout."""
        write_policy()
        return {"result": native.check_coherence()}

    @mcp.tool()
    def mathformer_physics_release_lean_version() -> Result:
        """Query Lean with the native 30s timeout and diagnostic hashing."""
        return {"result": native.check_lean_version()}

    @mcp.tool()
    def mathformer_physics_release_scan_imports() -> Imports:
        """Collect existing direct imports in source order, keeping duplicates."""
        return {"imports": [str(path) for path in native.imported_files()]}

    @mcp.tool()
    def mathformer_physics_release_assess(
        build: Check, coherence: Check, lean_version: Check
    ) -> Release:
        """Derive native release and library status from all three check values."""
        return {"release": native.assess_release(build, coherence, lean_version)}

    @mcp.tool()
    def mathformer_physics_release_write_report(
        output: str,
        imports: list[str],
        build: Check,
        coherence: Check,
        lean_version: Check,
        release: ReleaseStatus,
    ) -> Report:
        """Hash sources and write the native sorted JSON report, returning it."""
        write_policy()
        return {
            "report": native.write_report(
                Path(output),
                [Path(p) for p in imports],
                build,
                coherence,
                lean_version,
                release,
            )
        }
