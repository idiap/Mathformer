#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Build the named Mathformer workflows as fresh, layered PRISM projects."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from reasoning_projection_specs import PROJECTIONS

REPOSITORY = Path(__file__).resolve().parents[2]
SKILLS = REPOSITORY / "skills"
HOOK_CONTRACT = SKILLS / "SKILL_HOOKS.yaml"
PROJECTION_SPEC = Path(__file__).with_name("reviewed_reasoning_projections.json")
SEMANTIC_SOURCES = (
    SKILLS / "SKILL_HOOKS.yaml",
    SKILLS / "SKILL_TYPES.yaml",
    SKILLS / "OUTPUT_TYPES.yaml",
    SKILLS / "REASONING_TYPES.yaml",
    PROJECTION_SPEC,
)
EXECUTABLE_SUFFIXES = {
    ".bash",
    ".js",
    ".mjs",
    ".pl",
    ".py",
    ".rb",
    ".sh",
    ".ts",
    ".zsh",
}
GENERIC_TYPES = {
    "Task",
    "Input",
    "Output",
    "Data",
    "Payload",
    "State",
    "Result",
    "ConversionTask",
    "WorkflowTask",
}


# These are genuine model-dependent commitments. Every other hook is represented
# as a computed material binding descriptor, not as an LLM invocation.
EPISTEMIC_HOOKS = {
    "preformalization.paper_theory_expand",
    "preformalization.expansion_support",
    "preformalization.expansion_web_support",
    "preformalization.expand",
    "preformalization.review.suite",
    "preformalization.review.completeness",
    "preformalization.review.bindings",
    "draft.textbook_chapter_autoformalization",
    "draft.textbook_batch_autoformalize",
    "draft.textbook_object_autoformalization_run",
    "mathlib.compatibility_loop",
    "mathlib.web_grounding_loop",
    "mathlib.api_plan",
    "draft.initial",
    "critique.semantic",
    "critique.syntax",
    "critique.semantic_preservation",
    "critique.logical_soundness",
    "critique.mathlib_alignment",
    "critique.suite",
    "refine.formal",
    "refine.semantic",
    "output.denoise",
    "draft.sympy_initial",
    "critique.physics_sympy_semantics",
    "physics.sympy.design_guard.review",
    "refine.physics_sympy_review",
    "library.physics.coherence.repair_plan",
    "critique.physics_lean_semantics",
    "critique.physics_lean_generative_panel",
    "refine.physics_lean_review",
    "reflection.process_refinement",
}


BOUNDARY_TYPES = {
    "control_validation_loop": (
        "MathformerControlSurfaceSnapshot",
        "MathformerControlValidationDecision",
    ),
    "preformalization_readiness_loop": (
        "PaperFormalizationSourceSelection",
        "LeanDraftingReadinessDisposition",
    ),
    "textbook_theory_autoformalization_loop": (
        "LatexTextbookArchiveSelection",
        "TextbookAutoformalizationAcceptanceSummary",
    ),
    "mathlib_grounding_loop": (
        "LeanFormalizationConceptDemand",
        "MathlibGroundingDisposition",
    ),
    "draft_execute_refine_loop": (
        "LeanFormalizationDraftBrief",
        "LeanRefinementOutcome",
    ),
    "artifact_acceptance_loop": (
        "LeanArtifactAcceptanceRequest",
        "LeanArtifactAcceptanceDecision",
    ),
    "lean_consistency_testing_loop": (
        "CompiledLeanArtifactSet",
        "LeanConsistencyAssessment",
    ),
    "sympy_equational_trace_loop": (
        "SympyEquationFormalizationRequest",
        "SympyEquationalTraceAssessment",
    ),
    "sympy_physics_derivation_trace_loop": (
        "PhysicsSympyDerivationRequest",
        "PhysicsSympyConsistencyAssessment",
    ),
    "mathformerphysicslib_coherence_grounding_loop": (
        "MathformerPhysicsLibrarySnapshot",
        "MathformerPhysicsLibraryCoherenceDisposition",
    ),
    "lean_physics_derivation_trace_loop": (
        "PhysicsLeanDerivationRequest",
        "PhysicsLeanConsistencyAssessment",
    ),
    "isabelle_physics_derivation_trace_loop": (
        "PhysicsIsabelleDerivationRequest",
        "PhysicsIsabelleConsistencyAssessment",
    ),
    "mathformerlib_accumulation_loop": (
        "MathformerLibraryCandidateSet",
        "MathformerLibraryAccumulationDisposition",
    ),
    "reflection_testing_loop": (
        "MathformerWorkflowTrajectoryEvidence",
        "MathformerProcessImprovementDisposition",
    ),
}


INPUT_FIELDS = {
    "MathformerControlSurfaceSnapshot": (
        (
            "hook_registry_digest",
            "Digest of the canonical hook and loop-contract registry.",
        ),
        (
            "routing_registry_digest",
            "Digest of the controlled natural-language routing registry.",
        ),
        (
            "requested_checks",
            "Ordered control checks requested for this validation run.",
        ),
    ),
    "PaperFormalizationSourceSelection": (
        (
            "source_paths",
            "Selected paper or source paths that delimit formalization scope.",
        ),
        (
            "target_backend",
            "Formal proof backend targeted by the readiness assessment.",
        ),
        (
            "formalization_scope",
            "Human-readable scope for theory extraction and expansion.",
        ),
    ),
    "LatexTextbookArchiveSelection": (
        (
            "archive_paths",
            "Selected LaTeX textbook archives and their source identity.",
        ),
        (
            "target_chapters",
            "Chapter identifiers selected for the autoformalization batch.",
        ),
        ("target_backend", "Formal proof backend targeted by generated textbook jobs."),
    ),
    "LeanFormalizationConceptDemand": (
        (
            "concepts",
            "Concepts and declarations required by the proposed Lean artifact.",
        ),
        (
            "mathlib_revision",
            "Exact mathlib revision against which grounding is requested.",
        ),
        (
            "target_context",
            "Lean import and namespace context constraining candidate APIs.",
        ),
    ),
    "LeanFormalizationDraftBrief": (
        ("source_claims", "Source-anchored mathematical claims to formalize in Lean."),
        ("target_context", "Lean module, imports, namespace, and version constraints."),
        (
            "acceptance_criteria",
            "Criteria that candidate revisions must satisfy before acceptance.",
        ),
    ),
    "LeanArtifactAcceptanceRequest": (
        ("artifact_paths", "Lean artifacts submitted to the acceptance workflow."),
        (
            "source_anchors",
            "Source locations against which semantic drift is assessed.",
        ),
        (
            "acceptance_policy",
            "Named policy fixing required checks and blocking findings.",
        ),
    ),
    "CompiledLeanArtifactSet": (
        ("artifact_paths", "Compiled Lean artifacts selected for consistency testing."),
        (
            "compiler_evidence",
            "References to Lean compilation evidence for the exact artifacts.",
        ),
        (
            "consistency_scope",
            "Declared cross-file and source-alignment scope of the assessment.",
        ),
    ),
    "SympyEquationFormalizationRequest": (
        ("equations", "Mathematical equations selected for SymPy formalization."),
        (
            "symbol_assumptions",
            "Declared assumptions constraining symbols and transformations.",
        ),
        (
            "target_identity",
            "Identity or result that execution and counterexample search assess.",
        ),
    ),
    "PhysicsSympyDerivationRequest": (
        (
            "source_derivation",
            "Source-anchored informal physics derivation to represent in SymPy.",
        ),
        (
            "physical_context",
            "Units, dimensions, frames, regimes, and assumptions in scope.",
        ),
        (
            "target_quantity",
            "Physical quantity or equation targeted by the derivation.",
        ),
    ),
    "MathformerPhysicsLibrarySnapshot": (
        (
            "module_paths",
            "MathformerPhysicsLib modules included in the coherence snapshot.",
        ),
        (
            "mathlib_revision",
            "Mathlib revision used for grounding and redefinition checks.",
        ),
        (
            "coherence_policy",
            "Named criteria for API, integration, and conceptual coherence.",
        ),
    ),
    "PhysicsLeanDerivationRequest": (
        (
            "source_derivation",
            "Source-anchored informal physics derivation to formalize in Lean.",
        ),
        (
            "physical_context",
            "Units, dimensions, frames, regimes, and assumptions in scope.",
        ),
        (
            "lean_context",
            "Lean version, imports, namespace, and target theorem context.",
        ),
    ),
    "PhysicsIsabelleDerivationRequest": (
        (
            "source_derivation",
            "Source-anchored informal physics derivation to formalize in Isabelle.",
        ),
        (
            "physical_context",
            "Units, dimensions, frames, regimes, and assumptions in scope.",
        ),
        ("isabelle_context", "Isabelle session, imports, and target theorem context."),
    ),
    "MathformerLibraryCandidateSet": (
        (
            "candidate_paths",
            "Candidate formal artifacts proposed for MathformerLib accumulation.",
        ),
        (
            "registry_revision",
            "Exact library registry revision used by promotion checks.",
        ),
        (
            "promotion_policy",
            "Named policy defining realness and promotion requirements.",
        ),
    ),
    "MathformerWorkflowTrajectoryEvidence": (
        (
            "run_identifiers",
            "Workflow run identifiers included in reflective analysis.",
        ),
        (
            "baseline_digest",
            "Digest of the successful baseline that revisions must preserve.",
        ),
        (
            "observed_regressions",
            "Observed regressions or unresolved failures motivating revision.",
        ),
    ),
}


# Reviewed material order corrections where the hook registry is an inventory,
# not an executable dependency order.  Hook coverage remains in canonical
# registry order; only the typed material composition uses these sequences.
MATERIAL_ORDER_OVERRIDES = {
    "textbook_theory_autoformalization_loop": [
        "intake_latex_archive_theory_extract",
        "preformalization_textbook_theory_organize",
        "draft_textbook_chapter_autoformalization",
        "draft_textbook_batch_autoformalize",
        "preformalization_line_translation_packet",
        "preformalization_result_existence_precheck",
        "draft_textbook_object_autoformalization_run",
        "mathlib_grounding_maximize",
        "execute_initial",
        "check_compile",
        "postformalization_source_anchor_drift_guard",
        "artifact_realness_gate",
        "consistency_unified_report",
    ],
    "mathformerlib_accumulation_loop": [
        "artifact_realness_gate",
        "mathformerlib_promotion_gate",
        "mathformerlib_accumulate",
        "mathformerlib_registry",
        "library_documentation",
        "library_aligned_html_documentation",
    ],
}


