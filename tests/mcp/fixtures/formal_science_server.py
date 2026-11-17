# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only HTTP provider boundary; all registered steps remain production code."""

import io
import json
from pathlib import Path
import sys
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from formal_science_tools import source
from mcp_server import mcp

boundary = Path(sys.argv[1])
events = Path(sys.argv[2])


def urlopen(url):
    with events.open("a") as output:
        output.write(json.dumps({"url": url}) + "\n")
    specification = json.loads(boundary.read_text())
    if specification.get("error"):
        raise URLError(specification["error"])
    if specification.get("unexpected"):
        raise RuntimeError(specification["unexpected"])
    return io.BytesIO(specification["body"].encode())


source().urlopen = urlopen
mcp.run(transport="stdio")
