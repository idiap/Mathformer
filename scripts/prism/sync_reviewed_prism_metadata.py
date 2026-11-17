#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synchronize generated PRISM metadata around reviewed reasoning sources.

This command never writes ``reasoning.prism`` or canonical Mathformer skills.
Those files are reviewed inputs.  It synchronizes the declarative projection
specification, semantic taxonomies, catalog documentation, generated wrapper
module names, and generated-source hashes with the checked-in project plans.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[2]
COLLECTION = REPOSITORY / "mathformer-prism"
SPEC = Path(__file__).with_name("reviewed_reasoning_projections.json")

ROLE_BY_KIND = {
    "observation": "observation",
    "inventory": "observation",
    "interpretation": "mathematical_representation",
    "model": "mathematical_representation",
    "theory": "mathematical_representation",
    "context": "mathematical_representation",
    "obligation": "proposition",
    "retrieval": "retrieval_result",
    "grounding": "retrieval_result",
    "candidate": "formal_representation",
    "construction": "formal_representation",
    "evidence": "evidence",
    "assessment": "critique",
    "reflection": "critique",
    "plan": "recommendation",
    "decision": "decision",
}


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def taxonomy_description(value: str, subject: str) -> str:
    """Meet the taxonomy prose contract without changing reviewed PRISM types."""
    text = value.strip()
    if len(text) >= 20:
        return text
    stem = text.rstrip(".")
    return f"{stem} retained by the typed {subject} record."


def projection_spec(
    workflow: dict[str, Any], coverage: dict[str, Any]
) -> dict[str, Any]:
    projection = workflow["reasoning_projection"]
    hook_by_step = {
        item["occurrence_id"]: item["hook_id"] for item in coverage["mappings"]
    }
    stages = []
    for occurrence in projection["occurrences"]:
        arguments = occurrence["arguments"]
        direct = len(arguments) == 1 and "field" not in arguments[0]
        stage = {
            "id": occurrence["id"],
            "input_type": None if direct else occurrence["input_type"],
            "material_hooks": [
                hook_by_step[item] for item in occurrence["material_steps"]
            ],
            "method": occurrence["method"],
            "output_type": occurrence["output_type"],
            "rationale": occurrence["rationale"],
            "relation": occurrence.get("relation"),
            "semantic_kind": occurrence["semantic_kind"],
            "sources": [item["source"] for item in arguments],
        }
        stages.append(stage)
    material_type_count = 1 + len(workflow["steps"])
    return {
        "description": projection["description"],
        "input_name": projection["input_name"],
        "name": projection["name"],
        "profile_basis": projection["profile_basis"],
        "scope": projection["projection_scope"],
        "stages": stages,
        "topology": projection["topology"],
        "type_definitions": workflow["_all_type_definitions"][material_type_count:],
    }


def synchronize_taxonomy(
    workflow_id: str,
    plan: dict[str, Any],
    taxonomy: dict[str, Any],
) -> dict[str, Any]:
    workflow = plan["workflows"][0]
    projection = workflow["reasoning_projection"]
    material_by_type = {step["output_type"]: step for step in workflow["steps"]}
    projected_by_type = {
        item["output_type"]: item for item in projection["occurrences"]
    }
    existing_objects = {
        item["nominal_type"]: item for item in taxonomy.get("objects", [])
    }
    objects = []
    for definition in plan["type_definitions"]:
        name = definition["name"]
        old = existing_objects.get(name, {})
        if name == workflow["input"]["type"]:
            role, provenance = "query", "raw"
        elif name in material_by_type:
            step = material_by_type[name]
            role = old.get("epistemic_role", "operational")
            provenance = step["output_provenance"]
        elif name in projected_by_type:
            occurrence = projected_by_type[name]
            role = ROLE_BY_KIND[occurrence["semantic_kind"]]
            provenance = "generated"
        else:
            role, provenance = old.get("epistemic_role", "operational"), "generated"
        objects.append(
            {
                "assurance_justification": old.get(
                    "assurance_justification",
                    "The nominal record retains source identity and does not claim stronger assurance than its producer establishes.",
                ),
                "description": taxonomy_description(
                    definition["description"], definition["name"]
                ),
                "epistemic_role": role,
                "fields": [
                    {
                        **field,
                        "description": taxonomy_description(
                            field["description"], field["name"]
                        ),
                    }
                    for field in definition["fields"]
                ],
                "id": re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_"),
                "nominal_type": name,
                "provenance": provenance,
                "source_anchors": [
                    f"skills/SKILL_HOOKS.yaml#loop_contracts.{workflow_id}"
                ],
                "unresolved": [],
            }
        )
    result = dict(taxonomy)
    result["objects"] = objects
    return result


