# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only filesystem mount and deterministic external compiler boundary."""

from pathlib import Path
from comprehensive_workflow_boundary import install
from comprehensive_strict_tools import source_runner
import generative_family_workflow_tools as tools

NATIVE_WORKER = tools._worker


def worker(pipe):
    import os

    install(source_runner(), Path(os.environ["GENERATIVE_FIXTURE_ROOT"]))
    NATIVE_WORKER(pipe)


def serve(root):
    import os
    import mathformer as hub
    from mcp_server import mcp

    os.environ["GENERATIVE_FIXTURE_ROOT"] = str(root)
    hub.REPO_ROOT = Path(root)
    install(source_runner(), Path(root))
    tools._worker = worker
    mcp.run(transport="stdio")
