# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Dispose source-owned output defaults without modifying the copied source."""

from pathlib import Path
import shutil

SOURCE = "skills/latex-textbook/textbook-chapter-autoformalization-orchestrator/scripts/orchestrate_textbook_chapters.py"


def prepare(root, project):
    root = Path(root).resolve()
    shutil.copytree(
        Path(project) / "skills",
        root / "skills",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    # Some nested native checkers import shared helpers from scripts/.
    shutil.copytree(
        Path(project) / "scripts",
        root / "scripts",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    (root / "case.json").write_text('{"mode":"good"}')
    return root


def serve(root):
    import mcp_server
    import textbook_chapter_workflow_tools as tools

    root = Path(root).resolve()
    tools.ROOT = root
    tools.chapter_source.cache_clear()
    mcp_server._ALLOWED_WRITE_ROOTS = [root]
    mcp_server.CALL_LOG_PATH = root / "service-calls.jsonl"
    mcp_server.mcp.run(transport="stdio")
