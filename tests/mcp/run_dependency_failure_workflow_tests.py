#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Exercise native steps, production MCP registration, and real Lunar/PRISM.

No model/provider or external compiler is used by this workflow, so none is
substituted. Child scripts run only under the real SymPy import blocker in a
scratch checkout. Diagnostic inputs and altered loop bounds are compiler
fixtures, never alternate production implementations.
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
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
import yaml
from dependency_failure_tools import source
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
from mcp_connections.workflow_contract.validator import validate

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_sympy_dependency_failure_policy_workflow/workflow.yaml"
PREFIX = "mathformer_dependency_failure_"
SOURCE = "tests/physics_sympy/run_dependency_failure_policy.py"


def load_native(text, root):
    # The module's real __file__ resolves its native REPO_ROOT to the scratch
    # checkout; no source helper, subprocess or computation is replaced.
    namespace = {"__file__": str(root / SOURCE), "__name__": "native_fixture"}
    exec(compile(text, namespace["__file__"], "exec"), namespace)
    return namespace


def assets(document):
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


def row(parsed, code=3, stderr="", stdout=""):
    return {
        "script": source().SCRIPTS[0],
        "returncode": code,
        "stdout_json": parsed,
        "stderr": stderr,
        "raw_stdout": stdout,
    }


class DependencyFailureTests(unittest.TestCase):
    def test_bound_native_workflow(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_physics_sympy_dependency_failure_policy_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        with tempfile.TemporaryDirectory(
            prefix=".dependency-contract-", dir=ROOT
        ) as folder:
            path = Path(folder) / "workflow.json"
            path.write_text(json.dumps(document))
            checked = validate(path, ROOT, True)
        self.assertTrue(checked["valid"], checked)
        self.assertIn(SOURCE, [r["path"] for r in document["provenance"]["sources"]])
        for r in document["provenance"]["sources"]:
            self.assertEqual(
                r["digest"],
                "sha256:" + hashlib.sha256((ROOT / r["path"]).read_bytes()).hexdigest(),
            )
        # Read the native generator without writing the host-owned catalog/YAML.
        generator_path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location(
            "dependency_normalizer", generator_path
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        retained = next(d for d in generator.inventory() if d["id"] == document["id"])
        self.assertEqual(retained, document)
        with tempfile.TemporaryDirectory(prefix="dependency-policy-") as directory:
            root = Path(directory)
            (root / "tests/physics_sympy").mkdir(parents=True)
            for script in (*source().SCRIPTS, SOURCE):
                shutil.copyfile(ROOT / script, root / script)
            # Pipeline import encounters the native hook at its first sympy
            # import, before derivations, reports, providers or artifacts exist.
            (root / "backends").symlink_to(ROOT / "backends", target_is_directory=True)
            original = load_native(
                (
                    ROOT / "tests/mcp/fixtures/dependency_failure_original.py.txt"
                ).read_text(),
                root,
            )
            current = load_native((ROOT / SOURCE).read_text(), root)
            expected = original["run_check"]()
            self.assertTrue(expected["ok"])
            self.assertEqual(expected["findings"], [])
            self.assertEqual(
                [r["script"] for r in expected["results"]], list(source().SCRIPTS)
            )
            self.assertEqual([r["returncode"] for r in expected["results"]], [3, 3])
            self.assertEqual(current["run_check"](), expected)
            for native in (original, current):
                stream = io.StringIO()
                with redirect_stdout(stream):
                    self.assertEqual(native["main"](["--json"]), 0)
                self.assertEqual(json.loads(stream.getvalue()), expected)
            self.assertFalse((root / "artifacts").exists())
            asyncio.run(self.scenarios(document, root, expected))

    async def scenarios(self, document, root, expected):
        manager = SessionManager()
        async with manager.open(
            "dependency-policy",
            StdioConfig(
                command=sys.executable,
                args=[
                    "scripts/mcp_server.py",
                    "--transport",
                    "stdio",
                    "--auth-token",
                    "",
                ],
                cwd=str(ROOT),
                timeout_seconds=120,
            ),
            {"PYTHONPATH": os.environ["PYTHONPATH"]},
        ) as remote:
            inventory = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, tools=None):
                received = assets(doc)
                compiled = compile_workflow(
                    "mcp:dependency-policy",
                    workflow_documents([DESCRIPTOR], received)[0],
                    inventory if tools is None else tools,
                )
                return compiled, received

            compiled, received = compile(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            self.assertFalse(compile(document, [])[0]["runnable"])

            async def authorize():
                pass

            async def run(doc=document, directory=root):
                w, a = compile(doc)
                self.assertTrue(w["runnable"], w["diagnostics"])
                return await execute(
                    w,
                    a,
                    {"context": {"repository_root": str(directory)}},
                    remote,
                    authorize,
                )

            async def call(name, **kwargs):
                return await remote.call(PREFIX + name, kwargs)

            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"], {"report": expected})
            order = (
                [
                    "initialize_results",
                    "collect_next",
                    "collect_next",
                    "begin_validation",
                ]
                + ["inspect_current", "check_nonempty", "advance_validation"] * 2
                + ["build_report"]
            )
            self.assertEqual(
                [r["tool"] for r in result["calls"]], [PREFIX + n for n in order]
            )
            self.assertEqual(len(result["calls"]), 11)
            self.assertTrue(result["runtime"]["effect_records"])
            self.assertTrue(result["replay_artifacts"])

            # Real source errors: missing fixed child paths produce empty JSON
            # reports, and missing cwd propagates OSError at the first launch.
            empty = root / "empty"
            empty.mkdir()
            bad = await run(directory=empty)
            self.assertEqual(bad["status"], "accepted", bad)
            self.assertFalse(bad["outputs"]["report"]["ok"])
            self.assertEqual(
                [f["code"] for f in bad["outputs"]["report"]["findings"]],
                ["missing_structured_json"] * 2,
            )
            self.assertEqual(len(bad["calls"]), 11)
            for text in (
                (
                    ROOT / "tests/mcp/fixtures/dependency_failure_original.py.txt"
                ).read_text(),
                (ROOT / SOURCE).read_text(),
            ):
                native = load_native(text, empty)
                self.assertEqual(native["run_check"](), bad["outputs"]["report"])
                stream = io.StringIO()
                with redirect_stdout(stream):
                    self.assertEqual(native["main"]([]), 3)
                self.assertEqual(stream.getvalue(), "ok: False\nfindings: 2\n")
            self.assertEqual(
                [r["returncode"] for r in bad["outputs"]["report"]["results"]], [2, 2]
            )
            failed = await run(directory=root / "nonexistent")
            self.assertEqual(failed["status"], "failed", failed)
            self.assertIsNone(failed["outputs"])
            self.assertEqual(
                [r["tool"] for r in failed["calls"]],
                [PREFIX + "initialize_results", PREFIX + "collect_next"],
            )
            self.assertEqual(failed["calls"][-1]["status"], "rejected")

            # Exercise the same registered validators with diagnostic payloads.
            valid = {
                "style": "physics_sympy_dependency_blocker",
                "findings": [17, {"code": "missing_required_dependency"}],
            }
            fixtures = [
                (row(valid, 0), ["missing_dependency_returned_success"], True),
                (
                    row(
                        {"style": "other", "findings": ["ignored"]},
                        0,
                        "Traceback",
                        "Traceback",
                    ),
                    [
                        "wrong_missing_dependency_style",
                        "missing_dependency_code_absent",
                        "traceback_leaked",
                        "missing_dependency_returned_success",
                    ],
                    False,
                ),
                (
                    row({}, 0, "Traceback" + "e" * 600, "Traceback" + "o" * 600),
                    ["missing_structured_json"],
                    False,
                ),
                (row(False), ["missing_structured_json"], False),
                (row([]), ["missing_structured_json"], False),
            ]
            for first, codes, ok in fixtures:
                second = row(valid)
                second["script"] = source().SCRIPTS[1]
                rows = [first, second]
                before = deepcopy(rows)
                state = (await call("begin_validation", results=rows))["state"]
                self.assertEqual(state, {"index": 0, "results": rows, "findings": []})
                for index in range(2):
                    inspected = await call("inspect_current", state=state)
                    findings = (
                        await call(
                            (
                                "record_missing"
                                if inspected["missing"]
                                else "check_nonempty"
                            ),
                            state=state,
                            result=inspected["result"],
                        )
                    )["findings"]
                    advanced = await call(
                        "advance_validation", state=state, findings=findings
                    )
                    self.assertEqual(advanced["done"], index == 1)
                    self.assertEqual(advanced["state"]["index"], index + 1)
                    state = advanced["state"]
                report = (await call("build_report", state=state))["report"]
                self.assertEqual([f["code"] for f in report["findings"]], codes)
                self.assertEqual(report["ok"], ok)
                self.assertEqual(report["results"], before)
                if first["raw_stdout"].endswith("o" * 600):
                    self.assertEqual(report["findings"][0]["stdout"], "o" * 500)
                    self.assertEqual(report["findings"][0]["stderr"], "e" * 500)
                # Compiler fixture supplies actual validator input; no source
                # operation or registered tool is substituted.
                variant = deepcopy(document)
                variant["flow"]["steps"] = variant["flow"]["steps"][2:]
                variant["flow"]["steps"][0]["arguments"]["results"] = {"literal": rows}
                executed = await run(variant)
                self.assertEqual(executed["status"], "accepted", executed)
                self.assertEqual(executed["outputs"], {"report": report})
                self.assertEqual(len(executed["calls"]), 8)

            malformed = deepcopy(document)
            malformed["flow"]["steps"] = malformed["flow"]["steps"][2:]
            malformed["flow"]["steps"][0]["arguments"]["results"] = {
                "literal": [row(["truthy"]), row(valid)]
            }
            broken = await run(malformed)
            self.assertEqual(broken["status"], "failed", broken)
            self.assertIsNone(broken["outputs"])
            self.assertEqual(
                [r["tool"] for r in broken["calls"]],
                [
                    PREFIX + n
                    for n in ["begin_validation", "inspect_current", "check_nonempty"]
                ],
            )
            with self.assertRaises(AttributeError):
                source().check_nonempty({"findings": []}, row(["truthy"]))

            for position, count in [(1, 2), (3, 7)]:
                bounded = deepcopy(document)
                bounded["flow"]["steps"][position]["max_iterations"] = 1
                exhausted = await run(bounded)
                self.assertEqual(exhausted["status"], "failed", exhausted)
                self.assertEqual(exhausted["failure_disposition"], "fail")
                self.assertIsNone(exhausted["outputs"])
                self.assertEqual(len(exhausted["calls"]), count)
            budget = deepcopy(document)
            budget["policy"]["limits"]["max_operation_calls"] = 1
            exhausted = await run(budget)
            self.assertEqual(exhausted["status"], "failed")
            self.assertIsNone(exhausted["outputs"])
            self.assertEqual(
                sum(
                    bool(c.get("transport_call_performed")) for c in exhausted["calls"]
                ),
                1,
            )
            # Collection and validation cannot silently walk past the native end.
            with self.assertRaises(Exception):
                await call(
                    "collect_next",
                    results=expected["results"],
                    context={"repository_root": str(root)},
                )
            with self.assertRaises(Exception):
                await call(
                    "inspect_current",
                    state={"index": 2, "results": expected["results"], "findings": []},
                )
        self.assertFalse(manager.active)
        self.assertFalse((root / "artifacts").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
