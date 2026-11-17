#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Validate source projections and reject stale or fabricated workflow contracts."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "skills/control/workflow-contract-validator/scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import normalize_workflows as normalizer  # noqa: E402
import validate_workflow as validator  # noqa: E402


class NormalizedWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.descriptors = normalizer.inventory()
        cls.by_alias = {
            alias: item for item in cls.descriptors for alias in item["aliases"]
        }

    def test_complete_source_inventory(self):
        categories = {
            category: set() for category in ("hub", "route", "loop", "profile")
        }
        for item in self.descriptors:
            record = item["extensions"]["mathformer.source"]
            categories[record["category"]].add(record["native_id"])
        self.assertEqual(categories["hub"], set(normalizer.hub.build_registry()))
        self.assertEqual(
            categories["route"],
            {route.route_id for route in normalizer.hub.build_intent_routes()},
        )
        loops = normalizer.parse_loop_contracts(
            (REPO_ROOT / normalizer.HOOKS).read_text().splitlines()
        )
        self.assertEqual(categories["loop"], {loop["id"] for loop in loops})
        styles = yaml.safe_load((REPO_ROOT / normalizer.REASONING).read_text())[
            "reasoning_styles"
        ]
        self.assertEqual(categories["profile"], {style["id"] for style in styles})

    def test_all_generated_descriptors_validate_and_match_sources(self):
        result = normalizer.check()
        self.assertTrue(result["ok"], result["errors"][:5])
        self.assertFalse(result["execution_migrated"])
        self.assertFalse(result["runtime_bindings_qualified"])

    def test_hub_metadata_and_dependency_order_are_preserved(self):
        for action_id, action in normalizer.hub.build_registry().items():
            descriptor = self.by_alias[action_id]
            self.assertEqual(
                descriptor["extensions"]["mathformer.source"]["contract"],
                normalizer.hub.action_to_dict(action),
            )
            self.assertEqual(
                descriptor["extensions"]["mathformer.composition"][
                    "ordered_dependencies"
                ],
                list(action.depends_on),
            )
            self.assertEqual(
                descriptor["operations"]["invoke"]["execution"]["binding"]["target"],
                action_id,
            )
            self.assertEqual(descriptor["provenance"]["coverage"], "interface_only")

    def test_routes_preserve_exact_order_and_skill_links(self):
        for route in normalizer.hub.build_intent_routes():
            descriptor = self.by_alias[route.route_id]
            self.assertEqual(
                descriptor["extensions"]["mathformer.composition"]["ordered_actions"],
                list(route.action_ids),
            )
            self.assertEqual(
                tuple(
                    descriptor["extensions"]["mathformer.source"]["contract"][
                        "skill_routes"
                    ]
                ),
                route.skill_routes,
            )

    def test_declarative_membership_is_not_fabricated_execution(self):
        for descriptor in self.descriptors:
            category = descriptor["extensions"]["mathformer.source"]["category"]
            if descriptor["id"] == "loop_draft_execute_refine_loop_workflow":
                self.assertEqual(descriptor["lifecycle"], "active")
                self.assertEqual(descriptor["flow"]["steps"][1]["kind"], "loop")
                self.assertTrue(
                    all(
                        "binding" in op["execution"]
                        for op in descriptor["operations"].values()
                    )
                )
                continue
            if category not in ("loop", "profile"):
                continue
            self.assertEqual(descriptor["lifecycle"], "draft")
            self.assertEqual(descriptor["flow"]["kind"], "call")
            self.assertFalse(descriptor["inputs"])
            self.assertFalse(descriptor["outputs"])
            self.assertEqual(
                descriptor["operations"]["realize_contract"]["execution"]["mode"],
                "specification_only",
            )
            self.assertTrue(descriptor["provenance"]["gaps"])

    def test_source_schema_and_core_references(self):
        schema = json.loads(validator.SCHEMA_PATH.read_text())
        Draft202012Validator.check_schema(schema)
        registry = Registry().with_resource(
            schema["$id"], Resource.from_contents(schema)
        )

        def visit(value):
            if isinstance(value, dict):
                if "$ref" in value:
                    registry.resolver(schema["$id"]).lookup(value["$ref"])
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(schema)

    def test_real_controller_envelopes_without_backend_execution(self):
        schema = json.loads(
            (normalizer.OUTPUT / "hub-interface.schema.json").read_text()
        )
        payload_validator = Draft202012Validator(
            {"$ref": "#/$defs/HubResult", "$defs": schema["$defs"]}
        )
        hub = normalizer.hub
        actions = hub.build_registry()
        payloads = [
            hub.run_action("missing:fixture", actions, hub.RunContext(dry_run=True)),
            hub.run_action("repo:status", actions, hub.RunContext(dry_run=True)),
            hub.run_action(
                "control:all",
                actions,
                hub.RunContext(dry_run=True),
                extra_args=["unexpected"],
            ),
        ]
        # Test source sequence aggregation using stub results, never subprocesses.
        with patch.object(
            hub,
            "run_leaf_action",
            side_effect=lambda *args: {"ok": False, "status": "fixture_failure"},
        ):
            failed = hub.run_action("control:all", actions, hub.RunContext())
            continued = hub.run_action(
                "control:all", actions, hub.RunContext(keep_going=True)
            )
        self.assertEqual(len(failed["children"]), 1)
        self.assertEqual(
            len(continued["children"]), len(actions["control:all"].depends_on)
        )
        self.assertFalse(continued["ok"])
        for payload in [*payloads, failed, continued]:
            payload_validator.validate(payload)

    def write_descriptor(self, directory, descriptor):
        path = Path(directory) / "workflow.yaml"
        path.write_text(
            yaml.dump(descriptor, Dumper=normalizer.DescriptorDumper, sort_keys=False)
        )
        return path

    def test_changed_source_digest_is_rejected(self):
        descriptor = deepcopy(self.by_alias["repo:status"])
        # Use a temp location inside the repository for relative schema references.
        with tempfile.TemporaryDirectory(dir=normalizer.OUTPUT) as directory:
            path = Path(directory) / "workflow.yaml"
            descriptor["types"]["RunContext"][
                "schema"
            ] = "../hub-interface.schema.json#/$defs/RunContext"
            descriptor["types"]["HubResult"][
                "schema"
            ] = "../hub-interface.schema.json#/$defs/HubResult"
            descriptor["provenance"]["sources"][0]["digest"] = "sha256:" + "0" * 64
            path.write_text(yaml.dump(descriptor, Dumper=normalizer.DescriptorDumper))
            result = validator.validate(path, REPO_ROOT)
            self.assertFalse(result["valid"])
            self.assertTrue(
                any("source digest mismatch" in error for error in result["errors"]),
                result["errors"],
            )

    def test_stale_generated_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            result = normalizer.check(Path(directory))
            self.assertFalse(result["ok"])
            self.assertTrue(
                any("missing or stale" in error for error in result["errors"])
            )

    def test_duplicate_yaml_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.yaml"
            path.write_text("id: a_workflow\nid: b_workflow\n")
            self.assertFalse(validator.validate(path)["valid"])

    def test_forward_reference_and_unknown_type_are_rejected(self):
        descriptor = deepcopy(self.by_alias["control_validation_loop"])
        descriptor["inputs"] = {"contract": {"type": "Imaginary"}}
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_descriptor(directory, descriptor)
            self.assertFalse(validator.validate(path)["valid"])
            descriptor["inputs"] = {}
            descriptor["outputs"] = {
                "identity": {
                    "type": "ContractIdentity",
                    "value": {"ref": "steps.future.outputs.identity"},
                }
            }
            path = self.write_descriptor(directory, descriptor)
            self.assertFalse(validator.validate(path)["valid"])

    def test_generation_is_deterministic(self):
        first, catalog = normalizer.render()
        second, _ = normalizer.render()
        self.assertEqual(first, second)
        self.assertEqual(len(catalog["workflows"]), len(self.descriptors))
        self.assertTrue(
            all(
                (REPO_ROOT / row["owner_skill"]).is_file()
                for row in catalog["workflows"]
            )
        )


