#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Source fidelity and honest runtime qualification for the selected profile.

WORKFLOW_CONTRACT_PATH is mandatory. This qualification intentionally fails
until actual source-owned implementations are bound. A successful execution
refusal must never count as runnable qualification. There is currently no
provider or compiler invocation in the source to replace with a test fixture.
The actual ERFL parser, MCP server and Lunar/PRISM compiler are used below.
Neither the host-owned descriptor/catalog nor scientific artifacts are written.
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
APPLICATION_SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
sys.path.extend(APPLICATION_SITES)

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

IDENTITY = "profile_theory_library_curation_workflow"
ALIAS = "theory_library_curation"
SOURCE = "examples/reasoning_flows/theory_library_curation.rflow"
DESCRIPTOR = (
    "skills/control/workflow-contract-validator/references/"
    "normalized-workflows/profile/" + IDENTITY + "/workflow.yaml"
)


def document():
    return yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())


def assets(doc):
    values = {
        s["path"]: (ROOT / s["path"]).read_text() for s in doc["provenance"]["sources"]
    }
    values[DESCRIPTOR] = json.dumps(doc)
    return [
        dict(
            path=p,
            content=s,
            encoding="text",
            sha256=hashlib.sha256(s.encode()).hexdigest(),
        )
        for p, s in values.items()
    ]


