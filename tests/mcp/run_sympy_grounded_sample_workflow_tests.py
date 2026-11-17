#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synthetic Python artifacts through native gate, MCP, Lunar and real PRISM.

The gate has no model/provider or theorem compiler dependency to substitute.
Fixed artifact callbacks are input fixtures, not production step replacements.
The native design-guard Python CLI, registered tools, PRISM parser/checker/
compiler and runtime all run unmodified. No production artifacts are imported.
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
import re
import subprocess
import tempfile
import unittest
import yaml
from sympy_grounded_sample_tools import source, SOURCE
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.workflow_contract.validator import validate
from mcp_connections.execution import execute

NATIVE = source()
PREFIX = "mathformer_sympy_grounded_"
REFERENCES = "skills/control/workflow-contract-validator/references"
AUTHORED = REFERENCES + "/sympy-grounded-sample.workflow.json"
ID = "hub_physics_sympy_grounded_sample_thoroughness_0000_workflow"
DESCRIPTOR = f"{REFERENCES}/normalized-workflows/hub/{ID}/workflow.yaml"
DOCUMENT = yaml.safe_load(
    Path(os.environ.get("WORKFLOW_CONTRACT_PATH", ROOT / DESCRIPTOR)).read_text()
)
ORIGINAL = ROOT / "tests/mcp/fixtures/sympy_grounded_sample_original.py.txt"


def oracle():
    assert (
        hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
        == "fe5be51949bde770286123ddaa1850d6162c73b868ce7e18ebad2553950c8431"
    )
    namespace = vars(NATIVE).copy()
    exec(ORIGINAL.read_text(), namespace)
    return namespace


def fixture(extra="", depth=2, trace=None):
    fields = {
        "CLAIM": {"commentary_header": "\n".join(NATIVE.COMMENTARY_MARKERS)},
        "EQUATION_SURFACE": {
            "EQUATION_GRAPH": {
                "nodes": [{"id": str(i)} for i in range(depth)],
                "frame_context": {"frame": "Cartesian"},
            }
        },
        "DERIVATION_STEPS": [
            {"generated": False, "source": "source_backed", "source_anchor": "L1"}
            for _ in range(depth)
        ],
        "ASSUMPTION_CONTEXT": {
            "CONTEXT_ASSUMPTIONS": [
                {
                    "text": "fixed coordinate frame",
                    "support": "source_backed",
                    "source_anchor": "L1",
                }
            ]
        },
        "PROJECTION_BRIDGES": [{"status": "provided"}],
        "SYMPY_LIBRARY_GROUNDING": {"grounding_level": "high"},
    }
    return (
        "\n".join(k + " = " + repr(v) for k, v in fields.items())
        + "\nTRACE = "
        + repr(None if trace is None else str(trace))
        + """
import json
from pathlib import Path
history = ['import']
reviews = 0
def record(name):
    history.append(name)
    if TRACE:
        with Path(TRACE).open('a') as stream:
            stream.write(json.dumps({'event': name, 'history': list(history)})+'\\n')
def validate_dimensions():
    assert history == ['import'], history
    record('dimensions')
    return {'passed': True}
def validate_numeric_samples():
    assert history[-1] in ('dimensions', 'target'), history
    record('numeric')
    return {'passed': True, 'domain': 'x > 0'}
def validate_derivation_steps():
    assert history[-1] == 'numeric', history
    record('steps')
    return {'passed': True, 'step_count': len(DERIVATION_STEPS)}
def validate_no_hidden_target():
    assert history[-1] in ('import', 'steps'), history
    record('target')
    return {'passed': True}
def review_final_equations():
    global reviews
    reviews += 1
    assert history[-1] == ('target' if reviews == 1 else 'run_all'), history
    record('review'+str(reviews))
    return {'equation': {'style':'fixture', 'status':'pass', 'findings':[], 'repair_surfaces':list(history)}}
def run_all():
    assert history[-1] == 'review1', history
    record('run_all')
    return {'passed': True, 'final_equation_reviews': {'equation': {'status':'pass'}}}
"""
        + extra
    )


