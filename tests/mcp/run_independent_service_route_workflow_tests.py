#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline source parity, real registered tools, and Lunar PRISM execution."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(
        str(python), [str(python), "-B", str(Path(__file__).resolve()), *sys.argv[1:]]
    )
sys.dont_write_bytecode = True
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
import mathformer as hub
from independent_service_route_tools import unpack_match, ACTION_IDS
from independent_service_tree import prepare
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_mcp_independent_service_workflow/workflow.yaml"
STARTUP = ROOT / "tests/mcp/fixtures/independent_service_startup"


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in {r["path"]: r for r in document["provenance"]["sources"]}.values()
    ]


def native_run(inputs, root, mode, original=False):
    namespace = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/independent_service_original.py.txt").read_text(),
        namespace,
    )
    entrypoint = namespace["run_intent_match"] if original else hub.run_intent_match
    registry = {
        key: hub.WorkflowAction(
            **{
                name: tuple(value) if isinstance(value, list) else value
                for name, value in record.items()
            }
        )
        for key, record in inputs["registry"].items()
    }
    context = hub.RunContext(**inputs["context"])
    with (
        patch.object(hub, "REPO_ROOT", root),
        patch.dict(
            os.environ,
            {
                "PYTHONPATH": str(STARTUP),
                "PYTHONDONTWRITEBYTECODE": "1",
                "INDEPENDENT_SERVICE_FIXTURE": mode,
            },
        ),
    ):
        if mode == "launch_error":
            with patch.object(sys, "executable", str(root / "absent-python")):
                return entrypoint(unpack_match(inputs["match"]), registry, context)
        return entrypoint(unpack_match(inputs["match"]), registry, context)


@asynccontextmanager
async def preserve_errors(session):
    # SessionManager redacts transport errors; keep local assertion tracebacks.
    failure = None
    async with session as remote:
        try:
            yield remote
        except Exception as error:
            failure = error
    if failure:
        raise failure


