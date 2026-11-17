#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixture-only real MCP, Lunar and PRISM execution of the native renderer.

There is no model/provider or external compiler boundary in this workflow.
All fixtures use actual native source in an isolated filesystem checkout.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend")]
import asyncio
from copy import deepcopy
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
import yaml
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_reasoning_log_html_workflow/workflow.yaml"
SOURCE = (
    "skills/control/reasoning-log-schema-guardian/scripts/render_reasoning_log_html.py"
)
PREFIX = "mathformer_reasoning_html_"


def snapshot(doc):
    def asset(path, content):
        return dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(doc))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in doc["provenance"]["sources"]
    ]


class DashboardTests(unittest.TestCase):
    def test_real_registered_compile_execute(self):
        with tempfile.TemporaryDirectory(prefix="reasoning-html-") as directory:
            asyncio.run(self.scenario(Path(directory)))

    async def scenario(self, root):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["id"], "hub_control_reasoning_log_html_workflow")
        self.assertEqual(doc["lifecycle"], "active")
        self.assertIn(SOURCE, [s["path"] for s in doc["provenance"]["sources"]])
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        # Relocate actual source files, not replacement implementations, so the
        # source-owned REPO_ROOT fixture paths cannot touch production artifacts.
        guardian = Path(SOURCE).parent
        shutil.copytree(ROOT / guardian, root / guardian)
        (root / "scripts").mkdir()
        shutil.copy2(
            ROOT / "scripts/reasoning_html_tools.py",
            root / "scripts/reasoning_html_tools.py",
        )
        (root / "skills/SKILL_HOOKS.yaml").write_bytes(
            (ROOT / "skills/SKILL_HOOKS.yaml").read_bytes()
        )
        oracle = root / guardian / "original.py"
        shutil.copy2(ROOT / "tests/mcp/fixtures/reasoning_html_original.py.txt", oracle)
        server = (
            f'import sys;sys.path.insert(0,{str(root/"scripts")!r});'
            "import reasoning_html_tools;import audit_reasoning_log_quality;"
            f'assert audit_reasoning_log_quality.REPO_ROOT == __import__("pathlib").Path({str(root)!r}).resolve();'
            f'sys.path.insert(0,{str(ROOT/"scripts")!r});'
            'from mcp_server import mcp;mcp.run(transport="stdio")'
        )
        manager = SessionManager()
        failure = None
        async with manager.open(
            "dashboard",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(root)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(document, inventory=tools):
                    assets = snapshot(document)
                    return (
                        compile_workflow(
                            "mcp:dashboard",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            inventory,
                        ),
                        assets,
                    )

                compiled, assets = compile(doc)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(doc["operations"]))
                self.assertFalse(
                    compile(doc, [t for t in tools if t["name"] != PREFIX + "render"])[
                        0
                    ]["runnable"]
                )
                context = {"working_directory": str(root)}

                async def authorize():
                    pass

                async def run(argv, document=doc):
                    c, a = (compiled, assets) if document is doc else compile(document)
                    return await execute(
                        c,
                        a,
                        {"extra_args": argv, "context": context},
                        remote,
                        authorize,
                    )

                async def call(name, **arguments):
                    return await remote.call(
                        PREFIX + name, dict(arguments, context=context)
                    )

                def oracle_run(argv):
                    return subprocess.run(
                        [sys.executable, str(oracle), *argv],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                def argv(log, output, *flags):
                    return [
                        "--log-file",
                        log,
                        "--output-file",
                        output,
                        "--title",
                        "<Fixture & title>",
                        *flags,
                    ]

                canonical = {
                    "event_index": 1,
                    "timestamp_utc": "2026-07-08T00:00:00+00:00",
                    "timestamp_unix_ms": 1783468800000,
                    "monotonic_ns": 1,
                    "elapsed_ms_since_log_start": 12,
                    "step": "skill_application_start",
                    "payload": {
                        "skill_application": {
                            "skill": "fixture-skill",
                            "skill_call_id": "fixture-call",
                            "status": "running",
                            "intent": "inspect <evidence>",
                            "run_id": "fixture-run",
                        }
                    },
                }
                end = deepcopy(canonical)
                end["event_index"] = 2
                end["elapsed_ms_since_log_start"] = 23
                end["step"] = "skill_application_complete"
                end["payload"]["skill_application"].update(
                    status="complete", human_summary="finished & checked"
                )
                legacy = {
                    "event_index": 3,
                    "step": "legacy_step",
                    "payload": {"skill": "legacy-skill", "hook_id": "fixture.hook"},
                }
                cases = {
                    "mixed": "\n"
                    + json.dumps(canonical)
                    + "\n[]\n42\nmalformed\n"
                    + json.dumps(end)
                    + "\n"
                    + json.dumps(legacy)
                    + "\n",
                    "empty": "",
                    "many": "\n".join(
                        json.dumps(dict(canonical, event_index=i)) for i in range(257)
                    )
                    + "\n",
                }
                for name, content in cases.items():
                    (root / (name + ".jsonl")).write_text(content)
                    flags = ["--no-validation"]
                    arguments = argv(name + ".jsonl", "out/" + name + ".html", *flags)
                    expected = oracle_run(arguments)
                    self.assertEqual(expected.returncode, 0, expected.stderr)
                    expected_html = (root / ("out/" + name + ".html")).read_text()
                    current = subprocess.run(
                        [sys.executable, str(root / SOURCE), *arguments],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(
                        (current.returncode, current.stdout),
                        (expected.returncode, expected.stdout),
                    )
                    self.assertEqual(
                        (root / ("out/" + name + ".html")).read_text(), expected_html
                    )
                    (root / ("out/" + name + ".html")).unlink()
                    result = await run(arguments)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"]["result"],
                        {
                            "output_file": "out/" + name + ".html",
                            "exit_code": 0,
                            "stdout": expected.stdout,
                        },
                    )
                    self.assertEqual(
                        (root / ("out/" + name + ".html")).read_text(), expected_html
                    )
                    self.assertEqual(
                        [r["tool"] for r in result["calls"]],
                        [
                            PREFIX + s
                            for s in (
                                "parse_select",
                                "resolve_paths",
                                "load",
                                "validate",
                                "render",
                                "write_finish",
                            )
                        ],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                # Inspect line accumulation, discarded nonobjects and malformed JSON.
                parsed = await call(
                    "parse_select",
                    argv=argv("mixed.jsonl", "mixed.html", "--no-validation"),
                )
                self.assertFalse(parsed["missing"])
                paths = (
                    await call(
                        "resolve_paths",
                        options=parsed["options"],
                        selected=parsed["selected"],
                    )
                )["paths"]
                events = (await call("load", paths=paths))["events"]
                self.assertEqual([e["_line"] for e in events], [2, 5, 6, 7])
                self.assertEqual(events[1]["step"], "invalid_json")
                self.assertEqual(
                    events[0]["payload"]["skill_application"]["status"], "running"
                )
                self.assertEqual(
                    events[2]["payload"]["skill_application"]["status"], "complete"
                )
                self.assertIsNone(
                    (await call("validate", options=parsed["options"], paths=paths))[
                        "validation"
                    ]
                )
                self.assertEqual(
                    len(
                        (
                            await call(
                                "load", paths={"log_file": str(root / "many.jsonl")}
                            )
                        )["events"]
                    ),
                    257,
                )
                # Real validation blockers remain data: HTML is still written and
                # native status 2 is returned, with every strict flag forwarded.
                for flags in (
                    [],
                    [
                        "--strict",
                        "--require-instrumentation",
                        "--require-skill-application",
                    ],
                    ["--hooks-file", "skills/SKILL_HOOKS.yaml", "--strict"],
                ):
                    arguments = argv("mixed.jsonl", "validated.html", *flags)
                    expected = oracle_run(arguments)
                    self.assertEqual(expected.returncode, 2)
                    expected_html = (root / "validated.html").read_text()
                    (root / "validated.html").unlink()
                    result = await run(arguments)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["result"]["exit_code"], 2)
                    self.assertEqual(
                        (root / "validated.html").read_text(), expected_html
                    )
                    self.assertEqual(
                        result["outputs"]["result"]["stdout"], expected.stdout
                    )
                # Missing default: fixtures are created once, then selected path is
                # resolved; explicit missing paths are never replaced or retried.
                result = await run(["--no-validation"])
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(
                    result["calls"][1]["tool"], PREFIX + "fixtures_resolve"
                )
                good = root / "artifacts/reasoning/self_test/good.jsonl"
                self.assertTrue(good.exists())
                self.assertTrue(good.with_suffix(".html").exists())
                self.assertEqual(
                    len((await call("load", paths={"log_file": str(good)}))["events"]),
                    2,
                )
                for arguments, last, length in [
                    (argv("absent.jsonl", "absent.html", "--no-validation"), "load", 3),
                    (["--unknown-option"], "parse_select", 1),
                    (
                        argv("mixed.jsonl", "output-directory", "--no-validation"),
                        "write_finish",
                        6,
                    ),
                ]:
                    (root / "output-directory").mkdir(exist_ok=True)
                    expected = oracle_run(arguments)
                    self.assertNotEqual(expected.returncode, 0)
                    failed = await run(arguments)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(len(failed["calls"]), length)
                    self.assertEqual(failed["calls"][-1]["tool"], PREFIX + last)
                    self.assertTrue(failed["calls"][-1]["transport_call_performed"])
                self.assertFalse((root / "absent.jsonl").exists())
                self.assertFalse((root / "absent.html").exists())
                # A filesystem read error aborts without validation/render/write.
                failed = await run(
                    argv("output-directory", "never.html", "--no-validation")
                )
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(len(failed["calls"]), 3)
                self.assertFalse((root / "never.html").exists())
                # Descriptor budget exhaustion stops before writing; native source
                # has no event limit, loop, retry or resume to synthesize here.
                budget = deepcopy(doc)
                budget["policy"]["limits"]["max_operation_calls"] = 5
                failed = await run(
                    argv("mixed.jsonl", "budget.html", "--no-validation"), budget
                )
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIsNone(failed["outputs"])
                self.assertEqual(len(failed["calls"]), 6)
                self.assertFalse(
                    failed["calls"][-1].get("transport_call_performed", False)
                )
                self.assertIn("budget", failed["calls"][-1]["error"])
                self.assertFalse((root / "budget.html").exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
