# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synthetic catalog data in isolated repositories; native algorithms unchanged.

Only the DOMAIN_CATALOG literal is replaced. The generator, regression runner,
indexer, storage, Bloom filters, hashed embeddings and retrieval all run their
real source. There is no model/provider in this route and no prover is invoked.
"""

import ast
from pathlib import Path
import shutil

LEAF = "tests/kb/run_famous_theorem_corpus.py"
GENERATOR = "skills/premise-kb/premise-kb-theorem-seed-generator/scripts/generate_famous_theorem_axiom_corpus.py"
INDEXER = "skills/premise-kb/premise-kb-indexer/scripts/index_premise_kb.py"
ARTIFACT = "artifacts/kb/famous_corpus_test"
TARGET = "famous.complex_analysis.fundamental_theorem_of_algebra"
UNRELATED = "famous.geometry.pythagorean_theorem"


def catalog(mode="success"):
    result = {}
    for i, domain in enumerate(
        ["complex_analysis", "geometry", *[f"fixture_domain_{j}" for j in range(23)]]
    ):
        names = [f"Fixture domain {i} theorem {j}" for j in range(20)]
        if i == 0:
            names[0] = "Fundamental theorem of algebra"
        elif i == 1:
            names[0] = "Pythagorean theorem"
        result[domain] = {
            "label": f"fixture subject {i}",
            "tags": [domain, "fixture"],
            "names": names,
        }
    if mode == "duplicate":
        result["fixture_domain_0"]["names"][1] = result["fixture_domain_0"]["names"][0]
    elif mode == "malformed":
        result["fixture_domain_0"]["names"].pop()
    elif mode == "absent":
        result["geometry"]["names"][0] = "Fixture missing target"
    return result


def put(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def populate(root: Path, project: Path, mode="success"):
    for path in [LEAF, INDEXER]:
        put(root, path, (project / path).read_text())
    source = (project / GENERATOR).read_text()
    assignment = next(
        n
        for n in ast.parse(source).body
        if isinstance(n, ast.AnnAssign)
        and isinstance(n.target, ast.Name)
        and n.target.id == "DOMAIN_CATALOG"
    )
    # Change only the input data literal, with a structural assertion that every
    # executable function in the isolated generator is byte-for-byte AST equal.
    lines = source.splitlines(keepends=True)
    start = (
        sum(map(len, lines[: assignment.value.lineno - 1]))
        + assignment.value.col_offset
    )
    end = (
        sum(map(len, lines[: assignment.value.end_lineno - 1]))
        + assignment.value.end_col_offset
    )
    fixture_source = source[:start] + repr(catalog(mode)) + source[end:]

    def functions(text):
        return [
            ast.dump(n) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)
        ]

    assert functions(source) == functions(fixture_source)
    put(root, GENERATOR, fixture_source)
    dest = root / "backends/premise_kb/MathformerKB"
    shutil.copytree(
        project / "backends/premise_kb/MathformerKB",
        dest,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__"),
    )


def stale(root):
    put(root, ARTIFACT + "/stale.txt", "old output\n")


def stable(value):
    """Remove only native wall-clock provenance, never scientific/output data."""
    if isinstance(value, dict):
        return {
            key: stable(item) for key, item in value.items() if key != "retrieved_at"
        }
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value
