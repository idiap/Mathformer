#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make Mathformer's agentic workflow structure inspectable as a graph rather
#   than as scattered prose, skill manifests, and hook lists.
#
# Intent:
#   Generate a portable JSON model and self-contained HTML report following the
#   workflow graph visualization contract used by project-local agents.
#
# Function:
#   Builds workflow-family, stack, hook, reusable-skill, and reflective-loop
#   graph elements from a controlled Mathformer workflow catalogue.
#
# Maintenance Notes:
#   Keep workflow definitions synchronized with docs/architecture/AGENTIC_HUB.md and the
#   skills directory when new major loop contracts are added.

"""Render Mathformer agentic workflow graph reports."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import html
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "workflow_graphs"
HOOKS_FILE = REPO_ROOT / "skills" / "SKILL_HOOKS.yaml"


@dataclass(frozen=True)
class Step:
    """One ordered skill hook inside a workflow stack."""

    skill: str
    role: str
    posture: str
    output: str
    description: str
    trigger: str = "workflow handoff"


@dataclass(frozen=True)
class Workflow:
    """One workflow stack in the agentic graph model."""

    stack_id: str
    label: str
    family: str
    description: str
    trigger: str
    artifact_entrypoints: Sequence[str]
    steps: Sequence[Step]
    reflective_edges: Sequence[Dict[str, str]]


MANUAL_WORKFLOWS: Sequence[Workflow] = (
    Workflow(
        stack_id="sympy-physics-derivation-trace-loop",
        label="SymPy Physics Derivation Trace Loop",
        family="Physics And SymPy",
        description="Turns a physics derivation into executable SymPy inference steps, residual checks, reports, and refinement evidence.",
        trigger="physics source or FormalPhysics case needs SymPy autoformalization",
        artifact_entrypoints=(
            "backends/sympy/MathformerPhysicsSympy/pipeline.py",
            "artifacts/physics_sympy/*/core_equational_reasoning.py",
            "artifacts/physics_sympy/*/core_reasoning_refinement_loop.json",
        ),
        steps=(
            Step(
                "physics-derivation-source-extractor",
                "extractor",
                "deterministic",
                "evidence_packet",
                "Extract source statement, proof lines, equations, and anchors.",
            ),
            Step(
                "physics-symbol-table-builder",
                "extractor",
                "deterministic",
                "evidence_packet",
                "Bind quantities, symbols, and generated support variables.",
            ),
            Step(
                "physics-dimension-modeler",
                "guard",
                "deterministic",
                "gate_decision",
                "Build quantity dimensions and unit expectations.",
            ),
            Step(
                "physics-equation-parser",
                "extractor",
                "both",
                "evidence_packet",
                "Parse source and generated equations into executable surfaces.",
            ),
            Step(
                "physics-sympy-derivation-drafter",
                "writer",
                "both",
                "report_artifact",
                "Draft executable SymPy inference steps aligned with informal proof.",
            ),
            Step(
                "physics-sympy-equational-semantics-critic",
                "critic",
                "both",
                "finding",
                "Check whether SymPy equations preserve source semantics.",
            ),
            Step(
                "physics-sympy-review-refinement-router",
                "refiner",
                "both",
                "workflow_update",
                "Route localized repairs back to the core inference artifact.",
            ),
            Step(
                "autoformalization-reflective-refinement-loop",
                "refiner",
                "both",
                "workflow_update",
                "Run explicit generate-critique-refine-retest cycles for the core SymPy artifact.",
            ),
            Step(
                "physics-sympy-final-equation-reviewer",
                "guard",
                "both",
                "gate_decision",
                "Review final equations, residuals, and physical interpretation.",
            ),
            Step(
                "physics-derivation-consistency-report-orchestrator",
                "writer",
                "deterministic",
                "report_artifact",
                "Assemble JSON, Markdown, HTML, RFDE, and refinement-loop evidence.",
            ),
        ),
        reflective_edges=(
            {
                "from": "physics-sympy-equational-semantics-critic",
                "to": "physics-sympy-derivation-drafter",
                "output": "finding",
            },
            {
                "from": "physics-sympy-review-refinement-router",
                "to": "physics-sympy-derivation-drafter",
                "output": "workflow_update",
            },
            {
                "from": "physics-sympy-final-equation-reviewer",
                "to": "physics-sympy-review-refinement-router",
                "output": "gate_decision",
            },
        ),
    ),
    Workflow(
        stack_id="draft-execute-refine-loop",
        label="Draft Execute Refine Loop",
        family="Control And Refinement",
        description="General autoformalization loop from source packet to draft, backend execution, critique, localized repair, and re-test.",
        trigger="a formal artifact needs backend-checked refinement",
        artifact_entrypoints=(
            "skills/autoformalization/autoformalization-workflow-orchestrator",
            "skills/autoformalization/autoformalization-reflective-refinement-loop",
        ),
        steps=(
            Step(
                "autoformalization-workflow-orchestrator",
                "orchestrator",
                "both",
                "workflow_context",
                "Choose backend, criteria, and controlled execution plan.",
            ),
            Step(
                "lean-autoformalization-drafter",
                "writer",
                "generative",
                "report_artifact",
                "Draft formal artifact when the backend is Lean.",
            ),
            Step(
                "lean-execution-runner",
                "guard",
                "deterministic",
                "gate_decision",
                "Execute Lean and capture diagnostics.",
            ),
            Step(
                "lean-semantic-preservation-critic",
                "critic",
                "generative",
                "finding",
                "Critique meaning preservation.",
            ),
            Step(
                "lean-formal-refinement",
                "refiner",
                "both",
                "workflow_update",
                "Apply localized proof or statement repair.",
            ),
            Step(
                "autoformalization-reflective-refinement-loop",
                "refiner",
                "both",
                "workflow_update",
                "Run explicit critique-refine-retest cycles.",
            ),
            Step(
                "autoformalization-result-realness-verifier",
                "guard",
                "deterministic",
                "gate_decision",
                "Block mocked or placeholder results.",
            ),
        ),
        reflective_edges=(
            {
                "from": "lean-semantic-preservation-critic",
                "to": "lean-formal-refinement",
                "output": "finding",
            },
            {
                "from": "autoformalization-reflective-refinement-loop",
                "to": "autoformalization-workflow-orchestrator",
                "output": "workflow_update",
            },
        ),
    ),
    Workflow(
        stack_id="artifact-acceptance-loop",
        label="Artifact Acceptance Loop",
        family="Control And Refinement",
        description="Checks a candidate artifact for import discipline, reverse informalization, non-vacuity, and consistency status.",
        trigger="candidate artifact is ready for acceptance review",
        artifact_entrypoints=(
            "docs/architecture/AGENTIC_HUB.md",
            "artifacts/*/*.report.json",
        ),
        steps=(
            Step(
                "mathlib-import-minimizer",
                "guard",
                "deterministic",
                "gate_decision",
                "Minimize and verify imports.",
            ),
            Step(
                "lean-informalization-extractor",
                "extractor",
                "both",
                "evidence_packet",
                "Extract an informal view from formal artifact.",
            ),
            Step(
                "lean-nonvacuity-consistency-checker",
                "critic",
                "deterministic",
                "finding",
                "Detect vacuity and trivial target restatement.",
            ),
            Step(
                "lean-consistency-report-orchestrator",
                "writer",
                "deterministic",
                "report_artifact",
                "Aggregate acceptance evidence.",
            ),
            Step(
                "final-derivation-review-orchestrator",
                "guard",
                "both",
                "gate_decision",
                "Coordinate final acceptance review.",
            ),
            Step(
                "gate-policy-controller",
                "guard",
                "deterministic",
                "gate_decision",
                "Normalize final accept, warn, fail, and waiver status.",
            ),
        ),
        reflective_edges=(
            {
                "from": "lean-nonvacuity-consistency-checker",
                "to": "lean-consistency-report-orchestrator",
                "output": "finding",
            },
            {
                "from": "final-derivation-review-orchestrator",
                "to": "mathlib-import-minimizer",
                "output": "gate_decision",
            },
        ),
    ),
    Workflow(
        stack_id="mathlib-grounding-loop",
        label="Mathlib Grounding Loop",
        family="Lean And Mathlib",
        description="Maps source concepts to mathlib declarations, import plans, verified candidates, and explicit gaps.",
        trigger="Lean drafting needs library grounding",
        artifact_entrypoints=("skills/mathlib-*", "artifacts/mathlib_*"),
        steps=(
            Step(
                "mathlib-concept-candidate-mapper",
                "extractor",
                "both",
                "evidence_packet",
                "Rank candidate declarations.",
            ),
            Step(
                "mathlib-hierarchy-navigator",
                "extractor",
                "both",
                "evidence_packet",
                "Navigate local module hierarchy.",
            ),
            Step(
                "mathlib-import-set-builder",
                "planner",
                "deterministic",
                "plan_or_todo",
                "Build an import plan.",
            ),
            Step(
                "mathlib-candidate-verifier",
                "guard",
                "deterministic",
                "gate_decision",
                "Verify selected declarations with Lean checks.",
            ),
            Step(
                "mathlib-grounding-maximizer",
                "refiner",
                "both",
                "workflow_update",
                "Improve concept-to-library coverage.",
            ),
            Step(
                "mathlib-concept-coverage-reviewer",
                "critic",
                "both",
                "finding",
                "Review remaining coverage gaps.",
            ),
        ),
        reflective_edges=(
            {
                "from": "mathlib-concept-coverage-reviewer",
                "to": "mathlib-grounding-maximizer",
                "output": "finding",
            },
            {
                "from": "mathlib-grounding-maximizer",
                "to": "mathlib-concept-candidate-mapper",
                "output": "workflow_update",
            },
        ),
    ),
    Workflow(
        stack_id="premise-selection-loop",
        label="Premise Selection Loop",
        family="ATP And Premise Selection",
        description="Builds theorem memory, indexes fact corpora, and searches nearby premises for ATP or formalization tasks.",
        trigger="theorem proof needs premise memory or semantic retrieval",
        artifact_entrypoints=("MathformerKB", "artifacts/premise_kb"),
        steps=(
            Step(
                "premise-kb-theorem-seed-generator",
                "writer",
                "generative",
                "evidence_packet",
                "Generate theorem and axiom seed facts.",
            ),
            Step(
                "premise-kb-indexer",
                "extractor",
                "deterministic",
                "workflow_update",
                "Index facts into exact and vector memory.",
            ),
            Step(
                "vampire-atp-orchestrator",
                "orchestrator",
                "deterministic",
                "gate_decision",
                "Use selected premises for ATP proof search when applicable.",
            ),
            Step(
                "vampire-proof-informalizer",
                "writer",
                "generative",
                "report_artifact",
                "Explain formal ATP proof artifacts.",
            ),
        ),
        reflective_edges=(
            {
                "from": "vampire-atp-orchestrator",
                "to": "premise-kb-indexer",
                "output": "finding",
            },
        ),
    ),
    Workflow(
        stack_id="reflection-testing-loop",
        label="Reflection Testing Loop",
        family="Observability",
        description="Turns run evidence and RFDE observations into monotonic improvements to agents, tests, and workflow gates.",
        trigger="workflow evidence suggests an improvement or regression risk",
        artifact_entrypoints=(
            "artifacts/*reasoning*",
            "docs/architecture/AGENT_DYNAMICS_REPORT.md",
        ),
        steps=(
            Step(
                "reasoning-log-schema-guardian",
                "guard",
                "deterministic",
                "gate_decision",
                "Validate structured reasoning events.",
            ),
            Step(
                "reference-free-critic-monitor",
                "critic",
                "deterministic",
                "finding",
                "Track benchmark-free evolution measures.",
            ),
            Step(
                "skill-hook-coverage-maximizer",
                "critic",
                "deterministic",
                "finding",
                "Audit hook and skill reachability.",
            ),
            Step(
                "skill-test-program-orchestrator",
                "orchestrator",
                "both",
                "gate_decision",
                "Run deterministic and content-quality probes.",
            ),
            Step(
                "gate-policy-controller",
                "guard",
                "deterministic",
                "gate_decision",
                "Normalize pass, warn, fail, and waiver decisions.",
            ),
        ),
        reflective_edges=(
            {
                "from": "reference-free-critic-monitor",
                "to": "skill-hook-coverage-maximizer",
                "output": "finding",
            },
            {
                "from": "gate-policy-controller",
                "to": "reasoning-log-schema-guardian",
                "output": "gate_decision",
            },
            {
                "from": "skill-test-program-orchestrator",
                "to": "agentic-hub-contracts",
                "output": "workflow_update",
            },
        ),
    ),
    Workflow(
        stack_id="workflow-graph-reporting-layout-loop",
        label="Workflow Graph Reporting And Layout Loop",
        family="Observability",
        description="Turns workflow contracts into graph JSON, layout plans, clutter critiques, and readable HTML reports.",
        trigger="operator asks for workflow graph, skill coverage visualization, or layout repair",
        artifact_entrypoints=(
            "scripts/render_workflow_graphs.py",
            "scripts/plan_workflow_graph_layout.py",
            "scripts/audit_workflow_skill_integration.py",
            "artifacts/workflow_graphs",
        ),
        steps=(
            Step(
                "project-workflow-graph-reporter",
                "orchestrator",
                "deterministic",
                "workflow_context",
                "Coordinate graph extraction, modeling, rendering, and validation.",
            ),
            Step(
                "workflow-contract-extractor",
                "extractor",
                "deterministic",
                "evidence_packet",
                "Extract workflow stacks, hooks, and reflective-loop hints.",
            ),
            Step(
                "workflow-graph-modeler",
                "extractor",
                "deterministic",
                "evidence_packet",
                "Build the typed workflow graph representation.",
            ),
            Step(
                "workflow-layout-rationalizer",
                "planner",
                "deterministic",
                "plan_or_todo",
                "Choose lanes, overlays, and spacing from graph semantics.",
            ),
            Step(
                "workflow-layout-clutter-critic",
                "critic",
                "deterministic",
                "finding",
                "Diagnose visual clutter and edge pressure.",
            ),
            Step(
                "workflow-graph-html-reporter",
                "writer",
                "deterministic",
                "report_artifact",
                "Render the Cytoscape HTML explorer and static cards.",
            ),
            Step(
                "project-workflow-layout-reasoner",
                "refiner",
                "deterministic",
                "workflow_update",
                "Close the layout reasoning loop and validate readability.",
            ),
        ),
        reflective_edges=(
            {
                "from": "workflow-layout-clutter-critic",
                "to": "workflow-layout-rationalizer",
                "output": "finding",
            },
            {
                "from": "project-workflow-layout-reasoner",
                "to": "project-workflow-graph-reporter",
                "output": "workflow_update",
            },
        ),
    ),
)


def humanize(value: str) -> str:
    """Render identifiers as human-readable labels."""
    return value.replace("$", "").replace("_", " ").replace("-", " ").title()


def skill_descriptions(repository_root: Path = REPO_ROOT) -> Dict[str, str]:
    """Read skill descriptions from local SKILL.md files."""
    descriptions: Dict[str, str] = {}
    skill_files = [
        *sorted((repository_root / "skills").glob("*/*/SKILL.md")),
        *sorted((repository_root / "proj_skills").glob("*/SKILL.md")),
    ]
    for skill_file in skill_files:
        text = skill_file.read_text(encoding="utf-8", errors="ignore")
        name_match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
        desc_match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        name = name_match.group(1).strip() if name_match else skill_file.parent.name
        if desc_match:
            descriptions[name] = desc_match.group(1).strip()
    return descriptions


def skill_inventory(repository_root: Path = REPO_ROOT) -> Dict[str, Any]:
    """Read the full local skill inventory without adding all skills to the graph."""
    skills: List[Dict[str, str]] = []
    skill_files = [
        *sorted((repository_root / "skills").glob("*/*/SKILL.md")),
        *sorted((repository_root / "proj_skills").glob("*/SKILL.md")),
    ]
    for skill_file in skill_files:
        text = skill_file.read_text(encoding="utf-8", errors="ignore")
        name_match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
        desc_match = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
        name = name_match.group(1).strip() if name_match else skill_file.parent.name
        skills.append(
            {
                "name": name,
                "path": str(skill_file.relative_to(repository_root)),
                "description": desc_match.group(1).strip() if desc_match else "",
            }
        )
    return {"total": len(skills), "skills": skills}


def list_values_after_key(lines: Sequence[str], key: str) -> List[str]:
    """Read a YAML-ish list following ``key:`` without requiring PyYAML."""
    values: List[str] = []
    in_block = False
    base_indent = 0
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not in_block:
            if re.match(rf"^\s*{re.escape(key)}:\s*$", raw):
                in_block = True
                base_indent = len(raw) - len(raw.lstrip())
            continue
        indent = len(raw) - len(raw.lstrip())
        if indent <= base_indent and not stripped.startswith("- "):
            break
        if stripped.startswith("- "):
            values.append(stripped[2:].strip())
    return values


def parse_hooks_manifest(path: Path = HOOKS_FILE) -> Dict[str, Any]:
    """Parse the hook registry enough to seed workflow graph stacks."""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    hooks: Dict[str, Dict[str, Any]] = {}
    direct_routes: Dict[str, str] = {}
    loop_contracts: List[Dict[str, Any]] = []
    current_section = ""
    current_hook: Dict[str, Any] | None = None
    current_loop: Dict[str, Any] | None = None
    current_list: str | None = None

    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "hooks:":
            current_section = "hooks"
            current_hook = None
            current_loop = None
            current_list = None
            continue
        if stripped == "loop_contracts:":
            current_section = "loop_contracts"
            current_hook = None
            current_loop = None
            current_list = None
            continue
        if stripped == "direct_request_routing:":
            current_section = "direct_request_routing"
            current_hook = None
            current_loop = None
            current_list = None
            continue

        if current_section == "hooks":
            match = re.match(r"^-\s+id:\s*(\S+)\s*$", stripped)
            if match:
                current_hook = {
                    "id": match.group(1),
                    "owner_skill": "",
                    "phase": "",
                    "trigger": "",
                    "outputs": [],
                }
                hooks[current_hook["id"]] = current_hook
                current_list = None
                continue
            if current_hook is None:
                continue
            key_value = re.match(r"^([A-Za-z0-9_]+):\s*(.*?)\s*$", stripped)
            if key_value:
                key, value = key_value.groups()
                if value:
                    current_hook[key] = value
                    current_list = None
                else:
                    current_hook.setdefault(key, [])
                    current_list = key
                continue
            if stripped.startswith("- ") and current_list:
                current_hook.setdefault(current_list, []).append(stripped[2:].strip())
            continue

        if current_section == "loop_contracts":
            match = re.match(r"^-\s+id:\s*(\S+)\s*$", stripped)
            if match:
                current_loop = {
                    "id": match.group(1),
                    "description": "",
                    "required_hooks": [],
                    "recommended_hooks": [],
                    "required_owner_skills": [],
                }
                loop_contracts.append(current_loop)
                current_list = None
                continue
            if current_loop is None:
                continue
            key_value = re.match(r"^([A-Za-z0-9_]+):\s*(.*?)\s*$", stripped)
            if key_value:
                key, value = key_value.groups()
                if value:
                    current_loop[key] = value
                    current_list = None
                else:
                    current_loop.setdefault(key, [])
                    current_list = key
                continue
            if stripped.startswith("- ") and current_list:
                current_loop.setdefault(current_list, []).append(stripped[2:].strip())
            continue

        if current_section == "direct_request_routing" and ":" in stripped:
            key, value = stripped.split(":", 1)
            direct_routes[key.strip()] = value.strip()

    return {
        "hooks": hooks,
        "loop_contracts": loop_contracts,
        "direct_routes": direct_routes,
        "shared_runtime_scripts": list_values_after_key(
            lines, "shared_runtime_scripts"
        ),
    }


def role_for_skill(skill: str) -> str:
    """Infer a graph role from a skill name."""
    if any(term in skill for term in ("orchestrator", "workflow")):
        return "orchestrator"
    if any(
        term in skill
        for term in (
            "critic",
            "reviewer",
            "audit",
            "verifier",
            "checker",
            "validator",
            "guard",
        )
    ):
        return "critic"
    if any(term in skill for term in ("refine", "repair", "router", "maximizer")):
        return "refiner"
    if any(term in skill for term in ("drafter", "generator", "writer", "docs")):
        return "writer"
    if any(
        term in skill
        for term in (
            "extractor",
            "parser",
            "indexer",
            "navigator",
            "mapper",
            "builder",
            "modeler",
            "grounder",
        )
    ):
        return "extractor"
    if any(term in skill for term in ("planner", "plan")):
        return "planner"
    return "agent"


def output_for_role(role: str) -> str:
    """Map inferred roles to report output types."""
    return {
        "orchestrator": "workflow_context",
        "critic": "finding",
        "refiner": "workflow_update",
        "writer": "report_artifact",
        "extractor": "evidence_packet",
        "planner": "plan_or_todo",
        "agent": "workflow_update",
    }[role]


def posture_for_skill(skill: str) -> str:
    """Infer whether the hook is deterministic, generative, or hybrid."""
    if any(
        term in skill
        for term in ("drafter", "generator", "critic", "reviewer", "refinement")
    ):
        return "both"
    return "deterministic"


def family_for_loop(loop_id: str) -> str:
    """Assign loop-contract workflows to graph families."""
    if "physics" in loop_id and "sympy" in loop_id:
        return "Physics And SymPy"
    if "physics" in loop_id:
        return "Physics Derivation Backends"
    if any(
        term in loop_id
        for term in (
            "mathlib",
            "lean",
            "mathformerlib",
            "draft_execute",
            "artifact_acceptance",
        )
    ):
        return "Lean, Mathlib, And MathformerLib"
    if any(term in loop_id for term in ("sympy",)):
        return "SymPy Symbolic Backend"
    if any(term in loop_id for term in ("control", "reflection")):
        return "Control, Gates, And Observability"
    if any(term in loop_id for term in ("textbook", "preformalization")):
        return "Source Intake, Expansion, And Theory Extraction"
    return "Controlled Loop Contracts"


def workflow_from_loop(
    loop: Dict[str, Any], hooks: Dict[str, Dict[str, Any]], descriptions: Dict[str, str]
) -> Workflow:
    """Create one rendered workflow stack from a hook-registry loop contract."""
    skills = list(dict.fromkeys(loop.get("required_owner_skills", [])))
    hook_ids = loop.get("required_hooks", [])
    steps: List[Step] = []
    for index, skill in enumerate(skills):
        hook = hooks.get(hook_ids[index], {}) if index < len(hook_ids) else {}
        role = role_for_skill(skill)
        description = (
            descriptions.get(skill) or hook.get("trigger") or f"Run {humanize(skill)}."
        )
        steps.append(
            Step(
                skill=skill,
                role=role,
                posture=posture_for_skill(skill),
                output=output_for_role(role),
                description=description,
                trigger=hook.get("trigger", "loop contract handoff"),
            )
        )
    return Workflow(
        stack_id=str(loop["id"]).replace("_", "-"),
        label=humanize(str(loop["id"])),
        family=family_for_loop(str(loop["id"])),
        description=str(
            loop.get("description") or f"Canonical loop contract {loop['id']}."
        ),
        trigger="canonical loop contract from skills/SKILL_HOOKS.yaml",
        artifact_entrypoints=("skills/SKILL_HOOKS.yaml",),
        steps=tuple(steps),
        reflective_edges=(),
    )


def integration_surface_workflow(
    modeled: set[str],
    inventory: Dict[str, Any],
    manifest: Dict[str, Any],
    descriptions: Dict[str, str],
) -> Workflow | None:
    """Create a final workflow for integrated skills not owned by loop contracts."""
    direct_route_skills = set(manifest["direct_routes"].values())
    runtime_skills = {
        parts[1]
        for script in manifest["shared_runtime_scripts"]
        for parts in [script.split("/")]
        if len(parts) >= 3 and parts[0] == "skills"
    }
    remaining = [
        item["name"] for item in inventory["skills"] if item["name"] not in modeled
    ]
    ordered = sorted(
        remaining,
        key=lambda skill: (
            skill not in direct_route_skills,
            skill not in runtime_skills,
            skill,
        ),
    )
    if not ordered:
        return None
    steps = []
    for skill in ordered:
        role = role_for_skill(skill)
        evidence = (
            "direct route"
            if skill in direct_route_skills
            else (
                "shared runtime"
                if skill in runtime_skills
                else "project-local reporting"
            )
        )
        steps.append(
            Step(
                skill=skill,
                role=role,
                posture=posture_for_skill(skill),
                output=output_for_role(role),
                description=descriptions.get(skill, f"Integrated through {evidence}."),
                trigger=evidence,
            )
        )
    return Workflow(
        stack_id="direct-route-runtime-and-project-surface",
        label="Direct Route Runtime And Project Surface",
        family="Control, Gates, And Observability",
        description="Skills integrated through direct request routes, shared runtime scripts, compatibility wrappers, or project-local reporting surfaces rather than canonical loop ownership.",
        trigger="inventory integration coverage",
        artifact_entrypoints=("skills/SKILL_HOOKS.yaml", "proj_skills"),
        steps=tuple(steps),
        reflective_edges=(),
    )


def workflow_catalogue(
    descriptions: Dict[str, str],
    inventory: Dict[str, Any],
    hooks_file: Path = HOOKS_FILE,
) -> Sequence[Workflow]:
    """Build the rendered workflow catalogue from canonical contracts plus project-local loops."""
    manifest = parse_hooks_manifest(hooks_file)
    workflows: List[Workflow] = [
        workflow_from_loop(loop, manifest["hooks"], descriptions)
        for loop in manifest["loop_contracts"]
        if loop.get("required_owner_skills")
    ]
    existing_ids = {workflow.stack_id for workflow in workflows}
    for workflow in MANUAL_WORKFLOWS:
        if workflow.stack_id not in existing_ids:
            workflows.append(workflow)
            existing_ids.add(workflow.stack_id)
    modeled = {step.skill for workflow in workflows for step in workflow.steps}
    integration_workflow = integration_surface_workflow(
        modeled, inventory, manifest, descriptions
    )
    if integration_workflow:
        workflows.append(integration_workflow)
    return tuple(workflows)


def edge_id(source: str, target: str, edge_type: str) -> str:
    """Build a stable graph edge identifier."""
    return f"edge:{edge_type}:{source}:{target}".replace(" ", "-")


def add_edge(
    edges: List[Dict[str, Any]],
    source: str,
    target: str,
    edge_type: str,
    output: str,
    label: str,
) -> None:
    """Append one typed edge."""
    edges.append(
        {
            "data": {
                "id": edge_id(source, target, edge_type),
                "source": source,
                "target": target,
                "edge_type": edge_type,
                "output_type": output,
                "label": label,
            }
        }
    )


def load_catalogue(repository_root: Path = REPO_ROOT) -> Dict[str, Any]:
    """Read native inputs in their original order; pack workflows for MCP transport."""
    descriptions = skill_descriptions(repository_root)
    inventory = skill_inventory(repository_root)
    workflows = workflow_catalogue(
        descriptions, inventory, repository_root / "skills/SKILL_HOOKS.yaml"
    )
    return {
        "descriptions": descriptions,
        "inventory": inventory,
        "workflows": [asdict(workflow) for workflow in workflows],
    }


def build_model() -> Dict[str, Any]:
    """Build the workflow graph JSON model."""
    return assemble_model(load_catalogue(REPO_ROOT))


def assemble_model(catalogue: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the model using the same finite native graph traversals."""
    descriptions = catalogue["descriptions"]
    inventory = catalogue["inventory"]
    workflows = [
        Workflow(**{**row, "steps": [Step(**step) for step in row["steps"]]})
        for row in catalogue["workflows"]
    ]
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    families = sorted({workflow.family for workflow in workflows})
    skill_use_counter: Counter[str] = Counter()
    role_counter: Counter[str] = Counter()
    stacks: Dict[str, Any] = {}

    for family in families:
        family_id = f"family:{family.lower().replace(' ', '-')}"
        nodes.append(
            {
                "data": {
                    "id": family_id,
                    "label": family,
                    "node_type": "family",
                    "family": family,
                    "description": f"Workflow family for {family}.",
                    "detailed_description": f"Groups workflow stacks in the {family} part of Mathformer.",
                }
            }
        )

    for workflow in workflows:
        family_id = f"family:{workflow.family.lower().replace(' ', '-')}"
        workflow_id = f"workflow:{workflow.stack_id}"
        reflective = bool(workflow.reflective_edges)
        nodes.append(
            {
                "data": {
                    "id": workflow_id,
                    "label": workflow.label,
                    "node_type": "workflow",
                    "family": workflow.family,
                    "stack": workflow.label,
                    "description": workflow.description,
                    "detailed_description": workflow.description,
                    "trigger": workflow.trigger,
                    "artifact_entrypoints": list(workflow.artifact_entrypoints),
                    "reflective": reflective,
                }
            }
        )
        add_edge(
            edges,
            family_id,
            workflow_id,
            "family_contains_workflow",
            "workflow_group",
            "groups workflow",
        )
        stacks[workflow.stack_id] = {
            "label": workflow.label,
            "family": workflow.family,
            "description": workflow.description,
            "trigger": workflow.trigger,
            "artifact_entrypoints": list(workflow.artifact_entrypoints),
            "reflective": reflective,
            "ordered_hooks": [],
            "reflective_edges": list(workflow.reflective_edges),
        }
        previous_step_id = None
        for index, step in enumerate(workflow.steps, start=1):
            skill_use_counter[step.skill] += 1
            role_counter[step.role] += 1
            step_id = f"step:{workflow.stack_id}:{index:02d}"
            skill_id = f"skill:{step.skill}"
            nodes.append(
                {
                    "data": {
                        "id": step_id,
                        "label": f"{index}. {humanize(step.skill)}",
                        "node_type": "workflow_step",
                        "family": workflow.family,
                        "stack": workflow.label,
                        "skill": step.skill,
                        "role": step.role,
                        "execution_posture": step.posture,
                        "output_type": step.output,
                        "description": step.description,
                        "detailed_description": step.description,
                        "sequence_index": index,
                        "trigger": step.trigger,
                    }
                }
            )
            add_edge(
                edges,
                workflow_id,
                step_id,
                "workflow_entry" if index == 1 else "workflow_sequence",
                step.output,
                "starts with" if index == 1 else "passes output",
            )
            if previous_step_id:
                add_edge(
                    edges,
                    previous_step_id,
                    step_id,
                    "skill_handoff",
                    step.output,
                    f"hands off {step.output}",
                )
            previous_step_id = step_id
            stacks[workflow.stack_id]["ordered_hooks"].append(
                {
                    "index": index,
                    "skill": step.skill,
                    "role": step.role,
                    "execution_posture": step.posture,
                    "output_type": step.output,
                    "description": step.description,
                }
            )
            nodes.append(
                {
                    "data": {
                        "id": skill_id,
                        "label": humanize(step.skill),
                        "node_type": "skill",
                        "skill": step.skill,
                        "role": step.role,
                        "execution_posture": step.posture,
                        "output_type": step.output,
                        "description": descriptions.get(step.skill, step.description),
                        "detailed_description": descriptions.get(
                            step.skill, step.description
                        ),
                    }
                }
            )
            add_edge(
                edges,
                workflow_id,
                skill_id,
                "stack_uses_skill",
                step.output,
                f"invokes {step.output}",
            )

        step_by_skill = {
            step.skill: f"step:{workflow.stack_id}:{index:02d}"
            for index, step in enumerate(workflow.steps, start=1)
        }
        for feedback in workflow.reflective_edges:
            source = step_by_skill.get(feedback["from"], f"external:{feedback['from']}")
            target = step_by_skill.get(feedback["to"], f"external:{feedback['to']}")
            if source.startswith("external:"):
                nodes.append(
                    {
                        "data": {
                            "id": source,
                            "label": humanize(feedback["from"]),
                            "node_type": "external_ref",
                            "stack": workflow.label,
                        }
                    }
                )
            if target.startswith("external:"):
                nodes.append(
                    {
                        "data": {
                            "id": target,
                            "label": humanize(feedback["to"]),
                            "node_type": "external_ref",
                            "stack": workflow.label,
                        }
                    }
                )
            if source.startswith("external:") or target.startswith("external:"):
                add_edge(
                    edges,
                    source,
                    target,
                    "reflective_external_reference",
                    feedback["output"],
                    f"leaves view as {feedback['output']}",
                )
            else:
                add_edge(
                    edges,
                    source,
                    target,
                    "workflow_reflective_loop",
                    feedback["output"],
                    f"returns {feedback['output']}",
                )

    unique_nodes = {node["data"]["id"]: node for node in nodes}
    shared_skills = sorted(
        skill for skill, count in skill_use_counter.items() if count > 1
    )
    modeled_skills = sorted(skill_use_counter)
    available_skills = sorted(item["name"] for item in inventory["skills"])
    unmodeled_skills = [
        skill for skill in available_skills if skill not in skill_use_counter
    ]
    summary = {
        "stacks": len(workflows),
        "total_hooks": sum(len(workflow.steps) for workflow in workflows),
        "modeled_skills": len(skill_use_counter),
        "available_skills": inventory["total"],
        "unmodeled_skills": len(unmodeled_skills),
        "shared_skills": len(shared_skills),
        "reflective_stacks": sum(
            1 for workflow in workflows if workflow.reflective_edges
        ),
        "families": len(families),
    }
    return {
        "repo": "mathformer",
        "source_document": "docs/architecture/AGENTIC_HUB.md",
        "summary": summary,
        "families": {
            family: [
                workflow.stack_id for workflow in workflows if workflow.family == family
            ]
            for family in families
        },
        "skill_inventory": {
            "total": inventory["total"],
            "modeled": modeled_skills,
            "unmodeled": unmodeled_skills,
            "note": "The graph models major workflow-stack hooks, not every project skill.",
        },
        "shared_skills": [
            {"skill": skill, "use_count": skill_use_counter[skill]}
            for skill in shared_skills
        ],
        "reflection_role_counts": dict(role_counter),
        "graph": {
            "library_recommendation": "Cytoscape.js",
            "library_reason": "Workflow stacks are semantically typed ordered graphs with hierarchy, reuse, and reflection edges.",
            "layout_strategy": {
                "drilldown": "preset workflow -> ordered hook steps, with optional reflection edges",
            },
            "edge_semantics": {
                "family_contains_workflow": "Family contains workflow.",
                "workflow_entry": "Workflow starts at first hook.",
                "workflow_sequence": "Ordered hook-to-hook sequence.",
                "skill_handoff": "One skill output feeds another.",
                "stack_uses_skill": "Workflow stack invokes reusable skill.",
                "workflow_reflective_loop": "Critic, refiner, or guard returns evidence to an earlier step.",
                "reflective_external_reference": "Reflective edge leaves the local workflow view.",
            },
            "edge_label_taxonomy": {
                "family_contains_workflow": "groups {output}",
                "workflow_entry": "starts with {output}",
                "workflow_sequence": "passes {output}",
                "skill_handoff": "hands off {output}",
                "stack_uses_skill": "invokes {output}",
                "workflow_reflective_loop": "returns {output}",
                "reflective_external_reference": "leaves view as {output}",
            },
            "views": {
                "drilldown": "Click one workflow to inspect its ordered steps and reflective loops.",
            },
            "elements": {"nodes": list(unique_nodes.values()), "edges": edges},
        },
        "stacks": stacks,
    }


