#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Source suite, real text checker, registered MCP and real Lunar/PRISM runtime.

No provider or theorem compiler exists on this source path. Lean text and stage
receipts are deterministic input fixtures, never submitted to an external tool.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import unittest
import yaml
import run_grounded_sample_workflow_tests as fixture_suite
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_validate_physics_lean_grounded_samples_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/grounded-samples-route.workflow.json"
)
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
PREFIX = "mathformer_grounded_sample_"


def assets(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )
        for path, text in values.items()
    ]


class GroundedSamplesRouteTests(unittest.TestCase):
    maxDiff = None
    # Shared deterministic input fixture builder; no source step is substituted.
    setUp = fixture_suite.GroundedSampleTests.setUp
    write = fixture_suite.GroundedSampleTests.write
    lean = fixture_suite.GroundedSampleTests.lean
    record = fixture_suite.GroundedSampleTests.record
    request = fixture_suite.GroundedSampleTests.request
    baseline = fixture_suite.GroundedSampleTests.baseline
    test_native_entrypoint_equivalence_state_and_features = (
        fixture_suite.GroundedSampleTests.test_native_entrypoint_equivalence_state_and_features
    )

    def test_generator_identity_policies_and_provenance(self):
        spec = importlib.util.spec_from_file_location(
            "grounded_route_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(module.grounded_samples_route_descriptor(), document)
        self.assertEqual(json.loads(AUTHORED.read_text()), document)
        self.assertEqual(
            document["id"], "route_validate_physics_lean_grounded_samples_workflow"
        )
        self.assertEqual(
            document["aliases"], ["validate.physics.lean.grounded_samples"]
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 32},
        )
        self.assertEqual(
            document["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(document["policy"]["resume"]["mode"], "none")
        self.assertEqual(
            document["policy"]["effects"]["filesystem"]["write"],
            ["artifacts/physics_lean/grounded_sample_thoroughness/"],
        )
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 15)
        self.assertEqual(document["flow"]["steps"][1]["on_exhausted"], "fail")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            self.native.__file__,
            [str(ROOT / row["path"]) for row in document["provenance"]["sources"]],
        )

    def test_selected_original_source_equivalence(self):
        original = ROOT / "tests/mcp/fixtures/grounded_samples_route_original.py.txt"
        scope = {
            "__file__": str(
                ROOT / "tests/physics_lean/run_grounded_sample_thoroughness.py"
            ),
            "__name__": "frozen_grounded_suite",
        }
        exec(compile(original.read_text(), str(original), "exec"), scope)
        for selection in (
            None,
            [],
            ["generated_operator", "generated_bad", "generated_operator"],
            ["generated_calculus", "generated_plain"],
        ):
            expected = scope["run_suite"](selection, self.root)
            expected_bytes = self.fixed.read_bytes()
            self.assertEqual(self.native.run_suite(selection, self.root), expected)
            self.assertEqual(self.fixed.read_bytes(), expected_bytes)
        # Native subprocess failure handling accepts nonzero JSON reports; the
        # blocked Lean fixture exercises this through the unmodified checker.
        completed = self.native.run_suite(
            ["generated_bad", "generated_plain"], self.root
        )
        self.assertEqual([r["ok"] for r in completed["cases"]], [False, True])
        with self.assertRaises(SystemExit):
            scope["run_suite"](["generated_plain", "unknown"], self.root)
        with self.assertRaises(SystemExit):
            self.native.run_suite(["generated_plain", "unknown"], self.root)

    def test_registered_mcp_and_lunar_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        server = (
            'import sys;sys.path.insert(0,"scripts");'
            "from mcp_server import mcp,apply_runtime_config;"
            'apply_runtime_config(allowed_write_roots=[sys.argv[1]]);mcp.run(transport="stdio")'
        )
        # Service runs real registrations with relocated data and write roots.
        # No configuration/credentials are loaded by this entrypoint.
        async with manager.open(
            "grounded-samples-route",
            StdioConfig(
                command=sys.executable,
                args=["-c", server, str(self.root)],
                cwd=str(ROOT),
            ),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            await self.connected(remote)
        self.assertFalse(manager.active)

    async def connected(self, remote):
        document = yaml.safe_load(CONTRACT.read_text())
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(doc, inventory=None):
            received = assets(doc)
            selected = workflow_documents([DESCRIPTOR], received)[0]
            self.assertTrue(selected["validation"]["valid"], selected)
            w = compile_workflow(
                "mcp:grounded-samples-route",
                selected,
                tools if inventory is None else inventory,
            )
            return w, received

        workflow, received = compile(document)
        self.assertTrue(workflow["runnable"], workflow["diagnostics"])
        self.assertEqual(workflow["runtime_status"], "ready")
        self.assertTrue(workflow["prism_source"])
        self.assertTrue(workflow["runtime_source"])
        self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
        for operation in document["operations"].values():
            target = operation["execution"]["binding"]["target"]
            self.assertFalse(
                compile(document, [t for t in tools if t["name"] != target])[0][
                    "runnable"
                ]
            )

        async def allow():
            pass

        async def run(selection, changed=None):
            w, a = compile(changed) if changed else (workflow, received)
            self.assertTrue(w["runnable"], w["diagnostics"])
            return await execute(
                w,
                a,
                {"case_ids": selection, "repository_root": str(self.root)},
                remote,
                allow,
            )

        for selection in (
            None,
            [],
            ["generated_operator"],
            ["generated_calculus", "generated_plain"],
            ["generated_bad", "formalphysics_0000", "generated_bad"],
        ):
            expected = self.native.run_suite(selection, self.root)
            expected_bytes = self.fixed.read_bytes()
            self.fixed.unlink()
            result = await run(selection)
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"], {"report": expected})
            self.assertEqual(self.fixed.read_bytes(), expected_bytes)
            n = expected["case_count"]
            self.assertEqual(
                [c["operation"] for c in result["calls"]],
                ["initialize_suite"]
                + [op for _ in range(n) for op in ("audit_next", "append_guard")]
                + ["finalize_suite"],
            )
            self.assertEqual(n, len(dict.fromkeys(selection)) if selection else 15)
            self.assertTrue(result["runtime"]["effect_records"])
            self.assertTrue(result["runtime"]["provenance"])
            self.assertTrue(result["replay_artifacts"])
            if selection and "generated_bad" in selection:
                self.assertFalse(result["outputs"]["report"]["ok"])
                self.assertTrue(result["outputs"]["report"]["cases"][-1]["ok"])
        # Every advertised port matches the native frame and leaves prior state intact.
        packet = await remote.call(
            PREFIX + "initialize_suite",
            {
                "case_ids": ["generated_bad", "generated_plain", "generated_bad"],
                "repository_root": str(self.root),
            },
        )
        state = packet["state"]
        self.assertEqual(
            state,
            self.native.initialize_suite(
                ["generated_bad", "generated_plain", "generated_bad"], self.root
            ),
        )
        for done in (False, True):
            before = deepcopy(state)
            result = await remote.call(
                PREFIX + "audit_next",
                {"state": state, "repository_root": str(self.root)},
            )
            self.assertEqual(result["result"], self.native.audit_next(state, self.root))
            advanced = await remote.call(PREFIX + "append_guard", {**packet, **result})
            self.assertEqual(
                advanced, self.native.append_guard(state, result["result"])
            )
            self.assertEqual(state, before)
            self.assertEqual(advanced["done"], done)
            packet, state = {"state": advanced["state"]}, advanced["state"]
        finalized = await remote.call(
            PREFIX + "finalize_suite", {**packet, "repository_root": str(self.root)}
        )
        self.assertEqual(
            finalized, {"report": self.native.finalize_suite(state, self.root)}
        )
        # Initialization is atomic with respect to auditing; unknown/malformed
        # selections propagate a tool failure and produce no aggregate report.
        self.record("malformed", {}).write_text("{")
        for selection in (["generated_plain", "unknown"], ["malformed"]):
            self.fixed.unlink(missing_ok=True)
            result = await run(selection)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 1)
            self.assertIsNone(result["outputs"])
            self.assertFalse(self.fixed.exists())
        self.record("missing", {})
        self.record("checker_missing", {})
        self.lean("checker_missing", self.good, checker=False)
        for case in ("missing", "checker_missing"):
            with self.assertRaises((FileNotFoundError, RuntimeError)):
                self.native.run_suite(
                    ["generated_plain", case, "generated_operator"], self.root
                )
            result = await run(["generated_plain", case, "generated_operator"])
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(
                [c["operation"] for c in result["calls"]],
                ["initialize_suite", "audit_next", "append_guard", "audit_next"],
            )
            self.assertIsNone(result["outputs"])
            self.assertFalse(self.fixed.exists())
        # Deterministic final write failure reaches the original writer.
        self.fixed.mkdir(parents=True)
        result = await run(["generated_plain"])
        self.assertEqual(result["status"], "failed", result)
        self.assertEqual(result["calls"][-1]["operation"], "finalize_suite")
        self.assertIsNone(result["outputs"])
        self.fixed.rmdir()
        # Exactly-at-bound success versus exhausted traversal, without finalization.
        bounded = deepcopy(document)
        bounded["flow"]["steps"][1]["max_iterations"] = 1
        self.assertEqual(
            (await run(["generated_plain"], bounded))["status"], "accepted"
        )
        self.fixed.unlink()
        result = await run(["generated_plain", "generated_operator"], bounded)
        self.assertEqual(result["status"], "failed", result)
        self.assertEqual(result["failure_disposition"], "fail")
        self.assertEqual(len(result["calls"]), 3)
        self.assertIsNone(result["outputs"])
        self.assertFalse(self.fixed.exists())
        budget = deepcopy(document)
        budget["policy"]["limits"]["max_operation_calls"] = 1
        result = await run(["generated_plain"], budget)
        self.assertEqual(result["status"], "failed", result)
        self.assertEqual(
            sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 1
        )
        self.assertFalse(self.fixed.exists())
        with self.assertRaises(ExecutionRejected):
            await run(["generated_plain"] * 16)
        with self.assertRaises(MCPConnectionError):
            await remote.call(
                PREFIX + "initialize_suite",
                {
                    "case_ids": ["generated_plain"] * 16,
                    "repository_root": str(self.root),
                },
            )
        # Service mutation policy applies independently of host authorization.
        with self.assertRaises(MCPConnectionError):
            await remote.call(
                PREFIX + "finalize_suite",
                {
                    **packet,
                    "repository_root": str(self.root.parent / "outside-grounded-suite"),
                },
            )


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
