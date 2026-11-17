# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only Lean boundary. Python report programs execute unchanged."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
REAL_RUN = subprocess.run


def run(args, **kwargs):
    cwd = Path(kwargs["cwd"])
    if args[:3] == ["lake", "env", "lean"]:
        bad = "compile-fail" in cwd.name and "formalphysics_0191" in args[3]
        return subprocess.CompletedProcess(
            args,
            1 if bad else 0,
            "fixture compiler stdout\n",
            "fixture compiler stderr\n" if bad else "",
        )
    # These are real deterministic report helper programs, not fixtures for reports.
    if args[0] == sys.executable and args[1].startswith("skills/"):
        if "helper-fail" in cwd.name:
            # Exercise the actual helper's file-error path after earlier critics succeeded.
            if "review_mathematical_final_hypotheses.py" in args[1]:
                source = cwd / args[args.index("--source-file") + 1]
                source.unlink(missing_ok=True)
        return REAL_RUN([args[0], str(ROOT / args[1]), *args[2:]], **kwargs)
    raise AssertionError("Unexpected process boundary: " + repr(args))


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "scripts"))
    import refresh_formalphysics_extra_lean_reports as native

    native.subprocess.run = run
    import mcp_server

    if "--readonly" in sys.argv:
        mcp_server._READONLY = True
    mcp = mcp_server.mcp
    mcp.run(transport="stdio")