def rename_reasoning_wrappers(project: Path) -> int:
    materialization = project / "materialization.prism"
    text = materialization.read_text(encoding="utf-8")
    pattern = re.compile(
        r"from generated\.(reasoning_[a-z0-9_]+_\d+_skill) "
        r"import (\w+) as ([a-z0-9_]+)_reasoning_skill_(\d+)$",
        re.MULTILINE,
    )
    renames: list[tuple[Path, Path]] = []

    def replacement(match: re.Match[str]) -> str:
        old_module, export, occurrence, index = match.groups()
        new_module = f"reasoning_{occurrence}_{index}_skill"
        if old_module != new_module:
            old = project / "generated" / f"{old_module}.prism"
            new = project / "generated" / f"{new_module}.prism"
            if new.exists() and new != old:
                raise FileExistsError(f"refusing wrapper collision: {new}")
            renames.append((old, new))
        return (
            f"from generated.{new_module} import {export} as "
            f"{occurrence}_reasoning_skill_{index}"
        )

    updated = pattern.sub(replacement, text)
    for old, new in renames:
        if not old.is_file():
            raise FileNotFoundError(old)
        old.replace(new)
    if updated != text:
        materialization.write_text(updated, encoding="utf-8")
    return len(renames)


def catalog_markdown(catalog: dict[str, Any]) -> str:
    rows = [
        "# Mathformer PRISM workflow catalog",
        "",
        "The 14 public entries are named repository workflows. Skills are internal bindings, never public workflow entrypoints.",
        "Computed occurrences are structural material-binding descriptors; the fake handler does not execute native Mathformer scripts.",
        "",
        "| Workflow | Profile | Material occurrences | Reasoning occurrences | Entrypoint |",
        "|---|---|---:|---:|---|",
    ]
    for entry in catalog["workflows"]:
        rows.append(
            f"| `{entry['id']}` | `{entry['reasoning_profile_basis']}` | "
            f"{entry['occurrence_count']} | {entry['reasoning_occurrence_count']} | "
            f"`{entry['project']}/{entry['entrypoint']}` |"
        )
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    catalog = load(COLLECTION / "workflow_catalog.json")
    specs: dict[str, Any] = {}
    changed: list[str] = []
    wrapper_renames = 0
    for entry in catalog["workflows"]:
        workflow_id = entry["id"]
        project_root = COLLECTION / "projects" / workflow_id
        plan_path = project_root / "conversion" / "workflow-architecture-plan.json"
        taxonomy_path = project_root / "conversion" / "project-semantic-taxonomy.json"
        plan = load(plan_path)
        workflow = plan["workflows"][0]
        workflow["_all_type_definitions"] = plan["type_definitions"]
        coverage = load(project_root / "conversion" / "hook-coverage.json")
        specs[workflow_id] = projection_spec(workflow, coverage)
        workflow.pop("_all_type_definitions")
        taxonomy = synchronize_taxonomy(workflow_id, plan, load(taxonomy_path))
        expected = (
            json.dumps(taxonomy, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        )
        if taxonomy_path.read_text(encoding="utf-8") != expected:
            changed.append(str(taxonomy_path.relative_to(REPOSITORY)))
            if not args.check:
                taxonomy_path.write_text(expected, encoding="utf-8")
        if not args.check:
            wrapper_renames += rename_reasoning_wrappers(project_root / "prism_project")
    spec_document = {
        "artifact": "reviewed-reasoning-projections",
        "schema_version": "1.0",
        "workflows": specs,
    }
    expected_spec = (
        json.dumps(spec_document, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    )
    if not SPEC.exists() or SPEC.read_text(encoding="utf-8") != expected_spec:
        changed.append(str(SPEC.relative_to(REPOSITORY)))
        if not args.check:
            SPEC.write_text(expected_spec, encoding="utf-8")
    markdown_path = COLLECTION / "workflow_catalog.md"
    expected_markdown = catalog_markdown(catalog)
    if markdown_path.read_text(encoding="utf-8") != expected_markdown:
        changed.append(str(markdown_path.relative_to(REPOSITORY)))
        if not args.check:
            markdown_path.write_text(expected_markdown, encoding="utf-8")
    if not args.check:
        for entry in catalog["workflows"]:
            root = COLLECTION / entry["project"]
            generation_path = root.parent / "conversion" / "generation.json"
            generation = load(generation_path)
            generation["source_hashes"] = {
                str(path.relative_to(root)): digest(path)
                for path in sorted(root.rglob("*.prism"))
            }
            dump(generation_path, generation)
    print(
        json.dumps(
            {
                "status": "stale" if args.check and changed else "synchronized",
                "changed": changed,
                "wrapper_renames": wrapper_renames,
            },
            indent=2,
        )
    )
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
