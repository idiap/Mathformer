#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Check Lean physics derivation completeness beyond kernel compilation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
DECL_RE = re.compile(r"^\s*(theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_'.]*)\b", re.M)
WRAPPER_NAMES = ("PhysicalLawWitness", "GeneratedSupportAssumption")
COMPLETE_STATUS = "complete_autoformalization"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_prop(text: str) -> str:
    text = text.strip()
    while text.startswith("(") and text.endswith(")") and balanced(text[1:-1]):
        text = text[1:-1].strip()
    text = re.sub(r"\s+", "", text)
    text = text.replace("(", "").replace(")", "")
    return text


def balanced(text: str) -> bool:
    depth = 0
    pairs = {")": "(", "}": "{", "]": "["}
    stack: list[str] = []
    for char in text:
        if char in "({[":
            stack.append(char)
            depth += 1
        elif char in ")}]":
            if not stack or stack[-1] != pairs[char]:
                return False
            stack.pop()
            depth -= 1
    return depth == 0


def strip_outer_group(text: str) -> str:
    text = text.strip()
    if (
        len(text) >= 2
        and text[0] in "({"
        and (
            (text[0] == "(" and text[-1] == ")") or (text[0] == "{" and text[-1] == "}")
        )
    ):
        inner = text[1:-1].strip()
        if balanced(inner):
            return inner
    return text


def find_top_level_colon(text: str) -> int:
    depth = 0
    last = -1
    for index, char in enumerate(text):
        if char in "({[":
            depth += 1
        elif char in ")}]":
            depth = max(0, depth - 1)
        elif char == ":" and depth == 0 and text[index : index + 2] != ":=":
            last = index
    return last


def split_declaration_blocks(lean_text: str) -> list[dict[str, str]]:
    starts = list(DECL_RE.finditer(lean_text))
    blocks: list[dict[str, str]] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(lean_text)
        block = lean_text[match.start() : end]
        blocks.append({"kind": match.group(1), "name": match.group(2), "text": block})
    return blocks


def signature_and_proof(block: str) -> tuple[str, str]:
    marker = block.find(":= by")
    if marker >= 0:
        return block[:marker], block[marker + len(":= by") :]
    marker = block.find(":=")
    if marker >= 0:
        return block[:marker], block[marker + len(":=") :]
    return block, ""


def extract_conclusion(signature: str) -> str:
    colon = find_top_level_colon(signature)
    if colon < 0:
        return ""
    return signature[colon + 1 :].strip()


def top_level_groups(text: str) -> list[str]:
    groups: list[str] = []
    stack: list[tuple[str, int]] = []
    pairs = {")": "(", "}": "{", "]": "["}
    for index, char in enumerate(text):
        if char in "({[":
            stack.append((char, index))
        elif char in ")}]" and stack:
            opener, start = stack[-1]
            if opener == pairs[char]:
                stack.pop()
                if not stack and opener in "({":
                    groups.append(text[start : index + 1])
    return groups


def split_binder(group: str) -> dict[str, Any] | None:
    content = strip_outer_group(group)
    colon = find_top_level_colon(content)
    if colon < 0:
        return None
    names = content[:colon].strip()
    binder_type = content[colon + 1 :].strip()
    name_parts = [
        part for part in re.split(r"\s+", names) if part and not part.startswith("_")
    ]
    if not name_parts:
        return None
    return {"names": name_parts, "type": binder_type, "raw": group}


def wrapper_payload(binder_type: str) -> tuple[str, str] | None:
    stripped = binder_type.strip()
    for wrapper in WRAPPER_NAMES:
        if stripped.startswith(wrapper):
            payload = stripped[len(wrapper) :].strip()
            return wrapper, strip_outer_group(payload)
    return None


def proof_exact_unwraps(proof: str) -> list[str]:
    names = re.findall(r"\bexact\s+physicalLawHolds\s+([A-Za-z_][A-Za-z0-9_']*)", proof)
    names.extend(
        re.findall(
            r"\bexact\s+generatedSupportHolds\s+([A-Za-z_][A-Za-z0-9_']*)", proof
        )
    )
    return names


def add_finding(
    findings: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    message: str,
    declaration: str,
    evidence: dict[str, Any],
    repair_surface: str = "target_nonvacuity",
) -> None:
    findings.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "declaration": declaration,
            "evidence": evidence,
            "repair_surface": repair_surface,
        }
    )


