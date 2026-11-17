# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated governance inputs and byte-identical native implementations.

No source step is replaced. Every suite subprocess is a real Python validator
or planner, using empty synthetic registries rather than production artifacts.
No model/provider/compiler is required by this fixed suite invocation.
"""

import json
from pathlib import Path
import shutil


def populate(project, root):
    def copy(relative):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / relative, target)
        assert target.read_bytes() == (project / relative).read_bytes()

    def data(relative, payload):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload))

    for folder in ["meta_skills/scripts", "meta_skills/schemas"]:
        for path in (project / folder).glob(
            "*.py" if folder.endswith("scripts") else "*.json"
        ):
            copy(path.relative_to(project))
    for relative in [
        "tests/meta_skills/run_meta_skill_suite.py",
        "scripts/mathformer.py",
        "scripts/workflow_write_audit.py",
        "scripts/mcp_server.py",
        "skills/control/reasoning-log-schema-guardian/scripts/reasoning_log.py",
        "skills/physics-lean/physics-lean-goal-sample-autoformalizer/scripts/plan_goal_sample_autoformalization.py",
    ]:
        copy(relative)
    data(
        "meta_skills/taxonomy/workflow_taxonomy.json",
        {"workflow_coordinates": [], "axes": {}, "navigation_queries": []},
    )
    data(
        "meta_skills/registry/workflow_actions.yaml",
        {"workflow_actions": [], "allowed_mcp_tools": [], "denied_surfaces": []},
    )
    lean = root / "MathformerPhysicsLib/Lean/formalphysics_0014/MathformerPhysics.lean"
    lean.parent.mkdir(parents=True)
    lean.write_text("/- synthetic planner input: never compiled or promoted -/\n")


def reset(root):
    shutil.rmtree(root / "artifacts", ignore_errors=True)


def serve(root):
    """Production tool registrations with a fixture-owned filesystem scope."""
    import os
    import mcp_server

    os.environ.clear()
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    mcp_server._ALLOWED_WRITE_ROOTS = [Path(root).resolve()]
    mcp_server.mcp.run(transport="stdio")