class TheoryLibraryCurationTests(unittest.TestCase):
    def test_epistemic_dependencies_persistence_and_dispositions(self):
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
        self.assertEqual(flow.goal_handle, "curation_status")
        self.assertEqual(flow.repeats, [])
        occurrences = native.occurrences(flow.route)
        self.assertEqual([o.alias for o in occurrences], list("qgrxfe"))
        self.assertEqual([o.type_code for o in occurrences], list("QGRXFE"))
        steps = doc["flow"]["steps"]
        self.assertEqual(
            [s["id"] for s in steps], [*list("qgrxfe"), "persistence", "terminal"]
        )
        producers = {"curation_request": "inputs.curation_request"}
        for occurrence, step in zip(occurrences, steps):
            operation = doc["operations"][step["operation"]]
            self.assertEqual(
                step["arguments"],
                {p.name: {"ref": producers[p.name]} for p in occurrence.inputs},
            )
            self.assertEqual(
                operation["inputs"],
                {p.name: {"type": p.kind} for p in occurrence.inputs},
            )
            self.assertEqual(
                operation["outputs"],
                {p.name: {"type": p.kind} for p in occurrence.outputs},
            )
            for port in occurrence.outputs:
                producers[port.name] = f"steps.{occurrence.alias}.outputs.{port.name}"
        self.assertEqual(len(flow.resources), 1)
        resource = flow.resources[0]
        self.assertEqual(
            (resource.resource_class, resource.alias, resource.target),
            ("KB", "kb0", "MathformerKB"),
        )
        self.assertEqual(
            [
                (e.occurrence_alias, e.mode, e.resource_alias)
                for e in flow.resource_edges
            ],
            [("e", "persist", "kb0")],
        )
        self.assertEqual(steps[-2]["operation"], "declare_persistence")
        self.assertEqual(
            steps[-2]["arguments"],
            {"curation_status": {"ref": producers["curation_status"]}},
        )
        self.assertEqual(
            [(h.subject, h.status, h.action) for h in flow.handlers],
            [
                ("e", "accepted", "accept"),
                ("e", "repair_required", "stop"),
                ("e", "rejected", "stop"),
            ],
        )
        terminal = steps[-1]
        for case, handler in zip(terminal["cases"], flow.handlers):
            self.assertEqual(case["id"], handler.status)
            self.assertEqual(
                case["when"],
                {
                    "eq": [
                        {"ref": producers["curation_status"]},
                        {"literal": handler.status},
                    ]
                },
            )
            self.assertEqual(case["body"]["operation"], handler.action)
        self.assertEqual(terminal["default"]["operation"], flow.handlers[-1].action)
        self.assertEqual(
            doc["types"]["Decision"]["schema"]["enum"],
            [h.status for h in flow.handlers],
        )
        self.assertEqual(
            doc["outputs"]["curation_status"]["value"],
            {"ref": "flow.outputs.curation_status"},
        )
        self.assertEqual(
            doc["flow"]["outputs"]["curation_status"]["value"],
            {"ref": "steps.terminal.outputs.curation_status"},
        )

    def test_generator_and_provenance_preserve_validated_candidate(self):
        doc = document()
        self.assertEqual(normalizer().theory_library_curation_descriptor(), doc)
        self.assertIn(SOURCE, [row["path"] for row in doc["provenance"]["sources"]])
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
                row["path"],
            )
        files, catalog = normalizer().render_descriptors([doc])
        relative = Path("profile") / IDENTITY / "workflow.yaml"
        self.assertEqual(yaml.safe_load(files[relative]), doc)
        self.assertEqual(set(files), {relative, Path("catalog.json")})
        self.assertFalse(catalog["workflows"][0]["binding_declared"])
        self.assertFalse(catalog["workflows"][0]["runtime_qualified"])
        self.assertEqual(
            doc["policy"]["effects"],
            {
                "filesystem": {"read": ["repository"], "write": []},
                "network": [],
                "external_write": [],
            },
        )
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 8},
        )
        self.assertEqual(
            doc["policy"]["failure"]["retry"],
            {"max_attempts": 1, "retryable_codes": []},
        )
        self.assertEqual(doc["policy"]["resume"]["mode"], "none")

    def test_false_activation_and_provenance_drift_fail_validation(self):
        doc = document()
        self.assertTrue(
            workflow_documents([DESCRIPTOR], assets(doc))[0]["validation"]["valid"]
        )
        active = deepcopy(doc)
        active["lifecycle"] = "active"
        with self.assertRaisesRegex(CatalogError, "draft lifecycle"):
            workflow_documents([DESCRIPTOR], assets(active))
        drift = deepcopy(doc)
        drift["provenance"]["sources"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(CatalogError, "digest"):
            workflow_documents([DESCRIPTOR], assets(drift))

    def test_lunar_runtime_qualification_requires_real_bindings(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = document()
        manager = SessionManager()
        server = (
            "import sys;sys.dont_write_bytecode=True;sys.path.extend("
            + repr(APPLICATION_SITES)
            + ');sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        )
        failure = None
        async with manager.open(
            "theory-curation",
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
                    for flags in (
                        {},
                        {"dry_run": True},
                        {"allow_mutating": True, "keep_going": True},
                    ):
                        outcome = await remote.call(
                            "mathformer_run_workflow",
                            {"workflow_id": identity, **flags},
                        )
                        self.assertEqual(outcome["workflow_id"], IDENTITY)
                        self.assertFalse(outcome["ok"])
                        self.assertEqual(outcome["status"], "specification_only")
                        self.assertNotIn("curation_status", outcome)
                received = assets(doc)
                workflow = workflow_documents([DESCRIPTOR], received)[0]
                compiled = compile_workflow("mcp:theory-curation", workflow, tools)
                self.assertEqual(compiled["conversion_status"], "converted", compiled)
                self.assertTrue(compiled["prism_source_hash"])
                self.assertTrue(compiled["graph"])
                self.assertEqual(
                    {
                        m["operation"]
                        for m in compiled["source_mapping"]
                        if m["role"] == "source_call"
                    },
                    set(doc["operations"]),
                )
                authorization_calls = []

                async def authorize():
                    authorization_calls.append(True)

                with self.assertRaisesRegex(
                    ExecutionRejected, "no qualified executable MCP binding"
                ):
                    await execute(
                        compiled, received, {"curation_request": {}}, remote, authorize
                    )
                self.assertEqual(authorization_calls, [])
                # Required host qualification: do not report the successful
                # refusal checks above as a runnable implementation.
                self.assertTrue(
                    compiled["runnable"],
                    "No executable source is bound to theory_library_curation: "
                    + "\n".join(compiled["diagnostics"]),
                )
            except BaseException as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
