#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.
#
# Intent:
#   Tell coding agents what context to load, what invariants to preserve, and how to validate their work.
#
# Function:
#   Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Review final physics hypotheses for an Isabelle/HOL physics theory."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence

PHYSICAL_TERMS = [
    "force",
    "mass",
    "acceleration",
    "velocity",
    "energy",
    "momentum",
    "charge",
    "current",
    "field",
    "unit",
    "dimension",
]
VECTOR_TERMS = [
    "vector",
    "field",
    "gradient",
    "curl",
    "divergence",
    "cross",
    "\\vec",
    "\\times",
]
LAW_TERMS = [
    "newton",
    "maxwell",
    "lagrange",
    "hamilton",
    "conservation",
    "law",
    "constitutive",
]
ASSUMPTION_TERMS = [
    "positive",
    "nonzero",
    "non-zero",
    "differentiable",
    "smooth",
    "boundary",
    "regime",
]
BACKGROUND_SOURCE_TERMS = [
    "define",
    "definition",
    "given by",
    "euler",
    "lagrange",
    "lorentz",
    "maxwell",
    "hamilton",
    "tdse",
    "schrodinger",
    "operator",
    "potential",
    "partial",
    "derivative",
    "product rule",
    "chain rule",
    "projection",
    "component",
]
ISABELLE_NATIVE_SURFACE_TERMS = [
    "Complex_Main",
    "HOL-Analysis",
    "euclidean_space",
    "real_normed_vector",
    "real_inner",
    "complex",
    "inner",
    "norm",
    "dist",
    "bounded_linear",
    "linear",
    "continuous_on",
    "DERIV",
    "has_derivative",
    "has_vector_derivative",
    "integrable_on",
    "integral",
    "algebra_simps",
    "field_simps",
]
ISABELLE_VECTOR_SURFACE_TERMS = [
    "euclidean_space",
    "real_normed_vector",
    "real_inner",
    "inner",
    "norm",
    "real ^",
    "bounded_linear",
    "linear",
]
LOCAL_SCAFFOLD_PATTERNS = [
    r"\btypedecl\s+phys_dim\b",
    r"\bdatatype\s+quantity_kind\b",
    r"\brecord\s+physics_context\b",
    r"\brecord\s+source_law\b",
    r"\brecord\s+['A-Za-z0-9_ ]*quantity\b",
    r"\btype_synonym\s+['A-Za-z0-9_(), ]*vector_quantity\b",
]


def read_text(path: Path | None, inline: str | None) -> str:
    """Document the responsibility of ``read_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if inline is not None:
        return inline
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


def load_json(path: Path | None) -> dict[str, Any]:
    """Document the responsibility of ``load_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def has_any(text: str, terms: Sequence[str]) -> bool:
    """Document the responsibility of ``has_any``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_any`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def add_finding(
    findings: list[dict[str, Any]],
    severity: str,
    code: str,
    message: str,
    repair_surface: str,
) -> None:
    """Document the responsibility of ``add_finding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "repair_surface": repair_surface,
        }
    )


def packet_text(packet: dict[str, Any]) -> str:
    """Document the responsibility of ``packet_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``packet_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return json.dumps(packet, ensure_ascii=False).lower() if packet else ""


def packet_raw_text(packet: dict[str, Any]) -> str:
    """Document the responsibility of ``packet_raw_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``packet_raw_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return json.dumps(packet, ensure_ascii=False) if packet else ""


def strip_isabelle_text_blocks(theory_text: str) -> str:
    """Document the responsibility of ``strip_isabelle_text_blocks``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``strip_isabelle_text_blocks`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    without_symbolic = re.sub(
        r"text\s+\\<open>.*?\\<close>", "", theory_text, flags=re.S
    )
    return re.sub(r"text\s+<open>.*?<close>", "", without_symbolic, flags=re.S)


def count_terms(text: str, terms: Sequence[str]) -> int:
    """Document the responsibility of ``count_terms``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_terms`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    count = 0
    for term in terms:
        if re.search(r"\W", term):
            count += text.lower().count(term.lower())
        else:
            count += len(re.findall(rf"\b{re.escape(term)}\b", text, flags=re.I))
    return count


def count_isabelle_native_surfaces(text: str) -> int:
    """Document the responsibility of ``count_isabelle_native_surfaces``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_isabelle_native_surfaces`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return count_terms(text, ISABELLE_NATIVE_SURFACE_TERMS)


