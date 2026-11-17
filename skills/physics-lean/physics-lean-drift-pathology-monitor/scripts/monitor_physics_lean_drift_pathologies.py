#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make FormalScience semantic-drift monitoring explicit inside the Lean
#   physics autoformalization workflow.
#
# Intent:
#   Detect paper-derived physics formalization pathologies with deterministic,
#   inspectable cues before final consistency acceptance.
#
# Function:
#   Reads source text, Lean code, and optional critic packets, then emits a JSON
#   report over notational collapse, abstraction elevation, proof strategy
#   substitution, and implicit premise selection.
#
# Maintenance Notes:
#   Keep the taxonomy names synchronized with
#   references/formalscience_semantic_drift_taxonomy.md and update self-tests
#   when new cues are added.

"""Monitor Lean physics artifacts for FormalScience drift pathologies."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

CATEGORY_ORDER = [
    "notational_collapse",
    "abstraction_elevation",
    "proof_strategy_substitution",
    "implicit_premise_selection",
]

SEVERITY_RANK = {"info": 0, "warning": 1, "error": 2, "critical": 3}
DECL_LINE_RE = re.compile(
    r"^\s*(?:noncomputable\s+)?(?:def|theorem|lemma|structure|abbrev|axiom)\s+([A-Za-z0-9_'.]+)"
)

RERUN_GATES = {
    "notational_collapse": [
        "physics.lean.type_system.build",
        "critique.physics_lean_semantics",
        "critique.physics_lean_dimensions",
        "review.physics_final_hypotheses",
        "refine.physics_lean_review",
    ],
    "abstraction_elevation": [
        "physics.lean.workflow.plan",
        "physics.lean.type_system.build",
        "physics.lean.assumptions.encode",
        "critique.physics_lean_semantics",
        "critique.physics_lean_assumptions",
        "review.physics_final_hypotheses",
        "refine.physics_lean_review",
    ],
    "proof_strategy_substitution": [
        "critique.semantic_preservation",
        "critique.physics_lean_semantics",
        "review.physics_final_hypotheses",
    ],
    "implicit_premise_selection": [
        "physics.lean.assumptions.encode",
        "critique.physics_lean_assumptions",
        "review.physics_final_hypotheses",
    ],
}


def read_text(path: Path | None, inline: str | None) -> str:
    """Load text from an inline value or file path."""
    if inline is not None:
        return inline
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


def load_json(path: Path | None) -> dict[str, Any]:
    """Load an optional JSON object."""
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def lower(text: str) -> str:
    """Return a lower-cased search surface."""
    return text.lower()


def has_any(text: str, patterns: Iterable[str]) -> bool:
    """Return whether any literal cue appears in text."""
    lowered = lower(text)
    return any(pattern.lower() in lowered for pattern in patterns)


def regex_any(text: str, patterns: Iterable[str], flags: int = re.I | re.M) -> bool:
    """Return whether any regex cue matches text."""
    return any(re.search(pattern, text, flags) for pattern in patterns)


def count_regex(text: str, pattern: str, flags: int = re.I | re.M) -> int:
    """Count regex cue matches."""
    return len(re.findall(pattern, text, flags))


def add_finding(
    findings: list[dict[str, Any]],
    *,
    category: str,
    severity: str,
    code: str,
    message: str,
    source_cues: Sequence[str],
    lean_cues: Sequence[str],
    repair_surface: str,
    blocker: bool,
) -> None:
    """Append one normalized pathology finding."""
    findings.append(
        {
            "category": category,
            "severity": severity,
            "code": code,
            "message": message,
            "source_cues": list(source_cues),
            "lean_cues": list(lean_cues),
            "repair_surface": repair_surface,
            "rerun_gates": RERUN_GATES[category],
            "blocker": blocker,
        }
    )


def critic_codes(report: dict[str, Any]) -> set[str]:
    """Collect finding codes from a prior critic report."""
    codes = set()
    for item in report.get("findings", []):
        if isinstance(item, dict) and item.get("code"):
            codes.add(str(item["code"]))
    return codes


def assumption_labels(assumption_packet: dict[str, Any]) -> set[str]:
    """Collect assumption support labels from common packet shapes."""
    labels: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key in (
                "status",
                "support",
                "source_status",
                "provenance",
                "classification",
            ):
                if key in value and isinstance(value[key], str):
                    labels.add(value[key])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(assumption_packet)
    return labels


def source_features(source_text: str) -> dict[str, bool]:
    """Extract paper-taxonomy source cues."""
    return {
        "quantum_dense_notation": regex_any(
            source_text,
            [
                r"\bdirac\b",
                r"\bbraket\b",
                r"\bbra\b",
                r"\bket\b",
                r"\\psi\b",
                r"\bpsi\b",
                r"\bcommutator\b",
                r"\[q,\s*p\]",
                r"\bladder\b",
                r"\boperator\b",
                r"\bhilbert\b",
                r"\bheisenberg\b",
                r"\buncertainty\b",
            ],
        ),
        "operator_algebra": has_any(
            source_text,
            [
                "operator",
                "commutator",
                "unitary",
                "hamiltonian",
                "adjoint",
                "dagger",
                "\\dagger",
            ],
        ),
        "vector_or_field": has_any(
            source_text,
            [
                "vector",
                "field",
                "\\vec",
                "\\mathbf",
                "gradient",
                "divergence",
                "curl",
                "laplacian",
                "spherical",
                "coordinate",
                "basis",
                "\\hat",
            ],
        ),
        "calculus_or_integral": has_any(
            source_text,
            [
                "integral",
                "\\int",
                "differentiate",
                "derivative",
                "\\partial",
                "gradient",
                "divergence theorem",
                "stokes",
                "limit",
                "tends to",
                "at infinity",
            ],
        ),
        "physical_law": has_any(
            source_text,
            [
                "maxwell",
                "gauss",
                "poisson",
                "newton",
                "lagrange",
                "hamilton",
                "conservation",
                "work-energy",
                "coulomb",
                "schrodinger",
                "heisenberg",
            ],
        ),
        "implicit_premise_needs": has_any(
            source_text,
            [
                "divide",
                "denominator",
                "positive",
                "nonzero",
                "smooth",
                "differentiable",
                "boundary",
                "initial condition",
                "limit",
                "sqrt",
                "square root",
                "domain",
            ],
        ),
    }


def lean_features(lean_text: str) -> dict[str, bool | int]:
    """Extract Lean-surface cues for the taxonomy."""
    return {
        "raw_scalar_count": count_regex(
            lean_text, r"\b(Real|Float|Rat|Int|Complex|C)\b"
        ),
        "has_hilbert_or_inner_product": regex_any(
            lean_text,
            [
                r"\bInnerProductSpace\b",
                r"\bHilbert\b",
                r"\bNormed(AddComm)?Group\b",
                r"\bModule\b",
            ],
        ),
        "has_operator_surface": regex_any(
            lean_text,
            [
                r"\b(LinearMap|ContinuousLinearMap|Matrix|AlgHom|StarAlgHom)\b",
                r"\b[A-Z]\s*:\s*[^,\n]*(->|\\to)[^,\n]*",
            ],
        ),
        "has_quantity_or_dimension": regex_any(
            lean_text, [r"\b(Quantity|VectorQuantity|PhysDim|Unit|Dim)\b"]
        ),
        "has_vector_or_field": regex_any(
            lean_text,
            [
                r"\b(EuclideanSpace|Vector|VectorField|Field|Fin\s+\d+|InnerProductSpace)\b"
            ],
        ),
        "has_calculus_surface": regex_any(
            lean_text,
            [
                r"\b(deriv|fderiv|Differentiable|ContDiff|intervalIntegral|Measure|Tendsto|HasDerivAt)\b"
            ],
        ),
        "has_source_law_surface": regex_any(
            lean_text,
            [
                r"\b(SourceLaw|law|Law|maxwell|gauss|poisson|newton|lagrange|hamilton|conservation)\b"
            ],
        ),
        "trivial_proof_surface": regex_any(
            lean_text,
            [
                r"\b(simpa|simp|ring|linarith)\b.*\b(using|sub_zero|h[A-Za-z0-9_]+)",
                r":=\s*by\s*\n\s*(simpa|simp|ring)",
            ],
        ),
        "many_hypothesis_bindings": count_regex(lean_text, r"\(h[A-Za-z0-9_]*\s*:")
        >= 3,
        "has_target_shaped_hypothesis": regex_any(
            lean_text,
            [r"\(h[A-Za-z0-9_]*\s*:[^)]*=\s*[^)]*\)\s*:", r"using\s+h[A-Za-z0-9_]+"],
        ),
        "has_derivative_strategy_substitution": regex_any(
            lean_text,
            [r"\b(congrArg|funext|ext)\b", r"\bderiv\b.*\b(eq|congr|congrArg)\b"],
        ),
        "has_side_conditions": regex_any(
            lean_text,
            [
                r"(0\s*<|<=|>=|!=|\\ne|\\neq)",
                r"\b(Differentiable|Continuous|Integrable|Measurable|Nonempty|NoZeroDivisors)\b",
                r"\b(hpos|hnonzero|hne|hdiff|hboundary|hdom)\b",
            ],
        ),
    }


def source_concepts_from_features(source: dict[str, bool]) -> list[str]:
    """Map source cues to compact physics concept labels."""
    concepts = []
    if source.get("quantum_dense_notation") or source.get("operator_algebra"):
        concepts.append("quantum_operator_or_hilbert_surface")
    if source.get("vector_or_field"):
        concepts.append("vector_or_field_surface")
    if source.get("calculus_or_integral"):
        concepts.append("calculus_or_integral_surface")
    if source.get("physical_law"):
        concepts.append("source_law_surface")
    return concepts or ["unknown_physics_surface"]


def declaration_near(lines: Sequence[str], line_index: int) -> str | None:
    """Return the nearest declaration name above a line."""
    for index in range(line_index, max(-1, line_index - 8), -1):
        match = DECL_LINE_RE.match(lines[index])
        if match:
            return match.group(1)
    return None


def add_grounding_debt(
    findings: list[dict[str, Any]],
    *,
    code: str,
    severity: str,
    line: int,
    declaration: str | None,
    evidence: str,
    source_concepts: Sequence[str],
    missing_object_class: str,
    message: str,
    lean_path: str | None,
) -> None:
    """Append one FormalScience grounding-debt finding."""
    findings.append(
        {
            "code": code,
            "severity": severity,
            "file": lean_path,
            "line": line,
            "declaration": declaration,
            "source_concept": list(source_concepts),
            "missing_object_class": missing_object_class,
            "evidence": evidence.strip(),
            "message": message,
            "rerun_gates": [
                "critique.physics_lean_drift_pathology_monitor",
                "repair.physics_math_object_detect",
                "repair.mathformerphysicslib_object_workbench",
                "repair.physics_lean_repair_expansion_cartography",
            ],
        }
    )


def formal_science_grounding_debt_report(
    *,
    lean_text: str,
    source: dict[str, bool],
    lean: dict[str, bool | int],
    lean_path: str | None,
) -> dict[str, Any]:
    """Detect algebraic-shell and trivial-support debt in FormalPhysics Lean."""
    findings: list[dict[str, Any]] = []
    lines = lean_text.splitlines()
    source_concepts = source_concepts_from_features(source)
    generated_formalphysics_surface = lean_path is None or "formalphysics_" in lean_path

    for index, line in enumerate(lines):
        line_no = index + 1
        declaration = declaration_near(lines, index)
        if re.search(
            r"\b(?:def|abbrev)\s+[A-Za-z0-9_'.]+\b.*?:\s*Prop\s*:=\s*True\b", line
        ):
            add_grounding_debt(
                findings,
                code="prop_true_support_definition",
                severity="critical",
                line=line_no,
                declaration=declaration,
                evidence=line,
                source_concepts=source_concepts,
                missing_object_class="source_backed_foundation_surface",
                message="A local support definition is equivalent to `Prop := True`.",
                lean_path=lean_path,
            )
        if generated_formalphysics_surface and re.search(
            r"\babbrev\s+Law\b.*?:\s*Prop\s*:=\s*True\b", line
        ):
            add_grounding_debt(
                findings,
                code="local_law_shim_true",
                severity="critical",
                line=line_no,
                declaration=declaration,
                evidence=line,
                source_concepts=source_concepts,
                missing_object_class="source_law_foundation",
                message="A generated local `Law` shim collapses law evidence to `True`.",
                lean_path=lean_path,
            )
        if generated_formalphysics_surface and re.search(
            r"\babbrev\s+UnitDimensionCompatible\b", line
        ):
            add_grounding_debt(
                findings,
                code="local_unit_dimension_shim",
                severity="error",
                line=line_no,
                declaration=declaration,
                evidence=line,
                source_concepts=source_concepts,
                missing_object_class="MathformerPhysicsLib.Lean.Foundations.Units",
                message="A generated file defines a local unit/dimension compatibility shim.",
                lean_path=lean_path,
            )
        if generated_formalphysics_surface and re.search(
            r"\b(?:law|Law|source[A-Za-z0-9_'.]*|support[A-Za-z0-9_'.]*)\b[^:\n]*:\s*True\b",
            line,
        ):
            add_grounding_debt(
                findings,
                code="source_law_typed_true",
                severity="critical",
                line=line_no,
                declaration=declaration,
                evidence=line,
                source_concepts=source_concepts,
                missing_object_class="typed_source_law_or_context",
                message="A source-law or support binding is typed as exactly `True`.",
                lean_path=lean_path,
            )
        reflexive_unit = re.search(
            r"\bUnitDimensionCompatible\s+([A-Za-z0-9_.']+)\s+\1\b", line
        )
        if generated_formalphysics_surface and reflexive_unit:
            add_grounding_debt(
                findings,
                code="reflexive_unit_dimension_bridge",
                severity="warning",
                line=line_no,
                declaration=declaration,
                evidence=line,
                source_concepts=source_concepts,
                missing_object_class="non_reflexive_unit_dimension_evidence",
                message="Unit/dimension evidence is reflexive and may not preserve a source homogeneity claim.",
                lean_path=lean_path,
            )

    scalar_collapse = (
        bool(
            source.get("quantum_dense_notation")
            or source.get("operator_algebra")
            or source.get("vector_or_field")
        )
        and int(lean.get("raw_scalar_count", 0)) >= 3
        and not bool(lean.get("has_hilbert_or_inner_product"))
        and not bool(lean.get("has_vector_or_field"))
        and not bool(lean.get("has_operator_surface"))
    )
    if scalar_collapse:
        add_grounding_debt(
            findings,
            code="known_object_scalar_placeholder",
            severity="critical",
            line=1,
            declaration=None,
            evidence="raw scalar surface without matching Hilbert/vector/operator API",
            source_concepts=source_concepts,
            missing_object_class="typed_physics_object_surface",
            message="Known physics object classes are represented only by scalar placeholders.",
            lean_path=lean_path,
        )

    return {
        "style": "formal_science_grounding_debt_report",
        "schema_version": 1,
        "ok": not any(item["severity"] in {"critical", "error"} for item in findings),
        "finding_count": len(findings),
        "findings": findings,
    }


def inspect_pack(
    *,
    source_text: str,
    lean_text: str,
    type_packet: dict[str, Any],
    assumption_packet: dict[str, Any],
    unit_report: dict[str, Any],
    semantics_report: dict[str, Any],
    assumption_report: dict[str, Any],
    dimension_report: dict[str, Any],
    lean_path: str | None = None,
) -> dict[str, Any]:
    """Extract cues, grounding debt and ordered rule guards."""
    source = source_features(source_text)
    lean = lean_features(lean_text)
    grounding_debt = formal_science_grounding_debt_report(
        lean_text=lean_text,
        source=source,
        lean=lean,
        lean_path=lean_path,
    )
    type_packet_text = (
        json.dumps(type_packet, ensure_ascii=False).lower() if type_packet else ""
    )
    unit_status = unit_report.get("status") if unit_report else "missing"
    semantic_codes = critic_codes(semantics_report)
    assumption_codes = critic_codes(assumption_report)
    dimension_codes = critic_codes(dimension_report)
    labels = assumption_labels(assumption_packet)
    findings: list[dict[str, Any]] = []

    source_dense = (
        source["quantum_dense_notation"]
        or source["operator_algebra"]
        or source["vector_or_field"]
        or source["calculus_or_integral"]
    )
    lean_scalar_heavy = int(lean["raw_scalar_count"]) >= 3 and not bool(
        lean["has_quantity_or_dimension"]
    )
    packet_mentions_quantity = any(
        token in type_packet_text
        for token in ("quantity", "dimension", "vector", "operator", "hilbert")
    )
    unit_missing_or_failed = unit_status in {"missing", "fail", None}

    return {
        "source": source,
        "lean": lean,
        "grounding_debt": grounding_debt,
        "type_packet_text": type_packet_text,
        "unit_status": unit_status,
        "semantic_codes": sorted(semantic_codes),
        "assumption_codes": sorted(assumption_codes),
        "dimension_codes": sorted(dimension_codes),
        "labels": sorted(labels),
        "findings": findings,
        "source_dense": source_dense,
        "lean_scalar_heavy": lean_scalar_heavy,
        "packet_mentions_quantity": packet_mentions_quantity,
        "unit_missing_or_failed": unit_missing_or_failed,
    }


def apply_rules(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Accumulate independent native rules in source order."""
    source = analysis["source"]
    lean = analysis["lean"]
    semantic_codes = set(analysis["semantic_codes"])
    assumption_codes = set(analysis["assumption_codes"])
    dimension_codes = set(analysis["dimension_codes"])
    labels = set(analysis["labels"])
    findings = list(analysis["findings"])
    source_dense = analysis["source_dense"]
    lean_scalar_heavy = analysis["lean_scalar_heavy"]
    packet_mentions_quantity = analysis["packet_mentions_quantity"]
    unit_missing_or_failed = analysis["unit_missing_or_failed"]
    if source["quantum_dense_notation"] and not (
        bool(lean["has_hilbert_or_inner_product"]) or bool(lean["has_operator_surface"])
    ):
        add_finding(
            findings,
            category="notational_collapse",
            severity="critical",
            code="quantum_notation_collapsed",
            message="The source uses quantum notation or operators, but the Lean surface lacks Hilbert-space or operator structure.",
            source_cues=["quantum_dense_notation"],
            lean_cues=["missing_hilbert_or_operator_surface"],
            repair_surface="quantity_typing",
            blocker=True,
        )
    if source["vector_or_field"] and (
        not bool(lean["has_vector_or_field"])
        or "vector_structure_erased" in semantic_codes
    ):
        add_finding(
            findings,
            category="notational_collapse",
            severity="critical",
            code="vector_field_notation_collapsed",
            message="The source appears vectorial or field-based, but the Lean artifact lacks a visible vector, field, or projection-preserving surface.",
            source_cues=["vector_or_field"],
            lean_cues=["missing_vector_or_field_surface"],
            repair_surface="projection_bridge",
            blocker=True,
        )
    if source_dense and lean_scalar_heavy and not packet_mentions_quantity:
        add_finding(
            findings,
            category="notational_collapse",
            severity="critical",
            code="dense_physics_collapsed_to_scalars",
            message="Dense physics structure is represented mainly as raw scalar algebra without a quantity, dimension, vector, or operator packet.",
            source_cues=[key for key, value in source.items() if value],
            lean_cues=["raw_scalar_count", "missing_quantity_surface"],
            repair_surface="quantity_typing",
            blocker=True,
        )
    if (
        source_dense
        and unit_missing_or_failed
        and (
            "raw_scalar_erasure" in dimension_codes
            or "physical_quantities_erased" in semantic_codes
        )
    ):
        add_finding(
            findings,
            category="notational_collapse",
            severity="critical",
            code="unit_dimension_guard_confirms_collapse",
            message="Existing unit or semantics critics report erased physical quantities while the source contains physics-bearing notation.",
            source_cues=[key for key, value in source.items() if value],
            lean_cues=sorted(dimension_codes | semantic_codes),
            repair_surface="unit_dimension_obligation",
            blocker=True,
        )

    if source["calculus_or_integral"] and not bool(lean["has_calculus_surface"]):
        severity = (
            "critical"
            if bool(lean["trivial_proof_surface"])
            or bool(lean["has_target_shaped_hypothesis"])
            else "error"
        )
        add_finding(
            findings,
            category="abstraction_elevation",
            severity=severity,
            code="calculus_or_integral_abstracted_away",
            message="The source uses calculus, limits, or integration, but the Lean proof does not expose corresponding calculus surfaces.",
            source_cues=["calculus_or_integral"],
            lean_cues=["missing_calculus_surface"],
            repair_surface="support_dependency",
            blocker=severity == "critical",
        )
    if source["physical_law"] and not bool(lean["has_source_law_surface"]):
        add_finding(
            findings,
            category="abstraction_elevation",
            severity="error",
            code="physical_law_absorbed_into_hypotheses",
            message="The source invokes a named physics law, but the Lean artifact has no visible law binding or support lemma.",
            source_cues=["physical_law"],
            lean_cues=["missing_source_law_surface"],
            repair_surface="law_grounding",
            blocker=False,
        )
    if bool(lean["trivial_proof_surface"]) and bool(
        lean["has_target_shaped_hypothesis"]
    ):
        add_finding(
            findings,
            category="abstraction_elevation",
            severity="critical",
            code="proof_reduced_to_target_shaped_substitution",
            message="The Lean proof appears to discharge the goal by simplification from target-shaped hypotheses.",
            source_cues=[key for key, value in source.items() if value],
            lean_cues=["trivial_proof_surface", "target_shaped_hypothesis"],
            repair_surface="law_grounding",
            blocker=True,
        )

    if source["calculus_or_integral"] and bool(
        lean["has_derivative_strategy_substitution"]
    ):
        add_finding(
            findings,
            category="proof_strategy_substitution",
            severity="warning",
            code="alternate_calculus_strategy",
            message="The Lean artifact may use an alternative calculus proof strategy; verify that source objects and target semantics are preserved.",
            source_cues=["calculus_or_integral"],
            lean_cues=["derivative_strategy_substitution"],
            repair_surface="support_dependency",
            blocker=False,
        )

    has_useful_labels = bool(
        labels & {"source-backed", "mathlib-backed", "generated-support", "blocked"}
    )
    if bool(lean["has_side_conditions"]) and not has_useful_labels:
        add_finding(
            findings,
            category="implicit_premise_selection",
            severity="warning",
            code="implicit_premises_unlabeled",
            message="Lean exposes side conditions, but the assumption packet does not clearly label their support status.",
            source_cues=[
                (
                    "implicit_premise_needs"
                    if source["implicit_premise_needs"]
                    else "source_may_omit_side_conditions"
                )
            ],
            lean_cues=["side_conditions"],
            repair_surface="contextual_assumption",
            blocker=False,
        )
    if (
        "hidden_strengthening" in assumption_codes
        or "missing_assumption_packet" in semantic_codes
    ):
        add_finding(
            findings,
            category="implicit_premise_selection",
            severity="error",
            code="implicit_premises_failed_assumption_critic",
            message="Existing assumption/semantics critics indicate hidden strengthening or missing assumption provenance.",
            source_cues=["assumption_provenance_needed"],
            lean_cues=sorted(assumption_codes | semantic_codes),
            repair_surface="contextual_assumption",
            blocker=False,
        )

    return findings


