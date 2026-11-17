# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synthetic inputs and byte-identical native sources; no production artifacts."""

import json
import shutil

LEAF = "tests/mathlib/run_indexing_control_suite.py"
PROFILE = "skills/mathlib/mathlib-concept-ontology-manager/references/core.yaml"


def populate(root, project, *, declarations=True):
    roots = [
        "mathlib-index-builder",
        "mathlib-concept-ontology-manager",
        "mathlib-term-expansion-annotator",
        "mathlib-navigation-state-planner",
    ]
    paths = [
        project / LEAF,
        project / PROFILE,
        project
        / "skills/control/reasoning-log-schema-guardian/scripts/reasoning_log.py",
    ]
    for name in roots:
        paths.extend((project / "skills/mathlib" / name / "scripts").glob("*.py"))
    for path in paths:
        target = root / path.relative_to(project)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    mathlib = root / ".lake/packages/mathlib/Mathlib/Topology"
    mathlib.mkdir(parents=True, exist_ok=True)
    (mathlib.parent.parent / ".git").mkdir(exist_ok=True)
    (mathlib / "Basic.lean").write_text(
        "import Mathlib.Data.Set.Basic\n"
        + ("theorem compact_fixture : True := by trivial\n" if declarations else "")
    )
    (root / ".indexing-route-fixture").touch()


def clean(root):
    shutil.rmtree(root / "artifacts", ignore_errors=True)
    root.with_suffix(".calls.jsonl").unlink(missing_ok=True)


def stable(value):
    """Strip only volatile native observability for sequential oracle comparison."""
    if isinstance(value, dict):
        return {
            k: stable(v)
            for k, v in value.items()
            if k
            not in {
                "duration_seconds",
                "generated_at_utc",
                "build_timestamp_utc",
                "metadata_hash",
                "elapsed_seconds",
            }
        }
    if isinstance(value, list):
        return [stable(v) for v in value]
    if isinstance(value, str):
        try:
            return stable(json.loads(value))
        except (ValueError, TypeError):
            pass
    return value
