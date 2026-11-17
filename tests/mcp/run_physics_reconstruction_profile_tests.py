#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline fidelity and execution-refusal tests for the declarative profile.

This is deliberately NOT a runnable-physics qualification test. There is no
native scientific implementation, provider boundary, or compiler boundary to
fixture. Use the actual ERFL parser, registered MCP dispatcher, and Lunar/PRISM
compiler and execution gate. Never turn a successful refusal into a physics
result. WORKFLOW_CONTRACT_PATH explicitly selects the candidate or installed
contract; neither the normalized YAML nor catalog is written by these tests.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from copy import deepcopy
import hashlib
import json
import unittest
import yaml

from normalize_workflows_tools import source as normalizer
from reasoning_flow_tools import source as erfl_source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import CatalogError, workflow_documents
from mcp_connections.execution import ExecutionRejected, execute
from mcp_connections.workflow_compiler import compile_workflow

IDENTITY = "profile_physics_derivation_reconstruction_workflow"
ALIAS = "physics_derivation_reconstruction"
SOURCE = "examples/reasoning_flows/physics_derivation_reconstruction.rflow"
DESCRIPTOR = (
    "skills/control/workflow-contract-validator/references/"
    "normalized-workflows/profile/" + IDENTITY + "/workflow.yaml"
)


def document():
    return yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())


def snapshot(doc):
    def asset(path, content):
        return dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in doc["provenance"]["sources"]
    ]


