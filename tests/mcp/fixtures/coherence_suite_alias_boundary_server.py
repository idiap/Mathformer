# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only process boundary fixture; import the actual production registrations.

No canonical script is executed. No provider or compiler is needed by this
controller: their only possible entry is its external subprocess boundary.
"""

from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
import mcp_server as server
import mathformer as hub

mode, mount = sys.argv[1:]
mount = Path(mount).resolve()
registry = hub.build_registry()
ALIAS = "physics-lib:coherence-suite"
SUITE = "mathformerphysicslib:coherence-suite"
deps = registry[SUITE].depends_on
commands = {tuple(hub.resolve_command(registry[dep].command)): dep for dep in deps}
ledger = []
for dep in deps:
    for path in registry[dep].required_paths:
        target = mount / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch(exist_ok=True)
if mode == "preflight":
    (mount / registry[deps[2]].required_paths[0]).unlink()


def external_command(argv, **kwargs):
    dep = commands[tuple(argv)]  # Every other command fails closed in the fixture.
    assert kwargs == {
        "cwd": mount,
        "text": True,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "timeout": registry[dep].timeout_seconds,
    }
    assert argv[-2:] == ["--self-test", "--json"]
    ledger.append({"action": dep, "argv": argv, "timeout": kwargs["timeout"]})
    if dep == deps[2]:
        if mode == "exception":
            raise OSError("deterministic launch failure")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                argv, 1, output="partial", stderr="compiler timeout"
            )
        if mode == "write":
            (mount / "undeclared.txt").write_text("unexpected external output")
        if mode == "fail":
            return subprocess.CompletedProcess(
                argv, 7, "partial", "deterministic compiler diagnostic"
            )
    # Scientific-looking JSON is opaque to hub success; capture it unchanged.
    return subprocess.CompletedProcess(
        argv, 0, json.dumps({"ok": False, "action": dep}), ""
    )


hub.subprocess.run = external_command
scope = dict(vars(hub))
exec(
    (ROOT / "tests/mcp/fixtures/coherence_suite_alias_original.py.txt").read_text(),
    scope,
)


@server.mcp.tool()
def fixture_reset() -> dict:
    (mount / "undeclared.txt").unlink(missing_ok=True)
    ledger.clear()
    return {"reset": True}


@server.mcp.tool()
def fixture_ledger() -> dict:
    return {"calls": ledger}


@server.mcp.tool()
def fixture_original(context: dict, extra_args: list[str], seen: list[str]) -> dict:
    fixture_reset()
    return {
        "result": scope["run_action"](
            ALIAS,
            registry,
            hub.RunContext(**context),
            extra_args=extra_args,
            seen=set(seen),
            repository_root=mount,
        )
    }


server.mcp.run(transport="stdio")