def analyze_declaration(declaration: dict[str, str]) -> dict[str, Any]:
    signature, proof = signature_and_proof(declaration["text"])
    conclusion = extract_conclusion(signature)
    normalized_conclusion = normalize_prop(conclusion)
    binders = [
        binder
        for group in top_level_groups(signature)
        if (binder := split_binder(group))
    ]
    target_like_names: set[str] = set()
    findings: list[dict[str, Any]] = []
    if declaration["name"] in {
        "physicalLawHolds",
        "generatedSupportHolds",
        "dimensionCompatibleEq",
    }:
        return {
            "kind": declaration["kind"],
            "name": declaration["name"],
            "conclusion": conclusion,
            "binder_count": len(binders),
            "target_like_hypotheses": [],
            "findings": [],
            "ignored_projection_declaration": True,
        }

    for binder in binders:
        binder_type = str(binder["type"])
        normalized_type = normalize_prop(binder_type)
        for name in binder["names"]:
            if normalized_conclusion and normalized_type == normalized_conclusion:
                target_like_names.add(name)
                add_finding(
                    findings,
                    severity="high",
                    code="direct_target_repeated_as_hypothesis",
                    message="A theorem hypothesis has the same proposition as the theorem conclusion.",
                    declaration=declaration["name"],
                    evidence={
                        "hypothesis": name,
                        "hypothesis_type": binder_type,
                        "conclusion": conclusion,
                    },
                )
        wrapped = wrapper_payload(binder_type)
        if not wrapped:
            continue
        wrapper, payload = wrapped
        if normalized_conclusion and normalize_prop(payload) == normalized_conclusion:
            for name in binder["names"]:
                target_like_names.add(name)
                add_finding(
                    findings,
                    severity="high",
                    code="target_restatement_wrapped_in_witness",
                    message=f"{wrapper} wraps the theorem conclusion and cannot count as complete derivation support.",
                    declaration=declaration["name"],
                    evidence={
                        "hypothesis": name,
                        "wrapper": wrapper,
                        "wrapped_proposition": payload,
                        "conclusion": conclusion,
                    },
                )

    for name in proof_exact_unwraps(proof):
        if name in target_like_names:
            add_finding(
                findings,
                severity="high",
                code="proof_exactly_unwraps_target_witness",
                message="The proof closes by unwrapping a hypothesis whose proposition is the final target.",
                declaration=declaration["name"],
                evidence={"hypothesis": name, "conclusion": conclusion},
            )

    return {
        "kind": declaration["kind"],
        "name": declaration["name"],
        "conclusion": conclusion,
        "binder_count": len(binders),
        "target_like_hypotheses": sorted(target_like_names),
        "findings": findings,
    }


def heisenberg_obligations(lean_text: str) -> list[dict[str, Any]]:
    def has(needle):
        return needle in lean_text

    return [
        {
            "id": "hilbert_state_and_operator_surface",
            "description": "Represent states and operators on a Mathlib Hilbert-space surface.",
            "status": (
                "mathformerphysicslib_reused"
                if has("HilbertStateCarrier") and has("HilbertBoundedOperator")
                else "blocked"
            ),
            "evidence": ["HilbertStateCarrier", "HilbertBoundedOperator"],
        },
        {
            "id": "fluctuation_ket_definition",
            "description": "Use fluctuation kets for position and momentum deviations.",
            "status": (
                "mathformerphysicslib_reused" if has("fluctuationKet") else "blocked"
            ),
            "evidence": ["fluctuationKet"],
        },
        {
            "id": "expectation_value_binding",
            "description": "Bind xMean and pMean to expectation values of X and P in psi.",
            "status": (
                "proved"
                if "hilbertExpectation X psi" in lean_text
                and "hilbertExpectation P psi" in lean_text
                else "blocked"
            ),
            "evidence": ["xMean_law", "pMean_law", "hilbertExpectation"],
        },
        {
            "id": "commutator_to_dirac_bridge",
            "description": "Derive the braket difference or quotient from the canonical commutator law.",
            "status": (
                "proved_from_commutator_expectation"
                if "braket_difference_eq_commutator : PhysicalLawWitness" in lean_text
                and "canonical_commutator_expectation : PhysicalLawWitness" in lean_text
                and "diracImaginaryQuotient_from_commutator_expectation" in lean_text
                else (
                    "source_law_labeled"
                    if "commutator_bridge : PhysicalLawWitness" in lean_text
                    and "diracImaginaryQuotient_conjugate_lower_bound" in lean_text
                    else (
                        "blocked_commutator_imaginary_lower_bound"
                        if "commutator_inner_lower_bound : PhysicalLawWitness"
                        in lean_text
                        else (
                            "blocked"
                            if "commutator_bridge : PhysicalLawWitness" in lean_text
                            else "proved"
                        )
                    )
                )
            ),
            "evidence": [
                "braket_difference_eq_commutator",
                "canonical_commutator_expectation",
                "hilbertCommutatorExpectation",
                "diracImaginaryQuotient_from_commutator_expectation",
                "diracImaginaryQuotient_conjugate_lower_bound",
                "transitionAmplitude",
            ],
        },
        {
            "id": "variance_identity_sigma_x",
            "description": "Derive sigmaX squared from the fluctuation ket norm or inner product.",
            "status": (
                "generated_support_labeled"
                if "sigmaX_variance : PhysicalLawWitness" in lean_text
                and "fluctuationNormSquared X xMean psi" in lean_text
                else (
                    "proved"
                    if re.search(r"sigmaX\s*\^\s*2\s*=", lean_text)
                    else "blocked"
                )
            ),
            "evidence": ["sigmaX_variance", "fluctuationKet", "fluctuationNormSquared"],
        },
        {
            "id": "variance_identity_sigma_p",
            "description": "Derive sigmaP squared from the fluctuation ket norm or inner product.",
            "status": (
                "generated_support_labeled"
                if "sigmaP_variance : PhysicalLawWitness" in lean_text
                and "fluctuationNormSquared P pMean psi" in lean_text
                else (
                    "proved"
                    if re.search(r"sigmaP\s*\^\s*2\s*=", lean_text)
                    else "blocked"
                )
            ),
            "evidence": ["sigmaP_variance", "fluctuationKet", "fluctuationNormSquared"],
        },
        {
            "id": "cauchy_schwarz_application",
            "description": "Apply Cauchy-Schwarz to the fluctuation kets rather than assume the final inequality.",
            "status": (
                "proved"
                if "heisenbergVarianceProductBoundFromInnerLower" in lean_text
                else (
                    "blocked_target_restating_assumption"
                    if "cauchy_schwarz_uncertainty_law : PhysicalLawWitness"
                    in lean_text
                    else (
                        "blocked_intermediate_witness"
                        if "cauchy_schwarz_fluctuation_bound : PhysicalLawWitness"
                        in lean_text
                        or "cauchy_schwarz_squared_bound : PhysicalLawWitness"
                        in lean_text
                        else "proved"
                    )
                )
            ),
            "evidence": [
                "heisenbergVarianceProductBoundFromInnerLower",
                "norm_inner_le_norm",
            ],
        },
        {
            "id": "nonnegativity_and_square_root_step",
            "description": "Discharge nonnegativity and square-root/order reasoning for standard deviations.",
            "status": (
                "proved"
                if "heisenbergBoundFromSquaredLowerBound" in lean_text
                and "sigmaX_nonneg" in lean_text
                and "sigmaP_nonneg" in lean_text
                and "hbar_nonneg" in lean_text
                else (
                    "blocked_order_frontier"
                    if "lower_bound_identification : PhysicalLawWitness" in lean_text
                    or "cauchy_schwarz_squared_bound : PhysicalLawWitness" in lean_text
                    else (
                        "blocked"
                        if "sigmaX * sigmaP ≥ hbar / 2" in lean_text
                        and "Real.sqrt" not in lean_text
                        else "proved"
                    )
                )
            ),
            "evidence": [
                "heisenbergBoundFromSquaredLowerBound",
                "sigmaX_nonneg",
                "sigmaP_nonneg",
                "hbar_nonneg",
            ],
        },
    ]


