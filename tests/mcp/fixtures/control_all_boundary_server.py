# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only deterministic external command boundary; real registered MCP tools.

No canonical command is launched. Only subprocess.run at the external process
boundary is substituted; native preflight, recursion, state and audit run intact.
"""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts")]
import mcp_server as server
import mathformer as hub

mode, directory = sys.argv[1:]
hub.REPO_ROOT = Path(directory)
registry = hub.build_registry()
deps = registry["control:all"].depends_on
commands = {tuple(hub.resolve_command(registry[dep].command)): dep for dep in deps}
for dep in deps:
    for path in registry[dep].required_paths:
        target = hub.REPO_ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch(exist_ok=True)


def external_command(argv, **kwargs):
    dep = commands[tuple(argv)]  # Reject any unexpected process invocation.
    assert kwargs["cwd"] == hub.REPO_ROOT
    assert kwargs["text"] is True
    assert kwargs["stdout"] == subprocess.PIPE and kwargs["stderr"] == subprocess.PIPE
    assert kwargs["timeout"] == registry[dep].timeout_seconds
    if dep == deps[2]:
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                argv, 1, output="partial", stderr="compiler timeout"
            )
        if mode == "write":
            (hub.REPO_ROOT / "undeclared.txt").write_text("unexpected compiler output")
        if mode == "fail":
            return subprocess.CompletedProcess(
                argv, 7, "partial", "deterministic compiler diagnostic"
            )
    return subprocess.CompletedProcess(argv, 0, dep + ": checked", "")


hub.subprocess.run = external_command
scope = dict(vars(hub))
exec((ROOT / "tests/mcp/fixtures/control_all_original.py.txt").read_text(), scope)


@server.mcp.tool()
def fixture_original(context: dict, extra_args: list[str], ancestry: list[str]) -> dict:
    # Reset external filesystem effects before comparing independent executions.
    (hub.REPO_ROOT / "undeclared.txt").unlink(missing_ok=True)
    result = scope["run_action"](
        "control:all",
        registry,
        hub.RunContext(**context),
        extra_args=extra_args,
        seen=set(ancestry),
    )
    (hub.REPO_ROOT / "undeclared.txt").unlink(missing_ok=True)
    return {"result": result}


server.mcp.run(transport="stdio")
