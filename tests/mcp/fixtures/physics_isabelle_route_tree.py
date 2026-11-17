# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synthetic TeX with copied native generator; no scientific production inputs.

This generator has no external model/provider or compiler boundary. It must
render its actual eight candidates without invoking any prover or promotion.
"""

import importlib.util
from pathlib import Path
import shutil

LEAF = "scripts/generate_formalphysics_extra_isabelle.py"
SOURCES = Path("data/benchmarks/formal_science/physics_top10_sources")
ARTIFACTS = Path("artifacts/physics_isabelle/from_scratch_isabelle")
CASES = (
    "formalphysics_0066",
    "formalphysics_0191",
    "formalphysics_0172",
    "formalphysics_0119",
    "formalphysics_0026",
    "formalphysics_0176",
    "formalphysics_0054",
    "formalphysics_0059",
)


def load_generator(root):
    spec = importlib.util.spec_from_file_location(
        "_physics_isabelle_generator", root / LEAF
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def populate(root, source):
    target = root / LEAF
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / LEAF, target)
    leaf = load_generator(root)
    (root / SOURCES).mkdir(parents=True)
    for case_id, row in leaf.CASES.items():
        (root / SOURCES / f'{row["rank"]}_{case_id}.tex').write_text(
            f"Synthetic source {case_id}: $E = mc^2$.\nFixture only.\n",
            encoding="utf-8",
        )
    return leaf
