# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real MCP registration on an isolated mount; never start the child service."""

from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / "scripts"))
sys.path.extend(str(p) for p in (PROJECT / ".venv/lib").glob("python*/site-packages"))
import mcp_server as server

root = Path(sys.argv[1]).resolve()
server.hub.REPO_ROOT = root
server.apply_runtime_config(
    default_timeout_seconds=17, allowed_write_roots=[str(root / "artifacts")]
)
server.CALL_LOG_PATH = root / "artifacts/mcp_server/calls.jsonl"
server._READONLY = True
if sys.argv[2] == "launch_error":
    # Real OS failure at launch, with no running child or replacement runner.
    sys.executable = str(root / "unavailable-python")
server.mcp.run(transport="stdio")
