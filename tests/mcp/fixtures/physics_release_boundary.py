# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Only Lake is substituted. Coherence runs its real steps over fixture files."""

from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from coherence_gate_tools import source


def prepare(root, mode):
    public = root / "libraries/MathformerPhysicsLib.lean"
    public.parent.mkdir(parents=True, exist_ok=True)
    public.write_text("import Fixture.A Missing Fixture.A\n-- import Ignored\n")
    (root / "Fixture").mkdir(exist_ok=True)
    (root / "Fixture/A.lean").write_text("def a := 1\n")
    lib = root / "MathformerPhysicsLib"
    lean = lib / "Lean"
    lean.mkdir(parents=True, exist_ok=True)
    if mode != "coherence_high":
        (lean / "Foundations.lean").touch()
    if mode != "coherence_medium":
        (lib / "MANIFEST.json").write_text(
            json.dumps({"backends": {"Lean": {"foundations": {}}}})
        )
    if mode != "no_manifest":
        (root / "lake-manifest.json").write_text('{"fixture":true}')
    # Preserve the actual Python subprocess boundary and argv. This fixture
    # entrypoint loads the real gate and changes only its filesystem inputs.
    script = (
        root
        / "skills/mathformerphysicslib/mathformerphysicslib-coherence-gate/scripts/gate_coherence.py"
    )
    script.parent.mkdir(parents=True, exist_ok=True)
    project = Path(__file__).resolve().parents[3]
    script.write_text(
        "import sys\nfrom pathlib import Path\n"
        + f'sys.path[:0] = {[str(project/"scripts"), str(Path(__file__).resolve().parent)]!r}\n'
        + "from physics_release_boundary import coherence_inputs\n"
        + "from coherence_gate_tools import source\n"
        + f"with coherence_inputs(Path({str(root)!r})):\n"
        + "    raise SystemExit(source().main(sys.argv[1:]))\n"
    )
    return public


def coherence_inputs(root):
    source()
    import coherence_common as common

    stack = ExitStack()
    for key, value in dict(
        REPO_ROOT=root,
        LIB_ROOT=root / "MathformerPhysicsLib",
        LEAN_ROOT=root / "MathformerPhysicsLib/Lean",
        FOUNDATIONS_ROOT=root / "MathformerPhysicsLib/Lean/Foundations",
        FOUNDATIONS_INDEX=root / "MathformerPhysicsLib/Lean/Foundations.lean",
    ).items():
        stack.enter_context(patch.object(common, key, value))
    return stack


def boundaries(native, root, mode, calls):
    stack = ExitStack()
    stack.enter_context(patch.object(native, "REPO_ROOT", root))
    stack.enter_context(
        patch.object(
            native, "PUBLIC_ROOT", root / "libraries/MathformerPhysicsLib.lean"
        )
    )
    real_run = subprocess.run

    def command(argv, **kw):
        index = len(calls) % 3
        assert kw == dict(
            cwd=root, text=True, capture_output=True, timeout=(900, 180, 30)[index]
        ), kw
        expected = (
            ["lake", "build", "MathformerPhysicsLib"],
            [
                sys.executable,
                "skills/mathformerphysicslib/mathformerphysicslib-coherence-gate/scripts/gate_coherence.py",
                "--require-release",
                "--json",
            ],
            ["lake", "env", "lean", "--version"],
        )[index]
        assert argv == expected, argv
        calls.append((argv, kw["timeout"]))
        with (root / "commands.jsonl").open("a") as stream:
            stream.write(json.dumps([argv, kw["timeout"]]) + "\n")
        if index == 1:
            return real_run(argv, **kw)
        name = "build" if index == 0 else "lean"
        if mode == name + "_launch":
            raise OSError("fixture launch failure")
        if mode == name + "_timeout":
            raise subprocess.TimeoutExpired(
                argv, kw["timeout"], output=b"partial\xff", stderr=None
            )
        return subprocess.CompletedProcess(
            argv, 2 if mode == name + "_fail" else 0, name + " checked\n", ""
        )

    stack.enter_context(patch.object(native.subprocess, "run", command))
    return stack