class NormalizedCursor:
    """Incremental default unittest traversal, also used by the MCP boundary.

    The native TestSuite fixture machinery and TestCase.run own setup errors,
    assertion handling, skips, cleanups and per-case output.
    """

    def __init__(self, result):
        self.result = result
        self.cases = list(
            unittest.defaultTestLoader.loadTestsFromTestCase(NormalizedWorkflowTests)
        )
        self.suite = unittest.TestSuite(self.cases)
        self.result._testRunEntered = True
        if not self.cases:
            self.ready = False
            self.index = 0
            self.results = []
            return
        first = self.cases[0]
        self.suite._handleModuleFixture(first, result)
        self.suite._handleClassSetUp(first, result)
        result._previousTestClass = first.__class__
        self.ready = not (
            getattr(first.__class__, "_classSetupFailed", False)
            or result._moduleSetUpFailed
        )
        self.index = 0
        self.results = []
        if not self.ready:
            self.results.append({"status": "error", "detail": str(result.errors)})

    def state(self, shared):
        return {
            "shared": shared,
            "remaining": [case._testMethodName for case in self.cases[self.index :]],
            "results": list(self.results),
        }

    def run_test(self):
        if not self.ready or self.index >= len(self.cases):
            raise ValueError("no current test")
        before = (
            len(self.result.failures),
            len(self.result.errors),
            len(self.result.skipped),
        )
        case = self.cases[self.index]
        case.run(self.result)
        after = (
            len(self.result.failures),
            len(self.result.errors),
            len(self.result.skipped),
        )
        status = next(
            (
                name
                for i, name in enumerate(("failure", "error", "skipped"))
                if after[i] > before[i]
            ),
            "success",
        )
        return {"status": status, "method": case._testMethodName}

    def advance(self, test):
        if test["method"] != self.cases[self.index]._testMethodName:
            raise ValueError("test cursor mismatch")
        self.results.append(test)
        self.index += 1
        return self.index == len(self.cases)

    def close(self):
        self.suite._tearDownPreviousClass(None, self.result)
        self.suite._handleModuleTearDown(self.result)
        self.result._testRunEntered = False


class IncrementalNormalizedSuite(unittest.TestSuite):
    def run(self, result, debug=False):
        cursor = NormalizedCursor(result)
        if cursor.ready:
            while cursor.index < len(cursor.cases):
                if result.shouldStop:
                    break
                cursor.advance(cursor.run_test())
        cursor.close()
        return result


def load_tests(loader, tests, pattern):
    return IncrementalNormalizedSuite(
        loader.loadTestsFromTestCase(NormalizedWorkflowTests)
    )


if __name__ == "__main__":
    # Tests use temporary files only; prevent imported modules creating caches.
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    unittest.main()
