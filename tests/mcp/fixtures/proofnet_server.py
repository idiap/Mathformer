# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Only the external Hugging Face download boundary is substituted in tests."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from proofnet_tools import source
from mcp_server import mcp

boundary, ledger = map(Path, sys.argv[1:3])


def download(**kwargs):
    with ledger.open("a") as output:
        output.write(json.dumps(kwargs) + "\n")
    config = json.loads(boundary.read_text())
    if config.get("error"):
        raise RuntimeError(config["error"])
    return str(Path(config["directory"]) / kwargs["filename"])


source().hf_hub_download = download
mcp.run(transport="stdio")
