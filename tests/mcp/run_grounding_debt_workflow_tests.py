#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402
"""Real native monitor, MCP registration, PRISM compiler and Lunar executor.

There is no external model/provider or theorem compiler in this workflow.
Deterministic Lean text fixtures exercise its static monitor without compilation.
No production workflows, credentials, or proof artifacts are used.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != python.parent.parent.resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
import yaml
from grounding_debt_mount import mount, case, CASE_TEXT, MONITOR
from grounding_debt_tools import source
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, digest

ROUTE_TEST = "--route" in sys.argv
if ROUTE_TEST:
    sys.argv.remove("--route")
IDENTITY = (
    "route_validate_physics_lean_formal_science_grounding_debt_workflow"
    if ROUTE_TEST
    else "hub_physics_lean_formal_science_grounding_debt_workflow"
)
CATEGORY = "route" if ROUTE_TEST else "hub"
DESCRIPTOR = f"skills/control/workflow-contract-validator/references/normalized-workflows/{CATEGORY}/{IDENTITY}/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references"
    / (
        "grounding-debt-route.workflow.json"
        if ROUTE_TEST
        else "grounding-debt.workflow.json"
    )
)
PREFIX = "mathformer_grounding_debt_"
ORDER = [
    "monitor_synthetic",
    "monitor_case",
    "monitor_case",
    "construct_checks",
    "aggregate",
    "write_report",
    "emit_return",
]
CHECKS = [
    "trivial_support_debt_blocks",
    "formalphysics_0191_no_true_law_debt",
    "formalphysics_0059_no_true_law_debt",
    "formalphysics_0191_uses_hilbert_foundation_support",
    "formalphysics_0059_exposes_variational_derivative_integral_packet",
]

# Observe subprocess arguments without substituting any source function.
PROCESS_EVENTS = []


def observe(event, args):
    if event == "subprocess.Popen":
        PROCESS_EVENTS.append((args[1], args[2]))


sys.addaudithook(observe)


def oracle(root):
    path = ROOT / "tests/mcp/fixtures/grounding_debt_original.py.txt"
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == "843d9612c736be07d1ce437a06678037591e7f11c63e866c9c5ac4a70c6e0c28"
    )
    spec = importlib.util.spec_from_loader(
        "_grounding_original", SourceFileLoader("_grounding_original", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Mount file context only; every original function and subprocess is intact.
    module.REPO_ROOT = root
    module.ARTIFACT_ROOT = root / "artifacts/physics_lean/formal_science_grounding_debt"
    module.CASE_0191 = case(root, "0191")
    module.CASE_0059 = case(root, "0059")
    return module


def cli(module, argv, **kwargs):
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = module.main(argv, **kwargs)
        except SystemExit as error:
            code = error.code
    return code, stdout.getvalue(), stderr.getvalue()


def assets(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]


class GroundingDebtTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="grounding-debt-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        mount(self.root)
        self.context = {"repository_root": str(self.root), "allow_mutating": True}
        self.native = source()
        self.output = self.native.report_path(self.root)
        self.original = oracle(self.root)

    def assert_calls(self, events):
        self.assertEqual(len(events), 3)
        commands = [e[0] for e in events]
        self.assertTrue(all(c[:2] == [sys.executable, MONITOR] for c in commands))
        self.assertTrue(all(Path(e[1]) == self.root for e in events))
        self.assertEqual(
            [c[c.index("--lean-file") + 1] for c in commands],
            [
                "libraries/MathformerPhysicsLib/Lean/formalphysics_9999/MathformerPhysics.lean",
                "MathformerPhysicsLib/Lean/formalphysics_0191/MathformerPhysics.lean",
                "MathformerPhysicsLib/Lean/formalphysics_0059/MathformerPhysics.lean",
            ],
        )
        self.assertEqual(
            [c[2:4] for c in commands],
            [
                [
                    "--source-text",
                    "A Hamiltonian source law and Hilbert-space state imply the result.",
                ],
                [
                    "--source-text",
                    "TDSE product differentiation uses Hilbert states, Hamiltonians, adjoint bra law, ket law, and parameter derivatives.",
                ],
                [
                    "--source-text",
                    "Calculus of variations uses fixed endpoints, differentiation under the integral, and chain-rule integral substitution.",
                ],
            ],
        )
        self.assertEqual(
            commands[0][commands[0].index("--lean-text") + 1],
            "abbrev Law (_ : Prop) : Prop := True\nabbrev UnitDimensionCompatible (_ : Prop) : Prop := True\n"
            "theorem bad (source_law : True) (psi H : Real) (unit_dimension_bridge : UnitDimensionCompatible True) : True := by trivial\n",
        )

    def compare(self, json_mode, expected_ok):
        argv = ["--json"] if json_mode else []
        start = len(PROCESS_EVENTS)
        expected = cli(self.original, argv)
        expected_calls = PROCESS_EVENTS[start:]
        expected_bytes = self.output.read_bytes()
        self.output.unlink()
        start = len(PROCESS_EVENTS)
        actual = cli(self.native, argv, repository_root=self.root)
        self.assertEqual(actual, expected)
        self.assertEqual(PROCESS_EVENTS[start:], expected_calls)
        self.assert_calls(expected_calls)
        self.assertEqual(self.output.read_bytes(), expected_bytes)
        payload = json.loads(expected_bytes)
        self.assertEqual([c["id"] for c in payload["checks"]], CHECKS)
        self.assertEqual(payload["ok"], expected_ok)
        self.assertEqual(actual[0], 0 if expected_ok else 1)
        self.assertTrue(expected_bytes.endswith(b"\n"))
        if json_mode:
            self.assertEqual(json.loads(actual[1]), payload)
        else:
            self.assertEqual(
                actual[1],
                ("PASS" if expected_ok else "FAIL")
                + " formal science grounding debt gate\n",
            )
        return payload

    def test_original_equivalence_and_all_check_branches(self):
        self.compare(False, True)
        self.compare(True, True)
        # An unselected grounding finding must survive without failing the gate.
        path = case(self.root, "0191")
        path.write_text(CASE_TEXT["0191"] + "def arbitrarySupport : Prop := True\n")
        payload = self.compare(True, True)
        self.assertIn(
            "prop_true_support_definition", payload["checks"][1]["detail"]["codes"]
        )
        # Failure of one check does not stop subsequent checks or report/print.
        for case_id in ["0191", "0059"]:
            path = case(self.root, case_id)
            for debt in [
                "theorem bad (source_law : True) : True := by trivial\n",
                "abbrev Law (_ : Prop) : Prop := True\n",
            ]:
                path.write_text(CASE_TEXT[case_id] + debt)
                payload = self.compare(False, False)
                self.assertFalse(payload["checks"][1 if case_id == "0191" else 2]["ok"])
                self.assertTrue(payload["checks"][4]["ok"])
            path.write_text(CASE_TEXT[case_id])
        for case_id, text in CASE_TEXT.items():
            for line in text.splitlines():
                case(self.root, case_id).write_text(text.replace(line, ""))
                payload = self.compare(True, False)
                self.assertFalse(payload["checks"][3 if case_id == "0191" else 4]["ok"])
            case(self.root, case_id).write_text(text)
        bad = self.native.monitor_synthetic(repository_root=self.root)
        self.assertEqual(
            self.native.debt_codes(bad),
            {
                "prop_true_support_definition",
                "local_law_shim_true",
                "source_law_typed_true",
                "local_unit_dimension_shim",
            },
        )
        good = self.native.monitor_named_case("0059", repository_root=self.root)
        checks = self.native.construct_checks({}, good, good, repository_root=self.root)
        self.assertEqual([c["ok"] for c in checks], [False, True, True, True, True])
        report = self.native.aggregate(checks)
        self.assertIs(report["checks"], checks)
        self.assertFalse(report["ok"])

    def test_native_exceptions_and_cli(self):
        for argv in [["--unknown"], ["--json", "extra"]]:
            start = len(PROCESS_EVENTS)
            self.assertEqual(cli(self.native, argv)[0], cli(self.original, argv)[0])
            self.assertEqual(len(PROCESS_EVENTS), start)
        for module in [self.native, self.original]:
            with self.assertRaisesRegex(RuntimeError, "diagnostic"):
                module.run_json(
                    [
                        "-c",
                        'import sys; print("diagnostic", file=sys.stderr); sys.exit(7)',
                    ]
                )
            with self.assertRaises(json.JSONDecodeError):
                module.run_json(["-c", 'print("invalid JSON")'])
        # Real native monitor failure is not retried or converted into findings.
        case(self.root, "0191").unlink()
        for module, kwargs in [
            (self.original, {}),
            (self.native, {"repository_root": self.root}),
        ]:
            start = len(PROCESS_EVENTS)
            with self.assertRaisesRegex(RuntimeError, "command failed"):
                cli(module, [], **kwargs)
            self.assertEqual(len(PROCESS_EVENTS) - start, 2)
            self.assertFalse(self.output.exists())
        case(self.root, "0191").write_bytes(b"\xff")
        with self.assertRaises(UnicodeDecodeError):
            self.native.construct_checks({}, {}, {}, repository_root=self.root)
        with self.assertRaises(KeyError):
            self.native.monitor_named_case("9999", repository_root=self.root)

    def test_authored_generator_and_control_registration(self):
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("_grounding_normalizer", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        document = json.loads(AUTHORED.read_text())
        if ROUTE_TEST:
            self.assertEqual(module.grounding_debt_route_descriptor(), document)
            files, catalog = module.render_descriptors([document])
            self.assertEqual(
                yaml.safe_load(files[Path(CATEGORY) / IDENTITY / "workflow.yaml"]),
                document,
            )
            self.assertEqual(catalog["workflows"][0]["id"], IDENTITY)
            routes = {r.route_id: r for r in module.hub.build_intent_routes()}
            route = routes["validate.physics.lean.formal_science_grounding_debt"]
            self.assertEqual(
                route.action_ids, ("physics-lean:formal-science-grounding-debt",)
            )
            action = module.hub.build_registry()[route.action_ids[0]]
            self.assertEqual(
                action.command,
                (
                    "{python}",
                    "tests/physics_lean/run_formal_science_grounding_debt_gate.py",
                    "--json",
                ),
            )
            self.assertIsNone(action.timeout_seconds)
        else:
            matches = [row for row in module.inventory() if row["id"] == document["id"]]
            self.assertEqual(matches, [document])
        report = module.hub.audit_control(module.hub.build_registry())
        for name in [
            "scripts/grounding_debt_tools.py",
            "tests/mcp/run_grounding_debt_workflow_tests.py",
        ]:
            self.assertNotIn(name, report["uncontrolled_entrypoints"])

    def test_registered_mcp_and_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document, json.loads(AUTHORED.read_text()))
        self.assertEqual(document["id"], IDENTITY)
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 7},
        )
        self.assertIn(
            "tests/physics_lean/run_formal_science_grounding_debt_gate.py",
            [s["path"] for s in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        config = StdioConfig(
            command=sys.executable,
            args=[str(Path(__file__).resolve()), "--server", str(self.root)],
            cwd=str(ROOT),
        )
        failure = None
        async with manager.open(
            "grounding-debt", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
        ) as remote:
            try:
                await self.remote_scenario(document, remote)
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure
        config.args.append("--readonly")
        async with manager.open(
            "grounding-readonly", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
        ) as remote:
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "write_report",
                    {"report": {"ok": True}, "context": self.context},
                )

    async def remote_scenario(self, document, remote):
        tools = [
            t.model_dump(by_alias=True, exclude_none=True) for t in await remote.tools()
        ]

        def compile(doc, inventory=tools):
            snapshot = assets(doc)
            compiled = compile_workflow(
                "mcp:grounding-debt",
                workflow_documents([DESCRIPTOR], snapshot)[0],
                inventory,
            )
            return compiled, snapshot

        compiled, snapshot = compile(document)
        self.assertTrue(compiled["runnable"], compiled["diagnostics"])
        self.assertEqual(compiled["runtime_status"], "ready")
        self.assertTrue(compiled["prism_source"])
        self.assertTrue(compiled["runtime_source"])
        self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
        for op in document["operations"].values():
            name = op["execution"]["binding"]["target"]
            interface = next(t for t in tools if t["name"] == name)
            self.assertEqual(
                set(interface["inputSchema"].get("required", [])), set(op["inputs"])
            )
            self.assertEqual(
                set(interface["inputSchema"]["properties"]), set(op["inputs"])
            )
            self.assertEqual(
                set(interface["outputSchema"]["properties"]), set(op["outputs"])
            )
            self.assertEqual(
                set(interface["outputSchema"]["required"]), set(op["outputs"])
            )
            self.assertFalse(
                compile(document, [t for t in tools if t["name"] != name])[0][
                    "runnable"
                ]
            )

        async def authorize():
            pass

        async def run(json_mode=False, doc=document, context=None):
            c, a = (compiled, snapshot) if doc is document else compile(doc)
            self.assertTrue(c["runnable"], c["diagnostics"])
            return await execute(
                c,
                a,
                {"json_output": json_mode, "context": context or self.context},
                remote,
                authorize,
            )

        async def completed(json_mode, ok):
            result = await run(json_mode)
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(
                [c["tool"] for c in result["calls"]], [PREFIX + s for s in ORDER]
            )
            payload = result["outputs"]["report"]
            self.assertEqual(payload["ok"], ok)
            self.assertEqual(len(payload["checks"]), 5)
            written_bytes = self.output.read_bytes()
            self.assertEqual(json.loads(written_bytes), payload)
            self.assertEqual(
                [c["input_digest"] for c in result["calls"][:3]],
                [
                    digest({"context": self.context}),
                    digest({"case_id": "0191", "context": self.context}),
                    digest({"case_id": "0059", "context": self.context}),
                ],
            )
            expected = cli(self.original, ["--json"] if json_mode else [])
            self.assertEqual(written_bytes, self.output.read_bytes())
            self.assertEqual(result["outputs"]["exit_code"], expected[0])
            self.assertEqual(result["outputs"]["stdout"], expected[1])
            self.assertEqual(json.loads(self.output.read_text()), payload)
            self.assertTrue(result["runtime"]["effect_records"])
            self.assertTrue(result["runtime"]["provenance"])
            self.assertTrue(result["replay_artifacts"])
            return result

        await completed(False, True)
        await completed(True, True)
        case(self.root, "0191").write_text(
            CASE_TEXT["0191"] + "theorem bad (source_law : True) : True := by trivial\n"
        )
        result = await completed(False, False)
        self.assertFalse(result["outputs"]["report"]["checks"][1]["ok"])
        self.assertTrue(result["outputs"]["report"]["checks"][4]["ok"])
        case(self.root, "0191").write_text(CASE_TEXT["0191"])
        case(self.root, "0059").write_text(
            CASE_TEXT["0059"] + "def support : Prop := True\n"
        )
        await completed(True, True)
        case(self.root, "0059").write_text(CASE_TEXT["0059"])
        self.output.unlink()
        # Real subprocess failures stop at each monitor boundary without retries.
        for path, count in [
            (self.root / MONITOR, 1),
            (case(self.root, "0191"), 2),
            (case(self.root, "0059"), 3),
        ]:
            saved = path.read_bytes()
            path.unlink()
            try:
                result = await run()
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [PREFIX + s for s in ORDER[:count]],
                )
                self.assertIsNone(result["outputs"])
                self.assertFalse(self.output.exists())
                start = len(PROCESS_EVENTS)
                with self.assertRaisesRegex(RuntimeError, "command failed"):
                    cli(self.original, [])
                self.assertEqual(len(PROCESS_EVENTS) - start, count)
            finally:
                path.write_bytes(saved)
        # Context prevents accidental writes. Failure occurs at write, before emit.
        result = await run(context={**self.context, "allow_mutating": False})
        self.assertEqual(result["status"], "failed", result)
        self.assertEqual(len(result["calls"]), 6)
        self.assertFalse(self.output.exists())
        # Native write error is propagated after three monitors and all checks.
        self.output.parent.rmdir()
        self.output.parent.write_text("file")
        result = await run()
        self.assertEqual(result["status"], "failed", result)
        self.assertEqual(len(result["calls"]), 6)
        self.assertIsNone(result["outputs"])
        self.output.parent.unlink()
        # A fixed sequence has no loop exhaustion; operation budget exhaustion
        # stops before the next transport call. Completed writes survive.
        for limit in [1, 3, 5, 6]:
            bounded = deepcopy(document)
            bounded["policy"]["limits"]["max_operation_calls"] = limit
            result = await run(doc=bounded)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]),
                limit,
            )
            self.assertEqual(result["calls"][-1]["status"], "rejected")
            self.assertEqual(self.output.exists(), limit == 6)
            if limit == 6:
                self.assertTrue(json.loads(self.output.read_text())["ok"])
                self.output.unlink()
        timed = deepcopy(document)
        timed["policy"]["limits"]["wall_time_seconds"] = 1
        c, a = compile(timed)
        self.assertTrue(c["runnable"], c["diagnostics"])

        async def waiting_authority():
            await asyncio.Event().wait()

        with self.assertRaises(TimeoutError):
            await execute(
                c,
                a,
                {"json_output": False, "context": self.context},
                remote,
                waiting_authority,
            )
        self.assertFalse(self.output.exists())
        # Direct registered-tool failure paths cannot bypass native restrictions.
        for name, args in [
            ("monitor_case", {"case_id": "9999", "context": self.context}),
            (
                "monitor_synthetic",
                {"context": {**self.context, "repository_root": "relative"}},
            ),
            (
                "write_report",
                {
                    "report": {"ok": True},
                    "context": {
                        **self.context,
                        "repository_root": str(self.root.parent),
                    },
                },
            ),
        ]:
            with self.assertRaises(MCPConnectionError):
                await remote.call(PREFIX + name, args)
        # File changes between monitor and checks remain visible; no hidden snapshot.
        bad = (
            await remote.call(PREFIX + "monitor_synthetic", {"context": self.context})
        )["report"]
        good = (
            await remote.call(
                PREFIX + "monitor_case", {"case_id": "0059", "context": self.context}
            )
        )["report"]
        case(self.root, "0191").unlink()
        with self.assertRaises(MCPConnectionError):
            await remote.call(
                PREFIX + "construct_checks",
                {
                    "bad": bad,
                    "case_0191": good,
                    "case_0059": good,
                    "context": self.context,
                },
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
        program = unittest.main(verbosity=2, exit=False)
        result = program.result
        raise SystemExit(
            0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
        )
