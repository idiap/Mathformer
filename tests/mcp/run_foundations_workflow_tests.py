#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Exercise native stages, registered tools, Lunar compilation and PRISM runtime.

Run with LUNAR_PLATFORM_ROOT and WORKFLOW_CONTRACT_PATH. All native programs
and foundation inputs are mounted in a temporary repository. Only Lake is
substituted, in a test-only sitecustomize loaded by the verifier subprocess.
No model/provider participates in this native workflow.
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
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
import yaml
from foundations_workflow_tools import source, native_paths
from mcp_connections.client import SessionManager, MCPConnectionError, json_content
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_foundation_formalization_loop_workflow/workflow.yaml"
CONTRACT_ID = "hub_physics_lean_foundation_formalization_loop_workflow"
EMIT_TOOL = "mathformer_foundations_emit"
JSON_PORT = "json"
SELECTED = "tests/physics_lean/run_foundations_workflow.py"
FIXTURES = ROOT / "tests/mcp/fixtures"
CHILDREN = [
    "skills/physics-common/physics-foundation-object-intake/scripts/intake_physics_foundation_objects.py",
    "skills/mathformerphysicslib/mathformerphysicslib-foundation-surface-designer/scripts/design_foundation_surfaces.py",
    "skills/mathformerphysicslib/mathformerphysicslib-foundation-drafter/scripts/draft_foundation_modules.py",
    "skills/mathformerphysicslib/mathformerphysicslib-foundation-verifier/scripts/verify_foundation_modules.py",
    "skills/mathformerphysicslib/mathformerphysicslib-object-workbench/scripts/build_mathformerphysicslib_object_workbench.py",
]
LIBRARY = "MathformerPhysicsLib/Lean"


def copy_file(source_path, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, target)


def fixture(root):
    for relative in CHILDREN + [SELECTED]:
        copy_file(ROOT / relative, root / relative)
    # Native verifier/workbench still read this legacy source-owned mount.
    for path in (ROOT / "libraries" / LIBRARY / "Foundations").glob("*.lean"):
        copy_file(path, root / LIBRARY / "Foundations" / path.name)
    copy_file(
        ROOT / "libraries" / LIBRARY / "Foundations.lean",
        root / LIBRARY / "Foundations.lean",
    )


def environment(root):
    return {
        "PATH": os.defpath,
        "PYTHONPATH": str(FIXTURES / "foundations_compiler"),
        "FOUNDATIONS_FIXTURE_ROOT": str(root),
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def artifacts(root):
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in (root / "artifacts").rglob("*")
        if p.is_file()
    }


def clear_artifacts(root):
    shutil.rmtree(root / "artifacts", ignore_errors=True)
    (root / "compiler_calls.jsonl").unlink(missing_ok=True)


def lean_files(root):
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in (root / LIBRARY).rglob("*.lean")
    }


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(row["path"], (ROOT / row["path"]).read_text())
        for row in document["provenance"]["sources"]
    ]


def entrypoint(root, original=False, json_output=True):
    copy_file(
        (
            FIXTURES / "foundations_workflow_original.py.txt"
            if original
            else ROOT / SELECTED
        ),
        root / SELECTED,
    )
    return subprocess.run(
        [sys.executable, str(root / SELECTED)] + (["--json"] if json_output else []),
        cwd=root,
        env=environment(root),
        text=True,
        capture_output=True,
        check=False,
    )


@asynccontextmanager
async def diagnosed_session(manager, *args):
    async with manager.open(*args) as remote:
        try:
            yield remote
        except Exception:
            import traceback

            traceback.print_exc()
            raise