def summarize(
    analysis: dict[str, Any], findings: list[dict[str, Any]]
) -> dict[str, Any]:
    """Count findings and preserve scientific status independently of debt."""
    source = analysis["source"]
    lean = analysis["lean"]
    grounding_debt = analysis["grounding_debt"]
    semantic_codes = set(analysis["semantic_codes"])
    assumption_codes = set(analysis["assumption_codes"])
    dimension_codes = set(analysis["dimension_codes"])
    labels = set(analysis["labels"])
    category_counts = {category: 0 for category in CATEGORY_ORDER}
    for finding in findings:
        category_counts[finding["category"]] += 1
    max_rank = max((SEVERITY_RANK[item["severity"]] for item in findings), default=0)
    status = (
        "fail"
        if any(item["blocker"] for item in findings)
        else "warn" if max_rank >= 1 else "pass"
    )
    return {
        "style": "physics_lean_drift_pathology_monitor_report",
        "taxonomy_source": "FormalScience ACL 2026 semantic-drift taxonomy",
        "status": status,
        "category_counts": category_counts,
        "max_severity": next(
            (label for label, rank in SEVERITY_RANK.items() if rank == max_rank), "info"
        ),
        "source_features": source,
        "lean_features": lean,
        "assumption_support_labels": sorted(labels),
        "prior_critic_codes": {
            "physical_semantics": sorted(semantic_codes),
            "assumptions": sorted(assumption_codes),
            "dimensions": sorted(dimension_codes),
        },
        "grounding_debt_report": grounding_debt,
        "findings": findings,
        "acceptance_policy": {
            "notational_collapse": "critical findings block complete status",
            "abstraction_elevation": "critical findings block complete status; errors require localized refinement or explicit draft blocker",
            "proof_strategy_substitution": "allowed only with preserved source objects, target semantics, and law obligations",
            "implicit_premise_selection": "beneficial only when side conditions are labeled and not hidden strengthening",
        },
    }


