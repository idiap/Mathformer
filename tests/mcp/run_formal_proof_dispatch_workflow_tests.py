#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real source, MCP, PRISM parser/checker/compiler and Lunar runtime checks.

This source has no model/provider or theorem compiler boundary. Fixtures supply
catalog/descriptor bytes; no scientific implementation or compiler is replaced.
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
APPLICATION_SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(APPLICATION_SITES)

import ast
import asyncio
from copy import deepcopy
import hashlib
import json
import tempfile
import unittest
import yaml

import mcp_server as native
from workflow_catalog import WORKFLOWS, load_catalog, resolve_workflow, descriptor_text
from normalize_workflows_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

IDENTITY = "profile_formal_proof_discovery_workflow"
ALIAS = "formal_proof_discovery"
TOOL = "mathformer_formal_proof_discovery_dispatch"
DESCRIPTOR = str(WORKFLOWS / "profile" / IDENTITY / "workflow.yaml")
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/formal-proof-discovery-dispatch.workflow.json"
)


def oracle():
    # Evaluate only the frozen selected function, using the actual native
    # dependencies. No alternate dispatcher algorithm or fake source steps.
    path = ROOT / "tests/mcp/fixtures/formal_proof_dispatch_original.py.txt"
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    node.decorator_list = []
    namespace = dict(vars(native))
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace
    )
    return namespace["mathformer_run_workflow"]


def snapshot(document):
    def asset(path, content):
        return dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


class ProfileDispatchTests(unittest.TestCase):
    def test_original_entrypoint_equivalence_and_early_stop(self):
        original = oracle()
        for identity in (IDENTITY, ALIAS):
            for flags in (
                {},
                dict(dry_run=True),
                dict(
                    allow_mutating=True, keep_going=True, extra_args=["--must-not-run"]
                ),
            ):
                with self.subTest(identity=identity, flags=flags):
                    expected = original(identity, **flags)
                    self.assertEqual(
                        native.mathformer_run_workflow(identity, **flags), expected
                    )
                    self.assertEqual(
                        native.mathformer_formal_proof_discovery_dispatch(
                            identity, **flags
                        ),
                        {"result": expected},
                    )
                    self.assertFalse(expected["ok"])
                    self.assertEqual(expected["status"], "specification_only")
                    self.assertEqual(expected["workflow_id"], IDENTITY)
                    self.assertNotIn("proof_status", expected)
        unknown = "nonexistent_formal_proof_profile"
        expected = original(unknown)
        self.assertEqual(native.mathformer_run_workflow(unknown), expected)
        self.assertEqual(set(expected), {"ok", "status", "error"})
        self.assertEqual(expected["status"], "workflow_unavailable")
        with self.assertRaises(ValueError):
            native.mathformer_formal_proof_discovery_dispatch(
                "hub_repo_status_workflow"
            )
        # Runtime scientific dependencies are deliberately absent.
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(list(document["operations"]), ["dispatch"])
        profile = document["extensions"]["mathformer.declarative_profile"]
        self.assertFalse(profile["executable"])
        self.assertEqual(
            profile["types"]["Decision"]["schema"]["enum"],
            ["proof_checked", "repair_required", "blocked"],
        )
        self.assertEqual(profile["flow"]["steps"][-1]["kind"], "switch")

    def test_real_catalog_and_descriptor_failure_fixtures(self):
        with tempfile.TemporaryDirectory(prefix="proof-profile-") as directory:
            root = Path(directory)
            base = root / WORKFLOWS
            base.mkdir(parents=True)
            row = dict(
                id=IDENTITY,
                aliases=[ALIAS],
                category="profile",
                path="profile/workflow.yaml",
                descriptor_digest="sha256:" + "0" * 64,
            )
            catalog = dict(
                schema_version="mathformer.normalized-workflow-catalog/v1",
                counts={"profile": 1},
                workflows=[row],
            )
            registry = base / "catalog.json"

            def save():
                registry.write_text(json.dumps(catalog))

            save()
            self.assertEqual(resolve_workflow(ALIAS, root), row)
            with self.assertRaises(FileNotFoundError):
                descriptor_text(row, root)
            target = base / row["path"]
            target.parent.mkdir()
            target.write_text("source-bound descriptor\n")
            with self.assertRaisesRegex(ValueError, "descriptor drift"):
                descriptor_text(row, root)
            row["descriptor_digest"] = (
                "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()
            )
            save()
            self.assertEqual(
                descriptor_text(resolve_workflow(IDENTITY, root), root),
                target.read_text(),
            )
            target.write_text("tampered")
            with self.assertRaisesRegex(ValueError, "descriptor drift"):
                descriptor_text(row, root)
            row["path"] = "../escape.yaml"
            save()
            with self.assertRaisesRegex(ValueError, "escapes"):
                load_catalog(root)
            with self.assertRaisesRegex(ValueError, "escapes"):
                descriptor_text(row, root)
            row["path"] = "profile/workflow.yaml"
            row["aliases"] = [ALIAS, IDENTITY]
            save()
            with self.assertRaisesRegex(ValueError, "ambiguous"):
                load_catalog(root)
            row["aliases"] = [ALIAS]
            catalog["counts"]["profile"] = 2
            save()
            with self.assertRaisesRegex(ValueError, "count mismatch"):
                load_catalog(root)

    def test_authored_generator_preserves_binding_and_provenance(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document, json.loads(AUTHORED.read_text()))
        generated = source().formal_proof_discovery_descriptor()
        self.assertEqual(generated, document)
        files, catalog = source().render_descriptors([generated])
        row = catalog["workflows"][0]
        self.assertTrue(row["binding_declared"])
        self.assertFalse(row["runtime_qualified"])  # Scientific profile is unavailable.
        self.assertEqual(yaml.safe_load(files[Path(row["path"])]), document)
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            "scripts/mcp_server.py",
            [r["path"] for r in document["provenance"]["sources"]],
        )

    def test_registered_mcp_lunar_compile_execute_and_stopping(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        manager = SessionManager()
        # Import production registrations without main(): no service config,
        # credential reads, provider setup, subprocess actions, or promotion.
        server = (
            "import sys;sys.path.extend(" + repr(APPLICATION_SITES) + ");"
            'sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        )
        failure = None
        async with manager.open(
            "proof-profile",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]
                self.assertIn(TOOL, [t["name"] for t in tools])

                def compile(document, inventory=None):
                    assets = snapshot(document)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    compiled = compile_workflow(
                        "mcp:proof-profile",
                        selected,
                        tools if inventory is None else inventory,
                    )
                    return compiled, assets

                workflow, assets = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), {"dispatch"})
                missing, _ = compile(document, [])
                self.assertFalse(missing["runnable"])

                async def allow():
                    pass

                for identity, flags in (
                    (IDENTITY, {}),
                    (
                        ALIAS,
                        dict(
                            dry_run=True,
                            allow_mutating=True,
                            keep_going=True,
                            extra_args=["--not-executed"],
                        ),
                    ),
                ):
                    inputs = dict(
                        workflow_id=identity,
                        dry_run=False,
                        allow_mutating=False,
                        keep_going=False,
                        extra_args=None,
                    )
                    inputs.update(flags)
                    expected = oracle()(**inputs)
                    direct = await remote.call("mathformer_run_workflow", inputs)
                    self.assertEqual(direct, expected)
                    self.assertEqual(
                        await remote.call(TOOL, inputs), {"result": expected}
                    )
                    result = await execute(workflow, assets, inputs, remote, allow)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertFalse(result["outputs"]["result"]["ok"])
                    self.assertEqual([c["tool"] for c in result["calls"]], [TOOL])
                    self.assertTrue(result["execution_performed"])
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                # Source resolution errors stay native negative result data.
                unknown = await remote.call(
                    "mathformer_run_workflow",
                    {"workflow_id": "nonexistent_formal_proof_profile"},
                )
                self.assertEqual(unknown, oracle()("nonexistent_formal_proof_profile"))
                # The restricted adapter cannot broaden into a hub mutation.
                with self.assertRaises(MCPConnectionError):
                    await remote.call(TOOL, {"workflow_id": "hub_repo_status_workflow"})
                invalid = dict(inputs, workflow_id="hub_repo_status_workflow")
                with self.assertRaises(ExecutionRejected):
                    await execute(workflow, assets, invalid, remote, allow)
                # There is no source repeat/exhaustion path. Exercise the actual
                # runtime one-call ceiling with a second inspection in a test-only
                # composition; only the first call may cross the MCP boundary.
                bounded = deepcopy(document)
                second = deepcopy(bounded["flow"]["steps"][0])
                second["id"] = "second_inspection"
                bounded["flow"]["steps"].append(second)
                limited, received = compile(bounded)
                self.assertTrue(limited["runnable"], limited["diagnostics"])
                result = await execute(limited, received, inputs, remote, allow)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    1,
                )
                self.assertIn("budget", str(result).lower())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                limited, received = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(limited, received, inputs, remote, pending)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