class IndependentServiceTests(unittest.TestCase):
    def test_registered_tools_and_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "route_mcp_independent_service_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 3)
        self.assertEqual(document["flow"]["steps"][1]["on_exhausted"], "fail")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            "scripts/mathformer.py",
            [s["path"] for s in document["provenance"]["sources"]],
        )
        for mode in (
            "success",
            "config_failure",
            "preflight",
            "selfcheck_failure",
            "write_audit",
            "launch_error",
        ):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                prepare(root, mode)
                manager = SessionManager()
                async with preserve_errors(
                    manager.open(
                        "service-route",
                        StdioConfig(
                            command=sys.executable,
                            args=[
                                "-B",
                                str(
                                    ROOT
                                    / "tests/mcp/fixtures/independent_service_server.py"
                                ),
                                str(root),
                                mode,
                            ],
                            cwd=str(ROOT),
                        ),
                        {},
                    )
                ) as remote:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(doc=document, inventory=None):
                        assets = snapshot(doc)
                        selected = workflow_documents([DESCRIPTOR], assets)[0]
                        return (
                            compile_workflow(
                                "mcp:service-route",
                                selected,
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

                    compiled, assets = compile()
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile(inventory=[])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(inputs, doc=None):
                        c, a = compile(doc) if doc else (compiled, assets)
                        return await execute(c, a, inputs, remote, authorize)

                    inputs = await remote.call(
                        "mathformer_independent_service_inputs", {}
                    )
                    self.assertEqual(list(inputs["registry"]), list(ACTION_IDS))
                    self.assertTrue(
                        all(
                            record["timeout_seconds"] == 600
                            for record in inputs["registry"].values()
                        )
                    )
                    self.assertFalse(
                        any(
                            record["depends_on"]
                            for record in inputs["registry"].values()
                        )
                    )
                    inputs["match"]["score"] = 17
                    inputs["match"]["matched_terms"] = ["independent service"]
                    for keep_going in (False, True):
                        inputs["context"]["keep_going"] = keep_going
                        inputs["repository_root"] = str(root) if keep_going else None
                        # Each comparison starts from the same repository contents.
                        (root / "unexpected.txt").unlink(missing_ok=True)
                        if mode == "launch_error":
                            for original in (True, False):
                                with self.assertRaises(FileNotFoundError):
                                    native_run(inputs, root, mode, original)
                            result = await run(inputs)
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(len(result["calls"]), 3)
                            self.assertEqual(result["calls"][-1]["status"], "rejected")
                            continue
                        expected = native_run(inputs, root, mode, original=True)
                        (root / "unexpected.txt").unlink(missing_ok=True)
                        self.assertEqual(native_run(inputs, root, mode), expected)
                        (root / "unexpected.txt").unlink(missing_ok=True)
                        result = await run(inputs)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"result": expected})
                        native = result["outputs"]["result"]
                        count = (
                            3
                            if keep_going or mode in ("success", "selfcheck_failure")
                            else (2 if mode == "write_audit" else 1)
                        )
                        self.assertEqual(len(native["children"]), count)
                        self.assertEqual(len(result["calls"]), 2 + 3 * count)
                        self.assertEqual(
                            [c["action"]["id"] for c in native["children"]],
                            list(ACTION_IDS[:count]),
                        )
                        self.assertEqual(native["ok"], mode == "success")
                        self.assertEqual(
                            native["status"],
                            (
                                "intent_run_completed"
                                if native["ok"]
                                else "intent_run_failed"
                            ),
                        )
                        self.assertEqual(native["route"]["score"], 17)
                        self.assertEqual(
                            native["route"]["matched_terms"], ["independent service"]
                        )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                        if mode == "success":
                            reports = [
                                json.loads(child["stdout"])
                                for child in native["children"]
                            ]
                            dep = reports[1]
                            self.assertTrue(dep["ok"])
                            self.assertFalse(dep["ready"])
                            self.assertEqual(len(dep["python_packages"]), 10)
                            self.assertEqual(len(dep["external_tools"]), 6)
                            self.assertEqual(
                                [r["name"] for r in dep["missing_required"]],
                                ["mcp", "httpx", "uvicorn"],
                            )
                            self.assertTrue(reports[2]["ok"])
                            self.assertFalse(reports[2]["dependencies"]["ready"])
                            self.assertEqual(reports[2]["provider_env_keys"], [])
                            self.assertTrue(
                                all(
                                    child["write_audit"]["ok"]
                                    for child in native["children"]
                                )
                            )
                        elif mode == "preflight":
                            self.assertIn(
                                "missing required path",
                                str(native["children"][0]["preflight_errors"]),
                            )
                            self.assertNotIn("returncode", native["children"][0])
                        elif mode == "write_audit":
                            self.assertEqual(
                                native["children"][1]["status"], "undeclared_writes"
                            )
                            self.assertIn(
                                "unexpected.txt",
                                native["children"][1]["write_audit"][
                                    "unexpected_paths"
                                ],
                            )
                        elif mode == "selfcheck_failure":
                            report = json.loads(native["children"][-1]["stdout"])
                            self.assertIn(
                                "scripts/uncontrolled.py",
                                report["hub_audit"]["uncontrolled_entrypoints"],
                            )

                    # Native dry-run performs admission/preflight, never launches children.
                    inputs["context"].update(dry_run=True, keep_going=True)
                    dry = await run(inputs)
                    expected = native_run(inputs, root, mode, original=True)
                    self.assertEqual(dry["outputs"], {"result": expected})
                    self.assertTrue(
                        all("returncode" not in child for child in expected["children"])
                    )
                    if mode != "preflight":
                        self.assertTrue(
                            all(
                                child["status"] == "dry_run"
                                for child in expected["children"]
                            )
                        )
                        self.assertEqual(len(dry["calls"]), 11)
                    if mode == "success":
                        short = deepcopy(document)
                        short["flow"]["steps"][1]["max_iterations"] = 2
                        exhausted = await run(inputs, short)
                        self.assertEqual(exhausted["status"], "failed")
                        self.assertEqual(exhausted["failure_disposition"], "fail")
                        self.assertIsNone(exhausted["outputs"])
                        self.assertEqual(len(exhausted["calls"]), 7)
                        self.assertNotIn(
                            "mathformer_independent_service_finish",
                            [c["tool"] for c in exhausted["calls"]],
                        )
                        budget = deepcopy(document)
                        budget["policy"]["limits"]["max_operation_calls"] = 2
                        bounded = await run(inputs, budget)
                        self.assertEqual(bounded["status"], "failed")
                        self.assertEqual(
                            sum(
                                bool(c.get("transport_call_performed"))
                                for c in bounded["calls"]
                            ),
                            2,
                        )
                        # Caller data cannot change the registered command or repository mount.
                        tampered = deepcopy(inputs["registry"])
                        tampered[ACTION_IDS[0]]["command"] = ["unregistered"]
                        with self.assertRaises(ValueError):
                            await remote.call(
                                "mathformer_independent_service_run_child",
                                dict(
                                    action_id=ACTION_IDS[0],
                                    registry=tampered,
                                    context=inputs["context"],
                                    repository_root=None,
                                ),
                            )
                        with self.assertRaises(ValueError):
                            await remote.call(
                                "mathformer_independent_service_run_child",
                                dict(
                                    action_id=ACTION_IDS[0],
                                    registry=inputs["registry"],
                                    context=inputs["context"],
                                    repository_root=str(root / "other"),
                                ),
                            )
                        state = {"ok": True, "children": []}
                        advanced = await remote.call(
                            "mathformer_independent_service_advance",
                            dict(
                                state=state,
                                child={"ok": False},
                                context=inputs["context"],
                                action_count=3,
                            ),
                        )
                        self.assertEqual(state, {"ok": True, "children": []})
                        self.assertEqual(
                            advanced,
                            {
                                "state": {"ok": False, "children": [{"ok": False}]},
                                "done": False,
                            },
                        )
                        again = await remote.call(
                            "mathformer_independent_service_advance",
                            dict(
                                state=advanced["state"],
                                child={"ok": True},
                                context=inputs["context"],
                                action_count=3,
                            ),
                        )
                        self.assertFalse(again["state"]["ok"])
                self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
