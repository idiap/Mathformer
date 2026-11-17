# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated source inputs and a forwarding subprocess ledger.

The checker is static Python analysis: there is no provider or external compiler
boundary to fake. Run its unmodified source in the temporary repository. Every
child command is checked before launch so these tests cannot invoke a prover.
"""

import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
RUNNER = "tests/physics_lean/run_derivation_completeness_regression.py"
CHECKER = "skills/physics-lean/physics-lean-derivation-completeness-checker/scripts/check_derivation_completeness.py"
REPORT = "artifacts/physics_lean/derivation_completeness_regression/report.json"
CASES = ("0014", "0015", "0021", "0052", "0074")


def load(path, name):
    spec = importlib.util.spec_from_loader(name, SourceFileLoader(name, str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage(directory, mode="success"):
    directory = Path(directory)
    target = directory / CHECKER
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / CHECKER, target)
    shutil.copytree(
        ROOT / "tests/fixtures/physics_lean_adversarial",
        directory / "tests/fixtures/physics_lean_adversarial",
        dirs_exist_ok=True,
    )
    for suffix in CASES:
        case = "formalphysics_" + suffix
        lean = f"libraries/MathformerPhysicsLib/Lean/{case}/MathformerPhysics.lean"
        target = directory / lean
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / lean, target)
        record = (
            directory
            / f"artifacts/physics_lean/dirac_recursive_batch/{case}/source_record.json"
        )
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(
            json.dumps(
                {
                    "case_id": case,
                    "concepts": ["Heisenberg"] if suffix == "0014" else [],
                }
            )
        )
    if mode == "assertion_failure":
        shutil.copyfile(
            directory
            / "tests/fixtures/physics_lean_adversarial/direct_target_hypothesis.lean",
            directory
            / "tests/fixtures/physics_lean_adversarial/source_law_witness_not_target.lean",
        )
        # Independently fail the final assertion; collection must still finish.
        (
            directory
            / "libraries/MathformerPhysicsLib/Lean/formalphysics_0074/MathformerPhysics.lean"
        ).write_text("import Mathlib\n")
    elif mode == "missing_input":
        (
            directory
            / "tests/fixtures/physics_lean_adversarial/direct_target_hypothesis.lean"
        ).unlink()
    elif mode == "malformed_record":
        (
            directory
            / "artifacts/physics_lean/dirac_recursive_batch/formalphysics_0014/source_record.json"
        ).write_text("{invalid")
    elif mode == "write_failure":
        target = directory / REPORT
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir()


def configure(module, directory):
    directory = Path(directory)
    module.REPO_ROOT = directory
    module.ARTIFACT_ROOT = directory / Path(REPORT).parent
    module.FIXTURE_ROOT = directory / "tests/fixtures/physics_lean_adversarial"
    calls = []
    real_run = subprocess.run

    def forwarding_run(argv, **kwargs):
        assert argv[1] == CHECKER, argv
        assert kwargs == {
            "cwd": directory,
            "text": True,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
        }, kwargs
        assert argv[-1] == "--json", argv
        calls.append(argv[1:])
        return real_run(argv, **kwargs)

    module.subprocess = SimpleNamespace(run=forwarding_run, PIPE=subprocess.PIPE)
    return calls
