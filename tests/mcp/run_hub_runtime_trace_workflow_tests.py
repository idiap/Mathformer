#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native fixture subprocesses, registered MCP tools and real Lunar/PRISM.

No provider/model or external compiler exists in this workflow. Nothing at those
boundaries needs substitution. Fixture mounts contain byte-identical native
scripts and deterministic local inputs; production artifacts are never used.
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

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml
import mathformer as hub
from hub_runtime_trace_tools import ACTION
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_meta_skills_runtime_trace_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
RECORD = "meta_skills/scripts/record_skill_application.py"
VALIDATE = "meta_skills/scripts/validate_runtime_traces.py"
TRACE = "artifacts/meta_skills/runtime/mathformerphysicslib_coherence.jsonl"
REPORT = "artifacts/meta_skills/runtime_trace_validation.json"
PREFIX = "mathformer_hub_runtime_trace_"
SERVER = """import sys
sys.path.insert(0, 'scripts')
import mcp_server as server
from pathlib import Path
server.hub.REPO_ROOT = Path(sys.argv[1])
server.CALL_LOG_PATH = server.hub.REPO_ROOT / 'artifacts/mcp/calls.jsonl'
server._READONLY = sys.argv[2] == 'readonly'
if sys.argv[2] == 'restricted':
    server._ALLOWED_WRITE_ROOTS = [server.hub.REPO_ROOT / 'elsewhere']
server.mcp.run(transport='stdio')
"""


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    paths = dict.fromkeys(
        [SCHEMA, *(r["path"] for r in document["provenance"]["sources"])]
    )
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text()) for p in paths
    ]


class HubRuntimeTraceTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="hub-runtime-trace-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.document = yaml.safe_load(
            Path(
                os.environ.get("WORKFLOW_CONTRACT_PATH", ROOT / DESCRIPTOR)
            ).read_text()
        )
        self.mount()

    def mount(self):
        for name in (
            RECORD,
            VALIDATE,
            "meta_skills/schemas/runtime_skill_application.schema.json",
        ):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        # The recorder observes these artifacts; it never executes their workflow.
        for name in ("coherence_gate.json", "generative_coherence_critic_plan.json"):
            path = self.root / "artifacts/mathformerphysicslib/coherence" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}")

    def clean_outputs(self):
        shutil.rmtree(self.root / "artifacts/meta_skills", ignore_errors=True)

    def native(self, context, extra_args=(), seen=()):
        # Run the original entrypoint in the same interpreter as the MCP service.
        # Only the fixture filesystem mount changes; no source function is replaced.
        code = """import sys,json
sys.path.insert(0,'scripts')
import mathformer as hub
from pathlib import Path
hub.REPO_ROOT=Path(sys.argv[1])
request=json.loads(sys.argv[2])
print(json.dumps(hub.run_action('meta-skills:runtime-trace',hub.build_registry(),hub.RunContext(**request['context']),extra_args=request['extra_args'],seen=set(request['seen']))))
"""
        process = subprocess.run(
            [
                (
                    str(ROOT / ".venv/bin/python")
                    if (ROOT / ".venv/bin/python").exists()
                    else sys.executable
                ),
                "-c",
                code,
                str(self.root),
                json.dumps(
                    dict(context=context, extra_args=list(extra_args), seen=list(seen))
                ),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(process.stdout)

    def test_authored_generator_and_provenance(self):
        doc = self.document
        self.assertEqual(doc["id"], "hub_meta_skills_runtime_trace_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertIn(
            "scripts/mathformer.py", [r["path"] for r in doc["provenance"]["sources"]]
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("trace_hub_generator", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        selected = [d for d in module.inventory() if d["id"] == doc["id"]]
        self.assertEqual(selected, [doc])

    def test_native_guards_and_audit_failure(self):
        actions = hub.build_registry()
        admission = hub.admit_action("missing", actions, ["extra"], {"missing"})
        self.assertEqual(admission["status"], "unknown_action")
        self.assertEqual(
            hub.reject_action("missing", admission),
            dict(ok=False, status="unknown_action", action_id="missing"),
        )
        context = hub.RunContext()
        with patch.object(hub, "REPO_ROOT", self.root):
            item = actions[ACTION].depends_on[0]
            leaf = actions[item]
            boundary = hub.prepare_leaf_boundary(leaf, context, ())
            (self.root / "undeclared.txt").write_text("fixture concurrent write")
            result = hub.finish_leaf_boundary(
                leaf, boundary, dict(boundary["payload"], ok=True, status="completed")
            )
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "undeclared_writes")
            self.assertEqual(
                result["write_audit"]["unexpected_paths"], ["undeclared.txt"]
            )
            with self.assertRaises(FileNotFoundError):
                hub.launch_leaf_boundary(
                    leaf, {"argv": [str(self.root / "missing-executable")]}
                )

    def test_registered_mcp_and_real_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()

        def config(mode):
            return StdioConfig(
                command=(
                    str(ROOT / ".venv/bin/python")
                    if (ROOT / ".venv/bin/python").exists()
                    else sys.executable
                ),
                args=["-c", SERVER, str(self.root), mode],
                cwd=str(ROOT),
            )

        @asynccontextmanager
        async def opened(key, mode):
            error = None
            async with manager.open(key, config(mode), {}) as remote:
                try:
                    yield remote
                except Exception as caught:
                    error = caught
            if error is not None:
                raise error

        async with opened("runtime-trace", "normal") as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=None):
                assets = snapshot(doc)
                workflow = compile_workflow(
                    "mcp:runtime-trace",
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
            self.assertFalse(compile(self.document, [])[0]["runnable"])

            async def allow():
                pass

            async def run(context=None, extra_args=(), seen=(), document=None):
                w, a = compile(document) if document else (workflow, assets)
                self.assertTrue(w["runnable"], w["diagnostics"])
                return await execute(
                    w,
                    a,
                    {
                        "context": context or asdict(hub.RunContext()),
                        "extra_args": list(extra_args),
                        "seen": list(seen),
                    },
                    remote,
                    allow,
                )

            # Compare native entrypoint envelopes, including argv and write audits.
            for dry_run in (True, False):
                for keep_going in (True, False):
                    self.clean_outputs()
                    context = asdict(
                        hub.RunContext(
                            dry_run=dry_run, keep_going=keep_going, json_output=True
                        )
                    )
                    expected = self.native(context)
                    self.clean_outputs()
                    result = await run(context)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            PREFIX + n
                            for n in (
                                "admit",
                                "initialize",
                                "visit",
                                "advance",
                                "visit",
                                "advance",
                                "finish",
                            )
                        ],
                    )
                    self.assertEqual(expected["status"], "sequence_completed")
                    self.assertEqual(len(expected["children"]), 2)
                    self.assertTrue(
                        all(
                            c["action"]["timeout_seconds"] is None
                            for c in expected["children"]
                        )
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    if dry_run:
                        self.assertFalse((self.root / TRACE).exists())
                    else:
                        rows = [
                            json.loads(s)
                            for s in (self.root / TRACE).read_text().splitlines()
                        ]
                        self.assertEqual(len(rows), 7)
                        self.assertEqual(rows[0]["step"], "skill_application_start")
                        self.assertEqual(rows[-1]["next_action"]["type"], "none")
                        report = json.loads((self.root / REPORT).read_text())
                        self.assertTrue(report["ok"])
                        self.assertEqual(report["trace_count"], 1)
                        self.assertEqual(report["results"][0]["event_count"], 7)
            for args, seen, status in [
                (["extra"], [], "extra_args_for_sequence"),
                (["extra"], [ACTION], "dependency_cycle"),
            ]:
                self.clean_outputs()
                result = await run(extra_args=args, seen=seen)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"],
                    {"result": self.native(asdict(hub.RunContext()), args, seen)},
                )
                self.assertEqual(result["outputs"]["result"]["status"], status)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [PREFIX + "admit", PREFIX + "reject"],
                )
                self.assertFalse((self.root / TRACE).exists())
            # Missing first script triggers real preflight, then optional continuation.
            (self.root / RECORD).unlink()
            for keep_going, count in ((False, 1), (True, 2)):
                self.clean_outputs()
                context = asdict(hub.RunContext(keep_going=keep_going))
                expected = self.native(context)
                self.clean_outputs()
                result = await run(context)
                self.assertEqual(result["outputs"], {"result": expected})
                envelope = result["outputs"]["result"]
                self.assertFalse(envelope["ok"])
                self.assertEqual(envelope["status"], "sequence_failed")
                self.assertEqual(len(envelope["children"]), count)
                self.assertIn(
                    "missing required path",
                    str(envelope["children"][0]["preflight_errors"]),
                )
                if keep_going:
                    self.assertEqual(envelope["children"][1]["returncode"], 1)
                    self.assertEqual(
                        json.loads((self.root / REPORT).read_text())["trace_count"], 0
                    )
            # A later successful validation cannot restore aggregate success.
            self.mount()
            self.clean_outputs()
            self.native(asdict(hub.RunContext()))
            (self.root / RECORD).unlink()
            result = await run(asdict(hub.RunContext(keep_going=True)))
            self.assertFalse(result["outputs"]["result"]["ok"])
            self.assertTrue(result["outputs"]["result"]["children"][1]["ok"])
            # All sorted files and findings are retained after invalid lines.
            self.mount()
            self.clean_outputs()
            trace_dir = self.root / TRACE
            trace_dir.parent.mkdir(parents=True)
            (trace_dir.parent / "a.jsonl").write_text("invalid\n\n{}\n")
            (trace_dir.parent / "z.jsonl").write_text("")
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            self.assertFalse(result["outputs"]["result"]["ok"])
            report = json.loads((self.root / REPORT).read_text())
            self.assertEqual(
                [Path(r["path"]).name for r in report["results"]],
                ["a.jsonl", trace_dir.name, "z.jsonl"],
            )
            self.assertEqual([r["event_count"] for r in report["results"]], [2, 7, 0])
            codes = {f["code"] for f in report["findings"]}
            self.assertTrue(
                {
                    "invalid_jsonl",
                    "missing_field",
                    "invalid_step",
                    "missing_evidence",
                    "artifacts_not_list",
                    "empty_trace",
                }
                <= codes
            )
            # Native uncaught validation script errors become subprocess failures.
            (
                self.root / "meta_skills/schemas/runtime_skill_application.schema.json"
            ).write_text("invalid")
            result = await run()
            child = result["outputs"]["result"]["children"][1]
            self.assertNotEqual(child["returncode"], 0)
            self.assertIn("JSONDecodeError", child["stderr"])
            self.mount()
            self.clean_outputs()
            # The authored graph has exactly two visits (a finite unrolling).
            # Both successful and keep-going failed histories above reach index two;
            # the iterator's exhausted guard below rejects a third visit.
            # Host budget stops before the first native subprocess.
            capped = deepcopy(self.document)
            capped["policy"]["limits"]["max_operation_calls"] = 2
            result = await run(document=capped)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 2
            )
            self.assertFalse((self.root / TRACE).exists())
            admission = (
                await remote.call(PREFIX + "admit", {"extra_args": [], "seen": []})
            )["admission"]
            state = (
                await remote.call(PREFIX + "initialize", {"admission": admission})
            )["state"]
            self.assertEqual(
                state,
                dict(index=0, children=[], dependencies_ok=True, ancestry=[ACTION]),
            )
            context = asdict(hub.RunContext(dry_run=True, keep_going=True))
            for ok in (False, True):
                output = await remote.call(
                    PREFIX + "advance",
                    dict(state=state, child={"ok": ok}, context=context),
                )
                state = output["state"]
                self.assertFalse(state["dependencies_ok"])
                self.assertEqual(output["done"], state["index"] == 2)
            self.assertEqual(state["children"], [{"ok": False}, {"ok": True}])
            with self.assertRaises(MCPConnectionError):
                await remote.call(PREFIX + "visit", dict(state=state, context=context))
        # Service restrictions are enforced by the production registration too.
        for mode in ("readonly", "restricted"):
            async with opened(mode, mode) as remote:
                state = dict(
                    index=0, children=[], dependencies_ok=True, ancestry=[ACTION]
                )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "visit",
                        dict(state=state, context=asdict(hub.RunContext())),
                    )
                output = await remote.call(
                    PREFIX + "visit",
                    dict(state=state, context=asdict(hub.RunContext(dry_run=True))),
                )
                self.assertEqual(output["child"]["status"], "dry_run")
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
