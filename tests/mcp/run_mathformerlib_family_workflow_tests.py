#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Exercise the registered native steps through real Lunar compilation and PRISM."""

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
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import io
import json
import tempfile
import types
import unittest
import yaml
from mathformerlib_family_boundary import install
from comprehensive_strict_tools import source_runner
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_family_mathformerlib_workflow/workflow.yaml"
CANONICAL = (ROOT / "tests/test_matrix.json").read_text()
ARGS = dict(
    module_family=["mathformerlib"],
    profile="workstation",
    changed_files_only=False,
    emit_dependency_map_only=False,
    fail_on_warning=False,
    validate_matrix=False,
    run_id="fixture",
    output_file="artifacts/test_program/deterministic_tests.json",
    write_jsonl=None,
    write_junit=None,
    json=True,
)


def revision(text):
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def assets(document):
    values = {
        r["path"]: (ROOT / r["path"]).read_text()
        for r in document["provenance"]["sources"]
    }
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


def matrix(modes):
    return json.dumps(
        {
            "schema_version": 2,
            "tests": [
                dict(
                    id=f"fixture.{i}",
                    module_family="mathformerlib",
                    command=["fixture-compiler", m],
                    owner_skill="fixture",
                    hook_id="test.fixture",
                    fixture_ids=["compiler-fixture"],
                    test_kind="regression",
                    risk_level="low",
                    timeout_seconds=120,
                    expected_exit=0,
                    write_set=[],
                    **(
                        {"optional_dependency": "fixture_dependency_unavailable"}
                        if m == "missing"
                        else {}
                    ),
                )
                for i, m in enumerate(modes)
            ],
        }
    )


def original(root):
    native = types.ModuleType("mathformerlib_original")
    native.__file__ = str(ROOT / "tests/test_program/run_comprehensive_tests.py")
    exec(
        compile(
            (
                ROOT / "tests/mcp/fixtures/mathformerlib_family_original.py.txt"
            ).read_text(),
            native.__file__,
            "exec",
        ),
        native.__dict__,
    )
    install(native, root)
    return native


