# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Disposable native source tree and synthetic Lean text (never compiled).

No source step or production registry is substituted. Only the separate generic
compiler-boundary test uses a deterministic external compiler fixture.
"""

import shutil
import sys
from pathlib import Path

from coherence_grounding_filesystem import fixture

REPORT = "tests/physics_lean/run_mathformerphysicslib_coherence_loop.py"
COMMON = "skills/mathformerphysicslib/mathformerphysicslib-coherence-inventory-builder/scripts/coherence_common.py"
OUTPUT = Path("artifacts/mathformerphysicslib/coherence")


def closure(registry, actions):
    result = {}

    def visit(key):
        if key in result:
            return
        result[key] = registry[key]
        for dep in registry[key].depends_on:
            visit(dep)

    for key in actions:
        visit(key)
    return result


def populate(root, source, registry):
    paths = {path for item in registry.values() for path in item.required_paths}
    paths.update([COMMON, "libraries/MathformerPhysicsLib/release_status.py"])
    for path in paths:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / path, target)
    return fixture(root)


def guard(root, registry):
    """Allow only native Python scripts in the disposable tree, deny networking."""
    commands = {
        (sys.executable, *item.command[1:])
        for item in registry.values()
        if item.command
    }

    def audit(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "os.system"}:
            raise AssertionError("unexpected external boundary: " + event)
        if event == "subprocess.Popen":
            if tuple(args[1]) not in commands or Path(args[2]).resolve() != root:
                raise AssertionError("unexpected process: " + repr(args[1]))

    sys.addaudithook(audit)


def serve(directory):
    import mathformer as hub
    import mcp_server
    from physics_coherence_route_tools import ACTIONS

    root = Path(directory).resolve()
    mcp_server._ALLOWED_WRITE_ROOTS = [root]
    mcp_server.CALL_LOG_PATH = root / "service-calls.jsonl"
    guard(root, closure(hub.build_registry(), ACTIONS))
    mcp_server.mcp.run(transport="stdio")