def obligation(
    *,
    id: str,
    description: str,
    status: str,
    evidence: Sequence[str],
) -> dict[str, Any]:
    return {
        "id": id,
        "description": description,
        "status": status,
        "evidence": list(evidence),
    }


def vacuum_rabi_obligations(lean_text: str) -> list[dict[str, Any]]:
    def has(needle):
        return needle in lean_text

    return [
        obligation(
            id="two_level_basis_state_surface",
            description="Represent the two-level atom/photon basis and state on a Hilbert-space carrier.",
            status=(
                "mathformerphysicslib_reused"
                if has("HilbertStateCarrier")
                and has("NormalizedStateWitness")
                and has("HilbertOrthogonalityWitness")
                else "blocked"
            ),
            evidence=[
                "HilbertStateCarrier",
                "NormalizedStateWitness",
                "HilbertOrthogonalityWitness",
            ],
        ),
        obligation(
            id="transition_amplitude_from_state_expansion",
            description="Derive the transition amplitude from the expanded Rabi state and orthonormal basis.",
            status=(
                "blocked_bridge_witness"
                if "amplitude_law : PhysicalLawWitness" in lean_text
                else "proved"
            ),
            evidence=["amplitude_law", "transitionAmplitude", "orthogonality"],
        ),
        obligation(
            id="born_probability_from_amplitude",
            description="Derive the Born probability as the norm squared of the transition amplitude.",
            status=(
                "blocked_target_restating_assumption"
                if "probability_law : PhysicalLawWitness" in lean_text
                else "proved"
            ),
            evidence=["probability_law", "probabilityFromAmplitude", "Real.sin"],
        ),
        obligation(
            id="complex_norm_square_minus_i_sin",
            description="Prove that the norm squared of -i sin(Omega t / 2) is sin(Omega t / 2)^2.",
            status=(
                "proved"
                if "probabilityFromAmplitude ℂ" in lean_text
                or "Complex.normSq" in lean_text
                else "blocked"
            ),
            evidence=["Complex.I", "Real.sin", "norm squared"],
        ),
        obligation(
            id="probability_dimension_gate",
            description="Keep the probability equality dimension-compatible.",
            status=(
                "mathformerphysicslib_reused"
                if "DimensionCompatible" in lean_text
                else "blocked"
            ),
            evidence=["DimensionCompatible"],
        ),
    ]


