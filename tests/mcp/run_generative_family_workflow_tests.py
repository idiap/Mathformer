#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic native/MCP/Lunar/PRISM integration; no production checks run."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(ROOT / "tests/mcp/fixtures"),
]
APPLICATION_SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(APPLICATION_SITES)
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import tempfile
import types
import unittest
import yaml
from comprehensive_workflow_boundary import install
from comprehensive_strict_tools import source_runner
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
from generative_family_workflow_tools import DOMAIN

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_family_generative_workflow/workflow.yaml"
CONTEXT = dict(
    dry_run=False,
    json_output=True,
    keep_going=False,
    allow_mutating=False,
    write_report=False,
)


def matrix(modes, family="generative"):
    return {
        "schema_version": 2,
        "tests": [
            dict(
                id=f"fixture.{i}",
                module_family=family,
                command=["fixture-compiler", mode],
                owner_skill="fixture",
                hook_id="test.fixture",
                fixture_ids=["deterministic-compiler"],
                test_kind="regression",
                risk_level="low",
                timeout_seconds=2,
                expected_exit=0,
                write_set=[],
                **(
                    {"optional_dependency": "fixture_dependency_unavailable"}
                    if mode == "missing"
                    else {}
                ),
            )
            for i, mode in enumerate(modes)
        ],
    }


def snapshot(document):
    paths = {r["path"] for r in document["provenance"]["sources"]}
    values = {p: (ROOT / p).read_text() for p in paths}
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=p,
            content=s,
            encoding="text",
            sha256=hashlib.sha256(s.encode()).hexdigest(),
        )
        for p, s in values.items()
    ]


