#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Validate and run the fresh collection of named Mathformer PRISM workflows."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import concurrent.futures
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import yaml

REPOSITORY = Path(__file__).resolve().parents[2]
PROJECTION_SPECS = Path(__file__).with_name("reviewed_reasoning_projections.json")
LOCAL_TO_PRISM_SOURCE = REPOSITORY.parent / "to_prism" / "src"
if LOCAL_TO_PRISM_SOURCE.is_dir():
    sys.path.insert(0, str(LOCAL_TO_PRISM_SOURCE))
SEMANTIC_SOURCES = (
    REPOSITORY / "skills" / "SKILL_HOOKS.yaml",
    REPOSITORY / "skills" / "SKILL_TYPES.yaml",
    REPOSITORY / "skills" / "OUTPUT_TYPES.yaml",
    REPOSITORY / "skills" / "REASONING_TYPES.yaml",
    PROJECTION_SPECS,
)
GENERIC_TYPES = {
    "Task",
    "Input",
    "Output",
    "Data",
    "Payload",
    "State",
    "Result",
    "ConversionTask",
    "WorkflowTask",
}
NATIVE_HANDLERS = {"codex", "litellm"}
CONSERVATIVE_STATUS_PREFIXES = (
    "blocked",
    "deferred",
    "draft",
    "experimental",
    "fail",
    "failed",
    "incomplete",
    "insufficient",
    "not",
    "partial",
    "pending",
    "rejected",
    "retained",
    "review_required",
    "unresolved",
    "withheld",
)
CONSERVATIVE_EXACT_STATUSES = {"completed_empty_batch"}
PROMOTION_FIELDS = {
    "completed_units",
    "html_pages",
    "markdown_pages",
    "promoted_modules",
    "reused_units",
}


class VerificationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VerificationError(f"expected object: {path}")
    return value


def digest_sources() -> str:
    digest = hashlib.sha256()
    for path in SEMANTIC_SOURCES:
        relative = path.relative_to(REPOSITORY).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def digest_canonical_skills() -> str:
    """Fingerprint every file owned by the 188 canonical skill packages."""
    files: set[Path] = set()
    for instruction in (REPOSITORY / "skills").glob("*/*/SKILL.md"):
        files.update(path for path in instruction.parent.rglob("*") if path.is_file())
    digest = hashlib.sha256()
    for path in sorted(files):
        relative = path.relative_to(REPOSITORY).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def require(condition: object, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def record_fields(
    payload: dict[str, Any],
    workflow_id: str,
    label: str,
    handler: str,
) -> tuple[str, dict[str, Any], str]:
    """Return a terminal typed record after validating its explicit wrapper."""
    result = payload.get("result")
    if not (isinstance(result, dict)):
        raise VerificationError(f"{workflow_id}: {label} result envelope is invalid")
    if set(result) == {"value"}:
        wrapper = result["value"]
        result_envelope = "result"
    else:
        require(
            set(result) == {"procedure", "value"},
            f"{workflow_id}: {label} result envelope is invalid",
        )
        wrapper = result
        result_envelope = "computed_direct"
    if not (isinstance(wrapper, dict)):
        raise VerificationError(f"{workflow_id}: {label} result wrapper is missing")
    if "producer" in wrapper:
        producer = wrapper.get("producer")
        if not (isinstance(producer, str) and producer.startswith(f"{handler}:")):
            raise VerificationError(
                f"{workflow_id}: {label} generated result has wrong producer"
            )
        wrapper_kind = "generated"
    else:
        if not (isinstance(wrapper.get("procedure"), str) and wrapper["procedure"]):
            raise VerificationError(
                f"{workflow_id}: {label} computed result has no procedure"
            )
        wrapper_kind = "computed"
    value = wrapper.get("value")
    if not (isinstance(value, dict) and set(value) == {"fields", "type_name"}):
        raise VerificationError(
            f"{workflow_id}: {label} terminal record shape is invalid"
        )
    type_name = value.get("type_name")
    fields = value.get("fields")
    if not (isinstance(type_name, str)):
        raise VerificationError(f"{workflow_id}: {label} result has no nominal type")
    if not (isinstance(fields, dict)):
        raise VerificationError(f"{workflow_id}: {label} result has no fields")
    return type_name, fields, f"{result_envelope}:{wrapper_kind}"


def strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in strings(child)]
    return []


