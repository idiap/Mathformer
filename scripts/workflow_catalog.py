# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only normalized workflow discovery shared by plugins and MCP.

No descriptor is executed, no YAML dependency is required and no resource path
comes from a caller. The generated catalog selects files and binds their bytes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = Path(
    "skills/control/workflow-contract-validator/references/normalized-workflows"
)


def load_catalog(root: Path = REPO_ROOT) -> dict:
    """Load identities and reject ambiguous aliases or malformed registry paths."""
    catalog = json.loads((root / WORKFLOWS / "catalog.json").read_text())
    if catalog.get("schema_version") != "mathformer.normalized-workflow-catalog/v1":
        raise ValueError("unsupported normalized workflow catalog")
    identities = set()
    counts = {key: 0 for key in catalog["counts"]}
    for row in catalog["workflows"]:
        if not row["id"].endswith("_workflow") or row["category"] not in counts:
            raise ValueError("invalid normalized workflow identity/category")
        for identity in [row["id"], *row["aliases"]]:
            if identity in identities:
                raise ValueError(f"ambiguous normalized workflow identity: {identity}")
            identities.add(identity)
        base = (root / WORKFLOWS).resolve()
        if not (base / row["path"]).resolve().is_relative_to(base):
            raise ValueError("workflow path escapes catalog directory")
        counts[row["category"]] += 1
    if counts != catalog["counts"]:
        raise ValueError("normalized workflow catalog count mismatch")
    return catalog


def resolve_workflow(identifier: str, root: Path = REPO_ROOT) -> dict:
    """Resolve exact canonical identities or explicit native aliases only."""
    for row in load_catalog(root)["workflows"]:
        if identifier == row["id"] or identifier in row["aliases"]:
            return row
    raise ValueError(f"unknown normalized workflow: {identifier}")


def descriptor_text(row: dict, root: Path = REPO_ROOT) -> str:
    """Read a catalog-selected descriptor and verify its generated digest."""
    base = (root / WORKFLOWS).resolve()
    path = (base / row["path"]).resolve()
    if not path.is_relative_to(base):
        raise ValueError("workflow path escapes catalog directory")
    content = path.read_bytes()
    if row["descriptor_digest"] != "sha256:" + hashlib.sha256(content).hexdigest():
        raise ValueError(f'normalized workflow descriptor drift: {row["id"]}')
    return content.decode("utf-8")


def plugin_skill_name(identifier: str) -> str:
    """Map a canonical ID to an explicit portable client name within 64 chars."""
    slug = "workflow-" + identifier.replace("_", "-")
    if len(slug) <= 64:
        return slug
    suffix = hashlib.sha256(identifier.encode()).hexdigest()[:10]
    return slug[:53].rstrip("-") + "-" + suffix
