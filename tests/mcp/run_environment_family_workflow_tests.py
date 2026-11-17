#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Exercise native environment steps, MCP bindings, and real Lunar/PRISM execution."""

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
import hashlib
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

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_family_environment_workflow/workflow.yaml"
ARGS = dict(
    module_family=["environment"],
    changed_files_only=False,
    emit_dependency_map_only=False,
    profile="workstation",
    fail_on_warning=False,
    validate_matrix=False,
    run_id="fixture",
)


def matrix(modes, family="environment"):
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
                "timeout_seconds": 360,
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
    paths = {r["path"] for r in document["provenance"]["sources"]}
    values = {p: (ROOT / p).read_text() for p in paths}
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


class EnvironmentFamilyTests(unittest.TestCase):
    def test_native_invariants(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests").mkdir()
            native = source_runner()
            install(native, root)
            data = matrix(["pass"])
            data["tests"][0]["command"] = ["{python}", "-c", "import fixture_provider"]
            native.MATRIX_FILE.write_text(json.dumps(data))
            args = native.parse_args(
                ["--module-family", "environment", "--json", "--run-id", "fixture"]
            )
            state = native.prepare_checks(args)
            self.assertEqual(state["selected"][0]["command"][0], native.PYTHON)
            with self.assertRaisesRegex(ValueError, "unconsumed"):
                native.finalize_checks(state, args)
            broken = deepcopy(state)
            broken["results"] = [{}]
            with self.assertRaisesRegex(ValueError, "cursor"):
                native.advance_check(broken, args)
            final = native.advance_check(state, args)
            with self.assertRaisesRegex(ValueError, "exhausted"):
                native.advance_check(final, args)
            self.assertFalse(native.finalize_checks(final, args)["ok"])
            missing = matrix(["missing"])["tests"][0]
            self.assertEqual(native.run_check(missing, False)["status"], "skip")
            self.assertEqual(native.run_check(missing, True)["status"], "fail")

    def test_native_uncapped_and_schema_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "tests").mkdir()
            native = source_runner()
            install(native, root)
            native.MATRIX_FILE.write_text(json.dumps(matrix(["pass"] * 3)))
            args = native.parse_args(
                ["--module-family", "environment", "--run-id", "fixture"]
            )
            self.assertEqual(native.run(args)["summary"]["pass"], 3)
            state = native.prepare_checks(args)
            while state["index"] < len(state["selected"]):
                state = native.advance_check(state, args)
            state["results"][0].pop("regression_fingerprint")
            report = native.finalize_checks(state, args)
            self.assertFalse(report["ok"])
            self.assertTrue(
                any("regression_fingerprint" in e for e in report["schema_errors"])
            )

    def test_lunar_registered_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_test_family_environment_workflow")
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
            oracle = types.ModuleType("environment_original")
            oracle.__file__ = str(
                ROOT / "tests/test_program/run_comprehensive_tests.py"
            )
            exec(
                compile(
                    (
                        ROOT / "tests/mcp/fixtures/environment_family_original.py.txt"
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
                "environment-family",
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
                        compiled = compile_workflow(
                            "mcp:environment-family",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return compiled, assets

                    from mcp_connections.workflow_contract.validator import validate

                    with tempfile.NamedTemporaryFile(
                        mode="w+", suffix=".json", dir=ROOT
                    ) as check:
                        json.dump(document, check)
                        check.flush()
                        validation = validate(
                            check.name,
                            repository_root=ROOT,
                            require_declared_bindings=True,
                        )
                    self.assertFalse(validation["errors"], validation)
                    advertised = {t["name"]: t for t in tools}
                    for operation in document["operations"].values():
                        binding = operation["execution"]["binding"]
                        self.assertEqual(binding["operation"], binding["target"])
                        tool = advertised[binding["target"]]
                        self.assertEqual(
                            set(tool["inputSchema"]["properties"]),
                            set(operation["inputs"]),
                        )
                        self.assertEqual(
                            set(tool["outputSchema"]["properties"]),
                            set(operation["outputs"]),
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

                    async def run(data, doc=None, args=None):
                        path.write_text(json.dumps(data))
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        c, a = compile_doc(doc) if doc else (compiled, assets)
                        self.assertTrue(c["runnable"], c["diagnostics"])
                        return await execute(
                            c,
                            a,
                            {"args": ARGS if args is None else args},
                            remote,
                            authorize,
                        )

                    mixed = matrix(["pass", "fail", "pass"])
                    mixed["tests"][1]["module_family"] = "atp"
                    for data in [
                        matrix(["pass"] * 2),
                        matrix(["fail", "timeout"]),
                        matrix(["write", "pass"]),
                        matrix(["missing", "pass"]),
                        matrix(["pass"], "atp"),
                        mixed,
                    ]:
                        result = await run(data)
                        self.assertEqual(result["status"], "accepted", result)
                        report = result["outputs"]["report"]
                        expected = [
                            r["id"]
                            for r in data["tests"]
                            if r["module_family"] == "environment"
                        ]
                        self.assertEqual(
                            [r["check_id"] for r in report["results"]], expected
                        )
                        self.assertEqual(
                            sum(
                                c["operation"] == "advance_check"
                                for c in result["calls"]
                            ),
                            len(expected),
                        )
                        self.assertEqual(
                            len(result["calls"]),
                            2 * len(expected) + 3 if expected else 4,
                        )
                        self.assertEqual(report["schema_errors"], [])
                        self.assertTrue((root / report["dependency_map"]).is_file())
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        if data["tests"][0]["command"][-1] == "fail":
                            self.assertEqual(
                                [r["status"] for r in report["results"]],
                                ["fail", "fail"],
                            )
                            self.assertEqual(
                                report["results"][1]["stderr"], "timeout after 360s"
                            )
                        if data["tests"][0]["command"][-1] == "write":
                            self.assertFalse(report["results"][0]["write_audit"]["ok"])
                            self.assertFalse(report["ok"])
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        self.assertEqual(
                            report,
                            oracle.run(
                                oracle.parse_args(
                                    [
                                        "--module-family",
                                        "environment",
                                        "--json",
                                        "--run-id",
                                        "fixture",
                                    ]
                                )
                            ),
                        )
                    # Snapshot exits before even reading an invalid matrix.
                    snap_args = {**ARGS, "emit_dependency_map_only": True}
                    snapshot_result = await run({"schema_version": 1}, args=snap_args)
                    self.assertEqual(
                        snapshot_result["status"], "accepted", snapshot_result
                    )
                    self.assertEqual(
                        [c["operation"] for c in snapshot_result["calls"]],
                        [
                            "ensure_artifacts",
                            "empty_snapshot",
                            "retain_consumed",
                            "snapshot_report",
                        ],
                    )
                    self.assertEqual(
                        snapshot_result["outputs"]["report"],
                        oracle.run(
                            oracle.parse_args(
                                [
                                    "--module-family",
                                    "environment",
                                    "--run-id",
                                    "fixture",
                                    "--emit-dependency-map-only",
                                ]
                            )
                        ),
                    )
                    for overrides in [{"profile": "strict"}, {"fail_on_warning": True}]:
                        strict = await run(
                            matrix(["missing", "pass"]), args={**ARGS, **overrides}
                        )
                        self.assertEqual(strict["status"], "accepted", strict)
                        self.assertFalse(strict["outputs"]["report"]["ok"])
                        self.assertEqual(
                            [
                                r["status"]
                                for r in strict["outputs"]["report"]["results"]
                            ],
                            ["fail", "pass"],
                        )
                    coverage = await run(
                        matrix(["pass"]), args={**ARGS, "validate_matrix": True}
                    )
                    self.assertEqual(coverage["status"], "accepted", coverage)
                    self.assertTrue(coverage["outputs"]["report"]["matrix_errors"])
                    self.assertEqual(
                        coverage["outputs"]["report"]["results"][-1]["check_id"],
                        "meta.matrix_coverage",
                    )
                    self.assertFalse(coverage["outputs"]["report"]["ok"])
                    default_timeout = matrix(["timeout"])
                    default_timeout["tests"][0].pop("timeout_seconds")
                    timeout = await run(default_timeout)
                    self.assertEqual(
                        timeout["outputs"]["report"]["results"][0]["stderr"],
                        "timeout after 120s",
                    )
                    exhausted = deepcopy(document)
                    exhausted["flow"]["steps"][2]["max_iterations"] = 1
                    result = await run(matrix(["pass", "pass"]), exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertFalse(
                        any(
                            c["operation"] == "finalize_checks" for c in result["calls"]
                        )
                    )
                    result = await run(matrix(["pass"] * 3))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["ensure_artifacts", "prepare_checks"],
                    )
                    bad = matrix(["pass"])
                    bad["schema_version"] = 1
                    result = await run(bad)
                    self.assertEqual(result["status"], "failed", result)
                    with self.assertRaisesRegex(ValueError, "schema_version 2"):
                        oracle.run(
                            oracle.parse_args(["--module-family", "environment"])
                        )
                    result = await run(matrix(["crash", "pass"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["ensure_artifacts", "prepare_checks", "advance_check"],
                    )
                    with self.assertRaisesRegex(
                        OSError, "fixture compiler launch failed"
                    ):
                        oracle.run(
                            oracle.parse_args(["--module-family", "environment"])
                        )
                    expected = matrix(["fail"])
                    expected["tests"][0]["expected_exit"] = 7
                    self.assertTrue((await run(expected))["outputs"]["report"]["ok"])
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    self.assertEqual(
                        (await run(matrix(["pass"]), budget))["status"], "failed"
                    )
                    path.write_text(json.dumps(matrix(["pass"])))
                    context = (
                        await remote.call(
                            "mathformer_environment_ensure_artifacts", {"args": ARGS}
                        )
                    )["context"]
                    prepared = await remote.call(
                        "mathformer_environment_prepare_checks",
                        {"args": ARGS, "context": context},
                    )
                    state = prepared["state"]
                    ports = dict(state=state, context=context, args=ARGS)
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_environment_finalize_checks", ports
                        )
                    forged = deepcopy(state)
                    forged["selected"][0]["command"] = ["forged"]
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_environment_advance_check",
                            {**ports, "state": forged},
                        )
                    advanced = await remote.call(
                        "mathformer_environment_advance_check", ports
                    )
                    self.assertEqual(advanced["state"]["index"], 1)
                    self.assertEqual(advanced["state"]["matrix"], state["matrix"])
                    self.assertEqual(
                        advanced["state"]["results"][0]["check_id"], "fixture.0"
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call("mathformer_environment_advance_check", ports)
                    done = await remote.call(
                        "mathformer_environment_cursor_guard",
                        dict(state=advanced["state"], context=context),
                    )
                    self.assertTrue(done["done"])
                    final_ports = {**ports, "state": advanced["state"]}
                    await remote.call(
                        "mathformer_environment_finalize_checks", final_ports
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_environment_finalize_checks", final_ports
                        )

                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