def build_report(
    *,
    source_text: str,
    lean_text: str,
    type_packet: dict[str, Any],
    assumption_packet: dict[str, Any],
    unit_report: dict[str, Any],
    semantics_report: dict[str, Any],
    assumption_report: dict[str, Any],
    dimension_report: dict[str, Any],
    lean_path: str | None = None,
) -> dict[str, Any]:
    """Build the deterministic drift-pathology monitor report."""
    analysis = inspect_pack(
        source_text=source_text,
        lean_text=lean_text,
        type_packet=type_packet,
        assumption_packet=assumption_packet,
        unit_report=unit_report,
        semantics_report=semantics_report,
        assumption_report=assumption_report,
        dimension_report=dimension_report,
        lean_path=lean_path,
    )
    return summarize(analysis, apply_rules(analysis))


def parse_args(
    argv: Sequence[str] | None = None, *, prog: str | None = None
) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__, prog=prog)
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-text")
    parser.add_argument("--lean-file", type=Path)
    parser.add_argument("--lean-text")
    parser.add_argument("--type-packet", type=Path)
    parser.add_argument("--assumption-packet", type=Path)
    parser.add_argument("--unit-report", type=Path)
    parser.add_argument("--physical-semantics-report", type=Path)
    parser.add_argument("--assumption-critic-report", type=Path)
    parser.add_argument("--dimension-critic-report", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def load_inputs(
    options: dict[str, Any], *, working_directory: Path | None = None
) -> dict[str, Any]:
    """Read CLI inputs in native order, retaining the authored Lean path."""

    def path(name: str) -> Path | None:
        value = options.get(name)
        if value is None:
            return None
        result = Path(value)
        return working_directory / result if working_directory is not None else result

    return dict(
        source_text=read_text(path("source_file"), options.get("source_text")),
        lean_text=read_text(path("lean_file"), options.get("lean_text")),
        type_packet=load_json(path("type_packet")),
        assumption_packet=load_json(path("assumption_packet")),
        unit_report=load_json(path("unit_report")),
        semantics_report=load_json(path("physical_semantics_report")),
        assumption_report=load_json(path("assumption_critic_report")),
        dimension_report=load_json(path("dimension_critic_report")),
        lean_path=str(options["lean_file"]) if options.get("lean_file") else None,
    )


def emit(
    options: dict[str, Any],
    report: dict[str, Any],
    *,
    working_directory: Path | None = None,
    before_write=None,
) -> int:
    """Emit exactly one report, preserving native JSON bytes and exit status."""
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if options.get("output"):
        path = Path(options["output"])
        if working_directory is not None:
            path = working_directory / path
        if before_write is not None:
            before_write(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


def run_self_test() -> dict[str, Any]:
    """Run all three native fixtures and assertions, returning collapse."""
    collapse = build_report(
        source_text="Show that the quantum ket |psi> obeys a commutator relation [q, p] = i in Hilbert space.",
        lean_text="theorem bad (q p : Real) (h : q * p = p * q) : q * p = p * q := by simpa using h",
        type_packet={},
        assumption_packet={},
        unit_report={"status": "missing"},
        semantics_report={"findings": [{"code": "physical_quantities_erased"}]},
        assumption_report={},
        dimension_report={"findings": [{"code": "raw_scalar_erasure"}]},
    )
    assert collapse["status"] == "fail"
    assert collapse["category_counts"]["notational_collapse"] >= 1
    implicit = build_report(
        source_text="Differentiate sqrt(1 + x^2).",
        lean_text=(
            "theorem ok (x : Real) (hpos : 0 < 1 + x^2) "
            "(hdiff : DifferentiableAt Real (fun y => Real.sqrt (1 + y^2)) x) : True := by trivial"
        ),
        type_packet={},
        assumption_packet={"assumptions": [{"status": "generated-support"}]},
        unit_report={"status": "pass"},
        semantics_report={},
        assumption_report={},
        dimension_report={},
    )
    assert implicit["category_counts"]["implicit_premise_selection"] == 0
    debt = build_report(
        source_text="A Hamiltonian source law and Hilbert-space state imply the result.",
        lean_text=(
            "abbrev Law (_ : Prop) : Prop := True\n"
            "abbrev UnitDimensionCompatible (_ : Prop) : Prop := True\n"
            "theorem bad (source_law : True) (psi H : Real) "
            "(unit_dimension_bridge : UnitDimensionCompatible True) : True := by trivial\n"
        ),
        type_packet={},
        assumption_packet={},
        unit_report={"status": "missing"},
        semantics_report={},
        assumption_report={},
        dimension_report={},
        lean_path="libraries/MathformerPhysicsLib/Lean/formalphysics_9999/MathformerPhysics.lean",
    )
    assert debt["grounding_debt_report"]["finding_count"] >= 3
    assert "source_law_typed_true" in {
        item["code"] for item in debt["grounding_debt_report"]["findings"]
    }
    return collapse


def main(argv: Sequence[str] | None = None) -> int:
    """Run the monitor and print or write the JSON report."""
    args = parse_args(argv)
    report = (
        run_self_test() if args.self_test else build_report(**load_inputs(vars(args)))
    )
    return emit(vars(args), report)


if __name__ == "__main__":
    raise SystemExit(main())
