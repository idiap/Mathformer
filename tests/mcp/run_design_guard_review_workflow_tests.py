#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic fixture artifacts through actual MCP, Lunar and PRISM.

The reviewer has no provider/model or external compiler boundary. Only tiny
Python input artifacts are created; all native steps, MCP tools, PRISM parser,
checker, compiler and runtime execute for real. No production workflow runs.
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
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import yaml

from design_guard_review_tools import source, SOURCE
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute, ExecutionRejected
from mcp_connections.workflow_contract.validator import validate

NATIVE = source()
REFERENCES = "skills/control/workflow-contract-validator/references"
# The host supplies either a candidate or the provisionally installed contract.
# Keep one real execution suite for the two case-specific native hub routes.
DOCUMENT = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
CONTRACTS = {
    "hub_physics_sympy_design_guard_review_0000_workflow": (
        "formalphysics_0000",
        "design-guard-review.workflow.json",
    ),
    "hub_physics_sympy_design_guard_review_0004_workflow": (
        "formalphysics_0004",
        "design-guard-review-0004.workflow.json",
    ),
}
CASE, authored_name = CONTRACTS[DOCUMENT["id"]]
DESCRIPTOR = f"{REFERENCES}/normalized-workflows/hub/{DOCUMENT['id']}/workflow.yaml"
AUTHORED = f"{REFERENCES}/{authored_name}"
PREFIX = "mathformer_design_guard_"


def oracle():
    namespace = vars(NATIVE).copy()
    path = ROOT / "tests/mcp/fixtures/design_guard_review_original.py.txt"
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == "68c4ce3a235f856d1ef7844efb66a7cfb00913c82fb6eff17de047e74f1a3004"
    )
    exec(path.read_text(), namespace)
    return namespace["build_design_guard_review"]


def fixture_source(extra="", count=1):
    """Input modules expose native callable evidence; imports retain local history."""
    header = "\n".join(NATIVE.COMMENTARY_MARKERS)
    fields = {
        "CLAIM": {"commentary_header": header},
        "ASSUMPTION_CONTEXT": {
            "CONTEXT_ASSUMPTIONS": [
                {
                    "text": "fixed coordinate frame",
                    "support": "source_backed",
                    "source_anchor": "L1",
                }
                for _ in range(count)
            ]
        },
        "PROJECTION_BRIDGES": [{"status": "provided"} for _ in range(count)],
        "DERIVATION_STEPS": [
            {"generated": False, "source": "source_backed", "source_anchor": "L1"}
            for _ in range(count)
        ],
        "SYMPY_LIBRARY_GROUNDING": {"grounding_level": "high"},
        "EQUATION_SURFACE": {
            "EQUATION_GRAPH": {"frame_context": {"frame": "Cartesian"}}
        },
    }
    return (
        "# component-level artifact\n"
        + "\n".join(k + " = " + repr(v) for k, v in fields.items())
        + """
history = ['import']
def validate_no_hidden_target():
    assert history == ['import'], history
    history.append('target')
    return {'passed': True, 'history': list(history)}
def validate_numeric_samples():
    assert history == ['import', 'target'], history
    history.append('numeric')
    return {'passed': True, 'domain': 'x > 0', 'history': list(history)}
"""
        + extra
    )


def assets(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]


def request(path, log=None):
    return dict(
        case_id=CASE, path=str(path), reasoning_log=None if log is None else str(log)
    )


class ObservedRemote:
    def __init__(self, remote):
        self.remote = remote
        self.events = []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, name, arguments):
        result = await self.remote.call(name, arguments)
        self.events.append((name, deepcopy(arguments), deepcopy(result)))
        return result


