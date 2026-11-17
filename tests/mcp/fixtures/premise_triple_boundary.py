# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only replacement of the external Vampire process boundary."""

from pathlib import Path
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from backends.atp.MathformerATP import vampire as v
import premise_triple_tools as tools

ORIGINAL_WORKER = tools._worker


def compiler(command, **kwargs):
    if "--version" in command:
        return subprocess.CompletedProcess(
            command, 0, "deterministic Vampire fixture", ""
        )
    path = Path(command[-1])
    assert path.suffix == ".p", command
    root = next(p for p in path.parents if (p / "fixture-mode").is_file())
    mode = (root / "fixture-mode").read_text()
    with (root / "artifacts/vampire_atp/compiler.calls.jsonl").open("a") as out:
        out.write(json.dumps(dict(command=command, text=path.read_text())) + "\n")
    if mode == "error":
        raise RuntimeError("deterministic external compiler failure")
    if mode == "slow":
        time.sleep(2)
    proved = True
    if path.parent.name == "premise_minimization":
        proved = "without_generated_" not in path.name
    elif path.parent.name == "premise_generation":
        proved = mode != "lemma_fail"
    elif mode == "unproved":
        proved = False
    output = "% SZS status " + ("Theorem" if proved else "GaveUp") + "\n"
    if proved and "--proof" in command:
        output += "% SZS output start Proof\nfof(goal,conjecture,inv(mul(mul(x,y),z))=mul(inv(z),mul(inv(y),inv(x)))).\nfof(done,plain,$false,inference(resolution,[],[goal])).\n% SZS output end Proof\n"
    return subprocess.CompletedProcess(command, 0, output, "")


def install():
    import os

    os.environ["VAMPIRE_BIN"] = "fixture-vampire"
    v.subprocess.run = compiler


def worker(pipe, root, profile):
    install()
    ORIGINAL_WORKER(pipe, root, profile)


def serve(root):
    import mathformer as hub

    hub.REPO_ROOT = Path(root)
    import mcp_server

    tools._worker = worker
    mcp_server.mcp.run(transport="stdio")


if __name__ == "__main__":
    serve(sys.argv[1])
