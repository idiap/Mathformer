#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Skills source/MCP/Lunar/PRISM equivalence with external compiler fixtures."""

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
import types
import json
import tempfile
import unittest
import yaml
from comprehensive_workflow_boundary import install
from comprehensive_strict_tools import source_runner
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_family_skills_workflow/workflow.yaml"


def matrix(modes, family="skills"):
    return {
        "schema_version": 2,
        "tests": [
            {
                "id": f"fixture.{i}",
                "module_family": family,
                "command": ["fixture-compiler", mode],
                "owner_skill": "fixture",
                "hook_id": "test.fixture",
                "fixture_ids": ["deterministic-compiler"],
                "test_kind": "regression",
                "risk_level": "low",
                "timeout_seconds": 2,
                "expected_exit": 0,
                "write_set": [],
                **(
                    {"optional_dependency": "fixture_dependency_unavailable"}
                    if mode == "missing"
                    else {}
                ),
            }
            for i, mode in enumerate(modes)
        ],
    }


def snapshot(document):
    values = {
        r["path"]: (ROOT / r["path"]).read_text()
        for r in document["provenance"]["sources"]
    }
    values[DESCRIPTOR] = json.dumps(document)
    return [
        {
            "path": p,
            "content": s,
            "encoding": "text",
            "sha256": hashlib.sha256(s.encode()).hexdigest(),
        }
        for p, s in values.items()
    ]


