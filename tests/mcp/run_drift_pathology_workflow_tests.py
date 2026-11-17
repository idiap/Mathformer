#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402
"""Deterministic native fixtures through registered MCP and real Lunar/PRISM.

The monitor has no external model/provider or Lean compiler boundary to replace.
All source steps, MCP transport, PRISM parsing/checking/compilation and runtime
are real. Only temporary fixture inputs and outputs are used.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
import yaml
from drift_pathology_tools import native
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_drift_pathology_monitor_workflow/workflow.yaml"
PREFIX = "mathformer_drift_"
ALL = "quantum ket operator vector gradient integral Newton divide sqrt"
SCALAR = "theorem bad (q : Real) (p : Real) (r : Real) (hpos : 0 < q) (h : q * p = p * q) : q * p = p * q := by simpa using h\n-- congrArg"
DEBT = (
    "abbrev Law (_ : Prop) : Prop := True\n"
    "abbrev UnitDimensionCompatible (_ : Prop) : Prop := True\n"
    "def support : Prop := True\n"
    "theorem debt (source_law : True) : UnitDimensionCompatible x x := by trivial\n"
)


def oracle():
    path = ROOT / "tests/mcp/fixtures/drift_pathology_original.py.txt"
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == "2362ac89114297a35b69be7843caa1e1bafdf318400d2873a6e0287348a83653"
    )
    spec = importlib.util.spec_from_loader(
        "_drift_original", SourceFileLoader("_drift_original", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def cwd(root):
    before = Path.cwd()
    os.chdir(root)
    try:
        yield
    finally:
        os.chdir(before)


def cli(module, root, argv, process_argv=()):
    before = sys.argv
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        sys.argv = ["monitor.py", *process_argv]
        with cwd(root), redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = module.main(argv)
            except SystemExit as error:
                code = error.code
    finally:
        sys.argv = before
    return {"exit_code": code, "stdout": stdout.getvalue()}, stderr.getvalue()


def material(**updates):
    result = dict(
        source_text="",
        lean_text="",
        type_packet={},
        assumption_packet={},
        unit_report={},
        semantics_report={},
        assumption_report={},
        dimension_report={},
        lean_path=None,
    )
    result.update(updates)
    return result


def assets(document):
    def asset(path, content):
        return {
            "path": path,
            "content": content,
            "encoding": "text",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]


class DriftTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="drift-fixture-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.context = dict(
            working_directory=str(self.root),
            program_name="monitor.py",
            process_argv=[],
            allow_mutating=True,
        )
        self.oracle = oracle()

    def test_native_rule_matrix_and_scan_boundaries(self):
        # Independent rule combinations, both sides of each suppressing guard,
        # recursive support labels, prior-code deduplication and all statuses.
        codes = set()
        statuses = set()
        for source in ["", "quantum ket", "vector", "integral", "Newton", ALL]:
            for lean in [
                "",
                SCALAR,
                "Real Real Real",
                "Hilbert LinearMap Vector Quantity deriv Law",
                DEBT,
                "Differentiable hpos congrArg",
            ]:
                for packets in [
                    {},
                    dict(
                        type_packet={"surface": "Quantity"},
                        unit_report={"status": "pass"},
                        assumption_packet={"nested": [{"provenance": "source-backed"}]},
                    ),
                    dict(
                        unit_report={"status": None},
                        semantics_report={
                            "findings": [
                                {"code": "vector_structure_erased"},
                                {"code": "physical_quantities_erased"},
                                {"code": "missing_assumption_packet"},
                                None,
                            ]
                        },
                        assumption_report={
                            "findings": [{"code": "hidden_strengthening"}]
                        },
                        dimension_report={
                            "findings": [
                                {"code": "raw_scalar_erasure"},
                                {"code": "raw_scalar_erasure"},
                            ]
                        },
                    ),
                ]:
                    data = material(source_text=source, lean_text=lean, **packets)
                    actual = native.build_report(**data)
                    self.assertEqual(actual, self.oracle.build_report(**data))
                    # Byte equality also protects insertion-ordered cue lists.
                    self.assertEqual(
                        json.dumps(actual, ensure_ascii=False),
                        json.dumps(
                            self.oracle.build_report(**data), ensure_ascii=False
                        ),
                    )
                    analysis = native.inspect_pack(**data)
                    self.assertEqual(analysis["findings"], [])
                    findings = native.apply_rules(analysis)
                    self.assertEqual(analysis["findings"], [])
                    self.assertEqual(native.summarize(analysis, findings), actual)
                    codes.update(f["code"] for f in findings)
                    statuses.add(actual["status"])
        self.assertEqual(statuses, {"pass", "warn", "fail"})
        self.assertEqual(
            codes,
            {
                "quantum_notation_collapsed",
                "vector_field_notation_collapsed",
                "dense_physics_collapsed_to_scalars",
                "unit_dimension_guard_confirms_collapse",
                "calculus_or_integral_abstracted_away",
                "physical_law_absorbed_into_hypotheses",
                "proof_reduced_to_target_shaped_substitution",
                "alternate_calculus_strategy",
                "implicit_premises_unlabeled",
                "implicit_premises_failed_assumption_critic",
            },
        )
        for path in [None, "formalphysics_fixture/Example.lean", "Other.lean"]:
            data = material(lean_text=DEBT, lean_path=path)
            report = native.build_report(**data)
            self.assertEqual(report, self.oracle.build_report(**data))
            self.assertEqual(report["status"], "pass")  # independent debt status
            self.assertFalse(report["grounding_debt_report"]["ok"])
            debt_codes = {
                f["code"] for f in report["grounding_debt_report"]["findings"]
            }
            self.assertIn("prop_true_support_definition", debt_codes)
            self.assertEqual("local_law_shim_true" in debt_codes, path != "Other.lean")
        lines = ["def anchor : Nat := 0"] + ["-- gap"] * 8
        self.assertEqual(native.declaration_near(lines, 7), "anchor")
        self.assertIsNone(native.declaration_near(lines, 8))
        # No invented input-size or finding-count cap.
        report = native.build_report(
            **material(lean_text="def support : Prop := True\n" * 1031)
        )
        self.assertEqual(report["grounding_debt_report"]["finding_count"], 1031)
        self.assertEqual(
            native.run_self_test(),
            json.loads(cli(self.oracle, self.root, ["--self-test"])[0]["stdout"]),
        )

    def test_cli_compatibility_and_native_failures(self):
        (self.root / "source.txt").write_text(ALL)
        (self.root / "lean.lean").write_text(SCALAR)
        (self.root / "packet.json").write_text(
            '{"assumptions":[{"status":"generated-support"}]}'
        )
        for argv in [
            [],
            ["--help"],
            ["--bad"],
            ["--source-text"],
            ["--self-test", "--source-file", "missing"],
            [
                "--source-file",
                "source.txt",
                "--lean-file",
                "lean.lean",
                "--assumption-packet",
                "packet.json",
            ],
            [
                "--source-text",
                "",
                "--source-file",
                "missing",
                "--lean-text",
                "",
                "--lean-file",
                "missing",
            ],
            ["--self-test", "--output", "out/report.json"],
        ]:
            self.assertEqual(
                cli(native, self.root, argv), cli(self.oracle, self.root, argv)
            )
        for module in [native, self.oracle]:
            for payload, exception in [
                (b"{", json.JSONDecodeError),
                (b"\xff", UnicodeDecodeError),
                (b"[1]", AttributeError),
                (b'{"findings":null}', TypeError),
            ]:
                (self.root / "bad.json").write_bytes(payload)
                with self.assertRaises(exception):
                    cli(module, self.root, ["--physical-semantics-report", "bad.json"])
            with self.assertRaises(FileNotFoundError):
                cli(module, self.root, ["--source-file", "missing"])
            (self.root / "blocked").write_text("file")
            with self.assertRaises(FileExistsError):
                cli(module, self.root, ["--output", "blocked/report.json"])
        self.assertEqual(
            cli(native, self.root, None, ["--self-test"]),
            cli(self.oracle, self.root, None, ["--self-test"]),
        )

    def test_registered_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_physics_lean_drift_pathology_monitor_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 6},
        )
        self.assertEqual(
            document,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/drift-pathology-monitor.workflow.json"
                ).read_text()
            ),
        )
        self.assertIn(
            "skills/physics-lean/physics-lean-drift-pathology-monitor/scripts/monitor_physics_lean_drift_pathologies.py",
            [s["path"] for s in document["provenance"]["sources"]],
        )
        for source in document["provenance"]["sources"]:
            self.assertEqual(
                source["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        config = StdioConfig(
            command=sys.executable,
            args=[str(Path(__file__).resolve()), "--server", str(self.root)],
            cwd=str(ROOT),
        )
        async with manager.open(
            "drift-monitor", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
        ) as remote:
            try:
                await self.remote_scenario(document, remote)
            except Exception:
                import traceback

                traceback.print_exc()
                raise
        self.assertFalse(manager.active)
        config.args.append("--readonly")
        async with manager.open(
            "drift-readonly", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
        ) as remote:
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "emit",
                    dict(
                        options={"output": "readonly/report.json"},
                        report={},
                        report_json="{}",
                        context=self.context,
                    ),
                )
        self.assertFalse((self.root / "readonly").exists())

    async def remote_scenario(self, document, remote):
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(doc, inventory=tools):
            snapshot = assets(doc)
            return (
                compile_workflow(
                    "mcp:drift-monitor",
                    workflow_documents([DESCRIPTOR], snapshot)[0],
                    inventory,
                ),
                snapshot,
            )

        compiled, snapshot = compile(document)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertTrue(compiled["prism_source"])
        self.assertTrue(compiled["runtime_source"])
        self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
        for op in document["operations"].values():
            target = op["execution"]["binding"]["target"]
            self.assertFalse(
                compile(document, [t for t in tools if t["name"] != target])[0][
                    "runnable"
                ]
            )

        async def authorize():
            pass

        async def run(argv=(), doc=document, context=None):
            c, a = (compiled, snapshot) if doc is document else compile(doc)
            self.assertTrue(c["runnable"], c["diagnostics"])
            return await execute(
                c,
                a,
                {
                    "argv": None if argv is None else list(argv),
                    "context": context or self.context,
                },
                remote,
                authorize,
            )

        (self.root / "source.txt").write_text(ALL)
        (self.root / "formalphysics_fixture.lean").write_text(SCALAR + "\n" + DEBT)
        packet_files = {
            "type-packet": {"z": "raw", "a": "scalar"},
            "assumption-packet": {"nested": [{"provenance": "generated-support"}]},
            "unit-report": {"status": "fail"},
            "physical-semantics-report": {
                "findings": [
                    {"code": "physical_quantities_erased"},
                    {"code": "missing_assumption_packet"},
                ]
            },
            "assumption-critic-report": {
                "findings": [{"code": "hidden_strengthening"}]
            },
            "dimension-critic-report": {"findings": [{"code": "raw_scalar_erasure"}]},
        }
        packets = []
        for name, value in packet_files.items():
            (self.root / (name + ".json")).write_text(json.dumps(value))
            packets += ["--" + name, name + ".json"]
        cases = [
            [],
            ["--self-test", "--source-file", "missing", "--type-packet", "missing"],
            [
                "--source-file",
                "source.txt",
                "--lean-file",
                "formalphysics_fixture.lean",
                *packets,
            ],
            [
                "--source-text",
                "",
                "--source-file",
                "missing",
                "--lean-text",
                "",
                "--lean-file",
                "missing",
            ],
            ["--source-text", "Newton"],
            ["--lean-text", DEBT],
            ["--help"],
            ["--source-text", "integral", "--lean-text", "congrArg deriv eq"],
            ["--source-text", "quantum ket", "--lean-text", "Real Real Real"],
            ["--source-text", "vector", "--lean-text", "Vector"],
            ["--source-text", "x" * 25000 + " ket"],
        ]
        for argv in cases:
            for write in [False] if "--help" in argv else [False, True]:
                args = argv + (["--output", "out/report.json"] if write else [])
                expected, _ = cli(self.oracle, self.root, args)
                written = (
                    (self.root / "out/report.json").read_bytes() if write else None
                )
                report = (
                    None
                    if "--help" in argv
                    else json.loads(written or expected["stdout"])
                )
                if write:
                    (self.root / "out/report.json").write_text("stale")
                result = await run(args)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"], dict(report=report, **expected))
                steps = (
                    ["parse", "help"]
                    if "--help" in argv
                    else (
                        ["parse", "self_test", "emit"]
                        if "--self-test" in argv
                        else [
                            "parse",
                            "load",
                            "inspect_pack",
                            "apply_rules",
                            "summarize",
                            "emit",
                        ]
                    )
                )
                self.assertEqual(
                    [c["tool"] for c in result["calls"]], [PREFIX + s for s in steps]
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                if report and report["status"] == "fail":
                    self.assertEqual(result["outputs"]["exit_code"], 0)
                if write:
                    self.assertEqual(
                        (self.root / "out/report.json").read_bytes(), written
                    )
        context = dict(self.context, process_argv=["--self-test"])
        result = await run(None, context=context)
        self.assertEqual(result["outputs"]["report"], native.run_self_test())
        self.assertEqual(len(result["calls"]), 3)
        # Null argv consumes caller's process arguments; explicit [] overrides.
        self.assertEqual(
            (await run([], context=context))["outputs"]["report"]["status"], "pass"
        )

        # Test actual registered state ports and accumulation ordering.
        data = material(
            source_text=ALL,
            lean_text=SCALAR,
            semantics_report=packet_files["physical-semantics-report"],
            dimension_report=packet_files["dimension-critic-report"],
        )
        analysis = await remote.call(
            PREFIX + "inspect_pack", dict(material=data, material_json=json.dumps(data))
        )
        self.assertEqual(analysis["analysis"], native.inspect_pack(**data))
        self.assertEqual(analysis["analysis"]["findings"], [])
        findings = await remote.call(PREFIX + "apply_rules", analysis)
        expected = self.oracle.build_report(**data)
        self.assertEqual(findings["findings"], expected["findings"])
        self.assertEqual(
            [f["code"] for f in findings["findings"]][:4],
            [
                "quantum_notation_collapsed",
                "vector_field_notation_collapsed",
                "dense_physics_collapsed_to_scalars",
                "unit_dimension_guard_confirms_collapse",
            ],
        )
        summarized = await remote.call(
            PREFIX + "summarize", dict(**analysis, **findings)
        )
        self.assertEqual(summarized["report"], expected)
        with self.assertRaises(MCPConnectionError):
            await remote.call(
                PREFIX + "inspect_pack", dict(material=data, material_json="{}")
            )
        result = await run(["--lean-text", "def support : Prop := True\n" * 1031])
        self.assertEqual(result["status"], "accepted", result)
        self.assertEqual(
            result["outputs"]["report"]["grounding_debt_report"]["finding_count"], 1031
        )
        self.assertEqual(result["outputs"]["report"]["status"], "pass")

        for argv, count in [
            (["--bad"], 1),
            (["--source-text"], 1),
            (["--source-file", "missing"], 2),
        ]:
            result = await run(argv)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), count)
            self.assertIsNone(result["outputs"])
        for payload, count in [
            (b"{", 2),
            (b"\xff", 2),
            (b"[1]", 3),
            (b'{"findings":null}', 3),
        ]:
            (self.root / "bad.json").write_bytes(payload)
            result = await run(
                [
                    "--physical-semantics-report",
                    "bad.json",
                    "--output",
                    "never/report.json",
                ]
            )
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), count)
            self.assertEqual(result["calls"][-1]["status"], "rejected")
            self.assertFalse((self.root / "never").exists())
        denied = dict(self.context, allow_mutating=False)
        self.assertEqual((await run(context=denied))["status"], "accepted")
        (self.root / "blocked").write_text("file")
        for path, context in [
            ("denied/report.json", denied),
            ("blocked/report.json", self.context),
            (str(self.root.parent / "outside-drift.json"), self.context),
        ]:
            result = await run(["--output", path], context=context)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(len(result["calls"]), 6)
            self.assertEqual(result["calls"][-1]["tool"], PREFIX + "emit")
        self.assertFalse((self.root / "denied").exists())
        bounded = deepcopy(document)
        bounded["policy"]["limits"]["max_operation_calls"] = 3
        result = await run(["--output", "budget/report.json"], doc=bounded)
        self.assertEqual(result["status"], "failed", result)
        self.assertEqual(
            sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 3
        )
        self.assertIn("budget", str(result).lower())
        self.assertFalse((self.root / "budget").exists())
        timed = deepcopy(document)
        timed["policy"]["limits"]["wall_time_seconds"] = 1
        c, a = compile(timed)

        async def pending_authorization():
            await asyncio.Event().wait()

        with self.assertRaises(TimeoutError):
            await execute(
                c,
                a,
                {"argv": [], "context": self.context},
                remote,
                pending_authorization,
            )


if __name__ == "__main__":
    if "--server" in sys.argv:
        import mcp_server

        mcp_server._ALLOWED_WRITE_ROOTS = [
            Path(sys.argv[sys.argv.index("--server") + 1]).resolve()
        ]
        mcp_server._READONLY = "--readonly" in sys.argv
        mcp_server.mcp.run(transport="stdio")
    else:
        unittest.main(verbosity=2)
