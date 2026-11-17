# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external process fixture for the canonical review registry.

All production steps, preflight, recursion, write auditing, and MCP registration
remain real. No model/provider is used by this controller. Only external argv
execution (including compiler/prover entrypoints) is substituted, failing closed
for commands outside the selected action's reachable leaves.
"""

from pathlib import Path
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import mcp_server as server
import mathformer as hub

mode, directory = sys.argv[1:]
mount = Path(directory).resolve()
registry = hub.build_registry()
ACTION = "review:autoformalization-framework"
pending, visited, commands = [ACTION], set(), {}
while pending:
    action = pending.pop(0)
    if action in visited:
        continue
    visited.add(action)
    item = registry[action]
    pending.extend(item.depends_on)
    for path in item.required_paths:
        target = mount / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if path == "examples/reasoning_flows":
            target.mkdir(exist_ok=True)
        else:
            target.touch(exist_ok=True)
    if item.command:
        commands[tuple(hub.resolve_command(item.command))] = item
# Satisfy the native tool-availability check without launching a compiler.
bin_dir = mount / "fixture-bin"
bin_dir.mkdir()
for name in ("lake", "git"):
    path = bin_dir / name
    path.write_text("#!/bin/sh\nexit 99\n")
    path.chmod(0o755)
os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
server._READONLY = False
server._ALLOWED_WRITE_ROOTS = [mount]
ledger = []


def external_command(argv, **kwargs):
    item = commands[tuple(argv)]
    assert kwargs == dict(
        cwd=mount,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=item.timeout_seconds,
    )
    ledger.append(
        {"action": item.action_id, "argv": list(argv), "timeout": kwargs["timeout"]}
    )
    if item.action_id == "test:docs":
        if mode == "fail":
            return subprocess.CompletedProcess(
                argv, 7, "partial", "documentation diagnostic"
            )
        if mode == "exception":
            raise OSError("deterministic launch failure")
    if item.action_id == "mathformerphysicslib:release-gate":
        assert kwargs["timeout"] == 1200
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                argv, 1200, output="partial build", stderr="compiler timeout"
            )
        if mode == "write":
            (mount / "undeclared.txt").write_text("external output")
    return subprocess.CompletedProcess(
        argv, 0, json.dumps({"action": item.action_id, "compiled": True}), ""
    )


hub.subprocess.run = external_command
scope = dict(vars(hub))
exec((ROOT / "tests/mcp/fixtures/review_framework_original.py.txt").read_text(), scope)


@server.mcp.tool()
def fixture_reset() -> dict:
    (mount / "undeclared.txt").unlink(missing_ok=True)
    ledger.clear()
    return {"reset": True}


@server.mcp.tool()
def fixture_ledger() -> dict:
    return {"calls": ledger}


@server.mcp.tool()
def fixture_original(context: dict) -> dict:
    fixture_reset()
    return {
        "result": scope["run_action"](
            ACTION, registry, hub.RunContext(**context), repository_root=mount
        )
    }


server.mcp.run(transport="stdio")