class FoundationsTests(unittest.TestCase):
    def test_fixed_iterator_and_json_failures(self):
        state = {"argv": ["prefix"], "cursor": 0}
        for index, concept in enumerate(source.CONCEPTS):
            before = deepcopy(state)
            advanced = source.append_concept(state)
            self.assertEqual(state, before)
            self.assertEqual(advanced["state"]["cursor"], index + 1)
            self.assertEqual(
                advanced["state"]["argv"], before["argv"] + ["--concept", concept]
            )
            self.assertEqual(advanced["done"], index == 15)
            state = advanced["state"]
        self.assertEqual(len(source.CONCEPTS), 16)
        for cursor in (-1, 16, 17):
            with self.assertRaises(ValueError):
                source.append_concept({"argv": [], "cursor": cursor})
        # Real subprocess parsing and error propagation; neither is a mocked stage.
        with self.assertRaises(json.JSONDecodeError):
            source.run_json("-c", "print('invalid JSON')")
        with self.assertRaisesRegex(RuntimeError, "STDERR:\ncompiler-like failure"):
            source.run_json(
                "-c",
                "import sys; print('partial'); print('compiler-like failure',file=sys.stderr); sys.exit(7)",
            )
        with self.assertRaises(KeyError):
            source.evaluate({}, {}, {}, {}, {}, {})

    def test_original_cli_equivalence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            lean_before = lean_files(root)
            # Success, final false check, structural failure, external compiler failure.
            for mode in ("success", "no_reuse", "banned", "compiler_failure"):
                with self.subTest(mode=mode):
                    fixture(root)
                    if mode == "no_reuse":
                        shutil.rmtree(root / LIBRARY)
                        path = root / LIBRARY / "Foundations/Minimal.lean"
                        path.parent.mkdir(parents=True)
                        path.write_text(
                            "/-- Mathlib grounding: deterministic fixture. -/\ndef n : Nat := 0\n"
                        )
                    if mode == "banned":
                        with (root / LIBRARY / "Foundations/Carriers.lean").open(
                            "a"
                        ) as stream:
                            stream.write("\naxiom bad : False\n")
                    (root / "compiler_code").write_text(
                        "9" if mode == "compiler_failure" else "0"
                    )
                    mounted_lean = lean_files(root)
                    for json_output in (True, False):
                        outcomes = []
                        for original in (True, False):
                            clear_artifacts(root)
                            proc = entrypoint(root, original, json_output)
                            outcomes.append(
                                (proc.returncode, proc.stdout, artifacts(root))
                            )
                            self.assertEqual(lean_files(root), mounted_lean)
                            self.assertEqual(
                                len(
                                    (root / "compiler_calls.jsonl")
                                    .read_text()
                                    .splitlines()
                                ),
                                1,
                            )
                            if mode in ("banned", "compiler_failure"):
                                self.assertIn("command failed:", proc.stderr)
                                self.assertIn("verification_report.json", proc.stderr)
                                self.assertFalse(
                                    Path(native_paths(root)["workbench"]).exists()
                                )
                        self.assertEqual(outcomes[0], outcomes[1])
                        self.assertEqual(
                            outcomes[1][0],
                            0 if mode == "success" else 1,
                            outcomes[1][1],
                        )
                        if mode in ("success", "no_reuse") and json_output:
                            result = json.loads(outcomes[1][1])
                            self.assertEqual(result["ok"], mode == "success")
                            self.assertEqual(len(result["checks"]), 9)
                            self.assertEqual(
                                result["checks"]["workbench_reuses_foundations"],
                                mode == "success",
                            )
                    # Reinstall valid read-only fixture files for the next case.
                    shutil.rmtree(root / LIBRARY)
            fixture(root)
            self.assertEqual(lean_files(root), lean_before)

    def test_registered_lunar_prism_workflow(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], CONTRACT_ID)
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 24},
        )
        self.assertIn(SELECTED, [s["path"] for s in document["provenance"]["sources"]])
        if CONTRACT_ID.startswith("route_"):
            self.assertEqual(
                document["aliases"], ["formalize.physics.lean.foundations"]
            )
            self.assertEqual(set(document["inputs"]), {"context"})
            self.assertEqual(
                document["flow"]["steps"][-1]["arguments"]["json_mode"],
                {"literal": True},
            )
            self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 16)
            self.assertEqual(document["flow"]["steps"][1]["on_exhausted"], "fail")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        spec = importlib.util.spec_from_file_location(
            "foundations_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        authored = (
            normalizer.foundations_route_descriptor()
            if CONTRACT_ID.startswith("route_")
            else next(d for d in normalizer.inventory() if d["id"] == document["id"])
        )
        self.assertEqual(authored, document)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "mount"
            root.mkdir()
            fixture(root)
            manager = SessionManager()
            config = StdioConfig(
                command=sys.executable,
                args=[str(Path(__file__).resolve()), "--serve", str(root)],
                cwd=str(ROOT),
            )
            async with diagnosed_session(
                manager,
                "foundations",
                config,
                {"LUNAR_PLATFORM_ROOT": str(LUNAR), **environment(root)},
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, advertised=tools):
                    assets = snapshot(doc)
                    compiled = compile_workflow(
                        "mcp:foundations",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        advertised,
                    )
                    return compiled, assets

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(
                    compile(
                        document,
                        [
                            t
                            for t in tools
                            if t["name"] != "mathformer_foundations_verify"
                        ],
                    )[0]["runnable"]
                )

                async def authorize():
                    pass

                async def run(json_output=True, allow=True, doc=document):
                    selected, received = (
                        (compiled, assets) if doc is document else compile(doc)
                    )
                    self.assertTrue(selected["runnable"], selected["diagnostics"])
                    inputs = {
                        "context": {
                            "repository_root": str(root),
                            "allow_mutating": allow,
                        }
                    }
                    if "json" in doc["inputs"]:
                        inputs["json"] = json_output
                    return await execute(selected, received, inputs, remote, authorize)

                def names(result):
                    return [
                        c.get("tool", "")
                        .removeprefix("mathformer_foundations_")
                        .removesuffix("_native")
                        for c in result["calls"]
                    ]

                lean_before = lean_files(root)
                for json_output in (
                    (True, False) if "json" in document["inputs"] else (True,)
                ):
                    clear_artifacts(root)
                    expected = entrypoint(root, original=True, json_output=json_output)
                    self.assertEqual(expected.returncode, 0, expected.stderr)
                    expected_files = artifacts(root)
                    clear_artifacts(root)
                    result = await run(json_output)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["exit_code"], 0)
                    self.assertEqual(result["outputs"]["stdout"], expected.stdout)
                    self.assertEqual(artifacts(root), expected_files)
                    self.assertEqual(
                        names(result),
                        [
                            "prepare",
                            *(["append_concept"] * 16),
                            "intake",
                            "surface",
                            "draft",
                            "verify",
                            "workbench",
                            "evaluate",
                            "emit",
                        ],
                    )
                    self.assertEqual(len(result["calls"]), 24)
                    self.assertTrue(result["outputs"]["result"]["ok"])
                    self.assertEqual(len(result["outputs"]["result"]["checks"]), 9)
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["replay_artifacts"])
                    self.assertEqual(lean_files(root), lean_before)
                    reports = {
                        key: json.loads(Path(path).read_text())
                        for key, path in native_paths(root).items()
                    }
                    self.assertEqual(
                        reports["draft_report"]["terminal_state"], "draft_preview"
                    )
                    self.assertFalse(reports["draft_report"]["write"])
                    modules = reports["draft_report"]["modules"]
                    self.assertEqual(
                        [i["module"] for i in modules],
                        sorted(
                            {
                                s["foundation_module"]
                                for s in reports["surface_plan"]["surfaces"]
                            }
                        ),
                    )
                    # Exercise the actual child's finite iterator and serialized history.
                    draft_spec = importlib.util.spec_from_file_location(
                        "mounted_drafter", root / CHILDREN[2]
                    )
                    drafter = importlib.util.module_from_spec(draft_spec)
                    draft_spec.loader.exec_module(drafter)
                    request = {"plan": reports["surface_plan"], "write": False}
                    history = drafter.initialize_draft(request)
                    for cursor in range(len(modules)):
                        next_item = drafter.draft_next(request, history, root)
                        self.assertEqual(next_item["done"], cursor == len(modules) - 1)
                        history = next_item["state"]
                        self.assertEqual(history["cursor"], cursor + 1)
                        self.assertEqual(
                            [json.loads(i) for i in history["item_history"]],
                            history["items"],
                        )
                    self.assertEqual(
                        drafter.finish_draft(request, history, repository_root=root),
                        reports["draft_report"],
                    )
                    self.assertEqual(
                        reports["draft_report"]["source_surface_plan"],
                        reports["intake"]["packet_id"],
                    )
                    self.assertEqual(
                        reports["surface_plan"]["source_packet_id"],
                        reports["intake"]["packet_id"],
                    )
                    self.assertEqual(
                        reports["verification_report"]["module_count"],
                        len(lean_before) - 1,
                    )
                    self.assertEqual(
                        len((root / "compiler_calls.jsonl").read_text().splitlines()), 1
                    )
                    # Each final check is independently observable; recursive metadata
                    # changes a verdict, never the execution schedule.
                    mutations = [
                        ("intake_has_priority_1", "intake", "object_count", 0),
                        ("intake_has_hilbert_surfaces", "intake", "objects", []),
                        (
                            "surface_plan_complete",
                            "surface",
                            "terminal_state",
                            "incomplete",
                        ),
                        (
                            "surface_plan_has_hilbert_module",
                            "surface",
                            "accepted_index_imports",
                            [],
                        ),
                        (
                            "surface_plan_is_recursive",
                            "surface",
                            "recursive_policy",
                            {
                                "recursive": False,
                                "initial_surfaces_are_level_0_not_terminal_theory": True,
                            },
                        ),
                        (
                            "hilbert_recursive_frontier_present",
                            "surface",
                            "recursive_frontier",
                            [],
                        ),
                        ("draft_preview_only", "draft", "terminal_state", "other"),
                        ("verification_passed", "verify", "ok", False),
                        ("workbench_reuses_foundations", "workbench", "reuse_count", 0),
                    ]
                    actual = dict(
                        intake=reports["intake"],
                        surface=reports["surface_plan"],
                        draft=reports["draft_report"],
                        verify=reports["verification_report"],
                        workbench=reports["workbench"],
                    )
                    for check, port, key, value in mutations:
                        changed = deepcopy(actual)
                        changed[port][key] = value
                        raw = await remote.session.call_tool(
                            "mathformer_foundations_evaluate",
                            {
                                "paths": native_paths(root),
                                **changed,
                                "context": {
                                    "repository_root": str(root),
                                    "allow_mutating": False,
                                },
                            },
                        )
                        self.assertFalse(raw.isError, raw)
                        evaluated = json_content(raw)
                        self.assertEqual(
                            evaluated["result"]["checks"],
                            {
                                name: name != check
                                for name in result["outputs"]["result"]["checks"]
                            },
                        )
                        self.assertFalse(evaluated["result"]["ok"])
                        for mode in (True, False):
                            emitted = await remote.call(
                                EMIT_TOOL, {**evaluated, JSON_PORT: mode}
                            )
                            self.assertEqual(emitted["exit_code"], 1)
                            if mode:
                                self.assertEqual(
                                    json.loads(emitted["stdout"]), evaluated["result"]
                                )
                            else:
                                self.assertEqual(
                                    emitted["stdout"],
                                    "MathformerPhysicsLib foundations workflow: failed\n",
                                )
                            if EMIT_TOOL != "mathformer_foundations_emit":
                                legacy = await remote.call(
                                    "mathformer_foundations_emit",
                                    {**evaluated, "json": mode},
                                )
                                self.assertEqual(legacy, emitted)
                # Native JSON ports expose the full fixed argv traversal, no caller concepts.
                prepared = await remote.call(
                    "mathformer_foundations_prepare",
                    {"context": {"repository_root": str(root), "allow_mutating": True}},
                )
                state = prepared["state"]
                for i in range(16):
                    advanced = await remote.call(
                        "mathformer_foundations_append_concept", {"state": state}
                    )
                    self.assertEqual(advanced["done"], i == 15)
                    self.assertEqual(advanced["state"]["cursor"], i + 1)
                    state = advanced["state"]
                self.assertEqual(
                    state["argv"][6:],
                    [part for c in source.CONCEPTS for part in ("--concept", c)],
                )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_foundations_append_concept", {"state": state}
                    )
                corrupted = deepcopy(state)
                corrupted["argv"][0] = "-c"
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_foundations_intake",
                        {
                            "state": corrupted,
                            "paths": prepared["paths"],
                            "context": {
                                "repository_root": str(root),
                                "allow_mutating": True,
                            },
                        },
                    )
                # Malformed real file handoffs fail in their owning native children.
                packet = Path(prepared["paths"]["intake"])
                saved_packet = packet.read_text()
                packet.write_text("{")
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_foundations_surface",
                        {
                            "packet": str(packet),
                            "paths": prepared["paths"],
                            "context": {
                                "repository_root": str(root),
                                "allow_mutating": True,
                            },
                        },
                    )
                packet.write_text(saved_packet)
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        "mathformer_foundations_evaluate",
                        {
                            "paths": prepared["paths"],
                            "intake": {},
                            "surface": {},
                            "draft": {},
                            "verify": {},
                            "workbench": {},
                            "context": {
                                "repository_root": str(root),
                                "allow_mutating": True,
                            },
                        },
                    )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        EMIT_TOOL,
                        {
                            "result": {"ok": True},
                            JSON_PORT: True,
                            "rendered_result": '{"ok": false}',
                        },
                    )
                # A smaller host loop cap fails on exhaustion, before the first child.
                clear_artifacts(root)
                bounded = deepcopy(document)
                bounded["flow"]["steps"][1]["max_iterations"] = 15
                failed = await run(doc=bounded)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(names(failed), ["prepare", *(["append_concept"] * 15)])
                self.assertEqual(artifacts(root), {})
                self.assertFalse((root / "compiler_calls.jsonl").exists())
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 17
                failed = await run(doc=budget)
                self.assertEqual(failed["status"], "failed")
                self.assertIn("budget", failed["calls"][-1]["error"])
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in failed["calls"]
                    ),
                    17,
                )
                self.assertEqual(artifacts(root), {})
                # Compiler nonzero preserves partial reports, aborts before workbench, no retry.
                clear_artifacts(root)
                (root / "compiler_code").write_text("9")
                failed = await run()
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(names(failed)[-1], "verify")
                self.assertEqual(names(failed).count("verify"), 1)
                self.assertFalse(Path(native_paths(root)["workbench"]).exists())
                verification = json.loads(
                    Path(native_paths(root)["verification_report"]).read_text()
                )
                self.assertFalse(verification["ok"])
                self.assertEqual(
                    verification["accepted_index_compile"]["returncode"], 9
                )
                self.assertEqual(
                    verification["accepted_index_compile"]["stdout_tail"], "o" * 2000
                )
                self.assertEqual(
                    verification["accepted_index_compile"]["stderr_tail"], "e" * 2000
                )
                self.assertEqual(
                    len((root / "compiler_calls.jsonl").read_text().splitlines()), 1
                )
                # Failure to launch the compiler also aborts, before report emission.
                clear_artifacts(root)
                (root / "compiler_code").write_text("launch_error")
                failed = await run()
                self.assertEqual(failed["status"], "failed", failed)
                self.assertEqual(names(failed)[-1], "verify")
                self.assertEqual(names(failed).count("verify"), 1)
                self.assertFalse(
                    Path(native_paths(root)["verification_report"]).exists()
                )
                self.assertFalse(Path(native_paths(root)["workbench"]).exists())
                self.assertTrue(Path(native_paths(root)["draft_report"]).exists())
                self.assertEqual(
                    len((root / "compiler_calls.jsonl").read_text().splitlines()), 1
                )
                (root / "compiler_code").write_text("0")
                # Native failed final checks still reach emit with source exit 1.
                shutil.rmtree(root / LIBRARY)
                path = root / LIBRARY / "Foundations/Minimal.lean"
                path.parent.mkdir(parents=True)
                path.write_text(
                    "/-- Mathlib grounding: fixture. -/\ndef n : Nat := 0\n"
                )
                clear_artifacts(root)
                result = await run(False)
                self.assertEqual(result["status"], "accepted", result)
                self.assertEqual(result["outputs"]["exit_code"], 1)
                self.assertFalse(result["outputs"]["result"]["ok"])
                if "json" in document["inputs"]:
                    self.assertEqual(
                        result["outputs"]["stdout"],
                        "MathformerPhysicsLib foundations workflow: failed\n",
                    )
                else:
                    self.assertEqual(
                        json.loads(result["outputs"]["stdout"]),
                        result["outputs"]["result"],
                    )
                self.assertEqual(names(result)[-1], "emit")
                # Authorization and symlink escape rejection occur before native writes.
                clear_artifacts(root)
                failed = await run(allow=False)
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(names(failed), ["prepare"])
                self.assertFalse((root / "artifacts").exists())
                outside = base / "outside"
                outside.mkdir()
                (root / "artifacts").symlink_to(outside, target_is_directory=True)
                failed = await run()
                self.assertEqual(failed["status"], "failed")
                self.assertEqual(list(outside.iterdir()), [])
                (root / "artifacts").unlink()
                # Read-only service policy is checked in the same registration.
                from foundations_workflow_tools import (
                    register_foundations_workflow_tools,
                )
                from mcp.server.fastmcp import FastMCP

                server = FastMCP("readonly fixture")

                def deny():
                    raise ValueError("service read-only")

                register_foundations_workflow_tools(server, deny, lambda p: True)
                with self.assertRaises(Exception):
                    await server.call_tool(
                        "mathformer_foundations_prepare",
                        {
                            "context": {
                                "repository_root": str(root),
                                "allow_mutating": True,
                            }
                        },
                    )
                self.assertFalse((root / "artifacts").exists())
            self.assertFalse(manager.active)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        import mcp_server

        mcp_server.apply_runtime_config(allowed_write_roots=[sys.argv[2]])
        mcp_server.mcp.run(transport="stdio")
    else:
        if "--foundations-route" in sys.argv:
            sys.argv.remove("--foundations-route")
            DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_formalize_physics_lean_foundations_workflow/workflow.yaml"
            CONTRACT_ID = "route_formalize_physics_lean_foundations_workflow"
            EMIT_TOOL = "mathformer_foundations_emit_native"
            JSON_PORT = "json_mode"
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(FoundationsTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        raise SystemExit(
            0
            if result.wasSuccessful() and result.testsRun and not result.skipped
            else 1
        )
