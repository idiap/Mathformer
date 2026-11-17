# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic filesystem inputs for the real, unchanged schema self-test.

This route has no provider/model/compiler call. Its actual validator, renderers
and coverage auditor run on these isolated inputs. External compiler behavior
is covered separately by reasoning_route_compiler, never substituted here.
"""

from pathlib import Path
import shutil

DIRECTORY = Path("skills/control/reasoning-log-schema-guardian/scripts")
SELF_TEST = str(DIRECTORY / "self_test_reasoning_logs.py")
WRAPPER = DIRECTORY / "run_with_reasoning_log.py"


def populate(root, project, *, count=101, known_hook=True, wrapper=True):
    for name in (
        "self_test_reasoning_logs.py",
        "reasoning_log.py",
        "validate_reasoning_log.py",
        "render_reasoning_log.py",
        "render_reasoning_log_html.py",
        "audit_skill_reasoning_log_coverage.py",
    ):
        target = root / DIRECTORY / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / DIRECTORY / name, target)
    # Presence is the real auditor's wrapper criterion; copy unchanged source.
    if wrapper:
        shutil.copyfile(project / WRAPPER, root / WRAPPER)
    else:
        (root / WRAPPER).unlink(missing_ok=True)
    hooks = root / "skills/SKILL_HOOKS.yaml"
    hook = "control.reasoning_log_schema" if known_hook else "fixture.other_hook"
    hooks.write_text(f"hooks:\n  - id: {hook}\n")
    skills = root / "skills/fixture"
    if skills.exists():
        shutil.rmtree(skills)
    for i in range(count):
        path = skills / f"skill-{i:03}" / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nname: skill-{i:03}\n---\nSynthetic coverage input.\n")
    # There is no SKILL.md for the copied implementation, so only synthetic
    # skills count. This script creates a real missing-coverage branch.
    if count:
        scripts = skills / "skill-000/scripts"
        scripts.mkdir()
        (scripts / "plain.py").write_text("# synthetic script; never executed\n")
