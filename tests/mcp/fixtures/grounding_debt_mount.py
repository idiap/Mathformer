# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Finite Lean text inputs and the real static monitor, with no Lean compiler."""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
MONITOR = "skills/physics-lean/physics-lean-drift-pathology-monitor/scripts/monitor_physics_lean_drift_pathologies.py"
CASE_TEXT = {
    "0191": "import MathformerPhysicsLib.Lean.Foundations\n"
    "-- InnerProductSpace ℂ H\n-- HilbertBoundedOperator\n"
    "-- TimeDependentSchrodingerProductDifferentiationFrontier\n",
    "0059": "-- VariationChainIntegralFrontier\n-- differentiate_under_integral\n"
    "-- chain_rule_integral_substitution\n-- fixed_endpoints\n",
}


def case(root, case_id):
    return (
        root
        / f"MathformerPhysicsLib/Lean/formalphysics_{case_id}/MathformerPhysics.lean"
    )


def mount(root):
    monitor = root / MONITOR
    monitor.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / MONITOR, monitor)
    for case_id, text in CASE_TEXT.items():
        path = case(root, case_id)
        path.parent.mkdir(parents=True)
        path.write_text(text, encoding="utf-8")