def identifier(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    if not result:
        raise ValueError(f"cannot normalize identifier {value!r}")
    return f"workflow_{result}" if result[0].isdigit() else result


def pascal(value: str) -> str:
    result = "".join(
        part[:1].upper() + part[1:] for part in re.findall(r"[A-Za-z0-9]+", value)
    )
    if not result:
        raise ValueError(f"cannot normalize type name {value!r}")
    return f"Workflow{result}" if result[0].isdigit() else result


def digest_files(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(REPOSITORY).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def taxonomy_description(value: str, subject: str) -> str:
    """Meet the taxonomy prose contract without altering PRISM type labels."""
    text = value.strip()
    if len(text) >= 20:
        return text
    return f"{text.rstrip('.')} retained by the typed {subject} record."


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def frontmatter_first(text: str, source: Path) -> str:
    delimiters = list(re.finditer(r"(?m)^---[ \t]*\r?$", text))
    if len(delimiters) < 2:
        raise ValueError(f"{source} has no complete YAML frontmatter")
    opening, closing = delimiters[0], delimiters[1]
    frontmatter = text[opening.start() : closing.end()]
    preamble = text[: opening.start()].strip()
    body = text[closing.end() :].lstrip("\r\n")
    return (
        "\n\n".join(part for part in (frontmatter, preamble, body) if part).rstrip()
        + "\n"
    )


def discover_skills() -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in sorted(SKILLS.glob("*/*/SKILL.md")):
        name = path.parent.name
        if name in result:
            raise ValueError(f"duplicate canonical skill {name}")
        result[name] = path
    return result


def linked_resources(skill_file: Path) -> list[str]:
    resources: list[str] = []
    for path in sorted(skill_file.parent.rglob("*")):
        if path == skill_file or path.is_dir():
            continue
        if path.is_symlink() or path.suffix.lower() in EXECUTABLE_SUFFIXES:
            resources.append(path.relative_to(REPOSITORY).as_posix())
    return resources


def stage_skill(skill_file: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    write_text(
        destination / "SKILL.md",
        frontmatter_first(skill_file.read_text(encoding="utf-8"), skill_file),
    )
    for source in sorted(skill_file.parent.rglob("*")):
        if source == skill_file or source.is_dir() or source.is_symlink():
            continue
        if source.suffix.lower() in EXECUTABLE_SUFFIXES:
            continue
        target = destination / source.relative_to(skill_file.parent)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def category(hook_id: str) -> str:
    lowered = hook_id.lower()
    if any(
        part in lowered
        for part in (
            "critique",
            "review",
            "consistency",
            "validate",
            "verify",
            "check",
            "audit",
        )
    ):
        return "assessment"
    if any(
        part in lowered for part in ("draft", "refine", "formaliz", "expand", "denoise")
    ):
        return "candidate"
    if any(
        part in lowered
        for part in (
            "ground",
            "search",
            "discover",
            "navigate",
            "index",
            "extract",
            "parse",
        )
    ):
        return "retrieval"
    if any(part in lowered for part in ("plan", "strategy", "repair")):
        return "plan"
    if any(
        part in lowered for part in ("gate", "policy", "route", "promotion", "accept")
    ):
        return "decision"
    return "operation"


def stage_fields(hook_id: str) -> list[dict[str, str]]:
    fields = [
        {
            "name": "subject",
            "type": "String",
            "description": f"Exact subject processed by the {hook_id} occurrence.",
        },
        {
            "name": "source_anchors",
            "type": "List[String]",
            "description": f"Source anchors retained by the {hook_id} occurrence.",
        },
        {
            "name": "declared_artifacts",
            "type": "List[String]",
            "description": f"Artifact labels declared by the canonical {hook_id} contract.",
        },
        {
            "name": "gate_disposition",
            "type": "String",
            "description": f"Disposition under the explicit gate attached to {hook_id}.",
        },
        {
            "name": "limitations",
            "type": "List[String]",
            "description": f"Known limitations that constrain use of the {hook_id} result.",
        },
    ]
    extras = {
        "assessment": (
            (
                "criteria",
                "List[String]",
                "Named criteria applied by this scoped assessment.",
            ),
            (
                "findings",
                "List[String]",
                "Scoped findings with no authority beyond their cited grounds.",
            ),
            (
                "recommended_repairs",
                "List[String]",
                "Non-authoritative repairs proposed for identified findings.",
            ),
        ),
        "candidate": (
            (
                "candidate_content",
                "String",
                "Candidate transformation or artifact produced for later checks.",
            ),
            (
                "unresolved_obligations",
                "List[String]",
                "Obligations that remain before the candidate can be accepted.",
            ),
        ),
        "retrieval": (
            (
                "candidate_references",
                "List[String]",
                "Retrieved or extracted candidates with retained identifiers.",
            ),
            (
                "selection_basis",
                "String",
                "Named retrieval, parsing, or grounding basis used for selection.",
            ),
            (
                "exclusions",
                "List[String]",
                "Relevant candidates excluded together with their stated reason.",
            ),
        ),
        "plan": (
            (
                "directives",
                "List[String]",
                "Prospective directives that remain unauthoritative until executed.",
            ),
            (
                "dependencies",
                "List[String]",
                "Dependencies that constrain ordering or feasibility of the plan.",
            ),
            (
                "blockers",
                "List[String]",
                "Current blockers that prevent safe execution of plan directives.",
            ),
        ),
        "decision": (
            (
                "considered_dispositions",
                "List[String]",
                "Dispositions considered by the named workflow gate.",
            ),
            (
                "selected_disposition",
                "String",
                "Policy-selected disposition without creating object-level evidence.",
            ),
            (
                "rationale",
                "String",
                "Scope-bounded rationale for the selected operational disposition.",
            ),
        ),
        "operation": (
            (
                "operation_summary",
                "String",
                "Summary of the linked material operation represented by this record.",
            ),
            (
                "evidence_references",
                "List[String]",
                "References to evidence that a native execution may later produce.",
            ),
        ),
    }[category(hook_id)]
    fields.extend(
        {"name": name, "type": type_name, "description": description}
        for name, type_name, description in extras
    )
    return fields


def input_definition(type_name: str, workflow_id: str) -> dict[str, Any]:
    raw_fields = INPUT_FIELDS[type_name]
    fields = []
    for name, description in raw_fields:
        field_type = (
            "List[String]"
            if name.endswith("s")
            or name
            in {
                "source_paths",
                "archive_paths",
                "source_claims",
                "artifact_paths",
                "module_paths",
                "candidate_paths",
                "run_identifiers",
                "requested_checks",
                "target_chapters",
                "equations",
                "observed_regressions",
                "concepts",
                "source_anchors",
            }
            else "String"
        )
        fields.append({"name": name, "type": field_type, "description": description})
    return {
        "name": type_name,
        "description": f"Domain-specific source boundary for the named {workflow_id} Mathformer workflow.",
        "kind": "record",
        "fields": fields,
    }


def fixture_for(definition: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    fixture: dict[str, Any] = {}
    for field in definition["fields"]:
        fixture[field["name"]] = (
            [f"fixture:{workflow_id}:{field['name']}"]
            if field["type"] == "List[String]"
            else f"fixture:{workflow_id}:{field['name']}"
        )
    return fixture


def reasoning_record(
    name: str,
    description: str,
    fields: list[tuple[str, str, str]],
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "kind": "record",
        "fields": [
            {"name": field, "type": type_name, "description": field_description}
            for field, type_name, field_description in fields
        ],
    }


PROJECTION_FIELDS: dict[str, list[tuple[str, str, str]]] = {
    "observation": [
        (
            "observed_items",
            "List[String]",
            "Source items explicitly observed in the declared scope.",
        ),
        (
            "source_anchors",
            "List[String]",
            "Stable source anchors retained for the observed items.",
        ),
        (
            "unresolved_gaps",
            "List[String]",
            "Source gaps that prevent a complete observation.",
        ),
    ],
    "inventory": [
        (
            "inventoried_items",
            "List[String]",
            "Domain items included in the reviewed inventory.",
        ),
        ("dependencies", "List[String]", "Dependencies among the inventoried items."),
        (
            "inventory_gaps",
            "List[String]",
            "Known omissions or unresolved ownership gaps.",
        ),
    ],
    "interpretation": [
        (
            "interpreted_meanings",
            "List[String]",
            "Domain meanings explicitly attributed to the source.",
        ),
        ("assumptions", "List[String]", "Assumptions required by the interpretation."),
        (
            "validity_regimes",
            "List[String]",
            "Regimes that bound use of the interpretation.",
        ),
    ],
    "model": [
        (
            "modeled_elements",
            "List[String]",
            "Domain elements represented by the explicit model.",
        ),
        ("assumptions", "List[String]", "Assumptions retained by the model."),
        (
            "scope_limits",
            "List[String]",
            "Limits on adequacy or applicability of the model.",
        ),
    ],
    "theory": [
        (
            "theory_units",
            "List[String]",
            "Source-preserving units represented by the organized theory.",
        ),
        (
            "dependencies",
            "List[String]",
            "Dependencies retained among the theory units.",
        ),
        ("unresolved_gaps", "List[String]", "Theory gaps that remain explicit."),
    ],
    "context": [
        (
            "context_elements",
            "List[String]",
            "Domain elements fixed by this explicit context.",
        ),
        ("constraints", "List[String]", "Constraints governing use of the context."),
        ("assumptions", "List[String]", "Assumptions carried by the context."),
    ],
    "obligation": [
        (
            "required_conditions",
            "List[String]",
            "Conditions required before the named downstream use.",
        ),
        (
            "missing_premises",
            "List[String]",
            "Premises required but not established by the source.",
        ),
        (
            "side_conditions",
            "List[String]",
            "Domain or formal side conditions that remain explicit.",
        ),
    ],
    "retrieval": [
        (
            "candidates",
            "List[String]",
            "Retrieved candidates without an applicability claim.",
        ),
        (
            "provenance_refs",
            "List[String]",
            "References identifying candidate provenance.",
        ),
        (
            "unresolved_gaps",
            "List[String]",
            "Requested items for which no candidate was retrieved.",
        ),
    ],
    "grounding": [
        (
            "aligned_items",
            "List[String]",
            "Items with scope-bound applicability or semantic alignment.",
        ),
        (
            "rejected_candidates",
            "List[String]",
            "Candidates rejected by the grounding criteria.",
        ),
        (
            "unresolved_gaps",
            "List[String]",
            "Concepts for which grounding remains unresolved.",
        ),
    ],
    "candidate": [
        (
            "candidate_artifacts",
            "List[String]",
            "Candidate artifacts produced for later checks.",
        ),
        (
            "preserved_requirements",
            "List[String]",
            "Source requirements explicitly retained by the candidate.",
        ),
        (
            "open_obligations",
            "List[String]",
            "Validation obligations that remain open.",
        ),
    ],
    "construction": [
        (
            "constructed_artifacts",
            "List[String]",
            "Artifacts constructed for downstream execution or review.",
        ),
        (
            "preserved_requirements",
            "List[String]",
            "Requirements explicitly retained by the construction.",
        ),
        (
            "open_obligations",
            "List[String]",
            "Validation obligations that remain open.",
        ),
    ],
    "evidence": [
        (
            "evidence_refs",
            "List[String]",
            "Inspectible references to evidence in the declared scope.",
        ),
        (
            "observed_results",
            "List[String]",
            "Results directly observed by the bounded probe or execution.",
        ),
        ("limitations", "List[String]", "Limits on what the evidence can establish."),
    ],
    "assessment": [
        ("criteria", "List[String]", "Named criteria applied by this assessment."),
        (
            "findings",
            "List[String]",
            "Criterion-scoped findings supported by cited inputs.",
        ),
        ("blockers", "List[String]", "Findings that block the named downstream use."),
    ],
    "reflection": [
        (
            "comparisons",
            "List[String]",
            "Scope-bound comparisons among the supplied trajectories or reviews.",
        ),
        (
            "improvement_hypotheses",
            "List[String]",
            "Defeasible hypotheses suggested by the comparison.",
        ),
        (
            "limitations",
            "List[String]",
            "Limits on generalizing the reflective result.",
        ),
    ],
    "plan": [
        (
            "proposed_actions",
            "List[String]",
            "Prospective actions that remain unauthoritative until executed.",
        ),
        (
            "dependencies",
            "List[String]",
            "Dependencies that constrain the proposed actions.",
        ),
        (
            "revalidation_obligations",
            "List[String]",
            "Checks required after executing the plan.",
        ),
    ],
    "decision": [
        ("status", "String", "Scoped policy status selected by calibration."),
        ("blockers", "List[String]", "Blocking findings retained by the decision."),
        (
            "limitations",
            "List[String]",
            "Limits on interpreting or using the decision.",
        ),
    ],
}


def reviewed_reasoning_projection(
    workflow_id: str,
    input_type: str,
    required_hooks: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compile one reviewed declarative projection into the linked-plan shape."""
    raw = PROJECTIONS[workflow_id]
    input_name = str(raw.get("input_name", "workflow_source"))
    stages = list(raw["stages"])
    by_id = {str(item["id"]): item for item in stages}
    if len(by_id) != len(stages):
        raise ValueError(f"{workflow_id}: duplicate projected occurrence id")
    source_types: dict[str, str] = {input_name: input_type}
    definitions: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    mapped_hooks: list[str] = []
    for item in stages:
        occurrence_id = str(item["id"])
        sources = list(item["sources"])
        unknown_sources = sorted(set(sources) - set(source_types))
        if unknown_sources:
            raise ValueError(
                f"{workflow_id}:{occurrence_id}: unavailable projected sources {unknown_sources}"
            )
        if len(sources) == 1 and item.get("input_type") is None:
            occurrence_input_type = source_types[sources[0]]
            arguments = [{"source": sources[0]}]
        else:
            occurrence_input_type = str(item.get("input_type") or "")
            if not occurrence_input_type:
                raise ValueError(
                    f"{workflow_id}:{occurrence_id}: joined sources require input_type"
                )
            fields = [
                (
                    source,
                    source_types[source],
                    f"Reviewed {source.replace('_', ' ')} supplied to {item['method']}.",
                )
                for source in sources
            ]
            definitions.append(
                reasoning_record(
                    occurrence_input_type,
                    f"Reviewed domain inputs required by {item['method']} in {workflow_id}.",
                    fields,
                )
            )
            arguments = [{"field": source, "source": source} for source in sources]
        output_type = str(item["output_type"])
        semantic_kind = str(item["semantic_kind"])
        if semantic_kind not in PROJECTION_FIELDS:
            raise ValueError(
                f"{workflow_id}:{occurrence_id}: unknown semantic kind {semantic_kind}"
            )
        definitions.append(
            reasoning_record(
                output_type,
                f"{item['rationale']} This record retains the authority ceiling of a {semantic_kind} occurrence.",
                PROJECTION_FIELDS[semantic_kind],
            )
        )
        hooks = list(item["material_hooks"])
        unknown_hooks = sorted(set(hooks) - set(required_hooks))
        if unknown_hooks:
            raise ValueError(
                f"{workflow_id}:{occurrence_id}: maps hooks outside the loop {unknown_hooks}"
            )
        mapped_hooks.extend(hooks)
        occurrence = {
            "id": occurrence_id,
            "method": str(item["method"]),
            "input_type": occurrence_input_type,
            "output_type": output_type,
            "semantic_kind": semantic_kind,
            "rationale": str(item["rationale"]),
            "arguments": arguments,
            "material_steps": [identifier(hook) for hook in hooks],
        }
        if item.get("relation") is not None:
            occurrence["relation"] = str(item["relation"])
        occurrences.append(occurrence)
        source_types[occurrence_id] = output_type
    duplicate_hooks = sorted(
        {hook for hook in mapped_hooks if mapped_hooks.count(hook) > 1}
    )
    if duplicate_hooks:
        raise ValueError(
            f"{workflow_id}: projected material hooks overlap {duplicate_hooks}"
        )
    expected_epistemic = set(required_hooks) & EPISTEMIC_HOOKS
    missing_epistemic = sorted(expected_epistemic - set(mapped_hooks))
    if missing_epistemic:
        raise ValueError(
            f"{workflow_id}: projection leaves epistemic hooks orphaned {missing_epistemic}"
        )
    topology_ids = [
        occurrence_id
        for item in raw["topology"]
        for occurrence_id in (item["parallel"] if isinstance(item, dict) else [item])
    ]
    if topology_ids != list(dict.fromkeys(topology_ids)) or set(topology_ids) != set(
        by_id
    ):
        raise ValueError(
            f"{workflow_id}: reviewed topology is incomplete or duplicated"
        )
    output_occurrence = topology_ids[-1]
    if by_id[output_occurrence]["semantic_kind"] != "decision":
        raise ValueError(f"{workflow_id}: reviewed projection must end in calibration")
    projection = {
        "name": str(raw["name"]),
        "description": str(raw["description"]),
        "projection_kind": "generative_interpretation",
        "profile_basis": str(raw["profile_basis"]),
        "projection_scope": str(raw["scope"]),
        "review_status": "approved",
        "input_name": input_name,
        "input_type": input_type,
        "output_occurrence": output_occurrence,
        "output_type": source_types[output_occurrence],
        "occurrences": occurrences,
        "topology": list(raw["topology"]),
    }
    reviewed_definitions = raw.get("type_definitions")
    if reviewed_definitions is not None:
        definitions = list(reviewed_definitions)
    return definitions, projection


def lean_physics_reasoning_projection() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return the reviewed human-scale epistemic projection for Lean physics."""
    definitions = [
        reasoning_record(
            "PhysicsInterpretation",
            "An explicit interpretation of the physical meaning carried by the source derivation.",
            [
                (
                    "physical_assumptions",
                    "List[String]",
                    "Assumptions under which the source derivation is intended to hold.",
                ),
                (
                    "governing_laws",
                    "List[String]",
                    "Physical laws used by the interpreted source derivation.",
                ),
                (
                    "reference_frames",
                    "List[String]",
                    "Reference frames required to interpret the stated quantities.",
                ),
                (
                    "validity_regimes",
                    "List[String]",
                    "Regimes that bound the applicability of the interpreted laws.",
                ),
            ],
        ),
        reasoning_record(
            "ProofObligations",
            "Formal goals and side conditions exposed by the interpreted physical derivation.",
            [
                (
                    "lean_goals",
                    "List[String]",
                    "Lean propositions that the formal derivation must establish.",
                ),
                (
                    "missing_premises",
                    "List[String]",
                    "Source premises required but not yet explicitly represented.",
                ),
                (
                    "side_conditions",
                    "List[String]",
                    "Nonzero, positivity, domain, or other formal side conditions.",
                ),
            ],
        ),
        reasoning_record(
            "GroundingBasis",
            "The physical semantics and formal obligations used to select applicable mathlib declarations.",
            [
                (
                    "physical_semantics",
                    "PhysicsInterpretation",
                    "Interpreted physical meaning whose concepts require library grounding.",
                ),
                (
                    "formalization_obligations",
                    "ProofObligations",
                    "Lean obligations that constrain applicable declarations and imports.",
                ),
            ],
        ),
        reasoning_record(
            "MathlibGrounding",
            "A scope-bound alignment between the formalization demand and existing mathlib APIs.",
            [
                (
                    "declarations",
                    "List[String]",
                    "Mathlib declarations selected as applicable to the formalization.",
                ),
                (
                    "imports",
                    "List[String]",
                    "Narrow imports required for the selected declarations.",
                ),
                (
                    "unresolved_concepts",
                    "List[String]",
                    "Concepts for which no applicable declaration is established.",
                ),
            ],
        ),
        reasoning_record(
            "FormalizationBasis",
            "The interpreted physics, proof obligations, and mathlib alignment used to propose a Lean derivation.",
            [
                (
                    "physical_semantics",
                    "PhysicsInterpretation",
                    "Physical interpretation that the candidate must preserve.",
                ),
                (
                    "formalization_obligations",
                    "ProofObligations",
                    "Formal goals and side conditions the candidate must address.",
                ),
                (
                    "mathlib_alignment",
                    "MathlibGrounding",
                    "Applicable declarations and imports available to the candidate.",
                ),
            ],
        ),
        reasoning_record(
            "LeanDerivation",
            "A candidate Lean representation of the interpreted physical derivation.",
            [
                (
                    "lean_source",
                    "String",
                    "Candidate Lean declarations and proof terms.",
                ),
                (
                    "theorem_names",
                    "List[String]",
                    "Theorems introduced or targeted by the candidate.",
                ),
                (
                    "unresolved_goals",
                    "List[String]",
                    "Goals that remain unresolved in the candidate derivation.",
                ),
            ],
        ),
        reasoning_record(
            "LeanValidityCase",
            "A candidate Lean derivation paired with the obligations used to assess formal validity.",
            [
                (
                    "candidate_derivation",
                    "LeanDerivation",
                    "Candidate whose elaboration and proof obligations are assessed.",
                ),
                (
                    "required_obligations",
                    "ProofObligations",
                    "Formal obligations against which completeness is assessed.",
                ),
            ],
        ),
        reasoning_record(
            "LeanAssessment",
            "A criterion-scoped assessment of the candidate derivation's Lean validity.",
            [
                (
                    "elaboration_findings",
                    "List[String]",
                    "Findings about parsing, elaboration, and declaration resolution.",
                ),
                (
                    "kernel_findings",
                    "List[String]",
                    "Findings about kernel acceptance and proof completeness.",
                ),
                (
                    "unresolved_goals",
                    "List[String]",
                    "Formal goals not discharged by the candidate.",
                ),
            ],
        ),
        reasoning_record(
            "PhysicalFidelityCase",
            "A candidate Lean derivation paired with the intended physical semantics.",
            [
                (
                    "candidate_derivation",
                    "LeanDerivation",
                    "Candidate whose physical interpretation is assessed.",
                ),
                (
                    "intended_semantics",
                    "PhysicsInterpretation",
                    "Physical meaning that the candidate is intended to preserve.",
                ),
            ],
        ),
        reasoning_record(
            "PhysicalAssessment",
            "A criterion-scoped assessment of physical meaning preserved by the Lean candidate.",
            [
                (
                    "semantic_findings",
                    "List[String]",
                    "Findings about preservation of the intended physical meaning.",
                ),
                (
                    "assumption_findings",
                    "List[String]",
                    "Findings about assumptions, frames, and validity regimes.",
                ),
                (
                    "dimension_findings",
                    "List[String]",
                    "Findings about dimensions, units, and physical laws.",
                ),
            ],
        ),
        reasoning_record(
            "AcceptanceCase",
            "The candidate and independent formal and physical assessments used for calibration.",
            [
                (
                    "candidate_derivation",
                    "LeanDerivation",
                    "Candidate to which the calibrated disposition applies.",
                ),
                (
                    "formal_validity",
                    "LeanAssessment",
                    "Assessment of Lean elaboration and proof validity.",
                ),
                (
                    "physical_fidelity",
                    "PhysicalAssessment",
                    "Assessment of physical meaning and applicability.",
                ),
            ],
        ),
        reasoning_record(
            "PhysicsDisposition",
            "A calibrated status for the candidate Lean physics derivation.",
            [
                (
                    "status",
                    "String",
                    "Scoped acceptance, revision, rejection, or blocked status.",
                ),
                (
                    "blockers",
                    "List[String]",
                    "Findings that prevent acceptance in the declared scope.",
                ),
                (
                    "limitations",
                    "List[String]",
                    "Limits on the interpretation or use of the disposition.",
                ),
            ],
        ),
    ]
    groups = {
        "interpreted_problem": [
            "preformalization.expansion_support",
            "preformalization.expansion_web_support",
            "preformalization.expand",
        ],
        "derived_obligations": [
            "preformalization.review.suite",
            "preformalization.review.completeness",
            "preformalization.review.bindings",
        ],
        "grounded_mathlib": [
            "mathlib.compatibility_loop",
            "mathlib.web_grounding_loop",
            "mathlib.api_plan",
        ],
        "lean_candidate": ["refine.formal", "refine.semantic", "output.denoise"],
        "formal_assessment": [
            "critique.semantic",
            "critique.syntax",
            "critique.semantic_preservation",
            "critique.logical_soundness",
            "critique.mathlib_alignment",
            "critique.suite",
        ],
        "physical_assessment": [
            "critique.physics_lean_semantics",
            "critique.physics_lean_generative_panel",
        ],
        "disposition": ["refine.physics_lean_review"],
    }
    material = {
        key: [identifier(item) for item in values] for key, values in groups.items()
    }
    projection = {
        "name": "ReconstructInLean",
        "description": "Interpret a physical derivation, ground it in mathlib, propose Lean, assess formal and physical validity, and calibrate its status.",
        "projection_kind": "generative_interpretation",
        "profile_basis": "physics_derivation_reconstruction",
        "projection_scope": "one Lean reconstruction and assessment episode; detailed repair iteration remains material",
        "review_status": "approved",
        "input_name": "workflow_source",
        "input_type": "PhysicsLeanDerivationRequest",
        "output_occurrence": "disposition",
        "output_type": "PhysicsDisposition",
        "occurrences": [
            {
                "id": "interpreted_problem",
                "method": "InterpretPhysics",
                "input_type": "PhysicsLeanDerivationRequest",
                "output_type": "PhysicsInterpretation",
                "semantic_kind": "interpretation",
                "rationale": "Construct an explicit physical interpretation without claiming that it is adequate.",
                "arguments": [{"source": "workflow_source"}],
                "material_steps": material["interpreted_problem"],
            },
            {
                "id": "derived_obligations",
                "method": "DeriveProofObligations",
                "input_type": "PhysicsInterpretation",
                "output_type": "ProofObligations",
                "semantic_kind": "obligation",
                "relation": "ExposeProofObligations",
                "rationale": "Expose the formal goals, missing premises, and side conditions induced by the interpretation.",
                "arguments": [{"source": "interpreted_problem"}],
                "material_steps": material["derived_obligations"],
            },
            {
                "id": "grounded_mathlib",
                "method": "GroundInMathlib",
                "input_type": "GroundingBasis",
                "output_type": "MathlibGrounding",
                "semantic_kind": "grounding",
                "relation": "AlignWithMathlib",
                "rationale": "Align the physical concepts and proof obligations with applicable mathlib declarations.",
                "arguments": [
                    {"field": "physical_semantics", "source": "interpreted_problem"},
                    {
                        "field": "formalization_obligations",
                        "source": "derived_obligations",
                    },
                ],
                "material_steps": material["grounded_mathlib"],
            },
            {
                "id": "lean_candidate",
                "method": "SynthesizeLeanDerivation",
                "input_type": "FormalizationBasis",
                "output_type": "LeanDerivation",
                "semantic_kind": "candidate",
                "relation": "ProposeFormalization",
                "rationale": "Propose a Lean derivation while retaining unresolved validation obligations.",
                "arguments": [
                    {"field": "physical_semantics", "source": "interpreted_problem"},
                    {
                        "field": "formalization_obligations",
                        "source": "derived_obligations",
                    },
                    {"field": "mathlib_alignment", "source": "grounded_mathlib"},
                ],
                "material_steps": material["lean_candidate"],
            },
            {
                "id": "formal_assessment",
                "method": "AssessLeanValidity",
                "input_type": "LeanValidityCase",
                "output_type": "LeanAssessment",
                "semantic_kind": "assessment",
                "relation": "TestFormalValidity",
                "rationale": "Assess elaboration, kernel acceptance, and obligation coverage of the Lean candidate.",
                "arguments": [
                    {"field": "candidate_derivation", "source": "lean_candidate"},
                    {"field": "required_obligations", "source": "derived_obligations"},
                ],
                "material_steps": material["formal_assessment"],
            },
            {
                "id": "physical_assessment",
                "method": "AssessPhysicalFidelity",
                "input_type": "PhysicalFidelityCase",
                "output_type": "PhysicalAssessment",
                "semantic_kind": "assessment",
                "relation": "TestPhysicalFidelity",
                "rationale": "Assess preservation of physical meaning, assumptions, regimes, dimensions, and laws.",
                "arguments": [
                    {"field": "candidate_derivation", "source": "lean_candidate"},
                    {"field": "intended_semantics", "source": "interpreted_problem"},
                ],
                "material_steps": material["physical_assessment"],
            },
            {
                "id": "disposition",
                "method": "CalibrateAcceptance",
                "input_type": "AcceptanceCase",
                "output_type": "PhysicsDisposition",
                "semantic_kind": "decision",
                "relation": "CalibrateFromAssessments",
                "rationale": "Calibrate a scoped disposition without manufacturing additional evidence or proof.",
                "arguments": [
                    {"field": "candidate_derivation", "source": "lean_candidate"},
                    {"field": "formal_validity", "source": "formal_assessment"},
                    {"field": "physical_fidelity", "source": "physical_assessment"},
                ],
                "material_steps": material["disposition"],
            },
        ],
        "topology": [
            "interpreted_problem",
            "derived_obligations",
            "grounded_mathlib",
            "lean_candidate",
            {"parallel": ["formal_assessment", "physical_assessment"]},
            "disposition",
        ],
    }
    return definitions, projection


def make_model(
    loop: dict[str, Any],
    hooks: dict[str, dict[str, Any]],
    skill_paths: dict[str, Path],
    fingerprint: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    workflow_id = str(loop["id"])
    input_type, final_type = BOUNDARY_TYPES[workflow_id]
    input_def = input_definition(input_type, workflow_id)
    definitions = [input_def]
    steps: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    prior = input_type
    required = list(loop["required_hooks"])
    for index, hook_id in enumerate(required):
        hook = hooks[hook_id]
        output_type = (
            final_type
            if index == len(required) - 1
            else f"{pascal(workflow_id.removesuffix('_loop'))}{pascal(hook_id)}Artifact"
        )
        definitions.append(
            {
                "name": output_type,
                "description": f"Domain-specific result of {hook_id} within the named {workflow_id} workflow.",
                "kind": "record",
                "fields": stage_fields(hook_id),
            }
        )
        epistemic = hook_id in EPISTEMIC_HOOKS
        owner = str(hook["owner_skill"])
        skill_path = skill_paths[owner].parent.relative_to(REPOSITORY).as_posix()
        step_id = identifier(hook_id)
        step = {
            "id": step_id,
            "description": f"Apply the source-defined {hook_id} hook while retaining its gate and artifact contract.",
            "input_type": prior,
            "output_type": output_type,
            "semantic_role": "epistemic" if epistemic else "operational",
            "output_provenance": "generated" if epistemic else "computed",
            "failure_type": "ModelFailure" if epistemic else "Never",
            "effects": ["AI.Generate", "Context.Disclose"] if epistemic else [],
            "granularity_rationale": f"The {hook_id} result is independently gated or consumed before the next named hook.",
            "skills": [
                {
                    "path": skill_path,
                    "role": f"Canonical owner for the {hook_id} hook contract.",
                    "contribution": f"Supplies the source-defined trigger, artifacts, gate, and limitations for {hook_id}.",
                    "resource_dispositions": {
                        path.removeprefix(skill_path + "/"): "linked"
                        for path in linked_resources(skill_paths[owner])
                    },
                }
            ],
        }
        if epistemic:
            step["reasoning_type"] = f"{pascal(hook_id)}Occurrence"
            step["reasoning_rationale"] = (
                f"The {hook_id} occurrence makes a defeasible model-dependent commitment that later gates must assess."
            )
            relation_prefix = {
                "assessment": "Tests",
                "candidate": "Formalizes",
                "retrieval": "Grounds",
                "plan": "Recommends",
                "decision": "Supports",
                "operation": "Synthesizes",
            }[category(hook_id)]
            step["relation_type"] = f"{relation_prefix}{pascal(step_id)}"
        steps.append(step)
        coverage.append(
            {
                "hook_id": hook_id,
                "occurrence_id": step_id,
                "owner_skill": owner,
                "semantic_role": step["semantic_role"],
            }
        )
        prior = output_type
    override = MATERIAL_ORDER_OVERRIDES.get(workflow_id)
    if override is not None:
        if set(override) != {step["id"] for step in steps} or len(override) != len(
            steps
        ):
            raise ValueError(f"{workflow_id}: invalid reviewed material order override")
        steps_by_id = {step["id"]: step for step in steps}
        definition_by_name = {item["name"]: item for item in definitions[1:]}
        steps = [steps_by_id[step_id] for step_id in override]
        prior = input_type
        for step in steps:
            step["input_type"] = prior
            prior = step["output_type"]
        definitions = [input_def] + [
            definition_by_name[step["output_type"]] for step in steps
        ]
    roles = {step["semantic_role"] for step in steps}
    mode = "mixed" if len(roles) > 1 else next(iter(roles))
    reasoning_projection = None
    reasoning_definitions, reasoning_projection = reviewed_reasoning_projection(
        workflow_id,
        input_type,
        required,
    )
    existing_names = {item["name"] for item in definitions}
    reasoning_names = [item["name"] for item in reasoning_definitions]
    duplicates = sorted(
        (existing_names & set(reasoning_names))
        | {name for name in reasoning_names if reasoning_names.count(name) > 1}
    )
    if duplicates:
        raise ValueError(
            f"{workflow_id}: reasoning types duplicate material or projected types: {duplicates}"
        )
    definitions.extend(reasoning_definitions)
    expected_epistemic = {
        step["id"] for step in steps if step["semantic_role"] == "epistemic"
    }
    projected_material = {
        material_step
        for occurrence in reasoning_projection["occurrences"]
        for material_step in occurrence["material_steps"]
    }
    if not expected_epistemic <= projected_material:
        raise ValueError(
            f"{workflow_id}: reasoning projection leaves epistemic material steps "
            f"orphaned: {sorted(expected_epistemic - projected_material)}"
        )
    workflow_model = {
        "id": workflow_id,
        "review_status": "approved",
        "semantic_mode": mode,
        "description": str(loop["description"]).rstrip(".") + ".",
        "input": {
            "name": reasoning_projection["input_name"],
            "type": input_type,
            "fixture": fixture_for(input_def, workflow_id),
        },
        "output": {"type": final_type, "provenance": steps[-1]["output_provenance"]},
        "epistemic_contract": {
            "subject": f"The exact source artifacts and gates traversed by {workflow_id}.",
            "question": f"What typed artifacts and dispositions result from the declared {workflow_id} contract?",
            "observations": [
                "The canonical hook registry fixes hook order, owner skills, declared outputs, and gate text."
            ],
            "defeaters": [
                "A structural or fake-handler run does not establish native execution, mathematical correctness, or semantic equivalence."
            ],
            "defeater_rationale": "Evidence labels remain capped until native adapters and independent behavioral oracles execute.",
            "output_meaning": f"The final domain-specific artifact produced by the layered {workflow_id} shell.",
            "assurance": steps[-1]["output_provenance"],
            "assurance_justification": "Each occurrence preserves its own generated or computed provenance; the final wrapper follows the final occurrence.",
            "unresolved": [],
        },
        "steps": steps,
    }
    workflow_model["reasoning_projection"] = reasoning_projection
    model = {
        "artifact": "workflow-architecture-plan",
        "schema_version": "1.0",
        "source_fingerprint": f"sha256:{fingerprint}",
        "type_definitions": definitions,
        "workflows": [workflow_model],
    }
    projected_roles = {
        occurrence["output_type"]: {
            "observation": "observation",
            "inventory": "observation",
            "interpretation": "mathematical_representation",
            "model": "mathematical_representation",
            "theory": "mathematical_representation",
            "context": "mathematical_representation",
            "obligation": "proposition",
            "retrieval": "retrieval_result",
            "grounding": "retrieval_result",
            "candidate": "formal_representation",
            "construction": "formal_representation",
            "evidence": "evidence",
            "assessment": "critique",
            "reflection": "critique",
            "plan": "recommendation",
            "decision": "decision",
        }[occurrence["semantic_kind"]]
        for occurrence in reasoning_projection["occurrences"]
    }
    objects = []
    for index, definition in enumerate(definitions):
        if index == 0:
            role, provenance = "query", "raw"
        elif index > len(steps):
            provenance = "generated"
            role = projected_roles.get(definition["name"], "operational")
        else:
            step = steps[index - 1]
            provenance = step["output_provenance"]
            role = "operational"
            if step["semantic_role"] == "epistemic":
                role = {
                    "assessment": "critique",
                    "candidate": "formal_representation",
                    "retrieval": "retrieval_result",
                    "plan": "recommendation",
                    "decision": "decision",
                    "operation": "claim",
                }[category(coverage[index - 1]["hook_id"])]
        objects.append(
            {
                "id": identifier(definition["name"]),
                "nominal_type": definition["name"],
                "epistemic_role": role,
                "description": taxonomy_description(
                    definition["description"], definition["name"]
                ),
                "fields": [
                    {
                        **field,
                        "description": taxonomy_description(
                            field["description"], field["name"]
                        ),
                    }
                    for field in definition["fields"]
                ],
                "source_anchors": [
                    f"skills/SKILL_HOOKS.yaml#loop_contracts.{workflow_id}"
                ],
                "provenance": provenance,
                "assurance_justification": "The nominal record retains source identity and does not claim stronger assurance than its producer establishes.",
                "unresolved": [],
            }
        )
    operations = []
    for step, link in zip(steps, coverage, strict=True):
        epistemic = step["semantic_role"] == "epistemic"
        operations.append(
            {
                "id": step["id"],
                "granularity_rationale": step["granularity_rationale"],
                "kind": (
                    {
                        "assessment": "critique",
                        "candidate": "formalize",
                        "retrieval": "retrieve",
                        "plan": "recommend",
                        "decision": "decide",
                        "operation": "synthesize",
                    }[category(link["hook_id"])]
                    if epistemic
                    else "operational"
                ),
                "inference_class": (
                    {
                        "assessment": "material_defeasible",
                        "candidate": "representational",
                        "retrieval": "representational",
                        "plan": "material_defeasible",
                        "decision": "material_defeasible",
                        "operation": "material_defeasible",
                    }[category(link["hook_id"])]
                    if epistemic
                    else "none"
                ),
                "input_types": [step["input_type"]],
                "output_type": step["output_type"],
                "semantic_role": step["semantic_role"],
                "result_provenance": step["output_provenance"],
                "skill_composition": [
                    {
                        key: value
                        for key, value in step["skills"][0].items()
                        if key in {"path", "role", "contribution"}
                    }
                ],
                "rationale": step.get(
                    "reasoning_rationale",
                    f"The {link['hook_id']} occurrence records a deterministic material binding without epistemic inference.",
                ),
                "source_anchors": [f"skills/SKILL_HOOKS.yaml#hooks.{link['hook_id']}"],
            }
        )
    taxonomy = {
        "artifact": "project-semantic-taxonomy",
        "schema_version": "1.0",
        "source_fingerprint": f"sha256:{fingerprint}",
        "review_status": "approved",
        "objects": objects,
        "operations": operations,
        "unresolved": [],
    }
    hook_coverage = {
        "artifact": "hook-coverage",
        "schema_version": "1.0",
        "workflow_id": workflow_id,
        "source_fingerprint": f"sha256:{fingerprint}",
        "mappings": coverage,
    }
    return model, taxonomy, hook_coverage


def prism_type(definition: dict[str, Any]) -> str:
    lines = [f"# {definition['description']}", f"type {definition['name']}:"]
    for field in definition["fields"]:
        lines.extend(
            (f"    # {field['description']}", f"    {field['name']}: {field['type']}")
        )
    return "\n".join(lines)


def string_list(values: list[str]) -> str:
    return (
        "[" + ", ".join(json.dumps(value, ensure_ascii=False) for value in values) + "]"
    )


def build_skill_wrapper(
    *, prism: str, project: Path, skill_file: Path, step: dict[str, Any], scratch: Path
) -> tuple[str, str]:
    staged = scratch / step["id"] / skill_file.parent.name
    stage_skill(skill_file, staged)
    output = project / "generated" / f"{step['id']}_skill.prism"
    output.parent.mkdir(parents=True, exist_ok=True)
    completed = run(
        [
            prism,
            "build",
            "skill",
            str(staged),
            "--contract",
            f"types.{step['input_type']}",
            "--out",
            str(output),
        ],
        cwd=project,
    )
    payload = json.loads(completed.stdout)
    return f"generated.{step['id']}_skill", str(payload["export"])


def render_projection_occurrence(
    occurrence: dict[str, Any],
    *,
    input_name: str,
    indent: str,
    type_module: str = "",
    occurrence_module: str = "",
    relation_module: str = "",
) -> list[str]:
    arguments = occurrence["arguments"]

    def qualified(module: str, name: str) -> str:
        return f"{module}.{name}" if module else name

    def source_expression(source: str) -> str:
        return source if source == input_name else f"{source}.value"

    relation = (
        f" by {qualified(relation_module, occurrence['relation'])}"
        if occurrence.get("relation")
        else ""
    )
    lines = [f"{indent}# {occurrence['rationale']}"]
    if len(arguments) == 1 and "field" not in arguments[0]:
        lines.append(
            f"{indent}[{occurrence['id']}: "
            f"{qualified(occurrence_module, occurrence['method'])}("
            f"{source_expression(arguments[0]['source'])})]{relation}"
        )
        return lines
    lines.append(
        f"{indent}[{occurrence['id']}: "
        f"{qualified(occurrence_module, occurrence['method'])}("
        f"{qualified(type_module, occurrence['input_type'])}("
    )
    for argument in arguments:
        lines.append(
            f"{indent}    {argument['field']} = "
            f"{source_expression(argument['source'])},"
        )
    lines.append(f"{indent}))]{relation}")
    return lines


def render_reasoning_projection(
    project: Path,
    projection: dict[str, Any],
    *,
    project_name: str,
) -> None:
    occurrences = projection["occurrences"]
    methods = {item["method"]: item for item in occurrences}
    used_types = sorted(
        {projection["input_type"], projection["output_type"]}
        | {item["input_type"] for item in occurrences}
        | {item["output_type"] for item in occurrences}
    )
    imports = ["from types import (", *(f"    {name}," for name in used_types), ")", ""]
    occurrence_lines = list(imports)
    for method, occurrence in methods.items():
        occurrence_lines.extend(
            (
                f"# {occurrence['rationale']}",
                f"type {method} = (source: {occurrence['input_type']}) -> Generated[{occurrence['output_type']}]",
                "",
            )
        )
    write_text(project / "occurrences.prism", "\n".join(occurrence_lines))

    relations = sorted(
        {item["relation"] for item in occurrences if item.get("relation")}
    )
    relation_lines: list[str] = []
    for relation in relations:
        relation_lines.extend(
            (
                f"type {relation}Certificate[SourceValue, TargetValue]:",
                "    source: SourceValue",
                "    target: TargetValue",
                "",
                f"relation {relation}[SourceValue, TargetValue](",
                "    source: SourceValue,",
                "    target: TargetValue,",
                f") -> {relation}Certificate[SourceValue, TargetValue]",
                "",
            )
        )
    write_text(project / "relations.prism", "\n".join(relation_lines))

    type_module = ""
    occurrence_module = f"{project_name}_occurrences"
    relation_module = f"{project_name}_relations"
    lines = [
        *imports[:-1],
        f"import occurrences as {occurrence_module}",
        f"import relations as {relation_module}",
        "",
        f"# Reviewed {projection['projection_kind'].replace('_', ' ')} based on {projection['profile_basis']}.",
        f"# Scope: {projection['projection_scope']}.",
        f"# {projection['description']}",
        f"reasoning {projection['name']}(",
        f"    {projection['input_name']}: {projection['input_type']},",
        f") -> Generated[{projection['output_type']}]:",
        "    sequence:",
    ]
    by_id = {item["id"]: item for item in occurrences}
    for item in projection["topology"]:
        if isinstance(item, dict):
            lines.append("        parallel:")
            for occurrence_id in item["parallel"]:
                lines.extend(
                    render_projection_occurrence(
                        by_id[occurrence_id],
                        input_name=projection["input_name"],
                        indent="            ",
                        type_module=type_module,
                        occurrence_module=occurrence_module,
                        relation_module=relation_module,
                    )
                )
        else:
            lines.extend(
                render_projection_occurrence(
                    by_id[item],
                    input_name=projection["input_name"],
                    indent="        ",
                    type_module=type_module,
                    occurrence_module=occurrence_module,
                    relation_module=relation_module,
                )
            )
    lines.extend((f"    return {projection['output_occurrence']}", ""))
    write_text(project / "reasoning.prism", "\n".join(lines))


def render_material_relations(
    project: Path,
    imports: list[str],
    epistemic_steps: list[dict[str, Any]],
    filename: str,
) -> None:
    lines = list(imports)
    for step in epistemic_steps:
        relation = step["relation_type"]
        lines.extend(
            (
                f"type {relation}Certificate:",
                f"    source: {step['input_type']}",
                f"    target: Generated[{step['output_type']}]",
                "",
                f"relation {relation}(",
                f"    source: {step['input_type']},",
                f"    target: Generated[{step['output_type']}],",
                f") -> {relation}Certificate",
                "",
            )
        )
    write_text(project / filename, "\n".join(lines))


def render_project(
    root: Path,
    model: dict[str, Any],
    hooks: dict[str, dict[str, Any]],
    skill_files: dict[str, Path],
    prism: str,
) -> dict[str, str]:
    workflow = model["workflows"][0]
    steps = workflow["steps"]
    project = root / "prism_project"
    project.mkdir(parents=True)
    write_text(
        project / "types.prism",
        "\n\n".join(prism_type(item) for item in model["type_definitions"]),
    )
    projection = workflow.get("reasoning_projection")
    projection_types = (
        {projection["output_type"]}
        | {item["input_type"] for item in projection["occurrences"]}
        | {item["output_type"] for item in projection["occurrences"]}
        if projection is not None
        else set()
    )
    type_names = sorted(
        {workflow["input"]["type"], workflow["output"]["type"]}
        | {step["input_type"] for step in steps}
        | {step["output_type"] for step in steps}
        | projection_types
    )
    imports = ["from types import (", *(f"    {name}," for name in type_names), ")", ""]
    epistemic_steps = [step for step in steps if step["semantic_role"] == "epistemic"]
    material_relation_module = "relations"
    if projection is not None:
        if epistemic_steps:
            material_relation_module = "material_relations"
            render_material_relations(
                project, imports, epistemic_steps, "material_relations.prism"
            )
        render_reasoning_projection(
            project,
            projection,
            project_name=workflow["id"],
        )
        reviewed_reasoning = (
            REPOSITORY
            / "mathformer-prism"
            / "projects"
            / workflow["id"]
            / "prism_project"
            / "reasoning.prism"
        )
        if (
            reviewed_reasoning.is_file()
            and reviewed_reasoning.resolve() != (project / "reasoning.prism").resolve()
        ):
            shutil.copyfile(reviewed_reasoning, project / "reasoning.prism")
    elif epistemic_steps:
        occurrences = list(imports)
        for step in epistemic_steps:
            occurrences.extend(
                (
                    f"# {step['reasoning_rationale']}",
                    f"# Granularity: {step['granularity_rationale']}",
                    f"type {step['reasoning_type']} = (source: {step['input_type']}) -> Generated[{step['output_type']}]",
                    "",
                )
            )
        write_text(project / "occurrences.prism", "\n".join(occurrences))
        render_material_relations(project, imports, epistemic_steps, "relations.prism")
    workflow_name = pascal(workflow["id"])
    final_wrapper = (
        "Generated" if steps[-1]["output_provenance"] == "generated" else "Computed"
    )
    material = list(imports[:-1])
    for step in epistemic_steps:
        material.append(
            f"from {material_relation_module} import {step['relation_type']}Certificate"
        )
    if projection is not None:
        material.append(f"from reasoning import {projection['name']}")
        for relation in sorted(
            {
                item["relation"]
                for item in projection["occurrences"]
                if item.get("relation")
            }
        ):
            material.append(f"from relations import {relation}Certificate")
    bindings: list[tuple[str, str]] = []
    skill_bindings: dict[str, str] = {}
    projection_skill_bindings: dict[str, list[tuple[str, str]]] = {}
    steps_by_id = {step["id"]: step for step in steps}
    with tempfile.TemporaryDirectory(prefix="mathformer-prism-skills-") as temporary:
        scratch = Path(temporary)
        for step in steps:
            owner = Path(step["skills"][0]["path"]).name
            if step["semantic_role"] == "epistemic":
                module, export = build_skill_wrapper(
                    prism=prism,
                    project=project,
                    skill_file=skill_files[owner],
                    step=step,
                    scratch=scratch,
                )
                local_export = f"{step['id']}_skill_binding"
                material.append(f"from {module} import {export} as {local_export}")
                skill_bindings[step["id"]] = local_export
                bindings.append((step["id"], f"{step['id']}_agent"))
            else:
                bindings.append((step["id"], f"{step['id']}_material_binding"))
        if projection is not None:
            for occurrence in projection["occurrences"]:
                occurrence_bindings: list[tuple[str, str]] = []
                seen_owners: set[str] = set()
                for material_step in occurrence["material_steps"]:
                    owner = Path(steps_by_id[material_step]["skills"][0]["path"]).name
                    if owner in seen_owners:
                        continue
                    seen_owners.add(owner)
                    index = len(occurrence_bindings) + 1
                    synthetic_step = {
                        "id": f"reasoning_{occurrence['id']}_{index}",
                        "input_type": occurrence["input_type"],
                    }
                    module, export = build_skill_wrapper(
                        prism=prism,
                        project=project,
                        skill_file=skill_files[owner],
                        step=synthetic_step,
                        scratch=scratch,
                    )
                    alias = f"{occurrence['id']}_reasoning_skill_{index}"
                    material.append(f"from {module} import {export} as {alias}")
                    occurrence_bindings.append((owner, alias))
                projection_skill_bindings[occurrence["id"]] = occurrence_bindings
    material.append("")
    if projection is not None:
        for occurrence in projection["occurrences"]:
            relation = occurrence.get("relation")
            if relation:
                material.extend(
                    (
                        f"def {occurrence['id']}_reasoning_relation_builder[SourceValue, TargetValue](",
                        "    source: SourceValue,",
                        "    target: TargetValue,",
                        f") -> {relation}Certificate[SourceValue, TargetValue]:",
                        f"    return {relation}Certificate(source = source, target = target)",
                        "",
                    )
                )
        for occurrence in projection["occurrences"]:
            mapped = ", ".join(occurrence["material_steps"])
            owners = ", ".join(
                owner for owner, _ in projection_skill_bindings[occurrence["id"]]
            )
            exports = ", ".join(
                export for _, export in projection_skill_bindings[occurrence["id"]]
            )
            material.extend(
                (
                    f"# Generative interpretation {occurrence['method']} uses skill context selected from material steps: {mapped}.",
                    "# The detailed material steps execute only through material_main.prism; this agent does not claim their evidence.",
                    f"# Reviewed skill composition: {owners}.",
                    f"agent {occurrence['id']}_reasoning_agent(",
                    f"    task: {occurrence['input_type']},",
                    f") -> Result[Generated[{occurrence['output_type']}], ModelFailure]",
                    "    ! {AI.Generate, Context.Disclose}:",
                    f"    skills: Skills[{occurrence['input_type']}] = [{exports}]",
                    "",
                )
            )
        material.append(f"converted_reasoning = {projection['name']}(")
        for occurrence in projection["occurrences"]:
            occurrence_id = occurrence["id"]
            material.append(f"    {occurrence_id} = {occurrence_id}_reasoning_agent,")
            if occurrence.get("relation"):
                material.append(
                    f"    {occurrence_id}_by = {occurrence_id}_reasoning_relation_builder,"
                )
        material.extend((")", ""))
    type_by_name = {item["name"]: item for item in model["type_definitions"]}
    for step in steps:
        owner = Path(step["skills"][0]["path"]).name
        if step["semantic_role"] == "epistemic":
            export = bindings[[item[0] for item in bindings].index(step["id"])][1]
            built_export = skill_bindings[step["id"]]
            material.extend(
                (
                    f"# Epistemic occurrence owned by `{owner}`; output assurance remains Generated.",
                    f"agent {export}(",
                    f"    task: {step['input_type']},",
                    f") -> Result[Generated[{step['output_type']}], ModelFailure]",
                    "    ! {AI.Generate, Context.Disclose}:",
                    f"    skills: Skills[{step['input_type']}] = [{built_export}]",
                    "",
                    f"def {step['id']}_relation_builder(",
                    f"    source: {step['input_type']},",
                    f"    target: Generated[{step['output_type']}],",
                    f") -> {step['relation_type']}Certificate:",
                    f"    return {step['relation_type']}Certificate(source = source, target = target)",
                    "",
                )
            )
        else:
            output_def = type_by_name[step["output_type"]]
            values: list[str] = []
            hook_name = step["id"].replace("_", ".")
            for field in output_def["fields"]:
                if field["type"] == "List[String]":
                    value = string_list(
                        []
                        if field["name"]
                        not in {
                            "source_anchors",
                            "declared_artifacts",
                            "limitations",
                            "considered_dispositions",
                        }
                        else {
                            "source_anchors": ["skills/SKILL_HOOKS.yaml"],
                            "declared_artifacts": ["see hook-coverage.json"],
                            "limitations": [
                                "native implementation not executed by the structural fixture"
                            ],
                            "considered_dispositions": [
                                "pass",
                                "warn",
                                "fail",
                                "blocked",
                            ],
                        }[field["name"]]
                    )
                else:
                    value = json.dumps(
                        {
                            "subject": f"typed material binding for {step['id']}",
                            "gate_disposition": "not_executed_by_structural_fixture",
                            "selection_basis": "canonical Mathformer hook contract",
                            "selected_disposition": "not_tested",
                            "rationale": "native execution is outside this structural PRISM fixture",
                            "operation_summary": f"linked material operation {step['id']}",
                            "candidate_content": "not produced by structural fixture",
                        }.get(field["name"], f"not established for {hook_name}"),
                        ensure_ascii=False,
                    )
                values.append(f"        {field['name']} = {value},")
            function_name = f"{step['id']}_material_binding"
            material.extend(
                (
                    f"# Material binding descriptor for `{owner}`; this does not execute the linked native resource.",
                    f"def {function_name}(source: {step['input_type']}) -> Computed[{step['output_type']}]:",
                    f"    artifact = {step['output_type']}(",
                    *values,
                    "    )",
                    f"    return compute(artifact, procedure = {json.dumps('linked material binding: ' + step['id'])})",
                    "",
                )
            )
    workflow_effects = sorted({effect for step in steps for effect in step["effects"]})
    material.extend(
        (
            f"# {workflow['description']}",
            f"workflow {workflow_name}(",
            f"    {workflow['input']['name']}: {workflow['input']['type']},",
            f") -> {final_wrapper}[{workflow['output']['type']}]"
            + (
                "\n    fails ModelFailure\n    ! {" + ", ".join(workflow_effects) + "}:"
                if epistemic_steps
                else ":"
            ),
            "    sequence:",
        )
    )
    prior = workflow["input"]["name"]
    binding_by_step = dict(bindings)
    for step in steps:
        material.append(
            f"        [{step['id']}: {binding_by_step[step['id']]}({prior})]"
        )
        prior = f"{step['id']}.value"
    material.extend((f"    return {steps[-1]['id']}", ""))
    write_text(project / "materialization.prism", "\n".join(material))

    fixture = workflow["input"]["fixture"]
    input_def = type_by_name[workflow["input"]["type"]]
    fixture_lines = []
    for field in input_def["fields"]:
        value = fixture[field["name"]]
        fixture_lines.append(
            f"        {field['name']} = {string_list(value) if isinstance(value, list) else json.dumps(value, ensure_ascii=False)},"
        )
    any_epistemic = any(step["semantic_role"] == "epistemic" for step in steps)
    if any_epistemic:
        signature = (
            "def main(\n    model_access: ModelGenerate,\n    disclosure: ContextDisclose,\n) "
            f"-> Result[{final_wrapper}[{workflow['output']['type']}], ModelFailure] ! {{AI.Generate, Context.Disclose}}:"
        )
    else:
        signature = f"def main() -> {final_wrapper}[{workflow['output']['type']}]:"
    material_main_lines = [
        f"from materialization import {workflow_name}",
        f"from types import {workflow['input']['type']}, {workflow['output']['type']}",
        "",
        signature,
        f"    {workflow['input']['name']} = {workflow['input']['type']}(",
        *fixture_lines,
        "    )",
        f"    return solve {workflow_name}({workflow['input']['name']})",
        "",
    ]
    if projection is not None:
        write_text(project / "material_main.prism", "\n".join(material_main_lines))
        main_lines = [
            "from materialization import converted_reasoning",
            f"from reasoning import {projection['name']}",
            f"from types import {workflow['input']['type']}, {projection['output_type']}",
            "",
            "def main(",
            "    model_access: ModelGenerate,",
            "    disclosure: ContextDisclose,",
            f") -> Result[Generated[{projection['output_type']}], ModelFailure] ! {{AI.Generate, Context.Disclose}}:",
            f"    {workflow['input']['name']} = {workflow['input']['type']}(",
            *fixture_lines,
            "    )",
            f"    flow = converted_reasoning({workflow['input']['name']})",
            f"    return solve {projection['name']}({workflow['input']['name']}) using flow",
            "",
        ]
    else:
        main_lines = material_main_lines
    write_text(project / "main.prism", "\n".join(main_lines))
    material_api_signature = (
        "def run_material(\n"
        f"    {workflow['input']['name']}: {workflow['input']['type']},\n"
        "    model_access: ModelGenerate,\n"
        "    disclosure: ContextDisclose,\n"
        f") -> Result[{final_wrapper}[{workflow['output']['type']}], ModelFailure] ! {{AI.Generate, Context.Disclose}}:"
        if any_epistemic
        else f"def run_material({workflow['input']['name']}: {workflow['input']['type']}) -> {final_wrapper}[{workflow['output']['type']}]:"
    )
    write_text(
        project / "material_api.prism",
        "\n".join(
            (
                f"from materialization import {workflow_name}",
                f"from {workflow['id']} import {workflow['input']['type']}, {workflow['output']['type']}",
                "",
                material_api_signature,
                f"    return solve {workflow_name}({workflow['input']['name']})",
                "",
            )
        ),
    )
    if projection is not None:
        write_text(
            project / "reasoning_api.prism",
            "\n".join(
                (
                    "from materialization import converted_reasoning",
                    f"from reasoning import {projection['name']}",
                    f"from {workflow['id']} import {workflow['input']['type']}, {projection['output_type']}",
                    "",
                    "def run_reasoning(",
                    f"    {workflow['input']['name']}: {workflow['input']['type']},",
                    "    model_access: ModelGenerate,",
                    "    disclosure: ContextDisclose,",
                    f") -> Result[Generated[{projection['output_type']}], ModelFailure] ! {{AI.Generate, Context.Disclose}}:",
                    f"    flow = converted_reasoning({workflow['input']['name']})",
                    f"    return solve {projection['name']}({workflow['input']['name']}) using flow",
                    "",
                )
            ),
        )
    write_text(
        project / "prism",
        '#!/usr/bin/env sh\nset -eu\nPROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nPRISM_BIN=${PRISM_BIN:-prism}\ncd "$PROJECT_DIR"\nexec "$PRISM_BIN" "$@"',
    )
    (project / "prism").chmod(0o755)
    write_json(
        project / "runtime.json",
        {"handler": "fake", "workspace": ".", "output_class": "linked"},
    )
    namespace_project_types(
        project,
        project_name=workflow["id"],
    )
    sources = sorted(project.rglob("*.prism"))

    def validate_source(source: Path) -> None:
        relative = source.relative_to(project).as_posix()
        run([prism, "check", relative], cwd=project)
        run([prism, "compile", relative], cwd=project)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(validate_source, sources))
    hashes = {
        path.relative_to(project)
        .as_posix(): hashlib.sha256(path.read_bytes())
        .hexdigest()
        for path in sorted(project.rglob("*.prism"))
    }
    return hashes


def namespace_project_types(
    project: Path,
    *,
    project_name: str,
) -> None:
    """Give the domain-type module the original workflow project name."""
    source = project / "types.prism"
    target = project / f"{project_name}.prism"
    source.replace(target)
    block = re.compile(r"from types import \(")
    single = re.compile(r"from types import ")
    for path in sorted(project.rglob("*.prism")):
        if path == target:
            continue
        text = path.read_text(encoding="utf-8")
        text = block.sub(f"from {project_name} import (", text)
        text = single.sub(f"from {project_name} import ", text)
        path.write_text(text, encoding="utf-8")


def build(output: Path, prism: str, package_root: Path, archive_sha256: str) -> None:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to replace existing output: {output}")
    contract = yaml.safe_load(HOOK_CONTRACT.read_text(encoding="utf-8"))
    hooks = {str(item["id"]): item for item in contract["hooks"]}
    loops = list(contract["loop_contracts"])
    if {str(item["id"]) for item in loops} != set(BOUNDARY_TYPES):
        raise ValueError(
            "boundary-type review does not cover exactly the canonical loop contracts"
        )
    skill_files = discover_skills()
    source_fingerprint = digest_files(SEMANTIC_SOURCES)
    entries = []
    used_skills: dict[str, list[str]] = {name: [] for name in skill_files}
    output.mkdir(parents=True)
    for loop in loops:
        workflow_id = str(loop["id"])
        project_root = output / "projects" / workflow_id
        conversion = project_root / "conversion"
        conversion.mkdir(parents=True)
        model, taxonomy, coverage = make_model(
            loop, hooks, skill_files, source_fingerprint
        )
        write_json(conversion / "workflow-architecture-plan.json", model)
        write_json(conversion / "project-semantic-taxonomy.json", taxonomy)
        write_json(conversion / "hook-coverage.json", coverage)
        hashes = render_project(project_root, model, hooks, skill_files, prism)
        write_json(
            conversion / "generation.json",
            {
                "artifact": "generation-evidence",
                "schema_version": "1.0",
                "workflow_id": workflow_id,
                "source_fingerprint": f"sha256:{source_fingerprint}",
                "source_hashes": hashes,
                "reasoning_projection_spec_sha256": "sha256:"
                + hashlib.sha256(PROJECTION_SPEC.read_bytes()).hexdigest(),
                "portable": False,
                "authoritative_target": "canonical-.prism",
            },
        )
        for item in coverage["mappings"]:
            used_skills[item["owner_skill"]].append(workflow_id)
        workflow_model = model["workflows"][0]
        reasoning_projection = workflow_model.get("reasoning_projection")
        entries.append(
            {
                "id": workflow_id,
                "description": loop["description"],
                "project": f"projects/{workflow_id}/prism_project",
                "entrypoint": "main.prism",
                "typed_entrypoint": "reasoning_api.prism",
                "entrypoint_kind": (
                    "reasoning_projection"
                    if reasoning_projection
                    else "material_workflow"
                ),
                "public_output_type": (
                    reasoning_projection["output_type"]
                    if reasoning_projection
                    else workflow_model["output"]["type"]
                ),
                "material_entrypoint": (
                    "material_main.prism" if reasoning_projection else "main.prism"
                ),
                "typed_material_entrypoint": "material_api.prism",
                "workflow_plan": f"projects/{workflow_id}/conversion/workflow-architecture-plan.json",
                "semantic_taxonomy": f"projects/{workflow_id}/conversion/project-semantic-taxonomy.json",
                "hook_coverage": f"projects/{workflow_id}/conversion/hook-coverage.json",
                "semantic_mode": workflow_model["semantic_mode"],
                "occurrence_count": len(workflow_model["steps"]),
                "epistemic_occurrence_count": sum(
                    step["semantic_role"] == "epistemic"
                    for step in workflow_model["steps"]
                ),
                "reasoning_occurrence_count": (
                    len(reasoning_projection["occurrences"])
                    if reasoning_projection
                    else 0
                ),
                "reasoning_profile_basis": reasoning_projection["profile_basis"],
                "reasoning_projection_scope": reasoning_projection["projection_scope"],
                "reasoning_projection_kind": reasoning_projection["projection_kind"],
            }
        )
    catalog = {
        "artifact": "mathformer-prism-workflow-catalog",
        "schema_version": "4.0",
        "source_fingerprint": f"sha256:{source_fingerprint}",
        "workflow_count": len(entries),
        "public_entrypoint_kind": "named_loop_contract",
        "skill_modules_are_internal": True,
        "reasoning_projection_spec_sha256": "sha256:"
        + hashlib.sha256(PROJECTION_SPEC.read_bytes()).hexdigest(),
        "workflows": entries,
    }
    write_json(output / "workflow_catalog.json", catalog)
    rows = [
        "# Mathformer PRISM workflow catalog",
        "",
        "The 14 public entries are named repository workflows. Skills are internal bindings, never public workflow entrypoints.",
        "Computed occurrences are structural material-binding descriptors; the fake handler does not execute native Mathformer scripts.",
        "",
        "| Workflow | Profile | Material occurrences | Reasoning occurrences | Entrypoint |",
        "|---|---|---:|---:|---|",
    ]
    for entry in entries:
        rows.append(
            f"| `{entry['id']}` | `{entry['reasoning_profile_basis']}` | {entry['occurrence_count']} | {entry['reasoning_occurrence_count']} | `{entry['project']}/{entry['entrypoint']}` |"
        )
    write_text(output / "workflow_catalog.md", "\n".join(rows))
    dispositions = []
    for name, path in skill_files.items():
        workflows = sorted(set(used_skills[name]))
        dispositions.append(
            {
                "skill": name,
                "path": path.parent.relative_to(REPOSITORY).as_posix(),
                "disposition": (
                    "workflow_component"
                    if workflows
                    else "not_used_by_named_loop_contracts"
                ),
                "workflows": workflows,
                "reason": "Canonical skill remains preserved in the Mathformer repository; the linked conversion records use without relocating source.",
            }
        )
    write_json(
        output / "skill_dispositions.json",
        {
            "artifact": "skill-dispositions",
            "schema_version": "1.0",
            "skills": dispositions,
        },
    )
    write_json(
        output / "conversion" / "source-fingerprint.json",
        {
            "artifact": "source-fingerprint",
            "schema_version": "1.0",
            "algorithm": "sha256",
            "digest": source_fingerprint,
            "files": [
                path.relative_to(REPOSITORY).as_posix() for path in SEMANTIC_SOURCES
            ],
        },
    )
    converter_wheels = sorted(
        (package_root / "vendor" / "wheels").glob("to_prism-*.whl")
    )
    converter_wheel_sha256 = (
        hashlib.sha256(converter_wheels[-1].read_bytes()).hexdigest()
        if converter_wheels
        else None
    )
    write_json(
        output / "conversion" / "converter-package.json",
        {
            "artifact": "converter-package",
            "schema_version": "1.0",
            "archive_sha256": archive_sha256,
            "package_root": package_root.name,
            "prism_executable_sha256": hashlib.sha256(
                Path(prism).read_bytes()
            ).hexdigest(),
            "converter_wheel_sha256": converter_wheel_sha256,
        },
    )
    write_text(
        output / "README.md",
        f"""# Mathformer PRISM workflows

This directory was rebuilt from the canonical Mathformer loop contracts using the updated `to_prism` package.

- Public entrypoints: 14 named workflows under `projects/<workflow>/prism_project/main.prism`.
- Domain modules retain the original workflow name (`<workflow>.prism`); reasoning imports occurrences and relations as modules instead of enumerating their exports.
- Every public entrypoint is a reviewed human-scale generative reasoning projection; its detailed hook pipeline remains available as `material_main.prism`.
- Projection skill mappings provide reviewed generative context and do not claim that deterministic material checks ran inside the reasoning agent.
- Canonical skills: preserved in `../skills`; no skill-level PRISM entrypoints are published.
- Provenance: deterministic material bindings return `Computed[T]`; genuine model-dependent occurrences return `Generated[T]`.
- Output class: linked development projects. Set `PRISM_BIN` to the pinned PRISM executable before running a project launcher.
- Evidence cap: fake-handler runs establish typed topology and trace smoke only, not native, behavioral, semantic, or epistemic equivalence.

The aggregate catalog is `workflow_catalog.json`; each project contains its reviewed linked-workflow architecture plan, semantic taxonomy, hook coverage, and generated-source hashes. These linked plans are not `to_prism` executable generation plans because unadapted native operations are retained as explicit non-executing descriptors rather than falsely presented as Python-backed computation.

Source fingerprint: `sha256:{source_fingerprint}`.
""",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--prism",
        default=str(REPOSITORY.parent / "to_prism" / ".venv" / "bin" / "prism"),
    )
    parser.add_argument(
        "--package-root", type=Path, default=REPOSITORY.parent / "to_prism"
    )
    parser.add_argument(
        "--archive-sha256",
        default="ec48487ae3b47f348de3b2d82350bfdf62d2dc30887ad4147965762f50b3bd94",
    )
    args = parser.parse_args()
    try:
        build(args.output, args.prism, args.package_root.resolve(), args.archive_sha256)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"output": str(args.output.resolve()), "workflow_count": 14}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
