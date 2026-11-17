#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native oracle, real registered MCP ports and Lunar/PRISM runtime fixtures.

There is no provider/model or external compiler boundary in this source. All
symbolic calculations, five numeric samples, validation and rendering run for
real against temporary fixture/output mounts. PRISM parsing/checking/compiling
and execution are real. No production suite outputs or credentials are used.
"""

from tempfile import gettempdir
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
import hashlib
import json
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch
import yaml
from controlled_sympy_tools import source, register_controlled_sympy_tools
from mcp.server.fastmcp import FastMCP
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
from mcp_connections.workflow_contract.validator import validate

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_sympy_controlled_workflow/workflow.yaml"
PREFIX = "mathformer_controlled_sympy_"


def fixture(root):
    shutil.copytree(
        ROOT / "tests/physics_sympy/controlled_latex",
        root / "tests/physics_sympy/controlled_latex",
    )
    for name in ("scripts", "backends", "libraries"):
        (root / name).symlink_to(ROOT / name, target_is_directory=True)
    return root


def stable(value):
    # Source clocks run normally. Normalize only their nondeterministic value.
    if isinstance(value, dict):
        return {
            key: stable(item) for key, item in value.items() if key != "generated_at"
        }
    if isinstance(value, list):
        return [stable(item) for item in value]
    if isinstance(value, str):
        return re.sub(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:\+00:00|Z)",
            "<native-clock>",
            value,
        )
    return value


def artifacts(root):
    return {
        str(p.relative_to(root)): stable(p.read_text())
        for p in (root / "out").rglob("*")
        if p.is_file()
    }


def oracle(native):
    # Only the selected original function is frozen; its unchanged helpers are
    # real source functions. The refactored entrypoint shares those same helpers.
    namespace = dict(vars(native))
    exec(
        (ROOT / "tests/mcp/fixtures/controlled_sympy_original.py.txt").read_text(),
        namespace,
    )
    return namespace["controlled_suite"]


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


# Passive write observation also checks the order of native persistence calls.
watch = {"root": None, "writes": []}


def observe(event, args):
    if (
        event == "open"
        and watch["root"]
        and isinstance(args[0], str)
        and args[1]
        and any(c in args[1] for c in "wax")
    ):
        path = Path(args[0])
        if path.is_relative_to(watch["root"] / "out"):
            watch["writes"].append(str(path.relative_to(watch["root"])))


sys.addaudithook(observe)


class ControlledSympyTests(unittest.TestCase):
    def test_service_policies_and_input_integrity(self):
        async def check():
            server = FastMCP("policy-fixture")

            def deny():
                raise ValueError("read-only policy")

            register_controlled_sympy_tools(server, deny, lambda path: True)
            with self.assertRaisesRegex(Exception, "read-only policy"):
                await server.call_tool(
                    PREFIX + "initialize",
                    {
                        "output_root": str(
                            Path(gettempdir())
                            / "mathformer-test-fixtures/never-written"
                        )
                    },
                )
            server = FastMCP("mount-fixture")
            register_controlled_sympy_tools(server, lambda: None, lambda path: False)
            with self.assertRaisesRegex(Exception, "outside allowed write roots"):
                await server.call_tool(
                    PREFIX + "initialize",
                    {
                        "output_root": str(
                            Path(gettempdir())
                            / "mathformer-test-fixtures/never-written"
                        )
                    },
                )
            # Inconsistent native serializations are rejected before using state.
            server = FastMCP("state-fixture")
            register_controlled_sympy_tools(server, lambda: None, lambda path: True)
            with self.assertRaisesRegex(Exception, "disagree"):
                await server.call_tool(
                    PREFIX + "iteration_guard",
                    {"cases": {"items": [], "native_json": "[{}]"}},
                )

        asyncio.run(check())

    def test_native_and_registered_lunar_runtime(self):
        with tempfile.TemporaryDirectory(prefix="controlled-sympy-") as directory:
            root = fixture(Path(directory))
            with patch.object(source(), "REPO_ROOT", root):
                asyncio.run(self.scenario(root))

    async def scenario(self, root):
        native = source()
        document_path = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
        document = yaml.safe_load(document_path.read_text())
        self.assertEqual(document["id"], "hub_physics_sympy_controlled_workflow")
        self.assertEqual(document["lifecycle"], "active")
        with tempfile.TemporaryDirectory(
            prefix=".controlled-contract-", dir=ROOT
        ) as validation_dir:
            validation_path = Path(validation_dir) / "workflow.json"
            validation_path.write_text(json.dumps(document))
            checked = validate(validation_path, ROOT, True)
        self.assertTrue(checked["valid"], checked)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            "backends/sympy/MathformerPhysicsSympy/pipeline.py",
            [r["path"] for r in document["provenance"]["sources"]],
        )
        ids = native.controlled_case_ids()
        self.assertEqual(len(ids), 8)
        out = root / "out"
        watch.update(root=root, writes=[])
        expected = oracle(native)(out, include_details=True)
        expected_files, expected_writes = artifacts(root), list(watch["writes"])
        self.assertTrue(expected["ok"])
        self.assertEqual([c["case_id"] for c in expected["cases"]], ids)
        self.assertEqual(
            len(expected_files), 65
        )  # eight artifacts/reports per case plus suite
        shutil.rmtree(out)
        watch["writes"] = []
        actual = native.controlled_suite(out, include_details=True)
        self.assertEqual(stable(actual), stable(expected))
        self.assertEqual(artifacts(root), expected_files)
        self.assertEqual(watch["writes"], expected_writes)
        watch["root"] = None
        for case in actual["cases"]:
            report = case["consistency"]
            numeric = report["packets"]["numeric_sanity"]
            self.assertEqual(numeric["sample_count"], 5)
            self.assertEqual(len(numeric["domain_checks"]), 5)
            self.assertEqual(
                [s["sample_index"] for s in numeric["sample_results"]], list(range(5))
            )
            self.assertEqual(numeric["counterexamples"], [])
            self.assertTrue(
                all(s["domain_ok"] and s["passed"] for s in numeric["sample_results"])
            )
            self.assertTrue(case["controlled_validation"]["ok"])
            self.assertEqual(report["status"], "complete")
        # Exercise real numeric negative controls and zero-sample boundary.
        case_id = ids[0]
        sample = actual["cases"][0]["consistency"]["packets"]["numeric_sanity"][
            "sample_results"
        ][0]["sample"]
        trial = native.evaluate_numeric_trial(
            case_id, sample, native.derive_case(case_id)["expected_expression"] + 1
        )
        self.assertFalse(trial["passed"])
        self.assertEqual(trial["counterexample"]["sampled_values"], sample)
        self.assertTrue(trial["counterexample"]["failed_step_id"])
        zero = native.build_physics_numeric_sanity_packet(case_id, sample_count=0)
        self.assertEqual(zero["sample_count"], 0)
        self.assertEqual(zero["domain_checks"], [])
        self.assertEqual(zero["sample_results"], [])
        self.assertEqual(zero["counterexamples"], [])

        manager = SessionManager()
        failure = None
        async with manager.open(
            "controlled-sympy",
            StdioConfig(
                command=sys.executable,
                args=["tests/mcp/fixtures/controlled_sympy_server.py", str(root)],
                cwd=str(ROOT),
                timeout_seconds=600,
            ),
            {"PYTHONPATH": os.environ["PYTHONPATH"]},
        ) as remote:
            try:
                inventory = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, tools=None):
                    received = assets(doc)
                    compiled = compile_workflow(
                        "mcp:controlled-sympy",
                        workflow_documents([DESCRIPTOR], received)[0],
                        inventory if tools is None else tools,
                    )
                    return compiled, received

                compiled, received = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(doc=None, details=False):
                    w, a = compile(doc) if doc else (compiled, received)
                    return await execute(
                        w,
                        a,
                        {"output_root": str(out), "include_details": details},
                        remote,
                        authorize,
                    )

                async def call(name, **kwargs):
                    return await remote.call(PREFIX + name, kwargs)

                for details in (True, False):
                    shutil.rmtree(out)
                    await remote.call("fixture_writes", {})
                    result = await run(details=details)
                    self.assertEqual(result["status"], "accepted", result)
                    gold = deepcopy(expected)
                    if not details:
                        for c in gold["cases"]:
                            for key in (
                                "draft",
                                "consistency",
                                "controlled_validation",
                            ):
                                c.pop(key)
                    self.assertEqual(stable(result["outputs"]["suite"]), stable(gold))
                    self.assertEqual(
                        stable(json.loads((out / "suite_report.json").read_text())),
                        stable(gold),
                    )
                    files = artifacts(root)
                    self.assertEqual(
                        {
                            k: v
                            for k, v in files.items()
                            if not k.endswith("suite_report.json")
                        },
                        {
                            k: v
                            for k, v in expected_files.items()
                            if not k.endswith("suite_report.json")
                        },
                    )
                    if details:
                        self.assertEqual(files, expected_files)
                    self.assertEqual(
                        (await remote.call("fixture_writes", {}))["writes"],
                        expected_writes,
                    )
                    self.assertEqual(
                        [r["tool"] for r in result["calls"]],
                        [
                            PREFIX + n
                            for n in ["initialize"]
                            + [
                                "generate",
                                "assess",
                                "validate_persist_append",
                                "iteration_guard",
                            ]
                            * 8
                            + ["finalize"]
                        ],
                    )
                    self.assertEqual(len(result["calls"]), 34)
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])

                # Real classifier inputs produce both non-success dispositions.
                # These report fixtures are supplied to the actual registered
                # validation/persistence step; no source helper is substituted.
                state = (await call("initialize", output_root=str(out)))["cases"]
                for i, gold_case in enumerate(expected["cases"]):
                    before = deepcopy(state)
                    draft = (await call("generate", output_root=str(out), cases=state))[
                        "draft"
                    ]
                    self.assertEqual(draft["case_id"], ids[i])
                    report = deepcopy(gold_case["consistency"])
                    if i < 2:
                        validation = (
                            {"all_derivation_steps_execute": False}
                            if i == 0
                            else {"all_equations_dimensionally_consistent": False}
                        )
                        completion = native.classify_physics_sympy_completion(
                            validation
                        )
                        self.assertEqual(
                            completion["status"], "draft" if i == 0 else "blocked"
                        )
                        report.update(
                            status=completion["status"],
                            ok=False,
                            completion_semantics=completion,
                        )
                    report = {
                        **report,
                        "native_json": json.dumps(report, ensure_ascii=False),
                    }
                    state = (
                        await call(
                            "validate_persist_append",
                            output_root=str(out),
                            cases=state,
                            draft=draft,
                            report=report,
                            include_details=True,
                        )
                    )["cases"]
                    self.assertEqual(state["items"][:-1], before["items"])
                    self.assertEqual(json.loads(state["native_json"]), state["items"])
                    self.assertEqual(
                        (await call("iteration_guard", cases=state))["done"], i == 7
                    )
                suite = (await call("finalize", output_root=str(out), cases=state))[
                    "suite"
                ]
                self.assertFalse(suite["ok"])
                self.assertEqual(suite["case_count"], 8)
                self.assertEqual(
                    [c["status"] for c in suite["cases"]],
                    ["draft", "blocked"] + ["complete"] * 6,
                )
                self.assertEqual(
                    suite["cases"][0]["failed_controlled_checks"],
                    ["consistency_status_complete"],
                )
                self.assertTrue(suite["cases"][-1]["controlled_validation_ok"])
                with self.assertRaises(Exception):
                    await call("generate", output_root=str(out), cases=state)
                with self.assertRaises(Exception):
                    await call(
                        "finalize",
                        output_root=str(out),
                        cases={"items": [], "native_json": "[]"},
                    )

                # The original entrypoint also aborts on a missing controlled input.
                # Loop and operation budgets are compiler fixtures only; all actual
                # bound tools, source steps and PRISM runtime remain unchanged.
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 1
                shutil.rmtree(out)
                result = await run(bounded)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(result["failure_disposition"], "fail")
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 5)
                self.assertFalse((out / "suite_report.json").exists())
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 1
                result = await run(budget)
                self.assertEqual(result["status"], "failed")
                self.assertIsNone(result["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    1,
                )
                missing = (
                    root / "tests/physics_sympy/controlled_latex" / f"{ids[2]}.tex"
                )
                missing.unlink()
                shutil.rmtree(out)
                with self.assertRaises(FileNotFoundError):
                    oracle(native)(out, include_details=False)
                expected_partial = artifacts(root)
                shutil.rmtree(out)
                result = await run()
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertEqual(len(result["calls"]), 12)
                self.assertEqual(
                    result["calls"][-1]["tool"], PREFIX + "validate_persist_append"
                )
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                self.assertEqual(artifacts(root), expected_partial)
                self.assertEqual(len(list(out.rglob("controlled_validation.json"))), 2)
                self.assertFalse((out / ids[3]).exists())
                self.assertFalse((out / "suite_report.json").exists())
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
