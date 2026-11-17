#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

# File Documentation
#
# Motivation:
#   Give Mathformer one natural-language front door plus one controlled
#   execution substrate for setup, validation, backend demonstrations, artifact
#   generation, and repository-control checks.
#
# Intent:
#   Replace ad hoc "guess the script" usage with an intent-oriented interface
#   backed by a discoverable action hub whose commands are declared in code,
#   carry safety metadata, and can be audited.
#
# Function:
#   Resolves natural-language requests to controlled workflows, lists
#   registered workflows, shows their contract, runs them with dry-run and JSON
#   modes, sequences composed workflows, and audits Python entrypoints against
#   the hub, the comprehensive test matrix, and the skill-hook contract.
#
# Maintenance Notes:
#   Add new top-level repository workflows here. Add skill-owned scripts to
#   `skills/SKILL_HOOKS.yaml` and the comprehensive test matrix when they need
#   validation coverage. Keep this hub small enough that it remains trustworthy.

"""Natural-language Mathformer workflow interface and controlled action hub.

This module is deliberately dependency-light. It uses only the Python standard
library so it can serve as the first command a developer, agent, or VS Code
adapter runs in a fresh checkout.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

from reasoning_log import (
    append_skill_complete,
    append_skill_error,
    append_skill_start,
)  # noqa: E402
from scripts.workflow_write_audit import (
    audit_snapshots,
    snapshot_repository,
)  # noqa: E402

PYTHON_TOKEN = "{python}"
REPORT_DIR = REPO_ROOT / "artifacts" / "workflow_hub"

CONTROLLED_TEST_FAMILIES = (
    "control",
    "source",
    "paper",
    "textbook",
    "mathlib",
    "lean",
    "isabelle",
    "rocq",
    "sympy",
    "atp",
    "physics_lean",
    "physics_sympy",
    "rfde",
    "docs",
    "mathformerlib",
    "mathformerphysicslib",
    "environment",
    "e2e",
    "generative",
    "mcp",
    "meta_skills",
    "skills",
)


@dataclass(frozen=True)
class WorkflowAction:
    """Describe one registered repository action.

    Motivation:
        Make workflow execution explicit enough that humans and agents can
        inspect what will run before it runs.

    Intent:
        Store the stable action identifier, command, safety classification, and
        dependency metadata in one immutable record.

    Inputs:
        The dataclass fields are supplied by `build_registry`; commands are
        stored as argv lists, never shell strings.

    Outputs:
        Instances are consumed by listing, dry-run, execution, and audit paths.
    """

    action_id: str
    summary: str
    family: str
    kind: str
    safety: str
    command: Tuple[str, ...] = ()
    depends_on: Tuple[str, ...] = ()
    required_paths: Tuple[str, ...] = ()
    required_tools: Tuple[str, ...] = ()
    optional_tools: Tuple[str, ...] = ()
    writes: Tuple[str, ...] = ()
    allows_extra_args: bool = False
    timeout_seconds: Optional[int] = None
    notes: str = ""


@dataclass
class RunContext:
    """Carry shared execution options through nested workflow runs.

    Motivation:
        Keep composed workflows predictable when a top-level action invokes
        several registered child actions.

    Intent:
        Avoid global mutable flags by passing the user's runtime choices
        explicitly into every execution helper.

    Inputs:
        Populated from command-line arguments.

    Outputs:
        Read by `run_action` and `run_leaf_action` to decide whether to execute,
        print JSON, stop on failure, or permit mutating workflows.
    """

    dry_run: bool = False
    json_output: bool = False
    keep_going: bool = False
    allow_mutating: bool = False
    write_report: bool = False


@dataclass(frozen=True)
class IntentRoute:
    """Describe one natural-language route into controlled workflows.

    Motivation:
        Let users and agents ask for outcomes in ordinary language instead of
        memorizing repository action ids.

    Intent:
        Bind a human intent pattern to one or more audited workflow actions
        while keeping execution inside the existing safety model.

    Inputs:
        Fields are supplied by `build_intent_routes`; keywords are plain text
        phrases matched by the dependency-free resolver.

    Outputs:
        Instances are consumed by `resolve_intent` and optional `ask` execution.
    """

    route_id: str
    title: str
    description: str
    action_ids: Tuple[str, ...]
    positive_terms: Tuple[str, ...]
    skill_routes: Tuple[str, ...] = ()
    examples: Tuple[str, ...] = ()
    operator_note: str = ""


@dataclass(frozen=True)
class IntentMatch:
    """Represent one scored natural-language routing result.

    Motivation:
        Make NL routing inspectable instead of hiding it behind a black box.

    Intent:
        Carry the selected route, score, and evidence terms into human and JSON
        output.

    Inputs:
        Produced by `resolve_intent`.

    Outputs:
        Serialized by `intent_match_to_dict` and optionally executed by `ask`.
    """

    route: IntentRoute
    score: int
    matched_terms: Tuple[str, ...]


def rel(path: Path, repository_root: Optional[Path] = None) -> str:
    """Return a repository-relative path when possible.

    Motivation:
        Make hub output stable across machines and readable in reports.

    Intent:
        Prefer short repo-relative strings while still accepting absolute paths
        from subprocess metadata.

    Inputs:
        `path` may be inside or outside the repository.

    Outputs:
        A normalized display string.
    """

    repository_root = REPO_ROOT if repository_root is None else repository_root

    try:
        return path.resolve().relative_to(repository_root).as_posix()
    except ValueError:
        return str(path)


def py(path: str, *args: str) -> Tuple[str, ...]:
    """Build a Python command owned by the current interpreter.

    Motivation:
        Avoid platform-specific `python`, `python3`, and `py -3` assumptions.

    Intent:
        Store Python workflows with an interpreter placeholder that is resolved
        at execution time.

    Inputs:
        `path` is a repository-relative script path followed by fixed argv
        arguments.

    Outputs:
        A command tuple suitable for a `WorkflowAction`.
    """

    return (PYTHON_TOKEN, path, *args)


def uv_py(path: str, *args: str) -> Tuple[str, ...]:
    """Build a Python command launched through uv.

    Motivation:
        Keep environment setup aligned with the repository's uv-based installer.

    Intent:
        Make setup workflows use uv as the visible launcher while still running
        ordinary Python entrypoints.

    Inputs:
        `path` is a repository-relative script path followed by fixed argv
        arguments.

    Outputs:
        A command tuple suitable for a `WorkflowAction`.
    """

    return ("uv", "run", "python", path, *args)


def venv_py(path: str, *args: str) -> Tuple[str, ...]:
    """Build a command that prefers the repository virtualenv Python."""

    return (".venv/bin/python", path, *args)


def action(
    action_id: str,
    summary: str,
    *,
    family: str,
    kind: str,
    safety: str,
    command: Sequence[str] = (),
    depends_on: Sequence[str] = (),
    required_paths: Sequence[str] = (),
    required_tools: Sequence[str] = (),
    optional_tools: Sequence[str] = (),
    writes: Sequence[str] = (),
    allows_extra_args: bool = False,
    timeout_seconds: Optional[int] = None,
    notes: str = "",
) -> WorkflowAction:
    """Create a registry item with normalized tuple fields.

    Motivation:
        Keep the registry below concise without losing type and safety metadata.

    Intent:
        Provide one helper for constructing action declarations.

    Inputs:
        Human-readable metadata plus command/dependency details.

    Outputs:
        An immutable `WorkflowAction`.
    """

    return WorkflowAction(
        action_id=action_id,
        summary=summary,
        family=family,
        kind=kind,
        safety=safety,
        command=tuple(command),
        depends_on=tuple(depends_on),
        required_paths=tuple(required_paths),
        required_tools=tuple(required_tools),
        optional_tools=tuple(optional_tools),
        writes=tuple(writes),
        allows_extra_args=allows_extra_args,
        timeout_seconds=timeout_seconds,
        notes=notes,
    )


def build_registry() -> Dict[str, WorkflowAction]:
    """Return the authoritative hub action registry.

    Motivation:
        Make all common repository workflows discoverable from one place.

    Intent:
        Encode the fixed command, safety class, required inputs, and composition
        of each supported action without permitting arbitrary shell execution.

    Inputs:
        None. The registry is static by design.

    Outputs:
        A dictionary keyed by action id.
    """

    actions: List[WorkflowAction] = [
        action(
            "control:theory-library-curation-qualification",
            "Check curation profile source fidelity and require real runnable MCP bindings in Lunar.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py("tests/mcp/run_theory_library_curation_workflow_tests.py"),
            required_paths=("tests/mcp/run_theory_library_curation_workflow_tests.py",),
            timeout_seconds=120,
            notes="Requires LUNAR_PLATFORM_ROOT and explicit WORKFLOW_CONTRACT_PATH. Fails until an authoritative executable implementation is bound; never runs scientific workflows.",
        ),
        action(
            "control:physics-reconstruction-profile-fixtures",
            "Check the declarative physics reconstruction graph and reject unsupported execution through MCP and Lunar.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py("tests/mcp/run_physics_reconstruction_profile_tests.py"),
            required_paths=("tests/mcp/run_physics_reconstruction_profile_tests.py",),
            timeout_seconds=120,
            notes="Requires LUNAR_PLATFORM_ROOT and an explicit WORKFLOW_CONTRACT_PATH; does not run a scientific workflow.",
        ),
        action(
            "hub:audit",
            "Audit repository Python entrypoints against the hub, test matrix, and skill-hook contract.",
            family="control",
            kind="audit",
            safety="read_only",
            command=py("scripts/mathformer.py", "audit", "--json"),
            required_paths=(
                "scripts/mathformer.py",
                "skills/SKILL_HOOKS.yaml",
                "tests/test_program/run_comprehensive_tests.py",
            ),
        ),
        action(
            "repo:status",
            "Show concise git status for tracked and untracked files.",
            family="control",
            kind="inspection",
            safety="read_only",
            command=("git", "status", "--short"),
            required_tools=("git",),
        ),
        action(
            "repo:diff-check",
            "Run Git whitespace and conflict-marker checks on the current diff.",
            family="control",
            kind="validation",
            safety="read_only",
            command=("git", "diff", "--check"),
            required_tools=("git",),
        ),
        action(
            "control:thematic-layout",
            "Validate physical backend, library, skill, script, test, and documentation organization.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py("scripts/organize_repository_layout.py", "--json"),
            required_paths=(
                "scripts/organize_repository_layout.py",
                "skills/README.md",
                "scripts/README.md",
                "tests/README.md",
                "docs/README.md",
            ),
        ),
        action(
            "adoption:validate",
            "Validate the bounded portable capability contracts.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/workflow-contract-validator/scripts/portable_adoption.py",
                "validate",
            ),
            required_paths=(
                "skills/control/workflow-contract-validator/references/portable-adoption.json",
                "skills/control/workflow-contract-validator/references/portable-adoption.schema.json",
            ),
        ),
        action(
            "adoption:describe",
            "Resolve a portable operation identity or alias without invoking it.",
            family="control",
            kind="inspection",
            safety="read_only",
            command=py(
                "skills/control/workflow-contract-validator/scripts/portable_adoption.py",
                "describe",
            ),
            allows_extra_args=True,
        ),
        action(
            "adoption:invoke",
            "Invoke one existing pilot operation with optional public-result provenance.",
            family="control",
            kind="execution",
            safety="writes_artifacts",
            command=py(
                "skills/control/workflow-contract-validator/scripts/portable_adoption.py",
                "invoke",
            ),
            allows_extra_args=True,
            writes=("artifacts/adoption/",),
        ),
        action(
            "adoption:catalog",
            "Generate the pilot catalog from canonical authored metadata.",
            family="control",
            kind="render",
            safety="writes_repo",
            command=py(
                "skills/control/workflow-contract-validator/scripts/portable_adoption.py",
                "catalog",
            ),
            writes=("docs/migrations/portable-repository-adoption/catalog.md",),
        ),
        action(
            "adoption:catalog-check",
            "Reject drift in the generated portable pilot catalog.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/workflow-contract-validator/scripts/portable_adoption.py",
                "catalog",
                "--check",
            ),
        ),
        action(
            "adoption:receipt-validate",
            "Validate immutable invocation, result and reasoning joins offline.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/reasoning-log-schema-guardian/scripts/adoption_provenance.py",
                "validate",
            ),
            allows_extra_args=True,
        ),
        action(
            "adoption:receipt-render",
            "Render an existing invocation receipt without execution.",
            family="control",
            kind="render",
            safety="read_only",
            command=py(
                "skills/control/reasoning-log-schema-guardian/scripts/adoption_provenance.py",
                "render",
            ),
            allows_extra_args=True,
        ),
        action(
            "adoption:test-contracts",
            "Run portable identity, adapter and PRISM boundary compatibility tests.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py("tests/control/test_portable_adoption.py"),
        ),
        action(
            "adoption:test-provenance",
            "Run immutable provenance, failure and concurrency compatibility tests.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py("tests/control/test_adoption_provenance.py"),
        ),
        action(
            "adoption:check",
            "Validate portable contracts, generated discovery and compatibility tests.",
            family="control",
            kind="sequence",
            safety="read_only",
            depends_on=(
                "adoption:validate",
                "adoption:catalog-check",
                "adoption:test-contracts",
                "adoption:test-provenance",
            ),
        ),
        action(
            "control:workflow-contract",
            "Validate the skill-hook workflow contract in strict mode.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/workflow-contract-validator/scripts/validate_skill_hooks.py",
                "--strict",
                "--json",
            ),
            required_paths=("skills/SKILL_HOOKS.yaml",),
        ),
        action(
            "control:normalized-workflows",
            "Validate source coverage and typed workflow-skill/v1 descriptors without executing workflows.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
                "--check",
                "--json",
            ),
            required_paths=(
                "skills/control/workflow-contract-validator/references/normalized-workflows/catalog.json",
            ),
        ),
        action(
            "control:normalize-workflows",
            "Regenerate source-linked workflow-skill/v1 descriptions without running scientific workflows.",
            family="control",
            kind="generation",
            safety="writes_repo",
            command=py(
                "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
                "--write",
                "--json",
            ),
            writes=(
                "skills/control/workflow-contract-validator/references/normalized-workflows/",
            ),
        ),
        action(
            "control:normalized-workflows-tests",
            "Test normalized workflow coverage, source fidelity boundaries and adversarial descriptor failures.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py("tests/control/test_normalized_workflows.py"),
        ),
        action(
            "control:reasoning-flow-language",
            "Validate Mathformer ERFL reasoning programs, resource edges, relational coherence, and taxonomy alignment.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/reasoning-flow-language/scripts/validate_reasoning_flow.py",
                "examples/reasoning_flows",
                "--strict",
                "--check-registries",
                "--json",
            ),
            required_paths=(
                "skills/control/reasoning-flow-language/references/erfl-0.3.json",
                "skills/REASONING_TYPES.yaml",
                "skills/OUTPUT_TYPES.yaml",
                "examples/reasoning_flows",
            ),
        ),
        action(
            "control:reasoning-flow-catalog",
            "Check that the generated semantic-flow catalogue and materialization cross-reference match every canonical profile and workflow registry.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/reasoning-flow-language/scripts/render_all_reasoning_flows.py",
                "--check",
                "--json",
            ),
            required_paths=(
                "skills/control/reasoning-flow-language/scripts/render_all_reasoning_flows.py",
                "skills/control/reasoning-flow-language/references/erfl-0.3.json",
                "skills/REASONING_TYPES.yaml",
                "skills/SKILL_HOOKS.yaml",
                "scripts/mathformer.py",
                "examples/reasoning_flows",
                "docs/architecture/ALL_REASONING_FLOWS.md",
                "docs/architecture/REASONING_FLOW_MATERIALIZATIONS.md",
            ),
        ),
        action(
            "control:skill-coverage",
            "Audit that non-wrapper skills are reachable from hooks or direct routes.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/skill-hook-coverage-maximizer/scripts/audit_skill_hook_coverage.py",
                "--expect-ok",
                "--json",
            ),
            required_paths=("skills/SKILL_HOOKS.yaml",),
        ),
        action(
            "control:reasoning-log-coverage",
            "Audit that every skill has a reasoning-log coverage path.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/reasoning-log-schema-guardian/scripts/audit_skill_reasoning_log_coverage.py",
                "--strict",
                "--json",
            ),
            required_paths=(
                "skills/SKILL_HOOKS.yaml",
                "skills/control/reasoning-log-schema-guardian/scripts/run_with_reasoning_log.py",
            ),
        ),
        action(
            "control:reasoning-log-smoke",
            "Run the deterministic reasoning-log contract smoke test.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/reasoning-log-schema-guardian/scripts/self_test_reasoning_logs.py",
                "--json",
            ),
            required_paths=(
                "skills/SKILL_HOOKS.yaml",
                "skills/control/reasoning-log-schema-guardian/scripts/reasoning_log.py",
                "skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log.py",
                "skills/control/reasoning-log-schema-guardian/scripts/render_reasoning_log_html.py",
            ),
        ),
        action(
            "control:reasoning-log-html",
            "Render a reasoning-log JSONL file as a self-contained HTML dashboard.",
            family="control",
            kind="render",
            safety="writes_artifacts",
            command=py(
                "skills/control/reasoning-log-schema-guardian/scripts/render_reasoning_log_html.py"
            ),
            required_paths=(
                "skills/control/reasoning-log-schema-guardian/scripts/render_reasoning_log_html.py",
                "skills/control/reasoning-log-schema-guardian/scripts/render_reasoning_log.py",
                "skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log.py",
            ),
            writes=("artifacts/",),
            allows_extra_args=True,
            notes="Pass renderer flags after `--`, for example `-- --log-file artifacts/wiki_level_suite/reasoning.jsonl --output-file artifacts/wiki_level_suite/reasoning.html`.",
        ),
        action(
            "control:reasoning-log-quality",
            "Audit reasoning logs against the consumer-grade quality profile.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/reasoning-log-schema-guardian/scripts/audit_reasoning_log_quality.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/control/reasoning-log-schema-guardian/scripts/audit_reasoning_log_quality.py",
                "skills/control/reasoning-log-schema-guardian/references/schema.md",
            ),
        ),
        action(
            "control:reasoning-log-summary",
            "Summarize a reasoning log as compact machine-readable JSON for consumer applications.",
            family="control",
            kind="inspection",
            safety="read_only",
            command=py(
                "skills/control/reasoning-log-schema-guardian/scripts/summarize_reasoning_log.py",
                "--json",
            ),
            required_paths=(
                "skills/control/reasoning-log-schema-guardian/scripts/summarize_reasoning_log.py",
            ),
            allows_extra_args=True,
            notes="Pass `-- --log-file PATH` to summarize a specific reasoning log.",
        ),
        action(
            "control:reasoning-log-index",
            "Build the stable reasoning-log index and per-log machine summaries under artifacts/reasoning/.",
            family="control",
            kind="render",
            safety="writes_artifacts",
            command=py(
                "skills/control/reasoning-log-schema-guardian/scripts/index_reasoning_logs.py",
                "--ensure-fixtures",
                "--log-file",
                "artifacts/reasoning/self_test/good.jsonl",
                "--json",
            ),
            required_paths=(
                "skills/control/reasoning-log-schema-guardian/scripts/index_reasoning_logs.py",
                "skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log_index.py",
            ),
            writes=("artifacts/reasoning/",),
        ),
        action(
            "control:reasoning-log-index-validate",
            "Validate the stable reasoning-log index schema and artifact references.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log_index.py",
                "--json",
            ),
            required_paths=(
                "skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log_index.py",
            ),
        ),
        action(
            "control:reasoning-log-consumer-contract",
            "Run consumer-application fixtures over reasoning-log summaries.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py("tests/reasoning_logs/run_consumer_contract_suite.py", "--json"),
            required_paths=("tests/reasoning_logs/run_consumer_contract_suite.py",),
        ),
        action(
            "control:reasoning-log-consumer-readiness",
            "Run the reasoning-log consumer readiness gates.",
            family="control",
            kind="sequence",
            safety="writes_artifacts",
            depends_on=(
                "control:reasoning-log-smoke",
                "control:reasoning-log-coverage",
                "control:reasoning-log-quality",
                "control:reasoning-log-consumer-contract",
                "control:reasoning-log-index",
                "control:reasoning-log-index-validate",
            ),
            writes=("artifacts/reasoning/",),
        ),
        action(
            "control:all",
            "Run the repository-control gates managed by the hub.",
            family="control",
            kind="sequence",
            safety="read_only",
            depends_on=(
                "hub:audit",
                "control:thematic-layout",
                "control:workflow-contract",
                "control:reasoning-flow-language",
                "control:reasoning-flow-catalog",
                "control:skill-coverage",
                "control:reasoning-log-coverage",
                "control:reasoning-log-smoke",
                "repo:diff-check",
            ),
        ),
        action(
            "control:workflow-router-coverage",
            "Audit natural-language router coverage across every registered workflow family.",
            family="control",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py",
                "--audit-coverage",
                "--json",
            ),
            required_paths=(
                "scripts/mathformer.py",
                "skills/control/mathformer-workflow-router/SKILL.md",
                "skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py",
            ),
        ),
        action(
            "meta-skills:registry-validate",
            "Validate Looper-style visible meta-skill task registries against hub actions and skill paths.",
            family="meta_skills",
            kind="validation",
            safety="writes_artifacts",
            command=py("meta_skills/scripts/validate_task_registries.py", "--json"),
            required_paths=(
                "meta_skills/schemas/task_registry.schema.json",
                "meta_skills/scripts/validate_task_registries.py",
            ),
            writes=("artifacts/meta_skills/task_registry_validation.json",),
        ),
        action(
            "meta-skills:quality-cards",
            "Validate meta-skill quality cards for deterministic and generative boundaries.",
            family="meta_skills",
            kind="validation",
            safety="writes_artifacts",
            command=py("meta_skills/scripts/validate_skill_quality_cards.py", "--json"),
            required_paths=(
                "meta_skills/schemas/skill_quality_card.schema.json",
                "meta_skills/scripts/validate_skill_quality_cards.py",
            ),
            writes=("artifacts/meta_skills/skill_quality_card_validation.json",),
        ),
        action(
            "meta-skills:runtime-trace",
            "Record and validate the MathformerPhysicsLib coherence runtime skill-application trace.",
            family="meta_skills",
            kind="validation",
            safety="writes_artifacts",
            depends_on=(
                "meta-skills:runtime-trace-record",
                "meta-skills:runtime-trace-validate",
            ),
            writes=("artifacts/meta_skills/runtime/",),
        ),
        action(
            "meta-skills:runtime-trace-record",
            "Record an observational runtime skill-application trace for MathformerPhysicsLib coherence.",
            family="meta_skills",
            kind="generation",
            safety="writes_artifacts",
            command=py("meta_skills/scripts/record_skill_application.py", "--json"),
            required_paths=("meta_skills/scripts/record_skill_application.py",),
            writes=("artifacts/meta_skills/runtime/",),
        ),
        action(
            "meta-skills:runtime-trace-validate",
            "Validate runtime skill-application trace JSONL artifacts.",
            family="meta_skills",
            kind="validation",
            safety="writes_artifacts",
            command=py("meta_skills/scripts/validate_runtime_traces.py", "--json"),
            required_paths=(
                "meta_skills/schemas/runtime_skill_application.schema.json",
                "meta_skills/scripts/validate_runtime_traces.py",
            ),
            writes=("artifacts/meta_skills/runtime_trace_validation.json",),
        ),
        action(
            "meta-skills:workflow-evolution",
            "Validate workflow evolution graph artifacts for recursive repair workflows.",
            family="meta_skills",
            kind="validation",
            safety="writes_artifacts",
            command=py("meta_skills/scripts/validate_workflow_evolution.py", "--json"),
            required_paths=(
                "meta_skills/schemas/workflow_evolution.schema.json",
                "meta_skills/scripts/validate_workflow_evolution.py",
            ),
            writes=("artifacts/meta_skills/workflow_evolution_validation.json",),
        ),
        action(
            "meta-skills:skill-projections",
            "Build taxonomy projection cards for skills used by visible meta-skill workflows.",
            family="meta_skills",
            kind="generation",
            safety="writes_artifacts",
            command=py("meta_skills/scripts/build_skill_projections.py", "--json"),
            required_paths=(
                "meta_skills/taxonomy/workflow_taxonomy.json",
                "meta_skills/scripts/build_skill_projections.py",
            ),
            writes=(
                "meta_skills/taxonomy/skill_projection_cards.json",
                "artifacts/meta_skills/skill_projection_report.json",
            ),
        ),
        action(
            "meta-skills:taxonomic-navigation",
            "Run the taxonomy-first workflow navigation self-test.",
            family="meta_skills",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "meta_skills/scripts/navigate_workflow_taxonomy.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "meta_skills/taxonomy/workflow_taxonomy.json",
                "meta_skills/scripts/navigate_workflow_taxonomy.py",
            ),
            writes=("artifacts/meta_skills/taxonomic_navigation_report.json",),
        ),
        action(
            "meta-skills:generated-lifecycle",
            "Validate generated skill lifecycle records and promotion gates.",
            family="meta_skills",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "meta_skills/scripts/validate_generated_skill_lifecycle.py", "--json"
            ),
            required_paths=(
                "meta_skills/schemas/generated_skill_lifecycle.schema.json",
                "meta_skills/scripts/validate_generated_skill_lifecycle.py",
            ),
            writes=("artifacts/meta_skills/generated_skill_lifecycle_validation.json",),
        ),
        action(
            "meta-skills:mcp-boundary",
            "Validate that meta-skills expose workflow-level MCP actions and central config boundaries.",
            family="meta_skills",
            kind="validation",
            safety="writes_artifacts",
            command=py("meta_skills/scripts/validate_mcp_boundary.py", "--json"),
            required_paths=(
                "meta_skills/registry/workflow_actions.yaml",
                "meta_skills/scripts/validate_mcp_boundary.py",
                "scripts/mcp_server.py",
            ),
            writes=("artifacts/mcp/meta_skill_service_self_test.json",),
        ),
        action(
            "meta-skills:validate",
            "Run the compact meta-skill validation suite.",
            family="meta_skills",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/meta_skills/run_meta_skill_suite.py", "--json"),
            required_paths=(
                "tests/meta_skills/run_meta_skill_suite.py",
                "meta_skills/",
            ),
            writes=(
                "artifacts/meta_skills/",
                "artifacts/mcp/meta_skill_service_self_test.json",
            ),
        ),
        action(
            "mathlib:index-build",
            "Build the version-stamped Mathlib module, declaration, import, and declaration-graph index.",
            family="mathlib",
            kind="generation",
            safety="writes_artifacts",
            command=py(
                "skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py",
                "--json",
            ),
            required_paths=(
                "skills/mathlib/mathlib-index-builder/SKILL.md",
                "skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py",
                "skills/mathlib/mathlib-index-builder/scripts/mathlib_index_common.py",
                ".lake/packages/mathlib/Mathlib",
            ),
            writes=("artifacts/mathlib_index/index.json",),
            timeout_seconds=300,
        ),
        action(
            "mathlib:index-validate",
            "Validate that the existing Mathlib index matches the current Lean and mathlib revision stamp.",
            family="mathlib",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py",
                "--validate-existing",
                "--json",
            ),
            required_paths=(
                "skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py",
                "artifacts/mathlib_index/index.json",
            ),
        ),
        action(
            "mathlib:term-annotations",
            "Run ontology-backed Mathlib term expansion, domain disambiguation, proof-role tagging, and gap-ledger self-tests.",
            family="mathlib",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/mathlib/mathlib-term-expansion-annotator/scripts/annotate_mathlib_terms.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/mathlib/mathlib-term-expansion-annotator/SKILL.md",
                "skills/mathlib/mathlib-term-expansion-annotator/scripts/annotate_mathlib_terms.py",
                "skills/mathlib/mathlib-concept-ontology-manager/references/core.yaml",
            ),
            writes=("artifacts/mathlib_index/term_annotation_self_test.json",),
        ),
        action(
            "mathlib:navigation-state",
            "Plan bounded Mathlib navigation states with declaration-neighborhood, theorem-shape, import-cost, and gap-ledger evidence.",
            family="mathlib",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/mathlib/mathlib-navigation-state-planner/scripts/plan_mathlib_navigation_state.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/mathlib/mathlib-navigation-state-planner/SKILL.md",
                "skills/mathlib/mathlib-navigation-state-planner/scripts/plan_mathlib_navigation_state.py",
                "skills/mathlib/mathlib-index-builder/scripts/mathlib_index_common.py",
                "skills/mathlib/mathlib-term-expansion-annotator/scripts/annotate_mathlib_terms.py",
            ),
            writes=(
                "artifacts/mathlib_index/navigation_state.json",
                "artifacts/mathlib_index/gap_ledger.json",
                "artifacts/mathlib_index/navigation_state_self_test.json",
                "artifacts/mathlib_index/monotonic_refinement_report.json",
            ),
        ),
        action(
            "mathlib:indexing-control-suite",
            "Run the controlled Mathlib indexing, annotation, navigation, gap-ledger, and monotonicity regression suite.",
            family="mathlib",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/mathlib/run_indexing_control_suite.py", "--json"),
            required_paths=(
                "tests/mathlib/run_indexing_control_suite.py",
                "skills/mathlib/mathlib-index-builder/scripts/build_mathlib_index.py",
                "skills/mathlib/mathlib-term-expansion-annotator/scripts/annotate_mathlib_terms.py",
                "skills/mathlib/mathlib-navigation-state-planner/scripts/plan_mathlib_navigation_state.py",
            ),
            writes=("artifacts/mathlib_index/",),
            timeout_seconds=480,
        ),
        action(
            "setup:all",
            "Install all Python extras and the Lean-facing environment.",
            family="setup",
            kind="setup",
            safety="writes_environment",
            command=uv_py("scripts/install_env.py", "--all-extras", "--with-lean"),
            required_paths=("scripts/install_env.py",),
            required_tools=("uv",),
            writes=(".venv/", ".lake/"),
        ),
        action(
            "setup:atp-kb",
            "Install the smaller ATP and premise-KB profile.",
            family="setup",
            kind="setup",
            safety="writes_environment",
            command=uv_py("scripts/install_env.py", "--with-atp-kb"),
            required_paths=("scripts/install_env.py",),
            required_tools=("uv",),
            writes=(".venv/",),
        ),
        action(
            "setup:lean",
            "Install or update the Lean-facing environment profile.",
            family="setup",
            kind="setup",
            safety="writes_environment",
            command=py("scripts/install_env.py", "--skip-python", "--with-lean"),
            required_paths=("scripts/install_env.py",),
            writes=(".lake/",),
        ),
        action(
            "setup:sympy",
            "Install the SymPy and physics Python extras.",
            family="setup",
            kind="setup",
            safety="writes_environment",
            command=uv_py("scripts/install_env.py", "--with-sympy"),
            required_paths=("scripts/install_env.py",),
            required_tools=("uv",),
            writes=(".venv/",),
        ),
        action(
            "setup:python-all",
            "Install all known Python extras without running the Lean step.",
            family="setup",
            kind="setup",
            safety="writes_environment",
            command=uv_py("scripts/install_env.py", "--all-extras"),
            required_paths=("scripts/install_env.py",),
            required_tools=("uv",),
            writes=(".venv/",),
        ),
        action(
            "skills:link",
            "Publish repository skills to supported local agent-client folders.",
            family="skills",
            kind="setup",
            safety="writes_environment",
            command=py(
                "scripts/link_agent_skills.py",
                "--profile",
                "all-repo",
                "--mode",
                "auto",
                "--replace",
            ),
            required_paths=("scripts/link_agent_skills.py", "skills/"),
            writes=(".agents/skills/", ".claude/skills/", ".opencode/skills/"),
        ),
        action(
            "skills:plugin-sync",
            "Regenerate Codex and Claude plugin entrypoints from canonical skills.",
            family="skills",
            kind="setup",
            safety="writes_environment",
            command=py("scripts/sync_agent_plugins.py"),
            required_paths=("scripts/sync_agent_plugins.py", "skills/"),
            writes=("plugins/mathformer/", ".agents/plugins/", ".claude-plugin/"),
        ),
        action(
            "skills:plugin-check",
            "Check Codex and Claude plugin discovery, metadata and source parity.",
            family="skills",
            kind="validation",
            safety="read_only",
            command=py("scripts/sync_agent_plugins.py", "--check"),
            required_paths=("scripts/sync_agent_plugins.py", "skills/"),
        ),
        action(
            "skills:plugin-test",
            "Test plugin generation, drift detection and cached installation layout.",
            family="skills",
            kind="validation",
            safety="read_only",
            command=py("tests/agent_clients/test_agent_plugins.py"),
            required_paths=("tests/agent_clients/test_agent_plugins.py",),
        ),
        action(
            "skills:client-discovery",
            "Verify Codex, Claude Code, and OpenCode can discover the same repository skills.",
            family="skills",
            kind="validation",
            safety="read_only",
            command=py("tests/agent_clients/run_skill_client_discovery.py", "--json"),
            required_paths=(
                "tests/agent_clients/run_skill_client_discovery.py",
                "skills/",
            ),
        ),
        action(
            "agentc:analyze-logs",
            "Analyze an AgentC workflow report; pass --report-file and outputs after `--`.",
            family="agentc",
            kind="utility",
            safety="writes_artifacts",
            command=py(
                "skills/autoformalization/autoformalization-agentc/scripts/analyze_logs.py"
            ),
            required_paths=(
                "skills/autoformalization/autoformalization-agentc/scripts/analyze_logs.py",
            ),
            writes=("artifacts/",),
            allows_extra_args=True,
        ),
        action(
            "test:quick",
            "Run the quick repository smoke suite.",
            family="test",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/run_quick.py", "--json"),
            required_paths=("tests/run_quick.py",),
            writes=("artifacts/",),
        ),
        action(
            "test:docs",
            "Validate documentation links and expected documentation surfaces.",
            family="docs",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/run_docs.py", "--json"),
            required_paths=("tests/run_docs.py",),
            writes=("artifacts/",),
        ),
        action(
            "test:slow",
            "Run the slower repository validation suite.",
            family="test",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/run_slow.py", "--json"),
            required_paths=("tests/run_slow.py",),
            writes=("artifacts/",),
            timeout_seconds=900,
        ),
        action(
            "test:generative",
            "Run generative quality probes.",
            family="generative",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/run_generative.py", "--json"),
            required_paths=("tests/run_generative.py",),
            writes=("artifacts/",),
            timeout_seconds=900,
        ),
        action(
            "test:comprehensive",
            "Run the complete comprehensive test matrix.",
            family="test",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "tests/test_program/run_comprehensive_tests.py",
                "--module-family",
                "all",
                "--write-jsonl",
                "--write-junit",
                "--json",
            ),
            required_paths=(
                "tests/test_program/run_comprehensive_tests.py",
                "tests/test_matrix.json",
            ),
            writes=("artifacts/",),
            timeout_seconds=3600,
        ),
        action(
            "test:comprehensive-strict",
            "Run the comprehensive matrix and fail on skipped or unavailable selected capabilities.",
            family="test",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "tests/test_program/run_comprehensive_tests.py",
                "--module-family",
                "all",
                "--profile",
                "strict",
                "--write-jsonl",
                "--write-junit",
                "--json",
            ),
            required_paths=(
                "tests/test_program/run_comprehensive_tests.py",
                "tests/test_matrix.json",
            ),
            writes=("artifacts/",),
            timeout_seconds=3600,
        ),
        action(
            "review:autoformalization-framework",
            "Run the controlled cross-cutting autoformalization framework and physics release review.",
            family="quality",
            kind="sequence",
            safety="writes_artifacts",
            depends_on=(
                "control:all",
                "test:docs",
                "mathformerphysicslib:release-gate",
            ),
            writes=("artifacts/physics_lean/release_gate/", ".lake/"),
        ),
        action(
            "test:backend",
            "Run a backend test through the generic backend runner; pass backend arguments after `--`.",
            family="test",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/run_backend.py"),
            required_paths=("tests/run_backend.py",),
            writes=("artifacts/",),
            allows_extra_args=True,
        ),
        action(
            "lean:build",
            "Build the Lean project with Lake.",
            family="lean",
            kind="validation",
            safety="writes_build_cache",
            command=("lake", "build"),
            required_paths=("lakefile.toml", "lean-toolchain"),
            required_tools=("lake",),
            writes=(".lake/",),
            timeout_seconds=1200,
        ),
        action(
            "formalphysics:original-two-lean",
            "Regenerate the original two FormalPhysics Lean artifacts.",
            family="physics_lean",
            kind="generation",
            safety="writes_repo",
            command=py("scripts/generate_formalphysics_original_two_lean.py"),
            required_paths=("scripts/generate_formalphysics_original_two_lean.py",),
            writes=("libraries/MathformerPhysicsLib/Lean/",),
        ),
        action(
            "formalphysics:original-two-isabelle",
            "Regenerate the original two FormalPhysics Isabelle artifacts.",
            family="physics_isabelle",
            kind="generation",
            safety="writes_repo",
            command=py("scripts/generate_formalphysics_original_two_isabelle.py"),
            required_paths=("scripts/generate_formalphysics_original_two_isabelle.py",),
            writes=("libraries/MathformerPhysicsLib/backends/isabelle/Isabelle/",),
        ),
        action(
            "formalphysics:original-two-sympy",
            "Regenerate the original two FormalPhysics SymPy artifacts.",
            family="physics_sympy",
            kind="generation",
            safety="writes_repo",
            command=py(
                "scripts/generate_formalphysics_original_two_sympy.py", "--json"
            ),
            required_paths=("scripts/generate_formalphysics_original_two_sympy.py",),
            writes=(
                "libraries/MathformerPhysicsLib/SymPy/",
                "backends/sympy/MathformerSympyPhysics/",
            ),
        ),
        action(
            "formalphysics:extra-lean",
            "Regenerate the extended FormalPhysics Lean artifact set.",
            family="physics_lean",
            kind="generation",
            safety="writes_repo",
            command=py("scripts/generate_formalphysics_extra_lean.py"),
            required_paths=("scripts/generate_formalphysics_extra_lean.py",),
            writes=("libraries/MathformerPhysicsLib/Lean/",),
        ),
        action(
            "formalphysics:extra-isabelle",
            "Regenerate the extended FormalPhysics Isabelle artifact set.",
            family="physics_isabelle",
            kind="generation",
            safety="writes_repo",
            command=py("scripts/generate_formalphysics_extra_isabelle.py"),
            required_paths=("scripts/generate_formalphysics_extra_isabelle.py",),
            writes=("libraries/MathformerPhysicsLib/backends/isabelle/Isabelle/",),
        ),
        action(
            "formalphysics:extra-sympy",
            "Regenerate the extended FormalPhysics SymPy artifact set.",
            family="physics_sympy",
            kind="generation",
            safety="writes_repo",
            command=py("scripts/generate_formalphysics_extra_sympy.py", "--json"),
            required_paths=("scripts/generate_formalphysics_extra_sympy.py",),
            writes=(
                "libraries/MathformerPhysicsLib/SymPy/",
                "backends/sympy/MathformerSympyPhysics/",
            ),
        ),
        action(
            "formalphysics:top10-sympy",
            "Regenerate the top-10 FormalPhysics SymPy artifacts.",
            family="physics_sympy",
            kind="generation",
            safety="writes_repo",
            command=py("scripts/generate_formalphysics_top10_sympy.py"),
            required_paths=("scripts/generate_formalphysics_top10_sympy.py",),
            writes=(
                "libraries/MathformerPhysicsLib/SymPy/",
                "backends/sympy/MathformerSympyPhysics/",
            ),
        ),
        action(
            "formalphysics:refresh-extra-lean-reports",
            "Refresh consistency reports for extended FormalPhysics Lean artifacts.",
            family="physics_lean",
            kind="generation",
            safety="writes_repo",
            command=py("scripts/refresh_formalphysics_extra_lean_reports.py"),
            required_paths=("scripts/refresh_formalphysics_extra_lean_reports.py",),
            writes=("libraries/MathformerPhysicsLib/Lean/",),
        ),
        action(
            "physics-lean:audit-grounding",
            "Audit MathformerPhysics Lean grounding metadata.",
            family="physics_lean",
            kind="validation",
            safety="read_only",
            command=py("scripts/audit_mathformer_physics_lean_grounding.py"),
            required_paths=("scripts/audit_mathformer_physics_lean_grounding.py",),
        ),
        action(
            "physics-lean:update-grounding-audit",
            "Update MathformerPhysics Lean grounding audit artifacts.",
            family="physics_lean",
            kind="generation",
            safety="writes_repo",
            command=py(
                "scripts/audit_mathformer_physics_lean_grounding.py",
                "--update-consistency",
            ),
            required_paths=("scripts/audit_mathformer_physics_lean_grounding.py",),
            writes=("libraries/MathformerPhysicsLib/",),
        ),
        action(
            "physics-lean:drift-pathology-monitor",
            "Monitor a Lean physics artifact for FormalScience semantic-drift pathologies; pass source, Lean, and report arguments after `--`.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/physics-lean/physics-lean-drift-pathology-monitor/scripts/monitor_physics_lean_drift_pathologies.py"
            ),
            required_paths=(
                "skills/physics-lean/physics-lean-drift-pathology-monitor/scripts/monitor_physics_lean_drift_pathologies.py",
            ),
            writes=("artifacts/",),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:detect-pathology-objects",
            "Detect physics mathematical objects behind Lean physics pathology findings; pass report paths after `--`.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/physics-common/physics-math-object-detector/scripts/detect_physics_math_objects.py"
            ),
            required_paths=(
                "skills/physics-common/physics-math-object-detector/scripts/detect_physics_math_objects.py",
            ),
            writes=("artifacts/",),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:object-workbench",
            "Plan MathformerPhysicsLib-first work over detected physics objects; pass object packet arguments after `--`.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-object-workbench/scripts/build_mathformerphysicslib_object_workbench.py"
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-object-workbench/scripts/build_mathformerphysicslib_object_workbench.py",
            ),
            writes=("artifacts/",),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:pathology-repair-loop",
            "Orchestrate the library-first Lean physics pathology repair loop; pass monitor, object, workbench, and repair plans after `--`.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/physics-lean/physics-lean-pathology-repair-orchestrator/scripts/orchestrate_pathology_repair.py"
            ),
            required_paths=(
                "skills/physics-lean/physics-lean-pathology-repair-orchestrator/scripts/orchestrate_pathology_repair.py",
            ),
            writes=("artifacts/",),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:generative-repair-plan",
            "Build guarded Codex-exec generative repair prompts for Lean physics pathologies; pass deterministic repair packets after `--`.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/physics-lean/physics-lean-generative-repair-orchestrator/scripts/build_physics_lean_generative_repair_plan.py"
            ),
            required_paths=(
                "skills/physics-lean/physics-lean-generative-repair-orchestrator/scripts/build_physics_lean_generative_repair_plan.py",
            ),
            writes=("artifacts/",),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:repair-expansion-map",
            "Map the exhaustive recursive Lean physics pathology repair expansion; pass repair-loop and repair packet arguments after `--`.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/physics-lean/physics-lean-repair-expansion-cartographer/scripts/map_repair_expansion.py"
            ),
            required_paths=(
                "skills/physics-lean/physics-lean-repair-expansion-cartographer/scripts/map_repair_expansion.py",
            ),
            writes=("artifacts/",),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:recursive-repair-control",
            "Control recursive Lean physics pathology repair iterations from an expansion map; pass expansion-map arguments after `--`.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/physics-lean/physics-lean-recursive-repair-loop-controller/scripts/control_recursive_repair_loop.py"
            ),
            required_paths=(
                "skills/physics-lean/physics-lean-recursive-repair-loop-controller/scripts/control_recursive_repair_loop.py",
            ),
            writes=("artifacts/",),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:foundation-intake",
            "Normalize physics concepts or detected objects into a MathformerPhysicsLib foundations object packet.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/physics-common/physics-foundation-object-intake/scripts/intake_physics_foundation_objects.py"
            ),
            required_paths=(
                "skills/physics-common/physics-foundation-object-intake/scripts/intake_physics_foundation_objects.py",
            ),
            writes=("artifacts/mathformerphysicslib/foundations/",),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:foundation-surface-design",
            "Design Mathlib-first MathformerPhysicsLib foundation surfaces from an object packet.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-foundation-surface-designer/scripts/design_foundation_surfaces.py"
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-foundation-surface-designer/scripts/design_foundation_surfaces.py",
            ),
            writes=("artifacts/mathformerphysicslib/foundations/",),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:foundation-draft",
            "Draft or preview MathformerPhysicsLib Lean foundation modules from a surface plan.",
            family="physics_lean",
            kind="generation",
            safety="writes_repo",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-foundation-drafter/scripts/draft_foundation_modules.py"
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-foundation-drafter/scripts/draft_foundation_modules.py",
            ),
            writes=(
                "libraries/MathformerPhysicsLib/Lean/Foundations/",
                "libraries/MathformerPhysicsLib/Lean/Foundations.lean",
            ),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:foundation-verify",
            "Verify MathformerPhysicsLib Lean foundation modules for structural promotion readiness.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-foundation-verifier/scripts/verify_foundation_modules.py",
                "--json",
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-foundation-verifier/scripts/verify_foundation_modules.py",
            ),
            writes=("artifacts/mathformerphysicslib/foundations/",),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:foundation-formalization-loop",
            "Run the controlled MathformerPhysicsLib foundations workflow over the priority-1 object backlog.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/physics_lean/run_foundations_workflow.py", "--json"),
            required_paths=(
                "tests/physics_lean/run_foundations_workflow.py",
                "docs/libraries/MATHFORMERPHYSICSLIB_FOUNDATIONS_WORKFLOW.md",
            ),
            writes=("artifacts/mathformerphysicslib/foundations/",),
        ),
        action(
            "physics-lean:dirac-recursive-formalphysics",
            "Generate five recursively grounded Dirac-notation FormalPhysics Lean examples.",
            family="physics_lean",
            kind="generation",
            safety="writes_repo",
            command=py(
                "scripts/physics-lean/generate_formalphysics_dirac_recursive_lean.py",
                "--json",
            ),
            required_paths=(
                "scripts/physics-lean/generate_formalphysics_dirac_recursive_lean.py",
                "data/benchmarks/formal_science/FormalPhysics.json",
                "libraries/MathformerPhysicsLib/Lean/Foundations/HilbertSpace.lean",
            ),
            writes=(
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0014/",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0015/",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0021/",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0052/",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0074/",
                "artifacts/physics_lean/dirac_recursive_batch/",
            ),
        ),
        action(
            "physics-lean:derivation-completeness",
            "Check whether a Lean physics artifact is a complete autoformalization rather than a compiling scaffold.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/physics-lean/physics-lean-derivation-completeness-checker/scripts/check_derivation_completeness.py",
                "--lean-file",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0014/MathformerPhysics.lean",
                "--source-record",
                "artifacts/physics_lean/dirac_recursive_batch/formalphysics_0014/source_record.json",
                "--recursive-plan",
                "artifacts/physics_lean/dirac_recursive_batch/recursive_grounding_plan.json",
                "--output",
                "artifacts/physics_lean/derivation_completeness/formalphysics_0014.json",
                "--json",
            ),
            required_paths=(
                "skills/physics-lean/physics-lean-derivation-completeness-checker/scripts/check_derivation_completeness.py",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0014/MathformerPhysics.lean",
            ),
            writes=("artifacts/physics_lean/derivation_completeness/",),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:derivation-completeness-regression",
            "Run regression fixtures for Lean physics derivation-completeness detection.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "tests/physics_lean/run_derivation_completeness_regression.py", "--json"
            ),
            required_paths=(
                "tests/physics_lean/run_derivation_completeness_regression.py",
                "skills/physics-lean/physics-lean-derivation-completeness-checker/scripts/check_derivation_completeness.py",
                "tests/fixtures/physics_lean_adversarial/",
            ),
            writes=("artifacts/physics_lean/derivation_completeness_regression/",),
        ),
        action(
            "physics-lean:grounded-sample-thoroughness",
            "Run the 0014-anchored grounded-thoroughness gate for selected Lean physics FormalPhysics examples.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "tests/physics_lean/run_grounded_sample_thoroughness.py", "--json"
            ),
            required_paths=(
                "tests/physics_lean/run_grounded_sample_thoroughness.py",
                "skills/physics-lean/physics-lean-derivation-completeness-checker/scripts/check_derivation_completeness.py",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0014/MathformerPhysics.lean",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0015/MathformerPhysics.lean",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0021/MathformerPhysics.lean",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0052/MathformerPhysics.lean",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0074/MathformerPhysics.lean",
            ),
            writes=("artifacts/physics_lean/grounded_sample_thoroughness/",),
            allows_extra_args=True,
        ),
        action(
            "physics-lean:formal-science-grounding-debt",
            "Run the compact FormalScience grounding-debt gate over FormalPhysics Lean outputs.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "tests/physics_lean/run_formal_science_grounding_debt_gate.py", "--json"
            ),
            required_paths=(
                "tests/physics_lean/run_formal_science_grounding_debt_gate.py",
                "skills/physics-lean/physics-lean-drift-pathology-monitor/scripts/monitor_physics_lean_drift_pathologies.py",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0059/MathformerPhysics.lean",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0191/MathformerPhysics.lean",
            ),
            writes=("artifacts/physics_lean/formal_science_grounding_debt/",),
        ),
        action(
            "physics-lean:formalphysics-comparative-report",
            "Build a FormalPhysics comparative HTML/JSON report from external selected-example JSON; pass input/output arguments after `--`.",
            family="physics_lean",
            kind="render",
            safety="writes_artifacts",
            command=py(
                "skills/physics-common/formalphysics-comparative-analysis-reporter/scripts/build_comparative_report.py"
            ),
            required_paths=(
                "skills/physics-common/formalphysics-comparative-analysis-reporter/scripts/build_comparative_report.py",
                "skills/physics-common/formalphysics-comparative-analysis-reporter/scripts/prepare_comparison_inputs.py",
                "libraries/MathformerPhysicsLib/Lean/Foundations.lean",
            ),
            writes=("artifacts/formalphysics_comparative_analysis/",),
            allows_extra_args=True,
            timeout_seconds=900,
            notes="Pass `-- --input-json PATH --output-dir artifacts/formalphysics_comparative_analysis/RUN --json`; add `--execute-lean` to run lake compile checks.",
        ),
        action(
            "physics-lean:formalphysics-comparative-report-self-test",
            "Smoke-test the FormalPhysics comparative report builder.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "tests/physics_lean/run_formalphysics_comparative_report.py", "--json"
            ),
            required_paths=(
                "tests/physics_lean/run_formalphysics_comparative_report.py",
                "skills/physics-common/formalphysics-comparative-analysis-reporter/scripts/build_comparative_report.py",
                "skills/physics-common/formalphysics-comparative-analysis-reporter/scripts/prepare_comparison_inputs.py",
            ),
            writes=("artifacts/formalphysics_comparative_analysis/",),
            timeout_seconds=180,
        ),
        action(
            "physics-lean:formalphysics-judge-synthesis-report",
            "Build a FormalPhysics judge synthesis report from a comparative report JSON; pass input/output arguments after `--`.",
            family="physics_lean",
            kind="render",
            safety="writes_artifacts",
            command=py(
                "skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/build_synthesis_report.py",
                "--comparative-report",
                "artifacts/formalphysics_comparative_analysis/hub_selected_examples_report/comparative_report.json",
                "--output-dir",
                "artifacts/formalphysics_judge_synthesis/hub_selected_examples",
                "--json",
            ),
            required_paths=(
                "skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/build_synthesis_report.py",
                "skills/physics-common/formalphysics-judge-synthesis-reporter/references/synthesis_protocol.md",
            ),
            writes=("artifacts/formalphysics_judge_synthesis/",),
            allows_extra_args=True,
            timeout_seconds=300,
            notes=(
                "Defaults to the hub selected-examples comparative report; override with "
                "`-- --comparative-report artifacts/formalphysics_comparative_analysis/RUN/"
                "comparative_report.json --output-dir artifacts/formalphysics_judge_synthesis/RUN "
                "--codex-results-json path/to/results.json --json` when completed judge results exist."
            ),
        ),
        action(
            "physics-lean:formalphysics-judge-synthesis-report-self-test",
            "Smoke-test the FormalPhysics judge synthesis report builder.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "tests/physics_lean/run_formalphysics_judge_synthesis_report.py",
                "--json",
            ),
            required_paths=(
                "tests/physics_lean/run_formalphysics_judge_synthesis_report.py",
                "skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/build_synthesis_report.py",
                "skills/physics-common/formalphysics-judge-synthesis-reporter/references/synthesis_protocol.md",
            ),
            writes=("artifacts/formalphysics_judge_synthesis/",),
            timeout_seconds=180,
        ),
        action(
            "physics-lean:formalphysics-codex-exec-judge-runner",
            "Prepare or optionally execute selected FormalPhysics Codex-exec judge prompts; pass filters and --execute after `--`.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/run_codex_exec_judges.py",
                "--limit",
                "1",
                "--json",
            ),
            required_paths=(
                "skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/run_codex_exec_judges.py",
                "artifacts/formalphysics_comparative_analysis/hub_selected_examples_report/codex_exec_judge_prompts.json",
            ),
            writes=("artifacts/formalphysics_judge_synthesis/codex_exec_judges/",),
            allows_extra_args=True,
            timeout_seconds=1200,
            notes=(
                "Defaults to a one-prompt dry run. Add filters and `--execute` to run Codex-exec, "
                "use `--resume --workers N` for long runs, then feed the resulting "
                "codex_exec_judge_results.json into the synthesis action."
            ),
        ),
        action(
            "physics-lean:formalphysics-codex-exec-judge-runner-self-test",
            "Smoke-test the FormalPhysics Codex-exec judge runner without invoking Codex.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/run_codex_exec_judges.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/physics-common/formalphysics-judge-synthesis-reporter/scripts/run_codex_exec_judges.py",
            ),
            writes=("artifacts/formalphysics_judge_synthesis/codex_exec_judges/",),
            timeout_seconds=120,
        ),
        action(
            "physics-lean:goal-sample-recursive-0009",
            "Run FormalPhysics 0009 through the one-sample recursive goal autoformalization workflow.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "skills/physics-lean/physics-lean-goal-sample-autoformalizer/scripts/run_recursive_goal_case.py",
                "--source-record",
                "artifacts/physics_lean/new_qm_source_only/formalphysics_0009/source_record.json",
                "--json",
            ),
            required_paths=(
                "skills/physics-lean/physics-lean-goal-sample-autoformalizer/scripts/run_recursive_goal_case.py",
                "artifacts/physics_lean/new_qm_source_only/formalphysics_0009/source_record.json",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0009/MathformerPhysics.lean",
            ),
            writes=("artifacts/physics_lean/recursive_goal_runs/formalphysics_0009/",),
            timeout_seconds=900,
            allows_extra_args=True,
        ),
        action(
            "physics-lean:new-qm-source-only-batch",
            "Run the deprecated source-only QM batch scaffold under an explicit acknowledgement flag.",
            family="physics_lean",
            kind="generation",
            safety="writes_repo",
            command=py(
                "skills/physics-lean/physics-lean-goal-sample-autoformalizer/scripts/run_new_qm_source_only_batch.py",
                "--acknowledge-deprecated-batch-scaffold",
                "--json",
            ),
            required_paths=(
                "skills/physics-lean/physics-lean-goal-sample-autoformalizer/scripts/run_new_qm_source_only_batch.py",
                "data/benchmarks/formal_science/FormalPhysics.json",
            ),
            writes=(
                "libraries/MathformerPhysicsLib/Lean/formalphysics_*/",
                "artifacts/physics_lean/new_qm_source_only/",
            ),
            timeout_seconds=900,
            allows_extra_args=True,
        ),
        action(
            "physics-lean:backend-suite",
            "Run the deterministic Lean physics backend suite with a controlled artifact and adversarial pathology fixtures.",
            family="physics_lean",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "tests/physics_lean/run_lean_physics_backend_suite.py", "--json"
            ),
            required_paths=(
                "tests/physics_lean/run_lean_physics_backend_suite.py",
                "tests/physics_lean/run_grounded_sample_thoroughness.py",
                "tests/fixtures/physics_lean_adversarial/",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0000/MathformerPhysics.lean",
            ),
            writes=("artifacts/physics_lean/backend_suite/",),
        ),
        action(
            "rocq:self-test",
            "Generate and structurally validate the controlled Rocq suite.",
            family="rocq",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "scripts/run_rocq_autoformalization.py", "--self-test", "--json"
            ),
            required_paths=(
                "scripts/run_rocq_autoformalization.py",
                "backends/rocq/MathformerRocq/",
            ),
            writes=("artifacts/rocq_autoformalization/",),
        ),
        action(
            "rocq:wiki-suite",
            "Run the Rocq wiki-level controlled suite.",
            family="rocq",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/rocq/run_wiki_suite.py", "--json"),
            required_paths=("tests/rocq/run_wiki_suite.py",),
            writes=("artifacts/rocq_wiki_level/",),
        ),
        action(
            "rocq:check-generated",
            "Validate generated Rocq files and optionally compile them when Rocq is installed.",
            family="rocq",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py",
                "--path",
                "MathformerRocq",
                "--json",
            ),
            required_paths=(
                "skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py",
                "backends/rocq/MathformerRocq/",
            ),
            optional_tools=("rocq", "coqc"),
        ),
        action(
            "atp:demo",
            "Run the premise-guided Vampire ATP group inverse demonstration.",
            family="atp",
            kind="demo",
            safety="writes_artifacts",
            command=py(
                "scripts/run_vampire_atp.py",
                "--text-file",
                "examples/vampire_group_inverse_product_input.md",
                "--artifact-root",
                "artifacts/vampire_atp/atp_function_demo",
                "--premise-loop",
                "--premise-budget",
                "medium",
                "--time-limit",
                "3",
            ),
            required_paths=(
                "scripts/run_vampire_atp.py",
                "examples/vampire_group_inverse_product_input.md",
            ),
            optional_tools=("vampire",),
            writes=("artifacts/vampire_atp/atp_function_demo/",),
            timeout_seconds=120,
        ),
        action(
            "example:vampire-policy",
            "Run the policy-chain informal-to-Vampire example.",
            family="atp",
            kind="demo",
            safety="writes_artifacts",
            command=py("examples/vampire_informal_to_proofs.py"),
            required_paths=("examples/vampire_informal_to_proofs.py",),
            optional_tools=("vampire",),
            writes=("artifacts/vampire_atp/policy_chain_example/",),
            timeout_seconds=180,
        ),
        action(
            "example:vampire-strict-order",
            "Run the strict-order informal-to-Vampire example.",
            family="atp",
            kind="demo",
            safety="writes_artifacts",
            command=py("examples/vampire_nontrivial_math_to_proofs.py"),
            required_paths=("examples/vampire_nontrivial_math_to_proofs.py",),
            optional_tools=("vampire",),
            writes=("artifacts/vampire_atp/strict_order_asymmetry_example/",),
            timeout_seconds=180,
        ),
        action(
            "example:vampire-group",
            "Run the group inverse informal-to-Vampire example.",
            family="atp",
            kind="demo",
            safety="writes_artifacts",
            command=py("examples/vampire_complex_group_theorem_to_proofs.py"),
            required_paths=("examples/vampire_complex_group_theorem_to_proofs.py",),
            optional_tools=("vampire",),
            writes=("artifacts/vampire_atp/group_inverse_product_example/",),
            timeout_seconds=180,
        ),
        action(
            "kb:e2e",
            "Run the premise-selection knowledge-base end-to-end test.",
            family="kb",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/kb/run_premise_kb_e2e.py", "--json"),
            required_paths=(
                "tests/kb/run_premise_kb_e2e.py",
                "backends/premise_kb/MathformerKB/",
            ),
            writes=("artifacts/kb/",),
        ),
        action(
            "kb:famous-corpus",
            "Generate and validate the famous theorem and axiom corpus.",
            family="kb",
            kind="generation",
            safety="writes_artifacts",
            command=py("tests/kb/run_famous_theorem_corpus.py", "--json"),
            required_paths=("tests/kb/run_famous_theorem_corpus.py",),
            writes=("artifacts/kb/",),
        ),
        action(
            "kb:generate-seeds",
            "Generate a theorem and axiom seed JSONL file; pass options after `--`.",
            family="kb",
            kind="generation",
            safety="writes_artifacts",
            command=py(
                "skills/premise-kb/premise-kb-theorem-seed-generator/scripts/generate_theorem_axiom_seed_list.py"
            ),
            required_paths=(
                "skills/premise-kb/premise-kb-theorem-seed-generator/scripts/generate_theorem_axiom_seed_list.py",
            ),
            writes=("artifacts/kb/",),
            allows_extra_args=True,
        ),
        action(
            "kb:generate-famous-corpus",
            "Generate the 500-entry famous theorem and axiom corpus; pass options after `--`.",
            family="kb",
            kind="generation",
            safety="writes_artifacts",
            command=py(
                "skills/premise-kb/premise-kb-theorem-seed-generator/scripts/generate_famous_theorem_axiom_corpus.py"
            ),
            required_paths=(
                "skills/premise-kb/premise-kb-theorem-seed-generator/scripts/generate_famous_theorem_axiom_corpus.py",
            ),
            writes=("artifacts/kb/",),
            allows_extra_args=True,
        ),
        action(
            "kb:index",
            "Index premise-selection KB seed/corpus/proof artifacts; pass index options after `--`.",
            family="kb",
            kind="generation",
            safety="writes_artifacts",
            command=py(
                "skills/premise-kb/premise-kb-indexer/scripts/index_premise_kb.py"
            ),
            required_paths=(
                "skills/premise-kb/premise-kb-indexer/scripts/index_premise_kb.py",
                "backends/premise_kb/MathformerKB/",
            ),
            writes=("artifacts/kb/",),
            allows_extra_args=True,
        ),
        action(
            "kb:skill-scripts",
            "Run deterministic tests for premise-selection KB skill scripts.",
            family="kb",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/kb/run_premise_kb_skill_scripts.py", "--json"),
            required_paths=("tests/kb/run_premise_kb_skill_scripts.py",),
            writes=("artifacts/kb/",),
        ),
        action(
            "kb:manage",
            "Call the premise-selection KB management utility; pass subcommand arguments after `--`.",
            family="kb",
            kind="utility",
            safety="writes_artifacts",
            command=py("scripts/manage_premise_kb.py"),
            required_paths=(
                "scripts/manage_premise_kb.py",
                "backends/premise_kb/MathformerKB/",
            ),
            writes=("artifacts/kb/",),
            allows_extra_args=True,
        ),
        action(
            "sympy:controlled",
            "Run the controlled SymPy autoformalization suite.",
            family="sympy",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/sympy/run_controlled_suite.py", "--json"),
            required_paths=("tests/sympy/run_controlled_suite.py",),
            writes=("artifacts/sympy/", "artifacts/sympy_api/"),
        ),
        action(
            "sympy:wiki",
            "Run the controlled wiki-level SymPy case.",
            family="sympy",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/sympy/run_wiki_case.py", "--json"),
            required_paths=("tests/sympy/run_wiki_case.py",),
            writes=("artifacts/sympy/",),
        ),
        action(
            "physics-sympy:controlled",
            "Run the controlled physics SymPy suite.",
            family="physics_sympy",
            kind="validation",
            safety="writes_artifacts",
            command=venv_py("tests/physics_sympy/run_controlled_suite.py", "--json"),
            required_paths=("tests/physics_sympy/run_controlled_suite.py",),
            writes=("artifacts/physics_sympy/",),
        ),
        action(
            "physics-sympy:goal-sample-plan-0000",
            "Plan one-sample recursive goal evidence for FormalPhysics SymPy 0000.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py",
                "--case",
                "formalphysics_0000",
                "--run-gates",
                "--json",
            ),
            required_paths=(
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0000/MathformerPhysics.py",
            ),
            timeout_seconds=300,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:repair-expansion-map-0000",
            "Map the recursive SymPy repair expansion for FormalPhysics 0000.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "skills/physics-sympy/physics-sympy-repair-expansion-cartographer/scripts/map_physics_sympy_repair_expansion.py",
                "--case",
                "formalphysics_0000",
                "--json",
            ),
            required_paths=(
                "skills/physics-sympy/physics-sympy-repair-expansion-cartographer/scripts/map_physics_sympy_repair_expansion.py",
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0000/MathformerPhysics.py",
            ),
            timeout_seconds=360,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:recursive-repair-control-0000",
            "Control the recursive SymPy repair loop for FormalPhysics 0000.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "skills/physics-sympy/physics-sympy-recursive-repair-loop-controller/scripts/control_physics_sympy_recursive_repair.py",
                "--case",
                "formalphysics_0000",
                "--json",
            ),
            required_paths=(
                "skills/physics-sympy/physics-sympy-recursive-repair-loop-controller/scripts/control_physics_sympy_recursive_repair.py",
                "skills/physics-sympy/physics-sympy-repair-expansion-cartographer/scripts/map_physics_sympy_repair_expansion.py",
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0000/MathformerPhysics.py",
            ),
            timeout_seconds=420,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:design-guard-review-0000",
            "Review SymPy FormalPhysics 0000 for broad semantic-preservation design debts.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "skills/physics-sympy/physics-sympy-review-refinement-router/scripts/plan_physics_sympy_review_refinement.py",
                "--mode",
                "design_guard_review",
                "--case",
                "formalphysics_0000",
                "--json",
            ),
            required_paths=(
                "skills/physics-sympy/physics-sympy-review-refinement-router/scripts/plan_physics_sympy_review_refinement.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0000/MathformerPhysics.py",
            ),
            timeout_seconds=300,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:grounded-sample-thoroughness-0000",
            "Gate FormalPhysics SymPy 0000 for grounded sample thoroughness.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "tests/physics_sympy/run_grounded_sample_thoroughness.py",
                "--case",
                "formalphysics_0000",
                "--json",
            ),
            required_paths=(
                "tests/physics_sympy/run_grounded_sample_thoroughness.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0000/MathformerPhysics.py",
            ),
            timeout_seconds=360,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:source-only-recursive-0000",
            "Run the source-only recursive SymPy goal workflow for FormalPhysics 0000.",
            family="physics_sympy",
            kind="generation",
            safety="writes_artifacts",
            command=venv_py(
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/run_recursive_goal_case.py",
                "--source-record",
                "artifacts/physics_sympy/source_only/formalphysics_0000/source_record.json",
                "--json",
            ),
            required_paths=(
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/run_recursive_goal_case.py",
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py",
                "skills/physics-sympy/physics-sympy-review-refinement-router/scripts/plan_physics_sympy_review_refinement.py",
                "skills/physics-sympy/physics-sympy-repair-expansion-cartographer/scripts/map_physics_sympy_repair_expansion.py",
                "skills/physics-sympy/physics-sympy-recursive-repair-loop-controller/scripts/control_physics_sympy_recursive_repair.py",
                "tests/physics_sympy/run_grounded_sample_thoroughness.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0000/MathformerPhysics.py",
            ),
            writes=("artifacts/physics_sympy/recursive_goal_runs/formalphysics_0000/",),
            timeout_seconds=900,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:goal-sample-plan-0004",
            "Plan one-sample recursive goal evidence for FormalPhysics SymPy 0004.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py",
                "--case",
                "formalphysics_0004",
                "--run-gates",
                "--json",
            ),
            required_paths=(
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0004/MathformerPhysics.py",
            ),
            timeout_seconds=300,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:design-guard-review-0004",
            "Review SymPy FormalPhysics 0004 for broad semantic-preservation design debts.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "skills/physics-sympy/physics-sympy-review-refinement-router/scripts/plan_physics_sympy_review_refinement.py",
                "--mode",
                "design_guard_review",
                "--case",
                "formalphysics_0004",
                "--json",
            ),
            required_paths=(
                "skills/physics-sympy/physics-sympy-review-refinement-router/scripts/plan_physics_sympy_review_refinement.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0004/MathformerPhysics.py",
            ),
            timeout_seconds=300,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:repair-expansion-map-0004",
            "Map the recursive SymPy repair expansion for FormalPhysics 0004.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "skills/physics-sympy/physics-sympy-repair-expansion-cartographer/scripts/map_physics_sympy_repair_expansion.py",
                "--case",
                "formalphysics_0004",
                "--json",
            ),
            required_paths=(
                "skills/physics-sympy/physics-sympy-repair-expansion-cartographer/scripts/map_physics_sympy_repair_expansion.py",
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0004/MathformerPhysics.py",
            ),
            timeout_seconds=360,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:recursive-repair-control-0004",
            "Control the recursive SymPy repair loop for FormalPhysics 0004.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "skills/physics-sympy/physics-sympy-recursive-repair-loop-controller/scripts/control_physics_sympy_recursive_repair.py",
                "--case",
                "formalphysics_0004",
                "--json",
            ),
            required_paths=(
                "skills/physics-sympy/physics-sympy-recursive-repair-loop-controller/scripts/control_physics_sympy_recursive_repair.py",
                "skills/physics-sympy/physics-sympy-repair-expansion-cartographer/scripts/map_physics_sympy_repair_expansion.py",
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0004/MathformerPhysics.py",
            ),
            timeout_seconds=420,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:grounded-sample-thoroughness-0004",
            "Gate FormalPhysics SymPy 0004 for grounded sample thoroughness.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "tests/physics_sympy/run_grounded_sample_thoroughness.py",
                "--case",
                "formalphysics_0004",
                "--json",
            ),
            required_paths=(
                "tests/physics_sympy/run_grounded_sample_thoroughness.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0004/MathformerPhysics.py",
            ),
            timeout_seconds=360,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:source-only-recursive-0004",
            "Run the source-only recursive SymPy goal workflow for FormalPhysics 0004.",
            family="physics_sympy",
            kind="generation",
            safety="writes_artifacts",
            command=venv_py(
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/run_recursive_goal_case.py",
                "--case",
                "formalphysics_0004",
                "--source-record",
                "artifacts/physics_sympy/source_only/formalphysics_0004/source_record.json",
                "--regenerate-initial-artifact",
                "--json",
            ),
            required_paths=(
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/run_recursive_goal_case.py",
                "skills/physics-sympy/physics-sympy-goal-sample-autoformalizer/scripts/plan_goal_sample_sympy_autoformalization.py",
                "skills/physics-sympy/physics-sympy-review-refinement-router/scripts/plan_physics_sympy_review_refinement.py",
                "skills/physics-sympy/physics-sympy-repair-expansion-cartographer/scripts/map_physics_sympy_repair_expansion.py",
                "skills/physics-sympy/physics-sympy-recursive-repair-loop-controller/scripts/control_physics_sympy_recursive_repair.py",
                "tests/physics_sympy/run_grounded_sample_thoroughness.py",
                "artifacts/physics_sympy/source_only/formalphysics_0004/source_record.json",
            ),
            writes=(
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0004/MathformerPhysics.py",
                "artifacts/physics_sympy/recursive_goal_runs/formalphysics_0004/",
            ),
            timeout_seconds=900,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:formal-answer-reflection-policy",
            "Validate the optional post-hoc FormalPhysics formal-answer reflection policy.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "tests/physics_sympy/run_formal_answer_reflection_policy.py", "--json"
            ),
            required_paths=(
                "tests/physics_sympy/run_formal_answer_reflection_policy.py",
                "skills/physics-sympy/physics-sympy-formal-answer-reflector/scripts/compare_sympy_formal_physics_answers.py",
            ),
            timeout_seconds=120,
        ),
        action(
            "physics-sympy:dependency-failure-policy",
            "Validate friendly structured dependency failures for missing SymPy.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "tests/physics_sympy/run_dependency_failure_policy.py", "--json"
            ),
            required_paths=(
                "tests/physics_sympy/run_dependency_failure_policy.py",
                "tests/physics_sympy/run_phase1_dependency_grounding.py",
                "tests/physics_sympy/run_controlled_suite.py",
            ),
            timeout_seconds=120,
        ),
        action(
            "physics-sympy:cross-backend-semantic-packet-0000",
            "Build the Lean/SymPy semantic alignment packet for FormalPhysics 0000.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "tests/physics_sympy/run_cross_backend_semantic_packet.py",
                "--case",
                "formalphysics_0000",
                "--json",
            ),
            required_paths=(
                "tests/physics_sympy/run_cross_backend_semantic_packet.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0000/MathformerPhysics.py",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0000/MathformerPhysics.lean",
            ),
            timeout_seconds=180,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:cross-backend-semantic-packet-0004",
            "Build the Lean/SymPy semantic alignment packet for FormalPhysics 0004.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "tests/physics_sympy/run_cross_backend_semantic_packet.py",
                "--case",
                "formalphysics_0004",
                "--json",
            ),
            required_paths=(
                "tests/physics_sympy/run_cross_backend_semantic_packet.py",
                "libraries/MathformerPhysicsLib/SymPy/formalphysics_0004/MathformerPhysics.py",
                "libraries/MathformerPhysicsLib/Lean/formalphysics_0004/MathformerPhysics.lean",
            ),
            timeout_seconds=180,
            allows_extra_args=True,
        ),
        action(
            "physics-sympy:adversarial-design-guard",
            "Run adversarial design-guard fixtures for SymPy physics.",
            family="physics_sympy",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "tests/physics_sympy/run_adversarial_design_guard_suite.py", "--json"
            ),
            required_paths=(
                "tests/physics_sympy/run_adversarial_design_guard_suite.py",
                "skills/physics-sympy/physics-sympy-review-refinement-router/scripts/plan_physics_sympy_review_refinement.py",
            ),
            timeout_seconds=180,
        ),
        action(
            "isabelle:wiki",
            "Run the controlled wiki-level Isabelle case.",
            family="isabelle",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/isabelle/run_wiki_case.py", "--json"),
            required_paths=("tests/isabelle/run_wiki_case.py",),
            writes=("artifacts/isabelle/",),
            optional_tools=("isabelle",),
        ),
        action(
            "e2e:all-backends",
            "Run the cross-backend end-to-end smoke suite.",
            family="e2e",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/e2e/run_all_backends.py", "--json"),
            required_paths=("tests/e2e/run_all_backends.py",),
            writes=("artifacts/e2e/",),
            timeout_seconds=900,
        ),
        action(
            "prism:native-semantic-parallel-e2e",
            "Run the full PRISM native-handler end-to-end suite with bounded semantic safety oracles and four parallel workers.",
            family="e2e",
            kind="validation",
            safety="writes_repo",
            command=uv_py(
                "scripts/prism/verify_mathformer_prism.py",
                "--root",
                "mathformer-prism",
                "--jobs",
                "4",
                "--handler",
                "codex",
                "--output",
                "mathformer-prism/tests/native-semantic-parallel-e2e.json",
            ),
            required_paths=(
                "scripts/prism/verify_mathformer_prism.py",
                "scripts/prism/reviewed_reasoning_projections.json",
                "mathformer-prism/",
                "../to_prism/.venv/bin/prism",
            ),
            required_tools=("uv", "codex"),
            writes=("mathformer-prism/tests/native-semantic-parallel-e2e.json",),
            timeout_seconds=3600,
            notes="Requires native Codex access and the adjacent to_prism PRISM executable.",
        ),
        action(
            "benchmark:proofnet",
            "Run ProofNet benchmark utility subcommands; pass subcommand arguments after `--`.",
            family="benchmark",
            kind="utility",
            safety="writes_artifacts",
            command=py("benchmarks/proofnet/proofnet.py"),
            required_paths=("benchmarks/proofnet/proofnet.py",),
            writes=("data/", "artifacts/benchmarks/"),
            allows_extra_args=True,
            timeout_seconds=1200,
        ),
        action(
            "benchmark:proofnet-evaluate",
            "Evaluate ProofNet predictions; pass prediction arguments after `--`.",
            family="benchmark",
            kind="validation",
            safety="writes_artifacts",
            command=py("benchmarks/proofnet/evaluate_predictions.py"),
            required_paths=("benchmarks/proofnet/evaluate_predictions.py",),
            writes=("artifacts/benchmarks/"),
            allows_extra_args=True,
            timeout_seconds=1200,
        ),
        action(
            "benchmark:formal-science",
            "Run FormalScience benchmark utility subcommands; pass subcommand arguments after `--`.",
            family="benchmark",
            kind="utility",
            safety="writes_artifacts",
            command=py("benchmarks/formal_science/formal_science.py"),
            required_paths=("benchmarks/formal_science/formal_science.py",),
            writes=("data/", "artifacts/benchmarks/"),
            allows_extra_args=True,
            timeout_seconds=1200,
        ),
        action(
            "paper:evidence-packet",
            "Build the new-functionality evidence packet for paper updates.",
            family="paper",
            kind="generation",
            safety="writes_artifacts",
            command=py(
                "paper_skills/framework-repository-cartographer/scripts/build_paper_evidence_packet.py",
                "--output",
                "artifacts/paper_skills/new_functionality_evidence_packet.json",
                "--json",
            ),
            required_paths=(
                "paper_skills/framework-repository-cartographer/scripts/build_paper_evidence_packet.py",
            ),
            writes=("artifacts/paper_skills/",),
        ),
        action(
            "paper:update-plan",
            "Plan paper updates from the new-functionality evidence packet.",
            family="paper",
            kind="generation",
            safety="writes_artifacts",
            command=py(
                "paper_skills/scientific-paper-drafter/scripts/plan_paper_update.py",
                "--evidence-packet",
                "artifacts/paper_skills/new_functionality_evidence_packet.json",
                "--output",
                "artifacts/paper_skills/paper_update_plan.md",
                "--json",
            ),
            depends_on=("paper:evidence-packet",),
            required_paths=(
                "paper_skills/scientific-paper-drafter/scripts/plan_paper_update.py",
            ),
            writes=("artifacts/paper_skills/",),
        ),
        action(
            "paper:claim-audit-framework",
            "Audit the framework paper against the paper evidence packet.",
            family="paper",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "paper_skills/paper-claim-evidence-auditor/scripts/audit_paper_claims.py",
                "--paper",
                "paper/MATHFORMER_FRAMEWORK_PAPER.tex",
                "--evidence-packet",
                "artifacts/paper_skills/new_functionality_evidence_packet.json",
                "--output",
                "artifacts/paper_skills/framework_paper_claim_audit.json",
                "--json",
            ),
            depends_on=("paper:evidence-packet",),
            required_paths=(
                "paper_skills/paper-claim-evidence-auditor/scripts/audit_paper_claims.py",
                "paper/MATHFORMER_FRAMEWORK_PAPER.tex",
            ),
            writes=("artifacts/paper_skills/",),
        ),
        action(
            "paper:claim-audit-rfde",
            "Audit the RFDE paper against the paper evidence packet.",
            family="paper",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "paper_skills/paper-claim-evidence-auditor/scripts/audit_paper_claims.py",
                "--paper",
                "paper/REFERENCE_FREE_REFINEMENT_DYNAMICS.tex",
                "--evidence-packet",
                "artifacts/paper_skills/new_functionality_evidence_packet.json",
                "--output",
                "artifacts/paper_skills/rfde_paper_claim_audit.json",
                "--json",
            ),
            depends_on=("paper:evidence-packet",),
            required_paths=(
                "paper_skills/paper-claim-evidence-auditor/scripts/audit_paper_claims.py",
                "paper/REFERENCE_FREE_REFINEMENT_DYNAMICS.tex",
            ),
            writes=("artifacts/paper_skills/",),
        ),
        action(
            "paper:functionality-update-suite",
            "Build paper evidence, plan updates, and run claim-audit gates.",
            family="paper",
            kind="validation",
            safety="writes_artifacts",
            depends_on=(
                "paper:evidence-packet",
                "paper:update-plan",
                "paper:claim-audit-framework",
                "paper:claim-audit-rfde",
            ),
            writes=("artifacts/paper_skills/",),
        ),
        action(
            "paper:mechanistic-diagram-model",
            "Build the Mathformer mechanistic diagram model JSON.",
            family="paper",
            kind="generation",
            safety="writes_artifacts",
            command=py(
                "paper_skills/mechanistic-diagram-modeler/scripts/build_mechanistic_diagram_model.py",
                "--output",
                "artifacts/paper_skills/mathformer_mechanistic_diagram.json",
                "--json",
            ),
            required_paths=(
                "paper_skills/mechanistic-diagram-modeler/scripts/build_mechanistic_diagram_model.py",
            ),
            writes=("artifacts/paper_skills/",),
        ),
        action(
            "paper:mechanistic-figure-render",
            "Render a mechanistic figure model; pass model/output arguments after `--`.",
            family="paper",
            kind="generation",
            safety="writes_artifacts",
            command=py(
                "paper_skills/mechanistic-figure-renderer/scripts/render_mechanistic_figure.py"
            ),
            required_paths=(
                "paper_skills/mechanistic-figure-renderer/scripts/render_mechanistic_figure.py",
            ),
            writes=("artifacts/paper_skills/",),
            allows_extra_args=True,
        ),
        action(
            "paper:theory-evolution-model",
            "Build the default theory-evolution model JSON.",
            family="paper",
            kind="generation",
            safety="writes_artifacts",
            command=py(
                "paper_skills/theory-evolution-modeler/scripts/build_theory_evolution_model.py",
                "--output",
                "artifacts/paper_skills/theory_evolution_model.json",
                "--json",
            ),
            required_paths=(
                "paper_skills/theory-evolution-modeler/scripts/build_theory_evolution_model.py",
            ),
            writes=("artifacts/paper_skills/",),
        ),
        action(
            "paper:theory-evolution-simulate",
            "Run one theory-evolution simulation; pass model/output arguments after `--`.",
            family="paper",
            kind="generation",
            safety="writes_artifacts",
            command=py(
                "paper_skills/theory-evolution-simulator/scripts/simulate_theory_evolution.py"
            ),
            required_paths=(
                "paper_skills/theory-evolution-simulator/scripts/simulate_theory_evolution.py",
            ),
            writes=("artifacts/paper_skills/",),
            allows_extra_args=True,
            timeout_seconds=1200,
        ),
        action(
            "paper:theory-evolution-suite",
            "Run the theory-evolution simulation suite; pass model/output arguments after `--`.",
            family="paper",
            kind="generation",
            safety="writes_artifacts",
            command=py(
                "paper_skills/theory-evolution-simulator/scripts/run_theory_evolution_simulation_suite.py"
            ),
            required_paths=(
                "paper_skills/theory-evolution-simulator/scripts/run_theory_evolution_simulation_suite.py",
            ),
            writes=("artifacts/paper_skills/",),
            allows_extra_args=True,
            timeout_seconds=1200,
        ),
        action(
            "atp:premise-guided-group",
            "Run the premise-guided group inverse ATP regression.",
            family="atp",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/atp/run_premise_guided_group_inverse.py", "--json"),
            required_paths=("tests/atp/run_premise_guided_group_inverse.py",),
            writes=("artifacts/vampire_atp/",),
            timeout_seconds=180,
        ),
        action(
            "atp:premise-guided-triple",
            "Run the premise-guided triple-product ATP regression.",
            family="atp",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/atp/run_premise_guided_triple_inverse.py", "--json"),
            required_paths=("tests/atp/run_premise_guided_triple_inverse.py",),
            writes=("artifacts/vampire_atp/",),
            timeout_seconds=180,
        ),
        action(
            "lean:wiki-level-suite",
            "Run deterministic checks for the controlled wiki-level LaTeX-to-Lean suite.",
            family="lean",
            kind="validation",
            safety="writes_artifacts",
            command=py("tests/wiki_level/run_suite.py", "--json"),
            required_paths=("tests/wiki_level/run_suite.py",),
            writes=("artifacts/wiki_level_suite/",),
            timeout_seconds=300,
        ),
        action(
            "docs:library",
            "Regenerate aligned Mathformer library documentation.",
            family="docs",
            kind="generation",
            safety="writes_repo",
            command=py(
                "skills/mathformerlib/mathformer-library-docs-generator/scripts/generate_mathformer_library_docs.py",
                "--output-dir",
                "docs/libraries/mathformerlib",
            ),
            required_paths=(
                "skills/mathformerlib/mathformer-library-docs-generator/scripts/generate_mathformer_library_docs.py",
            ),
            writes=("docs/libraries/mathformerlib/",),
        ),
        action(
            "docs:reasoning-flow-catalog",
            "Regenerate the canonical semantic-flow catalogue and the separate repository materialization cross-reference.",
            family="docs",
            kind="generation",
            safety="writes_repo",
            command=py(
                "skills/control/reasoning-flow-language/scripts/render_all_reasoning_flows.py",
                "--json",
            ),
            required_paths=(
                "skills/control/reasoning-flow-language/scripts/render_all_reasoning_flows.py",
                "skills/control/reasoning-flow-language/references/erfl-0.3.json",
                "skills/REASONING_TYPES.yaml",
                "skills/SKILL_HOOKS.yaml",
                "scripts/mathformer.py",
                "examples/reasoning_flows",
            ),
            writes=(
                "docs/architecture/ALL_REASONING_FLOWS.md",
                "docs/architecture/REASONING_FLOW_MATERIALIZATIONS.md",
            ),
        ),
        action(
            "mcp:serve",
            "Start the Mathformer MCP server, exposing ask/list/show/run/audit as MCP tools.",
            family="mcp",
            kind="server",
            safety="read_only",
            command=py("scripts/mcp_server.py"),
            required_paths=("scripts/mcp_server.py", "scripts/mathformer.py"),
            notes=(
                "Long-running stdio (or streamable-http) entrypoint for MCP clients. "
                "Configure the client to launch `python3 scripts/mcp_server.py` directly "
                "instead of running this action through `ask --run`/`run`, since the hub "
                "runner buffers subprocess output and does not proxy stdin interactively."
            ),
        ),
        action(
            "mcp:service-config",
            "Validate the independent Mathformer MCP service config and tracked secret policy.",
            family="mcp",
            kind="validation",
            safety="read_only",
            command=py(
                "scripts/load_mcp_service_config.py",
                "--config",
                "config/mathformer_mcp.example.toml",
                "--scan-tracked",
                "--json",
            ),
            required_paths=(
                "scripts/load_mcp_service_config.py",
                "scripts/mcp_service_config.py",
                "config/mathformer_mcp.example.toml",
            ),
        ),
        action(
            "mcp:service-dependencies",
            "Probe independent Mathformer MCP service Python packages and external toolchains.",
            family="mcp",
            kind="dependency_probe",
            safety="read_only",
            command=py("scripts/probe_mcp_service_dependencies.py", "--json"),
            required_paths=(
                "scripts/probe_mcp_service_dependencies.py",
                "requirements-mcp-service.txt",
            ),
        ),
        action(
            "mcp:service-self-check",
            "Run the independent Mathformer MCP service startup self-check against the example config.",
            family="mcp",
            kind="validation",
            safety="read_only",
            command=py(
                "scripts/mathformer_mcp_service.py",
                "--config",
                "config/mathformer_mcp.example.toml",
                "--self-check",
                "--json",
            ),
            required_paths=(
                "scripts/mathformer_mcp_service.py",
                "scripts/mcp_server.py",
                "scripts/mcp_service_config.py",
                "config/mathformer_mcp.example.toml",
            ),
        ),
        action(
            "licenses:inventory",
            "Generate the Python dependency license inventory.",
            family="licenses",
            kind="generation",
            safety="writes_repo",
            command=py("scripts/generate_python_license_inventory.py"),
            required_paths=("scripts/generate_python_license_inventory.py",),
            writes=("docs/",),
        ),
        action(
            "control:workflow-skill-integration-audit",
            "Audit how Mathformer skills are integrated into workflow graph artifacts.",
            family="control",
            kind="audit",
            safety="writes_artifacts",
            command=py("scripts/audit_workflow_skill_integration.py", "--json"),
            required_paths=("scripts/audit_workflow_skill_integration.py",),
            writes=("artifacts/workflow_graphs/",),
        ),
        action(
            "docs:workflow-graph-render",
            "Render Mathformer workflow graph JSON and HTML reports.",
            family="docs",
            kind="generation",
            safety="writes_artifacts",
            command=py("scripts/render_workflow_graphs.py", "--json"),
            required_paths=("scripts/render_workflow_graphs.py",),
            writes=("artifacts/workflow_graphs/",),
        ),
        action(
            "docs:workflow-graph-layout",
            "Plan workflow graph layout metadata for Mathformer workflow reports.",
            family="docs",
            kind="generation",
            safety="writes_artifacts",
            command=py("scripts/plan_workflow_graph_layout.py", "--json"),
            required_paths=("scripts/plan_workflow_graph_layout.py",),
            writes=("artifacts/workflow_graphs/",),
        ),
        action(
            "paper:workflow-catalog",
            "Collect workflow graph evidence into paper-ready catalogue artifacts.",
            family="paper",
            kind="generation",
            safety="writes_artifacts",
            command=py(
                "paper_skills/framework-repository-cartographer/scripts/collect_workflow_catalog_for_paper.py",
                "--json",
            ),
            required_paths=(
                "paper_skills/framework-repository-cartographer/scripts/collect_workflow_catalog_for_paper.py",
            ),
            writes=("artifacts/paper_skills/",),
        ),
        action(
            "mathformerphysicslib:coherence-inventory",
            "Smoke-test MathformerPhysicsLib coherence inventory construction.",
            family="mathformerphysicslib",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts/build_coherence_inventory.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts/build_coherence_inventory.py",
            ),
        ),
        action(
            "mathformerphysicslib:concept-canonicalize",
            "Smoke-test MathformerPhysicsLib concept canonicalization.",
            family="mathformerphysicslib",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-concept-canonicalizer/scripts/canonicalize_physics_concepts.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-concept-canonicalizer/scripts/canonicalize_physics_concepts.py",
            ),
        ),
        action(
            "mathformerphysicslib:mathlib-grounding-audit",
            "Smoke-test MathformerPhysicsLib Mathlib grounding audits.",
            family="mathformerphysicslib",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-mathlib-grounding-auditor/scripts/audit_mathlib_grounding.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-mathlib-grounding-auditor/scripts/audit_mathlib_grounding.py",
            ),
        ),
        action(
            "mathformerphysicslib:redefinition-critic",
            "Smoke-test MathformerPhysicsLib redefinition critic.",
            family="mathformerphysicslib",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-redefinition-critic/scripts/critic_redefinitions.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-redefinition-critic/scripts/critic_redefinitions.py",
            ),
        ),
        action(
            "mathformerphysicslib:integration-critic",
            "Smoke-test MathformerPhysicsLib integration critic.",
            family="mathformerphysicslib",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-integration-critic/scripts/critic_integration.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-integration-critic/scripts/critic_integration.py",
            ),
        ),
        action(
            "mathformerphysicslib:api-operability-critic",
            "Smoke-test MathformerPhysicsLib API operability critic.",
            family="mathformerphysicslib",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-api-operability-critic/scripts/critic_api_operability.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-api-operability-critic/scripts/critic_api_operability.py",
            ),
        ),
        action(
            "mathformerphysicslib:generative-coherence-critic",
            "Smoke-test MathformerPhysicsLib generative coherence critic planning.",
            family="mathformerphysicslib",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-generative-coherence-critic/scripts/build_generative_coherence_critic_plan.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-generative-coherence-critic/scripts/build_generative_coherence_critic_plan.py",
            ),
        ),
        action(
            "mathformerphysicslib:coherence-repair-plan",
            "Smoke-test MathformerPhysicsLib coherence repair planning.",
            family="mathformerphysicslib",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-coherence-repair-planner/scripts/plan_coherence_repairs.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-coherence-repair-planner/scripts/plan_coherence_repairs.py",
            ),
        ),
        action(
            "mathformerphysicslib:coherence-gate",
            "Smoke-test MathformerPhysicsLib coherence gate.",
            family="mathformerphysicslib",
            kind="validation",
            safety="read_only",
            command=py(
                "skills/mathformerphysicslib/mathformerphysicslib-coherence-gate/scripts/gate_coherence.py",
                "--self-test",
                "--json",
            ),
            required_paths=(
                "skills/mathformerphysicslib/mathformerphysicslib-coherence-gate/scripts/gate_coherence.py",
            ),
        ),
        action(
            "mathformerphysicslib:coherence-suite",
            "Run the controlled MathformerPhysicsLib coherence smoke suite.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="read_only",
            depends_on=(
                "mathformerphysicslib:coherence-inventory",
                "mathformerphysicslib:concept-canonicalize",
                "mathformerphysicslib:mathlib-grounding-audit",
                "mathformerphysicslib:redefinition-critic",
                "mathformerphysicslib:integration-critic",
                "mathformerphysicslib:api-operability-critic",
                "mathformerphysicslib:generative-coherence-critic",
                "mathformerphysicslib:coherence-repair-plan",
                "mathformerphysicslib:coherence-gate",
            ),
        ),
        action(
            "mathformerphysicslib:coherence-loop-report",
            "Run the MathformerPhysicsLib coherence loop and generate JSON/Markdown evidence reports.",
            family="mathformerphysicslib",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "tests/physics_lean/run_mathformerphysicslib_coherence_loop.py",
                "--json",
            ),
            required_paths=(
                "tests/physics_lean/run_mathformerphysicslib_coherence_loop.py",
                "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts/coherence_common.py",
            ),
            writes=("artifacts/mathformerphysicslib/coherence/",),
        ),
        action(
            "mathformerphysicslib:all-candidate-compile",
            "Compile every tracked MathformerPhysicsLib Lean candidate with hashes and diagnostics.",
            family="mathformerphysicslib",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "tests/physics_lean/run_mathformerphysicslib_all_candidate_compile.py",
                "--json",
            ),
            required_paths=(
                "tests/physics_lean/run_mathformerphysicslib_all_candidate_compile.py",
                "libraries/MathformerPhysicsLib/Lean/",
            ),
            required_tools=("lake",),
            writes=("artifacts/physics_lean/all_candidate_compile/", ".lake/"),
            timeout_seconds=1800,
        ),
        action(
            "mathformerphysicslib:release-gate",
            "Build the promoted PhysicsLib public root and require coherence release acceptance.",
            family="mathformerphysicslib",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "tests/physics_lean/run_mathformerphysicslib_release_gate.py", "--json"
            ),
            required_paths=(
                "tests/physics_lean/run_mathformerphysicslib_release_gate.py",
                "libraries/MathformerPhysicsLib.lean",
            ),
            required_tools=("lake",),
            writes=("artifacts/physics_lean/release_gate/", ".lake/"),
            timeout_seconds=1200,
        ),
        action(
            "mathformerphysicslib:registry-build",
            "Rebuild the complete physics artifact registry and generated README coverage.",
            family="mathformerphysicslib",
            kind="generation",
            safety="writes_repo",
            command=py(
                "scripts/build_physics_registry.py", "--write", "--check", "--json"
            ),
            required_paths=(
                "scripts/build_physics_registry.py",
                "libraries/MathformerPhysicsLib/MANIFEST.json",
            ),
            writes=(
                "libraries/MathformerPhysicsLib/MANIFEST.json",
                "libraries/MathformerPhysicsLib/README.md",
            ),
        ),
        action(
            "mathformerphysicslib:registry-check",
            "Validate physics artifact registration and provenance hashes.",
            family="mathformerphysicslib",
            kind="validation",
            safety="read_only",
            command=py("scripts/build_physics_registry.py", "--check", "--json"),
            required_paths=(
                "scripts/build_physics_registry.py",
                "libraries/MathformerPhysicsLib/MANIFEST.json",
            ),
        ),
        action(
            "physics:ir-build",
            "Build a backend-neutral physics IR from one JSON source record; pass paths after `--`.",
            family="physics_sympy",
            kind="generation",
            safety="writes_artifacts",
            command=py("scripts/physics_ir.py"),
            required_paths=(
                "scripts/physics_ir.py",
                "libraries/MathformerPhysicsLib/physics_ir.py",
            ),
            writes=("artifacts/",),
            allows_extra_args=True,
        ),
        action(
            "mathformerphysicslib:cross-backend-parity",
            "Gate promoted physics semantics across Lean, SymPy, and registered Isabelle projections.",
            family="mathformerphysicslib",
            kind="validation",
            safety="read_only",
            command=venv_py(
                "tests/physics_sympy/run_cross_backend_parity_gate.py", "--json"
            ),
            required_paths=(
                "tests/physics_sympy/run_cross_backend_parity_gate.py",
                "libraries/MathformerPhysicsLib/physics_ir.py",
            ),
        ),
        action(
            "mathformerphysicslib:calibration-dashboard",
            "Measure physics critic false-positive and false-negative rates on labeled fixtures.",
            family="mathformerphysicslib",
            kind="validation",
            safety="writes_artifacts",
            command=py(
                "tests/physics_lean/run_critic_calibration_dashboard.py", "--json"
            ),
            required_paths=("tests/physics_lean/run_critic_calibration_dashboard.py",),
            writes=("artifacts/physics_lean/calibration/",),
        ),
        action(
            "environment:dependency-lock",
            "Validate the committed uv lock and dependency profiles.",
            family="environment",
            kind="validation",
            safety="read_only",
            command=py("tests/environment/run_dependency_lock_contract.py", "--json"),
            required_paths=(
                "pyproject.toml",
                "uv.lock",
                "tests/environment/run_dependency_lock_contract.py",
            ),
            required_tools=("uv",),
        ),
        action(
            "physics-lib:coherence-inventory",
            "Alias for MathformerPhysicsLib coherence inventory construction.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="read_only",
            depends_on=("mathformerphysicslib:coherence-inventory",),
        ),
        action(
            "physics-lib:coherence-canonicalize",
            "Alias for MathformerPhysicsLib concept canonicalization.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="read_only",
            depends_on=("mathformerphysicslib:concept-canonicalize",),
        ),
        action(
            "physics-lib:coherence-mathlib-grounding",
            "Alias for MathformerPhysicsLib Mathlib grounding audits.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="read_only",
            depends_on=("mathformerphysicslib:mathlib-grounding-audit",),
        ),
        action(
            "physics-lib:coherence-redefinition-critic",
            "Alias for MathformerPhysicsLib redefinition critic.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="read_only",
            depends_on=("mathformerphysicslib:redefinition-critic",),
        ),
        action(
            "physics-lib:coherence-integration-critic",
            "Alias for MathformerPhysicsLib integration critic.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="read_only",
            depends_on=("mathformerphysicslib:integration-critic",),
        ),
        action(
            "physics-lib:coherence-api-critic",
            "Alias for MathformerPhysicsLib API operability critic.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="read_only",
            depends_on=("mathformerphysicslib:api-operability-critic",),
        ),
        action(
            "physics-lib:coherence-generative-critic",
            "Alias for MathformerPhysicsLib generative coherence critic.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="read_only",
            depends_on=("mathformerphysicslib:generative-coherence-critic",),
        ),
        action(
            "physics-lib:coherence-repair-plan",
            "Alias for MathformerPhysicsLib coherence repair planning.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="read_only",
            depends_on=("mathformerphysicslib:coherence-repair-plan",),
        ),
        action(
            "physics-lib:coherence-gate",
            "Alias for MathformerPhysicsLib coherence gating.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="read_only",
            depends_on=("mathformerphysicslib:coherence-gate",),
        ),
        action(
            "physics-lib:coherence-suite",
            "Alias for the controlled MathformerPhysicsLib coherence suite.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="read_only",
            depends_on=("mathformerphysicslib:coherence-suite",),
        ),
        action(
            "physics-lib:coherence-loop-report",
            "Alias for the report-producing MathformerPhysicsLib coherence loop.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="writes_artifacts",
            depends_on=("mathformerphysicslib:coherence-loop-report",),
            writes=("artifacts/mathformerphysicslib/coherence/",),
        ),
        action(
            "physics-lib:all-candidate-compile",
            "Alias for compiling every tracked MathformerPhysicsLib Lean candidate.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="writes_artifacts",
            depends_on=("mathformerphysicslib:all-candidate-compile",),
            writes=("artifacts/physics_lean/all_candidate_compile/", ".lake/"),
        ),
        action(
            "physics-lib:release-gate",
            "Alias for the promoted MathformerPhysicsLib release gate.",
            family="mathformerphysicslib",
            kind="sequence",
            safety="writes_artifacts",
            depends_on=("mathformerphysicslib:release-gate",),
            writes=("artifacts/physics_lean/release_gate/", ".lake/"),
        ),
    ]

    for family in CONTROLLED_TEST_FAMILIES:
        action_id = f"test:family:{family.replace('_', '-')}"
        actions.append(
            action(
                action_id,
                f"Run the comprehensive test matrix for the {family} module family.",
                family=family,
                kind="validation",
                safety="writes_artifacts",
                command=py(
                    "tests/test_program/run_comprehensive_tests.py",
                    "--module-family",
                    family,
                    "--json",
                ),
                required_paths=(
                    "tests/test_program/run_comprehensive_tests.py",
                    "tests/test_matrix.json",
                ),
                writes=("artifacts/",),
                timeout_seconds=900,
            )
        )

    actions.extend(
        [
            action(
                "quality:smoke",
                "Run the compact quality gate for ordinary development changes.",
                family="quality",
                kind="sequence",
                safety="writes_artifacts",
                depends_on=(
                    "control:all",
                    "test:quick",
                    "test:docs",
                    "rocq:wiki-suite",
                    "kb:e2e",
                ),
            ),
            action(
                "quality:full",
                "Run the broad repository quality gate.",
                family="quality",
                kind="sequence",
                safety="writes_artifacts",
                depends_on=("control:all", "test:comprehensive"),
            ),
            action(
                "quality:strict",
                "Run the capability-complete strict repository release gate.",
                family="quality",
                kind="sequence",
                safety="writes_artifacts",
                depends_on=("control:all", "test:comprehensive-strict"),
            ),
        ]
    )

    registry = {item.action_id: item for item in actions}
    if len(registry) != len(actions):
        duplicates = sorted(
            {
                item.action_id
                for item in actions
                if sum(other.action_id == item.action_id for other in actions) > 1
            }
        )
        raise RuntimeError(f"Duplicate workflow action ids: {', '.join(duplicates)}")
    return registry


def action_to_dict(item: WorkflowAction) -> Dict[str, Any]:
    """Serialize one action for JSON output and reports.

    Motivation:
        Let humans, CI, and agents inspect the same action contract.

    Intent:
        Convert immutable dataclass state into plain JSON-compatible values.

    Inputs:
        A registered `WorkflowAction`.

    Outputs:
        A dictionary with command metadata and safety labels.
    """

    return {
        "id": item.action_id,
        "summary": item.summary,
        "family": item.family,
        "kind": item.kind,
        "safety": item.safety,
        "command": list(item.command),
        "depends_on": list(item.depends_on),
        "required_paths": list(item.required_paths),
        "required_tools": list(item.required_tools),
        "optional_tools": list(item.optional_tools),
        "writes": list(item.writes),
        "allows_extra_args": item.allows_extra_args,
        "timeout_seconds": item.timeout_seconds,
        "notes": item.notes,
    }


def build_intent_routes() -> Tuple[IntentRoute, ...]:
    """Return deterministic natural-language routes for common work.

    Motivation:
        Put natural language at the user and agent boundary while preserving the
        audited AgenticHub underneath.

    Intent:
        Capture common requests such as "prove this with Vampire", "check the
        docs", or "run premise selection" as stable route records.

    Inputs:
        None. The route table is static so it can be reviewed in diffs.

    Outputs:
        A tuple of `IntentRoute` records consumed by the NL resolver.
    """

    return (
        IntentRoute(
            route_id="validate.normalized_workflows",
            title="Validate normalized workflow skill contracts",
            description="Check every workflow-skill/v1 descriptor against canonical sources, payload schemas and dataflow without executing scientific workflows.",
            action_ids=("control:normalized-workflows",),
            skill_routes=("workflow-contract-validator",),
            positive_terms=(
                "validate normalized workflows",
                "workflow-skill/v1",
                "typed workflow contracts",
                "validate workflow skill format",
            ),
            examples=("Validate normalized workflows.",),
        ),
        IntentRoute(
            route_id="prove.vampire.atp",
            title="Prove an informal first-order theorem with Vampire ATP",
            description=(
                "Use when the user wants Mathformer to translate an informal theorem "
                "into TPTP, select or generate premises, run Vampire, and package a proof report."
            ),
            action_ids=("atp:demo",),
            skill_routes=("vampire-atp-orchestrator", "vampire-proof-informalizer"),
            positive_terms=(
                "prove",
                "proof",
                "vampire",
                "atp",
                "automated theorem prover",
                "first order",
                "tptp",
                "premise guided",
                "premise selection",
                "informal theorem",
                "group inverse",
                "strict order",
            ),
            examples=(
                "Prove this informal group theorem with Vampire.",
                "Run a premise-guided ATP proof search.",
            ),
            operator_note="Writes proof-discovery artifacts under artifacts/vampire_atp/.",
        ),
        IntentRoute(
            route_id="validate.atp",
            title="Validate the ATP proof-search family",
            description="Use after changing ATP translation, premise selection, or Vampire proof parsing.",
            action_ids=("test:family:atp",),
            skill_routes=("vampire-atp-orchestrator",),
            positive_terms=(
                "test atp",
                "validate atp",
                "atp regression",
                "vampire regression",
                "validate atp",
                "premise guided regression",
                "changed atp",
                "proof search",
                "proof search tests",
            ),
            examples=("Check that the Vampire proof-search workflow still works.",),
            operator_note="Runs the ATP family in the comprehensive test matrix.",
        ),
        IntentRoute(
            route_id="kb.premise.selection",
            title="Run or validate premise selection",
            description=(
                "Use when the user wants premise-selection candidates, exact presence checks, "
                "Bloom-filter membership, embedding search, or geometric distance."
            ),
            action_ids=("kb:e2e",),
            skill_routes=("premise-kb-indexer", "premise-kb-theorem-seed-generator"),
            positive_terms=(
                "premise kb",
                "knowledge base",
                "kb",
                "bloom",
                "presence check",
                "search",
                "nearby facts",
                "facts near",
                "fundamental theorem",
                "semantic search",
                "geometric distance",
                "embedding",
                "index premise",
                "premise selection",
            ),
            examples=(
                "Run premise selection and test semantic search.",
                "Check whether a theorem is already in the KB.",
            ),
            operator_note="Writes ignored KB artifacts under artifacts/kb/.",
        ),
        IntentRoute(
            route_id="kb.famous.corpus",
            title="Generate the famous theorem and axiom corpus",
            description="Use when the user wants a broad seed corpus for premise selection.",
            action_ids=("kb:famous-corpus",),
            skill_routes=("premise-kb-theorem-seed-generator", "premise-kb-indexer"),
            positive_terms=(
                "famous theorem",
                "famous corpus",
                "axiom corpus",
                "500 theorem",
                "500 famous",
                "generate theorem list",
                "generate axioms",
                "seed corpus",
            ),
            examples=("Create a corpus of famous theorems and axioms for the KB.",),
            operator_note="Generates and validates corpus artifacts under artifacts/kb/.",
        ),
        IntentRoute(
            route_id="formalize.lean",
            title="Work on Lean or mathlib formalization",
            description=(
                "Use when the user wants checked Lean work, mathlib-aligned declarations, "
                "or validation of Lean files."
            ),
            action_ids=("lean:build",),
            skill_routes=("lean-autoformalization-drafter", "lean-execution-runner"),
            positive_terms=(
                "lean",
                "mathlib",
                "lake build",
                "formalize in lean",
                "lean theorem",
                "compile lean",
                "checked formalization",
                "mathformerlib",
            ),
            examples=("Formalize this theorem in Lean and check it.",),
            operator_note="Writes Lean build cache under .lake/.",
        ),
        IntentRoute(
            route_id="validate.lean.fixture",
            title="Validate the wiki-level Lean suite",
            description="Use when the user changed wiki-level LaTeX-to-Lean fixtures or checks.",
            action_ids=("lean:wiki-level-suite",),
            skill_routes=("lean-autoformalization-drafter", "lean-execution-runner"),
            positive_terms=(
                "wiki level lean",
                "latex to lean",
                "lean fixture",
                "wiki suite",
                "expected declarations",
                "wiki level suite",
            ),
            examples=("Run the wiki-level Lean formalization suite.",),
            operator_note="Writes ignored suite artifacts under artifacts/wiki_level_suite/.",
        ),
        IntentRoute(
            route_id="formalize.rocq",
            title="Generate or validate Rocq proof scripts",
            description="Use when the user wants controlled Rocq `.v` candidates or Rocq checks.",
            action_ids=("rocq:wiki-suite",),
            skill_routes=("rocq-autoformalization-drafter", "rocq-execution-runner"),
            positive_terms=(
                "rocq",
                "coq",
                "proof script",
                "rocq proof",
                "coqc",
                "generate rocq",
                "check rocq",
            ),
            examples=("Generate Rocq proof scripts from the controlled fixtures.",),
            operator_note="Compiler checks run only when Rocq/coqc is installed.",
        ),
        IntentRoute(
            route_id="formalize.sympy",
            title="Check algebra or equations with SymPy",
            description="Use when the target is an executable equation, identity, or symbolic derivation.",
            action_ids=("sympy:controlled",),
            skill_routes=("sympy-autoformalization-drafter", "sympy-execution-runner"),
            positive_terms=(
                "sympy",
                "symbolic",
                "equation",
                "identity",
                "algebra",
                "counterexample",
                "simplify",
                "executable algebra",
            ),
            examples=("Check this identity with SymPy.",),
            operator_note="Writes ignored SymPy artifacts under artifacts/sympy/.",
        ),
        IntentRoute(
            route_id="formalize.physics.sympy",
            title="Check physics derivations with SymPy",
            description="Use when the target is a physics formula with assumptions, units, or dimensions.",
            action_ids=("physics-sympy:controlled",),
            skill_routes=(
                "physics-sympy-workflow-orchestrator",
                "physics-sympy-execution-runner",
            ),
            positive_terms=(
                "physics sympy",
                "physics derivation",
                "units",
                "dimensions",
                "dimension analysis",
                "regime assumptions",
                "physics equation",
            ),
            examples=("Validate this physics derivation with SymPy.",),
            operator_note="Writes ignored physics SymPy artifacts under artifacts/physics_sympy/.",
        ),
        IntentRoute(
            route_id="formalize.physics.sympy.goal_sample_0000",
            title="Run the recursive goal workflow for FormalPhysics SymPy 0000",
            description=(
                "Use when FormalPhysics SymPy 0000 should be inspected through the one-sample, "
                "source-only, recursive goal workflow with deterministic SymPy gates."
            ),
            action_ids=(
                "physics-sympy:source-only-recursive-0000",
                "physics-sympy:goal-sample-plan-0000",
                "physics-sympy:design-guard-review-0000",
                "physics-sympy:repair-expansion-map-0000",
                "physics-sympy:recursive-repair-control-0000",
                "physics-sympy:grounded-sample-thoroughness-0000",
                "physics-sympy:cross-backend-semantic-packet-0000",
                "physics-sympy:adversarial-design-guard",
                "physics-sympy:dependency-failure-policy",
            ),
            skill_routes=(
                "physics-sympy-goal-sample-autoformalizer",
                "physics-sympy-review-refinement-router",
                "physics-sympy-repair-expansion-cartographer",
                "physics-sympy-recursive-repair-loop-controller",
            ),
            positive_terms=(
                "same for sympy formalphysics_0000",
                "formalphysics sympy 0000",
                "formalphysics_sympy_0000",
                "formalphysics_0000",
                "sympy formalphysics_0000",
                "sympy example 0000",
                "physics sympy 0000",
                "example 0000",
                "0000",
                "recursive goal sympy",
                "sympy recursive goal",
                "new sympy physics recursive pipeline",
                "review the new sympy physics recursive pipeline",
                "sympy physics recursive pipeline",
                "review sympy physics recursive pipeline",
                "new sympy pipeline",
                "full review sympy pipeline",
                "recursive goal oriented physics sympy",
                "recursive goal oriented physics sympy example 0000",
                "review the sympy physics derivation workflow for one case",
                "one sample sympy",
                "source only sympy",
                "lorentz force x component",
            ),
            examples=(
                "Run the recursive goal oriented workflow for SymPy formalphysics_0000.",
                "Same for SymPy example 0000.",
                "Review the SymPy physics derivation workflow for one case.",
            ),
            operator_note="Locks formalphysics_0000 as the only sample; the source-only runner writes workflow-stage reports under artifacts/physics_sympy/recursive_goal_runs/formalphysics_0000/.",
        ),
        IntentRoute(
            route_id="formalize.physics.sympy.goal_sample_0004",
            title="Run the recursive goal workflow for FormalPhysics SymPy 0004",
            description=(
                "Use when FormalPhysics SymPy 0004 should be generated or inspected through the "
                "one-sample, source-only, recursive goal workflow with deterministic SymPy gates."
            ),
            action_ids=(
                "physics-sympy:source-only-recursive-0004",
                "physics-sympy:goal-sample-plan-0004",
                "physics-sympy:design-guard-review-0004",
                "physics-sympy:repair-expansion-map-0004",
                "physics-sympy:recursive-repair-control-0004",
                "physics-sympy:grounded-sample-thoroughness-0004",
                "physics-sympy:cross-backend-semantic-packet-0004",
                "physics-sympy:adversarial-design-guard",
                "physics-sympy:dependency-failure-policy",
            ),
            skill_routes=(
                "physics-sympy-goal-sample-autoformalizer",
                "physics-sympy-review-refinement-router",
                "physics-sympy-repair-expansion-cartographer",
                "physics-sympy-recursive-repair-loop-controller",
            ),
            positive_terms=(
                "autoformalize sympy formalphysics_0004",
                "sympy formalphysics_0004",
                "formalphysics sympy 0004",
                "formalphysics_0004",
                "physics sympy 0004",
                "sympy example 0004",
                "example 0004",
                "0004",
                "autoformalize 0004 from scratch",
                "formalphysics_0004 from scratch",
                "recursive goal oriented physics sympy 0004",
                "recursive goal sympy 0004",
                "goal oriented sympy 0004",
                "dimensionless ladder number operator",
                "ladder number operator",
                "harmonic oscillator number operator",
            ),
            examples=(
                "Autoformalize SymPy formalphysics_0004 from scratch.",
                "Run the recursive goal oriented workflow for SymPy formalphysics_0004.",
            ),
            operator_note="Locks formalphysics_0004 as the only sample; the source-only runner may generate the initial SymPy artifact and writes workflow-stage reports under artifacts/physics_sympy/recursive_goal_runs/formalphysics_0004/.",
        ),
        IntentRoute(
            route_id="monitor.physics.lean.drift",
            title="Monitor Lean physics semantic-drift pathologies",
            description=(
                "Use when the user wants FormalScience/FormalPhysics taxonomy monitoring for "
                "notational collapse, abstraction elevation, proof strategy substitution, or "
                "implicit premise selection during physics autoformalization."
            ),
            action_ids=("physics-lean:drift-pathology-monitor",),
            skill_routes=("physics-lean-drift-pathology-monitor",),
            positive_terms=(
                "physics lean drift",
                "semantic drift",
                "alignment drift",
                "drift pathology",
                "pathologies",
                "taxonomy",
                "formalscience taxonomy",
                "formalphysics taxonomy",
                "notational collapse",
                "abstraction elevation",
                "proof strategy substitution",
                "implicit premise selection",
                "autoformalizing physics",
                "autoformalization physics pathologies",
            ),
            examples=(
                "Monitor this Lean physics artifact for notational collapse and abstraction elevation.",
            ),
            operator_note="Pass source and Lean artifact paths after `--`; writes only when an --output path is supplied.",
        ),
        IntentRoute(
            route_id="repair.physics.lean.pathologies",
            title="Run the Lean physics pathology repair loop",
            description=(
                "Use when detected FormalScience/FormalPhysics pathologies should be repaired through "
                "physics object detection, MathformerPhysicsLib-first object work, guarded generative repair, "
                "exhaustive recursive expansion mapping, and controlled Lean target refinement planning."
            ),
            action_ids=(
                "physics-lean:detect-pathology-objects",
                "physics-lean:object-workbench",
                "physics-lean:pathology-repair-loop",
                "physics-lean:generative-repair-plan",
                "physics-lean:repair-expansion-map",
                "physics-lean:recursive-repair-control",
            ),
            skill_routes=(
                "physics-math-object-detector",
                "mathformerphysicslib-object-workbench",
                "physics-lean-pathology-repair-orchestrator",
                "physics-lean-generative-repair-orchestrator",
                "physics-lean-repair-expansion-cartographer",
                "physics-lean-recursive-repair-loop-controller",
            ),
            positive_terms=(
                "fix physics lean pathologies",
                "repair physics lean pathologies",
                "pathology repair loop",
                "fix notational collapse",
                "fix abstraction elevation",
                "mathformerphysicslib first",
                "work over physics object",
                "physics mathematical object",
                "library first repair",
                "repair semantic drift",
                "generative repair",
                "codex exec repair",
                "recursive repair",
                "exhaustive repair",
                "repair expansion map",
                "controlled recursive loop",
                "repair recursion control",
            ),
            examples=(
                "Repair detected Lean physics pathologies through MathformerPhysicsLib-first object work.",
            ),
            operator_note="Run monitor first, then pass its report through the object, workbench, and repair-loop actions.",
        ),
        IntentRoute(
            route_id="formalize.physics.lean.goal_sample_0009",
            title="Run the recursive goal autoformalization workflow for FormalPhysics 0009",
            description=(
                "Use when FormalPhysics 0009 should continue through the one-sample, "
                "MathformerPhysicsLib-first recursive goal workflow with deterministic gates."
            ),
            action_ids=("physics-lean:goal-sample-recursive-0009",),
            skill_routes=(
                "physics-lean-goal-sample-autoformalizer",
                "physics-lean-repair-expansion-cartographer",
                "physics-lean-recursive-repair-loop-controller",
            ),
            positive_terms=(
                "formalphysics 0009",
                "formalphysics_0009",
                "example 009",
                "009",
                "recursive goal",
                "goal oriented",
                "goal-oriented",
                "recursive goal oriented workflow",
                "recursive goal workflow",
                "one sample recursive",
                "skills maximization",
                "maximize skills",
                "source only qm",
                "fourier integration by parts",
                "position momentum fourier",
                "continue 009",
                "refine 009",
            ),
            examples=(
                "Continue the recursive goal oriented workflow for example 009.",
                "Run the one-sample recursive goal workflow for formalphysics_0009.",
            ),
            operator_note="Runs the source-only 0009 recursive goal runner and writes refreshed workflow artifacts.",
        ),
        IntentRoute(
            route_id="formalize.physics.lean.foundations",
            title="Build MathformerPhysicsLib Lean foundations",
            description=(
                "Use when fundamental physics concepts or mathematical objects should be "
                "autoformalized into MathformerPhysicsLib with Mathlib-first grounding."
            ),
            action_ids=("physics-lean:foundation-formalization-loop",),
            skill_routes=(
                "physics-foundation-object-intake",
                "mathformerphysicslib-foundation-surface-designer",
                "mathformerphysicslib-foundation-drafter",
                "mathformerphysicslib-foundation-verifier",
                "mathformerphysicslib-object-workbench",
            ),
            positive_terms=(
                "mathformerphysicslib foundations",
                "physics foundations workflow",
                "fundamental physics concepts",
                "physics mathematical objects",
                "autoformalize physics foundations",
                "mathlib grounded physics",
                "mathlib first physics",
                "foundation formalization loop",
                "recursive foundation workflow",
                "recursive mathformerphysicslib foundation",
                "recursive mathformerphysicslib foundations",
                "autoformalize hilbert space",
                "hilbert space foundation",
                "hilbert space foundations",
                "hilbert space recursive",
                "hilbert space mathformerphysicslib",
                "vector field foundation",
                "physics law witness",
                "unit dimension compatible",
            ),
            examples=(
                "Autoformalize these fundamental physics objects into MathformerPhysicsLib foundations.",
            ),
            operator_note="Runs the priority-1 controlled suite; pass individual foundation actions for custom packets.",
        ),
        IntentRoute(
            route_id="formalize.physics.lean.dirac_recursive",
            title="Generate recursively grounded Dirac FormalPhysics examples",
            description=(
                "Use when Dirac-notation FormalPhysics examples should be "
                "autoformalized through MathformerPhysicsLib foundations with recursive grounding."
            ),
            action_ids=("physics-lean:dirac-recursive-formalphysics",),
            skill_routes=(
                "physics-foundation-object-intake",
                "mathformerphysicslib-foundation-surface-designer",
                "mathformerphysicslib-foundation-verifier",
                "physics-lean-recursive-repair-loop-controller",
            ),
            positive_terms=(
                "dirac notation formalphysics",
                "dirac formal science",
                "dirac formalphysics",
                "recursive dirac",
                "recursively grounded dirac",
                "bra ket examples",
                "braket examples",
                "formal science dirac examples",
                "five dirac examples",
                "dirac recursive grounding",
            ),
            examples=(
                "Pick five Dirac notation FormalPhysics examples and autoformalize them recursively.",
            ),
            operator_note="Writes generated Lean files and grounding evidence under artifacts/physics_lean/dirac_recursive_batch/.",
        ),
        IntentRoute(
            route_id="validate.physics.lean.derivation_completeness",
            title="Check Lean physics derivation completeness",
            description=(
                "Use when a generated Lean physics artifact must be checked for complete "
                "autoformalization rather than compile-only or surface-grounded status."
            ),
            action_ids=("physics-lean:derivation-completeness",),
            skill_routes=(
                "physics-lean-derivation-completeness-checker",
                "physics-lean-recursive-repair-loop-controller",
            ),
            positive_terms=(
                "complete autoformalization",
                "is this a complete autoformalization",
                "check whether this lean physics artifact is complete",
                "check whether this lean physics artifact is a complete autoformalization",
                "lean physics derivation completeness",
                "derivation completeness",
                "target restating hypothesis",
                "target restating witness",
                "physical law witness target",
                "source step obligation ledger",
                "compiled surface is not complete",
            ),
            examples=(
                "Check whether this Lean physics artifact is a complete autoformalization.",
            ),
            operator_note="Defaults to formalphysics_0014 and accepts extra checker args for other files.",
        ),
        IntentRoute(
            route_id="report.formalphysics.comparative_analysis",
            title="Build a FormalPhysics comparative analysis report",
            description=(
                "Use when current Mathformer FormalPhysics Lean artifacts should be compared "
                "with external-system Lean outputs from selected-example JSON, using reference "
                "answers as non-gold evidence and including the full Foundations dependency surface."
            ),
            action_ids=(
                "physics-lean:formalphysics-comparative-report-self-test",
                "physics-lean:formalphysics-comparative-report",
            ),
            skill_routes=("formalphysics-comparative-analysis-reporter",),
            positive_terms=(
                "formalphysics comparative report",
                "formalphysics comparison report",
                "compare external system formalphysics",
                "compare mathformer with formaldiscovery",
                "selected_examples.json",
                "side by side lean",
                "lean side by side report",
                "reference answer not gold",
                "non gold reference answer",
                "compare lean formalizations",
                "formalphysics html report",
                "foundations dependency comparison",
            ),
            examples=(
                "Build the FormalPhysics comparative HTML report from selected_examples.json.",
                "Compare Mathformer and the external system side by side with Foundations dependencies.",
            ),
            operator_note=(
                "Run the report action with extra args: `-- --input-json PATH --output-dir "
                "artifacts/formalphysics_comparative_analysis/RUN --json`; add `--execute-lean` for compile gates."
            ),
        ),
        IntentRoute(
            route_id="report.formalphysics.judge_synthesis",
            title="Build a FormalPhysics judge synthesis report",
            description=(
                "Use when an existing FormalPhysics comparative report should be synthesized "
                "across all cases, both Lean approaches, deterministic judges, Codex-exec "
                "judge statuses, and theorem-prover/physics role reviews."
            ),
            action_ids=(
                "physics-lean:formalphysics-judge-synthesis-report-self-test",
                "physics-lean:formalphysics-judge-synthesis-report",
            ),
            skill_routes=("formalphysics-judge-synthesis-reporter",),
            positive_terms=(
                "formalphysics judge synthesis",
                "formalphysics synthesis report",
                "synthesize formalphysics judges",
                "synthesize reviewer outcomes",
                "strengths and weaknesses of each approach",
                "judge and reviewer synthesis",
                "formalphysics approach synthesis",
                "compare strengths weaknesses formalphysics",
            ),
            examples=(
                "Build a FormalPhysics synthesis report from the comparative report.",
                "Synthesize the judges and reviewers into strengths and weaknesses for each approach.",
            ),
            operator_note=(
                "The report action defaults to the hub selected-examples comparative report. "
                "Override with extra args: `-- --comparative-report "
                "artifacts/formalphysics_comparative_analysis/RUN/comparative_report.json "
                "--output-dir artifacts/formalphysics_judge_synthesis/RUN "
                "--codex-results-json path/to/results.json --json`."
            ),
        ),
        IntentRoute(
            route_id="report.formalphysics.codex_exec_judges",
            title="Prepare or execute FormalPhysics Codex-exec judge prompts",
            description=(
                "Use when selected FormalPhysics Codex-exec judge prompts should be prepared "
                "or explicitly executed so their completed JSON results can be ingested by "
                "the judge synthesis report."
            ),
            action_ids=(
                "physics-lean:formalphysics-codex-exec-judge-runner-self-test",
                "physics-lean:formalphysics-codex-exec-judge-runner",
            ),
            skill_routes=("formalphysics-judge-synthesis-reporter",),
            positive_terms=(
                "formalphysics codex exec judges",
                "formalphysics codex exec judge prompts",
                "run formalphysics codex judges",
                "run formalphysics codex exec judge prompts",
                "execute formalphysics judge prompts",
                "execute formalphysics codex exec judge prompts",
                "prepare formalphysics codex judge prompts",
                "prepare formalphysics codex exec judge prompts",
                "codex exec judge results",
                "codex exec judge prompts",
                "formalphysics judge result json",
            ),
            examples=(
                "Prepare one FormalPhysics Codex-exec judge prompt.",
                "Run selected FormalPhysics Codex-exec judges and write result JSON.",
            ),
            operator_note=(
                "The runner defaults to a one-prompt dry run. Add extra args such as "
                "`-- --candidate-id current_mathformer_lean --judge-id lean_tp_judge "
                "--limit 3 --execute --resume --workers 2` for real Codex-exec execution."
            ),
        ),
        IntentRoute(
            route_id="formalize.isabelle",
            title="Generate or check Isabelle-facing theories",
            description="Use when the user wants Isabelle/HOL or Isabelle/ZF-facing generated artifacts.",
            action_ids=("isabelle:wiki",),
            skill_routes=(
                "isabelle-autoformalization-drafter",
                "isabelle-execution-runner",
            ),
            positive_terms=(
                "isabelle",
                "isabelle hol",
                "isabelle zf",
                "thy",
                "theory file",
                "isar",
                "isarmathlib",
            ),
            examples=("Check the Isabelle wiki-level theory example.",),
            operator_note="External checks run only when Isabelle is installed.",
        ),
        IntentRoute(
            route_id="formalize.physics.isabelle",
            title="Plan Isabelle physics formalization workflows",
            description=(
                "Use when the user wants physics derivation autoformalization routed through "
                "the Isabelle-facing physics workflow rather than Lean or SymPy."
            ),
            action_ids=("formalphysics:extra-isabelle",),
            skill_routes=(
                "physics-isabelle-workflow-orchestrator",
                "physics-isabelle-derivation-drafter",
            ),
            positive_terms=(
                "physics isabelle",
                "isabelle physics",
                "formalize physics in isabelle",
                "isabelle physics derivation",
                "isabelle physics workflow",
                "formalphysics isabelle",
            ),
            examples=("Plan the Isabelle physics derivation workflow.",),
            operator_note="Runs the controlled Isabelle physics sample workflow.",
        ),
        IntentRoute(
            route_id="source.formalizable.units",
            title="Extract source-grounded formalizable units",
            description="Use when source text, paper text, or Lean/source alignment needs explicit unit packets.",
            action_ids=("test:family:source",),
            skill_routes=(
                "source-formalizable-unit-extractor",
                "source-line-translation-packet-builder",
                "source-formalization-drift-guard",
            ),
            positive_terms=(
                "source formalizable unit",
                "extract formalizable units",
                "source anchors",
                "line translation packet",
                "source to lean drift",
                "source formalization alignment",
                "formalizable source",
            ),
            examples=(
                "Extract source-grounded formalizable units and validate drift guards.",
            ),
            operator_note="Runs the source family in the comprehensive test matrix.",
        ),
        IntentRoute(
            route_id="textbook.autoformalization",
            title="Run textbook autoformalization controls",
            description="Use for LaTeX textbook archive extraction, chapter planning, and batch autoformalization gates.",
            action_ids=("test:family:textbook",),
            skill_routes=(
                "latex-archive-theory-extractor",
                "textbook-theory-tex-organizer",
                "textbook-chapter-autoformalization-orchestrator",
                "textbook-autoformalization-batch-orchestrator",
            ),
            positive_terms=(
                "textbook autoformalization",
                "latex archive",
                "textbook theory",
                "chapter autoformalization",
                "batch autoformalization",
                "tex bundle",
            ),
            examples=("Validate the textbook autoformalization workflow.",),
            operator_note="Runs the textbook family in the comprehensive test matrix.",
        ),
        IntentRoute(
            route_id="validate.physics.lean.backend",
            title="Validate the Lean physics backend",
            description=(
                "Use when the Lean physics loop, controlled FormalPhysics artifact, "
                "adversarial pathology fixtures, generative repair prompts, or recursive "
                "repair expansion controls need an end-to-end deterministic validation."
            ),
            action_ids=("physics-lean:backend-suite",),
            skill_routes=(
                "physics-lean-drift-pathology-monitor",
                "physics-lean-generative-repair-orchestrator",
                "physics-lean-repair-expansion-cartographer",
                "physics-lean-recursive-repair-loop-controller",
            ),
            positive_terms=(
                "validate lean physics backend",
                "lean physics backend suite",
                "full deterministic test family for lean physics",
                "controlled lean physics artifact",
                "adversarial lean fixtures",
                "raw scalar erasure fixture",
                "target as assumption fixture",
                "missing dimensions fixture",
                "missing frame conventions fixture",
                "silent strengthening fixture",
                "run lean physics loop",
            ),
            examples=("Validate the Lean physics backend suite.",),
            operator_note="Writes suite evidence under artifacts/physics_lean/backend_suite/.",
        ),
        IntentRoute(
            route_id="validate.physics.lean.formal_science_grounding_debt",
            title="Gate FormalPhysics Lean grounding before algebraic proof",
            description=(
                "Use when generated FormalPhysics Lean outputs should be checked for "
                "trivial grounding shells, source laws typed as True, local unit/dimension "
                "shims, and missing Hilbert or variational object surfaces."
            ),
            action_ids=("physics-lean:formal-science-grounding-debt",),
            skill_routes=(
                "physics-lean-drift-pathology-monitor",
                "physics-lean-repair-expansion-cartographer",
                "physics-lean-recursive-repair-loop-controller",
            ),
            positive_terms=(
                "ground formalphysics outputs recursively before algebraic proof",
                "formal science grounding debt",
                "formalphysics grounding debt",
                "source laws typed as true",
                "trivial grounding shell",
                "before algebraic proof",
            ),
            examples=(
                "Ground FormalPhysics outputs recursively before algebraic proof.",
            ),
            operator_note="Writes compact gate evidence under artifacts/physics_lean/formal_science_grounding_debt/.",
        ),
        IntentRoute(
            route_id="validate.physics.lean.grounded_samples",
            title="Validate grounded Lean physics samples",
            description=(
                "Use when selected FormalPhysics Lean samples should be checked one by one "
                "against the formalphysics_0014-style standard: MathformerPhysicsLib-first "
                "grounding, required foundation terms, complete autoformalization status, "
                "empty recursive frontier, generative probes, and no shortcut witnesses."
            ),
            action_ids=("physics-lean:grounded-sample-thoroughness",),
            skill_routes=(
                "physics-lean-derivation-completeness-checker",
                "physics-lean-recursive-repair-loop-controller",
                "mathformerphysicslib-mathlib-grounding-auditor",
            ),
            positive_terms=(
                "check selected lean physics samples one by one against 0014",
                "selected lean physics samples",
                "lean physics samples one by one",
                "against 0014",
                "grounded sample thoroughness",
                "make all samples like 0014",
                "same thoroughness as 0014",
                "one sample at a time",
                "formalphysics selected samples",
                "dirac samples grounded direction",
                "recursive frontier empty samples",
            ),
            examples=(
                "Check the selected Lean physics samples one at a time against 0014.",
            ),
            operator_note="Writes sample-level evidence under artifacts/physics_lean/grounded_sample_thoroughness/.",
        ),
        IntentRoute(
            route_id="mathlib.grounding",
            title="Ground formalization work in mathlib",
            description="Use when the request is about finding, validating, or maximizing reuse of existing mathlib objects.",
            action_ids=("test:family:mathlib",),
            skill_routes=(
                "mathlib-result-existence-checker",
                "mathlib-hierarchy-navigator",
                "mathlib-grounding-maximizer",
                "mathlib-import-set-builder",
            ),
            positive_terms=(
                "mathlib grounding",
                "ground in mathlib",
                "existing mathlib object",
                "mathlib first",
                "mathlib reuse",
                "mathlib import",
                "mathlib compatibility",
                "maximal mathlib",
            ),
            examples=("Ground this object in existing mathlib declarations first.",),
            operator_note="Runs the mathlib family in the comprehensive test matrix.",
        ),
        IntentRoute(
            route_id="mathlib.indexing_control",
            title="Build and validate the Mathlib indexing control loop",
            description=(
                "Use when Mathlib source indexing, ontology-backed term expansion, "
                "bounded navigation state, gap-ledger tracking, theorem-shape metadata, "
                "or monotonic regression checks need to run as one controlled workflow."
            ),
            action_ids=("mathlib:indexing-control-suite",),
            skill_routes=(
                "mathlib-index-builder",
                "mathlib-term-expansion-annotator",
                "mathlib-navigation-state-planner",
                "mathlib-concept-ontology-manager",
            ),
            positive_terms=(
                "mathlib indexing control",
                "mathlib index",
                "build mathlib index",
                "term expansion annotator",
                "mathlib term annotations",
                "navigation state planner",
                "bounded mathlib navigation",
                "mathlib gap ledger",
                "monotonic index refinement",
                "declaration graph",
                "theorem shape",
                "import cost scoring",
            ),
            examples=("Validate Mathlib indexing control.",),
            operator_note="Writes index, annotation, navigation, gap, and monotonicity evidence under artifacts/mathlib_index/.",
        ),
        IntentRoute(
            route_id="mathformerlib.accumulation",
            title="Accumulate checked work into MathformerLib",
            description="Use when formalizations should be registered, promoted, or documented in MathformerLib.",
            action_ids=("test:family:mathformerlib",),
            skill_routes=(
                "mathformerlib-accumulation-orchestrator",
                "mathformerlib-registry-manager",
                "mathformerlib-promotion-gate",
                "mathformer-library-docs-generator",
            ),
            positive_terms=(
                "mathformerlib",
                "mathformer library",
                "accumulate into library",
                "promote formalization",
                "library registry",
                "document mathformerlib",
            ),
            examples=(
                "Validate the MathformerLib accumulation and promotion workflow.",
            ),
            operator_note="Runs the MathformerLib family in the comprehensive test matrix.",
        ),
        IntentRoute(
            route_id="mathformerphysicslib.coherence",
            title="Audit MathformerPhysicsLib coherence and grounding",
            description=(
                "Use when MathformerPhysicsLib declarations, canonical concepts, Mathlib grounding, "
                "API operability, critic reports, or coherence repair plans need controlled validation."
            ),
            action_ids=(
                "physics-lib:coherence-suite",
                "physics-lib:coherence-loop-report",
            ),
            skill_routes=(
                "mathformerphysicslib-coherence-inventory-builder",
                "mathformerphysicslib-concept-canonicalizer",
                "mathformerphysicslib-mathlib-grounding-auditor",
                "mathformerphysicslib-redefinition-critic",
                "mathformerphysicslib-integration-critic",
                "mathformerphysicslib-api-operability-critic",
                "mathformerphysicslib-generative-coherence-critic",
                "mathformerphysicslib-coherence-repair-planner",
                "mathformerphysicslib-coherence-gate",
            ),
            positive_terms=(
                "mathformerphysicslib coherence",
                "physics lib coherence",
                "canonical concepts",
                "coherence gate",
                "coherence repair",
                "api operability",
                "mathformerphysicslib grounding",
                "maximally grounded",
                "maximally grounded on mathlib",
                "redefinition critic",
                "not redefining concepts",
                "integration critic",
                "coherent, integrated",
            ),
            examples=("Audit MathformerPhysicsLib coherence and grounding.",),
            operator_note="Runs self-tests plus the report-producing coherence loop under artifacts/mathformerphysicslib/coherence/.",
        ),
        IntentRoute(
            route_id="docs.validate",
            title="Review or validate documentation",
            description="Use when the user changed README, HOWTO, tutorials, install notes, or docs references.",
            action_ids=("test:docs",),
            skill_routes=("mathformer-library-docs-generator",),
            positive_terms=(
                "docs",
                "documentation",
                "readme",
                "howto",
                "tutorial",
                "install guide",
                "license docs",
                "review documentation",
                "changed docs",
            ),
            examples=("Review the documentation and run the doc checks.",),
            operator_note=(
                "Validation writes only declared disposable self-test reports under artifacts/; "
                "it does not edit documentation sources."
            ),
        ),
        IntentRoute(
            route_id="quality.smoke",
            title="Run the compact quality gate",
            description="Use for ordinary development changes when the user wants a broad but practical sanity check.",
            action_ids=("quality:smoke",),
            skill_routes=(
                "workflow-contract-validator",
                "skill-hook-coverage-maximizer",
            ),
            positive_terms=(
                "quality smoke",
                "smoke test",
                "quick quality",
                "compact quality",
                "compact quality gate",
                "ordinary development",
                "sanity check",
                "compact gate",
                "before commit",
            ),
            examples=("Run the compact quality gate before commit.",),
            operator_note="Runs control, quick, docs, Rocq, and KB checks.",
        ),
        IntentRoute(
            route_id="repository.portable-adoption",
            title="Validate portable repository adoption",
            description="Check the four-surface pilot contracts, discovery and legacy compatibility.",
            action_ids=("adoption:check",),
            skill_routes=(
                "workflow-contract-validator",
                "reasoning-log-schema-guardian",
            ),
            positive_terms=(
                "portable repository adoption",
                "portable adoption",
                "adoption compatibility",
            ),
            examples=("Validate portable repository adoption.",),
            operator_note="Uses existing canonical skills; checks never invoke a provider.",
        ),
        IntentRoute(
            route_id="workflow.router",
            title="Audit the natural-language workflow router",
            description=(
                "Use when checking that a generative, Codex-exec, Claude, or OpenCode entrypoint "
                "can reach every distinct Mathformer workflow through natural-language commands."
            ),
            action_ids=("control:workflow-router-coverage",),
            skill_routes=("mathformer-workflow-router",),
            positive_terms=(
                "workflow router",
                "natural language router",
                "router entrypoint",
                "codex exec router",
                "generative router",
                "all distinct workflows",
                "nl workflow coverage",
                "natural language commands",
                "access all workflows",
            ),
            examples=(
                "Check that the router entrypoint covers all distinct workflows using natural language commands.",
            ),
            operator_note="Read-only coverage audit over the hub registry and IntentRoute table.",
        ),
        IntentRoute(
            route_id="control.reasoning.flow.language",
            title="Validate epistemic reasoning flows",
            description=(
                "Use when authoring, importing, migrating, or validating ERFL reasoning-flow "
                "profiles against Mathformer's reasoning and output taxonomies."
            ),
            action_ids=(
                "control:reasoning-flow-language",
                "control:reasoning-flow-catalog",
            ),
            skill_routes=("reasoning-flow-language",),
            positive_terms=(
                "epistemic reasoning flow",
                "reasoning flow language",
                "ERFL",
                "typed reasoning flow",
                "validate reasoning flow",
                "migrate reasoning flow",
                "relational coherence",
            ),
            examples=("Validate the epistemic reasoning-flow profiles.",),
            operator_note="Read-only syntax, coherence, calibration, and registry-alignment validation.",
        ),
        IntentRoute(
            route_id="docs.reasoning.flow.catalog",
            title="Generate reasoning-flow references",
            description=(
                "Use when the canonical semantic catalogue of Mathformer ERFL profiles and "
                "its separate skill-materialization and operational-loop cross-reference "
                "must be generated or refreshed."
            ),
            action_ids=("docs:reasoning-flow-catalog",),
            skill_routes=("reasoning-flow-language",),
            positive_terms=(
                "all reasoning flows",
                "reasoning flow catalog",
                "reasoning flow catalogue",
                "explain repository reasoning flows",
                "document reasoning workflows",
                "workflow explanations",
                "render reasoning flow reference",
            ),
            examples=("Generate the reasoning-flow references with explanations.",),
            operator_note=(
                "Writes docs/architecture/ALL_REASONING_FLOWS.md and "
                "docs/architecture/REASONING_FLOW_MATERIALIZATIONS.md from validated "
                "canonical profiles and registries; allow repository mutation when running it."
            ),
        ),
        IntentRoute(
            route_id="control.reasoning.log.schema",
            title="Validate the reasoning-log schema",
            description="Use when a reasoning-log schema smoke test or strict contract check is requested.",
            action_ids=("control:reasoning-log-smoke",),
            skill_routes=("reasoning-log-schema-guardian",),
            positive_terms=(
                "validate reasoning log schema",
                "reasoning log schema",
                "reasoning-log schema",
                "reasoning log smoke",
                "reasoning-log smoke",
            ),
            examples=("Validate reasoning log schema.",),
            operator_note="Read-only schema smoke test.",
        ),
        IntentRoute(
            route_id="control.reasoning.log.html",
            title="Render a reasoning log as HTML",
            description="Use when a reasoning log should become a self-contained HTML dashboard.",
            action_ids=("control:reasoning-log-html",),
            skill_routes=("reasoning-log-schema-guardian",),
            positive_terms=(
                "render reasoning log as html",
                "reasoning log html",
                "reasoning-log html",
                "html reasoning log",
                "reasoning log dashboard",
            ),
            examples=("Render reasoning log as HTML.",),
            operator_note="Writes a generated HTML dashboard under artifacts/ by default.",
        ),
        IntentRoute(
            route_id="control.reasoning.log.coverage",
            title="Audit reasoning-log coverage for skills",
            description="Use when every skill should have a native, wrapper, or workflow-level reasoning-log path.",
            action_ids=("control:reasoning-log-coverage",),
            skill_routes=("reasoning-log-schema-guardian",),
            positive_terms=(
                "make sure skills have reasoning logs",
                "reasoning log coverage",
                "skills have reasoning logs",
                "audit skill reasoning logs",
            ),
            examples=("Make sure skills have reasoning logs.",),
            operator_note="Read-only coverage audit over skills and scripts.",
        ),
        IntentRoute(
            route_id="control.reasoning.log.quality",
            title="Audit reasoning-log quality",
            description="Use when reasoning logs need the consumer-grade quality and redaction policy.",
            action_ids=("control:reasoning-log-quality",),
            skill_routes=("reasoning-log-schema-guardian",),
            positive_terms=(
                "audit reasoning log quality",
                "reasoning log quality",
                "consumer-grade reasoning log",
                "reasoning log redaction",
                "reasoning log security",
            ),
            examples=("Audit reasoning log quality.",),
            operator_note="Read-only consumer-grade quality audit over deterministic fixtures.",
        ),
        IntentRoute(
            route_id="control.reasoning.log.summary",
            title="Summarize reasoning logs for consumer applications",
            description="Use when a UI, MCP client, or review workflow needs compact structured reasoning-log fields.",
            action_ids=("control:reasoning-log-summary",),
            skill_routes=("reasoning-log-schema-guardian",),
            positive_terms=(
                "summarize reasoning log",
                "summarize reasoning log for a consumer application",
                "consumer application reasoning log",
                "machine readable reasoning log summary",
                "reasoning log summary",
            ),
            examples=("Summarize reasoning log for a consumer application.",),
            operator_note="Read-only JSON summary; pass a log path via extra args for a specific log.",
        ),
        IntentRoute(
            route_id="control.reasoning.logs",
            title="Validate and expose reasoning logs for consumers",
            description=(
                "Use when reasoning logs need the full consumer-readiness suite: schema, coverage, quality, "
                "machine-readable summaries, stable index generation, and MCP-facing resource readiness."
            ),
            action_ids=("control:reasoning-log-consumer-readiness",),
            skill_routes=(
                "reasoning-log-schema-guardian",
                "mathformer-workflow-router",
            ),
            positive_terms=(
                "reasoning log consumer readiness",
                "reasoning logs consumer readiness",
                "reasoning log index",
                "reasoning-log discovery",
                "mcp reasoning log",
                "expose reasoning logs through mcp",
                "reasoning log consumer workflow",
            ),
            examples=("Run the reasoning-log consumer-readiness checks.",),
            operator_note="Writes generated consumer summaries and the stable reasoning-log index under artifacts/reasoning/.",
        ),
        IntentRoute(
            route_id="meta.skills.help",
            title="Show and validate meta-skill workflows",
            description=(
                "Use when the user asks what meta-skills do, how visible workflow registries, "
                "quality cards, runtime traces, taxonomy navigation, generated skill promotion, "
                "or MCP workflow boundaries are organized."
            ),
            action_ids=("meta-skills:validate",),
            skill_routes=("mathformer-workflow-router",),
            positive_terms=(
                "meta skill",
                "meta-skills",
                "meta skills",
                "show meta-skill workflows",
                "show meta skill workflows",
                "validate meta-skills",
                "validate meta skills",
                "generated skill promotion",
                "quality cards",
                "task registry",
                "visible workflow registry",
                "runtime trace",
                "taxonomy navigation",
                "workflow evolution",
                "mcp boundary",
                "looper integration",
            ),
            examples=(
                "Show meta-skill workflows.",
                "Validate meta-skills.",
                "Explain generated skill promotion.",
            ),
            operator_note="Runs the compact standard-library meta-skill validation suite and writes reports under artifacts/meta_skills/.",
        ),
        IntentRoute(
            route_id="review.autoformalization.framework",
            title="Review or improve the autoformalization framework",
            description=(
                "Use for cross-cutting architecture reviews or implementation of the "
                "autoformalization review backlog, with explicit PhysicsLib release evidence."
            ),
            action_ids=("review:autoformalization-framework",),
            skill_routes=(
                "mathformer-workflow-router",
                "mathformerphysicslib-coherence-gate",
            ),
            positive_terms=(
                "autoformalization framework review",
                "review autoformalization framework",
                "implement autoformalization framework review todos",
                "implement the autoformalization framework review todos",
                "full review autoformalization",
                "particular emphasis on physics",
                "physics autoformalization review",
            ),
            examples=(
                "Review the full autoformalization framework with particular emphasis on physics.",
                "Implement the autoformalization framework review TODOs.",
            ),
            operator_note=(
                "Runs controlled workflow, documentation, and promoted PhysicsLib release gates; "
                "implementation changes still require an agent or developer working from the reviewed backlog."
            ),
        ),
        IntentRoute(
            route_id="quality.strict",
            title="Run the capability-complete strict quality gate",
            description="Use for release validation where skipped or unavailable capabilities must fail.",
            action_ids=("quality:strict",),
            skill_routes=(
                "workflow-contract-validator",
                "skill-test-program-orchestrator",
            ),
            positive_terms=(
                "strict quality",
                "capability complete",
                "no skipped tests",
                "strict release gate",
                "fail unavailable capabilities",
            ),
            examples=("Run the strict capability-complete quality gate.",),
            operator_note="Fails when any selected capability is skipped, unavailable, or untested.",
        ),
        IntentRoute(
            route_id="quality.full",
            title="Run the full repository quality gate",
            description="Use when the user wants the broadest local validation available from the hub.",
            action_ids=("quality:full",),
            skill_routes=(
                "workflow-contract-validator",
                "skill-test-program-orchestrator",
            ),
            positive_terms=(
                "quality full",
                "full quality",
                "broad check",
                "full validation",
                "comprehensive",
                "complete test",
                "all tests",
            ),
            examples=("Run the full repository quality gate.",),
            operator_note="Can take longer because it invokes the comprehensive matrix.",
        ),
        IntentRoute(
            route_id="control.audit",
            title="Audit workflow control coverage",
            description="Use after adding or moving scripts, skills, tests, examples, or workflow code.",
            action_ids=("control:all",),
            skill_routes=(
                "workflow-contract-validator",
                "skill-hook-coverage-maximizer",
            ),
            positive_terms=(
                "control audit",
                "workflow control",
                "workflow is controlled",
                "workflow controlled",
                "every workflow",
                "uncontrolled scripts",
                "skill hook",
                "hook contract",
                "new workflow",
                "added script",
                "controlled actions",
            ),
            examples=("Audit that all workflow entrypoints are controlled.",),
            operator_note="Read-only control checks; git diff checks require a git checkout.",
        ),
        IntentRoute(
            route_id="paper.workflow",
            title="Run paper evidence and update workflows",
            description="Use when the paper evidence packet, claim audit, functionality update, or theory-evolution figures need validation.",
            action_ids=("paper:functionality-update-suite", "paper:workflow-catalog"),
            skill_routes=(
                "paper-theory-autoformalization-orchestrator",
                "paper-docling-layout-extractor",
            ),
            positive_terms=(
                "paper workflow",
                "paper evidence",
                "claim audit",
                "functionality update",
                "mechanistic diagram",
                "theory evolution",
                "paper update suite",
            ),
            examples=("Run the paper functionality update suite.",),
            operator_note="Runs controlled paper update checks and may write paper artifacts when invoked directly.",
        ),
        IntentRoute(
            route_id="workflow.graphs",
            title="Render and audit workflow graph reports",
            description="Use when the request asks for workflow graph layout, rendering, catalogue, or skill-integration reports.",
            action_ids=(
                "docs:workflow-graph-render",
                "docs:workflow-graph-layout",
                "control:workflow-skill-integration-audit",
            ),
            skill_routes=("mathformer-workflow-router",),
            positive_terms=(
                "workflow graph",
                "workflow graphs",
                "workflow layout",
                "workflow graph render",
                "workflow catalog",
                "workflow catalogue",
                "skill integration audit",
                "agentic workflow graph",
            ),
            examples=("Render the workflow graphs and audit skill integration.",),
            operator_note="Writes workflow graph reports under artifacts/workflow_graphs/.",
        ),
        IntentRoute(
            route_id="benchmark.workflow",
            title="Run benchmark workflows",
            description="Use when the request names ProofNet, benchmark export, or benchmark evaluation.",
            action_ids=("benchmark:proofnet",),
            skill_routes=("proofnet-benchmark-runner",),
            positive_terms=(
                "benchmark",
                "proofnet",
                "benchmark workflow",
                "benchmark evaluation",
                "formal science benchmark",
                "export proofnet",
            ),
            examples=("Run the ProofNet benchmark workflow.",),
            operator_note="Uses benchmark-specific controlled actions.",
        ),
        IntentRoute(
            route_id="generative.probes",
            title="Run generative skill and content probes",
            description="Use when Codex-exec or content-generative skills need deterministic test harness coverage.",
            action_ids=("test:generative",),
            skill_routes=("skill-test-program-orchestrator",),
            positive_terms=(
                "generative probe",
                "generative skill",
                "codex exec probe",
                "content skill",
                "content generative",
                "generative tests",
            ),
            examples=("Run the generative skill probes.",),
            operator_note="Runs deterministic coverage for generative/content skill behavior.",
        ),
        IntentRoute(
            route_id="prism.native-semantic-parallel-e2e",
            title="Run native parallel semantic PRISM validation",
            description=(
                "Use when the PRISM projections need full end-to-end execution with the native "
                "Codex handler, bounded semantic safety oracles, and four parallel PRISM processes."
            ),
            action_ids=("prism:native-semantic-parallel-e2e",),
            skill_routes=("mathformer-workflow-router",),
            positive_terms=(
                "prism native semantic parallel",
                "prism native parallel semantic",
                "prism native end to end",
                "prism semantic end to end",
                "prism parallel end to end",
                "native prism validation",
                "native handler prism",
                "semantic prism validation",
                "parallel prism validation",
                "full prism validation",
                "prism e2e",
            ),
            examples=(
                "Run the full PRISM native parallel semantic end-to-end validation.",
            ),
            operator_note=(
                "Runs four native Codex workers and writes the checked report to "
                "mathformer-prism/tests/native-semantic-parallel-e2e.json; repository mutation permission is required."
            ),
        ),
        IntentRoute(
            route_id="e2e.all.backends",
            title="Run all backend end-to-end workflows",
            description="Use when the request asks for end-to-end validation across Lean, ATP, KB, SymPy, Rocq, Isabelle, or related backends.",
            action_ids=("e2e:all-backends",),
            skill_routes=("skill-test-program-orchestrator",),
            positive_terms=(
                "end to end",
                "e2e",
                "all backends",
                "backend e2e",
                "full backend",
                "cross backend",
            ),
            examples=("Run all backend end-to-end workflows.",),
            operator_note="Runs the registered e2e backend action.",
        ),
        IntentRoute(
            route_id="environment.validate",
            title="Validate environment and dependency probes",
            description="Use when checking installation assumptions, dependency maps, optional tools, or environment readiness.",
            action_ids=("test:family:environment",),
            skill_routes=("skill-test-program-orchestrator",),
            positive_terms=(
                "environment",
                "dependency map",
                "dependencies",
                "installation readiness",
                "optional tools",
                "environment validation",
            ),
            examples=("Validate the environment dependency map.",),
            operator_note="Runs the environment family in the comprehensive test matrix.",
        ),
        IntentRoute(
            route_id="licenses.inventory",
            title="Build or validate the license inventory",
            description="Use when repository license metadata, SPDX headers, or license inventory artifacts need checking.",
            action_ids=("licenses:inventory",),
            skill_routes=(),
            positive_terms=(
                "license",
                "licenses",
                "license inventory",
                "spdx",
                "copyright",
                "legal metadata",
            ),
            examples=("Build the license inventory.",),
            operator_note="Runs the controlled license inventory action.",
        ),
        IntentRoute(
            route_id="rfde.evaluate",
            title="Run reference-free descriptive evaluation",
            description="Use when the request asks for RFDE, reference-free evaluation, or process-trajectory reports.",
            action_ids=("test:family:rfde",),
            skill_routes=(
                "reference-free-critic-monitor",
                "reference-free-descriptive-evaluator",
            ),
            positive_terms=(
                "rfde",
                "reference free",
                "descriptive evaluator",
                "critic monitor",
                "trajectory report",
                "process evaluation",
            ),
            examples=("Run the RFDE reference-free evaluation family.",),
            operator_note="Runs the RFDE family in the comprehensive test matrix.",
        ),
        IntentRoute(
            route_id="agentc.analyze",
            title="Analyze AgentC logs",
            description="Use when the request asks to inspect or summarize AgentC autoformalization traces.",
            action_ids=("agentc:analyze-logs",),
            skill_routes=("autoformalization-agentc",),
            positive_terms=(
                "agentc",
                "agentc logs",
                "analyze agentic logs",
                "agent trace",
                "autoformalization logs",
            ),
            examples=("Analyze the AgentC logs.",),
            operator_note="Runs the AgentC log analyzer.",
        ),
        IntentRoute(
            route_id="test.runner",
            title="Run the general test matrix",
            description="Use for quick, slow, comprehensive, or backend-oriented test runs.",
            action_ids=("test:quick",),
            skill_routes=("skill-test-program-orchestrator",),
            positive_terms=(
                "run tests",
                "test runner",
                "quick tests",
                "slow tests",
                "comprehensive tests",
                "test matrix",
                "pytest",
            ),
            examples=("Run the quick test matrix.",),
            operator_note="Selects the quick test action; ask for full quality or e2e for broader gates.",
        ),
        IntentRoute(
            route_id="setup.full",
            title="Set up the full local development environment",
            description="Use when the user wants all local profiles installed or refreshed.",
            action_ids=("setup:all",),
            skill_routes=(),
            positive_terms=(
                "setup all",
                "set up all",
                "install all",
                "full setup",
                "set up full",
                "full local development",
                "development environment",
                "fresh checkout",
                "install project",
            ),
            examples=("Set up the full local development environment.",),
            operator_note="Requires mutation permission because it can write .venv/ and .lake/.",
        ),
        IntentRoute(
            route_id="control.thematic.layout",
            title="Validate the thematic repository layout",
            description=(
                "Use after organizing backend components, libraries, skills, scripts, tests, "
                "or documentation into canonical thematic folders."
            ),
            action_ids=("control:thematic-layout",),
            skill_routes=(
                "mathformer-generative-workflow-coordinator",
                "mathformer-workflow-router",
            ),
            positive_terms=(
                "organize backends",
                "organize backend components",
                "organize mathformer directories",
                "aggregate mathformer components",
                "move mathformer folders",
                "mathformer atp folder",
                "mathformer sympy physics folder",
                "isabelle folder",
                "organize root lean files",
                "move root lean files",
                "lean files at repository root",
                "organize skills",
                "organize scripts",
                "organize tests",
                "organize docs",
                "thematic folders",
                "thematic layout",
                "repository layout",
                "navigation folders",
            ),
            examples=(
                "Validate the thematic folders for skills, tests, scripts, and docs.",
                "Organize Isabelle, MathformerATP, MathformerKB, and MathformerSympyPhysics into aggregate folders.",
                "Move the Lean files at the repository root into the Lean backend folder.",
            ),
            operator_note=(
                "Read-only validation. Physical component moves require an authorized repository edit; "
                "--apply only creates or repairs managed script and test views."
            ),
        ),
        IntentRoute(
            route_id="setup.atp.kb",
            title="Set up the ATP and premise-KB profile",
            description="Use when the user only needs Vampire ATP and premise-KB Python tooling.",
            action_ids=("setup:atp-kb",),
            skill_routes=(),
            positive_terms=(
                "setup atp",
                "set up atp",
                "setup kb",
                "set up kb",
                "install atp",
                "install kb",
                "atp kb profile",
                "atp and premise kb",
                "premise kb profile",
                "premise kb setup",
            ),
            examples=("Install the ATP and premise-KB profile.",),
            operator_note="Requires mutation permission because it can write .venv/.",
        ),
        IntentRoute(
            route_id="setup.python.all",
            title="Install all Python extras without Lean setup",
            description="Use when the user wants benchmarks, SymPy workflows, PDF extraction, and Python-only extras.",
            action_ids=("setup:python-all",),
            skill_routes=(),
            positive_terms=(
                "python extras",
                "all python extras",
                "install all python",
                "python only",
                "python all",
                "sympy workflows",
                "benchmark extras",
                "pdf extraction",
            ),
            examples=("Install all Python extras without running Lean setup.",),
            operator_note="Requires mutation permission because it can write .venv/.",
        ),
        IntentRoute(
            route_id="setup.lean",
            title="Set up the Lean profile",
            description="Use when the user only needs Lean/Lake-facing environment setup.",
            action_ids=("setup:lean",),
            skill_routes=(),
            positive_terms=(
                "setup lean",
                "set up lean",
                "install lean",
                "lean setup",
                "lean environment",
                "lake setup",
                "mathlib setup",
            ),
            examples=("Set up the Lean environment profile.",),
            operator_note="Requires mutation permission because it can write .lake/.",
        ),
        IntentRoute(
            route_id="skills.plugin-check",
            title="Validate Mathformer agent plugins",
            description="Check Codex and Claude plugin packaging and canonical skill parity.",
            action_ids=("skills:plugin-check", "skills:plugin-test"),
            skill_routes=(),
            positive_terms=(
                "validate agent plugins",
                "check agent plugins",
                "validate plugin packaging",
            ),
            examples=("Validate agent plugins.",),
        ),
        IntentRoute(
            route_id="skills.plugin-sync",
            title="Regenerate Mathformer agent plugins",
            description="Update plugin discovery surfaces after editing canonical skills.",
            action_ids=("skills:plugin-sync", "skills:plugin-check"),
            skill_routes=(),
            positive_terms=(
                "sync agent plugins",
                "regenerate agent plugins",
                "update plugin packaging",
            ),
            examples=("Regenerate agent plugins.",),
            operator_note="Writes the generated plugin and marketplace files.",
        ),
        IntentRoute(
            route_id="skills.link",
            title="Publish Mathformer skills to local agent clients",
            description="Use when VS Code, Codex, Claude Code, or OpenCode should see the repository skills.",
            action_ids=("skills:link", "skills:client-discovery"),
            skill_routes=(),
            positive_terms=(
                "link skills",
                "publish skills",
                "agent skills",
                "vscode",
                "codex",
                "claude code",
                "opencode",
                "agent client",
            ),
            examples=(
                "Make the Mathformer skills available to VS Code and agent clients.",
            ),
            operator_note="Requires mutation permission because it writes client skill folders.",
        ),
        IntentRoute(
            route_id="mcp.independent.service",
            title="Validate the independent whole-pipeline MCP service",
            description=(
                "Use when deploying Mathformer as an independent MCP service with service-local "
                "config, dependency closure, auth policy, and external API keys under config/."
            ),
            action_ids=(
                "mcp:service-config",
                "mcp:service-dependencies",
                "mcp:service-self-check",
            ),
            skill_routes=("mathformer-workflow-router",),
            positive_terms=(
                "independent mcp service",
                "whole pipeline mcp service",
                "mcp service dependencies",
                "service config",
                "external api keys",
                "config folder",
                "deploy mcp service",
                "validate independent mcp",
                "mcp service self check",
            ),
            examples=("Validate the independent MCP service deployment profile.",),
            operator_note="Read-only checks over service config, dependency probes, router coverage, and hub audit.",
        ),
        IntentRoute(
            route_id="mcp.serve",
            title="Start the Mathformer MCP server",
            description="Use when the user wants to expose Mathformer to an MCP client such as Claude Desktop, Claude Code, or another MCP-aware agent.",
            action_ids=("mcp:serve",),
            skill_routes=(),
            positive_terms=(
                "mcp server",
                "mcp",
                "model context protocol",
                "start mcp",
                "deploy mcp",
                "expose mathformer",
                "mcp client",
                "claude desktop",
            ),
            examples=("Start the Mathformer MCP server.",),
            operator_note=(
                "Discoverable here for cataloguing; in practice configure the MCP "
                "client to launch `python3 scripts/mcp_server.py` directly. See "
                "docs/architecture/MCP_SERVER.md for client configuration examples."
            ),
        ),
    )


def normalize_intent_text(text: str) -> str:
    """Normalize natural-language text for deterministic route matching.

    Motivation:
        Keep the NL interface dependency-free, transparent, and portable.

    Intent:
        Lowercase text and collapse punctuation so phrase matching is stable
        across casual user wording.

    Inputs:
        The raw user request.

    Outputs:
        A normalized string with single-space separators.
    """

    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def score_intent_route(
    normalized_query: str, route: IntentRoute
) -> Tuple[int, Tuple[str, ...]]:
    """Score how well one route matches a normalized request.

    Motivation:
        Make NL routing explainable and deterministic without calling a model.

    Intent:
        Award points for matched words and extra points for matched phrases,
        then return the evidence terms used for the score.

    Inputs:
        The normalized request text and a candidate route.

    Outputs:
        A nonnegative score and the original route terms that matched.
    """

    tokens = set(normalized_query.split())
    score = 0
    matched: List[str] = []
    for example in route.examples:
        if normalized_query == normalize_intent_text(example):
            score += 100
            matched.append(f"documented example: {example}")
    for term in route.positive_terms:
        normalized_term = normalize_intent_text(term)
        if not normalized_term:
            continue
        term_tokens = normalized_term.split()
        if len(term_tokens) == 1:
            if normalized_term in tokens:
                score += 2
                matched.append(term)
        elif normalized_term in normalized_query:
            score += 4 + min(4, len(term_tokens))
            matched.append(term)
    return score, tuple(matched)


def resolve_intent(
    request: str,
    registry: Mapping[str, WorkflowAction],
    *,
    limit: int = 5,
    family: Optional[str] = None,
) -> List[IntentMatch]:
    """Resolve a natural-language request into candidate workflow routes.

    Motivation:
        Let agents and humans express outcomes first while still landing on
        audited action ids.

    Intent:
        Match the request against a curated route table, filter by optional
        action family, drop routes whose actions are not registered, and return
        the best scored candidates.

    Inputs:
        A raw request string, the action registry, and optional limit/family
        filters.

    Outputs:
        A score-sorted list of `IntentMatch` records.
    """

    normalized_query = normalize_intent_text(request)
    matches: List[IntentMatch] = []
    for route in build_intent_routes():
        if any(action_id not in registry for action_id in route.action_ids):
            continue
        if family and not any(
            registry[action_id].family == family for action_id in route.action_ids
        ):
            continue
        score, matched_terms = score_intent_route(normalized_query, route)
        if score > 0:
            matches.append(
                IntentMatch(route=route, score=score, matched_terms=matched_terms)
            )
    matches.sort(key=lambda item: (-item.score, item.route.route_id))
    return matches[: max(1, limit)]


def intent_match_to_dict(
    match: IntentMatch, registry: Mapping[str, WorkflowAction]
) -> Dict[str, Any]:
    """Serialize an intent match for human and machine-readable output.

    Motivation:
        Make the NL interface auditable by showing the route, score, matched
        terms, skill owners, and controlled actions.

    Intent:
        Convert an `IntentMatch` into a stable JSON-compatible structure.

    Inputs:
        The match and action registry used to enrich action metadata.

    Outputs:
        A dictionary describing the route and recommended controlled actions.
    """

    route = match.route
    actions = [registry[action_id] for action_id in route.action_ids]
    return {
        "route_id": route.route_id,
        "title": route.title,
        "description": route.description,
        "score": match.score,
        "matched_terms": list(match.matched_terms),
        "skill_routes": list(route.skill_routes),
        "examples": list(route.examples),
        "operator_note": route.operator_note,
        "recommended_actions": [
            {
                "id": item.action_id,
                "summary": item.summary,
                "family": item.family,
                "kind": item.kind,
                "safety": item.safety,
                "writes": list(item.writes),
            }
            for item in actions
        ],
    }


def build_intent_payload(
    request: str,
    registry: Mapping[str, WorkflowAction],
    *,
    limit: int,
    family: Optional[str],
) -> Dict[str, Any]:
    """Build a complete natural-language routing payload.

    Motivation:
        Give VS Code adapters, agents, and humans one stable response shape for
        NL requests.

    Intent:
        Resolve the request, serialize matches, and include a clear fallback
        message when no route is confident enough to recommend.

    Inputs:
        Raw request text, registry, maximum number of matches, and family filter.

    Outputs:
        A JSON-compatible payload with route recommendations.
    """

    matches = resolve_intent(request, registry, limit=limit, family=family)
    payload: Dict[str, Any] = {
        "schema_version": 1,
        "ok": bool(matches),
        "request": request,
        "interface": "natural_language",
        "matches": [intent_match_to_dict(match, registry) for match in matches],
    }
    if not matches:
        payload["message"] = (
            "No controlled workflow route matched this request. Rephrase with the desired outcome, "
            "backend, or artifact type, or inspect the workflow catalogue."
        )
    return payload


def print_human_intent_payload(payload: Mapping[str, Any]) -> None:
    """Print a natural-language routing result for terminal readers.

    Motivation:
        Keep the `ask` interface usable without requiring JSON tooling.

    Intent:
        Present the recommended route, matched evidence, skill owners, and
        controlled actions in prose-first form.

    Inputs:
        The payload produced by `build_intent_payload`.

    Outputs:
        Writes a concise human-readable explanation to stdout.
    """

    print(f"Request: {payload.get('request', '')}")
    matches = payload.get("matches", [])
    if not matches:
        print(payload.get("message", "No route matched."))
        return
    for index, match in enumerate(matches, start=1):
        print(f"\n{index}. {match['title']}")
        print(f"   {match['description']}")
        if match.get("matched_terms"):
            print(f"   Matched: {', '.join(match['matched_terms'])}")
        if match.get("skill_routes"):
            print(f"   Agent route: {', '.join(match['skill_routes'])}")
        action_bits = [
            f"{item['id']} ({item['safety']})"
            for item in match.get("recommended_actions", [])
        ]
        print(f"   Controlled action: {', '.join(action_bits)}")
        if match.get("operator_note"):
            print(f"   Note: {match['operator_note']}")


def run_intent_match(
    match: IntentMatch,
    registry: Mapping[str, WorkflowAction],
    context: RunContext,
    *,
    repository_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute the controlled action sequence selected by an NL route.

    Motivation:
        Allow NL requests to drive workflows without bypassing safety checks.

    Intent:
        Run only registered action ids from the selected route and reuse the
        existing execution engine for preflight, dry-run, and mutation policy.

    Inputs:
        The selected match, action registry, and run context.

    Outputs:
        A result dictionary containing one child result per action.
    """

    state = initialize_intent_state()
    mount = {} if repository_root is None else {"repository_root": repository_root}
    for _action_id in match.route.action_ids:
        action_id = select_intent_action(state, match)
        child = run_action(action_id, registry, context, **mount)
        state, done = advance_intent_state(
            state, child, context, len(match.route.action_ids)
        )
        if done:
            break
    return finish_intent_state(state, match, registry)