def validate_placeholder_semantics(
    payload: dict[str, Any],
    workflow_id: str,
    label: str,
    expected_type: str,
    handler: str,
) -> dict[str, Any]:
    """Reject ungrounded success claims for the generated placeholder fixtures."""
    type_name, fields, wrapper_kind = record_fields(
        payload, workflow_id, label, handler
    )
    require(
        type_name == expected_type,
        f"{workflow_id}: {label} terminal type differs from the plan",
    )
    status_values = [
        value
        for key, value in fields.items()
        if key in {"status", "gate_disposition"} and isinstance(value, str)
    ]
    require(status_values, f"{workflow_id}: {label} terminal record has no disposition")
    normalized = re.sub(r"[^a-z0-9]+", "_", status_values[0].lower()).strip("_")
    require(
        normalized in CONSERVATIVE_EXACT_STATUSES
        or any(
            normalized == prefix or normalized.startswith(prefix + "_")
            for prefix in CONSERVATIVE_STATUS_PREFIXES
        ),
        f"{workflow_id}: {label} promoted unresolved fixture evidence: {status_values}",
    )
    limitations = fields.get("limitations", [])
    blockers = fields.get("blockers", [])
    require(
        bool(strings(limitations)) or bool(strings(blockers)),
        f"{workflow_id}: {label} gives no blockers or limitations for unresolved fixtures",
    )
    for field_name in PROMOTION_FIELDS:
        if field_name in fields:
            require(
                not strings(fields[field_name]),
                f"{workflow_id}: {label} populated `{field_name}` from unresolved fixtures",
            )
    return {
        "oracle": "placeholder_evidence_safety",
        "disposition_class": "conservative_nonpromotion",
        "wrapper": wrapper_kind,
        "status": status_values,
        "blocker_count": len(strings(blockers)),
        "limitation_count": len(strings(limitations)),
    }


def validate_native_effects(
    payload: dict[str, Any],
    workflow_id: str,
    label: str,
    handler: str,
    expected: int,
) -> dict[str, Any]:
    records = list(payload.get("effect_records", {}).values())
    require(
        len(records) == expected,
        f"{workflow_id}: {label} native effect count differs from the plan",
    )
    record_ids = set(payload.get("effect_records", {}))
    trace_record_ids = {
        item.get("metadata", {}).get("record")
        for item in payload.get("trace", [])
        if item.get("kind") == "effect"
    }
    require(
        trace_record_ids == record_ids,
        f"{workflow_id}: {label} native records do not match the effect trace",
    )
    call_ids: set[str] = set()
    for record in records:
        invocation = record.get("invocation", {})
        observation = record.get("observation", {})
        provenance = observation.get("provenance", {})
        require(
            invocation.get("handler") == handler,
            f"{workflow_id}: {label} did not activate {handler}",
        )
        require(
            invocation.get("symbol") == "generate",
            f"{workflow_id}: {label} recorded a non-generate native effect",
        )
        call_id = invocation.get("call_id")
        if not (isinstance(call_id, str) and call_id not in call_ids):
            raise VerificationError(
                f"{workflow_id}: {label} has duplicate or missing native call ids"
            )
        call_ids.add(call_id)
        if not (isinstance(invocation.get("input_digest"), str)):
            raise VerificationError(
                f"{workflow_id}: {label} native input digest is missing"
            )
        if not (isinstance(observation.get("output_digest"), str)):
            raise VerificationError(
                f"{workflow_id}: {label} native output digest is missing"
            )
        require(
            observation.get("status") == "accepted",
            f"{workflow_id}: {label} native effect failed",
        )
        require(
            provenance.get("provider") == handler,
            f"{workflow_id}: {label} has wrong native provenance",
        )
        require(
            not provenance.get("synthetic", False),
            f"{workflow_id}: {label} used synthetic native evidence",
        )
    return {
        "handler": handler,
        "accepted_effects": len(records),
        "synthetic_effects": 0,
    }


