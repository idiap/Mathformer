#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native source/MCP/Lunar/PRISM integration with isolated filesystem fixtures.

This workflow has no external provider or compiler boundary: use the real PRISM
parser/checker/compiler/runtime, never a simulated scientific implementation.
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
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import shutil
import tempfile
import unittest
import yaml
from reasoning_log_build_tools import environment, SOURCE
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_reasoning_log_index_workflow/workflow.yaml"


def assets_for(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


def context(root, **changes):
    return dict(
        repository_root=str(root),
        dry_run=False,
        json_output=False,
        keep_going=False,
        allow_mutating=True,
        write_report=False,
        **changes,
    )


class BuildTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / "artifacts/workflow_hub"
        base.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="log-build-fixture-", dir=base)
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.ctx = context(self.root)
        for name in (
            SOURCE,
            "skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log_index.py",
            "skills/SKILL_HOOKS.yaml",
        ):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)

    def test_native_oracle_and_empty_bad_continuation_discovery(self):
        spec = importlib.util.spec_from_loader(
            "index_oracle",
            SourceFileLoader(
                "index_oracle",
                str(ROOT / "tests/mcp/fixtures/reasoning_log_build_original.py.txt"),
            ),
        )
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        original.REPO_ROOT = self.root
        with environment(self.ctx) as (native, root):
            native.write_self_test_fixtures()
            good = root / "artifacts/reasoning/self_test/good.jsonl"
            bad = good.with_name("bad.jsonl")
            hooks = root / "skills/SKILL_HOOKS.yaml"
            out = root / "artifacts/reasoning/index.json"
            for logs in ([], [good], [bad, good]):
                expected = original.build_index(
                    log_files=logs, hooks_file=hooks, output_file=out
                )
                summaries = {
                    path: path.read_bytes()
                    for path in out.parent.glob("summaries/*.json")
                }
                actual = native.build_index(
                    log_files=logs, hooks_file=hooks, output_file=out
                )
                self.assertEqual(
                    summaries, {path: path.read_bytes() for path in summaries}
                )
                expected.pop("generated_at_utc")
                actual.pop("generated_at_utc")
                self.assertEqual(actual, expected)
                self.assertEqual(actual["log_count"], len(logs))
                self.assertEqual(actual["ok"], bad not in logs)
                if bad in logs:
                    self.assertEqual(actual["entries"][0]["quality_status"], "fail")
                    self.assertEqual(actual["entries"][1]["quality_status"], "pass")
            # Native CLI still shares precisely the same implementation.
            for module in (native, original):
                stream = io.StringIO()
                with redirect_stdout(stream):
                    code = module.main(
                        [
                            "--log-file",
                            str(bad),
                            "--hooks-file",
                            str(hooks),
                            "--output-file",
                            str(out),
                            "--json",
                        ]
                    )
                self.assertEqual(code, 3)
                self.assertFalse(json.loads(stream.getvalue())["ok"])
            excluded = root / "artifacts/reasoning/adversarial/extra.jsonl"
            excluded.parent.mkdir()
            excluded.write_text("{}\n")
            self.assertEqual(native.discover_logs(root / "artifacts"), [good])
            large = root / "artifacts/large.bin"
            large.write_bytes(b"a" * (2 * 1024 * 1024 + 17))
            self.assertEqual(native.sha256(large), original.sha256(large))
            self.assertEqual(
                native.sha256(large), hashlib.sha256(large.read_bytes()).hexdigest()
            )
            # A missing log is an actual exception in both entrypoints, no retry.
            for module in (native, original):
                partial = out.parent / (module.__name__ + ".json")
                with self.assertRaises(FileNotFoundError):
                    module.build_index(
                        log_files=[good, root / "absent"],
                        hooks_file=hooks,
                        output_file=partial,
                    )
                self.assertFalse(partial.exists())
                self.assertTrue(list((out.parent / "summaries").glob("good-*.json")))

    def test_mcp_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_control_reasoning_log_index_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        failure = None
        async with manager.open(
            "log-build",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(document, inventory=tools):
                    assets = assets_for(document)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    return (
                        compile_workflow("mcp:log-build", selected, inventory),
                        assets,
                    )

                compiled, assets = compile(doc)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
                self.assertFalse(compile(doc, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(ctx=None, document=None):
                    c, a = compile(document) if document else (compiled, assets)
                    return await execute(
                        c,
                        a,
                        {"context": self.ctx if ctx is None else ctx},
                        remote,
                        authorize,
                    )

                result = await run()
                self.assertEqual(result["status"], "accepted", result)
                hub = result["outputs"]["result"]
                self.assertTrue(hub["ok"], hub)
                self.assertEqual(hub["returncode"], 0)
                report = json.loads(hub["stdout"])
                self.assertEqual(report["log_count"], 1)
                self.assertTrue(report["ok"])
                self.assertEqual(
                    report,
                    json.loads(
                        (self.root / "artifacts/reasoning/index.json").read_text()
                    ),
                )
                entry = report["entries"][0]
                log = self.root / entry["log_file"]
                self.assertEqual(
                    entry["log_sha256"], hashlib.sha256(log.read_bytes()).hexdigest()
                )
                self.assertTrue(
                    (self.root / entry["reports"]["summary_json"]).is_file()
                )
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        "mathformer_log_build_" + s
                        for s in ["prepare", "initialize", "next", "write", "finish"]
                    ],
                )
                self.assertTrue(hub["write_audit"]["ok"])
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                for dry in (True, False):
                    ctx = {**self.ctx, "dry_run": dry}
                    required = self.root / SOURCE
                    if not dry:
                        required.unlink()
                    before = (self.root / "artifacts/reasoning/index.json").read_bytes()
                    early = await run(ctx)
                    self.assertEqual(early["status"], "accepted", early)
                    self.assertEqual(len(early["calls"]), 4)
                    value = early["outputs"]["result"]
                    if ctx["dry_run"]:
                        self.assertEqual(value["status"], "dry_run")
                    else:
                        self.assertFalse(value["ok"])
                        self.assertTrue(value["preflight_errors"])
                    self.assertEqual(
                        before,
                        (self.root / "artifacts/reasoning/index.json").read_bytes(),
                    )
                    if not dry:
                        shutil.copyfile(ROOT / SOURCE, required)
                # Explicit fixed bound exhaustion must abort before persistence/finish.
                bounded = deepcopy(doc)
                bounded["flow"]["steps"][2]["until"] = {"literal": False}
                failed = await run(document=bounded)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(failed["calls"]), 3)
                budget = deepcopy(doc)
                budget["policy"]["limits"]["max_operation_calls"] = 2
                failed = await run(document=budget)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    2,
                )
                # Real initialization I/O error still completes the failed process envelope
                # and write audit, rather than turning into a successful index.
                summaries = self.root / "artifacts/reasoning/summaries"
                shutil.rmtree(summaries)
                summaries.write_text("blocked")
                failed = await run()
                self.assertEqual(failed["status"], "accepted", failed)
                value = failed["outputs"]["result"]
                self.assertFalse(value["ok"])
                self.assertEqual(value["returncode"], 1)
                self.assertIn("FileExistsError", value["stderr"])
                self.assertIn("write_audit", value)
                summaries.unlink()
                # Registered operations preserve entry failures and audit overrides.
                boundary = (
                    await remote.call(
                        "mathformer_log_build_prepare", {"context": self.ctx}
                    )
                )["boundary"]
                state = (
                    await remote.call(
                        "mathformer_log_build_initialize",
                        {
                            "logs": ["artifacts/reasoning/self_test/good.jsonl"],
                            "boundary": boundary,
                        },
                    )
                )["state"]
                log.write_bytes(log.with_name("bad.jsonl").read_bytes())
                advanced = await remote.call(
                    "mathformer_log_build_next", {"state": state}
                )
                self.assertTrue(advanced["exhausted"])
                self.assertEqual(advanced["state"]["position"], 1)
                report = (
                    await remote.call(
                        "mathformer_log_build_write", {"state": advanced["state"]}
                    )
                )["report"]
                self.assertFalse(report["ok"])
                value = (
                    await remote.call(
                        "mathformer_log_build_finish",
                        {"boundary": boundary, "report": report},
                    )
                )["result"]
                self.assertEqual(value["returncode"], 3)
                self.assertFalse(value["ok"])
                boundary = (
                    await remote.call(
                        "mathformer_log_build_prepare", {"context": self.ctx}
                    )
                )["boundary"]
                state = (
                    await remote.call(
                        "mathformer_log_build_initialize",
                        {
                            "logs": ["artifacts/reasoning/self_test/good.jsonl"],
                            "boundary": boundary,
                        },
                    )
                )["state"]
                log.unlink()
                advanced = await remote.call(
                    "mathformer_log_build_next", {"state": state}
                )
                self.assertEqual(advanced["state"]["position"], 0)
                self.assertTrue(advanced["exhausted"])
                self.assertEqual(advanced["state"]["entries"], [])
                error_report = (
                    await remote.call(
                        "mathformer_log_build_write", {"state": advanced["state"]}
                    )
                )["report"]
                value = (
                    await remote.call(
                        "mathformer_log_build_finish",
                        {"boundary": boundary, "report": error_report},
                    )
                )["result"]
                self.assertFalse(value["ok"])
                self.assertEqual(value["returncode"], 1)
                self.assertIn("FileNotFoundError", value["stderr"])
                self.assertTrue(value["write_audit"]["ok"])
                boundary = (
                    await remote.call(
                        "mathformer_log_build_prepare", {"context": self.ctx}
                    )
                )["boundary"]
                (self.root / "undeclared.txt").write_text("audit fixture")
                value = (
                    await remote.call(
                        "mathformer_log_build_finish",
                        {"boundary": boundary, "report": report},
                    )
                )["result"]
                self.assertEqual(value["status"], "undeclared_writes")
                self.assertFalse(value["write_audit"]["ok"])
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