def count_isabelle_vector_surfaces(text: str) -> int:
    """Document the responsibility of ``count_isabelle_vector_surfaces``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_isabelle_vector_surfaces`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return count_terms(text, ISABELLE_VECTOR_SURFACE_TERMS)


def count_local_scaffolds(theory_code: str) -> int:
    """Document the responsibility of ``count_local_scaffolds``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_local_scaffolds`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return sum(
        len(re.findall(pattern, theory_code, flags=re.I | re.M))
        for pattern in LOCAL_SCAFFOLD_PATTERNS
    )


def count_string_context_surfaces(theory_code: str) -> int:
    """Document the responsibility of ``count_string_context_surfaces``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``count_string_context_surfaces`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return len(re.findall(r"::\s*string\b", theory_code, flags=re.I)) + len(
        re.findall(
            r'"\s*(?:source|generated|frame|smooth|law|context)[^"]*"',
            theory_code,
            flags=re.I,
        )
    )


def has_typed_prop_context(theory_code: str) -> bool:
    """Document the responsibility of ``has_typed_prop_context``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``has_typed_prop_context`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return bool(
        re.search(
            r"\b(assumes|and)\s+[A-Za-z0-9_']+\s*:\s*\"[^\"]*(?:>|<|~=|\\<noteq>|DERIV|has_derivative|has_vector_derivative|continuous_on|bounded_linear|linear|inner|norm)[^\"]*\"",
            theory_code,
            re.I,
        )
        or re.search(
            r"\bfixes\b[^\n:]+::\s*\"[^\"]*(?:euclidean_space|real_normed_vector|real_inner|complex)[^\"]*\"",
            theory_code,
            re.I,
        )
    )


def library_grounding_level(
    *,
    theory_code: str,
    type_packet: dict[str, Any],
    assumption_packet: dict[str, Any],
) -> str:
    """Document the responsibility of ``library_grounding_level``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``library_grounding_level`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    combined = (
        theory_code
        + "\n"
        + packet_raw_text(type_packet)
        + "\n"
        + packet_raw_text(assumption_packet)
    )
    native_count = count_isabelle_native_surfaces(combined)
    local_count = count_local_scaffolds(theory_code)
    string_count = count_string_context_surfaces(theory_code)
    typed_context = has_typed_prop_context(theory_code)
    if native_count > 0 and local_count == 0 and string_count == 0 and typed_context:
        return "high"
    if native_count > 0:
        return "medium"
    return "low"


def background_items(
    background_packet: dict[str, Any], type_packet: dict[str, Any]
) -> list[dict[str, Any]]:
    """Document the responsibility of ``background_items``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``background_items`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    items = background_packet.get("background_items", []) if background_packet else []
    if isinstance(items, list) and items:
        return [item for item in items if isinstance(item, dict)]
    requirements = type_packet.get("background_formalization_requirements", {}).get(
        "requirements", []
    )
    if isinstance(requirements, list):
        return [item for item in requirements if isinstance(item, dict)]
    return []


def open_background_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Document the responsibility of ``open_background_items``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``open_background_items`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    closed = {
        "formalized",
        "isabelle_reused",
        "isarmathlib_reused",
        "mathformer_reused",
        "blocked",
        "not_required",
        "complete",
    }
    open_items = []
    for item in items:
        status = str(item.get("formalization_status", "needs_autoformalization"))
        if status not in closed:
            open_items.append(item)
    return open_items


def support_declaration_count(theory_code: str) -> int:
    """Document the responsibility of ``support_declaration_count``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``support_declaration_count`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    support_decl = re.compile(
        r"^\s*(definition|abbreviation|locale|lemma)\s+[A-Za-z0-9_'.]+|"
        r"^\s*theorem\s+[A-Za-z0-9_'.]*(?:core|projection|bridge|support|law|unit|dimension|field|calculus|definition)[A-Za-z0-9_'.]*",
        re.M,
    )
    return len(support_decl.findall(theory_code))