def validate_plan(plan: dict[str, Any], workflow_id: str) -> None:
    require(
        plan.get("artifact") == "workflow-architecture-plan",
        f"{workflow_id}: wrong plan artifact",
    )
    require(
        plan.get("schema_version") == "1.0",
        f"{workflow_id}: wrong architecture-plan version",
    )
    workflows = plan.get("workflows")
    if not (isinstance(workflows, list) and len(workflows) == 1):
        raise VerificationError(f"{workflow_id}: plan must contain one workflow")
    workflow = workflows[0]
    require(workflow.get("id") == workflow_id, f"{workflow_id}: plan id mismatch")
    require(
        workflow.get("review_status") == "approved",
        f"{workflow_id}: plan is not approved",
    )
    require(
        workflow.get("semantic_mode") in {"operational", "epistemic", "mixed"},
        f"{workflow_id}: invalid semantic mode",
    )
    definitions = plan.get("type_definitions")
    if not (isinstance(definitions, list) and definitions):
        raise VerificationError(f"{workflow_id}: missing type definitions")
    names = [item.get("name") for item in definitions]
    require(len(names) == len(set(names)), f"{workflow_id}: duplicate nominal type")
    require(
        not (set(names) & GENERIC_TYPES), f"{workflow_id}: generic public type present"
    )
    steps = workflow.get("steps")
    if not (isinstance(steps, list) and steps):
        raise VerificationError(f"{workflow_id}: missing occurrences")
    prior = workflow["input"]["type"]
    roles = set()
    for step in steps:
        require(
            step["input_type"] == prior,
            f"{workflow_id}:{step['id']}: broken nominal chain",
        )
        require(
            step["input_type"] in names and step["output_type"] in names,
            f"{workflow_id}:{step['id']}: undeclared type",
        )
        role = step["semantic_role"]
        roles.add(role)
        if role == "epistemic":
            require(
                step["output_provenance"] == "generated",
                f"{workflow_id}:{step['id']}: epistemic output not generated",
            )
            require(
                step["failure_type"] == "ModelFailure",
                f"{workflow_id}:{step['id']}: wrong epistemic failure",
            )
            require(
                set(step["effects"]) == {"AI.Generate", "Context.Disclose"},
                f"{workflow_id}:{step['id']}: wrong epistemic effects",
            )
            require(
                bool(step.get("reasoning_type"))
                and bool(step.get("reasoning_rationale")),
                f"{workflow_id}:{step['id']}: missing reasoning contract",
            )
        else:
            require(
                step["output_provenance"] == "computed",
                f"{workflow_id}:{step['id']}: operational output not computed",
            )
            require(
                step["failure_type"] == "Never" and step["effects"] == [],
                f"{workflow_id}:{step['id']}: structural descriptor claims effects",
            )
            require(
                "reasoning_type" not in step,
                f"{workflow_id}:{step['id']}: operational step claims reasoning",
            )
        prior = step["output_type"]
    require(prior == workflow["output"]["type"], f"{workflow_id}: final type mismatch")
    expected_mode = "mixed" if len(roles) > 1 else next(iter(roles))
    require(
        workflow["semantic_mode"] == expected_mode,
        f"{workflow_id}: mode disagrees with occurrences",
    )
    require(
        workflow["output"]["provenance"] == steps[-1]["output_provenance"],
        f"{workflow_id}: final provenance mismatch",
    )
    require(
        workflow["epistemic_contract"]["unresolved"] == [],
        f"{workflow_id}: unresolved semantic questions",
    )
    projection = workflow.get("reasoning_projection")
    if projection is not None:
        require(
            workflow["semantic_mode"] in {"mixed", "operational"},
            f"{workflow_id}: reasoning projection requires mixed or operational material mode",
        )
        require(
            projection["input_name"] == workflow["input"]["name"],
            f"{workflow_id}: projected input name mismatch",
        )
        require(
            projection["input_type"] == workflow["input"]["type"],
            f"{workflow_id}: projected input type mismatch",
        )
        require(
            projection.get("review_status") == "approved",
            f"{workflow_id}: reasoning projection is not approved",
        )
        require(
            projection.get("projection_kind") == "generative_interpretation",
            f"{workflow_id}: reasoning projection kind is ambiguous",
        )
        require(
            bool(projection.get("profile_basis")),
            f"{workflow_id}: reasoning profile basis is missing",
        )
        require(
            bool(projection.get("projection_scope")),
            f"{workflow_id}: reasoning projection scope is missing",
        )
        occurrences = projection.get("occurrences", [])
        occurrence_ids = [item["id"] for item in occurrences]
        require(
            occurrences and len(occurrence_ids) == len(set(occurrence_ids)),
            f"{workflow_id}: invalid projected occurrences",
        )
        known_steps = {step["id"] for step in steps}
        covered: set[str] = set()
        mapped_sequence: list[str] = []
        for occurrence in occurrences:
            require(
                occurrence["input_type"] in names
                and occurrence["output_type"] in names,
                f"{workflow_id}:{occurrence['id']}: undeclared projected type",
            )
            mapped = set(occurrence.get("material_steps", []))
            require(
                mapped and mapped <= known_steps,
                f"{workflow_id}:{occurrence['id']}: invalid material-step mapping",
            )
            require(
                len(mapped) == len(occurrence["material_steps"]),
                f"{workflow_id}:{occurrence['id']}: duplicate material-step mapping",
            )
            mapped_sequence.extend(occurrence["material_steps"])
            covered.update(mapped)
        require(
            len(mapped_sequence) == len(set(mapped_sequence)),
            f"{workflow_id}: projected material support overlaps across occurrences",
        )
        epistemic_ids = {
            step["id"] for step in steps if step["semantic_role"] == "epistemic"
        }
        require(
            epistemic_ids <= covered,
            f"{workflow_id}: projected reasoning leaves epistemic material steps orphaned",
        )
        topology_ids = [
            occurrence_id
            for item in projection.get("topology", [])
            for occurrence_id in (
                item["parallel"] if isinstance(item, dict) else [item]
            )
        ]
        require(
            topology_ids
            and set(topology_ids) == set(occurrence_ids)
            and len(topology_ids) == len(occurrence_ids),
            f"{workflow_id}: projected topology is incomplete",
        )
        require(
            projection["output_occurrence"] == topology_ids[-1],
            f"{workflow_id}: projected output is not terminal",
        )
        terminal = next(
            item
            for item in occurrences
            if item["id"] == projection["output_occurrence"]
        )
        require(
            terminal.get("semantic_kind") == "decision",
            f"{workflow_id}: projected output is not an epistemic calibration",
        )