def summary_cards(summary: Dict[str, Any]) -> str:
    """Render summary card HTML."""
    labels = {
        "stacks": "Workflow Stacks",
        "total_hooks": "Total Hooks",
        "modeled_skills": "Modeled Skills",
        "available_skills": "Available Skills",
        "unmodeled_skills": "Unmodeled Skills",
        "shared_skills": "Shared Skills",
        "reflective_stacks": "Reflective Stacks",
        "families": "Workflow Families",
    }
    return "\n".join(
        f'<article class="card"><strong>{html.escape(str(value))}</strong><span>{html.escape(labels[key])}</span></article>'
        for key, value in summary.items()
    )


def workflow_cards(model: Dict[str, Any]) -> str:
    """Render static fallback workflow cards."""
    cards = []
    for stack_id, stack in model["stacks"].items():
        hooks = "\n".join(
            f"<li><b>{hook['index']}. {html.escape(humanize(hook['skill']))}</b> <span>{html.escape(hook['role'])} / {html.escape(hook['execution_posture'])}</span><p>{html.escape(hook['description'])}</p></li>"
            for hook in stack["ordered_hooks"]
        )
        loops = (
            "\n".join(
                f"<li>{html.escape(edge['from'])} returns {html.escape(edge['output'])} to {html.escape(edge['to'])}</li>"
                for edge in stack["reflective_edges"]
            )
            or "<li>No reflective edge declared.</li>"
        )
        cards.append(f"""
<details class="workflow-card">
  <summary>{html.escape(stack['label'])} <em>{html.escape(stack['family'])}</em></summary>
  <p>{html.escape(stack['description'])}</p>
  <h4>Ordered Hooks</h4>
  <ol>{hooks}</ol>
  <h4>Reflective Loops</h4>
  <ul>{loops}</ul>
</details>
""")
    return "\n".join(cards)


