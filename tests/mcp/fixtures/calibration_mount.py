# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Scratch repository containing native analyzers and finite source inputs."""

from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
SUITES = [
    "tests/physics_lean/run_derivation_completeness_regression.py",
    "tests/physics_lean/run_formal_science_grounding_debt_gate.py",
    "tests/physics_lean/run_redefinition_critic_calibration.py",
    "tests/physics_sympy/run_unit_semantics_contract.py",
]


def mount(root):
    files = SUITES + [
        "skills/physics-lean/physics-lean-derivation-completeness-checker/scripts/check_derivation_completeness.py",
        "skills/physics-lean/physics-lean-drift-pathology-monitor/scripts/monitor_physics_lean_drift_pathologies.py",
        "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts/coherence_common.py",
        "libraries/MathformerPhysicsLib/unit_semantics.py",
        "libraries/MathformerPhysicsLib/release_status.py",
    ]
    for name in files:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    fixture = "tests/fixtures/physics_lean_adversarial"
    shutil.copytree(ROOT / fixture, root / fixture)
    for case in ["0014", "0015", "0021", "0052", "0074", "0191", "0059"]:
        name = f"libraries/MathformerPhysicsLib/Lean/formalphysics_{case}/MathformerPhysics.lean"
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
        if case in ["0191", "0059"]:
            alias = (
                root
                / f"MathformerPhysicsLib/Lean/formalphysics_{case}/MathformerPhysics.lean"
            )
            alias.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(target, alias)
        record = (
            root
            / f"artifacts/physics_lean/dirac_recursive_batch/formalphysics_{case}/source_record.json"
        )
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(
            json.dumps(
                {
                    "case_id": f"formalphysics_{case}",
                    "concepts": ["heisenberg"] if case == "0014" else [],
                }
            )
        )


def configure(native, root):
    native.REPO_ROOT = root
    native.DEFAULT_OUTPUT = root / "artifacts/physics_lean/calibration/dashboard.json"
    native.VENV_PYTHON = root / ".venv/bin/python"
