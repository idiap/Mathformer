# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real local SymPy fixture stages, MCP tools and Lunar PRISM compile/execute.

No model or external compiler is used by this source. The five fixed LaTeX
fixtures execute the local Python/SymPy implementation with isolated outputs.
Missing fixture inputs/executables and filesystem collisions exercise failures.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
packages = next((ROOT / ".venv/lib").glob("python*/site-packages"))
os.environ["PYTHONPATH"] = os.pathsep.join(
    filter(None, [str(packages), os.environ.get("PYTHONPATH")])
)
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml
from sympy_controlled_suite_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_sympy_controlled_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/sympy-controlled-suite.workflow.json"
)
PREFIX = "mathformer_sympy_controlled_suite_"
ORDER = [
    "parse",
    "assumptions",
    "grounding",
    "draft",
    "execute",
    "identity",
    "counterexamples",
    "trace",
    "consistency",
]


def fixture(root, missing=None):
    root.mkdir(parents=True)
    skills = root / "skills/sympy"
    skills.mkdir(parents=True)
    for skill in (ROOT / "skills/sympy").iterdir():
        if skill.name != missing:
            (skills / skill.name).symlink_to(skill, target_is_directory=skill.is_dir())
    for folder in ["backends", "scripts"]:
        (root / folder).symlink_to(ROOT / folder, target_is_directory=True)
    for relative in source().SOURCES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, path)
    return root


def snapshot(doc):
    texts = {DESCRIPTOR: json.dumps(doc)}
    texts.update(
        {
            row["path"]: (ROOT / row["path"]).read_text()
            for row in doc["provenance"]["sources"]
        }
    )
    return [
        dict(
            path=p,
            content=t,
            encoding="text",
            sha256=hashlib.sha256(t.encode()).hexdigest(),
        )
        for p, t in texts.items()
    ]


def suite_root(root):
    return root / "artifacts/sympy/controlled_suite"


def oracle(root):
    path = ROOT / "tests/mcp/fixtures/sympy_controlled_suite_original.py.txt"
    namespace = {
        "__name__": "frozen_source",
        "__file__": str(ROOT / "tests/sympy/run_controlled_suite.py"),
    }
    exec(compile(path.read_text(), str(path), "exec"), namespace)
    namespace["REPO_ROOT"] = root
    out = io.StringIO()
    # Original API index is relative to cwd, just as the hub invocation is.
    with (
        patch.object(
            sys, "argv", ["suite", "--artifact-root", str(suite_root(root)), "--json"]
        ),
        redirect_stdout(out),
    ):
        code = namespace["main"]()
    return code, json.loads(out.getvalue())


def observable(report):
    """Compare native state/order/status, excluding process durations/paths/times."""

    def checks(rows):
        return [
            (x["id"], x["ok"], x["returncode"], x["cmd"][1], x["cmd"][-1]) for x in rows
        ]

    if "results" in report:
        return report["ok"], checks(report["results"])
    return (
        report["ok"],
        checks(report["preflight"]),
        [
            (
                c["source"],
                c.get("case_id"),
                c["ok"],
                checks(c["results"]),
                c.get("consistency", {}).get("status"),
                c.get("consistency", {}).get("metrics"),
            )
            for c in report["cases"]
        ],
    )


class Observed:
    def __init__(self, remote):
        self.remote, self.events = remote, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, name, args):
        result = await self.remote.call(name, args)
        self.events.append((name, deepcopy(args), deepcopy(result)))
        return result


class ControlledSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())

    def test_provenance_and_shared_native_entrypoint(self):
        self.assertEqual(self.doc, json.loads(AUTHORED.read_text()))
        self.assertEqual(self.doc["id"], "hub_sympy_controlled_workflow")
        self.assertEqual(self.doc["lifecycle"], "active")
        for row in self.doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            "tests/sympy/run_controlled_suite.py",
            [r["path"] for r in self.doc["provenance"]["sources"]],
        )

    def test_native_concept_projection(self):
        with tempfile.TemporaryDirectory() as temporary:
            packet = Path(temporary) / "parse.json"
            packet.write_text(
                json.dumps(
                    {"units": [{"concepts": ["z", "a", "z"]}, {"concepts": ["a", "b"]}]}
                )
            )
            self.assertEqual(source().concepts_from_parse(packet), ["a", "b", "z"])
            packet.write_text('{"units": []}')
            self.assertEqual(
                source().concepts_from_parse(packet), ["symbolic_simplification"]
            )
            packet.write_text("{broken")
            with self.assertRaises(json.JSONDecodeError):
                source().concepts_from_parse(packet)

    def test_registered_prism_runtime_and_failures(self):
        with tempfile.TemporaryDirectory(prefix="sympy-controlled-") as temporary:
            asyncio.run(self.scenario(Path(temporary)))

    async def scenario(self, base):
        manager = SessionManager()
        config = StdioConfig(
            command=str(ROOT / ".venv/bin/python"),
            args=[
                str(ROOT / "tests/mcp/fixtures/sympy_controlled_suite_server.py"),
                str(base),
            ],
            cwd=str(ROOT),
            timeout_seconds=600,
        )
        async with manager.open("suite", config, {}) as remote:
            try:
                inventory = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile_contract(doc, tools=None):
                    assets = snapshot(doc)
                    compiled = compile_workflow(
                        "mcp:suite",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory if tools is None else tools,
                    )
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    self.assertTrue(compiled["runtime_source"])
                    return compiled, assets

                compiled, assets = compile_contract(self.doc)
                self.assertEqual(set(compiled["bindings"]), set(self.doc["operations"]))
                for name in self.doc["operations"]:
                    tools = [t for t in inventory if t["name"] != PREFIX + name]
                    self.assertFalse(
                        compile_workflow(
                            "mcp:suite",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools,
                        )["runnable"]
                    )

                async def allow():
                    pass

                async def run(root, doc=None, context=None):
                    graph, files = (
                        compile_contract(doc) if doc is not None else (compiled, assets)
                    )
                    seen = Observed(remote)
                    result = await execute(
                        graph,
                        files,
                        {
                            "context": context
                            or {"working_directory": str(root), "allow_mutating": True}
                        },
                        seen,
                        allow,
                    )
                    return result, seen

                # Full successful traversal reaches both literal bounds normally.
                root = fixture(base / "success")
                result, seen = await run(root)
                self.assertEqual(result["status"], "accepted", str(result)[:4000])
                output = result["outputs"]["result"]
                self.assertEqual(output["exit_code"], 0)
                report = json.loads(Path(output["suite_report"]).read_text())
                self.assertEqual(json.loads(output["stdout"]), report)
                self.assertTrue(Path(output["index_html"]).is_file())
                self.assertEqual(len(result["calls"]), 15)
                self.assertEqual(
                    [e[0] for e in seen.events],
                    [
                        PREFIX + "initialize",
                        PREFIX + "preflight_step",
                        PREFIX + "preflight_step",
                        PREFIX + "prepare_cases",
                    ]
                    + [
                        name
                        for _ in range(5)
                        for name in [PREFIX + "run_case", PREFIX + "collect_case"]
                    ]
                    + [PREFIX + "finish"],
                )
                self.assertEqual(
                    [
                        e[2]["done"]
                        for e in seen.events
                        if e[0] == PREFIX + "preflight_step"
                    ],
                    [False, True],
                )
                self.assertEqual(
                    [
                        e[2]["state"]["cursor"]
                        for e in seen.events
                        if e[0] == PREFIX + "collect_case"
                    ],
                    [1, 2, 3, 4, 5],
                )
                self.assertEqual(
                    [
                        e[2]["done"]
                        for e in seen.events
                        if e[0] == PREFIX + "collect_case"
                    ],
                    [False] * 4 + [True],
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                for case in report["cases"]:
                    self.assertEqual(
                        [x["id"].split(".")[-1] for x in case["results"]], ORDER
                    )
                    self.assertTrue(Path(case["artifact"]).is_file())
                    self.assertEqual(
                        json.loads(
                            (
                                Path(case["html"]).parent
                                / "sympy_consistency_report.json"
                            ).read_text()
                        ),
                        case["consistency"],
                    )
                    counter = next(
                        x
                        for x in case["results"]
                        if x["id"].endswith(".counterexamples")
                    )
                    self.assertEqual(
                        counter["cmd"][counter["cmd"].index("--max-n") + 1], "100"
                    )
                    for check in case["results"]:
                        self.assertIn("duration_ms", check)
                        self.assertIn("stdout", check)
                oldroot = fixture(base / "oracle")
                code, expected = oracle(oldroot)
                self.assertEqual(code, 0)
                self.assertEqual(observable(report), observable(expected))
                # Shared CLI produces the same accumulated results as the original.
                native = source()
                cli_root = fixture(base / "cli")
                token = native.WORKING_DIRECTORY.set(cli_root)
                stream = io.StringIO()
                try:
                    with (
                        patch.object(
                            sys,
                            "argv",
                            [
                                "suite",
                                "--artifact-root",
                                str(suite_root(cli_root)),
                                "--json",
                            ],
                        ),
                        redirect_stdout(stream),
                    ):
                        code = native.main()
                finally:
                    native.WORKING_DIRECTORY.reset(token)
                self.assertEqual(code, 0)
                self.assertEqual(
                    observable(json.loads(stream.getvalue())), observable(expected)
                )

                # Missing stage executable is a real nonzero process result.
                for missing, count in [
                    ("sympy-dependency-prober", 1),
                    ("sympy-api-docs-indexer", 2),
                ]:
                    root = fixture(base / missing, missing=missing)
                    failed, calls = await run(root)
                    self.assertEqual(failed["status"], "accepted", failed)
                    out = failed["outputs"]["result"]
                    self.assertEqual(out["exit_code"], 1)
                    self.assertIsNone(out["index_html"])
                    failed_report = json.loads(Path(out["suite_report"]).read_text())
                    self.assertEqual(len(failed_report["results"]), count)
                    self.assertFalse(failed_report["results"][-1]["ok"])
                    self.assertFalse((suite_root(root) / "index.html").exists())
                    self.assertEqual(len(calls.events), count + 4)
                    oldroot = fixture(base / (missing + "-oracle"), missing=missing)
                    code, old = oracle(oldroot)
                    self.assertEqual(code, 1)
                    self.assertEqual(observable(failed_report), observable(old))

                # First failed case stops at parse, while four subsequent cases run.
                root = fixture(base / "parse-fail")
                (root / source().SOURCES[0]).unlink()
                failed, calls = await run(root)
                self.assertEqual(failed["status"], "accepted", failed)
                self.assertEqual(failed["outputs"]["result"]["exit_code"], 1)
                cases = json.loads(
                    Path(failed["outputs"]["result"]["suite_report"]).read_text()
                )["cases"]
                self.assertEqual(
                    [c["ok"] for c in cases], [False, True, True, True, True]
                )
                self.assertNotIn("case_id", cases[0])
                self.assertEqual(len(cases[0]["results"]), 1)
                # Later failure retains case_id and stops all later stages in that case.
                root = fixture(base / "stage-fail", missing="sympy-identity-validator")
                failed, calls = await run(root)
                self.assertEqual(failed["status"], "accepted", failed)
                cases = json.loads(
                    Path(failed["outputs"]["result"]["suite_report"]).read_text()
                )["cases"]
                self.assertEqual(len(cases), 5)
                for case in cases:
                    self.assertFalse(case["ok"])
                    self.assertIn("case_id", case)
                    self.assertEqual(
                        [r["id"].split(".")[-1] for r in case["results"]], ORDER[:6]
                    )

                # Real filesystem exceptions propagate; final reporting is absent.
                root = fixture(base / "write-fail")
                (suite_root(root) / "index.html").mkdir(parents=True)
                failed, calls = await run(root)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIsNone(failed["outputs"])
                self.assertFalse((suite_root(root) / "suite_report.json").exists())
                self.assertEqual(failed["calls"][-1]["tool"], PREFIX + "finish")

                # Compiler fixtures shorten bounds without replacing any source tool.
                for which in ["preflight", "cases"]:
                    root = fixture(base / ("exhaust-" + which))
                    doc = deepcopy(self.doc)
                    if which == "preflight":
                        doc["flow"]["steps"][1]["max_iterations"] = 1
                    else:
                        doc["flow"]["steps"][3]["max_iterations"] = 1
                    failed, calls = await run(root, doc)
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertEqual(failed["failure_disposition"], "fail")
                    self.assertIsNone(failed["outputs"])
                    self.assertFalse((suite_root(root) / "suite_report.json").exists())
                    self.assertEqual(
                        len(calls.events), 2 if which == "preflight" else 6
                    )
                root = fixture(base / "budget")
                doc = deepcopy(self.doc)
                doc["policy"]["limits"]["max_operation_calls"] = 2
                failed, calls = await run(root, doc)
                self.assertEqual(failed["status"], "failed")
                self.assertIn("budget", str(failed).lower())
                root = fixture(base / "denied")
                failed, calls = await run(
                    root,
                    context={"working_directory": str(root), "allow_mutating": False},
                )
                self.assertEqual(failed["status"], "failed")
                self.assertFalse((root / "artifacts").exists())
            except Exception:
                import traceback

                traceback.print_exc()
                raise
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
