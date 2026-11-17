#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
"""Validate adoption metadata and compare bounded adapters to existing behavior."""

from tempfile import gettempdir

from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/control/workflow-contract-validator/scripts"))
import portable_adoption as adoption
from adoption_provenance import (
    validate_invocation,
)


class AdoptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.index = adoption.load_contract()

    def mutated(self, mutate):
        data = deepcopy(self.data)
        mutate(data)
        with self.assertRaises((ValueError, KeyError, TypeError)):
            adoption.validate_metadata(data)

    def test_canonical_routes_and_aliases(self):
        self.assertEqual(len(self.data["surfaces"]), 4)
        self.assertEqual(len(self.index["operations"]), 8)
        for identity, (surface, op) in self.index["operations"].items():
            self.assertEqual(adoption.resolve(identity, self.data), (surface, op))
            for alias in op["aliases"]:
                self.assertEqual(adoption.resolve(alias, self.data), (surface, op))
        with self.assertRaises(ValueError):
            adoption.resolve("missing:operation", self.data)

    def test_ambiguous_ids_alias_cycles_and_stale_bindings(self):
        self.mutated(lambda d: d["surfaces"].append(deepcopy(d["surfaces"][0])))
        self.mutated(
            lambda d: d["surfaces"][1]["operations"][0].update(id="router:resolve")
        )
        self.mutated(
            lambda d: d["surfaces"][0]["operations"][0]["aliases"].append(
                "router:resolve"
            )
        )
        self.mutated(
            lambda d: d["surfaces"][1]["operations"][0]["aliases"].append(
                "mathformer-workflow-router:resolve"
            )
        )
        self.mutated(
            lambda d: d["surfaces"][0]["operations"][0]["binding"].update(
                symbol="absent_function"
            )
        )
        self.mutated(
            lambda d: d["surfaces"][1]["operations"][0]["binding"].update(
                action_id="control:missing"
            )
        )
        self.mutated(
            lambda d: d["surfaces"][0]["operations"][0]["binding"].update(
                path="../outside.py"
            )
        )

    def test_unknown_fields_and_incomplete_io(self):
        selectors = [
            lambda d: d,
            lambda d: d["surfaces"][0],
            lambda d: d["surfaces"][0]["operations"][0],
        ]
        for field in ("binding", "typing", "inputs", "outputs", "availability"):
            selectors.append(
                lambda d, field=field: d["surfaces"][0]["operations"][0][field]
            )
        for select in selectors:
            self.mutated(lambda d: select(d).update(unknown_field="unknown"))
        for field in ("inputs", "outputs"):
            self.mutated(
                lambda d, field=field: d["surfaces"][0]["operations"][0][field].update(
                    type=""
                )
            )
        self.mutated(
            lambda d: d["surfaces"][0]["operations"][0]["outputs"].update(
                authority="backend proved"
            )
        )

    def test_adapter_binding_cannot_drift_to_existing_implementation(self):
        # Merely finding a callable/path cannot establish that the dispatcher
        # executes it. Each mutation names a real repository implementation.
        self.mutated(
            lambda d: d["surfaces"][0]["operations"][0]["binding"].update(
                symbol="build_registry"
            )
        )
        self.mutated(
            lambda d: d["surfaces"][1]["operations"][0]["binding"].update(
                path="skills/control/reasoning-log-schema-guardian/scripts/summarize_reasoning_log.py",
                action_id="control:reasoning-log-summary",
            )
        )
        self.mutated(
            lambda d: d["surfaces"][3]["operations"][0]["binding"].update(
                path="mathformer-prism/projects/artifact_acceptance_loop/prism_project/material_main.prism"
            )
        )
        self.mutated(
            lambda d: d["surfaces"][3].update(owner="mathformer-prism/projects")
        )
        data = deepcopy(self.data)
        data["surfaces"][0]["operations"][0]["binding"]["symbol"] = "build_registry"
        with (
            patch.object(adoption, "load_contract", return_value=(data, {})),
            patch.object(adoption, "invoke_recorded") as recorder,
        ):
            with self.assertRaisesRegex(
                ValueError, "binding disagrees with explicit adapter"
            ):
                adoption.invoke(
                    "router:resolve", {"request": "validate portable adoption"}
                )
            recorder.assert_not_called()

    def test_taxonomy_values_are_checked(self):
        for field in (
            "execution_posture",
            "composition_role",
            "authority_profile",
            "output_type",
            "reasoning_method",
            "invocation_mechanism",
        ):
            self.mutated(
                lambda d, field=field: d["surfaces"][0]["operations"][0][
                    "typing"
                ].update({field: "invented"})
            )
        for field in ("specification_styles", "effect_profiles"):
            self.mutated(
                lambda d, field=field: d["surfaces"][0]["operations"][0][
                    "typing"
                ].update({field: ["invented"]})
            )

    def test_router_exact_json_parity_and_snapshot(self):
        hub = adoption.module_at(ROOT / "scripts/mathformer.py")
        for request in (
            "make sure every workflow is controlled",
            "unmatchable-quux-999",
        ):
            expected = json.loads(
                json.dumps(
                    [
                        asdict(item)
                        for item in hub.resolve_intent(
                            request, hub.build_registry(), limit=5, family=None
                        )
                    ]
                )
            )
            with tempfile.TemporaryDirectory() as temp:
                actual = adoption.invoke(
                    "router:resolve", {"request": request}, Path(temp)
                )
                self.assertEqual(actual, expected)
                receipt = validate_invocation(next(Path(temp).iterdir()))
                self.assertIn("reasoning_mapping", receipt["metadata"])
                self.assertEqual(
                    receipt["metadata"]["mapping_sources"]["skill_types"]["sha256"],
                    hashlib.sha256(
                        (ROOT / "skills/SKILL_TYPES.yaml").read_bytes()
                    ).hexdigest(),
                )

    def test_actual_validator_matches_legacy(self):
        hub = adoption.module_at(ROOT / "scripts/mathformer.py")
        legacy = hub.run_action(
            "control:workflow-contract",
            hub.build_registry(),
            hub.RunContext(json_output=True),
            extra_args=(),
        )
        with tempfile.TemporaryDirectory() as temp:
            actual = adoption.invoke("control:workflow-contract", {}, Path(temp))
            # Concurrent repository edits can affect the legacy write audit. The actual
            # leaf command, captured streams, exit code and result are exact contracts.
            for key in (
                "argv",
                "cwd",
                "dry_run",
                "preflight_errors",
                "returncode",
                "stdout",
                "stderr",
            ):
                self.assertEqual(actual.get(key), legacy.get(key), key)
            validate_invocation(next(Path(temp).iterdir()))

    def test_log_consumer_parity_without_rewriting_history(self):
        fixtures = adoption.module_at(
            ROOT / "tests/reasoning_logs/run_consumer_contract_suite.py"
        )
        summary = adoption.module_at(
            adoption.LOG_SCRIPTS / "summarize_reasoning_log.py"
        )
        validator = adoption.module_at(
            adoption.LOG_SCRIPTS / "validate_reasoning_log.py"
        )
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / "fixture.jsonl"
            fixtures.build_log(log, mode="single")
            original = log.read_bytes()
            for operation, function in [
                ("control:reasoning-log-summary", summary.summarize),
                ("reasoning-log:validate", validator.validate_reasoning_log),
            ]:
                expected = function(log, hooks_file=ROOT / "skills/SKILL_HOOKS.yaml")
                actual = adoption.invoke(operation, {"log_file": str(log)})
                self.assertEqual(actual, expected)
            self.assertEqual(log.read_bytes(), original)

    def test_cli_bad_input_and_catalog_drift(self):
        for argv in (
            ["describe", "missing:operation"],
            ["invoke", "router:resolve", "--inputs", "[1]"],
            ["invoke", "router:resolve", "--inputs", "{"],
            [
                "invoke",
                "router:resolve",
                "--output-dir",
                str(Path(gettempdir()) / "elsewhere"),
            ],
        ):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(adoption.main(argv), 2)
            self.assertFalse(json.loads(out.getvalue())["ok"])
        with tempfile.TemporaryDirectory() as temp:
            catalog = Path(temp) / "catalog.md"
            with (
                patch.object(adoption, "CATALOG", catalog),
                patch.object(adoption, "ROOT", Path(temp)),
                redirect_stdout(io.StringIO()),
            ):
                catalog.write_text(adoption.catalog_text(self.data))
                self.assertEqual(adoption.main(["catalog", "--check"]), 0)
                catalog.write_text("stale")
                self.assertEqual(adoption.main(["catalog", "--check"]), 2)
        self.assertEqual(
            adoption.catalog_text(self.data), adoption.catalog_text(deepcopy(self.data))
        )

    def test_prism_authority_boundaries(self):
        public = adoption.resolve("artifact_acceptance_loop:public", self.data)[1]
        material = adoption.resolve("artifact_acceptance_loop:material", self.data)[1]
        self.assertIn("Generated[", public["outputs"]["type"])
        self.assertIn("Computed[", material["outputs"]["type"])
        self.assertEqual(public["typing"]["execution_posture"], "generative")
        self.assertIn(
            "not_executed_by_structural_fixture", material["outputs"]["authority"]
        )
        self.mutated(
            lambda d: d["surfaces"][3]["operations"][0]["outputs"].update(
                type="Computed[ArtifactDisposition]"
            )
        )
        self.mutated(
            lambda d: d["surfaces"][3]["operations"][1]["typing"].update(
                output_authority="backend verified"
            )
        )

    @unittest.skipUnless(
        (ROOT.parent / "to_prism/.venv/bin/prism").is_file(),
        "adjacent PRISM runtime unavailable",
    )
    def test_prism_runtime_fixture_is_not_backend_evidence(self):
        for operation in (
            "artifact_acceptance_loop:public",
            "artifact_acceptance_loop:material",
        ):
            with tempfile.TemporaryDirectory() as temp:
                result = adoption.invoke(operation, {}, Path(temp))
                self.assertTrue(result["fixture"])
                self.assertFalse(result["backend_verified"])
                self.assertEqual(result["handler"], "fake")
                receipt = validate_invocation(next(Path(temp).iterdir()))
                self.assertTrue(receipt["metadata"]["fixture"])


class AdoptionCursor:
    """Incremental default unittest traversal, also used by the MCP boundary.

    The native TestSuite fixture machinery and TestCase.run own setup errors,
    assertion handling, skips, cleanups and per-case output.
    """

    def __init__(self, result):
        self.result = result
        self.cases = list(
            unittest.defaultTestLoader.loadTestsFromTestCase(AdoptionTests)
        )
        self.suite = unittest.TestSuite(self.cases)
        self.result._testRunEntered = True
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


class IncrementalAdoptionSuite(unittest.TestSuite):
    def run(self, result, debug=False):
        cursor = AdoptionCursor(result)
        if cursor.ready:
            while cursor.index < len(cursor.cases):
                if result.shouldStop:
                    break
                cursor.advance(cursor.run_test())
        cursor.close()
        return result


def load_tests(loader, tests, pattern):
    return IncrementalAdoptionSuite(loader.loadTestsFromTestCase(AdoptionTests))


if __name__ == "__main__":
    unittest.main()
