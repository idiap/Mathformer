#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Recover the concrete physics objects hidden behind drift-pathology findings.
#
# Intent:
#   Make pathology repair library-first by producing an explicit object queue
#   before target theorem refinement.
#
# Function:
#   Reads monitor/source/Lean evidence and emits object candidates with required
#   MathformerPhysicsLib surfaces and blocked-until gates.
#
# Maintenance Notes:
#   Keep object classes aligned with the pathology repair orchestrator and
#   MathformerPhysicsLib object workbench.

"""Detect physics mathematical objects behind Lean drift pathologies."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

OBJECT_SURFACES = {
    "quantum_state": {
        "mathlib": ["InnerProductSpace", "NormedAddCommGroup", "Module"],
        "library": ["state carrier", "ket-to-wavefunction bridge"],
        "repair_surface": "quantity_typing",
    },
    "quantum_operator": {
        "mathlib": ["LinearMap", "ContinuousLinearMap", "Matrix"],
        "library": ["operator carrier", "adjoint or composition support"],
        "repair_surface": "quantity_typing",
    },
    "unbounded_position_momentum": {
        "mathlib": ["Submodule", "LinearMap", "Dense", "IsClosed", "InnerProductSpace"],
        "library": [
            "domain-bearing unbounded operator",
            "dense common invariant core",
            "position/momentum canonical commutator",
        ],
        "repair_surface": "support_dependency",
    },
    "schwartz_l2_position_momentum_model": {
        "mathlib": [
            "SchwartzMap",
            "SchwartzMap.derivCLM",
            "InnerProductSpace",
            "CompleteSpace",
        ],
        "library": [
            "Mathlib Schwartz wavefunction anchor",
            "Schwartz derivative operator",
            "Schwartz/L2 position-momentum realization",
            "conversion to unbounded PositionMomentumPair",
        ],
        "repair_surface": "support_dependency",
    },
    "real_line_l2_position_momentum_instantiation": {
        "mathlib": ["MeasureTheory.Lp", "SchwartzMap.toLpCLM", "volume", "DenseRange"],
        "library": [
            "real-line L2 Hilbert carrier",
            "Schwartz-to-L2 continuous map",
            "almost-everywhere embedding agreement",
            "dense Schwartz core obligation",
        ],
        "repair_surface": "support_dependency",
    },
    "commutator": {
        "mathlib": ["NonUnitalNonAssocRing", "Algebra", "Matrix"],
        "library": ["commutator definition", "noncommutative expansion lemma"],
        "repair_surface": "law_grounding",
    },
    "hilbert_space_inner_product": {
        "mathlib": ["InnerProductSpace"],
        "library": ["inner-product norm bridge", "Cauchy-Schwarz support"],
        "repair_surface": "support_dependency",
    },
    "vector_field": {
        "mathlib": ["EuclideanSpace", "Fin n -> Real", "Module"],
        "library": ["vector field carrier", "component projection bridge"],
        "repair_surface": "projection_bridge",
    },
    "coordinate_frame": {
        "mathlib": ["Basis", "EuclideanSpace"],
        "library": ["frame context", "basis projection lemma"],
        "repair_surface": "frame_regime",
    },
    "basis_projection": {
        "mathlib": ["Basis", "inner", "Pi"],
        "library": ["projection bridge", "orthonormal-basis support"],
        "repair_surface": "projection_bridge",
    },
    "gradient_divergence_curl": {
        "mathlib": ["fderiv", "HasFDerivAt", "ContinuousLinearMap"],
        "library": ["calculus operator surface", "coordinate derivative bridge"],
        "repair_surface": "support_dependency",
    },
    "integral_or_limit": {
        "mathlib": ["intervalIntegral", "Measure", "Tendsto"],
        "library": ["integral-to-limit support", "boundary condition bridge"],
        "repair_surface": "support_dependency",
    },
    "dimensioned_quantity": {
        "mathlib": ["Real", "Module"],
        "library": ["dimension marker", "quantity wrapper or blocker"],
        "repair_surface": "unit_dimension_obligation",
    },
    "unit_bridge": {
        "mathlib": ["Real"],
        "library": ["unit homogeneity lemma", "dimension bridge"],
        "repair_surface": "unit_dimension_obligation",
    },
    "physical_law": {
        "mathlib": ["Prop"],
        "library": ["named source law surface", "law-to-equation support lemma"],
        "repair_surface": "law_grounding",
    },
    "boundary_or_regime_assumption": {
        "mathlib": ["Prop", "Filter", "Set"],
        "library": ["assumption label", "boundary or regime context"],
        "repair_surface": "contextual_assumption",
    },
}

RERUN_GATES = [
    "repair.mathformerphysicslib_object_workbench",
    "mathformerlib.registry",
    "mathformerlib.promotion_gate",
    "physics.lean.type_system.build",
    "critique.physics_lean_drift_pathology_monitor",
]


def read_text(path: Path | None, inline: str | None) -> str:
    """Load text from a path or inline string."""
    if inline is not None:
        return inline
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


def load_json(path: Path | None) -> dict[str, Any]:
    """Load optional JSON."""
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def has_any(text: str, patterns: Iterable[str]) -> bool:
    """Return true if any literal cue is present."""
    lower = text.lower()
    return any(pattern.lower() in lower for pattern in patterns)


def add_object(
    objects: dict[str, dict[str, Any]],
    *,
    object_class: str,
    confidence: float,
    source_cues: Sequence[str],
    lean_cues: Sequence[str],
    pathology_categories: Sequence[str],
    reason: str,
) -> None:
    """Add or merge one object candidate."""
    surface = OBJECT_SURFACES[object_class]
    existing = objects.get(object_class)
    if existing is None:
        objects[object_class] = {
            "object_class": object_class,
            "confidence": confidence,
            "source_cues": list(source_cues),
            "lean_cues": list(lean_cues),
            "pathology_categories": list(pathology_categories),
            "reason": reason,
            "required_mathlib_surfaces": surface["mathlib"],
            "required_mathformerphysicslib_surfaces": surface["library"],
            "repair_surface": surface["repair_surface"],
            "blocked_until": RERUN_GATES,
        }
        return
    existing["confidence"] = max(float(existing["confidence"]), confidence)
    existing["source_cues"] = sorted(set(existing["source_cues"]) | set(source_cues))
    existing["lean_cues"] = sorted(set(existing["lean_cues"]) | set(lean_cues))
    existing["pathology_categories"] = sorted(
        set(existing["pathology_categories"]) | set(pathology_categories)
    )


def detection_seed(
    source_text: str, lean_text: str, monitor_report: dict[str, Any]
) -> str:
    """Build a stable identifier seed for the object packet."""
    payload = json.dumps(
        {
            "source": source_text[:2000],
            "lean": lean_text[:2000],
            "findings": monitor_report.get("findings", []),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def initialize_state(*, source_text: str, lean_text: str, monitor_report: dict) -> dict:
    """Extract monitor evidence and initialize the finite candidate catalogue."""
    findings = monitor_report.get("findings", [])
    source_features = monitor_report.get("source_features", {})
    lean_features = monitor_report.get("lean_features", {})
    objects: dict[str, dict[str, Any]] = {}
    source_text.lower()  # Preserve native validation of the text input.

    categories = [
        str(item.get("category")) for item in findings if isinstance(item, dict)
    ]
    finding_codes = {
        str(item.get("code")) for item in findings if isinstance(item, dict)
    }

    return {
        "source_text": source_text,
        "lean_text": lean_text,
        "monitor_report": monitor_report,
        "findings": findings,
        "categories": categories,
        "finding_codes": sorted(finding_codes),
        "source_features": source_features,
        "lean_features": lean_features,
        "objects": objects,
    }


def accumulate_detections(state: dict) -> dict:
    """Apply all independent native branches, merging repeated object classes."""
    source_text = state["source_text"]
    monitor_report = state["monitor_report"]
    categories = state["categories"]
    finding_codes = state["finding_codes"]
    source_features = state["source_features"]
    lean_features = state["lean_features"]
    objects = state["objects"]
    if source_features.get("quantum_dense_notation") or has_any(
        source_text, ["ket", "bra", "psi", "\\psi", "hilbert"]
    ):
        add_object(
            objects,
            object_class="quantum_state",
            confidence=0.82,
            source_cues=["quantum_dense_notation"],
            lean_cues=(
                ["missing_hilbert_or_operator_surface"]
                if not lean_features.get("has_hilbert_or_inner_product")
                else ["hilbert_surface_present"]
            ),
            pathology_categories=categories or ["notational_collapse"],
            reason="Quantum state notation needs a Hilbert/module surface before target theorem repair.",
        )
        add_object(
            objects,
            object_class="hilbert_space_inner_product",
            confidence=0.7,
            source_cues=["hilbert_or_inner_product_context"],
            lean_cues=["inner_product_surface_check"],
            pathology_categories=categories or ["notational_collapse"],
            reason="Quantum state claims often require inner-product and norm support lemmas.",
        )
    if source_features.get("operator_algebra") or has_any(
        source_text, ["operator", "commutator", "unitary", "hamiltonian", "dagger"]
    ):
        add_object(
            objects,
            object_class="quantum_operator",
            confidence=0.86,
            source_cues=["operator_algebra"],
            lean_cues=(
                ["missing_operator_surface"]
                if not lean_features.get("has_operator_surface")
                else ["operator_surface_present"]
            ),
            pathology_categories=categories or ["notational_collapse"],
            reason="Operator algebra cannot be repaired by raw scalar multiplication alone.",
        )
    if has_any(
        source_text,
        [
            "unbounded operator",
            "position operator",
            "momentum operator",
            "position and momentum",
            "dense domain",
            "common domain",
            "common invariant core",
            "canonical commutator",
        ],
    ):
        add_object(
            objects,
            object_class="unbounded_position_momentum",
            confidence=0.93,
            source_cues=["unbounded_position_momentum_domain"],
            lean_cues=["domain_core_support_needed"],
            pathology_categories=categories
            or ["abstraction_elevation", "implicit_premise_selection"],
            reason=(
                "Position and momentum operators require explicit unbounded domains, a dense common "
                "invariant core, and a canonical commutator surface before theorem repair."
            ),
        )
    if has_any(
        source_text,
        [
            "l2(r)",
            "l²(r)",
            "l2 real line",
            "l² real line",
            "lebesgue l2",
            "real-line l2",
            "real line l2",
            "schwartz to l2",
            "schwartz-to-l2",
        ],
    ):
        add_object(
            objects,
            object_class="real_line_l2_position_momentum_instantiation",
            confidence=0.95,
            source_cues=["real_line_l2_position_momentum_instantiation"],
            lean_cues=["mathlib_l2_instantiation_needed"],
            pathology_categories=categories
            or ["abstraction_elevation", "implicit_premise_selection"],
            reason=(
                "A real-line particle model should route through Mathlib's Lp carrier, the "
                "Schwartz-to-L2 embedding, and explicit dense-core/action obligations."
            ),
        )
    if has_any(
        source_text,
        [
            "schwartz",
            "schwartz space",
            "l2",
            "l^2",
            "square integrable wavefunction",
            "real line wavefunction",
            "position-momentum model",
        ],
    ):
        add_object(
            objects,
            object_class="schwartz_l2_position_momentum_model",
            confidence=0.94,
            source_cues=["schwartz_l2_position_momentum_model"],
            lean_cues=["concrete_model_support_needed"],
            pathology_categories=categories
            or ["abstraction_elevation", "implicit_premise_selection"],
            reason=(
                "Concrete position/momentum autoformalization needs a Mathlib Schwartz-function "
                "anchor, Hilbert embedding obligations, and a conversion into the unbounded pair."
            ),
        )
    if has_any(source_text, ["commutator", "[q, p]", "[x, p]", "[x,p]"]):
        add_object(
            objects,
            object_class="commutator",
            confidence=0.9,
            source_cues=["commutator"],
            lean_cues=["law_or_operator_support_needed"],
            pathology_categories=categories or ["notational_collapse"],
            reason="Commutator semantics require a noncommutative support definition or lemma.",
        )
    if source_features.get("vector_or_field") or has_any(
        source_text, ["vector", "field", "gradient", "divergence", "curl", "\\vec"]
    ):
        add_object(
            objects,
            object_class="vector_field",
            confidence=0.84,
            source_cues=["vector_or_field"],
            lean_cues=(
                ["missing_vector_or_field_surface"]
                if not lean_features.get("has_vector_or_field")
                else ["vector_surface_present"]
            ),
            pathology_categories=categories
            or ["notational_collapse", "abstraction_elevation"],
            reason="Vector or field claims need a carrier and projection bridge before scalar core reuse.",
        )
    if has_any(
        source_text, ["coordinate", "basis", "spherical", "\\hat", "frame", "inertial"]
    ):
        add_object(
            objects,
            object_class="coordinate_frame",
            confidence=0.8,
            source_cues=["coordinate_or_frame"],
            lean_cues=["frame_context_check"],
            pathology_categories=categories or ["notational_collapse"],
            reason="Coordinate-frame information must be explicit before repairing a vector calculus theorem.",
        )
        add_object(
            objects,
            object_class="basis_projection",
            confidence=0.76,
            source_cues=["basis_or_projection"],
            lean_cues=["projection_bridge_check"],
            pathology_categories=categories or ["notational_collapse"],
            reason="Scalar projections must be tied back to the source vector or basis claim.",
        )
    if has_any(source_text, ["gradient", "divergence", "curl", "laplacian", "\\nabla"]):
        add_object(
            objects,
            object_class="gradient_divergence_curl",
            confidence=0.86,
            source_cues=["vector_calculus"],
            lean_cues=(
                ["missing_calculus_surface"]
                if not lean_features.get("has_calculus_surface")
                else ["calculus_surface_present"]
            ),
            pathology_categories=categories or ["abstraction_elevation"],
            reason="Vector calculus content needs a support declaration rather than a target-shaped hypothesis.",
        )
    if source_features.get("calculus_or_integral") or has_any(
        source_text, ["integral", "\\int", "limit", "at infinity", "tends to"]
    ):
        add_object(
            objects,
            object_class="integral_or_limit",
            confidence=0.82,
            source_cues=["calculus_or_integral"],
            lean_cues=(
                ["missing_calculus_surface"]
                if not lean_features.get("has_calculus_surface")
                else ["calculus_surface_present"]
            ),
            pathology_categories=categories or ["abstraction_elevation"],
            reason="Integral, derivative, or limit content should be modeled as a reusable support lemma.",
        )
    if source_features.get("physical_law") or has_any(
        source_text, ["maxwell", "gauss", "poisson", "newton", "conservation", "law"]
    ):
        add_object(
            objects,
            object_class="physical_law",
            confidence=0.84,
            source_cues=["physical_law"],
            lean_cues=(
                ["missing_source_law_surface"]
                if not lean_features.get("has_source_law_surface")
                else ["law_surface_present"]
            ),
            pathology_categories=categories or ["abstraction_elevation"],
            reason="Named laws must be represented as source-backed support, not absorbed into target hypotheses.",
        )
    if (
        source_features.get("implicit_premise_needs")
        or "implicit_premises_unlabeled" in finding_codes
    ):
        add_object(
            objects,
            object_class="boundary_or_regime_assumption",
            confidence=0.78,
            source_cues=["implicit_premise_needs"],
            lean_cues=(
                ["side_conditions"]
                if lean_features.get("has_side_conditions")
                else ["side_condition_check"]
            ),
            pathology_categories=categories or ["implicit_premise_selection"],
            reason="Implicit side conditions need explicit support labels before theorem repair.",
        )
    if has_any(
        source_text,
        ["unit", "dimension", "mass", "charge", "energy", "force", "momentum"],
    ) or "raw_scalar_erasure" in json.dumps(monitor_report):
        add_object(
            objects,
            object_class="dimensioned_quantity",
            confidence=0.76,
            source_cues=["dimensioned_physical_quantity"],
            lean_cues=(
                ["raw_scalar_count"] if lean_features.get("raw_scalar_count", 0) else []
            ),
            pathology_categories=categories or ["notational_collapse"],
            reason="Dimensioned quantities need an explicit unit or dimension bridge.",
        )
        add_object(
            objects,
            object_class="unit_bridge",
            confidence=0.7,
            source_cues=["unit_dimension_obligation"],
            lean_cues=["unit_report_check"],
            pathology_categories=categories or ["notational_collapse"],
            reason="Unit homogeneity should be local support evidence rather than a global assumption.",
        )

    return state


def finalize_packet(state: dict) -> dict:
    """Sort candidates, apply the fallback, and package source evidence."""
    source_text = state["source_text"]
    lean_text = state["lean_text"]
    monitor_report = state["monitor_report"]
    findings = state["findings"]
    categories = state["categories"]
    source_features = state["source_features"]
    lean_features = state["lean_features"]
    objects = state["objects"]
    object_list = sorted(
        objects.values(),
        key=lambda item: (-float(item["confidence"]), item["object_class"]),
    )
    if not object_list and findings:
        add_object(
            objects,
            object_class="physical_law",
            confidence=0.5,
            source_cues=["fallback_pathology_finding"],
            lean_cues=["unknown"],
            pathology_categories=categories,
            reason="Fallback object for a drift finding with insufficient source cues.",
        )
        object_list = list(objects.values())

    packet_id = f"physics_object_packet_{detection_seed(source_text, lean_text, monitor_report)}"
    return {
        "style": "physics_math_object_detection_packet",
        "packet_id": packet_id,
        "status": "ready" if object_list else "no_objects_detected",
        "object_count": len(object_list),
        "objects": object_list,
        "source_feature_summary": source_features,
        "lean_feature_summary": lean_features,
        "pathology_categories": sorted(set(categories)),
        "library_first_policy": {
            "target": "MathformerPhysicsLib",
            "rule": "work over detected physics objects before target theorem edits",
            "blocked_target_repair_until": [
                "object searched in Mathlib and MathformerPhysicsLib",
                "support declaration planned, reused, promoted, or explicitly blocked",
                "projection, law, unit, or assumption bridge named for target repair",
            ],
        },
    }


def build_packet(
    *, source_text: str, lean_text: str, monitor_report: dict[str, Any]
) -> dict[str, Any]:
    """Build a physics-object detection packet using the shared source steps."""
    return finalize_packet(
        accumulate_detections(
            initialize_state(
                source_text=source_text,
                lean_text=lean_text,
                monitor_report=monitor_report,
            )
        )
    )


def parse_args(
    argv: Sequence[str] | None = None, *, prog: str | None = None
) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__, prog=prog)
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-text")
    parser.add_argument("--lean-file", type=Path)
    parser.add_argument("--lean-text")
    parser.add_argument("--monitor-report", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def fixed_fixture() -> dict:
    """The exact native --self-test evidence, independent of input paths."""
    return {
        "source_text": "Show that the commutator [q, p] = i for quantum operators on a Hilbert space.",
        "lean_text": "theorem bad (q p : Real) : q * p = p * q := by ring",
        "monitor_report": {
            "source_features": {
                "quantum_dense_notation": True,
                "operator_algebra": True,
            },
            "lean_features": {
                "has_hilbert_or_inner_product": False,
                "has_operator_surface": False,
            },
            "findings": [
                {
                    "category": "notational_collapse",
                    "code": "quantum_notation_collapsed",
                }
            ],
        },
    }


def resolve_path(path, working_directory=None):
    return (
        Path(working_directory) / path if working_directory is not None else Path(path)
    )


def load_inputs(options: dict, *, working_directory=None) -> dict:
    """Load source, Lean, then monitor evidence in native order."""

    def path(name):
        value = options[name]
        return resolve_path(value, working_directory) if value is not None else None

    return {
        "source_text": read_text(path("source_file"), options["source_text"]),
        "lean_text": read_text(path("lean_file"), options["lean_text"]),
        "monitor_report": load_json(path("monitor_report")),
    }


def check_and_emit(
    options: dict, packet: dict, *, working_directory=None, before_write=None
) -> int:
    """Check the native fixture, serialize, and write or print the packet."""
    if options["self_test"]:
        assert packet["status"] == "ready"
        classes = {item["object_class"] for item in packet["objects"]}
        assert "quantum_operator" in classes
        assert "commutator" in classes
    output = json.dumps(packet, ensure_ascii=False, indent=2)
    if options["output"]:
        path = resolve_path(options["output"], working_directory)
        if before_write is not None:
            before_write(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run object detection through the same steps exposed over MCP."""
    options = vars(parse_args(argv))
    data = fixed_fixture() if options["self_test"] else load_inputs(options)
    packet = build_packet(**data)
    return check_and_emit(options, packet)


if __name__ == "__main__":
    raise SystemExit(main())