def target_as_assumption(theory_text: str) -> bool:
    """Document the responsibility of ``target_as_assumption``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``target_as_assumption`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    assumptions = {
        re.sub(r"\s+", " ", match).strip()
        for match in re.findall(
            r"\b(?:assumes|and)\s+[A-Za-z0-9_']+\s*:\s*\"([^\"]+)\"", theory_text
        )
    }
    shows = {
        re.sub(r"\s+", " ", match).strip()
        for match in re.findall(r"\bshows\s*\"([^\"]+)\"", theory_text)
    }
    return bool(assumptions.intersection(shows))


def build_report(
    *,
    source_text: str,
    theory_text: str,
    type_packet: dict[str, Any],
    assumption_packet: dict[str, Any],
    execution_report: dict[str, Any],
    background_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Document the responsibility of ``build_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: list[dict[str, Any]] = []
    source_physical = has_any(source_text, PHYSICAL_TERMS)
    source_vector = has_any(source_text, VECTOR_TERMS)
    source_law = has_any(source_text, LAW_TERMS)
    source_assumptions = has_any(source_text, ASSUMPTION_TERMS)
    source_background = has_any(source_text, BACKGROUND_SOURCE_TERMS)
    theory_code = strip_isabelle_text_blocks(theory_text)
    combined_type = theory_code + "\n" + packet_raw_text(type_packet)
    combined_assumptions = theory_code + "\n" + packet_raw_text(assumption_packet)
    has_theory_header = bool(
        re.search(r"^theory\s+[A-Za-z][A-Za-z0-9_]*\s*$", theory_text, re.M)
    )
    has_text_block = "text \\<open>" in theory_text or "text <open>" in theory_text
    has_final_theorem = bool(re.search(r"^\s*(theorem|lemma)\b", theory_text, re.M))
    has_source_header = bool(
        re.search(r"Original source|Original informal|Informal", theory_text, re.I)
    )
    has_alignment = bool(
        re.search(
            r"Formalized target|Formal alignment|maps to|Source-backed theorem",
            theory_text,
            re.I,
        )
    )
    native_surface_count = count_isabelle_native_surfaces(combined_type)
    vector_surface_count = count_isabelle_vector_surfaces(combined_type)
    local_scaffold_count = count_local_scaffolds(theory_code)
    string_context_count = count_string_context_surfaces(theory_code)
    typed_prop_context = has_typed_prop_context(theory_code)
    grounding_level = library_grounding_level(
        theory_code=theory_code,
        type_packet=type_packet,
        assumption_packet=assumption_packet,
    )
    required_background_items = background_items(background_packet or {}, type_packet)
    open_background = open_background_items(required_background_items)
    support_decl_count = support_declaration_count(theory_code)
    has_quantity_surface = bool(
        re.search(r"quantity|dimension|unit|scalar|real|complex", combined_type, re.I)
        or native_surface_count
    )
    has_vector_surface = bool(
        re.search(r"vector|field|curl|gradient|divergence", combined_type, re.I)
        or vector_surface_count
    )
    has_law_surface = bool(
        re.search(
            r"source_law|law|newton|maxwell|lagrange|constitutive",
            theory_code + "\n" + packet_raw_text(type_packet),
            re.I,
        )
    )
    has_assumption_labels = any(
        label in combined_assumptions.lower()
        for label in [
            "source-backed",
            "source_backed",
            "generated-support",
            "generated_support",
            "isabelle_hol_backed",
            "blocked",
        ]
    )
    placeholder_free = not bool(
        re.search(r"\b(sorry|oops|quickcheck_params|TODO)\b", theory_text, re.I)
    )
    execution_ok = (
        bool(execution_report.get("ok", False)) if execution_report else False
    )
    target_assumed = target_as_assumption(theory_text)

    if source_physical and not has_quantity_surface:
        add_finding(
            findings,
            "critical",
            "missing_quantity_dimension_surface",
            "Physics source lacks visible quantity/dimension/unit surface in Isabelle theory or packet.",
            "quantity_typing",
        )
    if source_vector and not has_vector_surface:
        add_finding(
            findings,
            "critical",
            "missing_vector_field_surface",
            "Vector or field source lacks visible vector/field/projection surface.",
            "projection_bridge",
        )
    if source_law and not has_law_surface:
        add_finding(
            findings,
            "error",
            "missing_law_surface",
            "Physical law provenance is not visible.",
            "law_grounding",
        )
    if source_assumptions and not has_assumption_labels:
        add_finding(
            findings,
            "error",
            "unlabeled_assumptions",
            "Assumptions are present but not source-backed/generated-support labeled.",
            "contextual_assumption",
        )
    if open_background:
        add_finding(
            findings,
            "critical",
            "background_formalization_obligations_open",
            "Required intermediate definitions or background results remain unformalized: "
            + ", ".join(str(item.get("id", "unknown")) for item in open_background[:6]),
            "support_dependency",
        )
    if (source_background or required_background_items) and not support_decl_count:
        add_finding(
            findings,
            "error",
            "missing_background_support_declarations",
            "The source requires intermediate definitions or background results, but the Isabelle artifact does not expose support definitions, bridge lemmas, or reusable core theorems.",
            "support_dependency",
        )
    if source_physical and grounding_level != "high":
        add_finding(
            findings,
            "critical",
            "isabelle_library_grounding_below_complete_threshold",
            "Physics-bearing Isabelle theorem surfaces do not reach high Isabelle/HOL library grounding; local wrappers or scalar cores must be replaced by native HOL/HOL-Analysis carriers, or an explicit dependency blocker must keep the artifact draft/blocked.",
            "isabelle_library_grounding",
        )
    if source_physical and local_scaffold_count:
        add_finding(
            findings,
            "error",
            "local_physics_scaffold_at_final_surface",
            "Local physics records/type declarations remain in the final Isabelle surface; they are fallback scaffolds, not maximal library grounding evidence.",
            "isabelle_library_grounding",
        )
    if source_vector and not vector_surface_count:
        add_finding(
            findings,
            "critical",
            "missing_isabelle_native_vector_surface",
            "The source is vector- or field-bearing, but no Isabelle/HOL native vector, norm/inner-product, function-field, or linear-map surface is visible.",
            "isabelle_library_grounding",
        )
    if source_physical and string_context_count and not typed_prop_context:
        add_finding(
            findings,
            "error",
            "string_context_without_typed_prop_context",
            "Context, law, frame, or smoothness evidence is encoded as string labels without corresponding typed Isabelle assumptions.",
            "isabelle_library_grounding",
        )
    if source_physical and not has_source_header:
        add_finding(
            findings,
            "error",
            "missing_source_commentary",
            "Isabelle theory does not preserve the original informal source in a text block.",
            "source_alignment_commentary",
        )
    if source_physical and not has_alignment:
        add_finding(
            findings,
            "error",
            "missing_informal_to_formal_alignment",
            "Isabelle theory does not map informal source to formal target/proof surface.",
            "source_alignment_commentary",
        )
    if not has_theory_header or not has_text_block:
        add_finding(
            findings,
            "error",
            "malformed_isabelle_surface",
            "Theory header or source-aware text block is missing.",
            "isabelle_surface",
        )
    if not has_final_theorem:
        add_finding(
            findings,
            "critical",
            "missing_final_theorem",
            "Isabelle physics candidate has no visible theorem or lemma.",
            "conclusion_shape",
        )
    if not placeholder_free:
        add_finding(
            findings,
            "critical",
            "placeholder_in_complete_candidate",
            "Complete Isabelle physics candidate cannot contain sorry, oops, quickcheck_params, or TODO.",
            "proof_realness",
        )
    if target_assumed:
        add_finding(
            findings,
            "critical",
            "target_equation_as_assumption",
            "The final target appears verbatim as a theorem assumption.",
            "nonvacuity",
        )
    if not execution_report:
        add_finding(
            findings,
            "critical",
            "missing_isabelle_execution_report",
            "Final Isabelle physics review requires execution evidence.",
            "execution",
        )
    elif not execution_ok:
        add_finding(
            findings,
            "critical",
            "isabelle_execution_not_passing",
            "Isabelle execution report is not passing.",
            "execution",
        )

    severity_rank = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    max_severity = max(
        (severity_rank[item["severity"]] for item in findings), default=0
    )
    status = "fail" if max_severity >= 2 else "warn" if max_severity == 1 else "pass"
    return {
        "style": "physics_isabelle_final_hypothesis_review",
        "status": status,
        "reviewed_properties": {
            "source_physical": source_physical,
            "source_vector": source_vector,
            "source_law": source_law,
            "quantity_surface": has_quantity_surface,
            "vector_surface": has_vector_surface,
            "law_surface": has_law_surface,
            "assumption_labels": has_assumption_labels,
            "source_commentary": has_source_header,
            "formal_alignment": has_alignment,
            "source_background": source_background,
            "has_final_theorem": has_final_theorem,
            "target_as_assumption": target_assumed,
            "execution_ok": execution_ok,
            "isabelle_library_grounding_level": grounding_level,
            "isabelle_native_surface_count": native_surface_count,
            "isabelle_vector_surface_count": vector_surface_count,
            "local_scaffold_count": local_scaffold_count,
            "string_context_surface_count": string_context_count,
            "typed_prop_context": typed_prop_context,
            "background_item_count": len(required_background_items),
            "open_background_item_count": len(open_background),
            "support_declaration_count": support_decl_count,
        },
        "findings": findings,
        "refinement_required": status == "fail",
        "refinement_handoff": {
            "router": "physics-isabelle-workflow-orchestrator",
            "repair_surfaces": sorted({item["repair_surface"] for item in findings}),
            "rerun_gates": [
                "dependency.resolve",
                "isabelle.grounding.search",
                "physics.isabelle.background.plan",
                "review.physics_isabelle_final_hypotheses",
                "review.mathematical_isabelle_final_hypotheses",
            ],
            "monotonicity_constraints": [
                "preserve source anchors and already passing theorem statements",
                "do not weaken the source physics target",
                "do not remove unit/dimension/context labels",
                "do not reduce Isabelle/HOL native library surface coverage",
                "do not remove or weaken already-correct background support declarations",
                "rerun Isabelle execution and consistency gates",
            ],
        },
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Document the responsibility of ``parse_args``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-text")
    parser.add_argument("--theory-file", type=Path)
    parser.add_argument("--theory-text")
    parser.add_argument("--type-packet", type=Path)
    parser.add_argument("--assumption-packet", type=Path)
    parser.add_argument("--execution-report", type=Path)
    parser.add_argument("--background-packet", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    args = parse_args(argv)
    if args.self_test:
        good_theory = """theory PhysicsSelfTest
  imports Complex_Main "HOL-Analysis.Analysis"
