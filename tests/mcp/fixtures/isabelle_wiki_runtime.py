# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline bootstrap for the real wiki MCP registrations.

Only compiler discovery/build are substituted (by isabelle_route_boundary in
child interpreters). Grounding, drafting and checking execute their real CLIs
in an isolated source tree. The two special compiler cases use the real
checker with the existing test-only compiler bootstrap.
"""

import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
COMPILER = Path(__file__).with_name("isabelle_wiki_compiler.py")
_run = subprocess.run


def isolate(module, root):
    module.REPO_ROOT = Path(root)
    module.DEFAULT_OUTPUT_DIR = Path(root) / "artifacts/isabelle/wiki_level"

    def run(argv, **kwargs):
        config = json.loads((Path(root) / ".isabelle-route-fixture.json").read_text())
        mode = config["compiler"]
        if argv[1].endswith("check_isabelle_theory.py") and mode.startswith(
            "outer-timeout"
        ):
            # Fault injection is confined to the compiler-owning process. No
            # source step is replaced. These are real TimeoutExpired payloads.
            output = {
                "outer-timeout-empty": None,
                "outer-timeout-bytes": b'{"ok":true}',
                "outer-timeout-invalid": b"\xff",
            }[mode]
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output=output)
        if argv[1].endswith("check_isabelle_theory.py") and mode in {
            "placeholder",
            "exit-disagrees",
        }:
            argv = [argv[0], str(COMPILER), "--checker", mode, *argv[2:]]
        return _run(argv, **kwargs)

    module.subprocess = SimpleNamespace(
        run=run, TimeoutExpired=subprocess.TimeoutExpired
    )
    return module


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "scripts"))
    from isabelle_wiki_tools import source
    import mcp_server

    root = Path(sys.argv[1]).resolve()
    isolate(source(), root)
    mcp_server.apply_runtime_config(allowed_write_roots=[str(root)])
    mcp_server.mcp.run(transport="stdio")
