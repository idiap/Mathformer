# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Actual native CLI checks, MCP bindings, Lunar PRISM compilation/runtime."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT / "tests/mcp/fixtures"),
    *SITES,
]
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import subprocess
import tempfile
import types
import unittest
import yaml
from lean_consistency_workflow_tools import (
    source_report,
    native_arguments,
    register_lean_consistency_tools,
)
from lean_consistency_boundary import install
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/loop/loop_lean_consistency_testing_loop_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/lean-consistency.workflow.json"
)
CORE = [
    "informalization_extractor",
    "declaration_shape",
    "informal_proof_internal_consistency",
    "reverse_informal_consistency",
    "nonvacuity",
    "cross_file_concepts",
]
GOOD = r"""import Mathlib.Data.Nat.Basic

/--
Original source (NL): Adding zero preserves a natural number.
Original source (LaTeX): `n + 0 = n` for every natural number n.
Mathlib grounding: Nat.add_zero.
-/
theorem add_zero_identity (n : Nat) : n + 0 = n := by
  exact Nat.add_zero n
"""


def oracle(root):
    module = types.ModuleType("lean_consistency_original")
    module.__file__ = str(
        ROOT
        / "skills/lean/lean-consistency-report-orchestrator/scripts/run_lean_consistency_report.py"
    )
    exec(
        compile(
            (ROOT / "tests/mcp/fixtures/lean_consistency_original.py.txt").read_text(),
            module.__file__,
            "exec",
        ),
        module.__dict__,
    )
    install(module, root)
    return module


def stable(value):
    if isinstance(value, list):
        return [stable(v) for v in value]
    if isinstance(value, dict):
        return {
            k: stable(v)
            for k, v in value.items()
            if k
            not in {"generated_at_utc", "created_at_utc", "duration_ms", "_duration_ms"}
        }
    return value


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


