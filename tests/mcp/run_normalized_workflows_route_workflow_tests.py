#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native, registered MCP and real Lunar/PRISM contract execution."""

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
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import io
import json
from contextlib import redirect_stdout
import tempfile
from types import SimpleNamespace
import unittest
import yaml
import mathformer as hub
from normalized_workflows_route_tools import (
    ACTION,
    ROUTE,
    selected_match,
    checked_registry,
    check_state,
)
from normalized_workflows_route_tree import populate, load_checker, CHECKER, OUTPUT
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = str(
    OUTPUT / "route/route_validate_normalized_workflows_workflow/workflow.yaml"
)
SCHEMA = str(OUTPUT / "hub-interface.schema.json")
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DOCUMENT = yaml.safe_load(CONTRACT.read_text())
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 23,
    "matched_terms": ["normalized", "workflows"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "invoke_action", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec(
        (
            ROOT / "tests/mcp/fixtures/normalized_workflows_route_original.py.txt"
        ).read_text(),
        scope,
    )
    return SimpleNamespace(**scope)


def snapshot(document):
    values = {
        s["path"]: (ROOT / s["path"]).read_text()
        for s in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=p,
            content=t,
            encoding="text",
            sha256=hashlib.sha256(t.encode()).hexdigest(),
        )
        for p, t in values.items()
    ]