class GenerativeFamilyTests(unittest.TestCase):
    def test_native_cursor_invariants(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests").mkdir()
            native = source_runner()
            install(native, root)
            data = matrix(["pass"])
            data["tests"][0]["command"][0] = "{python}"
            native.MATRIX_FILE.write_text(json.dumps(data))
            args = native.parse_args(["--module-family", "generative", "--json"])
            state = native.prepare_checks(args)
            self.assertEqual(state["selected"][0]["command"][0], native.PYTHON)
            with self.assertRaisesRegex(ValueError, "unconsumed"):
                native.finalize_checks(state, args)
            state["results"] = [{}]
            with self.assertRaisesRegex(ValueError, "cursor"):
                native.advance_check(state, args)
            empty = dict(
                matrix=[], selected=[], families=["generative"], index=0, results=[]
            )
            with self.assertRaisesRegex(ValueError, "exhausted"):
                native.advance_check(empty, args)
            missing = matrix(["missing"])["tests"][0]
            self.assertEqual(native.run_check(missing, False)["status"], "skip")
            self.assertEqual(native.run_check(missing, True)["status"], "fail")

    def test_native_deadline_boundary(self):
        import multiprocessing
        import time
        from generative_family_workflow_tools import GenerativeTools
        import mathformer as hub

        self.assertEqual(
            hub.build_registry()["test:family:generative"].timeout_seconds, 900
        )
        parent, child = multiprocessing.Pipe()
        service = GenerativeTools()
        try:
            # A real IPC boundary with no response, at the cumulative deadline.
            with self.assertRaisesRegex(TimeoutError, "900 seconds"):
                service.receive({"pipe": parent, "deadline": time.monotonic() - 1})
        finally:
            parent.close()
            child.close()
            service.close()

    def test_registered_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_test_family_generative_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertIn(
            "tests/test_program/run_comprehensive_tests.py",
            [r["path"] for r in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests/test_program").mkdir(parents=True)
            (root / "tests/test_program/run_comprehensive_tests.py").write_text(
                "# required path fixture\n"
            )
            path = root / "tests/test_matrix.json"
            path.write_text(json.dumps(matrix([])))
            native = source_runner()
            install(native, root)
            oracle = types.ModuleType("generative_family_original")
            oracle.__file__ = str(
                ROOT / "tests/test_program/run_comprehensive_tests.py"
            )
            exec(
                compile(
                    (
                        ROOT / "tests/mcp/fixtures/generative_family_original.py.txt"
                    ).read_text(),
                    oracle.__file__,
                    "exec",
                ),
                oracle.__dict__,
            )
            install(oracle, root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr(
                    [
                        str(ROOT / "scripts"),
                        str(ROOT / "tests/mcp/fixtures"),
                        str(ROOT),
                        *APPLICATION_SITES,
                    ]
                )
                + ";from generative_family_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "generative-family",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile_doc(doc, inventory=None):
                        assets = snapshot(doc)
                        return (
                            compile_workflow(
                                "mcp:generative-family",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                tools if inventory is None else inventory,
                            ),
                            assets,
                        )

                    compiled, assets = compile_doc(document)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertEqual(
                        set(compiled["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile_doc(document, [])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(data, doc=None, context=None):
                        path.write_text(json.dumps(data))
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        c, a = compile_doc(doc) if doc else (compiled, assets)
                        self.assertTrue(c["runnable"], c["diagnostics"])
                        return await execute(
                            c,
                            a,
                            {"context": context or CONTEXT, "domain": DOMAIN},
                            remote,
                            authorize,
                        )

                    mixed = matrix(["pass", "fail", "pass"])
                    mixed["tests"][1]["module_family"] = "atp"
                    for data in [
                        matrix(["pass"]),
                        matrix(
                            ["fail", "timeout", "write", "missing", "large", "pass"]
                        ),
                        matrix(["pass"], "atp"),
                        mixed,
                    ]:
                        result = await run(data)
                        self.assertEqual(result["status"], "accepted", result)
                        hub = result["outputs"]["result"]
                        report = json.loads(hub["stdout"])
                        self.assertEqual(
                            report,
                            json.loads(
                                (
                                    root
                                    / "artifacts/test_program/deterministic_tests.json"
                                ).read_text()
                            ),
                        )
                        self.assertEqual(hub["returncode"], 0 if report["ok"] else 3)
                        self.assertEqual(
                            hub["ok"], report["ok"] and hub["write_audit"]["ok"]
                        )
                        expected = [
                            r["id"]
                            for r in data["tests"]
                            if r["module_family"] == "generative"
                        ]
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]], expected
                        )
                        self.assertEqual(
                            sum(c["operation"] == "advance" for c in result["calls"]),
                            len(expected),
                        )
                        self.assertEqual(report["schema_errors"], [])
                        self.assertEqual(report["matrix_errors"], [])
                        self.assertTrue((root / report["dependency_map"]).is_file())
                        if len(expected) == 6:
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                ["fail", "fail", "fail", "skip", "pass", "pass"],
                            )
                            self.assertIn("timeout", report["results"][1]["stderr"])
                            self.assertFalse(report["results"][2]["write_audit"]["ok"])
                            self.assertFalse(hub["write_audit"]["ok"])
                            self.assertEqual(hub["status"], "undeclared_writes")
                            self.assertIn("<truncated>", report["results"][4]["stdout"])
                            self.assertLess(len(report["results"][4]["stdout"]), 5004)
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = oracle.main(
                                ["--module-family", "generative", "--json"]
                            )
                        self.assertEqual(json.loads(stream.getvalue()), report)
                        self.assertEqual(code, hub["returncode"])
                    # Native preflight/dry-run returns before worker preparation.
                    result = await run(
                        matrix(["crash"]), context={**CONTEXT, "dry_run": True}
                    )
                    self.assertEqual(result["outputs"]["result"]["status"], "dry_run")
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["enter", "bypass", "retain", "stop"],
                    )
                    path.unlink()
                    stopped = await remote.call(
                        "mathformer_generative_family_enter",
                        {"context": CONTEXT, "domain": DOMAIN},
                    )
                    self.assertFalse(stopped["proceed"])
                    self.assertFalse(stopped["result"]["ok"])
                    self.assertIn(
                        "missing required path",
                        stopped["result"]["preflight_errors"][0],
                    )
                    await remote.call(
                        "mathformer_generative_family_stop",
                        {"runtime": stopped["runtime"], "result": stopped["result"]},
                    )
                    # Exercise the real loop's terminal and exhaustion behavior with a small fixture.
                    exact = deepcopy(document)
                    loop = exact["flow"]["steps"][2]
                    loop["max_iterations"] = 2
                    self.assertEqual(
                        (await run(matrix(["pass", "pass"]), exact))["status"],
                        "accepted",
                    )
                    loop["max_iterations"] = 1
                    result = await run(matrix(["pass", "pass"]), exact)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse(
                        any(c["operation"] == "finalize" for c in result["calls"])
                    )
                    malformed = matrix(["pass"])
                    malformed["schema_version"] = 1
                    result = await run(malformed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["operation"], "prepare")
                    result = await run(matrix(["crash", "pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["enter", "prepare", "advance"],
                    )
                    with self.assertRaisesRegex(
                        OSError, "fixture compiler launch failed"
                    ):
                        oracle.run(
                            oracle.parse_args(
                                ["--module-family", "generative", "--json"]
                            )
                        )
                    output = root / "artifacts/test_program/deterministic_tests.json"
                    output.unlink()
                    output.mkdir()
                    result = await run(matrix(["pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["operation"], "publish")
                    output.rmdir()
                    default = matrix(["timeout", "pass"])
                    del default["tests"][0]["timeout_seconds"]
                    self.assertEqual(
                        json.loads((await run(default))["outputs"]["result"]["stdout"])[
                            "results"
                        ][0]["stderr"],
                        "timeout after 120s",
                    )
                    expected = matrix(["fail"])
                    expected["tests"][0]["expected_exit"] = 7
                    self.assertTrue((await run(expected))["outputs"]["result"]["ok"])

                    # Server-owned state prevents arbitrary command injection and replay.
                    async def prepare(data):
                        path.write_text(json.dumps(data))
                        entry = await remote.call(
                            "mathformer_generative_family_enter",
                            {"context": CONTEXT, "domain": DOMAIN},
                        )
                        args = dict(args=entry["args"], runtime=entry["runtime"])
                        state = await remote.call(
                            "mathformer_generative_family_prepare",
                            {**args, "domain": DOMAIN},
                        )
                        return args, state["state"]

                    args, state = await prepare(matrix(["pass", "pass"]))
                    self.assertEqual(state["index"], 0)
                    self.assertEqual(state["results"], [])
                    advanced = await remote.call(
                        "mathformer_generative_family_advance", {**args, "state": state}
                    )
                    self.assertEqual(advanced["state"]["index"], 1)
                    self.assertEqual(advanced["state"]["matrix"], state["matrix"])
                    self.assertEqual(
                        advanced["state"]["results"][0]["check_id"], "fixture.0"
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_generative_family_advance",
                            {**args, "state": state},
                        )
                    args, state = await prepare(matrix(["pass"]))
                    forged = deepcopy(state)
                    forged["selected"][0]["command"] = ["forged"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_generative_family_advance",
                            {**args, "state": forged},
                        )
                    args, state = await prepare(matrix(["pass"]))
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_generative_family_finalize",
                            {**args, "state": state},
                        )
                    # Exact input bound admitted, one-over rejected without truncation.
                    args, state = await prepare(matrix(["pass"] * 4096))
                    self.assertEqual(len(state["selected"]), 4096)
                    self.assertEqual(state["index"], 0)
                    with self.assertRaises(MCPConnectionError):
                        await prepare(matrix(["pass"] * 4097))
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    self.assertEqual(
                        (await run(matrix(["pass"]), budget))["status"], "failed"
                    )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
