#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated Git fixtures through actual native steps, MCP, Lunar and PRISM."""

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
from copy import deepcopy
import hashlib
import json
import subprocess
import tempfile
import unittest
import yaml
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_repo_status_workflow/workflow.yaml"
CONTEXT = dict(
    dry_run=False,
    json_output=False,
    keep_going=False,
    allow_mutating=False,
    write_report=False,
)


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
        for row in document["provenance"]["sources"]
    ]


class RepoStatusTests(unittest.TestCase):
    maxDiff = None

    def test_real_mcp_lunar_and_native_equivalence(self):
        with tempfile.TemporaryDirectory(prefix="repo-status-") as directory:
            self.directory = Path(directory) / "repo"
            subprocess.run(["git", "init", "--quiet", str(self.directory)], check=True)
            (self.directory / "untracked.txt").write_text("fixture\n")
            asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_repo_status_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            dict(wall_time_seconds=3600, max_operation_calls=4),
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(
            document,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/repo-status.workflow.json"
                ).read_text()
            ),
        )
        manager = SessionManager()
        server = str(ROOT / "tests/mcp/fixtures/repo_status_server.py")
        failure = None
        async with manager.open(
            "status",
            StdioConfig(command=sys.executable, args=[server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=tools):
                    assets = snapshot(doc)
                    workflow = compile_workflow(
                        "mcp:status",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory,
                    )
                    return workflow, assets

                workflow, assets = compile(document)
                self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                self.assertTrue(workflow["runtime_source"])
                self.assertEqual(set(workflow["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(overrides=None, doc=None):
                    values = dict(
                        context=CONTEXT,
                        extra_args=[],
                        seen=[],
                        repository_root=str(self.directory),
                        timeout_seconds=None,
                    )
                    values.update(overrides or {})
                    selected, received = compile(doc) if doc else (workflow, assets)
                    return await execute(selected, received, values, remote, authorize)

                # Every branch uses actual source implementations; native failure is data.
                for overrides, call_names in [
                    ({}, ["admit", "prepare", "launch", "audit"]),
                    (
                        {"context": dict(CONTEXT, dry_run=True)},
                        ["admit", "prepare", "return_prepared"],
                    ),
                    (
                        {"extra_args": ["--branch"]},
                        ["admit", "prepare", "return_prepared"],
                    ),
                    ({"seen": ["repo:status"]}, ["admit", "reject"]),
                ]:
                    actual = await run(overrides)
                    expected = (
                        await remote.call(
                            "fixture_original_status",
                            dict(
                                context=overrides.get("context", CONTEXT),
                                extra_args=overrides.get("extra_args", []),
                                seen=overrides.get("seen", []),
                                repository_root=str(self.directory),
                            ),
                        )
                    )["result"]
                    self.assertEqual(actual["status"], "accepted", actual)
                    self.assertEqual(actual["outputs"], {"result": expected})
                    self.assertEqual(
                        [c["tool"] for c in actual["calls"]],
                        ["mathformer_repo_status_" + n for n in call_names],
                    )
                    self.assertTrue(actual["runtime"]["effect_records"])
                    self.assertTrue(actual["runtime"]["provenance"])
                    self.assertTrue(actual["replay_artifacts"])
                self.assertEqual(
                    (await run())["outputs"]["result"]["stdout"], "?? untracked.txt\n"
                )
                # No retry or dependency traversal; a non-repository Git error still audits.
                empty = self.directory.parent / "empty"
                empty.mkdir()
                failed = await run({"repository_root": str(empty)})
                self.assertEqual(failed["status"], "accepted", failed)
                self.assertFalse(failed["outputs"]["result"]["ok"])
                self.assertEqual(failed["outputs"]["result"]["returncode"], 128)
                self.assertEqual(len(failed["calls"]), 4)
                # A deterministic immediate native process deadline, not a fake launcher.
                timed = await run({"timeout_seconds": 1e-12})
                self.assertEqual(timed["status"], "accepted", timed)
                self.assertEqual(timed["outputs"]["result"]["status"], "timeout")
                self.assertFalse(timed["outputs"]["result"]["ok"])
                self.assertIn("write_audit", timed["outputs"]["result"])
                self.assertEqual(len(timed["calls"]), 4)
                # Unexpected launch error propagates; audit never runs and no retries occur.
                absent = self.directory / "absent"
                failed = await run({"repository_root": str(absent)})
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIsNone(failed["outputs"])
                self.assertEqual(len(failed["calls"]), 3)
                self.assertEqual(failed["calls"][-1]["status"], "rejected")
                # Same-size edits to dirty files must survive the transported snapshots.
                args = dict(
                    context=CONTEXT,
                    extra_args=[],
                    repository_root=str(self.directory),
                    timeout_seconds=None,
                )
                boundary = (await remote.call("mathformer_repo_status_prepare", args))[
                    "boundary"
                ]
                launched = await remote.call(
                    "mathformer_repo_status_launch",
                    dict(
                        boundary=boundary,
                        repository_root=str(self.directory),
                        timeout_seconds=None,
                    ),
                )
                (self.directory / "untracked.txt").write_text("changed\n")
                audited = await remote.call(
                    "mathformer_repo_status_audit",
                    dict(
                        boundary=boundary,
                        result=launched["result"],
                        repository_root=str(self.directory),
                    ),
                )
                self.assertEqual(audited["result"]["status"], "undeclared_writes")
                self.assertFalse(audited["result"]["ok"])
                self.assertIn(
                    "untracked.txt",
                    audited["result"]["write_audit"]["unexpected_paths"],
                )
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 2
                failed = await run(doc=bounded)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    2,
                )
                self.assertIn("budget", str(failed).lower())
                # Tool discovery/preflight must detect a genuinely absent executable.
                async with manager.open(
                    "missing-git",
                    StdioConfig(command=sys.executable, args=[server], cwd=str(ROOT)),
                    {"PATH": str(empty)},
                ) as missing_remote:
                    values = dict(
                        context=CONTEXT,
                        extra_args=[],
                        seen=[],
                        repository_root=str(self.directory),
                        timeout_seconds=None,
                    )
                    missing = await execute(
                        workflow, assets, values, missing_remote, authorize
                    )
                    self.assertEqual(missing["status"], "accepted", missing)
                    self.assertFalse(missing["outputs"]["result"]["ok"])
                    self.assertTrue(
                        any(
                            "git" in error
                            for error in missing["outputs"]["result"][
                                "preflight_errors"
                            ]
                        )
                    )
                    self.assertEqual(
                        [c["tool"] for c in missing["calls"]],
                        [
                            "mathformer_repo_status_admit",
                            "mathformer_repo_status_prepare",
                            "mathformer_repo_status_return_prepared",
                        ],
                    )
                    original = await missing_remote.call(
                        "fixture_original_status",
                        dict(
                            context=CONTEXT,
                            extra_args=[],
                            seen=[],
                            repository_root=str(self.directory),
                        ),
                    )
                    self.assertEqual(missing["outputs"], original)
                timed_doc = deepcopy(document)
                timed_doc["policy"]["limits"]["wall_time_seconds"] = 1
                compiled, received = compile(timed_doc)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        compiled,
                        received,
                        dict(
                            context=CONTEXT,
                            extra_args=[],
                            seen=[],
                            repository_root=str(self.directory),
                            timeout_seconds=None,
                        ),
                        remote,
                        pending,
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
