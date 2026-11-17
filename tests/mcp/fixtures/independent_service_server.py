# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Actual server registration, pointed at a disposable diagnostic repository."""

import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT / "scripts"))
# Some existing server tools import scientific packages from the project env.
sys.path.extend(str(p) for p in (PROJECT / ".venv/lib").glob("python*/site-packages"))
import mcp_server as server

root = Path(sys.argv[1]).resolve()
server.hub.REPO_ROOT = root
server.CALL_LOG_PATH = root / "artifacts/mcp_server/calls.jsonl"
server._READONLY = True
server._ALLOWED_WRITE_ROOTS = [root / "artifacts"]
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONPATH"] = str(
    PROJECT / "tests/mcp/fixtures/independent_service_startup"
)
os.environ["INDEPENDENT_SERVICE_FIXTURE"] = sys.argv[2]
if sys.argv[2] == "launch_error":
    # The external Python interpreter is unavailable; the real launch raises.
    sys.executable = str(root / "absent-python")
server.mcp.run(transport="stdio")