def parameter_hamiltonian_obligations(lean_text: str) -> list[dict[str, Any]]:
    def has(needle):
        return needle in lean_text

    return [
        obligation(
            id="hamiltonian_operator_surface",
            description="Represent the parameterized Hamiltonian, derivative Hamiltonian, and expectation as Hilbert operators.",
            status=(
                "mathformerphysicslib_reused"
                if has("HilbertBoundedOperator")
                and has("hilbertExpectation")
                and has("parameterizedHilbertExpectation")
                else "blocked"
            ),
            evidence=[
                "HilbertBoundedOperator",
                "hilbertExpectation",
                "parameterizedHilbertExpectation",
            ],
        ),
        obligation(
            id="eigenvalue_to_expectation_curve_bridge",
            description="Derive the near energy/expectation curve identity from the eigenvalue equation and normalization.",
            status=(
                "proved"
                if has("energy_eq_parameterizedExpectation_near_of_eigenstate")
                and has("ParameterizedEigenstateEquation")
                and has("EigenstateExpectationIdentityNear")
                else (
                    "blocked_source_bridge"
                    if "energy_eq_expectation_near" in lean_text
                    else (
                        "blocked_target_restating_assumption"
                        if "expectation_identity : PhysicalLawWitness" in lean_text
                        else "blocked"
                    )
                )
            ),
            evidence=[
                "energy_eq_expectation_near",
                "eigenvalue equation",
                "normalization",
            ],
        ),
        obligation(
            id="parameterized_curve_and_differentiability",
            description="Represent actual lambda-indexed state/operator/eigenvalue curves before differentiating.",
            status=(
                "mathformerphysicslib_reused"
                if has("parameterizedHilbertExpectation")
                and has("HasDerivAt")
                and has("nhds lambda")
                else (
                    "blocked_generated_support_tautology"
                    if "GeneratedSupportAssumption (Differentiable ℝ (fun t : ℝ => t))"
                    in lean_text
                    else "blocked"
                )
            ),
            evidence=[
                "parameterizedHilbertExpectation",
                "HasDerivAt",
                "lambda-indexed curve",
            ],
        ),
        obligation(
            id="derivative_uniqueness_transfer_bridge",
            description="Prove equality of derivatives from near equality of the energy and expectation curves.",
            status=(
                "proved"
                if has("energyDerivativeEqExpectationDerivative")
                and "differentiation_law : PhysicalLawWitness" not in lean_text
                else (
                    "blocked_target_restating_assumption"
                    if "differentiation_law : PhysicalLawWitness" in lean_text
                    else "blocked"
                )
            ),
            evidence=["energyDerivativeEqExpectationDerivative", "HasDerivAt.unique"],
        ),
        obligation(
            id="expectation_derivative_calculation",
            description="Calculate the derivative of the expectation curve as <psi|dH|psi> under the needed state/operator hypotheses.",
            status=(
                "proved"
                if has("hellmannFeynmanDerivativeFromDifferentiatedEigenEquation")
                and has("DifferentiatedEigenstateEquation")
                and has("SelfAdjointOperatorWitness")
                else (
                    "blocked_target_restating_assumption"
                    if "differentiation_law : PhysicalLawWitness" in lean_text
                    else (
                        "blocked_typed_derivative_premise"
                        if "expectation_has_deriv" in lean_text
                        and "hilbertExpectation dHamiltonian psi" in lean_text
                        else "blocked"
                    )
                )
            ),
            evidence=[
                "expectation_has_deriv",
                "dHamiltonian",
                "hilbertExpectation dHamiltonian psi",
            ],
        ),
    ]


def position_expectation_obligations(lean_text: str) -> list[dict[str, Any]]:
    def has(needle):
        return needle in lean_text

    return [
        obligation(
            id="position_wavefunction_surface",
            description="Represent the position wavefunction and pointwise Born integrand.",
            status=(
                "mathformerphysicslib_reused"
                if has("PositionWavefunction") and has("positionExpectationIntegrand")
                else "blocked"
            ),
            evidence=["PositionWavefunction", "positionExpectationIntegrand"],
        ),
        obligation(
            id="born_density_integrand_bridge",
            description="Derive x * |Psi(x)|^2 from the Dirac position wavefunction definition.",
            status=(
                "blocked_bridge_witness"
                if "wavefunction_law : PhysicalLawWitness" in lean_text
                else "proved"
            ),
            evidence=[
                "wavefunction_law",
                "positionExpectationIntegrand",
                "‖psi x‖ ^ 2",
            ],
        ),
        obligation(
            id="resolution_identity_measure_kernel",
            description="Ground the position-basis resolution of identity and delta-kernel integration.",
            status=(
                "blocked_generated_support_tautology"
                if "resolution_of_identity : GeneratedSupportAssumption (Nonempty X)"
                in lean_text
                else "proved"
            ),
            evidence=["resolution_of_identity", "Dirac delta kernel", "MeasureTheory"],
        ),
        obligation(
            id="born_integral_bridge",
            description="Prove the expectation/integral equality instead of assuming the final equation.",
            status=(
                "blocked_target_restating_assumption"
                if "born_rule_integral_law : PhysicalLawWitness" in lean_text
                else "proved"
            ),
            evidence=["born_rule_integral_law", "expectation", "bornIntegral"],
        ),
        obligation(
            id="measure_integral_mathlib_surface",
            description="Use a Mathlib measure/integral surface for the position expectation value.",
            status=(
                "mathlib_reused"
                if "MeasureTheory" in lean_text or "∫" in lean_text
                else "blocked"
            ),
            evidence=["MeasureTheory", "integral"],
        ),
    ]