begin
text \\<open>Original source (NL): force law with unit and dimension.
Formalized target (Isabelle/HOL): F = m * a.
Source-backed theorem: Newton law scalar projection.
Generated note: source-backed dimensions and generated-support projection.
\\<close>
theorem t:
  fixes F a :: \"'v::euclidean_space\"
  assumes hvec: \"bounded_linear (\\<lambda>x::'v. x)\"
    and hNewtonLaw: \"inner F a = inner F a\"
    and h: \"a = F\"
  shows \"F = a\"
  using h by simp
end
"""
        good_report = build_report(
            source_text="Derive a force law with vector field units.",
            theory_text=good_theory,
            type_packet={
                "style": "isabelle_physics_type_system_packet",
                "isabelle_surfaces": {
                    "vector": "'a::euclidean_space",
                    "calculus": "has_derivative",
                },
            },
            assumption_packet={
                "source_status_policy": {
                    "source_backed": "source-backed",
                    "generated_support": "generated-support",
                }
            },
            execution_report={"ok": True},
            background_packet={},
        )
        assert good_report["status"] == "pass", good_report
        assert (
            good_report["reviewed_properties"]["isabelle_library_grounding_level"]
            == "high"
        )
        bad_theory = """theory PhysicsSelfTest
  imports Main
