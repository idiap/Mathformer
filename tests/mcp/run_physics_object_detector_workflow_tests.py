#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402
"""Native differential fixtures and real registered MCP -> Lunar -> PRISM runs.

No provider/model or external compiler is used by this deterministic detector.
No source step or Lunar parser/checker/compiler/runtime is replaced in tests.
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
from contextlib import (
    asynccontextmanager,
    contextmanager,
    redirect_stdout,
    redirect_stderr,
)
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
from physics_object_detector_tools import native
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_detect_pathology_objects_workflow/workflow.yaml"
PREFIX = "mathformer_physics_objects_"
ALL = "Hilbert operator unbounded operator L2(R) Schwartz commutator vector coordinate gradient integral Newton dimension"
REPORT = {
    "findings": [
        {"category": "z", "code": "implicit_premises_unlabeled"},
        {"category": "a", "code": "other"},
        None,
        "ignored",
    ],
    "lean_features": {
        "has_hilbert_or_inner_product": True,
        "has_operator_surface": True,
        "has_vector_or_field": True,
        "has_calculus_surface": True,
        "has_source_law_surface": True,
        "has_side_conditions": True,
        "raw_scalar_count": 3,
    },
}


def original():
    path = ROOT / "tests/mcp/fixtures/physics_object_detector_original.py.txt"
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == "7de12d9e9d78a0b4683e5e186a608982c3f395e0f41d10092877ece78a1085f5"
    )
    spec = importlib.util.spec_from_loader(
        "_physics_objects_original",
        SourceFileLoader("_physics_objects_original", str(path)),
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


def cli(module, root, argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with (
        cwd(root),
        patch.object(sys, "argv", ["detector.py", *argv]),
        redirect_stdout(stdout),
        redirect_stderr(stderr),
    ):
        try:
            code = module.main(argv)
        except SystemExit as error:
            code = error.code
    return {"stdout": stdout.getvalue(), "exit_code": code}, stderr.getvalue()


def snapshot(document):
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


@asynccontextmanager
async def checked_session(manager, *args):
    # SessionManager masks exception groups; retain local test diagnostics.
    async with manager.open(*args) as remote:
        try:
            yield remote
        except Exception:
            import traceback

            traceback.print_exc()
            raise


class DetectorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="physics-objects-fixture-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.context = {
            "working_directory": str(self.root),
            "program_name": "detector.py",
            "allow_mutating": True,
        }
        self.oracle = original()

    def test_native_differential_branches_and_cli(self):
        # Every literal branch, source flags independent of text, both Lean cues,
        # fallback, non-dictionary findings, all 16 classes, and empty detection.
        sources = [
            "",
            "ket",
            "operator",
            "dense domain",
            "L2(R)",
            "Schwartz",
            "[x,p]",
            "field",
            "basis",
            "curl",
            "limit",
            "Gauss",
            "mass",
            "a" * 2200 + ALL,
            ALL,
        ]
        reports = [
            {},
            REPORT,
            {"findings": [None]},
            {"metadata": "raw_scalar_erasure"},
            {
                "source_features": {
                    k: True
                    for k in (
                        "quantum_dense_notation",
                        "operator_algebra",
                        "vector_or_field",
                        "calculus_or_integral",
                        "physical_law",
                        "implicit_premise_needs",
                    )
                }
            },
        ]
        for source in sources:
            for report in reports:
                data = dict(source_text=source, lean_text=ALL, monitor_report=report)
                self.assertEqual(
                    native.build_packet(**data), self.oracle.build_packet(**data)
                )
        packet = native.build_packet(
            source_text=ALL, lean_text="", monitor_report=REPORT
        )
        self.assertEqual(packet["object_count"], 16)
        self.assertEqual(
            {o["object_class"] for o in packet["objects"]}, set(native.OBJECT_SURFACES)
        )
        self.assertEqual(packet["pathology_categories"], ["a", "z"])
        self.assertEqual(
            packet["objects"],
            sorted(
                packet["objects"], key=lambda o: (-o["confidence"], o["object_class"])
            ),
        )
        for o in packet["objects"]:
            self.assertEqual(o["blocked_until"], native.RERUN_GATES)
        # Raw Lean text changes only the packet id, never detection.
        empty = native.build_packet(source_text="", lean_text=ALL, monitor_report={})
        self.assertEqual(empty["status"], "no_objects_detected")
        a = native.build_packet(source_text="a" * 2200, lean_text="", monitor_report={})
        b = native.build_packet(
            source_text="a" * 2200 + " commutator", lean_text="", monitor_report={}
        )
        self.assertEqual(a["packet_id"], b["packet_id"])
        self.assertNotEqual(a["objects"], b["objects"])
        (self.root / "source.txt").write_text(ALL)
        (self.root / "lean.txt").write_text("Lean ü")
        (self.root / "monitor.json").write_text(json.dumps(REPORT))
        for argv in (
            [],
            ["--help"],
            ["--bad"],
            ["--source-text"],
            ["--self-test", "--source-file", "missing"],
            [
                "--source-file",
                "source.txt",
                "--lean-file",
                "lean.txt",
                "--monitor-report",
                "monitor.json",
            ],
            ["--source-text", "", "--source-file", "missing"],
            ["--source-text", ALL, "--output", "nested/packet.json"],
        ):
            expected = cli(self.oracle, self.root, argv)
            written = (
                (self.root / "nested/packet.json").read_bytes()
                if "--output" in argv
                else None
            )
            self.assertEqual(cli(native, self.root, argv), expected)
            if written:
                self.assertEqual(
                    (self.root / "nested/packet.json").read_bytes(), written
                )
        for payload, error in [
            (b"{", json.JSONDecodeError),
            (b"\xff", UnicodeDecodeError),
            (b"[]", AttributeError),
            (b'{"findings":null}', TypeError),
            (b'{"source_features":null}', AttributeError),
            (
                b'{"lean_features":null,"source_features":{"operator_algebra":true}}',
                AttributeError,
            ),
        ]:
            (self.root / "monitor.json").write_bytes(payload)
            for module in (native, self.oracle):
                with self.assertRaises(error):
                    cli(module, self.root, ["--monitor-report", "monitor.json"])

    def test_registered_mcp_real_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_physics_lean_detect_pathology_objects_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 6},
        )
        self.assertIn(
            "skills/physics-common/physics-math-object-detector/scripts/detect_physics_math_objects.py",
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
        async with checked_session(
            manager, "physics-objects", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                assets = snapshot(doc)
                result = compile_workflow(
                    "mcp:physics-objects",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    inventory,
                )
                return result, assets

            compiled, assets = compile(document)
            if not compiled["runnable"]:
                print(compiled["diagnostics"], file=sys.stderr)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertTrue(compiled["prism_source"])
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
                c, a = (compiled, assets) if doc is document else compile(doc)
                self.assertTrue(c["runnable"], c["diagnostics"])
                return await execute(
                    c,
                    a,
                    {
                        "extra_args": list(argv),
                        "context": self.context if context is None else context,
                    },
                    remote,
                    authorize,
                )

            (self.root / "source.txt").write_text(ALL)
            (self.root / "lean.txt").write_text("Lean ü")
            (self.root / "monitor.json").write_text(json.dumps(REPORT))
            cases = [
                [],
                [
                    "--self-test",
                    "--source-file",
                    "missing",
                    "--monitor-report",
                    "missing",
                ],
                [
                    "--source-file",
                    "source.txt",
                    "--lean-file",
                    "lean.txt",
                    "--monitor-report",
                    "monitor.json",
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
                ["--source-text", ALL, "--monitor-report", "monitor.json"],
                ["--source-text", "a" * 2200 + " commutator"],
                ["--help"],
            ]
            for argv in cases:
                for write in (False, True) if "--help" not in argv else (False,):
                    args = argv + (
                        ["--output", "artifacts/packet.json"] if write else []
                    )
                    expected, _ = cli(self.oracle, self.root, args)
                    written = (
                        (self.root / "artifacts/packet.json").read_bytes()
                        if write
                        else None
                    )
                    packet = (
                        json.loads(written or expected["stdout"])
                        if "--help" not in argv
                        else None
                    )
                    if write:
                        (self.root / "artifacts/packet.json").write_text("stale")
                    result = await run(args)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"packet": packet, **expected})
                    expected_tools = (
                        ["parse_cli", "help"]
                        if "--help" in argv
                        else [
                            "parse_cli",
                            "fixed_fixture" if "--self-test" in argv else "load_inputs",
                            "initialize_state",
                            "accumulate_detections",
                            "finalize_packet",
                            "check_and_emit",
                        ]
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [PREFIX + s for s in expected_tools],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    if write:
                        self.assertEqual(
                            (self.root / "artifacts/packet.json").read_bytes(), written
                        )
            # Full-catalogue bound is normal completion, including 1,031 findings.
            many = {
                "findings": [
                    {"category": str(i), "code": "implicit_premises_unlabeled"}
                    for i in range(1031)
                ]
            }
            (self.root / "monitor.json").write_text(json.dumps(many))
            result = await run(
                ["--source-text", ALL, "--monitor-report", "monitor.json"]
            )
            self.assertEqual(result["status"], "accepted", result)
            packet = result["outputs"]["packet"]
            self.assertEqual(packet["object_count"], 16)
            self.assertEqual(len(packet["pathology_categories"]), 1031)
            self.assertEqual(
                packet,
                self.oracle.build_packet(
                    source_text=ALL, lean_text="", monitor_report=many
                ),
            )
            # Registered state ports retain all evidence; repeated accumulation
            # executes native maximum-confidence / sorted-union merging.
            state = (
                await remote.call(
                    PREFIX + "initialize_state",
                    {
                        "data": {
                            "source_text": ALL,
                            "lean_text": "",
                            "monitor_report": REPORT,
                        },
                        "data_json": json.dumps(
                            {
                                "source_text": ALL,
                                "lean_text": "",
                                "monitor_report": REPORT,
                            }
                        ),
                    },
                )
            )["state"]
            state = (
                await remote.call(
                    PREFIX + "accumulate_detections",
                    {"state": state, "state_json": json.dumps(state)},
                )
            )["state"]
            obj = state["objects"]["quantum_operator"]
            obj.update(
                confidence=0.99,
                source_cues=["extra"],
                lean_cues=["extra"],
                pathology_categories=["extra"],
                reason="first reason",
            )
            merged = (
                await remote.call(
                    PREFIX + "accumulate_detections",
                    {"state": state, "state_json": json.dumps(state)},
                )
            )["state"]
            obj = merged["objects"]["quantum_operator"]
            self.assertEqual(obj["confidence"], 0.99)
            self.assertEqual(obj["source_cues"], ["extra", "operator_algebra"])
            self.assertEqual(obj["lean_cues"], ["extra", "operator_surface_present"])
            self.assertEqual(obj["pathology_categories"], ["a", "extra", "z"])
            self.assertEqual(obj["reason"], "first reason")
            (self.root / "monitor.json").write_text('{"findings":[null]}')
            fallback = await run(["--monitor-report", "monitor.json"])
            self.assertEqual(
                fallback["outputs"]["packet"]["objects"][0]["confidence"], 0.5
            )
            self.assertEqual(fallback["outputs"]["exit_code"], 0)
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
                (b"[]", 2),
                (b'{"findings":null}', 3),
                (b'{"source_features":null}', 3),
                (
                    b'{"lean_features":null,"source_features":{"operator_algebra":true}}',
                    3,
                ),
            ]:
                (self.root / "monitor.json").write_bytes(payload)
                result = await run(
                    [
                        "--monitor-report",
                        "monitor.json",
                        "--output",
                        "never/packet.json",
                    ]
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), count)
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                self.assertFalse((self.root / "never").exists())
            denied = dict(self.context, allow_mutating=False)
            self.assertEqual((await run(context=denied))["status"], "accepted")
            (self.root / "blocker").write_text("file")
            (self.root / "directory").mkdir()
            for path, context in [
                ("denied/out.json", denied),
                ("blocker/out.json", self.context),
                ("directory", self.context),
                (str(self.root.parent / "outside-detector.json"), self.context),
            ]:
                result = await run(["--output", path], context=context)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 6)
                self.assertEqual(result["calls"][-1]["tool"], PREFIX + "check_and_emit")
            self.assertFalse((self.root / "denied").exists())
            # Native assertion and I/O exceptions stop before any success emission.
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "check_and_emit",
                    {
                        "options": {"self_test": True, "output": None},
                        "packet": {"status": "ready", "objects": []},
                        "packet_json": json.dumps({"status": "ready", "objects": []}),
                        "context": self.context,
                    },
                )
            for module in (native, self.oracle):
                with self.assertRaises(FileExistsError):
                    cli(module, self.root, ["--output", "blocker/out.json"])
            bounded = deepcopy(document)
            bounded["policy"]["limits"]["max_operation_calls"] = 3
            result = await run(["--output", "budget/out.json"], doc=bounded)
            self.assertEqual(result["status"], "failed", result)
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]), 3
            )
            self.assertIn("budget", str(result).lower())
            self.assertFalse((self.root / "budget").exists())
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            c, a = compile(timed)

            async def pending():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(
                    c, a, {"extra_args": [], "context": self.context}, remote, pending
                )
        self.assertFalse(manager.active)
        config.args.append("--readonly")
        async with checked_session(
            manager,
            "physics-objects-readonly",
            config,
            {"LUNAR_PLATFORM_ROOT": str(LUNAR)},
        ) as remote:
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "check_and_emit",
                    {
                        "options": {"self_test": False, "output": "readonly/out.json"},
                        "packet": {},
                        "packet_json": "{}",
                        "context": self.context,
                    },
                )
            self.assertFalse((self.root / "readonly").exists())
        self.assertFalse(manager.active)


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
