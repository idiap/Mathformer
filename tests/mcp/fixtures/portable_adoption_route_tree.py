# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated authored metadata and unchanged native leaf inputs, without providers.

The contract-test file is deliberately absent: this tests an actual process
failure without invoking its nested workflow/PRISM subprocess tests. The final
provenance suite is safe and executes unmodified against temporary receipts.
"""

import importlib.util
import json
from pathlib import Path
import shutil

DIRECTORY = Path("skills/control/workflow-contract-validator")
CATALOG = Path("docs/migrations/portable-repository-adoption/catalog.md")


def populate(root, project):
    def copy(path):
        path = Path(path)
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / path, target)

    metadata = DIRECTORY / "references/portable-adoption.json"
    data = json.loads((project / metadata).read_text())
    paths = {
        metadata,
        DIRECTORY / "references/portable-adoption.schema.json",
        DIRECTORY / "scripts/portable_adoption.py",
        Path("scripts/mathformer.py"),
        Path("scripts/workflow_write_audit.py"),
        Path("tests/control/test_adoption_provenance.py"),
    }
    for name in ["adoption_provenance.py", "reasoning_log.py"]:
        paths.add(Path("skills/control/reasoning-log-schema-guardian/scripts") / name)
    for value in data["taxonomy_sources"].values():
        paths.add(Path(value))
    for surface in data["surfaces"]:
        (root / surface["owner"]).mkdir(parents=True, exist_ok=True)
        if surface["kind"] == "skill":
            paths.add(Path(surface["owner"]) / "SKILL.md")
        for operation in surface["operations"]:
            paths.add(Path(operation["binding"]["path"]))
            paths.update(
                Path(v.split("#", 1)[0])
                for v in operation["typing"]["sources"].values()
            )
    for path in sorted(paths):
        copy(path)
    # Native catalog renderer validates the copied inputs. It performs no
    # invocation, model call, compiler launch or artifact promotion.
    spec = importlib.util.spec_from_file_location(
        "portable_fixture_metadata",
        project / DIRECTORY / "scripts/portable_adoption.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = root / CATALOG
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(module.catalog_text(data))