class DesignGuardTests(unittest.TestCase):
    def test_original_and_shared_native_steps(self):
        original = oracle()
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            path = directory / "artifact.py"
            log = directory / "events.jsonl"
            for text, code in [
                (None, "artifact_missing"),
                ('raise RuntimeError("broken import")', "artifact_import_failed"),
                (fixture_source(), None),
                (
                    fixture_source(
                        '\ndef validate_numeric_samples():\n    raise ValueError("numeric failure")\n'
                    ),
                    "numeric_domain_hole",
                ),
                (
                    fixture_source("\ndel validate_numeric_samples\n"),
                    "numeric_domain_not_exposed",
                ),
            ]:
                if text is not None:
                    path.write_text(text)
                expected = original(CASE, path, None)
                self.assertEqual(
                    NATIVE.build_design_guard_review(CASE, path, None), expected
                )
                # Native transport-independent blocks share the algorithm.
                state, present = NATIVE.initialize_design_guard_review(path, None)
                self.assertEqual(state["evidence"]["artifact_exists"], present)
                if not present:
                    state = NATIVE.missing_design_guard_artifact(path, state)
                else:
                    state, artifact = NATIVE.read_design_guard_artifact(
                        CASE, path, state
                    )
                    state = (
                        NATIVE.failed_design_guard_import(state)
                        if artifact is None
                        else NATIVE.inspect_design_guard_module(state, artifact)
                    )
                self.assertEqual(
                    NATIVE.finish_design_guard_review(CASE, None, state), expected
                )
                if code:
                    self.assertIn(code, [f["code"] for f in expected["findings"]])
            path.write_text(fixture_source(count=1500))
            expected = original(CASE, path, None)
            self.assertEqual(
                expected, NATIVE.build_design_guard_review(CASE, path, None)
            )
            self.assertEqual(expected["evidence"]["assumption_count"], 1500)
            self.assertEqual(expected["evidence"]["projection_bridge_count"], 1500)
            self.assertEqual(expected["evidence"]["derivation_step_count"], 1500)
            self.assertEqual(expected["status"], "pass")
            # All log paths and only the first event are native behavior.
            path.write_text(fixture_source())
            for text, code in [
                (None, "reasoning_log_missing_or_empty"),
                ("", "reasoning_log_missing_or_empty"),
                ("  \n", "reasoning_log_missing_or_empty"),
                ("bad\n", "reasoning_log_invalid_json"),
                ('{"step":"first"}\ninvalid trailing JSON', None),
            ]:
                if text is not None:
                    log.write_text(text)
                expected = original(CASE, path, log)
                self.assertEqual(
                    NATIVE.build_design_guard_review(CASE, path, log), expected
                )
                if code:
                    self.assertIn(code, [f["code"] for f in expected["findings"]])
                else:
                    self.assertEqual(
                        expected["evidence"]["reasoning_log_first_event_step"], "first"
                    )
            log.write_text("[]\n")
            for call in [original, NATIVE.build_design_guard_review]:
                with self.assertRaises(AttributeError):
                    call(CASE, path, log)
                with self.assertRaises(IsADirectoryError):
                    call(CASE, directory, None)
            path.write_text(
                fixture_source(
                    '\ndef validate_no_hidden_target():\n    raise RuntimeError("uncaught target callback")\n'
                )
            )
            for call in [original, NATIVE.build_design_guard_review]:
                with self.assertRaisesRegex(RuntimeError, "uncaught target"):
                    call(CASE, path, None)
            # Preserve default path discrepancy rather than silently redirecting.
            self.assertEqual(
                NATIVE.case_path(CASE, None),
                ROOT / "MathformerPhysicsLib/SymPy" / CASE / "MathformerPhysics.py",
            )
            path.unlink()
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = NATIVE.main(
                    [
                        "--mode",
                        "design_guard_review",
                        "--case",
                        CASE,
                        "--sympy-file",
                        str(path),
                        "--json",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue()), original(CASE, path, None))
            self.assertEqual(json.loads(stdout.getvalue())["status"], "fail")
            output = directory / "report.json"
            log.write_text('{"step":"first"}\n')
            expected = original(CASE, path, log)
            self.assertEqual(
                NATIVE.main(
                    [
                        "--mode",
                        "design_guard_review",
                        "--case",
                        CASE,
                        "--sympy-file",
                        str(path),
                        "--output",
                        str(output),
                        "--reasoning-log",
                        str(log),
                    ]
                ),
                0,
            )
            self.assertEqual(json.loads(output.read_text()), expected)
            events = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(len(events), 2)
            self.assertIn("physics.sympy.design_guard.review", json.dumps(events[-1]))

    def test_authored_contract_validation_and_generator(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        authored = json.loads((ROOT / AUTHORED).read_text())
        self.assertEqual(authored, document)
        result = validate(
            ROOT / AUTHORED, repository_root=ROOT, require_declared_bindings=True
        )
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(document["lifecycle"], "active")
        if CASE == "formalphysics_0004":
            self.assertEqual(
                document["policy"]["limits"],
                {"wall_time_seconds": 3600, "max_operation_calls": 4},
            )
            self.assertEqual(
                document["aliases"], ["physics-sympy:design-guard-review-0004"]
            )
        self.assertIn(SOURCE, [s["path"] for s in document["provenance"]["sources"]])
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        spec = importlib.util.spec_from_file_location(
            "_design_guard_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(
            [d for d in module.inventory() if d["id"] == document["id"]], [authored]
        )

    def test_registered_tools_and_real_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        manager = SessionManager()
        failure = None
        command = (
            str(ROOT / ".venv/bin/python")
            if (ROOT / ".venv/bin/python").exists()
            else sys.executable
        )
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            async with manager.open(
                "design-guard",
                StdioConfig(command=command, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(doc, inventory=None):
                        received = assets(doc)
                        selected = workflow_documents([DESCRIPTOR], received)[0]
                        workflow = compile_workflow(
                            "mcp:design-guard",
                            selected,
                            tools if inventory is None else inventory,
                        )
                        return workflow, received

                    workflow, received = compile(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertTrue(workflow["prism_source"])
                    self.assertEqual(
                        set(workflow["bindings"]), set(document["operations"])
                    )
                    self.assertFalse(compile(document, [])[0]["runnable"])
                    for op in document["operations"].values():
                        target = op["execution"]["binding"]["target"]
                        self.assertFalse(
                            compile(
                                document, [t for t in tools if t["name"] != target]
                            )[0]["runnable"]
                        )
                    draft = deepcopy(document)
                    draft["lifecycle"] = "draft"
                    self.assertFalse(compile(draft)[0]["runnable"])

                    async def allow():
                        pass

                    async def run(req, doc=None):
                        w, a = compile(doc) if doc else (workflow, received)
                        observed = ObservedRemote(remote)
                        result = await execute(w, a, {"request": req}, observed, allow)
                        return result, observed.events

                    async def compare(path, log=None, tail=None):
                        req = request(path, log)
                        expected = oracle()(CASE, path, log)
                        result, events = await run(req)
                        self.assertEqual(result["status"], "accepted", result)
                        self.assertEqual(result["outputs"], {"report": expected})
                        self.assertEqual(
                            [c["tool"] for c in result["calls"]], [e[0] for e in events]
                        )
                        if tail:
                            self.assertEqual(
                                [e[0] for e in events],
                                [
                                    PREFIX + x
                                    for x in ["initialize", *tail, "finish_review"]
                                ],
                            )
                        self.assertTrue(result["runtime"]["effect_records"])
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        self.assertTrue(
                            all(
                                c["input_digest"] and c["output_digest"]
                                for c in result["calls"]
                            )
                        )
                        self.assertEqual(
                            events[0][2],
                            {
                                "state": NATIVE.initialize_design_guard_review(
                                    path, log
                                )[0],
                                "artifact_present": path.exists(),
                            },
                        )
                        state = deepcopy(events[0][2]["state"])
                        for name, args, out in events[1:]:
                            self.assertEqual(args["state"], state)
                            if name.endswith("missing_artifact"):
                                state = NATIVE.missing_design_guard_artifact(
                                    path, state
                                )
                            elif name.endswith("read_and_import"):
                                state, artifact = NATIVE.read_design_guard_artifact(
                                    CASE, path, state
                                )
                                self.assertEqual(
                                    out["module_loaded"], artifact is not None
                                )
                                self.assertEqual(
                                    out["artifact"] is not None, artifact is not None
                                )
                            elif name.endswith("failed_import"):
                                state = NATIVE.failed_design_guard_import(state)
                            elif name.endswith("inspect_module"):
                                state = NATIVE.inspect_design_guard_module(
                                    state, artifact
                                )
                            elif name.endswith("finish_review"):
                                self.assertEqual(
                                    out,
                                    {
                                        "report": NATIVE.finish_design_guard_review(
                                            CASE, log, state
                                        )
                                    },
                                )
                            if "state" in out:
                                self.assertEqual(out["state"], state)
                        return result, events

                    # Both missing and failed imports reach log inspection, and fail reports are returned data.
                    missing = directory / "missing.py"
                    result, _ = await compare(missing, tail=["missing_artifact"])
                    self.assertEqual(result["outputs"]["report"]["status"], "fail")
                    bad = directory / "import_failure.py"
                    bad.write_text('raise RuntimeError("fixture import failure")')
                    result, _ = await compare(
                        bad, tail=["read_and_import", "failed_import"]
                    )
                    self.assertEqual(
                        [f["code"] for f in result["outputs"]["report"]["findings"]][
                            :4
                        ],
                        ["missing_source_commentary_marker"] * 3
                        + ["artifact_import_failed"],
                    )
                    healthy = directory / "healthy.py"
                    healthy.write_text(fixture_source())
                    await compare(healthy, tail=["read_and_import", "inspect_module"])
                    # No source collection cap or retry/convergence loop is introduced.
                    many = directory / "many.py"
                    many.write_text(fixture_source(count=1500))
                    result, _ = await compare(
                        many, tail=["read_and_import", "inspect_module"]
                    )
                    self.assertEqual(
                        result["outputs"]["report"]["evidence"]["assumption_count"],
                        1500,
                    )
                    debt = directory / "debts.py"
                    debt.write_text(fixture_source("""
CLAIM = None
ASSUMPTION_CONTEXT = {'CONTEXT_ASSUMPTIONS': [None, {'support':'invalid'}, {'support':'source_backed'}, {'support':'generated_support'}]}
EQUATION_SURFACE = {}
PROJECTION_BRIDGES = [None, {'status':'bad'}]
DERIVATION_STEPS = [None, {}, {'generated':False}]
SYMPY_LIBRARY_GROUNDING = None
def validate_numeric_samples():
    raise ValueError('numeric callback failure')
"""))
                    result, _ = await compare(debt)
                    report = result["outputs"]["report"]
                    self.assertEqual(report["status"], "fail")
                    codes = [f["code"] for f in report["findings"]]
                    self.assertEqual(
                        codes,
                        [
                            "stale_or_missing_structured_commentary",
                            "assumption_support_label_missing",
                            "assumption_source_anchor_missing",
                            "silent_assumption_strengthening",
                            "missing_frame_or_regime_context",
                            "projection_bridge_status_not_ready",
                            "projection_bridge_status_not_ready",
                            "generated_support_label_missing",
                            "generated_support_label_missing",
                            "source_step_anchor_missing",
                            "installed_library_grounding_not_high",
                            "numeric_domain_hole",
                            "reasoning_log_not_requested",
                        ],
                    )
                    self.assertEqual(
                        report["repair_surfaces"],
                        sorted(set(f["repair_surface"] for f in report["findings"])),
                    )
                    self.assertEqual(report["high_severity_finding_count"], 12)
                    for extra in [
                        "\nASSUMPTION_CONTEXT = {}\nPROJECTION_BRIDGES = []\nDERIVATION_STEPS = []\ndel validate_numeric_samples\n",
                        "\ndef validate_no_hidden_target():\n    return False\ndef validate_numeric_samples():\n    return True\n",
                    ]:
                        path = directory / ("variant" + str(len(extra)) + ".py")
                        path.write_text(fixture_source(extra))
                        await compare(path)
                    log = directory / "events.jsonl"
                    for text in [
                        None,
                        "",
                        "  \n",
                        "invalid\n",
                        '{"step":"review.start"}\nnot json',
                    ]:
                        if text is not None:
                            log.write_text(text)
                        await compare(healthy, log)
                    # Transport retains the original imported module even when source changes.
                    req = request(healthy)
                    init = await remote.call(PREFIX + "initialize", {"request": req})
                    loaded = await remote.call(
                        PREFIX + "read_and_import",
                        {"request": req, "state": init["state"]},
                    )
                    healthy.write_text('raise RuntimeError("must not reimport")')
                    inspected = await remote.call(
                        PREFIX + "inspect_module",
                        {"state": loaded["state"], "artifact": loaded["artifact"]},
                    )
                    self.assertEqual(
                        inspected["state"]["evidence"]["target_nonleakage"]["history"],
                        ["import", "target"],
                    )
                    self.assertTrue(
                        inspected["state"]["evidence"]["numeric_domain"]["passed"]
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            PREFIX + "inspect_module",
                            {"state": loaded["state"], "artifact": loaded["artifact"]},
                        )
                    healthy.write_text(fixture_source())
                    loaded = await remote.call(
                        PREFIX + "read_and_import",
                        {"request": req, "state": init["state"]},
                    )
                    changed = deepcopy(loaded["state"])
                    changed["evidence"]["artifact_exists"] = False
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            PREFIX + "inspect_module",
                            {"state": changed, "artifact": loaded["artifact"]},
                        )
                    # Rejected state and callback exceptions both consume the handle.
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            PREFIX + "inspect_module",
                            {"state": loaded["state"], "artifact": loaded["artifact"]},
                        )
                    # Bad native callbacks and log metadata terminate; never finish or repair.
                    callback = directory / "callback.py"
                    callback.write_text(
                        fixture_source(
                            '\ndef validate_no_hidden_target():\n    raise RuntimeError("uncaught callback failure")\n'
                        )
                    )
                    result, _ = await run(request(callback))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            PREFIX + x
                            for x in ["initialize", "read_and_import", "inspect_module"]
                        ],
                    )
                    self.assertEqual(result["calls"][-1]["status"], "rejected")
                    init = await remote.call(
                        PREFIX + "initialize", {"request": request(callback)}
                    )
                    loaded = await remote.call(
                        PREFIX + "read_and_import",
                        {"request": request(callback), "state": init["state"]},
                    )
                    for _ in range(2):
                        with self.assertRaises(MCPConnectionError):
                            await remote.call(
                                PREFIX + "inspect_module",
                                {
                                    "state": loaded["state"],
                                    "artifact": loaded["artifact"],
                                },
                            )
                    healthy.write_text(fixture_source())
                    log.write_text("[]\n")
                    result, _ = await run(request(healthy, log))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        result["calls"][-1]["tool"], PREFIX + "finish_review"
                    )
                    result, _ = await run(request(directory))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 2)
                    # Descriptor operation budget stops dispatch and never returns a partial report.
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 1
                    result, _ = await run(request(missing), budget)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertIn("budget", str(result).lower())
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        1,
                    )
                    # Full four-call branches exactly fit the retained budget;
                    # one fewer call prevents finalization and partial acceptance.
                    budget["policy"]["limits"]["max_operation_calls"] = 3
                    result, _ = await run(request(many), budget)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        3,
                    )
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    timed_workflow, timed_assets = compile(timed)

                    async def pending_authorization():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            timed_workflow,
                            timed_assets,
                            {"request": request(missing)},
                            remote,
                            pending_authorization,
                        )
                    invalid = request(missing)
                    del invalid["case_id"]
                    with self.assertRaises(ExecutionRejected):
                        await run(invalid)
                    schema = document["types"][document["inputs"]["request"]["type"]][
                        "schema"
                    ]
                    if "const" in schema["properties"]["case_id"]:
                        with self.assertRaises(ExecutionRejected):
                            await run(
                                dict(request(missing), case_id="formalphysics_9999")
                            )
                    else:
                        # The selected function's case context is an explicit
                        # input, including overrides supplied to the native CLI.
                        other = request(missing)
                        other["case_id"] = "formalphysics_0001"
                        result, _ = await run(other)
                        self.assertEqual(
                            result["outputs"]["report"],
                            oracle()("formalphysics_0001", missing, None),
                        )
                except Exception as error:
                    failure = error
            if failure:
                raise failure
            # Configure the actual service's existing read-only policy: imports
            # and callbacks must be refused even for a healthy fixture module.
            readonly_server = 'import sys;sys.path.insert(0,"scripts");import mcp_server; mcp_server._READONLY=True; mcp_server.mcp.run(transport="stdio")'
            async with manager.open(
                "design-guard-readonly",
                StdioConfig(
                    command=command, args=["-c", readonly_server], cwd=str(ROOT)
                ),
                {},
            ) as remote:
                try:
                    req = request(healthy)
                    init = await remote.call(PREFIX + "initialize", {"request": req})
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            PREFIX + "read_and_import",
                            {"request": req, "state": init["state"]},
                        )
                except Exception as error:
                    failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DesignGuardTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun and not result.skipped else 1
    )