class NormalizedRouteTests(unittest.TestCase):
    maxDiff = None

    def test_generator_identity_policy_provenance_and_native_state(self):
        module = load_checker(ROOT)
        self.assertEqual(module.normalized_workflows_route_descriptor(), DOCUMENT)
        self.assertEqual(DOCUMENT["id"], "route_validate_normalized_workflows_workflow")
        self.assertEqual(DOCUMENT["aliases"], [ROUTE])
        self.assertEqual(DOCUMENT["lifecycle"], "active")
        self.assertEqual(
            DOCUMENT["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            DOCUMENT["policy"]["failure"]["retry"],
            {"max_attempts": 1, "retryable_codes": []},
        )
        self.assertEqual(DOCUMENT["policy"]["resume"]["mode"], "none")
        self.assertEqual(
            DOCUMENT["policy"]["effects"],
            {
                "filesystem": {
                    "read": ["repository", "native_runtime_inputs"],
                    "write": [],
                },
                "network": [],
                "external_write": [],
            },
        )
        self.assertIn(
            {
                "path": "scripts/mathformer.py",
                "selector": "run_intent_match",
                "digest": "sha256:"
                + hashlib.sha256(
                    (ROOT / "scripts/mathformer.py").read_bytes()
                ).hexdigest(),
            },
            DOCUMENT["provenance"]["sources"],
        )
        for row in DOCUMENT["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        item = checked_registry(REGISTRY)[ACTION]
        self.assertEqual(item.command, ("{python}", CHECKER, "--check", "--json"))
        self.assertFalse(item.depends_on)
        self.assertFalse(item.writes)
        self.assertIsNone(item.timeout_seconds)
        self.assertEqual(checked_registry({}), {})
        for keep in [False, True]:
            for child in [{"ok": True}, {"ok": False}, {}]:
                state = hub.initialize_intent_state()
                updated, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertEqual(state, {"ok": True, "children": []})
                self.assertEqual(
                    updated, {"ok": bool(child.get("ok")), "children": [child]}
                )
                self.assertTrue(done)
                check_state(updated)
                with self.assertRaisesRegex(ValueError, "bounds"):
                    check_state(updated, selecting=True)
        with self.assertRaisesRegex(ValueError, "accumulator"):
            check_state({"ok": True, "children": [{"ok": False}]})
        for field in ["command", "depends_on", "writes"]:
            forged = deepcopy(REGISTRY)
            forged[ACTION][field] = ["forged"]
            with self.assertRaisesRegex(ValueError, "projection"):
                checked_registry(forged)

    def test_real_validator_render_drift_schema_semantics_provenance_and_finish(self):
        module = load_checker(ROOT)
        files, catalog = module.render_descriptors([DOCUMENT])
        descriptor = next(p for p in files if p.name == "workflow.yaml")
        with tempfile.TemporaryDirectory(
            dir=ROOT, prefix=".normalized-check-test-"
        ) as directory:
            output = Path(directory).resolve()
            # Only this candidate is checked deeply, against real repository
            # source digests and schemas. All native validator logic is real.
            for relative, content in files.items():
                target = output / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            # Relative schema refs are resolved beside the isolated descriptor.
            (output / "hub-interface.schema.json").write_text(
                (ROOT / SCHEMA).read_text()
            )
            report = module.check_rendered(files, catalog, output)
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["descriptor_count"], 1)
            self.assertTrue(report["schema_and_dataflow_validated"])
            for mutation, expected in [
                ("missing", "missing or stale"),
                ("stale", "missing or stale"),
                ("schema", "lifecycle"),
                ("semantic", "ref"),
                ("provenance", "digest"),
            ]:
                changed = deepcopy(DOCUMENT)
                if mutation == "missing":
                    (output / descriptor).unlink()
                elif mutation == "stale":
                    (output / descriptor).write_text("{}")
                else:
                    if mutation == "schema":
                        changed["lifecycle"] = "invalid"
                    elif mutation == "semantic":
                        changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                            "state"
                        ] = {"ref": "steps.missing.outputs.state"}
                    else:
                        changed["provenance"]["sources"][0]["digest"] = (
                            "sha256:" + "0" * 64
                        )
                    changed_files, changed_catalog = module.render_descriptors(
                        [changed]
                    )
                    for relative, content in changed_files.items():
                        (output / relative).write_text(content)
                report = module.check_rendered(
                    files if mutation in ["missing", "stale"] else changed_files,
                    catalog if mutation in ["missing", "stale"] else changed_catalog,
                    output,
                )
                self.assertFalse(report["ok"])
                self.assertTrue(
                    any(expected in e.lower() for e in report["errors"]), report
                )
                for relative, content in files.items():
                    (output / relative).write_text(content)
            unexpected = output / "extra/workflow.yaml"
            unexpected.parent.mkdir()
            unexpected.write_text("{}")
            (output / "catalog.json").write_text("{}")
            report = module.check_rendered(files, catalog, output)
            self.assertEqual(len(report["errors"]), 2)
            self.assertIn("catalog.json", report["errors"][0])
            self.assertIn("unexpected descriptor", report["errors"][1])
            for ok in [False, True]:
                capture = io.StringIO()
                with redirect_stdout(capture):
                    code = module.finish({"ok": ok, "errors": []}, {"json": True})
                self.assertEqual(code, 0 if ok else 1)
                self.assertEqual(json.loads(capture.getvalue())["ok"], ok)
        # Real graph checks reject references and cycles before projection.
        item = hub.build_registry()[ACTION]
        for deps, message in [(("missing",), "unknown"), ((ACTION,), "cycle")]:
            with self.assertRaisesRegex(ValueError, message):
                module.audit_action_dependencies(
                    {ACTION: replace(item, depends_on=deps)}
                )

    def test_deterministic_external_compiler_boundary(self):
        # This route has no provider/compiler dependency. Test the generic native
        # launcher separately, substituting only an external compiler process.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            saved = hub.subprocess
            try:
                for mode in ["success", "reject", "write", "launch_error", "timeout"]:
                    (root / "undeclared.txt").unlink(missing_ok=True)
                    leaf = replace(
                        hub.build_registry()[ACTION],
                        command=("fixture-reasoning-compiler", mode),
                        required_paths=(),
                        timeout_seconds=3 if mode == "timeout" else None,
                    )
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "launch failed"):
                            hub.run_action(
                                ACTION,
                                {ACTION: leaf},
                                hub.RunContext(),
                                repository_root=root,
                            )
                    else:
                        result = hub.run_action(
                            ACTION,
                            {ACTION: leaf},
                            hub.RunContext(),
                            repository_root=root,
                        )
                        self.assertEqual(result["ok"], mode == "success")
                        self.assertEqual(
                            result["status"],
                            {"timeout": "timeout", "write": "undeclared_writes"}.get(
                                mode, "completed"
                            ),
                        )
                        if mode == "timeout":
                            self.assertEqual(
                                (
                                    result["returncode"],
                                    result["stdout"],
                                    result["stderr"],
                                ),
                                (None, "partial", "deadline"),
                            )
                        else:
                            self.assertEqual(
                                json.loads(result["stdout"])["artifact"]["nodes"],
                                ["input", "check"],
                            )
                            self.assertEqual(
                                result["returncode"], 7 if mode == "reject" else 0
                            )
                        if mode == "write":
                            self.assertEqual(
                                result["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                    self.assertEqual(
                        calls,
                        [{"argv": list(leaf.command), "timeout": leaf.timeout_seconds}],
                    )
            finally:
                hub.subprocess = saved

    def test_registered_mcp_real_lunar_compile_runtime_and_original_parity(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        error = None
        code = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "normalized-route",
            StdioConfig(command=sys.executable, args=["-c", code], cwd=str(ROOT)),
            {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
        ) as remote:
            try:
                await self.connected(remote)
            except Exception as exc:
                error = exc
        self.assertFalse(manager.active)
        if error:
            raise error

    async def connected(self, remote):
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile_document(document, advertised=tools):
            assets = snapshot(document)
            docs = workflow_documents([DESCRIPTOR], assets)
            self.assertEqual(len(docs), 1)
            self.assertTrue(docs[0]["validation"]["valid"], docs[0])
            compiled = compile_workflow("normalized-route", docs[0], advertised)
            self.assertEqual(compiled["conversion_status"], "converted", compiled)
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["graph"])
            return compiled, assets

        compiled, assets = compile_document(DOCUMENT)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertEqual(compiled["runtime_status"], "ready")
        for operation in ORDER:
            target = DOCUMENT["operations"][operation]["execution"]["binding"]["target"]
            unavailable, _ = compile_document(
                DOCUMENT, [t for t in tools if t["name"] != target]
            )
            self.assertFalse(unavailable["runnable"])

        async def authorize():
            pass

        async def run(inputs, changed=None):
            c, a = compile_document(changed) if changed else (compiled, assets)
            self.assertTrue(c["runnable"], c["diagnostics"])
            return await execute(c, a, inputs, remote, authorize)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            base = {
                "context": vars(hub.RunContext()),
                "match": MATCH,
                "registry": REGISTRY,
                "repository_root": str(root),
            }
            for ready in [False, True]:
                count = populate(root, ROOT) if ready else None
                for dry in [False, True]:
                    for keep in [False, True]:
                        inputs = deepcopy(base)
                        inputs["context"].update(dry_run=dry, keep_going=keep)
                        before = hub.snapshot_repository(root)
                        result = await run(inputs)
                        expected = original().run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(**inputs["context"]),
                            repository_root=root,
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"result": expected})
                        actual = result["outputs"]["result"]
                        child = actual["children"][0]
                        self.assertEqual(len(actual["children"]), 1)
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], ORDER
                        )
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]],
                            ["mathformer_normalized_route_" + op for op in ORDER],
                        )
                        self.assertEqual(actual["ok"], ready and dry)
                        self.assertEqual(actual["route"]["score"], MATCH["score"])
                        self.assertEqual(
                            actual["route"]["matched_terms"], MATCH["matched_terms"]
                        )
                        self.assertEqual(hub.snapshot_repository(root), before)
                        self.assertEqual(
                            child["argv"],
                            [sys.executable, CHECKER, "--check", "--json"],
                        )
                        if ready and not dry:
                            self.assertTrue(child["stdout"], child)
                            report = json.loads(child["stdout"])
                            self.assertEqual(child["returncode"], 1)
                            self.assertFalse(report["ok"])
                            self.assertEqual(report["descriptor_count"], count)
                            self.assertEqual(len(report["errors"]), count + 1)
                            self.assertTrue(
                                all("missing or stale" in e for e in report["errors"])
                            )
                            self.assertTrue(child["write_audit"]["ok"])
                        elif ready:
                            self.assertEqual(child["status"], "dry_run")
                            self.assertNotIn("returncode", child)
                        else:
                            self.assertTrue(child["preflight_errors"])
                            self.assertNotIn("returncode", child)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
            # Real unhandled validator exception becomes a captured unsuccessful
            # subprocess result; no retry and no scientific workflow is launched.
            (root / "skills/REASONING_TYPES.yaml").write_text("reasoning_styles: [")
            result = await run(base)
            child = result["outputs"]["result"]["children"][0]
            self.assertNotEqual(child["returncode"], 0)
            self.assertIn("ParserError", child["stderr"])
            self.assertFalse(result["outputs"]["result"]["ok"])
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
            for kind in ["registry", "route", "cursor", "missing_registry"]:
                inputs = deepcopy(base)
                inputs["context"]["dry_run"] = True
                changed = None
                if kind == "registry":
                    inputs["registry"][ACTION]["command"] = ["forged"]
                elif kind == "route":
                    inputs["match"]["route"]["title"] = "forged"
                elif kind == "missing_registry":
                    inputs["registry"] = {}
                    with self.assertRaises(KeyError):
                        original().run_intent_match(
                            selected_match(MATCH),
                            {},
                            hub.RunContext(dry_run=True),
                            repository_root=root,
                        )
                else:
                    changed = deepcopy(DOCUMENT)
                    changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                        "state"
                    ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    result["calls"][-1]["operation"],
                    {
                        "registry": "invoke_action",
                        "route": "select",
                        "cursor": "select",
                        "missing_registry": "finish",
                    }[kind],
                )
            unknown = await remote.call(
                "mathformer_normalized_route_invoke_action",
                {
                    "action_id": ACTION,
                    "context": vars(hub.RunContext(dry_run=True)),
                    "registry": {},
                    "repository_root": str(root),
                },
            )
            self.assertEqual(
                unknown,
                {
                    "child": {
                        "ok": False,
                        "status": "unknown_action",
                        "action_id": ACTION,
                    }
                },
            )
            inputs = deepcopy(base)
            inputs["context"]["dry_run"] = True
            changed = deepcopy(DOCUMENT)
            changed["flow"]["steps"][1]["until"] = {"literal": False}
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["outputs"])
            self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
            for cap in [1, 4]:
                changed = deepcopy(DOCUMENT)
                changed["policy"]["limits"]["max_operation_calls"] = cap
                result = await run(inputs, changed)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    cap,
                )
            timed = deepcopy(DOCUMENT)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            workflow, received = compile_document(timed)

            async def waiting_authority():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(workflow, received, inputs, remote, waiting_authority)
            for omitted in [False, True]:
                inputs["repository_root"] = None
                if omitted:
                    inputs.pop("repository_root")
                result = await run(inputs)
                self.assertEqual(
                    result["outputs"],
                    {
                        "result": hub.run_intent_match(
                            selected_match(MATCH),
                            checked_registry(REGISTRY),
                            hub.RunContext(dry_run=True),
                        )
                    },
                )


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
