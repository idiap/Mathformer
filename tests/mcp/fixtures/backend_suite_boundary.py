# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated native Python CLI execution; only the external Lean compiler is faked.

No report-producing script is replaced. Every child CLI is loaded from its real
source and executed against copied inputs in a temporary repository. Unexpected
external commands fail closed. Generative scripts build native advisory plans;
they never invoke a provider.
"""

from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]


def load(path, name="backend_fixture_child"):
    from importlib.machinery import SourceFileLoader

    spec = importlib.util.spec_from_loader(name, SourceFileLoader(name, str(path)))
    module = importlib.util.module_from_spec(spec)
    if path.suffix == ".txt":
        module.__file__ = str(
            ROOT / "tests/physics_lean/run_lean_physics_backend_suite.py"
        )
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def stage(directory, mode="success"):
    directory = Path(directory)

    def write(path, value):
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value))

    shutil.copytree(
        ROOT / "tests/fixtures/physics_lean_adversarial",
        directory / "tests/fixtures/physics_lean_adversarial",
        dirs_exist_ok=True,
    )
    # Source-owned sample text is test input, never compiled by an external process.
    thorough = load(ROOT / "tests/physics_lean/run_grounded_sample_thoroughness.py")
    for case in thorough.CASE_SPECS:
        src = (
            ROOT / f"libraries/MathformerPhysicsLib/Lean/{case}/MathformerPhysics.lean"
        )
        for base in ("libraries/MathformerPhysicsLib", "MathformerPhysicsLib"):
            target = directory / f"{base}/Lean/{case}/MathformerPhysics.lean"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(src.read_bytes())
        write(
            f"artifacts/physics_lean/dirac_recursive_batch/{case}/source_record.json",
            {
                "case_id": case,
                "concepts": ["Heisenberg"] if case == "formalphysics_0014" else [],
            },
        )
    write(
        "libraries/MathformerPhysicsLib/Lean/formalphysics_0000/consistency_report.json",
        {"status": "fixture_stored"},
    )
    target = (
        directory
        / "data/benchmarks/formal_science/physics_top10_sources/01_formalphysics_0000.tex"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "The Lorentz force on a charged particle is a vector in a coordinate frame. "
        "The electric and magnetic fields obey the Euler Lagrange equation."
    )
    reports = "artifacts/physics_lean/from_scratch_lean/formalphysics_0000/"
    write(
        reports + "type_system_packet.json",
        {"features": {"vectors": True}, "lean_surfaces": ["EuclideanSpace"]},
    )
    write(reports + "assumption_packet.json", {"assumptions": []})
    for name in (
        "unit_report",
        "physical_semantics_critic",
        "assumption_critic",
        "dimension_critic",
    ):
        write(reports + name + ".json", {"status": "pass", "findings": []})
    if mode == "boolean_failure":
        # Real critics see a protected vector/unit surface and fail the expected
        # raw-scalar-erasure subset check. All remaining cases must still run.
        (
            directory
            / "tests/fixtures/physics_lean_adversarial/raw_scalar_erasure.lean"
        ).write_text(
            "import Mathlib\n-- EuclideanSpace Real (Fin 3) UnitDimensionCompatible\n"
            "theorem fixture : True := by trivial\n"
        )
    if mode == "bad_json":
        (
            directory
            / "libraries/MathformerPhysicsLib/Lean/formalphysics_0000/consistency_report.json"
        ).write_text("{")
    if mode == "child_failure":
        (
            directory
            / "tests/fixtures/physics_lean_adversarial/raw_scalar_erasure.source.txt"
        ).unlink()
    if mode == "thoroughness_failure":
        (
            directory
            / "MathformerPhysicsLib/Lean/formalphysics_0000/MathformerPhysics.lean"
        ).write_text("")
    if mode == "regression_failure":
        (
            directory
            / "libraries/MathformerPhysicsLib/Lean/formalphysics_0014/MathformerPhysics.lean"
        ).write_text("")


def install(module, directory, mode="success"):
    directory = Path(directory)
    ledger = []

    def relocate(value):
        if (
            isinstance(value, Path)
            and value.is_absolute()
            and value.is_relative_to(ROOT)
        ):
            return directory / value.relative_to(ROOT)
        if isinstance(value, list):
            return [relocate(v) for v in value]
        return value

    def configure(native):
        for key, value in list(vars(native).items()):
            if isinstance(value, (Path, list)):
                setattr(native, key, relocate(value))
        # Explicit repository-root defaults were added to some native CLIs.
        # Relocate their bound defaults as well as module constants so the
        # exact entrypoint never reads or writes the production checkout.
        for value in vars(native).values():
            if inspect.isfunction(value) and value.__module__ == getattr(
                native, "__name__", None
            ):
                if value.__defaults__:
                    value.__defaults__ = tuple(relocate(v) for v in value.__defaults__)
                if value.__kwdefaults__:
                    value.__kwdefaults__ = {
                        k: relocate(v) for k, v in value.__kwdefaults__.items()
                    }
        if hasattr(native, "subprocess"):
            native.subprocess = SimpleNamespace(
                run=run,
                PIPE=subprocess.PIPE,
                TimeoutExpired=subprocess.TimeoutExpired,
                CompletedProcess=subprocess.CompletedProcess,
            )

    def run(argv, **kwargs):
        assert Path(kwargs["cwd"]) == directory
        assert kwargs.get("text") is True
        ledger.append(list(argv))
        if argv[:3] == ["lake", "env", "lean"]:
            assert len(argv) == 4
            assert (directory / argv[3]).is_file()
            if mode == "compiler_exception":
                raise OSError("fixture compiler unavailable")
            return subprocess.CompletedProcess(
                argv,
                7 if mode == "compile_failure" else 0,
                "fixture Lean diagnostic",
                "fixture compiler failure" if mode == "compile_failure" else "",
            )
        assert argv[0] == sys.executable, f"Forbidden external process: {argv}"
        path = ROOT / argv[1]
        assert path.is_file() and path.suffix == ".py"
        native = load(path)
        configure(native)
        out, err = io.StringIO(), io.StringIO()
        saved_cwd = Path.cwd()
        try:
            os.chdir(directory)
            with (
                patch.object(sys, "argv", argv[1:]),
                redirect_stdout(out),
                redirect_stderr(err),
            ):
                try:
                    # The scripts use both main() and main(argv); preserve each CLI.
                    code = (
                        native.main(argv[2:])
                        if inspect.signature(native.main).parameters
                        else native.main()
                    )
                except SystemExit as exc:
                    code = exc.code
                except Exception as exc:
                    print(f"{type(exc).__name__}: {exc}", file=err)
                    code = 1
        finally:
            os.chdir(saved_cwd)
        return subprocess.CompletedProcess(
            argv, code or 0, out.getvalue(), err.getvalue()
        )

    configure(module)
    return ledger