class LeanConsistencyTests(unittest.TestCase):
    def test_shared_stages_match_original_and_cli_failure_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            native = source_report()
            install(native, root)
            original = oracle(root)
            (root / "Good.lean").write_text(GOOD)
            (root / "Bad.lean").write_text(
                "theorem vacuous : True := by\n  trivial\n-- compiler-fail\n"
            )
            for values in [
                dict(lean_file=[]),
                dict(lean_file=[str(root / "Good.lean")]),
                dict(
                    lean_file=[str(root / "Bad.lean"), str(root / "Good.lean")],
                    run_lean_check=True,
                ),
                dict(
                    lean_file=[str(root / "absent.lean")],
                    skip_mathlib_grounding=True,
                    skip_reference_free_monitor=True,
                ),
            ]:
                expected = original.build_report(native_arguments(original, values))
                actual = native.build_report(native_arguments(native, values))
                self.assertEqual(stable(actual), stable(expected))
                self.assertEqual(
                    json.loads(
                        (root / "artifacts/lean_consistency/latest.json").read_text()
                    ),
                    actual,
                )
            with redirect_stdout(io.StringIO()):
                args = [
                    "--lean-file",
                    str(root / "Bad.lean"),
                    "--skip-mathlib-grounding",
                    "--skip-reference-free-monitor",
                ]
                self.assertEqual(native.main(args), 0)
                self.assertEqual(native.main([*args, "--expect-ok"]), 1)
            for marker, exception in [
                ("compiler-timeout", subprocess.TimeoutExpired),
                ("compiler-crash", OSError),
            ]:
                (root / "Crash.lean").write_text(GOOD + "\n-- " + marker)
                output = root / "aborted.json"
                with self.assertRaises(exception):
                    native.build_report(
                        native_arguments(
                            native,
                            dict(
                                lean_file=[str(root / "Crash.lean")],
                                run_lean_check=True,
                                output_file=str(output),
                            ),
                        )
                    )
                self.assertFalse(output.exists())

    def test_service_authority_and_context_guards(self):
        from mcp.server.fastmcp import FastMCP

        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                native = source_report()
                install(native, Path(tmp))
                for authorize, allowed in [
                    (
                        lambda: (_ for _ in ()).throw(PermissionError("readonly")),
                        lambda p: True,
                    ),
                    (lambda: None, lambda p: False),
                ]:
                    server = FastMCP("denied")
                    register_lean_consistency_tools(server, authorize, allowed)
                    with self.assertRaisesRegex(Exception, "readonly|write roots"):
                        await server.call_tool(
                            "mathformer_lean_consistency_initialize", {"args": {}}
                        )
                self.assertFalse(native.ARTIFACT_DIR.exists())

        asyncio.run(run())

    def test_registered_lunar_prism_execution(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document, json.loads(AUTHORED.read_text()))
        self.assertEqual(document["lifecycle"], "active")
        for source in document["provenance"]["sources"]:
            self.assertEqual(
                source["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(),
            )
        spec = importlib.util.spec_from_file_location(
            "consistency_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(
            next(d for d in generator.inventory() if d["id"] == document["id"]),
            document,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "Good.lean").write_text(GOOD)
            (root / "Bad.lean").write_text(
                "theorem vacuous : True := by\n  trivial\n-- compiler-fail\n"
            )
            original = oracle(root)
            bootstrap = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr(
                    [
                        str(ROOT / "scripts"),
                        str(ROOT / "tests/mcp/fixtures"),
                        str(ROOT),
                        *SITES,
                    ]
                )
                + ";from lean_consistency_boundary import serve;serve("
                + repr(str(root))
                + ")"
            )
            manager = SessionManager()
            async with manager.open(
                "lean-consistency",
                StdioConfig(
                    command=sys.executable, args=["-c", bootstrap], cwd=str(ROOT)
                ),
                {},
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile_doc(doc, inventory=None):
                    snapshot = assets(doc)
                    compiled = compile_workflow(
                        "mcp:lean-consistency",
                        workflow_documents([DESCRIPTOR], snapshot)[0],
                        tools if inventory is None else inventory,
                    )
                    return compiled, snapshot

                compiled, snapshot = compile_doc(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile_doc(document, [])[0]["runnable"])

                async def authorize():
                    pass

                scenarios = [
                    dict(),
                    dict(lean_file=[str(root / "Good.lean")]),
                    dict(
                        lean_file=[str(root / "Good.lean")],
                        run_lean_check=True,
                        skip_mathlib_grounding=True,
                        skip_reference_free_monitor=True,
                    ),
                    dict(
                        lean_file=[str(root / "Bad.lean"), str(root / "Good.lean")],
                        run_lean_check=True,
                        target_mathlib_compatibility=92,
                        target_reference_free_score=93,
                    ),
                    dict(
                        lean_file=[str(root / "Good.lean")], skip_mathlib_grounding=True
                    ),
                    dict(
                        lean_file=[str(root / "Good.lean")],
                        skip_reference_free_monitor=True,
                    ),
                    dict(
                        lean_file=[str(root / "absent.lean")],
                        skip_mathlib_grounding=True,
                        skip_reference_free_monitor=True,
                    ),
                ]
                for index, values in enumerate(scenarios):
                    with self.subTest(values=values):
                        values.update(
                            output_file=str(root / "unified.json"),
                            informalization_report=str(root / "extract.json"),
                            reasoning_log_file=str(root / "reasoning.jsonl"),
                        )
                        expected = original.build_report(
                            native_arguments(original, values)
                        )
                        before = {p.name: p.read_bytes() for p in root.glob("*.lean")}
                        (root / "process-calls.jsonl").unlink(missing_ok=True)
                        (root / "reasoning.jsonl").unlink(missing_ok=True)
                        result = await execute(
                            compiled, snapshot, {"args": values}, remote, authorize
                        )
                        self.assertEqual(result["status"], "accepted", result)
                        report = result["outputs"]["report"]
                        self.assertEqual(stable(report), stable(expected))
                        self.assertEqual(report["ok"], not report["blocking_layers"])
                        scores = [
                            s
                            for layer in report["layers"]
                            for s in layer["score_candidates"]
                        ]
                        self.assertEqual(
                            report["summary"]["consistency_score"],
                            (
                                round(sum(scores) / len(scores), 3)
                                if scores
                                else (100.0 if report["ok"] else 0.0)
                            ),
                        )
                        self.assertEqual(
                            report["summary"]["min_layer_score"],
                            (
                                min(scores)
                                if scores
                                else report["summary"]["consistency_score"]
                            ),
                        )
                        if index in {0, 1, 2, 4, 5}:
                            self.assertTrue(report["ok"], report["blocking_layers"])
                        if index == 1:
                            extracted = json.loads((root / "extract.json").read_text())
                            self.assertEqual(
                                extracted["summary"]["declaration_count"], 1
                            )
                            self.assertEqual(
                                extracted["files"][0]["declarations"][0]["name"],
                                "add_zero_identity",
                            )
                        self.assertEqual(
                            json.loads((root / "unified.json").read_text()), report
                        )
                        self.assertEqual(
                            result["outputs"]["report_path"], "unified.json"
                        )
                        self.assertEqual(
                            result["outputs"]["informalization_report_path"],
                            "extract.json",
                        )
                        self.assertEqual(
                            before,
                            {p.name: p.read_bytes() for p in root.glob("*.lean")},
                        )
                        self.assertEqual(
                            len(result["calls"]), 7
                        )  # No retries or refinement loop.
                        ids = [layer["id"] for layer in report["layers"]]
                        self.assertEqual(ids[:1], ["lean_compile"])
                        self.assertEqual([i for i in ids if i in CORE], CORE)
                        self.assertEqual(
                            "mathlib_grounding" in ids,
                            bool(values.get("lean_file"))
                            and not values.get("skip_mathlib_grounding", False),
                        )
                        self.assertEqual(
                            "reference_free_monitor" in ids,
                            bool(values.get("lean_file"))
                            and not values.get("skip_reference_free_monitor", False),
                        )
                        events = [
                            json.loads(s)
                            for s in (root / "reasoning.jsonl").read_text().splitlines()
                        ]
                        self.assertEqual(
                            events[0]["step"], "lean_consistency_report_start"
                        )
                        self.assertEqual(
                            events[-1]["step"], "lean_consistency_report_complete"
                        )
                        layer_events = [
                            e
                            for e in events
                            if e["step"] == "lean_consistency_report_layer_complete"
                        ]
                        self.assertEqual(len(layer_events), len(ids))
                        self.assertEqual(
                            [e["payload"]["id"] for e in layer_events], ids
                        )
                        calls = [
                            json.loads(s)
                            for s in (root / "process-calls.jsonl")
                            .read_text()
                            .splitlines()
                        ]
                        json_calls = [c for c in calls if c["command"][0] != "lake"]
                        expected_timeouts = (
                            [60, 120] if values.get("lean_file") else []
                        ) + [120, 90, 120, 150, 90, 90]
                        if "mathlib_grounding" in ids:
                            expected_timeouts.append(240)
                        if "reference_free_monitor" in ids:
                            expected_timeouts.append(120)
                        self.assertEqual(
                            [c["timeout"] for c in json_calls], expected_timeouts
                        )
                        compile_calls = [c for c in calls if c["command"][0] == "lake"]
                        self.assertEqual(
                            [c["command"][3] for c in compile_calls],
                            (
                                [Path(p).name for p in values.get("lean_file", [])]
                                if values.get("run_lean_check")
                                else []
                            ),
                        )
                        if index == 3:
                            self.assertFalse(report["ok"])
                            self.assertIn("lean_compile", report["blocking_layers"])
                            self.assertEqual(
                                report["layers"][0]["summary"]["failed_file_count"], 1
                            )
                            self.assertEqual(
                                report["layers"][-2]["summary"][
                                    "target_compatibility_score"
                                ],
                                92,
                            )
                            self.assertEqual(
                                report["layers"][-2]["summary"][
                                    "target_reference_free_score"
                                ],
                                93,
                            )
                            self.assertEqual(
                                json_calls[-2]["command"][2:6],
                                [
                                    "--target-compatibility-score",
                                    "92",
                                    "--target-reference-free-score",
                                    "93",
                                ],
                            )
                            self.assertEqual(
                                json_calls[-1]["command"][2:4],
                                ["--min-composite-score", "93"],
                            )
                        if index == 6:
                            self.assertTrue(
                                any(
                                    layer.get("payload_tail", {}).get("parse_error")
                                    for layer in report["layers"]
                                )
                            )
                # The inherited operation budget is exact: exhaustion prevents
                # publication after the six preceding source stages.
                limited = deepcopy(document)
                limited["policy"]["limits"]["max_operation_calls"] = 6
                w, a = compile_doc(limited)
                (root / "bounded.json").unlink(missing_ok=True)
                failed = await execute(
                    w,
                    a,
                    {"args": {"output_file": str(root / "bounded.json")}},
                    remote,
                    authorize,
                )
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIsNone(failed["outputs"])
                self.assertFalse((root / "bounded.json").exists())
                for marker in ["compiler-timeout", "compiler-crash"]:
                    (root / "Crash.lean").write_text(GOOD + "\n-- " + marker)
                    failed = await execute(
                        compiled,
                        snapshot,
                        {
                            "args": dict(
                                lean_file=[str(root / "Crash.lean")],
                                run_lean_check=True,
                                output_file=str(root / "aborted.json"),
                            )
                        },
                        remote,
                        authorize,
                    )
                    self.assertEqual(failed["status"], "failed", failed)
                    self.assertIsNone(failed["outputs"])
                    self.assertEqual(
                        [c["operation"] for c in failed["calls"]],
                        ["initialize", "compile"],
                    )
                    self.assertFalse((root / "aborted.json").exists())
                entered = await remote.call(
                    "mathformer_lean_consistency_initialize", {"args": {}}
                )
                arguments = dict(state=entered["state"], context=entered["context"])
                for tool in ["aggregate", "carry_state"]:
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            "mathformer_lean_consistency_" + tool, arguments
                        )
                tampered = deepcopy(arguments)
                tampered["state"]["args"]["run_lean_check"] = True
                with self.assertRaises(MCPConnectionError):
                    await remote.call("mathformer_lean_consistency_compile", tampered)
                await remote.call("mathformer_lean_consistency_compile", arguments)
                with self.assertRaises(MCPConnectionError):
                    await remote.call("mathformer_lean_consistency_compile", arguments)
            self.assertFalse(manager.active)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    sys.exit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