def stable_log(text):
    events = [json.loads(line) for line in text.splitlines()]
    metadata = {
        "event_index",
        "timestamp_utc",
        "timestamp_unix_ms",
        "monotonic_ns",
        "elapsed_ms_since_log_start",
        "elapsed_ms_since_prev_event",
    }
    for event in events[1:]:
        assert isinstance(event["event_index"], int)
        assert isinstance(event["monotonic_ns"], int)
        assert event["timestamp_utc"]
    assert events[1]["event_index"] < events[2]["event_index"]

    def normalize(value):
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key == "skill_call_id":
                    assert re.fullmatch(r"skill-[a-z0-9-]+-[0-9a-f]{12}", item)
                    item = item.rsplit("-", 1)[0] + "-<invocation>"
                result[key] = normalize(item)
            return result
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value

    return normalize(
        [{k: v for k, v in event.items() if k not in metadata} for event in events]
    )


def request(path=None, output=None, log=None):
    return dict(
        case="0",
        sympy_file=None if path is None else str(path),
        output=None if output is None else str(output),
        reasoning_log=None if log is None else str(log),
    )


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


class Observed:
    def __init__(self, remote, damage=None):
        self.remote, self.damage, self.events = remote, damage, []

    async def tools(self):
        return await self.remote.tools()

    async def call(self, name, arguments):
        result = await self.remote.call(name, arguments)
        self.events.append((name, deepcopy(arguments), deepcopy(result)))
        if self.damage and name == PREFIX + "import_state":
            self.damage(result)
        return result