def render_html(model: Dict[str, Any]) -> str:
    """Render the workflow graph HTML report."""
    embedded = json.dumps(model, ensure_ascii=False).replace("</", "<\\/")
    cards = summary_cards(model["summary"])
    stacks = workflow_cards(model)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mathformer Workflow Graphs</title>
  <script defer src="https://unpkg.com/cytoscape@3.28.1/dist/cytoscape.min.js"></script>
  <style>
    :root {{
      --ink: #182235;
      --muted: #5e6878;
      --line: #d8dee9;
      --paper: #ffffff;
      --blue: #234f8f;
      --green: #2f7d4f;
      --gold: #bd8429;
      --soft: #eef5f2;
    }}
    body {{ margin: 0; font: 15px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); background: linear-gradient(180deg, #eef5ff, #fff 360px); }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 36px 24px 70px; }}
    h1 {{ margin: 0 0 8px; color: var(--blue); font-size: 34px; border-left: 8px solid var(--green); padding-left: 16px; }}
    h2 {{ margin-top: 32px; color: var(--blue); border-top: 1px solid var(--line); padding-top: 18px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 24px 0; }}
    .card {{ background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; }}
    .card strong {{ display: block; color: var(--green); font-size: 28px; }}
    .card span, .muted {{ color: var(--muted); }}
    .graph-toolbar {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px; background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; margin-top: 14px; }}
    .graph-toolbar label {{ font-weight: 650; color: var(--blue); }}
    .graph-toolbar .toggle {{ color: var(--muted); font-weight: 500; }}
    select {{ border: 1px solid var(--line); border-radius: 6px; padding: 7px 9px; min-width: min(100%, 380px); background: #fff; }}
    .view-note {{ min-height: 1.4em; color: var(--muted); }}
    #cy {{ height: 620px; border: 1px solid var(--line); background: #fff; border-radius: 8px; }}
    #details {{ margin-top: 14px; background: var(--paper); border: 1px solid var(--line); border-left: 5px solid var(--green); border-radius: 8px; padding: 14px 16px; min-height: 90px; }}
    .workflow-card {{ background: #fff; border: 1px solid var(--line); border-radius: 8px; margin: 12px 0; padding: 12px 14px; }}
    .workflow-card summary {{ cursor: pointer; font-weight: 700; color: var(--blue); }}
    .workflow-card em {{ color: var(--muted); font-style: normal; margin-left: 8px; }}
    li span {{ color: var(--muted); }}
    code {{ background: #f6f8fa; border: 1px solid #e5e7eb; border-radius: 4px; padding: 0.1rem 0.25rem; }}
  </style>
</head>
<body>
<main>
  <h1>Mathformer Workflow Graphs</h1>
  <p class="muted">A portable workflow explorer for ordered agent stacks, reusable skills, and reflective loops.</p>
  <section class="cards">{cards}</section>
  <h2>Skill Integration Review</h2>
  <p>
    The graph intentionally visualizes selected major workflow stacks, not every local skill.
    <strong>{model["summary"].get("modeled_skills", 0)}</strong> skills are modeled as graph hooks,
    while <strong>{model["summary"].get("available_skills", 0)}</strong> skills are available locally.
    Most non-visualized skills are still integrated through hook ownership, direct routes, shared runtime scripts,
    or AgenticHub documentation.
  </p>
  <p>
    See <a href="workflow_skill_integration_audit.md">workflow_skill_integration_audit.md</a>
    and <a href="workflow_skill_integration_audit.json">workflow_skill_integration_audit.json</a>
    for the critical coverage review.
  </p>
  <h2>Graph Explorer</h2>
  <p>Select a workflow to inspect its ordered hooks. Turn on reflection only when you want to see feedback loops around the selected workflow.</p>
  <div class="graph-toolbar">
    <label for="workflow-select">Workflow</label>
    <select id="workflow-select"></select>
    <label class="toggle"><input id="show-labels" type="checkbox" checked> labels</label>
    <label class="toggle"><input id="show-reflection" type="checkbox"> reflection</label>
  </div>
  <p id="view-note" class="view-note"></p>
  <div id="cy"></div>
  <section id="details">Click a workflow, skill, step, or edge to inspect its metadata.</section>
  <h2>Static Workflow Stack Cards</h2>
  {stacks}
  <h2>JSON Model</h2>
  <p>The JSON model is embedded below and also emitted as <code>workflow_graphs.json</code>.</p>
  <script type="application/json" id="workflow-graph-model">{embedded}</script>
</main>
<script>
window.addEventListener('DOMContentLoaded', () => {{
  const model = JSON.parse(document.getElementById('workflow-graph-model').textContent);
  const allElements = [...model.graph.elements.nodes, ...model.graph.elements.edges];
  const details = document.getElementById('details');
  const workflowSelect = document.getElementById('workflow-select');
  const labelToggle = document.getElementById('show-labels');
  const reflectionToggle = document.getElementById('show-reflection');
  const viewNote = document.getElementById('view-note');
  Object.entries(model.stacks).forEach(([stackId, stack]) => {{
    const option = document.createElement('option');
    option.value = stackId;
    option.textContent = stack.label;
    workflowSelect.appendChild(option);
  }});
  function currentStack() {{
    return model.stacks[workflowSelect.value];
  }}
  const cy = cytoscape({{
    container: document.getElementById('cy'),
    elements: allElements,
    style: [
      {{ selector: 'node', style: {{ label: 'data(label)', 'font-size': 11, 'text-wrap': 'wrap', 'text-max-width': 150, 'background-color': '#dbeafe', 'border-width': 1, 'border-color': '#94a3b8', width: 38, height: 38 }} }},
      {{ selector: 'node[node_type = "family"]', style: {{ 'background-color': '#234f8f', color: '#234f8f', width: 54, height: 54, 'font-size': 13 }} }},
      {{ selector: 'node[node_type = "workflow"]', style: {{ 'background-color': '#2f7d4f', color: '#17412a', width: 48, height: 48 }} }},
      {{ selector: 'node[node_type = "workflow_step"]', style: {{ 'background-color': '#f6d58b', color: '#4a3511', shape: 'round-rectangle', width: 116, height: 46, 'text-max-width': 108 }} }},
      {{ selector: 'node[node_type = "skill"]', style: {{ 'background-color': '#e9d5ff', color: '#4c1d95', shape: 'hexagon' }} }},
      {{ selector: 'node[node_type = "external_ref"]', style: {{ 'background-color': '#fee2e2', shape: 'diamond' }} }},
      {{ selector: 'edge', style: {{ width: 1.4, label: '', 'font-size': 8, 'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'line-color': '#94a3b8', 'target-arrow-color': '#94a3b8' }} }},
      {{ selector: 'edge[edge_type = "workflow_reflective_loop"]', style: {{ 'line-style': 'dashed', 'line-color': '#bd8429', 'target-arrow-color': '#bd8429', width: 2.2 }} }}
      ,{{ selector: 'edge[edge_type = "reflective_external_reference"]', style: {{ 'line-style': 'dashed', 'line-color': '#dc2626', 'target-arrow-color': '#dc2626', width: 2.2 }} }}
    ],
    layout: {{ name: 'cose', nodeRepulsion: 26000, idealEdgeLength: 180, padding: 70 }}
  }});
  function showDetails(evt) {{
    const d = evt.target.data();
    const rows = Object.entries(d).filter(([k]) => !['id', 'source', 'target'].includes(k)).map(([k, v]) => `<dt>${{k}}</dt><dd>${{Array.isArray(v) ? v.join('<br>') : v}}</dd>`).join('');
    details.innerHTML = `<h3>${{d.label || d.id}}</h3><dl>${{rows}}</dl>`;
  }}
  cy.on('tap', 'node, edge', showDetails);
  function selectedWorkflowIds() {{
    const stackId = workflowSelect.value;
    const stack = currentStack();
    const ids = new Set([`workflow:${{stackId}}`]);
    cy.nodes().forEach(node => {{
      const d = node.data();
      if (d.node_type === 'workflow_step' && d.stack === stack.label) ids.add(d.id);
      if (d.node_type === 'external_ref' && d.stack === stack.label && reflectionToggle.checked) ids.add(d.id);
    }});
    return ids;
  }}
  function selectedEdgeTypes(baseTypes) {{
    const types = new Set(baseTypes);
    if (reflectionToggle.checked) {{
      types.add('workflow_reflective_loop');
      types.add('reflective_external_reference');
    }}
    return types;
  }}
  function showSubset(ids, edgeTypes) {{
    cy.elements().hide();
    cy.nodes().forEach(node => {{
      if (ids.has(node.id())) node.show();
    }});
    cy.edges().forEach(edge => {{
      if (edgeTypes.has(edge.data('edge_type')) && ids.has(edge.source().id()) && ids.has(edge.target().id())) edge.show();
    }});
  }}
  function applyDrilldownPreset() {{
    const stack = currentStack();
    const visibleSteps = cy.nodes('[node_type = "workflow_step"]:visible').sort((a, b) => (a.data('sequence_index') || 0) - (b.data('sequence_index') || 0));
    const stepPositions = new Map();
    const columns = Math.min(5, Math.max(1, visibleSteps.length));
    const startX = 145;
    const gapX = 220;
    const rowY = [150, 360, 570];
    visibleSteps.forEach((node, order) => {{
      const row = Math.floor(order / columns);
      const colInRow = order % columns;
      const col = row % 2 === 0 ? colInRow : columns - 1 - colInRow;
      const position = {{ x: startX + col * gapX, y: rowY[row] || rowY[rowY.length - 1] + (row - rowY.length + 1) * 190 }};
      node.position(position);
      stepPositions.set(node.data('skill'), position);
    }});
    cy.nodes('[node_type = "workflow"]:visible').positions(() => {{ return {{ x: 55, y: 255 }}; }});
    cy.nodes('[node_type = "external_ref"]:visible').positions((node, index) => {{ return {{ x: 1260, y: 110 + index * 150 }}; }});
    cy.zoom(1);
    cy.pan({{ x: 35, y: 25 }});
  }}
  function applyLabels() {{
    const show = labelToggle.checked;
    cy.nodes().style('label', show ? 'data(label)' : '');
    cy.edges().style('label', '');
    if (show) {{
      cy.edges('[edge_type = "workflow_reflective_loop"], [edge_type = "reflective_external_reference"]').style('label', 'data(label)');
    }}
  }}
  function renderDrilldown() {{
    const drilldownEdgeTypes = selectedEdgeTypes(['workflow_entry', 'skill_handoff']);
    drilldownEdgeTypes.delete('stack_uses_skill');
    showSubset(selectedWorkflowIds(), drilldownEdgeTypes);
    viewNote.textContent = `Click drill-down uses an explicit lane layout for: ${{currentStack().label}}. Reusable skill nodes stay hidden so the selected workflow remains readable.`;
    applyLabels();
    applyDrilldownPreset();
  }}
  workflowSelect.addEventListener('change', renderDrilldown);
  labelToggle.addEventListener('change', renderDrilldown);
  reflectionToggle.addEventListener('change', renderDrilldown);
  renderDrilldown();
}});
</script>
</body>
</html>
"""


def write_outputs(output_dir: Path) -> Dict[str, Any]:
    """Write workflow graph JSON and HTML files."""
    prepare_directory(str(output_dir), Path("."))
    model = build_model()
    return publish_model(output_dir, model, REPO_ROOT)


def prepare_directory(output_dir: str, repository_root: Path = REPO_ROOT) -> Path:
    """Resolve then create the native output directory before any input reads."""
    path = Path(output_dir)
    path = path if path.is_absolute() else repository_root / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def publish_model(
    output_dir: Path, model: Dict[str, Any], repository_root: Path = REPO_ROOT
) -> Dict[str, Any]:
    """Write JSON, then HTML, then construct relative report paths."""
    json_path = output_dir / "workflow_graphs.json"
    html_path = output_dir / "workflow_graphs.html"
    json_path.write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    html_path.write_text(render_html(model), encoding="utf-8")
    return {
        "ok": True,
        "json_path": str(json_path.relative_to(repository_root)),
        "html_path": str(html_path.relative_to(repository_root)),
        "summary": model["summary"],
    }


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    output_dir = (
        args.output_dir
        if args.output_dir.is_absolute()
        else REPO_ROOT / args.output_dir
    )
    report = write_outputs(output_dir)
    return emit_report(report, args.json)


def emit_report(report: Dict[str, Any], json_output: bool) -> int:
    """Keep native stdout and exit status in one shared completion boundary."""
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {report['ok']}")
        print(f"json: {report['json_path']}")
        print(f"html: {report['html_path']}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
