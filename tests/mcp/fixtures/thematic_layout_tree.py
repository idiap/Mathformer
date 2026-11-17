# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synthetic layout inputs; only the selected leaf is executable source.

Other declared paths are inert markers. This is an isolated filesystem fixture,
not a production workflow or a replacement implementation of layout checks.
"""

from pathlib import Path
import organize_repository_layout as layout


def put(root, relative, text="fixture\n"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def populate(root: Path, project: Path):
    for folder in ["scripts", "tests", "docs", "skills"]:
        put(root, folder + "/README.md")
    for theme in layout.DOC_THEMES:
        (root / "docs" / theme).mkdir(exist_ok=True)
    for names in layout.SCRIPT_THEMES.values():
        for name in names:
            put(root, "scripts/" + name)
    put(
        root,
        "scripts/organize_repository_layout.py",
        (project / "scripts/organize_repository_layout.py").read_text(),
    )
    for names in layout.TEST_ALIASES.values():
        for name in names:
            put(root, "tests/" + name)
    for family, components in layout.BACKEND_COMPONENTS.items():
        for name in components:
            put(root, "backends/" + family + "/" + name)
    for name in layout.LIBRARY_COMPONENTS:
        put(root, "libraries/" + name)
    put(root, "skills/control/mathformer-workflow-router/SKILL.md")
    put(root, "skills/lean/lean-fixture/SKILL.md")
    # Construct fixture links independently; production apply_views is never
    # invoked to prepare the tree or conceal a repair in the selected route.
    for alias, canonical in layout.expected_views(root).items():
        alias.parent.mkdir(parents=True, exist_ok=True)
        if not alias.is_symlink():
            alias.symlink_to(layout.relative_target(alias, canonical))
