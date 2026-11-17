#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402
"""Deterministic fixtures through actual MCP and Lunar/PRISM compilation/runtime.

The planner has no external model/provider or scientific compiler boundary.
None is fabricated or substituted. Tests only write disposable fixture files;
no hub workflow, theorem prover, provider, credential or promotion is invoked.
WORKFLOW_CONTRACT_PATH explicitly selects the candidate or installed contract.
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
    contextmanager,
    asynccontextmanager,
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
from foundation_surface_tools import native
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_foundation_surface_design_workflow/workflow.yaml"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/foundation-surface.workflow.json"
)
PREFIX = "mathformer_foundation_surface_"
ORIGINAL = ROOT / "tests/mcp/fixtures/foundation_surface_original.py.txt"


def original():
    assert (
        hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
        == "ac23adcb545f9336065fab38dc0651e7151c718d9bc6ab103db92289674949b0"
    )
    loader = SourceFileLoader("_surface_original", str(ORIGINAL))
    spec = importlib.util.spec_from_loader(loader.name, loader)
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
    out, err = io.StringIO(), io.StringIO()
    with (
        cwd(root),
        patch.object(sys, "argv", ["surface.py", *process_argv]),
        redirect_stdout(out),
        redirect_stderr(err),
    ):
        try:
            result = ("return", module.main(argv))
        except SystemExit as error:
            result = ("exit", error.code)
        except Exception as error:
            result = ("raise", type(error).__name__, str(error))
    return result, out.getvalue(), err.getvalue()


def fixture_packet():
    # Every known declaration/ladder, every bridge and non-bridge module,
    # unknown/falsey modules, missing/odd IDs, non-dict skipping and duplicates.
    objects = [
        dict(
            object_id=key,
            foundation_module=list(native.MODULES)[i % len(native.MODULES)],
            mathlib_search_terms={"z": "π", "a": [i]},
        )
        for i, key in enumerate(
            dict.fromkeys([*native.DECLARATIONS, *native.PROMOTION_LADDERS])
        )
    ]
    objects += [
        dict(object_id="unknown.α", foundation_module=module)
        for module in [*native.MODULES, "NoSuchModule", None, "", False, 7]
    ]
    objects += [
        None,
        "skip",
        [],
        13,
        {},
        {"object_id": None},
        {"object_id": ["odd"]},
        deepcopy(objects[0]),
    ]
    return {"packet_id": {"z": "α", "a": 3}, "objects": objects}


def snapshot(document):
    def asset(path, content):
        return dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]


@asynccontextmanager
async def diagnosed_session(manager, *args):
    async with manager.open(*args) as remote:
        try:
            yield remote
        except Exception:
            import traceback

            traceback.print_exc()
            raise


class SurfaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="foundation-surface-fixture-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.context = dict(
            working_directory=str(self.root),
            program_name="surface.py",
            allow_mutating=True,
        )
        self.oracle = original()

    def test_shared_native_steps_and_original_cli(self):
        for packet in (
            {},
            {"objects": []},
            fixture_packet(),
            {"objects": "skip"},
            {"objects": {"a": 1}},
            {"objects": [None, False, 8]},
        ):
            expected = self.oracle.build_plan(packet)
            self.assertEqual(native.build_plan(packet), expected)
            surfaces = native.design_surfaces(packet)
            modules = native.collect_modules(surfaces)
            self.assertEqual(native.assemble_plan(packet, surfaces, modules), expected)
            self.assertEqual(modules, sorted(set(s["module_path"] for s in surfaces)))
            self.assertEqual(
                expected["recursive_frontier"],
                [f for s in expected["surfaces"] for f in s["recursive_frontier"]],
            )
        for object_id in [
            *native.DECLARATIONS,
            *native.PROMOTION_LADDERS,
            "missing.α",
            None,
            19,
        ]:
            for module in [*native.MODULES, "unknown", None, False, 8]:
                item = dict(object_id=object_id, foundation_module=module)
                self.assertEqual(
                    native.design_surface(item), self.oracle.design_surface(item)
                )
        fallback = native.design_surface(
            {"object_id": "a.b", "foundation_module": "unknown"}
        )
        self.assertEqual(fallback["module_path"], native.MODULES["Contexts"])
        self.assertEqual(fallback["state"], "mathlib_reused")
        self.assertEqual(fallback["declarations"], ["a_b"])
        self.assertEqual(native.design_surface({})["state"], "candidate_generated")
        for packet in ([], None, 4, {"objects": None}, {"objects": 4}):

            def outcome(module):
                try:
                    return module.build_plan(packet)
                except Exception as error:
                    return type(error), str(error)

            self.assertEqual(outcome(native), outcome(self.oracle))
        (self.root / "packet.json").write_text(
            json.dumps(fixture_packet(), ensure_ascii=False)
        )
        (self.root / "bad.json").write_text("{")
        (self.root / "blocker").write_text("file")
        (self.root / "directory").mkdir()
        cases = [
            [],
            ["--help"],
            ["--bad"],
            ["--object-packet"],
            ["--self-test", "--object-packet", "missing"],
            ["--object-packet", "packet.json"],
            ["--object-packet", "missing"],
            ["--object-packet", "bad.json"],
            ["--output", "blocker/out.json"],
            ["--output", "directory"],
        ]
        cases += [
            ["--object-packet", "packet.json", "--output", "nested/plan.json", *flags]
            for flags in ([], ["--json"])
        ]
        for argv in cases:
            expected = cli(self.oracle, self.root, argv)
            written = (
                (self.root / "nested/plan.json").read_bytes()
                if "nested/plan.json" in argv
                else None
            )
            self.assertEqual(cli(native, self.root, argv), expected)
            if written is not None:
                self.assertEqual((self.root / "nested/plan.json").read_bytes(), written)
        self.assertEqual(
            cli(native, self.root, None, ["--self-test"]),
            cli(self.oracle, self.root, None, ["--self-test"]),
        )
        # Source assertions remain before serialization and file creation.
        args = native.parse_args(["--self-test"])
        plan = native.build_plan(native.fixed_packet())
        for mutate in (
            lambda p: p.update(surface_count=0),
            lambda p: p["surfaces"][0].update(module_path="wrong"),
            lambda p: p["recursive_policy"].update(recursive=False),
            lambda p: p.update(recursive_frontier_count=0),
        ):
            wrong = deepcopy(plan)
            mutate(wrong)
            with self.assertRaises(AssertionError):
                native.check_self_test(args, wrong)

        # Write has already happened if the later print fails (native ordering).
        class BrokenStream:
            def write(self, text):
                raise OSError("stdout fixture failure")

        args = native.parse_args(
            ["--output", str(self.root / "before-print.json"), "--json"]
        )
        with redirect_stdout(BrokenStream()), self.assertRaises(OSError):
            native.emit_plan(args, plan)
        self.assertEqual(
            json.loads((self.root / "before-print.json").read_text()), plan
        )

    def test_native_registry_service_inventory_and_generator(self):
        import mathformer
        from mathformer_mcp_service import service_coverage_report

        action = mathformer.build_registry()["physics-lean:foundation-surface-design"]
        self.assertFalse(action.depends_on)
        self.assertIsNone(action.timeout_seconds)
        self.assertEqual(
            action.command[-1],
            "skills/mathformerphysicslib/mathformerphysicslib-foundation-surface-designer/scripts/design_foundation_surfaces.py",
        )
        document = json.loads(AUTHORED.read_text())
        report = service_coverage_report(self.root / "unused.toml", {})
        for operation in document["operations"].values():
            self.assertIn(
                operation["execution"]["binding"]["target"], report["mcp_tools"]
            )
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("_surface_normalizer", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        generated = [d for d in module.inventory() if d["id"] == document["id"]]
        self.assertEqual(generated, [document])
        # Read-only audit may report unrelated pre-existing entries; our new
        # adapter and test must participate in the native control boundary.
        uncontrolled = mathformer.audit_control(mathformer.build_registry())[
            "uncontrolled_entrypoints"
        ]
        self.assertNotIn("scripts/foundation_surface_tools.py", uncontrolled)
        self.assertNotIn(
            "tests/mcp/run_foundation_surface_workflow_tests.py", uncontrolled
        )

    def test_registered_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(
            document["id"], "hub_physics_lean_foundation_surface_design_workflow"
        )
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            dict(wall_time_seconds=3600, max_operation_calls=7),
        )
        self.assertIn(
            "skills/mathformerphysicslib/mathformerphysicslib-foundation-surface-designer/scripts/design_foundation_surfaces.py",
            [s["path"] for s in document["provenance"]["sources"]],
        )
        for source in document["provenance"]["sources"]:
            self.assertEqual(
                source["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / source["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(json.loads(AUTHORED.read_text()), document)
        manager = SessionManager()
        config = StdioConfig(
            command=sys.executable,
            args=[str(Path(__file__).resolve()), "--server", str(self.root)],
            cwd=str(ROOT),
        )
        async with diagnosed_session(
            manager, "foundation-surface", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
        ) as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=tools):
                assets = snapshot(doc)
                return (
                    compile_workflow(
                        "mcp:foundation-surface",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory,
                    ),
                    assets,
                )

            compiled, assets = compile(document)
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
                c, a = (compiled, assets) if doc is document else compile(doc)
                self.assertTrue(c["runnable"], c["diagnostics"])
                return await execute(
                    c,
                    a,
                    dict(
                        argv=list(argv),
                        context=self.context if context is None else context,
                    ),
                    remote,
                    authorize,
                )

            def names(result):
                return [c["tool"].removeprefix(PREFIX) for c in result["calls"]]

            (self.root / "packet.json").write_text(
                json.dumps(fixture_packet(), ensure_ascii=False)
            )
            (self.root / "empty.json").write_text('{"objects":[null,4,"skip"]}')
            for argv in (
                [],
                ["--json"],
                ["--self-test", "--object-packet", "missing"],
                ["--object-packet", "packet.json"],
                ["--object-packet", "empty.json"],
            ):
                for flags in (
                    [],
                    ["--output", "artifacts/plan.json"],
                    ["--output", "artifacts/plan.json", "--json"],
                ):
                    args = argv + flags
                    expected, stdout, stderr = cli(self.oracle, self.root, args)
                    self.assertEqual(expected, ("return", 0))
                    self.assertEqual(stderr, "")
                    path = self.root / "artifacts/plan.json"
                    text = path.read_text()[:-1] if "--output" in flags else stdout[:-1]
                    expected_plan = json.loads(text)
                    if flags:
                        path.write_text("stale")
                    result = await run(args)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(
                        result["outputs"],
                        dict(
                            plan=expected_plan,
                            json_text=text,
                            exit_code=0,
                            stdout=stdout,
                        ),
                    )
                    self.assertEqual(
                        names(result),
                        [
                            "parse",
                            "fixture" if "--self-test" in argv else "load",
                            "design",
                            "modules",
                            "assemble",
                            "check_self_test",
                            "emit",
                        ],
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    if flags:
                        self.assertEqual(path.read_text(), text + "\n")
            # No artificial object cap: a large finite traversal completes exactly once.
            many = {
                "packet_id": "large",
                "objects": [
                    dict(object_id="unknown", foundation_module="Fields")
                    for _ in range(1031)
                ],
            }
            (self.root / "many.json").write_text(json.dumps(many))
            result = await run(
                ["--object-packet", "many.json", "--output", "many-plan.json"]
            )
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(result["outputs"]["plan"], self.oracle.build_plan(many))
            self.assertEqual(result["outputs"]["plan"]["surface_count"], 1031)
            self.assertEqual(len(result["calls"]), 7)
            # Help exits successfully before loading nonexistent inputs or writing.
            expected, stdout, _ = cli(self.oracle, self.root, ["--help"])
            result = await run(
                [
                    "--help",
                    "--object-packet",
                    "missing",
                    "--output",
                    "never-help/out.json",
                ]
            )
            self.assertEqual(result["status"], "accepted", result)
            self.assertEqual(names(result), ["parse", "help"])
            self.assertEqual(
                result["outputs"],
                dict(plan=None, json_text="", exit_code=0, stdout=stdout),
            )
            self.assertFalse((self.root / "never-help").exists())
            for argv, count in (
                (["--bad"], 1),
                (["--object-packet"], 1),
                (["--object-packet", "missing"], 2),
            ):
                result = await run(argv)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), count)
                self.assertIsNone(result["outputs"])
            for payload, count in (
                (b"{", 2),
                (b"\xff", 2),
                (b"[]", 3),
                (b"null", 3),
                (b"3", 3),
                (b'{"objects":null}', 3),
                (b'{"objects":4}', 3),
            ):
                (self.root / "bad.json").write_bytes(payload)
                result = await run(
                    ["--object-packet", "bad.json", "--output", "never-bad/out.json"]
                )
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), count)
                self.assertEqual(result["calls"][-1]["status"], "rejected")
                self.assertFalse((self.root / "never-bad").exists())
            denied = dict(self.context, allow_mutating=False)
            self.assertEqual((await run(context=denied))["status"], "accepted")
            (self.root / "blocker").write_text("file")
            (self.root / "directory").mkdir()
            for path, ctx in (
                ("denied/out.json", denied),
                ("blocker/out.json", self.context),
                ("directory", self.context),
                (str(self.root.parent / "outside-surface.json"), self.context),
            ):
                result = await run(["--output", path], context=ctx)
                self.assertEqual(result["status"], "failed", result)
                self.assertEqual(len(result["calls"]), 7)
                self.assertEqual(names(result)[-1], "emit")
            self.assertFalse((self.root / "denied").exists())
            # Native self-test assertion failure through the registered tool.
            plan = native.build_plan({})
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "check_self_test",
                    dict(
                        args=dict(self_test=True), plan=plan, plan_json=json.dumps(plan)
                    ),
                )
            # JSON companions are verified, never used as unchecked alternative state.
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "design", dict(packet={}, packet_json='{"objects":[{}]}')
                )
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
                    c, a, dict(argv=[], context=self.context), remote, pending
                )
        self.assertFalse(manager.active)
        config.args.append("--readonly")
        async with diagnosed_session(
            manager, "surface-readonly", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
        ) as remote:
            plan = native.build_plan({})
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "emit",
                    dict(
                        args=dict(output="readonly/out.json", json=False),
                        plan=plan,
                        plan_json=json.dumps(plan),
                        context=self.context,
                    ),
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
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(SurfaceTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        sys.exit(
            0
            if result.wasSuccessful() and result.testsRun and not result.skipped
            else 1
        )
