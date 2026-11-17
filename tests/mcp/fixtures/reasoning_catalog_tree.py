# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated catalogue inputs, using unmodified native renderer and validator.

The two profiles are deterministic synthetic typed reasoning graphs. No native
production catalogue is generated, and no model, prover or credentials are used.
"""

from pathlib import Path

LEAF = "skills/control/reasoning-flow-language/scripts/render_all_reasoning_flows.py"
SEMANTIC = "docs/architecture/ALL_REASONING_FLOWS.md"
MATERIAL = "docs/architecture/REASONING_FLOW_MATERIALIZATIONS.md"
NAMES = (
    "fixture_beta",
    "fixture_alpha",
)  # registry order deliberately differs from glob order
FLOW = """erfl 0.3
reasoning NAME {
  goal "produce a calibrated fixture result" -> status
  steps a:A[gap::Context->candidate::Claim] -assume> d:D[candidate::Claim->claim::Claim] -test> p:P[claim::Claim->evidence::Evidence] -assess> r:R[claim::Claim,evidence::Evidence->assessment::Assessment] -calibrate> e:E[claim::Claim,assessment::Assessment->status::Decision]
  on e.accepted => accept
  on e.blocked => stop
}
"""


def put(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def populate(root: Path, project: Path):
    for relative in [
        LEAF,
        LEAF.replace("render_all_reasoning_flows", "validate_reasoning_flow"),
        "skills/control/reasoning-flow-language/references/erfl-0.3.json",
        "skills/OUTPUT_TYPES.yaml",
    ]:
        put(root, relative, (project / relative).read_text())
    # Keep the actual primitive ontology, replacing only the profile collection.
    reasoning = (
        (project / "skills/REASONING_TYPES.yaml")
        .read_text()
        .split("\nreasoning_styles:\n")[0]
    )
    reasoning += "\nreasoning_styles:\n"
    for name in NAMES:
        reasoning += f"""  - id: {name}
    goal: A synthetic calibrated result
    control_skills:
      - fixture-control-skill
    stages:
      - primitive: deduction
        skill_options:
          - fixture-deduction-skill
"""
        put(root, f"examples/reasoning_flows/{name}.rflow", FLOW.replace("NAME", name))
    put(root, "skills/REASONING_TYPES.yaml", reasoning)
    put(
        root,
        "skills/SKILL_HOOKS.yaml",
        """loop_contracts:
  - id: fixture_operational_loop
    description: Synthetic materialization affinity
    required_hooks:
      - fixture-hook
    required_owner_skills:
      - fixture-control-skill
""",
    )
    put(
        root,
        "scripts/mathformer.py",
        'action("fixture:catalogue", "synthetic action identifier")\n',
    )
