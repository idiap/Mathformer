# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolate native checks in a disposable repository; replace only lake.

Every Python child runs the unchanged source CLI, including grounding's nested
checks. This coordinator has no model/provider calls: no provider is configured.
"""

from pathlib import Path
import json
import shutil
import subprocess
from types import SimpleNamespace


def install(native, directory):
    root = Path(directory).resolve()
    original_root = Path(__file__).resolve().parents[3]
    paths = [
        original_root / p.relative_to(native.REPO_ROOT) for p in native.SCRIPTS.values()
    ] + [
        original_root
        / "skills/mathlib/mathlib-import-minimizer/scripts/minimize_imports.py",
        original_root
        / "skills/mathlib/mathlib-compatibility-auditor/scripts/check_mathlib_compat.py",
        original_root
        / "skills/control/reasoning-log-schema-guardian/scripts/reasoning_log.py",
        original_root / "skills/control/gate-policy-controller/scripts/gate_policy.py",
    ]
    # Source is copied, never rewritten. __file__ resolves native default paths
    # into this isolated repository in all real child processes.
    for path in paths:
        relative = path.relative_to(original_root)
        source = original_root / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    native.SCRIPTS = {
        k: root / p.relative_to(native.REPO_ROOT) for k, p in native.SCRIPTS.items()
    }
    native.REPO_ROOT = root
    native.ARTIFACT_DIR = root / "artifacts/lean_consistency"
    calls = []

    def external(command, **kwargs):
        calls.append({"command": list(command), "timeout": kwargs["timeout"]})
        with (root / "process-calls.jsonl").open("a") as log:
            log.write(json.dumps(calls[-1]) + "\n")
        if command[:3] == ["lake", "env", "lean"]:
            assert kwargs["timeout"] == 240
            text = (root / command[3]).read_text()
            if "compiler-timeout" in text:
                raise subprocess.TimeoutExpired(command, kwargs["timeout"])
            if "compiler-crash" in text:
                raise OSError("deterministic compiler launch failure")
            failed = "compiler-fail" in text
            return subprocess.CompletedProcess(
                command, int(failed), "", "fixture diagnostic" if failed else ""
            )
        assert Path(command[1]) in native.SCRIPTS.values(), command
        return subprocess.run(command, **kwargs)

    native.subprocess = SimpleNamespace(run=external)
    return calls


def serve(directory):
    import mcp_server
    from lean_consistency_workflow_tools import source_report

    root = Path(directory).resolve().resolve()
    install(source_report(), root)
    mcp_server._ALLOWED_WRITE_ROOTS = [root]
    mcp_server.CALL_LOG_PATH = root / "service-calls.jsonl"
    mcp_server.mcp.run(transport="stdio")
