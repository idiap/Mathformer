#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real registered tools and Lunar/PRISM with deterministic filesystem fixtures.

There is no provider/model or external theorem compiler in this planning path.
Nothing substitutes the PRISM parser, checker, compiler, or executor. The only
child launched is the source self-test against a temporary repository context.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
import asyncio
from contextlib import redirect_stdout, redirect_stderr, asynccontextmanager
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
import yaml
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute
import generative_critic_tools as adapter

SOURCE = "skills/mathformerphysicslib/mathformerphysicslib-generative-coherence-critic/scripts/build_generative_coherence_critic_plan.py"
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_mathformerphysicslib_generative_coherence_critic_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTEXT = dict(
    dry_run=False,
    json_output=True,
    keep_going=False,
    allow_mutating=False,
    write_report=False,
)


@asynccontextmanager
async def session(manager, config):
    # Preserve assertion details when the MCP client's outer transport wrapper
    # would otherwise replace a consumer exception with a generic session error.
    failure = None
    async with manager.open("generative", config, {}) as remote:
        try:
            yield remote
        except Exception as error:
            failure = error
    if failure is not None:
        raise failure


def load(name, path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


native = load("generative_native", ROOT / SOURCE)
original = load(
    "generative_original", ROOT / "tests/mcp/fixtures/generative_critic_original.py.txt"
)


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    paths = {SCHEMA, *[s["path"] for s in document["provenance"]["sources"]]}
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text()) for p in sorted(paths)
    ]


