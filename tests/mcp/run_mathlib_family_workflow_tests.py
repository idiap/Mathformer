#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline source/MCP/Lunar regression gate; only provider/compiler boundaries vary."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(ROOT / "tests/mcp/fixtures"),
]
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path.extend(SITES)

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import shutil
import tempfile
import types
import unittest
import yaml
from mathlib_family_boundary import install
from comprehensive_strict_tools import source_runner
from mathlib_family_workflow_tools import register_mathlib_family_tools
from mathlib_route_tree import matrix
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_test_family_mathlib_workflow/workflow.yaml"
AUTHORED = (
    "skills/control/workflow-contract-validator/references/mathlib-family.workflow.json"
)
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
ARGS = dict(
    run_id="mathlib-fixture",
    module_family=["mathlib"],
    changed_files_only=False,
    emit_dependency_map_only=False,
    profile="workstation",
    fail_on_warning=False,
    validate_matrix=False,
)


def argv(args):
    result = [
        "--module-family",
        "mathlib",
        "--json",
        "--run-id",
        args["run_id"],
        "--profile",
        args["profile"],
    ]
    for key in ("emit_dependency_map_only", "fail_on_warning", "validate_matrix"):
        if args[key]:
            result.append("--" + key.replace("_", "-"))
    return result


def snapshot(doc):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in doc["provenance"]["sources"]
    }
    values[DESCRIPTOR] = json.dumps(doc)
    return [
        dict(
            path=p,
            content=s,
            encoding="text",
            sha256=hashlib.sha256(s.encode()).hexdigest(),
        )
        for p, s in values.items()
    ]


def oracle(root):
    # Frozen pre-guard-extraction entrypoint, independent of the MCP wrappers.
    module = types.ModuleType("mathlib_original")
    module.__file__ = str(ROOT / "tests/test_program/run_comprehensive_tests.py")
    exec(
        compile(
            (ROOT / "tests/mcp/fixtures/mathlib_family_original.py.txt").read_text(),
            module.__file__,
            "exec",
        ),
        module.__dict__,
    )
    install(module, root)
    return module


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k != "duration_seconds"}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