begin
text \\<open>Original source (NL): force law with unit and dimension.
Formalized target (Isabelle/HOL): F = m * a.
Source-backed theorem: Newton law scalar projection.
Generated note: source-backed dimensions and generated-support projection.
\\<close>
theorem t:
  fixes F m a :: real
  assumes h: \"F = m * a\"
  shows \"F = m * a\"
  using h by simp
end
"""
        report = build_report(
            source_text="Derive a force law with vector field units.",
            theory_text=bad_theory,
            type_packet={
                "style": "isabelle_physics_type_system_packet",
                "isabelle_surfaces": {"quantity": "dimension unit vector field"},
            },
            assumption_packet={
                "source_status_policy": {
                    "source_backed": "source-backed",
                    "generated_support": "generated-support",
                }
            },
            execution_report={"ok": True},
            background_packet={},
        )
        assert report["status"] == "fail"
        assert any(
            item["code"] == "target_equation_as_assumption"
            for item in report["findings"]
        )
        background_report = build_report(
            source_text="Define a vector field from a potential and derive the component projection.",
            theory_text=good_theory,
            type_packet={
                "style": "isabelle_physics_type_system_packet",
                "isabelle_surfaces": {
                    "vector": "'a::euclidean_space",
                    "calculus": "has_derivative",
                },
            },
            assumption_packet={
                "source_status_policy": {"source_backed": "source-backed"}
            },
            execution_report={"ok": True},
            background_packet={
                "background_items": [
                    {
                        "id": "bg.isabelle_field_carrier",
                        "formalization_status": "needs_autoformalization",
                    }
                ]
            },
        )
        assert background_report["status"] == "fail"
        assert (
            "support_dependency"
            in background_report["refinement_handoff"]["repair_surfaces"]
        )
    else:
        report = build_report(
            source_text=read_text(args.source_file, args.source_text),
            theory_text=read_text(args.theory_file, args.theory_text),
            type_packet=load_json(args.type_packet),
            assumption_packet=load_json(args.assumption_packet),
            execution_report=load_json(args.execution_report),
            background_packet=load_json(args.background_packet),
        )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
