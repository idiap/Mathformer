#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Case 0004 source, registered MCP and real Lunar/PRISM execution fixtures.

Only temporary Python artifact inputs are executed. This workflow has no model,
provider or theorem compiler boundary. Its real design-guard Python CLI and the
PRISM parser, checker, compiler and runtime run without substitution.
WORKFLOW_CONTRACT_PATH selects the candidate or provisionally installed contract.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])

# Rapid same-size fixture rewrites must never reuse timestamp-based .pyc files.
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# Reuse the finite artifact fixtures and pre-extraction entrypoint oracle.
from run_sympy_grounded_sample_workflow_tests import (
    fixture,
    oracle,
    Observed,
    NATIVE,
    SOURCE,
    PREFIX,
    SessionManager,
    StdioConfig,
    MCPConnectionError,
    workflow_documents,
    compile_workflow,
    validate,
    execute,
)
import asyncio
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
import yaml

ID = "hub_physics_sympy_grounded_sample_thoroughness_0004_workflow"
CASE = "formalphysics_0004"
REFERENCES = "skills/control/workflow-contract-validator/references"
AUTHORED = REFERENCES + "/sympy-grounded-sample-0004.workflow.json"
DESCRIPTOR = REFERENCES + "/normalized-workflows/hub/" + ID + "/workflow.yaml"
CONTRACT_PATH = Path(os.environ.get("WORKFLOW_CONTRACT_PATH", ROOT / DESCRIPTOR))
DOCUMENT = yaml.safe_load(CONTRACT_PATH.read_text())