class MathformerlibTests(unittest.TestCase):
    def test_native_cursor_invariants(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests").mkdir()
            native = source_runner()
            install(native, root)
            native.MATRIX_FILE.write_text(matrix(["pass", "missing"]))
            args = native.parse_args(["--module-family", "mathformerlib"])
            state = native.prepare_checks(args)
            with self.assertRaisesRegex(ValueError, "unconsumed"):
                native.finalize_checks(state, args)
            broken = deepcopy(state)
            broken["results"] = [{}]
            with self.assertRaisesRegex(ValueError, "cursor"):
                native.advance_check(broken, args)
            state = native.advance_check(state, args)
            state = native.advance_check(state, args)
            self.assertEqual(state["index"], 2)
            self.assertEqual([r["status"] for r in state["results"]], ["pass", "skip"])
            with self.assertRaisesRegex(ValueError, "exhausted"):
                native.advance_check(state, args)
            args.fail_on_warning = True
            self.assertEqual(
                native.run_check(state["selected"][1], True)["status"], "fail"
            )

    def test_registered_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_test_family_mathformerlib_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/mathformerlib-family.workflow.json"
                ).read_text()
            ),
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(row["digest"], revision((ROOT / row["path"]).read_text()))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests").mkdir()
            path = root / "tests/test_matrix.json"
            (root / "boundary.json").write_text(json.dumps(["pass", "pass"]))
            oracle = original(root)
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
                + ";from mathformerlib_family_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "mathformerlib",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]
                    self.assertTrue(
                        {
                            op["execution"]["binding"]["target"]
                            for op in document["operations"].values()
                        }
                        <= {t["name"] for t in tools}
                    )

                    def compile_doc(doc, inventory=None):
                        a = assets(doc)
                        c = compile_workflow(
                            "mcp:mathformerlib",
                            workflow_documents([DESCRIPTOR], a)[0],
                            tools if inventory is None else inventory,
                        )
                        return c, a

                    compiled, a = compile_doc(document)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    self.assertFalse(compile_doc(document, [])[0]["runnable"])

                    async def authorize():
                        pass

                    async def run(text=CANONICAL, args=None, doc=None):
                        path.write_text(text)
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        d = deepcopy(doc or document)
                        d["types"]["MatrixRevision"]["schema"]["const"] = revision(text)
                        c, a = compile_doc(d)
                        self.assertTrue(c["runnable"], c["diagnostics"])
                        return await execute(
                            c,
                            a,
                            {"args": args or ARGS, "matrix_revision": revision(text)},
                            remote,
                            authorize,
                        )

                    def loop(doc):
                        return doc["flow"]["steps"][2]

                    for text in [
                        CANONICAL,
                        matrix(["fail", "pass"]),
                        matrix(["timeout", "missing"]),
                        matrix(["write", "large"]),
                    ]:
                        result = await run(text)
                        self.assertEqual(result["status"], "accepted", result)
                        report = result["outputs"]["report"]
                        code = result["outputs"]["exit_code"]
                        self.assertEqual(
                            sum(c["operation"] == "advance" for c in result["calls"]), 2
                        )
                        self.assertEqual(len(result["calls"]), 10)
                        self.assertEqual(
                            report, json.loads((root / ARGS["output_file"]).read_text())
                        )
                        self.assertEqual(code, 0 if report["ok"] else 3)
                        self.assertEqual(report["schema_errors"], [])
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            original_code = oracle.main(
                                [
                                    "--module-family",
                                    "mathformerlib",
                                    "--json",
                                    "--run-id",
                                    "fixture",
                                ]
                            )
                        self.assertEqual(report, json.loads(stream.getvalue()))
                        self.assertEqual(code, original_code)
                        if text == matrix(["timeout", "missing"]):
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                ["fail", "skip"],
                            )
                        if text == matrix(["write", "large"]):
                            self.assertIn("undeclared", report["results"][0]["stderr"])
                            self.assertIn("<truncated>", report["results"][1]["stdout"])
                    empty = json.loads(matrix(["pass"]))
                    empty["tests"][0]["module_family"] = "atp"
                    result = await run(json.dumps(empty))
                    self.assertEqual(result["outputs"]["report"]["summary"]["total"], 0)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        [
                            "enter",
                            "prepare",
                            "remaining",
                            "retain",
                            "finalize",
                            "publish",
                        ],
                    )
                    # Early return bypasses matrix parsing, retains publication and sidecars.
                    args = {
                        **ARGS,
                        "emit_dependency_map_only": True,
                        "write_jsonl": "artifacts/test_program/deterministic_tests.jsonl",
                        "write_junit": "artifacts/test_program/deterministic_tests.xml",
                    }
                    result = await run("invalid matrix", args)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        [
                            "enter",
                            "snapshot_frame",
                            "remaining",
                            "retain",
                            "snapshot",
                            "publish",
                        ],
                    )
                    self.assertEqual(
                        result["outputs"]["report"]["families"], ["environment"]
                    )
                    self.assertTrue((root / args["write_jsonl"]).is_file())
                    self.assertTrue((root / args["write_junit"]).is_file())
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        code = oracle.main(
                            [
                                "--module-family",
                                "mathformerlib",
                                "--emit-dependency-map-only",
                                "--run-id",
                                "fixture",
                                "--json",
                                "--write-jsonl",
                                "--write-junit",
                            ]
                        )
                    self.assertEqual(
                        result["outputs"]["report"], json.loads(stream.getvalue())
                    )
                    self.assertEqual(code, result["outputs"]["exit_code"])
                    self.assertEqual(
                        json.loads((root / args["write_jsonl"]).read_text()),
                        result["outputs"]["report"]["results"][0],
                    )
                    # Ordinary failure continues; strict missing dependencies fails and still publishes.
                    result = await run(
                        matrix(["missing", "pass"]), {**ARGS, "profile": "strict"}
                    )
                    self.assertFalse(result["outputs"]["report"]["ok"])
                    self.assertEqual(result["outputs"]["exit_code"], 3)
                    self.assertEqual(
                        [r["status"] for r in result["outputs"]["report"]["results"]],
                        ["fail", "pass"],
                    )
                    self.assertFalse(
                        result["outputs"]["report"]["capability_ledger"]["strict_ready"]
                    )
                    result = await run(
                        matrix(["missing", "pass"]), {**ARGS, "fail_on_warning": True}
                    )
                    self.assertEqual(result["outputs"]["exit_code"], 3)
                    # Native coverage validation appends a meta failure after the selected checks.
                    result = await run(
                        matrix(["pass", "pass"]), {**ARGS, "validate_matrix": True}
                    )
                    report = result["outputs"]["report"]
                    self.assertTrue(report["matrix_errors"])
                    self.assertEqual(
                        report["results"][-1]["check_id"], "meta.matrix_coverage"
                    )
                    self.assertEqual(result["outputs"]["exit_code"], 3)
                    expected = json.loads(matrix(["fail", "pass"]))
                    expected["tests"][0]["expected_exit"] = 7
                    result = await run(json.dumps(expected))
                    self.assertTrue(result["outputs"]["report"]["ok"])
                    malformed = json.loads(matrix(["pass"]))
                    malformed["schema_version"] = 1
                    result = await run(json.dumps(malformed))
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ["enter", "prepare"]
                    )
                    exhausted = deepcopy(document)
                    loop(exhausted)["max_iterations"] = 1
                    result = await run(matrix(["pass", "pass"]), doc=exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse(
                        any(
                            c["operation"] in ("finalize", "publish")
                            for c in result["calls"]
                        )
                    )
                    result = await run(matrix(["pass"] * 3))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ["enter", "prepare"]
                    )
                    result = await run(matrix(["crash", "pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["enter", "prepare", "remaining", "advance"],
                    )
                    with self.assertRaises(OSError):
                        oracle.main(["--module-family", "mathformerlib"])
                    output = root / ARGS["output_file"]
                    output.unlink()
                    output.mkdir()
                    result = await run(matrix(["pass", "pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["operation"], "publish")
                    output.rmdir()
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    self.assertEqual((await run(doc=budget))["status"], "failed")
                    # Revision, owned history, phase, report and replay checks use the real registry.
                    path.write_text(CANONICAL)
                    ctx = (
                        await remote.call(
                            "mathformer_mathformerlib_enter", {"args": ARGS}
                        )
                    )["context"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_mathformerlib_prepare",
                            dict(
                                args=ARGS, context=ctx, matrix_revision="sha256:wrong"
                            ),
                        )
                    st = (
                        await remote.call(
                            "mathformer_mathformerlib_prepare",
                            dict(
                                args=ARGS,
                                context=ctx,
                                matrix_revision=revision(CANONICAL),
                            ),
                        )
                    )["state"]
                    ports = dict(args=ARGS, context=ctx, state=st)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call("mathformer_mathformerlib_finalize", ports)
                    for index in range(2):
                        self.assertTrue(
                            (
                                await remote.call(
                                    "mathformer_mathformerlib_remaining",
                                    dict(state=st, context=ctx),
                                )
                            )["remaining"]
                        )
                        forged = deepcopy(st)
                        forged["selected"][index]["command"] = ["forged"]
                        with self.assertRaises(MCPConnectionError):
                            await remote.call(
                                "mathformer_mathformerlib_advance",
                                {**ports, "state": forged},
                            )
                        st = (
                            await remote.call(
                                "mathformer_mathformerlib_advance",
                                {**ports, "state": st},
                            )
                        )["state"]
                        self.assertEqual(st["index"], index + 1)
                        self.assertEqual(len(st["results"]), index + 1)
                    self.assertFalse(
                        (
                            await remote.call(
                                "mathformer_mathformerlib_remaining",
                                dict(state=st, context=ctx),
                            )
                        )["remaining"]
                    )
                    report = (
                        await remote.call(
                            "mathformer_mathformerlib_finalize", {**ports, "state": st}
                        )
                    )["report"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_mathformerlib_publish",
                            dict(
                                args=ARGS, context=ctx, report={**report, "ok": False}
                            ),
                        )
                    await remote.call(
                        "mathformer_mathformerlib_publish",
                        dict(args=ARGS, context=ctx, report=report),
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_mathformerlib_publish",
                            dict(args=ARGS, context=ctx, report=report),
                        )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
