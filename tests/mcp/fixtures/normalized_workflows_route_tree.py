# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated definition inputs for the unchanged native normalization checker.

No providers, credentials or scientific processes are used. The deliberately
empty catalog exposes real drift detection across the entire finite inventory.
"""

import importlib.util
import json
from pathlib import Path
import shutil

DIRECTORY = Path("skills/control/workflow-contract-validator")
CHECKER = str(DIRECTORY / "scripts/normalize_workflows.py")
OUTPUT = DIRECTORY / "references/normalized-workflows"
CATALOG = OUTPUT / "catalog.json"


def load_checker(project):
    spec = importlib.util.spec_from_file_location(
        "normalized_route_checker", project / CHECKER
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def populate(root, project):
    # Copy implementation and definition inputs; skip caches, generated corpus
    # and navigation symlinks. No source or production artifact is regenerated.
    for folder in ["scripts", "skills", "examples"]:
        for source in (project / folder).rglob("*"):
            relative = source.relative_to(project)
            if (
                source.is_symlink()
                or not source.is_file()
                or "__pycache__" in relative.parts
                or relative.is_relative_to(OUTPUT)
            ):
                continue
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    # Finite synthetic hook/profile collections keep this fixture independent
    # of unrelated authored identities in the repository's larger corpus.
    (root / "skills/SKILL_HOOKS.yaml").write_text("hooks: []\nloop_contracts: []\n")
    (root / "skills/REASONING_TYPES.yaml").write_text("reasoning_styles: []\n")
    # Authored descriptors also reference backend and test implementation files.
    # Copy those inputs without executing any referenced code.
    references = project / DIRECTORY / "references"
    for authored in references.glob("*.workflow.json"):
        document = json.loads(authored.read_text())
        # Complete fixture-only catalog metadata on legacy authored examples.
        # These are data inputs to the real renderer, not executable substitutes.
        native = document.setdefault("extensions", {}).setdefault(
            "mathformer.source", {}
        )
        native.setdefault("category", document["id"].split("_", 1)[0])
        native.setdefault("native_id", document["aliases"][0])
        native.setdefault("owner_skill", str(DIRECTORY / "SKILL.md"))
        (root / authored.relative_to(project)).write_text(json.dumps(document))
        for row in document.get("provenance", {}).get("sources", []):
            relative = Path(row["path"])
            target = root / relative
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(project / relative, target)
    count = len(load_checker(root).inventory())
    (root / OUTPUT).mkdir(parents=True, exist_ok=True)
    (root / CATALOG).write_text("{}\n")
    return count