def assets(document):
    texts = {DESCRIPTOR: json.dumps(document)}
    texts.update(
        {
            row["path"]: (ROOT / row["path"]).read_text()
            for row in document["provenance"]["sources"]
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


def inputs(path, log=None):
    return dict(
        case_id=CASE, path=str(path), reasoning_log=None if log is None else str(log)
    )


def normalize_log(text):
    # The native logger owns nondeterministic timing and invocation ids.
    import re

    result = []
    for line in text.splitlines():
        event = json.loads(line)
        for key in (
            "event_index",
            "timestamp_utc",
            "timestamp_unix_ms",
            "monotonic_ns",
            "elapsed_ms_since_log_start",
            "elapsed_ms_since_prev_event",
        ):
            event.pop(key, None)
        result.append(
            re.sub(
                r"skill-([a-z0-9-]+)-[0-9a-f]{12}",
                r"skill-\1-<invocation>",
                json.dumps(event, sort_keys=True),
            )
        )
    return result


class Grounded0004Tests(unittest.TestCase):
    def test_contract_native_generator_and_provenance(self):
        self.assertEqual(DOCUMENT["id"], ID)
        self.assertEqual(DOCUMENT["lifecycle"], "active")
        self.assertEqual(DOCUMENT, json.loads((ROOT / AUTHORED).read_text()))
        self.assertIn(SOURCE, [s["path"] for s in DOCUMENT["provenance"]["sources"]])
        for row in DOCUMENT["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        # Candidate files can live outside the repository. Equality above binds
        # this repository-root provenance check to that explicitly selected file.
        validated = validate(
            ROOT / AUTHORED, repository_root=ROOT, require_declared_bindings=True
        )
        self.assertTrue(validated["valid"], validated["errors"])
        spec = importlib.util.spec_from_file_location(
            "_grounded0004_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(
            [d for d in normalizer.inventory() if d["id"] == ID], [DOCUMENT]
        )
        self.assertEqual(
            DOCUMENT["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(DOCUMENT["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(set(DOCUMENT["outputs"]), {"report"})

    def test_source_oracle_cli_and_large_finite_inputs(self):
        original = oracle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "artifact.py"
            variants = [
                None,
                'raise ValueError("fixture import error")',
                fixture(),
                fixture(depth=1),
                fixture(
                    '\ndef validate_dimensions(): record("dimensions"); return False\n'
                ),
                fixture("\nPROJECTION_BRIDGES=[]\n"),
                fixture(depth=1200),
            ]
            for text in variants:
                if text is not None:
                    path.write_text(text)
                expected = original["build_report"](CASE, path, None)
                self.assertEqual(NATIVE.build_report(CASE, path, None), expected)
                results = []
                for main in (original["main"], NATIVE.main):
                    stdout = io.StringIO()
                    with redirect_stdout(stdout):
                        code = main(
                            ["--case", CASE, "--sympy-file", str(path), "--json"]
                        )
                    results.append((code, stdout.getvalue()))
                self.assertEqual(results[0], results[1])
                self.assertEqual(code, 3 if expected["status"] == "blocked" else 0)

    def test_registered_policy_and_scope_lifecycle(self):
        async def scenario():
            import mcp_server as server
            import sympy_grounded_sample_tools as tools
            from mcp.server.fastmcp.exceptions import ToolError

            previous = server._READONLY

            async def call(name, **arguments):
                return (await server.mcp.call_tool(PREFIX + name, arguments))[1]

            try:
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "artifact.py"
                    path.write_text(fixture())
                    async with server.mcp.settings.lifespan(server.mcp):
                        server._READONLY = True
                        with self.assertRaises(ToolError):
                            await call("initialize_gate", **inputs(path))
                        self.assertFalse(tools._SCOPES)
                        server._READONLY = False
                        initial = await call("initialize_gate", **inputs(path))
                        with self.assertRaises(ToolError):
                            await call("inspect_validate", **initial)
                        self.assertFalse(tools._SCOPES)
                        initial = await call("initialize_gate", **inputs(path))
                        forged = deepcopy(initial)
                        forged["state"]["case_id"] = "changed"
                        with self.assertRaises(ToolError):
                            await call("import_failed", **forged)
                        with self.assertRaises(ToolError):
                            await call("import_failed", **initial)
                        initial = await call("initialize_gate", **inputs(path))
                        self.assertEqual(
                            await call("import_failed", **initial), {"failed": False}
                        )
                        with self.assertRaises(ToolError):
                            await call("import_failed", **initial)
                        initial = await call(
                            "initialize_gate", **inputs(Path(directory) / "missing.py")
                        )
                        self.assertEqual(
                            await call("import_failed", **initial), {"failed": True}
                        )
                        self.assertEqual(
                            (await call("import_blocked", **initial))["report"][
                                "status"
                            ],
                            "blocked",
                        )
                        self.assertFalse(tools._SCOPES)
                        self.assertFalse(
                            tools._REPORTS
                        )  # build_report creates no emission handles.
                        await call("initialize_gate", **inputs(path))
                        self.assertTrue(tools._SCOPES)
                    self.assertFalse(tools._SCOPES)
            finally:
                server._READONLY = previous

        asyncio.run(scenario())

    def test_registered_mcp_lunar_compile_and_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        original = oracle()
        server = (
            "import os,sys;sys.dont_write_bytecode=True;"
            'os.environ["PYTHONDONTWRITEBYTECODE"]="1";'
            'sys.path.insert(0,"scripts");import mcp_server;'
            'mcp_server.mcp.run(transport="stdio")'
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "artifact.py"
            trace = root / "trace.jsonl"
            log = root / "events.jsonl"
            async with manager.open(
                "sympy-grounded-0004",
                StdioConfig(
                    command=str(ROOT / ".venv/bin/python"),
                    args=["-c", server],
                    cwd=str(ROOT),
                ),
                {},
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=None):
                    received = assets(doc)
                    graph = compile_workflow(
                        "mcp:sympy-grounded-0004",
                        workflow_documents([DESCRIPTOR], received)[0],
                        tools if inventory is None else inventory,
                    )
                    return graph, received

                graph, received = compile(DOCUMENT)
                self.assertTrue(graph["runnable"], graph["diagnostics"])
                self.assertTrue(graph["runtime_source"])
                self.assertEqual(set(graph["bindings"]), set(DOCUMENT["operations"]))
                self.assertFalse(compile(DOCUMENT, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(values, doc=None, damage=None):
                    graph, received = compile(doc or DOCUMENT)
                    self.assertTrue(graph["runnable"], graph["diagnostics"])
                    observed = Observed(remote)
                    # The initialization interface here differs from the CLI adapter.
                    if damage:
                        original_call = observed.call

                        async def call(name, arguments):
                            result = await original_call(name, arguments)
                            if name == PREFIX + "initialize_gate":
                                damage(result)
                            return result

                        observed.call = call
                    result = await execute(graph, received, values, observed, authorize)
                    return result, observed

                variants = [
                    (None, "blocked"),
                    ('raise ValueError("fixture import failure")', "blocked"),
                    (fixture(trace=trace), "complete_sympy_physics_derivation"),
                    (
                        fixture(
                            '\ndef validate_dimensions(): record("dimensions"); return False\n'
                        ),
                        "derivation_partial",
                    ),
                    (
                        fixture(
                            '\ndef validate_dimensions(): record("dimensions"); raise ValueError("safe failure")\n'
                        ),
                        "derivation_partial",
                    ),
                    (fixture("\ndel validate_dimensions\n"), "derivation_partial"),
                    (fixture(depth=1), "grounded_scaffold"),
                    (fixture("\nPROJECTION_BRIDGES=[]\n"), "blocked"),
                    (fixture("\nCLAIM={}\n"), "blocked"),
                    (fixture("\nSYMPY_LIBRARY_GROUNDING={}\n"), "blocked"),
                    (fixture("\ndel review_final_equations\n"), "derivation_partial"),
                    (
                        fixture(
                            '\nclass Evidence:\n    def __str__(self): return "fixed-symbol"\ndef validate_dimensions():\n    record("dimensions")\n    return {"passed":True,"target_value":Evidence()}\n'
                        ),
                        "complete_sympy_physics_derivation",
                    ),
                    (
                        fixture(
                            '\ndef review_final_equations():\n    global reviews\n    reviews += 1\n    record("review"+str(reviews))\n    return {"equation":{"status":"pass" if reviews == 1 else "fail","repair_surfaces":list(history)}}\n',
                            trace=trace,
                        ),
                        "complete_sympy_physics_derivation",
                    ),
                    (fixture(depth=1200), "complete_sympy_physics_derivation"),
                ]
                for text, status in variants:
                    with self.subTest(status=status, fixture=text and text[-60:]):
                        if text is not None:
                            path.write_text(text)
                        expected = json.loads(
                            json.dumps(
                                original["build_report"](CASE, path, None), default=str
                            )
                        )
                        trace.unlink(missing_ok=True)
                        result, observed = await run(inputs(path))
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"report": expected})
                        self.assertEqual(expected["status"], status)
                        failed = observed.events[1][2]["failed"]
                        names = ["initialize_gate", "import_failed"] + (
                            ["import_blocked"]
                            if failed
                            else [
                                "inspect_validate",
                                "design_and_review",
                                "finish_report",
                            ]
                        )
                        self.assertEqual(
                            [e[0] for e in observed.events], [PREFIX + n for n in names]
                        )
                        self.assertEqual(len(result["calls"]), 3 if failed else 5)
                        if not failed:
                            state = observed.events[2][2]["state"]
                            self.assertEqual(
                                list(state["checks"]),
                                [
                                    "compiled_or_executed",
                                    "source_commentary",
                                    "equation_surface_depth",
                                    "library_grounding_high",
                                ],
                            )
                            self.assertEqual(
                                state["module"],
                                observed.events[0][2]["state"]["module"],
                            )
                            self.assertIn("run_all_report", state["validation"])
                            self.assertEqual(
                                observed.events[3][2]["state"]["case_id"], CASE
                            )
                            if trace.exists():
                                events = [
                                    json.loads(line)
                                    for line in trace.read_text().splitlines()
                                ]
                                self.assertEqual(
                                    [e["event"] for e in events],
                                    [
                                        "dimensions",
                                        "numeric",
                                        "steps",
                                        "target",
                                        "review1",
                                        "run_all",
                                        "target",
                                        "numeric",
                                        "review2",
                                    ],
                                )
                                self.assertEqual(
                                    events[-1]["history"],
                                    [
                                        "import",
                                        "dimensions",
                                        "numeric",
                                        "steps",
                                        "target",
                                        "review1",
                                        "run_all",
                                        "review2",
                                    ],
                                )
                                self.assertTrue(
                                    expected["checks"]["final_reviews"]["passed"]
                                )
                        else:
                            self.assertEqual(
                                list(expected["checks"]), ["compiled_or_executed"]
                            )
                            self.assertEqual(
                                expected["findings"][0]["code"],
                                "artifact_import_failed",
                            )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["replay_artifacts"])
                # Design guard logging remains source-owned, without a CLI gate event.
                path.write_text(fixture())
                log.write_text('{"step":"fixture_start"}\n')
                expected = original["build_report"](CASE, path, log)
                expected_log = normalize_log(log.read_text())
                log.write_text('{"step":"fixture_start"}\n')
                result, _ = await run(inputs(path, log))
                self.assertEqual(result["outputs"], {"report": expected})
                self.assertEqual(normalize_log(log.read_text()), expected_log)
                self.assertEqual(len(expected_log), 2)
                # Import failure immediately stops; no callback or design log runs.
                log.unlink()
                result, _ = await run(inputs(root / "missing.py", log))
                self.assertEqual(result["outputs"]["report"]["status"], "blocked")
                self.assertFalse(log.exists())
                # Exceptions safe_call does not catch propagate without retry.
                errors = [
                    (
                        '\ndef review_final_equations(): raise RuntimeError("direct failure")\n',
                        RuntimeError,
                        3,
                    ),
                    (
                        '\ndef review_final_equations():\n    global reviews\n    reviews += 1\n    if reviews == 2: raise RuntimeError("second review failure")\n    return {"equation":{"status":"pass"}}\n',
                        RuntimeError,
                        4,
                    ),
                    (
                        '\ndef validate_no_hidden_target(): record("target"); raise RuntimeError("design child failure")\n',
                        subprocess.CalledProcessError,
                        4,
                    ),
                    ('\nprint("invalid design JSON")\n', json.JSONDecodeError, 4),
                    ('\nEQUATION_SURFACE={"EQUATION_GRAPH":None}\n', AttributeError, 3),
                ]
                for extra, exception, count in errors:
                    path.write_text(fixture(extra))
                    with self.assertRaises(exception), redirect_stdout(io.StringIO()):
                        original["build_report"](CASE, path, None)
                    result, observed = await run(inputs(path))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(len(result["calls"]), count)
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            PREFIX + "inspect_validate",
                            {"state": observed.events[0][2]["state"]},
                        )
                path.write_text(fixture())
                result, _ = await run(inputs(path), damage=lambda _: path.unlink())
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 3)
                # Native has no search/exhaustion loop; these are host call/time bounds.
                path.write_text(fixture(trace=trace))
                trace.unlink(missing_ok=True)
                budget = deepcopy(DOCUMENT)
                budget["policy"]["limits"]["max_operation_calls"] = 2
                result, _ = await run(inputs(path), budget)
                self.assertEqual(result["status"], "failed", result)
                self.assertIsNone(result["outputs"])
                self.assertIn("budget", str(result).lower())
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    2,
                )
                self.assertFalse(trace.exists())
                timed = deepcopy(DOCUMENT)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                graph, received = compile(timed)

                async def pending_authorization():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        graph, received, inputs(path), remote, pending_authorization
                    )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
