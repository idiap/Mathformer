# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Byte-identical native runners with a finite compiler-fixture input matrix."""

import json
import shutil

NATIVE_FILES = (
    "tests/run_quick.py",
    "tests/test_program/run_comprehensive_tests.py",
    "scripts/workflow_write_audit.py",
)


def populate(root, source):
    for name in NATIVE_FILES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    matrix(root, ["pass"])


def matrix(root, modes, *, selected=True):
    rows = []
    for index, mode in enumerate(modes):
        row = dict(
            id=f"fixture.{index}",
            module_family="control" if selected else "lean",
            command=["fixture-test-runner-compiler", mode],
            owner_skill="skill-test-program-orchestrator",
            hook_id="test.skill_program",
            test_kind="unit",
            risk_level="low",
            fixture_ids=["deterministic-compiler"],
            write_set=["artifacts/"],
        )
        if mode == "timeout":
            row["timeout_seconds"] = 17
        if mode == "skip":
            row["optional_dependency"] = "fixture_unavailable_test_runner_provider"
        rows.append(row)
    path = root / "tests/test_matrix.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 2, "tests": rows}))


def records(path):
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def stable(value):
    """Remove only source clock measurements when comparing independent runs."""
    if isinstance(value, dict):
        return {
            key: stable(item)
            for key, item in value.items()
            if key not in ("duration_seconds", "run_id")
        }
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value