class MathlibTests(unittest.TestCase):
    maxDiff = None

    def test_identity_policies_provenance_and_authored_generator(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(doc, json.loads((ROOT / AUTHORED).read_text()))
        self.assertEqual(
            (doc["namespace"], doc["id"], doc["version"]),
            ("mathformer", "hub_test_family_mathlib_workflow", "1.0.0"),
        )
        self.assertEqual(doc["aliases"], ["test:family:mathlib"])
        self.assertEqual(doc["lifecycle"], "active")
        self.assertEqual(doc["activation"]["mode"], "explicit")
        self.assertEqual(
            doc["policy"]["limits"],
            {"wall_time_seconds": 900, "max_operation_calls": 22},
        )
        self.assertEqual(
            doc["policy"]["failure"]["retry"],
            {"max_attempts": 1, "retryable_codes": []},
        )
        self.assertEqual(doc["policy"]["resume"]["mode"], "none")
        self.assertEqual(doc["observability"]["receipts"], "required")
        self.assertEqual(doc["flow"]["steps"][2]["max_iterations"], 9)
        self.assertIn(
            "infer_scientific_truth_from_completion",
            doc["policy"]["authority"]["forbidden"],
        )
        self.assertTrue(
            any(
                r["path"] == "tests/test_program/run_comprehensive_tests.py"
                and r["selector"] == "run"
                for r in doc["provenance"]["sources"]
            )
        )
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("mathlib_normalizer", path)
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(generator.mathlib_family_descriptor(), doc)
        data = json.loads((ROOT / "tests/test_matrix.json").read_text())
        rows = [r for r in data["tests"] if r["module_family"] == "mathlib"]
        self.assertEqual(len(rows), 9)
        self.assertEqual(set(r["timeout_seconds"] for r in rows), {120, 240, 480})
        import mathformer as hub

        registry = hub.build_registry()
        self.assertEqual(registry["test:family:mathlib"].timeout_seconds, 900)
        audit = hub.audit_control(registry)
        for path in (
            "scripts/mathlib_family_workflow_tools.py",
            "tests/mcp/run_mathlib_family_workflow_tests.py",
        ):
            self.assertIn(path, audit["control_sources"]["internal_helpers"])
            self.assertNotIn(path, audit["uncontrolled_entrypoints"])

    def test_native_cursor_history_no_native_row_cap_and_schema_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "repo"
            (root / "tests").mkdir(parents=True)
            native = source_runner()
            install(native, root)
            data = matrix(["pass"])
            data["tests"][0]["command"] = ["{python}", "{sympy_python}"]
            native.MATRIX_FILE.write_text(json.dumps(data))
            state = native.prepare_checks(native.parse_args(argv(ARGS)))
            self.assertEqual(
                state["selected"][0]["command"], [native.PYTHON, native.SYMPY_PYTHON]
            )
            native.MATRIX_FILE.write_text(json.dumps(matrix(["fail", "pass"] * 6)))
            args = native.parse_args(argv(ARGS))
            self.assertFalse(native.enter_checks(args))
            state = native.prepare_checks(args)
            self.assertEqual(len(state["selected"]), 12)
            with self.assertRaisesRegex(ValueError, "unconsumed"):
                native.finalize_checks(state, args)
            broken = deepcopy(state)
            broken["results"] = [{}]
            with self.assertRaisesRegex(ValueError, "cursor"):
                native.advance_check(broken, args)
            while native.checks_pending(state):
                prior = deepcopy(state)
                state = native.advance_check(state, args)
                self.assertEqual(state["index"], prior["index"] + 1)
                self.assertEqual(state["results"][:-1], prior["results"])
                for key in ("matrix", "selected", "families"):
                    self.assertEqual(state[key], prior[key])
            with self.assertRaisesRegex(ValueError, "exhausted"):
                native.advance_check(state, args)
            report = native.finalize_checks(state, args)
            self.assertEqual(
                report["summary"],
                {"total": 12, "pass": 6, "fail": 6, "skip": 0, "warn": 0},
            )
            self.assertFalse(report["ok"])
            invalid = deepcopy(state)
            del invalid["results"][0]["command"]
            report = native.finalize_checks(invalid, args)
            self.assertFalse(report["ok"])
            self.assertIn("command", report["schema_errors"][0])
            native.MATRIX_FILE.unlink()
            early = {**ARGS, "emit_dependency_map_only": True}
            original = oracle(root)
            self.assertEqual(
                native.run(native.parse_args(argv(early))),
                original.run(original.parse_args(argv(early))),
            )
            asyncio.run(self.policy_checks(root))

    async def policy_checks(self, root):
        from mcp.server.fastmcp import FastMCP

        for authorize, allowed in [
            (
                lambda: (_ for _ in ()).throw(PermissionError("readonly")),
                lambda p: True,
            ),
            (lambda: None, lambda p: False),
        ]:
            registry = FastMCP("mathlib-policy")
            register_mathlib_family_tools(registry, authorize, allowed)
            with self.assertRaisesRegex(Exception, "readonly|write roots"):
                await registry.call_tool(
                    "mathformer_mathlib_family_enter", {"args": ARGS}
                )
        enabled = [True]

        def authorize():
            if not enabled[0]:
                raise PermissionError("readonly")

        registry = FastMCP("mathlib-recheck")
        register_mathlib_family_tools(registry, authorize)
        entered = (
            await registry.call_tool("mathformer_mathlib_family_enter", {"args": ARGS})
        )[1]
        enabled[0] = False
        with self.assertRaisesRegex(Exception, "readonly"):
            await registry.call_tool(
                "mathformer_mathlib_family_prepare",
                dict(args=ARGS, matrix=matrix(["pass"]), context=entered["context"]),
            )
        data = matrix(["pass"])
        data["tests"][0]["write_set"] = ["outside-policy/"]
        (root / "tests/test_matrix.json").write_text(json.dumps(data))
        registry = FastMCP("mathlib-declared-writes")
        register_mathlib_family_tools(
            registry, path_allowed=lambda p: Path(p).is_relative_to(root / "artifacts")
        )
        entered = (
            await registry.call_tool("mathformer_mathlib_family_enter", {"args": ARGS})
        )[1]
        with self.assertRaisesRegex(Exception, "write roots"):
            await registry.call_tool(
                "mathformer_mathlib_family_prepare",
                dict(args=ARGS, matrix=data, context=entered["context"]),
            )

    def test_registered_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "repo"
            (root / "tests").mkdir(parents=True)
            path = root / "tests/test_matrix.json"
            ledger_path = root.parent / "repo-compiler.jsonl"
            original = oracle(root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr(
                    [
                        str(ROOT / "scripts"),
                        str(ROOT / "tests/mcp/fixtures"),
                        str(ROOT),
                        *SITES,
                    ]
                )
                + ";from mathlib_family_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            failure = None
            async with manager.open(
                "mathlib",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compiled(document, inventory=None):
                        assets = snapshot(document)
                        workflow = compile_workflow(
                            "mcp:mathlib",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return workflow, assets

                    workflow, _ = compiled(doc)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertEqual(workflow["runtime_status"], "ready")
                    self.assertTrue(workflow["runtime_source"])
                    self.assertTrue(workflow["prism_source_hash"])
                    self.assertEqual(set(workflow["bindings"]), set(doc["operations"]))
                    self.assertFalse(compiled(doc, [])[0]["runnable"])
                    for name in doc["operations"]:
                        target = doc["operations"][name]["execution"]["binding"][
                            "target"
                        ]
                        self.assertTrue(any(t["name"] == target for t in tools))
                        self.assertFalse(
                            compiled(doc, [t for t in tools if t["name"] != target])[0][
                                "runnable"
                            ]
                        )

                    async def authorize():
                        pass

                    async def run(
                        data,
                        document=doc,
                        args=ARGS,
                        supplied=None,
                        omit_matrix=False,
                        blocker=None,
                    ):
                        if data is None:
                            path.unlink(missing_ok=True)
                        else:
                            path.write_text(json.dumps(data))
                        shutil.rmtree(root / "artifacts", ignore_errors=True)
                        (root / "undeclared.txt").unlink(missing_ok=True)
                        ledger_path.unlink(missing_ok=True)
                        w, assets = compiled(document)
                        self.assertTrue(w["runnable"], w["diagnostics"])
                        ports = {"args": args}
                        if not omit_matrix:
                            ports["matrix"] = data if supplied is None else supplied
                        blocked = root / "artifacts/test_program/dependency_map.json"
                        if blocker:
                            blocked.mkdir(parents=True)
                        try:
                            return await execute(w, assets, ports, remote, authorize)
                        finally:
                            if blocker:
                                blocked.rmdir()

                    mixed = matrix(["pass", "fail", "pass"])
                    mixed["tests"][1]["module_family"] = "atp"
                    expected_exit = matrix(["large", "fail", "pass"])
                    expected_exit["tests"][1]["expected_exit"] = 7
                    del expected_exit["tests"][2]["timeout_seconds"]
                    cases = [
                        (matrix(["pass"] * 9), ARGS),
                        (
                            matrix(
                                ["fail", "timeout", "write", "missing", "large", "pass"]
                            ),
                            ARGS,
                        ),
                        (matrix(["pass"], "atp"), ARGS),
                        (mixed, ARGS),
                        (expected_exit, ARGS),
                        (matrix(["missing"]), ARGS),
                        (matrix(["missing"]), {**ARGS, "fail_on_warning": True}),
                        (matrix(["missing"]), {**ARGS, "profile": "strict"}),
                        (matrix(["pass"]), {**ARGS, "profile": "strict"}),
                        (matrix(["pass"]), {**ARGS, "validate_matrix": True}),
                    ]
                    for data, args in cases:
                        with self.subTest(data=data, args=args):
                            result = await run(data, args=args)
                            self.assertEqual(result["status"], "accepted", result)
                            report = result["outputs"]["report"]
                            rows = [
                                r
                                for r in data["tests"]
                                if r["module_family"] == "mathlib"
                            ]
                            operations = [c["operation"] for c in result["calls"]]
                            self.assertEqual(
                                operations,
                                ["enter", "prepare", "pending"]
                                + (
                                    ["advance", "pending"] * len(rows)
                                    if rows
                                    else ["retain"]
                                )
                                + ["finalize"],
                            )
                            self.assertEqual(
                                [r["check_id"] for r in report["results"][: len(rows)]],
                                [r["id"] for r in rows],
                            )
                            self.assertEqual(report["schema_errors"], [])
                            self.assertTrue((root / report["dependency_map"]).is_file())
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["replay_artifacts"])
                            for receipt in result["calls"]:
                                self.assertEqual(receipt["status"], "accepted")
                                self.assertEqual(len(receipt["input_digest"]), 64)
                                self.assertEqual(len(receipt["output_digest"]), 64)
                            ledger = (
                                [
                                    json.loads(s)
                                    for s in ledger_path.read_text().splitlines()
                                ]
                                if ledger_path.exists()
                                else []
                            )
                            self.assertEqual(
                                ledger,
                                [
                                    dict(
                                        command=r["command"],
                                        timeout=r.get("timeout_seconds", 120),
                                    )
                                    for r in rows
                                    if "optional_dependency" not in r
                                ],
                            )
                            if len(rows) == 9:
                                self.assertEqual(len(result["calls"]), 22)
                                self.assertTrue(report["ok"])
                                self.assertEqual(report["summary"]["pass"], 9)
                            if len(rows) == 6:
                                self.assertEqual(
                                    [r["status"] for r in report["results"]],
                                    ["fail", "fail", "fail", "skip", "pass", "pass"],
                                )
                                self.assertEqual(
                                    report["results"][1]["stderr"], "timeout after 31s"
                                )
                                self.assertEqual(
                                    report["results"][1]["stdout"], "partial"
                                )
                                self.assertFalse(
                                    report["results"][2]["write_audit"]["ok"]
                                )
                                self.assertIn(
                                    "undeclared.txt",
                                    report["results"][2]["write_audit"][
                                        "unexpected_paths"
                                    ],
                                )
                                self.assertLess(
                                    len(report["results"][4]["stdout"]), 5000
                                )
                                self.assertFalse(report["ok"])
                            if args["validate_matrix"]:
                                self.assertTrue(report["matrix_errors"])
                                self.assertEqual(
                                    report["results"][-1]["check_id"],
                                    "meta.matrix_coverage",
                                )
                                self.assertFalse(report["ok"])
                            if data == matrix(["missing"]):
                                expected = (
                                    "fail"
                                    if args["profile"] == "strict"
                                    or args["fail_on_warning"]
                                    else "skip"
                                )
                                self.assertEqual(
                                    report["results"][0]["status"], expected
                                )
                                self.assertEqual(report["ok"], expected == "skip")
                            (root / "undeclared.txt").unlink(missing_ok=True)
                            self.assertEqual(
                                stable(report),
                                stable(original.run(original.parse_args(argv(args)))),
                            )
                            # run(), unlike main(), owns only the dependency snapshot.
                            self.assertFalse(
                                (
                                    root
                                    / "artifacts/test_program/deterministic_tests.json"
                                ).exists()
                            )
                    early = {**ARGS, "emit_dependency_map_only": True}
                    result = await run(None, args=early, omit_matrix=True)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["enter", "snapshot", "retain", "snapshot_result"],
                    )
                    self.assertEqual(
                        result["outputs"]["report"],
                        original.run(original.parse_args(argv(early))),
                    )
                    self.assertFalse(ledger_path.exists())
                    self.assertFalse(path.exists())
                    result = await run(matrix(["pass"]), omit_matrix=True)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ["enter", "prepare"]
                    )
                    self.assertFalse(ledger_path.exists())
                    # Exhaustion must fail without running the remaining check or finalizing.
                    exhausted = deepcopy(doc)
                    exhausted["flow"]["steps"][2]["max_iterations"] = 1
                    result = await run(matrix(["pass", "pass"]), exhausted)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(result["failure_disposition"], "fail")
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]],
                        ["enter", "prepare", "pending", "advance", "pending"],
                    )
                    self.assertEqual(len(ledger_path.read_text().splitlines()), 1)
                    self.assertFalse(
                        (root / "artifacts/test_program/dependency_map.json").exists()
                    )
                    forced = deepcopy(doc)
                    forced["flow"]["steps"][2]["until"] = {"literal": False}
                    result = await run(matrix(["pass"] * 9), forced)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        sum(c["operation"] == "advance" for c in result["calls"]), 9
                    )
                    self.assertNotIn(
                        "finalize", [c["operation"] for c in result["calls"]]
                    )
                    for data in [
                        matrix(["missing"] * 10),
                        matrix([]),
                        {**matrix(["pass"]), "schema_version": 1},
                    ]:
                        with self.assertRaises(ExecutionRejected):
                            await run(data)
                        self.assertFalse(ledger_path.exists())
                    for changed in [
                        {"module_family": ["atp"]},
                        {"changed_files_only": True},
                        {"run_id": 4},
                        {"extra": True},
                    ]:
                        with self.assertRaises(ExecutionRejected):
                            await run(matrix(["pass"]), args={**ARGS, **changed})
                    malformed = matrix(["pass"])
                    del malformed["tests"][0]["command"]
                    for data in [matrix(["crash", "pass"]), malformed]:
                        result = await run(data)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(result["calls"][-1]["operation"], "advance")
                        self.assertFalse(
                            (
                                root / "artifacts/test_program/dependency_map.json"
                            ).exists()
                        )
                        with self.assertRaises((OSError, KeyError)):
                            original.run(original.parse_args(argv(ARGS)))
                    result = await run(matrix(["pass"]), supplied=matrix(["fail"]))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ["enter", "prepare"]
                    )
                    self.assertFalse(ledger_path.exists())
                    result = await run(matrix(["pass"]), blocker=True)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["operation"], "finalize")
                    result = await run(None, args=early, omit_matrix=True, blocker=True)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["operation"], "snapshot")
                    for limit in (1, 3, 4):
                        budget = deepcopy(doc)
                        budget["policy"]["limits"]["max_operation_calls"] = limit
                        result = await run(matrix(["pass"]), budget)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertEqual(
                            sum(
                                bool(c.get("transport_call_performed"))
                                for c in result["calls"]
                            ),
                            limit,
                        )
                        self.assertIsNone(result["outputs"])
                    await self.owned_ports(remote, path)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure

    async def owned_ports(self, remote, path):
        async def call(name, **ports):
            return await remote.call("mathformer_mathlib_family_" + name, ports)

        data = matrix(["pass", "fail"])
        path.write_text(json.dumps(data))
        entered = await call("enter", args=ARGS)
        ports = dict(args=ARGS, context=entered["context"])
        with self.assertRaises(MCPConnectionError):
            await call("snapshot", **ports)
        state = (await call("prepare", **ports, matrix=data))["state"]
        for i in range(2):
            guarded = await call("pending", state=state, context=ports["context"])
            cursor = guarded["cursor"]
            self.assertTrue(guarded["pending"])
            self.assertEqual(cursor, {"pending": True, "state": state})
            with self.assertRaises(MCPConnectionError):
                await call("finalize", **ports, cursor=cursor)
            forged = deepcopy(cursor)
            forged["state"]["selected"][i]["command"] = ["forged"]
            with self.assertRaises(MCPConnectionError):
                await call("advance", **ports, cursor=forged)
            with self.assertRaises(MCPConnectionError):
                await call(
                    "advance",
                    args={**ARGS, "profile": "strict"},
                    context=ports["context"],
                    cursor=cursor,
                )
            updated = (await call("advance", **ports, cursor=cursor))["state"]
            self.assertEqual(updated["index"], i + 1)
            self.assertEqual(updated["results"][:-1], state["results"])
            for key in ("matrix", "selected", "families"):
                self.assertEqual(updated[key], state[key])
            with self.assertRaises(MCPConnectionError):
                await call("advance", **ports, cursor=cursor)
            state = updated
        guarded = await call("pending", state=state, context=ports["context"])
        self.assertFalse(guarded["pending"])
        with self.assertRaises(MCPConnectionError):
            await call("retain", cursor=guarded["cursor"], context=ports["context"])
        report = (await call("finalize", **ports, cursor=guarded["cursor"]))["report"]
        self.assertFalse(report["ok"])
        self.assertEqual(report["summary"]["total"], 2)
        with self.assertRaises(MCPConnectionError):
            await call("finalize", **ports, cursor=guarded["cursor"])
        # Direct callers cannot bypass the contract's admission bound.
        data = matrix(["pass"] * 10)
        path.write_text(json.dumps(data))
        entered = await call("enter", args=ARGS)
        with self.assertRaises(MCPConnectionError):
            await call("prepare", args=ARGS, context=entered["context"], matrix=data)
        # Failed native launch invalidates the entire invocation.
        data = matrix(["crash"])
        path.write_text(json.dumps(data))
        entered = await call("enter", args=ARGS)
        ports = dict(args=ARGS, context=entered["context"])
        state = (await call("prepare", **ports, matrix=data))["state"]
        cursor = (await call("pending", state=state, context=ports["context"]))[
            "cursor"
        ]
        for _ in range(2):
            with self.assertRaises(MCPConnectionError):
                await call("advance", **ports, cursor=cursor)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
