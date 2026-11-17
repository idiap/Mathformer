# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Small local input tree; every executable is copied byte-for-byte from source.

There is no provider/model dependency in this route. Tests never substitute a
local graph algorithm or install a production mock mode.
"""

from pathlib import Path
import shutil

SCRIPTS = (
    "scripts/render_workflow_graphs.py",
    "scripts/plan_workflow_graph_layout.py",
    "scripts/audit_workflow_skill_integration.py",
    "skills/control/workflow-contract-validator/scripts/validate_skill_hooks.py",
    "skills/control/skill-hook-coverage-maximizer/scripts/audit_skill_hook_coverage.py",
    "skills/control/skill-test-program-orchestrator/scripts/inventory_skills.py",
    "skills/control/reasoning-log-schema-guardian/scripts/reasoning_log.py",
)


def populate(root: Path, source: Path):
    for relative in SCRIPTS:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
    (root / "skills/SKILL_HOOKS.yaml").write_text("""runtime_contract:
  shared_runtime_scripts:
    - skills/runtime/scripts/run.py
hooks:
  - id: input
    owner_skill: first
    trigger: read evidence
    outputs:
      - evidence
loop_contracts:
  - id: fixture_loop
    required_hooks:
      - input
    required_owner_skills:
      - first
      - second
direct_request_routing:
  fixture: route
""")
    for name in ["first", "second", "route", "runtime", "orphan"]:
        path = root / f"skills/fixture/{name}/SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nname: {name}\ndescription: fixture {name}\n---\n")
    hub = root / "docs/architecture/AGENTIC_HUB.md"
    hub.parent.mkdir(parents=True, exist_ok=True)
    hub.write_text("### Fixture Count: `1`\n- [first](fixture): deterministic input\n")


def outputs(root):
    return {
        p.name: p.read_bytes()
        for p in sorted((root / "artifacts/workflow_graphs").glob("*"))
        if p.is_file()
    }


def clear_outputs(root):
    shutil.rmtree(root / "artifacts", ignore_errors=True)