def initialize_intent_state():
    """Initialize the native ordered route accumulator without retained history."""
    return {"ok": True, "children": []}


def select_intent_action(state, match):
    """Select the next native route item from its ordered observation history."""
    return match.route.action_ids[len(state["children"])]


def advance_intent_state(state, child, context, action_count):
    """Append in route order; failure remains sticky even under keep-going."""
    updated = {
        "ok": state["ok"] and bool(child.get("ok", False)),
        "children": [*state["children"], child],
    }
    done = len(updated["children"]) == action_count or (
        not child.get("ok", False) and not context.keep_going
    )
    return updated, done


def finish_intent_state(state, match, registry):
    """Pack the source-owned route metadata and ordered child observations."""
    return {
        "schema_version": 1,
        "ok": state["ok"],
        "status": "intent_run_completed" if state["ok"] else "intent_run_failed",
        "route": intent_match_to_dict(match, registry),
        "children": state["children"],
    }


def resolve_command(command: Sequence[str]) -> List[str]:
    """Resolve hub command placeholders into executable argv.

    Motivation:
        Keep registered commands portable across operating systems and Python
        launcher conventions.

    Intent:
        Replace `{python}` with `sys.executable` and leave every other argv
        token untouched.

    Inputs:
        A command tuple from an action declaration.

    Outputs:
        A list suitable for `subprocess.run`.
    """

    return [sys.executable if part == PYTHON_TOKEN else part for part in command]