class SkillsFamilyTests(unittest.TestCase):
    def test_registered_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_test_family_skills_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests").mkdir()
            path = root / "tests/test_matrix.json"
            native = source_runner()
            install(native, root)
            oracle = types.ModuleType("skills_family_original")
            oracle.__file__ = str(
                ROOT / "tests/test_program/run_comprehensive_tests.py"
            )
            exec(
                compile(
                    (
                        ROOT / "tests/mcp/fixtures/skills_family_original.py.txt"
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
                + ";from comprehensive_workflow_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "skills-family",
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
                                "mcp:skills-family",
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

                    def args(flags=()):
                        a = vars(
                            native.parse_args(
                                [
                                    "--module-family",
                                    "skills",
                                    "--json",
                                    "--run-id",
                                    "fixture",
                                    *flags,
                                ]
                            )
                        )
                        a["output_file"] = str(a["output_file"])
                        return a

                    async def run(data, flags=(), doc=None):
                        path.write_text(json.dumps(data))
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        c, a = compile_doc(doc) if doc else (compiled, assets)
                        self.assertTrue(c["runnable"], c["diagnostics"])
                        return await execute(
                            c,
                            a,
                            {"args": args(flags), "selection_bound": 1000},
                            remote,
                            authorize,
                        )

                    for data, flags in [
                        (matrix(["pass"]), ()),
                        (matrix(["fail", "timeout", "write", "missing", "pass"]), ()),
                        (matrix(["pass"], "atp"), ()),
                        (matrix(["missing"]), ("--profile", "strict")),
                        (matrix(["missing"]), ("--fail-on-warning",)),
                        (matrix(["pass"]), ("--emit-dependency-map-only",)),
                        (
                            matrix(["pass"]),
                            (
                                "--write-jsonl",
                                str(root / "artifacts/rows.jsonl"),
                                "--write-junit",
                                str(root / "artifacts/rows.xml"),
                            ),
                        ),
                    ]:
                        result = await run(data, flags)
                        self.assertEqual(result["status"], "accepted", result)
                        report = result["outputs"]["report"]
                        self.assertEqual(
                            report,
                            json.loads(
                                (
                                    root
                                    / "artifacts/test_program/deterministic_tests.json"
                                ).read_text()
                            ),
                        )
                        self.assertEqual(
                            json.loads(result["outputs"]["publication"]["stdout"]),
                            report,
                        )
                        self.assertEqual(
                            result["outputs"]["exit_code"], 0 if report["ok"] else 3
                        )
                        expected = [
                            r["id"]
                            for r in data["tests"]
                            if r["module_family"] == "skills"
                        ]
                        snap = "--emit-dependency-map-only" in flags
                        self.assertEqual(
                            sum(c["operation"] == "advance" for c in result["calls"]),
                            0 if snap else len(expected),
                        )
                        if not snap:
                            self.assertEqual(
                                [r["check_id"] for r in report["results"]], expected
                            )
                        if len(expected) == 5:
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                ["fail", "fail", "fail", "skip", "pass"],
                            )
                            self.assertFalse(report["results"][2]["write_audit"]["ok"])
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            code = oracle.main(
                                [
                                    "--module-family",
                                    "skills",
                                    "--json",
                                    "--run-id",
                                    "fixture",
                                    *flags,
                                ]
                            )
                        self.assertEqual(json.loads(stream.getvalue()), report)
                        self.assertEqual(code, result["outputs"]["exit_code"])
                    self.assertTrue((root / "artifacts/rows.xml").is_file())
                    self.assertEqual(
                        len((root / "artifacts/rows.jsonl").read_text().splitlines()), 1
                    )
                    mixed = matrix(["pass", "fail", "pass"])
                    mixed["tests"][1]["module_family"] = "atp"
                    result = await run(mixed)
                    self.assertEqual(
                        [r["check_id"] for r in result["outputs"]["report"]["results"]],
                        ["fixture.0", "fixture.2"],
                    )
                    self.assertTrue(result["outputs"]["report"]["ok"])
                    malformed = matrix(["crash"])
                    malformed["schema_version"] = 1
                    result = await run(malformed, ("--emit-dependency-map-only",))
                    self.assertEqual(result["status"], "accepted")
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        [
                            "enter",
                            "snapshot",
                            "retain_empty",
                            "saved_report",
                            "publish",
                        ],
                    )
                    result = await run(matrix(["pass"]), ("--validate-matrix",))
                    report = result["outputs"]["report"]
                    self.assertTrue(report["matrix_errors"])
                    self.assertEqual(
                        report["results"][-1]["check_id"], "meta.matrix_coverage"
                    )
                    self.assertFalse(report["ok"])
                    self.assertEqual(result["outputs"]["exit_code"], 3)
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        code = oracle.main(
                            [
                                "--module-family",
                                "skills",
                                "--json",
                                "--run-id",
                                "fixture",
                                "--validate-matrix",
                            ]
                        )
                    self.assertEqual(json.loads(stream.getvalue()), report)
                    self.assertEqual(code, 3)
                    exact = deepcopy(document)
                    exact["flow"]["steps"][2]["max_iterations"] = 2
                    self.assertEqual(
                        (await run(matrix(["pass", "pass"]), doc=exact))["status"],
                        "accepted",
                    )
                    exact["flow"]["steps"][2]["max_iterations"] = 1
                    result = await run(matrix(["pass", "pass"]), doc=exact)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse(
                        any(c["operation"] == "finalize" for c in result["calls"])
                    )
                    for mode in ["malformed", "crash"]:
                        data = matrix(
                            ["crash", "pass"] if mode == "crash" else ["pass"]
                        )
                        if mode == "malformed":
                            data["schema_version"] = 1
                        result = await run(data)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertFalse(
                            any(
                                c["operation"] in ("finalize", "publish")
                                for c in result["calls"]
                            )
                        )
                        with self.assertRaises((ValueError, OSError)):
                            oracle.run(
                                oracle.parse_args(
                                    ["--module-family", "skills", "--json"]
                                )
                            )
                    expected = matrix(["fail"])
                    expected["tests"][0]["expected_exit"] = 7
                    self.assertTrue((await run(expected))["outputs"]["report"]["ok"])
                    default = matrix(["timeout", "pass"])
                    del default["tests"][0]["timeout_seconds"]
                    self.assertEqual(
                        (await run(default))["outputs"]["report"]["results"][0][
                            "stderr"
                        ],
                        "timeout after 120s",
                    )
                    data = matrix(["pass", "pass"])
                    path.write_text(json.dumps(data))
                    a = args()
                    entered = await remote.call(
                        "mathformer_skills_family_enter", {"args": a}
                    )
                    ctx = entered["context"]
                    prepared = await remote.call(
                        "mathformer_skills_family_prepare",
                        {"args": a, "selection_bound": 1000, "context": ctx},
                    )
                    state = prepared["state"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_skills_family_finalize",
                            {"args": a, "state": state, "context": ctx},
                        )
                    forged = deepcopy(state)
                    forged["selected"][0]["command"] = ["forged"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_skills_family_advance",
                            {"args": a, "state": forged, "context": ctx},
                        )
                    advanced = await remote.call(
                        "mathformer_skills_family_advance",
                        {"args": a, "state": state, "context": ctx},
                    )
                    self.assertEqual(advanced["state"]["index"], 1)
                    self.assertEqual(advanced["state"]["matrix"], state["matrix"])
                    self.assertEqual(
                        advanced["state"]["results"][0]["check_id"], "fixture.0"
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_skills_family_advance",
                            {"args": a, "state": state, "context": ctx},
                        )
                    self.assertEqual(
                        (await run(matrix(["pass"] * 1001)))["status"], "failed"
                    )
                    output = root / "artifacts/test_program/deterministic_tests.json"
                    output.unlink()
                    output.mkdir()
                    result = await run(matrix(["pass"]))
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(result["calls"][-1]["operation"], "publish")
                    output.rmdir()
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    self.assertEqual(
                        (await run(matrix(["pass"]), doc=budget))["status"], "failed"
                    )
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
