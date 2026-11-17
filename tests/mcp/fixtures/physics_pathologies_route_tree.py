# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Disposable, unchanged native planner sources and an outbound-process guard.

The selected route emits plans only: there is no provider or external Lean
compiler to replace. External controller-boundary diagnostics use the separate
reasoning_route_compiler fixture, never a substitute for any of these planners.
"""

from pathlib import Path
import shutil
import sys


def populate(root, source, registry):
    for item in registry.values():
        for path in item.required_paths:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / path, target)


def guard(root, registry):
    commands = {(sys.executable, *item.command[1:]) for item in registry.values()}

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
    from physics_pathologies_route_tools import ACTIONS

    root = Path(directory).resolve()
    mcp_server._ALLOWED_WRITE_ROOTS = [root]
    mcp_server.CALL_LOG_PATH = root / "service-calls.jsonl"
    guard(root, {key: hub.build_registry()[key] for key in ACTIONS})
    mcp_server.mcp.run(transport="stdio")
