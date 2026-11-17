# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated inputs for the real coverage CLI, plus finite coverage snapshots.

Implementation files are copied unchanged. No referenced action is executed.
"""

import importlib.util
import shutil

LEAF = "skills/control/mathformer-workflow-router/scripts/route_mathformer_workflow.py"
LOG = "skills/control/reasoning-log-schema-guardian/scripts/reasoning_log.py"


def populate(root, project):
    for relative in [
        "scripts/mathformer.py",
        "scripts/workflow_write_audit.py",
        LEAF,
        LOG,
        "skills/control/mathformer-workflow-router/SKILL.md",
    ]:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / relative, target)


def load_router(project):
    spec = importlib.util.spec_from_file_location(
        "workflow_router_fixture", project / LEAF
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def coverage_snapshot():
    def route(name, actions):
        return {
            "route_id": name,
            "title": name,
            "action_ids": actions,
            "skill_routes": ["fixture-owner"],
            "examples": ["fixture example"],
        }

    return {
        "registry": {
            "a": {"family": "alpha"},
            "b": {"family": "beta"},
            "uncovered": {"family": "gamma"},
        },
        "routes": [
            route("first", ["b", "a", "a", "test:family:delta", "missing"]),
            route("empty", []),
            route("last", ["b"]),
        ],
    }