class GenerativeTests(unittest.TestCase):
    def test_original_cli_and_full_scan_before_slice(self):
        reports = [
            {
                "style": "z",
                "findings": [None, 7]
                + [
                    {"severity": "high", "kind": str(i), "evidence": [i]}
                    for i in range(15)
                ],
            },
            {"style": "a", "findings": [{"severity": "low"}]},
        ]
        plan = native.generative_plan(reports)
        self.assertEqual(plan["probe_count"], 7)
        context = plan["deterministic_context"]
        self.assertEqual(context["digest"]["finding_count"], 16)
        self.assertEqual(context["digest"]["severity_counts"], {"high": 15, "low": 1})
        self.assertEqual(
            [x["kind"] for x in context["findings"]], [str(i) for i in range(12)]
        )
        self.assertTrue(
            plan["blocking_policy"]["may_block_only_with_deterministic_evidence"]
        )
        self.assertTrue(plan["codex_exec_policy"]["enabled"])
        self.assertTrue(
            any(p["id"] == "negative_control_incoherent_repair" for p in plan["probes"])
        )
        self.assertEqual(
            native.generative_plan([])["deterministic_context"]["digest"][
                "finding_count"
            ],
            0,
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = []
            for i, report in enumerate(reports):
                path = root / f"{i}.json"
                path.write_text(json.dumps(report))
                files += ["--report", str(path)]
            for flags in ([], ["--json"], ["--self-test", "--json"]):
                outputs = []
                for module in (original, native):
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        self.assertEqual(
                            module.main(
                                files + flags + ["--output", str(root / "out.json")]
                            ),
                            0,
                        )
                    outputs.append(stream.getvalue())
                    self.assertEqual(json.loads((root / "out.json").read_text()), plan)
                self.assertEqual(*outputs)
                self.assertEqual(json.loads(outputs[0]), plan)
            bad = root / "bad.json"
            bad.write_text("{")
            for module in (original, native):
                with self.assertRaises(json.JSONDecodeError):
                    module.main(["--report", str(bad)])
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    module.main(["--invalid"])
            stages = []
            with redirect_stdout(io.StringIO()):
                native.main(
                    ["--self-test", "--json"],
                    repository_root=root,
                    stage_observer=lambda stage, value: stages.append(
                        (stage, deepcopy(value))
                    ),
                )
            self.assertEqual([x[0] for x in stages], ["reports", "plan"])
            self.assertEqual(len(stages[0][1]), 4)
            self.assertEqual(stages[1][1], native.generative_plan(stages[0][1]))
            # Both CLIs use the same temporary filesystem context. No source
            # operation is replaced to compare the default-report branches.
            common = sys.modules["coherence_common"]
            names = ["REPO_ROOT", "LIB_ROOT", "LEAN_ROOT", "FOUNDATIONS_INDEX"]
            previous = [getattr(common, name) for name in names]
            replacements = [
                root,
                root / "MathformerPhysicsLib",
                root / "MathformerPhysicsLib/Lean",
                root / "MathformerPhysicsLib/Lean/Foundations.lean",
            ]
            try:
                for name, value in zip(names, replacements):
                    setattr(common, name, value)
                for flags in ([], ["--json"], ["--self-test", "--json"]):
                    outputs = []
                    for module in (original, native):
                        stream = io.StringIO()
                        with redirect_stdout(stream):
                            self.assertEqual(module.main(flags), 0)
                        outputs.append(stream.getvalue())
                    self.assertEqual(*outputs)
            finally:
                for name, value in zip(names, previous):
                    setattr(common, name, value)

            # Observer is a real source boundary. A corrupted plan must fail the
            # original assertions before emission, rather than be accepted.
            def corrupt(stage, value):
                if stage == "plan":
                    value["probe_count"] = 0

            stream = io.StringIO()
            with redirect_stdout(stream), self.assertRaises(AssertionError):
                native.main(files + ["--self-test"], stage_observer=corrupt)
            self.assertEqual(stream.getvalue(), "")
        # Scanning past the first twelve is observable even when context is full.
        with self.assertRaises(TypeError):
            native.generative_plan([reports[0], {"findings": None}])

    def test_registered_tools_compile_and_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"],
            "hub_mathformerphysicslib_generative_coherence_critic_workflow",
        )
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(SOURCE, [r["path"] for r in document["provenance"]["sources"]])
        manager = SessionManager()
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            async with session(
                manager,
                StdioConfig(
                    command=str(ROOT / ".venv/bin/python"),
                    args=["-c", server],
                    cwd=str(ROOT),
                ),
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=tools):
                    received = assets(doc)
                    w = compile_workflow(
                        "mcp:generative",
                        workflow_documents([DESCRIPTOR], received)[0],
                        inventory,
                    )
                    return w, received

                w, a = compile(document)
                self.assertTrue(w["runnable"], w["diagnostics"])
                self.assertTrue(w["runtime_source"])
                self.assertEqual(set(w["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def allow():
                    pass

                async def run(
                    context=CONTEXT, extra_args=None, seen=None, doc=document
                ):
                    compiled, received = compile(doc)
                    self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                    return await execute(
                        compiled,
                        received,
                        dict(
                            context=context,
                            repository_root=str(root),
                            extra_args=extra_args or [],
                            seen=seen or [],
                        ),
                        remote,
                        allow,
                    )

                result = await run()
                self.assertEqual(result["status"], "accepted", result)
                payload = result["outputs"]["result"]
                self.assertTrue(payload["ok"], payload)
                self.assertEqual(payload["returncode"], 0)
                expected = native.generative_plan(native.default_reports(True, root))
                self.assertEqual(
                    payload["stdout"],
                    json.dumps(expected, indent=2, sort_keys=True) + "\n",
                )
                self.assertEqual(payload["stderr"], "")
                self.assertTrue(payload["write_audit"]["ok"])
                self.assertEqual(
                    [c["tool"] for c in result["calls"]],
                    [
                        "mathformer_generative_critic_" + n
                        for n in [
                            "prepare",
                            "default_reports",
                            "plan",
                            "complete_child",
                            "finish",
                        ]
                    ],
                )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["replay_artifacts"])
                for options in [
                    dict(context={**CONTEXT, "dry_run": True}),
                    dict(extra_args=["--report", "unreachable"]),
                    dict(seen=[adapter.ACTION]),
                ]:
                    early = await run(**options)
                    self.assertEqual(early["status"], "accepted", early)
                    self.assertEqual(len(early["calls"]), 2)
                    out = early["outputs"]["result"]
                    self.assertNotIn("write_audit", out)
                    self.assertNotIn("stdout", out)
                    self.assertEqual(out["ok"], bool(options.get("context")))
                    if options.get("context"):
                        self.assertEqual(out["status"], "dry_run")
                    if options.get("extra_args"):
                        self.assertTrue(out["preflight_errors"])
                    if options.get("seen"):
                        self.assertEqual(out["status"], "dependency_cycle")
                # Real registered staged tools reveal the same data the child
                # carries. State tampering is rejected; no second child launches.
                boundary = (
                    await remote.call(
                        "mathformer_generative_critic_prepare",
                        dict(
                            context=CONTEXT,
                            repository_root=str(root),
                            extra_args=[],
                            seen=[],
                        ),
                    )
                )["boundary"]
                state = (
                    await remote.call(
                        "mathformer_generative_critic_default_reports",
                        {"boundary": boundary},
                    )
                )["state"]
                self.assertEqual(
                    json.loads(state["reports_json"]),
                    native.default_reports(True, root),
                )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_generative_critic_plan",
                        {"state": {**state, "reports_json": "[]"}},
                    )
                state = (
                    await remote.call(
                        "mathformer_generative_critic_plan", {"state": state}
                    )
                )["state"]
                self.assertEqual(json.loads(state["plan_json"]), expected)
                child = (
                    await remote.call(
                        "mathformer_generative_critic_complete_child", {"state": state}
                    )
                )["child"]
                self.assertEqual(child["returncode"], 0)
                # The real hub audit must reject an undeclared fixture write.
                (root / "undeclared.txt").write_text("fixture mutation")
                audited = (
                    await remote.call(
                        "mathformer_generative_critic_finish",
                        dict(boundary=boundary, child=child),
                    )
                )["result"]
                self.assertFalse(audited["ok"])
                self.assertEqual(audited["status"], "undeclared_writes")
                # A real filesystem error in the child is captured once, carried
                # through all remaining stages, and audited as a failed result.
                common = sys.modules["coherence_common"]
                graph = common.canonicalize(common.self_test_inventory())
                owner = next(c for c in graph["concepts"] if c["owner_module"])
                blocker = root / owner["owner_module"]
                blocker.mkdir(parents=True)
                failed = await run()
                self.assertEqual(failed["status"], "accepted", failed)
                out = failed["outputs"]["result"]
                self.assertFalse(out["ok"])
                self.assertEqual(out["returncode"], 1)
                self.assertEqual(out["stdout"], "")
                self.assertIn("IsADirectoryError", out["stderr"])
                self.assertTrue(out["write_audit"]["ok"], out)
                self.assertEqual(len(failed["calls"]), 5)
                # The five-call authored limit is sufficient; a reduced budget
                # stops before finish and cannot turn a partial run into output.
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 4
                exhausted = await run(doc=bounded)
                self.assertEqual(exhausted["status"], "failed", exhausted)
                self.assertIsNone(exhausted["outputs"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed"))
                        for c in exhausted["calls"]
                    ),
                    4,
                )
                self.assertIn("budget", str(exhausted).lower())
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