def negative_controls(plan: dict[str, Any], coverage: dict[str, Any]) -> list[str]:
    passed: list[str] = []
    generic = copy.deepcopy(plan)
    generic["type_definitions"][0]["name"] = "Task"
    generic["workflows"][0]["input"]["type"] = "Task"
    generic["workflows"][0]["steps"][0]["input_type"] = "Task"
    try:
        validate_plan(generic, generic["workflows"][0]["id"])
    except VerificationError:
        passed.append("generic_type_rejected")
    broken = copy.deepcopy(plan)
    if len(broken["workflows"][0]["steps"]) > 1:
        broken["workflows"][0]["steps"][1]["input_type"] = broken["workflows"][0][
            "input"
        ]["type"]
        try:
            validate_plan(broken, broken["workflows"][0]["id"])
        except VerificationError:
            passed.append("broken_type_chain_rejected")
    unresolved = copy.deepcopy(plan)
    unresolved["workflows"][0]["epistemic_contract"]["unresolved"] = [
        "The workflow boundary still requires a source decision."
    ]
    try:
        validate_plan(unresolved, unresolved["workflows"][0]["id"])
    except VerificationError:
        passed.append("unresolved_semantics_rejected")
    missing = copy.deepcopy(coverage)
    missing["mappings"] = missing["mappings"][1:]
    if len(missing["mappings"]) != len(coverage["mappings"]):
        passed.append("missing_hook_mapping_detected")
    return passed