def dirac_imaginary_part_obligations(lean_text: str) -> list[dict[str, Any]]:
    def has(needle):
        return needle in lean_text

    return [
        obligation(
            id="braket_binding_surface",
            description="Bind z and reverse to Dirac transition amplitudes definitionally or by proved source lemmas.",
            status=(
                "blocked_definitional_binding"
                if "z_law : PhysicalLawWitness" in lean_text
                or "reverse_law : PhysicalLawWitness" in lean_text
                else "proved"
            ),
            evidence=["z_law", "reverse_law", "transitionAmplitude"],
        ),
        obligation(
            id="conjugate_symmetry_surface",
            description="Use Hilbert-space conjugate symmetry for the reversed braket.",
            status=(
                "mathformerphysicslib_reused"
                if has("DiracConjugateSymmetryWitness")
                else "blocked"
            ),
            evidence=["DiracConjugateSymmetryWitness", "conjugate_relation"],
        ),
        obligation(
            id="complex_imaginary_quotient_bridge",
            description="Prove Im z = (z - z*) / (2i) on the Complex/Dirac quotient surface.",
            status=(
                "blocked_complex_im_projection"
                if "diracImaginaryQuotient_eq_starQuotient" in lean_text
                and "Complex.im" not in lean_text
                else (
                    "blocked_bridge_witness"
                    if "quotient_law : PhysicalLawWitness" in lean_text
                    else "proved"
                )
            ),
            evidence=[
                "diracImaginaryQuotient_eq_starQuotient",
                "diracImaginaryQuotient",
                "Complex.im",
            ],
        ),
        obligation(
            id="quotient_definition_rewrite",
            description="Replace quotient as a free variable with a definition or proved lemma from z and reverse.",
            status=(
                "blocked_bridge_witness"
                if "quotient_law : PhysicalLawWitness" in lean_text
                else "proved"
            ),
            evidence=["quotient_law", "quotient", "diracImaginaryQuotient"],
        ),
        obligation(
            id="square_identity_bridge",
            description="Prove the square identity from the imaginary-part bridge instead of assuming imSq = quotient^2.",
            status=(
                "blocked_bridge_witness"
                if "square_law : PhysicalLawWitness" in lean_text
                else "proved"
            ),
            evidence=["square_law", "imSq", "quotient ^ 2"],
        ),
    ]


