# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Only the external Vampire process is substituted, never native source steps."""

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from backends.atp.MathformerATP import vampire as v


def compiler(command, **kwargs):
    if "--version" in command:
        return subprocess.CompletedProcess(
            command, 0, "deterministic Vampire boundary", ""
        )
    path = Path(command[-1])
    assert path.suffix == ".p", command
    root = next(p for p in path.parents if (p / "fixture-mode").is_file())
    mode = (root / "fixture-mode").read_text()
    with (root / "calls.jsonl").open("a") as out:
        out.write(json.dumps({"command": command, "text": path.read_text()}) + "\n")
    if mode == "error":
        raise RuntimeError("deterministic compiler failure")
    proved = True
    if path.parent.name == "premise_minimization":
        proved = "without_generated_" not in path.name
    elif path.parent.name == "premise_generation":
        proved = not (mode == "lemma_fail" and path.name.startswith("01_"))
    elif mode == "unproved":
        proved = False
    output = "% SZS status " + ("Theorem" if proved else "GaveUp") + "\n"
    if proved and "--proof" in command:
        output += "% SZS output start Proof\nfof(f1,axiom,p).\nfof(f2,plain,$false,inference(resolution,[],[f1])).\n% SZS output end Proof\n"
    return subprocess.CompletedProcess(command, 0, output, "")


def serve():
    os.environ["VAMPIRE_BIN"] = "fixture-vampire"
    v.subprocess.run = compiler
    import mcp_server

    mcp_server.mcp.run(transport="stdio")


if __name__ == "__main__":
    serve()
