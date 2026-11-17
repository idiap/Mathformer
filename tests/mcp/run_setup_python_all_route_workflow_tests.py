#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real MCP, PRISM compilation/runtime and source parity; uv and package installation are boundary fixtures."""

from tempfile import gettempdir
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
FIXTURES = ROOT / "tests/mcp/fixtures"
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(FIXTURES),
    str(ROOT),
    *SITES,
]

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

import mathformer as hub
from setup_python_all_route_tools import ACTION, ROUTE, selected_match, checked_registry
from setup_python_all_route_boundary import DEPS, INSTALL
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_setup_python_all_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/setup-python-all-route.workflow.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": [ACTION]},
    "score": 17.5,
    "matched_terms": ["setup", "python"],
}
REGISTRY = {ACTION: hub.action_to_dict(hub.build_registry()[ACTION])}
ORDER = ["initialize", "select", "run_action", "advance", "finish"]


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "setup_python_all_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def populate(root):
    target = root / "scripts/install_env.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "scripts/install_env.py", target)
    assert target.read_bytes() == (ROOT / "scripts/install_env.py").read_bytes()


def binary(root):
    directory = root.parent / "bin"
    directory.mkdir(exist_ok=True)
    launcher = directory / "uv"
    launcher.write_text(
        "#!"
        + sys.executable
        + "\nimport sys\nsys.path.insert(0, "
        + repr(str(FIXTURES))
        + ")\nfrom setup_python_all_route_boundary import boundary\n"
        + 'raise SystemExit(boundary("uv"))\n'
    )
    launcher.chmod(0o755)
    return directory


def reset(root, mode="success"):
    shutil.rmtree(root / ".venv", ignore_errors=True)
    shutil.rmtree(root / ".lake", ignore_errors=True)
    (root / "unexpected.txt").unlink(missing_ok=True)
    (root.parent / "uv.jsonl").unlink(missing_ok=True)
    (root.parent / "mode.txt").write_text(mode)


def launches(root):
    path = root.parent / "uv.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
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