def path_exists(repo_relative: str) -> bool:
    """Check whether a declared repository path exists.

    Motivation:
        Fail clearly before launching a workflow with missing local inputs.

    Intent:
        Treat path declarations as repository-relative contracts.

    Inputs:
        A path string from action metadata.

    Outputs:
        `True` when the path exists in the checkout.
    """

    return (REPO_ROOT / repo_relative).exists()


def preflight(
    item: WorkflowAction,
    context: RunContext,
    extra_args: Sequence[str],
    *,
    repository_root=None,
) -> List[str]:
    """Return blocking preflight errors for an action.

    Motivation:
        Catch uncontrolled or impossible execution before subprocess launch.

    Intent:
        Enforce required paths, required tools, extra-argument policy, and
        explicit permission for environment or repository mutations.

    Inputs:
        The action, user execution context, and pass-through arguments.

    Outputs:
        A list of human-readable blocking errors.
    """

    errors: List[str] = []
    if extra_args and not item.allows_extra_args:
        errors.append(f"{item.action_id} does not accept extra arguments")
    for repo_path in item.required_paths:
        if not (
            path_exists(repo_path)
            if repository_root is None
            else (Path(repository_root) / repo_path).exists()
        ):
            errors.append(f"missing required path: {repo_path}")
    for tool in item.required_tools:
        if shutil.which(tool) is None:
            errors.append(f"missing required tool on PATH: {tool}")
    if item.safety in {"writes_repo", "writes_environment"} and not (
        context.allow_mutating or context.dry_run
    ):
        errors.append(
            f"{item.action_id} has safety={item.safety}; rerun with --allow-mutating or --dry-run"
        )
    return errors


