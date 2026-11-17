# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only deterministic external package/tool discovery; no providers run."""

import importlib.metadata
import os
from pathlib import Path
import shutil

_original_version = importlib.metadata.version
PACKAGES = {
    "mcp",
    "httpx",
    "uvicorn",
    "sympy",
    "numpy",
    "huggingface_hub",
    "docling",
    "openai",
    "anthropic",
    "google-genai",
}


def version(name):
    if name in PACKAGES:
        # All optional providers and the three required SDKs are absent.
        # The source must preserve ok=True and ready=False.
        if (
            os.environ.get("INDEPENDENT_SERVICE_FIXTURE") == "write_audit"
            and name == "mcp"
        ):
            Path("unexpected.txt").write_text(
                "external discovery boundary wrote a file\n"
            )
        raise importlib.metadata.PackageNotFoundError(name)
    return _original_version(name)


importlib.metadata.version = version
_original_which = shutil.which


def which(name, *args, **kwargs):
    if name in {"lake", "lean", "vampire", "rocq", "coqc", "isabelle"}:
        return None
    return _original_which(name, *args, **kwargs)


shutil.which = which
