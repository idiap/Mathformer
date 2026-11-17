#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - bootstrap the repository and Lunar environments first
"""Deterministic file fixtures exercise native steps, registered MCP and PRISM.

This workflow has no model/provider or external compiler boundary. No source
step is substituted: Lunar's actual parser, checker, compiler and runtime run.
The original entrypoint is retained as an independent behavioral oracle.
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
from contextlib import redirect_stdout, redirect_stderr, contextmanager
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
import physics_ir as native
from libraries.MathformerPhysicsLib.physics_ir import Quantity, Obligation
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_ir_build_workflow/workflow.yaml"


def original():
    path = ROOT / "tests/mcp/fixtures/physics_ir_original.py.txt"
    spec = importlib.util.spec_from_loader(
        "_physics_ir_original", SourceFileLoader("_physics_ir_original", str(path))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def cwd(path):
    before = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(before)


def cli(module, root, argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with (
        cwd(root),
        patch.object(sys, "argv", ["physics_ir.py", *argv]),
        redirect_stdout(stdout),
        redirect_stderr(stderr),
    ):
        try:
            code = module.main()
        except SystemExit as error:
            code = error.code
    return {"stdout": stdout.getvalue(), "exit_code": code}, stderr.getvalue()


def fixture_record():
    return {
        "case_id": "fixture",
        "statement_nl": "A source statement",
        "statement_latex": "x=y",
        "target": "target",
        "source_anchors": ["source:1", ""],
        "quantities": {"z": ["distance", "L", "m"], "a": ["time", "T", "s"]},
        "assumptions": ["Å " + "X" * 120, "", "same", "same"],
        "steps": [
            {"id": "first", "expression": "x=1"},
            {"claim": "y=2"},
            {"id": "third", "generated_support": True},
            {"id": "fourth", "generated": True},
        ],
        "obligations": [{"id": "ignored"}],
        "projection_bridges": [{"id": "bridge", "source": "source", "target": "lean"}],
        "frame": {"name": "inertial"},
        "regimes": ["classical"],
        "laws": ["law:1"],
    }


def snapshot(document):
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


class PhysicsIRTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="physics-ir-fixture-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source.json"
        self.context = {
            "working_directory": str(self.root),
            "allow_mutating": True,
            "program_name": "physics_ir.py",
        }
        self.oracle = original()

    def save(self, record):
        self.source.write_text(json.dumps(record), encoding="utf-8")

    def test_original_cli_and_native_collection_semantics(self):
        records = [
            fixture_record(),
            {},
            {"steps": [], "obligations": [{"claim": "fallback"}]},
            {
                "quantities": {"a": [], "z": ["z"]},
                "steps": [{"id": "duplicate"}, {"id": "duplicate"}],
            },
        ]
        for record in records:
            self.save(record)
            for extra in (
                [],
                ["--output", "nested/report.json"],
                ["--output", "nested/report.json", "--json"],
            ):
                argv = ["--source-record", "source.json", *extra]
                expected = cli(self.oracle, self.root, argv)
                written = (
                    (self.root / "nested/report.json").read_bytes() if extra else None
                )
                self.assertEqual(cli(native, self.root, argv), expected)
                if extra:
                    self.assertEqual(
                        (self.root / "nested/report.json").read_bytes(), written
                    )
        for argv in (["--help"], [], ["--bad"], ["--source-record"]):
            self.assertEqual(
                cli(native, self.root, argv), cli(self.oracle, self.root, argv)
            )
        for payload, error in [
            (b"{", json.JSONDecodeError),
            (b"\xff", UnicodeDecodeError),
            (b"[]", AttributeError),
            (b'{"steps":[null]}', AttributeError),
            (b'{"quantities":[1]}', AttributeError),
        ]:
            self.source.write_bytes(payload)
            for module in (native, self.oracle):
                with self.assertRaises(error):
                    cli(
                        module,
                        self.root,
                        [
                            "--source-record",
                            "source.json",
                            "--output",
                            "never/report.json",
                        ],
                    )
            self.assertFalse((self.root / "never").exists())
        self.source.unlink()
        for module in (native, self.oracle):
            with self.assertRaises(FileNotFoundError):
                cli(module, self.root, ["--source-record", "source.json"])
        record = fixture_record()
        self.save(record)
        with cwd(self.root):
            ir = native.convert_request(
                native.load_request(["--source-record", "source.json"])
            )
        self.assertEqual([q.quantity_id for q in ir.quantities], ["a", "z"])
        self.assertEqual(
            [o.depends_on for o in ir.obligations], [(), ("first",), (), ("third",)]
        )
        self.assertEqual(ir.obligations[1].obligation_id, "obligation_002")
        self.assertEqual(len(ir.assumptions[0].assumption_id.split("_", 2)[2]), 80)
        self.assertEqual(ir.projection_bridges[0].target_surface, "lean")
        self.assertEqual(ir.target_claim, "target")
        self.assertEqual(
            native.ir_from_dict(json.loads(json.dumps(ir.to_dict()))).ir_digest,
            ir.ir_digest,
        )
        # Full accumulated errors, including the final dependency, without early stop.
        broken = replace(
            ir,
            schema_version=9,
            case_id="",
            source_digest="",
            quantities=(
                Quantity("q", "q", "unknown", "m"),
                Quantity("q", "q", "L", "unknown"),
            ),
            obligations=(
                Obligation("o", "step", "", depends_on=("z",)),
                Obligation("o", "step", "", depends_on=("a",)),
            ),
        )
        errors = native.validate_ir(broken)
        self.assertEqual(len(errors), 9)
        self.assertEqual(errors[-1], "obligation o has unknown dependencies: ['a']")

    def test_registered_mcp_and_real_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_physics_ir_build_workflow")
        self.assertEqual(document["aliases"], ["physics:ir-build"])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 6},
        )
        self.assertIn(
            "scripts/physics_ir.py",
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
            "physics-ir", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                assets = snapshot(doc)
                result = compile_workflow(
                    "mcp:physics-ir",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    inventory,
                )
                return result, assets

            compiled, assets = compile(document)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            for operation in document["operations"].values():
                target = operation["execution"]["binding"]["target"]
                self.assertFalse(
                    compile(document, [t for t in tools if t["name"] != target])[0][
                        "runnable"
                    ]
                )

            async def authorize():
                pass

            async def run(extra=(), doc=document, context=None, argv=None):
                c, a = (compiled, assets) if doc is document else compile(doc)
                return await execute(
                    c,
                    a,
                    {
                        "argv": (
                            ["--source-record", "source.json", *extra]
                            if argv is None
                            else argv
                        ),
                        "context": self.context if context is None else context,
                    },
                    remote,
                    authorize,
                )

            names = ["load", "convert", "validate", "package"]
            records = [
                fixture_record(),
                {},
                {"steps": [], "obligations": [{"id": "fallback"}]},
                {
                    "quantities": {"a": [], "z": ["z"]},
                    "steps": [{"id": "dup"}, {"id": "dup"}],
                },
            ]
            for index, record in enumerate(records):
                self.save(record)
                for extra in (
                    [],
                    ["--output", "written/report.json"],
                    ["--output", "written/report.json", "--json"],
                ):
                    expected, _ = cli(
                        self.oracle,
                        self.root,
                        ["--source-record", "source.json", *extra],
                    )
                    report = (
                        json.loads(expected["stdout"])
                        if not extra or "--json" in extra
                        else json.loads((self.root / extra[1]).read_text())
                    )
                    written = (self.root / extra[1]).read_bytes() if extra else None
                    if extra:
                        (self.root / extra[1]).write_text("stale")
                    result = await run(extra)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"], {"report": report, "completion": expected}
                    )
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            "mathformer_physics_ir_" + s
                            for s in names + (["write"] if extra else []) + ["emit"]
                        ],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    if extra:
                        self.assertEqual((self.root / extra[1]).read_bytes(), written)
                    if index == 1:
                        self.assertTrue(report["ok"])
                        self.assertEqual(report["artifact_status"], "blocked")
                        self.assertEqual(
                            report["blockers"], ["no_derivation_obligations"]
                        )
                    if index == 3:
                        self.assertEqual(expected["exit_code"], 3)
                        self.assertEqual(len(report["blockers"]), 3)
            # No graph-imposed truncation: all native input elements are consumed.
            many = {
                "steps": [{"id": f"s{i}"} for i in range(1031)],
                "assumptions": ["x" * 81] * 113,
            }
            self.save(many)
            result = await run()
            self.assertEqual(result["status"], "accepted", result)
            ir = result["outputs"]["report"]["physics_ir"]
            self.assertEqual(len(ir["obligations"]), 1031)
            self.assertEqual(ir["obligations"][-1]["depends_on"], ["s1029"])
            self.assertEqual(len(ir["assumptions"]), 113)
            # Direct registered validation also preserves accumulation for malformed IR.
            ir["schema_version"] = 4
            ir["obligations"][-1]["depends_on"] = ["unknown"]
            checked = await remote.call("mathformer_physics_ir_validate", {"ir": ir})
            self.assertEqual(
                checked["errors"],
                [
                    "unsupported schema_version: 4",
                    "obligation s1030 has unknown dependencies: ['unknown']",
                ],
            )
            self.source.unlink()
            help_result = await run(argv=["--help"])
            self.assertEqual(help_result["status"], "accepted", help_result)
            self.assertEqual(
                help_result["outputs"],
                {
                    "report": None,
                    "completion": cli(self.oracle, self.root, ["--help"])[0],
                },
            )
            self.assertEqual(len(help_result["calls"]), 2)
            for argv in ([], ["--bad"], ["--source-record", "missing.json"]):
                failed = await run(argv=argv)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(failed["calls"]), 1)
            for content, count in [
                (b"{", 1),
                (b"\xff", 1),
                (b"[]", 1),
                (b'{"steps":[null]}', 2),
                (b'{"quantities":[1]}', 2),
            ]:
                self.source.write_bytes(content)
                failed = await run(["--output", "never/report.json"])
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(failed["calls"]), count)
                self.assertIsNone(failed["outputs"])
                self.assertEqual(failed["calls"][-1]["status"], "rejected")
                self.assertTrue(failed["calls"][-1]["transport_call_performed"])
                self.assertFalse((self.root / "never").exists())
            self.save(fixture_record())
            denied = dict(self.context, allow_mutating=False)
            self.assertEqual((await run(context=denied))["status"], "accepted")
            (self.root / "blocker").write_text("file")
            (self.root / "directory").mkdir()
            for path, context in [
                ("denied/report.json", denied),
                ("blocker/nested/report.json", self.context),
                ("directory", self.context),
                (str(self.root.parent / "outside.json"), self.context),
            ]:
                failed = await run(["--output", path], context=context)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(len(failed["calls"]), 5)
                self.assertEqual(
                    failed["calls"][-1]["tool"], "mathformer_physics_ir_write"
                )
            self.assertFalse((self.root / "denied").exists())
            # Actual source write errors match original stopping before stdout.
            for module in (native, self.oracle):
                with self.assertRaises(FileExistsError):
                    cli(
                        module,
                        self.root,
                        [
                            "--source-record",
                            "source.json",
                            "--output",
                            "blocker/report.json",
                        ],
                    )
            bounded = deepcopy(document)
            bounded["policy"]["limits"]["max_operation_calls"] = 2
            failed = await run(["--output", "budget/report.json"], doc=bounded)
            self.assertEqual(failed["status"], "failed", failed)
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in failed["calls"]), 2
            )
            self.assertIn("budget", str(failed).lower())
            self.assertFalse((self.root / "budget").exists())
            timed = deepcopy(document)
            timed["policy"]["limits"]["wall_time_seconds"] = 1
            c, a = compile(timed)

            async def pending():
                await asyncio.Event().wait()

            with self.assertRaises(TimeoutError):
                await execute(
                    c, a, {"argv": ["--help"], "context": self.context}, remote, pending
                )
        self.assertFalse(manager.active)
        config.args.append("--readonly")
        async with manager.open(
            "physics-ir-readonly", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
        ) as remote:
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    "mathformer_physics_ir_write",
                    {
                        "request": {"output": "readonly/report.json"},
                        "report": {},
                        "context": self.context,
                    },
                )
            self.assertFalse((self.root / "readonly").exists())
        self.assertFalse(manager.active)


if __name__ == "__main__":
    if "--server" in sys.argv:
        from mcp_server import mcp
        import mcp_server

        mcp_server._ALLOWED_WRITE_ROOTS = [
            Path(sys.argv[sys.argv.index("--server") + 1]).resolve()
        ]
        mcp_server._READONLY = "--readonly" in sys.argv
        mcp.run(transport="stdio")
    else:
        unittest.main(verbosity=2)
