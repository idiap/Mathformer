# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated canonical inputs and copied native sources for the mathlib route."""

import json
import shutil

LEAF = "tests/test_program/run_comprehensive_tests.py"


def matrix(modes, family="mathlib"):
    return {
        "schema_version": 2,
        "tests": [
            dict(
                id=f"fixture.{i}",
                module_family=family,
                command=["fixture-compiler", mode],
                owner_skill="fixture",
                hook_id="test.fixture",
                fixture_ids=["compiler"],
                test_kind="regression",
                risk_level="low",
                timeout_seconds=30 + i,
                expected_exit=0,
                write_set=[],
                **(
                    {"optional_dependency": "fixture_missing_provider"}
                    if mode == "missing"
                    else {}
                ),
            )
            for i, mode in enumerate(modes)
        ],
    }


def populate(root, project, data, *, ready=True):
    for relative in (LEAF, "scripts/workflow_write_audit.py"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / relative, target)
    (root / ".mathlib-route-fixture").touch()
    if ready:
        (root / "tests/test_matrix.json").write_text(json.dumps(data))


def clean(root):
    shutil.rmtree(root / "artifacts", ignore_errors=True)
    (root / "undeclared.txt").unlink(missing_ok=True)
    root.with_suffix(".calls.jsonl").unlink(missing_ok=True)


def stable(value):
    if isinstance(value, dict):
        return {
            k: stable(v)
            for k, v in value.items()
            if k not in {"run_id", "duration_seconds"}
        }
    if isinstance(value, list):
        return [stable(v) for v in value]
    if isinstance(value, str):
        try:
            return stable(json.loads(value))
        except (ValueError, TypeError):
            pass
    return value