def print_human_action_list(actions: Iterable[WorkflowAction]) -> None:
    """Print a compact human-readable action list.

    Motivation:
        Make `list` useful from a terminal without requiring JSON tooling.

    Intent:
        Show the id, family, safety, and one-line purpose for each action.

    Inputs:
        The actions selected by filters.

    Outputs:
        Writes a table-like text listing to stdout.
    """

    for item in actions:
        print(f"{item.action_id:34} {item.family:15} {item.safety:18} {item.summary}")


def write_report(action_id: str, payload: Mapping[str, Any]) -> Path:
    """Write an execution report under ignored artifacts.

    Motivation:
        Preserve evidence from hub-controlled workflows without polluting the
        tracked source tree.

    Intent:
        Store JSON reports in a stable location for later inspection.

    Inputs:
        The action id and JSON-compatible payload.

    Outputs:
        The path of the written report.
    """

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", action_id)
    path = REPORT_DIR / f"{safe_id}.json"
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def append_hub_start(
    log_file: Optional[Path], *, mode: str, target: str, dry_run: bool
) -> Optional[str]:
    """Start a compact hub-level reasoning-log event when requested."""
    if log_file is None:
        return None
    return append_skill_start(
        log_file,
        skill="mathformer-hub",
        intent="Run a controlled Mathformer hub action or natural-language route.",
        inputs={"mode": mode, "target": target, "dry_run": dry_run},
        artifacts={},
        human_summary=f"Started Mathformer hub {mode} for `{target}`.",
    )


