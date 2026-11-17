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

"""Build a generative critic plan for Lean physics artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

CRITIC_PANEL = [
    "physics-lean-physical-semantics-critic",
    "physics-lean-assumption-critic",
    "physics-lean-dimension-critic",
    "physics-lean-drift-pathology-monitor",
    "lean-semantic-preservation-critic",
    "lean-logical-soundness-critic",
    "lean-mathlib-alignment-critic",
    "autoformalization-result-realness-verifier",
    "lean-nonvacuity-consistency-checker",
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


def build_plan(*, source_text: str, lean_text: str, high_risk: bool) -> dict[str, Any]:
    """Document the responsibility of ``build_plan``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    source_preview = " ".join(source_text.split())[:500]
    lean_preview = " ".join(lean_text.split())[:500]
    probe_prompts = [
        {
            "id": "physical_semantics_adversary",
            "critic": "physics-lean-physical-semantics-critic",
            "prompt": (
                "Compare the source physics and Lean artifact. Generate one concrete way the Lean theorem "
                "could be true while the source derivation is false because quantities, vectors, frames, "
                "regimes, or laws were erased. Return verdict, evidence, blocker_class, and regression_risk."
            ),
        },
        {
            "id": "assumption_stress",
            "critic": "physics-lean-assumption-critic",
            "prompt": (
                "List each Lean side condition and classify it as source-backed, mathlib-backed, "
                "generated-support, or blocked. Identify any hidden strengthening and cite the missing source "
                "anchor."
            ),
        },
        {
            "id": "dimension_stress",
            "critic": "physics-lean-dimension-critic",
            "prompt": (
                "Generate a unit or dimension stress test for the Lean theorem. Identify raw-scalar erasure, "
                "missing projection lemmas, or a vector/scalar mismatch."
            ),
        },
        {
            "id": "empty_formalism_adversary",
            "critic": "lean-logical-soundness-critic",
            "prompt": (
                "Try to reduce the Lean artifact to a vacuous theorem, target-as-assumption, or theorem over "
                "uninterpreted constants. Report whether the artifact proves actual physics."
            ),
        },
        {
            "id": "formalscience_drift_taxonomy_probe",
            "critic": "physics-lean-drift-pathology-monitor",
            "prompt": (
                "Classify possible FormalScience/FormalPhysics drift pathologies in the Lean artifact: "
                "notational collapse, abstraction elevation, proof strategy substitution, and implicit premise "
                "selection. For each suspected category, give source cues, Lean cues, and whether it blocks "
                "complete status."
            ),
        },
    ]
    return {
        "style": "physics_lean_generative_critic_plan",
        "codex_exec_enabled": True,
        "high_risk": high_risk,
        "critic_panel": CRITIC_PANEL,
        "source_preview": source_preview,
        "lean_preview": lean_preview,
        "probe_prompts": probe_prompts,
        "recommended_command": (
            "python skills/control/skill-test-program-orchestrator/scripts/run_content_skill_codex_exec_tests.py "
            "--execute --skill physics-lean-generative-critic-orchestrator --json"
        ),
        "acceptance_policy": {
            "deterministic_first": True,
            "generative_findings_require_evidence": True,
            "repeat_independent_blockers_before_process_change": True,
            "protected_dimensions": [
                "source_fidelity",
                "quantity_typing",
                "unit_dimension_discipline",
                "contextual_assumptions",
                "non_vacuity",
                "lean_execution",
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
    parser.add_argument("--lean-file", type=Path)
    parser.add_argument("--lean-text")
    parser.add_argument("--high-risk", action="store_true")
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
        plan = build_plan(
            source_text="A force vector equals mass times acceleration in an inertial frame.",
            lean_text="theorem bad (F m a : Real) : F = m * a := by sorry",
            high_risk=True,
        )
        assert plan["codex_exec_enabled"] is True
        assert len(plan["probe_prompts"]) >= 4
    else:
        plan = build_plan(
            source_text=read_text(args.source_file, args.source_text),
            lean_text=read_text(args.lean_file, args.lean_text),
            high_risk=args.high_risk,
        )
    output = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
