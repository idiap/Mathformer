# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Hermetic repositories containing unchanged diagnostic implementations."""

from pathlib import Path
import shutil

PROJECT = Path(__file__).resolve().parents[3]
FILES = (
    "scripts/mathformer.py",
    "scripts/workflow_write_audit.py",
    "scripts/workflow_catalog.py",
    "scripts/mcp_service_config.py",
    "scripts/load_mcp_service_config.py",
    "scripts/probe_mcp_service_dependencies.py",
    "scripts/mathformer_mcp_service.py",
    "scripts/mcp_server.py",
    "requirements-mcp-service.txt",
    "skills/control/reasoning-log-schema-guardian/scripts/reasoning_log.py",
)


def prepare(root, mode="success"):
    for name in FILES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT / name, target)
    config = root / "config/mathformer_mcp.example.toml"
    config.parent.mkdir()
    config.write_text('[service]\ntransport = "stdio"\n')
    catalog = (
        root
        / "skills/control/workflow-contract-validator/references/normalized-workflows/catalog.json"
    )
    catalog.parent.mkdir(parents=True)
    catalog.write_text(
        '{"schema_version":"mathformer.normalized-workflow-catalog/v1","counts":{},"workflows":[]}'
    )
    if mode == "config_failure":
        config.write_text('[service]\ntransport = "invalid"\n')
    if mode == "preflight":
        (root / "scripts/load_mcp_service_config.py").unlink()
    if mode == "selfcheck_failure":
        (root / "scripts/uncontrolled.py").write_text(
            "# Uncontrolled input, never executed.\n"
        )