def append_hub_complete(
    log_file: Optional[Path],
    *,
    skill_call_id: Optional[str],
    mode: str,
    target: str,
    payload: Mapping[str, Any],
    report_file: Optional[str] = None,
) -> None:
    """Complete a compact hub-level reasoning-log event when requested."""
    if log_file is None or skill_call_id is None:
        return
    ok = bool(payload.get("ok"))
    artifacts = {"report_file": report_file} if report_file else {}
    evidence = {
        "mode": mode,
        "target": target,
        "ok": ok,
        "status": payload.get("status"),
        "selected_route_id": payload.get("selected_route_id"),
    }
    if ok:
        append_skill_complete(
            log_file,
            skill="mathformer-hub",
            skill_call_id=skill_call_id,
            intent="Run a controlled Mathformer hub action or natural-language route.",
            inputs={"mode": mode, "target": target},
            artifacts=artifacts,
            evidence=evidence,
            decision={"status": "pass"},
            risks={},
            next_action="Inspect child workflow reports or produced artifacts if needed.",
            human_summary=f"Completed Mathformer hub {mode} for `{target}`.",
        )
    else:
        append_skill_error(
            log_file,
            skill="mathformer-hub",
            skill_call_id=skill_call_id,
            intent="Run a controlled Mathformer hub action or natural-language route.",
            inputs={"mode": mode, "target": target},
            artifacts=artifacts,
            evidence=evidence,
            risks={
                "status": payload.get("status"),
                "preflight_errors": payload.get("preflight_errors", []),
            },
            next_action="Inspect the hub payload and rerun with corrected action, permissions, or dependencies.",
            error=str(payload.get("status", "hub action failed")),
        )


