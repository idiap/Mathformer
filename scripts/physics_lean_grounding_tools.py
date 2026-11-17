# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP ports for the native textual Lean physics audit.

The repository context is an explicit mount; no tool changes process globals.
The 10,000-case limit belongs to the normalized contract, not the CLI.
"""

from contextlib import redirect_stdout
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict

import audit_mathformer_physics_lean_grounding as source


class Initialized(TypedDict):
    state: dict
    nonempty: bool


class Advanced(TypedDict):
    state: dict
    done: bool


class Emitted(TypedDict):
    audit_json: dict
    audit_markdown: str
    printed_counts: dict
    exit_code: int


class Cases(TypedDict):
    cases: list[dict]


class DiscoveredUpdate(TypedDict):
    options: dict
    state: dict


class ExtractedCases(TypedDict):
    cases: list[dict]
    case_history: list[str]


class PreparedUpdate(TypedDict):
    state: dict
    run: bool


def library(repository_root: str) -> Path:
    return Path(repository_root).resolve() / "MathformerPhysicsLib"


def case_path(repository_root: str, name: str) -> Path:
    if Path(name).name != name or not name.startswith("formalphysics_"):
        raise ValueError("Expected a discovered formalphysics case name")
    return library(repository_root) / "Lean" / name


def register_physics_lean_grounding_tools(mcp, write_policy, path_allowed):
    def authorize(path):
        write_policy()
        if not path_allowed(path):
            raise ValueError("Grounding output is outside service write roots")

    @mcp.tool()
    def mathformer_physics_grounding_discover_update(
        repository_root: str, scope: dict
    ) -> DiscoveredUpdate:
        """Start the fixed update-grounding-audit action in its declared domain.

        Scope witnesses complete native discovery; it never filters the scan.
        Authorization precedes the selected mutating action, even on empty input.
        """
        authorize(library(repository_root))
        options = vars(source.parse_args(["--update-consistency"]))
        discovery = source.discover_cases(library(repository_root) / "Lean")
        if len(discovery) > 1024:
            raise ValueError("Discovery exceeds the normalized 1024-case domain")
        if scope != {"eligible_paths": discovery}:
            raise ValueError("Scope must equal complete native sorted discovery")
        return {"options": options, "state": source.initialize_scan(discovery)["state"]}

    @mcp.tool()
    def mathformer_physics_grounding_extract_cases(state: dict) -> ExtractedCases:
        """Export completed cases and native serialization order for audit files."""
        if state["pending"] or state["nonempty"]:
            raise ValueError("Cannot extract an unfinished scan")
        return {"cases": state["cases"], "case_history": state["case_history"]}

    @mcp.tool()
    def mathformer_physics_grounding_prepare_updates(
        cases: list[dict], options: dict
    ) -> PreparedUpdate:
        """Apply the native assertion before packing the report traversal."""
        if options["self_test"]:
            source.assert_grounding(cases)
        initialized = source.initialize_updates(cases)
        return {
            "state": initialized["state"],
            "run": options["update_consistency"] and initialized["nonempty"],
        }

    @mcp.tool()
    def mathformer_physics_grounding_initialize_scan(
        repository_root: str, options: dict
    ) -> Initialized:
        """Discover actual eligible paths; callers cannot supply a filtered inventory."""
        discovery = source.discover_cases(library(repository_root) / "Lean")
        if len(discovery) > 10000:
            raise ValueError("Discovery exceeds the normalized 10000-case domain")
        return source.initialize_scan(discovery)

    @mcp.tool()
    def mathformer_physics_grounding_audit_next(
        repository_root: str, state: dict
    ) -> Advanced:
        """Read and classify the next Lean file, retaining accumulated case data."""
        path = Path(state["pending"][0])
        if path != case_path(repository_root, path.name):
            raise ValueError("Pending case is outside the repository Lean mount")
        return source.audit_next(state)

    @mcp.tool()
    def mathformer_physics_grounding_assert_grounding(cases: list[dict]) -> Cases:
        """Assert nonempty high grounding and then all-high before any writes."""
        source.assert_grounding(cases)
        return {"cases": cases}

    @mcp.tool()
    def mathformer_physics_grounding_retain_cases(cases: list[dict]) -> Cases:
        """Expose unchanged cases across native empty/skipped branches."""
        return {"cases": cases}

    @mcp.tool()
    def mathformer_physics_grounding_empty_traversal(state: dict) -> Advanced:
        """Complete an empty iterator without a case read or report visit."""
        if state["pending"] or state["nonempty"]:
            raise ValueError("Empty traversal requires an empty pending iterator")
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_physics_grounding_initialize_updates(
        cases: list[dict],
    ) -> Initialized:
        return source.initialize_updates(cases)

    @mcp.tool()
    def mathformer_physics_grounding_update_next(
        repository_root: str, state: dict
    ) -> Advanced:
        """Skip absent reports or refresh one existing report under service controls."""
        report = (
            case_path(repository_root, state["pending"][0]["case"])
            / "consistency_report.json"
        )
        if report.exists():
            authorize(report)
        return source.update_next(state, library(repository_root) / "Lean")

    @mcp.tool()
    def mathformer_physics_grounding_emit_audit(
        repository_root: str, cases: list[dict], case_history: list[str], options: dict
    ) -> Emitted:
        """Write native audit bytes and preserve counts on the diagnostic channel."""
        # PRISM nominal JSON envelopes canonicalize object keys. Retain native
        # insertion order in serialized case history so file bytes also agree.
        ordered_cases = [json.loads(item) for item in case_history]
        if ordered_cases != cases:
            raise ValueError("Case history differs from the accumulated cases")
        root = library(repository_root)
        audit_json, audit_md = (
            root / "MATHLIB_GROUNDING_AUDIT.json",
            root / "MATHLIB_GROUNDING_AUDIT.md",
        )
        authorize(audit_json)
        authorize(audit_md)
        with redirect_stdout(sys.stderr):
            return source.emit_audit(ordered_cases, options, audit_json, audit_md)