class SetupRouteTests(unittest.TestCase):
    maxDiff = None

    def test_contract_generator_and_provenance(self):
        document = yaml.safe_load(CONTRACT.read_text())
        spec = importlib.util.spec_from_file_location(
            "setup_route_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(generator.setup_python_all_route_descriptor(), document)
        self.assertEqual(document, json.loads((ROOT / AUTHORED).read_text()))
        self.assertEqual(document["id"], "route_setup_python_all_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 5},
        )
        self.assertEqual(
            document["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(list(document["operations"]), ORDER)
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                and row["selector"] == "run_intent_match"
                for row in document["provenance"]["sources"]
            )
        )
        full = hub.build_registry()
        self.assertEqual(
            checked_registry(
                {key: hub.action_to_dict(value) for key, value in full.items()}
            ),
            full,
        )
        self.assertIsNone(checked_registry(REGISTRY)[ACTION].timeout_seconds)
        audit = hub.audit_control(full)
        for entry in [
            "scripts/setup_python_all_route_tools.py",
            "tests/mcp/run_setup_python_all_route_workflow_tests.py",
            "tests/mcp/fixtures/setup_python_all_route_boundary.py",
        ]:
            self.assertNotIn(entry, audit["uncontrolled_entrypoints"])

    def test_native_state_history_sticky_failure_and_one_action_stop(self):
        for keep in [False, True]:
            for ok in [False, True]:
                state = hub.initialize_intent_state()
                before = deepcopy(state)
                child = {"ok": ok, "stdout": "native evidence"}
                updated, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 1
                )
                self.assertEqual(state, before)
                self.assertEqual(updated, {"ok": ok, "children": [child]})
                self.assertTrue(done)
                self.assertEqual(
                    hub.select_intent_action(state, selected_match(MATCH)), ACTION
                )
        for keep in [False, True]:
            updated, done = hub.advance_intent_state(
                {"ok": True, "children": []},
                {"ok": False},
                hub.RunContext(keep_going=keep),
                2,
            )
            self.assertEqual(done, not keep)
            updated, done = hub.advance_intent_state(
                updated, {"ok": True}, hub.RunContext(keep_going=True), 2
            )
            self.assertFalse(updated["ok"])
            self.assertEqual(updated["children"], [{"ok": False}, {"ok": True}])
            self.assertTrue(done)

    def test_registered_tools_lunar_compiler_runtime_and_parity(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            populate(root)
            bin_dir = binary(root)
            reset(root)
            server = (
                "import sys;sys.dont_write_bytecode=True;sys.path[:0]="
                + repr([str(ROOT / "scripts"), str(FIXTURES), str(ROOT), *SITES])
                + ";from setup_python_all_route_boundary import serve;serve("
                + repr(str(root))
                + ","
                + repr(str(bin_dir))
                + ")"
            )
            manager = SessionManager()
            async with manager.open(
                "setup-route",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {},
            ) as remote:
                failure = None
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(doc, inventory=None):
                        assets = snapshot(doc)
                        bound = compile_workflow(
                            "mcp:setup-route",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            tools if inventory is None else inventory,
                        )
                        return bound, assets

                    bound, assets = compile(document)
                    self.assertTrue(bound["runnable"], bound["diagnostics"])
                    self.assertEqual(bound["runtime_status"], "ready")
                    self.assertTrue(bound["prism_source"])
                    self.assertTrue(bound["runtime_source"])
                    self.assertEqual(set(bound["bindings"]), set(ORDER))
                    self.assertFalse(compile(document, [])[0]["runnable"])
                    broken = deepcopy(document)
                    broken["operations"]["run_action"]["execution"]["binding"][
                        "target"
                    ] = "absent_setup_tool"
                    self.assertFalse(compile(broken)[0]["runnable"])
                    advertised = {t["name"]: t for t in tools}
                    for op in document["operations"].values():
                        binding = op["execution"]["binding"]
                        self.assertEqual(binding["target"], binding["operation"])
                        tool = advertised[binding["target"]]
                        self.assertEqual(
                            set(tool["inputSchema"]["properties"]), set(op["inputs"])
                        )
                        self.assertEqual(
                            set(tool["outputSchema"]["properties"]), set(op["outputs"])
                        )

                    async def authorize():
                        pass

                    base = dict(
                        match=MATCH,
                        registry=REGISTRY,
                        repository_root=str(root),
                        context=vars(hub.RunContext(allow_mutating=True)),
                    )

                    async def run(inputs=None, doc=None):
                        c, a = compile(doc) if doc is not None else (bound, assets)
                        self.assertTrue(c["runnable"], c["diagnostics"])
                        return await execute(
                            c, a, base if inputs is None else inputs, remote, authorize
                        )

                    # Actual source installer in a temporary repository. No real uv,
                    # Python environment creation, provider, pip or Lean invocation.
                    for mode in [
                        "success",
                        "launch_failure",
                        "venv_failure",
                        "missing_python",
                        "installer_missing_uv",
                        "pip_failure",
                        "undeclared_write",
                    ]:
                        for keep in [False, True]:
                            reset(root, mode)
                            inputs = deepcopy(base)
                            inputs["context"]["keep_going"] = keep
                            result = await run(inputs)
                            self.assertEqual(result["status"], "accepted", result)
                            route = result["outputs"]["result"]
                            child = route["children"][0]
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], ORDER
                            )
                            self.assertEqual(
                                [c["tool"] for c in result["calls"]],
                                [
                                    "mathformer_setup_python_all_route_" + op
                                    for op in ORDER
                                ],
                            )
                            self.assertEqual(len(route["children"]), 1)
                            self.assertEqual(route["route"]["score"], MATCH["score"])
                            self.assertEqual(
                                route["route"]["matched_terms"], MATCH["matched_terms"]
                            )
                            self.assertEqual(route["ok"], mode == "success")
                            self.assertEqual(
                                route["status"],
                                (
                                    "intent_run_completed"
                                    if mode == "success"
                                    else "intent_run_failed"
                                ),
                            )
                            self.assertEqual(
                                child["argv"],
                                [
                                    "uv",
                                    "run",
                                    "python",
                                    "scripts/install_env.py",
                                    "--all-extras",
                                ],
                            )
                            calls = launches(root)
                            expected_calls = [INSTALL]
                            if mode not in ["launch_failure", "installer_missing_uv"]:
                                expected_calls.append(["venv", str(root / ".venv")])
                            if mode not in [
                                "launch_failure",
                                "installer_missing_uv",
                                "venv_failure",
                                "missing_python",
                            ]:
                                expected_calls.append(
                                    [
                                        "pip",
                                        "install",
                                        "--python",
                                        str(root / ".venv/bin/python"),
                                        *DEPS,
                                    ]
                                )
                            self.assertEqual(calls, expected_calls)
                            self.assertFalse((root / ".lake").exists())
                            if mode == "success":
                                self.assertEqual(child["returncode"], 0)
                                self.assertIn(
                                    "Installing Python dependencies: "
                                    + ", ".join(DEPS),
                                    child["stdout"],
                                )
                                self.assertIn(
                                    "Lean setup not requested.", child["stdout"]
                                )
                                self.assertIn(
                                    "Environment setup complete.", child["stdout"]
                                )
                                self.assertTrue((root / ".venv/bin/python").exists())
                            else:
                                self.assertFalse(child["ok"])
                                if mode == "undeclared_write":
                                    self.assertEqual(child["returncode"], 0)
                                    self.assertEqual(
                                        child["status"], "undeclared_writes"
                                    )
                                    self.assertEqual(
                                        child["write_audit"]["unexpected_paths"],
                                        ["unexpected.txt"],
                                    )
                                else:
                                    self.assertNotEqual(child["returncode"], 0)
                                    self.assertNotIn(
                                        "Environment setup complete.", child["stdout"]
                                    )
                            self.assertTrue(result["runtime"]["effect_records"])
                            self.assertTrue(result["runtime"]["provenance"])
                            self.assertTrue(result["replay_artifacts"])
                            reset(root, mode)
                            with patch.dict(
                                os.environ,
                                {
                                    "PATH": str(bin_dir),
                                    "PYTHONDONTWRITEBYTECODE": "1",
                                    "PYTHONUNBUFFERED": "1",
                                },
                                clear=True,
                            ):
                                expected = original().run_intent_match(
                                    selected_match(MATCH),
                                    checked_registry(REGISTRY),
                                    hub.RunContext(**inputs["context"]),
                                    repository_root=root,
                                )
                            self.assertEqual(route, expected)
                            self.assertEqual(launches(root), calls)
                    reset(root, "timeout")
                    inputs = deepcopy(base)
                    inputs["registry"][ACTION]["timeout_seconds"] = 7
                    result = await run(inputs)
                    child = result["outputs"]["result"]["children"][0]
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(child["status"], "timeout")
                    self.assertEqual(child["timeout_seconds"], 7)
                    self.assertIsNone(child["returncode"])
                    self.assertEqual(
                        (child["stdout"], child["stderr"]),
                        ("partial stdout", "partial stderr"),
                    )
                    self.assertFalse(result["outputs"]["result"]["ok"])
                    self.assertEqual([c["operation"] for c in result["calls"]], ORDER)
                    self.assertTrue(child["write_audit"]["ok"])
                    self.assertEqual(launches(root), [])
                    # Preflight failure and dry-run never reach uv. Both keep-going
                    # values still return exactly one child, with native metadata.
                    reset(root)
                    for missing in [False, True]:
                        if missing:
                            (root / "scripts/install_env.py").unlink()
                        for dry in [False, True]:
                            for keep in [False, True]:
                                inputs = deepcopy(base)
                                inputs["context"].update(
                                    dry_run=dry, keep_going=keep, allow_mutating=False
                                )
                                result = await run(inputs)
                                with patch.dict(
                                    os.environ, {"PATH": str(bin_dir)}, clear=True
                                ):
                                    expected = hub.run_intent_match(
                                        selected_match(MATCH),
                                        checked_registry(REGISTRY),
                                        hub.RunContext(**inputs["context"]),
                                        repository_root=root,
                                    )
                                self.assertEqual(
                                    result["outputs"], {"result": expected}
                                )
                                self.assertEqual(len(result["calls"]), 5)
                                self.assertEqual(launches(root), [])
                    populate(root)
                    uv_path = bin_dir / "uv"
                    uv_path.rename(bin_dir / "hidden")
                    result = await run()
                    self.assertFalse(result["outputs"]["result"]["ok"])
                    self.assertIn(
                        "missing required tool on PATH: uv",
                        result["outputs"]["result"]["children"][0]["preflight_errors"],
                    )
                    (bin_dir / "hidden").rename(uv_path)
                    # An executable uv with a missing interpreter passes tool
                    # discovery but raises at the actual native launch boundary.
                    launcher = uv_path.read_text()
                    uv_path.write_text(
                        f"#!{Path(gettempdir()) / 'mathformer-absent-interpreter'}\n"
                    )
                    try:
                        result = await run()
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], ORDER[:3]
                        )
                        self.assertEqual(result["calls"][-1]["status"], "rejected")
                        self.assertEqual(launches(root), [])
                    finally:
                        uv_path.write_text(launcher)
                    # The nullable default mount is preserved without launching.
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = True
                    inputs["repository_root"] = None
                    result = await run(inputs)
                    self.assertTrue(result["outputs"]["result"]["ok"])
                    self.assertEqual(
                        result["outputs"]["result"]["children"][0]["status"], "dry_run"
                    )
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = True
                    for port in ["registry", "match"]:
                        forged = deepcopy(inputs)
                        if port == "registry":
                            forged[port][ACTION]["notes"] = "forged notes"
                        else:
                            forged[port]["route"]["title"] = "forged title"
                        result = await run(forged)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            len(result["calls"]), 3 if port == "registry" else 2
                        )
                    # Both the candidate's minimal JSON projection and the MCP
                    # capped full registry hydrate the same native objects.
                    reset(root)
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = True
                    required = document["types"]["Registry"]["schema"]["properties"][
                        ACTION
                    ]["required"]
                    inputs["registry"] = {
                        ACTION: {key: REGISTRY[ACTION][key] for key in required}
                    }
                    result = await run(inputs)
                    expected = original().run_intent_match(
                        selected_match(MATCH),
                        checked_registry(inputs["registry"]),
                        hub.RunContext(**inputs["context"]),
                        repository_root=root,
                    )
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(launches(root), [])
                    from dataclasses import replace

                    capped = {
                        key: (
                            replace(value, timeout_seconds=600)
                            if value.command and value.timeout_seconds is None
                            else value
                        )
                        for key, value in hub.build_registry().items()
                    }
                    inputs["registry"] = {
                        key: hub.action_to_dict(value) for key, value in capped.items()
                    }
                    self.assertEqual(checked_registry(inputs["registry"]), capped)
                    result = await run(inputs)
                    expected = original().run_intent_match(
                        selected_match(MATCH),
                        capped,
                        hub.RunContext(**inputs["context"]),
                        repository_root=root,
                    )
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(
                        result["outputs"]["result"]["children"][0]["action"][
                            "timeout_seconds"
                        ],
                        600,
                    )
                    self.assertEqual(launches(root), [])
                    inputs = deepcopy(base)
                    inputs["context"]["dry_run"] = True
                    # Real runtime call budget and exhaustion guard. Changed graphs
                    # are test probes, never alternative production implementations.
                    for budget in [1, 4]:
                        changed = deepcopy(document)
                        changed["policy"]["limits"]["max_operation_calls"] = budget
                        result = await run(inputs, changed)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            sum(
                                bool(c.get("transport_call_performed"))
                                for c in result["calls"]
                            ),
                            budget,
                        )
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["until"] = {"literal": False}
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], ORDER[:-1]
                    )
                    self.assertIsNone(result["outputs"])
                    self.assertIn("exhaust", str(result).lower())
                    changed = deepcopy(document)
                    changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                        "state"
                    ] = {"literal": {"ok": True, "children": [{"ok": True}]}}
                    result = await run(inputs, changed)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 2)
                    inputs["context"]["dry_run"] = False
                    inputs["repository_root"] = str(root.parent / "outside")
                    result = await run(inputs)
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(len(result["calls"]), 3)
                    self.assertEqual(launches(root), [])
                    timed = deepcopy(document)
                    timed["policy"]["limits"]["wall_time_seconds"] = 1
                    c, a = compile(timed)

                    async def pending():
                        await asyncio.Event().wait()

                    with self.assertRaises(TimeoutError):
                        await execute(c, a, base, remote, pending)
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure

    def test_registered_readonly_and_unexpected_launch_exception(self):
        asyncio.run(self.admission())

    async def admission(self):
        from mcp.server.fastmcp import FastMCP
        from setup_python_all_route_tools import register_setup_python_all_route_tools
        import subprocess

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "repo"
            populate(root)
            bin_dir = binary(root)
            reset(root)

            def readonly():
                raise PermissionError("service read-only policy")

            for authorize, allowed, error in [
                (readonly, lambda p: True, "read-only"),
                (lambda: None, lambda p: False, "service roots"),
            ]:
                mcp = FastMCP("setup-policy")
                register_setup_python_all_route_tools(mcp, authorize, allowed)
                args = dict(
                    action_id=ACTION,
                    registry=REGISTRY,
                    repository_root=str(root),
                    context=vars(hub.RunContext(allow_mutating=True)),
                )
                with self.assertRaisesRegex(Exception, error):
                    await mcp.call_tool(
                        "mathformer_setup_python_all_route_run_action", args
                    )
                args["context"]["dry_run"] = True
                with patch.dict(os.environ, {"PATH": str(bin_dir)}, clear=True):
                    await mcp.call_tool(
                        "mathformer_setup_python_all_route_run_action", args
                    )
            # uv's unexpected launch error is an exception, not negative data.
            # Substitute only this external process boundary.
            mcp = FastMCP("setup-launch")
            register_setup_python_all_route_tools(mcp, lambda: None, lambda p: True)
            args["context"]["dry_run"] = False
            with (
                patch.dict(os.environ, {"PATH": str(bin_dir)}, clear=True),
                patch.object(
                    subprocess,
                    "run",
                    side_effect=OSError("fixture uv launch unavailable"),
                ),
            ):
                with self.assertRaisesRegex(Exception, "fixture uv launch unavailable"):
                    await mcp.call_tool(
                        "mathformer_setup_python_all_route_run_action", args
                    )
                with self.assertRaisesRegex(OSError, "fixture uv launch unavailable"):
                    original().run_intent_match(
                        selected_match(MATCH),
                        checked_registry(REGISTRY),
                        hub.RunContext(allow_mutating=True),
                        repository_root=root,
                    )
            self.assertEqual(launches(root), [])


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )
