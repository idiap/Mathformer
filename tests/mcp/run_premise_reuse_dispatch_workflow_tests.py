#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native dispatch, MCP bindings, and real Lunar/PRISM execution.

The selected source has no provider, model, external compiler, or theorem prover
boundary. Catalog/descriptor files are the fixtures; no source step, PRISM
parser/checker/compiler, or runtime is substituted. No service main/config loads.
"""

from tempfile import gettempdir

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
from functools import partial
import hashlib
import json
import tempfile
import unittest
import yaml

import mcp_server as native
from workflow_catalog import WORKFLOWS, resolve_workflow, descriptor_text
from normalize_workflows_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected
from mcp_connections.workflow_contract.validator import validate

IDENTITY = "profile_premise_retrieval_and_verified_reuse_workflow"
ALIAS = "premise_retrieval_and_verified_reuse"
PREFIX = "mathformer_premise_reuse_"
DESCRIPTOR = str(WORKFLOWS / "profile" / IDENTITY / "workflow.yaml")
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/premise-reuse-dispatch.workflow.json"
)


def oracle(root=None):
    """Run the frozen original function with real catalog functions.

    Binding their existing root argument selects fixture files; it does not
    replace the resolver, digest checker, return steps, or action implementations.
    """
    path = ROOT / "tests/mcp/fixtures/premise_reuse_dispatch_original.py.txt"
    node = next(
        n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)
    )
    namespace = dict(vars(native))
    if root is not None:
        namespace.update(
            resolve_workflow=partial(resolve_workflow, root=root),
            descriptor_text=partial(descriptor_text, root=root),
        )
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


class CatalogFixture:
    """A real versioned, digest-bound snapshot consumed by production functions."""

    def __init__(self, root):
        self.root = root
        base = root / WORKFLOWS
        base.mkdir(parents=True)
        self.descriptor = base / "profile/fixture/workflow.yaml"
        self.descriptor.parent.mkdir(parents=True)
        self.descriptor.write_text("schema_version: workflow-skill/v1\n# fixture 雪\n")
        self.row = dict(
            id=IDENTITY,
            aliases=[ALIAS],
            category="profile",
            coverage="partial",
            path="profile/fixture/workflow.yaml",
            descriptor_digest="sha256:"
            + hashlib.sha256(self.descriptor.read_bytes()).hexdigest(),
        )
        self.catalog = dict(
            schema_version="mathformer.normalized-workflow-catalog/v1",
            counts={"profile": 1},
            workflows=[self.row],
        )
        self.registry = base / "catalog.json"
        self.save()

    def save(self):
        self.registry.write_text(json.dumps(self.catalog))

    @property
    def context(self):
        return {"repository_root": str(self.root)}


class PremiseReuseDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract_path = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
        cls.document = yaml.safe_load(cls.contract_path.read_text())

    def setUp(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(
            prefix="premise-dispatch-fixture-", dir=base
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_native_original_equivalence_and_exact_negative_status(self):
        original = oracle()
        for identity in (IDENTITY, ALIAS):
            for flags in (
                {},
                dict(
                    dry_run=True,
                    allow_mutating=True,
                    keep_going=True,
                    extra_args=["--never-executed"],
                ),
            ):
                expected = original(identity, **flags)
                self.assertEqual(
                    native.mathformer_run_workflow(identity, **flags), expected
                )
                read = native.mathformer_premise_reuse_resolve_and_read(identity)[
                    "outcome"
                ]
                self.assertTrue(read["loaded"])
                self.assertIsNone(read["error"])
                self.assertEqual(read["row"], resolve_workflow(identity))
                self.assertEqual(
                    native.mathformer_premise_reuse_return_specification(read),
                    {"result": expected},
                )
                self.assertFalse(expected["ok"])
                self.assertEqual(expected["status"], "specification_only")
                self.assertEqual(
                    set(expected),
                    {
                        "schema_version",
                        "ok",
                        "status",
                        "workflow_id",
                        "coverage",
                        "message",
                    },
                )
                with self.assertRaises(ValueError):
                    native.mathformer_premise_reuse_return_unavailable(read)
        unknown = "nonexistent_premise_profile"
        self.assertEqual(native.mathformer_run_workflow(unknown), original(unknown))
        self.assertEqual(original(unknown)["status"], "workflow_unavailable")
        with self.assertRaises(ValueError):
            native.mathformer_premise_reuse_resolve_and_read("hub_repo_status_workflow")
        with self.assertRaises(ValueError):
            native.mathformer_premise_reuse_resolve_and_read(
                IDENTITY, {"repository_root": str(Path(gettempdir()))}
            )

    def test_authored_generator_and_full_provenance(self):
        document = self.document
        self.assertEqual(document["id"], IDENTITY)
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document, json.loads(AUTHORED.read_text()))
        generated = source().premise_reuse_dispatch_descriptor()
        self.assertEqual(generated, document)
        files, catalog = source().render_descriptors([generated])
        row = catalog["workflows"][0]
        self.assertTrue(row["binding_declared"])
        self.assertFalse(
            row["runtime_qualified"]
        )  # Inspection is not scientific reuse.
        self.assertEqual(yaml.safe_load(files[Path(row["path"])]), document)
        self.assertEqual(document["policy"]["limits"]["max_operation_calls"], 2)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        # The explicit candidate may live in the host harness outside this repo.
        # Validate those exact bytes in a repository-local scratch location.
        checked = self.root / "workflow.yaml"
        checked.write_bytes(self.contract_path.read_bytes())
        validation = validate(
            checked, repository_root=ROOT, require_declared_bindings=True
        )
        self.assertTrue(validation["valid"], validation["errors"])

    def test_registered_tools_lunar_compile_execution_branches_and_bounds(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        server = (
            "import sys;sys.path.extend(" + repr(APPLICATION_SITES) + ");"
            'sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        )
        failure = None
        async with manager.open(
            "premise-inspection",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]
                self.assertTrue(
                    {PREFIX + n for n in self.document["operations"]}
                    <= {t["name"] for t in tools}
                )

                def compile(document, inventory=None):
                    assets = snapshot(document)
                    workflow = compile_workflow(
                        "mcp:premise-inspection",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools if inventory is None else inventory,
                    )
                    return workflow, assets

                workflow, assets = compile(self.document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(
                    set(workflow["bindings"]), set(self.document["operations"])
                )
                self.assertFalse(
                    compile(
                        self.document,
                        [
                            t
                            for t in tools
                            if t["name"] != PREFIX + "return_unavailable"
                        ],
                    )[0]["runnable"]
                )

                async def allow():
                    pass

                async def run(inputs, document=None):
                    w, a = (
                        compile(document)
                        if document is not None
                        else (workflow, assets)
                    )
                    return await execute(w, a, inputs, remote, allow)

                async def compare(inputs, root=None):
                    expected = oracle(root)(
                        **{k: v for k, v in inputs.items() if k != "context"}
                    )
                    result = await run(inputs)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertFalse(result["outputs"]["result"]["ok"])
                    branch = (
                        "return_specification"
                        if expected["status"] == "specification_only"
                        else "return_unavailable"
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [PREFIX + "resolve_and_read", PREFIX + branch],
                    )
                    self.assertTrue(
                        all(c["status"] == "accepted" for c in result["calls"])
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    return result

                for identity in (IDENTITY, ALIAS):
                    await compare({"workflow_id": identity})
                    inputs = dict(
                        workflow_id=identity,
                        dry_run=True,
                        allow_mutating=True,
                        keep_going=True,
                        extra_args=["--no-native-action"],
                    )
                    self.assertEqual(
                        await remote.call("mathformer_run_workflow", inputs),
                        oracle()(**inputs),
                    )
                    await compare(inputs)

                fixture = CatalogFixture(self.root / "snapshot")
                inputs = {"workflow_id": ALIAS, "context": fixture.context}
                await compare(inputs, fixture.root)
                # A snapshot lacking this identity takes the native resolution failure.
                fixture.row["aliases"] = []
                fixture.row["id"] = "profile_other_workflow"
                fixture.save()
                missing = await compare(inputs, fixture.root)
                self.assertIn(
                    "unknown normalized workflow", missing["outputs"]["result"]["error"]
                )
                fixture.row.update(id=IDENTITY, aliases=[ALIAS])
                fixture.save()
                # Read errors, catalog errors, and digest failures are ordinary data.
                for change in (
                    "missing_descriptor",
                    "digest_drift",
                    "bad_json",
                    "missing_catalog",
                    "path_escape",
                ):
                    with self.subTest(change=change):
                        fixture.descriptor.write_text("changed bytes")
                        fixture.row["path"] = "profile/fixture/workflow.yaml"
                        fixture.save()
                        if change == "missing_descriptor":
                            fixture.descriptor.unlink()
                        if change == "bad_json":
                            fixture.registry.write_text("{broken")
                        if change == "missing_catalog":
                            fixture.registry.unlink()
                        if change == "path_escape":
                            fixture.row["path"] = "../outside.yaml"
                            fixture.save()
                        result = await compare(inputs, fixture.root)
                        self.assertEqual(
                            result["outputs"]["result"]["status"],
                            "workflow_unavailable",
                        )
                        self.assertEqual(
                            set(result["outputs"]["result"]), {"ok", "status", "error"}
                        )
                outcome = native.read_workflow_dispatch(ALIAS, fixture.root)
                with self.assertRaises(ValueError):
                    native.mathformer_premise_reuse_return_specification(outcome)
                # A malformed required catalog structure causes uncaught KeyError.
                # Verify propagation, no retry, and no terminal tool after failure.
                fixture.registry.write_text(
                    json.dumps(
                        {"schema_version": "mathformer.normalized-workflow-catalog/v1"}
                    )
                )
                with self.assertRaises(KeyError):
                    oracle(fixture.root)(ALIAS)
                with self.assertRaises(KeyError):
                    native.read_workflow_dispatch(ALIAS, fixture.root)
                failed = await run(inputs)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIsNone(failed["outputs"])
                self.assertEqual(
                    [c["tool"] for c in failed["calls"]], [PREFIX + "resolve_and_read"]
                )
                self.assertEqual(failed["calls"][0]["status"], "rejected")
                self.assertTrue(failed["runtime"]["effect_records"])
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "resolve_and_read",
                        {"workflow_id": "hub_repo_status_workflow"},
                    )
                with self.assertRaises(ExecutionRejected):
                    await run({"workflow_id": "hub_repo_status_workflow"})

                # There is no source iteration/exhaustion. Lower the host call
                # ceiling only in a test contract: read succeeds, return is blocked.
                limited = deepcopy(self.document)
                limited["policy"]["limits"]["max_operation_calls"] = 1
                exhausted = await run({"workflow_id": IDENTITY}, limited)
                self.assertEqual(exhausted["status"], "failed", exhausted)
                self.assertIsNone(exhausted["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed"))
                        for c in exhausted["calls"]
                    ),
                    1,
                )
                self.assertIn("budget", str(exhausted).lower())
                timed = deepcopy(self.document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                w, a = compile(timed)
                self.assertTrue(w["runnable"], w["diagnostics"])

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(w, a, {"workflow_id": IDENTITY}, remote, pending)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
