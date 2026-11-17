# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synthetic manuscripts/graph with unmodified native paper leaf programs.

There is no provider/compiler call in this route. All recorded validation
commands in evidence packets remain inert strings. Nothing is promoted.
"""

import json
from pathlib import Path
import shutil

EVIDENCE = "paper_skills/framework-repository-cartographer/scripts/build_paper_evidence_packet.py"
PLAN = "paper_skills/scientific-paper-drafter/scripts/plan_paper_update.py"
AUDIT = "paper_skills/paper-claim-evidence-auditor/scripts/audit_paper_claims.py"
CATALOG = "paper_skills/framework-repository-cartographer/scripts/collect_workflow_catalog_for_paper.py"
FRAMEWORK = "paper/MATHFORMER_FRAMEWORK_PAPER.tex"
RFDE = "paper/REFERENCE_FREE_REFINEMENT_DYNAMICS.tex"
OUTPUT = "artifacts/paper_skills"
PACKET = OUTPUT + "/new_functionality_evidence_packet.json"
GRAPH = "artifacts/workflow_graphs/workflow_graphs.json"


def put(root, path, content):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def populate(root: Path, project: Path):
    for path in (EVIDENCE, PLAN, AUDIT, CATALOG):
        put(root, path, (project / path).read_text())
    put(
        root,
        FRAMEWORK,
        "Synthetic inspection evidence: \\repo{fixture/evidence.json}.\n",
    )
    put(
        root,
        RFDE,
        "Synthetic reference-free monitor: \\repo{fixture/trajectory.json}.\n",
    )
    graph = {
        "summary": {
            "stacks": 2,
            "total_hooks": 1,
            "modeled_skills": 1,
            "available_skills": 2,
            "shared_skills": 0,
            "reflective_stacks": 1,
            "families": 2,
        },
        "stacks": {
            "fixture-support": {
                "label": "Fixture & support",
                "family": "Control",
                "ordered_hooks": [],
            },
            "preformalization-readiness-loop": {
                "label": "Synthetic intake",
                "family": "Intake",
                "ordered_hooks": [
                    {
                        "index": 3,
                        "skill": "fixture",
                        "role": "input",
                        "output_type": "candidate",
                    }
                ],
                "reflective_edges": [{"from": "b", "to": "a"}],
            },
        },
    }
    put(root, GRAPH, json.dumps(graph))


def reset_outputs(root):
    shutil.rmtree(root / OUTPUT, ignore_errors=True)


def leaves(result):
    if "argv" in result:
        yield result
    for child in result.get("children", []):
        yield from leaves(child)
    if "leaf" in result:
        yield from leaves(result["leaf"])