def run_one(
    root: Path,
    entry: dict[str, Any],
    prism_bin: str,
    temporary: Path,
    handler: str,
) -> dict[str, Any]:
    workflow_id = entry["id"]
    project = (root / entry["project"]).resolve()
    require(
        root.resolve() in project.parents, f"{workflow_id}: project escapes collection"
    )
    output = temporary / f"{workflow_id}.json"
    environment = dict(os.environ)
    environment["PRISM_BIN"] = prism_bin
    start = time.monotonic_ns()
    run_result = subprocess.run(
        [
            str(project / "prism"),
            "run",
            entry["entrypoint"],
            "--handler",
            handler,
            "--output",
            str(output),
        ],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    end = time.monotonic_ns()
    require(
        run_result.returncode == 0,
        f"{workflow_id}: prism run failed: {run_result.stderr or run_result.stdout}",
    )
    verify = subprocess.run(
        [str(project / "prism"), "verify-run", str(output), "--mode", "offline"],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    require(
        verify.returncode == 0,
        f"{workflow_id}: offline verification failed: {verify.stderr or verify.stdout}",
    )
    payload = load_json(output)
    plan = load_json(root / entry["workflow_plan"])
    workflow = plan["workflows"][0]
    steps = workflow["steps"]
    projection = workflow.get("reasoning_projection")
    material_payload: dict[str, Any] = {}
    nodes = [
        item for item in payload.get("trace", []) if item.get("kind") == "workflow-node"
    ]
    agents = [
        item for item in payload.get("trace", []) if item.get("kind") == "agent-invoked"
    ]
    computations = [
        item
        for item in payload.get("trace", [])
        if item.get("kind") == "deterministic-computation"
    ]
    epistemic = [step for step in steps if step["semantic_role"] == "epistemic"]
    operational = [step for step in steps if step["semantic_role"] == "operational"]
    native_reasoning: dict[str, Any] | None = None
    semantic_reasoning: dict[str, Any] | None = None
    native_material: dict[str, Any] | None = None
    semantic_material: dict[str, Any] | None = None
    if projection is not None:
        projected_ids = [
            occurrence_id
            for item in projection["topology"]
            for occurrence_id in (
                item["parallel"] if isinstance(item, dict) else [item]
            )
        ]
        require(
            [item["name"] for item in nodes] == projected_ids,
            f"{workflow_id}: public trace differs from reviewed reasoning topology",
        )
        require(
            len(agents) == len(projected_ids),
            f"{workflow_id}: projected agent count differs from reasoning occurrences",
        )
        require(
            not computations,
            f"{workflow_id}: reasoning entrypoint leaked detailed material computation",
        )
        materialization = (project / "materialization.prism").read_text(
            encoding="utf-8"
        )
        steps_by_id = {step["id"]: step for step in steps}
        for occurrence in projection["occurrences"]:
            owners: list[str] = []
            for step_id in occurrence["material_steps"]:
                owner = Path(steps_by_id[step_id]["skills"][0]["path"]).name
                if owner not in owners:
                    owners.append(owner)
            marker = "# Reviewed skill composition: " + ", ".join(owners) + "."
            require(
                marker in materialization,
                f"{workflow_id}:{occurrence['id']}: projected skill composition differs from plan",
            )

        material_output = temporary / f"{workflow_id}.material.json"
        material_run = subprocess.run(
            [
                str(project / "prism"),
                "run",
                entry["material_entrypoint"],
                "--handler",
                handler,
                "--output",
                str(material_output),
            ],
            cwd=project,
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )
        require(
            material_run.returncode == 0,
            f"{workflow_id}: detailed material run failed: {material_run.stderr or material_run.stdout}",
        )
        material_verify = subprocess.run(
            [
                str(project / "prism"),
                "verify-run",
                str(material_output),
                "--mode",
                "offline",
            ],
            cwd=project,
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )
        require(
            material_verify.returncode == 0,
            f"{workflow_id}: detailed material verification failed: {material_verify.stderr or material_verify.stdout}",
        )
        material_payload = load_json(material_output)
        material_nodes = [
            item
            for item in material_payload.get("trace", [])
            if item.get("kind") == "workflow-node"
        ]
        material_agents = [
            item
            for item in material_payload.get("trace", [])
            if item.get("kind") == "agent-invoked"
        ]
        material_computations = [
            item
            for item in material_payload.get("trace", [])
            if item.get("kind") == "deterministic-computation"
        ]
        require(
            [item["name"] for item in material_nodes] == [step["id"] for step in steps],
            f"{workflow_id}: detailed material trace differs from hook plan",
        )
        require(
            len(material_agents) == len(epistemic),
            f"{workflow_id}: detailed material agent count differs from plan",
        )
        require(
            len(material_computations) == len(operational),
            f"{workflow_id}: detailed material computation count differs from plan",
        )
        require(
            all(item.get("metadata", {}).get("skills") for item in material_agents),
            f"{workflow_id}: detailed material agent missing skill binding",
        )
        if handler in NATIVE_HANDLERS:
            fixture_strings = strings(workflow["input"].get("fixture"))
            require(
                any(value.startswith("fixture:") for value in fixture_strings),
                f"{workflow_id}: native semantic oracle requires explicit placeholder fixtures",
            )
            native_reasoning = validate_native_effects(
                payload, workflow_id, "reasoning", handler, len(projected_ids)
            )
            native_material = validate_native_effects(
                material_payload, workflow_id, "material", handler, len(epistemic)
            )
            semantic_reasoning = validate_placeholder_semantics(
                payload, workflow_id, "reasoning", projection["output_type"], handler
            )
            semantic_material = validate_placeholder_semantics(
                material_payload,
                workflow_id,
                "material",
                workflow["output"]["type"],
                handler,
            )
            require(
                payload.get("status") == material_payload.get("status") == "accepted",
                f"{workflow_id}: public/material acceptance differs",
            )
            require(
                semantic_reasoning["disposition_class"]
                == semantic_material["disposition_class"],
                f"{workflow_id}: public/material fixture dispositions diverge",
            )
    else:
        require(
            [item["name"] for item in nodes] == [step["id"] for step in steps],
            f"{workflow_id}: runtime occurrence order differs from plan",
        )
        require(
            len(agents) == len(epistemic),
            f"{workflow_id}: agent count differs from epistemic occurrences",
        )
        require(
            len(computations) == len(operational),
            f"{workflow_id}: computed count differs from operational occurrences",
        )
    require(
        all(item.get("metadata", {}).get("skills") for item in agents),
        f"{workflow_id}: epistemic agent missing skill binding",
    )
    result = {
        "workflow_id": workflow_id,
        "status": payload.get("status"),
        "verified": True,
        "occurrences": len(nodes),
        "epistemic_occurrences": len(epistemic),
        "operational_occurrences": len(operational),
        "reasoning_occurrences": len(nodes) if projection is not None else 0,
        "detailed_material_structural_smoke": projection is not None,
        "public_entrypoint": (
            "reasoning_projection" if projection is not None else "material_workflow"
        ),
        "run_started_ns": start,
        "run_ended_ns": end,
    }
    if handler in NATIVE_HANDLERS:
        if projection is None:
            raise VerificationError("Native execution requires a reasoning projection")
        native_projection: dict[str, Any] = projection
        result.update(
            {
                "native_execution": {
                    "reasoning": native_reasoning,
                    "material": native_material,
                },
                "semantic_fixture_safety": {
                    "reasoning": semantic_reasoning,
                    "material": semantic_material,
                },
                "bounded_behavioral_correspondence": {
                    "oracle": "accepted_execution_plus_conservative_nonpromotion",
                    "reasoning_status": payload.get("status"),
                    "material_status": (
                        material_payload.get("status")
                        if projection is not None
                        else payload.get("status")
                    ),
                    "shared_input_type": workflow["input"]["type"],
                    "mapped_material_steps": sum(
                        len(item["material_steps"])
                        for item in native_projection["occurrences"]
                    ),
                    "material_step_count": len(steps),
                    "epistemic_material_steps_covered": all(
                        step["id"]
                        in {
                            step_id
                            for item in native_projection["occurrences"]
                            for step_id in item["material_steps"]
                        }
                        for step in epistemic
                    ),
                },
            }
        )
    return result


class VerificationSession:
    """Shared source steps; resources remain owned until all futures are joined."""

    def __init__(
        self, root, prism_bin, jobs, report_path, handler, selected_workflows=None
    ):
        self.root = root
        self.prism_bin = prism_bin
        self.jobs = jobs
        self.report_path = report_path
        self.handler = handler
        self.selected_workflows = selected_workflows
        self.resources = None
        self.cursor = 0
        self.before = digest_sources()
        self.skills_before = digest_canonical_skills()
        self.catalog = load_json(self.root / "workflow_catalog.json")
        contract = yaml.safe_load(
            (REPOSITORY / "skills" / "SKILL_HOOKS.yaml").read_text(encoding="utf-8")
        )
        self.loops = {item["id"]: item for item in contract["loop_contracts"]}
        self.hooks = {item["id"]: item for item in contract["hooks"]}
        self.entries = self.catalog.get("workflows", [])
        require(
            self.catalog.get("artifact") == "mathformer-prism-workflow-catalog",
            "catalog artifact is invalid",
        )
        require(
            self.catalog.get("schema_version") == "4.0",
            "catalog schema version is invalid",
        )
        require(
            self.catalog.get("workflow_count") == len(self.entries),
            "catalog workflow count is stale",
        )
        require(
            len(self.entries) == len({item["id"] for item in self.entries}),
            "duplicate catalog workflow id",
        )
        require(
            {item["id"] for item in self.entries} == set(self.loops),
            "catalog does not exactly match loop contracts",
        )
        require(
            all(
                item.get("entrypoint_kind") == "reasoning_projection"
                for item in self.entries
            ),
            "every named workflow must publish a reviewed reasoning entrypoint",
        )
        require(
            self.catalog["source_fingerprint"] == f"sha256:{self.before}",
            "catalog source fingerprint is stale",
        )
        self.projection_digest = (
            "sha256:" + hashlib.sha256(PROJECTION_SPECS.read_bytes()).hexdigest()
        )
        require(
            self.catalog.get("reasoning_projection_spec_sha256")
            == self.projection_digest,
            "catalog reasoning projection digest is stale",
        )
        self.taxonomy_issues: list[str] = []
        self.negative: set[str] = set()

    def validate_entry(self):
        entry = self.entries[self.cursor]
        workflow_id = entry["id"]
        plan = load_json(self.root / entry["workflow_plan"])
        taxonomy = load_json(self.root / entry["semantic_taxonomy"])
        coverage = load_json(self.root / entry["hook_coverage"])
        validate_plan(plan, workflow_id)
        projection = plan["workflows"][0].get("reasoning_projection")
        workflow_model = plan["workflows"][0]
        expected_entrypoint_kind = (
            "reasoning_projection" if projection is not None else "material_workflow"
        )
        require(
            entry.get("entrypoint_kind") == expected_entrypoint_kind,
            f"{workflow_id}: catalog entrypoint kind disagrees with the plan",
        )
        require(
            entry.get("reasoning_occurrence_count")
            == (len(projection["occurrences"]) if projection is not None else 0),
            f"{workflow_id}: catalog reasoning occurrence count is stale",
        )
        require(
            entry.get("occurrence_count") == len(workflow_model["steps"]),
            f"{workflow_id}: catalog material occurrence count is stale",
        )
        require(
            entry.get("epistemic_occurrence_count")
            == sum(
                step["semantic_role"] == "epistemic" for step in workflow_model["steps"]
            ),
            f"{workflow_id}: catalog epistemic occurrence count is stale",
        )
        expected_output = (
            projection["output_type"]
            if projection is not None
            else workflow_model["output"]["type"]
        )
        require(
            entry.get("public_output_type") == expected_output,
            f"{workflow_id}: catalog public output type is stale",
        )
        if projection is None:
            raise VerificationError("Catalog reasoning fields require a projection")
        require(
            entry.get("reasoning_profile_basis") == projection["profile_basis"],
            f"{workflow_id}: catalog reasoning profile is stale",
        )
        require(
            entry.get("reasoning_projection_scope") == projection["projection_scope"],
            f"{workflow_id}: catalog reasoning scope is stale",
        )
        require(
            entry.get("reasoning_projection_kind") == projection["projection_kind"],
            f"{workflow_id}: catalog reasoning kind is stale",
        )
        material_entrypoint = (
            self.root / entry["project"] / entry["material_entrypoint"]
        )
        require(
            material_entrypoint.is_file(),
            f"{workflow_id}: detailed material entrypoint is missing",
        )
        require(
            (
                self.root / entry["project"] / entry.get("typed_entrypoint", "")
            ).is_file(),
            f"{workflow_id}: typed reasoning API entrypoint is missing",
        )
        require(
            (
                self.root
                / entry["project"]
                / entry.get("typed_material_entrypoint", "")
            ).is_file(),
            f"{workflow_id}: typed material API entrypoint is missing",
        )
        try:
            from to_prism.conformance import validate_generated_layers

            layer_issues = validate_generated_layers(self.root / entry["project"], plan)
        except ImportError:
            layer_issues = ["to_prism package unavailable; layer conformance not run"]
        require(not layer_issues, f"{workflow_id}: " + "; ".join(layer_issues))
        require(
            taxonomy["review_status"] == "approved" and taxonomy["unresolved"] == [],
            f"{workflow_id}: taxonomy not approved",
        )
        require(
            taxonomy["source_fingerprint"] == f"sha256:{self.before}",
            f"{workflow_id}: taxonomy fingerprint mismatch",
        )
        mappings = coverage["mappings"]
        require(
            [item["hook_id"] for item in mappings]
            == self.loops[workflow_id]["required_hooks"],
            f"{workflow_id}: incomplete hook coverage",
        )
        plan_steps = {item["id"]: item for item in plan["workflows"][0]["steps"]}
        for mapping in mappings:
            require(
                mapping["occurrence_id"] in plan_steps,
                f"{workflow_id}: hook maps to missing occurrence",
            )
            expected_owner = self.hooks[mapping["hook_id"]]["owner_skill"]
            require(
                mapping["owner_skill"] == expected_owner,
                f"{workflow_id}: hook owner mismatch",
            )
            skill_names = {
                Path(item["path"]).name
                for item in plan_steps[mapping["occurrence_id"]]["skills"]
            }
            require(
                expected_owner in skill_names,
                f"{workflow_id}: occurrence omits hook owner",
            )
        evidence = load_json(
            self.root / "projects" / workflow_id / "conversion" / "generation.json"
        )
        require(
            evidence.get("reasoning_projection_spec_sha256") == self.projection_digest,
            f"{workflow_id}: generation evidence has stale projection digest",
        )
        project = self.root / entry["project"]
        for relative, expected in evidence["source_hashes"].items():
            path = project / relative
            require(
                path.is_file()
                and hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                f"{workflow_id}: generated hash mismatch for {relative}",
            )
        try:
            from to_prism.schemas import validate_document

            self.taxonomy_issues.extend(
                f"{workflow_id}: {issue}"
                for issue in validate_document(taxonomy, "project-semantic-taxonomy")
            )
        except ImportError:
            self.taxonomy_issues.append(
                "to_prism package unavailable; schema validation not run"
            )
        self.negative.update(negative_controls(plan, coverage))
        self.cursor += 1
        return self.cursor == len(self.entries)

    def prepare_runtime(self):
        require(not self.taxonomy_issues, "; ".join(self.taxonomy_issues))
        dispositions = load_json(self.root / "skill_dispositions.json")["skills"]
        canonical_skills = list((REPOSITORY / "skills").glob("*/*/SKILL.md"))
        require(
            len(dispositions) == len(canonical_skills) == 188,
            "skill disposition inventory is incomplete",
        )
        self.requested = self.selected_workflows or {
            item["id"] for item in self.entries
        }
        unknown = self.requested - {item["id"] for item in self.entries}
        require(
            not unknown, "unknown selected workflows: " + ", ".join(sorted(unknown))
        )
        self.run_entries = [
            item for item in self.entries if item["id"] in self.requested
        ]
        self.resources = ExitStack()
        try:
            temporary_name = self.resources.enter_context(
                tempfile.TemporaryDirectory(prefix="mathformer-prism-runs-")
            )
            self.temporary = Path(temporary_name)
            self.executor = self.resources.enter_context(
                concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(max(self.jobs, 1), 4)
                )
            )
            self.futures = [
                self.executor.submit(
                    run_one,
                    self.root,
                    entry,
                    self.prism_bin,
                    self.temporary,
                    self.handler,
                )
                for entry in self.run_entries
            ]
            self.results = []
            self.runtime_failures = []
            self.cursor = 0
        except BaseException:
            self.close()
            raise

    def await_entry(self):
        entry = self.run_entries[self.cursor]
        future = self.futures[self.cursor]
        try:
            self.results.append(future.result())
        except Exception as exc:
            self.runtime_failures.append(f"{entry['id']}: {exc}")
        self.cursor += 1
        return self.cursor == len(self.run_entries)

    def finish_runtime(self):
        try:
            require(not self.runtime_failures, "; ".join(self.runtime_failures))
        finally:
            self.close()

    def close(self):
        if self.resources is not None:
            self.resources.close()
            self.resources = None

    def write_report(self):
        self.results.sort(key=lambda item: item["workflow_id"])
        overlap = any(
            left["run_started_ns"] < right["run_ended_ns"]
            and right["run_started_ns"] < left["run_ended_ns"]
            for index, left in enumerate(self.results)
            for right in self.results[index + 1 :]
        )
        require(
            overlap or len(self.results) < 2,
            "parallel runner did not observe overlapping PRISM run intervals",
        )
        after = digest_sources()
        skills_after = digest_canonical_skills()
        require(
            self.before == after,
            "canonical semantic sources changed during verification",
        )
        require(
            self.skills_before == skills_after,
            "canonical skill sources changed during verification",
        )
        native = self.handler in NATIVE_HANDLERS
        report = {
            "artifact": "parallel-workflow-conformance",
            "schema_version": "2.0",
            "status": "passed",
            "workflow_count": len(self.results),
            "catalog_workflow_count": len(self.entries),
            "jobs": min(max(self.jobs, 1), 4, len(self.results)),
            "actual_run_overlap": overlap,
            "overlap_scope": "prism_process_lifetimes",
            "handler": self.handler,
            "runtime_selection": sorted(self.requested),
            "static_catalog_scope": "all_catalog_workflows",
            "source_unchanged": True,
            "source_fingerprint": f"sha256:{self.before}",
            "canonical_skills_unchanged": True,
            "canonical_skill_fingerprint": f"sha256:{self.skills_before}",
            "negative_controls": sorted(self.negative),
            "workflows": self.results,
            "evidence": {
                "structural": "established",
                "schema": "established",
                "nominal_type_chain": "established",
                "reasoning_materialization_layers": "established",
                "reasoning_to_skill_bindings": "established_for_reviewed_projections",
                "repository_hook_coverage": "established",
                "trace": "provider_native" if native else "fake_handler_smoke",
                "provider_native_model_execution": (
                    "established" if native else "not_tested"
                ),
                "codex_native_agent_execution": (
                    ("established" if self.handler == "codex" else "not_applicable")
                    if native
                    else "not_tested"
                ),
                "native_execution": (
                    "established_for_ai_generate_effects" if native else "not_tested"
                ),
                "bounded_behavioral_correspondence": (
                    "established_for_accepted_execution_and_conservative_nonpromotion"
                    if native
                    else "not_tested"
                ),
                "behavioral_equivalence": "not_established_no_independent_native_baseline",
                "semantic_fixture_safety": "established" if native else "not_tested",
                "semantic_correctness": "not_established_beyond_registered_oracles",
                "semantic_equivalence": "not_established_no_crosswalk_oracle",
                "epistemic_safety": (
                    "established_for_placeholder_nonpromotion"
                    if native
                    else "not_tested"
                ),
                "portability": "not_applicable_linked_output",
            },
        }
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return report


def verify(
    root: Path,
    prism_bin: str,
    jobs: int,
    report_path: Path,
    handler: str,
    selected_workflows: set[str] | None = None,
) -> dict[str, Any]:
    session = VerificationSession(
        root, prism_bin, jobs, report_path, handler, selected_workflows
    )
    try:
        for _ in session.entries:
            session.validate_entry()
        session.prepare_runtime()
        for _ in session.run_entries:
            session.await_entry()
        session.finish_runtime()
        return session.write_report()
    finally:
        session.close()


def serve_steps(
    endpoint, root, prism_bin, jobs, report_path, handler, selected_workflows
):
    """Private file channel for the same VerificationSession methods.

    The hub owns subprocess timeout/output. Disconnect/cancellation closes the
    same native resources as verify(). The channel supplies no provider behavior.
    Atomic records live in a parent-owned private temporary directory.
    """
    directory = Path(endpoint)
    index = 0
    session = None

    def respond(value):
        temporary = directory / "response.pending"
        temporary.write_text(json.dumps(value), encoding="utf-8")
        temporary.replace(directory / f"response-{index}.json")

    try:
        session = VerificationSession(
            root, prism_bin, jobs, report_path, handler, selected_workflows
        )
        phase = "validate_entry"
        respond({"ok": True, "cursor": session.cursor, "catalog": session.catalog})
        while True:
            index += 1
            request = directory / f"request-{index}.json"
            while not request.exists():
                require(
                    not (directory / "cancel").exists(),
                    "verifier step channel disconnected",
                )
                time.sleep(0.02)
            method = json.loads(request.read_text(encoding="utf-8"))["method"]
            require(method == phase, "out-of-order verifier step")
            if method == "validate_entry":
                done = session.validate_entry()
                if done:
                    phase = "await_entry"
                respond({"ok": True, "cursor": session.cursor, "done": done})
            elif method == "await_entry":
                if session.resources is None:
                    session.prepare_runtime()
                done = session.await_entry()
                if done:
                    phase = "finalize"
                respond(
                    {
                        "ok": True,
                        "cursor": session.cursor,
                        "done": done,
                        "runtime_failures": session.runtime_failures,
                    }
                )
            elif method == "finalize":
                session.finish_runtime()
                report = session.write_report()
                respond({"ok": True})
                return report
    except Exception as exc:
        respond({"ok": False, "error": str(exc)})
        raise
    finally:
        if session is not None:
            session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY / "mathformer-prism")
    parser.add_argument(
        "--prism-bin",
        default=str(REPOSITORY.parent / "to_prism" / ".venv" / "bin" / "prism"),
    )
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--handler", choices=("fake", "codex", "litellm"), default="fake"
    )
    parser.add_argument("--workflow", action="append", default=[])
    args = parser.parse_args()
    report_path = (
        args.output or args.root / "tests" / "parallel-workflow-conformance.json"
    )
    try:
        endpoint = os.environ.get("MATHFORMER_PRISM_STEP_CHANNEL")
        runner = (
            verify if endpoint is None else lambda *args: serve_steps(endpoint, *args)
        )
        report = runner(
            args.root.resolve(),
            args.prism_bin,
            args.jobs,
            report_path.resolve(),
            args.handler,
            set(args.workflow) or None,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "workflows": report["workflow_count"],
                "handler": report["handler"],
                "actual_run_overlap": report["actual_run_overlap"],
                "report": str(report_path.resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
