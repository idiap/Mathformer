#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real MCP/PRISM execution on isolated Git fixtures; no providers or proofs."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))
import asyncio
from copy import deepcopy
import hashlib
import json
import subprocess
import tempfile
import unittest
import yaml
import mathformer as hub
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_repo_diff_check_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
ACTION = "repo:diff-check"


def original():
    scope = dict(vars(hub))
    exec(
        (ROOT / "tests/mcp/fixtures/repo_diff_check_original.py.txt").read_text(), scope
    )
    return scope["run_action"]


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text())
        for p in sorted(
            {row["path"] for row in document["provenance"]["sources"]} | {SCHEMA}
        )
    ]


def git(root, *args):
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=True
    )


class DiffCheckTests(unittest.TestCase):
    maxDiff = None

    def test_registered_mcp_and_real_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document["id"], "hub_repo_diff_check_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 4},
        )
        self.assertEqual(document["policy"]["effects"]["filesystem"]["write"], [])
        self.assertIn(
            "scripts/mathformer.py",
            [r["path"] for r in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        item = hub.build_registry()[ACTION]
        self.assertEqual(item.command, ("git", "diff", "--check"))
        self.assertEqual(
            (
                item.depends_on,
                item.writes,
                item.allows_extra_args,
                item.timeout_seconds,
            ),
            ((), (), False, None),
        )
        self.assertEqual(
            hub.run_action("missing", {}, hub.RunContext()),
            {"ok": False, "status": "unknown_action", "action_id": "missing"},
        )
        manager = SessionManager()
        server = (
            "import sys;sys.path.extend("
            + repr([str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")])
            + ');sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        )
        failure = None
        async with manager.open(
            "diff-check",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile_document(d):
                    assets = snapshot(d)
                    compiled = compile_workflow(
                        "mcp:diff-check",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        tools,
                    )
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(set(compiled["bindings"]), set(d["operations"]))
                    return compiled, assets

                workflow, assets = compile_document(document)

                async def authorize():
                    pass

                async def run(request, d=None):
                    compiled, received = (
                        (workflow, assets) if d is None else compile_document(d)
                    )
                    return await execute(compiled, received, request, remote, authorize)

                def inputs(root, dry=False, args=(), seen=()):
                    return dict(
                        context=vars(hub.RunContext(dry_run=dry)),
                        extra_args=list(args),
                        seen=list(seen),
                        repository_root=None if root is None else str(root),
                    )

                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory).resolve()
                    git(root, "init", "-q")
                    tracked = root / "tracked.txt"
                    tracked.write_text("base\n")
                    git(root, "add", "tracked.txt")
                    for text in ["base\n", "base\nvalid\n", "base\ninvalid  \n"]:
                        tracked.write_text(text)
                        for dry, args, seen in [
                            (False, [], []),
                            (True, [], []),
                            (False, ["--invalid"], []),
                            (True, ["--invalid"], []),
                            (False, [], [ACTION]),
                            (False, ["--invalid"], [ACTION]),
                            (False, [], ["caller"]),
                        ]:
                            request = inputs(root, dry, args, seen)
                            before = hub.snapshot_repository(root)
                            expected = original()(
                                ACTION,
                                hub.build_registry(),
                                hub.RunContext(**request["context"]),
                                extra_args=args,
                                seen=set(seen),
                                repository_root=root,
                            )
                            result = await run(request)
                            self.assertEqual(result["status"], "accepted", result)
                            # Darwin's Git may emit this environment warning only
                            # in the stdio child; retain and compare all Git diagnostics.
                            actual = deepcopy(result["outputs"]["result"])
                            if "stderr" in actual:
                                actual["stderr"] = (
                                    actual["stderr"]
                                    .replace(
                                        "git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\n",
                                        "",
                                    )
                                    .lstrip("\n")
                                )
                            self.assertEqual(actual, expected)
                            self.assertEqual(before, hub.snapshot_repository(root))
                            if ACTION in seen:
                                names = ["admit", "reject"]
                            elif dry or args:
                                names = ["admit", "prepare", "early_return"]
                                if args:
                                    self.assertNotIn("status", expected)
                            else:
                                names = ["admit", "prepare", "launch", "finish"]
                                self.assertEqual(
                                    expected["returncode"],
                                    2 if "invalid" in text else 0,
                                )
                                self.assertEqual(expected["ok"], "invalid" not in text)
                                self.assertTrue(expected["write_audit"]["ok"])
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], names
                            )
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                    # Native process errors are result data, not transport failures.
                    with tempfile.TemporaryDirectory() as empty:
                        result = await run(inputs(Path(empty).resolve()))
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"]["result"]["returncode"], 129)
                        self.assertFalse(result["outputs"]["result"]["ok"])
                    # Mount disappearance gives an actual launch exception, propagated
                    # through MCP and terminating Lunar before audit, without retries.
                    missing = root / "missing"
                    result = await run(inputs(missing))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["admit", "prepare", "launch"],
                    )
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    with self.assertRaises(FileNotFoundError):
                        original()(
                            ACTION,
                            hub.build_registry(),
                            hub.RunContext(),
                            repository_root=missing,
                        )
                    # Audit actual changes between transported snapshot boundaries.
                    prepared = await remote.call(
                        "mathformer_repo_diff_check_prepare",
                        dict(
                            context=vars(hub.RunContext()),
                            extra_args=[],
                            repository_root=str(root),
                        ),
                    )
                    boundary = prepared["boundary"]
                    self.assertTrue(boundary["execute"])
                    launched = await remote.call(
                        "mathformer_repo_diff_check_launch",
                        dict(boundary=boundary, repository_root=str(root)),
                    )
                    (root / "unexpected.txt").write_text("concurrent write")
                    finished = await remote.call(
                        "mathformer_repo_diff_check_finish",
                        dict(
                            boundary=boundary,
                            payload=launched["payload"],
                            repository_root=str(root),
                        ),
                    )
                    self.assertEqual(finished["result"]["status"], "undeclared_writes")
                    self.assertFalse(finished["result"]["ok"])
                    self.assertEqual(
                        finished["result"]["write_audit"]["unexpected_paths"],
                        ["unexpected.txt"],
                    )
                    self.assertIn("wrote outside", finished["result"]["stderr"])
                    # Host call bound stops before final audit; source has no loop,
                    # timeout budget, retry or exhaustion behavior of its own.
                    small = deepcopy(document)
                    small["policy"]["limits"]["max_operation_calls"] = 3
                    result = await run(inputs(root), small)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        3,
                    )
                result = await run(inputs(None, dry=True))
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["outputs"]["result"],
                    original()(
                        ACTION, hub.build_registry(), hub.RunContext(dry_run=True)
                    ),
                )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure
        # Missing Git is an actual environment condition at the external tool
        # boundary, including in dry-run. No monkeypatched production functions.
        manager = SessionManager()
        async with manager.open(
            "no-git",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {"PATH": ""},
        ) as remote:
            prepared = await remote.call(
                "mathformer_repo_diff_check_prepare",
                dict(
                    context=vars(hub.RunContext(dry_run=True)),
                    extra_args=[],
                    repository_root=None,
                ),
            )
            self.assertFalse(prepared["boundary"]["execute"])
            self.assertTrue(prepared["boundary"]["payload"]["preflight_errors"])
            self.assertNotIn("status", prepared["boundary"]["payload"])
            result = await execute(
                workflow, assets, inputs(None, dry=True), remote, authorize
            )
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(
                result["outputs"]["result"], prepared["boundary"]["payload"]
            )
            self.assertEqual(
                [c["operation"] for c in result["calls"]],
                ["admit", "prepare", "early_return"],
            )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
