# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only deterministic substitution at the Vampire process boundary."""

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from backends.atp.MathformerATP import vampire as v
import atp_demo_tools

ORIGINAL_WORKER = atp_demo_tools._worker


def compiler(command, **kwargs):
    if "--version" in command:
        return subprocess.CompletedProcess(
            command, 0, "Vampire deterministic fixture", ""
        )
    path = Path(command[-1])
    if path.suffix != ".p":
        raise AssertionError(command)
    root = next(parent for parent in path.parents if parent.name == "atp_function_demo")
    mode = (root.parents[2] / "fixture-mode").read_text()
    text = path.read_text()
    record = {"path": str(path), "command": command, "text": text}
    with (root / "compiler.calls.jsonl").open("a") as out:
        out.write(json.dumps(record) + "\n")
    if mode == "error":
        raise RuntimeError("deterministic compiler boundary failure")
    if mode == "slow":
        import time

        time.sleep(2)
    is_lemma = path.parent.name == "premise_generation"
    is_min = path.parent.name == "premise_minimization"
    proved = (
        (not path.name.startswith("02_"))
        if (is_lemma or is_min)
        else mode != "unproved"
    )
    # Complete SZS/TSTP fixture passes through the real native parser and informalizer.
    output = "% SZS status " + ("Theorem" if proved else "GaveUp") + "\n"
    if (
        proved
        and "--proof" in command
        and command[command.index("--proof") + 1] == "tptp"
    ):
        output += "% SZS output start Proof\nfof(f1,axiom,p).\nfof(f2,plain,$false,inference(resolution,[],[f1])).\n% SZS output end Proof\n"
    return subprocess.CompletedProcess(command, 0, output, "fixture diagnostic")


def install():
    original = v.VampireRunner

    class FixtureRunner(original):
        def __init__(self, binary=None):
            super().__init__(binary="fixture-vampire")

    v.VampireRunner = FixtureRunner
    v.subprocess.run = compiler


def worker(pipe, root, demo):
    install()
    ORIGINAL_WORKER(pipe, root, demo)


def serve(root):
    import mathformer as hub

    hub.REPO_ROOT = Path(root)
    # Load the actual server and its registrations, without main/config/credentials.
    import mcp_server

    atp_demo_tools._worker = worker
    mcp_server.mcp.run(transport="stdio")


if __name__ == "__main__":
    serve(sys.argv[1])