class GateTests(unittest.TestCase):
    def test_contract_provenance_and_native_generator(self):
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
        result = validate(
            ROOT / AUTHORED, repository_root=ROOT, require_declared_bindings=True
        )
        self.assertTrue(result["valid"], result["errors"])
        spec = importlib.util.spec_from_file_location(
            "_sympy_gate_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual([d for d in module.inventory() if d["id"] == ID], [DOCUMENT])
        original = oracle()
        self.assertEqual(
            NATIVE.case_path("formalphysics_0000", None),
            original["case_path"]("formalphysics_0000", None),
        )
        self.assertEqual(NATIVE.normalize_case("17", None), "formalphysics_0017")
        self.assertEqual(
            NATIVE.normalize_case(None, Path("formalphysics_0012/input.py")),
            "formalphysics_0012",
        )

    def test_original_entrypoint_and_native_steps(self):
        original = oracle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "artifact.py"
            samples = [
                (None, "blocked"),
                ('raise ValueError("import failed")', "blocked"),
                (fixture(), "complete_sympy_physics_derivation"),
                (
                    fixture(
                        '\ndef validate_dimensions(): record("dimensions"); return False\n'
                    ),
                    "derivation_partial",
                ),
                (fixture(depth=1), "grounded_scaffold"),
                (fixture("\nPROJECTION_BRIDGES = []\n"), "blocked"),
                (fixture("\ndel review_final_equations\n"), "derivation_partial"),
            ]
            for text, status in samples:
                with self.subTest(status=status, text=text and text[-70:]):
                    if text is not None:
                        path.write_text(text)
                    expected = original["build_report"](
                        "formalphysics_0000", path, None
                    )
                    self.assertEqual(expected["status"], status)
                    self.assertEqual(
                        NATIVE.build_report("formalphysics_0000", path, None), expected
                    )
                    state = NATIVE.initialize_gate("formalphysics_0000", path, None)
                    if state["module"] is None:
                        actual = NATIVE.blocked_gate_report(state)
                    else:
                        actual = NATIVE.classify_gate(
                            NATIVE.design_and_review_gate(NATIVE.inspect_gate(state))
                        )
                    self.assertEqual(actual, expected)
                    args = ["--case", "0", "--sympy-file", str(path), "--json"]
                    outputs = []
                    for main in (original["main"], NATIVE.main):
                        stdout = io.StringIO()
                        with redirect_stdout(stdout):
                            code = main(args)
                        outputs.append((code, stdout.getvalue()))
                    self.assertEqual(outputs[0], outputs[1])
                    self.assertEqual(code, 3 if status == "blocked" else 0)
            # Large finite inputs are traversed once without invented iteration bounds.
            path.write_text(fixture(depth=1200))
            self.assertEqual(
                NATIVE.build_report("formalphysics_0000", path, None),
                original["build_report"]("formalphysics_0000", path, None),
            )
            # Direct reviews propagate; safe_call validators become failed evidence.
            failures = [
                (
                    '\ndef review_final_equations(): raise RuntimeError("review failed")\n',
                    RuntimeError,
                ),
                (
                    '\ndef review_final_equations():\n    global reviews\n    reviews += 1\n    if reviews == 2: raise RuntimeError("second review failed")\n    return {"equation":{"status":"pass"}}\n',
                    RuntimeError,
                ),
                (
                    '\ndef validate_no_hidden_target(): record("target"); raise RuntimeError("target child fails")\n',
                    subprocess.CalledProcessError,
                ),
                ('\nprint("invalid design JSON")\n', json.JSONDecodeError),
                ('\nEQUATION_SURFACE = {"EQUATION_GRAPH": None}\n', AttributeError),
            ]
            for extra, exception in failures:
                path.write_text(fixture(extra))
                for build in (original["build_report"], NATIVE.build_report):
                    with self.assertRaises(exception), redirect_stdout(io.StringIO()):
                        build("formalphysics_0000", path, None)
            # Source-owned output and log order, including partial writes on log failure.
            path.write_text(fixture())
            output = root / "report.json"
            log = root / "events.jsonl"
            argv = [
                "--sympy-file",
                str(path),
                "--output",
                str(output),
                "--reasoning-log",
                str(log),
            ]
            captures = []
            for main in (original["main"], NATIVE.main):
                log.write_text('{"step":"fixture_start"}\n')
                code = main(argv)
                captures.append((code, output.read_text(), stable_log(log.read_text())))
            self.assertEqual(captures[0], captures[1])
            self.assertEqual(
                len(log.read_text().splitlines()), 3
            )  # seed, design guard, gate
            for emit in (
                lambda report: original["main"](
                    [
                        "--sympy-file",
                        str(root / "missing.py"),
                        "--output",
                        str(output),
                        "--reasoning-log",
                        str(root),
                    ]
                ),
                lambda report: NATIVE.emit_gate_report(report, output, root),
            ):
                with self.assertRaises(IsADirectoryError):
                    emit(
                        NATIVE.build_report(
                            "formalphysics_0000", root / "missing.py", None
                        )
                    )
                self.assertEqual(json.loads(output.read_text())["status"], "blocked")

    def test_registered_service_policy_and_scope_cleanup(self):
        async def scenario():
            import mcp_server as server
            import sympy_grounded_sample_tools as tools
            from mcp.server.fastmcp.exceptions import ToolError

            previous_readonly, previous_roots = (
                server._READONLY,
                server._ALLOWED_WRITE_ROOTS,
            )

            async def call(name, **arguments):
                result = await server.mcp.call_tool(PREFIX + name, arguments)
                return result[1]

            try:
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    allowed = root / "allowed"
                    allowed.mkdir()
                    path = root / "artifact.py"
                    path.write_text(fixture())
                    server.apply_runtime_config(allowed_write_roots=[str(allowed)])
                    async with server.mcp.settings.lifespan(server.mcp):
                        server._READONLY = True
                        with self.assertRaises(ToolError):
                            await call("import_state", request=request(path))
                        self.assertFalse(tools._SCOPES)
                        server._READONLY = False
                        # Gate output precedes a later log authorization failure.
                        init = await call(
                            "import_state", request=request(root / "missing.py")
                        )
                        report = await call("blocked_report", state=init["state"])
                        self.assertFalse(tools._SCOPES)
                        output = allowed / "report.json"
                        outside_log = root / "outside.jsonl"
                        with self.assertRaises(ToolError):
                            await call(
                                "emit",
                                request=request(output=output, log=outside_log),
                                **report,
                            )
                        self.assertEqual(
                            json.loads(output.read_text())["status"], "blocked"
                        )
                        self.assertFalse(outside_log.exists())
                        self.assertFalse(tools._REPORTS)
                        with self.assertRaises(ToolError):
                            await call("emit", request=request(output=output), **report)
                        # A design guard log write outside service roots is denied
                        # before launching the child and consumes the module scope.
                        init = await call(
                            "import_state", request=request(path, log=outside_log)
                        )
                        inspected = await call("inspect_validate", state=init["state"])
                        with self.assertRaises(ToolError):
                            await call("design_and_review", **inspected)
                        self.assertFalse(tools._SCOPES)
                        self.assertFalse(outside_log.exists())
                        init = await call(
                            "import_state", request=request(root / "missing.py")
                        )
                        report = await call("blocked_report", state=init["state"])
                        outside_output = root / "outside.json"
                        with self.assertRaises(ToolError):
                            await call(
                                "emit", request=request(output=outside_output), **report
                            )
                        self.assertFalse(outside_output.exists())
                        # Shutdown releases both abandoned imported modules and
                        # un-emitted reports without running more validators.
                        await call("import_state", request=request(path))
                        init = await call(
                            "import_state", request=request(root / "missing.py")
                        )
                        await call("blocked_report", state=init["state"])
                        self.assertEqual(len(tools._SCOPES), 1)
                        self.assertEqual(len(tools._REPORTS), 1)
                    self.assertFalse(tools._SCOPES)
                    self.assertFalse(tools._REPORTS)
            finally:
                server._READONLY, server._ALLOWED_WRITE_ROOTS = (
                    previous_readonly,
                    previous_roots,
                )

        asyncio.run(scenario())

    def test_actual_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()
        failure = None
        command = str(ROOT / ".venv/bin/python")
        server = 'import sys;sys.path.insert(0,"scripts");import mcp_server;mcp_server.mcp.run(transport="stdio")'
        original = oracle()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "artifact.py"
            trace = root / "trace.jsonl"
            output = root / "report.json"
            log = root / "events.jsonl"
            async with manager.open(
                "sympy-grounded",
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
                        graph = compile_workflow(
                            "mcp:sympy-grounded",
                            workflow_documents([DESCRIPTOR], received)[0],
                            tools if inventory is None else inventory,
                        )
                        return graph, received

                    graph, received = compile(DOCUMENT)
                    self.assertTrue(graph["runnable"], graph["diagnostics"])
                    self.assertTrue(graph["runtime_source"])
                    self.assertEqual(
                        set(graph["bindings"]), set(DOCUMENT["operations"])
                    )
                    self.assertFalse(compile(DOCUMENT, [])[0]["runnable"])
                    self.assertTrue(
                        all(
                            op["execution"]["binding"]["target"]
                            in {t["name"] for t in tools}
                            for op in DOCUMENT["operations"].values()
                        )
                    )

                    async def authorize():
                        pass

                    async def run(req, doc=None, damage=None):
                        graph, received = compile(doc or DOCUMENT)
                        self.assertTrue(graph["runnable"], graph["diagnostics"])
                        observed = Observed(remote, damage)
                        result = await execute(
                            graph, received, {"request": req}, observed, authorize
                        )
                        return result, observed

                    variants = [
                        (None, "blocked"),
                        ('raise ValueError("fixture import failure")', "blocked"),
                        (fixture(trace=trace), "complete_sympy_physics_derivation"),
                        (
                            fixture(
                                '\ndef validate_dimensions(): record("dimensions"); return {"passed":False}\n'
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
                        (
                            fixture(
                                '\ndef validate_derivation_steps(): record("steps"); return False\n'
                            ),
                            "derivation_partial",
                        ),
                        (
                            fixture(
                                '\ndef run_all(): record("run_all"); raise ValueError("run all safe failure")\n'
                            ),
                            "derivation_partial",
                        ),
                        (
                            fixture(
                                '\nclass Evidence:\n    def __str__(self): return "fixed-symbol"\ndef validate_dimensions():\n    record("dimensions")\n    return {"passed":True,"target_value":Evidence()}\n'
                            ),
                            "complete_sympy_physics_derivation",
                        ),
                        (fixture(depth=1), "grounded_scaffold"),
                        (fixture("\nPROJECTION_BRIDGES=[]\n"), "blocked"),
                        (
                            fixture("\ndel review_final_equations\n"),
                            "derivation_partial",
                        ),
                        (
                            fixture(
                                '\ndef review_final_equations():\n    global reviews\n    reviews += 1\n    record("review"+str(reviews))\n    return {"equation":{"status":"pass" if reviews == 1 else "fail","repair_surfaces":list(history)}}\n',
                                trace=trace,
                            ),
                            "complete_sympy_physics_derivation",
                        ),
                    ]
                    for text, status in variants:
                        with self.subTest(status=status, text=text and text[-70:]):
                            if text is not None:
                                path.write_text(text)
                            expected = json.loads(
                                json.dumps(
                                    original["build_report"](
                                        "formalphysics_0000", path, None
                                    ),
                                    default=str,
                                )
                            )
                            trace.unlink(missing_ok=True)
                            result, observed = await run(request(path))
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(
                                result["outputs"],
                                {
                                    "report": expected,
                                    "exit_code": 3 if status == "blocked" else 0,
                                },
                            )
                            self.assertEqual(expected["status"], status)
                            imported = observed.events[0][2]["imported"]
                            self.assertEqual(
                                [e[0] for e in observed.events],
                                [
                                    PREFIX + n
                                    for n in (
                                        [
                                            "import_state",
                                            "inspect_validate",
                                            "design_and_review",
                                            "classify_report",
                                            "emit",
                                        ]
                                        if imported
                                        else ["import_state", "blocked_report", "emit"]
                                    )
                                ],
                            )
                            if imported:
                                checks = observed.events[1][2]["state"]["checks"]
                                self.assertEqual(
                                    list(checks),
                                    [
                                        "compiled_or_executed",
                                        "source_commentary",
                                        "equation_surface_depth",
                                        "library_grounding_high",
                                    ],
                                )
                                self.assertIn(
                                    "run_all_report",
                                    observed.events[1][2]["state"]["validation"],
                                )
                                self.assertEqual(
                                    observed.events[1][2]["state"]["module"],
                                    observed.events[0][2]["state"]["module"],
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
                                if (
                                    "target_value"
                                    in expected["checks"]["unit_dimension"]["evidence"]
                                ):
                                    self.assertEqual(
                                        expected["checks"]["unit_dimension"][
                                            "evidence"
                                        ]["target_value"],
                                        "fixed-symbol",
                                    )
                                if (
                                    trace.exists()
                                    and expected["checks"]["final_reviews"]["evidence"][
                                        "equation"
                                    ]["status"]
                                    == "fail"
                                ):
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
                    # Use CLI defaults explicitly without a production import: the
                    # documented default path is absent in this checkout.
                    self.assertFalse(
                        NATIVE.case_path("formalphysics_0000", None).exists()
                    )
                    result, _ = await run({})
                    self.assertEqual(result["outputs"]["exit_code"], 3)
                    self.assertEqual(
                        result["outputs"]["report"]["artifact_path"],
                        "MathformerPhysicsLib/SymPy/formalphysics_0000/MathformerPhysics.py",
                    )
                    # Source output and two logging stages remain byte-for-byte.
                    path.write_text(fixture())
                    argv = [
                        "--sympy-file",
                        str(path),
                        "--output",
                        str(output),
                        "--reasoning-log",
                        str(log),
                    ]
                    log.write_text('{"step":"fixture_start"}\n')
                    original["main"](argv)
                    expected_output, expected_log = output.read_text(), log.read_text()
                    log.write_text('{"step":"fixture_start"}\n')
                    output.unlink()
                    result, observed = await run(request(path, output, log))
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(output.read_text(), expected_output)
                    self.assertEqual(
                        stable_log(log.read_text()), stable_log(expected_log)
                    )
                    # No retry, no emit after direct callback or design CLI failure.
                    errors = [
                        (
                            '\ndef review_final_equations(): raise RuntimeError("first direct failure")\n',
                            2,
                        ),
                        (
                            '\ndef review_final_equations():\n    global reviews\n    reviews+=1\n    if reviews==2: raise RuntimeError("second direct failure")\n    return {"equation":{"status":"pass"}}\n',
                            3,
                        ),
                        (
                            '\ndef validate_no_hidden_target(): record("target"); raise RuntimeError("child failure")\n',
                            3,
                        ),
                        ('\nprint("polluted design JSON")\n', 3),
                        ('\nEQUATION_SURFACE={"EQUATION_GRAPH":None}\n', 2),
                    ]
                    for extra, calls in errors:
                        path.write_text(fixture(extra))
                        output.unlink(missing_ok=True)
                        result, observed = await run(request(path, output))
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(len(result["calls"]), calls)
                        self.assertEqual(result["calls"][-1]["status"], "rejected")
                        self.assertFalse(output.exists())
                        # The failed scope was consumed and cannot be replayed.
                        with self.assertRaises(MCPConnectionError):
                            await remote.call(
                                PREFIX + "inspect_validate",
                                {"state": observed.events[0][2]["state"]},
                            )
                    # A source read failure after import also propagates directly.
                    path.write_text(fixture())
                    result, _ = await run(request(path), damage=lambda _: path.unlink())
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 2)
                    path.write_text(fixture())
                    result, _ = await run(request(path, root))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(result["calls"][-1]["tool"], PREFIX + "emit")
                    # Native blocked branch writes output before log failure.
                    output.unlink(missing_ok=True)
                    result, _ = await run(request(root / "missing.py", output, root))
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        json.loads(output.read_text())["status"], "blocked"
                    )
                    # Finite graph call budget: no invented convergence loop.
                    path.write_text(fixture())
                    budget = deepcopy(DOCUMENT)
                    budget["policy"]["limits"]["max_operation_calls"] = 2
                    output.unlink()
                    result, observed = await run(request(path, output), budget)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertIsNone(result["outputs"])
                    self.assertIn("budget", str(result).lower())
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        2,
                    )
                    self.assertFalse(output.exists())
                    timed = deepcopy(DOCUMENT)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    graph, received = compile(timed)

                    async def pending_authorization():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(
                            graph,
                            received,
                            {"request": request(path)},
                            remote,
                            pending_authorization,
                        )
                    # Replayed, forged and out-of-order handles cannot re-import
                    # or rerun callbacks; abandoned handles are process-scoped.
                    initialized = await remote.call(
                        PREFIX + "import_state", {"request": request(path)}
                    )
                    bad = deepcopy(initialized["state"])
                    bad["case_id"] = "changed"
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(PREFIX + "inspect_validate", {"state": bad})
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            PREFIX + "inspect_validate", {"state": initialized["state"]}
                        )
                    initialized = await remote.call(
                        PREFIX + "import_state", {"request": request(path)}
                    )
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            PREFIX + "design_and_review",
                            {"state": initialized["state"]},
                        )
                except Exception as error:
                    failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
