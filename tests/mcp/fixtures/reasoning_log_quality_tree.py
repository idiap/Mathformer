# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated native auditor sources and deterministic log inputs.

There is no provider/compiler in this route. Real auditor code runs against
these temporary trees; external compiler checks use reasoning_route_compiler.
"""

import importlib.util
from pathlib import Path
import shutil

DIRECTORY = Path("skills/control/reasoning-log-schema-guardian/scripts")
AUDITOR = str(DIRECTORY / "audit_reasoning_log_quality.py")
FIXTURES = Path("artifacts/reasoning/self_test")


def populate(root, source):
    for name in (
        "audit_reasoning_log_quality.py",
        "validate_reasoning_log.py",
        "reasoning_log.py",
    ):
        target = root / DIRECTORY / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / DIRECTORY / name, target)
    schema = Path("skills/control/reasoning-log-schema-guardian/references/schema.md")
    (root / schema).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / schema, root / schema)
    # Minimal source-format hook declaration, containing no credentials.
    (root / "skills/SKILL_HOOKS.yaml").write_text(
        "hooks:\n  - id: control.reasoning_log_schema\n"
    )


def auditor(root):
    spec = importlib.util.spec_from_file_location(
        "_isolated_quality_auditor", root / AUDITOR
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def events(count=2):
    # Reuse deterministic transport fields; include the native required payload.
    from reasoning_log_html_tree import events as log_events

    rows = log_events(count)
    for row in rows:
        row["payload"]["skill"] = row["payload"]["skill_application"]["skill"]
    return rows
