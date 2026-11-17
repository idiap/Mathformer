# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic Lean/Git process fixture and finite Lean source corpus.

Only the external version subprocess interface is replaced. These sources are
text fixtures for the real regex indexer, and require no theorem prover.
"""

import json
from pathlib import Path
import subprocess
from types import SimpleNamespace


def version_process(settings, record):
    def run(command, **kwargs):
        record(command, kwargs)
        values = settings()
        if values.get("error") == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        if values.get("error") == "os":
            raise OSError("fixture process unavailable")
        key = "git" if command[0] == "git" else "lean"
        return SimpleNamespace(
            stdout=values.get(key, "") + "\nsecond line ignored\n",
            stderr="",
            returncode=0,
        )

    return SimpleNamespace(
        run=run, PIPE=subprocess.PIPE, TimeoutExpired=subprocess.TimeoutExpired
    )


def lean_tree(root):
    files = {
        "Z.lean": "import Mathlib.Algebra.Base\nlemma convex_last : True := by trivial\n",
        "Algebra/Base/Child.lean": "import Mathlib.Algebra.Base\nlemma child : True := by trivial\n",
        "Algebra/Base.lean": (
            "import Mathlib.Init Mathlib.External\n"
            "/-- A compact fixture document -/\n"
            "theorem compact_first (x : Nat) : x = x := by rfl\n"
            "import Mathlib.IgnoredAfterDeclaration\n"
            "def tail_value : Nat := 2\n"
        ),
        "Dense.lean": "\n".join(
            f"lemma compact_{i:02d} : True := by trivial" for i in range(24)
        )
        + "\n",
    }
    # Deliberately create in unsorted order: parse_mathlib owns sort order.
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (root / "ignored.txt").write_text("lemma never_indexed : True := by trivial")
    # pathlib sorts path components: Base/Child precedes Base.lean.
    return ["Algebra/Base/Child.lean", "Algebra/Base.lean", "Dense.lean", "Z.lean"]


def serve(control, log, write_root, readonly=False):
    import mcp_server
    from mathlib_index_build_tools import source
    import sys

    source()
    common = sys.modules["mathlib_index_common"]

    def record(command, kwargs):
        with Path(log).open("a") as stream:
            stream.write(
                json.dumps(
                    {
                        "command": command,
                        "cwd": str(kwargs["cwd"]),
                        "timeout": kwargs["timeout"],
                        "check": kwargs["check"],
                    }
                )
                + "\n"
            )

    common.subprocess = version_process(
        lambda: json.loads(Path(control).read_text()), record
    )
    mcp_server.apply_runtime_config(allowed_write_roots=[write_root])
    mcp_server._READONLY = readonly
    mcp_server.mcp.run(transport="stdio")