def generic_obligations(
    source_record: dict[str, Any], lean_text: str
) -> list[dict[str, Any]]:
    case_id = str(source_record.get("case_id") or "")
    case_obligation_builders = {
        "formalphysics_0015": vacuum_rabi_obligations,
        "formalphysics_0021": parameter_hamiltonian_obligations,
        "formalphysics_0052": position_expectation_obligations,
        "formalphysics_0074": dirac_imaginary_part_obligations,
    }
    if case_id in case_obligation_builders:
        return case_obligation_builders[case_id](lean_text)

    required_terms = [str(item) for item in source_record.get("required_terms", [])]
    if required_terms:
        workflow_stage_reports = source_record.get("workflow_stage_reports", {})
        if not isinstance(workflow_stage_reports, dict):
            workflow_stage_reports = {}
        required_workflow_stages = [
            "source_extraction",
            "informal_expansion",
            "readiness_review",
            "symbol_table",
            "equation_parse",
            "dimension_model",
            "unit_grounding",
            "derivation_plan",
            "lean_workflow_plan",
            "lean_type_packet",
            "lean_assumption_packet",
            "math_object_detection",
            "mathlib_grounding",
            "lean_execution",
            "unit_report",
            "semantics_critic",
            "assumption_critic",
            "dimension_critic",
            "drift_monitor",
            "pathology_repair",
            "generative_repair",
            "repair_expansion_map",
            "recursive_control",
            "final_hypothesis_review",
            "consistency_report",
        ]
        obligations = [
            obligation(
                id=f"required_grounding_term_{index + 1}",
                description=f"Required grounded Lean surface `{term}` appears in the artifact.",
                status=(
                    "mathformerphysicslib_reused"
                    if term in lean_text
                    else "blocked_missing_required_term"
                ),
                evidence=[term],
            )
            for index, term in enumerate(required_terms)
        ]

        def workflow_stage_evidenced(stage: str) -> bool:
            report = workflow_stage_reports.get(stage)
            if isinstance(report, dict):
                if not bool(report.get("ok") is True and report.get("path")):
                    return False
                bad_statuses = {
                    "fail",
                    "blocked",
                    "needs_expansion",
                    "blocked_on_library_or_labels",
                }
                status = str(report.get("payload_status") or "")
                decision = str(report.get("payload_decision") or "")
                payload_ok = report.get("payload_ok")
                if (
                    status in bad_statuses
                    or decision == "blocked"
                    or payload_ok is False
                ):
                    return False
                if stage == "recursive_control":
                    return decision == "complete" or status == "complete"
                return True
            return bool(report)

        for stage in required_workflow_stages:
            report = workflow_stage_reports.get(stage, "")
            evidenced = workflow_stage_evidenced(stage)
            obligations.append(
                obligation(
                    id=f"workflow_stage_{stage}",
                    description=f"Previous physics autoformalization workflow stage `{stage}` has report evidence.",
                    status=(
                        "workflow_stage_evidenced"
                        if evidenced
                        else "blocked_missing_workflow_stage"
                    ),
                    evidence=[stage, str(report)],
                )
            )
        if "Recursive grounding:" not in lean_text:
            obligations.append(
                obligation(
                    id="recursive_grounding_header",
                    description="Artifact must describe the recursive MathformerPhysicsLib grounding path.",
                    status="blocked_missing_recursive_grounding_header",
                    evidence=["Recursive grounding:"],
                )
            )
        source_blob = " ".join(
            [
                str(source_record.get("field", "")),
                str(source_record.get("question", "")),
                " ".join(str(item) for item in source_record.get("concepts", [])),
            ]
        ).lower()
        quantum_like = any(
            term in source_blob
            for term in [
                "quantum",
                "heisenberg",
                "schrodinger",
                "schrödinger",
                "oscillator",
                "dirac",
                "hilbert",
                "hamiltonian",
            ]
        )
        if (
            quantum_like
            and "MathformerPhysicsLib.Foundations.QuantumMechanicsExamples"
            not in lean_text
        ):
            obligations.append(
                obligation(
                    id="qm_examples_namespace_opened",
                    description="New QM examples must reuse the shared quantum-mechanics example surfaces.",
                    status="blocked_missing_qm_examples_surface",
                    evidence=["QuantumMechanicsExamples"],
                )
            )
        return obligations

    concepts = [str(item) for item in source_record.get("concepts", [])]
    obligations: list[dict[str, Any]] = []
    for index, concept in enumerate(concepts):
        concept_lower = concept.lower()
        if any(
            term in concept_lower for term in ["heisenberg", "fluctuation", "cauchy"]
        ):
            return heisenberg_obligations(lean_text)
        status = "mathformerphysicslib_reused"
        if (
            "bound" in concept_lower
            or "identity" in concept_lower
            or "law" in concept_lower
        ):
            status = (
                "generated_support_labeled"
                if "PhysicalLawWitness" in lean_text
                else "blocked"
            )
        obligations.append(
            {
                "id": f"source_concept_{index + 1}",
                "description": concept,
                "status": status,
                "evidence": [concept],
            }
        )
    return obligations


