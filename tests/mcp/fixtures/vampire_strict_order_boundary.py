# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic replacement of only the external Vampire subprocess boundary."""

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from backends.atp.MathformerATP import vampire as v


def compiler(command, **kwargs):
    assert command[0] == "fixture-vampire", command
    assert "timeout" not in kwargs  # Native implementation has no Python timeout.
    if "--version" in command:
        return subprocess.CompletedProcess(command, 0, "fixture Vampire 1", "")
    path = Path(command[-1])
    root = path.parent.parent
    mode = (root / "fixture-mode").read_text()
    assert command[command.index("--time_limit") + 1] == "10"
    assert command[command.index("--mode") + 1] == "portfolio"
    assert command[command.index("--proof") + 1] == "tptp"
    assert path.suffix == ".p"
    text = path.read_text()
    assert all(
        name in text for name in ("r_transitive", "r_irreflexive", "r_asymmetric")
    )
    assert text.count("fof(") == 3
    with (root / "calls.jsonl").open("a") as out:
        out.write(json.dumps({"command": command, "text": path.read_text()}) + "\n")
    if mode == "error":
        raise RuntimeError("deterministic Vampire failure")
    status = {
        "unproved": "GaveUp",
        "unsatisfiable": "Unsatisfiable",
        "contradictory": "ContradictoryAxioms",
    }.get(mode, "Theorem")
    output = "% SZS status " + status + "\n"
    if mode != "unproved":
        lines = [f"fof(f{i},axiom,p)." for i in range(25)]
        lines.append(
            "fof(end,plain,"
            + ("p" if mode == "nofalse" else "$false")
            + ",inference(resolution,[],[f0]))."
        )
        output += (
            "% SZS output start Proof\n"
            + "\n".join(lines)
            + "\n% SZS output end Proof\n"
        )
    return subprocess.CompletedProcess(
        command, 7 if mode == "nonzero" else 0, output, ""
    )


# Install only the external compiler boundary inside the spawned native worker.
from vampire_policy_tools import _native_search_worker as native_worker


def compiler_worker(*args):
    v.subprocess.run = compiler
    return native_worker(*args)


def serve():
    from vampire_strict_order_tools import source

    source().ARTIFACT_ROOT = Path(sys.argv[1]) / "output"
    os.environ["VAMPIRE_BIN"] = "fixture-vampire"
    v.subprocess.run = compiler
    import vampire_policy_tools

    vampire_policy_tools._native_search_worker = compiler_worker
    import mcp_server

    mcp_server.mcp.run(transport="stdio")


if __name__ == "__main__":
    serve()
