# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synthetic repository inputs; the auditor executable is unchanged source.

There is no model/provider/compiler in this route. The separate generic leaf
compiler fixture is used only to verify native capture and write-audit errors.
"""

import importlib.util

AUDITOR = "skills/control/reasoning-log-schema-guardian/scripts/audit_skill_reasoning_log_coverage.py"
WRAPPER = (
    "skills/control/reasoning-log-schema-guardian/scripts/run_with_reasoning_log.py"
)


def load_auditor(project):
    spec = importlib.util.spec_from_file_location(
        "coverage_fixture_auditor", project / AUDITOR
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def populate(root, project, *, wrapper=True, count=4, scripts=3):
    def write(relative, text):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    write(AUDITOR, (project / AUDITOR).read_text())
    if wrapper:
        write(WRAPPER, "# fixture presence only; never executed\n")
    write(
        "skills/SKILL_HOOKS.yaml",
        """runtime_contract:
  shared_runtime_scripts:
    - skills/fixture/skill-00/scripts/00.py
    - skills/fixture/skill-00/scripts/00.py
hooks:
  - id: fixture.hook
    owner_skill: hook-only
""",
    )
    for i in range(count):
        prefix = f"skills/fixture/skill-{i:02}"
        write(prefix + "/SKILL.md", f"---\nname: skill-{i:02}\n---\nFixture\n")
        for j in range(scripts):
            write(
                prefix + f"/scripts/{j:02}.py",
                "# append_skill_start\n" if j % 2 == 0 else "# plain\n",
            )
        # Both native globs are immediate, not recursive.
        write(prefix + "/scripts/nested/ignored.py", "# ignored\n")
    write("skills/fixture/hook-only/SKILL.md", "---\nname: hook-only\n---\n")
    write("skills/fixture/agent-only/SKILL.md", "---\nname: agent-only\n---\n")
    write("skills/fixture/agent-only/agents/agent.yaml", "name: fixture\n")
    write("skills/fixture/fallback/SKILL.md", "No frontmatter\n")
    write("skills/too/deep/ignored/SKILL.md", "Ignored depth\n")
    return load_auditor(project).audit(root / "skills", root)