def repair_frontier_nodes(
    obligations: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    mapping = {
        "expectation_value_binding": "dirac.expectation_value",
        "commutator_to_dirac_bridge": "dirac.imaginary_part_identity",
        "variance_identity_sigma_x": "dirac.fluctuation_ket",
        "variance_identity_sigma_p": "dirac.fluctuation_ket",
        "cauchy_schwarz_application": "dirac.fluctuation_ket",
        "nonnegativity_and_square_root_step": "ordered_real_variance.standard_deviation",
        "transition_amplitude_from_state_expansion": "dirac.transition_amplitude",
        "born_probability_from_amplitude": "dirac.born_probability",
        "complex_norm_square_minus_i_sin": "complex.norm_square_trigonometric_amplitude",
        "expectation_identity_from_eigen_law": "dirac.expectation_value",
        "parameterized_curve_and_differentiability": "calculus.parameterized_hilbert_curve",
        "hellmann_feynman_derivative_bridge": "quantum.hellmann_feynman_derivative",
        "eigenvalue_to_expectation_curve_bridge": "quantum.eigenstate_expectation_identity",
        "derivative_uniqueness_transfer_bridge": "calculus.derivative_uniqueness",
        "expectation_derivative_calculation": "quantum.hellmann_feynman_derivative",
        "born_density_integrand_bridge": "dirac.position_wavefunction",
        "resolution_identity_measure_kernel": "measure_theory.position_basis_resolution",
        "born_integral_bridge": "dirac.position_expectation_integral",
        "measure_integral_mathlib_surface": "measure_theory.integral_surface",
        "braket_binding_surface": "dirac.transition_amplitude",
        "complex_imaginary_quotient_bridge": "complex.imaginary_part_quotient",
        "quotient_definition_rewrite": "dirac.imaginary_part_identity",
        "square_identity_bridge": "algebra.square_congruence",
    }
    nodes: list[dict[str, Any]] = []
    for obligation in obligations:
        status = str(obligation.get("status"))
        if not status.startswith("blocked"):
            continue
        object_id = mapping.get(str(obligation.get("id")), str(obligation.get("id")))
        nodes.append(
            {
                "id": f"derivation.{obligation['id']}",
                "object_id": object_id,
                "status": "outstanding",
                "reason": obligation.get("description"),
                "next_action": "expand_foundation_surface_then_rerun_derivation_completeness",
            }
        )
    return nodes


def generative_probes(
    findings: Sequence[dict[str, Any]], obligations: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    context = {
        "findings": list(findings),
        "blocked_obligations": [
            item
            for item in obligations
            if str(item.get("status")).startswith("blocked")
        ],
    }
    context_json = json.dumps(context, ensure_ascii=False, indent=2, sort_keys=True)
    base = {
        "style": "physics_lean_derivation_completeness_generative_probe",
        "deterministic_context_json": context_json,
        "required_evidence": [
            "finding code",
            "declaration",
            "obligation id",
            "rerun gate",
        ],
        "blocking_policy": "advisory_until_deterministic_checker_reruns",
    }
    return [
        {
            **base,
            "id": "remove_non_source_witness_probe",
            "question": "Would the theorem still prove the target after removing all non-source PhysicalLawWitness hypotheses?",
        },
        {
            **base,
            "id": "equivalent_hypothesis_probe",
            "question": "Which theorem hypothesis is equivalent to the final conclusion?",
        },
        {
            **base,
            "id": "missing_source_step_probe",
            "question": "Which source derivation step has no Lean proof object or reusable Mathlib/MathformerPhysicsLib theorem?",
        },
        {
            **base,
            "id": "recursive_object_probe",
            "question": "Which MathformerPhysicsLib object should be built next before the target theorem can be complete?",
        },
    ]


def status_from(
    *,
    lean_text: str,
    declarations: Sequence[dict[str, Any]],
    obligations: Sequence[dict[str, Any]],
    recursive_frontier_count: int,
) -> tuple[str, list[str]]:
    flags = ["compiled_surface" if lean_text.strip() else "missing_lean_text"]
    if any(
        term in lean_text
        for term in [
            "MathformerPhysicsLib.Lean.Foundations",
            "HilbertStateCarrier",
            "PhysicalLawWitness",
        ]
    ):
        flags.append("grounded_scaffold")
    blocking_findings = [
        finding
        for declaration in declarations
        for finding in declaration.get("findings", [])
        if finding.get("severity") == "high"
    ]
    blocked_obligations = [
        item for item in obligations if str(item.get("status")).startswith("blocked")
    ]
    if blocking_findings:
        flags.append("derivation_partial")
        return "blocked_target_restating_assumption", flags
    if recursive_frontier_count > 0 or blocked_obligations:
        flags.append("derivation_partial")
        return "derivation_partial", flags
    flags.append(COMPLETE_STATUS)
    return COMPLETE_STATUS, flags


def analyze_file(
    *,
    lean_file: Path,
    source_record: dict[str, Any],
    recursive_frontier_count: int,
) -> dict[str, Any]:
    lean_text = lean_file.read_text(encoding="utf-8")
    declarations = [
        analyze_declaration(block) for block in split_declaration_blocks(lean_text)
    ]
    obligations = generic_obligations(source_record, lean_text)
    status, flags = status_from(
        lean_text=lean_text,
        declarations=declarations,
        obligations=obligations,
        recursive_frontier_count=recursive_frontier_count,
    )
    findings = [
        finding
        for declaration in declarations
        for finding in declaration.get("findings", [])
    ]
    frontier_nodes = repair_frontier_nodes(obligations)
    blocked_obligations = [
        item for item in obligations if str(item.get("status")).startswith("blocked")
    ]
    return {
        "file": rel(lean_file),
        "case_id": source_record.get("case_id"),
        "status": status,
        "status_flags": flags,
        "complete": status == COMPLETE_STATUS,
        "declaration_count": len(declarations),
        "declarations": declarations,
        "findings": findings,
        "obligations": obligations,
        "blocked_obligations": blocked_obligations,
        "blocked_obligation_count": len(blocked_obligations),
        "recursive_frontier_count": recursive_frontier_count,
        "repair_frontier_nodes": frontier_nodes,
        "generative_repair_probes": generative_probes(findings, obligations),
    }


def recursive_frontier_count(plan: dict[str, Any]) -> int:
    if not plan:
        return 0
    if "recursive_frontier_count" in plan:
        return int(plan.get("recursive_frontier_count") or 0)
    frontier = plan.get("recursive_frontier")
    return len(frontier) if isinstance(frontier, list) else 0


def initialize_report(args: argparse.Namespace) -> dict[str, Any]:
    """Load native inputs once, in CLI order, for the ordered file traversal."""
    source_record = load_json(args.source_record)
    plan = load_json(args.recursive_plan)
    frontier_count = args.recursive_frontier_count
    if frontier_count is None:
        frontier_count = recursive_frontier_count(plan)
    return {
        "files": [str(Path(path)) for path in args.lean_file],
        "source_record": source_record,
        "frontier_count": frontier_count,
        "index": 0,
        "artifacts": [],
    }


def analyze_current(state: dict[str, Any]) -> dict[str, Any]:
    return analyze_file(
        lean_file=Path(state["files"][state["index"]]),
        source_record=state["source_record"],
        recursive_frontier_count=state["frontier_count"],
    )


def advance_report(state: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    updated = {
        **state,
        "index": state["index"] + 1,
        "artifacts": [*state["artifacts"], artifact],
    }
    return {"state": updated, "done": updated["index"] == len(updated["files"])}


def aggregate_report(state: dict[str, Any]) -> dict[str, Any]:
    files = state["files"]
    artifacts = state["artifacts"]
    frontier_count = state["frontier_count"]
    status_order = {
        COMPLETE_STATUS: 0,
        "derivation_partial": 1,
        "blocked_target_restating_assumption": 2,
        "missing_lean_text": 3,
    }
    status = max(
        (item["status"] for item in artifacts),
        key=lambda value: status_order.get(value, 1),
        default=COMPLETE_STATUS,
    )
    finding_count = sum(len(item["findings"]) for item in artifacts)
    blocked_obligation_count = sum(
        int(item["blocked_obligation_count"]) for item in artifacts
    )
    return {
        "schema_version": 1,
        "style": "physics_lean_derivation_completeness_report",
        "ok": status == COMPLETE_STATUS,
        "status": status,
        "summary": {
            "file_count": len(files),
            "finding_count": finding_count,
            "blocked_obligation_count": blocked_obligation_count,
            "recursive_frontier_count": frontier_count,
            "complete_file_count": sum(1 for item in artifacts if item["complete"]),
        },
        "artifacts": artifacts,
        "acceptance_policy": {
            "complete_status": COMPLETE_STATUS,
            "open_recursive_frontier_blocks_completion": True,
            "target_restating_witness_blocks_completion": True,
            "compiled_surface_is_not_complete": True,
            "allowed_physical_law_witness_roles": [
                "source_law",
                "constitutive_assumption",
                "domain_assumption",
                "bridge_lemma",
                "generated_support",
            ],
            "forbidden_witness_role_for_complete_status": "target_conclusion",
        },
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    state = initialize_report(args)
    for _ in state["files"]:
        state = advance_report(state, analyze_current(state))["state"]
    return aggregate_report(state)


def self_test(directory: Path | None = None) -> dict[str, Any]:
    bad = """
import Mathlib
structure PhysicalLawWitness (P : Prop) : Type where holds : P
theorem physicalLawHolds {P : Prop} (law : PhysicalLawWitness P) : P := law.holds
theorem target (x y : Nat) (h : PhysicalLawWitness (x = y)) : x = y := by
  exact physicalLawHolds h
"""
    good = """
import Mathlib
theorem target (x y : Nat) (h : x = y) : y = x := by
  exact h.symm
"""
    tmp = (
        directory
        if directory is not None
        else REPO_ROOT
        / "artifacts"
        / "physics_lean"
        / "derivation_completeness_self_test"
    )
    tmp.mkdir(parents=True, exist_ok=True)
    bad_path = tmp / "bad.lean"
    good_path = tmp / "good.lean"
    bad_path.write_text(bad, encoding="utf-8")
    good_path.write_text(good, encoding="utf-8")
    bad_report = analyze_file(
        lean_file=bad_path, source_record={}, recursive_frontier_count=0
    )
    good_report = analyze_file(
        lean_file=good_path, source_record={}, recursive_frontier_count=0
    )
    checks = [
        bad_report["status"] == "blocked_target_restating_assumption",
        any(
            item["code"] == "target_restatement_wrapped_in_witness"
            for item in bad_report["findings"]
        ),
        good_report["status"] == COMPLETE_STATUS,
    ]
    return {
        "schema_version": 1,
        "style": "physics_lean_derivation_completeness_self_test",
        "ok": all(checks),
        "checks": checks,
        "bad_status": bad_report["status"],
        "good_status": good_report["status"],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lean-file", action="append", default=[], help="Lean file to analyze."
    )
    parser.add_argument(
        "--source-record", type=Path, help="Source record JSON for the Lean file."
    )
    parser.add_argument(
        "--recursive-plan", type=Path, help="Recursive grounding plan JSON."
    )
    parser.add_argument(
        "--recursive-frontier-count",
        type=int,
        help="Known open recursive frontier count.",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expect-complete", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        report = self_test()
    else:
        if not args.lean_file:
            raise SystemExit("--lean-file is required unless --self-test is used")
        report = build_report(args)
    return emit_report(args, report)


def emit_report(args: argparse.Namespace, report: dict[str, Any]) -> int:
    """Preserve native output ordering, formatting, writes and exit semantics."""
    if args.output:
        write_json(args.output, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status={report.get('status')} ok={report.get('ok')}")
    return 1 if args.expect_complete and not report.get("ok") else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
