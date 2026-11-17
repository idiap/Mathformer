# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external process fixture. Never launches a provider or compiler."""

from pathlib import Path
import json
import subprocess
from types import SimpleNamespace


def install(module, mode="success"):
    ledger = []

    def run(argv, **kwargs):
        assert kwargs["cwd"] == module.REPO_ROOT
        assert kwargs["text"] is True and kwargs["capture_output"] is True
        name = Path(argv[1]).name if argv[0] != "lake" else "lean"
        if name == "estimate_proof_expansion_difficulty.py":
            assert kwargs["timeout"] == 60
            assert argv[2:5] == ["--max-words-per-segment", "80", "--json"]
            assert kwargs["input"]
            payload = {"max_difficulty_score": 2, "web_search_recommended_count": 1}
        elif name == "map_mathlib_concepts.py":
            timeout = int(argv[argv.index("--verify-timeout-sec") + 1])
            assert kwargs["timeout"] == max(120, timeout * 20)
            assert argv[argv.index("--verify-max-concepts") + 1] == "5"
            assert argv[argv.index("--verify-max-candidates") + 1] == "3"
            payload = {
                "group": {
                    "candidates": [
                        {"qualified_name": "Nat.add_comm", "check_ok": True}
                    ],
                    "relevant_modules": [],
                }
            }
        elif name == "navigate_mathlib_hierarchy.py":
            assert kwargs["timeout"] == 60
            payload = {
                "query_results": {"matching_modules": [], "matching_declarations": []}
            }
        elif name == "check_mathlib_compat.py":
            assert kwargs["timeout"] == 120
            payload = {"compatibility_score": 100}
            Path(argv[argv.index("--output") + 1]).write_text(json.dumps(payload))
        elif name == "lean":
            assert argv[:3] == ["lake", "env", "lean"]
            assert kwargs["timeout"] == 120
            text = Path(argv[3]).read_text()
            payload = None
        else:
            raise AssertionError(f"Unrecognized external command: {argv}")
        ledger.append(
            {"cmd": list(argv), "timeout": kwargs["timeout"], "input": kwargs["input"]}
        )
        if mode == "exception":
            raise OSError("fixture external process unavailable")
        if mode == "timeout" and name == "lean":
            raise subprocess.TimeoutExpired(
                argv, kwargs["timeout"], output="", stderr="fixture timeout"
            )
        failed = mode == "fail"
        stdout = (
            "\n".join(
                line[7:] for line in text.splitlines() if line.startswith("#check ")
            )
            if payload is None
            else json.dumps(payload)
        )
        return subprocess.CompletedProcess(
            argv, 7 if failed else 0, stdout, "fixture: error: failed" if failed else ""
        )

    module.subprocess = SimpleNamespace(
        run=run, TimeoutExpired=subprocess.TimeoutExpired
    )
    return ledger