class PhysicsReconstructionProfileTests(unittest.TestCase):
    def test_native_epistemic_dependencies_and_terminal_dispositions(self):
        doc = document()
        self.assertEqual(doc["id"], IDENTITY)
        self.assertEqual(doc["aliases"], [ALIAS])
        native = erfl_source({"repository_root": str(ROOT)})
        text = (ROOT / SOURCE).read_text()
        flow = native.parse_document(text)
        registry = native.load_registry(native.DEFAULT_REGISTRY)
        report = native.validate_text(
            text, source=SOURCE, registry=registry, strict=True
        )
        self.assertTrue(report["ok"], report)
        self.assertEqual(flow.name, ALIAS)
        self.assertEqual(flow.repeats, [])
        self.assertEqual(flow.resources, [])
        self.assertEqual(flow.goal_handle, "physics_status")
        occurrences = native.occurrences(flow.route)
        self.assertEqual([o.alias for o in occurrences], list("osmagdpre"))
        self.assertEqual([o.type_code for o in occurrences], list("OSMAGDPRE"))
        steps = doc["flow"]["steps"]
        self.assertEqual(
            [step["id"] for step in steps[:-1]], [o.alias for o in occurrences]
        )
        producers = {"source": "inputs.source"}
        kinds = {"source": "Context"}
        # Compare every input dependency and nominal port against the real AST,
        # including context reuse and the claim's three downstream consumers.
        for occurrence, step in zip(occurrences, steps):
            operation = doc["operations"][step["operation"]]
            self.assertEqual(
                step["arguments"],
                {
                    port.name: {"ref": producers[port.name]}
                    for port in occurrence.inputs
                },
            )
            self.assertEqual(
                operation["inputs"],
                {port.name: {"type": port.kind} for port in occurrence.inputs},
            )
            self.assertEqual(
                operation["outputs"],
                {port.name: {"type": port.kind} for port in occurrence.outputs},
            )
            for port in occurrence.inputs:
                self.assertEqual(kinds[port.name], port.kind)
            for port in occurrence.outputs:
                producers[port.name] = f"steps.{occurrence.alias}.outputs.{port.name}"
                kinds[port.name] = port.kind
        self.assertEqual(
            [(h.subject, h.status, h.action) for h in flow.handlers],
            [
                ("e", "accepted_for_scope", "accept"),
                ("e", "reconstruction_gap", "stop"),
                ("e", "refuted", "stop"),
            ],
        )
        terminal = steps[-1]
        for case, handler in zip(terminal["cases"], flow.handlers):
            self.assertEqual(case["id"], handler.status)
            self.assertEqual(
                case["when"],
                {
                    "eq": [
                        {"ref": producers["physics_status"]},
                        {"literal": handler.status},
                    ]
                },
            )
            self.assertEqual(case["body"]["operation"], handler.action)
        self.assertEqual(len(terminal["cases"]), len(flow.handlers))
        self.assertEqual(terminal["default"]["operation"], "stop")
        self.assertEqual(
            doc["types"]["Decision"]["schema"]["enum"],
            [h.status for h in flow.handlers],
        )

    def test_generator_preserves_graph_and_current_provenance(self):
        doc = document()
        self.assertEqual(doc["lifecycle"], "draft")
        self.assertEqual(doc["provenance"]["coverage"], "partial")
        self.assertIn(SOURCE, [row["path"] for row in doc["provenance"]["sources"]])
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
                row["path"],
            )
        self.assertEqual(
            normalizer().physics_derivation_reconstruction_descriptor(), doc
        )
        # Render the selected descriptor without invoking the unrelated full
        # corpus inventory (which may have independent alias collisions).
        files, catalog = normalizer().render_descriptors([doc])
        self.assertEqual(
            set(files),
            {Path("profile") / IDENTITY / "workflow.yaml", Path("catalog.json")},
        )
        self.assertEqual(
            yaml.safe_load(files[Path("profile") / IDENTITY / "workflow.yaml"]), doc
        )
        self.assertFalse(catalog["workflows"][0]["binding_declared"])
        self.assertFalse(catalog["workflows"][0]["runtime_qualified"])
        self.assertEqual(doc["policy"]["effects"]["network"], [])
        self.assertEqual(doc["policy"]["effects"]["filesystem"]["write"], [])
        self.assertEqual(
            doc["policy"]["failure"]["retry"],
            {"max_attempts": 1, "retryable_codes": []},
        )
        self.assertEqual(doc["policy"]["resume"]["mode"], "none")
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 10},
        )
        self.assertTrue(doc["provenance"]["gaps"])
        for operation in doc["operations"].values():
            self.assertEqual(operation["execution"]["mode"], "specification_only")
            self.assertNotIn("binding", operation["execution"])

    def test_validation_rejects_false_activation_and_source_drift(self):
        doc = document()
        self.assertTrue(
            workflow_documents([DESCRIPTOR], snapshot(doc))[0]["validation"]["valid"]
        )
        active = deepcopy(doc)
        active["lifecycle"] = "active"
        with self.assertRaisesRegex(CatalogError, "draft lifecycle"):
            workflow_documents([DESCRIPTOR], snapshot(active))
        drift = deepcopy(doc)
        drift["provenance"]["sources"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(CatalogError, "digest"):
            workflow_documents([DESCRIPTOR], snapshot(drift))

    def test_real_mcp_and_lunar_refuse_unimplemented_physics(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = document()
        manager = SessionManager()
        application_sites = [
            str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")
        ]
        server = (
            "import sys;sys.path.extend(" + repr(application_sites) + ");"
            'sys.path.insert(0,"scripts");'
            'from mcp_server import mcp;mcp.run(transport="stdio")'
        )
        failure = None
        async with manager.open(
            "physics-profile",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]
                self.assertIn("mathformer_run_workflow", [t["name"] for t in tools])
                for identity in (IDENTITY, ALIAS):
                    # This is the native refusal path; no scientific workflow runs,
                    # including when callers pass mutation permission or dry-run.
                    for flags in (
                        {},
                        {"dry_run": True},
                        {
                            "allow_mutating": True,
                            "keep_going": True,
                            "extra_args": ["--must-not-run"],
                        },
                    ):
                        result = await remote.call(
                            "mathformer_run_workflow",
                            {"workflow_id": identity, **flags},
                        )
                        self.assertFalse(result["ok"])
                        self.assertEqual(result["status"], "specification_only")
                        self.assertEqual(result["workflow_id"], IDENTITY)
                        self.assertNotIn("physics_status", result)
                assets = snapshot(doc)
                workflow = workflow_documents([DESCRIPTOR], assets)[0]
                compiled = compile_workflow("mcp:physics-profile", workflow, tools)
                self.assertEqual(compiled["conversion_status"], "converted", compiled)
                self.assertTrue(compiled["prism_source_hash"])
                self.assertTrue(compiled["graph"])
                self.assertFalse(compiled["runnable"], compiled["diagnostics"])
                self.assertEqual(compiled["runtime_status"], "inspection_only")
                self.assertEqual(compiled["bindings"], {})
                self.assertIsNone(compiled["runtime_source"])
                mapped = {
                    m["operation"]
                    for m in compiled["source_mapping"]
                    if m["role"] == "source_call"
                }
                self.assertEqual(mapped, set(doc["operations"]))
                diagnostics = "\n".join(compiled["diagnostics"])
                for name in doc["operations"]:
                    self.assertIn(name + ":", diagnostics)
                authorization_calls = []

                async def authorize():
                    authorization_calls.append(True)

                with self.assertRaisesRegex(
                    ExecutionRejected, "no qualified executable MCP binding"
                ):
                    await execute(
                        compiled,
                        assets,
                        {"source": {"text": "fixture"}},
                        remote,
                        authorize,
                    )
                self.assertEqual(authorization_calls, [])
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