def run_leaf_action(
    item: WorkflowAction,
    context: RunContext,
    extra_args: Sequence[str],
    *,
    repository_root=None,
) -> Dict[str, Any]:
    """Run one non-composed action.

    Motivation:
        Centralize subprocess behavior so every workflow has the same dry-run,
        preflight, report, and output semantics.

    Intent:
        Execute only the argv declared by the registry, plus explicitly allowed
        extra args, without invoking a shell.

    Inputs:
        A leaf `WorkflowAction`, runtime context, and optional pass-through args.

    Outputs:
        A result dictionary containing command, exit code, output, and status.
    """

    mount = {} if repository_root is None else {"repository_root": repository_root}
    boundary = prepare_leaf_boundary(item, context, extra_args, **mount)
    payload = boundary["payload"]
    if not boundary["execute"]:
        return payload
    payload = launch_leaf_boundary(item, payload, **mount)
    return finish_leaf_boundary(item, boundary, payload, **mount)


def complete_leaf_boundary(payload, returncode, stdout, stderr):
    """Pack native captured process output for one-shot and staged callers."""
    payload.update(
        status="completed",
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        ok=returncode == 0,
    )
    return payload


def launch_leaf_boundary(item, payload, *, repository_root=None, environment=None):
    """Shared one-shot subprocess boundary; unexpected launch errors propagate."""
    command = payload["argv"]
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT if repository_root is None else repository_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=item.timeout_seconds,
            **({} if environment is None else {"env": environment}),
        )
        complete_leaf_boundary(payload, result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired as exc:
        payload.update(
            {
                "status": "timeout",
                "returncode": None,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "ok": False,
                "timeout_seconds": item.timeout_seconds,
            }
        )
    return payload


def prepare_leaf_boundary(item, context, extra_args, *, repository_root=None):
    """Shared preflight and before-snapshot; staged callers may supply their mount.

    Registry admission/argv remain project-owned. Ordinary CLI callers retain
    the repository default; in-process adapters pass their explicit filesystem
    context to both snapshot boundaries.
    """
    errors = preflight(item, context, extra_args, repository_root=repository_root)
    command = resolve_command(item.command) + list(extra_args)
    payload: Dict[str, Any] = {
        "action": action_to_dict(item),
        "argv": command,
        "cwd": rel(REPO_ROOT if repository_root is None else repository_root),
        "dry_run": context.dry_run,
        "ok": not errors,
        "preflight_errors": errors,
    }
    if errors:
        return {"execute": False, "payload": payload, "snapshot": {}}
    if context.dry_run:
        payload["status"] = "dry_run"
        return {"execute": False, "payload": payload, "snapshot": {}}

    return {
        "execute": True,
        "payload": payload,
        "snapshot": snapshot_repository(
            REPO_ROOT if repository_root is None else repository_root
        ),
    }


def finish_leaf_boundary(item, boundary, payload, *, repository_root=None):
    """Audit the same repository mount used by prepare_leaf_boundary."""
    payload = dict(payload)
    after_snapshot = snapshot_repository(
        REPO_ROOT if repository_root is None else repository_root
    )
    write_audit = audit_snapshots(
        boundary["snapshot"],
        after_snapshot,
        action_id=item.action_id,
        safety=item.safety,
        declared_roots=item.writes,
    )
    payload["write_audit"] = write_audit
    if not write_audit["ok"]:
        payload["ok"] = False
        payload["status"] = "undeclared_writes"
        unexpected = ", ".join(write_audit["unexpected_paths"])
        message = (
            f"action {item.action_id} wrote outside its declared roots "
            f"{list(item.writes)}: {unexpected}"
        )
        payload["stderr"] = "\n".join(
            part for part in (payload.get("stderr", ""), message) if part
        )
    return payload


def admit_action(action_id, registry, extra_args=(), seen=None):
    """Apply native entry guards in order, copying recursion ancestry."""
    ancestry = set(seen or set())
    status = "accepted"
    if action_id not in registry:
        status = "unknown_action"
    elif action_id in ancestry:
        status = "dependency_cycle"
    else:
        ancestry.add(action_id)
        if registry[action_id].depends_on and extra_args:
            status = "extra_args_for_sequence"
    return {
        "accepted": status == "accepted",
        "status": status,
        "ancestry": sorted(ancestry),
    }


def reject_action(action_id, admission):
    """Return native failure data without executing dependencies."""
    result = {"ok": False, "status": admission["status"], "action_id": action_id}
    if admission["status"] == "dependency_cycle":
        result["cycle"] = sorted(set(admission["ancestry"]) | {action_id})
    return result


def initialize_dependencies(admission):
    """Materialize the native iterator and its loop-carried state."""
    return {
        "index": 0,
        "children": [],
        "dependencies_ok": True,
        "ancestry": list(admission["ancestry"]),
    }


def visit_dependency(item, registry, context, state, *, repository_root=None):
    """Visit one registered dependency through the original recursive controller."""
    mount = {} if repository_root is None else {"repository_root": repository_root}
    return run_action(
        item.depends_on[state["index"]],
        registry,
        context,
        seen=set(state["ancestry"]),
        **mount,
    )


def advance_dependencies(item, state, child, context):
    """Append exactly once; a failed dependency never recovers aggregate success."""
    updated = {
        "index": state["index"] + 1,
        "children": [*state["children"], child],
        "dependencies_ok": state["dependencies_ok"] and bool(child.get("ok", False)),
        "ancestry": list(state["ancestry"]),
    }
    done = updated["index"] == len(item.depends_on) or (
        not child.get("ok", False) and not context.keep_going
    )
    return updated, done


def finish_dependencies(item, state):
    """Return the native sequence envelope; no parent command is implied."""
    return {
        "action": action_to_dict(item),
        "status": (
            "sequence_completed" if state["dependencies_ok"] else "sequence_failed"
        ),
        "ok": state["dependencies_ok"],
        "children": state["children"],
    }


def dependency_command_guard(item, state, context):
    """Shared native predicate for launching a composed action's command."""
    return bool(item.command) and (state["dependencies_ok"] or context.keep_going)


def aggregate_dependencies(item, state, leaf):
    """Preserve dependency failure even when the parent's command succeeds."""
    ok = state["dependencies_ok"] and leaf.get("ok", False)
    return {
        "action": action_to_dict(item),
        "status": "completed_with_dependencies" if ok else "failed_with_dependencies",
        "ok": ok,
        "children": state["children"],
        "leaf": leaf,
    }


def run_action(
    action_id: str,
    registry: Mapping[str, WorkflowAction],
    context: RunContext,
    *,
    extra_args: Sequence[str] = (),
    seen: Optional[Set[str]] = None,
    repository_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run a registered action or composed workflow sequence.

    Motivation:
        Let higher-level quality gates reuse smaller controlled actions without
        duplicating command lists.

    Intent:
        Resolve the action id, prevent dependency cycles, run dependencies in
        order, and stop on failure unless keep-going is requested.

    Inputs:
        The action id, registry, execution context, optional extra args, and
        recursion guard. An explicit repository_root carries the caller's mount
        through dependency recursion, preflight, subprocess cwd and write audits;
        omitted mounts preserve the CLI's repository default.

    Outputs:
        A result dictionary for the action or sequence.
    """

    mount = {} if repository_root is None else {"repository_root": repository_root}
    prepared = prepare_action(
        action_id, registry, context, extra_args=extra_args, seen=seen, **mount
    )
    if "result" in prepared:
        return prepared["result"]
    item = registry[action_id]
    leaf = run_leaf_action(item, context, extra_args, **mount)
    if "state" in prepared:
        return aggregate_dependencies(item, prepared["state"], leaf)
    return leaf


def prepare_action(
    action_id,
    registry,
    context,
    *,
    extra_args=(),
    seen=None,
    dependency_runner=None,
    repository_root=None,
):
    """Shared admission and ordered dependency traversal before leaf preflight.

    Staged in-process callers supply a native dependency runner; the CLI retains
    visit_dependency and its subprocess execution without a timeout override.
    """
    admission = admit_action(action_id, registry, extra_args, seen)
    if not admission["accepted"]:
        return {"result": reject_action(action_id, admission)}
    item = registry[action_id]
    if not item.depends_on:
        return {}
    state = initialize_dependencies(admission)
    mount = {} if repository_root is None else {"repository_root": repository_root}
    for _child_id in item.depends_on:
        child = (
            visit_dependency(item, registry, context, state, **mount)
            if dependency_runner is None
            else dependency_runner(
                item.depends_on[state["index"]], set(state["ancestry"])
            )
        )
        state, done = advance_dependencies(item, state, child, context)
        if done:
            break
    if not dependency_command_guard(item, state, context):
        return {"result": finish_dependencies(item, state)}
    return {"state": state}


def extract_python_paths_from_commands(
    commands: Iterable[Sequence[str]], repository_root: Optional[Path] = None
) -> Set[str]:
    """Extract repository Python script paths from command arrays.

    Motivation:
        The hub audit needs a common representation of scripts controlled by
        actions, tests, and skill hooks.

    Intent:
        Identify argv entries that are repo-relative `.py` files.

    Inputs:
        An iterable of argv sequences.

    Outputs:
        A set of normalized repository-relative Python paths.
    """

    repository_root = REPO_ROOT if repository_root is None else repository_root

    paths: Set[str] = set()
    for command in commands:
        for part in command:
            if part.endswith(".py") and not part.startswith("-"):
                candidate = (repository_root / part).resolve()
                if candidate.exists():
                    paths.add(rel(candidate, repository_root))
    return paths


def load_test_matrix_commands(repository_root: Optional[Path] = None) -> Set[str]:
    """Load Python script paths from the comprehensive test matrix.

    Motivation:
        Avoid duplicating every skill smoke test in the hub while still knowing
        those workflows are controlled by the matrix.

    Intent:
        Import `run_comprehensive_tests.py` and read its built-in command list
        without executing the commands.

    Inputs:
        None.

    Outputs:
        A set of repo-relative Python script paths referenced by matrix checks.
    """

    repository_root = REPO_ROOT if repository_root is None else repository_root

    matrix_path = (
        repository_root / "tests" / "test_program" / "run_comprehensive_tests.py"
    )
    if not matrix_path.exists():
        return set()
    spec = importlib.util.spec_from_file_location(
        "mathformer_test_program", matrix_path
    )
    if spec is None or spec.loader is None:
        return set()
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "load_matrix"):
        return set()
    matrix = module.load_matrix()
    return extract_python_paths_from_commands(
        (item.get("command", []) for item in matrix), repository_root
    )


def load_skill_hook_scripts(repository_root: Optional[Path] = None) -> Set[str]:
    """Read skill-owned scripts from `skills/SKILL_HOOKS.yaml`.

    Motivation:
        The skill-hook contract is the control layer for specialized agent
        workflows, so the hub audit should trust scripts listed there.

    Intent:
        Use a dependency-free line parser for repo-relative Python paths.

    Inputs:
        None.

    Outputs:
        A set of repo-relative skill script paths.
    """

    repository_root = REPO_ROOT if repository_root is None else repository_root

    hook_path = repository_root / "skills" / "SKILL_HOOKS.yaml"
    if not hook_path.exists():
        return set()
    text = hook_path.read_text(encoding="utf-8")
    return set(
        re.findall(
            r"skills/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/scripts/[A-Za-z0-9_./-]+\.py", text
        )
    )


def discover_python_entrypoints(repository_root: Optional[Path] = None) -> Set[str]:
    """Discover repository Python entrypoints governed by workflow controls.

    Motivation:
        Find new scripts that might bypass the hub or skill-hook contract.

    Intent:
        Inspect top-level scripts, test runners, and skill scripts while
        excluding package internals that are imported rather than invoked.

    Inputs:
        None.

    Outputs:
        A set of repo-relative Python files that should be controlled.
    """

    repository_root = REPO_ROOT if repository_root is None else repository_root

    paths: Set[str] = set()
    for pattern in (
        "scripts/*.py",
        "tests/**/*.py",
        "skills/*/*/scripts/*.py",
        "benchmarks/**/*.py",
        "paper_skills/*/scripts/*.py",
        "examples/*.py",
    ):
        for path in repository_root.glob(pattern):
            if path.name == "__init__.py":
                continue
            if "fixtures" in path.parts:
                continue
            paths.add(rel(path, repository_root))
    return paths


def audit_control(
    registry: Mapping[str, WorkflowAction], repository_root: Optional[Path] = None
) -> Dict[str, Any]:
    """Audit whether Python entrypoints are controlled by declared workflows.

    Motivation:
        Keep the repository from drifting back toward undocumented script
        execution as new capabilities are added.

    Intent:
        Consider an entrypoint controlled if it is directly registered in the
        hub, included in the comprehensive test matrix, or governed by the
        skill-hook runtime contract.

    Inputs:
        The current hub registry.

    Outputs:
        A JSON-compatible audit report with uncontrolled paths and summary
        counts.
    """

    repository_root = REPO_ROOT if repository_root is None else repository_root

    registry_paths = extract_python_paths_from_commands(
        (item.command for item in registry.values()), repository_root
    )
    matrix_paths = load_test_matrix_commands(repository_root)
    hook_paths = load_skill_hook_scripts(repository_root)
    sources, controlled = audit_pack_sources(registry_paths, matrix_paths, hook_paths)
    findings = audit_inspect_paths(sources, controlled, repository_root)
    errors = audit_dependencies(registry)
    return audit_report(sources, findings, errors)


def audit_pack_sources(registry_paths, matrix_paths, hook_paths):
    """Pack source inventories and the native helper exemptions."""
    registry_paths, matrix_paths, hook_paths = map(
        set, (registry_paths, matrix_paths, hook_paths)
    )
    controlled_paths = registry_paths | matrix_paths | hook_paths
    internal_helpers = {
        "scripts/repo_status_tools.py",
        "tests/mcp/run_repo_status_workflow_tests.py",
        "tests/mcp/fixtures/repo_status_server.py",
        "scripts/workflow_router_route_tools.py",
        "tests/mcp/run_workflow_router_route_workflow_tests.py",
        "tests/mcp/fixtures/workflow_router_route_tree.py",
        "scripts/workflow_graphs_route_tools.py",
        "tests/mcp/run_workflow_graphs_route_workflow_tests.py",
        "scripts/judge_synthesis_route_tools.py",
        "tests/mcp/run_judge_synthesis_route_workflow_tests.py",
        "tests/mcp/fixtures/judge_synthesis_route_boundary.py",
        "scripts/comparative_analysis_route_tools.py",
        "tests/mcp/run_comparative_analysis_route_workflow_tests.py",
        "scripts/codex_exec_judges_route_tools.py",
        "tests/mcp/run_codex_exec_judges_route_workflow_tests.py",
        "scripts/vampire_route_tools.py",
        "tests/mcp/run_vampire_route_workflow_tests.py",
        "scripts/mcp_serve_route_tools.py",
        "tests/mcp/run_mcp_serve_route_workflow_tests.py",
        "tests/mcp/fixtures/mcp_serve_route_server.py",
        "scripts/independent_service_route_tools.py",
        "tests/mcp/run_independent_service_route_workflow_tests.py",
        "scripts/premise_selection_route_tools.py",
        "tests/mcp/run_premise_selection_route_workflow_tests.py",
        "scripts/famous_corpus_route_tools.py",
        "tests/mcp/run_famous_corpus_route_workflow_tests.py",
        "tests/mcp/fixtures/famous_corpus_route_tree.py",
        "scripts/environment_validate_route_tools.py",
        "tests/mcp/run_environment_validate_route_workflow_tests.py",
        "tests/mcp/fixtures/environment_route_boundary.py",
        "tests/mcp/fixtures/environment_route_startup/sitecustomize.py",
        "scripts/e2e_all_backends_route_tools.py",
        "tests/mcp/run_e2e_all_backends_route_workflow_tests.py",
        "tests/mcp/fixtures/e2e_route_boundary.py",
        "tests/mcp/fixtures/e2e_route_startup/sitecustomize.py",
        "scripts/mathformerlib_accumulation_route_tools.py",
        "tests/mcp/run_mathformerlib_accumulation_route_workflow_tests.py",
        "tests/mcp/fixtures/mathformerlib_accumulation_route_boundary.py",
        "tests/mcp/fixtures/accumulation_route_startup/sitecustomize.py",
        "scripts/meta_help_route_tools.py",
        "tests/mcp/run_meta_help_route_workflow_tests.py",
        "tests/mcp/fixtures/meta_help_route_tree.py",
        "scripts/docs_validate_route_tools.py",
        "scripts/lean_fixture_route_tools.py",
        "tests/mcp/run_lean_fixture_route_workflow_tests.py",
        "tests/mcp/fixtures/lean_fixture_boundary.py",
        "tests/mcp/fixtures/lean_fixture_startup/sitecustomize.py",
        "scripts/validate_atp_route_tools.py",
        "tests/mcp/run_validate_atp_route_workflow_tests.py",
        "tests/mcp/fixtures/validate_atp_route_boundary.py",
        "tests/mcp/run_docs_validate_route_workflow_tests.py",
        "tests/mcp/fixtures/docs_route_boundary.py",
        "tests/mcp/fixtures/docs_route_startup/sitecustomize.py",
        "tests/mcp/run_premise_reuse_dispatch_workflow_tests.py",
        "tests/mcp/run_formal_proof_dispatch_workflow_tests.py",
        "scripts/reflection_observer_tools.py",
        "scripts/mathlib_grounding_workflow_tools.py",
        "tests/mcp/run_mathlib_grounding_workflow_tests.py",
        "scripts/lean_consistency_workflow_tools.py",
        "tests/mcp/run_lean_consistency_workflow_tests.py",
        "scripts/agentc_refinement_workflow_tools.py",
        "tests/mcp/run_agentc_refinement_workflow_tests.py",
        "scripts/physics_lean_family_tools.py",
        "tests/mcp/run_physics_lean_family_workflow_tests.py",
        "scripts/physics_sympy_family_workflow_tools.py",
        "tests/mcp/run_physics_sympy_family_workflow_tests.py",
        "scripts/rfde_family_workflow_tools.py",
        "tests/mcp/run_rfde_family_workflow_tests.py",
        "scripts/mathlib_family_workflow_tools.py",
        "tests/mcp/run_mathlib_family_workflow_tests.py",
        "tests/mcp/fixtures/mathlib_family_boundary.py",
        "scripts/textbook_route_tools.py",
        "tests/mcp/run_textbook_route_workflow_tests.py",
        "tests/mcp/fixtures/textbook_route_fixture.py",
        "tests/mcp/fixtures/textbook_route_startup/sitecustomize.py",
        "scripts/rfde_route_tools.py",
        "tests/mcp/run_rfde_route_workflow_tests.py",
        "tests/mcp/fixtures/rfde_route_boundary.py",
        "scripts/source_family_workflow_tools.py",
        "tests/mcp/run_source_family_workflow_tests.py",
        "tests/mcp/fixtures/source_family_boundary.py",
        "scripts/paper_family_workflow_tools.py",
        "tests/mcp/run_paper_family_workflow_tests.py",
        "scripts/meta_skills_family_workflow_tools.py",
        "tests/mcp/run_meta_skills_family_workflow_tests.py",
        "scripts/skills_family_workflow_tools.py",
        "tests/mcp/run_skills_family_workflow_tests.py",
        "scripts/mcp_family_workflow_tools.py",
        "scripts/textbook_family_workflow_tools.py",
        "tests/mcp/run_textbook_family_workflow_tests.py",
        "tests/mcp/run_mcp_family_workflow_tests.py",
        "scripts/mathformerphysicslib_family_tools.py",
        "tests/mcp/run_mathformerphysicslib_family_workflow_tests.py",
        "scripts/mathformerlib_family_tools.py",
        "tests/mcp/run_mathformerlib_family_workflow_tests.py",
        "tests/mcp/run_mathformerlib_accumulation_workflow_tests.py",
        "scripts/lean_family_workflow_tools.py",
        "tests/mcp/run_lean_family_workflow_tests.py",
        "scripts/isabelle_family_workflow_tools.py",
        "tests/mcp/run_isabelle_family_workflow_tests.py",
        "scripts/generative_family_workflow_tools.py",
        "tests/mcp/run_generative_family_workflow_tests.py",
        "scripts/environment_family_workflow_tools.py",
        "tests/mcp/run_environment_family_workflow_tests.py",
        "scripts/e2e_family_workflow_tools.py",
        "tests/mcp/run_e2e_family_workflow_tests.py",
        "scripts/docs_family_workflow_tools.py",
        "tests/mcp/run_docs_family_workflow_tests.py",
        "scripts/control_family_workflow_tools.py",
        "tests/mcp/run_control_family_workflow_tests.py",
        "scripts/sympy_family_workflow_tools.py",
        "tests/mcp/run_sympy_family_workflow_tests.py",
        "scripts/docs_workflow_tools.py",
        "tests/mcp/run_docs_workflow_tests.py",
        "scripts/comprehensive_workflow_tools.py",
        "tests/mcp/run_comprehensive_workflow_tests.py",
        "scripts/comprehensive_strict_tools.py",
        "tests/mcp/run_comprehensive_strict_workflow_tests.py",
        "scripts/backend_test_tools.py",
        "tests/mcp/run_backend_test_workflow_tests.py",
        "scripts/plugin_test_tools.py",
        "tests/mcp/run_plugin_test_workflow_tests.py",
        "scripts/plugin_check_tools.py",
        "tests/mcp/run_plugin_check_workflow_tests.py",
        "scripts/client_discovery_tools.py",
        "tests/mcp/run_client_discovery_workflow_tests.py",
        "scripts/setup_sympy_tools.py",
        "scripts/setup_lean_tools.py",
        "scripts/setup_atp_kb_tools.py",
        "scripts/setup_atp_kb_route_tools.py",
        "scripts/setup_lean_route_tools.py",
        "tests/mcp/run_setup_lean_route_workflow_tests.py",
        "tests/mcp/fixtures/setup_lean_route_boundary.py",
        "scripts/setup_python_all_route_tools.py",
        "tests/mcp/run_setup_python_all_route_workflow_tests.py",
        "tests/mcp/fixtures/setup_python_all_route_boundary.py",
        "scripts/setup_full_route_tools.py",
        "tests/mcp/run_setup_full_route_workflow_tests.py",
        "tests/mcp/fixtures/setup_full_route_boundary.py",
        "tests/mcp/run_setup_atp_kb_route_workflow_tests.py",
        "tests/mcp/fixtures/setup_atp_kb_route_boundary.py",
        "scripts/setup_all_tools.py",
        "scripts/setup_python_all_tools.py",
        "scripts/sympy_source_only_tools.py",
        "tests/mcp/run_sympy_source_only_workflow_tests.py",
        "tests/mcp/run_sympy_source_only_0004_workflow_tests.py",
        "tests/mcp/run_sympy_physics_derivation_loop_tests.py",
        "tests/mcp/fixtures/sympy_source_only_server.py",
        "scripts/sympy_expansion_tools.py",
        "tests/mcp/run_sympy_expansion_workflow_tests.py",
        "tests/mcp/run_sympy_expansion_0004_workflow_tests.py",
        "scripts/sympy_goal_plan_tools.py",
        "tests/mcp/run_sympy_goal_plan_workflow_tests.py",
        "tests/mcp/run_sympy_goal_plan_0004_workflow_tests.py",
        "scripts/cross_backend_semantic_packet_tools.py",
        "tests/mcp/run_cross_backend_semantic_packet_workflow_tests.py",
        "scripts/adversarial_design_guard_tools.py",
        "tests/mcp/run_adversarial_design_guard_workflow_tests.py",
        "scripts/sympy_grounded_sample_tools.py",
        "tests/mcp/run_sympy_grounded_sample_workflow_tests.py",
        "tests/mcp/run_sympy_grounded_sample_0004_workflow_tests.py",
        "scripts/design_guard_review_tools.py",
        "tests/mcp/run_design_guard_review_workflow_tests.py",
        "scripts/repair_expansion_tools.py",
        "tests/mcp/run_repair_expansion_workflow_tests.py",
        "scripts/pathology_repair_tools.py",
        "tests/mcp/run_pathology_repair_workflow_tests.py",
        "scripts/recursive_repair_control_tools.py",
        "tests/mcp/run_recursive_repair_control_workflow_tests.py",
        "scripts/sympy_recursive_repair_control_tools.py",
        "tests/mcp/run_sympy_recursive_repair_control_workflow_tests.py",
        "scripts/sympy_recursive_repair_control_0004_tools.py",
        "tests/mcp/run_sympy_recursive_repair_control_0004_workflow_tests.py",
        "scripts/new_qm_source_only_tools.py",
        "tests/mcp/run_new_qm_source_only_workflow_tests.py",
        "scripts/recursive_goal_tools.py",
        "tests/mcp/run_recursive_goal_workflow_tests.py",
        "tests/mcp/run_recursive_goal_loop_tests.py",
        "tests/mcp/run_recursive_goal_route_tests.py",
        "scripts/generative_repair_tools.py",
        "tests/mcp/run_generative_repair_workflow_tests.py",
        "scripts/foundation_surface_tools.py",
        "tests/mcp/run_foundation_surface_workflow_tests.py",
        "scripts/dirac_recursive_tools.py",
        "tests/mcp/run_dirac_recursive_workflow_tests.py",
        "scripts/physics_lean_grounding_tools.py",
        "tests/mcp/run_physics_lean_grounding_workflow_tests.py",
        "tests/mcp/run_update_grounding_audit_workflow_tests.py",
        "scripts/foundations_workflow_tools.py",
        "tests/mcp/run_foundations_workflow_tests.py",
        "scripts/foundation_draft_tools.py",
        "tests/mcp/run_foundation_draft_workflow_tests.py",
        "scripts/foundation_verify_tools.py",
        "tests/mcp/run_foundation_verify_workflow_tests.py",
        "scripts/foundation_intake_tools.py",
        "tests/mcp/run_foundation_intake_workflow_tests.py",
        "scripts/grounding_debt_tools.py",
        "tests/mcp/run_grounding_debt_workflow_tests.py",
        "scripts/drift_pathology_tools.py",
        "tests/mcp/run_drift_pathology_workflow_tests.py",
        "scripts/source_units_route_tools.py",
        "tests/mcp/run_source_units_route_workflow_tests.py",
        "tests/mcp/fixtures/source_units_route_boundary.py",
        "tests/mcp/fixtures/source_units_route_startup/sitecustomize.py",
        "scripts/drift_monitor_route_tools.py",
        "tests/mcp/run_drift_route_workflow_tests.py",
        "scripts/physics_object_detector_tools.py",
        "tests/mcp/run_physics_object_detector_workflow_tests.py",
        "scripts/physics_ir_tools.py",
        "tests/mcp/run_physics_ir_workflow_tests.py",
        "scripts/meta_suite_tools.py",
        "scripts/workflow_evolution_tools.py",
        "tests/mcp/run_workflow_evolution_tests.py",
        "scripts/task_registry_tools.py",
        "tests/mcp/run_task_registry_workflow_tests.py",
        "scripts/generated_lifecycle_tools.py",
        "scripts/mathlib_term_tools.py",
        "tests/mcp/run_mathlib_term_workflow_tests.py",
        "scripts/mathlib_navigation_tools.py",
        "tests/mcp/run_mathlib_navigation_workflow_tests.py",
        "scripts/indexing_control_route_tools.py",
        "tests/mcp/run_indexing_control_route_workflow_tests.py",
        "tests/mcp/fixtures/indexing_route_tree.py",
        "tests/mcp/fixtures/indexing_route_boundary/sitecustomize.py",
        "scripts/mathlib_indexing_control_tools.py",
        "tests/mcp/run_indexing_control_workflow_tests.py",
        "scripts/mathlib_index_validation_tools.py",
        "tests/mcp/run_mathlib_index_validate_workflow_tests.py",
        "scripts/mathlib_index_build_tools.py",
        "tests/mcp/run_mathlib_index_build_workflow_tests.py",
        "scripts/formal_answer_policy_tools.py",
        "tests/mcp/run_formal_answer_policy_workflow_tests.py",
        "scripts/physics_registry_tools.py",
        "scripts/cross_backend_parity_tools.py",
        "scripts/physics_candidate_compile_tools.py",
        "scripts/physics_release_gate_tools.py",
        "scripts/e2e_all_backends_tools.py",
        "scripts/proofnet_tools.py",
        "scripts/proofnet_evaluate_tools.py",
        "scripts/formal_science_tools.py",
        "scripts/formalphysics_extra_isabelle_tools.py",
        "scripts/formalphysics_original_two_isabelle_tools.py",
        "scripts/formalphysics_original_two_lean_tools.py",
        "scripts/formalphysics_original_two_sympy_tools.py",
        "scripts/formalphysics_top10_sympy_tools.py",
        "scripts/formalphysics_extra_sympy_tools.py",
        "scripts/controlled_sympy_tools.py",
        "scripts/sympy_controlled_suite_tools.py",
        "tests/mcp/run_sympy_controlled_suite_workflow_tests.py",
        "tests/mcp/run_sympy_equational_trace_loop_tests.py",
        "tests/mcp/run_executable_symbolic_derivation_workflow_tests.py",
        "scripts/formalphysics_extra_lean_tools.py",
        "scripts/formalphysics_refresh_tools.py",
        "scripts/premise_triple_tools.py",
        "scripts/premise_group_tools.py",
        "scripts/premise_kb_e2e_tools.py",
        "scripts/premise_kb_index_tools.py",
        "scripts/kb_skill_scripts_tools.py",
        "scripts/kb_manage_tools.py",
        "scripts/famous_corpus_tools.py",
        "scripts/famous_generator_tools.py",
        "scripts/vampire_group_example_tools.py",
        "scripts/vampire_strict_order_tools.py",
        "scripts/vampire_policy_tools.py",
        "scripts/atp_demo_tools.py",
        "scripts/mathformer.py",
        "scripts/mcp_service_config.py",
        "scripts/mcp_agent_assets.py",
        "scripts/agentc_workflow_tools.py",
        "scripts/adversarial_validation_tools.py",
        "scripts/agentc_analysis_tools.py",
        "scripts/catalog_check_tools.py",
        "scripts/adoption_catalog_tools.py",
        "tests/mcp/run_adoption_catalog_workflow_tests.py",
        "scripts/service_config_tools.py",
        "scripts/service_self_check_tools.py",
        "tests/mcp/run_service_config_workflow_tests.py",
        "scripts/normalize_workflows_tools.py",
        "scripts/prism_verification_tools.py",
        "scripts/prism_native_route_tools.py",
        "tests/mcp/run_prism_native_route_workflow_tests.py",
        "tests/mcp/fixtures/prism_route_boundary.py",
        "scripts/textbook_chapter_workflow_tools.py",
        "scripts/isabelle_trace_workflow_tools.py",
        "tests/mcp/run_isabelle_trace_workflow_tests.py",
        "tests/mcp/fixtures/isabelle_trace_boundaries.py",
        "scripts/mechanistic_diagram_tools.py",
        "scripts/theory_evolution_simulate_tools.py",
        "tests/mcp/run_theory_evolution_simulate_workflow_tests.py",
        "scripts/theory_evolution_suite_tools.py",
        "tests/mcp/run_theory_evolution_suite_workflow_tests.py",
        "scripts/theory_evolution_model_tools.py",
        "tests/mcp/run_theory_evolution_model_workflow_tests.py",
        "scripts/mechanistic_figure_tools.py",
        "tests/mcp/run_mechanistic_figure_workflow_tests.py",
        "tests/mcp/run_mechanistic_diagram_workflow_tests.py",
        "scripts/quality_card_tools.py",
        "scripts/theorem_seed_tools.py",
        "scripts/thematic_layout_tools.py",
        "scripts/lean_route_tools.py",
        "tests/mcp/run_lean_route_workflow_tests.py",
        "tests/mcp/fixtures/lean_route_compiler.py",
        "scripts/rocq_route_tools.py",
        "scripts/mathlib_route_tools.py",
        "tests/mcp/run_mathlib_route_workflow_tests.py",
        "tests/mcp/fixtures/mathlib_route_service.py",
        "tests/mcp/fixtures/mathlib_route_tree.py",
        "tests/mcp/fixtures/mathlib_route_boundary/sitecustomize.py",
        "tests/mcp/run_rocq_route_workflow_tests.py",
        "tests/mcp/fixtures/rocq_route_tree.py",
        "tests/mcp/fixtures/rocq_route_boundary/sitecustomize.py",
        "scripts/isabelle_route_tools.py",
        "tests/mcp/run_isabelle_route_workflow_tests.py",
        "scripts/isabelle_wiki_tools.py",
        "tests/mcp/run_isabelle_wiki_workflow_tests.py",
        "tests/mcp/fixtures/isabelle_wiki_runtime.py",
        "tests/mcp/fixtures/isabelle_wiki_compiler.py",
        "scripts/physics_isabelle_route_tools.py",
        "scripts/sympy_route_tools.py",
        "tests/mcp/run_sympy_route_workflow_tests.py",
        "tests/mcp/fixtures/sympy_route_boundary.py",
        "scripts/physics_sympy_goal_route_tools.py",
        "scripts/physics_sympy_goal_0004_route_tools.py",
        "tests/mcp/run_physics_sympy_goal_0004_route_workflow_tests.py",
        "tests/mcp/fixtures/physics_sympy_goal_0004_route_tree.py",
        "tests/mcp/run_physics_sympy_goal_route_workflow_tests.py",
        "tests/mcp/run_physics_isabelle_route_workflow_tests.py",
        "tests/mcp/fixtures/physics_isabelle_route_tree.py",
        "tests/mcp/fixtures/isabelle_route_tree.py",
        "tests/mcp/fixtures/isabelle_route_boundary/sitecustomize.py",
        "scripts/thematic_layout_route_tools.py",
        "scripts/skills_link_route_tools.py",
        "tests/mcp/run_skills_link_route_workflow_tests.py",
        "scripts/skills_publication_tools.py",
        "tests/mcp/run_skills_publication_workflow_tests.py",
        "scripts/skills_plugin_sync_route_tools.py",
        "tests/mcp/run_skills_plugin_sync_route_workflow_tests.py",
        "tests/mcp/fixtures/skills_plugin_sync_repository.py",
        "scripts/skills_plugin_check_route_tools.py",
        "tests/mcp/run_skills_plugin_check_route_workflow_tests.py",
        "tests/mcp/fixtures/skills_plugin_check_repository.py",
        "scripts/normalized_workflows_route_tools.py",
        "tests/mcp/run_normalized_workflows_route_workflow_tests.py",
        "tests/mcp/fixtures/normalized_workflows_route_tree.py",
        "scripts/portable_adoption_route_tools.py",
        "tests/mcp/run_portable_adoption_route_workflow_tests.py",
        "tests/mcp/fixtures/portable_adoption_route_tree.py",
        "tests/mcp/run_thematic_layout_route_workflow_tests.py",
        "scripts/licenses_inventory_route_tools.py",
        "tests/mcp/run_licenses_inventory_route_workflow_tests.py",
        "tests/mcp/fixtures/licenses_metadata/sitecustomize.py",
        "tests/mcp/fixtures/licenses_metadata/licenses_metadata_provider.py",
        "scripts/workflow_graph_layout_tools.py",
        "scripts/workflow_graph_render_tools.py",
        "scripts/lean_build_tools.py",
        "tests/mcp/run_lean_build_workflow_tests.py",
        "scripts/dependency_lock_tools.py",
        "scripts/dependency_failure_tools.py",
        "scripts/skill_projection_tools.py",
        "tests/mcp/run_skill_projections_workflow_tests.py",
        "scripts/taxonomic_navigation_tools.py",
        "tests/mcp/run_taxonomic_navigation_workflow_tests.py",
        "scripts/service_dependency_tools.py",
        "tests/mcp/run_service_dependencies_workflow_tests.py",
        "scripts/integration_audit_tools.py",
        "scripts/reasoning_catalog_tools.py",
        "scripts/reasoning_catalog_render_tools.py",
        "scripts/library_docs_tools.py",
        "scripts/license_inventory_tools.py",
        "scripts/api_critic_tools.py",
        "scripts/coherence_api_alias_tools.py",
        "scripts/coherence_gate_alias_tools.py",
        "tests/mcp/run_coherence_gate_alias_workflow_tests.py",
        "scripts/coherence_canonicalize_alias_tools.py",
        "tests/mcp/run_coherence_canonicalize_alias_workflow_tests.py",
        "tests/mcp/run_coherence_api_alias_workflow_tests.py",
        "scripts/redefinition_critic_tools.py",
        "tests/mcp/run_redefinition_critic_workflow_tests.py",
        "scripts/integration_critic_tools.py",
        "scripts/mathlib_grounding_tools.py",
        "scripts/generative_critic_tools.py",
        "scripts/coherence_generative_alias_tools.py",
        "tests/mcp/run_coherence_generative_alias_workflow_tests.py",
        "scripts/coherence_repair_alias_tools.py",
        "tests/mcp/run_coherence_repair_alias_workflow_tests.py",
        "scripts/coherence_integration_alias_tools.py",
        "tests/mcp/run_coherence_integration_alias_workflow_tests.py",
        "scripts/coherence_grounding_alias_tools.py",
        "tests/mcp/run_coherence_grounding_alias_workflow_tests.py",
        "tests/mcp/run_generative_critic_workflow_tests.py",
        "scripts/coherence_gate_tools.py",
        "scripts/coherence_repair_tools.py",
        "tests/mcp/run_coherence_repair_workflow_tests.py",
        "scripts/coherence_inventory_alias_tools.py",
        "scripts/coherence_redefinition_alias_tools.py",
        "tests/mcp/run_coherence_redefinition_alias_workflow_tests.py",
        "tests/mcp/run_coherence_inventory_alias_workflow_tests.py",
        "scripts/coherence_inventory_tools.py",
        "scripts/concept_canonicalize_tools.py",
        "tests/mcp/run_concept_canonicalize_workflow_tests.py",
        "scripts/coherence_loop_tools.py",
        "tests/mcp/run_coherence_loop_workflow_tests.py",
        "tests/mcp/run_coherence_loop_alias_workflow_tests.py",
        "tests/mcp/run_coherence_inventory_workflow_tests.py",
        "scripts/reasoning_index_tools.py",
        "scripts/wiki_suite_tools.py",
        "scripts/physics_backend_suite_tools.py",
        "scripts/physics_lean_backend_route_tools.py",
        "tests/mcp/run_physics_lean_backend_route_workflow_tests.py",
        "tests/mcp/fixtures/physics_lean_backend_route_server.py",
        "scripts/grounded_sample_tools.py",
        "tests/mcp/run_grounded_sample_workflow_tests.py",
        "tests/mcp/run_grounded_samples_route_workflow_tests.py",
        "scripts/derivation_completeness_route_tools.py",
        "scripts/derivation_completeness_tools.py",
        "tests/mcp/run_derivation_completeness_workflow_tests.py",
        "scripts/derivation_regression_tools.py",
        "tests/mcp/run_derivation_regression_workflow_tests.py",
        "scripts/reasoning_summary_tools.py",
        "scripts/object_workbench_tools.py",
        "tests/mcp/run_object_workbench_workflow_tests.py",
        "scripts/codex_judge_self_test_tools.py",
        "scripts/judge_synthesis_report_tools.py",
        "scripts/synthesis_builder_tools.py",
        "tests/mcp/run_synthesis_builder_workflow_tests.py",
        "tests/mcp/run_judge_synthesis_report_workflow_tests.py",
        "scripts/comparative_report_self_test_tools.py",
        "scripts/comparative_report_tools.py",
        "scripts/codex_judge_runner_tools.py",
        "tests/mcp/run_codex_judge_runner_workflow_tests.py",
        "scripts/runtime_trace_tools.py",
        "scripts/runtime_trace_validation_tools.py",
        "scripts/hub_runtime_trace_tools.py",
        "tests/mcp/run_hub_runtime_trace_workflow_tests.py",
        "scripts/paper_workflow_catalog_tools.py",
        "scripts/paper_route_tools.py",
        "tests/mcp/run_paper_workflow_catalog_tests.py",
        "scripts/paper_update_plan_tools.py",
        "tests/mcp/run_paper_update_plan_workflow_tests.py",
        "scripts/paper_evidence_packet_tools.py",
        "scripts/paper_claim_audit_tools.py",
        "tests/mcp/run_paper_claim_audit_workflow_tests.py",
        "scripts/paper_claim_audit_rfde_tools.py",
        "tests/mcp/run_paper_claim_audit_rfde_workflow_tests.py",
        "tests/mcp/run_runtime_trace_validation_tests.py",
        "tests/mcp/run_runtime_trace_workflow_tests.py",
        "scripts/skill_coverage_tools.py",
        "scripts/router_coverage_tools.py",
        "scripts/mcp_boundary_tools.py",
        "scripts/rocq_self_test_tools.py",
        "tests/mcp/run_rocq_self_test_workflow_tests.py",
        "scripts/rocq_wiki_suite_tools.py",
        "tests/mcp/run_rocq_wiki_suite_workflow_tests.py",
        "scripts/rocq_check_tools.py",
        "tests/mcp/run_rocq_check_workflow_tests.py",
        "tests/mcp/fixtures/rocq_compiler_server.py",
        "scripts/reasoning_smoke_tools.py",
        "scripts/reasoning_log_build_tools.py",
        "scripts/reasoning_flow_tools.py",
        "scripts/reasoning_consumer_tools.py",
        "scripts/reasoning_quality_tools.py",
        "scripts/reasoning_html_tools.py",
        "scripts/skill_hooks_tools.py",
        "scripts/adoption_test_contracts_tools.py",
        "scripts/normalized_workflow_test_tools.py",
        "scripts/calibration_dashboard_tools.py",
        "tests/mcp/run_calibration_dashboard_workflow_tests.py",
        "scripts/adoption_provenance_test_tools.py",
        "scripts/adoption_check_tools.py",
        "scripts/agentc_analyze_route_tools.py",
        "tests/mcp/run_agentc_analyze_route_workflow_tests.py",
        "scripts/benchmark_route_tools.py",
        "tests/mcp/run_benchmark_route_workflow_tests.py",
        "scripts/control_audit_route_tools.py",
        "tests/mcp/run_control_audit_route_workflow_tests.py",
        "tests/mcp/fixtures/control_audit_compiler.py",
        "scripts/reasoning_flow_route_tools.py",
        "scripts/generative_probes_route_tools.py",
        "tests/mcp/run_generative_probes_route_workflow_tests.py",
        "tests/mcp/fixtures/generative_probes_tree.py",
        "scripts/reasoning_catalog_route_tools.py",
        "tests/mcp/run_reasoning_catalog_route_workflow_tests.py",
        "tests/mcp/run_reasoning_flow_route_workflow_tests.py",
        "tests/mcp/fixtures/reasoning_route_compiler.py",
        "scripts/reasoning_log_coverage_route_tools.py",
        "tests/mcp/run_reasoning_log_coverage_route_workflow_tests.py",
        "tests/mcp/fixtures/reasoning_log_coverage_tree.py",
        "scripts/reasoning_log_html_route_tools.py",
        "tests/mcp/run_reasoning_log_html_route_workflow_tests.py",
        "tests/mcp/fixtures/reasoning_log_html_tree.py",
        "scripts/reasoning_log_quality_route_tools.py",
        "scripts/physics_coherence_route_tools.py",
        "scripts/physics_pathologies_route_tools.py",
        "tests/mcp/run_physics_pathologies_route_workflow_tests.py",
        "tests/mcp/fixtures/physics_pathologies_route_tree.py",
        "tests/mcp/run_reasoning_log_quality_route_workflow_tests.py",
        "tests/mcp/fixtures/reasoning_log_quality_tree.py",
        "scripts/reasoning_logs_route_tools.py",
        "tests/mcp/run_reasoning_logs_route_workflow_tests.py",
        "tests/mcp/fixtures/reasoning_logs_route_tree.py",
        "scripts/reasoning_log_summary_route_tools.py",
        "tests/mcp/run_reasoning_log_summary_route_workflow_tests.py",
        "tests/mcp/fixtures/reasoning_log_summary_tree.py",
        "scripts/reasoning_log_schema_route_tools.py",
        "tests/mcp/run_reasoning_log_schema_route_workflow_tests.py",
        "tests/mcp/fixtures/reasoning_log_schema_tree.py",
        "scripts/control_all_tools.py",
        "scripts/repo_diff_check_tools.py",
        "tests/mcp/run_repo_diff_check_workflow_tests.py",
        "scripts/review_framework_tools.py",
        "tests/mcp/fixtures/review_framework_boundary_server.py",
        "tests/mcp/run_review_framework_workflow_tests.py",
        "scripts/quality_smoke_tools.py",
        "tests/mcp/run_quality_smoke_workflow_tests.py",
        "scripts/quality_smoke_route_tools.py",
        "tests/mcp/run_quality_smoke_route_workflow_tests.py",
        "scripts/test_runner_route_tools.py",
        "tests/mcp/run_test_runner_route_workflow_tests.py",
        "tests/mcp/fixtures/quality_smoke_route_compiler.py",
        "scripts/quality_full_tools.py",
        "tests/mcp/run_quality_full_workflow_tests.py",
        "scripts/quality_strict_route_tools.py",
        "tests/mcp/run_quality_strict_route_workflow_tests.py",
        "tests/mcp/fixtures/quality_strict_route_boundary.py",
        "scripts/framework_review_route_tools.py",
        "scripts/quality_full_route_tools.py",
        "tests/mcp/run_quality_full_route_workflow_tests.py",
        "tests/mcp/fixtures/quality_full_route_boundary.py",
        "tests/mcp/fixtures/quality_full_route_startup/sitecustomize.py",
        "scripts/readiness_tools.py",
        "scripts/coherence_suite_tools.py",
        "scripts/coherence_suite_alias_tools.py",
        "tests/mcp/run_coherence_suite_alias_workflow_tests.py",
        "tests/mcp/fixtures/coherence_suite_alias_boundary_server.py",
        "scripts/adoption_describe_tools.py",
        "scripts/adoption_invoke_tools.py",
        "scripts/adoption_receipt_render_tools.py",
        "scripts/adoption_receipt_validate_tools.py",
        "scripts/adoption_validate_tools.py",
        "scripts/workflow_write_audit.py",
        "scripts/workflow_catalog.py",
        "skills/autoformalization/autoformalization-agentc/scripts/agentc.py",
        "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts/coherence_common.py",
        "skills/mathlib/mathlib-concept-ontology-manager/scripts/ontology.py",
        "skills/mathlib/mathlib-index-builder/scripts/mathlib_index_common.py",
        "skills/control/reasoning-log-schema-guardian/scripts/reasoning_log.py",
    }
    return {
        "hub_registry": sorted(registry_paths),
        "comprehensive_test_matrix": sorted(matrix_paths),
        "skill_hooks": sorted(hook_paths),
        "internal_helpers": sorted(internal_helpers),
    }, sorted(controlled_paths)


def audit_inspect_paths(
    sources, controlled_paths, repository_root: Optional[Path] = None
):
    """Complete both native path inspections before returning findings."""

    repository_root = REPO_ROOT if repository_root is None else repository_root
    registry_paths = sources["hub_registry"]
    internal_helpers = set(sources["internal_helpers"])
    controlled_paths = set(controlled_paths)
    discovered = discover_python_entrypoints(repository_root)
    uncontrolled = sorted(
        path
        for path in discovered
        if path not in controlled_paths and path not in internal_helpers
    )

    direct_but_missing = sorted(
        path for path in registry_paths if not (repository_root / path).exists()
    )
    return {
        "discovered": sorted(discovered),
        "uncontrolled": uncontrolled,
        "direct_missing": direct_but_missing,
    }


def audit_dependencies(registry):
    """Retain dependency traversal order and duplicate findings."""
    dependency_errors = []
    for item in registry.values():
        for child in item.depends_on:
            if child not in registry:
                dependency_errors.append(
                    {"action_id": item.action_id, "missing_dependency": child}
                )

    return dependency_errors


def audit_report(sources, findings, dependency_errors):
    """Build the native audit report without turning findings into exceptions."""
    registry_paths = sources["hub_registry"]
    matrix_paths = sources["comprehensive_test_matrix"]
    hook_paths = sources["skill_hooks"]
    internal_helpers = sources["internal_helpers"]
    discovered = findings["discovered"]
    uncontrolled = findings["uncontrolled"]
    direct_but_missing = findings["direct_missing"]
    return {
        "schema_version": 1,
        "ok": not uncontrolled and not direct_but_missing and not dependency_errors,
        "entrypoint_count": len(discovered),
        "controlled_count": len(discovered) - len(uncontrolled),
        "uncontrolled_entrypoints": uncontrolled,
        "registry_script_count": len(registry_paths),
        "matrix_script_count": len(matrix_paths),
        "skill_hook_script_count": len(hook_paths),
        "direct_registered_missing_paths": direct_but_missing,
        "dependency_errors": dependency_errors,
        "control_sources": {
            "hub_registry": sorted(registry_paths),
            "comprehensive_test_matrix": sorted(matrix_paths),
            "skill_hooks": sorted(hook_paths),
            "internal_helpers": sorted(internal_helpers),
        },
    }


def normalize_extra_args(extra_args: Sequence[str]) -> List[str]:
    """Normalize pass-through arguments after `run ACTION -- ...`.

    Motivation:
        Keep the argparse interface pleasant while preserving exact argv tokens.

    Intent:
        Remove the separator token when present and leave all other arguments
        untouched.

    Inputs:
        Raw remainder arguments from argparse.

    Outputs:
        The pass-through argv list.
    """

    args = list(extra_args)
    if args and args[0] == "--":
        return args[1:]
    return args


def absorb_run_options(args: argparse.Namespace) -> None:
    """Recover run options that appear after the action id.

    Motivation:
        Users naturally type `run ACTION --dry-run --json`, but argparse's
        remainder parsing treats those tokens as pass-through arguments.

    Intent:
        Accept hub options after the action id until a `--` separator appears;
        arguments after the separator remain child workflow arguments.

    Inputs:
        The parsed argparse namespace for the `run` command.

    Outputs:
        Mutates the namespace in place so execution sees the intended flags.
    """

    option_to_attr = {
        "--dry-run": "dry_run",
        "--json": "json",
        "--keep-going": "keep_going",
        "--allow-mutating": "allow_mutating",
        "--write-report": "write_report",
    }
    value_option_to_attr = {
        "--reasoning-log-file": "reasoning_log_file",
    }
    recovered: List[str] = []
    remaining = list(args.extra_args)
    while remaining:
        token = remaining.pop(0)
        if token == "--":
            recovered.extend(remaining)
            break
        attr = option_to_attr.get(token)
        value_attr = value_option_to_attr.get(token)
        if attr is None and value_attr is None:
            recovered.append(token)
            recovered.extend(remaining)
            break
        if attr is not None:
            setattr(args, attr, True)
            continue
        if not remaining:
            recovered.append(token)
            break
        assert value_attr is not None
        setattr(args, value_attr, Path(remaining.pop(0)))
    args.extra_args = recovered


def emit_result(payload: Mapping[str, Any], *, json_output: bool) -> None:
    """Write a command result to stdout.

    Motivation:
        Support both human terminal usage and machine-readable agent usage.

    Intent:
        Print full JSON when requested; otherwise replay subprocess output and
        finish with a concise status line.

    Inputs:
        A result payload and output mode flag.

    Outputs:
        Writes to stdout/stderr.
    """

    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if "stdout" in payload and payload["stdout"]:
        print(payload["stdout"], end="")
    if "stderr" in payload and payload["stderr"]:
        print(payload["stderr"], end="", file=sys.stderr)
    status = payload.get("status", "unknown")
    ok = payload.get("ok", False)
    print(f"{'PASS' if ok else 'FAIL'} {status}")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Motivation:
        Keep hub commands discoverable and stable for humans, CI, and agents.

    Intent:
        Define ask, list, show, run, and audit subcommands with consistent JSON
        flags.

    Inputs:
        None.

    Outputs:
        An argparse parser.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser(
        "list", help="List registered workflow actions."
    )
    list_parser.add_argument("--family")
    list_parser.add_argument("--json", action="store_true")

    ask_parser = subparsers.add_parser(
        "ask",
        help="Resolve a natural-language request into controlled workflow routes.",
    )
    ask_parser.add_argument(
        "request",
        nargs="+",
        help="Natural-language request, such as 'prove this theorem with Vampire'.",
    )
    ask_parser.add_argument(
        "--family", help="Restrict matches to actions in one workflow family."
    )
    ask_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of route recommendations to show.",
    )
    ask_parser.add_argument(
        "--run", action="store_true", help="Run the top matched controlled route."
    )
    ask_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="When --run is used, show what would run without executing.",
    )
    ask_parser.add_argument("--json", action="store_true")
    ask_parser.add_argument("--keep-going", action="store_true")
    ask_parser.add_argument("--allow-mutating", action="store_true")
    ask_parser.add_argument("--write-report", action="store_true")
    ask_parser.add_argument(
        "--reasoning-log-file",
        type=Path,
        help="Optional hub-level reasoning-log JSONL file.",
    )

    show_parser = subparsers.add_parser(
        "show", help="Show one workflow action contract."
    )
    show_parser.add_argument("action_id")
    show_parser.add_argument("--json", action="store_true")

    run_parser = subparsers.add_parser("run", help="Run a registered workflow action.")
    run_parser.add_argument("action_id")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--json", action="store_true")
    run_parser.add_argument("--keep-going", action="store_true")
    run_parser.add_argument("--allow-mutating", action="store_true")
    run_parser.add_argument("--write-report", action="store_true")
    run_parser.add_argument(
        "--reasoning-log-file",
        type=Path,
        help="Optional hub-level reasoning-log JSONL file.",
    )
    run_parser.add_argument("extra_args", nargs=argparse.REMAINDER)

    audit_parser = subparsers.add_parser(
        "audit", help="Audit workflow-control coverage."
    )
    audit_parser.add_argument("--json", action="store_true")
    audit_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return nonzero if uncontrolled entrypoints are found.",
    )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the Mathformer AgenticHub CLI.

    Motivation:
        Provide one front door for repository actions and one control point for
        execution policy.

    Intent:
        Parse user intent, dispatch to the registry, and return meaningful exit
        codes for local use and CI.

    Inputs:
        Optional argv sequence for tests; defaults to process arguments.

    Outputs:
        Process exit code.
    """

    registry = build_registry()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list":
        items = sorted(registry.values(), key=lambda item: item.action_id)
        if args.family:
            items = [item for item in items if item.family == args.family]
        payload = {
            "schema_version": 1,
            "ok": True,
            "actions": [action_to_dict(item) for item in items],
        }
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print_human_action_list(items)
        return 0

    if args.command == "ask":
        request_text = " ".join(args.request)
        limit = max(1, args.limit)
        matches = resolve_intent(
            request_text, registry, limit=limit, family=args.family
        )
        payload = {
            "schema_version": 1,
            "ok": bool(matches),
            "request": request_text,
            "interface": "natural_language",
            "matches": [intent_match_to_dict(match, registry) for match in matches],
        }
        if not matches:
            payload["message"] = (
                "No controlled workflow route matched this request. Rephrase with the desired outcome, "
                "backend, or artifact type, or inspect the workflow catalogue."
            )
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print_human_intent_payload(payload)
            return 1
        if args.run:
            hub_call_id = append_hub_start(
                args.reasoning_log_file,
                mode="ask-run",
                target=matches[0].route.route_id,
                dry_run=args.dry_run,
            )
            context = RunContext(
                dry_run=args.dry_run,
                json_output=args.json,
                keep_going=args.keep_going,
                allow_mutating=args.allow_mutating,
                write_report=args.write_report,
            )
            run_payload = run_intent_match(matches[0], registry, context)
            payload = dict(payload)
            payload["selected_route_id"] = matches[0].route.route_id
            payload["run"] = run_payload
            if args.write_report:
                report_path = write_report(f"ask_{matches[0].route.route_id}", payload)
                payload["report_file"] = rel(report_path)
            append_hub_complete(
                args.reasoning_log_file,
                skill_call_id=hub_call_id,
                mode="ask-run",
                target=matches[0].route.route_id,
                payload=run_payload,
                report_file=payload.get("report_file"),
            )
            emit_result(payload if args.json else run_payload, json_output=args.json)
            return 0 if run_payload.get("ok", False) else 1
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print_human_intent_payload(payload)
        return 0

    if args.command == "show":
        item = registry.get(args.action_id)
        if item is None:
            payload = {
                "schema_version": 1,
                "ok": False,
                "error": f"unknown action: {args.action_id}",
            }
            print(
                json.dumps(payload, indent=2, sort_keys=True)
                if args.json
                else payload["error"]
            )
            return 2
        payload = {"schema_version": 1, "ok": True, "action": action_to_dict(item)}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(json.dumps(payload["action"], indent=2, sort_keys=True))
        return 0

    if args.command == "audit":
        payload = audit_control(registry)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"{'PASS' if payload['ok'] else 'FAIL'} workflow-control audit")
            if payload["uncontrolled_entrypoints"]:
                print("Uncontrolled entrypoints:")
                for path in payload["uncontrolled_entrypoints"]:
                    print(f"  - {path}")
        return 0 if payload["ok"] or not args.strict else 1

    if args.command == "run":
        absorb_run_options(args)
        hub_call_id = append_hub_start(
            args.reasoning_log_file,
            mode="run",
            target=args.action_id,
            dry_run=args.dry_run,
        )
        context = RunContext(
            dry_run=args.dry_run,
            json_output=args.json,
            keep_going=args.keep_going,
            allow_mutating=args.allow_mutating,
            write_report=args.write_report,
        )
        extra_args = normalize_extra_args(args.extra_args)
        payload = run_action(args.action_id, registry, context, extra_args=extra_args)
        if args.write_report:
            report_path = write_report(args.action_id, payload)
            payload = dict(payload)
            payload["report_file"] = rel(report_path)
        append_hub_complete(
            args.reasoning_log_file,
            skill_call_id=hub_call_id,
            mode="run",
            target=args.action_id,
            payload=payload,
            report_file=payload.get("report_file"),
        )
        emit_result(payload, json_output=args.json)
        return 0 if payload.get("ok", False) else 1

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
