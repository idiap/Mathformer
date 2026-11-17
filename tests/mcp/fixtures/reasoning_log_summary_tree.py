# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synthetic inputs and isolated real summary sources; no provider substitution.

The route has no model or compiler. Generic external compiler boundary checks
reuse reasoning_route_compiler; the summarizer is always real source code.
"""

import importlib.util
import json
from pathlib import Path
import shutil
import sys

from reasoning_log_quality_tree import events as quality_events

DIRECTORY = Path("skills/control/reasoning-log-schema-guardian/scripts")
SUMMARIZER = str(DIRECTORY / "summarize_reasoning_log.py")
LOGS = [
    Path("artifacts/reasoning/self_test/good.jsonl"),
    Path(
        "artifacts/physics_sympy/recursive_goal_runs/formalphysics_0000/reasoning.jsonl"
    ),
    Path("artifacts/wiki_level_suite/reasoning.jsonl"),
]
FIXTURES = LOGS[0].parent


def populate(root, source):
    for name in (
        "summarize_reasoning_log.py",
        "render_reasoning_log.py",
        "validate_reasoning_log.py",
        "audit_reasoning_log_quality.py",
        "reasoning_log.py",
    ):
        target = root / DIRECTORY / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / DIRECTORY / name, target)
    (root / "skills/SKILL_HOOKS.yaml").write_text(
        "hooks:\n  - id: control.reasoning_log_schema\n"
    )


def events(count=2):
    rows = quality_events(count)
    for row in rows:
        row["payload"]["skill_application"].update(
            hook_id="control.reasoning_log_schema", run_id="fixture-run"
        )
    return rows


def write_log(root, rows=None, index=0):
    target = root / LOGS[index]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "".join(json.dumps(row) + "\n" for row in (events() if rows is None else rows))
    )
    return target


def summarizer(root):
    # Load copied dependencies in one isolated import scope. Keep references in
    # the returned module and restore the process's existing imports afterward.
    names = (
        "audit_reasoning_log_quality",
        "render_reasoning_log",
        "validate_reasoning_log",
        "reasoning_log",
    )
    saved = {name: sys.modules.pop(name, None) for name in names}
    old_path = sys.path[:]
    sys.path.insert(0, str(root / DIRECTORY))
    try:
        spec = importlib.util.spec_from_file_location(
            "_isolated_summary", root / SUMMARIZER
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = old_path
        for name, value in saved.items():
            sys.modules.pop(name, None)
            if value is not None:
                sys.modules[name] = value
