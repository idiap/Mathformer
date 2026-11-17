# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Disposable native input files; there are no provider/compiler calls to replace.

Lean text is scanned, never compiled. The server uses the production registry
and source functions with explicit repository context and restricted write roots.
"""

from pathlib import Path
import sys


def fixture(root, mode="blocked"):
    lean = root / "MathformerPhysicsLib/Lean"
    lean.mkdir(parents=True, exist_ok=True)
    (lean / "formalphysics_vector.lean").write_text(
        "import Mathlib\ndef vector : Nat := 1\n"
    )
    if mode == "blocked":
        (lean / "Other.lean").write_text("import Mathlib\ndef vector : Nat := 2\n")
    else:
        (lean / "Foundations.lean").write_text("")
        if mode == "accepted":
            (lean.parent / "MANIFEST.json").write_text(
                '{"backends":{"Lean":{"foundations":{}}}}'
            )
    return lean


def deny_external(event, args):
    if event in {
        "subprocess.Popen",
        "os.system",
        "socket.connect",
        "socket.getaddrinfo",
    }:
        raise AssertionError(
            "This reporting workflow must not invoke external boundaries: " + event
        )


def serve(directory):
    import mcp_server
    from coherence_loop_tools import source

    root = Path(directory).resolve()
    native = source()
    native.REPO_ROOT = root
    import coherence_common as common

    common.REPO_ROOT = root
    common.LIB_ROOT = root / "MathformerPhysicsLib"
    common.LEAN_ROOT = common.LIB_ROOT / "Lean"
    common.FOUNDATIONS_INDEX = common.LEAN_ROOT / "Foundations.lean"
    mcp_server._ALLOWED_WRITE_ROOTS = [root]
    mcp_server.CALL_LOG_PATH = root / "service-calls.jsonl"
    # Install after imports: forbid accidental model, compiler or prover calls
    # during every actual registered source step, without replacing those steps.
    sys.addaudithook(deny_external)
    mcp_server.mcp.run(transport="stdio")
